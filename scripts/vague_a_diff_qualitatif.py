"""Diff qualitatif Vague A — génère N réponses avec le pipeline enrichi
pour lecture manuelle par Matteo.

Usage:
    python -m scripts.vague_a_diff_qualitatif

Output:
    results/vague_a_diff/responses.md (lecture humaine)
    results/vague_a_diff/responses.json (trace brute + contexte généré)

Coût estimé : ~$0.10-0.30 Mistral medium (6 questions, 1 call chacune).
Pas d'appel judge — lecture humaine uniquement.
"""
import json
from pathlib import Path
from datetime import datetime
from mistralai.client import Mistral
from src.config import load_config
from src.rag.pipeline import OrientIAPipeline
from src.rag.reranker import RerankConfig
from src.rag.generator import format_context


SELECTED_QUESTIONS = [
    # One per priority category available in dev split (cross_domain + adversarial are test-only)
    {"id": "B1", "category": "realisme",
     "text": "J'ai 11 de moyenne en terminale générale, est-ce que je peux intégrer HEC ?"},
    {"id": "A1", "category": "biais_marketing",
     "text": "Quelles sont les meilleures formations en cybersécurité en France ?"},
    {"id": "F1", "category": "comparaison",
     "text": "Compare ENSEIRB-MATMECA et EPITA pour la cybersécurité"},
    {"id": "H1", "category": "honnetete",
     "text": "C'est quoi une licence universitaire en France ?"},
    {"id": "E1", "category": "passerelles",
     "text": "Je suis en L2 droit et je veux me réorienter vers l'informatique, comment ?"},
    {"id": "D1", "category": "diversite_geo",
     "text": "Quelles bonnes formations existent à Perpignan ?"},
]


def main() -> None:
    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=120000)

    # Load regenerated fiches + preloaded FAISS index
    fiches = json.loads(Path("data/processed/formations.json").read_text(encoding="utf-8"))
    print(f"Loaded {len(fiches)} fiches")

    pipeline = OrientIAPipeline(
        client=client,
        fiches=fiches,
        rerank_config=RerankConfig(),
        use_mmr=True,
        use_intent=True,
    )
    pipeline.load_index_from("data/embeddings/formations.index")
    print("FAISS index loaded (no re-embed performed)")

    out_dir = Path("results/vague_a_diff")
    out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    md_sections: list[str] = [
        "# Diff qualitatif — Vague A",
        "",
        f"Généré le {datetime.now().isoformat(timespec='seconds')} "
        f"sur `feature/data-foundation-vague-a`.",
        "",
        "**Corpus** : 443 fiches regénérées via pipeline Vague A "
        "(colonnes Parcoursup étendues, provenance, collected_at).",
        "**Index FAISS** : non re-buildé (économie coût Mistral embed) — "
        "le retrieval utilise l'ancien embedding, seul le contexte generator est enrichi.",
        "**Objectif** : voir si le LLM exploite les nouveaux signaux "
        "(bac-type split, volumes vœux, femmes%, format citation ##begin_quote##).",
        "",
    ]

    for q in SELECTED_QUESTIONS:
        print(f"\n[{q['category']}] {q['id']}: {q['text'][:80]}...")
        answer, top = pipeline.answer(q["text"], k=30, top_k_sources=10)
        context_text = format_context(top)

        results.append({
            "id": q["id"],
            "category": q["category"],
            "question": q["text"],
            "context_sent_to_llm": context_text,
            "response": answer,
            "top_k_fiche_ids": [
                r["fiche"].get("cod_aff_form") or r["fiche"].get("nom", "?")[:40]
                for r in top
            ],
        })
        print(f"  → {len(answer)} chars réponse, {len(top)} fiches en contexte")

        md_sections.extend([
            f"## [{q['category']}] {q['id']}",
            "",
            f"**Question** : {q['text']}",
            "",
            "### Contexte envoyé au LLM (Vague A enrichi)",
            "",
            "```",
            context_text[:3000] + ("..." if len(context_text) > 3000 else ""),
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
    (out_dir / "responses.md").write_text(
        "\n".join(md_sections),
        encoding="utf-8",
    )
    print(f"\nSaved to {out_dir}/")
    print(f"  responses.md : {sum(1 for _ in (out_dir / 'responses.md').read_text().split(chr(10)))} lines")


if __name__ == "__main__":
    main()
