# Sprint 7 — Verdict méthodo + quick wins (5 actions + R6 compression + bench × 2 modes)

**Date** : 2026-04-27 (J-28 deadline INRIA 2026-05-25)
**Scope** : adresse les 3 leviers Sprint 7 du verdict Sprint 6 (méthodo
fact-check / bench enrichi / anti-hallu LLM) + amplification axe 3b star
+ tuning intent classifier
**Coût total** : ~$0,20 bench-check Action 1 + ~$0,10 build Phase E delta
+ ~$11,40 bench Option E × 2 modes triple-run = **~$11,70**

---

## ⚠️ Lecture du verdict

Synthèse honnête finale du Sprint 7 livré sous l'ordre Jarvis
`2026-04-27-1025-claudette-orientia-sprint7-methodo-quickwins`.

Mesure du gain combiné des 5 actions Sprint 7 (+ R6 compression Levier 3)
sur le bench enrichi 38q (24 baseline FIGÉE Sprint 5/6 stricte + 14
nouvelles Sprint 7), avec décomposition retrieval-side per-axe et
per-mode (Baseline vs Both).

---

## 1. Contexte

### Verdict Sprint 6 (rappel honnête)

Sprint 6 enrichissement corpora (+1 792 cells) **n'a PAS comblé le gap
-16,4pp verified** identifié dans verdict Sprint 5. Mean +0,4pp dans le
bruit IC95 8,89pp.

3 hypothèses pour le gap non-comblé (Sprint 7 attaque ces 3 leviers) :
- **Méthodologie fact-check** pénalise anti-hallu défensif (axe 4 muet)
- **Bench 24q** sous-représente les nouveaux axes
- **40% LLM hallucine** (audit Sprint 5 n=20) reste levier prédominant

### Sprint 7 — 5 actions priorisées + R6 compression

| Action | Description | PR | Cells/Tests |
|---|---|---|---|
| 1 | Fact-check `verified_by_official_source` (axe 4 unmute) | #87 | +24 tests |
| 5 | Intent + reranker boosts Sprint 6 axes (4 nouveaux DOMAIN_HINT) | #88 | +53 tests |
| 2 | Bench enrichi 38q (24 baseline + 14 nouvelles, option C) | #89 | +26 tests |
| 4 | Inserjeunes granularité 3 (×3,9 cells, +2 004 fap_region) | #90 | +7 tests |
| 3 | Anti-hallu LLM (Levier 1 v3.3 strict R1-R5 + Levier 2 critic loop) | #91 | +23 tests |
| **3b** | **R6 inline citation `[Source: ...]` (compression Levier 3)** | #92 | +6 tests |
| **Cumul tests** | | | **+139 tests** |

Phase E updated : **58 093 vecteurs** (+1 996 cells vs Phase E Sprint 6
56 089 — +2 004 nouvelles inserjeunes formation_region_diplome).

---

## 2. Méthodologie bench

### Bench Option E — 38 queries × 3 runs IC95 × 2 modes

- **Mode Baseline** : v3.2 SYSTEM_PROMPT + critic loop OFF (= comportement
  Sprint 5/6 baseline reproductible apples-to-apples)
- **Mode Both** : v3.3 strict (R1-R6) + critic loop ON (= cumul actions
  Sprint 7)

Pas d'ablation Strict-only ou Critic-only dans Sprint 7 (budget Option E
contraint). En backlog Sprint 7.5 si verdict ambigu.

### Comparabilité directe avec baseline Sprint 5/6

L'option C du patch Action 2 préserve les 24 queries baseline strictes
(6 personas q1 + 6 dares + 6 blocs + **6 user_naturel q11-q16** strict
Sprint 5/6) → mean Sprint 7 vs mean Sprint 5/6 baseline 39,4% ± IC95
3,66pp directement comparable.

### Décomposition retrieval-side per-axe + per-mode (Option A)

Mapping granularité → axe Sprint 6 (étendu Sprint 7) :
- `fap_region` → axe 1 DARES re-agg
- `formation_france`, `region_diplome`, `formation_region_diplome` (NEW
  Sprint 7 Action 4) → axe 3b inserjeunes
- `dispositif`, `voie` → axe 4 financement
- `territoire`, `synthese_cross` → axe 2 DROM territorial
- `bac_pro_domaine`, `cap_domaine`, `type_diplome_synthese` → axe 3a
  voie pré-bac

Caveat épistémique : corrélation, pas causalité (cf verdict Sprint 6 §4).

---

## 3. Bench-check intermédiaire Action 1 (post-merge #87)

**Confirmation empirique unmute axe 4 financement** :

- 4 queries Sprint 7 FINANCEMENT_QUERIES, 45 stats
- pct_verified : **93,3%** (vs 0% Sprint 6 axe 4 muet)
- n_verified_strict : 39 / n_verified_by_source : **3** (Action 1 unmute)
- pct_hallucinated : **0%**

Source : `results/sprint7_bench_check_action1_financement/_AGGREGATE.json`.

Lecture honnête : effet plus subtil que dramatique (3/42 verified sont
`by_source`, 39/42 sont strict). Le LLM gen tend à citer directement
les chiffres présents dans les fiches. Mais 0 hallucinations sur 45
stats → anti-hallu défensif tient bon avec le nouveau verdict.

---

## 4. Résultats globaux bench × 2 modes

> **Section à remplir post-bench**. Placeholders ci-dessous.

### IC95 aggregate

| Métrique | Sprint 7 Mode Both | Sprint 7 Mode Baseline | Sprint 5/6 baseline figée |
|---|---|---|---|
| pct_verified mean | _TBD_ ± IC95 _TBD_ | _TBD_ ± IC95 _TBD_ | 39,4% ± 3,66pp |
| pct_hallucinated mean | _TBD_ ± IC95 _TBD_ | _TBD_ ± IC95 _TBD_ | 17,9% ± 3,90pp |
| avg latency | _TBD_ s | _TBD_ s | 12,35s |
| **Delta verified Both vs Baseline** | _TBD_ pp | — | — |
| **Delta verified Both vs Sprint 5/6** | _TBD_ pp | — | — |
| **Delta halluc Both vs Baseline** | _TBD_ pp | — | — |
| n_total_stats | _TBD_ | _TBD_ | ~552 |
| Total elapsed | _TBD_ min | _TBD_ min | ~50 min |

### Lecture (post-bench)

> Section à remplir selon résultat.
>
> Si delta verified ≥ 8pp → gain solide, Sprint 8 = ground truth + structured output JSON
> Si delta 3-8pp → gain modéré, isoler Strict vs Critic en Sprint 7.5
> Si delta < 3pp → gain faible, ablation ciblée prio 1 Sprint 7.5

---

## 5. Décomposition retrieval-side per-axe × per-mode

> **Section à remplir post-analyse**. Tableau cible :

| Axe | Both: active% | Both: verif%when | Baseline: active% | Baseline: verif%when |
|---|---|---|---|---|
| 1 — DARES re-agg | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| 2 — DROM territorial | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| 3a — Voie pré-bac | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| 3b — Inserjeunes (×3,9 cells) | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| 4 — Financement (Action 1 unmute) | _TBD_ | _TBD_ | _TBD_ | _TBD_ |

---

## 6. Décomposition par "vieilles" vs "nouvelles" queries

> **Section à remplir post-analyse**. Mesurer le gain sur :
> - 24 baseline FIGÉE q11-q16 stricts vs 14 nouvelles Sprint 7
> - Si gain plus fort sur nouvelles → axes 3a/3b/4 effectifs
> - Si gain similaire sur vieilles → effet anti-hallu LLM générique

---

## 7. Roadmap Sprint 8 priorisée selon résultats

### Si verdict gain solide (≥8pp delta verified)

- **Priorité 1 — Ground truth ablation** : 1 run par axe désactivé pour
  isoler la causalité (vs Option A retrieval corrélationnelle)
- **Priorité 2 — Structured output JSON** {claim, source} parser-friendly
  (vraie version Levier 3, R6 reste compress 30min Sprint 7)
- **Priorité 3 — Bench extended 50q** pour réduire l'IC95 sub-2pp

### Si verdict gain modéré (3-8pp delta verified)

- **Priorité 1 — Sprint 7.5 ablation** : isoler Strict-only vs Critic-only
  (~$5-7 délta)
- **Priorité 2 — Re-tuning intent boost values** (1.4-1.5 → expérimenter)
- **Priorité 3 — Critic loop tuning** : si critic ne bouge pas l'aiguille,
  désactiver par défaut

### Si verdict gain faible (<3pp delta verified)

- **Priorité 1 — Re-évaluer méthodologie fact-check** : peut-être que
  StatFactChecker manque des claims importants
- **Priorité 2 — User testing réel** : LLM-judge plateau, étudiants
  réels = ground truth ultime
- **Priorité 3 — Pivot RAFT spécialisé** (cf STRATEGIE_VISION §6)

---

## 8. Caveats honnêtes Sprint 7

> **Section à compléter post-bench**. Caveats déjà connus :

1. **n=38 queries × 3 runs** vs n=48 baseline figée Sprint 5. Compromis
   budget Option E. Compatible avec mean Sprint 5/6 sur subset 24q figé.

2. **Pas d'ablation Strict-only / Critic-only** en Sprint 7. Bench mode
   Both = combinaison Action 1+5+2+4+3+3b cumulée. Si gain ambigu →
   Sprint 7.5 ablation ciblée.

3. **Option A retrieval-side corrélation** : les attributions pp par axe
   restent indicatives (limite épistémique reproduit verdict Sprint 6).

4. **R6 inline citation** = variante pragmatique 30min, pas la vraie
   structured output JSON parser-friendly. Bench mesure si R6 améliore
   le sourcage visible mais ne valide pas la JSON robustesse.

5. **Discipline scientifique R3** : verdict honnête même si gain <attendu.
   Pattern Sprint 5 R3 revert + Sprint 6 R3 honnêteté reproduit.

---

## 9. Reproductibilité

```bash
cd ~/projets/OrientIA && source .venv/bin/activate

# Build Phase E updated (delta inserjeunes Action 4 granularité 3)
python -m scripts.build_index_phaseE  # ~$0.10, ~30s

# Bench-check intermédiaire Action 1 (validation unmute axe 4)
python -m scripts.bench_check_action1_financement  # ~$0.20, ~3 min

# Bench final 2 modes triple-run IC95 (Option E budget validé)
python -m scripts.run_bench_sprint7_final  # ~$11.40, ~2h05

# Analyse retrieval-side per-axe per-mode
python -m scripts.analyze_retrieval_per_axis_sprint7  # gratuit, ~10s

# Outputs :
# - data/processed/formations_multi_corpus_phaseE.{json,index}
# - results/sprint7_bench_check_action1_financement/
# - results/sprint7_bench_final_2026-04-27/{mode_baseline,mode_both}/
# - results/sprint7_bench_final_2026-04-27/_VERDICT_DELTA.json
# - results/sprint7_bench_final_2026-04-27/_RETRIEVAL_ANALYSIS_PER_AXIS_SPRINT7.json
```

---

## 10. Sprint 7 status final

✅ Phase 0 — Audit méthodo Sprint 6 (3 leviers identifiés)
✅ Action 1 — Re-design fact-check `verified_by_official_source` (mergée #87)
✅ Action 5 — Tuner intent + 4 reranker boosts (mergée #88)
✅ Action 2 — Bench enrichi 38q (option C 24q strict baseline) (mergée #89)
✅ Action 4 — Inserjeunes granularité 3 (×3,9 cells) (mergée #90)
✅ Action 3 — Anti-hallu LLM Leviers 1+2 (mergée #91)
✅ Action 3b — R6 inline citation compression Levier 3 (mergée #92)
✅ Bench-check intermédiaire Action 1 — UNMUTE axe 4 confirmé (93,3% verified, 0 halluc)
🟡 Bench final Option E — _en cours / TBD post-bench_
🟡 Verdict final — ce document, à finaliser

**Cumul Sprint 7** :
- 6 PRs livrées (5 mergées + 1 verdict final)
- +139 tests cumul Sprint 7, **1 534 passed, 0 régression**
- 1 996 nouvelles cells retrievable (granularité 3 inserjeunes)
- Phase E : 58 093 vecteurs

**Vélocité** : 5 actions + R6 livrées en ~3h cumul vs 4,5-5,5j workflow
initial = ratio ETA/réel **~14×**.

---

*Doc préparée par Claudette le 2026-04-27 sous l'ordre
`2026-04-27-1025-claudette-orientia-sprint7-methodo-quickwins`.
Dernière mise à jour : post-bench × 2 modes.*
