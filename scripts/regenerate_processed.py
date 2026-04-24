"""Regenerate all processed data files from scratch (ADR-046).

Pipeline idempotent qui ré-ingère les sources externes et reconstruit
tous les fichiers `data/processed/*.json` consommés par le RAG et les
enrichissements. Peut être run en CI (GitHub Actions) ou localement
après un `git clone`.

**Ordre d'exécution critique** (dépendances) :

1. Sources externes (API) — indépendantes entre elles :
   - MonMaster → `monmaster_formations.json`
   - InserSup → `insersup_insertion.json`
   - Inserjeunes → `inserjeunes_lycee_pro.json` + `inserjeunes_cfa.json`
   - IP Doc → `ip_doc_doctorat.json`

2. Sources locales (xlsx déjà commités par Matteo) :
   - Céreq → `cereq_insertion_stats.json`
   - INSEE (si présent) → `insee_salaires_pcs_age.json` + taux_emploi
   - DARES (si présent) → `dares_metiers_2030.json`

3. Merger v2 (consomme tout ce qui précède) :
   - `formations.json` = aggregation de toutes les sources

**Gestion des erreurs** :

- Si une source externe échoue (API down) : log warning, continue avec
  les autres. Le merger v2 accepte les sources absentes (no-op).
- Si une source locale manque (xlsx pas uploadé) : skip silencieux.
- Exit code 0 = succès total ; 1 = au moins une source critique absente.

Usage :
    python scripts/regenerate_processed.py
    python scripts/regenerate_processed.py --skip-external  # Utiliser les JSON déjà présents
    python scripts/regenerate_processed.py --only monmaster,insersup
"""
from __future__ import annotations

import argparse
import sys
import time
import traceback
from pathlib import Path
from typing import Callable


REPO_ROOT = Path(__file__).resolve().parent.parent
# Permettre import `src.*` quand exécuté comme `python scripts/...`
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _run_step(name: str, fn: Callable[[], None], critical: bool = False) -> bool:
    """Exécute une étape avec gestion d'erreur. Retourne True si succès."""
    print(f"\n▶ [{name}] démarrage…")
    t0 = time.time()
    try:
        fn()
        print(f"✅ [{name}] OK ({time.time()-t0:.1f}s)")
        return True
    except Exception as e:  # noqa: BLE001
        marker = "❌" if critical else "⚠️ "
        print(f"{marker} [{name}] {'CRITIQUE ' if critical else ''}ÉCHEC : {e}")
        traceback.print_exc(limit=3)
        return False


def step_monmaster() -> None:
    from src.collect.monmaster import collect_monmaster_fiches
    collect_monmaster_fiches()


def step_insersup() -> None:
    from src.collect.insersup_api import collect_insersup_insertion
    collect_insersup_insertion()


def step_inserjeunes() -> None:
    from src.collect.inserjeunes import collect_inserjeunes
    collect_inserjeunes()


def step_ip_doc() -> None:
    from src.collect.ip_doc_doctorat import collect_ip_doc_doctorat
    collect_ip_doc_doctorat()


def step_cereq() -> None:
    from src.collect.cereq import collect_cereq_stats
    collect_cereq_stats()


def step_insee() -> None:
    from src.collect.insee import collect_insee_stats, InseeDataMissing
    try:
        collect_insee_stats()
    except InseeDataMissing as e:
        print(f"  [insee] skip — {e!s:.150}")


def step_dares() -> None:
    from src.collect.dares_metiers_2030 import (
        collect_dares_metiers_2030, DaresDataMissing,
    )
    try:
        collect_dares_metiers_2030()
    except DaresDataMissing as e:
        print(f"  [dares] skip — {e!s:.150}")


def step_merge_v2() -> None:
    """Reconstruit formations.json via merge_all_extended."""
    from src.collect.run_merge_v2 import main
    main()


STEPS: dict[str, tuple[Callable[[], None], bool]] = {
    # name → (fn, critical)
    "monmaster": (step_monmaster, True),
    "insersup": (step_insersup, False),
    "inserjeunes": (step_inserjeunes, False),
    "ip_doc": (step_ip_doc, False),
    "cereq": (step_cereq, True),
    "insee": (step_insee, False),
    "dares": (step_dares, False),
    "merge_v2": (step_merge_v2, True),
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenerate all processed data (ADR-046)")
    parser.add_argument(
        "--only",
        type=str,
        default=None,
        help="CSV des étapes à exécuter (ex: monmaster,insersup). Défaut = tout.",
    )
    parser.add_argument(
        "--skip-external",
        action="store_true",
        help="Skip les fetchs API (monmaster/insersup/inserjeunes/ip_doc), "
             "utiliser les JSON déjà présents. Utile pour re-run merge v2 seul.",
    )
    args = parser.parse_args()

    steps_to_run = set(args.only.split(",")) if args.only else set(STEPS)
    if args.skip_external:
        steps_to_run -= {"monmaster", "insersup", "inserjeunes", "ip_doc"}

    print("=" * 60)
    print("Regenerate processed data (ADR-046)")
    print(f"Steps : {sorted(steps_to_run)}")
    print("=" * 60)

    failures_critical = []
    failures_non_critical = []

    # Exécution en ordre strict (étape final = merge_v2)
    ordered = [
        "monmaster", "insersup", "inserjeunes", "ip_doc",
        "cereq", "insee", "dares",
        "merge_v2",
    ]
    for name in ordered:
        if name not in steps_to_run or name not in STEPS:
            continue
        fn, critical = STEPS[name]
        ok = _run_step(name, fn, critical=critical)
        if not ok:
            (failures_critical if critical else failures_non_critical).append(name)

    print("\n" + "=" * 60)
    print("Récapitulatif")
    print("=" * 60)
    if failures_critical:
        print(f"❌ Critiques échoués : {failures_critical}")
    if failures_non_critical:
        print(f"⚠️  Non-critiques échoués : {failures_non_critical}")
    if not failures_critical and not failures_non_critical:
        print("✅ Tous les steps OK.")

    return 1 if failures_critical else 0


if __name__ == "__main__":
    raise SystemExit(main())
