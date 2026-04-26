"""Append-rebuild FAISS index Phase C (variante) — France Comp blocs RNCP.

Charge l'index Phase B (49 295 vecteurs : 47 590 formations + 1 705
multi-corpus) et append les ~4 891 cells France Compétences blocs RNCP
(1 cell par fiche RNCP active avec blocs) après embedding Mistral.

Stratégie reuse (consistante avec PR #67 Phase B / PR #70 Phase C DARES) :
- Reuse via `faiss.reconstruct_n` les 49 295 vecteurs existants ($0)
- Embed via Mistral mistral-embed les ~4 891 cells nouveaux (~$0.13)
- Concat → nouvel IndexFlatL2 ~54 186 vecteurs

Coût total : ~$0.13.

Pourquoi pas de dépendance sur Phase C DARES ?
- Isolation scientifique : chaque PR mesure UNE variable. PR #71 isole
  l'apport blocs RNCP vs phaseB baseline (PR #70 isole DARES). Une
  combinaison phaseD = phaseB + DARES + blocs sera mesurable post-merge.

Sortie :
- `data/processed/formations_multi_corpus_phaseC_blocs.json`
- `data/embeddings/formations_multi_corpus_phaseC_blocs.index`
"""
from __future__ import annotations

import json
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

# Sources existantes (Phase B aggregé 3-corpora)
SRC_FICHES = Path("data/processed/formations_multi_corpus_phaseB.json")
SRC_INDEX = Path("data/embeddings/formations_multi_corpus_phaseB.index")

# Nouveau corpus aggrégé France Comp blocs (PR #71)
PHASEC_CORPORA = [
    Path("data/processed/france_comp_blocs_corpus.json"),
]

# Outputs
TARGET_FICHES = Path("data/processed/formations_multi_corpus_phaseC_blocs.json")
TARGET_INDEX = Path("data/embeddings/formations_multi_corpus_phaseC_blocs.index")


def main() -> int:
    print("=" * 60)
    print("Append-rebuild Phase C (France Comp blocs RNCP) reuse $0+$0.13")
    print("=" * 60)

    if not all((SRC_FICHES.exists(), SRC_INDEX.exists())):
        print(f"❌ Sources Phase B absentes :")
        for p in (SRC_FICHES, SRC_INDEX):
            if not p.exists():
                print(f"  - {p}")
        return 1

    print(f"\n1. Loading source Phase B…")
    fiches_b = json.loads(SRC_FICHES.read_text(encoding="utf-8"))
    index_b = faiss.read_index(str(SRC_INDEX))
    print(f"   {len(fiches_b):,} fiches, index ntotal={index_b.ntotal:,}, d={index_b.d}")
    if len(fiches_b) != index_b.ntotal:
        print(f"   ⚠️  Désalignement source : abort")
        return 1

    print(f"\n2. Loading corpus France Comp blocs…")
    new_records: list[dict] = []
    for path in PHASEC_CORPORA:
        if not path.exists():
            print(f"   ⚠️  {path} absent — skip")
            continue
        records = json.loads(path.read_text(encoding="utf-8"))
        n = len([r for r in records if r.get("text")])
        new_records.extend([r for r in records if r.get("text")])
        print(f"   {path.name} : {n} cells avec text")
    print(f"   total nouveaux records : {len(new_records)}")
    if not new_records:
        print(f"   ⚠️  Aucun nouveau record — abort. "
              f"Run d'abord : python -m src.collect.build_france_comp_blocs_corpus")
        return 1

    print(f"\n3. Embedding via Mistral mistral-embed (batch 64)…")
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
    src_arr = index_b.reconstruct_n(0, index_b.ntotal)
    print(f"   reconstructed {src_arr.shape} in {time.time()-t0:.1f}s")

    print(f"\n5. Building combined IndexFlatL2…")
    combined_index = faiss.IndexFlatL2(index_b.d)
    combined_index.add(src_arr)
    combined_index.add(new_arr)
    print(f"   combined ntotal={combined_index.ntotal:,}")

    print(f"\n6. Building combined fiches list…")
    combined_fiches = list(fiches_b) + new_records
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

    print("\n✅ Phase C blocs index built (France Comp blocs RNCP appended).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
