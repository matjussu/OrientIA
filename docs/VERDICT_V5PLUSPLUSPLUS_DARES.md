# Verdict bench v5+++ DARES Métiers 2030

**Date** : 2026-04-26 (nuit, ordre Jarvis 2026-04-26-0029)
**Scope PR** : #70 `feat/dares-metiers-2030`
**Pipeline** : append-rebuild Phase C → 49 406 vecteurs (49 295 phaseB + 111 DARES)
**Bench** : 18 queries × 6 personas, fact-checker StatFactChecker Mistral Small
**Coût total** : ~$0.06 (embed $0.01 Phase C + bench $0.05)

---

## Résumé exécutif

**v5+++ ≥ v5++ sur la suite shipping (18 queries personas v4)** — pas de
régression, gain marginal +3.2pp verified, hallucination stable. Push
autorisé selon discipline scientifique (cf agent_journal R3 revert).

**Caveat important** : les 18 queries baseline sont formation-centric et
ne déclenchent **aucune** activation du domain hint `metier_prospective`.
Les 111 cells DARES sont indexées mais leur boost reranker (×1.5) n'est
pas exercé sur cette suite. Le gain mesuré relève vraisemblablement du
drift L2 marginal (les 111 cells réordonnent légèrement les top-K), pas
du boost intentionnel.

Une mesure équitable de l'apport DARES nécessiterait des queries dédiées
("quels métiers vont recruter en 2030", "FAP X postes à pourvoir Bretagne",
etc.). À planifier en bench complémentaire post-merge si Matteo souhaite
chiffrer la valeur ajoutée prospective.

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

## Suivi recommandé (post-merge)

1. **Bench DARES dédié** : 6-12 queries ciblées prospective ("FAP G postes
   à pourvoir Île-de-France 2030", "quels métiers manuels recrutent",
   "départs en fin de carrière infirmier", etc.) pour mesurer le gain
   attendu du boost ×1.5 sur le domain `metier_prospective`. Estimation
   ~$0.05 + 30 min.
2. **Triple-run v5+++ Phase C** (bonus task #3 ordre 0029) pour IC95 sur
   la suite shipping, si bande passante avant réveil Matteo. Confirme la
   stabilité du gain +3.2pp ou révèle qu'il est dans le bruit.
3. **PR #71 France Compétences blocs RNCP** — second corpus tonight, à
   livrer en parallèle (cf order 0029).

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
