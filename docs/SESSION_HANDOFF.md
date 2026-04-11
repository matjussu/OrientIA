# OrientIA — Session Handoff

**Last updated:** 2026-04-11 (end of day, Phase 4 benchmark iteration 2 in progress)

This document captures the full state of the project at a given point so that a
fresh Claude Code session (or a human picking up the work) can resume without
having to replay the prior conversation. It should be updated whenever the
project's state changes materially.

## 1. Project at a glance

OrientIA is a research project submitted to the **INRIA AI Grand Challenge**.
Thesis: a specialized RAG system with label-based re-ranking (SecNumEdu / CTI /
Grade Master / Public boosts) produces measurably better French student
orientation responses than general-purpose LLMs (ChatGPT, raw Mistral).

- **Repo (private):** https://github.com/matjussu/OrientIA
- **Local:** `/home/matteo_linux/projets/OrientIA`
- **Plan:** `docs/superpowers/plans/2026-04-10-orientia-mvp.md`
- **Stack:** Python 3.12, mistralai 2.3.2, anthropic 0.93, faiss-cpu, rapidfuzz,
  fastapi, pytest. React+Vite for the frontend (Phase 5, not started).

## 2. Progress

| Phase | Tasks | Status |
|---|---|---|
| 0 — Bootstrap | 0.1, 0.2, 0.3, 0.4 | ✅ 4/4 |
| 1 — Eval dataset | 1.1, 1.2 | ✅ 2/2 |
| 2 — Data collection | 2.1 – 2.6 | ✅ 6/6 |
| 3 — RAG pipeline | 3.1 – 3.7 | ✅ 7/7 |
| 4 — Benchmark | 4.1 – 4.5 | 🟡 code done + run 2 in progress |
| 5 — Interface | 5.1, 5.2, 5.3 | ⏳ pending |
| 6 — Finalization | 6.1, 6.2, 6.3 | ⏳ pending |

**24/30 tasks complete (80%)**. Test suite: **91 tests green**.

## 3. Data layer output

Located at `data/processed/formations.json` (152 KB, committed).

- **439 fiches total**
  - 343 from Parcoursup (cyber + data/IA domain filter on `lib_for_voe_ins` with `\b`-bounded keywords to prevent "SSI" matching "aSSIstant")
  - 96 ONISEP-only (from 102 ONISEP entries, 6 fuzzy-merged with Parcoursup)
  - ~290 bac+2 BTS CIEL dominate because Parcoursup lists them, but higher-ed
    cyber schools (ENSIBS, IMT Atlantique, CentraleSupélec) come from ONISEP.

- **Labels:** 21 SecNumEdu + 7 CTI + 1 Grade Master. Attached via a 3-stage
  matcher in `src/collect/merge.py:attach_labels`:
  1. Full-signature fuzzy match (threshold 85) against the scraped SecNumEdu
     list at `data/raw/secnumedu.json` (111 entries from cyber.gouv.fr).
  2. Establishment-only fuzzy fallback (cyber domain only).
  3. **Manual cross-reference table** at `data/manual_labels.json` (25 entries,
     AUTHORITATIVE — overrides stages 1/2). Entries with empty labels act as a
     blocklist: EPITA, Epitech, Guardia, IONIS, École 42 are explicitly
     unlabeled for benchmark contrast.

- **Niveau field:** inferred from formation name via `src/collect/niveau.py`
  (bac+2 / bac+3 / bac+5 / bac+8 / None). Distribution: 274 / 59 / 69 / 0 / 37.

## 4. RAG pipeline state

### Index
- Pre-built FAISS index at `data/embeddings/formations.index` (439 × 1024
  `mistral-embed` vectors, 1.8 MB, gitignored).
- Built once during a sanity check in Phase 3 → cached → reused by
  `src/rag/cli.py` and `src/eval/run_real.py`.

### Reranker (the "INRIA innovation")
`src/rag/reranker.py:RerankConfig` with 7 boost fields:

```python
secnumedu_boost: float = 1.5        # primary label
cti_boost: float = 1.3              # secondary label
grade_master_boost: float = 1.3     # tertiary label
public_boost: float = 1.1           # public vs private
level_boost_bac5: float = 1.15      # higher-ed over BTS
level_boost_bac3: float = 1.05      # mid tier
etab_named_boost: float = 1.1       # named school vs generic diploma
```

Sanity check on A1 ("meilleures formations cyber") produced a clean top-10
where position 1 is CentraleSupélec-IMT Atlantique [SecNumEdu + CTI + Grade
Master] at score 2.539 (baseline similarity 0.5 compounded by all 4 relevant
boosts × bac+5 × named).

### System prompt (`src/prompt/system.py`)

**Version 2 (run 2)** — relaxed from the strict sourcing rule:

- Identity: "conseiller d'orientation spécialisé dans le système éducatif
  français, en t'appuyant EN PRIORITÉ sur les données fournies en contexte.
  Tu peux compléter avec tes connaissances générales, mais signale-le
  clairement avec « (connaissance générale) »."
- 4 layers: NEUTRALITÉ, RÉALISME, AGENTIVITÉ, SOURÇAGE (now allows hybrid:
  fiches = source of truth for numbers; general knowledge allowed for
  descriptions, advice, geography, passerelles).
- Format: 📍 per-formation blocks + 🔀 passerelles + 💡 open question.

**Why the change:** Run 1 showed that the strict "ne cite JAMAIS un
établissement hors contexte" rule crippled the RAG on geographic diversity
(D5 "cyber en Bretagne" scored 12/18 because it kept saying "Ville non
précisée"). Run 2 tests whether relaxing this fixes the negative result.

## 5. Benchmark — run 1 (NEGATIVE RESULT)

Run 1 used the strict system prompt (pre-fix). Blind benchmark with Claude
Sonnet 4.5 as judge on 32 questions (30 scored + 2 honesty), randomized
{A, B, C} labels per question, 6 criteria × 0-3 points.

### Aggregate /18

| System | Total | Rank |
|---|---|---|
| **mistral_raw** | **16.19** | 🥇 |
| our_rag | 13.41 | 🥈 |
| chatgpt_recorded | 6.25 | 🥉 |

### Per category (total /18)

| Category | mistral_raw | our_rag | chatgpt | Delta (RAG − Mistral) |
|---|---|---|---|---|
| biais_marketing | **16.00** | 13.60 | 5.20 | −2.40 |
| realisme | **15.80** | 15.40 | 5.60 | −0.40 |
| decouverte | **17.20** | 12.60 | 4.40 | **−4.60** 😬 |
| diversite_geo | **16.20** | 13.00 | 8.20 | **−3.20** |
| passerelles | **17.00** | 13.40 | 5.60 | **−3.60** |
| comparaison | **15.40** | 13.20 | 7.20 | −2.20 |
| honnetete | **15.00** | 11.50 | 9.50 | **−3.50** |

### Per criterion /3

| Criterion | mistral_raw | our_rag | chatgpt |
|---|---|---|---|
| neutralite | 3.00 | 2.88 | 1.00 |
| realisme | 2.97 | 2.34 | 1.06 |
| sourcage | 2.91 | 2.31 | 0.47 |
| diversite_geo | 2.34 | 1.44 | 0.66 |
| agentivite | 2.88 | 2.75 | 1.88 |
| decouverte | 2.09 | 1.69 | 1.19 |

### Diagnosis (run 1)

The thesis "RAG > raw Mistral on French orientation" is **empirically refuted
by run 1**. Mistral raw wins on every category. Our RAG beats ChatGPT by ~7
points, which is meaningful but far from the thesis.

**Root cause** ("retrieval constraint harm"):

1. Mistral already has extensive French education knowledge from training.
   It knows ENSIBS, IMT Atlantique, Sciences Po, HEC, Parcoursup, all of it.
2. The RAG feeds it top-10 retrieved fiches and a strict prompt "ne cite
   JAMAIS un établissement hors contexte". This CONSTRAINS Mistral to the
   10 fiches, many of which are generic ONISEP diplomas with empty etab.
3. Mistral raw is UNCONSTRAINED and draws from its full training → more
   diverse, more specific, more geographic coverage.
4. The Claude judge cannot fact-check sources. When Mistral raw confidently
   cites "Parcoursup 2023 taux 72%", the judge rewards apparent sourcing
   even if the number is invented. Our RAG, restrained, says "non précisé"
   → penalized.

**Evidence point**: on D5 "cyber en Bretagne", our RAG got 12/18 with geo 1/3
because it said "Ville non précisée" for the ONISEP ENSIBS fiche. Mistral raw
got 17/18 with geo 3/3 citing Brest/Vannes/Rennes/Lannion. **ChatGPT also
beat our RAG on D5** (12/18, but still behind Mistral).

### Files saved from run 1
- `results/run1_strict_sourcing/raw_responses/` (responses + label mapping)
- `results/run1_strict_sourcing/scores/` (blind + unblinded + summary)
- `results/run1_strict_sourcing/charts/radar_by_system.png`

## 6. Benchmark — run 2 (FIX APPLIED, IN PROGRESS)

Run 2 uses the **relaxed system prompt** (commit 8b1f14f). The fix:

```diff
- en t'appuyant EXCLUSIVEMENT sur des données officielles vérifiables
+ en t'appuyant EN PRIORITÉ sur les données fournies en contexte.
+ Tu peux compléter avec tes connaissances générales, mais signale-le
+ clairement avec « (connaissance générale) ».

SOURÇAGE :
- - Ne cite JAMAIS un établissement qui n'apparaît pas explicitement
-   dans les FICHES fournies en contexte. [...]
+ - Les FICHES fournies sont ta SOURCE DE VÉRITÉ pour les chiffres :
+   taux d'accès, coût, labels, URL ONISEP. N'invente JAMAIS ces valeurs.
+ - Pour le reste (descriptions, conseils, passerelles, géographie), tu
+   peux t'appuyer sur tes connaissances. Signale-le avec
+   « (connaissance générale) ».
```

Also added retry logic for Mistral 429 rate limit with 15s base delay (after
hitting service-tier capacity at question B4 on the first attempt of run 2).

**Run 2 status at handoff write:** 29/32 questions completed, background
process `bfadrxxz3` still running. Expected to finish shortly.

## 7. API budget state

### Mistral
- Quota: 1 Md tokens/month free tier. Used: ~130K tokens across 2 full runs
  (~0.013%). **Not a constraint.**
- Rate limit: shared service-tier capacity, fires 429 on bursts. Handled by
  `_call_with_retry` in `src/eval/runner.py` with 15s base delay on rate
  limit errors. Pragmatic but not bulletproof — under heavy load, may still
  slow down.

### Anthropic
- Initial credit: $5 free tier.
- Per judge run cost: ~$1.15 (32 questions × 3500 tokens × Sonnet 4.5 pricing).
- **After run 2 judge**, remaining credit ≈ $2.7.
- **Task 4.5 grid search** would cost 5 × $1.15 = **$5.75** → **OVER BUDGET.**

Options for Task 4.5:
- (A) Skip grid search entirely, document as "deferred due to budget".
- (B) Mini grid search on 3 values {1.0, 1.5, 2.0} = $3.45, tight but fits.
- (C) Matteo tops up Anthropic credit by $5-10.

Matteo will decide based on his remaining credit balance (user-check required).

## 8. Known issues / open questions

1. **Benchmark run 2 delta TBD** — we don't yet know if the system prompt
   relaxation fixes the negative result. Waiting for run 2 + new judge run.
2. **Grid search budget** — see section 7.
3. **Parcoursup data is BTS-heavy** — 63% of fiches are bac+2 BTS CIEL.
   Higher-ed (ENSIBS, IMT, CentraleSupélec) comes only from ONISEP, and
   ONISEP often lists formation types without establishment names.
4. **Judge rewards confident-looking sourcing over truthful restraint** —
   methodological flaw in the Claude-as-judge approach. Mentioned as a
   limitation in the eventual paper.
5. **ONISEP field mapping is best-effort** — the formations dataset
   (5fa591127f501) has no `etablissement` field. School names are extracted
   heuristically from `libelle_formation_principal` via regex in
   `src/collect/onisep.py:extract_school_from_formation_name`. Only 25/102
   ONISEP fiches get a populated establishment this way.

## 9. Next steps (in order)

1. **Wait for run 2 to finish** (29/32 at write time, ~2 more questions)
2. **Run Claude judge on run 2** (`python -m src.eval.run_judge`, ~$1.15)
3. **Run analyze** (`python -m src.eval.analyze`, free)
4. **Compare run 1 vs run 2** — did the system prompt relaxation close or
   reverse the gap? Three outcomes:
   - our_rag > mistral_raw → thesis validated, publish
   - Still our_rag < mistral_raw but narrower gap → partial fix, document
     both results honestly
   - Still our_rag << mistral_raw → accept negative result, pivot paper
     narrative to "when does RAG help and when does it hurt"
5. **Decide on grid search** (Task 4.5) based on budget
6. **Phase 5 — Interface** (FastAPI + React, ~2 days)
7. **Phase 6 — Finalization** (report, demo video script, tag v1.0)

## 10. Commit history (recent)

```
5e019f6 fix(eval): handle 429 rate limit with longer backoff in retry logic
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

## 11. How to resume in a fresh session

```bash
cd /home/matteo_linux/projets/OrientIA
source .venv/bin/activate

# Read the state
cat docs/SESSION_HANDOFF.md
git log --oneline -15

# Verify test suite still passes
pytest tests/ -v 2>&1 | tail -5

# Check benchmark state
ls -lh results/raw_responses/ results/scores/ 2>/dev/null
python3 -c "import json; d = json.load(open('results/raw_responses/responses_blind.json')); print(f'{len(d)}/32')" 2>/dev/null

# If run 2 is complete, run judge + analyze
python -m src.eval.run_judge    # ~5 min, ~$1.15 Anthropic
python -m src.eval.analyze      # free, ~1 sec
```

Then resume from section 9 "Next steps".
