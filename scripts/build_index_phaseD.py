"""Build Phase D index — phaseB + DARES + blocs RNCP combiné.

Main actuel a les 2 corpus (DARES PR #70 + blocs PR #71) mergés mais
chaque index Phase C est séparé (phaseC_dares ou phaseC_blocs uniquement).
Phase D est l'index unifié qui contient les 2 ensemble — état cible
"main complet" pour bench persona complet baseline pré-agentique.

## Stratégie reuse $0

Aucun appel Mistral embed nécessaire :
- phaseB.index (49 295 vecteurs) — reuse via reconstruct_n
- phaseC_dares.index (49 406) — extraire les 111 derniers vecteurs (DARES cells)
- phaseC_blocs.index (54 186) — extraire les 4 891 derniers vecteurs (blocs cells)
- Concat → 49 295 + 111 + 4 891 = 54 297 vecteurs

Coût : $0 (les embeddings existent déjà sur disque, juste extraction +
combinaison).

## Sortie

- `data/processed/formations_multi_corpus_phaseD.json`
- `data/embeddings/formations_multi_corpus_phaseD.index`
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

# Sources
SRC_PHASEB_FICHES = Path("data/processed/formations_multi_corpus_phaseB.json")
SRC_PHASEB_INDEX = Path("data/embeddings/formations_multi_corpus_phaseB.index")
SRC_PHASEC_DARES_INDEX = Path("data/embeddings/formations_multi_corpus_phaseC_dares.index")
SRC_PHASEC_BLOCS_INDEX = Path("data/embeddings/formations_multi_corpus_phaseC_blocs.index")

# Corpus json (committés sur main)
SRC_DARES_CORPUS = Path("data/processed/dares_corpus.json")
SRC_BLOCS_CORPUS = Path("data/processed/france_comp_blocs_corpus.json")

# Outputs
TARGET_FICHES = Path("data/processed/formations_multi_corpus_phaseD.json")
TARGET_INDEX = Path("data/embeddings/formations_multi_corpus_phaseD.index")


def main() -> int:
    print("=" * 60)
    print("Build Phase D (phaseB + DARES + blocs RNCP) reuse $0")
    print("=" * 60)

    # Verify sources
    missing = [p for p in (SRC_PHASEB_FICHES, SRC_PHASEB_INDEX,
                            SRC_PHASEC_DARES_INDEX, SRC_PHASEC_BLOCS_INDEX,
                            SRC_DARES_CORPUS, SRC_BLOCS_CORPUS) if not p.exists()]
    if missing:
        print("❌ Sources absentes :")
        for p in missing:
            print(f"  - {p}")
        return 1

    print("\n1. Loading phaseB (base + multi-corpus phaseB)...")
    fiches_b = json.loads(SRC_PHASEB_FICHES.read_text(encoding="utf-8"))
    index_b = faiss.read_index(str(SRC_PHASEB_INDEX))
    print(f"   {len(fiches_b):,} fiches, index ntotal={index_b.ntotal:,}, d={index_b.d}")
    if len(fiches_b) != index_b.ntotal:
        print("   ⚠️  Désalignement phaseB : abort")
        return 1

    print("\n2. Reconstructing phaseB vectors...")
    t0 = time.time()
    src_b = index_b.reconstruct_n(0, index_b.ntotal)
    print(f"   {src_b.shape} in {time.time()-t0:.1f}s")

    print("\n3. Extracting DARES vectors from phaseC_dares.index...")
    index_pc_dares = faiss.read_index(str(SRC_PHASEC_DARES_INDEX))
    n_dares_expected = len(json.loads(SRC_DARES_CORPUS.read_text(encoding="utf-8")))
    if index_pc_dares.ntotal != index_b.ntotal + n_dares_expected:
        print(f"   ⚠️  phaseC_dares ntotal={index_pc_dares.ntotal} ≠ phaseB+{n_dares_expected}={index_b.ntotal+n_dares_expected}")
        return 1
    dares_arr = index_pc_dares.reconstruct_n(index_b.ntotal, n_dares_expected)
    print(f"   {dares_arr.shape} (DARES cells, last {n_dares_expected} of phaseC_dares)")

    print("\n4. Extracting blocs RNCP vectors from phaseC_blocs.index...")
    index_pc_blocs = faiss.read_index(str(SRC_PHASEC_BLOCS_INDEX))
    n_blocs_expected = len(json.loads(SRC_BLOCS_CORPUS.read_text(encoding="utf-8")))
    if index_pc_blocs.ntotal != index_b.ntotal + n_blocs_expected:
        print(f"   ⚠️  phaseC_blocs ntotal={index_pc_blocs.ntotal} ≠ phaseB+{n_blocs_expected}={index_b.ntotal+n_blocs_expected}")
        return 1
    blocs_arr = index_pc_blocs.reconstruct_n(index_b.ntotal, n_blocs_expected)
    print(f"   {blocs_arr.shape} (blocs cells, last {n_blocs_expected} of phaseC_blocs)")

    print("\n5. Building combined Phase D IndexFlatL2...")
    combined_index = faiss.IndexFlatL2(index_b.d)
    combined_index.add(src_b)
    combined_index.add(dares_arr)
    combined_index.add(blocs_arr)
    print(f"   combined ntotal={combined_index.ntotal:,}")

    print("\n6. Building combined fiches list...")
    dares_records = json.loads(SRC_DARES_CORPUS.read_text(encoding="utf-8"))
    blocs_records = json.loads(SRC_BLOCS_CORPUS.read_text(encoding="utf-8"))
    combined_fiches = list(fiches_b) + dares_records + blocs_records
    print(f"   combined fiches len={len(combined_fiches):,}")
    if len(combined_fiches) != combined_index.ntotal:
        print("   ⚠️  Désalignement final : abort")
        return 1

    print("\n7. Saving outputs...")
    TARGET_FICHES.write_text(
        json.dumps(combined_fiches, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"   fiches → {TARGET_FICHES} ({TARGET_FICHES.stat().st_size / 1024**2:.1f} MB)")
    faiss.write_index(combined_index, str(TARGET_INDEX))
    print(f"   index → {TARGET_INDEX} ({TARGET_INDEX.stat().st_size / 1024**2:.1f} MB)")

    print("\n✅ Phase D index built (phaseB + DARES + blocs combiné).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
