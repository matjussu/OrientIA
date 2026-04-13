# OrientIA — Session Handoff

**Last updated:** 2026-04-13 (after Run 10 + Phase F.1 + F.2 complete, awaiting sample test)

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

**our_rag wins all 7 categories.** But see section 4 — this result has
serious methodological limitations (N=32, train=test, single judge,
single run) that Phase F is designed to fix.

### What's happening now (Phase F active, 2026-04-13 → 2026-05-04)

The plan `/home/matteo_linux/.claude/plans/radiant-beaming-mitten.md`
describes a 3-week sprint to transform the PoC into a scientifically
defensible study:
- Solidify : N=32 → 100 questions, 3 systems → 7 (fair baselines incl.
  mistral_v3_2_no_rag), 1 run → 3 runs with variance bars.
- Prove : multi-judge (Claude + GPT-4o + 2 students), adversarial test
  set, cross-domain probe.
- Deliver : markdown study report + optional UI demo + reproducibility
  package. NO formal paper writing in this sprint (deferred).

**Repo (private):** https://github.com/matjussu/OrientIA
**Local:** `/home/matteo_linux/projets/OrientIA`
**Plan:** `/home/matteo_linux/.claude/plans/radiant-beaming-mitten.md`
**Stack:** Python 3.12, mistralai 2.3.2 (paid tier), anthropic 0.93,
openai 2.31 (new in Phase F), faiss-cpu, rapidfuzz, pandas, fastapi,
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
| Runs 1-6 (prompt iteration, data iteration) | ✅ | Plateau gap -1.6 identified |
| Run 7 (Phase 1 — prompt v3) | ✅ | Gap -1.47 |
| Run 8 (Phase C — prompt v3.1) | ✅ | Gap -0.16 (parity) |
| Run 9 (Phase D — confirmation) | ✅ | Gap +0.25 (win, v2) |
| Run 10 (Phase E — fair baseline) | ✅ | Gap +5.31 (decisive, v1) |
| Phase 3 — fact_check + judge v2 | ✅ | Claude Haiku fact-check shipped (not yet run on Anthropic budget exhausted before) |

### Academic-grade upgrade (Phase F + G + H, active)
| Phase | Status | Commit |
|---|---|---|
| **F.1** Dataset 32 → 100 (32 dev + 68 test, 10 adversarial, 8 cross-domain) | ✅ | `627af62` |
| **F.2 pt 1** 3 new system classes (Mistral-custom-prompt, OpenAI, Claude) | ✅ | `546baeb` |
| **F.2 pt 2** Runner + judge generalised for N systems | ✅ | `ed6c08c` |
| **F.2 pt 3** `run_real_full.py` 7-system orchestrator + `--sample` mode | ✅ | `b21aa76` |
| **F.2 checkpoint** Sample test 5 q × 7 systems (~$0.50) | ⏳ awaiting user API setup | — |
| F.3 Method extensions (MMR + intent + multi-label) | pending | — |
| F.4 Run F — 7 sys × 100 q × 3 runs × 2 judges (~$35) | pending | — |
| G.1 Statistics module (bootstrap, t-test, κ, α) | pending | — |
| G.2 Human eval (2 students × 30 questions blind) | pending | — |
| G.3-4 Adversarial + cross-domain analysis | pending | — |
| G.5 Run G — same + Claude Haiku fact-check (~$30) | pending | — |
| H.1 STUDY_REPORT.md (markdown, no LaTeX) | pending | — |
| H.2 UI demo (optional) | pending | — |
| H.3 Reproducibility package | pending | — |

**Test suite: 169 tests green** (was 91 at Run 6 baseline).

---

## 3. Data layer state

**`data/processed/formations.json`: 443 fiches** (unchanged since Run 6).

### Composition
- 343 Parcoursup fiches (cyber + data_ia, `\b`-bounded keywords)
- 102 ONISEP fiches (JWT auth, Application-ID `69d9234235746681b78b4568`)
- 7 fuzzy-matched, 336 parcoursup_only, 100 onisep_only

### Labels (3-stage matcher in `src/collect/merge.py:attach_labels`)
- 21 SecNumEdu + 7 CTI + 1 Grade Master (as of Run 10)
- Manual table at `data/manual_labels.json` (25 entries, AUTHORITATIVE).
  Blocklist includes EPITA, Epitech, Guardia, IONIS, École 42.
- **F.3 will expand coverage** to 50+ labelled fiches (CTI/CGE/Grade Master
  systematic cross-reference).

### Enriched Parcoursup fields (per `src/collect/parcoursup.py:extract_fiche`)
- `niveau` inferred (bac+2/3/5)
- `detail` text, `departement`, `profil_admis` (mentions %, bac_type %,
  acces %, boursiers %)
- `debouches` (ROME 4.0, injected post-merge, ~9 codes for cyber / 6 for data_ia)

### Niveau breakdown
274 bac+2 / 61 bac+3 / 71 bac+5 / 37 None.

---

## 4. RAG pipeline state

### Index
- `data/embeddings/formations.index` (1.7 MB, 443 × 1024 mistral-embed, gitignored).

### Reranker (`src/rag/reranker.py`)
Defaults:
```python
secnumedu_boost = 1.5  # but empirical best = 1.0 (Run 3 ablation)
cti_boost = 1.3
grade_master_boost = 1.3
public_boost = 1.1
level_boost_bac5 = 1.15
level_boost_bac3 = 1.05
etab_named_boost = 1.1
```

### System prompt (`src/prompt/system.py`)
Currently **v3.2** (Phase E.2, commit `b7d696b`) — includes:
- Anti-confession rule (Phase 1)
- Plan A/B/C structure (Phase 1)
- ≥ 3 régions diversity (Phase 1)
- Conceptual bypass for H-category (Phase C)
- Interdisciplinary bias for C-category (Phase C)
- Distinct-villes rule for D-category (Phase C)
- **Comparison-table rule for F-category** (Phase E.2)

### `fiche_to_text` (embeddings) vs `format_context` (generator)
- `src/rag/embeddings.py:fiche_to_text` — does NOT include ROME debouches
  (pollution risk). Protected file.
- `src/rag/generator.py:format_context` — signal-first 7-line layout,
  detail truncated at 500 chars, top-3 ROME metiers. Commits `2c8c99f`,
  `3ecfc44`.

### 7-system baseline matrix (Phase F.2, ready for Run F)

Systems defined in `src/eval/systems.py`:

| # | name | prompt | RAG | purpose |
|---|---|---|---|---|
| 1 | `our_rag` | v3.2 | yes | full stack (thesis) |
| 2 | `mistral_neutral` | NEUTRAL | no | baseline |
| 3 | **`mistral_v3_2_no_rag`** | v3.2 | no | **isolates RAG** |
| 4 | `gpt4o_neutral` | NEUTRAL | no | OpenAI baseline |
| 5 | `gpt4o_v3_2_no_rag` | v3.2 | no | OpenAI + our prompt |
| 6 | `claude_neutral` | NEUTRAL | no | Anthropic baseline |
| 7 | `claude_v3_2_no_rag` | v3.2 | no | Anthropic + our prompt |

**System 3** is the scientific key : if `our_rag > mistral_v3_2_no_rag`
significantly, the RAG adds value beyond prompt engineering. If not,
we publish honestly.

Orchestrator: `src/eval/run_real_full.py` (`--sample N` for cost
validation, default full = 100 questions × 7 systems).

---

## 5. Benchmark history — 10 runs + methodological findings

### Aggregate scores (/18, Claude Sonnet 4.5 judge v1, dev set N=32)

| # | Config | our_rag | mistral_raw | gap | notes |
|---|---|---|---|---|---|
| 1 | strict prompt, labels ON | 13.41 | 16.19 | -2.78 | baseline minimum |
| 2 | relaxed, labels ON | 14.19 | 16.09 | -1.90 | +0.78 after removing strict sourcing |
| 3 | relaxed, labels OFF | 14.50 | 16.22 | -1.72 | label boost ablation |
| 4 | 1098 fiches | 14.44 | 16.19 | -1.75 | data expansion failed |
| 5 | ROME injected | 14.31 | 15.84 | -1.53 | ROME in context, not embeddings |
| 6 | full stack (ROME decouple + PS enrich + strict joins) | 14.28 | 15.91 | -1.63 | plateau |
| 7 | Phase 1 (format_v2 + prompt v3) | 14.78 | 16.25 | -1.47 | anti-confession flip |
| 8 | Phase C (prompt v3.1) | 15.16 | 15.31 | -0.16 | parity |
| 9 | confirmation | 15.75 | 15.50 | +0.25 | win (v1) / +0.38 (v2) |
| **10** | **Phase E (fair baseline + v3.2 comparison table)** | **16.59** | **11.28** | **+5.31** | decisive |

### Judge v2 (regex fact-check, free post-process)
- Run 7 v2 : gap -0.88 (vs -1.47 v1) — fact-check penalises fabrications
- Run 8 v2 : gap 0.00 (parity)
- Run 9 v2 : gap +0.38
- Run 10 v2 : gap +5.31 (equal to v1 here because both our_rag and the
  neutral mistral_raw have similar sourçage profiles under the regex)

### Judge v2 Claude Haiku
Code shipped in Phase E.3 (`src/eval/fact_check_claude.py`, commit `9f1b5aa`).
**Never run** — Anthropic budget was exhausted before we could. Ready for
Run G in Phase G.5 once budget returns.

### Historical findings (for the study report)

1. **Retrieval constraint harm** (Run 1 → Run 2 diagnostic, +0.78 pts) —
   the strict "ne cite JAMAIS hors contexte" rule crippled the RAG on
   orthogonal questions.
2. **Label boost over-concentration** (Run 3 ablation, +0.31) — with
   only 21 labelled fiches, secnumedu_boost=1.5 hurt diversity.
3. **Data breadth does not help** (Run 4 regression) — broader ONISEP
   queries diluted domain specificity.
4. **ROME helps discovery** (Run 5, decouverte +1.40) — but ONLY when
   kept out of embeddings.
5. **Enrichment is category-dependent** (Run 6) — helps factual
   questions, hurts conceptual ones.
6. **Anti-confession is the big prompt lever** (Phase 1) — flipped
   passerelles gap from -1.20 to +1.00.
7. **Conceptual bypass / interdisciplinary / distinct-villes** (Phase C)
   — each rule fixed one specific category.
8. **Comparison-table rule** (Phase E.2) — flipped comparaison from
   -1.40 to +3.60 on Run 10.
9. **Shared prompt = methodological error** (Phase E.1) — our Run 7-9
   parity was inflated because mistral_raw was being crippled by our
   custom rules. NEUTRAL_MISTRAL_PROMPT fixed this and revealed the
   true gap (+5.31).

### Known Run 10 limitations (Phase F is designed to fix all)

- N=32 → IC95% ±2 pts. True gap might be +3 to +7.
- Train = test : v3.x was tuned ON these 32 questions.
- Single judge Claude Sonnet 4.5 → no cross-check.
- Single run of Run 10 → no variance bars.
- ChatGPT recordings non-representative (short responses, no system
  prompt, snapshot 2026-04-10).
- No test set on real hold-out questions.
- No adversarial test measuring honesty rate.
- No cross-domain test.

---

## 6. Active plan — the 3-week solidify+prove sprint

See `/home/matteo_linux/.claude/plans/radiant-beaming-mitten.md` for
the full plan. Key milestones:

### Week 1 — Solidify (in progress)
- [x] F.1 Dataset expansion (100 q, dev/test/adversarial/cross-domain)
- [x] F.2 7-system baseline matrix (code shipped)
- [ ] **F.2 checkpoint** : sample test 5 q × 7 systems (~$0.50). Requires
      OPENAI_API_KEY set + Anthropic top-up ($5).
- [ ] F.3 Method extensions : MMR + intent + multi-label (TDD, 0 cost)
- [ ] F.4 RUN F : 7 sys × 100 q × 3 runs × 2 judges (~$35)

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

### Decision points (checkpoints Matteo)
1. F.2 end (sample test results)
2. F.4 end (Run F results + ablation table)
3. G.5 end (Run G results + human eval)
4. H.1 end (study report review)

---

## 7. Code changes made this sprint (Phase F.1 + F.2, commits)

### F.1 — Dataset
- `627af62` feat(eval): F.1 — extend dataset 32 → 100 (dev/test split + types)
  - `src/eval/questions.json` now 100 questions (32 dev + 68 test)
  - New fields per question: `split`, `type`
  - 10 adversarial (X1-X10) with fake schools/reports/towns
  - 8 cross-domain (Z1-Z8) for outside cyber/data
  - `tests/test_questions.py` rewritten (11 new tests)

### F.2 — 7-system matrix
- `546baeb` feat(eval): F.2 part 1 — 3 new system classes
  - `MistralWithCustomPromptSystem`, `OpenAIBaseline`, `ClaudeBaseline`
  - Config: new optional `OPENAI_API_KEY`
  - Dep: `openai==2.31.0` added
  - 5 new tests in `test_systems.py`
- `ed6c08c` feat(eval): F.2 part 2 — generalise runner + judge to N systems
  - `runner.py`: `blind_labels(n)` helper, `assert >= 2` instead of `== 3`
  - `judge.py`: `_build_user_content(question, answers)` dynamic template,
    `_max_tokens_for_n(n)` scaling
  - Backward compat: all N=3 tests still pass
- `b21aa76` feat(eval): F.2 part 3 — run_real_full orchestrates the 7-system matrix
  - `src/eval/run_real_full.py` with `make_seven_systems(cfg)` factory
  - `--sample N` mode for cost validation

### Protected files (still)
- `src/rag/embeddings.py` — `fiche_to_text` must NOT include ROME debouches
- `data/manual_labels.json` — blocklist authoritative
- `src/eval/judge.py` v1 rubric — preserved for v1 vs v2 comparison
- `src/rag/reranker.py` — `RerankConfig` defaults stable since Run 3

---

## 8. API budget state (CRITICAL)

### Mistral
- **Paid tier active** (Matteo topped up ~$10 initially, probably still
  some credit). Embeddings + chat.complete usage for generation.
- **Operational config** :
  ```python
  Mistral(api_key=..., timeout_ms=120000)  # Non-optional since Run A
  ```
  `_call_with_retry` (`src/eval/runner.py`) handles rate limits, timeouts,
  5xx, and Cloudflare 520s.

### Anthropic
- **Was: $0** (exhausted at end of Run 10, 2026-04-11).
- **Pending: Matteo top-up** (~$5 for sample test, then ~$30-50 for
  Run F + G).
- **Usage planned** : judge Sonnet 4.5 on Run F (×2), judge Sonnet on
  Run G (×2), Claude Haiku fact-check on Run G, 2 Claude baselines
  (claude_neutral, claude_v3_2_no_rag) as systems.

### OpenAI (new in Phase F)
- **Pending: Matteo setup** of `OPENAI_API_KEY`.
- Usage planned : GPT-4o as baseline system (×2 per run), GPT-4o as
  2nd judge (×3 runs).
- `src/config.py:Config.openai_api_key` is optional (empty string when
  unset) — allows pytest collection without the key.

### Total budget for 3-week sprint : ~$70-90

| Item | Cost |
|---|---|
| Sample test 5 q × 7 sys | ~$0.50 |
| Run F (generation + 2 judges × 3 runs) | ~$35 |
| Run G (generation + 3 judges × 3 runs) | ~$30 |
| Buffer (debug, re-run) | ~$15-20 |

### Rule : ZERO intermediate benchmarks
F.3 extensions are developed + tested locally without any judge calls.
Only F.4 (Run F) and G.5 (Run G) spend judge money. Everything else
is free.

---

## 9. How to resume in a fresh session

```bash
cd /home/matteo_linux/projets/OrientIA
source .venv/bin/activate

# Check state
cat docs/SESSION_HANDOFF.md   # this file
cat CLAUDE.md                 # operational directives
git log --oneline -15
pytest tests/ 2>&1 | tail -5  # 169 should be green

# Confirm Phase F artifacts are ready
python3 -c "import json; d = json.load(open('src/eval/questions.json')); print(f\"{len(d['questions'])} questions\")"
# → 100 questions

python3 -c "from src.eval.run_real_full import make_seven_systems; print('ready')"
# → ready

# Check environment keys
python3 -c "from src.config import load_config; c = load_config(); print(f'Mistral: {bool(c.mistral_api_key)}, Anthropic: {bool(c.anthropic_api_key)}, OpenAI: {bool(c.openai_api_key)}')"
# → all three must be True before the sample test

# When budget + keys are set, run the sample test (~$0.50):
python -m src.eval.run_real_full --sample 5 --out-dir results/sample_test
# Inspect results/sample_test/responses_blind.json to verify
# 5 questions × 7 labels are all populated.
```

Then pick up from **Phase F.3** (method extensions) per the plan.

---

## 10. Files to NOT modify lightly

Still hold — these represent hard-won empirical decisions :

- `src/prompt/system.py` — v3.2 is the result of 5 iterations (strict →
  relaxed → v3 anti-confession → v3.1 conceptual/interdisciplinary/
  villes → v3.2 comparison-table). Further changes should be ADDITIVE,
  not reverts.
- `src/eval/runner.py` — retry + resume + incremental save + Cloudflare
  handling are load-bearing for any multi-hour run.
- `data/manual_labels.json` — 25 entries curated for authoritative
  behaviour. Stage 3 of attach_labels depends on this.
- `src/rag/embeddings.py:fiche_to_text` — must NOT include ROME.
- `src/rag/reranker.py` — `RerankConfig` defaults should stay; runtime
  configs can override `secnumedu_boost=1.0` for ablation.
- `src/eval/judge.py` v1 rubric — preserved for longitudinal comparison
  with Run 6-9 archives.

---

## 11. Archives

All 10 historical runs archived under `results/run{N}_*/` :
- `run1_strict_sourcing/`
- `run2_relaxed_sourcing/` (separate dir from others)
- `run3_ablation_no_labels/`
- `run4_data_expansion/`
- `run5_rome_enriched/`
- `run6_full_stack/`
- `run7_phase1_densification/`
- `run8_phase1c_prompt_v31/`
- `run9_phase1c_confirmation/`
- `run10_phase_e_fair_baseline/`

Each contains `raw_responses/`, `scores/` (blind + unblinded + summary,
v1 and v2 when available), and `charts/` (radars).

Latest working state also in top-level `results/scores/` and
`results/raw_responses/` (gitignored for raw_responses, committed for
scores) — overwritten on each new run.

---

## 12. What comes next — immediate actions for the next session

**If Matteo has NOT yet set up OPENAI_API_KEY + Anthropic top-up** :
- Don't run `--sample 5` yet (will fail).
- Work on F.3 method extensions (MMR, intent, multi-label) — TDD, $0.
- Keep checking if keys are set (section 9 check command).

**If Matteo HAS set up keys** :
- Run `python -m src.eval.run_real_full --sample 5 --out-dir results/sample_test`
- Verify 5 × 7 = 35 responses are generated (mistral + gpt-4o + claude
  should all work).
- Inspect response quality briefly (are they substantive? formatted well?).
- If all good, proceed to F.3.
- If something fails, fix before F.3.

**Then** F.3 (method extensions) in TDD, then Run F in Phase F.4.
