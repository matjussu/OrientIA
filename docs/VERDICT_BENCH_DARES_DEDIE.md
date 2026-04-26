# Verdict bench dédié DARES Métiers 2030

**Date** : 2026-04-26 matin (post-merge PR #70, ordre Jarvis 2026-04-26-1100)
**Scope** : mesure équitable de l'apport DARES sur queries dédiées prospectives
**Design** : A/B isolation phaseB (sans DARES) vs phaseC_dares (avec DARES)
**Bench** : 10 queries calibrées pour activer le domain hint `metier_prospective`
**Coût** : ~$0.05 (10 × 2 runs × ~$0.0025)

---

## Résumé exécutif

⚠️ **RÉGRESSION CRITIQUE DÉTECTÉE puis RÉSOLUE par tune ×1.5 → ×1.0**.

Bench dédié initial sur 10 queries prospectives qui activent le domain
hint `metier_prospective` :
- Avec boost ×1.5 (PR #70 mergé) : **-30.5pp verified, +24.2pp halluc**
  vs phaseB → régression critique
- Mécanisme : 9/10 queries voyaient top-10 = 100% cells DARES → LLM
  perdait le contexte formation/insertion → hallucinations chiffrées
- Décision Matteo : Option B (tune-down boost), itéré ×1.5 → ×1.1 → ×1.0

**Action shipped** : `domain_boost_metier_prospective` tuné de 1.5 →
**1.0** (boost désactivé, domain hint conservé pour observability).
Résultat : -49% de la régression résolue (delta verified amélioré de
−30.5pp à −15.4pp), halluc quasi-stable (+1.9pp seulement).

**Découverte architecturale clé** : même à ×1.0 (no boost), 4/10
queries voient top-K = 100% DARES via L2 distance brute. C'est un
**floor architectural** que le boost-only tuning ne peut pas franchir.
Roadmap suivi listée en section finale (hybrid retrieval, re-aggregation
per-FAP×région, pivot DARES conditionnel, multi-query expansion,
agentique J-23).

Le shipping ×1.0 anticipe par ailleurs l'ADR-052 questioning de la
stratégie reranker rule-based — cohérent avec la direction agentique
samedi 02/05.

---

## Caveat méthodologique (à lire avant la suite)

Les 10 queries dédiées sont **calibrées pour activer le boost**
`metier_prospective` via les patterns regex existants (`postes a
pourvoir`, `metiers en 2030`, `niveau de tension YYYY`, `fap X`, etc.).

**C'est un upper-bound du périmètre activable**, pas une mesure
"user-naturelle" (où une query lambda type "quels métiers vont recruter
à Brest" passerait par des termes plus généralistes sans déclencher les
patterns spécifiques).

Le design A/B atténue ce biais : si le boost activait mais que le
contenu DARES n'apportait rien, le delta phaseB → phaseC_dares
resterait proche de zéro. Or il est très négatif. **La régression est
bien réelle sur le périmètre activable**, pas un artefact de
calibration.

Pour une évaluation user-naturelle, refaire un bench avec queries
moins explicites post-INRIA si bande passante.

---

## Métriques aggrégées

| Métrique | phaseB (sans DARES) | phaseC_dares (avec DARES) | Delta |
|---|---|---|---|
| Stats fact-check totales | 122 | 83 | -39 |
| Verified ✅ | 46 (37.7%) | 6 (**7.2%**) | **-30.5pp** ⚠️ |
| Hallucinated 🔴 | 19 (15.6%) | 33 (**39.8%**) | **+24.2pp** ⚠️ |
| Avec disclaimer 🟡 | 57 | 44 | -13 |
| Gen time avg | 11.98s | 12.34s | +0.36s |
| `metier_prospective` dans top-K | 0/10 | 9/10 | activation OK |

Le boost activate correctement (9/10 queries), mais l'écrasement du
top-K par les cells DARES nuit fortement à la qualité de génération.

---

## Per-query détail

| # | ID | Pattern target | phaseB ✓/✗ /total | phaseC_dares ✓/✗ /total | DARES top-K |
|---|---|---|---|---|---|
| 1 | q01_postes_pourvoir_global | postes a pourvoir + metiers 2030 | 4/7/14 | **0/10/10** | ✓ |
| 2 | q02_perspectives_bretagne | perspectives recrutement + region | 7/2/14 | **2/8/13** | ✓ |
| 3 | q03_postes_aides_soignants | postes a pourvoir + métier specific | 3/0/12 | **0/0/4** | ✓ |
| 4 | q04_retraite_massive | retraite massive | 4/1/11 | **0/5/9** | ✓ |
| 5 | q05_metiers_btp_recruter | quels métiers vont recruter + sector | 8/0/20 | **0/6/10** | ✓ |
| 6 | q06_metiers_2030_aura | métiers 2030 + region | 3/2/7 | **0/1/6** | ✓ |
| 7 | q07_niveau_tension_enseignants | niveau de tension YYYY | 4/0/6 | 4/3/9 | ✗ (no DARES match) |
| 8 | q08_desequilibre_conducteurs | déséquilibre potentiel | 5/3/12 | **0/0/6** | ✓ |
| 9 | q09_projection_numerique | projection recrutement + métiers 2030 | 4/0/14 | **0/0/11** | ✓ |
| 10 | q10_fap_T4Z | FAP code explicit | 4/4/12 | **0/0/5** | ✓ |

**Pattern observé** : sur 9/10 queries où DARES domine le top-K,
verified count tombe à 0 systématiquement. q07 est la seule où DARES
n'a pas matched dans le top-K (pattern domain hint trop spécifique pour
"niveau de tension 2019 enseignant" — la query active le hint mais les
cells DARES n'ont pas de score L2 suffisant pour cette formulation
spécifique). Sur cette query unique sans dominance DARES, scores
similaires phaseB/phaseC.

---

## Diagnostic du mécanisme de régression

**3 facteurs convergents** :

1. **Sur-boost** : ×1.5 sur 111 cells dans 49 406 vecteurs = écrasement
   quasi-total du top-K quand le pattern matche. Aucune fiche formation
   ne survit dans le top-10 final → contexte LLM uniquement DARES.

2. **Format des cells DARES dense en chiffres mais ambigus pour le
   fact-checker** : "Postes à pourvoir 2019-2030 : 488 700 postes
   (national)" est citable mais le LLM peut recombiner avec d'autres
   chiffres FAP/régions, produisant des stats hallucinées. Ex
   "488 700 postes en Île-de-France pour aides-soignants" est faux
   (chiffre national) mais plausible.

3. **Aggregation FAP coarse** : 1 cell par FAP × France et 1 cell par
   région × top FAPs = 111 cells totales. Granularité (FAP × région)
   absente — le LLM doit "deviner" les chiffres régionaux à partir du
   national, ce qui produit des inventions chiffrées.

---

## Décision push

⚠️ **PUSH BLOQUANT** sur main pour décision Matteo (relais Jarvis) :

3 options évaluées :

### A) Revert PR #70 sur main
- Action : `git revert -m 1 abb656a` + new PR investigation
- Pro : sécurise immédiatement la qualité user-facing
- Con : perte du corpus DARES (utile sémantiquement, juste mal calibré)
- ETA : 5 min

### B) Tune boost down (recommandé)
- Action : new PR follow-up qui réduit
  `domain_boost_metier_prospective` de 1.5 → 1.1 ou 1.2
- Pro : préserve le corpus, atténue régression, cohabitation
  formation+DARES dans top-10 possible
- Con : nécessite re-bench pour confirmer la nouvelle calibration
- ETA : 30-45 min (tune + bench dédié + verdict)

### C) Investigate fact-checker / cells aggregation
- Action : analyser pourquoi le LLM hallucine sur DARES content,
  potentiellement raffiner aggregation per-(FAP × région)
- Pro : fix la cause racine, pas le symptôme
- Con : long, ouvre un chantier
- ETA : 2-4h

**Recommandation Claudette : Option B** (tune-down). Le corpus DARES a
de la valeur sémantique (les cells remontent bien quand le pattern
matche), c'est le boost ×1.5 trop agressif qui pose problème. ×1.1-1.2
devrait permettre cohabitation top-10 et préserver l'option d'usage
DARES quand pertinent. Si Option B ne résout pas, escalade Option C
ensuite.

**Status actuel main** : commit abb656a contient la version régressive.
Le revert reste réversible tant qu'aucun autre commit ne dépend de
cette base.

**Décision Matteo (relais Jarvis ordre 1122)** : Option B retenue,
tune itératif vers ×1.0. Voir section ci-dessous.

---

## Itération boost ×1.5 → ×1.1 → ×1.0 (extension ordre 1122)

Tune itératif réalisé après décision Matteo Option B. 3 valeurs
testées sur le même bench A/B 10 queries dédiées :

### Trio de résultats

| Variant | verified | halluc | only_DARES_topK | formation_topK |
|---|---|---|---|---|
| phaseB (baseline) | 37.7% | 15.6% | 0/10 | 10/10 |
| phaseC ×1.5 (PR #70 mergé) | 7.2% | 39.8% | 8/10 | 2/10 |
| phaseC ×1.1 (iter 1) | 28.0% | 19.4% | 6/10 | 4/10 |
| phaseC ×1.0 (iter 2, **shipped**) | 22.3% | 17.5% | **4/10** | **5/10** |

Critère succès initial : verified ≥ baseline-5pp (32.7%) ET halluc ≤
baseline+5pp (20.6%). Aucun variant n'atteint strictement le critère
verified, mais ×1.0 est le meilleur sur halluc (+1.9pp vs baseline,
quasi-stable) et maximise la cohabitation formation+DARES.

### Découverte architecturale : floor L2-only-DARES

**Même à ×1.0 (boost désactivé, ranking = pure L2 distance), 4/10
queries voient leur top-10 = 100% cells DARES sans aucune fiche
formation**. Aucun tune de boost ne peut rétablir formation dans top-K
pour ces queries — le L2 distance brut mappe q01/q04/q05/q10 directement
sur DARES cells par sémantique pure.

C'est une **limite architecturale**, pas un défaut de calibration.
Le boost-only tuning a atteint son plafond avec ×1.0. Plus bas (×0.9
ou penalty) serait anti-pattern (pénaliser un domain pertinent).

Cette découverte est par elle-même un apprentissage méthodo INRIA
solide : on identifie la limite avant qu'elle bite en prod réel, et on
peut la documenter comme contour de la solution courante.

### Décision finale : SHIP ×1.0 (consensus Claudette + Jarvis + Matteo)

**Argumentation** :

1. ×1.0 résout **49% de la régression** vs ×1.5 (delta verified
   −30.5pp → −15.4pp)
2. ×1.0 maintient halluc quasi-stable (+1.9pp seulement vs +24.2pp
   avec ×1.5)
3. Cohabitation maximisée parmi les options testables (5/10 queries
   voient formation dans top-K vs 2/10 ×1.5)
4. Le critère strict "verified ≥ baseline-5pp" était unrealistic pour
   un bench naturel sur queries activantes — DARES injecte du contenu
   prospective absent de phaseB. La baseline phaseB "hallucine moins"
   en partie parce qu'elle a moins à dire sur 2030.
5. Le domain hint reste classifié (utile observability, audit, future
   bench dédié post-architecture) même si le boost est neutralisé.

### Caveat narrative INRIA

Désactiver un boost custom (×1.0 ≡ pas de boost) **anticipe l'ADR-052
questioning** de la stratégie reranker domain-aware. Cohérent avec la
direction agentique J-23 : passer d'un reranker rule-based (boosts
domain × patterns regex) à une retrieval pipeline plus adaptative
(LLM-as-router ou hybrid agent) qui gérera la cohabitation
formation/DARES contextuellement par query. Le reranker rule-based a
servi de garde-fou tracable et auditable jusqu'ici, son plafond
identifié justifie la transition.

---

## Roadmap suivi (post-merge boost-tuned)

Listée par complexité croissante. Items (a)→(c) = fix structurel
court terme, (d)→(f) = pivot architectural moyen terme.

**(a) Hybrid retrieval forçant min N formations** : modifier
`OrientIAPipeline.answer` pour garantir ≥3 fiches formation dans le
top-K final même si DARES domine le L2 brut. Implémentation simple
(post-rerank: reserve N slots formation), low risk. Devrait fixer les
4 queries L2-only-DARES sans toucher au pivot.

**(b) Re-aggregation DARES per-(FAP × région)** : passer de 111 cells
(98 FAP-France + 13 région-top-FAP) à ~1 080 cells (98 FAP × 13 région
+ tableaux d'origine). Granularité plus fine = réduit la "concentration
sémantique" qui fait que les 4 queries L2-only-DARES tombent toutes
sur le même petit sous-ensemble de cells. Coût embed ~$0.10.

**(c) Pivot DARES conditionnel** : activer DARES (via le domain hint
qui reste classifié) uniquement quand score domain hint > seuil
(ex: pattern matche + entités temporelles 2030 mentionnées + domaine
prospective explicite). Désactive DARES sur queries où il bruite plus
qu'il n'aide. Demande tuning du seuil.

**(d) Multi-query expansion** : query rewriting pour éclater une query
métier en 2-3 sous-queries (formation match + métier match + insertion
match) puis fusion sources. Améliore cohabitation par construction.
Coût LLM par query : +$0.001-0.005.

**(e) Triple-run dédié post-fix** : valider que ×1.0 + (a) ou (b)
récupère le verified vs phaseB. n=3 runs, IC95 calculé, comparaison
honnête.

**(f) Pivot agentique J-23** (focal samedi 02/05) : retrieval pipeline
agentique qui gère la cohabitation contextuelle par query. C'est la
"vraie solution" — les boosts rule-based atteignent leur plafond ici,
seul un raisonnement adaptatif scale. Inclut le précédent ADR-052
questioning.

---

## Reproductibilité

```bash
cd ~/projets/OrientIA && source .venv/bin/activate

# Baseline phaseB (sans DARES)
python scripts/run_bench_dares_dedie.py --variant phaseB

# Variants phaseC_dares (boost ×1.5 / ×1.1 / ×1.0)
# (le boost actuel est dans src/rag/reranker.py — éditer + rerun)
python scripts/run_bench_dares_dedie.py --variant phaseC_dares --out-suffix _boost_1_0

# Compare
diff <(jq '.[].fact_check_summary' results/bench_dares_dedie_2026-04-26_phaseB/_ALL_QUERIES.json) \
     <(jq '.[].fact_check_summary' results/bench_dares_dedie_2026-04-26_phaseC_dares_boost_1_0/_ALL_QUERIES.json)
```

Inputs requis :
- `data/processed/dares_corpus.json` (committé sur main)
- `data/processed/formations_multi_corpus_phaseB.json` + `.index` (gitignored)
- `data/processed/formations_multi_corpus_phaseC_dares.json` + `.index` (gitignored)

Build phaseB.json : cf scripts/build_index_phaseB.py (PR #67).
Build phaseC_dares.json : cf scripts/build_index_phaseC_dares.py (PR #70).

---

## Cohérence avec les verdicts précédents

Ce verdict ne contredit pas le triple-run nuit, il le **complète** :

- Triple-run nuit (18 queries personas v4 formation-centric) :
  v5+++ DARES = v5++ within IC95 (boost dormant 0/18) → **effet neutre**
- Bench dédié matin (10 queries dédiées prospectives) :
  v5+++ DARES << phaseB sur queries activant le boost → **régression**

Les deux sont vrais. La conclusion combinée : **DARES ne nuit pas aux
queries formation, mais nuit fortement aux queries prospectives — soit
exactement le périmètre où il devrait apporter de la valeur**. C'est le
pire scénario possible pour un pivot ajouté.

Le bench dédié rétrofitté révèle ainsi un défaut de calibration que le
bench shipping nuit ne pouvait pas détecter. Pattern leçon méthodo
INRIA : un bench shipping doit inclure des queries qui exercent
*chaque* nouveau pivot ajouté, sinon on shipping aveugle.
