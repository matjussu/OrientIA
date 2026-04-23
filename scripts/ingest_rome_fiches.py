"""Ingestion fire-and-forget des 1584 fiches ROME 4.0 détaillées.

Rate limit France Travail = 1 RPS sur `api_rome-fiches-metiersv1`. Durée ~26 min.

Usage : `python scripts/ingest_rome_fiches.py` (background via run_in_background).

Sortie : 1 fichier JSON par code ROME dans `data/raw/rome_api/fiches_metiers/`.
Résume : `data/raw/rome_api/fiches_metiers_progress.json` (checkpoint resume).
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# Load .env
for line in Path(".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

sys.path.insert(0, ".")

from src.collect.rome_api import RomeApiClient  # noqa: E402


FICHES_DIR = Path("data/raw/rome_api/fiches_metiers")
PROGRESS_PATH = Path("data/raw/rome_api/fiches_metiers_progress.json")


def main():
    # Liste des codes
    metiers_list_path = Path("data/raw/rome_api/metiers_list.json")
    if not metiers_list_path.exists():
        print(f"✗ Missing {metiers_list_path}. Run GET /metiers/metier first.")
        sys.exit(1)

    metiers = json.loads(metiers_list_path.read_text(encoding="utf-8"))
    codes = [m["code"] for m in metiers if m.get("code")]
    print(f"  [rome_fiches] {len(codes)} codes à ingérer")

    FICHES_DIR.mkdir(parents=True, exist_ok=True)
    already_done = {p.stem for p in FICHES_DIR.glob("*.json")}
    to_fetch = [c for c in codes if c not in already_done]
    print(f"  [rome_fiches] {len(already_done)} déjà fetched, {len(to_fetch)} à faire")

    client = RomeApiClient(rpm=50)  # 1 RPS safe margin
    import requests

    total_ok = 0
    total_err = 0
    start = time.time()
    for i, code in enumerate(to_fetch):
        try:
            client._limiter.acquire()
            url = f"https://api.francetravail.io/partenaire/rome-fiches-metiers/v1/fiches-rome/fiche-metier/{code}"
            resp = client._session.get(
                url, headers=client._auth_headers(), timeout=30
            )
            if resp.status_code == 200:
                fiche = resp.json()
                (FICHES_DIR / f"{code}.json").write_text(
                    json.dumps(fiche, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                total_ok += 1
            else:
                total_err += 1
                print(f"  [rome_fiches] {code}: HTTP {resp.status_code}")
        except Exception as exc:
            total_err += 1
            print(f"  [rome_fiches] {code}: {type(exc).__name__}: {str(exc)[:100]}")

        # Progress every 50 fiches
        if (i + 1) % 50 == 0:
            elapsed = time.time() - start
            rate = (i + 1) / elapsed
            eta_s = (len(to_fetch) - i - 1) / rate if rate > 0 else 0
            print(
                f"  [rome_fiches] {i+1}/{len(to_fetch)} — ok={total_ok} err={total_err} — "
                f"ETA {eta_s/60:.1f} min"
            )
            PROGRESS_PATH.write_text(
                json.dumps({
                    "i": i + 1,
                    "total": len(to_fetch),
                    "ok": total_ok,
                    "err": total_err,
                    "rate_rps": rate,
                }), encoding="utf-8"
            )

    elapsed = time.time() - start
    print(f"  [rome_fiches] DONE — {total_ok} OK / {total_err} ERR / {elapsed/60:.1f} min")
    PROGRESS_PATH.write_text(
        json.dumps({"status": "done", "ok": total_ok, "err": total_err, "duration_s": elapsed}),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
