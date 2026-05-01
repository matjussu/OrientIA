# Sprint 12 Axe 2 — S0' Audit complémentaire pipeline Sprint 1-4 axe B existant

**Date** : 2026-05-01 (post-STOP urgent Jarvis 17:43 CEST)
**Branche** : `main` (audit complémentaire post-A1+A2 livrés sur `feat/sprint12-axe-2-agentic-phase-1`)
**Référence ordre** : `2026-05-01-1820-claudette-orientia-sprint12-axe-2-agentic-phase-1-A1-A2-A4` (S0' réajustement post-erreur direction Jarvis)
**Auteur** : Claudette
**Scope** : audit historique projet 5 jours en arrière pour comprendre divergence pipeline Sprint 1-4 ↔ Sprint 9 ↔ Sprint 11 actuel.

---

## 1. État `src/agent/` Sprint 1-4 axe B sur main

**Tous mergés sur main efe28a2** (D1 mergé) :

| Module | Sprint | Commit clé | Statut |
|---|---|---|---|
| `src/agent/tools/profile_clarifier.py` (332l, Mistral Large) | Sprint 1 | `6f7b2ba` | ✅ mergé |
| `src/agent/tools/query_reformuler.py` (329l) | Sprint 2 | `546b7be` | ✅ mergé |
| `src/agent/tools/fetch_stat_from_source.py` (347l) | Sprint 3 | `c9aa6b1` | ✅ mergé |
| `src/agent/pipeline_agent.py` (328l, AgentPipeline end-to-end) | Sprint 4 | `3b75190` | ✅ mergé (PR ABOUTISSEMENT INRIA J-29) |
| `src/agent/agent.py`, `tool.py`, `cache.py`, `parallel.py`, `retry.py`, `streaming.py` | Sprints 1-3 infra | divers | ✅ mergés |

**Total infra Sprint 1-4 axe B** : ~1500 lignes mergées sur main. Présentes dans `git log main -- src/agent/*` confirmé. **Le pipeline agentique souverain Mistral function-calling EXISTE en prod**.

## 2. Pourquoi PAS dans `src/eval/systems.py` Run F+G

**Inspection `src/eval/systems.py`** : 8 classes Système :

1. `OurRagSystem` (Mistral medium + RAG single-shot, OrientIAPipeline)
2. `MistralRawSystem` (Mistral medium NEUTRAL prompt, no RAG)
3. `ChatGPTRecordedSystem` (recorded GPT-4o)
4. `MistralWithCustomPromptSystem` (sert `mistral_neutral` + `mistral_v3_2_no_rag`)
5. `OpenAIBaseline` (GPT-4o API)
6. `ClaudeBaseline` (Claude Sonnet)
7. **`HierarchicalSystem`** (Sprint 9 — wrap `Coordinator` qui embed `AgentPipeline` Sprint 4 via `SynthesizerAgent`)
8. (ABC base)

**AUCUN système direct nommé `our_rag_agent_pipeline_sprint4` qui invoque `AgentPipeline.answer(query)` directement**.

**Wrapping indirect** : `HierarchicalSystem.respond_single_shot()` (Sprint 9 PR #100 mergé 2026-04-29) `→ SynthesizerAgent.synthesize() → AgentPipeline (embedded TEL QUEL pattern strangler fig)`. Donc le pipeline EST utilisé dans le bench Mode Baseline mais à travers la couche Hierarchical (qui ajoute EmpathicAgent + AnalystAgent + Coordinator).

**Verdict** : pipeline pas orphan, mais activé dans un wrapping qui ne permet pas un bench standalone propre du `pipeline_agent.AgentPipeline` lui-même.

## 3. Lecture `docs/SPRINT4_AGENT_VS_BASELINE_VERDICT.md` — caveat latence ×3.2

**Caveat 3 documenté ouvertement** (lignes 56-72 du verdict) :

- **Latence pipeline Sprint 4 : 39.87s avg** (range 25-67s) vs baseline figée **12.35s avg** = ×3.2 plus lent
- Décomposition : ProfileClarifier ~2s + QueryReformuler ~9s + Retrieval parallel ~0.5s + **Génération finale Mistral Medium ~14-25s irréductible** + FetchStatFromSource parallel ~5-9s
- **Bottleneck principal = generation finale 2-3K tokens output** (Mistral Medium ~100ms/token)

**Levier comparable vs baseline** :
- Cohabitation user-naturel top-K : **1/10 (formation seul) baseline → 10/10 (10 corpora) pipeline Sprint 4** = gain structurel massif
- Erreur réglementaire psy_en : ❌ baseline (catch manuel Claude eval) → ✅ structurellement (LLM-judge agent)
- Success rate : 100 % vs 100 % (égalité)

**Décision push Sprint 4** (2026-04-26) : ✅ **PR ABOUTISSEMENT INRIA J-29 push-ready** — pivot architectural validé, 10 corpora actifs, anti-hallu structurelle, 0 régression technique. Caveats latence + fact-check méthode honnêtement documentés.

## 4. Pourquoi Sprint 11 P1.1 a optimisé single-shot Mistral medium au lieu de pipeline

**Hypothèse formulée** (audit indirect via timeline + journaux) :

- Sprint 9 (2026-04-28) : pivot conseiller conversationnel multi-tour. `HierarchicalSystem.respond_single_shot()` préserve bench Mode Baseline en embed `AgentPipeline` TEL QUEL via `SynthesizerAgent`. **Pipeline Sprint 4 est conservé, juste wrappé**.
- Sprint 10 (2026-04-29) : 4 chantiers RAG enrichissement (textualisation, RAG filtré, Q&A golden, test serving E2E). `OurRagSystem` (single-shot) reste le système référence pour ces enrichissements.
- Sprint 11 P0 (2026-04-29) : refonte SYSTEM_PROMPT 4 directives. Cible `OurRagSystem` (single-shot) car c'est le système où Matteo a observé les hallu Q5/Q8/Q10.
- Sprint 11 P1.1 (2026-04-30 → 2026-05-01) : optimisations prompt v5/v5b sur **`our_rag_v2_data`** (variante post-D1 du `OurRagSystem`). Latence ~9-18s acceptable user-facing.
- **Le pipeline Sprint 4 axe B (latence 40s) n'a pas été optimisé en parallèle** — probablement décision implicite "trop lent pour user-facing UX, attendre Sprint 12+ pour streaming user-side réduisant la latence perçue".

**Bottom line** : la divergence n'est pas une "abandon" du pipeline agentic — c'est une priorité de timing INRIA J-29 sur le quick win prompt single-shot. Le pipeline Sprint 4 existe, fonctionne (48/48 success Sprint 4 bench), reste dispo via HierarchicalSystem.

## 5. Bench medium vs large Sprint 2 (decision_ship_medium=false)

**Inspection `results/sprint2_profile_clarifier_medium_vs_large_2026-04-26.json`** :

Variant `large` (mistral-large-latest) :
- 15/15 success
- match_age_pct **83.3 %** (5/6)
- match_intent_pct **58.3 %** (7/12)
- avg_latency 2.08s

Decision : **`decision_ship_medium=false`** — Mistral Medium ne tient pas sur la classification ProfileClarifier function-calling. Mistral Large requis.

**Implication Phase 1 révisée** : si on active pipeline Sprint 4 dans `systems.py`, **on garde mistral-large pour function-calling tools** + mistral-medium pour la génération finale (cohérent stack Sprint 4 verdict).

## 6. Recommandation Phase 1 révisée — Option α (privilégiée)

**Option α — Activer pipeline Sprint 1-4 dans `systems.py` + bench empirique** (~2-3h dev, ~$30-50 bench)

Plan :
1. Ajouter `class AgentPipelineSystem(System)` dans `src/eval/systems.py` qui wrap `pipeline_agent.AgentPipeline.answer(query) → text`. Code existant, juste wrapping.
2. Bench 10q hold-out vs `mistral_v3_2_no_rag` (Mistral medium single-shot v3.2 prompt). Critère GO Δ Claude rubric > +0.5.
3. Tests + verdict doc.

**A1 (Pydantic contracts) + A2 (mapping rules) livrés ce matin restent UTILES** :
- A1 : interfaces I/O agnostiques d'orchestrateur — peuvent envelopper l'AgentPipeline output (ToolCallResult, AgentInput, AgentOutput) sans aucun changement architectural
- A2 : bridge dataclass libre-forme → enums typés — utile pour faire passer un profil Sprint 9 enriched en input à AgentPipeline si Phase 2+ cherche multi-tour

**Option β** — Si bench α révèle régression ou pipeline Sprint 4 broken post-Sprint 9 (ex : interfaces Mistral SDK changées) → identifier patch min + re-bench. ~+1-2j

**Option γ** — Sonnet 4.5 orchestrator UNIQUEMENT si α et β échouent + justification souveraineté FR mise en discussion ouverte. PAS prioritaire.

**Mon biais** : option α en premier parce que :
- Code existe (1500 lignes mergées) → coût marginal proche de 0
- Architecturé pour souveraineté FR (Mistral Large function-calling)
- Caveat latence ×3.2 connu mais pas blocker pour bench INRIA jury (UX user-facing améliorable Sprint 12+ via streaming)
- Évite réinvention Sonnet 4.5 que tu (Jarvis) a flaggé comme erreur direction

## 7. Critères mesurables Phase 1 révisée Option α

- AgentPipelineSystem class ajoutée systems.py (50 lignes max, wrapping)
- Bench 10q hold-out test set (pas dev set) avec Claude rubric judge (cf `src/eval/run_judge.py`)
- Métrique : `mean(rubric_score_agent_pipeline) - mean(rubric_score_mistral_v3_2_no_rag)` ≥ +0.5 → GO
- Latence p50 mesurée + documentée (acceptance INRIA jury vs UX user-facing distincts)
- 0 régression suite globale tests

## 8. Apprentissage #8 candidate

**"Audit historique projet 5+ jours en arrière obligatoire avant de proposer pivot architectural — éviter auto-symétrie roadmap qui ignore l'existant"** (proposed Jarvis 17:43).

L'erreur direction n'était pas un crash de A1+A2 dev — c'était la spec ordre Jarvis qui ignorait Sprint 1-4 axe B existant. La discipline corrective : avant de spec un pivot, lire docs/SPRINT*_VERDICT.md + git log -p src/agent/* pour les 5 derniers sprints.

## 9. Suite

Ping `s0-prime-audit-done` à Jarvis avec ce doc. Discussion conjointe option α / β / γ. Pas de code avant alignement.

---

**Coût audit** : $0. **Wall-clock** : ~25 min (lecture verdict Sprint 4 + SESSION_HANDOFF + grep systems.py + bench json).
