# OrientIA: A Specialized RAG System for French Educational Guidance

**OrientIA** is a specialized Retrieval-Augmented Generation (RAG) framework designed to provide high-fidelity academic and vocational guidance within the French educational landscape. Developed as a submission for the **INRIA AI Grand Challenge**, the project demonstrates that architectural precision and institutional data integration can significantly outperform general-purpose Large Language Models (LLMs) in domains requiring high neutrality and factual accuracy.

---

## Executive Summary

The primary objective of OrientIA is to mitigate the "marketing bias" and hallucinations prevalent in commercial LLMs. By utilizing a standard base model (Mistral) paired with a custom re-ranking mechanism based on official French labels, the system prioritizes public, high-quality, and verified educational pathways over those with high SEO visibility.

---

## Technical Architecture

### 1. Multi-Source Data Integration
The system ingests and fuses four primary open-source datasets. A critical technical challenge addressed is the lack of a universal identifier across these datasets, resolved through a dual-pass join:
* **RNCP Key Matching:** Direct alignment where National Directory of Professional Certifications keys exist.
* **Fuzzy Matching:** Utilization of the `rapidfuzz` library to normalize and match entities based on institution name and geolocation (70-80% success rate).

**Core Datasets:**
* **Parcoursup Open Data:** Provides access rates, admission profiles (Bac type, honors), and capacity for 14,252 programs.
* **ONISEP:** Official descriptions and career mappings for 5,869 formations.
* **ROME 4.0 (France Travail):** Operational directory of 1,584 professions and 17,825 skills to facilitate "discovery" of obscure career paths.
* **SecNumEdu (ANSSI):** Specialized labeling for excellence in cybersecurity education.

### 2. Label-Based Re-ranking Algorithm
The core scientific contribution is the implementation of an institutional re-ranking layer. While standard RAG systems retrieve documents based on cosine similarity (FAISS), OrientIA applies a weighted boost to results carrying official labels.
* **Optimization:** Weights (e.g., 1.5 for SecNumEdu) were determined via grid search to balance semantic relevance with institutional quality.
* **Bias Correction:** This ensures that high-quality public programs, which often lack the descriptive metadata density of private competitors, are surfaced to the user.

### 3. Four-Layer System Prompt
To ensure the LLM (Mistral Medium) adheres to guidance ethics, the prompt is structured into four distinct layers:
1.  **Identity:** Specialist in the French educational system.
2.  **Behavioral Constraints:** Enforced neutrality, realism (using Parcoursup access rates), and agency.
3.  **Output Schema:** Standardized JSON-like structure for every recommended program (Source, Access Rate, Status, Cost).
4.  **Guardrails:** Redirection for out-of-scope queries or psychological distress.

### 4. Metadata Filter (Sprint 10, opt-in)
A precision-oriented post-FAISS filter restricting the candidate pool to programs matching the user's hard constraints (region, level, alternance, budget, sector) before the generator step. The criteria are extracted automatically from the AnalystAgent's `profile_delta` (Sprint 9-archi), so no extra NLU layer is needed.

* **Schema (5 criteria, all optional):** `region`, `niveau_min`/`niveau_max` (Bac+N range), `alternance` (bool), `budget_max` (€/year), `secteur` (list of canonical sectors).
* **Architecture:** Post-FAISS / pre-MMR. FAISS retrieves `k × INITIAL_K_MULTIPLIER` (=3), reranker boosts, then `apply_metadata_filter` prunes. Auto-expansion `k × 2` up to `k × MAX_K_MULTIPLIER` (=10) if the filtered pool is smaller than `top_k_sources`.
* **Defensive vs strict matching:** `region` / `niveau` / `budget` adopt a defensive pass-through (a program with missing metadata is *included* — formations without published cost or location info shouldn't be excluded a priori). `alternance` and `secteur` are strict (a program without `alternance: true/false` is *excluded* when the user explicitly demands alternance).
* **Backward-compat:** `OrientIAPipeline(use_metadata_filter=False)` by default. Run F+G results remain reproducible without configuration changes. Activate via `OrientIAPipeline(..., use_metadata_filter=True)` and pass `criteria=extract_filter_from_profile(profile_delta)` to `.answer()`.
* **Observability:** `pipeline.last_filter_stats` dict after each `.answer()` call exposes `filter_active`, `k_initial`/`k_final`, `n_retrieved`, `n_after_filter`, `expansions`, `hit_max` — used to instrument the F+G recall A/B measurements.

Frontmatter consumed by the filter is produced by the `scripts/textualize_formations.py` pipeline (Sprint 10 chantier B), which converts ONISEP and RNCP source records into Markdown documents with structured frontmatter.

Design ADR: `docs/SPRINT10_RAG_FILTRE_DESIGN.md`.

---

## Evaluation Framework: LLM-as-a-Judge

OrientIA is evaluated on a double-blind benchmark of **100 questions**
(32 development questions + 68 hold-out test questions), split across
7 categories + 10 adversarial + 8 cross-domain. A 7-system ablation
matrix compares OrientIA against fair Mistral / OpenAI / Anthropic
baselines.

### Methodology
* **Judge Model:** Claude Sonnet 4.5 (Anthropic). Run F / G add
  GPT-4o as a second judge and Claude Haiku as a fact-check layer
  to cross-validate the primary judge.
* **Scoring:** Each response is rated from 0 to 3 across six
  dimensions: Institutional Neutrality, Realism, Sourcing, Geographic
  Diversity, Agency, and Discovery (max 18/18).
* **Randomization:** System identities are masked and randomized
  per query (N-system blinding up to N=7).
* **Statistical rigour:** 3 runs per configuration with variance bars
  (IC95%), paired t-tests, Cohen's d, and inter-judge agreement
  (Cohen's κ, Krippendorff's α).

### Baseline Matrix (7 systems)
The scientific ablation isolates the contribution of retrieval vs
prompt engineering :

1. `our_rag` — v3.2 prompt + RAG (full stack)
2. `mistral_neutral` — naïve baseline
3. `mistral_v3_2_no_rag` — **isolates the RAG contribution** alone
4. `gpt4o_neutral` / 5. `gpt4o_v3_2_no_rag` — OpenAI cross-vendor
6. `claude_neutral` / 7. `claude_v3_2_no_rag` — Anthropic cross-vendor

### Adversarial + Cross-Domain Tests
* 10 adversarial questions with fake schools, fake reports, and fake
  towns stress-test the honesty of each system. The `honesty_rate`
  metric measures % of answers that refuse to fabricate.
* 8 cross-domain questions (droit, médecine, architecture, journalisme)
  test generalisation outside the cyber/data training domain.

### Methodological Finding (publishable)
The project uncovered a structural bias in naïve LLM-as-judge
pipelines: the judge rewards *apparent* sourcing (confident citation
of any institution) over *true* sourcing (citations verifiable against
the underlying knowledge base). OrientIA's fact-check layer (Claude
Haiku) penalises fabricated citations, which converts a previously-
neutral gap into a substantial win for the grounded RAG.

---

## Technical Stack

| Component | Technology | Rationale |
| :--- | :--- | :--- |
| **Generation Model** | Mistral Medium | Native French optimization and sovereign infrastructure. |
| **Embedding Model** | mistral-embed | Provider consistency for vector space alignment. |
| **Vector Database** | FAISS | Efficient similarity search without dedicated GPU overhead. |
| **Backend** | FastAPI | Asynchronous Python framework for high-concurrency requests. |
| **Frontend** | React 19 / Tailwind | Modular and lightweight interface. |
| **Infrastructure** | Railway / Vercel | Scalable deployment utilizing free-tier ecosystem. |

---

## Current Status

Active Phase F — a 3-week academic-grade upgrade sprint (2026-04-13
onward). The 32-question PoC benchmark has been expanded to 100
questions with a proper dev / test split (32 / 68) to eliminate the
train-equals-test objection. The 7-system baseline matrix is ready;
Runs F and G will produce the variance-bar publication numbers. See
[`docs/SESSION_HANDOFF.md`](docs/SESSION_HANDOFF.md) for the detailed
project state, run history (10 runs executed), and the working plan.

## Limitations and Ethics

* **Scope:** Currently optimised for the Cyber and Data/AI sectors;
  scaling to the full 14,000+ program catalogue is ongoing. The
  cross-domain test (8 questions outside the training domain) is
  deliberately included to measure graceful fall-back behaviour.
* **Statistical caveats:** Historical runs (6-10) reported scores
  without variance bars. Phase F introduces 3-runs-per-config +
  IC95% to address this.
* **Transparency:** All data used is public, official, and free.
  No illegal scraping or paid APIs were utilised in the construction
  of the knowledge base.
* **Open Science:** This project advocates for "Architectural
  Sovereignty"—the idea that national data and specific logic layers
  are more important for public service than the underlying model
  size.

---

## License

This project is distributed under the MIT License. Developed for the INRIA AI Grand Challenge.
