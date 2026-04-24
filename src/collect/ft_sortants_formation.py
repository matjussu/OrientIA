"""Sortants de formation et accès à l'emploi France Travail v1 (ADR-043).

Source : `https://api.francetravail.io/partenaire/sortants-formation-acces-emploi/v1`
Rate limit officiel : 10 RPS.

**Focus scope élargi ADR-039** : cohorte **post-formation spécifique**,
complémentaire de `ft_acces_emploi.py` (tous demandeurs) et Céreq (cohorte
3 ans). Bridge direct post-formation.

Apports OrientIA (phase c "insertion jeunes diplômés") :
- Taux accès emploi 6m par ROME × bassin × niveau formation
- Cohort-specific : sortants formation (trim glissant) — proche profil Céreq

Prérequis Matteo : scope `api_sortants-formation-acces-emploiv1` (ou variante,
nom exact à confirmer via dropdown dashboard).
"""
from __future__ import annotations

from typing import Any, Optional

from src.collect.ft_base import FranceTravailClient


class SortantsFormationClient(FranceTravailClient):
    API_NAME = "sortants-formation"
    # Nom testé 2026-04-24 : invalid_scope. Variante compactée
    # api_sortantsformationaccesemploiv1 également invalid → probable
    # habilitation partenariat FT requise (pas juste case à cocher) — action
    # Matteo dashboard partenaires.
    SCOPE = "api_sortants-formation-acces-emploiv1"  # habilitation pending
    BASE_URL = (
        "https://api.francetravail.io/partenaire/sortants-formation-acces-emploi/v1"
    )
    DEFAULT_RPM = 500  # 10 RPS

    def get_insertion_post_formation(
        self,
        code_rome: Optional[str] = None,
        niveau_formation: Optional[str] = None,
        bassin_emploi: Optional[str] = None,
        annee: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """GET stats insertion emploi 6m post-formation.

        Filtre par ROME × niveau formation (ex "bac+3") × bassin emploi × année.
        """
        params: dict[str, Any] = {}
        if code_rome:
            params["codeROME"] = code_rome
        if niveau_formation:
            params["niveauFormation"] = niveau_formation
        if bassin_emploi:
            params["bassinEmploi"] = bassin_emploi
        if annee:
            params["annee"] = annee
        payload = self._get("/insertion", params=params)
        return payload if isinstance(payload, list) else payload.get("insertions", [])


def normalize_insertion(record: dict[str, Any]) -> dict[str, Any]:
    """Normalise record insertion en enrichissement OrientIA.

    Format aligné avec Céreq (même schema `taux_emploi_6m`, `taux_cdi`, etc.)
    pour permettre merge dans `attach_cereq_insertion()` existant ou équivalent.
    """
    return {
        "source": "ft_sortants_formation",
        "code_rome": record.get("codeROME"),
        "niveau_formation": record.get("niveauFormation"),
        "bassin_emploi": record.get("bassinEmploi"),
        "region": record.get("region"),
        "annee": record.get("annee"),
        "effectif_sortants": record.get("effectifSortants"),
        "taux_emploi_6m": record.get("tauxAccesEmploi6Mois"),
        "taux_cdi": record.get("tauxCDI"),
        "delai_median_mois": record.get("delaiMedianEmploi"),
    }
