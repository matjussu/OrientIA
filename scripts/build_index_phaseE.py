"""Append-rebuild FAISS index Phase E — Sprint 6 corpora gaps.

Étend Phase D (54 297 vecteurs : 49 295 phaseB + 111 DARES anciennes
+ 4 891 blocs RNCP) avec les **5 axes Sprint 6** :
- DARES re-agg `granularity:fap_region` (PR #81) — 1 049 nouvelles cells
- inserjeunes lycée pro (PR #82) — 689 cells
- financement curated (PR #83) — 28 cells
- DROM-COM territorial (PR #84) — 6 cells
- voie pré-bac BAC PRO + CAP (PR #85) — 20 cells

Total : 1 792 nouveaux embeds Mistral.

## Stratégie reuse $0 sur 54 297 anciens

- Reuse via `faiss.reconstruct_n` sur phaseD.index ($0)
- Embed via Mistral mistral-embed seulement les 1 792 nouvelles cells
  (~$0.10 estimation à $0.10/M tokens, ~700 chars/cell × 1 792 ~ 200k tokens)
- Concat → nouvel IndexFlatL2 56 089 vecteurs

## Note importante : alignement DARES corpus actuel vs phaseD

phaseD a été construit avec `dares_corpus.json` ANCIEN (111 cells : 98 fap +
13 region). Depuis la PR #81 mergée, `dares_corpus.json` sur main contient
1 160 cells (les 111 anciennes + 1 049 fap_region nouvelles). Donc :
- Les fiches phaseD (54 297) restent valides comme base
- Les 1 049 cells DARES `granularity:fap_region` sont à filtrer depuis
  `dares_corpus.json` actuel et à embed comme nouvelles

Sortie :
- `data/processed/formations_multi_corpus_phaseE.json`
- `data/embeddings/formations_multi_corpus_phaseE.index`
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

# Sources existantes (Phase D = phaseB + DARES anciennes + blocs)
SRC_FICHES_PHASED = Path("data/processed/formations_multi_corpus_phaseD.json")
SRC_INDEX_PHASED = Path("data/embeddings/formations_multi_corpus_phaseD.index")

# Corpus Sprint 6 — sources pour les nouvelles cells à embed
DARES_CORPUS = Path("data/processed/dares_corpus.json")  # 1 160 cells, on prend granularity:fap_region (1 049)
INSERJEUNES_CORPUS = Path("data/processed/inserjeunes_lycee_pro_corpus.json")  # 689 cells
FINANCEMENT_CORPUS = Path("data/processed/financement_corpus.json")  # 28 cells
DOMTOM_CORPUS = Path("data/processed/domtom_corpus.json")  # 6 cells
VOIE_PRE_BAC_CORPUS = Path("data/processed/voie_pre_bac_corpus.json")  # 20 cells

# Outputs Phase E
TARGET_FICHES = Path("data/processed/formations_multi_corpus_phaseE.json")
TARGET_INDEX = Path("data/embeddings/formations_multi_corpus_phaseE.index")


def _load_new_records() -> tuple[list[dict], dict[str, int]]:
    """Charge les nouvelles cells Sprint 6 à embed.

    Returns:
        (records list, counts par axe pour traçabilité)
    """
    counts: dict[str, int] = {}
    new_records: list[dict] = []

    # 1. DARES granularity:fap_region (nouvelles, 1 049 cells)
    if DARES_CORPUS.exists():
        all_dares = json.loads(DARES_CORPUS.read_text(encoding="utf-8"))
        fap_region = [r for r in all_dares if r.get("granularity") == "fap_region" and r.get("text")]
        new_records.extend(fap_region)
        counts["dares_fap_region"] = len(fap_region)
        print(f"   DARES fap_region : {len(fap_region)} cells")

    # 2. Inserjeunes (toutes, 689 cells)
    if INSERJEUNES_CORPUS.exists():
        ins = [r for r in json.loads(INSERJEUNES_CORPUS.read_text(encoding="utf-8")) if r.get("text")]
        new_records.extend(ins)
        counts["inserjeunes"] = len(ins)
        print(f"   Inserjeunes : {len(ins)} cells")

    # 3. Financement (toutes, 28 cells)
    if FINANCEMENT_CORPUS.exists():
        fin = [r for r in json.loads(FINANCEMENT_CORPUS.read_text(encoding="utf-8")) if r.get("text")]
        new_records.extend(fin)
        counts["financement"] = len(fin)
        print(f"   Financement : {len(fin)} cells")

    # 4. DROM territorial (toutes, 6 cells)
    if DOMTOM_CORPUS.exists():
        dom = [r for r in json.loads(DOMTOM_CORPUS.read_text(encoding="utf-8")) if r.get("text")]
        new_records.extend(dom)
        counts["domtom"] = len(dom)
        print(f"   DOMTOM territorial : {len(dom)} cells")

    # 5. Voie pré-bac (toutes, 20 cells)
    if VOIE_PRE_BAC_CORPUS.exists():
        vpb = [r for r in json.loads(VOIE_PRE_BAC_CORPUS.read_text(encoding="utf-8")) if r.get("text")]
        new_records.extend(vpb)
        counts["voie_pre_bac"] = len(vpb)
        print(f"   Voie pré-bac : {len(vpb)} cells")

    return new_records, counts


def main() -> int:
    print("=" * 60)
    print("Append-rebuild Phase E — Sprint 6 (5 axes corpora)")
    print("=" * 60)

    # Verify sources
    if not all((SRC_FICHES_PHASED.exists(), SRC_INDEX_PHASED.exists())):
        print("❌ Sources Phase D absentes :")
        for p in (SRC_FICHES_PHASED, SRC_INDEX_PHASED):
            if not p.exists():
                print(f"  - {p}")
        return 1

    print("\n1. Loading source Phase D...")
    fiches_d = json.loads(SRC_FICHES_PHASED.read_text(encoding="utf-8"))
    index_d = faiss.read_index(str(SRC_INDEX_PHASED))
    print(f"   {len(fiches_d):,} fiches, index ntotal={index_d.ntotal:,}, d={index_d.d}")
    if len(fiches_d) != index_d.ntotal:
        print("   ⚠️  Désalignement Phase D : abort")
        return 1

    print("\n2. Loading nouveaux corpora Sprint 6...")
    new_records, counts = _load_new_records()
    print(f"   total nouveaux records : {len(new_records)}")
    print(f"   décomposition : {counts}")
    if not new_records:
        print("   ⚠️  Aucun nouveau record — abort")
        return 1

    print("\n3. Embedding via Mistral mistral-embed...")
    cfg = load_config()
    from mistralai.client import Mistral
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=180000)
    texts = [r["text"] for r in new_records]
    t0 = time.time()
    vectors = embed_texts_batched(client, texts, batch_size=64)
    new_arr = np.array(vectors, dtype="float32")
    print(f"   embedded shape: {new_arr.shape} in {time.time()-t0:.1f}s")

    print("\n4. Reconstructing Phase D vectors via faiss.reconstruct_n...")
    t0 = time.time()
    src_arr = index_d.reconstruct_n(0, index_d.ntotal)
    print(f"   reconstructed {src_arr.shape} in {time.time()-t0:.1f}s")

    print("\n5. Building combined IndexFlatL2...")
    combined_index = faiss.IndexFlatL2(index_d.d)
    combined_index.add(src_arr)
    combined_index.add(new_arr)
    print(f"   combined ntotal={combined_index.ntotal:,}")

    print("\n6. Building combined fiches list...")
    combined_fiches = list(fiches_d) + new_records
    print(f"   combined len={len(combined_fiches):,}")
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

    print(f"\n✅ Phase E index built (Sprint 6 5 axes appended).")
    print(f"   Phase D base    : 54 297 vecteurs")
    print(f"   Sprint 6 axes   : {sum(counts.values())} nouvelles cells embed")
    print(f"     - DARES fap_region : {counts.get('dares_fap_region', 0)}")
    print(f"     - inserjeunes      : {counts.get('inserjeunes', 0)}")
    print(f"     - financement      : {counts.get('financement', 0)}")
    print(f"     - DROM territorial : {counts.get('domtom', 0)}")
    print(f"     - voie pré-bac     : {counts.get('voie_pre_bac', 0)}")
    print(f"   Phase E total   : {combined_index.ntotal:,} vecteurs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
