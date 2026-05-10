"""Step 11.7 — Re-applique `_is_retrieval_eligible` (politique v2 granulaire)
sur le corpus v7 sans relancer toute la pipeline d'ingestion.

Le flag `retrieval_eligible` est posé en Stage 5 du merge pipeline
(`run_merge_v3.py:674-676`) et est idempotent. Ce script court-circuite
les autres stages et recalcule UNIQUEMENT le flag.

Audit empirique 2026-05-09 (lecture du dump qualitatif step 11.5) a
révélé que la politique v1 blacklist excluait HEC, CentraleSupélec,
IMT Atlantique, INSA Rennes — toutes invisibles au retrieve. Politique
v2 : critère granulaire (etablissement OR nom OR ville OR region OR
domain populé) au lieu de blacklist source.

Usage :
    cd ~/projets/OrientIA && source .venv/bin/activate
    python scripts/refresh_retrieval_eligible_step11_7.py
    python scripts/refresh_retrieval_eligible_step11_7.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.collect.run_merge_v3 import _is_retrieval_eligible  # noqa: E402


DEFAULT_CORPUS = PROJECT_ROOT / "data" / "processed" / "formations_v7.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-path", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Affiche le delta sans écrire dans le JSON.",
    )
    parser.add_argument(
        "--no-backup", action="store_true",
        help="Skip backup .pre_step11_7 (utile en re-run).",
    )
    args = parser.parse_args()

    if not args.corpus_path.exists():
        print(f"ERREUR : corpus absent : {args.corpus_path}", file=sys.stderr)
        return 1

    print(f"=== Refresh retrieval_eligible (step 11.7) ===")
    print(f"Corpus : {args.corpus_path}")
    print(f"Mode   : {'DRY-RUN' if args.dry_run else 'WRITE'}")

    fiches = json.loads(args.corpus_path.read_text(encoding="utf-8"))
    print(f"Loaded {len(fiches)} fiches\n")

    # Compteurs delta par source
    by_source_before: Counter = Counter()
    by_source_after: Counter = Counter()
    by_source_total: Counter = Counter()
    n_changed_to_true = 0
    n_changed_to_false = 0

    for fiche in fiches:
        if not isinstance(fiche, dict):
            continue
        src = fiche.get("source") or "—"
        by_source_total[src] += 1
        old_flag = fiche.get("retrieval_eligible")
        new_flag = _is_retrieval_eligible(fiche)

        if old_flag is True:
            by_source_before[src] += 1
        if new_flag:
            by_source_after[src] += 1

        if old_flag is False and new_flag is True:
            n_changed_to_true += 1
        elif old_flag is True and new_flag is False:
            n_changed_to_false += 1

        if not args.dry_run:
            fiche["retrieval_eligible"] = new_flag

    # Audit
    print("=== Delta par source (eligible AVANT → APRÈS / total) ===")
    for src, total in sorted(by_source_total.items(), key=lambda kv: -kv[1]):
        before = by_source_before[src]
        after = by_source_after[src]
        delta = after - before
        sign = "+" if delta > 0 else ("=" if delta == 0 else "")
        print(f"  {src:30s} : {before:>5d} → {after:>5d} ({sign}{delta:>+5d}) / {total}")

    print(f"\n=== Récap global ===")
    total_before = sum(by_source_before.values())
    total_after = sum(by_source_after.values())
    print(f"Total éligibles AVANT : {total_before:>6d} / {len(fiches)}")
    print(f"Total éligibles APRÈS : {total_after:>6d} / {len(fiches)}")
    print(f"Δ éligibles           : {total_after - total_before:+d}")
    print(f"Fiches False → True   : {n_changed_to_true}")
    print(f"Fiches True → False   : {n_changed_to_false}")

    if args.dry_run:
        print("\nDRY-RUN — corpus non modifié.")
        return 0

    if n_changed_to_true == 0 and n_changed_to_false == 0:
        print("\nAucun changement détecté — corpus inchangé.")
        return 0

    # Backup avant écriture
    if not args.no_backup:
        backup_path = args.corpus_path.with_suffix(args.corpus_path.suffix + ".pre_step11_7")
        if not backup_path.exists():
            print(f"\n📦 Backup : {backup_path}")
            shutil.copy2(args.corpus_path, backup_path)

    # Écriture (preserve indent + ordre)
    print(f"\n💾 Écriture {args.corpus_path}...")
    t0 = time.time()
    args.corpus_path.write_text(
        json.dumps(fiches, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"   ✓ done en {time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
