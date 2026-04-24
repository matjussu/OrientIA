"""Inserjeunes — insertion professionnelle voie pro + apprentissage (DEPP/DARES).

Source lycée pro : https://data.education.gouv.fr/explore/dataset/fr-en-inserjeunes-lycee_pro-formation-fine/
Source CFA     : https://data.education.gouv.fr/explore/dataset/fr-en-inserjeunes-cfa/
Licence : Etalab 2.0 (statistique publique).
API : Opendatasoft v2.1 (même plateforme que MonMaster / InserSup).

**Apports OrientIA** (ADR-039 phase a + b initial voie pro et apprentissage) :

- Voie pro : 132 124 records par établissement × formation fine (CAP → BTS)
- Apprentissage CFA : 11 314 records par centre de formation
- Taux d'emploi 6 / 12 / 18 / 24 mois + taux poursuite études
- **Comble un angle mort majeur** : aucune autre source OrientIA actuelle
  ne couvre la voie pro ou l'apprentissage avec cette granularité fine
  (Parcoursup limité aux choix post-bac, MonMaster au master,
  InserSup au supérieur, Céreq agrégé au niveau diplôme global).

**2 datasets, 2 schémas légèrement différents** :

Lycée pro (`fr-en-inserjeunes-lycee_pro-formation-fine`) : granularité
formation_fine avec `type_diplome`, `libelle_formation`, `duree_formation`,
code MEFSTAT11, flag nouveau/rénové.

CFA (`fr-en-inserjeunes-cfa`) : granularité CFA (établissement) sans
détail formation. Inclut `taux_contrats_interrompus`, `va_emploi_6_mois`
(valeur ajoutée) et `taux_emploi_6_mois_attendu` (prédiction DEPP).

On les ingère dans 2 JSONs séparés pour conserver les différences.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Optional

import requests


LYCEE_PRO_EXPORT_URL = (
    "https://data.education.gouv.fr/api/explore/v2.1/catalog/"
    "datasets/fr-en-inserjeunes-lycee_pro-formation-fine/exports/json"
)
CFA_EXPORT_URL = (
    "https://data.education.gouv.fr/api/explore/v2.1/catalog/"
    "datasets/fr-en-inserjeunes-cfa/exports/json"
)

PROCESSED_LYCEE_PRO_PATH = Path("data/processed/inserjeunes_lycee_pro.json")
PROCESSED_CFA_PATH = Path("data/processed/inserjeunes_cfa.json")


# --- Mapping type_diplome → niveau OrientIA ---
# Source catalogue MEFSTAT : CAP et assimilés niveau V, Bac pro niveau IV,
# BTS niveau III (aujourd'hui niveau 5 via cadre national certifs).

TYPE_DIPLOME_TO_NIVEAU: dict[str, str] = {
    "CAP": "cap-bep",
    "CAP et assimilés": "cap-bep",
    "BEP": "cap-bep",
    "Bac pro": "bac",
    "Bac professionnel": "bac",
    "Mention complémentaire": "bac",
    "Baccalauréat professionnel": "bac",
    "BP": "bac",
    "Brevet professionnel": "bac",
    "BTS": "bac+2",
    "Brevet de technicien supérieur": "bac+2",
    "BMA": "bac",  # Brevet des métiers d'art
}


def type_diplome_to_niveau(label: Optional[str]) -> Optional[str]:
    """Mapping `type_diplome` Inserjeunes → niveau OrientIA.

    Fallback substring : couvre les variantes (« Bac pro SN », « CAP
    boulanger », etc.).
    """
    if not label:
        return None
    if label in TYPE_DIPLOME_TO_NIVEAU:
        return TYPE_DIPLOME_TO_NIVEAU[label]
    key = label.lower()
    if "cap" in key or "bep" in key:
        return "cap-bep"
    if "bts" in key:
        return "bac+2"
    if "bac pro" in key or "baccalauréat pro" in key or "brevet pro" in key or "brevet prof" in key:
        return "bac"
    if "mention complémentaire" in key:
        return "bac"
    return None


# --- Fetch & normalize ---


class InserjeunesFetchError(Exception):
    """Erreur réseau ou réponse API inattendue."""


def _fetch_bulk(
    url: str,
    max_records: Optional[int] = None,
    session: Optional[requests.Session] = None,
    timeout: int = 300,
) -> list[dict[str, Any]]:
    """Fetch via `/exports/json` (bulk, contourne cap offset 10k)."""
    sess = session or requests.Session()
    params: dict[str, Any] = {}
    if max_records is not None:
        params["limit"] = max_records
    resp = sess.get(url, params=params, timeout=timeout)
    if resp.status_code != 200:
        raise InserjeunesFetchError(
            f"Inserjeunes API {resp.status_code}: {resp.text[:200]}"
        )
    data = resp.json()
    if not isinstance(data, list):
        raise InserjeunesFetchError(
            f"Réponse inattendue (attendu list, obtenu {type(data).__name__})"
        )
    return data


def fetch_lycee_pro_records(
    max_records: Optional[int] = None,
    session: Optional[requests.Session] = None,
) -> list[dict[str, Any]]:
    """Fetch le dataset Inserjeunes lycée pro (formation fine)."""
    return _fetch_bulk(LYCEE_PRO_EXPORT_URL, max_records=max_records, session=session)


def fetch_cfa_records(
    max_records: Optional[int] = None,
    session: Optional[requests.Session] = None,
) -> list[dict[str, Any]]:
    """Fetch le dataset Inserjeunes CFA (centre de formation apprentis)."""
    return _fetch_bulk(CFA_EXPORT_URL, max_records=max_records, session=session)


def _safe_int(val: Any) -> Optional[int]:
    if val is None or val == "":
        return None
    try:
        return int(float(str(val).replace(",", ".")))
    except (ValueError, TypeError):
        return None


def _safe_ratio(val: Any) -> Optional[float]:
    """Ratio [0,1]. Valeur >1 = pourcentage à diviser par 100."""
    if val is None or val == "":
        return None
    try:
        f = float(str(val).replace(",", "."))
    except (ValueError, TypeError):
        return None
    return f / 100.0 if f > 1.0 else f


def _extract_taux_horizons(record: dict) -> dict[str, Optional[float]]:
    """Horizons taux d'emploi 6/12/18/24 mois (pas de 30m pour Inserjeunes)."""
    return {
        "6m": _safe_ratio(record.get("taux_emploi_6_mois")),
        "12m": _safe_ratio(record.get("taux_emploi_12_mois")),
        "18m": _safe_ratio(record.get("taux_emploi_18_mois")),
        "24m": _safe_ratio(record.get("taux_emploi_24_mois")),
    }


def normalize_lycee_pro_record(record: dict[str, Any]) -> dict[str, Any]:
    """Normalise un record Inserjeunes lycée pro (formation fine)."""
    type_diplome = record.get("type_diplome")
    return {
        "source": "inserjeunes_lycee_pro",
        "annee": record.get("annee"),
        "uai": record.get("uai"),
        "etablissement": record.get("libelle"),
        "region": record.get("region"),
        "type_diplome": type_diplome,
        "niveau_orientia": type_diplome_to_niveau(type_diplome),
        "code_formation_mefstat11": record.get("code_formation_mefstat11"),
        "libelle_formation": record.get("libelle_formation"),
        "duree_formation": record.get("duree_formation"),
        "diplome_renove_ou_nouveau": record.get("diplome_renove_ou_nouveau"),
        "part_poursuite_etudes": _safe_ratio(record.get("part_en_poursuite_d_etudes")),
        "part_emploi_6_mois_post": _safe_ratio(record.get("part_en_emploi_6_mois_apres_la_sortie")),
        "part_autres_situations": _safe_ratio(record.get("part_des_autres_situations")),
        "taux_poursuite_etudes": _safe_ratio(record.get("taux_poursuite_etudes")),
        "taux_emploi": _extract_taux_horizons(record),
    }


def normalize_cfa_record(record: dict[str, Any]) -> dict[str, Any]:
    """Normalise un record Inserjeunes CFA (centre de formation apprentis)."""
    return {
        "source": "inserjeunes_cfa",
        "annee": record.get("annee"),
        "uai": record.get("uai"),
        "etablissement": record.get("libelle"),
        "region": record.get("region"),
        "niveau_orientia": None,  # CFA agrégé, pas de type_diplome au niveau record
        "part_poursuite_etudes": _safe_ratio(record.get("part_en_poursuite_d_etudes")),
        "part_emploi_6_mois_post": _safe_ratio(record.get("part_en_emploi_6_mois_apres_la_sortie")),
        "part_autres_situations": _safe_ratio(record.get("part_des_autres_situations")),
        "taux_contrats_interrompus": _safe_ratio(record.get("taux_contrats_interrompus")),
        "taux_poursuite_etudes": _safe_ratio(record.get("taux_poursuite_etudes")),
        "taux_emploi": _extract_taux_horizons(record),
        "taux_emploi_6_mois_attendu": _safe_ratio(record.get("taux_emploi_6_mois_attendu")),
        "valeur_ajoutee_emploi_6_mois": _safe_ratio(record.get("va_emploi_6_mois")),
    }


def normalize_lycee_pro_all(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_lycee_pro_record(r) for r in raw]


def normalize_cfa_all(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_cfa_record(r) for r in raw]


def save_processed(
    records: list[dict[str, Any]], path: Path,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return path


def collect_inserjeunes(
    max_records: Optional[int] = None,
    save: bool = True,
) -> dict[str, list[dict[str, Any]]]:
    """Pipeline complet : fetch lycée pro + CFA → normalize → save.

    Retourne {"lycee_pro": [...], "cfa": [...]}.
    """
    t0 = time.time()
    print("  [inserjeunes] Fetch lycée pro (formation_fine)…")
    lp_raw = fetch_lycee_pro_records(max_records=max_records)
    print(f"  [inserjeunes] lycée pro {len(lp_raw)} records en {time.time()-t0:.1f}s")

    t1 = time.time()
    print("  [inserjeunes] Fetch CFA…")
    cfa_raw = fetch_cfa_records(max_records=max_records)
    print(f"  [inserjeunes] CFA {len(cfa_raw)} records en {time.time()-t1:.1f}s")

    lp_norm = normalize_lycee_pro_all(lp_raw)
    cfa_norm = normalize_cfa_all(cfa_raw)

    if save:
        save_processed(lp_norm, PROCESSED_LYCEE_PRO_PATH)
        save_processed(cfa_norm, PROCESSED_CFA_PATH)
        print(f"  [inserjeunes] saved → {PROCESSED_LYCEE_PRO_PATH} + {PROCESSED_CFA_PATH}")

    return {"lycee_pro": lp_norm, "cfa": cfa_norm}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingestion Inserjeunes DEPP/DARES")
    parser.add_argument("--max", type=int, default=None)
    args = parser.parse_args()
    result = collect_inserjeunes(max_records=args.max)
    print(f"  [inserjeunes] total : {len(result['lycee_pro'])} lycée pro + {len(result['cfa'])} CFA")
