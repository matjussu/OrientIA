"""Ingestion La Bonne Alternance live (D10).

Post-merge PR #35 (URLs fixées), lance l'ingestion réelle pour combler la
phase (b) réorientation/alternance à 0% (ADR-039).

Stratégie :
- `/api/formation/v1/search` : 1 query par ROME code principal × 15 domaines,
  ~40 queries, bulk collect + dedup par `id` (ou `_id`).
- `/api/job/v1/search` : sample léger par ROME code + geo "France entière"
  pour validation format + volume (filtre actives only, 30j récentes).

Rate limit non-documenté mais probable 5-20 RPS. On reste safe à 2 RPS via
le client `labonnealternance.py` (DEFAULT_RPM=120).
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

import requests  # noqa: E402

from src.collect.labonnealternance import (  # noqa: E402
    FORMATIONS_ENDPOINT,
    JOBS_ENDPOINT,
    LabonneAlternanceClient,
)


OUT_DIR = Path("data/raw/lba")
FORMATIONS_OUT = Path("data/processed/lba_formations.json")
JOBS_SAMPLE_OUT = Path("data/processed/lba_jobs_sample.json")


# Sélection de codes ROME représentatifs pour les 15 domaines OrientIA.
# Chaque entrée = (domaine_orientia, rome_code_cible).
ROME_CODES_BY_DOMAIN = [
    # Tech
    ("cyber", "M1844"),           # Analyste cybersécurité
    ("data_ia", "M1405"),         # Data scientist
    # Santé
    ("sante", "J1501"),           # Infirmier
    ("sante", "J1404"),           # Kinésithérapeute
    # Droit + Eco-gestion
    ("droit", "K1901"),           # Aide juridique
    ("eco_gestion", "M1203"),     # Comptabilité
    ("eco_gestion", "D1402"),     # Commerce
    ("eco_gestion", "M1402"),     # Finance
    # Sciences humaines / Langues / Lettres-Arts
    ("sciences_humaines", "K1204"),  # Social
    ("langues", "E1108"),            # Traduction
    ("lettres_arts", "L1302"),       # Arts scéniques
    ("lettres_arts", "E1103"),       # Design
    # Sport / Sciences / Ingénierie
    ("sport", "G1204"),              # Animation sportive
    ("sciences_fondamentales", "H1206"),  # Recherche
    ("ingenierie_industrielle", "H1102"),  # Ingé mécanique
    ("ingenierie_industrielle", "H1208"),  # Ingé électrique
    # Communication / Education / Agriculture / Tourisme
    ("communication", "E1103"),       # Communication
    ("education", "K2101"),           # Éducation
    ("agriculture", "A1401"),         # Maraîchage
    ("tourisme_hotellerie", "G1703"), # Réception hôtel
]


GEO_CENTERS = [
    ("Paris", 48.8534, 2.3488),
    ("Lyon", 45.7640, 4.8357),
    ("Toulouse", 43.6047, 1.4442),
    ("Lille", 50.6292, 3.0573),
    ("Marseille", 43.2965, 5.3698),
    ("Bordeaux", 44.8378, -0.5792),
    ("Nantes", 47.2184, -1.5536),
    ("Strasbourg", 48.5734, 7.7521),
]


def fetch_formations_by_rome(client: LabonneAlternanceClient, rome: str, page_size: int = 100) -> list[dict]:
    """Fetch formations alternance pour un code ROME.

    Params LBA swagger : `romes` (pluriel CSV), `page_size`, `page_index`,
    `latitude`+`longitude`+`radius` (requis pour search géolocalisé).

    LBA cap radius ~200 km max. Pour couverture France on fait plusieurs
    queries géolocalisées (GEO_CENTERS) puis dedup cross-queries par ID.
    """
    # LBA limite radius à ~200km max (testé empiriquement). Pour couvrir
    # France entière on fait 3 queries géolocalisées : Paris (nord IDF),
    # Lyon (sud-est) et Toulouse (sud-ouest), puis dedup par id.
    client._limiter.acquire()
    resp = client._session.get(
        FORMATIONS_ENDPOINT,
        headers=client._auth_headers(),
        params={
            "romes": rome,
            "page_size": page_size,
            "latitude": 48.8534,  # Paris
            "longitude": 2.3488,
            "radius": 200,
        },
        timeout=30,
    )
    if resp.status_code != 200:
        return []
    payload = resp.json()
    return payload.get("data", [])


def fetch_jobs_sample(client: LabonneAlternanceClient, rome: str, longitude: float, latitude: float, radius: int = 100, limit: int = 50) -> list[dict]:
    """Fetch sample offres alternance par ROME + géoloc (Paris centre par défaut)."""
    client._limiter.acquire()
    resp = client._session.get(
        JOBS_ENDPOINT,
        headers=client._auth_headers(),
        params={
            "romes": rome,
            "longitude": longitude,
            "latitude": latitude,
            "radius": radius,
            "limit": limit,
        },
        timeout=30,
    )
    if resp.status_code != 200:
        return []
    payload = resp.json()
    # Format LBA : {"jobs": [...], "warnings": [...]}
    return payload.get("jobs", [])


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    client = LabonneAlternanceClient()

    # Phase 1 : formations par ROME
    print(f"  [lba] Fetching formations sur {len(ROME_CODES_BY_DOMAIN)} codes ROME...")
    all_formations = []
    seen_ids = set()
    per_domain = {}
    for domain, rome in ROME_CODES_BY_DOMAIN:
        try:
            # Fetch depuis plusieurs centres géo pour couvrir France
            forms = []
            for city, lat, lon in GEO_CENTERS:
                client._limiter.acquire()
                resp = client._session.get(
                    FORMATIONS_ENDPOINT,
                    headers=client._auth_headers(),
                    params={
                        "romes": rome,
                        "page_size": 100,
                        "latitude": lat,
                        "longitude": lon,
                        "radius": 200,
                    },
                    timeout=30,
                )
                if resp.status_code == 200:
                    forms.extend(resp.json().get("data", []))
            added = 0
            for f in forms:
                # LBA formations : identifiant.cle_ministere_educatif est l'ID
                # unique (format "XXX-dept#siret" par session de formation).
                ident = f.get("identifiant") or {}
                fid = ident.get("cle_ministere_educatif") or f.get("_id") or f.get("id")
                if not fid:
                    continue
                if fid in seen_ids:
                    continue
                seen_ids.add(fid)
                f["_orientia_domain"] = domain  # traçabilité mapping
                f["_orientia_rome"] = rome
                all_formations.append(f)
                added += 1
            per_domain.setdefault(domain, 0)
            per_domain[domain] += added
            print(f"  [lba] {domain:25s} ROME {rome}: +{added} uniques")
        except Exception as exc:
            print(f"  [lba] {domain}/{rome}: {type(exc).__name__}: {str(exc)[:100]}")

    print(f"\n  [lba] Formations uniques : {len(all_formations)}")
    print(f"  [lba] Répartition par domaine : {per_domain}")
    FORMATIONS_OUT.parent.mkdir(parents=True, exist_ok=True)
    FORMATIONS_OUT.write_text(
        json.dumps(all_formations, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  [lba] Formations sauvées → {FORMATIONS_OUT}")

    # Phase 2 : sample offres jobs (juste validation format + volume)
    print(f"\n  [lba] Fetching jobs sample (Paris centre, ROME cyber/data/santé)...")
    jobs_sample = []
    for rome in ["M1844", "M1405", "J1501"]:
        try:
            jobs = fetch_jobs_sample(client, rome, longitude=2.3488, latitude=48.8534, radius=100, limit=50)
            for j in jobs:
                j["_orientia_rome"] = rome
            jobs_sample.extend(jobs)
            print(f"  [lba] ROME {rome} jobs sample: {len(jobs)} offres")
        except Exception as exc:
            print(f"  [lba] jobs/{rome}: {type(exc).__name__}: {str(exc)[:100]}")

    JOBS_SAMPLE_OUT.write_text(
        json.dumps(jobs_sample, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n  [lba] Jobs sample : {len(jobs_sample)} offres → {JOBS_SAMPLE_OUT}")
    print(f"  [lba] DONE. Total corpus LBA : {len(all_formations)} formations + {len(jobs_sample)} jobs sample")


if __name__ == "__main__":
    main()
