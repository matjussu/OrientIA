"""Append-rebuild FAISS index Phase B — 3 corpora aggrégés.

Charge l'index v5 dedupé (48 829 vecteurs) et append les 466 nouveaux
records aggrégés (CROUS + INSEE + InserSup) après embedding Mistral.

Stratégie reuse (consistante avec PR #64) :
- Reuse via `faiss.reconstruct_n` les 48 829 vecteurs existants ($0)
- Embed via Mistral mistral-embed les ~466 records nouveaux (~$0.05)
- Concat → nouvel IndexFlatL2 49 295 vecteurs

Coût total : ~$0.05.

Sortie :
- `data/processed/formations_multi_corpus_phaseB.json`
- `data/embeddings/formations_multi_corpus_phaseB.index`
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

import faiss
import numpy as np


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.config import load_config  # noqa: E402
from src.rag.embeddings import embed_texts_batched  # noqa: E402

# Sources existantes (Phase A dedupé)
SRC_FICHES = Path("data/processed/formations_multi_corpus_dedupe.json")
SRC_INDEX = Path("data/embeddings/formations_multi_corpus_dedupe.index")

# Nouveaux corpora aggrégés Phase B
PHASEB_CORPORA = [
    Path("data/processed/crous_corpus.json"),
    Path("data/processed/insee_salaan_corpus.json"),
    Path("data/processed/insersup_corpus.json"),
]

# Outputs
TARGET_FICHES = Path("data/processed/formations_multi_corpus_phaseB.json")
TARGET_INDEX = Path("data/embeddings/formations_multi_corpus_phaseB.index")


def main() -> int:
    print("=" * 60)
    print("Append-rebuild Phase B (CROUS + INSEE + InserSup) reuse $0")
    print("=" * 60)

    if not all((SRC_FICHES.exists(), SRC_INDEX.exists())):
        print(f"❌ Sources Phase A absentes :")
        for p in (SRC_FICHES, SRC_INDEX):
            if not p.exists():
                print(f"  - {p}")
        return 1

    print(f"\n1. Loading source dedupé v5…")
    fiches_a = json.loads(SRC_FICHES.read_text(encoding="utf-8"))
    index_a = faiss.read_index(str(SRC_INDEX))
    print(f"   {len(fiches_a):,} fiches, index ntotal={index_a.ntotal:,}, d={index_a.d}")
    if len(fiches_a) != index_a.ntotal:
        print(f"   ⚠️  Désalignement source : abort")
        return 1

    print(f"\n2. Loading 3 nouveaux corpora aggrégés Phase B…")
    new_records: list[dict] = []
    for path in PHASEB_CORPORA:
        if not path.exists():
            print(f"   ⚠️  {path} absent — skip")
            continue
        records = json.loads(path.read_text(encoding="utf-8"))
        n = len([r for r in records if r.get("text")])
        new_records.extend([r for r in records if r.get("text")])
        print(f"   {path.name} : {n} cells avec text")
    print(f"   total nouveaux records : {len(new_records)}")
    if not new_records:
        print(f"   ⚠️  Aucun nouveau record — abort")
        return 1

    print(f"\n3. Embedding via Mistral mistral-embed…")
    cfg = load_config()
    from mistralai.client import Mistral
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=180000)
    texts = [r["text"] for r in new_records]
    t0 = time.time()
    vectors = embed_texts_batched(client, texts, batch_size=64)
    new_arr = np.array(vectors, dtype="float32")
    print(f"   embedded shape: {new_arr.shape} in {time.time()-t0:.1f}s")

    print(f"\n4. Reconstructing source vectors via faiss.reconstruct_n…")
    t0 = time.time()
    src_arr = index_a.reconstruct_n(0, index_a.ntotal)
    print(f"   reconstructed {src_arr.shape} in {time.time()-t0:.1f}s")

    print(f"\n5. Building combined IndexFlatL2…")
    combined_index = faiss.IndexFlatL2(index_a.d)
    combined_index.add(src_arr)
    combined_index.add(new_arr)
    print(f"   combined ntotal={combined_index.ntotal:,}")

    print(f"\n6. Building combined fiches list…")
    combined_fiches = list(fiches_a) + new_records
    print(f"   combined len={len(combined_fiches):,}")
    if len(combined_fiches) != combined_index.ntotal:
        print(f"   ⚠️  Désalignement final : abort")
        return 1

    print(f"\n7. Saving outputs…")
    TARGET_FICHES.write_text(
        json.dumps(combined_fiches, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"   fiches → {TARGET_FICHES} ({TARGET_FICHES.stat().st_size / 1024**2:.1f} MB)")
    faiss.write_index(combined_index, str(TARGET_INDEX))
    print(f"   index → {TARGET_INDEX} ({TARGET_INDEX.stat().st_size / 1024**2:.1f} MB)")

    print("\n✅ Phase B index built.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
