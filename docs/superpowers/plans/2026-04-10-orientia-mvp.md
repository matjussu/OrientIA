# OrientIA MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a specialized French orientation RAG system that uses label-based re-ranking to correct the marketing bias of general-purpose LLMs, benchmarked against raw Mistral and recorded ChatGPT on 32 questions with a blind Claude judge, and exposed via a minimal React interface.

**Architecture:** Python backend (FastAPI + FAISS + mistralai SDK) orchestrating three layered components: a data pipeline that merges Parcoursup, ONISEP, ROME and SecNumEdu using RNCP as primary key and fuzzy matching as fallback; a RAG pipeline with configurable label-based re-ranking; and a benchmark harness that runs all systems with randomized blind labels and sweeps re-ranking coefficients via grid search. Frontend is a minimal React+Vite chat UI.

**Tech Stack:** Python 3.12, `mistralai`, `faiss-cpu`, `fastapi`, `uvicorn`, `rapidfuzz`, `pandas`, `anthropic` (judge), `numpy`, `matplotlib`, `pytest`, React 19 + Vite, Tailwind, deployed on Vercel (frontend) + Railway (backend).

**Scope (locked):**
- **Domains:** Cybersécurité + Data/IA only (no commerce/droit in V1)
- **Target fiches:** 200-300 structured formation records
- **Language:** French only
- **Benchmark:** 30 official questions + 2 honesty-test questions = 32 total
- **Judge:** Claude via Anthropic API
- **Grid search:** 5 values of label boost coefficients
- **Frontend:** minimal, template React — no polish

---

## File Structure

```
OrientIA/
├── .gitignore
├── .env.example
├── README.md
├── pyproject.toml
├── requirements.txt
├── INRIA_AI_ORIENTATION_PROJECT.md    # (existing spec)
├── V1.md                              # (existing analysis)
├── docs/
│   └── superpowers/
│       └── plans/
│           └── 2026-04-10-orientia-mvp.md  # (this file)
├── data/
│   ├── raw/                           # downloaded snapshots (gitignored)
│   ├── processed/
│   │   └── formations.json            # final merged fiches
│   └── embeddings/
│       └── formations.index           # FAISS binary
├── src/
│   ├── __init__.py
│   ├── config.py                      # env loading
│   ├── collect/
│   │   ├── __init__.py
│   │   ├── normalize.py               # shared text normalization
│   │   ├── parcoursup.py              # download + filter
│   │   ├── onisep.py                  # JWT auth + fetch + filter
│   │   ├── secnumedu.py               # manual list loader
│   │   ├── rome.py                    # ROME 4.0 loader
│   │   └── merge.py                   # RNCP + fuzzy mapping
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── embeddings.py              # mistral-embed wrapper
│   │   ├── index.py                   # FAISS build/load
│   │   ├── retriever.py               # top-k retrieval
│   │   ├── reranker.py                # label-based boost
│   │   ├── generator.py               # Mistral chat
│   │   └── pipeline.py                # end-to-end orchestrator
│   ├── prompt/
│   │   ├── __init__.py
│   │   └── system.py                  # 4-layer system prompt
│   ├── eval/
│   │   ├── __init__.py
│   │   ├── questions.json             # 32 benchmark questions
│   │   ├── ideal_answers.json         # reference answers
│   │   ├── systems.py                 # 3 system wrappers
│   │   ├── runner.py                  # run all systems + blind labels
│   │   ├── judge.py                   # Claude judge
│   │   ├── grid_search.py             # coefficient sweep
│   │   └── analyze.py                 # stats + charts
│   └── api/
│       ├── __init__.py
│       └── main.py                    # FastAPI app
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── api.js
│       └── index.css
├── tests/
│   ├── __init__.py
│   ├── test_normalize.py
│   ├── test_parcoursup.py
│   ├── test_merge.py
│   ├── test_embeddings.py
│   ├── test_retriever.py
│   ├── test_reranker.py
│   ├── test_generator.py
│   ├── test_systems.py
│   ├── test_runner.py
│   ├── test_judge.py
│   └── test_api.py
└── results/
    ├── raw_responses/                 # gitignored
    ├── scores/
    └── charts/
```

---

# Phase 0 — Bootstrap

## Task 0.1: Git repo + base files

**Files:**
- Create: `/home/matteo_linux/projets/OrientIA/.gitignore`
- Create: `/home/matteo_linux/projets/OrientIA/README.md`
- Create: `/home/matteo_linux/projets/OrientIA/.env.example`

- [ ] **Step 1: Initialize git and add remote**

The GitHub repo already exists at https://github.com/matjussu/OrientIA.git (private repo).

Run:
```bash
cd /home/matteo_linux/projets/OrientIA
git init -b main
git config user.name "Matjussu"
git config user.email "matteolepietre@gmail.com"
git remote add origin https://github.com/matjussu/OrientIA.git
```
Expected: `Initialized empty Git repository in .../OrientIA/.git/`

- [ ] **Step 2: Write .gitignore**

Create `.gitignore`:
```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
.pytest_cache/

# Secrets
.env
*.key

# Data (big files)
data/raw/
data/embeddings/*.index
results/raw_responses/

# Node
frontend/node_modules/
frontend/dist/
frontend/.vite/

# OS / editor
.DS_Store
*.swp
.idea/
.vscode/

# Zone identifiers (WSL artifacts)
*:Zone.Identifier
*:mshield
```

- [ ] **Step 3: Write .env.example**

Create `.env.example`:
```dotenv
MISTRAL_API_KEY=your_mistral_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
ONISEP_EMAIL=your_email_here
ONISEP_PASSWORD=your_password_here
ONISEP_APP_ID=your_app_id_here
```

- [ ] **Step 4: Write README.md**

Create `README.md`:
```markdown
# OrientIA

Specialized French-orientation RAG system with label-based re-ranking, benchmarked against general-purpose LLMs.

Submitted to the INRIA AI Grand Challenge.

## Quick start

1. Copy `.env.example` to `.env` and fill in your keys.
2. Install dependencies: `pip install -r requirements.txt`
3. Collect data: `python -m src.collect.merge`
4. Build index: `python -m src.rag.index`
5. Run benchmark: `python -m src.eval.runner`

## Project structure

See `docs/superpowers/plans/2026-04-10-orientia-mvp.md` for the full implementation plan.

## License

MIT
```

- [ ] **Step 5: Stage, commit, and push**

```bash
git add .gitignore .env.example README.md INRIA_AI_ORIENTATION_PROJECT.md V1.md docs/
git commit -m "chore: bootstrap repository with gitignore, readme, env template"
git push -u origin main
```
Expected: `[main (root-commit) xxxxxxx] chore: bootstrap repository...` then successful push.

If the remote already has commits (e.g. an auto-generated README from GitHub), run `git pull --rebase origin main` first, resolve any conflicts, then push.

---

## Task 0.2: Python project + dependencies

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `src/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Write pyproject.toml**

```toml
[project]
name = "orientia"
version = "0.1.0"
description = "Specialized RAG for French student orientation"
requires-python = ">=3.12"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]

[tool.ruff]
line-length = 100
target-version = "py312"
```

- [ ] **Step 2: Write requirements.txt**

```
mistralai>=1.0.0
anthropic>=0.39.0
faiss-cpu>=1.8.0
numpy>=2.0.0
pandas>=2.2.0
rapidfuzz>=3.9.0
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
python-dotenv>=1.0.0
requests>=2.31.0
matplotlib>=3.9.0
pytest>=8.0.0
pytest-cov>=5.0.0
httpx>=0.27.0
```

- [ ] **Step 3: Create empty init files**

```bash
mkdir -p src/collect src/rag src/prompt src/eval src/api tests
touch src/__init__.py src/collect/__init__.py src/rag/__init__.py \
      src/prompt/__init__.py src/eval/__init__.py src/api/__init__.py \
      tests/__init__.py
```

- [ ] **Step 4: Create venv and install**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```
Expected: all packages install without error.

- [ ] **Step 5: Verify install**

```bash
python -c "import mistralai, anthropic, faiss, pandas, rapidfuzz, fastapi; print('OK')"
```
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml requirements.txt src/ tests/
git commit -m "chore: add python project config and dependencies"
```

---

## Task 0.3: Config loader

**Files:**
- Create: `src/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_config.py`:
```python
import os
import pytest
from src.config import Config, load_config


def test_load_config_reads_env(monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "mistral_test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic_test")
    monkeypatch.setenv("ONISEP_EMAIL", "a@b.c")
    monkeypatch.setenv("ONISEP_PASSWORD", "pw")
    monkeypatch.setenv("ONISEP_APP_ID", "app123")

    cfg = load_config()
    assert isinstance(cfg, Config)
    assert cfg.mistral_api_key == "mistral_test"
    assert cfg.anthropic_api_key == "anthropic_test"
    assert cfg.onisep_email == "a@b.c"


def test_load_config_missing_key_raises(monkeypatch):
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="MISTRAL_API_KEY"):
        load_config()
```

- [ ] **Step 2: Run test to see it fail**

```bash
pytest tests/test_config.py -v
```
Expected: `ModuleNotFoundError: No module named 'src.config'`

- [ ] **Step 3: Implement config**

Create `src/config.py`:
```python
import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    mistral_api_key: str
    anthropic_api_key: str
    onisep_email: str
    onisep_password: str
    onisep_app_id: str


def _require(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value


def load_config() -> Config:
    load_dotenv()
    return Config(
        mistral_api_key=_require("MISTRAL_API_KEY"),
        anthropic_api_key=_require("ANTHROPIC_API_KEY"),
        onisep_email=_require("ONISEP_EMAIL"),
        onisep_password=_require("ONISEP_PASSWORD"),
        onisep_app_id=_require("ONISEP_APP_ID"),
    )
```

- [ ] **Step 4: Run test again — PASS**

```bash
pytest tests/test_config.py -v
```
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add src/config.py tests/test_config.py
git commit -m "feat(config): add env-based config loader"
```

---

## Task 0.4: Manual secret setup (human action)

**Files:** `.env` (local only, gitignored)

- [ ] **Step 1: Create Mistral account**

Go to https://console.mistral.ai → sign up → generate API key → copy to `.env`.

- [ ] **Step 2: Create Anthropic account**

Go to https://console.anthropic.com → sign up → API keys → create → copy to `.env`.

- [ ] **Step 3: Create ONISEP account**

Go to https://opendata.onisep.fr/ → sign up → get `Application-ID` → copy email/password/app_id to `.env`.

- [ ] **Step 4: Verify .env loads**

```bash
python -c "from src.config import load_config; c = load_config(); print('mistral:', c.mistral_api_key[:8], '...')"
```
Expected: `mistral: XXXXXXXX ...`

- [ ] **Step 5: Smoke-test APIs**

```bash
python -c "
from mistralai import Mistral
from src.config import load_config
c = load_config()
client = Mistral(api_key=c.mistral_api_key)
r = client.chat.complete(model='mistral-small-latest', messages=[{'role':'user','content':'hi'}])
print('Mistral OK:', r.choices[0].message.content[:40])
"
```
Expected: a response without 401/429 errors.

```bash
python -c "
import anthropic
from src.config import load_config
c = load_config()
client = anthropic.Anthropic(api_key=c.anthropic_api_key)
r = client.messages.create(model='claude-sonnet-4-5', max_tokens=20, messages=[{'role':'user','content':'hi'}])
print('Claude OK:', r.content[0].text[:40])
"
```
Expected: a response without errors.

(No commit — `.env` is gitignored.)

---

# Phase 1 — Evaluation Dataset (first, before any system)

## Task 1.1: Question schema

**Files:**
- Create: `src/eval/questions.json`

- [ ] **Step 1: Write the 32 questions**

Create `src/eval/questions.json`:
```json
{
  "version": "1.0",
  "questions": [
    {"id": "A1", "category": "biais_marketing", "text": "Quelles sont les meilleures formations en cybersécurité en France ?"},
    {"id": "A2", "category": "biais_marketing", "text": "Je veux faire une école de commerce, lesquelles me recommandes-tu ?"},
    {"id": "A3", "category": "biais_marketing", "text": "Quelles écoles d'ingénieur informatique choisir ?"},
    {"id": "A4", "category": "biais_marketing", "text": "Je cherche un master en intelligence artificielle, que recommandes-tu ?"},
    {"id": "A5", "category": "biais_marketing", "text": "Quelles sont les meilleures formations en data science ?"},

    {"id": "B1", "category": "realisme", "text": "J'ai 11 de moyenne en terminale générale, est-ce que je peux intégrer HEC ?"},
    {"id": "B2", "category": "realisme", "text": "Je suis en bac pro commerce, je veux faire médecine, c'est possible ?"},
    {"id": "B3", "category": "realisme", "text": "J'ai un bac techno STI2D, je peux aller en prépa MP ?"},
    {"id": "B4", "category": "realisme", "text": "Je veux intégrer l'X avec un dossier moyen, comment faire ?"},
    {"id": "B5", "category": "realisme", "text": "J'ai 13 de moyenne, est-ce que Sciences Po Paris est réaliste ?"},

    {"id": "C1", "category": "decouverte", "text": "J'aime les données et la géopolitique, quels métiers existent ?"},
    {"id": "C2", "category": "decouverte", "text": "Je suis passionné par la mer et la technologie, que faire ?"},
    {"id": "C3", "category": "decouverte", "text": "J'aime écrire et j'adore les sciences, quel métier combinerait les deux ?"},
    {"id": "C4", "category": "decouverte", "text": "Je veux travailler dans la sécurité mais pas être policier, quelles options ?"},
    {"id": "C5", "category": "decouverte", "text": "J'aime la nature et l'informatique, est-ce compatible ?"},

    {"id": "D1", "category": "diversite_geo", "text": "Quelles bonnes formations existent à Perpignan ?"},
    {"id": "D2", "category": "diversite_geo", "text": "Je suis à Brest, quelles sont mes options en informatique sans déménager ?"},
    {"id": "D3", "category": "diversite_geo", "text": "Y a-t-il de bonnes formations d'ingénieur hors Paris ?"},
    {"id": "D4", "category": "diversite_geo", "text": "Je veux rester en Occitanie, qu'est-ce qui existe en IA ?"},
    {"id": "D5", "category": "diversite_geo", "text": "Quelles formations accessibles en cybersécurité en Bretagne ?"},

    {"id": "E1", "category": "passerelles", "text": "Je suis en L2 droit et je veux me réorienter vers l'informatique, comment ?"},
    {"id": "E2", "category": "passerelles", "text": "J'ai un BTS SIO, je peux faire un master ensuite ?"},
    {"id": "E3", "category": "passerelles", "text": "Je suis en école de commerce mais je veux faire de la data, quelles passerelles ?"},
    {"id": "E4", "category": "passerelles", "text": "J'ai raté ma PACES, quelles alternatives dans la santé ?"},
    {"id": "E5", "category": "passerelles", "text": "Je travaille depuis 3 ans, je veux reprendre mes études en cyber, comment ?"},

    {"id": "F1", "category": "comparaison", "text": "Compare ENSEIRB-MATMECA et EPITA pour la cybersécurité"},
    {"id": "F2", "category": "comparaison", "text": "Dauphine vs école de commerce pour travailler en finance ?"},
    {"id": "F3", "category": "comparaison", "text": "BTS SIO vs BUT informatique : lequel choisir ?"},
    {"id": "F4", "category": "comparaison", "text": "Licence info à la fac vs prépa MP : avantages et inconvénients ?"},
    {"id": "F5", "category": "comparaison", "text": "Master IA à Toulouse vs Saclay : quelles différences ?"},

    {"id": "H1", "category": "honnetete", "text": "C'est quoi une licence universitaire en France ?"},
    {"id": "H2", "category": "honnetete", "text": "Comment fonctionne Parcoursup et quand sont les échéances ?"}
  ]
}
```

Note: categories A-F are scored questions; H1-H2 are honesty tests where RAG is not expected to outperform — they prove we don't cherry-pick.

- [ ] **Step 2: Write schema validator test**

Create `tests/test_questions.py`:
```python
import json
from pathlib import Path


def test_questions_file_exists_and_valid():
    path = Path("src/eval/questions.json")
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "questions" in data
    assert len(data["questions"]) == 32

    ids = [q["id"] for q in data["questions"]]
    assert len(ids) == len(set(ids)), "duplicate question ids"

    categories = {q["category"] for q in data["questions"]}
    assert categories == {
        "biais_marketing", "realisme", "decouverte",
        "diversite_geo", "passerelles", "comparaison", "honnetete"
    }

    for q in data["questions"]:
        assert q["text"].strip()
        assert q["id"][0] in "ABCDEFH"
```

- [ ] **Step 3: Run test — PASS**

```bash
pytest tests/test_questions.py -v
```
Expected: `1 passed`

- [ ] **Step 4: Commit**

```bash
git add src/eval/questions.json tests/test_questions.py
git commit -m "feat(eval): add 32 benchmark questions (30 scored + 2 honesty)"
```

---

## Task 1.2: Ideal answer sketches

**Files:**
- Create: `src/eval/ideal_answers.json`

- [ ] **Step 1: Write ideal answers for 10 questions (2 per category for spot-check)**

These are not scored automatically; they are human references used during analysis to verify the judge isn't drifting.

Create `src/eval/ideal_answers.json`:
```json
{
  "A1": {
    "key_points": [
      "Doit citer au moins 3 formations labellisées SecNumEdu ANSSI",
      "Doit inclure au moins une formation publique (CyberSchool Rennes, ENSIBS, Télécom Paris, IMT Atlantique, ENSSAT)",
      "Doit mentionner le label SecNumEdu explicitement",
      "Ne doit PAS se limiter à EPITA/Guardia/écoles privées à fort SEO"
    ],
    "must_include_labels": ["SecNumEdu"],
    "must_include_status": ["Public"]
  },
  "A4": {
    "key_points": [
      "Doit citer des masters publics reconnus (MVA Saclay, IASD Dauphine-PSL, Master IA Sorbonne Université)",
      "Doit mentionner les écoles d'ingénieurs publiques avec parcours IA",
      "Doit mentionner la sélectivité réelle"
    ],
    "must_include_status": ["Public"]
  },
  "B1": {
    "key_points": [
      "Doit dire clairement que HEC est extrêmement sélectif",
      "Doit donner un chiffre (taux d'admission ~4%)",
      "Doit proposer des alternatives réalistes (SKEMA, Audencia, Grenoble EM, admissions parallèles)",
      "Ne doit PAS dire 'tout est possible avec de la motivation'"
    ],
    "must_not_include_phrase": ["tout est possible", "rien n'est impossible"]
  },
  "B4": {
    "key_points": [
      "Doit mentionner le taux d'admission de l'X (~5-7%)",
      "Doit recommander prépas CPGE ou concours directs selon profil",
      "Doit proposer des alternatives INSA, Centrale-Supélec, ENS",
      "Doit être honnête sur la difficulté"
    ]
  },
  "C4": {
    "key_points": [
      "Doit explorer cybersécurité, intelligence économique, OSINT",
      "Doit citer des métiers ROME concrets (analyste SOC, consultant, auditeur)",
      "Doit proposer des formations labellisées SecNumEdu"
    ]
  },
  "D5": {
    "key_points": [
      "Doit citer spécifiquement CyberSchool Rennes, ENSIBS Vannes, IMT Atlantique Brest",
      "Doit mentionner le label SecNumEdu",
      "Doit varier les niveaux (BUT, master, ingénieur)"
    ],
    "must_include_cities": ["Rennes", "Brest", "Vannes"]
  },
  "E5": {
    "key_points": [
      "Doit mentionner le CPF, la VAE, les formations en alternance",
      "Doit citer des parcours concrets (Master Cyber en alternance, MS spécialisé)",
      "Doit parler du public adulte / formation continue"
    ]
  },
  "F1": {
    "key_points": [
      "Doit noter qu'ENSEIRB-MATMECA est publique (Bordeaux INP, CTI) et EPITA privée",
      "Doit comparer les coûts (droits publics vs 9-10k€/an)",
      "Doit noter que l'ENSEIRB a un parcours SecNumEdu"
    ]
  },
  "H1": {
    "key_points": [
      "Doit expliquer la durée (3 ans, 180 ECTS)",
      "Doit mentionner LMD / Bologne",
      "Doit expliquer la poursuite possible en master",
      "Question générique : le RAG n'est PAS attendu comme supérieur ici"
    ],
    "rag_expected_advantage": false
  },
  "H2": {
    "key_points": [
      "Doit expliquer le calendrier (inscription janvier, vœux mars, réponses mai-juin)",
      "Doit expliquer les types de vœux (non hiérarchisés sauf sous-vœux)",
      "Question procédurale : le RAG n'est PAS attendu comme supérieur ici"
    ],
    "rag_expected_advantage": false
  }
}
```

- [ ] **Step 2: Add validation test**

Append to `tests/test_questions.py`:
```python
def test_ideal_answers_reference_valid_ids():
    questions = json.loads(Path("src/eval/questions.json").read_text(encoding="utf-8"))
    ideal = json.loads(Path("src/eval/ideal_answers.json").read_text(encoding="utf-8"))
    valid_ids = {q["id"] for q in questions["questions"]}
    for qid in ideal:
        assert qid in valid_ids, f"ideal_answers references unknown id: {qid}"
```

- [ ] **Step 3: Run tests**

```bash
pytest tests/test_questions.py -v
```
Expected: `2 passed`

- [ ] **Step 4: Commit**

```bash
git add src/eval/ideal_answers.json tests/test_questions.py
git commit -m "feat(eval): add ideal-answer sketches for 10 spot-check questions"
```

---

# Phase 2 — Data Collection

`★ Insight ─────────────────────────────────────`
This is the riskiest phase. The Parcoursup↔ONISEP join is the hidden critical path. We tackle it with RNCP first (structured key), `rapidfuzz` fuzzy matching second (name+city). We accept 70-80% join rate and document it as a known limitation. No grandiose ambition — lean data, then RAG.
`─────────────────────────────────────────────────`

## Task 2.1: Text normalization helpers

**Files:**
- Create: `src/collect/normalize.py`
- Create: `tests/test_normalize.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_normalize.py`:
```python
from src.collect.normalize import normalize_name, normalize_city


def test_normalize_name_removes_accents_and_articles():
    assert normalize_name("Université de Rennes") == "universite rennes"
    assert normalize_name("École d'ingénieurs de Brest") == "ecole ingenieurs brest"
    assert normalize_name("INSA Centre-Val de Loire") == "insa centre val loire"


def test_normalize_name_collapses_whitespace():
    assert normalize_name("  Master    IA  ") == "master ia"


def test_normalize_city_lowercases_strips_accents():
    assert normalize_city("Saint-Étienne") == "saint etienne"
    assert normalize_city("PARIS") == "paris"
```

- [ ] **Step 2: Run test — FAIL**

```bash
pytest tests/test_normalize.py -v
```
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement**

Create `src/collect/normalize.py`:
```python
import re
import unicodedata


_STOPWORDS = {"de", "du", "des", "la", "le", "les", "d", "l"}


def _strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _clean(text: str) -> str:
    text = _strip_accents(text).lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_name(text: str) -> str:
    cleaned = _clean(text)
    tokens = [t for t in cleaned.split() if t not in _STOPWORDS]
    return " ".join(tokens)


def normalize_city(text: str) -> str:
    return _clean(text)
```

- [ ] **Step 4: Run test — PASS**

```bash
pytest tests/test_normalize.py -v
```
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add src/collect/normalize.py tests/test_normalize.py
git commit -m "feat(collect): add text normalization helpers"
```

---

## Task 2.2: Parcoursup CSV download + filter

**Files:**
- Create: `src/collect/parcoursup.py`
- Create: `tests/test_parcoursup.py`
- Data: `data/raw/parcoursup_2025.csv` (manual download)

- [ ] **Step 1: Manual download**

Go to https://data.education.gouv.fr/explore/dataset/fr-esr-parcoursup/ → click "Export" → CSV → save to `data/raw/parcoursup_2025.csv`.

```bash
mkdir -p data/raw
ls -lh data/raw/parcoursup_2025.csv
```
Expected: file exists, ~40-80 MB.

- [ ] **Step 2: Inspect columns**

```bash
python -c "
import pandas as pd
df = pd.read_csv('data/raw/parcoursup_2025.csv', sep=';', nrows=5, encoding='utf-8')
print(list(df.columns))
print(df.shape)
" | head -50
```
Expected: list of column names. Note the columns for formation name, établissement, city, RNCP code (if present), taux d'accès, effectif.

- [ ] **Step 3: Write failing test**

Create `tests/test_parcoursup.py`:
```python
import pandas as pd
from src.collect.parcoursup import load_parcoursup, filter_domain, DOMAIN_KEYWORDS


def test_domain_keywords_defined():
    assert "cyber" in DOMAIN_KEYWORDS
    assert "data_ia" in DOMAIN_KEYWORDS
    assert any("cybersécurité" in kw.lower() or "cyber" in kw.lower()
               for kw in DOMAIN_KEYWORDS["cyber"])
    assert any("data" in kw.lower() or "intelligence artificielle" in kw.lower()
               for kw in DOMAIN_KEYWORDS["data_ia"])


def test_filter_domain_keeps_cyber_entries():
    df = pd.DataFrame({
        "formation": [
            "Master Cybersécurité",
            "Licence Histoire",
            "BUT Informatique parcours cyber",
            "BTS Comptabilité",
        ]
    })
    filtered = filter_domain(df, "cyber", name_column="formation")
    assert len(filtered) == 2
    assert "Histoire" not in filtered["formation"].values
```

- [ ] **Step 4: Run test — FAIL**

```bash
pytest tests/test_parcoursup.py -v
```

- [ ] **Step 5: Implement**

Create `src/collect/parcoursup.py`:
```python
from pathlib import Path
import pandas as pd


DOMAIN_KEYWORDS = {
    "cyber": [
        "cybersécurité", "cyber sécurité", "cyber-sécurité", "cybersecurity",
        "sécurité informatique", "sécurité des systèmes", "sécurité numérique",
        "SSI", "SecNumEdu",
    ],
    "data_ia": [
        "intelligence artificielle", "data science", "données", "data",
        "machine learning", "apprentissage automatique", "big data",
        "IA", "science des données", "data analyst", "data engineer",
    ],
}


def load_parcoursup(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    return pd.read_csv(path, sep=";", encoding="utf-8", low_memory=False)


def filter_domain(df: pd.DataFrame, domain: str, name_column: str) -> pd.DataFrame:
    if domain not in DOMAIN_KEYWORDS:
        raise ValueError(f"Unknown domain: {domain}")
    keywords = DOMAIN_KEYWORDS[domain]
    pattern = "|".join(keywords)
    mask = df[name_column].fillna("").str.contains(pattern, case=False, regex=True)
    return df[mask].copy()
```

- [ ] **Step 6: Run test — PASS**

```bash
pytest tests/test_parcoursup.py -v
```

- [ ] **Step 7: Explore real data interactively**

```bash
python -c "
from src.collect.parcoursup import load_parcoursup, filter_domain
df = load_parcoursup('data/raw/parcoursup_2025.csv')
print('Total rows:', len(df))
print('Columns with \"formation\":', [c for c in df.columns if 'formation' in c.lower() or 'nom' in c.lower()][:10])
print('Columns with \"rncp\":', [c for c in df.columns if 'rncp' in c.lower()])
print('Columns with \"ville\" or \"commune\":', [c for c in df.columns if 'ville' in c.lower() or 'commune' in c.lower()][:5])
"
```

Record the exact column names for `formation`, `etablissement`, `ville`, `rncp`, `taux_acces`. Use them in the next step.

- [ ] **Step 8: Extend with extractor function**

Append to `src/collect/parcoursup.py`:
```python
# Column name mappings — adjust after Step 7 based on actual CSV columns.
COLUMN_MAP = {
    "formation": "fili",              # exact name from inspection
    "etablissement": "g_ea_lib_vx",   # establishment label
    "ville": "ville_etab",             # city
    "rncp": "rncp",                    # may be absent
    "taux_acces": "tx_acces",          # taux d'accès
    "places": "capa_fin",              # capacity
}


def extract_fiche(row: pd.Series) -> dict:
    return {
        "source": "parcoursup",
        "nom": str(row.get(COLUMN_MAP["formation"], "")).strip(),
        "etablissement": str(row.get(COLUMN_MAP["etablissement"], "")).strip(),
        "ville": str(row.get(COLUMN_MAP["ville"], "")).strip(),
        "rncp": str(row.get(COLUMN_MAP["rncp"], "")).strip() or None,
        "taux_acces_parcoursup_2025": _safe_float(row.get(COLUMN_MAP["taux_acces"])),
        "nombre_places": _safe_int(row.get(COLUMN_MAP["places"])),
    }


def _safe_float(val) -> float | None:
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_int(val) -> int | None:
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def collect_parcoursup_fiches(path: str | Path) -> list[dict]:
    df = load_parcoursup(path)
    all_fiches = []
    for domain in ("cyber", "data_ia"):
        filtered = filter_domain(df, domain, COLUMN_MAP["formation"])
        for _, row in filtered.iterrows():
            fiche = extract_fiche(row)
            fiche["domaine"] = domain
            all_fiches.append(fiche)
    return all_fiches
```

- [ ] **Step 9: Commit**

```bash
git add src/collect/parcoursup.py tests/test_parcoursup.py
git commit -m "feat(collect): parcoursup csv loader with domain filter"
```

---

## Task 2.3: ONISEP JWT auth + fetch

**Files:**
- Create: `src/collect/onisep.py`
- Create: `tests/test_onisep.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_onisep.py`:
```python
from unittest.mock import patch, MagicMock
from src.collect.onisep import authenticate, fetch_formations


def test_authenticate_returns_token():
    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = {"token": "jwt_fake_token"}

    with patch("src.collect.onisep.requests.post", return_value=fake_response) as mock_post:
        token = authenticate("a@b.c", "pw")
        assert token == "jwt_fake_token"
        mock_post.assert_called_once()


def test_fetch_formations_uses_token_and_app_id():
    fake = MagicMock()
    fake.status_code = 200
    fake.json.return_value = {"results": [{"nom": "Master IA"}]}

    with patch("src.collect.onisep.requests.get", return_value=fake) as mock_get:
        data = fetch_formations("tok", "appid", query="intelligence artificielle")
        assert data == [{"nom": "Master IA"}]
        headers = mock_get.call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer tok"
        assert headers["Application-ID"] == "appid"
```

- [ ] **Step 2: Run test — FAIL**

```bash
pytest tests/test_onisep.py -v
```

- [ ] **Step 3: Implement**

Create `src/collect/onisep.py`:
```python
import json
from pathlib import Path
import requests


AUTH_URL = "https://api.opendata.onisep.fr/api/1.0/login"
FORMATIONS_DATASET = "5fa591127f501"
SEARCH_URL = f"https://api.opendata.onisep.fr/api/1.0/dataset/{FORMATIONS_DATASET}/search"


def authenticate(email: str, password: str) -> str:
    resp = requests.post(AUTH_URL, data={"email": email, "password": password}, timeout=30)
    resp.raise_for_status()
    return resp.json()["token"]


def fetch_formations(token: str, app_id: str, query: str, size: int = 500) -> list[dict]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Application-ID": app_id,
    }
    params = {"q": query, "size": size}
    resp = requests.get(SEARCH_URL, headers=headers, params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data.get("results", [])


def save_raw(data: list[dict], path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def collect_onisep_fiches(email: str, password: str, app_id: str) -> list[dict]:
    token = authenticate(email, password)
    fiches = []
    for domain, query in [
        ("cyber", "cybersécurité"),
        ("data_ia", "intelligence artificielle"),
        ("data_ia", "data science"),
    ]:
        results = fetch_formations(token, app_id, query)
        for r in results:
            fiches.append({
                "source": "onisep",
                "domaine": domain,
                "nom": r.get("libelle_formation_principal") or r.get("nom") or "",
                "etablissement": r.get("nom_etab") or r.get("etablissement") or "",
                "ville": r.get("lib_com") or r.get("ville") or "",
                "rncp": r.get("code_rncp") or None,
                "url_onisep": r.get("url_onisep") or r.get("url") or None,
                "type_diplome": r.get("type_formation_court") or None,
                "statut": r.get("statut") or None,
            })
    return fiches
```

- [ ] **Step 4: Run test — PASS**

```bash
pytest tests/test_onisep.py -v
```

- [ ] **Step 5: Smoke-test against real API**

```bash
python -c "
from src.config import load_config
from src.collect.onisep import collect_onisep_fiches, save_raw
c = load_config()
fiches = collect_onisep_fiches(c.onisep_email, c.onisep_password, c.onisep_app_id)
print(f'Got {len(fiches)} ONISEP fiches')
save_raw(fiches, 'data/raw/onisep_formations.json')
"
```
Expected: a number like 200-800 fiches; file saved.

If field names don't match real API response, iterate on the mapping in Step 3, re-run.

- [ ] **Step 6: Commit**

```bash
git add src/collect/onisep.py tests/test_onisep.py
git commit -m "feat(collect): onisep jwt auth and formations fetch"
```

---

## Task 2.4: SecNumEdu manual list

**Files:**
- Create: `src/collect/secnumedu.py`
- Create: `data/raw/secnumedu.json` (manual)

- [ ] **Step 1: Manually scrape cyber.gouv.fr/secnumedu**

Visit https://cyber.gouv.fr/secnumedu. Copy the labelled formations list. Format as JSON.

Create `data/raw/secnumedu.json`:
```json
[
  {"nom": "Cybersécurité des systèmes d'information", "etablissement": "ENSIBS", "ville": "Vannes"},
  {"nom": "Master Cybersécurité CyberSchool", "etablissement": "Université de Rennes", "ville": "Rennes"},
  {"nom": "Ingénieur Cybersécurité", "etablissement": "IMT Atlantique", "ville": "Brest"},
  {"nom": "Mastère Spécialisé Cybersécurité", "etablissement": "Télécom Paris", "ville": "Palaiseau"},
  {"nom": "Master CRYPTIS", "etablissement": "Université de Limoges", "ville": "Limoges"},
  {"nom": "Master Cybersécurité", "etablissement": "ENSEIRB-MATMECA", "ville": "Bordeaux"},
  {"nom": "Master Cybersécurité", "etablissement": "EURECOM", "ville": "Biot"},
  {"nom": "Master Cybersécurité", "etablissement": "INSA Centre Val de Loire", "ville": "Bourges"},
  {"nom": "Master Cybersécurité", "etablissement": "Télécom SudParis", "ville": "Évry"},
  {"nom": "Mastère Spécialisé Cybersécurité", "etablissement": "ENSSAT", "ville": "Lannion"}
]
```

(Continue with the full ~80 formations from the official list. This is manual work estimated at 1-2h.)

- [ ] **Step 2: Write loader test**

Create `tests/test_secnumedu.py`:
```python
import json
from pathlib import Path
from src.collect.secnumedu import load_secnumedu


def test_load_secnumedu_returns_list_with_label(tmp_path):
    data = [{"nom": "Test", "etablissement": "Univ X", "ville": "Paris"}]
    path = tmp_path / "secnumedu.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    fiches = load_secnumedu(path)
    assert len(fiches) == 1
    assert fiches[0]["labels"] == ["SecNumEdu"]
    assert fiches[0]["source"] == "secnumedu"
    assert fiches[0]["domaine"] == "cyber"
```

- [ ] **Step 3: Run test — FAIL**

```bash
pytest tests/test_secnumedu.py -v
```

- [ ] **Step 4: Implement**

Create `src/collect/secnumedu.py`:
```python
import json
from pathlib import Path


def load_secnumedu(path: str | Path) -> list[dict]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    fiches = []
    for entry in raw:
        fiches.append({
            "source": "secnumedu",
            "domaine": "cyber",
            "nom": entry["nom"],
            "etablissement": entry["etablissement"],
            "ville": entry["ville"],
            "rncp": entry.get("rncp"),
            "labels": ["SecNumEdu"],
        })
    return fiches
```

- [ ] **Step 5: Run test — PASS**

```bash
pytest tests/test_secnumedu.py -v
```

- [ ] **Step 6: Commit**

```bash
git add src/collect/secnumedu.py data/raw/secnumedu.json tests/test_secnumedu.py
git commit -m "feat(collect): secnumedu list loader + manually structured snapshot"
```

---

## Task 2.5: ROME 4.0 loader (débouchés metadata)

**Files:**
- Create: `src/collect/rome.py`
- Create: `tests/test_rome.py`
- Data: `data/raw/rome_4_0.csv` (manual download)

- [ ] **Step 1: Download ROME 4.0**

Go to https://www.francetravail.org/opendata/repertoire-operationnel-des-meti.html → download CSV → save to `data/raw/rome_4_0.csv`.

- [ ] **Step 2: Write failing test**

Create `tests/test_rome.py`:
```python
from src.collect.rome import load_rome_job_titles


def test_load_rome_returns_code_to_title_mapping(tmp_path):
    csv = tmp_path / "rome.csv"
    csv.write_text(
        "code_rome;libelle\n"
        "M1802;Expertise et support en systèmes d'information\n"
        "M1805;Études et développement informatique\n",
        encoding="utf-8",
    )
    mapping = load_rome_job_titles(csv)
    assert mapping["M1802"] == "Expertise et support en systèmes d'information"
    assert mapping["M1805"] == "Études et développement informatique"
```

- [ ] **Step 3: Run test — FAIL**

```bash
pytest tests/test_rome.py -v
```

- [ ] **Step 4: Implement**

Create `src/collect/rome.py`:
```python
from pathlib import Path
import pandas as pd


RELEVANT_ROME_CODES = {
    # Cyber
    "M1802": "Expertise et support en systèmes d'information",
    "M1805": "Études et développement informatique",
    "M1803": "Direction des systèmes d'information",
    "M1801": "Administration de systèmes d'information",
    # Data / IA
    "M1403": "Études et prospective socio-économiques",
    "M1811": "Data engineer",
}


def load_rome_job_titles(path: str | Path) -> dict[str, str]:
    df = pd.read_csv(path, sep=";", encoding="utf-8")
    if "code_rome" not in df.columns:
        df.columns = [c.lower().replace("é", "e").replace("è", "e") for c in df.columns]
    return dict(zip(df["code_rome"], df["libelle"]))


def get_debouches_for_domain(domain: str) -> list[dict]:
    codes = {
        "cyber": ["M1802", "M1805", "M1803", "M1801"],
        "data_ia": ["M1811", "M1805", "M1403"],
    }[domain]
    return [{"code_rome": c, "libelle": RELEVANT_ROME_CODES.get(c, c)} for c in codes]
```

- [ ] **Step 5: Run test — PASS**

```bash
pytest tests/test_rome.py -v
```

- [ ] **Step 6: Commit**

```bash
git add src/collect/rome.py tests/test_rome.py
git commit -m "feat(collect): rome 4.0 job title loader for debouches"
```

---

## Task 2.6: Merge — RNCP-first with fuzzy fallback

**Files:**
- Create: `src/collect/merge.py`
- Create: `tests/test_merge.py`

`★ Insight ─────────────────────────────────────`
This is the critical path. `rapidfuzz.token_set_ratio` handles token-order differences ("Master IA Toulouse" vs "Toulouse Master IA") and is 3-5x faster than `fuzzywuzzy`. We normalize first, then match. Threshold 85 is empirical — tune with real data. We merge ONISEP→Parcoursup (to attach taux_acces) and SecNumEdu→merged (to attach labels).
`─────────────────────────────────────────────────`

- [ ] **Step 1: Write failing test**

Create `tests/test_merge.py`:
```python
from src.collect.merge import merge_by_rncp, fuzzy_match_fiches, merge_all


def test_merge_by_rncp_joins_matching_codes():
    parcoursup = [
        {"nom": "Master IA", "ville": "Paris", "rncp": "12345", "taux_acces_parcoursup_2025": 25.0},
    ]
    onisep = [
        {"nom": "Master Intelligence Artificielle", "ville": "Paris", "rncp": "12345",
         "url_onisep": "http://onisep.fr/x"},
    ]
    merged = merge_by_rncp(parcoursup, onisep)
    assert len(merged) == 1
    assert merged[0]["rncp"] == "12345"
    assert merged[0]["taux_acces_parcoursup_2025"] == 25.0
    assert merged[0]["url_onisep"] == "http://onisep.fr/x"


def test_fuzzy_match_joins_similar_names():
    parcoursup_orphans = [
        {"nom": "Master Cybersécurité", "etablissement": "ENSIBS",
         "ville": "Vannes", "rncp": None, "taux_acces_parcoursup_2025": 18.0},
    ]
    onisep_orphans = [
        {"nom": "Master cyber", "etablissement": "ensibs",
         "ville": "vannes", "rncp": None, "url_onisep": "http://x"},
    ]
    merged = fuzzy_match_fiches(parcoursup_orphans, onisep_orphans, threshold=75)
    assert len(merged) == 1
    assert merged[0]["url_onisep"] == "http://x"


def test_merge_all_attaches_secnumedu_labels():
    parcoursup = [{"nom": "Master Cyber", "etablissement": "ENSIBS", "ville": "Vannes",
                   "rncp": None, "taux_acces_parcoursup_2025": 22.0}]
    onisep = []
    secnumedu = [{"nom": "Master Cyber", "etablissement": "ENSIBS", "ville": "Vannes",
                  "labels": ["SecNumEdu"]}]
    merged = merge_all(parcoursup, onisep, secnumedu)
    assert len(merged) == 1
    assert "SecNumEdu" in merged[0]["labels"]
```

- [ ] **Step 2: Run test — FAIL**

```bash
pytest tests/test_merge.py -v
```

- [ ] **Step 3: Implement**

Create `src/collect/merge.py`:
```python
from rapidfuzz import fuzz
from src.collect.normalize import normalize_name, normalize_city


def merge_by_rncp(parcoursup: list[dict], onisep: list[dict]) -> list[dict]:
    onisep_by_rncp = {f["rncp"]: f for f in onisep if f.get("rncp")}
    merged = []
    for ps in parcoursup:
        rncp = ps.get("rncp")
        if rncp and rncp in onisep_by_rncp:
            merged_fiche = {**onisep_by_rncp[rncp], **ps}
            merged_fiche["match_method"] = "rncp"
            merged.append(merged_fiche)
    return merged


def _signature(fiche: dict) -> str:
    return f"{normalize_name(fiche.get('nom',''))} {normalize_name(fiche.get('etablissement',''))} {normalize_city(fiche.get('ville',''))}"


def fuzzy_match_fiches(
    parcoursup: list[dict],
    onisep: list[dict],
    threshold: int = 85,
) -> list[dict]:
    onisep_sigs = [(f, _signature(f)) for f in onisep]
    merged = []
    for ps in parcoursup:
        ps_sig = _signature(ps)
        best_score = 0
        best_onisep = None
        for onisep_fiche, on_sig in onisep_sigs:
            score = fuzz.token_set_ratio(ps_sig, on_sig)
            if score > best_score:
                best_score = score
                best_onisep = onisep_fiche
        if best_onisep and best_score >= threshold:
            merged_fiche = {**best_onisep, **ps}
            merged_fiche["match_method"] = f"fuzzy_{best_score}"
            merged.append(merged_fiche)
    return merged


def attach_labels(fiches: list[dict], secnumedu: list[dict]) -> list[dict]:
    sec_sigs = [(f, _signature(f)) for f in secnumedu]
    for f in fiches:
        f_sig = _signature(f)
        existing_labels = list(f.get("labels", []))
        for sec, sec_sig in sec_sigs:
            score = fuzz.token_set_ratio(f_sig, sec_sig)
            if score >= 85:
                for label in sec.get("labels", []):
                    if label not in existing_labels:
                        existing_labels.append(label)
                break
        f["labels"] = existing_labels
    return fiches


def merge_all(
    parcoursup: list[dict],
    onisep: list[dict],
    secnumedu: list[dict],
    fuzzy_threshold: int = 85,
) -> list[dict]:
    # Step 1: RNCP matching
    rncp_matched = merge_by_rncp(parcoursup, onisep)
    matched_rncps = {f.get("rncp") for f in rncp_matched if f.get("rncp")}

    # Step 2: Fuzzy matching on parcoursup orphans against onisep orphans
    ps_orphans = [p for p in parcoursup
                  if not p.get("rncp") or p.get("rncp") not in matched_rncps]
    onisep_orphans = [o for o in onisep
                      if not o.get("rncp") or o.get("rncp") not in matched_rncps]
    fuzzy_matched = fuzzy_match_fiches(ps_orphans, onisep_orphans, fuzzy_threshold)

    # Step 3: Parcoursup-only (kept even without ONISEP enrichment —
    # taux d'accès is the most critical field and we don't want to lose it)
    fuzzy_matched_sigs = {_signature(f) for f in fuzzy_matched}
    ps_only = []
    for p in ps_orphans:
        if _signature(p) not in fuzzy_matched_sigs:
            p_copy = dict(p)
            p_copy["match_method"] = "parcoursup_only"
            ps_only.append(p_copy)

    all_merged = rncp_matched + fuzzy_matched + ps_only

    # Step 4: Attach SecNumEdu labels
    all_merged = attach_labels(all_merged, secnumedu)

    # Step 5: Infer statut from establishment name when missing
    for f in all_merged:
        if not f.get("statut"):
            est = normalize_name(f.get("etablissement", ""))
            if any(pub in est for pub in ["universite", "ecole normale", "institut national",
                                           "ecole nationale", "insa", "ens", "cnam",
                                           "imt", "telecom paris", "polytechnique"]):
                f["statut"] = "Public"
            else:
                f["statut"] = "Inconnu"
        f.setdefault("labels", [])

    return all_merged
```

- [ ] **Step 4: Run test — PASS**

```bash
pytest tests/test_merge.py -v
```

- [ ] **Step 5: Run full merge on real data**

Create a helper script `src/collect/run_merge.py`:
```python
import json
from pathlib import Path
from src.collect.parcoursup import collect_parcoursup_fiches
from src.collect.secnumedu import load_secnumedu
from src.collect.merge import merge_all


def main():
    ps = collect_parcoursup_fiches("data/raw/parcoursup_2025.csv")
    onisep_raw = json.loads(Path("data/raw/onisep_formations.json").read_text(encoding="utf-8"))
    sec = load_secnumedu("data/raw/secnumedu.json")

    merged = merge_all(ps, onisep_raw, sec)
    print(f"Parcoursup input: {len(ps)}")
    print(f"ONISEP input: {len(onisep_raw)}")
    print(f"SecNumEdu input: {len(sec)}")
    print(f"Merged output: {len(merged)}")

    rncp_count = sum(1 for f in merged if f.get("match_method") == "rncp")
    fuzzy_count = sum(1 for f in merged if f.get("match_method", "").startswith("fuzzy"))
    labelled = sum(1 for f in merged if f.get("labels"))
    print(f"  via RNCP: {rncp_count}")
    print(f"  via fuzzy: {fuzzy_count}")
    print(f"  with labels: {labelled}")

    Path("data/processed").mkdir(parents=True, exist_ok=True)
    Path("data/processed/formations.json").write_text(
        json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Saved to data/processed/formations.json")


if __name__ == "__main__":
    main()
```

Run:
```bash
python -m src.collect.run_merge
```

Expected output: 200-500 merged fiches, with RNCP match on ~30-50% and fuzzy on ~20-40%. If join rate is below 50%, tune `fuzzy_threshold` down to 80 and re-run.

- [ ] **Step 6: Commit**

```bash
git add src/collect/merge.py src/collect/run_merge.py tests/test_merge.py data/processed/formations.json
git commit -m "feat(collect): rncp+fuzzy merge pipeline producing formations.json"
```

---

# Phase 3 — RAG Pipeline

## Task 3.1: System prompt module

**Files:**
- Create: `src/prompt/system.py`
- Create: `tests/test_system_prompt.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_system_prompt.py`:
```python
from src.prompt.system import SYSTEM_PROMPT, build_user_prompt


def test_system_prompt_contains_neutrality_rules():
    assert "SecNumEdu" in SYSTEM_PROMPT or "labels officiels" in SYSTEM_PROMPT
    assert "biais marketing" in SYSTEM_PROMPT.lower()


def test_system_prompt_contains_realism_thresholds():
    assert "10" in SYSTEM_PROMPT and "30" in SYSTEM_PROMPT
    assert "taux d'accès" in SYSTEM_PROMPT.lower()


def test_system_prompt_forbids_yes_man():
    assert "tout est possible" in SYSTEM_PROMPT.lower()


def test_build_user_prompt_injects_context():
    context = "FICHE 1: Master Cyber Rennes..."
    question = "Quelles formations cyber ?"
    result = build_user_prompt(context, question)
    assert context in result
    assert question in result
```

- [ ] **Step 2: Run test — FAIL**

```bash
pytest tests/test_system_prompt.py -v
```

- [ ] **Step 3: Implement**

Create `src/prompt/system.py`:
```python
SYSTEM_PROMPT = """Tu es un conseiller d'orientation spécialisé dans le système éducatif français.
Tu aides les lycéens et étudiants à explorer des formations et des métiers en t'appuyant
EXCLUSIVEMENT sur des données officielles vérifiables.

Tu n'es PAS un moteur de recherche web. Tu ne recommandes JAMAIS une formation sur la base
de sa visibilité en ligne. Tu privilégies les critères objectifs : labels officiels
(SecNumEdu ANSSI, grade Licence/Master délivré par l'État, habilitation CTI, accréditation
CGE), taux d'accès Parcoursup, taux d'insertion professionnelle, coût réel de la formation.

NEUTRALITÉ :
- Quand tu listes des formations, inclus TOUJOURS les formations publiques labellisées
  avant les formations privées non labellisées.
- Si une formation possède un label officiel (SecNumEdu, CTI, CGE, grade Master),
  mentionne-le systématiquement.
- Ne reproduis JAMAIS le biais marketing : une école avec un bon SEO n'est pas une
  meilleure école.

RÉALISME :
- Utilise les taux d'accès Parcoursup pour évaluer la faisabilité.
  - Taux < 10% : "Formation extrêmement sélective"
  - Taux 10-30% : "Formation sélective"
  - Taux 30-60% : "Formation modérément sélective"
  - Taux > 60% : "Formation accessible"
- Quand un étudiant vise une formation très sélective, propose TOUJOURS des alternatives
  réalistes ET des passerelles pour y accéder plus tard.
- Ne dis JAMAIS "tout est possible avec de la motivation". Dis la vérité avec bienveillance.

AGENTIVITÉ :
- Ne donne JAMAIS une réponse unique et fermée.
- Propose toujours 2-3 options avec les critères de choix expliqués.
- Termine par une question ouverte qui pousse l'étudiant à réfléchir sur SES priorités.
- Rappelle régulièrement que c'est l'étudiant qui décide, pas toi.

SOURÇAGE :
- Cite TOUJOURS la source de chaque donnée factuelle.
- Si tu ne trouves pas l'information dans tes données, dis-le explicitement.
- Ne fabrique JAMAIS de chiffre.

FORMAT DE SORTIE :
Pour chaque formation recommandée :
📍 [Nom] — [Établissement], [Ville]
• Type : [diplôme] | Statut : [Public/Privé]
• Labels : [liste ou "aucun"]
• Sélectivité : [taux Parcoursup]
• Source : [origine de la donnée]

Termine toujours par :
🔀 Passerelles possibles : ...
💡 Question pour toi : ...

CAS LIMITES :
- Détresse → Fil Santé Jeunes (0 800 235 236) + conseiller humain.
- Hors orientation → recentre poliment.
- Données manquantes → oriente vers ONISEP ou Parcoursup.
"""


def build_user_prompt(context: str, question: str) -> str:
    return f"""Voici les données de référence pour répondre à la question :

{context}

Question de l'étudiant : {question}

Réponds en suivant le format spécifié dans tes instructions."""
```

- [ ] **Step 4: Run test — PASS**

```bash
pytest tests/test_system_prompt.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/prompt/system.py tests/test_system_prompt.py
git commit -m "feat(prompt): 4-layer system prompt (neutrality/realism/agency/source)"
```

---

## Task 3.2: Embeddings wrapper

**Files:**
- Create: `src/rag/embeddings.py`
- Create: `tests/test_embeddings.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_embeddings.py`:
```python
from unittest.mock import MagicMock, patch
from src.rag.embeddings import embed_texts, fiche_to_text


def test_fiche_to_text_includes_key_fields():
    fiche = {
        "nom": "Master Cyber",
        "etablissement": "ENSIBS",
        "ville": "Vannes",
        "statut": "Public",
        "labels": ["SecNumEdu"],
        "taux_acces_parcoursup_2025": 22.0,
    }
    text = fiche_to_text(fiche)
    assert "Master Cyber" in text
    assert "ENSIBS" in text
    assert "Vannes" in text
    assert "SecNumEdu" in text
    assert "22" in text


def test_embed_texts_calls_mistral_api():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
    mock_client.embeddings.create.return_value = mock_response

    result = embed_texts(mock_client, ["hello"])
    assert result == [[0.1, 0.2, 0.3]]
    mock_client.embeddings.create.assert_called_once_with(
        model="mistral-embed", inputs=["hello"]
    )
```

- [ ] **Step 2: Run test — FAIL**

```bash
pytest tests/test_embeddings.py -v
```

- [ ] **Step 3: Implement**

Create `src/rag/embeddings.py`:
```python
from mistralai import Mistral


EMBED_MODEL = "mistral-embed"


def fiche_to_text(fiche: dict) -> str:
    parts = [
        f"Formation : {fiche.get('nom', '')}",
        f"Établissement : {fiche.get('etablissement', '')}",
        f"Ville : {fiche.get('ville', '')}",
    ]
    if fiche.get("type_diplome"):
        parts.append(f"Diplôme : {fiche['type_diplome']}")
    if fiche.get("statut"):
        parts.append(f"Statut : {fiche['statut']}")
    labels = fiche.get("labels") or []
    if labels:
        parts.append(f"Labels : {', '.join(labels)}")
    if fiche.get("taux_acces_parcoursup_2025") is not None:
        parts.append(f"Taux d'accès Parcoursup 2025 : {fiche['taux_acces_parcoursup_2025']}%")
    if fiche.get("nombre_places") is not None:
        parts.append(f"Places : {fiche['nombre_places']}")
    if fiche.get("domaine"):
        parts.append(f"Domaine : {fiche['domaine']}")
    return " | ".join(parts)


def embed_texts(client: Mistral, texts: list[str]) -> list[list[float]]:
    response = client.embeddings.create(model=EMBED_MODEL, inputs=texts)
    return [d.embedding for d in response.data]


def embed_texts_batched(client: Mistral, texts: list[str], batch_size: int = 64) -> list[list[float]]:
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        all_embeddings.extend(embed_texts(client, batch))
    return all_embeddings
```

- [ ] **Step 4: Run test — PASS**

```bash
pytest tests/test_embeddings.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/rag/embeddings.py tests/test_embeddings.py
git commit -m "feat(rag): mistral-embed wrapper with fiche serializer"
```

---

## Task 3.3: FAISS index build/load

**Files:**
- Create: `src/rag/index.py`
- Create: `tests/test_index.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_index.py`:
```python
import numpy as np
from src.rag.index import build_index, save_index, load_index


def test_build_index_returns_searchable_faiss_index(tmp_path):
    embeddings = np.random.rand(10, 128).astype("float32")
    index = build_index(embeddings)
    assert index.ntotal == 10

    query = embeddings[0:1]
    distances, indices = index.search(query, k=3)
    assert indices[0][0] == 0


def test_save_and_load_index_roundtrip(tmp_path):
    embeddings = np.random.rand(5, 64).astype("float32")
    index = build_index(embeddings)
    path = tmp_path / "test.index"

    save_index(index, path)
    loaded = load_index(path)
    assert loaded.ntotal == 5
```

- [ ] **Step 2: Run test — FAIL**

```bash
pytest tests/test_index.py -v
```

- [ ] **Step 3: Implement**

Create `src/rag/index.py`:
```python
from pathlib import Path
import faiss
import numpy as np


def build_index(embeddings: np.ndarray) -> faiss.IndexFlatL2:
    if embeddings.dtype != np.float32:
        embeddings = embeddings.astype("float32")
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)
    return index


def save_index(index: faiss.IndexFlatL2, path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(path))


def load_index(path: str | Path) -> faiss.IndexFlatL2:
    return faiss.read_index(str(path))
```

- [ ] **Step 4: Run test — PASS**

```bash
pytest tests/test_index.py -v
```

- [ ] **Step 5: Create real index from formations.json**

Create `src/rag/build_real_index.py`:
```python
import json
from pathlib import Path
import numpy as np
from mistralai import Mistral
from src.config import load_config
from src.rag.embeddings import fiche_to_text, embed_texts_batched
from src.rag.index import build_index, save_index


def main():
    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key)

    fiches = json.loads(Path("data/processed/formations.json").read_text(encoding="utf-8"))
    texts = [fiche_to_text(f) for f in fiches]
    print(f"Embedding {len(texts)} fiches...")

    embeddings = embed_texts_batched(client, texts, batch_size=32)
    arr = np.array(embeddings, dtype="float32")
    print(f"Embedding shape: {arr.shape}")

    index = build_index(arr)
    save_index(index, "data/embeddings/formations.index")
    print(f"Saved index with {index.ntotal} vectors")

    Path("data/embeddings/fiche_order.json").write_text(
        json.dumps([f.get("nom", "") for f in fiches], ensure_ascii=False),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
```

Run:
```bash
python -m src.rag.build_real_index
```
Expected: `Saved index with ~300 vectors`.

- [ ] **Step 6: Commit**

```bash
git add src/rag/index.py src/rag/build_real_index.py tests/test_index.py
git commit -m "feat(rag): faiss index build/save/load"
```

---

## Task 3.4: Retriever

**Files:**
- Create: `src/rag/retriever.py`
- Create: `tests/test_retriever.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_retriever.py`:
```python
import numpy as np
from unittest.mock import MagicMock
from src.rag.index import build_index
from src.rag.retriever import retrieve_top_k


def test_retrieve_top_k_returns_k_fiches_with_scores():
    fiches = [{"id": i, "nom": f"Formation {i}"} for i in range(20)]
    embeddings = np.random.rand(20, 64).astype("float32")
    index = build_index(embeddings)

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=list(embeddings[0]))]
    mock_client.embeddings.create.return_value = mock_response

    results = retrieve_top_k(mock_client, index, fiches, "query", k=5)
    assert len(results) == 5
    assert "fiche" in results[0]
    assert "score" in results[0]
    assert results[0]["fiche"]["id"] == 0
```

- [ ] **Step 2: Run test — FAIL**

```bash
pytest tests/test_retriever.py -v
```

- [ ] **Step 3: Implement**

Create `src/rag/retriever.py`:
```python
import numpy as np
import faiss
from mistralai import Mistral
from src.rag.embeddings import embed_texts


def retrieve_top_k(
    client: Mistral,
    index: faiss.IndexFlatL2,
    fiches: list[dict],
    question: str,
    k: int = 10,
) -> list[dict]:
    q_emb = embed_texts(client, [question])[0]
    q_arr = np.array([q_emb], dtype="float32")
    distances, indices = index.search(q_arr, k)

    results = []
    for rank, idx in enumerate(indices[0]):
        if idx < 0 or idx >= len(fiches):
            continue
        dist = float(distances[0][rank])
        score = 1.0 / (1.0 + dist)
        results.append({"fiche": fiches[idx], "score": score, "base_score": score})
    return results
```

- [ ] **Step 4: Run test — PASS**

```bash
pytest tests/test_retriever.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/rag/retriever.py tests/test_retriever.py
git commit -m "feat(rag): top-k faiss retriever with normalized scores"
```

---

## Task 3.5: Label-based reranker (configurable weights)

**Files:**
- Create: `src/rag/reranker.py`
- Create: `tests/test_reranker.py`

`★ Insight ─────────────────────────────────────`
The reranker takes a `RerankConfig` dataclass, not hard-coded numbers. This is what makes the grid search in Task 4.5 trivial: we just instantiate the config with different values. Immutable dataclass so configs can be hashed and cached.
`─────────────────────────────────────────────────`

- [ ] **Step 1: Write failing test**

Create `tests/test_reranker.py`:
```python
from src.rag.reranker import RerankConfig, rerank


def test_rerank_boosts_secnumedu():
    results = [
        {"fiche": {"labels": ["SecNumEdu"], "statut": "Public"}, "score": 0.5, "base_score": 0.5},
        {"fiche": {"labels": [], "statut": "Privé"}, "score": 0.6, "base_score": 0.6},
    ]
    cfg = RerankConfig(secnumedu_boost=1.5, cti_boost=1.0, public_boost=1.0)
    reranked = rerank(results, cfg)
    assert reranked[0]["fiche"]["labels"] == ["SecNumEdu"]
    assert reranked[0]["score"] > reranked[1]["score"]


def test_rerank_with_no_boost_keeps_order_if_equal():
    results = [
        {"fiche": {"labels": [], "statut": "Public"}, "score": 0.5, "base_score": 0.5},
        {"fiche": {"labels": [], "statut": "Public"}, "score": 0.4, "base_score": 0.4},
    ]
    cfg = RerankConfig(secnumedu_boost=1.0, cti_boost=1.0, public_boost=1.0)
    reranked = rerank(results, cfg)
    assert reranked[0]["score"] == 0.5
    assert reranked[1]["score"] == 0.4


def test_rerank_public_boost_separates_public_from_private():
    results = [
        {"fiche": {"labels": [], "statut": "Public"}, "score": 0.5, "base_score": 0.5},
        {"fiche": {"labels": [], "statut": "Privé"}, "score": 0.55, "base_score": 0.55},
    ]
    cfg = RerankConfig(secnumedu_boost=1.0, cti_boost=1.0, public_boost=1.3)
    reranked = rerank(results, cfg)
    assert reranked[0]["fiche"]["statut"] == "Public"
```

- [ ] **Step 2: Run test — FAIL**

```bash
pytest tests/test_reranker.py -v
```

- [ ] **Step 3: Implement**

Create `src/rag/reranker.py`:
```python
from dataclasses import dataclass


@dataclass(frozen=True)
class RerankConfig:
    secnumedu_boost: float = 1.5
    cti_boost: float = 1.3
    grade_master_boost: float = 1.3
    public_boost: float = 1.1

    def as_dict(self) -> dict:
        return {
            "secnumedu_boost": self.secnumedu_boost,
            "cti_boost": self.cti_boost,
            "grade_master_boost": self.grade_master_boost,
            "public_boost": self.public_boost,
        }


def rerank(results: list[dict], config: RerankConfig) -> list[dict]:
    reranked = []
    for r in results:
        fiche = r["fiche"]
        score = r["base_score"]
        labels = fiche.get("labels") or []
        if "SecNumEdu" in labels:
            score *= config.secnumedu_boost
        if "CTI" in labels:
            score *= config.cti_boost
        if "Grade Master" in labels:
            score *= config.grade_master_boost
        if fiche.get("statut") == "Public":
            score *= config.public_boost
        new = dict(r)
        new["score"] = score
        reranked.append(new)
    reranked.sort(key=lambda x: x["score"], reverse=True)
    return reranked
```

- [ ] **Step 4: Run test — PASS**

```bash
pytest tests/test_reranker.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/rag/reranker.py tests/test_reranker.py
git commit -m "feat(rag): label-based reranker with configurable weights"
```

---

## Task 3.6: Generator (Mistral chat with RAG context)

**Files:**
- Create: `src/rag/generator.py`
- Create: `tests/test_generator.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_generator.py`:
```python
from unittest.mock import MagicMock
from src.rag.generator import format_context, generate


def test_format_context_includes_all_fiches():
    results = [
        {"fiche": {"nom": "Master A", "etablissement": "X", "ville": "Paris",
                   "labels": ["SecNumEdu"], "statut": "Public",
                   "taux_acces_parcoursup_2025": 25.0}, "score": 0.9},
        {"fiche": {"nom": "Master B", "etablissement": "Y", "ville": "Lyon",
                   "labels": [], "statut": "Privé"}, "score": 0.7},
    ]
    context = format_context(results)
    assert "Master A" in context
    assert "Master B" in context
    assert "SecNumEdu" in context


def test_generate_calls_mistral_with_system_and_user_prompts():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Response text"))]
    mock_client.chat.complete.return_value = mock_response

    results = [{"fiche": {"nom": "F", "etablissement": "E", "ville": "V", "labels": [],
                          "statut": "Public"}, "score": 0.5}]
    answer = generate(mock_client, results, "question?", model="mistral-medium-latest")
    assert answer == "Response text"
    call = mock_client.chat.complete.call_args
    messages = call.kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "question?" in messages[1]["content"]
```

- [ ] **Step 2: Run test — FAIL**

```bash
pytest tests/test_generator.py -v
```

- [ ] **Step 3: Implement**

Create `src/rag/generator.py`:
```python
from mistralai import Mistral
from src.prompt.system import SYSTEM_PROMPT, build_user_prompt


def format_context(results: list[dict]) -> str:
    blocks = []
    for i, r in enumerate(results, 1):
        f = r["fiche"]
        lines = [f"FICHE {i}:"]
        lines.append(f"  Nom: {f.get('nom','')}")
        lines.append(f"  Établissement: {f.get('etablissement','')}")
        lines.append(f"  Ville: {f.get('ville','')}")
        lines.append(f"  Statut: {f.get('statut','Inconnu')}")
        labels = f.get("labels") or []
        lines.append(f"  Labels: {', '.join(labels) if labels else 'aucun'}")
        if f.get("taux_acces_parcoursup_2025") is not None:
            lines.append(f"  Taux d'accès Parcoursup 2025: {f['taux_acces_parcoursup_2025']}%")
        if f.get("nombre_places") is not None:
            lines.append(f"  Places: {f['nombre_places']}")
        if f.get("url_onisep"):
            lines.append(f"  Source ONISEP: {f['url_onisep']}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def generate(
    client: Mistral,
    retrieved: list[dict],
    question: str,
    model: str = "mistral-medium-latest",
    temperature: float = 0.3,
) -> str:
    context = format_context(retrieved)
    user_prompt = build_user_prompt(context, question)
    response = client.chat.complete(
        model=model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content
```

- [ ] **Step 4: Run test — PASS**

```bash
pytest tests/test_generator.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/rag/generator.py tests/test_generator.py
git commit -m "feat(rag): mistral generator with context formatting"
```

---

## Task 3.7: Pipeline orchestrator + CLI smoke test

**Files:**
- Create: `src/rag/pipeline.py`
- Create: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_pipeline.py`:
```python
from unittest.mock import MagicMock, patch
import numpy as np
from src.rag.reranker import RerankConfig
from src.rag.pipeline import OrientIAPipeline


def test_pipeline_end_to_end_mock():
    fiches = [
        {"nom": "Master Cyber ENSIBS", "etablissement": "ENSIBS", "ville": "Vannes",
         "statut": "Public", "labels": ["SecNumEdu"]},
        {"nom": "Master Commerce", "etablissement": "X", "ville": "Paris",
         "statut": "Privé", "labels": []},
    ]
    mock_client = MagicMock()

    emb_response = MagicMock()
    emb_response.data = [MagicMock(embedding=[0.1, 0.2]), MagicMock(embedding=[0.11, 0.21])]
    q_response = MagicMock()
    q_response.data = [MagicMock(embedding=[0.1, 0.2])]
    mock_client.embeddings.create.side_effect = [emb_response, q_response]

    chat_response = MagicMock()
    chat_response.choices = [MagicMock(message=MagicMock(content="Recommandation..."))]
    mock_client.chat.complete.return_value = chat_response

    pipeline = OrientIAPipeline(mock_client, fiches, rerank_config=RerankConfig())
    pipeline.build_index()
    answer, sources = pipeline.answer("Quelles formations cyber ?", k=2)
    assert "Recommandation" in answer
    assert len(sources) == 2
```

- [ ] **Step 2: Run test — FAIL**

```bash
pytest tests/test_pipeline.py -v
```

- [ ] **Step 3: Implement**

Create `src/rag/pipeline.py`:
```python
import numpy as np
from mistralai import Mistral
from src.rag.embeddings import fiche_to_text, embed_texts_batched
from src.rag.index import build_index
from src.rag.retriever import retrieve_top_k
from src.rag.reranker import RerankConfig, rerank
from src.rag.generator import generate


class OrientIAPipeline:
    def __init__(
        self,
        client: Mistral,
        fiches: list[dict],
        rerank_config: RerankConfig | None = None,
        model: str = "mistral-medium-latest",
    ):
        self.client = client
        self.fiches = fiches
        self.rerank_config = rerank_config or RerankConfig()
        self.model = model
        self.index = None

    def build_index(self) -> None:
        texts = [fiche_to_text(f) for f in self.fiches]
        embeddings = embed_texts_batched(self.client, texts, batch_size=32)
        self.index = build_index(np.array(embeddings, dtype="float32"))

    def answer(self, question: str, k: int = 10, top_k_sources: int = 5) -> tuple[str, list[dict]]:
        if self.index is None:
            raise RuntimeError("Pipeline not built — call build_index() first.")
        retrieved = retrieve_top_k(self.client, self.index, self.fiches, question, k=k)
        reranked = rerank(retrieved, self.rerank_config)
        top = reranked[:top_k_sources]
        answer_text = generate(self.client, top, question, model=self.model)
        return answer_text, top
```

- [ ] **Step 4: Run test — PASS**

```bash
pytest tests/test_pipeline.py -v
```

- [ ] **Step 5: Write CLI smoke test script**

Create `src/rag/cli.py`:
```python
import json
import sys
from pathlib import Path
from mistralai import Mistral
from src.config import load_config
from src.rag.pipeline import OrientIAPipeline


def main():
    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key)
    fiches = json.loads(Path("data/processed/formations.json").read_text(encoding="utf-8"))

    print(f"Loading {len(fiches)} fiches and building index...")
    pipeline = OrientIAPipeline(client, fiches)
    pipeline.build_index()

    question = sys.argv[1] if len(sys.argv) > 1 else "Quelles sont les meilleures formations en cybersécurité en France ?"
    print(f"\nQuestion: {question}\n")
    answer, sources = pipeline.answer(question)
    print(answer)
    print("\n--- Sources ---")
    for s in sources:
        f = s["fiche"]
        print(f"  • {f.get('nom')} — {f.get('etablissement')} ({f.get('ville')}) [score={s['score']:.3f}]")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run CLI against real data**

```bash
python -m src.rag.cli "Quelles sont les meilleures formations en cybersécurité en France ?"
```
Expected: a formatted response with SecNumEdu formations at the top.

- [ ] **Step 7: Commit**

```bash
git add src/rag/pipeline.py src/rag/cli.py tests/test_pipeline.py
git commit -m "feat(rag): pipeline orchestrator + cli smoke test"
```

---

# Phase 4 — Benchmark

## Task 4.1: Three system wrappers

**Files:**
- Create: `src/eval/systems.py`
- Create: `tests/test_systems.py`
- Create: `data/chatgpt_recorded.json`

- [ ] **Step 1: Record ChatGPT responses (manual)**

For each of the 32 questions in `src/eval/questions.json`, open https://chat.openai.com (free tier or paid), paste the question verbatim, copy the response. Save to `data/chatgpt_recorded.json`:

```json
{
  "A1": "Réponse ChatGPT à la question A1...",
  "A2": "Réponse ChatGPT à la question A2...",
  "...": "..."
}
```

Document the date and model version in a comment field:
```json
{
  "_metadata": {
    "model": "gpt-4o",
    "date_recorded": "2026-04-XX",
    "notes": "Free tier, web interface, fresh conversation per question"
  },
  "A1": "..."
}
```

- [ ] **Step 2: Write failing test**

Create `tests/test_systems.py`:
```python
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.eval.systems import OurRagSystem, MistralRawSystem, ChatGPTRecordedSystem


def test_chatgpt_recorded_returns_stored_answer(tmp_path):
    data = {"A1": "answer A1", "_metadata": {"model": "gpt-4o"}}
    path = tmp_path / "chatgpt.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    system = ChatGPTRecordedSystem(path)
    assert system.answer("A1", "ignored question") == "answer A1"


def test_mistral_raw_uses_same_system_prompt_but_no_context():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="raw answer"))]
    mock_client.chat.complete.return_value = mock_response

    system = MistralRawSystem(mock_client)
    answer = system.answer("A1", "Quelles formations cyber ?")
    assert answer == "raw answer"
    messages = mock_client.chat.complete.call_args.kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert "Quelles formations cyber" in messages[1]["content"]
    assert "FICHE" not in messages[1]["content"]


def test_our_rag_uses_pipeline():
    mock_pipeline = MagicMock()
    mock_pipeline.answer.return_value = ("our answer", [])

    system = OurRagSystem(mock_pipeline)
    assert system.answer("A1", "question") == "our answer"
```

- [ ] **Step 3: Run test — FAIL**

```bash
pytest tests/test_systems.py -v
```

- [ ] **Step 4: Implement**

Create `src/eval/systems.py`:
```python
import json
from pathlib import Path
from abc import ABC, abstractmethod
from mistralai import Mistral
from src.prompt.system import SYSTEM_PROMPT
from src.rag.pipeline import OrientIAPipeline


class System(ABC):
    name: str

    @abstractmethod
    def answer(self, qid: str, question: str) -> str:
        ...


class OurRagSystem(System):
    name = "our_rag"

    def __init__(self, pipeline: OrientIAPipeline):
        self.pipeline = pipeline

    def answer(self, qid: str, question: str) -> str:
        text, _sources = self.pipeline.answer(question)
        return text


class MistralRawSystem(System):
    """Same system prompt, no RAG context — isolates the effect of retrieval."""
    name = "mistral_raw"

    def __init__(self, client: Mistral, model: str = "mistral-medium-latest"):
        self.client = client
        self.model = model

    def answer(self, qid: str, question: str) -> str:
        response = self.client.chat.complete(
            model=self.model,
            temperature=0.3,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
        )
        return response.choices[0].message.content


class ChatGPTRecordedSystem(System):
    name = "chatgpt_recorded"

    def __init__(self, path: str | Path):
        self.data = json.loads(Path(path).read_text(encoding="utf-8"))

    def answer(self, qid: str, question: str) -> str:
        if qid not in self.data:
            raise KeyError(f"No recorded ChatGPT response for {qid}")
        return self.data[qid]
```

- [ ] **Step 5: Run test — PASS**

```bash
pytest tests/test_systems.py -v
```

- [ ] **Step 6: Commit**

```bash
git add src/eval/systems.py tests/test_systems.py data/chatgpt_recorded.json
git commit -m "feat(eval): three system wrappers (our RAG / mistral raw / chatgpt)"
```

---

## Task 4.2: Benchmark runner with blind label randomization

**Files:**
- Create: `src/eval/runner.py`
- Create: `tests/test_runner.py`

`★ Insight ─────────────────────────────────────`
The runner randomizes {A, B, C} labels per question and saves the mapping in a separate file the judge never sees. This is the double-blind protocol: the judge sees only anonymous labels, and we can later reverse-map to score each system. Saving the seed makes it reproducible.
`─────────────────────────────────────────────────`

- [ ] **Step 1: Write failing test**

Create `tests/test_runner.py`:
```python
import json
from pathlib import Path
from unittest.mock import MagicMock
from src.eval.runner import run_benchmark, BlindLabel


def test_run_benchmark_produces_blind_mapping(tmp_path):
    questions = [
        {"id": "A1", "category": "biais_marketing", "text": "question 1"},
        {"id": "A2", "category": "biais_marketing", "text": "question 2"},
    ]

    sys1 = MagicMock(name="sys1"); sys1.answer.return_value = "answer from 1"
    sys2 = MagicMock(name="sys2"); sys2.answer.return_value = "answer from 2"
    sys3 = MagicMock(name="sys3"); sys3.answer.return_value = "answer from 3"

    systems = {"our_rag": sys1, "mistral_raw": sys2, "chatgpt_recorded": sys3}
    out_dir = tmp_path / "out"
    run_benchmark(questions, systems, out_dir, seed=42)

    responses = json.loads((out_dir / "responses_blind.json").read_text(encoding="utf-8"))
    mapping = json.loads((out_dir / "label_mapping.json").read_text(encoding="utf-8"))

    assert len(responses) == 2
    for q_entry in responses:
        assert set(q_entry["answers"].keys()) == {"A", "B", "C"}
    for qid, map_for_q in mapping.items():
        assert set(map_for_q.keys()) == {"A", "B", "C"}
        assert set(map_for_q.values()) == {"our_rag", "mistral_raw", "chatgpt_recorded"}
```

- [ ] **Step 2: Run test — FAIL**

```bash
pytest tests/test_runner.py -v
```

- [ ] **Step 3: Implement**

Create `src/eval/runner.py`:
```python
import json
import random
from pathlib import Path
from dataclasses import dataclass


BlindLabel = str  # "A" | "B" | "C"
BLIND_LABELS = ["A", "B", "C"]


def run_benchmark(
    questions: list[dict],
    systems: dict,
    output_dir: str | Path,
    seed: int = 42,
) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)

    responses_blind = []
    label_mapping = {}

    system_names = list(systems.keys())
    assert len(system_names) == 3, "Expected exactly 3 systems"

    for q in questions:
        shuffled = system_names[:]
        rng.shuffle(shuffled)
        mapping = dict(zip(BLIND_LABELS, shuffled))
        label_mapping[q["id"]] = mapping

        answers = {}
        for label, sys_name in mapping.items():
            system = systems[sys_name]
            answers[label] = system.answer(q["id"], q["text"])

        responses_blind.append({
            "id": q["id"],
            "category": q["category"],
            "text": q["text"],
            "answers": answers,
        })

    (output_dir / "responses_blind.json").write_text(
        json.dumps(responses_blind, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "label_mapping.json").write_text(
        json.dumps(label_mapping, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "seed.txt").write_text(str(seed), encoding="utf-8")
```

- [ ] **Step 4: Run test — PASS**

```bash
pytest tests/test_runner.py -v
```

- [ ] **Step 5: Run real benchmark**

Create `src/eval/run_real.py`:
```python
import json
from pathlib import Path
from mistralai import Mistral
from src.config import load_config
from src.rag.pipeline import OrientIAPipeline
from src.eval.systems import OurRagSystem, MistralRawSystem, ChatGPTRecordedSystem
from src.eval.runner import run_benchmark


def main():
    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key)

    fiches = json.loads(Path("data/processed/formations.json").read_text(encoding="utf-8"))
    pipeline = OrientIAPipeline(client, fiches)
    print("Building index...")
    pipeline.build_index()

    systems = {
        "our_rag": OurRagSystem(pipeline),
        "mistral_raw": MistralRawSystem(client),
        "chatgpt_recorded": ChatGPTRecordedSystem("data/chatgpt_recorded.json"),
    }

    questions = json.loads(Path("src/eval/questions.json").read_text(encoding="utf-8"))["questions"]
    print(f"Running benchmark on {len(questions)} questions × {len(systems)} systems...")
    run_benchmark(questions, systems, "results/raw_responses", seed=42)
    print("Done. Saved to results/raw_responses/")


if __name__ == "__main__":
    main()
```

Run:
```bash
python -m src.eval.run_real
```
Expected: `results/raw_responses/responses_blind.json` and `label_mapping.json`.

- [ ] **Step 6: Commit**

```bash
git add src/eval/runner.py src/eval/run_real.py tests/test_runner.py
git commit -m "feat(eval): benchmark runner with blind label randomization"
```

---

## Task 4.3: Claude judge with blind scoring

**Files:**
- Create: `src/eval/judge.py`
- Create: `tests/test_judge.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_judge.py`:
```python
import json
from unittest.mock import MagicMock
from src.eval.judge import judge_question, JUDGE_PROMPT


def test_judge_prompt_defines_six_criteria():
    for crit in ["neutralite", "realisme", "sourcage", "diversite_geo", "agentivite", "decouverte"]:
        assert crit in JUDGE_PROMPT.lower() or crit.replace("_", " ") in JUDGE_PROMPT.lower()


def test_judge_question_parses_json_response():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps({
        "A": {"neutralite": 2, "realisme": 3, "sourcage": 2, "diversite_geo": 1,
              "agentivite": 2, "decouverte": 1, "total": 11, "justification": "ok"},
        "B": {"neutralite": 1, "realisme": 1, "sourcage": 0, "diversite_geo": 1,
              "agentivite": 2, "decouverte": 1, "total": 6, "justification": "weak"},
        "C": {"neutralite": 3, "realisme": 3, "sourcage": 3, "diversite_geo": 2,
              "agentivite": 3, "decouverte": 2, "total": 16, "justification": "strong"},
    }))]
    mock_client.messages.create.return_value = mock_response

    scores = judge_question(
        mock_client,
        question="test?",
        answers={"A": "answer a", "B": "answer b", "C": "answer c"},
    )
    assert scores["A"]["total"] == 11
    assert scores["C"]["total"] == 16
```

- [ ] **Step 2: Run test — FAIL**

```bash
pytest tests/test_judge.py -v
```

- [ ] **Step 3: Implement**

Create `src/eval/judge.py`:
```python
import json
import re
from anthropic import Anthropic


JUDGE_PROMPT = """Tu es un évaluateur expert en orientation scolaire française.
On te donne une question d'un étudiant et TROIS réponses anonymisées (A, B, C) de trois systèmes IA différents.
Tu NE DOIS PAS deviner quel système a produit quelle réponse.
Évalue chaque réponse indépendamment sur les 6 critères suivants, chacun noté de 0 à 3.

CRITÈRES :

1. NEUTRALITÉ institutionnelle
   0 : ne mentionne que des écoles privées
   1 : mélange sans distinction
   2 : mentionne des formations publiques
   3 : priorise les labels officiels (SecNumEdu, CTI, CGE, Grade Master)

2. RÉALISME
   0 : "Tout est possible !" sans nuance
   1 : mentionne la sélectivité vaguement
   2 : cite des données de sélectivité
   3 : donne taux d'accès précis + alternatives réalistes

3. SOURÇAGE
   0 : aucune source
   1 : sources vagues ("on dit que...")
   2 : mentionne des institutions
   3 : cite des données vérifiables avec la source précise

4. DIVERSITÉ géographique
   0 : que Paris
   1 : principalement Paris + 1-2 villes
   2 : plusieurs régions
   3 : couverture territoriale adaptée au profil

5. AGENTIVITÉ
   0 : réponse fermée et directive
   1 : peu de choix
   2 : propose des options
   3 : options + question ouverte + encourage la réflexion

6. DÉCOUVERTE
   0 : ne mentionne que des métiers évidents
   1 : 1-2 suggestions classiques
   2 : propose des pistes originales
   3 : fait découvrir des métiers/formations méconnus et pertinents

IMPORTANT :
- Évalue uniquement la réponse fournie, pas tes propres connaissances.
- Sois objectif et cohérent.
- Présente les scores du plus élevé au plus bas dans chaque rubrique pour réduire le rubric order bias.

Réponds UNIQUEMENT au format JSON valide, sans texte autour :

{
  "A": {"neutralite": X, "realisme": X, "sourcage": X, "diversite_geo": X, "agentivite": X, "decouverte": X, "total": X, "justification": "..."},
  "B": {...},
  "C": {...}
}
"""


def _extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON found in judge response: {text[:200]}")
    return json.loads(match.group(0))


def judge_question(
    client: Anthropic,
    question: str,
    answers: dict[str, str],
    model: str = "claude-sonnet-4-5",
) -> dict:
    user_content = f"""Question de l'étudiant : {question}

RÉPONSE A :
{answers['A']}

RÉPONSE B :
{answers['B']}

RÉPONSE C :
{answers['C']}
"""
    response = client.messages.create(
        model=model,
        max_tokens=2000,
        system=JUDGE_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )
    text = response.content[0].text
    return _extract_json(text)


def judge_all(
    client: Anthropic,
    responses_blind: list[dict],
    model: str = "claude-sonnet-4-5",
) -> list[dict]:
    all_scores = []
    for entry in responses_blind:
        scores = judge_question(client, entry["text"], entry["answers"], model=model)
        all_scores.append({
            "id": entry["id"],
            "category": entry["category"],
            "scores": scores,
        })
    return all_scores
```

- [ ] **Step 4: Run test — PASS**

```bash
pytest tests/test_judge.py -v
```

- [ ] **Step 5: Run real judging**

Create `src/eval/run_judge.py`:
```python
import json
from pathlib import Path
from anthropic import Anthropic
from src.config import load_config
from src.eval.judge import judge_all


def main():
    cfg = load_config()
    client = Anthropic(api_key=cfg.anthropic_api_key)

    responses = json.loads(
        Path("results/raw_responses/responses_blind.json").read_text(encoding="utf-8")
    )
    print(f"Judging {len(responses)} questions...")
    scores = judge_all(client, responses)

    Path("results/scores").mkdir(parents=True, exist_ok=True)
    Path("results/scores/blind_scores.json").write_text(
        json.dumps(scores, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Saved to results/scores/blind_scores.json")


if __name__ == "__main__":
    main()
```

Run:
```bash
python -m src.eval.run_judge
```
Expected: ~32 JSON entries with scores.

- [ ] **Step 6: Commit**

```bash
git add src/eval/judge.py src/eval/run_judge.py tests/test_judge.py
git commit -m "feat(eval): claude judge with 6-criterion rubric + json parsing"
```

---

## Task 4.4: Analysis — unblind + aggregate + charts

**Files:**
- Create: `src/eval/analyze.py`
- Create: `tests/test_analyze.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_analyze.py`:
```python
from src.eval.analyze import unblind_scores, aggregate_by_system


def test_unblind_scores_maps_labels_to_systems():
    blind_scores = [
        {"id": "A1", "category": "biais_marketing", "scores": {
            "A": {"neutralite": 3, "realisme": 2, "sourcage": 2, "diversite_geo": 1,
                  "agentivite": 2, "decouverte": 1, "total": 11, "justification": ""},
            "B": {"neutralite": 1, "realisme": 1, "sourcage": 0, "diversite_geo": 1,
                  "agentivite": 1, "decouverte": 1, "total": 5, "justification": ""},
            "C": {"neutralite": 2, "realisme": 3, "sourcage": 3, "diversite_geo": 2,
                  "agentivite": 3, "decouverte": 2, "total": 15, "justification": ""},
        }},
    ]
    mapping = {"A1": {"A": "our_rag", "B": "mistral_raw", "C": "chatgpt_recorded"}}

    unblinded = unblind_scores(blind_scores, mapping)
    assert unblinded[0]["systems"]["our_rag"]["total"] == 11
    assert unblinded[0]["systems"]["chatgpt_recorded"]["total"] == 15


def test_aggregate_by_system_averages_criteria():
    unblinded = [
        {"id": "A1", "category": "biais_marketing", "systems": {
            "our_rag": {"neutralite": 3, "realisme": 2, "sourcage": 2, "diversite_geo": 1,
                        "agentivite": 2, "decouverte": 1, "total": 11},
            "mistral_raw": {"neutralite": 1, "realisme": 1, "sourcage": 0, "diversite_geo": 1,
                            "agentivite": 1, "decouverte": 1, "total": 5},
        }},
        {"id": "A2", "category": "biais_marketing", "systems": {
            "our_rag": {"neutralite": 3, "realisme": 3, "sourcage": 3, "diversite_geo": 2,
                        "agentivite": 2, "decouverte": 2, "total": 15},
            "mistral_raw": {"neutralite": 2, "realisme": 1, "sourcage": 1, "diversite_geo": 1,
                            "agentivite": 1, "decouverte": 1, "total": 7},
        }},
    ]
    agg = aggregate_by_system(unblinded)
    assert agg["our_rag"]["neutralite"] == 3.0
    assert agg["our_rag"]["total"] == 13.0
    assert agg["mistral_raw"]["total"] == 6.0
```

- [ ] **Step 2: Run test — FAIL**

```bash
pytest tests/test_analyze.py -v
```

- [ ] **Step 3: Implement**

Create `src/eval/analyze.py`:
```python
import json
from pathlib import Path
from collections import defaultdict


CRITERIA = ["neutralite", "realisme", "sourcage", "diversite_geo", "agentivite", "decouverte"]


def unblind_scores(blind_scores: list[dict], mapping: dict) -> list[dict]:
    unblinded = []
    for entry in blind_scores:
        qid = entry["id"]
        q_map = mapping[qid]
        systems_scores = {}
        for label, score in entry["scores"].items():
            sys_name = q_map[label]
            systems_scores[sys_name] = {k: v for k, v in score.items() if k != "justification"}
        unblinded.append({
            "id": qid,
            "category": entry["category"],
            "systems": systems_scores,
        })
    return unblinded


def aggregate_by_system(unblinded: list[dict]) -> dict:
    by_sys = defaultdict(lambda: defaultdict(list))
    for entry in unblinded:
        for sys_name, scores in entry["systems"].items():
            for crit in CRITERIA + ["total"]:
                if crit in scores:
                    by_sys[sys_name][crit].append(scores[crit])
    agg = {}
    for sys_name, crits in by_sys.items():
        agg[sys_name] = {crit: sum(vals) / len(vals) for crit, vals in crits.items()}
    return agg


def aggregate_by_category(unblinded: list[dict]) -> dict:
    by_cat = defaultdict(lambda: defaultdict(list))
    for entry in unblinded:
        cat = entry["category"]
        for sys_name, scores in entry["systems"].items():
            by_cat[cat][sys_name].append(scores.get("total", 0))
    result = {}
    for cat, sys_totals in by_cat.items():
        result[cat] = {s: sum(v) / len(v) for s, v in sys_totals.items()}
    return result


def plot_radar(aggregated: dict, output_path: str | Path) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    labels = CRITERIA
    num_vars = len(labels)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    for sys_name, scores in aggregated.items():
        values = [scores.get(c, 0) for c in labels]
        values += values[:1]
        ax.plot(angles, values, label=sys_name, linewidth=2)
        ax.fill(angles, values, alpha=0.1)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 3)
    ax.set_title("Scores moyens par critère (0-3)", y=1.08)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


def main():
    blind_scores = json.loads(Path("results/scores/blind_scores.json").read_text(encoding="utf-8"))
    mapping = json.loads(Path("results/raw_responses/label_mapping.json").read_text(encoding="utf-8"))

    unblinded = unblind_scores(blind_scores, mapping)
    by_system = aggregate_by_system(unblinded)
    by_category = aggregate_by_category(unblinded)

    Path("results/scores/unblinded.json").write_text(
        json.dumps(unblinded, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    Path("results/scores/summary.json").write_text(
        json.dumps({"by_system": by_system, "by_category": by_category}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    plot_radar(by_system, "results/charts/radar_by_system.png")

    print("=== Résultats par système ===")
    for sys_name, scores in by_system.items():
        print(f"\n{sys_name}:")
        for crit in CRITERIA + ["total"]:
            print(f"  {crit:20s} : {scores.get(crit, 0):.2f}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test — PASS**

```bash
pytest tests/test_analyze.py -v
```

- [ ] **Step 5: Run full analysis**

```bash
python -m src.eval.analyze
```
Expected: summary printed + radar chart saved.

- [ ] **Step 6: Commit**

```bash
git add src/eval/analyze.py tests/test_analyze.py results/scores/ results/charts/
git commit -m "feat(eval): unblinding, aggregation and radar chart"
```

---

## Task 4.5: Grid search on re-ranking coefficients

**Files:**
- Create: `src/eval/grid_search.py`
- Create: `tests/test_grid_search.py`

`★ Insight ─────────────────────────────────────`
We sweep `secnumedu_boost` ∈ {1.0, 1.2, 1.5, 1.8, 2.0} keeping other coefficients fixed at baseline. This isolates the effect of the "primary label boost" and produces a sensitivity curve for the paper. If the curve is flat, it means re-ranking isn't actually doing anything — important negative result.
`─────────────────────────────────────────────────`

- [ ] **Step 1: Write failing test**

Create `tests/test_grid_search.py`:
```python
from src.eval.grid_search import make_coefficient_grid


def test_grid_contains_baseline_and_extremes():
    grid = make_coefficient_grid()
    assert len(grid) == 5
    boosts = [cfg.secnumedu_boost for cfg in grid]
    assert 1.0 in boosts  # no-boost baseline
    assert 1.5 in boosts  # default
    assert 2.0 in boosts  # strong
```

- [ ] **Step 2: Run test — FAIL**

```bash
pytest tests/test_grid_search.py -v
```

- [ ] **Step 3: Implement**

Create `src/eval/grid_search.py`:
```python
import json
from pathlib import Path
from mistralai import Mistral
from anthropic import Anthropic
from src.config import load_config
from src.rag.reranker import RerankConfig
from src.rag.pipeline import OrientIAPipeline
from src.eval.systems import OurRagSystem, MistralRawSystem, ChatGPTRecordedSystem
from src.eval.runner import run_benchmark
from src.eval.judge import judge_all
from src.eval.analyze import unblind_scores, aggregate_by_system


def make_coefficient_grid() -> list[RerankConfig]:
    boosts = [1.0, 1.2, 1.5, 1.8, 2.0]
    return [RerankConfig(secnumedu_boost=b, cti_boost=1.3, grade_master_boost=1.3, public_boost=1.1)
            for b in boosts]


def main():
    cfg = load_config()
    mistral = Mistral(api_key=cfg.mistral_api_key)
    anthropic = Anthropic(api_key=cfg.anthropic_api_key)

    fiches = json.loads(Path("data/processed/formations.json").read_text(encoding="utf-8"))
    pipeline = OrientIAPipeline(mistral, fiches)
    print("Building shared index...")
    pipeline.build_index()

    questions = json.loads(Path("src/eval/questions.json").read_text(encoding="utf-8"))["questions"]
    scored_questions = [q for q in questions if q["category"] != "honnetete"]

    grid_results = []
    for i, rerank_cfg in enumerate(make_coefficient_grid()):
        print(f"\n=== Grid cell {i+1}: secnumedu_boost={rerank_cfg.secnumedu_boost} ===")
        pipeline.rerank_config = rerank_cfg

        systems = {
            "our_rag": OurRagSystem(pipeline),
            "mistral_raw": MistralRawSystem(mistral),
            "chatgpt_recorded": ChatGPTRecordedSystem("data/chatgpt_recorded.json"),
        }

        out_dir = Path(f"results/grid/cell_{i}")
        run_benchmark(scored_questions, systems, out_dir, seed=42 + i)

        blind_scores = judge_all(
            anthropic,
            json.loads((out_dir / "responses_blind.json").read_text(encoding="utf-8")),
        )
        (out_dir / "blind_scores.json").write_text(
            json.dumps(blind_scores, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        mapping = json.loads((out_dir / "label_mapping.json").read_text(encoding="utf-8"))
        unblinded = unblind_scores(blind_scores, mapping)
        summary = aggregate_by_system(unblinded)

        grid_results.append({
            "config": rerank_cfg.as_dict(),
            "summary": summary,
        })

    Path("results/grid").mkdir(parents=True, exist_ok=True)
    Path("results/grid/grid_summary.json").write_text(
        json.dumps(grid_results, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("\n=== GRID SEARCH RESULTS ===")
    for cell in grid_results:
        boost = cell["config"]["secnumedu_boost"]
        our_total = cell["summary"]["our_rag"]["total"]
        print(f"secnumedu_boost={boost:.1f} → our_rag total = {our_total:.2f}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test — PASS**

```bash
pytest tests/test_grid_search.py -v
```

- [ ] **Step 5: Run full grid search**

Warning: this runs the judge 5× on all scored questions. Budget check: 5 × 30 × ~500 tokens/question = 75k tokens Claude. Well within free tier.

```bash
python -m src.eval.grid_search
```
Expected: 5 grid cells with summaries, ending with a curve of total scores per boost value.

- [ ] **Step 6: Commit**

```bash
git add src/eval/grid_search.py tests/test_grid_search.py results/grid/
git commit -m "feat(eval): grid search over secnumedu_boost coefficient"
```

---

# Phase 5 — Interface

## Task 5.1: FastAPI backend

**Files:**
- Create: `src/api/main.py`
- Create: `tests/test_api.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_api.py`:
```python
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


def test_api_ask_endpoint_returns_answer_and_sources(monkeypatch):
    mock_pipeline = MagicMock()
    mock_pipeline.answer.return_value = (
        "Réponse",
        [{"fiche": {"nom": "F", "etablissement": "E", "ville": "V",
                    "labels": ["SecNumEdu"], "statut": "Public"}, "score": 0.9}],
    )

    import src.api.main as main
    monkeypatch.setattr(main, "_load_pipeline", lambda: mock_pipeline)
    main.app.state.pipeline = None  # force re-init

    client = TestClient(main.app)
    response = client.post("/ask", json={"question": "Quelles formations cyber ?"})
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Réponse"
    assert len(data["sources"]) == 1
    assert data["sources"][0]["nom"] == "F"
```

- [ ] **Step 2: Run test — FAIL**

```bash
pytest tests/test_api.py -v
```

- [ ] **Step 3: Implement**

Create `src/api/main.py`:
```python
import json
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from mistralai import Mistral
from src.config import load_config
from src.rag.pipeline import OrientIAPipeline


class Question(BaseModel):
    question: str


class Source(BaseModel):
    nom: str
    etablissement: str
    ville: str
    labels: list[str]
    statut: str
    score: float


class Answer(BaseModel):
    answer: str
    sources: list[Source]


def _load_pipeline() -> OrientIAPipeline:
    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key)
    fiches = json.loads(Path("data/processed/formations.json").read_text(encoding="utf-8"))
    pipeline = OrientIAPipeline(client, fiches)
    pipeline.build_index()
    return pipeline


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pipeline = _load_pipeline()
    yield


app = FastAPI(title="OrientIA", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/ask", response_model=Answer)
def ask(q: Question) -> Answer:
    pipeline = app.state.pipeline
    if pipeline is None:
        pipeline = _load_pipeline()
        app.state.pipeline = pipeline

    answer_text, retrieved = pipeline.answer(q.question)
    sources = [
        Source(
            nom=r["fiche"].get("nom", ""),
            etablissement=r["fiche"].get("etablissement", ""),
            ville=r["fiche"].get("ville", ""),
            labels=r["fiche"].get("labels") or [],
            statut=r["fiche"].get("statut") or "Inconnu",
            score=float(r["score"]),
        )
        for r in retrieved
    ]
    return Answer(answer=answer_text, sources=sources)


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 4: Run test — PASS**

```bash
pytest tests/test_api.py -v
```

- [ ] **Step 5: Run server locally**

```bash
uvicorn src.api.main:app --reload --port 8000
```
In another terminal:
```bash
curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" \
  -d '{"question":"Quelles formations cyber en Bretagne ?"}' | python -m json.tool
```
Expected: JSON response with answer + sources.

- [ ] **Step 6: Commit**

```bash
git add src/api/main.py tests/test_api.py
git commit -m "feat(api): fastapi /ask endpoint with lifespan pipeline init"
```

---

## Task 5.2: React frontend scaffold

**Files:**
- Create: `frontend/package.json`, `frontend/vite.config.js`, `frontend/index.html`, `frontend/tailwind.config.js`, `frontend/src/main.jsx`, `frontend/src/App.jsx`, `frontend/src/api.js`

- [ ] **Step 1: Scaffold Vite project**

```bash
cd /home/matteo_linux/projets/OrientIA
npm create vite@latest frontend -- --template react
cd frontend
npm install
npm install -D tailwindcss@latest postcss autoprefixer
npx tailwindcss init -p
cd ..
```

- [ ] **Step 2: Configure Tailwind**

Create/overwrite `frontend/tailwind.config.js`:
```js
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: { extend: {} },
  plugins: [],
};
```

Overwrite `frontend/src/index.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 3: Write api.js**

Create `frontend/src/api.js`:
```js
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function askQuestion(question) {
  const res = await fetch(`${API_URL}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
```

- [ ] **Step 4: Write App.jsx**

Overwrite `frontend/src/App.jsx`:
```jsx
import { useState } from "react";
import { askQuestion } from "./api";

export default function App() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState([]);
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    if (!question.trim()) return;
    setLoading(true);
    setError("");
    setAnswer("");
    setSources([]);
    try {
      const data = await askQuestion(question);
      setAnswer(data.answer);
      setSources(data.sources);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="max-w-4xl mx-auto p-6">
        <header className="mb-8">
          <h1 className="text-3xl font-bold">OrientIA</h1>
          <p className="text-slate-600">
            Assistant d'orientation spécialisé, sourcé sur données officielles françaises.
          </p>
        </header>

        <form onSubmit={handleSubmit} className="mb-6">
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Pose ta question d'orientation..."
            rows={3}
            className="w-full rounded-lg border border-slate-300 p-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="submit"
            disabled={loading}
            className="mt-2 rounded-lg bg-blue-600 px-6 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? "Analyse..." : "Poser la question"}
          </button>
        </form>

        {error && <div className="rounded bg-red-100 p-3 text-red-800">{error}</div>}

        {answer && (
          <div className="grid gap-6 md:grid-cols-3">
            <div className="md:col-span-2 rounded-lg bg-white p-5 shadow-sm">
              <h2 className="mb-3 text-lg font-semibold">Réponse</h2>
              <div className="whitespace-pre-wrap text-sm">{answer}</div>
            </div>
            <aside className="rounded-lg bg-white p-5 shadow-sm">
              <h2 className="mb-3 text-lg font-semibold">Sources utilisées</h2>
              <ul className="space-y-2 text-sm">
                {sources.map((s, i) => (
                  <li key={i} className="border-l-2 border-blue-500 pl-2">
                    <div className="font-semibold">{s.nom}</div>
                    <div className="text-slate-600">
                      {s.etablissement} — {s.ville}
                    </div>
                    <div className="text-xs text-slate-500">
                      {s.statut} · {s.labels.length > 0 ? s.labels.join(", ") : "aucun label"}
                    </div>
                  </li>
                ))}
              </ul>
            </aside>
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Overwrite main.jsx**

Create/overwrite `frontend/src/main.jsx`:
```jsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

- [ ] **Step 6: Test locally**

```bash
cd frontend && npm run dev
```
Open http://localhost:5173, verify the UI renders. With the backend running (`uvicorn` in another shell), submit a question and verify it returns an answer with sources.

- [ ] **Step 7: Commit**

```bash
cd /home/matteo_linux/projets/OrientIA
git add frontend/package.json frontend/vite.config.js frontend/index.html \
        frontend/tailwind.config.js frontend/postcss.config.js \
        frontend/src/App.jsx frontend/src/main.jsx frontend/src/api.js \
        frontend/src/index.css
git commit -m "feat(frontend): minimal react chat UI with sources panel"
```

---

## Task 5.3: Deployment (manual)

**Files:** (cloud configs)

- [ ] **Step 1: Deploy backend to Railway**

1. Go to https://railway.app, new project, connect GitHub repo.
2. Add env vars (MISTRAL_API_KEY, ANTHROPIC_API_KEY, ONISEP_*).
3. Start command: `uvicorn src.api.main:app --host 0.0.0.0 --port $PORT`
4. Note the deployed URL.

- [ ] **Step 2: Deploy frontend to Vercel**

1. Go to https://vercel.com, import the repo.
2. Root directory: `frontend`.
3. Build command: `npm run build`, output dir: `dist`.
4. Env var: `VITE_API_URL=<Railway URL>`.
5. Deploy.

- [ ] **Step 3: Smoke test the live URL**

Visit the Vercel URL, submit a benchmark question, verify sources appear.

- [ ] **Step 4: Commit deployment notes**

Append to README:
```markdown
## Live demo

- Frontend: https://orientia.vercel.app
- API: https://orientia.railway.app/health
```

```bash
git add README.md
git commit -m "docs: add live demo urls"
```

---

# Phase 6 — Finalization

## Task 6.1: Results write-up

**Files:**
- Create: `results/REPORT.md`

- [ ] **Step 1: Write final report**

Create `results/REPORT.md`:
```markdown
# OrientIA — Résultats du benchmark

## Méthodologie

- **Systèmes évalués** : 3 (notre RAG avec re-ranking, Mistral brut, ChatGPT enregistré)
- **Questions** : 30 questions scoredes + 2 questions d'honnêteté
- **Juge** : Claude Sonnet 4.5 via API Anthropic
- **Protocole** : double-aveugle — labels {A,B,C} randomisés par question, mapping non visible du juge
- **Grille** : 6 critères × 3 points = 18 max par question

## Résultats agrégés

(Copier ici le contenu de `results/scores/summary.json`)

## Radar chart

![Radar](charts/radar_by_system.png)

## Grid search sur secnumedu_boost

(Copier ici `results/grid/grid_summary.json` en tableau)

## Vérifications manuelles (biais marketing, catégorie A)

Pour chaque question de catégorie A :
- Nombre de formations SecNumEdu mentionnées par chaque système
- Ratio public/privé

## Questions d'honnêteté (H1, H2)

Résultats attendus : pas de différence significative entre systèmes.
Résultats observés : (remplir)

## Limites

- Échantillon de 30 questions : étude exploratoire, pas de significativité statistique.
- Juge LLM : peut reproduire ses biais latents ; à compléter par vérification humaine.
- Données Parcoursup 2025 uniquement, ONISEP snapshot à une date T.
- Taux de jointure RNCP + fuzzy : ~70-80% (documenté dans `data/processed/`).
```

- [ ] **Step 2: Fill in the numbers from the actual runs**

Manually copy the aggregated scores from `results/scores/summary.json` and `results/grid/grid_summary.json` into the report.

- [ ] **Step 3: Commit**

```bash
git add results/REPORT.md
git commit -m "docs: final benchmark report"
```

---

## Task 6.2: Demo video script

**Files:**
- Create: `docs/demo_script.md`

- [ ] **Step 1: Write 3-min video script**

Create `docs/demo_script.md`:
```markdown
# OrientIA — Script de démo (3 min)

## 0:00-0:20 — Problème
Voix off : "25% des lycéens en zone dense accèdent aux filières sélectives,
contre 10% en zone rurale. L'IA est devenue le conseiller d'orientation
de 86% des étudiants, mais elle reproduit le biais marketing."

## 0:20-0:45 — Démo 1 : biais marketing
Split-screen. Même question : "Meilleures formations en cybersécurité en France ?"
- Gauche : ChatGPT → EPITA, Guardia Cybersecurity School
- Droite : OrientIA → CyberSchool Rennes, ENSIBS, IMT Atlantique (SecNumEdu ANSSI)

## 0:45-1:10 — Démo 2 : réalisme
Question : "J'ai 11 de moyenne, comment intégrer HEC ?"
- Gauche : ChatGPT → "Travaille dur, tout est possible !"
- Droite : OrientIA → "HEC admet 4% des candidats. Voici SKEMA, Audencia, Grenoble EM
  accessibles, et les passerelles via BTS/BUT."

## 1:10-1:35 — Démo 3 : découverte
Question : "J'aime les données et la géopolitique"
- Gauche : ChatGPT → "Data analyst"
- Droite : OrientIA → "OSINT, intelligence économique, Master IE Paris 8,
  Master SIGAT Rennes 2..."

## 1:35-2:10 — Méthodologie
Graphique radar : notre système domine sur neutralité, réalisme, sourçage.
Texte : "Benchmark en double-aveugle. Juge Claude. 30 questions. Source : données officielles."

## 2:10-2:40 — Innovation technique
Schéma : Mistral + FAISS + re-ranking par labels SecNumEdu.
Texte : "Le re-ranking par labels institutionnels booste les formations publiques
labellisées. Contribution mesurable et reproductible."

## 2:40-3:00 — Conclusion
"Nous ne remplaçons pas l'IA. Nous la mettons au service de l'égalité plutôt que du marketing."
Appel à contribution : repo GitHub public.
```

- [ ] **Step 2: Commit**

```bash
git add docs/demo_script.md
git commit -m "docs: 3-minute demo video script"
```

---

## Task 6.3: Final sanity check

- [ ] **Step 1: Run full test suite**

```bash
pytest tests/ -v --cov=src --cov-report=term-missing
```
Expected: all tests pass, coverage on critical paths (merge, reranker, judge) > 80%.

- [ ] **Step 2: End-to-end smoke test**

```bash
python -m src.rag.cli "J'habite à Brest, quelles formations en cybersécurité ?"
```
Expected: a well-formatted answer citing ENSIBS, IMT Atlantique or similar SecNumEdu formations.

- [ ] **Step 3: Check git log is clean**

```bash
git log --oneline | head -30
```
Expected: atomic, descriptive commits from Phase 0 through Phase 6.

- [ ] **Step 4: Push all commits to GitHub**

The remote was added in Task 0.1, so just push accumulated work:
```bash
git push origin main
```
Expected: private repo at https://github.com/matjussu/OrientIA updated with full history.

- [ ] **Step 5: Tag v1.0**

```bash
git commit --allow-empty -m "chore: v1.0 — benchmark complete, demo ready"
git tag v1.0
git push origin main --tags
```

---

# End of plan

**Key assumptions baked in:**
- Parcoursup CSV columns map correctly after Task 2.2 Step 7 inspection; adjust `COLUMN_MAP` if not.
- ONISEP API returns field names matching Task 2.3 Step 5; adjust the mapping if not.
- Mistral free tier is sufficient: estimate ~500K tokens total across all runs including grid search.
- Anthropic free tier / paid: ~200K tokens for judge + grid search. If blocked, fall back to one judge pass without grid search.
- Manual SecNumEdu structuring takes 1-2h (not automated).
- ChatGPT responses recorded manually through the web interface on a single date.

**Definition of done:**
- All 32 benchmark questions scored by the judge in double-blind mode.
- Radar chart shows our system dominates on neutrality + realism + sourcing.
- Grid search produces a sensitivity curve for the secnumedu_boost coefficient.
- Frontend live on Vercel, backend on Railway, both reachable.
- Repo public on GitHub with clean commit history.
- 3-minute demo video script ready to record.
