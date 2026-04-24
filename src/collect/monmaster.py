"""Ingestion MonMaster (data.enseignementsup-recherche.gouv.fr) — D8 Axe 1.

Source : https://data.enseignementsup-recherche.gouv.fr (Opendatasoft API REST).
Dataset `fr-esr-mon_master` — campagne MonMaster 2025 (16 257 parcours).

Accès **public sans authentification** (Licence Etalab 2.0, redistribution OK).

Couverture scope élargi phase (c) — masters universitaires.
Complémentaire de `parcoursup.py` (phase a) et `rncp.py` (phases b-c
certifications hors voie classique).

Pattern : download paginé raw → normalisation vers schéma OrientIA
→ save `data/processed/monmaster_formations.json`.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Iterator, Optional

import requests

from src.eval.rate_limit import RateLimiter


BASE_URL = (
    "https://data.enseignementsup-recherche.gouv.fr/api/explore/v2.1/catalog/"
    "datasets/fr-esr-mon_master/records"
)
# Endpoint bulk-export — contourne le cap offset=10000 de /records.
# Opendatasoft v2.1 streame l'intégralité du dataset en une requête JSON.
EXPORT_URL = (
    "https://data.enseignementsup-recherche.gouv.fr/api/explore/v2.1/catalog/"
    "datasets/fr-esr-mon_master/exports/json"
)
DEFAULT_LIMIT = 100  # max per call sur Opendatasoft v2.1
DEFAULT_RPM = 120  # Opendatasoft standard = 10k req/day, on reste safe

RAW_DIR = Path("data/raw/monmaster")
PROCESSED_PATH = Path("data/processed/monmaster_formations.json")


def fetch_records_page(
    offset: int = 0,
    limit: int = DEFAULT_LIMIT,
    session: Optional[requests.Session] = None,
) -> dict[str, Any]:
    """Fetch une page de records MonMaster. Retourne le payload JSON brut.

    Format réponse Opendatasoft v2.1 :
      {"total_count": int, "results": [record, ...]}
    """
    sess = session or requests.Session()
    params = {"limit": limit, "offset": offset}
    resp = sess.get(BASE_URL, params=params, timeout=60)
    resp.raise_for_status()
    return resp.json()


def fetch_all_records(
    limit_per_call: int = DEFAULT_LIMIT,
    max_records: Optional[int] = None,
    rate_limiter: Optional[RateLimiter] = None,
    session: Optional[requests.Session] = None,
) -> Iterator[dict[str, Any]]:
    """Itérateur paginé sur tous les records MonMaster.

    Passer `max_records` pour limiter (utile dev/test). None = tout le corpus
    (~16k records, ~2-3 min avec rate limit 120 RPM).

    ⚠️ Cap offset=10000 sur l'endpoint `/records` (Opendatasoft v2.1). Pour
    dumps complets >10k records, utiliser `fetch_export_bulk()` à la place.
    """
    limiter = rate_limiter or RateLimiter(max_per_minute=DEFAULT_RPM)
    sess = session or requests.Session()
    offset = 0
    total_fetched = 0
    total_count = None

    while True:
        limiter.acquire()
        page = fetch_records_page(offset=offset, limit=limit_per_call, session=sess)
        if total_count is None:
            total_count = page.get("total_count", 0)
        results = page.get("results", [])
        if not results:
            return
        for rec in results:
            if max_records is not None and total_fetched >= max_records:
                return
            yield rec
            total_fetched += 1
        offset += limit_per_call
        if offset >= total_count or offset >= 10000:
            # Hard cap Opendatasoft v2.1 sur /records — bascule vers export
            return


def fetch_export_bulk(
    session: Optional[requests.Session] = None,
    timeout: int = 300,
) -> list[dict[str, Any]]:
    """Fetch TOUS les records MonMaster en une seule requête via /exports/json.

    Contourne le cap offset=10000 de l'endpoint /records. Streaming JSON
    array, payload ~5-15 MB pour les 16k records MonMaster 2025.

    Usage pour corpus complet. Pour dev/test small → `fetch_all_records(max_records=N)`.
    """
    sess = session or requests.Session()
    resp = sess.get(EXPORT_URL, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def save_raw_records(records: list[dict[str, Any]], path: Path = None) -> Path:
    """Dump la liste complète de records au format JSON sur disque.

    Gitignored par défaut (`data/raw/*` dans .gitignore).
    """
    target = path or (RAW_DIR / "mon_master_records_2025.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return target


# --- Normalisation vers schéma OrientIA ---


def _parse_ville(lieux: str) -> str:
    """Extrait la ville depuis le champ `lieux` brut.

    Format typique : "Université X - VILLE (dept)|Campus Y - VILLE (dept)".
    On prend la première ville avant le pipe.
    """
    if not lieux:
        return ""
    first = lieux.split("|")[0]
    # Pattern : "XXX - VILLE (dept)"
    if " - " in first:
        tail = first.rsplit(" - ", 1)[-1]
        # Retirer la partie "(dept)"
        if "(" in tail:
            tail = tail.rsplit("(", 1)[0]
        return tail.strip()
    return first.strip()


def _compute_taux_admission(record: dict[str, Any]) -> Optional[float]:
    """Calcule le taux d'admission = n_accept_total / n_can_pp (procedure principale).

    None si numérateur ou dénominateur manquant/zéro.

    Clampé à [0, 1] : certains records MonMaster sources ont
    `n_accept_total > n_can_pp` (procédure complémentaire ajoutant des
    acceptés hors liste principale — cf 6 cas "LANGUES LITTERATURES"
    identifiés dans l'audit 2026-04-23). On plafonne pour garder la
    sémantique "proba d'admission d'un candidat PP" dans [0, 1]. Les
    champs bruts `n_candidats_pp` / `n_acceptes_total` restent exposés
    dans la fiche pour un recalcul alternatif si besoin.
    """
    n_can = record.get("n_can_pp") or 0
    n_accept = record.get("n_accept_total") or 0
    if n_can <= 0:
        return None
    return min(1.0, n_accept / n_can)


def _extract_profil_admis_stats(record: dict[str, Any]) -> dict[str, Any]:
    """Stats de profil d'entrée admis — qui est pris dans ce master.

    Utilise les champs `pct_accept_<profil>` (lg3, lp3, but3, master, autre,
    noninscri) déjà calculés côté API. Source de vérité pour "quel bac+3 a
    ses chances ici ?" sans que le LLM invente.
    """
    return {
        "pct_lg3": record.get("pct_accept_lg3"),        # Licence générale L3
        "pct_lp3": record.get("pct_accept_lp3"),        # Licence pro
        "pct_but3": record.get("pct_accept_but3"),      # BUT
        "pct_master": record.get("pct_accept_master"),  # Déjà master (M1→M2)
        "pct_autre": record.get("pct_accept_autre"),    # Autres diplômes
        "pct_femme": record.get("pct_accept_femme"),    # Ratio filles
        "pct_etab": record.get("pct_accept_etab"),      # Même établissement
        "pct_lieu_acad": record.get("pct_accept_lieu_acad"),  # Même académie
    }


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    """Transforme un record MonMaster brut en fiche OrientIA.

    Schéma de sortie (aligné avec les autres `src/collect/*.py`) :
        source, phase, nom, etablissement, ville, academie, region,
        niveau, mention, parcours, discipline, secteur_discipline,
        modalite_enseignement, alternance, capacite, n_candidats,
        n_acceptes, taux_admission, profil_admis, id_mon_master.

    `phase = "master"` explicite → facilite la répartition 33/33/34
    scope élargi (ADR-039).
    """
    return {
        "source": "monmaster",
        "phase": "master",  # scope élargi : phase (c)
        "nom": f"{record.get('mention', '')} — {record.get('parcours', '')}".strip(" —"),
        "etablissement": record.get("eta_nom") or "",
        "ville": _parse_ville(record.get("lieux", "")),
        "academie": record.get("acad_lib") or record.get("lieu_acad_lib"),
        "region": record.get("acad_reg_lib") or record.get("lieu_reg_acad_lib"),
        "niveau": "bac+5",  # MonMaster = bac+5 uniquement
        "mention": record.get("mention"),
        "parcours": record.get("parcours"),
        "discipline": record.get("disci_lib"),
        "secteur_discipline": record.get("secteur_disci_lib"),
        "modalite_enseignement": record.get("modalite_enseignement") or [],
        "alternance": record.get("alternance") == "1",
        "capacite": record.get("col"),
        "n_candidats_pp": record.get("n_can_pp"),
        "n_acceptes_total": record.get("n_accept_total"),
        "rang_dernier_appele": record.get("rang_dernier_appele_pp"),
        "taux_admission": _compute_taux_admission(record),
        "profil_admis": _extract_profil_admis_stats(record),
        "id_mon_master": {
            "ifc": record.get("ifc"),
            "inm": record.get("inm"),
            "inmp": record.get("inmp"),
            "session": record.get("session"),
            "id_paysage": record.get("id_paysage"),
        },
    }


def normalize_all(raw_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Applique `normalize_record` à toute la liste brute."""
    return [normalize_record(r) for r in raw_records]


def _session_sort_key(fiche: dict[str, Any]) -> str:
    """Clé de tri : chaîne session (lex ok car années à 4 chiffres).

    Retourne chaîne vide si session absente → trié avant toute valeur
    présente. `_dedupe_keep_latest_session` préfère session non-vide.
    """
    id_mm = fiche.get("id_mon_master") or {}
    return str(id_mm.get("session") or "")


def dedupe_keep_latest_session(
    fiches: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Dédoublonne par `id_mon_master.ifc` en conservant la session la plus
    récente (ADR-044).

    Pourquoi : l'API MonMaster expose 2 snapshots annuels par formation
    (sessions 2024 + 2025 en avril 2026). Pour le RAG c'est la dernière
    année qui compte (fraîcheur données > série temporelle). Un ADR
    séparé (ADR-044) capture ce choix.

    Conserve l'ordre de première apparition pour stabilité des diffs.
    """
    latest: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for fiche in fiches:
        id_mm = fiche.get("id_mon_master") or {}
        ifc = id_mm.get("ifc")
        if not ifc:
            # Pas d'IFC → clé unique de fallback, pas de dédup possible
            key = f"_no_ifc_{id(fiche)}"
            latest[key] = fiche
            order.append(key)
            continue
        if ifc not in latest:
            order.append(ifc)
            latest[ifc] = fiche
        else:
            if _session_sort_key(fiche) > _session_sort_key(latest[ifc]):
                latest[ifc] = fiche
    return [latest[k] for k in order]


def save_processed(
    normalized: list[dict[str, Any]], path: Path = PROCESSED_PATH
) -> Path:
    """Dump les fiches normalisées en JSON. Commité (pas dans .gitignore)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return path


# --- Entrée principale ---


def collect_monmaster_fiches(
    max_records: Optional[int] = None,
    save_raw: bool = True,
    save_normalized: bool = True,
    use_bulk_export: bool = True,
) -> list[dict[str, Any]]:
    """Pipeline end-to-end : download → normalize → save.

    Usage CLI : `python -m src.collect.monmaster`
    Arg `max_records` pour dev/test (None = corpus complet).
    Arg `use_bulk_export` : True pour corpus complet (via /exports/json,
    contourne cap offset=10000), False pour pagination classique.
    """
    if max_records is None and use_bulk_export:
        print("  [monmaster] Bulk export /exports/json (tout le corpus)...")
        raw = fetch_export_bulk()
    else:
        raw = list(fetch_all_records(max_records=max_records))
    if save_raw:
        path = save_raw_records(raw)
        print(f"  [monmaster] {len(raw)} records raw sauvés → {path}")
    normalized = normalize_all(raw)
    before_dedup = len(normalized)
    normalized = dedupe_keep_latest_session(normalized)
    removed = before_dedup - len(normalized)
    if removed:
        print(
            f"  [monmaster] dedup ADR-044 : {removed} snapshots antérieurs "
            f"écartés ({before_dedup} → {len(normalized)})"
        )
    if save_normalized:
        path = save_processed(normalized)
        print(f"  [monmaster] {len(normalized)} fiches normalisées → {path}")
    return normalized


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingestion MonMaster D8")
    parser.add_argument(
        "--max", type=int, default=None, help="Limite records (dev/test). None = tout."
    )
    parser.add_argument(
        "--no-save", action="store_true", help="Skip écriture fichiers (dry-run)"
    )
    args = parser.parse_args()
    fiches = collect_monmaster_fiches(
        max_records=args.max,
        save_raw=not args.no_save,
        save_normalized=not args.no_save,
    )
    print(f"  [monmaster] total fiches produites : {len(fiches)}")
