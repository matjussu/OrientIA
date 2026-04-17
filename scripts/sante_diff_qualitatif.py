"""Qualitative diff on santé-focused questions — validates the extension.

Runs 4 test questions covering main santé trajectories:
- Generic "I want to do medicine"
- Reorientation scenario
- Concrete specific: nurse vs kiné
- Profile/selectivity: PASS with average grades

Outputs a markdown file ready for Matteo to read.
"""
import json
from pathlib import Path
from datetime import datetime
from mistralai.client import Mistral
from src.config import load_config
from src.rag.pipeline import OrientIAPipeline
from src.rag.reranker import RerankConfig
from src.rag.generator import format_context
from src.eval.metrics_det import score_response


QUESTIONS = [
    {"id": "S1", "category": "decouverte_sante",
     "text": "Je veux devenir médecin, comment faire ?"},
    {"id": "S2", "category": "realisme_sante",
     "text": "J'ai 12 de moyenne générale en terminale, est-ce que j'ai mes chances en PASS ?"},
    {"id": "S3", "category": "comparaison_sante",
     "text": "Compare devenir infirmier et kinésithérapeute : études, salaires, débouchés."},
    {"id": "S4", "category": "passerelles_sante",
     "text": "Je suis en L2 psychologie et je veux me réorienter vers l'orthophonie, comment ?"},
]


def main() -> None:
    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=120000)
    fiches = json.loads(Path("data/processed/formations.json").read_text(encoding="utf-8"))
    print(f"Loaded {len(fiches)} fiches ({sum(1 for f in fiches if f.get('domaine') == 'sante')} santé)")

    pipeline = OrientIAPipeline(
        client=client, fiches=fiches, rerank_config=RerankConfig(),
        use_mmr=True, use_intent=True,
    )
    pipeline.load_index_from("data/embeddings/formations.index")

    out_dir = Path("results/sante_diff")
    out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    md: list[str] = [
        "# Diff qualitatif — Extension santé",
        "",
        f"Généré le {datetime.now().isoformat(timespec='seconds')}",
        f"**Corpus** : 1424 fiches (981 santé + cyber/data) sur index FAISS re-buildé.",
        "",
    ]

    for q in QUESTIONS:
        print(f"\n[{q['category']}] {q['id']}: {q['text'][:80]}...")
        answer, top = pipeline.answer(q["text"], k=30, top_k_sources=10)
        ctx = format_context(top)

        scores = score_response(answer, fiches)
        b3 = scores["actionability"]["score"]
        b5 = scores["fraicheur"]["score"]
        b6 = scores["citation_precision"]["score"]
        words = len(answer.split())
        has_sante_in_ctx = sum(1 for r in top if r["fiche"].get("domaine") == "sante")
        has_insertion_ctx = sum(1 for r in top if r["fiche"].get("insertion"))

        results.append({
            "id": q["id"], "category": q["category"], "question": q["text"],
            "answer": answer, "top_contexts": has_sante_in_ctx,
            "insertion_available": has_insertion_ctx,
            "b3": b3, "b5": b5, "b6": b6, "words": words,
        })
        print(f"  → {words} mots | santé dans top10={has_sante_in_ctx} | "
              f"insertion dans top10={has_insertion_ctx} | B3={b3} B5={b5} B6={b6}")

        md.extend([
            f"## [{q['category']}] {q['id']}",
            "",
            f"**Question** : {q['text']}",
            "",
            f"**Metrics** : B3={b3}/6 | B5={b5}/3 | B6={b6} | {words} mots | "
            f"{has_sante_in_ctx}/10 fiches santé | {has_insertion_ctx}/10 avec insertion",
            "",
            "### Contexte (extrait)",
            "```",
            ctx[:2000] + ("..." if len(ctx) > 2000 else ""),
            "```",
            "",
            "### Réponse générée",
            "",
            answer,
            "",
            "---",
            "",
        ])

    (out_dir / "responses.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_dir / "responses.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\nSaved to {out_dir}/")

    # Print aggregate summary
    avg_b3 = sum(r["b3"] for r in results) / len(results)
    avg_b5 = sum(r["b5"] for r in results) / len(results)
    b6s = [r["b6"] for r in results if r["b6"] is not None]
    avg_b6 = sum(b6s) / len(b6s) if b6s else None
    avg_words = sum(r["words"] for r in results) / len(results)
    print(f"\n=== AGGREGATE (santé diff) ===")
    print(f"  B3 avg: {avg_b3:.2f}/6")
    print(f"  B5 avg: {avg_b5:.2f}/3")
    print(f"  B6 avg: {avg_b6:.2f} (n={len(b6s)})" if avg_b6 is not None
          else "  B6 avg: N/A (no citations)")
    print(f"  Words avg: {avg_words:.0f}")


if __name__ == "__main__":
    main()
