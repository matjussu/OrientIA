# OrientIA — Session Handoff

**Last updated:** 2026-04-16 (Run F+G COMPLETE — triple-layer analysis ready for paper)

This document is the **single source of truth for project state**. Any fresh
session (Claude Code or human) must read this FIRST. Updated whenever the
project's state changes materially.

---

## 1. Project at a glance

OrientIA is a research project for the **INRIA AI Grand Challenge** (French
student orientation guidance). Contest submission in ~3 weeks from 2026-04-13.

### Current empirical standing — Run 10 (2026-04-13)

On the original 32-question benchmark (dev set):

| System | Judge v1 | Judge v2 (regex fact-check) |
|---|---|---|
| our_rag (v3.2 + RAG) | **16.59** | **16.59** |
| mistral_raw (NEUTRAL) | 11.28 | 11.28 |
| chatgpt_recorded | 7.12 | 7.12 |
| **Gap our_rag vs mistral_raw** | **+5.31** | **+5.31** |

**our_rag wins all 7 categories** on dev. But see section 4 — this result
has methodological limitations (N=32, train=test, single judge, single run)
that Phase F is designed to fix.

### Run F+G COMPLETE (2026-04-16) — triple-layer analysis ready

Full benchmark executed: **100 questions × 7 systems × 3 judges**
= 2100 rubric judgments + 700 fact-checks.

**Artifacts in `results/run_F_robust/`:**
- `responses_blind.json` (4.7MB) — 100 q × 7 blinded answers
- `label_mapping.json` — per-question A-G → system mapping
- `scores_claude.json` — Claude Sonnet 4.5 v1 judge (6-criterion rubric)
- `scores_gpt4o.json` — GPT-4o v1 judge (same rubric)
- `scores_haiku_factcheck.json` — Haiku 4.5 fact-check (94 q) + Sonnet 4.5 fallback (6 cross-domain q blocked by API 529)
- `ANALYSIS_DUAL_JUDGE.md` — Run F only (v1 only)
- `ANALYSIS_TRIPLE_LAYER.md` — **FINAL** (v1 + v2 factcheck-weighted)

**Headline Run F+G** (mean /18, 100 questions):

| System | Claude v1 | Claude v2 | GPT-4o v1 | GPT-4o v2 |
|---|---|---|---|---|
| mistral_v3_2_no_rag | 15.43 | 14.39 | 16.12 | 15.12 |
| **our_rag** | 15.16 | **14.33** | **16.16** | **15.18** |
| claude_v3_2_no_rag | 13.71 | 13.31 | 14.70 | 14.10 |
| mistral_neutral (ref) | 11.72 | 11.45 | 14.56 | 14.06 |
| claude_neutral | 8.70 | 8.64 | 10.55 | 10.44 |
| gpt4o_v3_2_no_rag | 7.77 | 7.72 | 10.05 | 9.92 |
| gpt4o_neutral | 6.03 | 5.99 | 9.14 | 9.02 |

**Pivotal finding (ADR-014)** — The v3.2 prompt without RAG fabricates
plausible citations that naïve LLM-as-judge reward but Haiku fact-check
penalises. Under fact-check, `our_rag` overtakes `mistral_v3_2_no_rag`
on in-domain (92q) : Claude +0.03, GPT-4o +0.23. Per-category:
adversarial +0.70 shift, biais_marketing +0.67, cross_domain +0.62.

Inter-judge agreement (Run F rubric): Pearson 0.747, Spearman 0.752,
weighted κ 0.46-0.59 across 6 criteria.

Total Run F+G budget: **~$42** (sous le plan $70-90).

**Repo (private):** https://github.com/matjussu/OrientIA
**Local:** `/home/matteo_linux/projets/OrientIA`
**Plan:** `/home/matteo_linux/.claude/plans/radiant-beaming-mitten.md`
**Stack:** Python 3.12, mistralai 2.3.2 (paid tier), anthropic 0.93,
openai 2.31 (F.2), faiss-cpu, rapidfuzz, pandas, fastapi,
pytest 9.0.3, matplotlib.

---

## 2. Progress

### Initial phases (all done)
| Phase | Status |
|---|---|
| 0 — Bootstrap | ✅ 4/4 |
| 1 — Eval dataset (32 q) | ✅ 2/2 |
| 2 — Data collection | ✅ 6/6 |
| 3 — RAG pipeline | ✅ 7/7 |
| 4 — Benchmark (code) | ✅ 5/5 |

### Execution phases (10 runs + 3 method phases done)
| Phase | Status | Output |
|---|---|---|
| Runs 1-6 | ✅ | Plateau -1.6 identified |
| Run 7 (Phase 1 — prompt v3) | ✅ | Gap -1.47 |
| Run 8 (Phase C — prompt v3.1) | ✅ | Gap -0.16 |
| Run 9 (Phase D — confirmation) | ✅ | Gap +0.25 (v2 +0.38) |
| Run 10 (Phase E — fair baseline) | ✅ | **Gap +5.31** |
| Phase 3 — fact_check + judge v2 | ✅ | Claude Haiku fact-check shipped (not yet run) |

### Academic-grade upgrade (Phase F, running; G+H pending)
| Phase | Status | Commit |
|---|---|---|
| **F.1** Dataset 32 → 100 (32 dev + 68 test, 10 adv, 8 cross-domain) | ✅ | `627af62` |
| **F.2 pt 1** 3 new system classes | ✅ | `546baeb` |
| **F.2 pt 2** Runner + judge generalised to N systems | ✅ | `ed6c08c` |
| **F.2 pt 3** `run_real_full.py` 7-system orchestrator | ✅ | `b21aa76` |
| **F.2 runner fix** scale print + ThreadPoolExecutor to N | ✅ | `8295b1e` |
| **F.2 checkpoint** Sample test 5q × 7 sys ($0.50 actual) | ✅ | (validated) |
| **F.3.a** MMR post-rerank (TDD, 10 unit + 2 integration tests) | ✅ | `054bf4b` |
| **F.3.b** Rule-based intent classifier (TDD, 36 tests) | ✅ | `e4ed7ed` |
| **F.3.c** ~~Manual label expansion~~ SKIPPED (low ROI) | ⏭️ | — |
| **F.3.c-bis** Activate MMR+intent on OurRagSystem | ✅ | `dae9799` |
| **F.3.d** Local retrieval inspection on dev set (free) | ✅ | `dae9799` |
| **F.4 prep** Multi-judge (Claude Sonnet + GPT-4o) + run_judge_multi | ✅ | `8513b3c` |
| **F.4 prep** RPM rate limiter (OpenAI tier-1 fix) | ✅ | `40464f0` |
| **F.4 RUN F** generation 7 sys × 100 q (1 run) | ✅ done | `b02h15mwi` |
| **F.4 RUN F** GPT-4o judge (100q, $5) | ✅ done | Run F scores |
| **F.4 RUN F** Claude Sonnet judge (100q, $10 + $14 lost first attempt) | ✅ done | Run F scores + incremental save fix `3c4daf8` |
| **F.4 FIX** `judge_all` incremental save + resume | ✅ done | `3c4daf8` critical budget-safety fix |
| **G.5 RUN G** Haiku fact-check (94q Haiku + 6q Sonnet fallback) | ✅ done | `edb4e57` |
| F.4 RUN F runs 2 and 3 (variance, optional) | pending | — |
| G.1 Statistics module (bootstrap, t-test, κ, α) | pending | — |
| G.2 Human eval (2 students × 30 q blind) | pending | — |
| G.3-4 Adversarial + cross-domain analysis | ✅ in analyses | — |
| **H.1 STUDY_REPORT.md** (markdown, data ready) | pending — **next** | — |
| H.2 UI demo (optional) | pending | — |
| H.3 Reproducibility package | pending | — |

**Test suite: 231 tests green** (vs 169 at start of Phase F).

---

## 3. Data layer state

**`data/processed/formations.json`: 443 fiches** (unchanged since Run 6).

### Composition
- 343 Parcoursup fiches (cyber + data_ia)
- 102 ONISEP fiches
- 7 fuzzy-matched, 336 parcoursup_only, 100 onisep_only

### Labels (3-stage matcher in `src/collect/merge.py:attach_labels`)
- 21 SecNumEdu + 7 CTI + 1 Grade Master (as of Run 10 — unchanged).
- Manual table at `data/manual_labels.json` (25 entries, AUTHORITATIVE).
  Blocklist includes EPITA, Epitech, Guardia, IONIS, École 42.
- **F.3.c SKIPPED** — label expansion from 21 to 50 was identified as
  low-ROI (marginal multiplicative effect). Proper 200+ label expansion
  deferred to post-Run F decision.

### Enriched Parcoursup fields
- `niveau` inferred (bac+2/3/5)
- `detail`, `departement`, `profil_admis` (mentions %, bac_type %)
- `debouches` (ROME 4.0, injected post-merge)

### Niveau breakdown
274 bac+2 / 61 bac+3 / 71 bac+5 / 37 None.

---

## 4. RAG pipeline state

### Index
- `data/embeddings/formations.index` (1.7 MB, 443 × 1024 mistral-embed, gitignored).

### Reranker (`src/rag/reranker.py`)
```python
secnumedu_boost = 1.5     # but empirical best = 1.0 (Run 3 ablation)
cti_boost = 1.3
grade_master_boost = 1.3
public_boost = 1.1
level_boost_bac5 = 1.15
level_boost_bac3 = 1.05
etab_named_boost = 1.1
```

### System prompt (`src/prompt/system.py`)
Currently **v3.2** (Phase E.2, commit `b7d696b`).

### NEW : MMR post-rerank (Phase F.3.a)
- `src/rag/mmr.py` — `mmr_select(candidates, k, lambda_)` using
  embeddings from `IndexFlatL2.reconstruct()` (zero extra API cost).
- Retriever enriched : each result now carries `embedding: np.ndarray`.
- Pipeline flag `use_mmr=True` with default `mmr_lambda=0.7`.

### NEW : Intent classifier (Phase F.3.b)
- `src/rag/intent.py` — rule-based, 7 classes :
  `comparaison / geographic / realisme / passerelles / decouverte /
  conceptual / general`.
- Per-intent config : `intent_to_config(intent) -> IntentConfig` modulates
  `top_k_sources` + `mmr_lambda` per question.
- Pipeline flag `use_intent=True` overrides caller-provided top_k and lambda
  with the intent config.

### Phase F.3 retrieval config per intent
| intent | top_k_sources | mmr_lambda |
|---|---|---|
| general | 10 | 0.7 |
| comparaison | 12 | 0.6 |
| geographic | 12 | 0.4 |
| realisme | 6 | 0.85 |
| passerelles | 10 | 0.6 |
| decouverte | 12 | 0.3 |
| conceptual | 4 | 0.9 |

### F.3.d local validation findings (dev set, 32 q, free)
- D1, D2 [diversite_geo] : +2, +5 distinct villes (target hit)
- C2 [decouverte] : 1 → 4 distinct villes (target hit)
- E3, E4 [passerelles] : +2, +1 villes
- B4, B5 [realisme] : villes drop because top_k 10→6 (intended)
- Aggregate : +0.25 villes/q, -0.56 labelled fiches/q (focus tradeoff)
- Output saved to `results/retrieval_inspection.md`.

### 7-system baseline matrix (ready in `src/eval/systems.py`)
| # | name | prompt | RAG | purpose |
|---|---|---|---|---|
| 1 | `our_rag` | v3.2 | yes + MMR + intent | full stack (thesis) |
| 2 | `mistral_neutral` | NEUTRAL | no | baseline |
| 3 | **`mistral_v3_2_no_rag`** | v3.2 | no | **isolates RAG** |
| 4 | `gpt4o_neutral` | NEUTRAL | no | OpenAI baseline |
| 5 | `gpt4o_v3_2_no_rag` | v3.2 | no | OpenAI + prompt |
| 6 | `claude_neutral` | NEUTRAL | no | Anthropic baseline |
| 7 | `claude_v3_2_no_rag` | v3.2 | no | Anthropic + prompt |

**System 3** is the scientific key. `our_rag` gains MMR + intent since
Phase F.3.c-bis (commit `dae9799`).

### NEW : OpenAI tier-1 rate limiter (Phase F.4)
- `src/eval/rate_limit.py` — `RateLimiter(max_per_minute)`, thread-safe
  minimum-interval gate.
- Shared 12 RPM limiter between the 2 `OpenAIBaseline` systems in
  `run_real_full.make_seven_systems`.
- Solo 12 RPM limiter in `run_judge_multi._run_gpt4o`.
- Mistral + Anthropic paid tiers unthrottled (not needed at our volume).
- Empirical effect : 5 min/q → 27-48s/q (6-10× speedup), zero 429.

---

## 5. Benchmark history — 10 runs + methodological findings

### Aggregate scores (/18, Claude Sonnet 4.5 judge v1, dev set N=32)

| # | Config | our_rag | mistral_raw | gap | notes |
|---|---|---|---|---|---|
| 1 | strict prompt, labels ON | 13.41 | 16.19 | -2.78 | baseline minimum |
| 2 | relaxed, labels ON | 14.19 | 16.09 | -1.90 | +0.78 after relaxing |
| 3 | relaxed, labels OFF | 14.50 | 16.22 | -1.72 | label ablation |
| 4 | 1098 fiches | 14.44 | 16.19 | -1.75 | data expansion failed |
| 5 | ROME injected | 14.31 | 15.84 | -1.53 | ROME in ctx only |
| 6 | full stack | 14.28 | 15.91 | -1.63 | plateau |
| 7 | Phase 1 (prompt v3) | 14.78 | 16.25 | -1.47 | anti-confession |
| 8 | Phase C (prompt v3.1) | 15.16 | 15.31 | -0.16 | parity |
| 9 | confirmation | 15.75 | 15.50 | +0.25 | first win |
| **10** | **Phase E (fair baseline + v3.2)** | **16.59** | **11.28** | **+5.31** | decisive |

### Judge v2 (regex fact-check)
- Run 7 v2 : -0.88, Run 8 v2 : 0.00, Run 9 v2 : +0.38, Run 10 v2 : +5.31.

### Claude Haiku fact-check
Code shipped in Phase E.3 (`src/eval/fact_check_claude.py`, commit `9f1b5aa`).
**Never run** — Anthropic budget was exhausted before. Will execute at
Run G in Phase G.5.

### Historical findings (for the study report)
1. Retrieval constraint harm (Run 1→2, +0.78)
2. Label boost over-concentration (Run 3 ablation, +0.31)
3. Data breadth does not help (Run 4 regression)
4. ROME helps discovery — only out of embeddings (Run 5)
5. Enrichment is category-dependent (Run 6)
6. Anti-confession is the big prompt lever (Phase 1)
7. Conceptual / interdisciplinary / villes rules (Phase C)
8. Comparison-table rule (Phase E.2, +5.00 on comparaison)
9. Shared prompt = methodological error (Phase E.1)
10. **NEW (F.3.d) : MMR+intent gives +0.25 villes/q on dev, highest on
    the targeted D/C/E categories, no penalty elsewhere.**

### Run 10 limitations (Phase F is designed to fix all)
- N=32 → IC95% ±2 pts. True gap might be +3 to +7.
- Train = test : v3.x was tuned ON these 32 questions.
- Single judge Claude Sonnet 4.5.
- Single run of Run 10.
- ChatGPT recordings non-representative.
- No adversarial or cross-domain tests.

---

## 6. Active plan — the 3-week solidify+prove sprint

See `/home/matteo_linux/.claude/plans/radiant-beaming-mitten.md`.

### Week 1 — Solidify (Phase F, in progress)
- [x] F.1 Dataset expansion (100 q, dev/test/adversarial/cross-domain)
- [x] F.2 7-system baseline matrix + sample test validation
- [x] F.3 Method extensions (MMR + intent), F.3.c skipped
- [x] F.4 prep: multi-judge + rate limiter
- [🟡] F.4 RUN F — generation in progress (65/100 as of 16:27 on 2026-04-15)
- [ ] F.4 RUN F — multi-judge (Claude Sonnet + GPT-4o), auto-launched
      when generation finishes
- [ ] Checkpoint Matteo on Run F results → decide variance runs (x2 more)

### Week 2 — Prove
- G.1 Statistics module (bootstrap IC95%, paired t-test, Cohen's d, κ, α)
- G.2 Human eval (2 students × 30 questions blind, κ humain-Claude)
- G.3 Adversarial honesty rate
- G.4 Cross-domain analysis
- G.5 RUN G with 3 judges (Claude Sonnet + GPT-4o + Haiku fact-check, ~$30)

### Week 3 — Deliver
- H.1 `docs/STUDY_REPORT.md` (markdown, no LaTeX)
- H.2 UI demo (optional)
- H.3 Reproducibility package (`reproduce.sh`, dataset commit, video)

### Decision points
1. ~~F.2 checkpoint~~ ✅ passed
2. F.4 checkpoint (Run F results + ablation table) — **imminent**
3. G.5 checkpoint (Run G + human eval)
4. H.1 checkpoint (study report)

---

## 7. Commits made this sprint (chronological)

### F.1 — Dataset
- `627af62` feat(eval): F.1 — extend dataset 32 → 100 (dev/test split + types)

### F.2 — 7-system matrix
- `546baeb` feat(eval): F.2 part 1 — 3 new system classes
- `ed6c08c` feat(eval): F.2 part 2 — generalise runner + judge to N systems
- `b21aa76` feat(eval): F.2 part 3 — run_real_full orchestrates the 7-system matrix
- `8dce21d` docs: refresh SESSION_HANDOFF + README for Phase F state
- `8295b1e` fix(eval): scale runner print + ThreadPoolExecutor to N systems

### F.3 — Method extensions
- `054bf4b` feat(rag): F.3.a — MMR post-rerank for top-k diversification
- `e4ed7ed` feat(rag): F.3.b — rule-based intent classifier modulates retrieval
- `dae9799` feat(eval): F.3.c-bis + F.3.d — activate MMR/intent + retrieval inspection

### F.4 — preparation
- `8513b3c` feat(eval): F.4 multi-judge — GPT-4o judge + run_judge_multi orchestrator
- `40464f0` feat(eval): RPM rate limiter to handle OpenAI tier-1 (15 RPM gpt-4o)

### Protected files (still)
- `src/rag/embeddings.py` — `fiche_to_text` MUST NOT include ROME.
- `data/manual_labels.json` — blocklist authoritative.
- `src/eval/judge.py` v1 rubric — preserved for longitudinal comparison.
- `src/rag/reranker.py` — `RerankConfig` defaults stable since Run 3.

---

## 8. API budget state

### Mistral
- **Paid tier active**. Embeddings + chat.complete for generation.
- `Mistral(api_key=..., timeout_ms=120000)` since Run A.
- `_call_with_retry` handles rate limits, timeouts, 5xx, Cloudflare 520s.

### Anthropic (topped up 2026-04-15)
- **~$30-40 recharged** for Run F + G coverage.
- Usage : judge Sonnet 4.5 on Run F (×3), judge Sonnet on Run G (×3),
  Claude Haiku fact-check on Run G, 2 Claude baselines per run.

### OpenAI (new in Phase F, topped up 2026-04-15)
- **~$15 recharged**, tier 1 (15 RPM for gpt-4o).
- Rate limiter caps our outbound rate at 12 RPM → zero 429.
- Usage : GPT-4o as baseline system (×2 per run), GPT-4o as 2nd judge.

### Total sprint budget (estimate)
| Item | Cost |
|---|---|
| Sample tests (v1 + v2) | ~$0.80 (spent) |
| Run F generation (100q × 7 sys × 1 run) | ~$8-12 |
| Run F judge multi (Claude + GPT-4o) | ~$5-7 |
| Runs 2, 3 of F (if approved) | ~$25-30 |
| Run G generation + 3 judges | ~$25-30 |
| Buffer | ~$15-20 |
| **Total** | **~$70-90** |

### Rule : ZERO intermediate benchmarks
F.3 extensions were developed + tested locally without any judge calls
(F.3.d uses no LLMs). Only F.4 (Run F) and G.5 (Run G) spend judge money.

---

## 9. How to resume in a fresh session

```bash
cd /home/matteo_linux/projets/OrientIA
source .venv/bin/activate

# 1. Check state
cat docs/SESSION_HANDOFF.md   # this file
git log --oneline -15
pytest tests/ 2>&1 | tail -5  # 231 should be green

# 2. Confirm API keys
python3 -c "from src.config import load_config; c = load_config(); print(f'Mistral:{bool(c.mistral_api_key)}, Anthropic:{bool(c.anthropic_api_key)}, OpenAI:{bool(c.openai_api_key)}')"
# → all three True

# 3. Check Run F state
ls results/run_F_robust/
python3 -c "import json; print(len(json.load(open('results/run_F_robust/responses_blind.json'))), '/100')"

# 4a. If Run F generation finished (100/100) but judge not run:
python -m src.eval.run_judge_multi \
  --responses results/run_F_robust/responses_blind.json \
  --out-dir results/run_F_robust

# 4b. If Run F generation interrupted mid-way, resume:
python -m src.eval.run_real_full --out-dir results/run_F_robust
# Runner detects done_ids and continues.

# 4c. If Run F judge done — analyse:
ls results/run_F_robust/
# → responses_blind.json, label_mapping.json, scores_claude.json, scores_gpt4o.json
# → then compare judges via per-system means + compute κ inter-judge.
```

Then pick up from **F.4 analysis → variance runs → G.1 statistics module**.

---

## 10. Files to NOT modify lightly

Still hold — hard-won empirical decisions :
- `src/prompt/system.py` — v3.2 = result of 5 iterations. Changes should
  be ADDITIVE, not reverts.
- `src/eval/runner.py` — retry + resume + incremental save + Cloudflare
  handling are load-bearing for any multi-hour run.
- `data/manual_labels.json` — 25 entries curated authoritative.
- `src/rag/embeddings.py:fiche_to_text` — MUST NOT include ROME.
- `src/rag/reranker.py` — `RerankConfig` defaults stable since Run 3.
- `src/eval/judge.py` v1 rubric — preserved for v1 vs v2 comparison.
- `src/eval/rate_limit.py` — the 12 RPM cap is calibrated for OpenAI
  tier-1 with 2 concurrent systems + 25% safety margin. Don't raise
  until tier 2 confirmed.

---

## 11. Archives

All 10 historical runs under `results/run{N}_*/` :
- `run1_strict_sourcing/`
- `run2_relaxed_sourcing/`
- `run3_ablation_no_labels/`
- `run4_data_expansion/`
- `run5_rome_enriched/`
- `run6_full_stack/`
- `run7_phase1_densification/`
- `run8_phase1c_prompt_v31/`
- `run9_phase1c_confirmation/`
- `run10_phase_e_fair_baseline/`

Phase F run : `results/run_F_robust/` (active).

---

## 12. What comes next — immediate actions

**While Run F generation is running (~ETA 17:05 on 2026-04-15):**
- Monitor via `python3 -c "import json; print(len(json.load(open('results/run_F_robust/responses_blind.json'))))"`
- Claude auto-wakeups every 15-20 min to track progress.

**When generation hits 100/100:**
- Auto-launch `run_judge_multi` (~15-20 min, ~$5-7).
- Write analysis : per-system / per-category means, inter-judge κ,
  diff-vs-baseline table, 7-system ablation.

**After Run F analysis:**
- Present results to Matteo → decision to run variance (x2 more runs)
  or skip straight to Run G depending on the signal.
- If ablation proves RAG contribution significant → go to G.1 stats module.
- If our_rag ≤ mistral_v3_2_no_rag → honest publication that all gain
  came from the prompt.
