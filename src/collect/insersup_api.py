"""InserSup — ingestion API Opendatasoft MESR (distincte du CSV legacy).

Source : https://data.enseignementsup-recherche.gouv.fr/explore/dataset/fr-esr-insersup/
API : Opendatasoft v2.1 (même plateforme que MonMaster/ONISEP ext/LBA, pattern
connu — `/exports/json` pour bulk export contournant le cap offset=10k).
Licence : Etalab 2.0 (statistique publique ouverte).

**Distinction `insersup.py` vs `insersup_api.py`** :

- `src/collect/insersup.py` (legacy) : **CSV loader + attach** — lit un CSV
  `data/raw/insersup.csv` téléchargé manuellement, joint aux fiches existantes
  via UAI. Préservé pour rétrocompat avec le pipeline merge v1.
- `src/collect/insersup_api.py` (ce module) : **API bulk fetch** — récupère
  les données via l'API Opendatasoft officielle et produit
  `data/processed/insersup_insertion.json` (table de référence stats).
  Consommable par le merger v2 via une future `attach_insersup_v2()` ou
  comme source autonome.

**Apports OrientIA** (phase c insertion pro, ADR-039) :

- Insertion salariée vs non-salariée à 6 / 12 / 18 / 24 / 30 mois
- Granularité établissement × discipline (comble le gap Céreq qui agrège
  par niveau de diplôme seul)
- Complémentaire à Céreq sans le remplacer (Céreq a des métriques que
  InserSup n'expose pas : revenu_travail, trajectoires, correspondance)

**Stratégie ingestion** :

- 839 554 records totaux (toutes dimensions détaillées)
- Filtre par défaut sur **agrégats "ensemble"** (obtention_diplome +
  genre + nationalite + regime_inscription) → ~48 230 records.
  Suffisant pour RAG sans sur-combinatoire.
- Endpoint `/exports/json` (bulk, contourne cap offset=10k).
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Optional

import requests


BASE_EXPORT_URL = (
    "https://data.enseignementsup-recherche.gouv.fr/api/explore/v2.1/"
    "catalog/datasets/fr-esr-insersup/exports/json"
)
BASE_RECORDS_URL = (
    "https://data.enseignementsup-recherche.gouv.fr/api/explore/v2.1/"
    "catalog/datasets/fr-esr-insersup/records"
)
DEFAULT_WHERE = (
    'obtention_diplome:"ensemble" AND genre:"ensemble" '
    'AND nationalite:"ensemble" AND regime_inscription:"ensemble"'
)

RAW_DIR = Path("data/raw")
PROCESSED_PATH = Path("data/processed/insersup_insertion.json")


# --- Mapping type_diplome_long → niveau OrientIA ---

TYPE_DIPLOME_TO_NIVEAU: dict[str, str] = {
    "Master LMD": "bac+5",
    "Master MEEF": "bac+5",
    "Licence LMD": "bac+3",
    "Licence générale": "bac+3",
    "Licence professionnelle": "bac+3",
    "Diplôme d'ingénieurs": "bac+5",
    "Diplôme visé niveau bac+5 grade Master": "bac+5",
    "Diplôme visé niveau bac+3 grade Licence": "bac+3",
    "Diplôme gradé ou visé management niveau bac+5": "bac+5",
    "Bachelor universitaire de technologie": "bac+3",  # BUT
    "DUT": "bac+2",
    "BTS": "bac+2",
    "Doctorat": "bac+8",
}


def type_diplome_to_niveau(label: Optional[str]) -> Optional[str]:
    """Mapping `type_diplome_long` InserSup → niveau OrientIA.

    Priorité : match exact, puis substring insensible à la casse pour
    tolérer les variantes d'écriture.
    """
    if not label:
        return None
    if label in TYPE_DIPLOME_TO_NIVEAU:
        return TYPE_DIPLOME_TO_NIVEAU[label]
    key = label.lower()
    if "master" in key or "ingénieur" in key or "ingenieur" in key:
        return "bac+5"
    if "licence pro" in key or "licence prof" in key:
        return "bac+3"
    if "licence" in key or "bachelor" in key:
        return "bac+3"
    if "dut" in key or "bts" in key:
        return "bac+2"
    if "doctorat" in key:
        return "bac+8"
    return None


# --- Fetch & normalize ---


class InsersupFetchError(Exception):
    """Erreur réseau ou réponse API inattendue."""


def fetch_insersup_records(
    where: str = DEFAULT_WHERE,
    max_records: Optional[int] = None,
    session: Optional[requests.Session] = None,
    timeout: int = 300,
) -> list[dict[str, Any]]:
    """Fetch via `/exports/json` (contourne cap offset 10k du /records).

    Args:
        where: clause de filtrage Opendatasoft (par défaut : agrégats
               'ensemble' sur les 4 dimensions combinatoires).
        max_records: limite optionnelle (dev/test).
        session: requests.Session optionnel.
        timeout: timeout HTTP (défaut 5 min pour bulk export ~40MB).

    Returns:
        Liste de records bruts (dict Opendatasoft).
    """
    sess = session or requests.Session()
    params: dict[str, Any] = {"where": where}
    if max_records is not None:
        params["limit"] = max_records
    resp = sess.get(BASE_EXPORT_URL, params=params, timeout=timeout)
    if resp.status_code != 200:
        raise InsersupFetchError(
            f"InserSup API {resp.status_code}: {resp.text[:200]}"
        )
    data = resp.json()
    if not isinstance(data, list):
        raise InsersupFetchError(
            f"Réponse inattendue (attendu list, obtenu {type(data).__name__})"
        )
    return data


def _safe_int(val: Any) -> Optional[int]:
    if val is None or val == "":
        return None
    try:
        return int(float(str(val).replace(",", ".")))
    except (ValueError, TypeError):
        return None


def _safe_ratio(val: Any) -> Optional[float]:
    """Convertit en ratio [0,1]. InserSup expose les taux en %.

    Heuristique : valeur > 1 = pourcentage (ex "1.01" = 1.01% = 0.0101).
    Valeur ≤ 1 = ratio déjà normalisé. Attention : une valeur de
    pourcentage "1.0" est ambiguë mais très rare dans la donnée réelle
    (100% = chiffre brut "100" qui devient 1.0 après division, pas une
    entrée source "1.0"). On tranche : strictement > 1 → pct.
    """
    if val is None or val == "":
        return None
    try:
        f = float(str(val).replace(",", "."))
    except (ValueError, TypeError):
        return None
    return f / 100.0 if f > 1.0 else f


def _extract_horizons(record: dict, prefix: str) -> dict[str, Optional[float]]:
    """Extrait les mesures aux 5 horizons (6/12/18/24/30 mois) pour un préfixe.

    Ex pour `prefix="tx_sortants_en_emploi_sal_fr"` :
        {"6m": 0.75, "12m": 0.80, "18m": 0.78, "24m": 0.82, "30m": 0.82}

    Valeurs None si absentes du record.
    """
    return {
        f"{h}m": _safe_ratio(record.get(f"{prefix}_{h}"))
        for h in (6, 12, 18, 24, 30)
    }


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    """Normalise un record InserSup brut en fiche stats OrientIA.

    Schéma de sortie :
        source, date_jeu, cohorte_promo, region, academie, etablissement,
        type_diplome, niveau_orientia, domaine, discipline, secteur_discipline,
        libelle_diplome, nb_sortants, nb_poursuivants,
        taux_emploi_salarie_fr (dict 5 horizons), taux_emploi_non_salarie (idem),
        cohorte_dimensions (obtention / genre / nationalite / regime).
    """
    promo = record.get("promo")
    # `promo` est souvent une list (ex ["2021"]) côté Opendatasoft
    cohorte_promo = (
        promo[0] if isinstance(promo, list) and promo else promo
    ) if promo else None

    type_diplome = record.get("type_diplome_long")

    return {
        "source": "insersup",
        "date_jeu": record.get("date_jeu"),
        "cohorte_promo": cohorte_promo,
        "region": record.get("reg_nom"),
        "academie": record.get("aca_nom"),
        "etablissement": record.get("uo_lib"),
        "type_diplome": type_diplome,
        "niveau_orientia": type_diplome_to_niveau(type_diplome),
        "domaine": record.get("dom_lib"),
        "discipline": record.get("discipli_lib"),
        "secteur_discipline": record.get("sectdis_lib"),
        "libelle_diplome": record.get("libelle_diplome"),
        "nb_sortants": _safe_int(record.get("nb_sortants")),
        "nb_poursuivants": _safe_int(record.get("nb_poursuivants")),
        "taux_emploi_salarie_fr": _extract_horizons(
            record, "tx_sortants_en_emploi_sal_fr"
        ),
        "taux_emploi_non_salarie": _extract_horizons(
            record, "tx_sortants_en_emploi_non_sal"
        ),
        "cohorte_dimensions": {
            "obtention_diplome": record.get("obtention_diplome"),
            "genre": record.get("genre"),
            "nationalite": record.get("nationalite"),
            "regime_inscription": record.get("regime_inscription"),
        },
    }


def normalize_all(raw_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_record(r) for r in raw_records]


def save_raw(
    raw: list[dict[str, Any]],
    path: Path = RAW_DIR / "insersup_records.json",
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return path


def save_processed(
    normalized: list[dict[str, Any]], path: Path = PROCESSED_PATH,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return path


def collect_insersup_insertion(
    where: str = DEFAULT_WHERE,
    max_records: Optional[int] = None,
    save_raw_flag: bool = False,
    save_normalized: bool = True,
) -> list[dict[str, Any]]:
    """Pipeline complet : fetch → normalize → save.

    `save_raw_flag=False` par défaut (data/raw/ gitignored, pas commité).
    """
    t0 = time.time()
    print("  [insersup_api] Fetch via /exports/json (filtre ensemble agrégé)…")
    raw = fetch_insersup_records(where=where, max_records=max_records)
    print(f"  [insersup_api] {len(raw)} records récupérés en {time.time()-t0:.1f}s")

    if save_raw_flag:
        p = save_raw(raw)
        print(f"  [insersup_api] raw sauvés → {p}")

    normalized = normalize_all(raw)
    print(f"  [insersup_api] {len(normalized)} fiches normalisées")

    if save_normalized:
        p = save_processed(normalized)
        print(f"  [insersup_api] saved → {p}")

    return normalized


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingestion InserSup MESR via API Opendatasoft")
    parser.add_argument("--max", type=int, default=None, help="Limite records")
    parser.add_argument(
        "--save-raw", action="store_true", help="Sauver le raw (gitignored)"
    )
    parser.add_argument(
        "--where", default=DEFAULT_WHERE,
        help='Clause de filtrage (défaut = agrégats "ensemble")'
    )
    args = parser.parse_args()
    fiches = collect_insersup_insertion(
        where=args.where, max_records=args.max, save_raw_flag=args.save_raw
    )
    print(f"  [insersup_api] total : {len(fiches)} entrées")
