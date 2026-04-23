"""La Bonne Alternance — API publique France Travail (D10 Axe 1).

Source : https://api.apprentissage.beta.gouv.fr
Docs : https://api.apprentissage.beta.gouv.fr/fr/documentation-technique

Scope élargi ADR-039 : phase (b) réorientation via alternance + apprentissage.

**Auth** : nécessite un token Bearer via data.gouv.fr (habilitation légère,
délai ~48h pas 24-48h comme France Travail ROME). Procédure dans
`docs/TODO_MATTEO_APIS.md` §5.

Env vars attendues :
    LBA_API_TOKEN=<token_bearer>

Sans credentials, toute fonction lève `LabonneAlternanceCredentialsMissing`.

**Endpoints cibles** :
- `/formations` : formations en alternance (BTS / BUT / Licence pro /
  Master pro) par RNCP / ROME / géographie.
- `/jobs` : offres d'emploi en alternance temps quasi-réel (225k actives).

Scaffold-only : activation dès que `LBA_API_TOKEN` arrive dans `.env`.
Tests mockés couvrent le flux d'auth + endpoints.
"""
from __future__ import annotations

import os
import time
from typing import Any, Optional

import requests

from src.eval.rate_limit import RateLimiter


BASE_URL = "https://api.apprentissage.beta.gouv.fr"
FORMATIONS_ENDPOINT = f"{BASE_URL}/api/v1/formations"
JOBS_ENDPOINT = f"{BASE_URL}/api/v1/jobs"

# 5-20 req/s selon endpoint — on reste safe à 120 RPM (2 RPS).
DEFAULT_RPM = 120


class LabonneAlternanceError(Exception):
    """Base pour toute erreur côté client Bonne Alternance."""


class LabonneAlternanceCredentialsMissing(LabonneAlternanceError):
    """Token `LBA_API_TOKEN` absent ou vide dans `.env`.

    Cf `docs/TODO_MATTEO_APIS.md` §5 pour l'habilitation data.gouv.fr.
    """


def _get_token() -> str:
    tok = os.environ.get("LBA_API_TOKEN", "").strip()
    if not tok:
        raise LabonneAlternanceCredentialsMissing(
            "LBA_API_TOKEN absent dans .env. "
            "Cf docs/TODO_MATTEO_APIS.md §5 pour l'habilitation."
        )
    return tok


class LabonneAlternanceClient:
    """Client minimal La Bonne Alternance (apprentissage.beta.gouv.fr).

    Usage typique (post-token) :

        client = LabonneAlternanceClient()
        forms = client.search_formations(rome="M1844", departement="75")
        jobs = client.search_jobs(rome_codes=["M1844", "M1819"], geo="75")
    """

    def __init__(
        self,
        session: Optional[requests.Session] = None,
        rate_limiter: Optional[RateLimiter] = None,
        rpm: int = DEFAULT_RPM,
    ):
        self._session = session or requests.Session()
        self._limiter = rate_limiter or RateLimiter(max_per_minute=rpm)

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {_get_token()}",
            "Accept": "application/json",
        }

    def search_formations(
        self,
        rome: Optional[str] = None,
        rncp: Optional[str] = None,
        departement: Optional[str] = None,
        niveau: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """GET /formations — recherche formations en alternance.

        Filtres acceptés : rome code, rncp code, département (code postal
        ou INSEE), niveau (3, 4, 5, 6, 7). Au moins un filtre recommandé.
        """
        self._limiter.acquire()
        params: dict[str, Any] = {"limit": limit}
        if rome:
            params["rome"] = rome
        if rncp:
            params["rncp"] = rncp
        if departement:
            params["departement"] = departement
        if niveau:
            params["niveau"] = niveau
        resp = self._session.get(
            FORMATIONS_ENDPOINT, headers=self._auth_headers(), params=params, timeout=30
        )
        resp.raise_for_status()
        payload = resp.json()
        if isinstance(payload, list):
            return payload
        return payload.get("formations") or payload.get("resultats") or []

    def search_jobs(
        self,
        rome_codes: Optional[list[str]] = None,
        geo: Optional[str] = None,
        rayon_km: int = 30,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """GET /jobs — offres alternance temps quasi-réel.

        `geo` = code postal ou INSEE. `rayon_km` = rayon de recherche autour.
        """
        self._limiter.acquire()
        params: dict[str, Any] = {"limit": limit, "rayon": rayon_km}
        if rome_codes:
            params["romes"] = ",".join(rome_codes)
        if geo:
            params["insee"] = geo
        resp = self._session.get(
            JOBS_ENDPOINT, headers=self._auth_headers(), params=params, timeout=30
        )
        resp.raise_for_status()
        payload = resp.json()
        if isinstance(payload, list):
            return payload
        return payload.get("jobs") or payload.get("resultats") or []


# --- Normalisation (scaffold) ---


def normalize_formation(record: dict[str, Any]) -> dict[str, Any]:
    """Transforme une formation alternance LBA en fiche OrientIA (phase b)."""
    return {
        "source": "labonnealternance",
        "phase": "reorientation",  # ADR-039 phase (b)
        "id_lba": record.get("id") or record.get("_id"),
        "intitule": record.get("intitule_long") or record.get("intitule") or "",
        "etablissement": record.get("etablissement_formateur_entreprise_raison_sociale")
            or record.get("etablissement_formateur_raison_sociale")
            or record.get("etablissement"),
        "ville": record.get("etablissement_formateur_localite") or record.get("ville"),
        "departement": record.get("etablissement_formateur_code_postal", "")[:2]
            or record.get("departement"),
        "rncp": record.get("rncp_code") or record.get("rncp"),
        "rome_codes": record.get("romes") or [],
        "niveau": record.get("niveau") or record.get("niveau_europeen"),
        "duree": record.get("duree"),
        "rythme": record.get("rythme_alternance"),
        "modalite": "alternance",
    }


def normalize_job_offer(record: dict[str, Any]) -> dict[str, Any]:
    """Transforme une offre alternance LBA en contexte insertion pour
    une fiche formation (enrichissement latéral, pas fiche principale)."""
    return {
        "source": "labonnealternance",
        "type": "offre_alternance",
        "id_offre": record.get("id"),
        "intitule": record.get("title") or record.get("intitule"),
        "entreprise": record.get("company_name") or record.get("entreprise"),
        "rome_code": record.get("rome_code"),
        "lieu": record.get("place") or record.get("lieu"),
        "date_debut": record.get("start_date") or record.get("date_debut"),
        "duree_contrat_mois": record.get("duration") or record.get("duree_mois"),
    }
