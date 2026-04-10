import json
import sys
from pathlib import Path
from mistralai.client import Mistral
from src.config import load_config
from src.rag.pipeline import OrientIAPipeline


FICHES_PATH = "data/processed/formations.json"
INDEX_PATH = "data/embeddings/formations.index"


def main():
    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key)
    fiches = json.loads(Path(FICHES_PATH).read_text(encoding="utf-8"))

    pipeline = OrientIAPipeline(client, fiches)

    if Path(INDEX_PATH).exists():
        print(f"Loading cached index from {INDEX_PATH}...")
        pipeline.load_index_from(INDEX_PATH)
    else:
        print(f"Building index for {len(fiches)} fiches (this takes ~10s)...")
        pipeline.build_index()
        pipeline.save_index_to(INDEX_PATH)
        print(f"Index saved to {INDEX_PATH}")

    question = sys.argv[1] if len(sys.argv) > 1 else \
        "Quelles sont les meilleures formations en cybersécurité en France ?"
    print(f"\n{'=' * 70}")
    print(f"QUESTION: {question}")
    print('=' * 70)

    answer, sources = pipeline.answer(question)

    print(f"\n--- RÉPONSE ---\n{answer}")

    print(f"\n--- SOURCES TOP-{len(sources)} ---")
    for i, s in enumerate(sources, 1):
        f = s["fiche"]
        labels = ", ".join(f.get("labels") or []) or "(aucun)"
        etab = f.get("etablissement") or "(aucun)"
        niveau = f.get("niveau") or "?"
        print(f"  {i:2d}. [score={s['score']:.3f}] {niveau} | labels={labels}")
        print(f"      {f.get('nom', '')[:70]}")
        print(f"      @ {etab}")


if __name__ == "__main__":
    main()
