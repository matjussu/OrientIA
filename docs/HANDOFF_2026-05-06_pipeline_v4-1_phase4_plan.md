# OrientIA — Handoff session 2026-05-06

**État** : refonte produit niveau 2 — fin de session avec v4.1 strict bascule par défaut.

**Pour la prochaine session** : ce document contient (1) le pipeline production actuel exact, (2) le plan détaillé Phase 4 multi-tour conversationnel.

---

## 1) Pipeline production actuel — détail end-to-end

Voici le flow exact d'une question utilisateur dans le pipeline qui sortirait de `make_production_pipeline(client, fiches)` aujourd'hui (post-commit `5f2b201`). C'est ce que verrait un lycéen qui tape sa question.

```
                          [Question utilisateur]
                                   │
                                   ▼
        ┌──────────────────────────────────────────────────┐
        │ ÉTAPE 1 — ScopeClassifier (amont)                 │
        │ ─────────────────────────────────                 │
        │ (a) Regex urgent pré-filter                       │
        │     • "suicide", "me tuer", "violences"... → URGENT
        │     → court-circuit en 0.0s                       │
        │                                                    │
        │ (b) Mistral Small (mistral-small-latest)          │
        │     • timeout 5s, 9 few-shot examples             │
        │     • classifie : urgent / out_of_scope / in_scope
        └──────────────────────────────────────────────────┘
            │             │              │
       URGENT         OUT_OF_SCOPE     IN_SCOPE
            │             │              │
            ▼             ▼              │
    URGENT_RESPONSE  OUT_OF_SCOPE_       │
    (3114, 3919,     RESPONSE            │
    119, 3018)       (reformule en       │
                     orientation)        │
            └─────────┬────┘              │
                      ▼                   │
             [Réponse pré-écrite]         │
             (~0-2s, 91-118 mots)         │
                                          ▼
        ┌──────────────────────────────────────────────────┐
        │ ÉTAPE 2 — Intent classifier                       │
        │ classify_intent() → 8 classes                     │
        │ (factual_pointed / comparaison / realisme /       │
        │  geographic / passerelles / decouverte /          │
        │  conceptual / general)                            │
        │ classify_domain_hint() → DARES / APEC / CROUS / ... │
        └──────────────────────────────────────────────────┘
                     │
                     ▼
        ┌──────────────────────────────────────────────────┐
        │ ÉTAPE 3 — SELECT bypass (si factual_pointed)     │
        │ ─────────────────────────────────                 │
        │ • try_select_or_none(question, fiches)            │
        │   - Detect field key (taux_acces, salaire, ...)   │
        │   - Extract entity (formation+ville+niveau)       │
        │   - Fuzzy match rapidfuzz ≥ 85                    │
        │   - INVALID_VALUES guard (0, null, N/A)           │
        │   - Anti-stale 18 mois                            │
        │ • Si match : RÉPONSE DÉTERMINISTE (zéro LLM)      │
        │   → return text, []                               │
        └──────────────────────────────────────────────────┘
                     │ (pas factual ou pas de match)
                     ▼
        ┌──────────────────────────────────────────────────┐
        │ ÉTAPE 4 — Retrieval                               │
        │ ─────────────────────────────────                 │
        │ • Embedding question (mistral-embed, 1024d)       │
        │ • FAISS IndexFlatL2 sur 48 914 fiches            │
        │ • retrieve_top_k(k=30)                            │
        │ • rerank() avec boosts (SecNumEdu 1.5, CTI 1.3)   │
        │ • Domain-aware reranker (ADR-049)                 │
        │ • MMR diversification (mmr_lambda par intent)     │
        │ • Metadata filter si criteria fourni              │
        │ → top_k_sources (variable selon intent)           │
        └──────────────────────────────────────────────────┘
                     │
                     ▼
        ┌──────────────────────────────────────────────────┐
        │ ÉTAPE 5 — Golden QA few-shot retrieval            │
        │ ─────────────────────────────────                 │
        │ • Embedding question (Mistral-embed)              │
        │ • FAISS Golden QA (4000 Q&A refined)              │
        │ • top-1 → exemple ton/structure UNIQUEMENT        │
        │ • Préfixe "IGNORE écoles/chiffres exemple"        │
        └──────────────────────────────────────────────────┘
                     │
                     ▼
        ┌──────────────────────────────────────────────────┐
        │ ÉTAPE 6 — Generation (mode v4.1 strict)          │
        │ ─────────────────────────────────                 │
        │ • format_sources_for_llm(top_5_sources)           │
        │   → JSON tabulaire `<sources>` typé via FactCard  │
        │ • _build_user_prompt_strict_v4()                  │
        │   → user message = Golden QA prefix + <sources>   │
        │     + question + rappel contrat                   │
        │ • SYSTEM_PROMPT_V4_STRICT (R1-R6)                 │
        │   - R1 chiffres uniquement depuis <sources>       │
        │   - R2 formations uniquement depuis <sources>     │
        │   - R3 [source SX] obligatoire après chiffre      │
        │   - R4 style libre depuis Golden QA               │
        │   - R5 posture empathique + question finale       │
        │   - R6 STRICT max 250 mots                        │
        │ • client.chat.complete(                           │
        │     model="mistral-medium-latest",                │
        │     temperature=0.3,                              │
        │     max_tokens=400)                               │
        │ → tour 1 answer (~7s, ~184 mots, ~9 citations)    │
        └──────────────────────────────────────────────────┘
                     │
                     ▼
        ┌──────────────────────────────────────────────────┐
        │ ÉTAPE 7 — Validator + retry-with-hint             │
        │ ─────────────────────────────────                 │
        │ • rules.py (anti-discrimination, no-chiffres-conv)│
        │ • corpus_check.py (claims vs corpus, sim 0.30)    │
        │ • presence.py (info obligatoire manquante)        │
        │ • [Layer3 LLM Mistral Small : OFF par défaut]    │
        │ → ValidatorResult (honesty_score, flagged)        │
        │                                                    │
        │ Si failed_claims ≠ vide ET budget timeout :       │
        │   → tour 2 avec hint réinjecté                    │
        │   → MAX_RETRIES_WITH_HINT = 1 cap dur             │
        │   → retry_stability metric                        │
        └──────────────────────────────────────────────────┘
                     │
                     ▼
        ┌──────────────────────────────────────────────────┐
        │ ÉTAPE 8 — UX Policy (Block / Warn / Modify)       │
        │ apply_policy(answer, validation)                  │
        │ → final_answer (peut être remplacé si BLOCK)      │
        └──────────────────────────────────────────────────┘
                     │
                     ▼
        ┌──────────────────────────────────────────────────┐
        │ ÉTAPE 9 — Phase projet minimal (V4)               │
        │ append_phase_projet(answer, question)             │
        │ → si question touche enjeu fort (HEC, PASS, kiné),│
        │   append 3Q réflexion + redirect CIO/Psy-EN       │
        └──────────────────────────────────────────────────┘
                     │
                     ▼
        ┌──────────────────────────────────────────────────┐
        │ ÉTAPE 10 — Post-process déterministe              │
        │ post_process_answer(answer, top)                  │
        │ • strip_invented_urls (github.com hallu)          │
        │ • fix_broken_markdown_tables                      │
        │ • validate_onisep_slugs (FOR.XXXX faux)           │
        └──────────────────────────────────────────────────┘
                     │
                     ▼
              [Réponse finale]
              (~7-12s, ~184 mots, sourcée)
```

### Coût et latency par étape (mesurés mini-bench v4.1)

| Étape | Latency | Coût LLM |
|---|---|---|
| 1 ScopeClassifier (Mistral Small) | 0.5-1s | ~$0.0005 |
| 2 Intent classifier | <0.01s | 0 (regex) |
| 3 SELECT bypass | <0.1s | 0 (déterministe) |
| 4 Retrieval (embed + FAISS) | 0.3s | ~$0.0001 |
| 5 Golden QA retrieval | 0.3s | ~$0.0001 |
| 6 Generation v4.1 (Mistral Medium) | **5-15s** | **~$0.001-0.003** |
| 7 Validator c1+c2 + retry potentiel | <0.5s (sans retry) / +5-15s (avec) | 0 (déterministe) |
| 8-10 Policy/Phase/Post-process | <0.1s | 0 (déterministe) |
| **TOTAL moyen** | **~7-12s** | **~$0.002-0.005** |

### Ce qui est ACTIVÉ par défaut

- ✅ ScopeClassifier (gate amont)
- ✅ Validator c1+c2 (rules + corpus_check + presence)
- ✅ Golden QA few-shot
- ✅ Post-process déterministe
- ✅ MMR diversification
- ✅ Intent classifier
- ✅ SELECT bypass factual_pointed
- ✅ Métadonnées filter (mais inactif sans criteria)
- ✅ **strict v4.1 (FactCard JSON + R6 max 250 mots)** ← bascule récente
- ✅ Retry-with-hint (cap 1, timeout 30s)
- ✅ UX Policy (Block/Warn/Modify)
- ✅ Phase projet minimal

### Ce qui est OFF par défaut

- ❌ Layer3 LLM Mistral Small (opt-in via `enable_layer3=True`, +$0.001/q)
- ❌ Mistral Large (rejeté ADR-053)
- ❌ Multi-tour conversationnel (Phase 4 à venir)

---

## 2) Plan Phase 4 — Multi-tour conversationnel

> On passe d'un Q&A single-shot à un conseiller multi-tour. La complexité n'est PAS technique (Sprint 9 hierarchical existe à 95%) — c'est **architecturale** : il faut décider comment greffer la mémoire de session sur le pipeline strict v4.1 sans casser l'honnêteté qu'on vient de construire.

### Vision finale Phase 4 (illustrée)

```
Tour 1 : "Je suis en terminale, j'hésite entre prépa et BUT info"
         ↓
         [Pipeline v4.1] + AnalystAgent extrait profil
         → Réponse exploration (questions ouvertes, 2-3 pistes)
         → UserSessionProfile = {niveau: "terminale", interets: ["info"]}

Tour 2 : "Je veux pas être loin de Lyon, et j'angoisse pour la prépa"
         ↓
         [Pipeline v4.1] + Profil enrichi
         → Réponse exploration (angoisse reconnue, géo Lyon ajoutée)
         → UserSessionProfile = {niveau: "terminale", interets: ["info"],
                                  contraintes: ["geo_Lyon"], emotion: "anxiete_prepa"}

Tour 3 : "Donne-moi des recos concrètes"
         ↓
         [Pipeline v4.1] + Profil mature + RECO MODE
         → 3 options pondérées (BUT info Lyon vs INSA Lyon vs alternative)
         → Question finale "qu'est-ce qui t'attire le plus ?"
```

### Approche en 4 sous-phases

#### Phase 4.1 (1 jour) — `ConversationalSystem` wrappant `OrientIAPipeline`

**Différence clé avec Sprint 9 original** : Sprint 9 hierarchical wrappait `AgentPipeline` (le POC sub-queries qui a son propre retrieval). Maintenant on a `OrientIAPipeline` v4.1 strict qui marche bien. Donc on simplifie :

```python
class ConversationalSystem:
    def __init__(self, pipeline: OrientIAPipeline,
                 client: Mistral,
                 store: SessionStore):
        self.pipeline = pipeline      # v4.1 strict
        self.analyst = AnalystAgent(client)  # Sprint 9 réutilisé
        self.store = store

    def continue_session(self, session_id: str, message: str) -> dict:
        session = self.store.load(session_id) or Session.new()
        session.add_user_turn(message)

        # Mode listening (tours 1-2) : exploration
        # Mode reco (tours 3+) : déclenchement pipeline complet
        if session.should_trigger_full_pipeline():
            # PIPELINE V4.1 STRICT avec history injecté
            text, sources = self.pipeline.answer(
                question=self._build_enriched_query(session),
                history=session.history_messages(),
            )
        else:
            # Mode listening léger : EmpathicAgent uniquement
            response = self.empathic.respond(session)
            text = response.to_user_text()

        # AnalystAgent extrait/met à jour le profil en parallèle
        delta = self.analyst.update_profile(session)
        session.profile.merge_update(delta)

        session.attach_assistant_response(text, ...)
        self.store.save(session)
        return {"text": text, "session_id": session_id, ...}
```

**Difficulté** : décider quand le pipeline v4.1 strict prend le relais vs quand l'EmpathicAgent répond seul. Si on appelle v4.1 à chaque tour, on coûte cher pour rien sur tour 1 ("je m'appelle Léa, je suis en terminale"). Solution : règle `should_trigger_full_pipeline()`.

#### Phase 4.2 (1 jour) — `SessionStore` SQLite

Persistence simple, pas de Redis. Schéma :

```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,           -- UUID
    profile_json TEXT,             -- UserSessionProfile sérialisé
    turns_json TEXT,               -- list[Turn]
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

Permet à un user de revenir 2 jours plus tard et continuer.

#### Phase 4.3 (0.5 jour) — `EmpathicAgent` parsing structuré

Aujourd'hui retourne `raw_text` monolithique. Avec sections markdown imposées, on parse :

```
**Reformulation :** Si je te comprends bien...
**Reconnaissance :** Tu sembles inquiet pour la prépa
**Exploration :** 3 questions pour creuser...
**Question :** Qu'est-ce qui te freine le plus ?
```

Permet au frontend de styliser chaque section.

#### Phase 4.4 (1 jour) — API FastAPI minimal

```
POST /sessions                          → {session_id}
POST /sessions/{id}/messages {message}  → {text, reco_mode_active, ...}
GET  /sessions/{id}                     → {profile, turns} (debug)
DELETE /sessions/{id}                   → cleanup
```

CORS basique localhost. Pas d'auth pour démo.

### Risques principaux Phase 4

1. **Coût latency** : tour 3 (reco mode) déclenche pipeline v4.1 complet (~7-12s) ENSUITE EmpathicAgent re-emballe la réponse en posture conseiller (+3-5s). Total 10-17s par reco. Acceptable mais limite.

2. **Cohérence honnêteté** : v4.1 strict garantit que la réponse "raw" est honnête. Si EmpathicAgent réécrit la réponse pour le ton, est-ce qu'il préserve les claims ? Risque de re-introduire les hallu qu'on vient de couper.

3. **`should_trigger_full_pipeline()` règle complexe** : Sprint 9 utilisait `tour >= 3 + confidence >= 0.5`. À adapter selon les vrais comportements utilisateurs.

4. **Session store SQLite** sur WSL2 = pas de souci performance, mais penser à WAL mode pour concurrence si plusieurs requêtes en parallèle.

5. **Test utilisateur réel obligatoire** : sans 5 lycéens qui parlent au système, on ne sait pas si le mode listening / reco est satisfaisant. Tu l'avais flaggé toi-même comme règle absolue (`feedback_spot_check_obligatoire.md`).

### Ordre recommandé

```
Étape 4-A (3h)  : Modif EmpathicAgent pour PRÉSERVER les claims du pipeline
                  v4.1 strict (pas de réécriture des chiffres). Test sur 3 cas.

Étape 4-B (1j)  : ConversationalSystem + intégration v4.1 strict en
                  retour pipeline. Mini-bench multi-tour 2 threads × 3 tours.

Étape 4-C (1j)  : SessionStore SQLite + tests round-trip.

Étape 4-D (0.5j): EmpathicResponse parsing structuré (regex sections).

Étape 4-E (1j)  : API FastAPI + README + 3 curl démo.

Étape 4-F (0.5j): Test utilisateur réel par toi avec 3 lycéens.

TOTAL : ~5-6 jours
```

### Inquiétude principale

L'EmpathicAgent du Sprint 9 a été conçu **avant** v4.1 strict. Il pouvait réécrire les chiffres librement parce que le pipeline en-dessous (AgentPipeline) était permissif. Avec v4.1 strict en-dessous, **on doit verrouiller l'EmpathicAgent pour qu'il ne réécrive pas les claims**.

C'est techniquement faisable mais c'est l'effort caché de Phase 4. Si on néglige ça, on annule les gains de la session courante.

**Proposition** : commencer par **Étape 4-A** (verrouillage EmpathicAgent) avant tout le reste. C'est 3h, low-risk, et ça valide qu'on peut greffer la couche conversationnelle sans casser l'honnêteté.

---

## 3) Contexte session courante (rappel)

### Commits livrés sur `docs/audit-golden-qa-2026-05-02`

```
5f2b201  v4.1 — R6 max 250 mots + top-5 + bascule par défaut
c9098fe  ADR-053 stratégie WHAT/HOW + SESSION_HANDOFF section 0
9a55c2c  Étape 2 itération — Mistral Large rejeté, scope++ conservé
e0845f7  Étape 2 — FactCard + prompt strict v4
2c8999d  Étape 1 — ScopeClassifier amont
bacb940  Audit retrieval quality
583be08  Phase 2.5+A — Layer3 + audit data
462b043  Phase 3 — ADR-052 critic_loop
5cd3643  Phase 2 — production factory
91d129b  Phase 1 — tri sec + experimental/
dd347da  Phase 0 — baseline
```

### Comparaison 4-way mini-bench (23 questions)

| Config | flagged | avg_hon | avg_lat | avg_words | Layer3 |
|---|---|---|---|---|---|
| v3.2 production | 0 | 1.0 | 10.19s | 239 | 37 |
| v4.0 strict (Med) | 1 | 0.993 | 46.87s | 434 | 34 |
| v4.0 (Lrg+scope++) | 1 | 0.989 | 25.25s | 479 | 38 |
| **v4.1 (R6+top5)** | **0** | **1.0** | **7.26s** | **184** | 40 |

**Conclusion** : v4.1 surpasse v3.2 production sur latency (-29%), longueur (-23%), honnêteté préservée (0 flagged), citations explicites systématiques. Layer3 +8% est un biais d'attribution (le LLM-judge pénalise la visibilité des chiffres sourcés).

### Pour démarrer la prochaine session

```bash
cd ~/projets/OrientIA && source .venv/bin/activate
git log --oneline -12                              # voir où on en est
cat docs/HANDOFF_2026-05-06_pipeline_v4-1_phase4_plan.md   # ce document
cat docs/SESSION_HANDOFF.md | head -80             # section 0 = état refonte
cat docs/DECISION_LOG.md | tail -250               # ADR-052 + ADR-053
```

**Prochain coup à jouer** : Étape 4-A (verrouillage EmpathicAgent vs v4.1 strict) puis 4-B (ConversationalSystem) → 4-F (test utilisateur réel).
