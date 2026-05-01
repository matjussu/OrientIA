"""Sprint 12 axe 2 — embed le corpus combined Golden Pipeline.

Charge ``data/processed/formations_golden_pipeline.json`` (~61 657 entrées
combinant ``formations_unified`` + ``dares`` + ``rncp_blocs``, cf
``scripts/build_formations_golden_corpus.py``), embed chaque item via
``corpus_item_to_text()`` qui route selon le champ ``corpus``, produit
``data/embeddings/formations_golden_pipeline.index`` (FAISS dim 1024).

**NE PAS écraser** ``formations_unified.index`` : le golden pipeline est
opt-in via une nouvelle constante (``GOLDEN_INDEX_PATH``). L'index legacy
reste dispo pour le système ``our_rag_enriched`` (rollback safety net +
bench α-comparatif Sprint 12).

Coût Mistral-embed estimé : ~61 657 vecteurs.
- formations_unified (~800 chars/text) : 55 606 × 200 tokens ≈ 11.1M tokens
- dares (~300 chars/text) : 1 160 × 75 tokens ≈ 0.087M tokens
- rncp_blocs (~600 chars/text) : 4 891 × 150 tokens ≈ 0.73M tokens
Total ≈ 12M tokens × $0.10/1M ≈ ~$1.2 (vs ~$3 pour unified seul — corpora
Sprint 6 sont préformatés courts, marginal cost faible).

ETA wall-clock : ~10-15 min batched (batch_size=64).

Usage:
  PYTHONPATH=. python3 scripts/embed_golden_pipeline.py [--force]

Plan : ``docs/GOLDEN_PIPELINE_PLAN.md`` étape 2.
Spec ordre Jarvis : 2026-05-01-2031-claudette-orientia-sprint12-axe-2-golden-pipeline-fusion.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from mistralai.client import Mistral

from src.config import load_config
from src.rag.embeddings import corpus_item_to_text, embed_texts_batched
from src.rag.index import build_index, save_index

ROOT = Path(__file__).resolve().parents[1]
INPUT_GOLDEN = ROOT / "data" / "processed" / "formations_golden_pipeline.json"
OUTPUT_INDEX = ROOT / "data" / "embeddings" / "formations_golden_pipeline.index"
LEGACY_UNIFIED_INDEX = ROOT / "data" / "embeddings" / "formations_unified.index"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Override existing formations_golden_pipeline.index (disabled par défaut "
             "pour éviter les rebuilds API accidentels coûteux).",
    )
    args = parser.parse_args(argv)

    if not INPUT_GOLDEN.exists():
        print(f"⚠️  Input absent : {INPUT_GOLDEN}", flush=True)
        print(f"   Run d'abord : python scripts/build_formations_golden_corpus.py")
        return 1

    if OUTPUT_INDEX.exists() and not args.force:
        print(f"⚠️  Index existe déjà : {OUTPUT_INDEX}")
        print(f"   Skip rebuild (économie API). Pass --force pour override.")
        return 0

    # Garde-fou hard : NE JAMAIS écraser formations_unified.index (legacy).
    if OUTPUT_INDEX.resolve() == LEGACY_UNIFIED_INDEX.resolve():
        print(f"❌  STOP : OUTPUT_INDEX collisionne avec legacy {LEGACY_UNIFIED_INDEX}")
        return 1

    print(f"==> Loading golden corpus depuis {INPUT_GOLDEN}", flush=True)
    with INPUT_GOLDEN.open("r", encoding="utf-8") as f:
        golden = json.load(f)
    print(f"    {len(golden):,} entrées chargées")

    breakdown = {
        "formations_unified": sum(1 for it in golden if it.get("corpus") == "formations_unified"),
        "dares": sum(1 for it in golden if it.get("corpus") == "dares"),
        "rncp_blocs": sum(1 for it in golden if it.get("corpus") == "rncp_blocs"),
    }
    print(f"    Breakdown : {breakdown}")

    print(f"\n==> Building embed texts via corpus_item_to_text() — route par corpus")
    texts = [corpus_item_to_text(rec) for rec in golden]
    n_empty = sum(1 for t in texts if not t.strip())
    print(f"    {len(texts):,} textes prêts (dont {n_empty} vides)")

    print(f"\n==> Embedding via Mistral-embed dim 1024 (batched 64) — ETA ~10-15 min")
    cfg = load_config()
    if not cfg.mistral_api_key:
        print("❌  MISTRAL_API_KEY absent dans .env")
        return 1
    client = Mistral(api_key=cfg.mistral_api_key)

    t_start = time.time()
    embeddings = embed_texts_batched(client, texts, batch_size=64)
    elapsed = time.time() - t_start
    print(f"    Done en {elapsed/60:.1f} min — {len(embeddings):,} vecteurs")

    arr = np.array(embeddings, dtype="float32")
    if arr.shape[0] != len(golden):
        print(f"❌  Mismatch : {arr.shape[0]} embeddings vs {len(golden)} entries")
        return 1

    print(f"\n==> Building FAISS index (dim {arr.shape[1]})")
    index = build_index(arr)

    OUTPUT_INDEX.parent.mkdir(parents=True, exist_ok=True)
    save_index(index, str(OUTPUT_INDEX))
    size_mb = OUTPUT_INDEX.stat().st_size / (1024 * 1024)
    print(f"\n==> Index sauvé : {OUTPUT_INDEX}")
    print(f"    ntotal: {index.ntotal:,}, dim: {index.d}, size: {size_mb:.1f} MB")

    # Sanity check : legacy index intact
    if LEGACY_UNIFIED_INDEX.exists():
        legacy_size_mb = LEGACY_UNIFIED_INDEX.stat().st_size / (1024 * 1024)
        print(f"    Legacy {LEGACY_UNIFIED_INDEX.name} intact : {legacy_size_mb:.1f} MB ✅")

    return 0


if __name__ == "__main__":
    sys.exit(main())
