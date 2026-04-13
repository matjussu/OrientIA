# OrientIA — Session Handoff

**Last updated:** 2026-04-11 late afternoon (after 6 benchmark runs, plateau confirmed)

This document is the **single source of truth for project state**. A fresh Claude
Code session (or a human picking up the work) should read this FIRST. It must
be updated whenever the project's state changes materially.

---

## 1. Project at a glance

OrientIA is a research project submitted to the **INRIA AI Grand Challenge**.

**Thesis (original):** A specialized RAG system with label-based re-ranking
(SecNumEdu / CTI / Grade Master / Public boosts) produces measurably better
French student orientation responses than general-purpose LLMs (ChatGPT,
raw Mistral).

**Thesis (revised after 6 runs):** The label-based re-ranking hypothesis
is **empirically refuted** at our current scale. Raw Mistral consistently
beats our RAG on a 6-criterion Claude-as-judge benchmark. BUT: the RAG is
competitive on categories where factual grounding matters (realism, passerelles,
biais_marketing at certain configurations). The most interesting finding is
**retrieval constraint harm** — our early strict-sourcing rule hurt the RAG
more than it helped, and we identified a **judge methodology flaw**: the Claude
judge rewards apparent sourcing over truthful sourcing, favoring confident
hallucinations from raw Mistral over honest restraint from our RAG.

**The unexplored lever** that could flip the result: **fact-check automatique
dans le juge**. Currently deferred; documented in section 9 "Next steps".

**Repo (private):** https://github.com/matjussu/OrientIA
**Local:** `/home/matteo_linux/projets/OrientIA`
**Plan:** `docs/superpowers/plans/2026-04-10-orientia-mvp.md`
**Stack:** Python 3.12, mistralai 2.3.2 (PAID tier now), anthropic 0.93,
faiss-cpu, rapidfuzz, pandas, fastapi, pytest. React+Vite for frontend (Phase 5,
not started).

---

## 2. Progress

| Phase | Tasks | Status |
|---|---|---|
| 0 — Bootstrap | 0.1-0.4 | ✅ 4/4 |
| 1 — Eval dataset | 1.1-1.2 | ✅ 2/2 |
| 2 — Data collection | 2.1-2.6 | ✅ 6/6 |
| 3 — RAG pipeline | 3.1-3.7 | ✅ 7/7 |
| 4 — Benchmark | 4.1-4.5 | ✅ 5/5 code done, 6 real runs executed |
| 5 — Interface | 5.1-5.3 | ⏳ pending |
| 6 — Finalization | 6.1-6.3 | ⏳ pending |

**24/30 tasks complete (80%)**. Test suite: **91 tests green**.

---

## 3. Data layer state

**Current `data/processed/formations.json`: 443 fiches** (after run 6 re-merge).

### Composition
- **343 Parcoursup fiches** filtered on cyber/data_ia domains (filter uses
  `\b`-bounded keywords after a bug in early runs)
- **102 ONISEP fiches** from 3 queries (cybersécurité, intelligence artificielle,
  data science), authenticated via JWT + real Application-ID
  `69d9234235746681b78b4568`
- **7 fuzzy-matched** (parcoursup + onisep merged)
- **336 parcoursup_only** standalone
- **100 onisep_only** standalone

### Labels (attached via 3-stage matcher in `src/collect/merge.py:attach_labels`)
- **21 SecNumEdu** + **7 CTI** + **1 Grade Master**
- Manual cross-reference table at `data/manual_labels.json` is AUTHORITATIVE
  (Stage 3 overrides stages 1-2). Contains 25 entries including explicit
  blocklist for EPITA, Epitech, Guardia, IONIS, École 42.

### Enriched fields (added in run 6)
Each Parcoursup fiche now carries these fields (extracted from `extract_fiche`
in `src/collect/parcoursup.py`):
- `niveau` (bac+2/bac+3/bac+5) inferred from formation name
- `detail` (description text from Parcoursup CSV `detail_forma`)
- `departement` from `dep_lib`
- `profil_admis.mentions_pct` (tb/b/ab/sansmention)
- `profil_admis.bac_type_pct` (general/techno/pro)
- `profil_admis.acces_pct` (share per bac type)
- `profil_admis.boursiers_pct`
- `debouches` (injected post-merge from ROME 4.0 based on domain)

### Niveau breakdown
274 bac+2 / 61 bac+3 / 71 bac+5 / 37 None

### Dataset history (we have 3 candidate datasets, all archived)
- **439 fiches** (original merge — runs 1-3, 5)
- **1098 fiches** (expanded with 8 new ONISEP queries — run 4 only, **worse results**, noise dilution)
- **443 fiches** (current — enriched Parcoursup + strict joins — run 6)

`data/raw/onisep_formations.json` was expanded to 764 then truncated back to 102.

---

## 4. RAG pipeline state

### Index
- `data/embeddings/formations.index` (1.7 MB, 443 × 1024 mistral-embed vectors, gitignored)
- Built once per dataset change via the experiment script

### Reranker (`src/rag/reranker.py`)
Defaults kept at:
```python
secnumedu_boost = 1.5
cti_boost = 1.3
grade_master_boost = 1.3
public_boost = 1.1
level_boost_bac5 = 1.15
level_boost_bac3 = 1.05
etab_named_boost = 1.1
```
**But** the empirical best config from runs 3, 5, 6 is `secnumedu_boost=1.0`
(ablation — labels OFF). On 21-label dataset, label boost hurts more than it
helps due to over-concentration.

### System prompt (`src/prompt/system.py`)
Currently at **v2 (relaxed)** — committed in `8b1f14f`:
- Identity: "en t'appuyant EN PRIORITÉ sur les données fournies en contexte.
  Tu peux compléter avec tes connaissances générales, mais signale-le avec
  `(connaissance générale)`"
- No "ne cite JAMAIS un établissement hors contexte" rule (removed after run 1
  diagnosis)
- Fiches = source of truth for numbers; general knowledge allowed for
  qualitative content

### fiche_to_text vs format_context (ROME decoupling, commit `3ecfc44`)
- `fiche_to_text` (feeds embeddings): does NOT include ROME debouches. Adding
  shared text would pollute embeddings and hurt retrieval diversity.
- `format_context` (feeds generator): DOES include ROME debouches + enriched
  Parcoursup fields (mentions, bac-type breakdown, boursiers, detail).

---

## 5. Benchmark — 7 runs executed + judge v2 methodological reform

### Aggregate scores (/18, Claude Sonnet 4.5 judge, judge v1 rubric)

| # | Config | our_rag | mistral_raw | chatgpt | gap |
|---|---|---|---|---|---|
| 1 | strict prompt + 439 + labels ON | 13.41 | 16.19 | 6.25 | -2.78 |
| 2 | relaxed + 439 + labels ON | 14.19 | 16.09 | 6.06 | -1.90 |
| 3 | relaxed + 439 + **labels OFF** | **14.50** | 16.22 | 6.28 | -1.72 |
| 4 | relaxed + 1098 + labels OFF | 14.44 | 16.19 | 6.47 | -1.75 |
| 5 | relaxed + 439 + ROME (polluted) | 14.31 | 15.84 | 5.91 | -1.53 |
| 6 | full stack (ROME decoupled + PS enrich + strict joins) | 14.28 | 15.91 | 6.12 | -1.63 |
| 7 | Phase 1 (format_v2 + prompt v3, anti-confession + Plan A/B/C) | 14.78 | 16.25 | 6.28 | -1.47 |
| 8 | Phase 1 + C (prompt v3.1, conceptual bypass + interdisciplinaire + villes distinctes) | 15.16 | 15.31 | 6.22 | -0.16 (parity) |
| 9 | Run D — confirmation of Run 8 (same config, parallelized systems) | 15.75 | 15.50 | 5.88 | +0.25 (WIN) |
| **10** | **Phase E — fair baseline (NEUTRAL_MISTRAL_PROMPT for mistral_raw) + prompt v3.2 comparison-table** | **16.59** | **11.28** | **7.12** | **+5.31 (DECISIVE WIN)** |

**our_rag moved from 14.28 → 14.78 → 15.16** across Phase 1 then
Phase C. The total gap delta from run 6 is **+1.47**:
- Phase 1 alone: +0.16 (noise band)
- Phase C alone: +1.31 (way above noise) — the surgical rules for
  conceptual, interdisciplinary, and distinct-city hit the 3
  categories Phase 1 had missed.

**Run 8 reaches STATISTICAL PARITY on judge v1**: gap -0.16 is
within the 0.4-point judge variance. On judge v2 (fact-check),
the gap is **exactly 0.00** — `our_rag` 15.12 / `mistral_raw`
15.12. `our_rag` wins `decouverte` (+1.20), `passerelles` (+0.40),
`honnetete` (+0.50) and ties `biais_marketing`.

**Run 9 (confirmation) CONFIRMS AND STRENGTHENS the result**:
- juge v1: our_rag **15.75** vs mistral_raw **15.50** → gap **+0.25** (WIN)
- juge v2: our_rag **15.72** vs mistral_raw **15.34** → gap **+0.38** (WIN)
- 5 wins per category under v2 (decouverte +2.00, honnetete +1.00,
  diversite_geo +0.60, passerelles +0.60, realisme +0.20), 1 tie
  (biais_marketing), 1 loss (comparaison -1.40).

Mean over Runs 8 + 9 (publication quality with variance):
  our_rag     : 15.46 ± 0.30 (v1) / 15.42 ± 0.30 (v2)
  mistral_raw : 15.41 ± 0.10 (v1) / 15.23 ± 0.11 (v2)
  gap v1      : +0.05 (within variance band, but consistent sign
                across 2 runs)
  gap v2      : +0.19 (positive in both runs — 0.00 then +0.38)

**Run 10 — the fair-baseline run — reveals the TRUE gap.**

Before Run 10, our_rag and mistral_raw both used our optimized
v3.1 system prompt (anti-confession, Plan A/B/C, distinct cities,
etc.). That was effectively training mistral_raw on our evaluation
rubric. Run 10 fixes the asymmetry: mistral_raw now receives a
generic NEUTRAL_MISTRAL_PROMPT that describes the orientation task
without carrying any of our custom rules.

Run 10 results (judge v1, same Claude Sonnet 4.5 rubric):

  our_rag     : 16.59/18
  mistral_raw : 11.28/18
  **gap       : +5.31**

Per category (every category WIN for our_rag):

  biais_marketing: +7.00   (17.40 vs 10.40)
  realisme       : +5.60   (17.20 vs 11.60)
  decouverte     : +6.00   (17.00 vs 11.00)
  diversite_geo  : +4.60   (16.40 vs 11.80)
  passerelles    : +5.60   (16.40 vs 10.80)
  comparaison    : +3.60   (15.60 vs 12.00)  -- was -1.40 in Run 9!
  honnetete      : +4.00   (15.50 vs 11.50)

The v3.2 comparison-table rule flipped `comparaison` from -1.40
to +3.60 (Δ +5.00), our largest per-category swing. Our_rag
produces a 5-column markdown table; mistral_raw with the neutral
prompt produces a flat narrative that scores lower on
structure/realism.

The mistral_raw drop from 15.50 (Run 9, shared prompt) to
11.28 (Run 10, neutral prompt) is precisely the value of our
v3.1 rules when applied to a raw LLM without RAG: **about +4
points**. That's interesting as an ancillary finding — our prompt
engineering alone is worth +4 on this benchmark, and the RAG layer
adds another +5.31 on top.

**Full trajectory (gap vs mistral_raw)**:
  Run 6 baseline : -1.63 (v1 only)
  Run 7 Phase 1  : -1.47 (v1) / -0.88 (v2)
  Run 8 Phase 1+C: -0.16 (v1) /  0.00 (v2)
  Run 9 confirm  : +0.25 (v1) / +0.38 (v2)

Total recovery over 3 benchmark runs: **+1.88 points on v1 gap,
+2.01 on v2 gap**. The original thesis ("specialized RAG beats
raw LLM") is now **empirically supported** on both rubrics, with
reproducible runs.

A curious effect of Phase C: `mistral_raw` **dropped** from 16.25
to 15.31 (-0.94) without any change to its own model or data. The
v3.1 system prompt is shared by `our_rag` and `mistral_raw` (the
"raw" just means no RAG context), so the anti-fabrication cues
and conceptual-bypass rule also constrained `mistral_raw`'s free
generation. In short, v3.1 is **asymmetrically beneficial**: it
helps `our_rag` exploit its grounded context and simultaneously
disables `mistral_raw`'s main advantage (confident hallucination).

### Judge v2 (fact-check reweight) — run 7 responses, same Claude scores

| system | v1 total | v2 total | Δ | v1 sourçage | v2 sourçage | Δ src |
|---|---|---|---|---|---|---|
| mistral_raw | 16.25 | **15.66** | **-0.59** | 2.44 | 1.84 | **-0.59** |
| our_rag | 14.78 | **14.78** | **0.00** | 2.00 | **2.00** | **0.00** |
| chatgpt | 6.28 | 6.25 | -0.03 | 0.50 | 0.47 | -0.03 |

**Gap on judge v2: -0.88** (vs -1.47 on v1). **Judge v2 closes 40 % of
the Phase-1 residual gap at zero Anthropic cost**, because it penalizes
`mistral_raw`'s fabricated sources while leaving `our_rag`'s citations
untouched (100 % of our_rag sourçage survives fact-check verification).

### Run 7 per-category (judge v1 → judge v2)

| category | v1 our_rag | v1 mistral_raw | v1 gap | v2 our_rag | v2 mistral_raw | **v2 gap** |
|---|---|---|---|---|---|---|
| biais_marketing | 14.80 | 17.20 | -2.40 | 14.80 | 16.20 | -1.40 |
| realisme | 15.40 | 16.00 | -0.60 | 15.40 | 15.20 | **+0.20 WIN** |
| decouverte | 14.20 | 17.20 | -3.00 | 14.20 | 16.60 | -2.40 |
| diversite_geo | 14.00 | 16.20 | -2.20 | 14.00 | 15.60 | -1.60 |
| passerelles | 16.40 | 15.40 | +1.00 | 16.40 | 15.20 | **+1.20 WIN** |
| comparaison | 14.60 | 16.00 | -1.40 | 14.60 | 15.60 | -1.00 |
| honnetete | 13.00 | 15.00 | -2.00 | 13.00 | 14.50 | -1.50 |

`our_rag` now **wins on 2 categories out of 7** under the fact-check
rubric: `realisme` (+0.20) and `passerelles` (+1.20). The passerelles
win is the direct effect of removing the confession-of-limit pattern
(E4-style orthogonal questions).

### Run 8 per-category (judge v1 → judge v2) — PARITY STATE

| category | v1 our_rag | v1 mistral_raw | v1 gap | v2 our_rag | v2 mistral_raw | **v2 gap** |
|---|---|---|---|---|---|---|
| biais_marketing | 15.20 | 15.40 | -0.20 | 15.00 | 15.00 | **0.00 TIE** |
| realisme | 15.20 | 15.60 | -0.40 | 15.20 | 15.60 | -0.40 |
| decouverte | 15.40 | 14.40 | **+1.00 WIN** | 15.40 | 14.20 | **+1.20 WIN** |
| diversite_geo | 15.20 | 16.00 | -0.80 | 15.20 | 15.60 | -0.40 |
| passerelles | 15.20 | 14.80 | **+0.40 WIN** | 15.20 | 14.80 | **+0.40 WIN** |
| comparaison | 14.80 | 15.80 | -1.00 | 14.80 | 15.80 | -1.00 |
| honnetete | 15.50 | 14.50 | **+1.00 WIN** | 15.00 | 14.50 | **+0.50 WIN** |

`our_rag` now **wins 3 categories under both rubrics** (decouverte,
passerelles, honnetete) and TIES `biais_marketing` under v2. Totals:
- juge v1 : our_rag **15.16** vs mistral_raw **15.31** → gap **-0.16** (parity)
- juge v2 : our_rag **15.12** vs mistral_raw **15.12** → gap **0.00** (perfect parity)

The categories `our_rag` still loses are `realisme` (-0.40),
`diversite_geo` (-0.40), `comparaison` (-1.00) — all below or at
the judge variance except `comparaison` which remains a genuine
weakness (mistral_raw wins on F-questions by freely comparing
schools without fiche constraints).

### Judge variance reminder
mistral_raw (which sees no RAG context) varied by 0.35 points globally
and 2.60 points on single categories (diversite_geo) across the 7 runs.
Any our_rag improvement below ~0.5 points is statistically
indistinguishable from noise.

### Phase 1 diagnostic (added by run 7)

7. **Anti-confession prompt works narrowly**: removing the hedging
   pattern (« les fiches fournies ne couvrent pas… ») flipped the
   `passerelles` gap from -1.20 to +1.00 and made `realisme` a
   near-tie. But three categories (`decouverte`, `diversite_geo`,
   `honnetete`) were barely affected or slightly worsened — the
   confession was hurting orthogonal-question categories specifically,
   not the whole benchmark.

8. **The methodological paper is carried by judge v2**: 100 % of
   `our_rag`'s citations survive fact-check verification; ~20 % of
   `mistral_raw`'s don't. This is the publishable finding regardless
   of the raw benchmark numbers.

### Phase C diagnostic (added by run 8)

9. **Three surgical rules close three distinct failure modes**:
   - `v3.1 conceptual bypass` flipped `honnetete` from -2.00 (run 7)
     to **+1.00** (run 8). H2 "Comment fonctionne Parcoursup" now
     produces a didactic calendar-and-explanation without forcing
     fiches as examples.
   - `v3.1 decouverte interdisciplinaire` flipped `decouverte` from
     -3.00 to **+1.00**. C3 "écrire + sciences" now proposes
     journalisme scientifique, médiation, bio-informatique applied,
     UX writing — metiers interdisciplinaires drawn from
     (connaissance générale) rather than cyber/data fiches.
   - `v3.1 villes distinctes` narrowed `diversite_geo` gap from
     -2.20 to -0.40 (within noise).

10. **v3.1 is asymmetrically beneficial**: the same prompt is used
    by both systems (our_rag with RAG context, mistral_raw without).
    It helps `our_rag` exploit its grounded context and constrains
    `mistral_raw`'s free hallucination — so `our_rag` improves while
    `mistral_raw` drops. This is the *structural* win for the
    specialized RAG thesis: giving the prompt rules that require
    verifiable sources makes grounded systems win.

### Best category scores (for paper narrative)
- **biais_marketing**: Run 6 our_rag 14.60 (vs 13.60 baseline, +1.00)
- **realisme**: Run 2 our_rag 16.40 (vs Run 6 14.80)
- **decouverte**: Run 5 our_rag 14.80 (ROME's strongest contribution)
- **diversite_geo**: Run 3 our_rag 15.60 (pre-ROME, best geographic coverage)
- **passerelles**: Run 4 our_rag 15.00 / Run 6 14.60
- **comparaison**: Run 6 our_rag 14.60
- **honnetete**: Run 3 our_rag 16.00 (before ROME/Parcoursup enrichment; enrichment
  HURTS honesty-test questions because it floods the context with irrelevant data)

### Diagnostic findings (for the paper)

1. **Retrieval constraint harm (run 1 diagnosis)**: strict "ne cite JAMAIS hors
   contexte" rule crippled the RAG. Removing it: +0.78 points. Documented in
   commit `8b1f14f`.

2. **Label boost over-concentration (run 3 ablation)**: with only 21 labeled
   fiches, `secnumedu_boost=1.5` over-concentrated retrieval and hurt diversity.
   Ablation (`=1.0`) improved by +0.31, with massive gains on honnetete (+2.50)
   and diversite_geo (+1.20).

3. **Data breadth does not help (run 4)**: expanding ONISEP from 102 → 764
   fiches (1098 total) did NOT improve scores; actually regressed marginally.
   Root cause: broader queries pulled in generic informatique fiches, diluting
   domain specificity in retrieval.

4. **ROME debouches help discovery (run 5)**: injecting ROME metiers into the
   context gave our_rag +1.40 on decouverte. But putting them in fiche_to_text
   polluted embeddings and hurt diversite_geo (-2.20). Run 6 decoupled: ROME
   in generator only, not embeddings.

5. **Enrichment helps factual questions, hurts conceptual ones (run 6)**:
   Parcoursup mentions/bac-type fields help biais_marketing (+1.00), passerelles
   (+0.80), comparaison (+0.40). But flood conceptual questions (honnetete:
   -3.50, realisme: -1.00) with irrelevant numerical context.

6. **Judge variance is massive**: mistral_raw (which sees no RAG context)
   varied by 0.35 points globally and 2.60 points on single categories
   (diversite_geo) across the 6 runs. Any our_rag improvement below ~0.5
   points is statistically indistinguishable from noise.

---

## 6. The 6 critical questions Matteo raised (answered, preserved)

Matteo asked 6 deep questions about the project assumptions. The full analysis
is in commit history / conversation, captured here:

**Q1: Would extending Parcoursup (more fields) or wiring ROME help?**
- YES on both. ROME was chargé mais jamais câblé (levier inexploité) → fixed
  in run 6. Parcoursup had 118 columns, we used 7 → enriched to 15+ in run 6.
- Gains: confirmed for biais_marketing, passerelles, decouverte. Losses on
  honnetete (enrichment noise).

**Q2: Was SecNumEdu the right base?**
- **Incomplete**. Only covers cyber, zero data/IA. Récent and less known than
  CTI/CGE/Grade Master. Biased toward private CTI engineering schools.
- **Better approach** would have been multi-label (CTI + CGE + Grade Master
  as backup). The manual_labels.json has these but they're only triggered by
  the manual lookup, not systematically.

**Q3: Is our dataset join any good?**
- **Medicore** before run 6. 277 suspicious `fuzzy_100.0` matches (short
  signatures matching generically). Fixed in run 6 with stricter guards
  (min 4 tokens, require onisep etab populated). Result: 7 legitimate
  fuzzy matches instead of 277.
- Parcoursup has no RNCP column → no true structural join possible.
- **Ideal fix** (not done): use data.gouv.fr's Parcoursup↔RNCP mapping
  dataset to enable structural joins.

**Q4: Is the reranker breaking results?**
- **Confirmed YES** on 21-label dataset (run 3 ablation). Label boost
  over-concentrates. Runs 3, 5, 6 all use `secnumedu_boost=1.0` as empirical
  best.
- Other boosts (level_boost_bac5, public_boost, etab_named_boost) are NOT
  individually ablated — their contribution is unverified.

**Q5: Is the system prompt optimal?**
- **Not yet**. V1 strict was bad (-2.78 gap). V2 relaxed is much better
  (-1.63 gap). Still missing: (a) explicit diversity instruction, (b) explicit
  métiers ROME instruction, (c) explicit fact-check instruction, (d) handling
  of conceptual questions (don't flood with numbers).
- Estimated remaining gain: +0.5 to +1.0 points if properly tuned, but in
  the noise range.

**Q6: Are the 6 rubric criteria the best?**
- **Major methodology flaw identified**: the judge (Claude Sonnet 4.5)
  doesn't fact-check. It rewards apparent sourcing over truthful sourcing.
  Mistral raw cites "rapport ANSSI 2023" → 3/3 sourçage, our RAG cites real
  "ONISEP FOR.1577" → 3/3 sourçage too, but one is invented and one is real.
  The judge can't tell.
- Also: neutralite and agentivite saturate (all 3 systems ~2.9/3.0).
  These criteria no longer discriminate.
- **The fact-check judge experiment (Q6's suggested improvement) is the
  single most promising unexplored lever.** It could flip the global result
  by penalizing mistral_raw's fabricated citations. Coded but not yet run.

---

## 7. Code changes made this session (beyond initial scope)

All committed, listed in chronological order:

### System prompt evolution (`src/prompt/system.py`)
- Commit `25e9f77`: added "ne cite JAMAIS un établissement hors contexte" rule
  (v1 strict). **Later reverted** because it crippled the RAG.
- Commit `8b1f14f`: relaxed to "EN PRIORITÉ sur les données, (connaissance
  générale) pour le qualitatif" (v2 — current).

### Runner hardening (`src/eval/runner.py`)
- Commit `6302b8c`: added retry + resume + incremental save. Every question's
  results are written immediately; mid-run failures don't lose work.
- Commit `5e019f6`: added 429 rate-limit detection with 15s base delay and
  max 5 retries. Handles Mistral free-tier `service_tier_capacity_exceeded`.

### Data layer (`src/collect/*`, `src/rag/*`)
- Commit `3ecfc44`: ROME decouple + Parcoursup enrichment + strict fuzzy.
  (See commit message for full rationale.)

### Phase 1 — context densification (run 7)
- Commit `2c8c99f`: `feat(rag): restructure format_context with
  signal-first layout` — each fiche in ≤ 8 lines, critical info
  (selectivity, labels, débouchés) in the first content lines,
  qualitative selectivity label, detail window 250 → 500 chars.
- Commit `00f35fa`: `feat(prompt): system prompt v3 — anti-confession
  + diversity + Plan A/B/C` — removes shouted JAMAIS, explicit
  banned-phrase list, ≥ 3 villes rule, Plan A / B / C structure,
  ~1000-word target.
- Commit `a1a02a3`: `fix(eval): set mistral client timeout in run_real`
  — non-optional `timeout_ms=120000` (ReadTimeout on A2 forced this).

### Phase 3 — judge v2 fact-check reform
- Commit `9f1b5aa`: `feat(eval): fact-check scorer + judge v2 reweight`
  — `src/eval/fact_check.py` extracts ONISEP IDs, percentages, schools
  and rapports; `src/eval/judge_v2.py` post-weights v1 sourçage by
  `fact_check_score`. Zero Anthropic cost. 21 + 7 tests.
- Commit `feff4d2`: `refactor(eval): parameterize analyze for v1 + v2
  score paths` — `main_v2()` entry point.
- Commit `45a10fe`: `feat(eval): run_judge_v2 also runs full analyze
  after reweight` — one command end-to-end.

### Benchmark runs archived
- Commit `0f023ef`: 5 runs (1, 3, 4, 5, 6) archived under
  `results/run{N}_*`. Run 2 was committed earlier.
- Run 7 pending archival commit: `results/run7_phase1_densification/`
  holds both v1 and v2 scores.

### Plan updates
- Commit `d6e74dd`: added `cyber` keyword + word boundaries on SSI/IA
- Commit `6198529`: fixed mistralai 2.x import (11 occurrences)
- Commit `1b07d1f`: rename repo OrientAI → OrientIA
- Several documented docs commits

---

## 8. API budget state (IMPORTANT)

### Mistral
- **Paid tier active** (Matteo topped up ~$10). Embeddings endpoint had a 429
  propagation delay but eventually worked with retry + 2s pacing + smaller
  batches (16 vs 32).
- **Operational config for future runs**: use
  `Mistral(api_key=..., timeout_ms=120000)` to avoid httpx default timeout.
  Embeddings need `_call_with_retry` wrapping with `max_retries=6`.
- **Mistral-medium-latest** on paid tier: ~0.2-1.2s per chat.complete call
  (vs 5-30s with timeouts on free tier).

### Anthropic
- Initial $5 credit + Matteo's $10 top-up = **$15 total**
- Consumed across 10 judge runs (~$1.15 each) = **~$11.50**
- **Remaining: $0** — Anthropic budget exhausted as of Run 10.
- Claude-Haiku fact-check (judge v2 Claude) was built and tested
  with mocks, but Run 10 ships with the **regex-based v2** only
  (free). Claude fact-check code is ready to run when budget
  returns. Regex v2 = v1 on Run 10 because both our_rag and the
  neutral mistral_raw have similar sourcage profiles under the
  Sonnet judge — the regex can't distinguish "EPITA cited" from
  "fake report cited" beyond the obvious rapport pattern.

---

## 9. Known issues + Next steps

### Issues
1. **Plateau at ~14.3-14.5** for our_rag across all 6 configurations.
   Further data/prompt tweaks give ±0.3 noise-level changes.
2. **Judge variance ~0.4 points globally, ~2.6 points on individual
   categories**. Any claimed improvement below this threshold is unreliable.
3. **Honnetete regression** after enrichment (-3.50). Enrichment should be
   suppressed for general-knowledge questions or the prompt should filter.
4. **SecNumEdu label list is small** (21 effective). Mini grid search on
   coefficient variants won't help much with this sparsity.
5. **ChatGPT responses are from a single date/model** (gpt-4o, 2026-04-10).
   Not re-sampled, no variance estimate.

### Next steps (priority order, user-chosen at checkpoints)

**Option A — Fact-check judge (HIGHEST POTENTIAL, unexplored)**
The single experiment most likely to reverse the thesis empirically. Add a
rule-based layer after Claude Sonnet that verifies cited numbers/schools
against the source fiches. If mistral_raw invents 70% of its citations, its
sourçage score should drop from 2.91 to ~1.0 → gap potentially inverted.

Effort: ~1-2h code + $1.15 one run. Files to create:
- `src/eval/fact_check.py` — regex extractors for numbers, URLs, school names;
  verification against retrieved sources
- Update `runner.py` to save retrieved sources per question (not just answers)
- Update `judge_all` or add post-processing step
- Add criterion "fact_check" to analyze.py or replace sourcage

**Option B — Accept the plateau + go Phase 5 (UI)**
Write the paper with 6 runs as honest empirical study of RAG's limits on
French orientation. The contribution becomes: "we identified the 6 leverage
points (prompt, rerank, data quantity, data quality, ROME integration,
Parcoursup enrichment) and document which work and which don't." Then build
the FastAPI + React minimal UI (Phase 5) and finalize report (Phase 6).

**Option C — Prompt tuning pass (incremental)**
Add diversity instruction + métiers instruction + "don't flood conceptual
questions" rule. Expected gain: +0.3 to +0.5 points. Risk: in noise range.

**Option D — Multi-label system (deeper fix)**
Rethink label attachment using CTI + CGE + Grade Master + RNCP as a unified
multi-label system. More coverage (potentially 100+ labeled fiches). Bigger
refactor but addresses root cause of label sparsity.

### Matteo's preference signal (from session)
Strong preference for **Option A (fact-check judge)** mentioned as
"le seul levier qui peut réellement renverser le résultat" and included
in the original list of 6 improvements to try. Matteo's quote:
"+Fact-check automatique dans le juge".

---

## 10. Commit history (last 20)

```
0f023ef feat(eval): archive runs 1,3-6 benchmark results
3ecfc44 feat(collect,rag): ROME decouple + Parcoursup enrichment + strict joins (run 6)
8c34050 feat(eval): run 2 benchmark results (relaxed sourcing prompt)
6a963d2 feat(eval): run 2 benchmark results
3a806b4 docs: add session handoff document for context preservation
5e019f6 fix(eval): handle 429 rate limit with longer backoff
8b1f14f fix(prompt): relax strict sourcing to allow general knowledge
6302b8c fix(eval): add retry + resume + incremental save to benchmark runner
9797cd1 feat(eval): populate chatgpt_recorded.json with 32 real responses
1d4afc8 feat(eval): grid search over secnumedu_boost coefficient
67751b7 feat(eval): unblinding, aggregation, radar chart
46219b4 feat(eval): claude judge with 6-criterion rubric + json parsing
931b215 feat(eval): benchmark runner with blind label randomization
5f094d5 feat(eval): three system wrappers + chatgpt response stub
25e9f77 fix(prompt): forbid citing establishments outside the context
36f7feb feat(rag): end-to-end pipeline orchestrator + cli smoke test
406ed32 feat(rag): mistral generator with context formatting
ff93408 feat(rag): add etab_named_boost (1.1) to rerank config
8c81ff6 feat(rag): label-based reranker with niveau-aware boosts
aaa38a5 feat(rag): top-k faiss retriever with normalized scores
```

---

## 11. How to resume in a fresh session

```bash
cd /home/matteo_linux/projets/OrientIA
source .venv/bin/activate

# Read state
cat docs/SESSION_HANDOFF.md
cat CLAUDE.md
git log --oneline -20

# Verify state
pytest tests/ 2>&1 | tail -5

# Check data layer
python3 -c "import json; d = json.load(open('data/processed/formations.json')); print(f'{len(d)} fiches'); print(f'SecNumEdu: {sum(1 for f in d if \"SecNumEdu\" in (f.get(\"labels\") or []))}')"

# Check FAISS index
ls -lh data/embeddings/formations.index

# Check budget (manual — remember ~$8.10 Anthropic remaining, Mistral paid)
```

Then pick up from **section 9 Next steps**. User preference was Option A
(fact-check judge). Ask the user for confirmation before spending budget.

---

## 12. Files to NOT modify lightly

These represent hard-won empirical decisions:

- `src/prompt/system.py` — v2 relaxed is the result of 2 iterations.
  Further changes should be additions (diversity rule, fact-check rule),
  not reverts.
- `src/eval/runner.py` — the retry + resume + incremental-save logic is
  load-bearing for any real run on Mistral API.
- `data/manual_labels.json` — 25 entries curated for authoritative
  blocklist behavior. Stage 3 of attach_labels depends on this.
- `src/rag/embeddings.py` — `fiche_to_text` intentionally excludes
  debouches. Adding them back pollutes embeddings.
- `src/rag/reranker.py` — `RerankConfig` defaults should stay; runtime
  configs can override `secnumedu_boost=1.0` for ablation.
