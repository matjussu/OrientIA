"""Smoke test des 5 scaffolds France Travail post-activation scopes.

Objectif : confirmer qu'en plus du token OAuth2 (déjà vérifié), chaque
module arrive à appeler au moins 1 endpoint réel sans 403/404.

Pas une ingestion complète — juste 1 appel par module avec un paramètre
minimaliste (ex : code ROME M1805 = Ingénieur informatique).

Sortie : rapport console + `data/raw/ft_smoke_<date>.json` avec les
réponses brutes pour référence debug.

Usage :
    python scripts/smoke_ft_live.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date as _date
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

load_dotenv()

from src.collect.ft_acces_emploi import AccesEmploiClient  # noqa: E402
from src.collect.ft_base import (  # noqa: E402
    FranceTravailError,
    FranceTravailScopeInvalid,
)
from src.collect.ft_marche_travail import MarcheTravailClient  # noqa: E402
from src.collect.ft_offres_emploi import OffresEmploiClient  # noqa: E402
from src.collect.ft_sortants_formation import SortantsFormationClient  # noqa: E402
from src.collect.romeo import RomeoClient  # noqa: E402


SMOKE_CODE_ROME = "M1805"  # Ingénieur informatique (recherches denses → trafic test OK)
SMOKE_DEPARTEMENT = "75"    # Paris

OUT_DIR = Path("data/raw")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def smoke_marche_travail(results: dict) -> None:
    """Test : tensions marché pour M1805."""
    name = "marche-travail"
    try:
        client = MarcheTravailClient()
        payload = client.get_tensions(code_rome=SMOKE_CODE_ROME)
        results[name] = {"status": "ok", "preview": _preview(payload)}
        print(f"  ✅ {name}: {_preview(payload)}")
    except FranceTravailScopeInvalid as e:
        results[name] = {"status": "scope_invalid", "error": str(e)[:200]}
        print(f"  ⚠️  {name}: scope non-activé ({e!s:.100})")
    except FranceTravailError as e:
        results[name] = {"status": "api_error", "error": str(e)[:200]}
        print(f"  ❌ {name}: {e!s:.200}")
    except Exception as e:  # noqa: BLE001
        results[name] = {"status": "unexpected", "error": f"{type(e).__name__}: {e}"}
        print(f"  ❌ {name}: unexpected {type(e).__name__}: {e!s:.150}")


def smoke_offres_emploi(results: dict) -> None:
    """Test : 1 page offres d'emploi M1805 (range 0-2, 3 offres)."""
    name = "offres-emploi"
    try:
        client = OffresEmploiClient()
        payload = client.search(
            code_rome=SMOKE_CODE_ROME, range_start=0, range_end=2
        )
        results[name] = {"status": "ok", "preview": _preview(payload)}
        print(f"  ✅ {name}: {_preview(payload)}")
    except FranceTravailScopeInvalid as e:
        results[name] = {"status": "scope_invalid", "error": str(e)[:200]}
        print(f"  ⚠️  {name}: scope non-activé ({e!s:.100})")
    except FranceTravailError as e:
        results[name] = {"status": "api_error", "error": str(e)[:200]}
        print(f"  ❌ {name}: {e!s:.200}")
    except Exception as e:  # noqa: BLE001
        results[name] = {"status": "unexpected", "error": f"{type(e).__name__}: {e}"}
        print(f"  ❌ {name}: unexpected {type(e).__name__}: {e!s:.150}")


def smoke_sortants_formation(results: dict) -> None:
    """Test : insertion post-formation pour un code formation type."""
    name = "sortants-formation"
    try:
        client = SortantsFormationClient()
        payload = client.get_insertion_post_formation(code_rome=SMOKE_CODE_ROME)
        results[name] = {"status": "ok", "preview": _preview(payload)}
        print(f"  ✅ {name}: {_preview(payload)}")
    except FranceTravailScopeInvalid as e:
        results[name] = {"status": "scope_invalid", "error": str(e)[:200]}
        print(f"  ⚠️  {name}: scope non-activé ({e!s:.100})")
    except FranceTravailError as e:
        results[name] = {"status": "api_error", "error": str(e)[:200]}
        print(f"  ❌ {name}: {e!s:.200}")
    except Exception as e:  # noqa: BLE001
        results[name] = {"status": "unexpected", "error": f"{type(e).__name__}: {e}"}
        print(f"  ❌ {name}: unexpected {type(e).__name__}: {e!s:.150}")


def smoke_acces_emploi(results: dict) -> None:
    """Test : taux retour emploi pour M1805."""
    name = "acces-emploi"
    try:
        client = AccesEmploiClient()
        payload = client.get_taux_acces(code_rome=SMOKE_CODE_ROME)
        results[name] = {"status": "ok", "preview": _preview(payload)}
        print(f"  ✅ {name}: {_preview(payload)}")
    except FranceTravailScopeInvalid as e:
        results[name] = {"status": "scope_invalid", "error": str(e)[:200]}
        print(f"  ⚠️  {name}: scope non-activé ({e!s:.100})")
    except FranceTravailError as e:
        results[name] = {"status": "api_error", "error": str(e)[:200]}
        print(f"  ❌ {name}: {e!s:.200}")
    except Exception as e:  # noqa: BLE001
        results[name] = {"status": "unexpected", "error": f"{type(e).__name__}: {e}"}
        print(f"  ❌ {name}: unexpected {type(e).__name__}: {e!s:.150}")


def smoke_romeo(results: dict) -> None:
    """Test : prédiction métiers depuis un texte libre."""
    name = "romeo"
    try:
        client = RomeoClient()
        payload = client.predict_rome_from_text(
            text="développeur python full stack",
        )
        results[name] = {"status": "ok", "preview": _preview(payload)}
        print(f"  ✅ {name}: {_preview(payload)}")
    except FranceTravailScopeInvalid as e:
        results[name] = {"status": "scope_invalid", "error": str(e)[:200]}
        print(f"  ⚠️  {name}: scope non-activé ({e!s:.100})")
    except FranceTravailError as e:
        results[name] = {"status": "api_error", "error": str(e)[:200]}
        print(f"  ❌ {name}: {e!s:.200}")
    except Exception as e:  # noqa: BLE001
        results[name] = {"status": "unexpected", "error": f"{type(e).__name__}: {e}"}
        print(f"  ❌ {name}: unexpected {type(e).__name__}: {e!s:.150}")


def _preview(payload: Any) -> str:
    """Résumé court d'une réponse pour le log."""
    if isinstance(payload, list):
        return f"list[{len(payload)}] sample={str(payload[0])[:120] if payload else '(empty)'}"
    if isinstance(payload, dict):
        keys = list(payload.keys())[:6]
        return f"dict keys={keys} n_keys_total={len(payload)}"
    return f"{type(payload).__name__}: {str(payload)[:100]}"


def main() -> int:
    print("Smoke test 5 modules FT France Travail — endpoints live")
    print("(code_rome de test : M1805 Ingénieur informatique)")
    print()

    cid = os.environ.get("FT_CLIENT_ID", "").strip()
    csec = os.environ.get("FT_CLIENT_SECRET", "").strip()
    if not cid or not csec:
        print("❌ FT_CLIENT_ID / FT_CLIENT_SECRET absents — abort")
        return 1

    results: dict[str, Any] = {}
    smoke_marche_travail(results)
    smoke_offres_emploi(results)
    smoke_sortants_formation(results)
    smoke_acces_emploi(results)
    smoke_romeo(results)

    out_path = OUT_DIR / f"ft_smoke_{_date.today().isoformat()}.json"
    out_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print()
    print(f"Rapport détaillé → {out_path}")

    # Summary
    oks = [k for k, v in results.items() if v.get("status") == "ok"]
    scope_issues = [k for k, v in results.items() if v.get("status") == "scope_invalid"]
    api_errors = [k for k, v in results.items() if v.get("status") in ("api_error", "unexpected")]

    print()
    print(f"✅ OK           : {len(oks)}/5 ({', '.join(oks) or '—'})")
    print(f"⚠️  scope_invalid : {len(scope_issues)}/5 ({', '.join(scope_issues) or '—'})")
    print(f"❌ api/unexpected : {len(api_errors)}/5 ({', '.join(api_errors) or '—'})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
