# Golden Pipeline OrientIA — Plan séquencé

> **Pipeline canonique cible** = fusion `src/agent/` Sprints 1-4 axe B agentic Mistral-large-latest + acquis Sprint 9-12 + Backstop B soft Sprint 11 P1.1
>
> **Statut** : peer-reviewed Claudette + validé Matteo 2026-05-01 19:10 CEST. À dispatcher 2026-05-02 matin.
>
> **Décision référence** : `~/obsidian-vault/08-Decisions/2026-05-01-golden-pipeline-axe-2-fusion-agentic-acquis-sprint-9-12.md`
>
> **Plan vault complet** : `~/obsidian-vault/01-Projets/Actifs/OrientIA-Golden-Pipeline-Plan-2026-05-01.md`

---

## Objectif

**Un seul pipeline canonical sur main** qui combine la somme des forces accumulées sur 5 sprints :
- Orchestration agentic Sprint 1-4 (3 tools mistral-large + cohabitation multi-corpus + fact-check in-loop + citation verbatim)
- Données enrichies Sprint 9-12 (corpus 55k normalisé + Q&A Golden + profil_admis + metadata filter + 4 directives prompt)
- Anti-hallu post-process Sprint 11 P1.1 (Backstop B soft optionnel en série après FetchStatFromSource)

**Pas de pipeline parallèle.** `pipeline_agent_golden` remplace progressivement `our_rag_enriched` post-validation.

---

## Plan séquencé 5 étapes (ETA 2-3j cumul, ~$8-12)

### Étape 1 — Corpus combined assembly (~0.5j, $0)

- [ ] Script `scripts/build_formations_golden_corpus.py` qui assemble :
  - `data/processed/formations_unified.json` 55 606 fiches (Sprint 10 chantier B + profil_admis Sprint 12 D1)
  - `data/processed/dares_corpus.json` (Sprint 6, blocs prospectifs DARES)
  - `data/processed/france_comp_blocs_corpus.json` (Sprint 6, blocs RNCP)
- [ ] Output `data/processed/formations_golden_pipeline.json`
- [ ] Garde field `source` discriminant
- [ ] `fiche_to_text()` étendu pour route sur `source` (formations_unified single-format vs corpora Sprint 6 multi-source)
- [ ] Tests unitaires (~5 cas par source)

### Étape 2 — Embedding rebuild (~0.5j, ~$3.5)

- [ ] Script `scripts/embed_golden_pipeline.py` (clone `embed_unified.py`)
- [ ] Output `data/embeddings/formations_golden_pipeline.index`
- [ ] **NE PAS écraser** `formations_unified.index` (218M actuel utilisé par `our_rag_enriched` Run F+G archive + bench α-comparatif S5)
- [ ] Documenter dans `src/rag/cli.py:INDEX_PATH` flag opt-in golden

### Étape 3 — Adaptations `pipeline_agent.py` (~1j, $0)

- [ ] **Migration corpus** : `AgentPipeline.fiches` accepte nouveau corpus combined
- [ ] **Q&A Golden injection** : 1 example par défaut (token budget safe), prefix system prompt générateur final
- [ ] **Metadata filter wrapping** : `apply_metadata_filter` wrap `retrieve_top_k` interne, `use_metadata_filter=True` quand `ProfileState` typé
- [ ] **Bridge A2** : commit `b452ada` (`src/axe2/profile_mapping.py` + `analyze_for_routing()`) câblé pour produire `Profile` enums + `ProfileState` Pydantic
- [ ] **4 directives prompt Sprint 11 P0** : Strict Grounding + Glossaire Anti-Amnésie + Progressive Disclosure + Format Adaptatif
- [ ] **Buffer mémoire short-term** : cap N=3 derniers tours
- [ ] **Backstop B soft optionnel post-process** : architecture en série après FetchStatFromSource

### Étape 4 — Tests régression + bench validation (~0.5j, ~$3-5)

- [ ] Update tests potentiellement impactés (estimation 30-100) :
  - `test_systems.py`, `test_hierarchical_archi.py`, `test_pipeline_agent_*.py`, `test_metadata_filter.py`
- [ ] Cible suite globale : ≥2071 tests verts, 0 régression
- [ ] **Bench validation 10q hold-out** : `pipeline_agent_golden` vs `our_rag_enriched`
- [ ] **Critère succès** : golden ≥ our_rag_enriched sur **7/10 questions minimum**
- [ ] Sample 3 questions verbatim Pattern #4

### Étape 5 — Verdict + PR #117 (~0.5j, $0)

- [ ] Doc verdict `docs/sprint12-axe-2-golden-pipeline-2026-05-01.md` (~150 lignes)
- [ ] PR #117 ready-for-review avec flag `pipeline_agent_golden` dans `src/eval/systems.py`
- [ ] `our_rag_enriched` reste accessible (rollback safety net + bench A/B)
- [ ] Update `docs/SESSION_HANDOFF.md` section "Pipeline canonique"
- [ ] Update `docs/DECISION_LOG.md` ADR-XXX

---

## Décisions techniques tranchées (peer review Claudette)

| Question | Décision |
|---|---|
| Tools `mistral-large-latest` ? | **MAINTENU** (bench Sprint 2 `decision_ship_medium=false` empirique) |
| FetchStatFromSource ON/OFF ? | **ON par défaut** bench config + flag opt-out user-facing UX (latence +5-10s) |
| Backstop B + FetchStatFromSource | **Complémentaires en série** : FetchStat in-loop top-5 + Backstop post-process annote restants |
| Q&A Golden cap exemples ? | **1 example par défaut** (token budget safe ~20-23k vs 32k Mistral medium) |
| Buffer mémoire profondeur ? | **N=3 derniers tours max** |
| Index naming ? | `formations_golden_pipeline.index` (NE PAS écraser `formations_unified.index`) |
| `our_rag_enriched` dépréciation ? | **Garder les 2** post-merge, déprécier après 3 mois sans régression |

---

## 6 risques structurels identifiés (peer review Claudette)

| # | Risque | Mitigation | Coût |
|---|---|---|---|
| 1 ⚠️ | Bridge `Profile` Sprint 1 ↔ `UserSessionProfile` Sprint 9 | Bridge A2 commit `b452ada` à câbler | +0.5j |
| 2 ⚠️ | Token limit ~20-23k vs 32k Mistral medium | Cap Q&A Golden 1 example + buffer 3 tours | minimal |
| 3 ⚠️ | 30-100 tests régression à updater | Inclus dans 0.5j étape 4 | inclus |
| 4 🟡 | D5/D3/FALC pause s'absorbent dans golden | Gain stratégique, documenter dans verdict | gain |
| 5 🟡 | Index naming registry | Documenter `src/rag/cli.py:INDEX_PATH` | minimal |
| 6 🟡 | Dépréciation `our_rag_enriched` | Garder les 2, déprécier après 3 mois | aucun |

---

## Critères succès simples

- ✅ 0 régression suite globale (≥2071 tests verts)
- ✅ Bench validation : golden ≥ our_rag_enriched sur 7/10 questions minimum
- ✅ Latence <30s acceptable INRIA (vs 39.87s Sprint 4 verdict avec fact-check ON)
- ✅ Coût total <$15 cumul (rebuild + bench + judge)
- ✅ Cohabitation multi-corpus ≥5 corpora actifs sur 10q

---

## Apprentissages capitalisés

- **#8** : Audit historique projet 5+ jours obligatoire avant tout pivot architectural
- **#9** : Vérifier convergence acquis entre 2 stacks parallèles avant tout bench/pivot
- **#10** : Bench biaisé par data différentes ≠ verdict définitif — toujours apple-to-apple ou pas de conclusion
- **#11** : Peer review plan multi-jour OBLIGATOIRE avant dispatch formel (Claudette + Jarvis alignement pré-action)

---

*Doc plan filesystem côté repo OrientIA. Source de vérité unique pour le scope golden pipeline. Plan vault complet avec contexte/historique : `~/obsidian-vault/01-Projets/Actifs/OrientIA-Golden-Pipeline-Plan-2026-05-01.md`.*
