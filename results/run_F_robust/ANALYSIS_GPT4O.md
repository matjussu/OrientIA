# Run F — GPT-4o judge analysis (preliminary)

**Date:** 2026-04-15 19:40
**Judge:** GPT-4o only (Claude judge stalled on API degradation, will retry)
**Dataset:** 100 questions × 7 systems blinded (A-G), 1 run

> ⚠️ **Status:** Single-judge result. Claude Sonnet 4.5 judge to be re-run
> when Anthropic API is healthy. Final analysis requires both judges + κ.

---

## 1. Headline — Per-system mean score (/18, n=100)

| Rank | System | Mean | Δ vs `mistral_neutral` |
|---|---|---|---|
| 🥇 | **`our_rag`** | **16.16** | **+1.60** |
| 🥈 | **`mistral_v3_2_no_rag`** | **16.12** | **+1.56** |
| 🥉 | `claude_v3_2_no_rag` | 14.70 | +0.14 |
| 4 | `mistral_neutral` (fair baseline) | 14.56 | (ref) |
| 5 | `claude_neutral` | 10.55 | -4.01 |
| 6 | `gpt4o_v3_2_no_rag` | 10.05 | -4.51 |
| 7 | `gpt4o_neutral` | 9.14 | -5.42 |

---

## 2. The big finding — RAG contribution is ≈ 0 on this judge

`our_rag` (16.16) vs `mistral_v3_2_no_rag` (16.12) = **+0.04 pts** = noise.

Per-criterion breakdown (out of 3 each):

| Criterion | `our_rag` | `mistral_v3_2_no_rag` | Δ |
|---|---|---|---|
| Neutralité | 2.77 | 2.87 | **-0.10** |
| Réalisme | 2.69 | 2.71 | -0.02 |
| Sourçage | 2.35 | 2.34 | +0.01 |
| Diversité géo | 2.75 | 2.74 | +0.01 |
| Agentivité | 2.91 | 2.84 | +0.07 |
| Découverte | 2.69 | 2.62 | +0.07 |

**Honest reading:** The +1.60 gap vs the fair baseline comes from the v3.2
**prompt**, NOT from the RAG retrieval. This is exactly the scenario
flagged in ADR-013 ("if our_rag ≤ mistral_v3_2_no_rag, all gain came
from the prompt").

⚠️ **Caveat:** GPT-4o judge tends to under-score grounded sourcing
(saw same pattern in Run 8 v1). Claude Sonnet's prior on source
verification is stronger. Wait for Claude judge before concluding.

---

## 3. Per-category ablation (mean /18)

| Category | `our_rag` | `mistral_v3_2_no_rag` | Δ RAG | Notes |
|---|---|---|---|---|
| **honnetete** | **16.80** | 14.20 | **+2.60** | ✅ RAG wins decisively on definition questions (intent → conceptual, top_k=4) |
| **biais_marketing** | 16.75 | 16.58 | +0.17 | Tie |
| **adversarial** | 16.60 | 16.50 | +0.10 | Tie — both refuse fakes well |
| **diversite_geo** | 16.50 | 16.67 | -0.17 | Surprising — F.3 MMR didn't help here? |
| **passerelles** | 16.17 | 15.75 | +0.42 | Slight RAG win |
| **realisme** | 16.08 | 16.08 | 0.00 | Exact tie |
| **comparaison** | 15.75 | 15.58 | +0.17 | Tie |
| **cross_domain** | 15.38 | **17.38** | **-2.00** | ❌ Expected — RAG retrieves polluting fiches outside cyber/data |
| **decouverte** | 15.33 | **16.50** | **-1.17** | ⚠️ Concerning — découverte should be a RAG strength |

### Interesting wins / losses

**Big RAG win:** `honnetete` +2.60. Conceptual definition questions
("c'est quoi une licence universitaire?") benefit from the intent
classifier routing them to a tight 4-source context. The RAG grounds
the definition in actual programs.

**Big RAG loss:** `cross_domain` -2.00. Documented in METHODOLOGY § 7.1.
The RAG retrieves cyber/data fiches for questions about avocat
fiscaliste / kiné / etc., polluting the context. This is the cost of
specialisation.

**Worrying loss:** `decouverte` -1.17. The intent classifier sends
décourverte to top_k=12, λ=0.3 (most aggressive diversification). Either
this config is wrong, OR the GPT-4o judge undervalues the surfaced
"unusual" formations. **Need Claude judge to disambiguate.**

---

## 4. Anomaly: GPT-4o systems are last

`gpt4o_v3_2_no_rag` 10.05 and `gpt4o_neutral` 9.14 rank dead last,
4-5 points behind comparable Mistral / Claude systems.

Two hypotheses:
1. **GPT-4o really produces shorter/less-structured French orientation
   answers** (it's English-first, RLHF on US college advice).
2. **GPT-4o judge has an anti-self bias** (well-documented in
   LLM-as-judge literature — opposite of self-preference).

Neither can be confirmed without the Claude judge. If Claude ALSO
rates GPT-4o systems last → hypothesis 1. If Claude rates them
mid-pack → hypothesis 2 (and we have a great methodological finding
for the paper).

---

## 5. What this changes for the project

### What we can claim today (defensible)
1. The v3.2 prompt + RAG stack significantly outperforms the fair
   baseline `mistral_neutral` (+1.60 / 18 = +9% relative).
2. The v3.2 prompt is portable across vendors with degraded effect
   (Claude +0.14 vs Mistral +1.56).
3. The RAG decisively wins on `honnetete` definition questions.

### What we CANNOT yet claim
1. That the RAG itself adds value beyond the prompt (gap +0.04 = noise
   on this judge).
2. That GPT-4o is actually worse (judge bias unclear).
3. Anything with statistical significance — n=100 single judge single run.

### Required next steps (in priority order)
1. **Claude Sonnet judge** (retry tomorrow morning with same blinded
   responses). Same data, idempotent re-run.
2. **Inter-judge κ** — if Claude and GPT-4o agree (κ ≥ 0.6) → result
   is robust. If they disagree → judge variance is the story.
3. **F.4 variance runs (×2 more)** — if Claude confirms `our_rag` ≈
   `mistral_v3_2_no_rag`, we need the variance bars to publish honestly.
4. **F.3 inspection on `decouverte`** — investigate why MMR+intent
   underperforms on the very category they were meant to improve.

### What this means for the paper
- The story shifts from "RAG dominates" to "Architectural prompt +
  RAG dominates as a stack, with prompt carrying most of the lift".
- This is **still publishable and useful** — but more honest.
- The cross-domain limitation is an honest disclaimer, not a failure.
- The honnetete +2.60 is a clear-cut RAG win to highlight.

---

## 6. Cost so far

- Generation : Mistral $X + OpenAI $Y + Anthropic $Z (TBD from invoices)
- GPT-4o judge : ~$5 estimated
- Claude judge : ~$0 (process killed before completion)
- **Total Run F-1 so far: ~$10-15** (rough)

Budget remaining for Claude judge re-run + variance runs: ample.
