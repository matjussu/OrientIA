"""Déduplique le `formations.json` existant sans re-runner le merger v2 entier.

Standalone script qui applique `dedup_parcoursup_by_cod_aff_form` sur
le fichier produit `data/processed/formations.json`. Utile pour appliquer
ADR-050 sans avoir à re-fetch tous les sources externes (MonMaster API,
RNCP, etc.) qui peuvent être indisponibles ou lentes.

Sortie :
- `data/processed/formations_dedupe.json` (résultat dédupé)
- Backup : `data/processed/formations.json.pre_dedup` (lien vers original)

Le merger v2 patché dans `src/collect/merge.py` produira directement le
résultat dédupé pour les futures regen complètes (cf ADR-050).
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.collect.merge import dedup_parcoursup_by_cod_aff_form  # noqa: E402

SOURCE = Path("data/processed/formations.json")
BACKUP = Path("data/processed/formations.json.pre_dedup")
TARGET = Path("data/processed/formations_dedupe.json")


def main() -> int:
    if not SOURCE.exists():
        print(f"❌ {SOURCE} absent")
        return 1

    print(f"Loading {SOURCE}…")
    fiches = json.loads(SOURCE.read_text(encoding="utf-8"))
    print(f"  {len(fiches):,} fiches in")

    print(f"Backing up to {BACKUP}…")
    if not BACKUP.exists():
        shutil.copy2(SOURCE, BACKUP)
    print("  backup OK")

    print("Running dedup_parcoursup_by_cod_aff_form…")
    deduped = dedup_parcoursup_by_cod_aff_form(fiches)
    print(f"  {len(deduped):,} fiches out (dropped {len(fiches) - len(deduped):,})")

    print(f"Saving {TARGET}…")
    TARGET.write_text(
        json.dumps(deduped, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  saved ({TARGET.stat().st_size / 1024**2:.1f} MB)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
