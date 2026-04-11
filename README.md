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

---

## Evaluation Framework: LLM-as-a-Judge

To validate the system, a double-blind benchmark was conducted using 32 specialized queries, comparing OrientIA against raw Mistral and GPT-4.

### Methodology
* **Juge Model:** Claude 3.5 (Anthropic) was selected as the evaluator to eliminate "self-preference bias" (where a model favors its own generation style).
* **Scoring:** Each response is rated from 0 to 3 across six dimensions: Institutional Neutrality, Realism, Sourcing, Geographic Diversity, Agency, and Discovery.
* **Randomization:** System identities were masked and randomized per query to ensure objective judging.

### Honesty Check (H1/H2)
The benchmark includes procedural questions where RAG offers no inherent advantage. Similar performance across all systems on these questions serves as a control to prove the validity of the specialized scoring on complex queries.

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

## Limitations and Ethics

* **Scope:** Currently optimized for the Cyber and Data/AI sectors; scaling to the full 14,000+ program catalog is ongoing.
* **Transparency:** All data used is public, official, and free. No illegal scraping or paid APIs were utilized in the construction of the knowledge base.
* **Open Science:** This project advocates for "Architectural Sovereignty"—the idea that national data and specific logic layers are more important for public service than the underlying model size.

---

## License

This project is distributed under the MIT License. Developed for the INRIA AI Grand Challenge.
