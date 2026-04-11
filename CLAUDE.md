# CLAUDE.md — Operating directives for OrientIA

These are directives for Claude Code (any model, any session) working on
OrientIA. They are engineering-discipline rules, not project information.
For project state, read `docs/SESSION_HANDOFF.md`.

---

## 1. Start of every session — non-negotiable

1. **Read `docs/SESSION_HANDOFF.md` FIRST** before touching code or running
   commands. It contains the latest project state, blockers, budget, and
   user preferences. If it's missing or outdated, ask the user before
   proceeding.
2. **Read the last 15 commits** (`git log --oneline -15`) to understand
   recent direction.
3. **Verify the test suite passes** (`pytest tests/ -v 2>&1 | tail -5`)
   before making any change. If it's broken on pull, STOP and diagnose.
4. **Check budget state** from the handoff. NEVER run a benchmark or paid
   experiment without explicit user confirmation if it costs > $0.50.

---

## 2. Communication style with Matteo

- **French.** Always. Technical terms in English are fine when natural.
- **Direct and data-driven.** Don't soften bad results. If the RAG lost,
  say so explicitly, then propose options.
- **Present decisions as options with costs/benefits**. Let Matteo decide.
  Example: "Option A: X ($1.15, +0.5 estimated). Option B: Y ($0, -effort).
  My recommendation: A. Dis-moi."
- **No emoji padding** unless the user uses emojis first or the content
  genuinely needs them (radar charts, benchmark tables).
- **Single insights in `★ Insight` blocks** when the information is
  genuinely non-obvious. Don't use them for trivial commentary.
- **Concise status updates during long tasks.** Background process
  progress: "Run X at 20/32, ETA 4 min".

---

## 3. Engineering discipline — HARD RULES

### TDD (test-driven development)
- For any new Python module: **write test first, run red, implement, run
  green, commit**. Never skip the red phase.
- For data-layer or pipeline changes that are hard to unit-test: write a
  smoke test that loads real data and checks invariants.

### Isolate variables
- **Change ONE thing at a time** when measuring impact. Bundling 3 fixes
  in a single benchmark run (as was done in run 6) makes attribution
  impossible.
- Exception: if the user explicitly requests "try X+Y+Z together", say yes
  but warn that attribution will be unclear and suggest a 2nd run with
  individual ablations if results are ambiguous.

### Judge / benchmark noise awareness
- The Claude-as-judge has **~0.4 points of global variance** and up to
  **2.6 points of category-level variance**. Any improvement below 0.5
  points total is **indistinguishable from noise**. Don't claim victory
  on it.
- When comparing runs, check: did mistral_raw (which doesn't use our
  context) also change? If yes by a similar magnitude, the delta is
  judge variance, not your improvement.

### Commit frequently, commit atomically
- One conceptual change per commit. Write a descriptive body (not just
  title) explaining the rationale, especially for non-obvious choices.
- After any experiment that produces results to archive, commit the
  results folder immediately.
- **Push to origin at every commit** unless the user says otherwise.
  The repo is private; losing local state is the worst outcome.

### Checkpoint frequently — SESSION_HANDOFF.md is load-bearing
- Update `docs/SESSION_HANDOFF.md` every time:
  - A benchmark run completes
  - The data layer is re-merged with different config
  - The system prompt is changed
  - A significant refactor lands
  - The user's preference on next steps changes
- The handoff file is the single point of recovery if conversation
  context is lost. Treat it as a living document, not an afterthought.

### Before committing
- Run `pytest tests/ 2>&1 | tail -5` — must show 0 failures
- Run `git status --short` — make sure you're not committing accidentally
- For large commits, run `git diff --stat` to sanity-check the scope

---

## 4. Decision-making protocol

### Never spend budget without explicit confirmation
- Mistral paid tier is active. Mistral calls are "free" in the sense that
  Matteo has credit; still, communicate cost estimates for any run > 10
  API calls.
- Anthropic judge calls cost ~$1.15 per 32-question benchmark. NEVER run
  a judge without the user saying "go" for that specific experiment.
- Grid searches cost $5-6. NEVER run one without explicit confirmation.
- When presenting options, include `$` cost estimates.

### When an experiment fails or results are disappointing
- **Diagnose before iterating.** Show the user what you think went wrong
  and why. Don't just run a "fix" blindly.
- Offer **3 options minimum** when possible (a fix, a different angle,
  an honest "accept and pivot"). Let the user choose.
- Say "I don't know" when you don't know. Don't guess.

### Know when to stop
- **Diminishing returns**: if 2 consecutive experiments move scores by
  < 0.3 points in random directions, you've hit a plateau. Tell the user
  and propose to pivot strategy (data layer, different eval method, or
  move to next phase).
- **Budget wall**: if the next experiment would consume > 40% of remaining
  Anthropic budget, warn the user explicitly before running it.
- **Time wall**: if we're deep in debugging a side issue (rate limits,
  flaky tests), consider if the side issue is blocking the real goal
  or just friction we can work around.

---

## 5. Running long tasks (benchmarks, re-merges, index rebuilds)

### Use background mode for anything > 2 minutes
```bash
# Use run_in_background=true in Bash tool
# Let the notification system wake you when done
# DO NOT poll actively
```

### Write state incrementally
- Any loop that processes N items and could fail midway MUST write state
  after each item. The runner already does this (`results/*/raw_responses/
  responses_blind.json` is flushed every question).

### Handle transient errors with retry logic
- `_call_with_retry` in `src/eval/runner.py` is the canonical pattern.
  Use it for any Mistral/Anthropic call in a long loop.
- Rate-limit (429) errors need long base delay (15s+).
- Read/connect timeouts need short base delay (2s+).
- Max retries 5-6 is reasonable.

### Always set Mistral client timeout explicitly
```python
Mistral(api_key=..., timeout_ms=120000)  # 2 minutes
```
The default httpx timeout is too short for mistral-medium-latest on long
contexts. This is non-optional.

---

## 6. Writing the final paper (Phase 6)

When you get there, honor the empirical data:
- **Do not claim the RAG beats mistral_raw globally**. The 6 runs show
  consistent gap of -1.6 to -1.9.
- **Do claim RAG reaches parity or wins on specific categories**
  (realism at certain configs, honesty at ablation config, biais_marketing
  with enrichment).
- **Do claim the retrieval-constraint-harm finding** (run 1 → run 2
  diagnostic) as a methodological contribution.
- **Do claim the judge methodology flaw** (rewards apparent sourcing) as
  a warning for future RAG benchmarks.
- **Do NOT overstate.** Negative and partial results, honestly presented,
  are publishable.

If the fact-check judge experiment is run and reverses the result,
that becomes the paper's headline. If not, the plateau analysis becomes
the headline.

---

## 7. Things to avoid (lessons from this session)

1. **Bundling multiple fixes in one experiment** — run 6 combined ROME
   decouple + Parcoursup enrichment + strict joins. The mixed results
   were impossible to attribute. Run ablations individually when time
   permits.

2. **Claiming wins from noise-level deltas** — early runs claimed
   "+0.78 points = success" when judge variance was similar. Always
   check: did the control group (mistral_raw) also change?

3. **Assuming strict instructions help** — the early "ne cite JAMAIS
   hors contexte" prompt rule crippled the RAG. Strict sourcing is
   epistemically tempting but practically harmful when the dataset
   is incomplete.

4. **Ignoring budget until it bites** — calculate Anthropic cost per
   experiment upfront. Offer the user the choice of running vs skipping
   based on cost.

5. **Forgetting to commit after successful experiments** — at one point
   we had 5 runs of results sitting uncommitted in `results/`. Always
   archive and commit immediately after an experiment succeeds.

6. **Running subagents when inline is clearer** — subagents are great
   for isolated TDD tasks, but for orchestration scripts (running 3
   components in sequence with error handling), inline is simpler and
   faster to debug.

---

## 8. Project-specific shortcuts

### Run the CLI smoke test on a real question
```bash
source .venv/bin/activate
python -m src.rag.cli "Ta question ici"
```

### Re-run the merge pipeline
```bash
python -m src.collect.run_merge
```

### Full benchmark + judge + analyze pipeline
```bash
python -m src.eval.run_real     # benchmark ($0, Mistral paid)
python -m src.eval.run_judge    # judge ($1.15, Anthropic)
python -m src.eval.analyze      # free, produces radar chart
```

### Start a custom experiment with different RerankConfig
Use an inline Python script with `from src.rag.reranker import RerankConfig`
and `OrientIAPipeline(client, fiches, rerank_config=custom_cfg)`. See
`run3_ablation` or `run6_full_stack` experiments in the git history for
templates.

### Restore 439-fiche dataset (truncate ONISEP to 102, re-merge)
```python
import json
from pathlib import Path
p = Path('data/raw/onisep_formations.json')
data = json.loads(p.read_text('utf-8'))
if len(data) > 102:
    p.write_text(json.dumps(data[:102], ensure_ascii=False, indent=2), 'utf-8')
# Then: python -m src.collect.run_merge
```

---

## 9. Meta-directive

If in doubt about a change, **ask the user**. The cost of a clarifying
question is ~10 seconds. The cost of implementing the wrong thing and
re-running benchmarks is ~$1.15 + 10 minutes + the user's trust.

The user (Matteo) has consistently shown he prefers:
- Honest diagnosis over optimistic framing
- Data over narrative
- Options over predetermined choices
- Iterating on real results over guessing at optimums

Honor this. You are not trying to make him happy. You are trying to
produce a publishable INRIA paper with empirically defensible findings.
Those two goals are aligned.
