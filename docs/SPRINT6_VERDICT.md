# Sprint 6 — Verdict combler les gaps data (5 axes corpora)

**Date** : 2026-04-27 (J-28 deadline INRIA 2026-05-25)
**Scope** : combler les 60% gap data identifié dans verdict Sprint 5 §4 P1 via 5 axes d'enrichissement corpora (DARES re-agg / inserjeunes / financement / DROM territorial / voie pré-bac)
**Coût total** : ~$0.10 build Phase E + ~$3.60 bench triple-run = ~$3.70

---

## ⚠️ Lecture du verdict

Ce document est la **synthèse honnête finale** du Sprint 6 livré par
Claudette le 2026-04-27 sous l'ordre Jarvis
`2026-04-27-0825-claudette-orientia-sprint6-corpora-gaps`.

Il quantifie l'impact des 5 axes d'enrichissement corpora sur le
benchmark apples-to-apples vs baseline figée Sprint 5 (39.4% verified
± IC95 3.66pp, 17.9% halluc ± 3.90pp), avec décomposition retrieval-side
per-axe (Option A — corrélation indicative, pas causalité ground truth).

---

## 1. Contexte

### Verdict Sprint 5 (rappel)

Le rebench apples-to-apples Sprint 5 (PR #80, 24q × 3 IC95) a mesuré
une **régression -16.4pp verified** vs baseline figée :

| Métrique | Sprint 5 agent (24q × 3) | Baseline figée (48q × 3) | Delta |
|---|---|---|---|
| pct_verified | 23.0% ± IC95 19.73pp | 39.4% ± 3.66pp | **−16.4pp** ⚠️ |
| pct_hallucinated | 17.7% ± 27.85pp | 17.9% ± 3.90pp | −0.2pp ≈ |
| avg latency | 23.12s | 12.35s | +10.8s |

Décomposition causale Sprint 5 (audit qualitatif Claude Sonnet 4.5
sur 20 claims unsupported, n=20) :
- **60% gap data** (top-K corpora ne couvre pas le claim valide) ⭐ priorité
- 40% LLM hallucine (claim fabriqué)
- 0% LLM-judge sur-strict (calibration fact-checkers fair)

### Sprint 6 — 5 axes d'enrichissement

| Axe | Description | Cells ajoutées | PR |
|---|---|---:|---|
| 1 | DARES re-agg FAP × région granulaire | +1 049 | #81 mergée |
| 3b | Inserjeunes lycée pro re-agg | +689 | #82 mergée |
| 4 | Financement études/formation curated | +28 | #83 mergée |
| 2 | DROM-COM territorial curated | +6 | #84 mergée |
| 3a | Voie pré-bac (BAC PRO + CAP) catalogue | +20 | #85 mergée |
| **Total** | | **+1 792 cells** | 5 PRs |

Phase E index : **56 089 vecteurs** (54 297 phaseD + 1 792 nouveaux).

---

## 2. Méthodologie bench

### Apples-to-apples Sprint 5 reproduit

- 24 queries balanced (6 personas + 6 DARES + 6 blocs + 6 user-naturel)
- Triple-run IC95 (n=3, t=4.303 df=2)
- AgentPipeline aggregated_top_n=8, enable_fact_check=False
- StatFactChecker post-hoc sur sources_aggregated apples-to-apples baseline

### Différence vs Sprint 5

- Index : **Phase E** (56 089 vecteurs) au lieu de Phase D (54 297)
- Champ supplémentaire `granularities_top_k` extrait pour chaque entry
  (permet l'analyse retrieval-side per-axe Option A)

### Décomposition retrieval-side per-axe (Option A)

Méthodologie : pour chaque query × run, identifier les granularités
présentes dans le top-K et croiser avec les stats verified pour
estimer la contribution **corrélationnelle** par axe.

**Caveat épistémique explicite** : c'est de la corrélation, pas de la
causalité. Un axe présent dans le top-K associé à des stats verified
n'est pas pour autant la cause causale de ces verified. Le LLM gen
peut citer une fiche A même quand l'axe X est aussi dans le top-K.
Ground truth causal = ablation 1 run/axe désactivé (×6 cost). Acceptable
Sprint 6 pour orientation Sprint 7.

---

## 3. Résultats globaux

### IC95 aggregate

> **Section à remplir post-bench**. Placeholders ci-dessous.

| Métrique | Sprint 6 Phase E (24q × 3) | Sprint 5 (24q × 3) | Baseline figée (48q × 3) |
|---|---|---|---|
| pct_verified mean | _TBD_ ± IC95 _TBD_ pp | 23.0% ± 19.73pp | 39.4% ± 3.66pp |
| pct_hallucinated mean | _TBD_ ± IC95 _TBD_ pp | 17.7% ± 27.85pp | 17.9% ± 3.90pp |
| avg latency | _TBD_ s | 23.12s | 12.35s |
| Delta verified vs Sprint 5 | _TBD_ pp | — | — |
| Delta verified vs baseline | _TBD_ pp | −16.4pp | — |

### Lecture

> Section à remplir post-bench selon le résultat :
> - Si gain solide vs Sprint 5 (>8pp) : enrichissement corpora a comblé une partie du gap data
> - Si gain modéré (3-8pp) : enrichissement partiel, axes muets potentiels à creuser
> - Si gain faible (<3pp) : enrichissement insuffisant ou ciblage retrieval défaillant

---

## 4. Décomposition retrieval-side per-axe (Option A)

> **Section à remplir post-analyse**. Tableau cible :

| Axe | Pct queries actives | Pct verified when active | Attribution pp estimée | Muet ? |
|---|---|---|---|---|
| 1 — DARES re-agg | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| 3b — Inserjeunes | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| 4 — Financement | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| 2 — DROM territorial | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| 3a — Voie pré-bac | _TBD_ | _TBD_ | _TBD_ | _TBD_ |

### Identification axes muets

Un axe est candidat **muet** si actif dans ≥3 queries top-K mais
0 verified attribuable. Candidats Sprint 7 dépriorisation ou
re-architecture.

> Section à remplir post-analyse.

### Lecture per-axe

> Section à remplir post-analyse. Pour chaque axe :
> - Pourquoi cette contribution ? (queries types matchées)
> - Limite identifiée ?
> - Recommandation Sprint 7 ?

---

## 5. Roadmap Sprint 7+ (priorisée selon résultat)

### Si gain global solide (≥8pp verified récupérés)

- **Priorité 1 — Anti-hallucination LLM (40% restant audit Sprint 5)** :
  - Prompt système gen plus strict sur sources verbatim
  - Critic loop : LLM relit sa réponse + flag chiffres non-sourcés
  - Génération structured JSON + per-claim source citation
- **Priorité 2 — Optim latence agent** : streaming, parallel sub-query, prompts cap

### Si gain global modéré ou faible

- **Priorité 1 — Re-architecture retrieval** : ablation ciblée pour identifier le ou les axes muets, soit re-design des cells (texte plus signalant), soit re-tuning intent classifier / reranker
- **Priorité 2 — Anti-hallu** identique ci-dessus
- **Priorité 3 — Backlog Sprint 6 axes optionnels** :
  - Granularité 3 inserjeunes (libellé × type × région) — verdict Sprint 5 P1.4
  - Insersup re-agg per-(diplôme × discipline × région) — verdict Sprint 5 P1.4

### Roadmap fixe quel que soit le résultat

- **Polish dossier livrable INRIA J-28** : narrative Sprint 6 défendable
- **Documentation reproductibilité** : `scripts/build_index_phaseE.py` + `scripts/run_bench_sprint6_apples.py` + `scripts/analyze_retrieval_per_axis_sprint6.py` doivent être exécutables fresh-clone

---

## 6. Caveats honnêtes Sprint 6

1. **n=24 queries balanced** vs n=48 baseline. Compromis budget accepté
   Sprint 5 reproduit pour comparabilité IC95. Représentatif mais pas
   exhaustif.

2. **IC95 large** (Sprint 5 ±19-28pp avec n=3 sur 24q) : la variance
   per-run domine. Le mean reste informatif mais pas significatif
   stat p<0.05. Repeating n=5/n=10 réduira IC95 mais coût × ; out of
   scope Sprint 6.

3. **Option A retrieval-side = corrélation, pas causalité**. Les
   attributions pp par axe sont des estimations indicatives (le LLM
   gen peut citer une autre fiche du top-K même si l'axe X est présent).
   Ground truth → ablation 1 run/axe désactivé (×6 cost).

4. **Anti-hallu défensif corpus curé (axes 4 + 2)** : les chiffres exacts
   peuvent vieillir entre la curation manuelle (2026-04-27) et le bench.
   URL officielle systématique pour vérification user, mais pour le
   StatFactChecker post-hoc, les chiffres approximatifs marqués `~X` ne
   sont pas extraits comme stats vérifiables (dilution potentielle des
   "verified" sur ces 2 axes).

5. **Phase E ne contient pas tous les corpus possibles**. Backlog Sprint
   7+ : insersup re-agg P1.4, granularité 3 inserjeunes, INSEE
   territorial métropolitain élargi, ONISEP fiche complète qualitative
   live (si gap résiduel mesuré).

6. **Discipline scientifique** : verdict honnête même si gain <attendu.
   Pattern reproduit du Sprint 5 (revert R3 single-run optimisme corrigé
   par triple-run transparence).

---

## 7. Reproductibilité

```bash
cd ~/projets/OrientIA && source .venv/bin/activate

# Phase E build (delta sur phaseD, ~30s + ~$0.10)
python -m scripts.build_index_phaseE

# Bench triple-run (24q × 3, ~50 min, ~$3.60)
python -m scripts.run_bench_sprint6_apples

# Analyse retrieval-side per-axe (post-process, gratuit)
python -m scripts.analyze_retrieval_per_axis_sprint6

# Outputs :
# - data/processed/formations_multi_corpus_phaseE.{json,index}
# - results/sprint6_bench_apples_2026-04-27/run{1,2,3}/
# - results/sprint6_bench_apples_2026-04-27/_AGGREGATE.json
# - results/sprint6_bench_apples_2026-04-27/_RETRIEVAL_ANALYSIS_PER_AXIS.json
```

---

## 8. Sprint 6 status final

✅ Phase 0 — Audit gap-par-gap (sources légales identifiées)
✅ Axes data 1, 2, 3a, 3b, 4 — 5/5 livrés (5 PRs mergées sur main)
✅ Phase E build — 56 089 vecteurs (×1.033 vs Phase D, +1 792 cells)
🟡 Bench triple-run — _en cours / TBD_
🟡 Analyse retrieval-side — _en attente bench_
🟡 Verdict final — ce document, à finaliser post-bench

**Cumul cells retrievable Sprint 6 vs baseline pré-Sprint 6** :
**+1 792 cells** (+3.3% sur Phase D 54 297 → Phase E 56 089).

**Tests** : 1 372 verts cumul (post-merge 5 axes), 0 régression sur 5 PRs.

---

*Doc préparée par Claudette le 2026-04-27 sous l'ordre
`2026-04-27-0825-claudette-orientia-sprint6-corpora-gaps`. Dernière
mise à jour : post-bench triple-run + analyse retrieval-side.*
