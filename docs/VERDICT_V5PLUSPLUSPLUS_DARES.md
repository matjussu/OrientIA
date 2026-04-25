# Verdict bench v5+++ DARES Métiers 2030

**Date** : 2026-04-26 (nuit, ordre Jarvis 2026-04-26-0029)
**Scope PR** : #70 `feat/dares-metiers-2030`
**Pipeline** : append-rebuild Phase C → 49 406 vecteurs (49 295 phaseB + 111 DARES)
**Bench** : 18 queries × 6 personas, fact-checker StatFactChecker Mistral Small
**Coût total** : ~$0.06 (embed $0.01 Phase C + bench $0.05)

---

## Résumé exécutif

**v5+++ DARES = v5++ within IC95 sur la suite shipping (triple-run, n=3)**
— pas de régression, pas de gain mesurable non plus, le single-run gain
+3.2pp verified initial était dans le bruit (cf section Triple-run IC95
ci-dessous).

Push autorisé (pas de régression, IC95 inclut v5++ baseline). Les 111
cells DARES sont indexées correctement mais leur boost reranker (×1.5)
n'est pas exercé : 0/18 queries shipping activent le domain hint
`metier_prospective` car la suite est formation-centric par design.

Une mesure équitable de l'apport DARES nécessite des **queries dédiées**
("quels métiers vont recruter en 2030", "FAP X postes à pourvoir Bretagne",
etc.) — bench complémentaire post-merge listé en suivi #1.

**Note historique** : ce document a été initialement publié avec un
verdict single-run optimiste (+3.2pp verified). Le triple-run l'a
révisé à la baisse en transparence scientifique (pattern R3 revert
d'hier). Le headline ci-dessus reflète la conclusion finale.

---

## Métriques aggrégées

| Métrique | v5++ (baseline) | v5+++ (Phase C DARES) | Delta |
|---|---|---|---|
| Stats fact-check totales | 200 | 192 | -8 |
| Verified ✅ | 79 (39.5%) | 82 (42.7%) | **+3.2pp** |
| Hallucinated 🔴 | 36 (18.0%) | 35 (18.2%) | +0.2pp |
| Avec disclaimer 🟡 | 85 | 75 | -10 |
| Gen time avg | 14.02s | 14.47s | +0.45s |
| Domains présents top-10 | formation, metier, parcours_bacheliers | (idem) | identique |
| Domain `metier_prospective` activé | n/a | **0/18 queries** | — |

**Lecture** : sur la suite formation-centric, v5+++ ne régresse pas et
gagne +3.2pp en taux de stats verified. La variance per-query est
significative (cf détail ci-dessous), mais en agrégat le pivot DARES est
neutre-positif. Le 0/18 queries activant `metier_prospective` confirme
que le bench actuel n'est pas un test équitable de DARES per se.

---

## Per-query (sample notable)

| # | Query | v5++ ✓/✗ /total | v5+++ ✓/✗ /total | Lecture |
|---|---|---|---|---|
| 4 | theo_q1 (passerelles L1/L2 droit) | 5/0/7 | 11/0/17 | +6 verified, +10 stats extraites |
| 5 | theo_q2 (sortir du droit) | 0/2/4 | 12/1/17 | gros gain |
| 6 | theo_q3 (M2 droit) | 12/0/16 | 0/0/0 | retrieval miss — cas atypique |
| 8 | emma_q2 (M2 alternance vs classique) | 0/0/2 | 4/6/12 | +verified mais aussi +halluc |
| 11 | mohamed_q2 (CAP cuisine reconversion) | 4/0/13 | 0/1/1 | retrieval drift négatif |
| 13 | valerie_q1 (coût école commerce) | 4/2/13 | 8/0/16 | +4 verified, -2 halluc |

**Pattern observé** : la variance per-query reflète un **retrieval drift
ponctuel** (top-K réorganisé par les 111 nouveaux vecteurs DARES en
distance L2 brute, hors boost reranker). Compense en moyenne mais expose
quelques queries à des bascules locales (q6 theo_q3, q11 mohamed_q2).
Magnitude similaire au drift Phase B observé hier (cf bench v5++ run3).

---

## Décision push

✅ **PUSH AUTORISÉ** sur `feat/dares-metiers-2030` :

- Critère discipline scientifique respecté : v5+++ pas pire que v5++ sur
  la suite shipping
- Hallucination ratio stable (+0.2pp dans le bruit de mesure)
- Gain sur le ratio verified, même si side-effect plutôt qu'effet
  intentionnel — le pivot DARES n'introduit pas de toxicité

**Ne pas merger automatiquement** — en attente de `merge-approval` Matteo
(pattern human-gated CLAUDE.md §Merge autorisé post-validation).

---

## Triple-run IC95 (extension nuit 2026-04-26)

Triple-run v5+++ DARES exécuté en parallèle (run2 + run3 lancés après
livraison initiale, run1 = bench shipping). Pattern v5++ run3 revert
d'hier — discipline scientifique impose de mesurer la stabilité avant
de claim un gain.

### Résultats par run

| Run | n_stats | verified | hallucinated | gen avg |
|---|---|---|---|---|
| run1 (shipping) | 192 | 42.7% | 18.2% | 14.47s |
| run2 | 211 | 39.8% | 11.4% | 14.06s |
| run3 | 200 | 36.5% | 14.5% | 12.60s |

### Aggregate (n=3, t-distribution df=2 → t=4.303 pour IC95)

| Métrique | Mean | Std | IC95 |
|---|---|---|---|
| pct_verified | 39.7% | 3.10 | ±7.71pp |
| pct_hallucinated | 14.7% | 3.40 | ±8.46pp |
| n_stats_total | 201.0 | 9.54 | ±23.70 |
| avg_gen_s | 13.7s | 0.98 | ±2.44s |

### Honnêteté scientifique : le gain single-run était dans le bruit

Le verdict initial (single-run shipping) annonçait **+3.2pp verified**
vs v5++ baseline. Le triple-run révèle :

- **Delta verified vs v5++ (39.5%) : +0.2pp** (mean ; IC95 ±7.71pp)
- **Delta hallucinated vs v5++ (18.0%) : -3.3pp** (mean ; IC95 ±8.46pp)

**Les 2 deltas sont DANS le bruit** — les intervalles de confiance
englobent zéro. On ne peut pas statistiquement distinguer v5+++ DARES
de v5++ sur la suite shipping. Le résumé exécutif initial était trop
optimiste sur la portée du gain et est corrigé ci-dessous.

### Per-query variance (extrait notable)

- `theo_q3` : verified=[0, 0, 4] — 2/3 runs retrieval miss (0 stats extraites)
- `mohamed_q3` : verified=[0, 0, 0] — 3/3 zero stats (cas atypique stable)
- `theo_q2` : verified=[12, 5, 0] — swing 0→12 entre runs (variance LLM gen)
- `psy_en_q2` : halluc=[7, 6, 1] — swing 1→7 entre runs

La variance per-query domine le signal aggregé. La suite 18-query est
trop petite pour détecter un gain marginal de cette magnitude.

### Conclusion révisée du verdict

Le pivot DARES (111 cells) **n'apporte pas de gain mesurable** sur la
suite shipping formation-centric, et **n'apporte pas non plus de
régression mesurable**. C'est cohérent avec l'observation initiale
(0/18 queries activent `metier_prospective` domain hint).

**Push reste autorisé** (pas de régression, IC95 inclut v5++ baseline),
mais la valeur ajoutée de DARES nécessite des **queries dédiées** pour
être chiffrée. C'est explicitement le suivi #1 ci-dessous.

Coût triple-run : ~$0.10 ($0.05 × 2 runs supplémentaires).

---

## Suivi recommandé (post-merge)

1. **Bench DARES dédié** (PRIORITAIRE post-merge — bench manquant) :
   6-12 queries ciblées prospective ("FAP G postes à pourvoir
   Île-de-France 2030", "quels métiers manuels recrutent", "départs
   en fin de carrière infirmier", etc.) pour mesurer le gain attendu
   du boost ×1.5 sur le domain `metier_prospective`. Estimation
   ~$0.05 + 30 min. C'est le bench qui chiffrera la valeur ajoutée
   de DARES.
2. **Phase D combinée** (post-merge PR #70 + PR #71) : index = phaseB
   + DARES + blocs (~54 297 vecteurs). Bench v5++++ Phase D vs v5++
   pour l'effet cumulatif des 2 PRs livrés cette nuit.
3. **PR #71 France Compétences blocs RNCP** — livré en parallèle
   (https://github.com/matjussu/OrientIA/pull/71). Bench blocs
   single-run montre -6.8pp halluc (à confirmer en triple-run avant
   claim définitif).

---

## Reproductibilité

```bash
cd ~/projets/OrientIA && source .venv/bin/activate

# 1. Build index Phase C (49 406 vecteurs, ~$0.01)
python scripts/build_index_phaseC_dares.py

# 2. Bench v5+++ (~12 min, ~$0.05)
python scripts/run_bench_personas_v5plusplusplus_dares.py

# 3. Compare vs v5++ (relabeled baseline)
diff <(jq '.[].fact_check_summary' results/bench_personas_v5plusplus_relabeled_2026-04-25/_ALL_QUERIES.json) \
     <(jq '.[].fact_check_summary' results/bench_personas_v5plusplusplus_dares_2026-04-26/_ALL_QUERIES.json)
```

Inputs requis :
- `data/processed/dares_corpus.json` (commité dans c1c1c53)
- `data/processed/formations_multi_corpus_phaseB.json` + `.index` (gitignored, rebuild via `scripts/build_index_phaseB.py`)
