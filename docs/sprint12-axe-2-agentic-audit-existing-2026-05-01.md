# Sprint 12 Axe 2 Phase 1 — S0 Audit existing agentic infrastructure

**Date** : 2026-05-01
**Branche** : `feat/sprint12-axe-2-agentic-phase-1` (depuis `efe28a2` post-D1 mergé)
**Référence ordre** : `2026-05-01-1820-claudette-orientia-sprint12-axe-2-agentic-phase-1-A1-A2-A4` (Sous-étape 0)
**Auteur** : Claudette
**Scope** : audit code-only (no code S0), carte interfaces actuelles vs cibles A1/A2/A4, recommandations design.

---

## Inventaire 2 stacks agentic existants

### Stack legacy Sprint 1 axe B — `src/agent/` (~1500 lignes)

| Module | Lignes | Rôle |
|---|---|---|
| `tool.py` | 128 | `Tool` + `ToolRegistry` Mistral function-calling, `to_mistral_schema()`, `dispatch()` |
| `pipeline_agent.py` | 328 | Orchestration multi-tool agentic pipeline complète |
| `agent.py` | 160 | Wrapper agent stateful |
| `cache.py` | 107 | LRUCache pour tool calls |
| `retry.py` | 105 | `call_with_retry` pour Mistral API |
| `streaming.py` | 109 | Streaming events (token/tool_call/etc.) |
| `parallel.py` | 132 | ThreadPoolExecutor utilities |
| `tools/profile_clarifier.py` | 332 | `Profile` dataclass enums + Mistral force `tool_choice="any"` |
| `tools/query_reformuler.py` | 329 | Query expansion / reformulation |
| `tools/fetch_stat_from_source.py` | 347 | Anchor stat retrieval depuis source officielle |

### Stack moderne Sprint 9 hierarchical — `src/agents/hierarchical/` (~900 lignes)

| Module | Lignes | Rôle |
|---|---|---|
| `coordinator.py` | 166 | Orchestrateur entry-point user, dispatch ThreadPoolExecutor |
| `empathic_agent.py` | 171 | Foreground blocking, persona conseiller, ≤3s target |
| `analyst_agent.py` | 180 | Background parallèle, function-calling `update_session_profile` |
| `synthesizer_agent.py` | 115 | On-demand séquentiel, embed `AgentPipeline` legacy |
| `session.py` | 115 | State user-session multi-turn |
| `schemas.py` | 126 | `UserSessionProfile` + `EmpathicResponse` dataclasses |
| `__init__.py` | 46 | Exports publics |

`src/state/user_profile_schema.json` = source de vérité JSON schema (validation cross-agent).

---

## Overlap analysis pour A1 / A2 / A4

### A2 ProfileClarifier — RECOMMANDATION : étendre `AnalystAgent` Sprint 9

**Existing fait déjà** :
- `tools/profile_clarifier.py` (Sprint 1, single-shot) — `Profile` dataclass avec **enums stricts** (`age_group ∈ VALID_AGE_GROUPS`, `education_level ∈ VALID_EDUCATION_LEVELS`, `intent_type ∈ VALID_INTENT_TYPES`). Cible : routing retrieval (filter corpora, pondérer ranking).
- `agents/hierarchical/analyst_agent.py` (Sprint 9, multi-tour) — `UserSessionProfile` dataclass **libre-forme structuré** (`niveau_scolaire="terminale_spe_maths_physique"`). Cible : posture conseiller intra-session.

**Gap A2 Axe 2** :
- Spec ordre demande "ProfileClarifier extension AnalystAgent existant Sprint 9 (PAS réinvention)"
- Donc cible = AnalystAgent, pas Profile Sprint 1 legacy
- **Mais** Profile Sprint 1 a un asset précieux : enums typés pour routing retrieval downstream. Si Axe 2 doit ROUTER (search_formations etc.), il faut convertir `UserSessionProfile` libre-forme → enums typés à un moment.
- **Hypothèse design** : ajouter à AnalystAgent une méthode `to_routing_profile() → ProfileState` (Pydantic Axe 2) qui dérive les enums depuis le libre-forme via mapping rules + cache.

**Décision proposée S0** : extension de `AnalystAgent` avec une nouvelle méthode `analyze_for_routing(session)` qui :
1. Réutilise la machinerie function-calling Mistral existante (`update_session_profile` tool)
2. Produit en plus un `ProfileState` Pydantic typed (A1) avec enums routables
3. Le `UserSessionProfile` libre-forme reste préservé (compat Sprint 9 EmpathicAgent)

### A1 typed contracts Pydantic — RECOMMANDATION : ADDITIF (pas migration)

**Existing utilise dataclasses** : `Profile`, `UserSessionProfile`, `EmpathicResponse`, `CoordinatorTurnResult`, `Tool` — toutes en `@dataclass`.

**Spec A1 demande Pydantic** : `ProfileState`, `SubQuestion`, `ToolCallResult`, `AgentInput/Output`.

**Risque migration totale** : casser Sprint 9 + 30+ tests existants. Pas dans le scope Phase 1 (R3 isolated strict).

**Décision proposée S0** :
- **NEW** Pydantic models dans `src/axe2/contracts.py` (nouveau module) — couvre A1 spec
- **PRESERVE** dataclasses Sprint 9 — adapters bidirectionnels au besoin (`UserSessionProfile.from_pydantic(ProfileState)` et inverse)
- **ARGUMENTAIRE Pydantic > dataclass pour Axe 2** :
    - Validation runtime (vs dataclass = no-op type hints)
    - JSON schema export natif (utile pour orchestrator tool definitions)
    - `model_config = ConfigDict(extra="forbid")` strict
    - `Field(..., ge=0, le=1)` constraints (e.g. confidence)
    - Sérialisation `.model_dump_json()` consistent avec Anthropic SDK / OpenAI SDK

### A4 3 tools core — RECOMMANDATION : réutiliser `Tool`+`ToolRegistry` Sprint 1

**Existing fait déjà** :
- `Tool` dataclass + `ToolRegistry` (`src/agent/tool.py`) — pattern Mistral function-calling battle-tested
- `to_mistral_schema()` + `dispatch()` API stable

**Mais l'orchestrator cible est Anthropic Sonnet 4.5, pas Mistral**. Le format tool différe légèrement (`input_schema` vs `parameters`). Solutions :
1. Étendre `Tool` avec `to_anthropic_schema()` méthode (additif, ne casse rien Mistral)
2. Ou écrire un adapter `tool_to_anthropic(tool: Tool) → dict` standalone

**Décision proposée S0** : option 1 (méthode additive sur `Tool`). Préserve l'invariant unique dataclass = unique tool definition.

**Tools cibles A4** :
- `search_formations(query, niveau?, region?, domaine?, top_k=5)` → wrap `OrientIAPipeline` existant (`src/rag/pipeline.py`). Réutilisation directe.
- `get_debouches(rncp_or_nom, top_k=3)` → stub Phase 1, retour basique liste libellés ROME depuis fiches. Existing `fetch_stat_from_source.py` (347 lignes) probablement réutilisable partiellement.
- `get_admission_calendar(annee=2026)` → hardcoded Phase 1, retour static dict des phases Parcoursup (formulation vœux jan-mars, phase principale juin-juillet, complémentaire jul-sep).

---

## Orchestrator — confirmation Sonnet 4.5 vs alternatives

**Spec ordre recommande Sonnet 4.5** (STRATEGIE_VISION). Justifications retenues :
- ✅ Tool-use natif robuste vs Mistral function-calling (bench Sprint 9 montre que Mistral force `tool_choice="any"` car le modèle décroche parfois)
- ✅ Reasoning multi-step (chain-of-thought intégrée pour décider quel tool appeler)
- ✅ Souveraineté FR : générateur final reste Mistral medium → cohérent argument INRIA
- ✅ Coût acceptable : Sonnet 4.5 ~$3/MTok input, ~$15/MTok output. 10q bench S4 → ~$0.30-0.80 (input prompts ~5k tokens × 10q + output ~1-2k tokens × 10q)

**Alternative considérée** : Haiku 4.5 (latence-sensitive)
- ✅ Plus rapide ~1-2s vs ~3-5s
- ❌ Reasoning multi-step plus faible que Sonnet 4.5 sur tool orchestration
- ❌ Risque hallu tool-call plus élevé

**Alternative considérée** : Opus 4.7 (capability max)
- ✅ Capability max
- ❌ Coût ~5× Sonnet → bench S4 ~$2.5-4 acceptable mais marge ratée
- ❌ Surdimensionné Phase 1 minimal

**Recommandation S0 confirmée** : **Sonnet 4.5 pour orchestrator Phase 1**. Re-évaluation post-bench S4 GO/NO-GO si latence ou coût pose problème.

---

## Carte interfaces actuelles vs cibles A1/A2/A4

### Actuel (post-D1 efe28a2)

```
User query
  ↓
Coordinator (Sprint 9)
  ↓
  ├─ EmpathicAgent (Mistral, persona, 3s) ──→ EmpathicResponse (dataclass)
  ├─ AnalystAgent (Mistral, function-call) ──→ profile_delta (dict) ──→ UserSessionProfile (dataclass)
  └─ SynthesizerAgent (séquentiel, embed AgentPipeline) ──→ SynthesizedFactualBase
```

### Cible Axe 2 Phase 1 minimal (post-A4)

```
User query
  ↓
Sonnet 4.5 orchestrator (NEW) ──→ AgentInput (Pydantic)
  ↓ tool-use multi-step
  ├─ profile_clarifier (extension AnalystAgent) ──→ ProfileState (Pydantic, enum-typed)
  ├─ search_formations (NEW, wrap RAG) ──→ ToolCallResult { fiches[] }
  ├─ get_debouches (NEW stub) ──→ ToolCallResult { rome_libelles[] }
  ├─ get_admission_calendar (NEW hardcoded) ──→ ToolCallResult { phases[] }
  ↓ après ≤4 tool-calls, Sonnet décide stop
  ↓
Mistral chat.complete (générateur final, prompt enrichi par ProfileState + ToolCallResults)
  ↓
AgentOutput (Pydantic) ──→ user
```

**Phase 2 hors scope (séparée PR conditionnelle GO bench)** :
- A3 SubQuestionDecomposer
- A5 Composer
- A6 Validator (faithfulness gate avant émission)
- A7 streaming + UX (Frontia integration)

---

## Préservation pipeline single-shot existant

`our_rag_v2_data` (post-D1) reste accessible en parallèle dans `src/eval/systems.py` :
- `our_rag_v2_data` : pipeline Mistral medium prompt long single-shot v5b + backstop B soft (post-Sprint 11 mergé)
- `our_rag_v3_agentic_minimal` (NEW Phase 1) : flow Sonnet 4.5 orchestrator + Mistral générateur

Bench S4 compare les 2 systèmes côte-à-côte sur 10q hold-out. Critère GO Δ Claude rubric > +0.5.

---

## Risques + mitigations identifiés S0

| Risque | Mitigation |
|---|---|
| Migration Pydantic casse Sprint 9 dataclasses | A1 ADDITIF — nouveau module `src/axe2/contracts.py`, pas de modif schemas Sprint 9 |
| AnalystAgent extension casse profil Sprint 9 | A2 ajoute méthode `analyze_for_routing()`, préserve `update_profile()` existant |
| Tool format Sonnet ≠ Mistral incompatibilité | A4 ajoute méthode `to_anthropic_schema()` sur `Tool`, préserve `to_mistral_schema()` |
| Quota Anthropic Sonnet sature pendant bench S4 | MAX_CONSECUTIVE_429 strict (capitalisation Sprint 9 nuit 3 Apprentissage #5) + flag immédiat |
| Latence bench S4 ≫ single-shot (Sonnet 4.5 ~5s + Mistral ~10s = 15s/q) | Acceptable pour Phase 1 minimal. Phase 2 ajoutera streaming + cache pour latence cible |
| Critère GO Δ +0.5 ambigu | Mesure : Claude Sonnet 4.5 rubric judge (cf `src/eval/run_judge.py` existant), score 0-5, 5 critères, mean. Δ = mean(v3_agentic) - mean(v3_2_no_rag) |

---

## Livrables S0 (ce doc) + suite

- ✅ Inventaire 2 stacks agentic existants
- ✅ Overlap analysis A1/A2/A4 + recommandations design
- ✅ Carte interfaces actuelles vs cibles
- ✅ Confirmation Sonnet 4.5 orchestrator
- ✅ Risques + mitigations
- ✅ Préservation pipeline `our_rag_v2_data` parallèle (rollback safety net)

**Validation Pattern #3+#4 attendue Jarvis** sur ce doc AVANT démarrage S1 (A1 typed contracts Pydantic).

**Suite après GO** :
- A1 (~5h) : `src/axe2/contracts.py` — `ProfileState`, `SubQuestion`, `ToolCallResult`, `AgentInput`, `AgentOutput` Pydantic v2 + tests round-trip + validation
- A2 (~7h) : extension AnalystAgent `analyze_for_routing()` produisant `ProfileState` + tests mocks
- A4 (~10h) : 3 tools core + Tool.to_anthropic_schema() + tests
- Bench S4 (~2.5h, ~$30-50) : Sonnet 4.5 orchestrator running, 10q hold-out, decision gate GO/NO-GO

**ETA cumul** : ~25h cumul ≈ 3.5 jours wall-clock.
