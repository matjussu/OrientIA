# Sprint 12 axe 2 — Test 1 (apple-to-apple) verdict FINAL

> **Statut** : VERDICT EMPIRIQUE FINAL — **NO-GO 4/10 (golden ≥ enriched)** confirme **Option C abandon partiel**.
> **Date** : 2026-05-02
> **Branche** : `feat/sprint12-axe-2-golden-pipeline` (étape 7 même PR #117)
> **Spec ordre** : 2026-05-02-1133-claudette-orientia-sprint12-axe-2-golden-pipeline-v3-test-1
> **V1** : `docs/sprint12-axe-2-golden-pipeline-2026-05-01.md` (NO-GO 6/10, filter strict)
> **V2** : `docs/sprint12-axe-2-golden-pipeline-v2-filter-soft-2026-05-01.md` (NO-GO 5/10, filter soft boost ×1.3)

---

## TL;DR

- Bench biais Pattern #3 **confirmé empiriquement** : `OurRagSystem.answer()` ne passe pas `criteria` → enriched bypass metadata_filter en pratique. Asymétrie réelle v1+v2.
- **Apple-to-apple Test 1** (`enable_metadata_filter=False` côté golden) : NO-GO **4/10** (golden ≥ enriched). Pire que v1 (6/10) et v2 (5/10).
- **Découverte inattendue** : `mistral_v3_2_no_rag` baseline cumul **128** > enriched 120 > golden 118. Le NO-RAG bat les 2 systems RAG sur ce sample (cohérent Run F+G).
- `diversite_geo` golden **coincé à 5/30** même sans filter → biais retrieval/corpus, pas filter.
- **1 bug structurel patché** en cours de Test 1 (`generator.py:_fiche_header` cast str manquant, 3/10 crashes initiaux).
- **Reco Claudette confirmée empiriquement : Option C abandon partiel.** Le golden mode tel que conçu n'apporte pas de gain mesurable, indépendamment du filter.

---

## Contexte — Discovery Pattern #3 Matteo+Jarvis

Le bench v1 + v2 n'était **pas apple-to-apple**.

`OurRagSystem.answer()` ligne 53 (`src/eval/systems.py`) :
```python
def answer(self, qid: str, question: str) -> str:
    text, _sources = self.pipeline.answer(question)  # PAS de criteria !
    return text
```

`OrientIAPipeline.answer()` accepte `criteria: FilterCriteria | None = None` (default None). Quand criteria=None ou is_empty(), `_retrieve_and_filter` bypass `apply_metadata_filter`.

**En pratique** :
- `our_rag_enriched` : criteria toujours None → **bypass metadata_filter** → diversite_geo non pénalisée
- `pipeline_agent_golden` : ProfileClarifier infère Profile → ProfileState → criteria non-vide → metadata_filter strict (v1) ou boost (v2) APPLIQUÉ → asymétrie

**Résultat empirique** : la perte -11 diversite_geo v1 et -8 v2 était **partiellement** un biais bench, **mais pas seulement** — Test 1 montre que diversite_geo golden reste coincé à 5/30 même sans filter (cf §Aspects).

---

## Test 1 — Configuration apple-to-apple

**Modif** : `scripts/bench_sprint12_axe2_golden_validation.py:build_golden_system` :
```python
agent_pipeline = AgentPipeline(
    ...,
    enable_metadata_filter=False,  # apple-to-apple avec our_rag_enriched
    ...
)
```

**Triangulaire** : 3ᵉ système ajouté `mistral_v3_2_no_rag` (`MistralWithCustomPromptSystem` + `SYSTEM_PROMPT` v4 default + sans RAG context).

---

## Bugs rencontrés Test 1 — Log détaillé

### Bug #1 STRUCTUREL — `_fiche_header` cast str manquant

**Symptôme** :
```
AttributeError: 'int' object has no attribute 'strip'
File "src/rag/generator.py", line 28, in _fiche_header
    niveau = (f.get("niveau") or "").strip()
```
Crash pre-generate (elapsed_generate=0.0s), `result.error` capturé, `answer_text=""` → réponse vide jugée 0/30.

**Trigger** : 3 questions / 10 dans le 1er run Test 1 (A6, A9, B10) — toutes ont des sub-queries qui retrievent au moins 1 fiche du corpus combined dont `niveau` est int.

**Root cause** : corpus combined hétérogène. Items `formations_unified` ont `niveau` parfois en int (1-8 RNCP), `dares` n'a pas de niveau, `rncp_blocs` a niveau str. Le code `_fiche_header` (load-bearing mais pas listé "protected explicit" CLAUDE.md) attend str → `(int).strip()` crash.

**Pourquoi pas vu plus tôt** :
- Tests étape 3 mocks (`fake_fiches` tout-str) ne reproduisent pas l'hétérogénéité corpus
- v1 strict : items "buggy" droppés par metadata_filter (niveau int ≠ niveau_min/max int) avant generate → masqué
- v2 soft : 1/10 crash A7 attribué à transient API
- v3 no filter : 3/10 crashes A6, A9, B10 → pattern récurrent → vrai bug révélé

**Fix appliqué** : `src/rag/generator.py:_fiche_header` lignes 28-33 cast `str(f.get(...) or "").strip()` (6 lignes, additif défensif). Modif noop sur str, convert int→"42" sur int.

**Validation** : diag isolé A6 post-fix → 2318 chars cohérent. Re-run final 0 crashes (10/10 réponses ≥ 1700 chars).

**Tests garde-fou** : à ajouter post-livraison (test ciblé `_fiche_header` accepte fiches niveau int).

### Bugs API transient antérieurs (rappel)

- v1 étape 4 : B10 crash 1 fois → re-run isolé OK 1632 chars. Transient Mistral.
- v2 étape 6 : A7 crash 1 fois → re-run isolé OK 2520 chars. Transient.

Ces 2 sont **bien transient** (re-run réussit), pas la même nature que bug #1 (récurrent jusqu'au fix code).

---

## Méthodologie bench Test 1

- **Reproductibilité** : 10 mêmes questions hold-out v1+v2 (split=test)
- **Systems** :
  1. `pipeline_agent_golden` v3 (config v2 - metadata_filter)
  2. `our_rag_enriched` (legacy, identique v1+v2)
  3. `mistral_v3_2_no_rag` (NEW baseline triangulaire)
- **Judge** : Claude Sonnet 4.5 multi-aspect rubric (single-judge MVP, identique v1+v2)
- **Backups archive** : `*_v1_filter_strict.json` (v1) + `*_v2_filter_soft.json` (v2)

---

## Résultats Test 1 — final post-fix bug #1

### Globaux

| Métrique | v1 strict | v2 soft | v3 Test 1 | Cible |
|---|---|---|---|---|
| Wins golden | 5/10 | 4/10 | **3/10** | ≥7 |
| Wins enriched | 4/10 | 5/10 | 6/10 | — |
| Wins no_rag | — | — | — | informatif |
| Ties | 1/10 | 1/10 | 1/10 | — |
| **Golden ≥ enriched** | **6/10** | **5/10** | **4/10** | ≥7 GO |
| Cumul golden | 125 | 123 | **118** | ≥130 |
| Cumul enriched | 124 | 133 | **120** | — |
| **Cumul mistral_v3_2_no_rag** | — | — | **128** ⭐ | — |
| **diversite_geo G** | **5** | **8** | **5** | ≥12 |

### Aspects cumul Test 1 (10q × 3 systems)

| Aspect | Golden | Enriched | NO-RAG |
|---|---|---|---|
| neutralite | 26 | 24 | 23 |
| realisme | 20 | 24 | 23 |
| sourcage | 24 | 25 | 11 |
| **diversite_geo** | **5** ⚠️ | 14 | **22** 🏆 |
| agentivite | 27 | 22 | 28 |
| decouverte | 16 | 11 | 21 |
| **TOTAL** | **118** | **120** | **128** 🏆 |

**Lectures clé** :
- `diversite_geo` golden = 5/30 même sans filter. Le biais n'est PAS uniquement le filter — c'est aussi l'aggregation top-K=8 du retrieval golden + sub-queries qui convergent IDF (corpus dominant).
- `mistral_v3_2_no_rag` (baseline NO-RAG) **gagne** sur `diversite_geo` (22) et `decouverte` (21) — sans contraintes corpus, le LLM brasse plus large.
- `sourcage` RAG > NO-RAG (24 vs 11) — RAG aide vraiment ici. Mais c'est le seul aspect où RAG domine clairement.
- Cumul **golden 118 < enriched 120 < NO-RAG 128**. Le NO-RAG bat les 2 RAG. Cohérent Run F+G.

### Variance bruit cross-run

Variance enriched v1→v3 (système identique, bruit pur judge) :
- mean -0.40, **stdev 2.07** par question, range [-4, +3]

Variance golden v1→v3 (vraie change : filter strict → no filter) :
- mean -0.70, **stdev 2.31** par question, range [-4, +4]

Cumul sur 10q : stdev cumul ≈ √10 × 2.07 ≈ 6.5. L'écart cumul golden -7 (125→118) est à 1×stdev → dans le bruit.

**Conclusion méthodologique** : single-judge n=10 ne distingue pas signal réel d'un bruit ici non plus. Mais le **wins count** (5→4→3) montre une tendance régulière à la baisse côté golden — peut être bruit ou signal faible.

### Per-question (10q)

| QID | v1 G | v2 G | v3 G | v1 E | v2 E | v3 E | v3 NR | Win v3 |
|---|---|---|---|---|---|---|---|---|
| A6 | 15 | 17 | 14 | 7 | 11 | 7 | 12 | 🟢 G |
| A9 | 13 | 13 | 12 | 9 | 5 | 12 | 7 | 🟡 tie |
| A11 | 16 | 9 | 13 | 12 | 17 | 11 | 12 | 🟢 G |
| A12 | 13 | 12 | 12 | 12 | 11 | 8 | 16 | 🟢 G |
| A7 | 13 | 12 | 9 | 12 | 12 | 13 | 9 | 🔴 E |
| A10 | 13 | 16 | 12 | 14 | 14 | 14 | 12 | 🔴 E |
| A8 | 8 | 12 | 12 | 16 | 16 | 14 | 14 | 🔴 E |
| B10 | 13 | 13 | 11 | 16 | 17 | 14 | 16 | 🔴 E |
| B11 | 11 | 11 | 11 | 11 | 14 | 13 | 14 | 🔴 E |
| B12 | 10 | 9 | 12 | 15 | 16 | 14 | 16 | 🔴 E |

3 wins golden : A6, A11, A12 (questions où le profil ≈ query, golden tire profit de l'agentic+sourcage).
6 wins enriched : A7, A10, A8, B10, B11, B12 (questions plus pratiques, enriched + rerank+MMR plus efficace).

---

## Sample 3 questions verbatim Pattern #4

### Cas 1 — Win golden : A6 "développeur web full-stack" (G=14 E=7 NR=12)

Cohérence v1+v2+v3 : golden gagne consistantly (15, 17, 14 vs 7, 11, 7). Pattern : query bien-définie tech, profil-aligned (lyceen_terminale → BTS/BUT info, etc.) → golden tire profit de la fusion sub-queries cross-corpus + agentic prompt v4.

### Cas 2 — Loss enriched : A8 "écoles design en France" (G=12 E=14 NR=14)

V1 catastrophique G=8 E=16 (-8 attribué à filter strict). V3 apple-to-apple G=12 E=14 (-2). Le fix bench a réduit l'écart, **mais enriched + NO-RAG restent meilleurs**. Lecture : sur les questions nationales, golden retrieval converge encore IDF (cf diversite_geo 5) — biais corpus + retrieval.

### Cas 3 — Loss enriched : B12 "Parcoursup moyen" (G=12 E=14 NR=16)

V1 G=10 E=15, V2 G=9 E=16, V3 G=12 E=14. Pattern stable : enriched + NO-RAG répondent mieux à des questions pratiques de stratégie Parcoursup. Le golden, malgré agentic+fact-check, n'a pas l'avantage sur ce type de query.

---

## Décision finale Test 1 — Option C confirmée

### Verdict empirique

- NO-GO 4/10 strict (golden ≥ enriched). **Pire que v1 et v2**.
- Apple-to-apple a réduit l'écart `diversite_geo` (5→5 vs filter strict, mais de 14→14 côté enriched) — pas de gain net pour golden.
- `mistral_v3_2_no_rag` baseline (cumul 128) > golden (118) confirme que le pipeline complet golden n'apporte pas de gain mesurable.

### Recommandation Option C abandon partiel

PR #117 close sans merge. **Préserver les acquis réutilisables** :
- ✅ Backstop B soft (`src/backstop/`) : déjà sur main, exploitable directement par OrientIAPipeline (modif additive si on veut)
- ✅ FetchStat in-loop : code dans `pipeline_agent.py` peut être backporté dans `OrientIAPipeline` (effort 0.5j)
- ✅ A1+A2 contracts/bridge (`src/axe2/`) : utilisables Phase 2 agentic Sonnet 4.5 future
- ✅ Corpus combined (`formations_golden_pipeline.json`) : conservable si on veut rebench
- ✅ Bug fix `_fiche_header` cast str : reste sur main (utile défensivement même hors golden mode)

**Pourquoi Option C > Option 2 ProfileState plus permissif** :
1. Test 1 prouve que le filter n'est pas la cause unique du gap. Sans filter, golden est encore moins bon.
2. Le retrieval golden (sub_queries × top-K=6) est moins efficace qu'`OrientIAPipeline` legacy (k=30 + rerank + MMR + intent classifier).
3. Multi-judge + n>30 demanderait +$10-15 pour méthodologie robuste avant tout rebench Option 2 — ROI faible.

---

## Apprentissages capitalisés

- **#15** Single-judge bench n=10 a stdev ~2.07 par question → écarts cumul <13 indistinguables d'un bruit. Méthodologie robuste = multi-judge + κ inter-judge OU n≥30 OU delta ≥3×stdev.
- **#16** Boost ×1.3 sur metadata filter améliore marginalement diversite_geo mais ne compense pas over-filter conceptuel.
- **#17 (NEW)** Bench apparemment apple-to-apple peut être biaisé par flags actifs implicites différents entre systems. Cross-vérifier que les 2 systems appliquent réellement les mêmes transformations en pratique (path bypass éventuel via `criteria=None` ou `is_empty()`). Discovery Matteo+Jarvis Pattern #3 confirmée.
- **#18 (NEW)** Tests mockés Mistral ≠ tests intégration LLM sur data flow réel hétérogène. Mocks `fake_fiches` étape 3 tout-str → bug `(int).strip()` invisible jusqu'au bench. Bench validation est le vrai test d'intégration des paths data hétérogènes (corpus combined). À capitaliser : ajouter mini-suite tests intégration sur corpus multi-source réel (sample 100 fiches mixtes).
- **#19 (NEW)** Le filter metadata strict/soft n'était pas la cause unique du gap diversite_geo. Le retrieval golden (sub_queries × top-K=6 par sub-q × agg=8) converge IDF naturellement à cause de la distribution corpus + sub_queries de QueryReformuler qui convergent. Le rerank+MMR+intent d'`OrientIAPipeline` legacy diversifie mieux. Pour fix la diversité, il faudrait soit (a) ajouter MMR au pipeline_agent, (b) re-pondérer le corpus par région/domaine au retrieval, (c) re-équilibrer la distribution corpus IDF/régions. Hors scope Sprint 12 axe 2.

---

## Coûts cumul Sprint 12 axe 2 finaux

- Étape 2 embedding : ~$1.2
- Étape 4 bench v1 : ~$0.65
- Étape 6 bench v2 : ~$0.70
- Test 1 bench v3 (incl. re-runs bug #1 et fix) : ~$1.0
- **Total : ~$3.55** (vs estimé $8-12 plan original)

---

## Artefacts livrables (additions Test 1)

- `scripts/bench_sprint12_axe2_golden_validation.py` : `enable_metadata_filter=False` côté golden + `mistral_v3_2_no_rag` triangulaire ajouté
- `src/rag/generator.py:_fiche_header` : fix bug #1 cast str() défensif (6 lignes additives)
- `results/bench_sprint12_axe2_golden_validation/*_v1_filter_strict.json` (archive v1)
- `results/bench_sprint12_axe2_golden_validation/*_v2_filter_soft.json` (archive v2)
- `results/bench_sprint12_axe2_golden_validation/{responses_blind,judge_scores,verdict_raw}.json` (v3 Test 1 final, 3 systems)
- `docs/sprint12-axe-2-golden-pipeline-v3-test-1-2026-05-02.md` (ce verdict)

---

*Plan de fond : `docs/GOLDEN_PIPELINE_PLAN.md`. V1 : `docs/sprint12-axe-2-golden-pipeline-2026-05-01.md`. V2 : `docs/sprint12-axe-2-golden-pipeline-v2-filter-soft-2026-05-01.md`.*
