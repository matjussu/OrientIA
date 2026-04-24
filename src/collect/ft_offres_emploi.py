"""Offres d'emploi France Travail v2 (ADR-043 P0).

Source : `https://api.francetravail.io/partenaire/offresdemploi/v2`
Rate limit officiel : 10 RPS (probable).

Apports OrientIA (phase c contexte marché concret) :
- Annonces temps réel FT + partenaires, ~20k+ offres actives
- Filtrage par ROME × région × type contrat (CDI/CDD/Alternance/Stage)
- Complément de `labonnealternance.py` (qui couvre spécifiquement alternance)

Prérequis Matteo : scope `api_offresdemploi-v2` à cocher dans app OrientIA
dashboard FT.
"""
from __future__ import annotations

from typing import Any, Optional

from src.collect.ft_base import FranceTravailClient


class OffresEmploiClient(FranceTravailClient):
    API_NAME = "offres-emploi"
    # Nom de scope compacté (pas de tiret "-v2") — confirmé par probe OAuth2
    # 2026-04-24 + doc publique France Travail. Le nom `api_offresdemploi-v2`
    # (avec tiret) retourne invalid_scope.
    SCOPE = "api_offresdemploiv2"
    BASE_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2"
    DEFAULT_RPM = 500

    def search(
        self,
        code_rome: Optional[str] = None,
        code_departement: Optional[str] = None,
        type_contrat: Optional[str] = None,  # CDI / CDD / MIS / SAI / DDI / LIB / FRA
        range_start: int = 0,
        range_end: int = 149,  # max 150/page
    ) -> dict[str, Any]:
        """GET /offres/search — recherche offres emploi actives.

        Retour : dict {resultats: [...], filtresPossibles: {...}}.
        Pagination via header Content-Range ou param `range`.
        """
        params: dict[str, Any] = {"range": f"{range_start}-{range_end}"}
        if code_rome:
            params["codeROME"] = code_rome
        if code_departement:
            params["departement"] = code_departement
        if type_contrat:
            params["typeContrat"] = type_contrat
        return self._get("/offres/search", params=params)

    def get_offre(self, offre_id: str) -> dict[str, Any]:
        """GET détail offre par ID."""
        if not offre_id:
            raise ValueError("offre_id vide")
        return self._get(f"/offres/{offre_id}")


def normalize_offre(record: dict[str, Any]) -> dict[str, Any]:
    """Normalise une offre en fiche contextuelle OrientIA.

    Schema aligné `labonnealternance.normalize_job_offer` pour join possible
    (type='offre_emploi' vs 'offre_alternance').
    """
    return {
        "source": "ft_offres_emploi",
        "type": "offre_emploi",
        "id_offre": record.get("id"),
        "intitule": record.get("intitule"),
        "description": record.get("description"),
        "code_rome": record.get("romeCode") or (record.get("metier") or {}).get("code"),
        "libelle_rome": (record.get("metier") or {}).get("libelle"),
        "entreprise": (record.get("entreprise") or {}).get("nom"),
        "secteur": record.get("secteurActiviteLibelle"),
        "lieu": (record.get("lieuTravail") or {}).get("libelle"),
        "code_postal": (record.get("lieuTravail") or {}).get("codePostal"),
        "type_contrat": record.get("typeContrat"),
        "salaire": (record.get("salaire") or {}).get("libelle"),
        "date_creation": record.get("dateCreation"),
        "experience": record.get("experienceExige"),
        "date_actualisation": record.get("dateActualisation"),
    }
