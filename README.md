# OrientAI : A Specialized RAG System for French Educational Guidance

**OrientAI**  is a Retrieval-Augmented
Generation (RAG) system specialised in French academic and vocational
guidance, post-baccalauréat. It is the submission of *Matteo Lepietre*
to the **INRIA AI Grand Challenge** (2026).

you can try the LLM here : https://orientai-platform.fr/

The system pairs an LLM (Mistral) with a French-only, publicly-sourced
corpus of **47 214 program/career records** and a multi-stage pipeline
designed to suppress the marketing bias, hallucinations, and ranking
fabrications that general-purpose chatbots produce on this domain.

---

## 1. What this project actually does

A high-school student or a re-orienting graduate types a free-form question
(*"Which engineering schools in cybersecurity exist in Brittany?"*,
*"Can I combine a CROUS grant with a part-time job?"*, *"What is the
acceptance rate for the Bachelor Cyber EFREI Bordeaux?"*) and receives a
short, sourced, neutral answer grounded in official French data
(Parcoursup, ONISEP, MonMaster, ROME, RNCP, InsertSup, CROUS, INSEE,
APEC, DARES, France Compétences, …).

Three properties matter:

1. **Honesty over fluency** : the system *refuses* requests it cannot
   ground in its corpus (ranking superlatives, fictional schools, pure
   medical advice, celebrity questions). Honesty is measured: see Gate 4
   in [`docs/BENCH_GATES.md`](docs/BENCH_GATES.md).
2. **Public-data sovereignty** : every numeric claim is traceable to an
   official open dataset. No private rankings, no SEO-boosted private
   schools, no scraped LinkedIn salary data.
3. **Production discipline** — single FastAPI endpoint, deterministic
   factory configuration, full test suite (2 500+ tests), ADR log (60+
   entries) for every load-bearing decision.

---

## 2. System v4.1 : pipeline at a glance

A single endpoint, `POST /answer` (`src/api/server.py:386`), runs the
following stages for every user question. All stages are deterministic
in their configuration (`src/rag/factory.py:make_production_pipeline`).

```
                     question + (optional history)
                                  │
              ┌───────────────────▼────────────────────┐
              │ 1. ScopeClassifier        (Mistral S.) │  → if out_of_scope / urgent
              │    in_scope / out_of_scope / urgent    │     / identity / greeting
              │    / identity / greeting               │  → short-circuit with a
              │    (regex + LLM, history-aware)        │     pre-written response.
              └───────────────────┬────────────────────┘
                                  │ in_scope
              ┌───────────────────▼────────────────────┐
              │ 2. RouterLLM              (Mistral S.) │  → sub-indexes ⊆ {formations,
              │    JSON-tool, picks sub-indexes,       │     metiers, statistiques,
              │    filter criteria (region, niveau,    │     aides_territoires},
              │    secteur, alternance, budget),       │     FilterCriteria,
              │    refusal_reason if applicable        │     refusal templates.
              └───────────────────┬────────────────────┘
                                  │
              ┌───────────────────▼────────────────────┐
              │ 3. Intent classifier      (rule-based) │  → 7 intent classes drive
              │    factual_pointed / geographic /      │     (top_k, mmr_lambda).
              │    comparaison / realisme /            │
              │    passerelles / decouverte / general  │
              └───────────────────┬────────────────────┘
                                  │
              ┌───────────────────▼────────────────────┐
              │ 4. Structured SELECT bypass            │  → if factual_pointed and
              │    (fuzzy named-formation lookup)      │     match: zero-LLM answer.
              └───────────────────┬────────────────────┘
                                  │ no SELECT
              ┌───────────────────▼────────────────────┐
              │ 5. Hybrid retrieval                    │  → FAISS dense (1024-d)
              │    FAISS dense + BM25 lexical +        │     + BM25 (Okapi, FR
              │    RRF fusion + quad sub-indexes       │     stopwords) fused with
              │    + metadata filter w/ auto-expansion │     Reciprocal Rank Fusion.
              │    + domain-aware reranker             │     k = 150 → MMR → top-K.
              │    + MMR diversification               │
              └───────────────────┬────────────────────┘
                                  │ top-K sources
              ┌───────────────────▼────────────────────┐
              │ 6. Golden-QA few-shot (optional)       │  → injects a structurally
              │    Mistral-embed of curated Q/A bank   │     similar past answer
              └───────────────────┬────────────────────┘     (tone / format only).
                                  │
              ┌───────────────────▼────────────────────┐
              │ 7. Generation             (Mistral M.) │  → JSON FactCard sources,
              │    System prompt v4.1 strict           │     answer ≤ 250 words,
              │    (R1–R7: chiffres / identité /       │     mandatory citations
              │    citations / style / posture /       │     "[source S1]" for any
              │    longueur / hardlock régional)       │     numerical claim.
              └───────────────────┬────────────────────┘
                                  │ tour 1 answer
              ┌───────────────────▼────────────────────┐
              │ 8. Validator (2-3 layers)              │  → Layer 1: 10 rules
              │    rules + corpus_check + layer 3 LLM  │     Layer 2: corpus fuzzy
              │                                        │     Layer 3: Mistral S.
              │    → honesty_score ∈ [0, 1], flagged   │     (intent-gated)
              └───────────────────┬────────────────────┘
                                  │ if flagged: retry-with-hint (1 retry, 30s cap)
              ┌───────────────────▼────────────────────┐
              │ 9. UX policy (α + β + γ)               │  → BLOCK / WARN / PASS,
              │    hybrid deterministic decision       │     optional footer info.
              └───────────────────┬────────────────────┘
                                  │
              ┌───────────────────▼────────────────────┐
              │ 10. Post-process                       │  → strip invented URLs,
              │    deterministic URL / markdown fixes  │     fix broken tables,
              │                                        │     validate ONISEP slugs.
              └───────────────────┬────────────────────┘
                                  ▼
                       (answer, sources[], meta)
```

Target end-to-end latency (production): **p50 ≈ 6 s**, **p95 ≤ 12 s**,
measured on the 65–71-question evaluation set.

For the full step-by-step description see
[`docs/ARCHITECTURE_EXPLICATIVE.md`](docs/ARCHITECTURE_EXPLICATIVE.md)
(32 KB, fully aligned with the current v4.1 production code).

---

## 3. Corpus : what powers the answers

The retrieval corpus (`data/processed/formations_v7.json`,
[aliased](docs/SESSION_HANDOFF_2026-05-08_VERROUILLAGE.md) as
`formations.json`, ~89 MB) contains **47 214 records** consolidated from
multiple open French datasets, of which **43 185 (91.5%) are
retrieval-eligible** (the remainder are excluded by the Vague 1.C
granular policy : non-named records that pollute results).

Major sources (top 12 by record count):

| Source | Records | What it brings |
|---|---:|---|
| Parcoursup Open Data | 8 191 | Acceptance rates, admitted profiles, capacities |
| MonMaster | 7 573 | Master programs, M1/M2 selectivity |
| RNCP (France Compétences) | 5 181 | National certifications + competency blocs (4 891) |
| ONISEP | 4 758 + 1 075 idéo | Official program descriptions + career outlets |
| InsertJeunes (CFA + Lycée Pro) | 4 065 + 2 693 | Apprenticeship insertion rates |
| La Bonne Alternance | 4 008 | Live alternance opportunities (corpus snapshot) |
| ROME 4.0 (France Travail) | 1 584 + skills | 17 825 competencies for métier discovery |
| DARES | 1 160 + 2030 prospective | Labour-market projections by profession |
| InsertSup MESR | 368 | Post-master employment statistics |
| Manual labels (SecNumEdu / CTI / CGE / Grade Master) | 25 entries | Authoritative French quality labels |
| CROUS (residences + restaurants) | 820 + 999 | Student life data per city/region |
| Calendar Parcoursup / MonMaster | 16 entries | Official dates (verified, 2026-05-08) |
| INSEE salaires 2023 | 10 050 | Sectoral / regional / diploma salary statistics |
| APEC regional observatory | 13 | Executive labour market per region |

The corpus is partitioned into **four FAISS sub-indexes** at build time
(`scripts/build_quad_subindexes.py`), each dedicated to a query class
chosen by the RouterLLM:

| Sub-index | Vectors | Used for |
|---|---:|---|
| `formations` | 32 481 | Program-centric queries (Parcoursup / MonMaster / ONISEP / RNCP) |
| `metiers` | 4 894 | Career discovery, métier descriptions, prospective |
| `statistiques` | 831 | Salary, insertion rates, regional labour data |
| `aides_territoires` | 4 979 | Funding, scholarships, CROUS, regional aid |

Embeddings: **`mistral-embed`** at 1024 dimensions, total ~170 MB on
disk, gitignored (rebuilt from corpus + script).

---

## 4. System prompt v4.1 strict : non-negotiable contract

The generation prompt is intentionally short and enforces seven rules
("R1–R7") on top of a JSON FactCard structure for sources. See
`src/prompt/system_v4_strict.py` for the exact text. Summary:

- **R1 Numbers**: every numeric claim must be sourced from a FactCard
  `chiffres` block; no implicit averages or "approximately".
- **R2 Identity**: name only formations / institutions present in the
  current FactCard set.
- **R3 Citations**: `[source SX]` after every numeric statement; the
  citation must point to an actually-cited source.
- **R4 Style**: neutral, no superlatives ("the best", "top 3"), no
  marketing language.
- **R5 Posture**: open-ended questions are encouraged at the end; no
  bullet-point overload; no confessional "I have no info on X" when a
  partial answer is possible.
- **R6 Length**: hard cap **250 words** (`max_tokens=400`). Concise is
  the product, not the limitation.
- **R7 Hardlock**: regional / level / sector / alternance constraints
  emitted by the RouterLLM are injected at the top of the prompt and
  cannot be relaxed by the LLM ("no out-of-region alternative without
  explicitly saying the region is empty").

---

## 5. Evaluation : Phase D

Evaluation runs are reproduced end-to-end by
[`scripts/reproduce_bench.sh`](scripts/reproduce_bench.sh) (eight
stages, ~$25–30 of API calls, ~2–3 h wall-clock). The current
benchmark uses:

- **65–71 questions** in
  [`data/golden_eval/golden_60.json`](data/golden_eval/golden_60.json)
  (schema v3.1 since ADR-060) covering 11 categories: `lyceen_parcoursup`,
  `reorientation`, `metier`, `calendaire`, `geographique`,
  `vie_etudiante`, `vie_etudiante_periph`, `adversarial`, `cross_domain`,
  `live` (bugs reproduced from the live platform), `paraphrase`.
- **6 GO/NO-GO gates** in [`docs/BENCH_GATES.md`](docs/BENCH_GATES.md):
  retrieval (recall@5 ≥ 75%, MRR ≥ 0.55, nDCG@10 ≥ 0.65), honesty
  (validator avg ≥ 0.95), latency (p95 ≤ 12 s), adversarial refusal
  (≥ 80% on superlatives / fake schools / prompt injection), cross-vendor
  rubric agreement (Claude Sonnet 4.5 + GPT-4o ≥ 12/18 with inter-judge
  κ ≥ 0.4), Haiku fact-check (≥ 0.85 / no unverifiable high-confidence).
- **7-system ablation matrix** (`src/eval/systems.py`): `our_rag_v7`,
  `mistral_neutral`, `mistral_v3_2_no_rag`, `gpt4o_neutral`,
  `gpt4o_v3_2_no_rag`, `claude_neutral`, `claude_v3_2_no_rag`.
  Isolates the *RAG contribution* (same model, same prompt, RAG only
  difference) and the *prompt portability* across vendors.
- **Seed-deterministic blinding** (A–G label permutation per question,
  `generation/seed.txt` + `label_mapping.json`).
- **Multi-judge with incremental save** (Claude + GPT-4o + Haiku
  fact-check, each can be resumed from `save_path` after a crash; the
  previous run survived a rate-limit kill at step 7 with zero data loss).

The original Phase F methodology (Run F+G, April 2026, 100q) is
preserved as historical reference in
[`docs/METHODOLOGY.md`](docs/METHODOLOGY.md).

---

## 6. Technical stack

| Layer | Component | Notes |
|---|---|---|
| Runtime | Python 3.12 | local `.venv`, locked in `requirements.lock` |
| Generation | `mistral-medium-latest` | `T=0.3`, `max_tokens=400`, v4.1 strict prompt |
| Scope / routing / validator-L3 | `mistral-small-latest` | `T=0`, JSON-tool |
| Embeddings | `mistral-embed` | 1024-d, batch 64 |
| Judges (eval) | Claude Sonnet 4.5 + GPT-4o + Claude Haiku 4.5 | rate-limit-aware, retry-on-429 |
| Vector store | FAISS `IndexFlatL2` | CPU, no GPU dependency |
| Lexical | `rank_bm25.BM25Okapi` | FR stopwords (~45), strip-accents tokeniser |
| Backend | FastAPI + uvicorn | single worker, bearer-token auth, 10 req/min/IP |
| Deployment | Railway (backend) + Docker | `Dockerfile`, `.railwayignore` enforce ~100 MB cap |
| Tests | pytest 9 | 2 516 tests, 0 fail (last full run 2026-05-08) |

---

## 7. Setup / run locally

```bash
git clone https://github.com/matjussu/OrientIA.git
cd OrientIA

# Python 3.12 virtual env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock

# Secrets — fill in the three API keys (Mistral mandatory, Anthropic +
# OpenAI mandatory only for the benchmark)
cp .env.example .env
$EDITOR .env

# Production corpus + FAISS index (will rebuild from /data — ~$5 of
# Mistral embed calls on first run, idempotent thereafter)
python -m src.collect.merge
python -m src.rag.embeddings
python scripts/build_quad_subindexes.py

# Tests
pytest tests/

# Local API
uvicorn src.api.server:app --reload
# → POST /answer {"question": "..."} on http://localhost:8000
```

For the full reproduction of the published benchmark numbers:

```bash
./scripts/reproduce_bench.sh             # full bench (~$25, ~2–3 h)
./scripts/reproduce_bench.sh --dry-run   # validate env / paths only
./scripts/reproduce_bench.sh --skip-judges     # skip LLM judges (~$15 saved)
./scripts/reproduce_bench.sh --skip-factcheck  # skip Haiku (~$3-5 saved)
```

Output: `results/bench_v7_v4_1_<timestamp>/SUMMARY.md` (GO / NO-GO verdict
against the 6 gates) plus all raw responses, scores, and blinding maps.

---

## 8. Scope and limitations

OrientAI is built for the French post-baccalauréat orientation market:
formations Parcoursup / MonMaster, métiers ROME, student life (CROUS,
funding), official statistics (Parcoursup, InsertSup, INSEE, APEC,
DARES). It will *refuse* (Gate 4) out-of-scope queries:

- pure medical advice ("how to cure the flu?")
- celebrity questions
- subjective superlatives without official ranking ("the best business
  school in France?") — redirected to Onisep / SCUIO / CIO
- fabricated entities (fictional schools, fictional cities, future
  calendar dates beyond official horizon)

Known structural limitations are documented in
[`docs/LIMITATIONS.md`](docs/LIMITATIONS.md):

- Some sources are partially ingested (APEC PDFs, La Bonne Alternance
  is a static snapshot rather than a live API).
- Regional coverage is uneven (41.5% of retrieval-eligible records lack
  an explicit region — structural property of RNCP / ONISEP / LBA
  national records).
- The judge rubric (Claude + GPT-4o) was calibrated on the v3.2 prompt
  in Phase F and is preserved frozen for longitudinal comparison; the
  v4.1 strict mode (≤ 250 words, factual-first) may score lower on
  "discovery" and "agency" criteria that reward open-ended prose — this
  trade-off is intentional and documented in
  [`docs/SESSION_HANDOFF_2026-05-08_VERROUILLAGE.md`](docs/SESSION_HANDOFF_2026-05-08_VERROUILLAGE.md).

---

## 9. Repository layout

```
OrientIA/
├── src/
│   ├── api/                # FastAPI server (single endpoint /answer)
│   ├── collect/            # Open-data ingestion + fuzzy merge
│   ├── rag/                # ScopeClassifier, RouterLLM, retriever,
│   │                       # reranker, MMR, generator, validator wiring
│   ├── prompt/             # System prompts (v3.2 historical, v4.1 strict)
│   ├── validator/          # Rules + corpus_check + UX policy
│   ├── eval/               # 7-system ablation + judges + fact-check
│   └── config.py           # Env-var loader (.env)
├── data/
│   ├── manual_labels.json          # 25 authoritative quality labels (tracked)
│   ├── golden_eval/golden_60.json  # Benchmark questions (65–71q, v3.1)
│   ├── raw/                # Open-data fixtures (most paths gitignored)
│   ├── processed/          # Corpus build artefacts (gitignored)
│   └── embeddings/         # FAISS indexes (gitignored, ~170–193 MB)
├── docs/
│   ├── ARCHITECTURE_EXPLICATIVE.md   # Full system v4.1 walk-through
│   ├── BENCH_GATES.md               # 6 GO/NO-GO gates definition
│   ├── METHODOLOGY.md               # Phase F historical methodology + banner
│   ├── DECISION_LOG.md              # 60+ ADR entries (architecture + data)
│   ├── LIMITATIONS.md               # Honest scope + structural caveats
│   ├── PIPELINE_v4_1_FLAGS.md       # 13 factory.py flags documented
│   └── SESSION_HANDOFF*.md          # Sprint handoffs (transparency)
├── scripts/
│   ├── reproduce_bench.sh           # End-to-end benchmark (8 stages)
│   ├── build_quad_subindexes.py     # Build the 4 FAISS sub-indexes
│   ├── eval_recall.py               # Standalone retrieval evaluation
│   ├── synthesize_bench_results.py  # Apply the 6 gates → SUMMARY.md
│   └── …                            # ~80 utility / audit scripts
├── tests/                  # pytest, 2 516 verts (2026-05-08)
├── Dockerfile              # Production image (Railway)
├── requirements.lock       # Pinned deps for full reproducibility
└── README.md               # (this file)
```

---

## 10. License and contact

MIT License — see [`LICENSE`](LICENSE). Built by *Matteo Lepietre* for
the INRIA AI Grand Challenge 2026. All data used is public, official,
and free; no scraping, no paid third-party APIs in the knowledge base.

The project is part of a broader thesis on **architectural sovereignty**:
the claim that national open data + a disciplined pipeline outperforms
larger general-purpose models in domains where neutrality, sourcing,
and factual grounding matter more than raw fluency.
