"""Embed les Q&A Golden (keep+flag) en FAISS index dédié — Sprint 10 chantier D.

Charge `data/golden_qa/golden_qa_v1.jsonl`, filtre `decision in (keep, flag)`,
embed `question_seed + " | " + final_qa.question` (PAS l'answer — décision
sync architecture : embed sur intent matching, l'answer arrive en context
post-retrieve), produit :

- `data/embeddings/golden_qa.index` (FAISS IndexFlatL2 dim 1024)
- `data/processed/golden_qa_meta.json` (mapping idx → record complet
  pour récupérer answer/score/critique post-retrieve top-1)

Usage : `python3 scripts/embed_golden_qa.py`

Coût Mistral-embed : ~45 vectors × ~50 tokens = 2.25k tokens = ~$0.0002 (négligeable).

Spec ordre Jarvis : 2026-04-29-1146-claudette-orientia-sprint10-finalisation-rag-complet (chantier D-1).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from mistralai.client import Mistral

from src.config import load_config
from src.rag.embeddings import embed_texts_batched
from src.rag.index import build_index, save_index

ROOT = Path(__file__).resolve().parents[1]
INPUT_JSONL = ROOT / "data" / "golden_qa" / "golden_qa_v1.jsonl"
OUTPUT_INDEX = ROOT / "data" / "embeddings" / "golden_qa.index"
OUTPUT_META = ROOT / "data" / "processed" / "golden_qa_meta.json"


def load_keep_flag(path: Path = INPUT_JSONL) -> list[dict]:
    """Charge les records keep+flag depuis le JSONL Q&A Golden."""
    if not path.exists():
        raise FileNotFoundError(f"Q&A Golden JSONL absent : {path}")
    records = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec.get("decision") in ("keep", "flag"):
                records.append(rec)
    return records


def build_embed_text(rec: dict) -> str:
    """Assemble le texte à embedder pour une Q&A Golden.

    Décision sync architecture (validée Jarvis) : embed `question_seed +
    final_qa.question`, PAS l'answer. Justification : matching côté user
    query = intent question, l'answer arrive en context post-retrieve.
    Embed answer dilue le signal sémantique.
    """
    seed = (rec.get("question_seed") or "").strip()
    refined_q = (rec.get("final_qa") or {}).get("question", "").strip()
    if not seed and not refined_q:
        # Edge case : record sans question — fallback sur le prompt_id
        return f"{rec.get('prompt_id', 'unknown')} {rec.get('category', '')}"
    if not refined_q:
        return seed
    if not seed:
        return refined_q
    return f"{seed} | {refined_q}"


def build_meta_record(rec: dict, idx: int) -> dict:
    """Assemble le meta record (idx → données utilisables post-retrieve).

    Garde uniquement ce qui est nécessaire pour le few-shot prefix
    (answer_refined, question, score, decision, prompt_id, category) +
    les flags utiles pour debug/audit.
    """
    final_qa = rec.get("final_qa") or {}
    return {
        "idx": idx,
        "prompt_id": rec.get("prompt_id"),
        "category": rec.get("category"),
        "iteration": rec.get("iteration"),
        "question_seed": rec.get("question_seed"),
        "question_refined": final_qa.get("question"),
        "answer_refined": final_qa.get("answer_refined"),
        "score_total": rec.get("score_total"),
        "decision": rec.get("decision"),
        "axe_couvert": rec.get("axe_couvert"),
    }


def main() -> int:
    print(f"==> Chargement Q&A Golden depuis {INPUT_JSONL}")
    records = load_keep_flag()
    print(f"    {len(records)} records keep+flag chargés")

    if not records:
        print("⚠️  Aucun record keep+flag — abort")
        return 1

    # Embedded text + meta
    texts = [build_embed_text(r) for r in records]
    metas = [build_meta_record(r, i) for i, r in enumerate(records)]

    # Sample preview
    print(f"\n--- Sample first 3 embed texts ---")
    for i, t in enumerate(texts[:3]):
        preview = t[:150] + ("..." if len(t) > 150 else "")
        print(f"  [{i}] {preview}")

    print(f"\n==> Embedding via Mistral-embed dim 1024...")
    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key)
    embeddings = embed_texts_batched(client, texts, batch_size=32)

    arr = np.array(embeddings, dtype="float32")
    print(f"    Embedded {arr.shape[0]} vectors / dim {arr.shape[1]}")

    # Build FAISS index
    OUTPUT_INDEX.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_META.parent.mkdir(parents=True, exist_ok=True)

    index = build_index(arr)
    save_index(index, str(OUTPUT_INDEX))
    print(f"==> Index FAISS sauvé : {OUTPUT_INDEX} ({index.ntotal} vectors)")

    OUTPUT_META.write_text(
        json.dumps({"records": metas, "n": len(metas)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"==> Meta sauvé : {OUTPUT_META} ({len(metas)} records)")

    # Stats sanity
    decisions = {}
    categories = {}
    for m in metas:
        decisions[m["decision"]] = decisions.get(m["decision"], 0) + 1
        categories[m["category"]] = categories.get(m["category"], 0) + 1
    print(f"\n--- Stats ---")
    print(f"    decisions : {decisions}")
    print(f"    categories : {categories}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
