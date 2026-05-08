#!/usr/bin/env python3
"""Phase 3 V2 — Étape 1 : split du corpus v5 en chunks pour rewrite Agent.

Découpe les 13 417 fiches annexes (``domain`` non-vide) de
``formations_v5.json`` en chunks de N fiches dans un répertoire de travail
+ produit un ``manifest.json`` qui sert de référence pour l'orchestration
des invocations Agent (cf ADR-060 addendum 2026-05-08).

Usage :
    # Split full 13 417 fiches en 269 chunks de 50
    python scripts/prepare_rewrite_chunks.py

    # Sample 5 fiches dans 1 chunk pour test pivot Agent
    python scripts/prepare_rewrite_chunks.py --sample 5 \\
        --chunks-dir /tmp/orientia_rewrite_test_5

    # Override paths
    python scripts/prepare_rewrite_chunks.py \\
        --input data/processed/formations_v5.json \\
        --chunks-dir /tmp/orientia_rewrite_chunks_v6 \\
        --chunk-size 50
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.rewrite.chunk_dispatcher import (  # noqa: E402
    DEFAULT_CHUNK_SIZE,
    chunk_distribution,
    split_into_chunks,
)

logger = logging.getLogger("prepare_rewrite_chunks")


def _stratified_sample(fiches: list[dict], n: int, seed: int = 42) -> list[dict]:
    """Échantillonne ``n`` fiches en couvrant tous les domains présents."""
    import random

    rng = random.Random(seed)
    by_domain: dict[str, list[dict]] = {}
    for f in fiches:
        by_domain.setdefault(f.get("domain", "?"), []).append(f)
    domains = sorted(by_domain.keys())
    out: list[dict] = []
    used: set[str] = set()
    # 1) au moins une fiche par domain
    for d in domains:
        cands = [f for f in by_domain[d] if f["id"] not in used]
        if cands and len(out) < n:
            picked = rng.choice(cands)
            out.append(picked)
            used.add(picked["id"])
    # 2) compléter aléatoirement
    pool = [f for f in fiches if f["id"] not in used]
    rng.shuffle(pool)
    while len(out) < n and pool:
        out.append(pool.pop())
    return out[:n]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Split corpus v5 annexes en chunks pour rewrite Agent (ADR-060)",
    )
    parser.add_argument(
        "--input",
        default="data/processed/formations_v5.json",
        help="Chemin du corpus v5 source",
    )
    parser.add_argument(
        "--chunks-dir",
        default="/tmp/orientia_rewrite_chunks_v6",
        help="Répertoire où écrire les chunks + manifest",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help=f"Nb de fiches par chunk (default {DEFAULT_CHUNK_SIZE})",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Si fourni, ne split qu'un sample stratifié de N fiches "
        "(pour test pivot)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Seed pour shuffle (assure répartition domains équilibrée)",
    )
    parser.add_argument(
        "--no-shuffle",
        action="store_true",
        help="Désactive le shuffle (préserve l'ordre du JSON v5)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    input_path = Path(args.input)
    chunks_dir = Path(args.chunks_dir)

    logger.info(f"Loading {input_path}")
    v5 = json.loads(input_path.read_text(encoding="utf-8"))
    logger.info(f"  → {len(v5)} fiches v5 totales")

    annex = [f for f in v5 if f.get("domain")]
    logger.info(f"  → {len(annex)} fiches annexes")

    if args.sample is not None:
        annex = _stratified_sample(annex, args.sample, seed=args.seed)
        logger.info(f"  → sample stratifié {len(annex)} fiches")

    seed = None if args.no_shuffle else args.seed
    manifest = split_into_chunks(
        annex,
        chunks_dir,
        chunk_size=args.chunk_size,
        seed=seed,
    )

    logger.info(f"Splitted into {manifest.n_chunks} chunks of ≤{args.chunk_size}")
    logger.info(f"Manifest : {chunks_dir / 'manifest.json'}")
    dist = chunk_distribution(manifest)
    logger.info("Distribution des fiches par domain :")
    for d, n in sorted(dist.items(), key=lambda x: -x[1]):
        logger.info(f"  {d:30s}: {n}")

    print()
    print(f"Chunks prêts dans : {chunks_dir}")
    print(f"Nombre de chunks : {manifest.n_chunks}")
    print(f"Pour orchestrer le rewriting via Agent, voir le handoff "
          f"docs/HANDOFF_REWRITE_ANNEX_TEXTS.md addendum 2026-05-08")
    return 0


if __name__ == "__main__":
    sys.exit(main())
