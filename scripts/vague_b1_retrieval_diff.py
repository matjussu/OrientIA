"""Vague B.1 retrieval diff — measure the effect of the new
parcoursup_rich_boost on the top-K surfaced for the 6 questions
used in the Vague A qualitative diff.

Compares:
  - WITHOUT boost (parcoursup_rich_boost=1.0, other defaults)
  - WITH boost (parcoursup_rich_boost=1.2, other defaults)

Emits counts of Parcoursup-rich fiches in the top-10 per question.

No LLM calls. No cost. Reproducible retrieval inspection.
"""
from __future__ import annotations

import json
from pathlib import Path
from mistralai.client import Mistral
from src.config import load_config
from src.rag.pipeline import OrientIAPipeline
from src.rag.reranker import RerankConfig, _is_parcoursup_rich


QUESTIONS = [
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


def _retrieve_top_with_cfg(client, fiches, question: str, cfg: RerankConfig) -> list[dict]:
    p = OrientIAPipeline(
        client=client, fiches=fiches, rerank_config=cfg,
        use_mmr=True, use_intent=True,
    )
    p.load_index_from("data/embeddings/formations.index")
    # Use the same internal logic as pipeline.answer() but skip generation
    from src.rag.retriever import retrieve_top_k
    from src.rag.reranker import rerank
    from src.rag.mmr import mmr_select
    from src.rag.intent import classify_intent, intent_to_config

    icfg = intent_to_config(classify_intent(question))
    retrieved = retrieve_top_k(client, p.index, fiches, question, k=30)
    reranked = rerank(retrieved, cfg)
    top = mmr_select(reranked, k=icfg.top_k_sources, lambda_=icfg.mmr_lambda)
    return top


def main() -> None:
    cfg_env = load_config()
    client = Mistral(api_key=cfg_env.mistral_api_key, timeout_ms=120000)
    fiches = json.loads(Path("data/processed/formations.json").read_text(encoding="utf-8"))

    cfg_off = RerankConfig(parcoursup_rich_boost=1.0)   # old behavior
    cfg_on = RerankConfig(parcoursup_rich_boost=1.2)    # Vague B.1 default

    print(f"{'Q':<4} {'Category':<18} {'Rich/10 OFF':<12} {'Rich/10 ON':<12} {'Δ':<5}")
    print("-" * 60)

    total_off = 0
    total_on = 0
    for q in QUESTIONS:
        top_off = _retrieve_top_with_cfg(client, fiches, q["text"], cfg_off)
        top_on = _retrieve_top_with_cfg(client, fiches, q["text"], cfg_on)
        rich_off = sum(1 for r in top_off if _is_parcoursup_rich(r["fiche"]))
        rich_on = sum(1 for r in top_on if _is_parcoursup_rich(r["fiche"]))
        delta = rich_on - rich_off
        total_off += rich_off
        total_on += rich_on
        sign = "+" if delta > 0 else ""
        print(f"{q['id']:<4} {q['category']:<18} {rich_off}/{len(top_off)}          "
              f"{rich_on}/{len(top_on)}          {sign}{delta}")

    print("-" * 60)
    print(f"{'Total':<22} {total_off:<12} {total_on:<12} {'+' if total_on > total_off else ''}{total_on - total_off}")


if __name__ == "__main__":
    main()
