# OrientIA — Decision Log

**Purpose:** chronological log of major design decisions with date,
rationale, and alternatives considered. Complements `METHODOLOGY.md`
(the *how*) with the *why*. Each entry is ADR-lite (Architecture
Decision Record) format.

Entries are append-only — if a decision gets reversed, add a new
entry pointing to the old one, don't edit history.

---

## ADR-001 — Use Mistral as generation and embedding model (2026-03-10)

**Context.** The project targets French educational guidance for INRIA's
AI Grand Challenge.

**Decision.** Use `mistral-medium-latest` for generation and
`mistral-embed` for embeddings across the `our_rag` system.

**Rationale.**
- Native French optimization (vs GPT-4o / Claude being English-first).
- French sovereignty narrative aligns with INRIA's mission.
- Same provider for embeddings + generation = vector-space consistency.
- Cost-competitive for the benchmark scale.

**Alternatives considered.**
- OpenAI `text-embedding-3-large` + `gpt-4o` : rejected on sovereignty.
- Anthropic Claude + Voyage embeddings : rejected on French specialisation.
- Local open-weights (Llama, Mistral-Nemo) : rejected — higher complexity,
  lower baseline quality for French.

---

## ADR-002 — Label-based reranker instead of pure vector similarity (2026-03-15)

**Context.** FAISS cosine-similarity retrieval surfaces private schools
with dense SEO metadata more than public programs with sparse ONISEP
descriptions.

**Decision.** Add a multiplicative reranker stage that boosts fiches
carrying official labels (SecNumEdu, CTI, Grade Master, public status).

**Rationale.**
- The thesis of OrientIA is that *official institutional labels* are
  the right correction for private-school marketing bias.
- Multiplicative boost is simple, interpretable, auditable.
- Weights determined via grid search (`src/eval/grid_search.py`).

**Alternatives.**
- Hybrid BM25 + vector : rejected — still doesn't encode the label
  priority.
- LLM-based reranker : rejected on cost + latency.

---

## ADR-003 — 7-system ablation matrix instead of 3-system comparison (2026-04-13)

**Context.** Phase E (Run 10) showed `our_rag` +5.31 over `mistral_raw`,
but the original 3-system setup (our_rag / mistral_raw / chatgpt_recorded)
can't disentangle "RAG adds value" from "our v3.2 prompt adds value".

**Decision.** Expand to a 7-system matrix :
```
1. our_rag                 (v3.2 + RAG)
2. mistral_neutral         (NEUTRAL, no RAG)
3. mistral_v3_2_no_rag     (v3.2, no RAG)      ← ISOLATES RAG
4. gpt4o_neutral           (cross-vendor fair baseline)
5. gpt4o_v3_2_no_rag       (cross-vendor prompt portability)
6. claude_neutral          (cross-vendor fair baseline)
7. claude_v3_2_no_rag      (cross-vendor prompt portability)
```

**Rationale.**
- System 3 is the scientific key : if `our_rag > mistral_v3_2_no_rag`
  significantly, RAG adds value beyond prompt engineering.
- Systems 4-7 test cross-vendor prompt portability : does v3.2 also
  improve GPT-4o / Claude ? (If yes, that strengthens the contribution.)
- Systems 2, 4, 6 act as honest baselines for each LLM family.

**Alternatives.**
- Keep 3 systems and accept the ambiguity : rejected — reviewer would
  rightly call out the train=test problem.
- 9 systems (add ChatGPT + generic Claude as 8/9) : rejected on cost
  ($35 → $50+) and diminishing scientific return.

---

## ADR-004 — ChatGPT recordings replaced by API baselines (2026-04-13)

**Context.** Runs 1-10 used `chatgpt_recorded` (manual ChatGPT Plus web UI
responses, frozen at 2026-04-10) as the third system. This was non-
representative : short responses, no system prompt, manual transcription.

**Decision.** Remove `chatgpt_recorded` entirely in Phase F. Replace with
API-driven `OpenAIBaseline` (×2 configurations) in the 7-system matrix.

**Rationale.**
- Reproducibility : API calls are deterministic + scriptable, web UI
  recordings are not.
- Controllability : we can set temperature, max_tokens, system prompt
  exactly — web UI injects hidden context.
- Fairness : the API version is what a developer would actually use.

**Alternatives.** Keep recordings as supplementary : rejected, confuses
the narrative.

---

## ADR-005 — Dev/test split at 32/68 instead of 80/20 random (2026-04-13)

**Context.** The original 32 questions have been used for 10 runs of
prompt tuning (v3 → v3.1 → v3.2). A reviewer would rightly say
"train = test, overfitting".

**Decision.** Preserve the 32 original questions as `dev` set (for
historical traceability and prompt tuning). Add 68 brand-new questions
as `test` set (generation assisted by Claude Opus, manual review). The
**headline numbers in the study report will come from the test set**.

**Rationale.**
- Historical traceability : we can still compare Run F to Run 1-10
  via the dev subset.
- Hold-out honesty : test set has never informed any prompt change.
- Category balance preserved : both splits cover the 9 categories
  proportionally.

**Alternatives.**
- 80/20 random split : rejected — loses historical comparability.
- 50/50 : rejected — dev too small to still calibrate prompts.

---

## ADR-006 — Human evaluation via 2 students (IA + Cyber), not domain experts (2026-04-13)

**Context.** Original Phase G plan mentioned "expert humain" as a
ground truth. Matteo pushed back : no expert available, but 2 student
peers available (1 IA, 1 Cyber student).

**Decision.** Use 2 students × 30 blind-labelled questions as the human
eval protocol. Measure :
- Inter-student Cohen's κ (agreement between the 2)
- Student-vs-Claude κ (validates LLM-as-judge methodology)
- Student ranking of the 7 systems (headline human-preference metric)

**Rationale.**
- Students represent the target audience (18-22 yr olds in orientation
  decisions) — their preferences are diagnostic.
- 2 students gives us agreement stats; a single expert would not.
- Zero API cost for this layer → doesn't compete with Run F/G budget.

**Alternatives.**
- No human eval : rejected — the paper needs human validation of
  LLM-as-judge to be defensible.
- Recruit paid experts : rejected on cost + timeline.

---

## ADR-007 — NEUTRAL_MISTRAL_PROMPT as baseline (2026-04-12, Phase E.1)

**Context.** Runs 6-9 compared `our_rag` against `mistral_raw` where
mistral_raw used the *same* v3.2 prompt as our_rag. This handicapped the
baseline : mistral_raw had to respect rules (anti-confession, Plan A/B/C,
etc.) designed for a RAG-augmented model.

**Decision.** Create `NEUTRAL_MISTRAL_PROMPT` — a plain generic-assistant
prompt — and use it for the 3 `*_neutral` baselines (mistral, gpt4o,
claude).

**Rationale.**
- Scientific integrity : a fair baseline must not be crippled by rules
  it can't satisfy (can't cite sources when it has no retrieval).
- Reveals the true contribution of the RAG + prompt combination.
- Run 10 showed the gap grew from +0.25 (unfair) to +5.31 (fair) — i.e.
  we had been *underestimating* OrientIA's contribution all along.

---

## ADR-008 — MMR post-rerank with λ=0.7 default (2026-04-15, Phase F.3.a)

**Context.** Run 10 analysis showed `diversite_geo` failing : top-5
retrievals were often 3+ near-duplicate Paris-EFREI fiches.

**Decision.** Add Maximal Marginal Relevance as a post-rerank selection
step with default `λ=0.7` (moderate balance leaning toward relevance).

**Rationale.**
- MMR is the standard IR technique for this exact problem (Carbonell &
  Goldstein 1998), well-understood and auditable.
- λ=0.7 keeps relevance primary — we don't want to surface irrelevant
  fiches for the sake of diversity. Per-intent `intent_to_config()` can
  override to more aggressive (0.3-0.4) for decouverte / geographic.
- Embeddings already in FAISS → reconstructing them via
  `index.reconstruct()` is free (no extra Mistral API calls).

**Alternatives.**
- Structural diversity (filter by distinct `ville`) : rejected —
  less principled, doesn't generalise.
- Embedding-based clustering : rejected on complexity.
- Do nothing and trust the reranker : rejected — the failure mode is
  real and empirically measured.

---

## ADR-009 — Rule-based intent classifier, not LLM (2026-04-15, Phase F.3.b)

**Context.** Different question types benefit from different retrieval
strategies. Need a way to classify each question before retrieval.

**Decision.** Rule-based classifier (regex + keyword lists + closed-set
city/region match) mapping French questions to 7 intents.

**Rationale.**
- **Deterministic**. Same question → same intent. Critical for
  reproducibility and paper defensibility.
- **Zero API cost**. LLM classifier would add 100 calls per benchmark
  run, inflating OpenAI tier-1 rate-limit pressure.
- **Auditable**. We can show the exact regex patterns in the paper
  appendix. No "trust the model".
- **Fast to iterate**. Test-driven : add a failing case, extend the
  regex, move on.

**Alternatives.**
- Zero-shot LLM classifier (mistral-small) : rejected on cost + non-
  determinism.
- Fine-tuned French BERT classifier : rejected — overkill for 7 classes
  with clear surface patterns.

---

## ADR-010 — Skip manual label expansion (F.3.c) (2026-04-15)

**Context.** Original Phase F plan included F.3.c : expand
`data/manual_labels.json` from 21 → ~50 entries (add CTI / CGE / Grade
Master systematically).

**Decision.** **Skip F.3.c** as planned. Do not expand labels manually.

**Rationale.**
- The target "21 → 50" is negligible vs the 443 total fiches. Even
  hitting 50 would keep coverage at 11% of the knowledge base — the
  label boost multiplicative effect would still be diluted.
- For a *systemic* neutralité gain, we'd need 200+ labels (cross-
  referencing CTI's official 210-school list, CGE's 242, Grade Master's
  600+). That's a multi-day task not fitting Phase F's 3-day window.
- Run 10 already showed `neutralite` as a strength, not a weakness.
  Investing F.3 effort in MMR + intent (which target the actual
  weaknesses : diversite_geo, comparaison) has higher expected gain.
- Deferred option F.3.c-pro (proper 200+ label expansion) remains on
  the table post-Run F if empirical data shows a neutralité gap.

**Alternatives considered.** Do F.3.c half-heartedly : rejected on
principle — half work hurts credibility more than no work.

---

## ADR-011 — Multi-judge (Claude Sonnet + GPT-4o) instead of single judge (2026-04-15, Phase F.4)

**Context.** Runs 1-10 used Claude Sonnet 4.5 as the sole judge. A
reviewer could rightly say : "single-judge bias undetectable".

**Decision.** Use 2 judges in parallel for Run F : Claude Sonnet 4.5
and GPT-4o. Run G will add Claude Haiku as a 3rd judge (cheap, enabling
fact-check).

**Rationale.**
- Inter-judge agreement (Cohen's κ) measures methodological robustness.
  If κ ≥ 0.6 (substantial), we can defend the LLM-as-judge approach.
- Two vendors (Anthropic + OpenAI) reduces shared-bias risk.
- The shared JUDGE_PROMPT is byte-identical across judges — any
  disagreement is attributable to the model, not the instruction.

**Alternatives.**
- Stick with single judge : rejected on reviewer pushback risk.
- Three judges from the start : rejected on cost + coordination ; scale
  up progressively (2 → 3 at Run G once infrastructure proven).

---

## ADR-012 — 12 RPM OpenAI rate limiter instead of upgrading tier (2026-04-15, Phase F.4)

**Context.** First Run F attempt was running at 5 min/question due to
OpenAI tier-1 caps (15 RPM for gpt-4o). Exponential backoff from
parallel 429s turned a 30-min run into 8h.

**Decision.** Ship a thread-safe rate limiter capping combined OpenAI
rate at 12 RPM. Do NOT upgrade OpenAI tier.

**Rationale.**
- **Zero quality compromise**. Same models, same prompts, same matrix.
  Only orchestration changed.
- **Tier upgrade is slow** : requires $50 cumulative spend + 7 days
  (policy), not activable on-demand.
- **12 RPM = 60/12 = 5s gap with 20% safety margin** below the 15 RPM
  cap. Empirical : zero 429 after deploy.
- **Wall-time drops 8h → ~1h** (Mistral + Anthropic stay unthrottled).

**Alternatives.**
- Drop to 1 OpenAI baseline : rejected — breaks the 7-system matrix.
- gpt-4o-mini on one baseline : rejected — breaks cross-vendor
  consistency.
- Batch API (50% cheaper, 24h delay) : rejected — breaks iteration loop.

---

## ADR-013 — Progressive Run F : 1 run first, then decide variance runs (2026-04-15)

**Context.** Phase F plan called for 3 runs × 7 systems × 100 questions
for variance measurement (~$35). Without seeing intermediate results,
this is a big commit.

**Decision.** Run a single full F pass first (~$15-20), checkpoint with
Matteo, then decide whether to commit to 2 additional runs ($25-30 more)
based on signal strength.

**Rationale.**
- **Risk mitigation** : if our_rag ≤ mistral_v3_2_no_rag on Run 1,
  variance runs won't change the story. Save budget for debugging.
- **Fast feedback loop** : 1h vs 3h wall-time per decision cycle.
- **Budget discipline** : aligns with "ZERO intermediate benchmarks"
  rule — Run F-1 is itself the "result", not an intermediate.

**Alternatives.** Commit all 3 runs upfront : rejected on risk.

---

## Pending decisions (to be logged when made)

- ADR-014 : Whether to run F variance runs (×2 more) — pending Run F-1 results.
- ADR-015 : Whether to add Voyage embeddings as hybrid retrieval — post-Run F.
- ADR-016 : Final study report format (markdown only vs markdown + PDF) — Week 3.
- ADR-017 : Demo UI stack (FastAPI + React vs Next.js) — optional, Week 3.
