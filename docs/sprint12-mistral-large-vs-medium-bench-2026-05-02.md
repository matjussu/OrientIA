# Sprint 12 — Bench Mistral Large vs Medium en gen finale (verdict)

> **Statut** : VERDICT EMPIRIQUE (à compléter post-bench multi-judge n=30)
> **Date** : 2026-05-02
> **Branche** : `feat/sprint12-bench-mistral-large-vs-medium` depuis main `efe28a2`
> **Spec ordre** : 2026-05-02-1239-claudette-orientia-sprint12-bench-mistral-large-vs-medium

---

## TL;DR (à compléter post-bench)

- **Decision** : `GO_LARGE` / `NO_GO` / `SIGNAL_MEDIOCRE`
- **Δ Claude rubric cumul 30q** : (TBD)
- **Δ GPT-4o rubric cumul 30q** : (TBD)
- **κ inter-judge** : (TBD) (cible ≥0.6 sinon flag fragilité)
- **Vérifiabilité Haiku factcheck** : medium=(TBD), large=(TBD), Δ=(TBD)
- **Latence** : medium=(TBD)s/q, large=(TBD)s/q
- **Coût total bench** : ~$2.62 estimé

---

## Contexte

Run F+G du 16/04 disait "prompt seul compétitif". Test 1 Sprint 12 axe 2 (`docs/sprint12-axe-2-golden-pipeline-v3-test-1-2026-05-02.md`) disait "no-RAG cumul 128 > enriched 120 sur n=10 single-judge". Les bench v1/v2/v3 axe 2 étaient bruit-dominants (stdev ~2.07/Q sur n=10).

**Hypothèse Matteo+Jarvis 2026-05-02 10:30** : le bottleneck est probablement Mistral medium en gen finale, pas l'architecture RAG. Variable jamais testée — Mistral Large vs medium sur le pipeline canonical actuel.

- Si **Large >> medium** → fix qu'on cherche depuis 2 semaines
- Si **Large ≈ medium** → problème ailleurs (architecture, données, RAFT future)

Coût marginal acceptable : Mistral Large ~5× medium ($0.025 vs $0.005/req) = OK pour démo INRIA + utilisateur réel si gain prouvé.

---

## Méthodologie ROBUSTE (Apprentissage #15 appliqué)

| Élément | Choix |
|---|---|
| **N questions** | **30** (vs n=10 v1+v2+Test 1 axe 2 = bruit dominant) |
| **Split** | `test` hold-out, sorted by id (reproductible) |
| **Judges cross-vendor** | Claude Sonnet 4.5 + GPT-4o + Haiku 4.5 factcheck |
| **κ inter-judge** | Cohen's kappa Claude vs GPT-4o sur winner par question |
| **Variable isolée** | SEULEMENT `OrientIAPipeline.model` change |
| **Tout le reste identique** | Corpus 55k, prompt v4 default, metadata filter, Q&A Golden, rerank, MMR, intent classifier |

### Critères de décision explicites

- **GO Large** : `Δ Claude rubric cumul > +1.5` (>3×stdev observé v1+v2+Test 1 ≈ 2.07/Q × √30 ≈ 11.3 mais Δ moyenné par question ≈ stdev individuel /√n donc seuil cumul +1.5 = robuste)
- **NO-GO** : `Δ < +0.5` (modèle pas bottleneck)
- **Signal médiocre** : `0.5 ≤ Δ < 1.5` (n=30 insuffisant)

---

## Configuration

### `our_rag_enriched_medium` (baseline)

`OurRagSystem(OrientIAPipeline(model="mistral-medium-latest", ...))` config canonical Sprint 11 P1.1 :
- Corpus 55 606 fiches `formations_unified.json` + index `formations_unified.index`
- `use_metadata_filter=True` (default)
- `use_golden_qa=True`
- SYSTEM_PROMPT v4 (default = Sprint 11 P0 préfixe + corps v3.2)

### `our_rag_enriched_large` (variable testée)

Identique baseline **sauf** `model="mistral-large-latest"` au constructeur OrientIAPipeline.

---

## Résultats — métriques globales (à compléter)

(à compléter post-bench)

| Métrique | medium | large | Δ |
|---|---|---|---|
| Claude rubric cumul (sum 30q) | TBD | TBD | TBD |
| Claude mean per Q | TBD | TBD | TBD |
| Claude stdev | TBD | TBD | — |
| Wins (Claude) | TBD | TBD | — |
| GPT-4o rubric cumul | TBD | TBD | TBD |
| Haiku vérifiabilité mean | TBD | TBD | TBD |
| Latence avg (s) | TBD | TBD | TBD |
| Coût per Q (cumul) | TBD | TBD | — |

### κ inter-judge (Claude vs GPT-4o)

| Métrique | Valeur |
|---|---|
| Agreement % | TBD |
| Cohen's kappa | TBD |
| n questions | TBD |

(Si κ < 0.6 : flag fragilité, prudence interpretation)

---

## Sample 5 questions verbatim Pattern #4 (à compléter)

### Cas 1 — Win Large (Δ ≥ +3) — TBD

### Cas 2 — Win Large (Δ ≥ +2) — TBD

### Cas 3 — Win Large (Δ ≥ +1) — TBD

### Cas 4 — Win Medium (Δ ≤ -1) — TBD

### Cas 5 — Tie ou cas équivalent — TBD

---

## Décision finale et recommandations (à compléter)

(à compléter selon verdict)

### Si GO_LARGE clair (Δ > +1.5)

Reco bascule `mistral-large-latest` partout sur le pipeline canonical :
- Modif `src/rag/pipeline.py` : `model: str = "mistral-large-latest"` (passer default)
- Modif `src/rag/cli.py` : INDEX_PATH inchangé, juste model par defaut
- Bench V2 baselines naturels Playwright (chatgpt_natural / claude_natural / mistral_natural) avec Large pour mesurer cibles INRIA jury
- Dossier INRIA narratif "modèle plus capable + RAG enrichi = combinaison gagnante"
- Coût additionnel utilisateur ~5× (acceptable pour démo INRIA)

### Si NO_GO (Δ < +0.5)

Modèle pas le bottleneck. Recos :
- Priorité Sprint 12 Bench V2 baselines naturels Playwright pour mesurer où on est vraiment vs cibles INRIA jury (pas un investment Large vs Medium)
- Reflexion ailleurs : architecture (rerank intelligent ?), données (RAFT fine-tuning ?), prompt (v5 ?)

### Si signal médiocre (0.5 ≤ Δ < 1.5)

n=30 insuffisant. Options :
- Étendre à n=68 (test set complet) si budget OK (~$5)
- Multi-juges renforcé (5 juges au lieu de 3) si budget OK (~$3)
- Flag honnête au dossier INRIA "le gain Large est modéré, dans la marge d'incertitude méthodologique"

---

## Bugs rencontrés pendant le bench (à compléter)

(à compléter — log précis si bugs)

### Bug #(N) — TBD

(format : symptôme + trigger + root cause + fix + tests garde-fou)

---

## Coûts cumul Sprint 12 final

(à compléter post-bench)

- Étape 4 axe 2 bench v1 : ~$0.65
- Étape 6 axe 2 bench v2 : ~$0.70
- Étape 7 axe 2 Test 1 : ~$1.0
- **Bench Mistral Large vs Medium n=30 multi-judge** : ~$X.XX (TBD)
- **Total Sprint 12 cumul : ~$X.XX** (vs estimé total $30-50)

---

## Apprentissages cumul (#15-#19 axe 2 + nouveaux)

- **#15** Single-judge n=10 a stdev ~2.07/Q → écarts cumul <13 dans bruit. n=30 + multi-judge cross-vendor minimum pour verdicts robustes.
- **#16** Boost ×1.3 metadata filter améliore marginalement diversite_geo
- **#17** Bench apple-to-apple peut être biaisé par flags actifs implicites (criteria=None bypass)
- **#18** Tests mockés Mistral ≠ tests intégration data hétérogène
- **#19** Filter metadata n'est pas la cause unique du gap diversite_geo
- **#20 (NEW candidate)** Variable isolée stricte requise pour bench A/B robuste : seul le model gen change, tout le reste identique. Permet d'attribuer le delta exclusivement au model variable.

---

## Artefacts livrables

- `src/eval/systems.py` : `OurRagSystem.name` paramétrable (modif additive)
- `scripts/bench_sprint12_mistral_large_vs_medium.py` (NEW)
- `results/bench_sprint12_mistral_large_vs_medium/` :
  - `responses_blind.json` (30q × 2 systems)
  - `latency.json` (per-Q × per-system)
  - `scores_claude.json`
  - `scores_gpt4o.json`
  - `haiku_factcheck.json`
  - `verdict.json` (computed metrics + decision)
- `docs/sprint12-mistral-large-vs-medium-bench-2026-05-02.md` (ce verdict)

---

*Spec ordre : `2026-05-02-1239-claudette-orientia-sprint12-bench-mistral-large-vs-medium`. Plan vault associé (Jarvis).*
