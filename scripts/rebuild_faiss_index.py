"""Rebuild the FAISS index using the current fiche_to_text.

Usage:
  # Default — rebuild data/embeddings/formations.index from formations.json
  python -m scripts.rebuild_faiss_index

  # Override paths via env vars (Phase C.2 corpus v5 et au-delà)
  ORIENTIA_CORPUS_PATH=data/processed/formations_v5.json \\
  ORIENTIA_INDEX_PATH=data/embeddings/formations_v5.index \\
  python -m scripts.rebuild_faiss_index

Cost: mistral-embed at ~$0.10/1M tokens.
- v3.2 (~48k fiches × ~250 tokens) ≈ 12M tokens ≈ $1.20
- v5 (~47k fiches × ~500 tokens, plus dense) ≈ 23M tokens ≈ $2.30
"""
import json
import os
from pathlib import Path
from mistralai.client import Mistral
from src.config import load_config
from src.rag.pipeline import OrientIAPipeline


# Override via env vars pour rebuild parallèle (e.g. v5 sans toucher v3.2 prod)
FICHES_PATH = os.environ.get("ORIENTIA_CORPUS_PATH", "data/processed/formations.json")
INDEX_PATH = os.environ.get("ORIENTIA_INDEX_PATH", "data/embeddings/formations.index")


def main() -> None:
    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=120000)
    fiches = json.loads(Path(FICHES_PATH).read_text(encoding="utf-8"))
    print(f"Source corpus : {FICHES_PATH} ({len(fiches)} fiches)")
    print(f"Target index  : {INDEX_PATH}")
    print("Rebuilding FAISS index with current fiche_to_text...")
    pipeline = OrientIAPipeline(client=client, fiches=fiches)
    pipeline.build_index()
    pipeline.save_index_to(INDEX_PATH)
    print(f"Index saved to {INDEX_PATH}")


if __name__ == "__main__":
    main()
