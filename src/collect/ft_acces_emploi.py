"""Accès à l'emploi des demandeurs d'emploi France Travail v1 (ADR-042).

Source : `https://api.francetravail.io/partenaire/acces-a-l-emploi-des-demandeurs-d-emploi/v1`
Rate limit officiel : 10 RPS.

**Apports OrientIA (phase c benchmark tous profils marché)** :
- Taux accès emploi 6m par ROME × région × catégorie DE (A/B) × âge (16-25 / 25-50 / 50+)
- Population : ~1.2M demandeurs/trim, seuils anonymisation n≥30-50

Complémentaire de `ft_sortants_formation.py` (cohorte post-formation) et
Céreq (cohorte 3 ans post-diplôme).

Prérequis Matteo : scope `api_acces-a-lemploi-des-demandeurs-demploiv1`
(ou variante, nom exact à confirmer dropdown dashboard).
"""
from __future__ import annotations

from typing import Any, Optional

from src.collect.ft_base import FranceTravailClient


class AccesEmploiClient(FranceTravailClient):
    API_NAME = "acces-emploi"
    SCOPE = "api_acces-a-lemploi-des-demandeurs-demploiv1"  # À CONFIRMER
    BASE_URL = (
        "https://api.francetravail.io/partenaire/acces-a-l-emploi-des-demandeurs-d-emploi/v1"
    )
    DEFAULT_RPM = 500

    def get_taux_acces(
        self,
        code_rome: Optional[str] = None,
        categorie: Optional[str] = None,  # "A" ou "B"
        region: Optional[str] = None,
        tranche_age: Optional[str] = None,  # ex "16-25"
        periode: Optional[str] = None,  # "YYYY-TN"
    ) -> list[dict[str, Any]]:
        """GET taux retour emploi 6m par filtres."""
        params: dict[str, Any] = {}
        if code_rome:
            params["codeROME"] = code_rome
        if categorie:
            params["categorie"] = categorie
        if region:
            params["region"] = region
        if tranche_age:
            params["trancheAge"] = tranche_age
        if periode:
            params["periode"] = periode
        payload = self._get("/taux-acces", params=params)
        return payload if isinstance(payload, list) else payload.get("taux", [])


def normalize_taux_acces(record: dict[str, Any]) -> dict[str, Any]:
    """Normalise record en enrichissement OrientIA (schema aligné Céreq)."""
    return {
        "source": "ft_acces_emploi",
        "code_rome": record.get("codeROME"),
        "categorie_demandeur": record.get("categorie"),
        "region": record.get("region"),
        "tranche_age": record.get("trancheAge"),
        "periode": record.get("periode"),
        "effectif_base": record.get("effectifBase"),
        "taux_emploi_6m": record.get("tauxAccesEmploi6Mois") or record.get("tauxAcces"),
        "duree_moyenne_mois": record.get("dureeMoyenneEmploiAccede"),
        "type_contrat_cdi_pct": record.get("pctCDI"),
    }
