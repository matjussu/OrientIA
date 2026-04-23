"""ONISEP OpenData formations — ingestion scope élargi 15 domaines (D2 ADR-039).

Source : https://api.opendata.onisep.fr (dataset formations `5fa591127f501`)
Auth : email + password + Application-ID header (OAuth2-like, `src/collect/onisep.py`).

Ce module étend `src/collect/onisep.py` avec un mapping **15 domaines OrientIA →
queries ONISEP**, aligné avec `src/collect/parcoursup.py` EXTENDED_DOMAINS
(ADR-041). Chaque domaine est couvert par 1 à 5 queries (synonymes /
sous-domaines) pour maximiser la récolte sans multiplier les faux positifs.

Dedup : par `(url_onisep, code_rncp)` tuple (unique identifier formation ONISEP),
fallback signature `nom+etablissement+ville` si IDs manquent.

Scope élargi (ADR-039) : couvre toutes les phases (a) initial + (c) master
selon le niveau_de_sortie_indicatif retourné par ONISEP.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

import requests

from src.collect.onisep import (
    authenticate,
    extract_school_from_formation_name,
    fetch_formations,
)


# Mapping domaine OrientIA → queries ONISEP (synonymes/sous-domaines).
# Aligné avec `src/collect/parcoursup.py` DOMAIN_KEYWORDS pour cohérence
# cross-source. Chaque query est une recherche full-text côté ONISEP API.
DOMAIN_QUERIES: dict[str, list[str]] = {
    "cyber": ["cybersécurité"],
    "data_ia": ["intelligence artificielle", "data science", "big data"],
    "sante": ["médecine", "infirmier", "kinésithérapie", "pharmacie", "sage-femme"],
    "droit": ["droit", "notariat", "science politique"],
    "eco_gestion": ["gestion", "commerce", "finance", "management", "comptabilité"],
    "sciences_humaines": ["sociologie", "psychologie", "histoire", "géographie"],
    "langues": ["langues étrangères appliquées", "LLCE", "traduction"],
    "lettres_arts": ["lettres", "arts plastiques", "design", "architecture"],
    "sport": ["STAPS", "sport"],
    "sciences_fondamentales": ["mathématique", "physique", "chimie", "biologie"],
    "ingenierie_industrielle": ["ingénieur", "mécanique", "électronique", "génie civil"],
    "communication": ["communication", "journalisme"],
    "education": ["enseignement", "MEEF"],
    "agriculture": ["agriculture", "agronomie"],
    "tourisme_hotellerie": ["tourisme", "hôtellerie"],
}

RAW_DIR = Path("data/raw/onisep_extended")
PROCESSED_PATH = Path("data/processed/onisep_formations_extended.json")


def _map_niveau(niveau_sortie: str | None) -> Optional[str]:
    """Map ONISEP 'bac + N' → OrientIA 'bac+N'."""
    if not niveau_sortie:
        return None
    normalized = niveau_sortie.replace(" ", "").lower()
    if normalized in ("bac+2", "bac+3", "bac+5", "bac+8"):
        return normalized
    return None


def _infer_phase(niveau: Optional[str]) -> str:
    """ADR-039 : phase selon niveau."""
    return "master" if niveau in ("bac+5", "bac+8") else "initial"


def normalize_onisep_record(
    record: dict[str, Any],
    domaine: str,
) -> dict[str, Any]:
    """Transforme un record ONISEP API en fiche OrientIA (compat merge.py)."""
    nom = (record.get("libelle_formation_principal") or "").strip()
    etab = extract_school_from_formation_name(nom) or ""
    niveau = _map_niveau(record.get("niveau_de_sortie_indicatif"))
    return {
        "source": "onisep",
        "phase": _infer_phase(niveau),
        "domaine": domaine,
        "nom": nom,
        "etablissement": etab,
        "ville": "",  # ONISEP formations dataset n'a pas de ville
        "rncp": record.get("code_rncp") or None,
        "url_onisep": record.get("url_et_id_onisep") or None,
        "type_diplome": record.get("libelle_type_formation") or None,
        "sigle_formation": record.get("sigle_formation") or None,
        "duree": record.get("duree") or None,
        "tutelle": record.get("tutelle") or None,
        "niveau": niveau,
        "niveau_certification": record.get("niveau_de_certification") or None,
        "code_nsf": record.get("code_nsf") or None,
        "statut": None,
    }


def _signature(fiche: dict[str, Any]) -> str:
    """Clé de dedup : url_onisep prioritaire, fallback (nom, rncp, etab)."""
    url = (fiche.get("url_onisep") or "").strip()
    if url:
        return f"url:{url}"
    rncp = (fiche.get("rncp") or "").strip()
    if rncp:
        return f"rncp:{rncp}"
    nom = (fiche.get("nom") or "").strip().lower()
    etab = (fiche.get("etablissement") or "").strip().lower()
    return f"{nom}|{etab}"


def collect_onisep_formations_extended(
    domains: Optional[list[str]] = None,
    size: int = 500,
) -> list[dict[str, Any]]:
    """Ingère les formations ONISEP pour chaque domaine (scope élargi 15).

    Auth via env vars : `ONISEP_EMAIL`, `ONISEP_PASSWORD`, `ONISEP_APP_ID`.
    Dedup cross-queries (une formation capturée par 2 queries → 1 seule fiche).
    """
    email = os.environ.get("ONISEP_EMAIL", "").strip()
    password = os.environ.get("ONISEP_PASSWORD", "").strip()
    app_id = os.environ.get("ONISEP_APP_ID", "").strip()
    if not (email and password and app_id):
        raise ValueError(
            "ONISEP_EMAIL / ONISEP_PASSWORD / ONISEP_APP_ID manquants dans .env. "
            "Cf docs/TODO_MATTEO_APIS.md §2."
        )

    target_domains = domains or list(DOMAIN_QUERIES.keys())
    token = authenticate(email, password)
    print(f"  [onisep_ext] Token OK, {len(target_domains)} domaines à fetch")

    all_fiches: list[dict[str, Any]] = []
    seen: set[str] = set()
    per_domain_counts: dict[str, int] = {}

    for domain in target_domains:
        if domain not in DOMAIN_QUERIES:
            print(f"  [onisep_ext] ⚠️ domain {domain} inconnu, skip")
            continue
        domain_count = 0
        for query in DOMAIN_QUERIES[domain]:
            try:
                results = fetch_formations(token, app_id, query, size=size)
            except Exception as exc:
                print(f"  [onisep_ext] {domain}/{query}: {type(exc).__name__}: {str(exc)[:100]}")
                continue
            for r in results:
                fiche = normalize_onisep_record(r, domaine=domain)
                if not fiche["nom"]:
                    continue
                sig = _signature(fiche)
                if sig in seen:
                    continue
                seen.add(sig)
                all_fiches.append(fiche)
                domain_count += 1
        per_domain_counts[domain] = domain_count
        print(f"  [onisep_ext] {domain}: {domain_count} fiches")

    return all_fiches, per_domain_counts


def save_processed(
    fiches: list[dict[str, Any]], path: Path = PROCESSED_PATH
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(fiches, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return path


if __name__ == "__main__":
    fiches, counts = collect_onisep_formations_extended()
    print()
    print(f"  [onisep_ext] TOTAL : {len(fiches)} fiches uniques sur {len(counts)} domaines")
    print(f"  [onisep_ext] Répartition : {counts}")
    save_processed(fiches)
    print(f"  [onisep_ext] Sauvé → {PROCESSED_PATH}")
