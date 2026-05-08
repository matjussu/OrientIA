# Sprint 9 hierarchical — re-audit 2026-05-08

**Contexte** : Phase B4 du plan `verrouillage-bench-multi-tour`. Lever l'ambiguïté entre "Sprint 9 archivé NO-GO" (audit pipeline initial) et "Sprint 9 95% prêt à brancher" (mémoire perso). Décider Path A (intégrer Sprint 9) vs Path B (multi-tour minimal `ConversationState` réutilisant les bons composants Sprint 9).

**TL;DR** : **Path B retenu**. Les composants `Session` + `UserSessionProfile` sont réutilisables (state management correct). Mais l'orchestrateur `Coordinator` + `EmpathicAgent` réintroduiraient verbosité et réécriture des claims v4.1 strict — risque démesuré pour le gain.

---

## Inventaire `src/agents/hierarchical/`

Le code Sprint 9 est **présent sur main** (commit `8e2470c` HEAD), pas sur une branche séparée. Mais il est **uniquement exposé via `src/eval/systems.py:HierarchicalSystem`** pour benchmarker (mode `respond_single_shot` via `Session.new_for_bench()`). Aucun appel depuis `src/rag/pipeline.py` ni `src/api/server.py`.

| Fichier | Rôle | Statut multi-tour minimal |
|---|---|---|
| `session.py` (4.7 KB) | `Session` dataclass : turns, profile, flags `reco_requested_explicit`, `should_trigger_synthesizer()`, `history_messages()` | ✅ **Réutilisable tel quel** comme base de `ConversationState` |
| `schemas.py` (4.9 KB) | `UserSessionProfile` (niveau_scolaire, region, intérêts, contraintes, valeurs, confidence, tour_count) + `EmpathicResponse` | ✅ Profil **réutilisable**, EmpathicResponse non |
| `coordinator.py` (6.3 KB) | Orchestre les 3 agents, parallèle ThreadPoolExecutor, latency 33-43s mode reco | ❌ Trop lourd, latency excessive |
| `empathic_agent.py` (6.7 KB) | Foreground blocking, persona conseiller, **re-emballe la base factuelle** (line 116-125) | ❌ **Bloquant** : viole R1-R6 v4.1 strict |
| `analyst_agent.py` (7.1 KB) | Background, update `UserSessionProfile` via Mistral | ⚠ Coût ajouté, peut être remplacé par extraction inline dans le generator existant |
| `synthesizer_agent.py` (4.3 KB) | Embed `AgentPipeline` factuel, mode reco tour 3+ | ❌ AgentPipeline = autre POC NO-GO, pas v4.1 strict |

---

## Pourquoi Path A est risqué

### 1. EmpathicAgent réécrit les claims v4.1 strict

Code `empathic_agent.py:116-125` :
```python
if factual_base:
    system_parts.append(
        "## BASE FACTUELLE FOURNIE PAR LE SYNTHESIZERAGENT\n\n"
        "Ce qui suit est le résultat du pipeline RAG factuel "
        "(retrieval ONISEP/Parcoursup/etc.). Tu DOIS le "
        "re-emballer dans ta posture conseiller (reformulation "
        "+ 3 options pondérées + question finale). NE PAS le "
        "restituer brut — adapte au registre conversationnel.\n\n"
        f"{factual_base}"
    )
```

Le pipeline v4.1 strict produit des claims `[source SX]` sourcées via FactCard JSON (R1-R3) avec contrat 250 mots max (R6). L'EmpathicAgent prend ces claims **en input** et **demande au LLM de les reformuler** dans une "posture conseiller" expressive. Conséquences :
- Les `[source SX]` peuvent disparaître ou être mal réattribués
- `max_tokens=1500` (vs `400` v4.1 R6) → réponses 4× plus longues
- Pas de re-validation `corpus_check` post-réécriture → claims fabriqués passent

### 2. Latency explose en mode reco

Coordinator docstring (`coordinator.py:17-19`) :
```
Mode reco (tour 3+) : SynthesizerAgent ~30-40s + EmpathicAgent ~3s
                    + AnalystAgent ~3s (parallèle) ≈ 33-43s
```

Cible démo INRIA : p95 ≤ 12s. Mode reco hors budget par 3-4×.

### 3. Pas de bench v4.1 vs Sprint 9 mesurable

L'audit pipeline initial mentionnait "bench Sprint 12 NO-GO" — vérifié : `results/bench_sprint12_mistral_large_vs_medium/` compare en réalité **Mistral Large vs Medium**, **pas** Sprint 9 vs v4.1. Donc Sprint 9 n'a **jamais été benché contre la production v4.1 strict actuelle**. Path A demanderait un bench préalable pour justifier le risque (~$15-20 + 1 jour) — bénéfice incertain.

---

## Pourquoi Path B est solide

### 1. `Session` + `UserSessionProfile` couvrent le besoin "mémoire conversationnelle"

Le besoin Matteo : *"L'utilisateur peut poser plusieurs questions à la suite"*. Le composant `Session` répond exactement à ça :
- `turns: list[Turn]` — historique structuré (user/assistant + flag mode)
- `history_messages()` → format Mistral compliant pour generator (déjà attendu)
- `add_user_turn()` / `attach_assistant_response()` — API claire
- `tour_count` — pour adapter le comportement (ex: au tour 1, profil vide → 0 référence; au tour 3+, on peut citer "la 2e formation que tu as mentionnée")

`UserSessionProfile` est expressif (intérêts, contraintes, valeurs, questions ouvertes) — utile pour préserver le contexte mais peut être **rempli inline** par le generator existant (extraction simple en post-tour) plutôt que par AnalystAgent dédié.

### 2. `pipeline.answer()` accepte déjà `history`

Sprint 11 P0 Item 2 (`pipeline.py:258, 268-271, 280-281, 402, 477, 536`) : argument `history: list[dict] | None = None` supporté, format Mistral compliant `[{"role": "user"|"assistant", "content": str}]`, passé au generator. Default None = stateless v1 (pas de régression Run F+G). **L'infrastructure est prête, il manque juste le wiring `ConversationState` → `pipeline.answer(history=...)` + résolution des références ("la 2e formation que tu as citée").**

### 3. Path B = ajout, pas réécriture

Path B ajoute une couche `ConversationState` au-dessus du pipeline v4.1 sans modifier ce dernier. Path A remplace le générateur v4.1 par un Coordinator + EmpathicAgent. **Ajout < remplacement** en termes de risque produit.

---

## Composants Sprint 9 à réutiliser dans Path B

| Composant | Source | Réutilisation Path B |
|---|---|---|
| `Session` dataclass | `src/agents/hierarchical/session.py` | Importer ou inspirer un `ConversationState` light dans `src/rag/conversation.py` (Path B Phase E) |
| `Turn` dataclass | idem | Idem |
| `UserSessionProfile` (champs scalaires + listes + `merge_update`) | `src/agents/hierarchical/schemas.py` | Importer pour le buffer profil |
| `_EXPLICIT_RECO_REGEX` (regex patterns "donne-moi des reco") | `session.py:24-32` | Utile pour switch mode si on veut un mode "reco explicite" plus tard |
| `should_trigger_synthesizer()` | `session.py:81-97` | Pas réutilisé directement — Path B garde v4.1 toujours actif (pas de mode listening sans factual base) |

---

## Composants Sprint 9 à NE PAS importer

| Composant | Pourquoi pas |
|---|---|
| `Coordinator` | Orchestration 3-agents incompatible avec pipeline single-call v4.1 |
| `EmpathicAgent` | Réécrit les claims v4.1 strict (R1-R6 violation) |
| `AnalystAgent` | Background Mistral call coûteux — l'extraction profil peut être inline |
| `SynthesizerAgent` | Wrappe `AgentPipeline` (autre POC NO-GO), pas v4.1 |
| `persona_conseiller_v1.txt` | Encourage verbosité expressive vs R6 250 mots |

---

## Verdict

**Path B retenu** pour Phase E.GO. Architecture cible :

```
Frontend (Next.js)
    │ POST /answer { question, history: [{role, content}], session_id? }
    ▼
src/api/server.py
    │ pipeline.answer(question, history=request.history)
    ▼
src/rag/pipeline.py (v4.1 strict, inchangé)
    │ + injection conversation_context block (history → prompt context, séparé de <sources>)
    │ + résolution références ("la 2e formation que tu as citée") via last_sources
    ▼
src/rag/conversation.py (NOUVEAU)
    │ ConversationState dataclass : history, last_sources, extracted_profile
    │ + helpers serialize/deserialize pour API persistence
```

**Effort estimé Phase E.GO** : 2-3 jours (vs 1-2j Path A, mais Path A nécessiterait un bench préalable + diagnostic régression presque certain). Coût: 0 API additionnelle (pas de Mistral call dédié pour Analyst).

**Composants Sprint 9 importés** : `Session`, `Turn`, `UserSessionProfile.merge_update` (helpers), `_EXPLICIT_RECO_REGEX`. Le reste reste dans `src/agents/hierarchical/` comme **POC documenté**, accessible si on veut le re-bench post-démo.

**Risques résiduels Path B** :
- History poisoning (un mauvais tour 1 contamine les tours suivants) → tester avec questions adversarial multi-tour en Phase E
- Latency cumulée (history grossit → context window) → cap à 5 derniers tours

---

*Rapport produit en Phase B4 du plan verrouillage-bench-multi-tour. Lecture suggérée avant Phase E.GO.*
