"""Marché du travail France Travail v1 (ADR-042 / ADR-043).

Source : `https://api.francetravail.io/partenaire/marche-du-travail/v1`
Rate limit officiel : 10 RPS.

Apports OrientIA (phase c "où exercer ce métier") :
- Tension marché offres/demandeurs par ROME × région/dept/bassin
- Indicateur Dares
- Difficultés recrutement

Prérequis activation côté Matteo : scope `api_marchedutravailv1` coché dans
son app OrientIA dashboard France Travail (procédure §1 TODO_MATTEO_APIS.md).

Scaffold uniquement tant que scope pas activé — toute méthode lève
`FranceTravailScopeInvalid` explicite.
"""
from __future__ import annotations

from typing import Any, Optional

from src.collect.ft_base import FranceTravailClient


class MarcheTravailClient(FranceTravailClient):
    API_NAME = "marche-travail"
    SCOPE = "api_marchedutravailv1"  # À CONFIRMER via dropdown dashboard FT
    BASE_URL = "https://api.francetravail.io/partenaire/marche-du-travail/v1"
    DEFAULT_RPM = 500  # 10 RPS officiel = 600 RPM, marge 17%

    # Les endpoints exacts sont à confirmer post-activation scope + swagger.
    # Endpoints candidats basés sur documentation FT :

    def get_tensions(
        self,
        code_rome: Optional[str] = None,
        region: Optional[str] = None,
        departement: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """GET indicateurs de tension marché emploi.

        Filtre par code_rome / region / departement. Sans filtre = national.
        Retourne liste de records {rome, geo, tension_score, offres, demandeurs}.
        """
        params: dict[str, Any] = {}
        if code_rome:
            params["codeROME"] = code_rome
        if region:
            params["region"] = region
        if departement:
            params["departement"] = departement
        payload = self._get("/tensions", params=params)
        return payload if isinstance(payload, list) else payload.get("tensions", [])

    def get_indicateurs_recrutement(
        self,
        code_rome: Optional[str] = None,
        code_bassin: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """GET indicateurs difficultés recrutement par bassin emploi."""
        params: dict[str, Any] = {}
        if code_rome:
            params["codeROME"] = code_rome
        if code_bassin:
            params["codeBassin"] = code_bassin
        payload = self._get("/difficultes-recrutement", params=params)
        return payload if isinstance(payload, list) else payload.get("indicateurs", [])

    def get_offres_agregees(
        self,
        code_rome: Optional[str] = None,
        region: Optional[str] = None,
    ) -> dict[str, Any]:
        """GET stats agrégées offres d'emploi disponibles par ROME × région."""
        params: dict[str, Any] = {}
        if code_rome:
            params["codeROME"] = code_rome
        if region:
            params["region"] = region
        return self._get("/offres-agregees", params=params)


# --- Normalisation (scaffold — à brancher après première ingestion live) ---


def normalize_tension(record: dict[str, Any]) -> dict[str, Any]:
    """Normalise un record tension marché en enrichissement OrientIA.

    À appliquer côté `merge.py:attach_market_indicators(fiches)` post-S+2 pour
    enrichir chaque fiche formation avec `marche_travail.tension_score` par ROME.
    """
    return {
        "source": "ft_marche_travail",
        "code_rome": record.get("codeROME"),
        "region": record.get("region"),
        "departement": record.get("departement"),
        "tension_score": record.get("tensionScore") or record.get("tension"),
        "offres_actives": record.get("offresActives"),
        "demandeurs_emploi": record.get("demandeursEmploi"),
        "periode": record.get("periode"),
    }
