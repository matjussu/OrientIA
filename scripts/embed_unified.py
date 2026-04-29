"""Reembed le corpus unifié 55k via Mistral-embed dim 1024 — Sprint 10 chantier B.

Charge `data/processed/formations_unified.json` (~55k entries normalized par
`scripts/normalize_frontmatter.py`), produit `data/embeddings/formations_unified.index`
(FAISS dim 1024) consommable par le pipeline OrientIA après repointage.

Coût Mistral-embed : ~55k vectors × ~500 tokens ≈ 27.5M tokens × $0.10/1M ≈ ~$3.
ETA wall-clock : ~10-15 min batched.

Usage :
  PYTHONPATH=. python3 scripts/embed_unified.py

Spec ordre Jarvis : 2026-04-29-1146-claudette-orientia-sprint10-finalisation-rag-complet
(chantier B-3).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
from mistralai.client import Mistral

from src.config import load_config
from src.rag.embeddings import embed_texts_batched, fiche_to_text
from src.rag.index import build_index, save_index

ROOT = Path(__file__).resolve().parents[1]
INPUT_UNIFIED = ROOT / "data" / "processed" / "formations_unified.json"
OUTPUT_INDEX = ROOT / "data" / "embeddings" / "formations_unified.index"


def main() -> int:
    if not INPUT_UNIFIED.exists():
        print(f"⚠️  Input absent : {INPUT_UNIFIED} — run normalize_frontmatter.py d'abord")
        return 1

    print(f"==> Loading unified corpus depuis {INPUT_UNIFIED}")
    with INPUT_UNIFIED.open() as f:
        unified = json.load(f)
    print(f"    {len(unified)} entries chargées")

    print(f"\n==> Building embed texts via fiche_to_text() (cohérent avec corpus existant)")
    texts = [fiche_to_text(rec) for rec in unified]
    n_empty = sum(1 for t in texts if not t.strip())
    print(f"    {len(texts)} textes prêts (dont {n_empty} vides — fallback géré côté FAISS)")

    print(f"\n==> Embedding via Mistral-embed dim 1024 (batched 64) — ETA ~10-15 min")
    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key)

    t_start = time.time()
    embeddings = embed_texts_batched(client, texts, batch_size=64)
    elapsed = time.time() - t_start
    print(f"    Done en {elapsed/60:.1f} min — {len(embeddings)} vectors")

    arr = np.array(embeddings, dtype="float32")
    if arr.shape[0] != len(unified):
        print(f"⚠️  Mismatch : {arr.shape[0]} embeddings vs {len(unified)} entries")
        return 1

    print(f"\n==> Building FAISS index (dim {arr.shape[1]})")
    index = build_index(arr)

    OUTPUT_INDEX.parent.mkdir(parents=True, exist_ok=True)
    save_index(index, str(OUTPUT_INDEX))
    size_mb = OUTPUT_INDEX.stat().st_size / (1024 * 1024)
    print(f"==> Index sauvé : {OUTPUT_INDEX}")
    print(f"    ntotal: {index.ntotal}, dim: {index.d}, size: {size_mb:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
