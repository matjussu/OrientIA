"""F.3.d — Local retrieval inspection on the dev set.

Compares the top-K sources surfaced by the RAG pipeline with and
without the Phase F.3 extensions (MMR + intent routing). Pure
retrieval — no LLM generation calls, so this script is **free**
and reproducible.

Usage:
  python -m src.eval.inspect_retrieval                # all 32 dev qs
  python -m src.eval.inspect_retrieval --first 5      # quick look
  python -m src.eval.inspect_retrieval --category comparaison

Outputs:
  results/retrieval_inspection.md — markdown table per question
  prints summary stats: distinct cities/etablissements per top-k
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from src.config import load_config
from src.rag.pipeline import OrientIAPipeline
from src.rag.intent import classify_intent
from mistralai.client import Mistral


FICHES_PATH = "data/processed/formations.json"
INDEX_PATH = "data/embeddings/formations.index"
QUESTIONS_PATH = "src/eval/questions.json"
OUT_PATH = "results/retrieval_inspection.md"


def _build_pipeline(client: Mistral, fiches: list[dict], **kwargs) -> OrientIAPipeline:
    p = OrientIAPipeline(client, fiches, **kwargs)
    if Path(INDEX_PATH).exists():
        p.load_index_from(INDEX_PATH)
    else:
        raise RuntimeError(f"FAISS index missing at {INDEX_PATH}")
    return p


def _retrieve_only(pipeline: OrientIAPipeline, question: str) -> list[dict]:
    """Run retrieve + rerank (+ optional MMR + intent), return top
    sources WITHOUT the LLM generation call."""
    from src.rag.retriever import retrieve_top_k
    from src.rag.reranker import rerank
    from src.rag.mmr import mmr_select
    from src.rag.intent import intent_to_config

    if pipeline.index is None:
        raise RuntimeError("Pipeline not built")

    top_k_sources = 10
    mmr_lambda = pipeline.mmr_lambda
    if pipeline.use_intent:
        cfg = intent_to_config(classify_intent(question))
        top_k_sources = cfg.top_k_sources
        mmr_lambda = cfg.mmr_lambda

    retrieved = retrieve_top_k(
        pipeline.client, pipeline.index, pipeline.fiches, question, k=30
    )
    reranked = rerank(retrieved, pipeline.rerank_config)
    if pipeline.use_mmr:
        return mmr_select(reranked, k=top_k_sources, lambda_=mmr_lambda)
    return reranked[:top_k_sources]


def _summarise(sources: list[dict]) -> dict:
    villes = [s["fiche"].get("ville") or "?" for s in sources]
    etabs = [s["fiche"].get("etablissement") or s["fiche"].get("nom") or "?"
             for s in sources]
    labels = [tuple(s["fiche"].get("labels") or []) for s in sources]
    return {
        "n": len(sources),
        "distinct_villes": len(set(villes)),
        "distinct_etabs": len(set(etabs)),
        "labelled_count": sum(1 for ls in labels if ls),
        "top_villes": Counter(villes).most_common(3),
        "etabs": etabs,
    }


def _format_block(question: dict, base: list[dict], extended: list[dict]) -> str:
    intent = classify_intent(question["text"])
    base_s = _summarise(base)
    ext_s = _summarise(extended)
    lines = [
        f"### {question['id']} — {question['category']} ({intent})",
        f"> {question['text']}",
        "",
        f"| metric | baseline | F.3 (MMR+intent) |",
        f"|---|---|---|",
        f"| top-k | {base_s['n']} | {ext_s['n']} |",
        f"| distinct villes | {base_s['distinct_villes']} | {ext_s['distinct_villes']} |",
        f"| distinct etabs | {base_s['distinct_etabs']} | {ext_s['distinct_etabs']} |",
        f"| labelled fiches | {base_s['labelled_count']} | {ext_s['labelled_count']} |",
        "",
        "**baseline etabs:** " + ", ".join(base_s["etabs"][:8]),
        "",
        "**F.3 etabs:** " + ", ".join(ext_s["etabs"][:8]),
        "",
        "---",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first", type=int, default=0,
                        help="Limit to first N dev questions")
    parser.add_argument("--category", default="",
                        help="Filter to one category (e.g. comparaison)")
    parser.add_argument("--out", default=OUT_PATH)
    args = parser.parse_args()

    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=120000)
    fiches = json.loads(Path(FICHES_PATH).read_text(encoding="utf-8"))

    base = _build_pipeline(client, fiches)
    extended = _build_pipeline(client, fiches, use_mmr=True, use_intent=True)

    questions = json.loads(Path(QUESTIONS_PATH).read_text(encoding="utf-8"))[
        "questions"
    ]
    dev_questions = [q for q in questions if q.get("split") == "dev"]
    if args.category:
        dev_questions = [q for q in dev_questions if q["category"] == args.category]
    if args.first > 0:
        dev_questions = dev_questions[: args.first]

    print(f"Inspecting {len(dev_questions)} dev questions...")

    blocks = []
    aggregate = {"base_villes": 0, "ext_villes": 0,
                 "base_etabs": 0, "ext_etabs": 0,
                 "base_labelled": 0, "ext_labelled": 0,
                 "n": 0}
    for q in dev_questions:
        b = _retrieve_only(base, q["text"])
        e = _retrieve_only(extended, q["text"])
        blocks.append(_format_block(q, b, e))
        bs, es = _summarise(b), _summarise(e)
        aggregate["base_villes"] += bs["distinct_villes"]
        aggregate["ext_villes"] += es["distinct_villes"]
        aggregate["base_etabs"] += bs["distinct_etabs"]
        aggregate["ext_etabs"] += es["distinct_etabs"]
        aggregate["base_labelled"] += bs["labelled_count"]
        aggregate["ext_labelled"] += es["labelled_count"]
        aggregate["n"] += 1
        print(f"  {q['id']:6s} [{q['category']:15s}] base villes={bs['distinct_villes']} → ext={es['distinct_villes']}")

    n = aggregate["n"] or 1
    summary = (
        f"# Retrieval Inspection — Dev Set ({n} questions)\n\n"
        f"## Aggregate (mean per question)\n\n"
        f"| metric | baseline | F.3 (MMR+intent) | delta |\n"
        f"|---|---|---|---|\n"
        f"| distinct villes | {aggregate['base_villes']/n:.2f} | {aggregate['ext_villes']/n:.2f} | "
        f"{(aggregate['ext_villes']-aggregate['base_villes'])/n:+.2f} |\n"
        f"| distinct etabs | {aggregate['base_etabs']/n:.2f} | {aggregate['ext_etabs']/n:.2f} | "
        f"{(aggregate['ext_etabs']-aggregate['base_etabs'])/n:+.2f} |\n"
        f"| labelled fiches | {aggregate['base_labelled']/n:.2f} | {aggregate['ext_labelled']/n:.2f} | "
        f"{(aggregate['ext_labelled']-aggregate['base_labelled'])/n:+.2f} |\n\n"
        f"## Per-question detail\n\n"
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(summary + "\n".join(blocks), encoding="utf-8")
    print(f"\nWrote {out_path}")
    print(f"\nAggregate (mean):")
    print(f"  villes:    {aggregate['base_villes']/n:.2f} → {aggregate['ext_villes']/n:.2f}")
    print(f"  etabs:     {aggregate['base_etabs']/n:.2f} → {aggregate['ext_etabs']/n:.2f}")
    print(f"  labelled:  {aggregate['base_labelled']/n:.2f} → {aggregate['ext_labelled']/n:.2f}")


if __name__ == "__main__":
    main()
