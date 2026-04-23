"""Ingestion RNCP France Compétences (D9 Axe 1 scope élargi 17-25 ans).

Source : `https://www.data.gouv.fr/datasets/repertoire-national-des-certifications-professionnelles-et-repertoire-specifique/`
Licence Etalab 2.0 — redistribution autorisée.

Schéma relationnel (10 CSVs dans le ZIP officiel). On joint :
- `Standard` : fiche principale (nom, niveau NQF/EQF, actif/inactif)
- `VoixdAccès` : apprentissage / formation continue / VAE / expérience
- `Rome` : codes métiers ROME 4.0 (aligne avec `src/collect/rome_api.py`)
- `Nsf` : Nomenclature des Spécialités de Formation (secteur)
- `Certificateurs` : organisme certificateur (SIRET + nom)

Filtre : fiches `ACTIVE` uniquement (6 590 sur 29 707 totales).

Couverture scope élargi :
- Phase (a) initial : complémente Parcoursup avec certifs post-bac (NIV4 bac).
- Phase (b) réorientation : voies d'accès alternance / VAE / formation continue.
- Phase (c) master + insertion pro : NIV7 (bac+5) = 8 950 fiches, y compris MBA, MSc, etc.

Pas d'ingestion API live : le CSV export quotidien (via cron J+0) couvre
les besoins OrientIA. API `api.apprentissage.beta.gouv.fr` reste une option
future (nécessite token, scope noté dans docs/TODO_MATTEO_APIS.md).
"""
from __future__ import annotations

import csv
import io
import json
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

import requests


DATA_GOUV_DATASET_ID = "5eebbc067a14b6fecc9c9976"

# URL stable du CSV export — versionné par date dans le path static.data.gouv.fr.
# Pour trouver la dernière URL : `GET /api/1/datasets/{DATASET_ID}/` puis
# cherche ressource dont `title` commence par `export-fiches-csv-`.
DEFAULT_CSV_ZIP_URL = (
    "https://static.data.gouv.fr/resources/"
    "repertoire-national-des-certifications-professionnelles-et-repertoire-specifique/"
    "20260423-020001/export-fiches-csv-2026-04-23.zip"
)

RAW_DIR = Path("data/raw/rncp")
PROCESSED_PATH = Path("data/processed/rncp_certifications.json")

# Mapping Nomenclature Europe → niveau interne OrientIA (bac+N).
NIVEAU_EU_TO_ORIENTIA = {
    "NIV3": "cap-bep",       # CAP/BEP
    "NIV4": "bac",           # Bac pro / général / techno
    "NIV5": "bac+2",         # BTS / BUT 2 / DEUG
    "NIV6": "bac+3",         # Licence / BUT / Bachelor
    "NIV7": "bac+5",         # Master / Ingénieur
    "NIV8": "bac+8",         # Doctorat
}

# Mapping Nomenclature Europe → phase scope élargi (ADR-039).
NIVEAU_EU_TO_PHASE = {
    "NIV3": "initial",
    "NIV4": "initial",
    "NIV5": "initial",
    "NIV6": "initial",
    "NIV7": "master",         # bac+5 = phase (c)
    "NIV8": "master",
}


# --- Download ---


def fetch_latest_csv_zip_url(
    session: Optional[requests.Session] = None, timeout: int = 30
) -> str:
    """Interroge data.gouv.fr API pour trouver l'URL du dernier export CSV.

    Évite d'hardcoder une URL datée qui se périmera dans 48h. Fallback sur
    DEFAULT_CSV_ZIP_URL si l'API est down.
    """
    sess = session or requests.Session()
    try:
        url = f"https://www.data.gouv.fr/api/1/datasets/{DATA_GOUV_DATASET_ID}/"
        resp = sess.get(url, timeout=timeout)
        resp.raise_for_status()
        payload = resp.json()
        for res in payload.get("resources", []):
            title = (res.get("title") or "").lower()
            if title.startswith("export-fiches-csv-") and (res.get("format") or "").lower() == "zip":
                return res.get("url") or DEFAULT_CSV_ZIP_URL
    except Exception:
        pass
    return DEFAULT_CSV_ZIP_URL


def download_csv_zip(
    target_path: Optional[Path] = None,
    url: Optional[str] = None,
    session: Optional[requests.Session] = None,
) -> Path:
    """Télécharge le ZIP CSV RNCP sur disque.

    Idempotent : si le fichier existe déjà et a la même taille que celui
    distant, skip. Sinon re-download.
    """
    sess = session or requests.Session()
    resolved_url = url or fetch_latest_csv_zip_url(session=sess)
    target = target_path or (RAW_DIR / resolved_url.rsplit("/", 1)[-1])
    target.parent.mkdir(parents=True, exist_ok=True)

    # Skip si déjà présent — HEAD pour comparer la taille
    if target.exists():
        head = sess.head(resolved_url, timeout=30, allow_redirects=True)
        remote_size = int(head.headers.get("Content-Length", 0))
        if target.stat().st_size == remote_size and remote_size > 0:
            return target

    resp = sess.get(resolved_url, timeout=300, stream=True)
    resp.raise_for_status()
    with open(target, "wb") as f:
        for chunk in resp.iter_content(chunk_size=65536):
            if chunk:
                f.write(chunk)
    return target


# --- Parsing ---


def _read_csv_from_zip(zip_path: Path, csv_name: str) -> list[dict[str, Any]]:
    """Lit un des CSVs internes du ZIP RNCP (delimiter ';', encoding utf-8)."""
    with zipfile.ZipFile(zip_path) as z:
        with z.open(csv_name) as f:
            text = io.TextIOWrapper(f, encoding="utf-8")
            return list(csv.DictReader(text, delimiter=";"))


def _find_csv_name(zip_path: Path, prefix: str) -> Optional[str]:
    """Cherche un CSV dans le ZIP dont le nom commence par prefix (date varie)."""
    with zipfile.ZipFile(zip_path) as z:
        for n in z.namelist():
            if n.startswith(prefix):
                return n
    return None


def parse_rncp_zip(zip_path: Path) -> dict[str, list[dict[str, Any]]]:
    """Charge les 5 CSVs clefs du ZIP (Standard + VoixdAccès + Rome + Nsf + Certificateurs).

    Les noms de fichiers incluent une date qui varie chaque jour — on matche
    par prefix.
    """
    csv_names = {
        "standard": "export_fiches_CSV_Standard_",
        "voies_acces": "export_fiches_CSV_VoixdAccès_",
        "rome": "export_fiches_CSV_Rome_",
        "nsf": "export_fiches_CSV_Nsf_",
        "certificateurs": "export_fiches_CSV_Certificateurs_",
    }
    out: dict[str, list[dict[str, Any]]] = {}
    for key, prefix in csv_names.items():
        fname = _find_csv_name(zip_path, prefix)
        if fname is None:
            out[key] = []
            continue
        out[key] = _read_csv_from_zip(zip_path, fname)
    return out


# --- Normalisation ---


def _index_by_fiche(rows: list[dict[str, Any]], key: str = "Numero_Fiche") -> dict[str, list[dict[str, Any]]]:
    """Groupe une liste de rows par Numero_Fiche → liste de rows."""
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        numero = r.get(key)
        if numero:
            out[numero].append(r)
    return dict(out)


def normalize_rncp_certification(
    std_row: dict[str, Any],
    voies: list[dict[str, Any]],
    rome: list[dict[str, Any]],
    nsf: list[dict[str, Any]],
    certificateurs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Joint les 5 tables pour produire une fiche OrientIA normalisée."""
    niveau_eu = std_row.get("Nomenclature_Europe_Niveau", "")
    return {
        "source": "rncp",
        "phase": NIVEAU_EU_TO_PHASE.get(niveau_eu, "initial"),
        "numero_fiche": std_row.get("Numero_Fiche"),
        "intitule": std_row.get("Intitule", "").strip(),
        "abrege_type": std_row.get("Abrege_Libelle"),
        "abrege_intitule": std_row.get("Abrege_Intitule"),
        "niveau_eu": niveau_eu,
        "niveau": NIVEAU_EU_TO_ORIENTIA.get(niveau_eu),
        "niveau_intitule": std_row.get("Nomenclature_Europe_Intitule"),
        "type_enregistrement": std_row.get("Type_Enregistrement"),
        "actif": std_row.get("Actif") == "ACTIVE",
        "validation_partielle": std_row.get("Validation_Partielle") == "Oui",
        "date_dernier_jo": std_row.get("Date_dernier_jo"),
        "date_effet": std_row.get("Date_Effet"),
        "date_fin_enregistrement": std_row.get("Date_Fin_Enregistrement"),
        "voies_acces": sorted(
            set(v.get("Si_Jury") for v in voies if v.get("Si_Jury"))
        ),
        "codes_rome": [
            {"code": r.get("Codes_Rome_Code"), "libelle": r.get("Codes_Rome_Libelle")}
            for r in rome
            if r.get("Codes_Rome_Code")
        ],
        "codes_nsf": [
            {"code": n.get("Nsf_Code"), "libelle": n.get("Nsf_Intitule")}
            for n in nsf
            if n.get("Nsf_Code")
        ],
        "certificateurs": [
            {
                "siret": (c.get("Siret_Certificateur") or "").strip(),
                "nom": c.get("Nom_Certificateur", "").strip(),
            }
            for c in certificateurs
            if c.get("Nom_Certificateur")
        ],
    }


def build_certifications(
    parsed: dict[str, list[dict[str, Any]]],
    only_active: bool = True,
) -> list[dict[str, Any]]:
    """Joint les 5 tables par Numero_Fiche et normalise au schéma OrientIA.

    `only_active=True` (défaut) filtre les fiches ACTIVE (6590 sur 29707).
    """
    standard = parsed.get("standard", [])
    voies_by_fiche = _index_by_fiche(parsed.get("voies_acces", []))
    rome_by_fiche = _index_by_fiche(parsed.get("rome", []))
    nsf_by_fiche = _index_by_fiche(parsed.get("nsf", []))
    cert_by_fiche = _index_by_fiche(parsed.get("certificateurs", []))

    out: list[dict[str, Any]] = []
    for std_row in standard:
        if only_active and std_row.get("Actif") != "ACTIVE":
            continue
        numero = std_row.get("Numero_Fiche")
        normalized = normalize_rncp_certification(
            std_row=std_row,
            voies=voies_by_fiche.get(numero, []),
            rome=rome_by_fiche.get(numero, []),
            nsf=nsf_by_fiche.get(numero, []),
            certificateurs=cert_by_fiche.get(numero, []),
        )
        out.append(normalized)
    return out


def save_processed(
    normalized: list[dict[str, Any]], path: Path = PROCESSED_PATH
) -> Path:
    """Dump les certifications normalisées en JSON (commité)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return path


# --- Entrée principale ---


def collect_rncp_certifications(
    zip_path: Optional[Path] = None,
    download_if_missing: bool = True,
    only_active: bool = True,
    save: bool = True,
) -> list[dict[str, Any]]:
    """Pipeline end-to-end RNCP : download + parse + join + normalize + save.

    `zip_path` : si fourni, parse ce fichier local. Sinon cherche le plus
    récent dans `data/raw/rncp/` ou download.
    """
    # Résoudre zip_path : paramètre > plus récent local > download
    if zip_path is None:
        existing = sorted(RAW_DIR.glob("export-fiches-csv-*.zip"))
        if existing and not download_if_missing:
            zip_path = existing[-1]
        elif existing:
            zip_path = existing[-1]  # réutilise le plus récent si présent
        else:
            zip_path = download_csv_zip()
    parsed = parse_rncp_zip(zip_path)
    certifs = build_certifications(parsed, only_active=only_active)
    if save:
        path = save_processed(certifs)
        print(f"  [rncp] {len(certifs)} certifications normalisées → {path}")
    return certifs


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingestion RNCP D9")
    parser.add_argument("--zip", type=str, help="Chemin ZIP CSV local (optionnel)")
    parser.add_argument(
        "--include-inactive",
        action="store_true",
        help="Inclure certifications inactives (défaut : actives seulement)",
    )
    parser.add_argument(
        "--no-download",
        action="store_true",
        help="Ne pas downloader si ZIP absent localement",
    )
    args = parser.parse_args()

    certifs = collect_rncp_certifications(
        zip_path=Path(args.zip) if args.zip else None,
        only_active=not args.include_inactive,
        download_if_missing=not args.no_download,
    )
    print(f"  [rncp] total certifications : {len(certifs)}")
