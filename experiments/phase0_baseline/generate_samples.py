"""Phase 0.2 — Generate baseline samples on 10 representative questions.

Runs the current (run 6) pipeline on 10 questions spanning all categories,
saves responses + basic metrics to samples.json for before/after comparison
in Phase 1.

Cost: ~$0.20 Mistral paid tier (10 chat.complete calls + retrieval).
"""
import json
import re
import time
from pathlib import Path

from mistralai.client import Mistral

from src.config import load_config
from src.rag.pipeline import OrientIAPipeline


TARGET_QIDS = ["A1", "B1", "B4", "C1", "C3", "D1", "D3", "E1", "E4", "H1"]

FICHES_PATH = "data/processed/formations.json"
INDEX_PATH = "data/embeddings/formations.index"
QUESTIONS_PATH = "src/eval/questions.json"
OUTPUT_PATH = "experiments/phase0_baseline/samples.json"

CONFESSION_PATTERNS = [
    r"n'ai pas de donn[ée]es",
    r"fiches ne couvrent",
    r"pas d'informations",
    r"aucune donn[ée]e",
    r"je ne dispose pas",
    r"hors contexte",
]


def count_citations(text: str) -> int:
    patterns = [
        r"ONISEP",
        r"Parcoursup",
        r"SecNumEdu",
        r"\bCTI\b",
        r"FOR\.\w+",
        r"Source\s*:",
        r"rapport\s+\w+",
    ]
    return sum(len(re.findall(p, text, flags=re.IGNORECASE)) for p in patterns)


def count_confession_phrases(text: str) -> int:
    return sum(len(re.findall(p, text, flags=re.IGNORECASE)) for p in CONFESSION_PATTERNS)


def count_distinct_cities(text: str) -> int:
    cities = {
        "paris", "lyon", "toulouse", "bordeaux", "marseille", "nice", "nantes",
        "strasbourg", "lille", "rennes", "brest", "montpellier", "grenoble",
        "saclay", "perpignan", "caen", "reims", "dijon", "orléans", "amiens",
        "clermont", "poitiers", "limoges", "avignon", "metz", "nancy",
        "compiègne", "compiegne", "rouen", "tours", "aurillac", "troyes",
        "valenciennes", "le mans", "pau", "besançon", "besancon", "cergy",
    }
    text_lower = text.lower()
    found = {c for c in cities if c in text_lower}
    return len(found)


def main() -> None:
    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=120000)

    fiches = json.loads(Path(FICHES_PATH).read_text(encoding="utf-8"))
    questions_raw = json.loads(Path(QUESTIONS_PATH).read_text(encoding="utf-8"))
    questions = {q["id"]: q for q in questions_raw["questions"]}

    print(f"Loaded {len(fiches)} fiches and {len(questions)} questions")

    pipeline = OrientIAPipeline(client, fiches)
    if not Path(INDEX_PATH).exists():
        raise FileNotFoundError(
            f"FAISS index missing at {INDEX_PATH}. Build it first."
        )
    pipeline.load_index_from(INDEX_PATH)
    print(f"Loaded FAISS index from {INDEX_PATH}")

    samples = []
    for qid in TARGET_QIDS:
        q = questions[qid]
        print(f"\n[{qid}] {q['category']} — {q['text'][:60]}...")
        t0 = time.time()
        try:
            answer, top = pipeline.answer(q["text"])
        except Exception as exc:
            print(f"  ERROR: {exc}")
            samples.append({
                "id": qid,
                "category": q["category"],
                "text": q["text"],
                "error": str(exc),
            })
            continue
        elapsed = time.time() - t0

        word_count = len(answer.split())
        citations = count_citations(answer)
        confessions = count_confession_phrases(answer)
        distinct_cities = count_distinct_cities(answer)

        print(
            f"  ok in {elapsed:.1f}s | {word_count} mots | "
            f"{citations} citations | {confessions} confessions | "
            f"{distinct_cities} villes"
        )

        samples.append({
            "id": qid,
            "category": q["category"],
            "text": q["text"],
            "answer": answer,
            "retrieved_count": len(top),
            "retrieved_top5_names": [
                (t["fiche"].get("nom") or "")[:80] for t in top[:5]
            ],
            "metrics": {
                "word_count": word_count,
                "citations": citations,
                "confessions": confessions,
                "distinct_cities": distinct_cities,
                "elapsed_s": round(elapsed, 2),
            },
        })

    output = {
        "phase": "0.2 baseline",
        "pipeline_version": "run6_full_stack",
        "n_fiches": len(fiches),
        "samples": samples,
        "aggregate": {
            "mean_word_count": round(
                sum(s["metrics"]["word_count"] for s in samples if "metrics" in s)
                / max(1, sum(1 for s in samples if "metrics" in s)),
                1,
            ),
            "mean_citations": round(
                sum(s["metrics"]["citations"] for s in samples if "metrics" in s)
                / max(1, sum(1 for s in samples if "metrics" in s)),
                1,
            ),
            "total_confessions": sum(
                s["metrics"]["confessions"] for s in samples if "metrics" in s
            ),
            "questions_with_confession": sum(
                1 for s in samples if "metrics" in s and s["metrics"]["confessions"] > 0
            ),
        },
    }

    Path(OUTPUT_PATH).parent.mkdir(parents=True, exist_ok=True)
    Path(OUTPUT_PATH).write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nSaved to {OUTPUT_PATH}")
    print(f"\nAggregate: {json.dumps(output['aggregate'], indent=2)}")


if __name__ == "__main__":
    main()
