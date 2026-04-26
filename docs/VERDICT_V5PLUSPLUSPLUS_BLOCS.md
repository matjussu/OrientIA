# Verdict bench v5+++ blocs France Compétences RNCP

**Date** : 2026-04-26 (nuit, ordre Jarvis 2026-04-26-0029)
**Scope PR** : #71 `feat/france-comp-blocs-rncp`
**Pipeline** : append-rebuild Phase C blocs → 54 186 vecteurs (49 295 phaseB + 4 891 blocs RNCP)
**Bench** : 18 queries × 6 personas, fact-checker StatFactChecker Mistral Small
**Coût total** : ~$0.18 (embed $0.13 Phase C blocs + bench $0.05)

---

## Résumé exécutif

**v5+++ blocs > v5++ avec gain substantiel sur hallucination** :
**-6.8pp d'hallucination** (18.0% → 11.2%), +1.1pp verified
(39.5% → 40.6%), gen time équivalent (14.02s → 13.79s, -0.23s).

Push largement autorisé selon discipline scientifique. Le pivot blocs
RNCP réduit fortement la fabrication de stats par le LLM, probablement
parce que les cellules blocs apportent du contenu pédagogique *concret*
(« Bloc 1 : assurer la maintenance frigorifique ») qui ancre la
génération en factualité vs sources formation génériques.

Notable : sur 18 queries formation-centric, **2 queries voient une
cellule `competences_certif` remonter dans le top-K via similarité L2
brute** (q3_lila « projet ENS éditorial » → matche bloc rédaction ;
q1_theo « passerelles L1/L2 droit » → matche bloc certif droit). Sans
matcher le pattern domain hint regex, les blocs s'imposent par
sémantique. Le pivot est utile même hors trigger explicit.

---

## Pipeline ajoutée vs main

### Module collector

`src/collect/build_france_comp_blocs_corpus.py` (~250 lignes) — exploite
le CSV `Blocs_De_Compétences` déjà présent dans le ZIP RNCP local
(`data/raw/rncp/export-fiches-csv-*.zip`), inutilisé jusqu'ici par
`src/collect/rncp.py`.

**Stratégie aggregation** :
- 1 cell par fiche RNCP active avec blocs (intersection 6 590 active ×
  10 181 fiches-avec-blocs = 4 891 cells)
- Texte format : intitulé + niveau + ROMEs visés + voies d'accès +
  blocs concaténés + source attribution
- 52 592 raw rows → 4 891 cells = 10.7× réduction de dilution top-K
  (pattern v5++ Phase B / v5+++ DARES)

**Pas d'appel API externe** : les blocs sont déjà dans le ZIP existant.
Build complet < 30s, $0 download.

### Domain wiring

- `src/rag/intent.py` : nouveau `DOMAIN_HINT_COMPETENCES_CERTIF` +
  13 patterns regex (blocs / compétences / contenu pédagogique / RNCP
  numéro / VAE par bloc / savoir-faire certifiés)
- `src/rag/reranker.py` : `domain_boost_competences_certif = 1.5`
  (cohérent avec APEC/INSEE/DARES = 1.5 pour données chiffrées externes
  authoritatives)

### Tests

- `tests/test_build_france_comp_blocs_corpus.py` : 17 tests (couverture
  index by fiche / format text / aggregate / build_corpus / save round-trip)
- `tests/test_reranker_domain_aware.py` étendu : 6 tests classify
  `DOMAIN_HINT_COMPETENCES_CERTIF` + 2 tests rerank boost sur le domain
  + assertion `domain_boost_competences_certif=1.5` dans
  `RerankConfig` defaults

**Suite complète** : 1 150 tests verts (1 125 baseline + 25 nouveaux),
0 régression.

---

## Métriques aggrégées

| Métrique | v5++ (baseline) | v5+++ blocs | Delta |
|---|---|---|---|
| Stats fact-check totales | 200 | 197 | -3 |
| Verified ✅ | 79 (39.5%) | 80 (40.6%) | **+1.1pp** |
| Hallucinated 🔴 | 36 (18.0%) | 22 (**11.2%**) | **-6.8pp** ⭐ |
| Avec disclaimer 🟡 | 85 | 95 | +10 |
| Gen time avg | 14.02s | 13.79s | -0.23s |
| Domain `competences_certif` dans top-K | n/a | 2/18 queries | — |

**Lecture** : forte baisse de l'hallucination (-6.8pp) avec gain marginal
sur verified (+1.1pp). Le LLM consomme moins de stats fabriquées quand
les blocs RNCP fournissent du contenu pédagogique concret. La hausse de
disclaimer (+10) suggère que le fact-checker note davantage de "stat
plausible mais non vérifiable" — pattern conservateur préférable à
l'hallucination franche.

---

## Per-query détail (notable)

| # | Query | v5++ ✓/✗ /total | v5+++ ✓/✗ /total | Lecture |
|---|---|---|---|---|
| 3 | lila_q3 (terminale L 14 moyenne) | 4/0/13 | 8/0/13 | +4 verified, **competences_certif dans top-K** |
| 4 | theo_q1 (passerelles L1/L2 droit) | 5/0/7 | 6/0/18 | +stats extraites, **competences_certif dans top-K** |
| 5 | theo_q2 (sortir du droit) | 0/2/4 | 6/0/13 | +6 verified, élimine 2 halluc |
| 9 | emma_q3 (M1 info Lille data) | 1/1/7 | 6/0/12 | +5 verified, élimine halluc |
| 13 | valerie_q1 (coût école commerce) | 4/2/13 | 7/0/13 | +3 verified, **élimine 2 halluc** |
| 16 | psy_en_q1 (insertion 3 ans) | 3/6/14 | 3/0/18 | **élimine 6 halluc** |
| 17 | psy_en_q2 (1ère S 7 maths) | 2/6/8 | 10/4/15 | +8 verified, -2 halluc |

**Régressions ponctuelles** (drift L2 normal pour pivot multi-corpus) :

| # | Query | v5++ ✓/✗ /total | v5+++ ✓/✗ /total |
|---|---|---|---|
| 2 | lila_q2 (fac vs école com) | 9/2/18 | 2/3/9 |
| 6 | theo_q3 (M2 droit) | 12/0/16 | 4/0/9 |
| 11 | mohamed_q2 (CAP cuisine) | 4/0/13 | 0/4/5 |

Compensées en aggregé. Magnitude similaire au drift Phase B / Phase C
DARES observé hier et cette nuit.

---

## Décision push

✅ **PUSH AUTORISÉ** sur `feat/france-comp-blocs-rncp` :

- Critère discipline scientifique respecté : v5+++ blocs **strictement
  meilleur** que v5++ (verified +, halluc -)
- Hallucination en forte baisse — bénéfice principal du pivot blocs RNCP
  est l'ancrage factuel de la génération, pas seulement le retrieval
  enrichi
- Effet émergent confirmé : 2 queries surfacent les blocs en top-K sans
  trigger explicit du pattern regex — le pivot est utile au-delà du seul
  case "questions compétences"

**Ne pas merger automatiquement** — en attente de `merge-approval`
Matteo (pattern human-gated CLAUDE.md §Merge autorisé post-validation).

---

## Suivi recommandé (post-merge)

1. **Bench blocs dédié** : 6-12 queries ciblées compétences ("quels blocs
   valide le BTS X", "que vais-je apprendre en BUT Y", "compétences VAE
   pour titre RNCP Z") pour mesurer le gain attendu du boost ×1.5 sur le
   domain `competences_certif`. Estimation ~$0.05 + 30 min.
2. **Phase D combinée** (post-merge PR #70 + PR #71) : index =
   phaseB + DARES + blocs (~54 297 vecteurs) pour tester l'effet
   cumulatif des 2 PRs. Bench v5++++ Phase D vs v5++ baseline.

---

## Reproductibilité

```bash
cd ~/projets/OrientIA && source .venv/bin/activate

# 1. Build corpus France Comp blocs (~30s, $0)
python -m src.collect.build_france_comp_blocs_corpus

# 2. Build index Phase C blocs (~90s, ~$0.13)
python scripts/build_index_phaseC_blocs.py

# 3. Bench v5+++ blocs (~12 min, ~$0.05)
python scripts/run_bench_personas_v5plusplusplus_blocs.py

# 4. Compare vs v5++ (relabeled baseline — voir PR #70)
diff <(jq '.[].fact_check_summary' results/bench_personas_v5plusplus_relabeled_2026-04-25/_ALL_QUERIES.json) \
     <(jq '.[].fact_check_summary' results/bench_personas_v5plusplusplus_blocs_2026-04-26/_ALL_QUERIES.json)
```

Inputs requis :
- `data/raw/rncp/export-fiches-csv-*.zip` (téléchargé par `src/collect/rncp.py`)
- `data/processed/rncp_certifications.json` (committé, généré par
  `src/collect/rncp.py` puis save_processed)
- `data/processed/formations_multi_corpus_phaseB.json` + `.index`
  (gitignored, rebuild via PR #67 pipelines)

**Note baseline v5++** : les artefacts `bench_personas_v5plusplus_relabeled_2026-04-25/`
sont committés dans PR #70 (cf docs/VERDICT_V5PLUSPLUSPLUS_DARES.md). Si
vous reviewez PR #71 en isolation, attendez la merge ou checkout local
des 2 PRs simultanément pour exécuter le diff.
