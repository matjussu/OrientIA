"""INSEE Base Tous Salariés (BTS) — statistiques salaires par PCS × âge (D14 ADR-040).

Source : https://www.insee.fr/fr/statistiques/8730395 (BTS 2023, Fichier "salariés")
Licence : Open Data INSEE / Etalab 2.0
Volume brut : ~2.5M lignes individuelles (échantillon 1/12ème population salariée FR)

**Particularité ingestion** : INSEE distribue des données individuelles (pas
agrégées). L'ingestion OrientIA fait une agrégation pandas :

    raw (2.5M rows) → groupby(PCS, AGE_TR) → {n, salaire_mean, salaire_median, salaire_p25, salaire_p75}

Le fichier aggregated (~500 lignes × 4-6 tranches âge = ~2-3k entrées) est
petit et commitable dans `data/processed/`.

**Statut** : SCAFFOLD-READY — le live run nécessite ~100-500 MB download +
~30s aggregation pandas. Lancer `python -m src.collect.insee_emploi` quand
décision prise côté budget bandwidth + disque.

Scope ADR-040 D14 : complète la dimension "salaires par ancienneté" du scope
élargi 17-25 ans avec des données officielles nationales INSEE (vs Céreq
qui est par niveau diplôme × secteur, granularité différente).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import requests


# URLs download (dernière campagne 2023 publiée fin 2024). Ces URLs sont
# parfois datées dans le path INSEE (on maintient un fallback). À date de
# scaffold : campagne 2023 stable.
DEFAULT_SALARIES_CSV_URL = (
    "https://www.insee.fr/fr/statistiques/fichier/8730395/bts_2023_salaries.csv"
)
DEFAULT_PCS_REFERENTIEL_URL = (
    "https://www.insee.fr/fr/information/6051913"  # PCS 2020 ref table
)

RAW_DIR = Path("data/raw/insee_emploi")
PROCESSED_PATH = Path("data/processed/insee_salaires_pcs_age.json")


class InseeDataMissing(Exception):
    """Le CSV INSEE BTS attendu n'est pas présent localement."""


def download_bts_salaries(
    target_path: Optional[Path] = None,
    url: str = DEFAULT_SALARIES_CSV_URL,
    session: Optional[requests.Session] = None,
    timeout: int = 600,  # 10 min — fichier potentiellement lourd
) -> Path:
    """Télécharge le CSV brut BTS salariés INSEE.

    Taille attendue : 100-500 MB. Timeout généreux, stream write.
    """
    sess = session or requests.Session()
    target = target_path or (RAW_DIR / "bts_2023_salaries.csv")
    target.parent.mkdir(parents=True, exist_ok=True)

    resp = sess.get(url, timeout=timeout, stream=True)
    resp.raise_for_status()
    with open(target, "wb") as f:
        for chunk in resp.iter_content(chunk_size=1024 * 1024):  # 1 MB chunks
            if chunk:
                f.write(chunk)
    return target


def aggregate_salaries_by_pcs_age(
    csv_path: Path,
    pcs_column: str = "PCS",
    age_column: str = "AGE_TR",
    salary_column: str = "SNHM",  # Salaire Net Horaire Moyen — standard INSEE
) -> list[dict[str, Any]]:
    """Agrège les ~2.5M lignes individuelles en stats par (PCS × AGE_TR).

    Retourne une liste de dicts :
        {
            "code_pcs": str,
            "tranche_age": str,  # ex: "26-30" ou "20-23"
            "n_salaries": int,
            "salaire_mean": float,
            "salaire_median": float,
            "salaire_p25": float,
            "salaire_p75": float,
        }

    Import pandas au niveau fonction pour qu'il ne soit pas chargé au simple
    import du module (évite latence démarrage quand on n'appelle pas cette fn).
    """
    if not csv_path.exists():
        raise InseeDataMissing(
            f"CSV BTS INSEE absent : {csv_path}. "
            "Run `python -m src.collect.insee_emploi --download` d'abord."
        )
    import pandas as pd

    # Le CSV INSEE utilise le point-virgule comme séparateur (standard FR)
    df = pd.read_csv(csv_path, sep=";", encoding="utf-8", low_memory=False)

    # Sanity check colonnes attendues
    missing = {c for c in (pcs_column, age_column, salary_column) if c not in df.columns}
    if missing:
        raise ValueError(
            f"Colonnes manquantes dans CSV BTS : {missing}. "
            f"Colonnes disponibles : {list(df.columns)[:20]}..."
        )

    grouped = df.groupby([pcs_column, age_column])[salary_column].agg(
        ["count", "mean", "median",
         lambda s: s.quantile(0.25),
         lambda s: s.quantile(0.75)]
    )
    # Rename lambdas → p25 / p75
    grouped.columns = ["n_salaries", "salaire_mean", "salaire_median", "salaire_p25", "salaire_p75"]

    out = []
    for (pcs, age_tr), row in grouped.iterrows():
        out.append({
            "code_pcs": str(pcs),
            "tranche_age": str(age_tr),
            "n_salaries": int(row["n_salaries"]),
            "salaire_mean": round(float(row["salaire_mean"]), 2),
            "salaire_median": round(float(row["salaire_median"]), 2),
            "salaire_p25": round(float(row["salaire_p25"]), 2),
            "salaire_p75": round(float(row["salaire_p75"]), 2),
        })
    return out


def save_processed(
    entries: list[dict[str, Any]], path: Path = PROCESSED_PATH
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return path


def build_pcs_index(
    entries: list[dict[str, Any]]
) -> dict[str, dict[str, dict[str, Any]]]:
    """Index imbriqué pour lookup rapide : `index[pcs_code][age_tr]` → stats."""
    index: dict[str, dict[str, dict[str, Any]]] = {}
    for e in entries:
        pcs = e.get("code_pcs")
        age = e.get("tranche_age")
        if not pcs or not age:
            continue
        index.setdefault(pcs, {})[age] = e
    return index


def collect_insee_salaries(
    csv_path: Optional[Path] = None,
    download_if_missing: bool = False,
    save: bool = True,
) -> list[dict[str, Any]]:
    """Pipeline end-to-end : (download si requested) → aggregate → save.

    Par défaut `download_if_missing=False` — le download est ~100-500 MB,
    on veut une confirmation explicite. Passer `--download` au CLI.
    """
    target = csv_path or (RAW_DIR / "bts_2023_salaries.csv")
    if not target.exists():
        if download_if_missing:
            print(f"  [insee] Downloading BTS 2023 salaries CSV (~100-500 MB) → {target}...")
            download_bts_salaries(target)
        else:
            raise InseeDataMissing(
                f"CSV BTS absent : {target}. "
                "Lancer avec --download ou download manuel depuis "
                "https://www.insee.fr/fr/statistiques/8730395"
            )
    entries = aggregate_salaries_by_pcs_age(target)
    if save:
        path = save_processed(entries)
        print(f"  [insee] {len(entries)} entrées agrégées (PCS×âge) → {path}")
    return entries


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingestion INSEE BTS D14 Axe 1")
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download le CSV BTS si absent (~100-500 MB)",
    )
    args = parser.parse_args()
    try:
        entries = collect_insee_salaries(download_if_missing=args.download)
        print(f"  [insee] total entries : {len(entries)}")
    except InseeDataMissing as e:
        print(f"  [insee] ⚠️  {e}")
