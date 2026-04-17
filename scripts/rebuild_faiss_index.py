"""Rebuild the FAISS index using the current fiche_to_text.

Usage:
  python -m scripts.rebuild_faiss_index

Writes the new index to data/embeddings/formations.index, overwriting
the existing file. (A backup should be made first via `cp formations.index
formations.index.pre_<tag>`.)

Cost: mistral-embed at ~$0.10/1M tokens.
- 443 fiches × ~250 tokens each (after Vague B.3) ≈ 110K tokens
- Estimated cost: ~$0.01
"""
import json
from pathlib import Path
from mistralai.client import Mistral
from src.config import load_config
from src.rag.pipeline import OrientIAPipeline


FICHES_PATH = "data/processed/formations.json"
INDEX_PATH = "data/embeddings/formations.index"


def main() -> None:
    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=120000)
    fiches = json.loads(Path(FICHES_PATH).read_text(encoding="utf-8"))
    print(f"Rebuilding FAISS index for {len(fiches)} fiches with current fiche_to_text...")
    pipeline = OrientIAPipeline(client=client, fiches=fiches)
    pipeline.build_index()
    pipeline.save_index_to(INDEX_PATH)
    print(f"Index saved to {INDEX_PATH}")


if __name__ == "__main__":
    main()
