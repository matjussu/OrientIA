"""Step 11.7 chantier 3 — Re-embed corpus v7 avec fiche_to_text enrichi.

Re-génère les embeddings Mistral 1024-dim pour les 47 214 fiches de
data/processed/formations_v7.json en utilisant le `fiche_to_text` v4
(step 11.7 chantier 3) qui injecte :
- Signatures publiques des écoles prestigieuses (HEC, INSA, ENIB,
  ENSEIRB-MATMECA, IMT, CentraleSupélec, Polytech, Sciences Po...)
- Mots-clés métier détectés dans nom/detail/parcours_long/mention/specialite
  (cybersécurité, data, IA, robotique, réseaux, etc.)

Coût estimé : ~$3 (47 214 fiches × ~600 tokens × $0.10/1M = ~$2.83)
ETA wall-clock : ~10-15 min batched (batch_size=64)

Backup automatique de l'index actuel : formations.index.pre_step11_7

Usage :
    cd ~/projets/OrientIA && source .venv/bin/activate
    python scripts/reembed_v7_step11_7.py
    python scripts/reembed_v7_step11_7.py --dry-run  # affiche stats sans embed
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mistralai.client import Mistral

from src.config import load_config
from src.rag.embeddings import embed_texts_batched, fiche_to_text
from src.rag.index import build_index, save_index


DEFAULT_CORPUS = PROJECT_ROOT / "data" / "processed" / "formations_v7.json"
DEFAULT_INDEX = PROJECT_ROOT / "data" / "embeddings" / "formations.index"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-path", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--index-path", type=Path, default=DEFAULT_INDEX)
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Génère les textes (gratuit) sans re-embed.",
    )
    parser.add_argument(
        "--no-backup", action="store_true",
        help="Skip backup .pre_step11_7 (utile en re-run).",
    )
    args = parser.parse_args()

    if not args.corpus_path.exists():
        print(f"ERREUR : corpus absent : {args.corpus_path}", file=sys.stderr)
        return 1

    print(f"=== Re-embed step 11.7 chantier 3 ===")
    print(f"Corpus     : {args.corpus_path}")
    print(f"Index out  : {args.index_path}")
    print(f"Mode       : {'DRY-RUN (no API call)' if args.dry_run else 'EMBED ($3)'}\n")

    fiches = json.loads(args.corpus_path.read_text(encoding="utf-8"))
    print(f"Loaded {len(fiches)} fiches")

    # Génère les textes via fiche_to_text v4 (step 11.7)
    print("\nGénération textes via fiche_to_text v4 (step 11.7 chantier 3)...")
    t0 = time.time()
    texts = [fiche_to_text(f) for f in fiches]
    print(f"    Done en {time.time() - t0:.1f}s — {len(texts)} textes prêts")
    n_empty = sum(1 for t in texts if not t.strip())
    print(f"    Textes vides : {n_empty}")
    n_with_sig = sum(1 for t in texts if "Signature école" in t)
    n_with_metier = sum(1 for t in texts if "Mots-clés métier" in t)
    print(f"    Avec signature école : {n_with_sig} ({100*n_with_sig/len(texts):.1f}%)")
    print(f"    Avec mots-clés métier : {n_with_metier} ({100*n_with_metier/len(texts):.1f}%)")

    # Estimation coût (token approx ~750 caractères / texte)
    avg_chars = sum(len(t) for t in texts) / max(len(texts), 1)
    est_tokens = sum(len(t) for t in texts) / 4  # heuristique 1 token ≈ 4 chars
    est_cost = est_tokens * 0.10 / 1_000_000
    print(f"    Avg text size : {avg_chars:.0f} chars")
    print(f"    Estimated tokens : {est_tokens / 1_000_000:.2f}M")
    print(f"    Estimated cost : ${est_cost:.2f}")

    if args.dry_run:
        print("\nDRY-RUN — pas de re-embed.")
        return 0

    cfg = load_config()
    if not cfg.mistral_api_key:
        print("ERREUR : MISTRAL_API_KEY absent", file=sys.stderr)
        return 1
    client = Mistral(api_key=cfg.mistral_api_key)

    # Backup avant re-embed
    if not args.no_backup and args.index_path.exists():
        backup_path = args.index_path.with_suffix(args.index_path.suffix + ".pre_step11_7")
        if not backup_path.exists():
            print(f"\n📦 Backup index actuel → {backup_path}")
            shutil.copy2(args.index_path, backup_path)

    # Re-embed via Mistral (batched 64)
    print(f"\n=== Embedding via Mistral-embed (batched 64) — ETA ~10-15 min ===")
    t0 = time.time()
    embeddings = embed_texts_batched(client, texts, batch_size=64)
    elapsed = time.time() - t0
    print(f"    Done en {elapsed/60:.1f} min — {len(embeddings)} vectors")

    arr = np.array(embeddings, dtype="float32")
    if arr.shape[0] != len(fiches):
        print(f"⚠️  Mismatch : {arr.shape[0]} embeddings vs {len(fiches)} fiches", file=sys.stderr)
        return 1

    # Build FAISS + sauvegarde
    print(f"\n=== Build FAISS IndexFlatL2 (dim {arr.shape[1]}) ===")
    index = build_index(arr)
    args.index_path.parent.mkdir(parents=True, exist_ok=True)
    save_index(index, str(args.index_path))
    size_mb = args.index_path.stat().st_size / (1024 * 1024)
    print(f"    ✓ Index sauvé : {args.index_path}")
    print(f"    ntotal={index.ntotal}, dim={index.d}, size={size_mb:.1f} MB")

    print("\n✅ Re-embed terminé. Penser à re-build les sub-indexes :")
    print("   python scripts/build_quad_subindexes.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
