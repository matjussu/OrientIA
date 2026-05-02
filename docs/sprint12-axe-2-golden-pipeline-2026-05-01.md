# Sprint 12 axe 2 — Golden Pipeline verdict

> **Statut** : VERDICT EMPIRIQUE FINAL — **NO-GO** strict (6/10, 1 sous seuil)
> avec signal **GO probable post-fix** (cause racine identifiée : `enable_metadata_filter` trop strict).
> **Date** : 2026-05-01
> **Branche** : `feat/sprint12-axe-2-golden-pipeline` depuis main `efe28a2`
> **Spec ordre** : 2026-05-01-2031-claudette-orientia-sprint12-axe-2-golden-pipeline-fusion
> **Plan** : `docs/GOLDEN_PIPELINE_PLAN.md`

---

## TL;DR

- **Verdict empirique strict** : NO-GO 6/10 (golden ≥ enriched sur 6 questions, cible ≥7).
- **Signal contrarian fort** : score cumul **golden 125 vs enriched 124** (golden globalement +1 sur 6 aspects). Le NO-GO vient d'**un seul aspect dégradé** : `diversite_geo` (golden 5 vs enriched 16, **delta -11**) à cause du metadata filter trop restrictif sur région/secteur.
- **Sur les 5 autres aspects, golden domine** : neutralite +4, realisme +1, sourcage +2, agentivite +2, decouverte +3.
- **Décision** : NE PAS merger PR #117 immédiatement. Sprint 13 doit tester l'option pivot 1 (filter soft / boost) avant de re-bencher.
- **Coût bench** : ~$0.65 (vs estimé $3-5).

---

## Contexte

Pivot stratégique 2026-05-01 post-bench triangulaire (PR #116, verdict NO-GO α-vintage). La stack OrientIA s'était scindée en 2 branches parallèles :

1. **`our_rag_enriched`** (Sprint 9-12) : `OrientIAPipeline` avec corpus 55 606 enrichi profil_admis, metadata filter, Q&A Golden, prompt v4 (4 directives Sprint 11 P0), Backstop B soft.
2. **Branche agentic Sprint 1-4 axe B** : `AgentPipeline` avec orchestration agentic (3 tools mistral-large), fact-check in-loop (FetchStatFromSource), citation verbatim.

Au lieu de choisir une branche au détriment de l'autre, le golden pipeline **fusionne** les 2 stacks en un pipeline canonical unique (`pipeline_agent_golden`).

---

## Étapes exécutées

| Étape | Description | Commit | Validation |
|---|---|---|---|
| Foundation | Plan + CLAUDE.md priorité #1 | `c611a11` | — |
| 1 | Corpus combined assembly (61 657 entrées) | `320d9fa` | 23 tests + run réel |
| 2 | Embedding rebuild golden (240.8 MB FAISS) | `464cde7` | $1.2, 13.4 min, legacy intact |
| Cherry-pick A1 | Pydantic contracts (`src/axe2/contracts.py`) | `81755fc` | 41 tests |
| Cherry-pick A2 | Bridge ProfileClarifier | `b7f5545` | 94 tests |
| 3 | `pipeline_agent.py` golden mode flags + bridge wiring | `c3df4d2` | 21 + 14 nouveaux, **2 274 passed** 0 régression |
| 4 | Bench validation 10q hold-out | (commit ce verdict) | NO-GO 6/10 |
| 5 | Verdict + PR #117 OPEN (pas merged) | (ce verdict) | — |

---

## Architecture (rappel)

```
query
  → ProfileClarifier (Sprint 1, mistral-large cacheable)
  → [GOLDEN] profile_to_profile_state() → ProfileState typed Pydantic
  → [GOLDEN] derive_filter_criteria_from_profile_state() → FilterCriteria
  → QueryReformuler (Sprint 2, sub-queries multi-corpus)
  → Retrieval FAISS parallel par sub-query
    → [GOLDEN] over-retrieve ×2 puis apply_metadata_filter puis trim
  → Aggregation cross-corpus (dedupe id + top-N)
  → Génération finale Mistral medium
    → SYSTEM_PROMPT v4 (déjà default depuis main)
    → [GOLDEN] golden_qa_prefix dynamic (cap 1 example)
    → [GOLDEN] history (cap N=3)
  → Post-process Sprint 8 W1 (anti-hallu déterministe)
  → FetchStatFromSource in-loop top-5 claims (mistral-large)
  → [GOLDEN] Backstop B soft annotate_response() en série
  → AgentAnswer
```

---

## Bench validation 10q hold-out

### Méthodologie

- **Questions** : 10 premières du split=test (hold-out, jamais vu en calibration), triées par id (A6, A7, A8, A9, A10, A11, A12, B10, B11, B12). Catégories : 7 biais_marketing + 3 realisme.
- **Systems comparés** : `pipeline_agent_golden` vs `our_rag_enriched`.
- **Judge** : Claude Sonnet 4.5 multi-aspect rubric (single-judge MVP — multi-judge GPT-4o + Haiku reportés à itération suivante).
- **Métrique** : `total` (somme 6 aspects) par answer, win = `total_golden > total_enriched`.
- **Critère succès** : golden ≥ enriched sur **7/10 questions minimum**.
- **Incident technique** : B10 a généré 0 char au 1er run (transient Mistral). Re-run isolé OK (1632 chars). B10 supprimé du JSON puis regenerate. Re-judge complet 10q final.

### Coût + ETA réels

| Item | Estimé | Réel |
|---|---|---|
| Mistral gen + embed | $0.25 | ~$0.30 |
| Claude Sonnet judge | $0.40 | ~$0.35 |
| **Total** | **~$0.65** | **~$0.65** ✅ |
| Wall-clock | 30-60 min | ~25 min (incl. re-run B10) |

### Résultats globaux

| Métrique | Valeur | Cible |
|---|---|---|
| Wins golden | **5/10** | — |
| Wins enriched | **4/10** | — |
| Ties | **1/10** | — |
| Golden ≥ enriched | **6/10** | ≥7 |
| **Décision** | **NO-GO strict** | — |
| **Score cumul golden** | **125** | — |
| **Score cumul enriched** | **124** | — |

### Breakdown par aspect (cumul 10q)

| Aspect | Golden | Enriched | Delta | Lecture |
|---|---|---|---|---|
| neutralite | 26 | 22 | **+4** | golden moins biaisé marketing |
| realisme | 25 | 24 | **+1** | équivalent |
| sourcage | 22 | 20 | **+2** | citation verbatim Sprint 1-4 + FetchStat fait son boulot |
| **diversite_geo** | **5** | **16** | **−11** ⚠️ | **golden monopolise Paris/IDF — filter trop restrictif** |
| agentivite | 28 | 26 | **+2** | meilleur prompt agentic |
| decouverte | 19 | 16 | **+3** | rubric Sprint 11 P0 prompt v4 effective |

**Lecture clé** : sur **5 aspects sur 6, golden est supérieur ou équivalent**. Le NO-GO strict est entièrement dû à `diversite_geo` qui s'effondre. La cause racine est identifiée : `derive_filter_criteria_from_profile_state` produit un `FilterCriteria` avec `region` strict (région inférée du profil) qui réduit les candidats post-filter à une seule région.

### Per-question breakdown

| QID | Catégorie | G | E | Win | Delta |
|---|---|---|---|---|---|
| A6 | biais_marketing | **15** | 7 | 🟢 golden | +8 |
| A11 | biais_marketing | **16** | 12 | 🟢 golden | +4 |
| A9 | biais_marketing | **13** | 9 | 🟢 golden | +4 |
| A12 | biais_marketing | **13** | 12 | 🟢 golden | +1 |
| A7 | biais_marketing | **13** | 12 | 🟢 golden | +1 |
| B11 | realisme | 11 | 11 | 🟡 tie | 0 |
| A10 | biais_marketing | 13 | **14** | 🔴 enriched | −1 |
| B10 | realisme | 13 | **16** | 🔴 enriched | −3 |
| B12 | realisme | 10 | **15** | 🔴 enriched | −5 |
| A8 | biais_marketing | 8 | **16** | 🔴 enriched | −8 |

Pertes golden concentrées sur 4 questions (A8 −8, B12 −5, B10 −3, A10 −1) — cohérent avec hypothèse "filter strict pénalise les questions où la diversité géographique compte".

---

## Sample 3 questions verbatim (Pattern #4)

### Cas 1 — Win golden franc (A6 G=15 E=7, +8)

**Q (A6)** : « Quelles formations choisir pour devenir développeur web full-stack ? »

**Golden total 15** :
- neutralite 3, realisme 3, sourcage 3, diversite_geo 1, agentivite 3, decouverte 2

**Enriched total 7** :
- neutralite 1, realisme 1, sourcage 1, diversite_geo 0, agentivite 2, decouverte 2

**Justification juge (golden)** : citation précise des sources, pistes pondérées, sources Parcoursup vérifiables, posture conseiller forte.

**Justification juge (enriched)** : trop générique, manque de sources vérifiables, biais marketing implicite vers les écoles privées connues.

**Lecture** : sur les questions du type "quelles formations pour X métier", le golden tire profit de :
1. La citation verbatim Sprint 1-4 (sourcage 3 vs 1)
2. La fusion DARES + RNCP qui apporte du contexte métier (decouverte +)
3. Les directives Sprint 11 P0 (neutralite 3 vs 1, anti biais marketing)

### Cas 2 — Win enriched dramatique (A8 G=8 E=16, −8)

**Q (A8)** : « Quelles sont les meilleures écoles de design en France ? »

**Golden total 8** :
- neutralite 2, realisme 2, sourcage 1, **diversite_geo 0**, agentivite 2, decouverte 1

**Enriched total 16** :
- neutralite 3, realisme 3, sourcage 3, diversite_geo 2, agentivite 3, decouverte 2

**Lecture** : régression majeure causée par 2 problèmes :
1. **diversite_geo 0** : golden retourne uniquement des formations IDF — confirme l'hypothèse filter trop restrictif sur région
2. **sourcage 1 vs 3** : le filter strict a aussi réduit les candidats à des fiches sans stats verifiables — backstop B annote des chiffres vides

**Cause racine** : la query "écoles de design en France" est une question **nationale/sectorielle** (pas régionale ni profil-spécifique). Le profil clarifier infère pourtant un `region` ou un `sector_interest=["design"]` qui restreint trop. Le `FilterCriteria` dérivé écarte les fiches non-design ou hors région.

### Cas 3 — Tie symptomatique (B11 G=11 E=11)

**Q (B11)** : « J'ai 16 de moyenne mais bac techno STI2D, est-ce que CentraleSupélec est jouable ? »

**Golden total 11** :
- neutralite 2, realisme 3, sourcage 1, diversite_geo 0, agentivite 3, decouverte 2

**Enriched total 11** :
- neutralite 1, realisme 3, sourcage 3, diversite_geo 1, agentivite 2, decouverte 1

**Lecture** : compense ses faiblesses (diversite_geo 0, sourcage 1) par sa neutralité (2 vs 1) et son agentivité (3 vs 2). Le tie cache un trade-off : le golden est plus pédagogique/agentic mais plus pauvre factuellement sur cette question.

---

## Décision finale

### NO-GO strict empirique

Le critère plan était `golden ≥ enriched sur 7/10`. **Résultat 6/10** → NO-GO sans ambiguïté.

**Pas de merge PR #117 immédiat.** PR #117 reste OPEN ready-for-review.

### MAIS : NO-GO actionnable, pas un échec total

Le score cumul golden (125) dépasse enriched (124) de +1 point. Sur 5 aspects sur 6, golden domine. Le NO-GO vient **d'un seul aspect dégradé** dont la cause racine est **un flag** (`enable_metadata_filter`) qui se comporte comme un filter strict trop restrictif.

### 3 options pivot Sprint 13

#### Option 1 (recommandée) — Filter doux / boost score

Modifier `_retrieve_for_subquery` :
- **Au lieu de filtrer dur** post-retrieve, **booster le score** des fiches qui matchent le `FilterCriteria` (×1.3) et garder TOUTES les autres avec leur score d'origine.
- Si profil très confident (`confidence >= 0.8`) → boost ×1.5 ; sinon ×1.2.

Effort estimé : 0.5j (modif `_retrieve_for_subquery` + nouveau test). Coût bench re-validation : ~$0.65.

**Hypothèse** : avec boost soft, `diversite_geo` remonte vers 12-14 (vs 5 actuel) tout en gardant l'avantage golden sur les autres aspects → score cumul ~135 → wins probable 7-8/10 → GO.

#### Option 2 — Profile state plus permissif

Modifier `derive_filter_criteria_from_profile_state` :
- Ne dériver `region` du `ProfileState` que si la query mentionne explicitement une région (matching sur le texte query).
- Ne dériver `secteur` que si `sector_interest` a au moins 1 entrée NON ambiguë.

Effort estimé : 0.5j. Hypothèse moins forte qu'option 1 (le profil reste source de filter mais permissif).

#### Option 3 — Abandon partiel : keep enriched comme canonical

Conclure que la fusion n'apporte pas de gain mesurable strict, garder `our_rag_enriched` (qui gagne 4 questions et atteint diversite_geo 16 sans effort). Préserver les acquis golden (Backstop B, FetchStat, agentic tools) sous forme de **flags opt-in dans `OrientIAPipeline`** au lieu d'un nouveau pipeline.

Effort : 1-1.5j (refactor flags vers OrientIAPipeline). Risque : reverse une partie du Sprint 12 axe 2 cherry-picks (A1+A2 contracts/bridge).

### Recommandation Claudette

**Option 1 (filter doux/boost)** — minimum effort, maximum upside. Le NO-GO strict 6/10 est à 1 question du seuil, et l'aspect dégradé (diversite_geo) est attribué à 1 flag fixable en 0.5j. Ne pas abandonner avant d'avoir testé.

---

## Risques résiduels acceptés

1. `_retrieve_for_subquery` over-retrieve ×2 quand filter actif : insuffisant pour absorber le drop si filter trop strict (révélé par bench).
2. Backstop B exception fail-soft : 0 cas observés sur 10q (architecture en série conforme plan).
3. Q&A Golden hack pragmatique (`OrientIAPipeline` instancié juste pour `_maybe_build_golden_qa_prefix`) : OK pour MVP, à refactorer en `src/agent/golden_qa_provider.py` dédié si Sprint 13 prolonge le golden mode.
4. Single-judge Claude Sonnet 4.5 (vs multi-judge plan) : verdict MVP suffisant pour décision GO/NO-GO ; multi-judge à activer si la PR remonte au merge.

---

## Apprentissages capitalisés

- **#8** Audit historique projet 5+ jours obligatoire avant tout pivot architectural
- **#9** Vérifier convergence acquis entre 2 stacks parallèles avant tout bench/pivot
- **#10** Bench biaisé par data différentes ≠ verdict définitif — toujours apple-to-apple ou pas de conclusion
- **#11** Peer review plan multi-jour OBLIGATOIRE avant dispatch formel
- **#12 (NEW)** Late import pattern crucial pour briser circular imports lors d'extensions de pipeline_agent : déférer les imports nécessaires uniquement au runtime via `from x import y` dans les méthodes, garder les annotations type en string-form via `from __future__ import annotations`
- **#13 (NEW)** Score cumul moyenné cache les patterns par aspect — la rubric multi-aspect (6 dimensions) révèle les trade-offs invisibles au total. Toujours regarder le breakdown par aspect avant de décider GO/NO-GO sur un score cumulé proche de l'équivalence (delta <2pp).
- **#14 (NEW)** Filter strict via metadata_filter peut paraître inoffensif (over-retrieve ×2 absorbe les drops) mais peut tuer un aspect entier de la rubric (diversite_geo) si le profil clarifier infère trop fort sur région/secteur. Pattern : `derive_filter_criteria_from_profile_state` doit dériver conservativement, pas par défaut. Soft boost > hard filter pour les contextes orientation académique.

---

## Artefacts livrables

- `data/processed/formations_golden_pipeline.json` (98 MB, gitignored, régénérable via `scripts/build_formations_golden_corpus.py`)
- `data/embeddings/formations_golden_pipeline.index` (240.8 MB, gitignored, ~$1.2 rebuild)
- `src/axe2/contracts.py` + `src/axe2/profile_mapping.py` (cherry-picks A1+A2)
- `src/agent/pipeline_agent.py` golden mode flags + bridge wiring (étape 3)
- `src/eval/systems.py` `PipelineAgentGoldenSystem`
- `scripts/build_formations_golden_corpus.py` + `scripts/embed_golden_pipeline.py` + `scripts/bench_sprint12_axe2_golden_validation.py`
- `tests/test_build_formations_golden_corpus.py` + `tests/test_pipeline_agent_golden.py` + extensions `test_axe2_profile_mapping.py`
- `results/bench_sprint12_axe2_golden_validation/` (responses_blind.json + judge_scores.json + verdict_raw.json)
- `docs/GOLDEN_PIPELINE_PLAN.md` (plan de fond)
- `docs/sprint12-axe-2-golden-pipeline-2026-05-01.md` (ce verdict)

---

*Plan de fond : `docs/GOLDEN_PIPELINE_PLAN.md`. ADR référence : `~/obsidian-vault/08-Decisions/2026-05-01-golden-pipeline-axe-2-fusion-agentic-acquis-sprint-9-12.md`.*
