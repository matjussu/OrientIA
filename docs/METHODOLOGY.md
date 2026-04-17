# OrientIA — Methodology

**Purpose:** permanent reference for the evaluation methodology. Everything
in this file must be precise enough that an outside reader (reviewer or
future-us) can reproduce the experiment from scratch. No rationale
questions here — see `DECISION_LOG.md` for "why did we choose X".

**Last updated:** 2026-04-15 (Phase F.4, Run F generation in progress).

---

## 1. Dataset

### 1.1 Composition (100 questions, `src/eval/questions.json`)

| Split | Count | Notes |
|---|---|---|
| **dev** | 32 | Original Run 1-10 questions. v3.x prompt was tuned on these. |
| **test** | 68 | New in F.1, held out from all prompt tuning. |
| **Total** | **100** | — |

### 1.2 Categories (9 types)

| Category | Count | Purpose |
|---|---|---|
| `biais_marketing` | 12 | Detects private-school SEO bias |
| `realisme` | 12 | Tests admission-rate grounding |
| `decouverte` | 12 | Tests open-ended career exploration |
| `diversite_geo` | 12 | Tests regional coverage |
| `passerelles` | 12 | Tests cross-field transitions |
| `comparaison` | 12 | Tests side-by-side institutional comparison |
| `honnetete` | 10 | Tests conceptual definitions (can model admit boundaries?) |
| `adversarial` | 10 | Fake schools / fake reports / fake towns — tests honesty |
| `cross_domain` | 8 | Questions outside cyber/data (droit, médecine, etc.) |

### 1.3 Each question schema (v2.0)
```json
{
  "id": "A1",
  "category": "biais_marketing",
  "split": "dev" | "test",
  "type": "normal" | "adversarial" | "cross_domain",
  "text": "..."
}
```

### 1.4 Source data (knowledge base for RAG)

`data/processed/formations.json` — **443 fiches** (formations), produced by
`src/collect/merge.py` from 4 open-source datasets:

| Source | Count | Fields contributed |
|---|---|---|
| Parcoursup Open Data | 343 | `nom, ville, statut, niveau, detail, departement, profil_admis, selectivite` |
| ONISEP | 102 | `nom, description_onisep, debouches_onisep` |
| ROME 4.0 (France Travail) | (injected) | Top-3 `debouches` codes + labels per fiche |
| SecNumEdu / CTI / CGE / Grade Master | 21 labels | `labels: [...]` list |

Merge strategy :
- RNCP key match (strict) → 7 fuzzy matches
- Fuzzy match on `etablissement` + `ville` via rapidfuzz, threshold 70-80 →
  remainder
- Manual labels from `data/manual_labels.json` (25 entries) — authoritative.

---

## 2. RAG pipeline (the `our_rag` system)

### 2.1 Index
- FAISS `IndexFlatL2` on Mistral embeddings (`mistral-embed`, 1024 dims).
- Cached at `data/embeddings/formations.index` (1.7 MB, gitignored).
- Rebuilt only when fiches change.

### 2.2 Retrieval flow per question
1. **Embed query** (Mistral embed) → `q_vec ∈ ℝ^1024`.
2. **Retrieve top-k=30** from FAISS (L2 distance → similarity via `1/(1+d)`).
3. **Enrich** each result with its raw embedding via
   `index.reconstruct(i)` (zero extra API call — embeddings already live
   in the index).
4. **Rerank** with label boosts :
   ```
   score = base * secnumedu_boost^[has_secnumedu]
                * cti_boost^[has_cti]
                * grade_master_boost^[has_grade_master]
                * public_boost^[is_public]
                * level_boost_bac5^[niveau=bac+5]
                * level_boost_bac3^[niveau=bac+3]
                * etab_named_boost^[has_named_etab]
   ```
   Defaults in `RerankConfig` : 1.5, 1.3, 1.3, 1.1, 1.15, 1.05, 1.1.
5. **Classify intent** (rule-based) → one of 7 classes (see §2.4).
6. **Select intent-specific (top_k_sources, mmr_lambda)**.
7. **MMR selection** (F.3.a) — greedy pick of `top_k_sources` items
   maximising `λ · relevance − (1 − λ) · max_sim(already_selected)`
   where relevance = normalised rerank score, similarity = cosine between
   embeddings.
8. **Format context** via `src/rag/generator.py:format_context` (signal-
   first 7-line layout, detail truncated at 500 chars, top-3 ROME métiers).
9. **Generate** with Mistral chat completion, system prompt v3.2,
   temperature 0.3.

### 2.3 MMR formula (Maximal Marginal Relevance)
```
MMR(i | S) = λ · relevance(i) − (1 − λ) · max_{j ∈ S} cos(e_i, e_j)

where
  e_i, e_j ∈ ℝ^1024  (Mistral embeddings, ℓ2-normalised)
  relevance(i) = rerank_score(i) / max_j rerank_score(j)  ∈ [0, 1]
  S          = set of already-selected candidates
  λ          = tradeoff (0=pure diversity, 1=pure relevance)
```

First pick is `argmax_i relevance(i)` (no diversity term). Subsequent picks
iterate the formula above. Implementation : `src/rag/mmr.py:mmr_select`.

### 2.4 Intent classifier (rule-based, `src/rag/intent.py`)

7 classes determined by ordered regex checks on `strip_accents(lower(q))`:

| Class | Trigger patterns (non-exhaustive) |
|---|---|
| `comparaison` | `\bcompar(e/aison)\b`, `\bdifference entre\b`, `\b[ACRONYM] (ou/et) [ACRONYM]\b` |
| `realisme` | `\b\d{1,2} de moyenne\b`, `\btaux d'admission\b`, `\bselectivite\b`, `\baccessible\b` |
| `passerelles` | `\breorient(er/ation)\b`, `\breconversion\b`, `\bpasserelle\b`, `\bchanger de filiere\b` |
| `conceptual` | `\bc'est quoi\b`, `\bqu'est-ce\b`, `\bcomment fonctionne\b`, `\bexplique(r)\b` |
| `decouverte` | `\bquels metiers\b`, `\bdecouvr(ir)\b`, `\bmeconnu\b`, `\boriginal\b`, `\bjaime\b` |
| `geographic` | French city / region token match (closed set of 50+ cities, 20+ regions) |
| `general` | Fallback |

### 2.5 Per-intent retrieval strategy

| Intent | `top_k_sources` | `mmr_lambda` | Rationale |
|---|---|---|---|
| `comparaison` | 12 | 0.6 | Widen to surface 2-3 named institutions side-by-side |
| `geographic` | 12 | 0.4 | Aggressive diversification over regional offering |
| `realisme` | 6 | 0.85 | Focus — all data points on the specific formation |
| `passerelles` | 10 | 0.6 | Moderate breadth for bridge formations |
| `decouverte` | 12 | 0.3 | Most aggressive diversification — surface unexpected paths |
| `conceptual` | 4 | 0.9 | Single canonical answer, minimal context |
| `general` | 10 | 0.7 | Baseline / default |

### 2.6 System prompt (v3.2, `src/prompt/system.py`)

Four-layer structure :
1. **Identity** : French orientation specialist, cyber/data focus.
2. **Behavioural constraints** : neutrality (official labels first),
   realism (Parcoursup access rates when available), agency
   (open questions, encourage reflection).
3. **Output schema** : Plan A / Plan B / Plan C structure + source
   citation + access rate + status (public/private) + cost.
4. **Guardrails** : redirection for out-of-scope or psychological distress.

Specific targeted rules added through iterations :
- **Anti-confession** (Phase 1) — don't tell the user "I have no info on X";
  instead give best-effort guidance. Flipped passerelles gap from -1.20 to +1.00.
- **Conceptual bypass** (Phase C) — for `honnetete` definition questions,
  skip the Plan A/B/C structure.
- **Interdisciplinary bias** (Phase C) — for `decouverte`, encourage
  unconventional combinations.
- **Distinct-villes ≥ 3** (Phase C) — for `diversite_geo`, enforce
  at least 3 different regions mentioned.
- **Comparison-table rule** (Phase E.2) — for `comparaison`, require a
  side-by-side markdown table. Flipped comparaison gap +5.00.

---

## 3. 7-system ablation matrix

Full matrix in `src/eval/systems.py`, built by `make_seven_systems()` :

| # | Name | Prompt | RAG | MMR+Intent | Purpose |
|---|---|---|---|---|---|
| 1 | `our_rag` | v3.2 | ✅ | ✅ (F.3.c-bis) | Full stack (thesis) |
| 2 | `mistral_neutral` | NEUTRAL | ❌ | ❌ | Raw-LLM baseline |
| 3 | **`mistral_v3_2_no_rag`** | v3.2 | ❌ | ❌ | **Isolates RAG** |
| 4 | `gpt4o_neutral` | NEUTRAL | ❌ | ❌ | OpenAI vendor baseline |
| 5 | `gpt4o_v3_2_no_rag` | v3.2 | ❌ | ❌ | OpenAI + our prompt |
| 6 | `claude_neutral` | NEUTRAL | ❌ | ❌ | Anthropic vendor baseline |
| 7 | `claude_v3_2_no_rag` | v3.2 | ❌ | ❌ | Anthropic + our prompt |

Scientific tests :
- **RAG contribution** : `our_rag` vs `mistral_v3_2_no_rag` (same model,
  same prompt, RAG is the only difference).
- **Prompt portability** : system 3 vs 2, system 5 vs 4, system 7 vs 6.
- **Vendor effect** : system 3 vs 5 vs 7 (same prompt, different LLMs).

### NEUTRAL_MISTRAL_PROMPT

A plain generic-assistant prompt used as fair baseline. Avoids the v3.2
rules so the comparison isolates prompt engineering from model ability.
See `src/eval/systems.py:NEUTRAL_MISTRAL_PROMPT` for the full text.

---

## 4. Judge protocol (LLM-as-judge)

### 4.1 Rubric (6 criteria × 0-3 each, total /18)

| # | Criterion | 0 | 1 | 2 | 3 |
|---|---|---|---|---|---|
| 1 | **Neutralité institutionnelle** | Only private schools | Mixed without distinction | Mentions public | Prioritises official labels |
| 2 | **Réalisme** | "All possible!" | Vague selectivity | Cites data | Precise access rates |
| 3 | **Sourçage** | None | Vague ("on dit...") | Mentions institutions | Verifiable source (Parcoursup, ONISEP, ANSSI) |
| 4 | **Diversité géographique** | Paris only | Paris + 1-2 | Several regions | Adapted to profile |
| 5 | **Agentivité** | Closed/directive | Few options | Proposes | Options + open question |
| 6 | **Découverte** | Obvious métiers only | 1-2 classic | Original paths | Surprising-but-relevant |

Exact prompt : `src/eval/judge.py:JUDGE_PROMPT`. Must stay identical across
judges (Claude, GPT-4o) so disagreement reflects judge variance, not
prompt variance.

### 4.2 Blinding protocol

Per question, the 7 systems are assigned shuffled labels `A..G`.
Shuffling uses a deterministic seed (default 42) so the same order is
reproducible. Mapping saved to `label_mapping.json` alongside
`responses_blind.json` — the **judge never sees it**.

Judge receives :
```
Question: ...
RÉPONSE A: ...
RÉPONSE B: ...
...
RÉPONSE G: ...
```
and outputs a JSON object keyed by label, 6 scores + justification per
label, total per label.

### 4.3 Multi-judge (F.4)

Both judges see the **exact same** blinded input. Implementation :
- `src/eval/judge.py` : Claude Sonnet 4.5 judge.
- `src/eval/judge_openai.py` : GPT-4o judge (reuses `JUDGE_PROMPT`,
  `_build_user_content`, `_extract_json`, `_max_tokens_for_n` from
  `judge.py`).
- `src/eval/run_judge_multi.py` : orchestrator writing
  `scores_claude.json` + `scores_gpt4o.json`.

Inter-judge agreement to be computed in Phase G.1 (Cohen's κ on the
6 criteria, Krippendorff's α across judges).

### 4.4 Judge-v2 regex fact-check

`src/eval/judge_v2.py` applies a deterministic post-processing pass over
v1 scores : detects institution/establishment citations, verifies they
appear in our knowledge base (`data/processed/formations.json`), and
down-weights `sourcage` scores where a citation is unverifiable.

The Claude-Haiku-based fact-check (`src/eval/fact_check_claude.py`,
commit `9f1b5aa`) is a more expensive version planned for Phase G.5.
Both are free for the `our_rag` fiches; they only penalise fabrication
across all systems uniformly.

---

## 5. API rate-limit discipline

### 5.1 OpenAI (tier 1 : 15 RPM for gpt-4o)

`src/eval/rate_limit.py:RateLimiter` — thread-safe minimum-interval gate.
Shared across all OpenAI callers per benchmark run.

Configuration :
- Generation phase (`run_real_full`) : **12 RPM** shared between
  `gpt4o_neutral` + `gpt4o_v3_2_no_rag` (1 limiter, 2 consumers).
- Judge phase (`run_judge_multi`) : **12 RPM** for the sole GPT-4o
  judge (1 limiter, 1 consumer).

12 RPM = 5s minimum gap between calls = 20% safety margin below the
15 RPM cap. No 429 ever observed.

### 5.2 Anthropic / Mistral

Paid tiers with >50 RPM — no throttling needed at our volume (100 q ×
few systems).

### 5.3 Retry + resume logic

`src/eval/runner.py` handles :
- Transient timeouts (ReadTimeout, APIConnectionError)
- HTTP 5xx (including Cloudflare 520)
- 429 rate limit (defensive fallback even with the limiter)
- Exponential backoff (2s, 4s, 8s, 16s, 32s, 5 retries max)

Incremental save : after each question, the full `responses_blind.json`
is rewritten atomically. On interruption, re-running picks up at the
first non-`done_id` question without regenerating.

---

## 6. Reproducibility

### 6.1 Deterministic seeds
- Label shuffling : seed 42 (or passed via `--seed`).
- Generation temperature : 0.3 (low, not zero to allow for natural
  French phrasing).
- MMR : deterministic given the same embeddings + relevance scores.
- Intent classifier : deterministic (pure regex).

### 6.2 Pinned dependencies
`pyproject.toml` has upper-bounds on all API clients
(mistralai 2.3.2, anthropic 0.93, openai 2.31). Breaking provider
changes are isolated.

### 6.3 Reproduce commands

```bash
# Full Run F (generation + multi-judge)
python -m src.eval.run_real_full --out-dir results/run_F_robust
python -m src.eval.run_judge_multi \
  --responses results/run_F_robust/responses_blind.json \
  --out-dir results/run_F_robust

# Sample validation ($0.50)
python -m src.eval.run_real_full --sample 5 --out-dir results/sample

# Retrieval inspection (free, no judge calls)
python -m src.eval.inspect_retrieval --first 32

# Full test suite
pytest tests/ -q
```

---

## 7. Known limitations (honest caveats for the paper)

1. **Domain scope** : optimised for cyber + data/AI. Cross-domain
   accuracy drops by design (Z1-Z8 test set measures this).
2. **Dataset freshness** : Parcoursup + ONISEP snapshot from 2025-Q4.
   No re-crawl since.
3. **Tier-1 API caps** : 12 RPM throttle means Run F takes ~1h instead
   of ~15min. Doesn't affect correctness, only wall-time.
4. **Single-language** : all questions + rubric in French. Methodology
   transfers to other languages but the exact regex intent classifier
   would need rewriting.
5. **Judge model bias** : Claude + GPT-4o may share cultural priors
   (Anglosphere + RLHF). Phase G.2 (human eval) measures this.
6. **Variance not yet measured** : Run F at handoff is a single run per
   config. Phase F variance runs (×2 more) planned after checkpoint.
