"""Ingestion Offres Emploi France Travail v2 (live, 2026-04-24).

Contexte : scope `api_offresdemploiv2 o2dsoffre` confirmé actif post
upload Matteo. Ce script fetch des échantillons d'offres sur des codes
ROME clés pour OrientIA et produit un fichier stats marché temps réel.

**Rate limit** : 10 RPS officiel FT, DEFAULT_RPM 500 dans scaffold.
**Max par page** : 150 offres (cap FT).

Usage :
    python scripts/ingest_ft_offres_emploi.py

Output : `data/processed/ft_offres_sample.json`
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(str(REPO_ROOT / ".env"))

# Patch scope combo before import cache
import src.collect.ft_offres_emploi as _mod  # noqa: E402
_mod.OffresEmploiClient.SCOPE = "api_offresdemploiv2 o2dsoffre"

from src.collect.ft_offres_emploi import OffresEmploiClient, normalize_offre  # noqa: E402


# ROME codes prioritaires OrientIA (scope domaine couverture) :
ROME_CODES_PRIORITAIRES = [
    ("M1805", "Développeur / Développeuse informatique"),
    ("M1812", "Direction sécurité IT (RSSI)"),
    ("M1811", "Data engineer / ingénieur data"),
    ("M1855", "Développeur web"),
    ("J1506", "Soins infirmiers généralistes"),
    ("J1501", "Aide-soignant / Aide-soignante"),
    ("K1801", "Conseil en emploi et insertion professionnelle"),
    ("G1503", "Management du personnel de cuisine"),
    ("F1703", "Maçonnerie"),
    ("H1203", "Conception et dessin de produits électriques et électroniques"),
]

MAX_OFFRES_PAR_ROME = 150  # max FT
OUTPUT_PATH = REPO_ROOT / "data" / "processed" / "ft_offres_sample.json"


def main() -> int:
    client = OffresEmploiClient()
    all_offres = []
    t0 = time.time()

    for code_rome, label in ROME_CODES_PRIORITAIRES:
        print(f"  [ft-offres] Fetch {code_rome} ({label})…")
        try:
            resp = client.search(
                code_rome=code_rome, range_start=0, range_end=MAX_OFFRES_PAR_ROME - 1
            )
            offres = resp.get("resultats", []) if isinstance(resp, dict) else []
            print(f"      → {len(offres)} offres")
            for o in offres:
                n = normalize_offre(o)
                n["_code_rome_query"] = code_rome
                n["_libelle_rome_query"] = label
                all_offres.append(n)
        except Exception as e:
            print(f"      ❌ {type(e).__name__}: {str(e)[:120]}")
        time.sleep(0.2)  # anti burst rate-limit

    elapsed = time.time() - t0
    print(f"\n  [ft-offres] Total : {len(all_offres)} offres en {elapsed:.1f}s")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(all_offres, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  [ft-offres] Saved → {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
