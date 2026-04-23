"""France Travail ROME 4.0 live API client (scaffold — S+1 Axe 1 D3).

Complémentaire de `src/collect/rome.py` (lecture ZIP offline). Cible les
endpoints LIVE qui exposent des données non-présentes dans le zip :
- tension marché de l'emploi par métier/région
- appellations principales
- enrichissements récents (post-release v460 d'avril 2025)

OAuth2 client_credentials flow — ne s'active qu'une fois les credentials
`FT_CLIENT_ID` + `FT_CLIENT_SECRET` présents dans `.env`. En leur absence,
toute fonction lève `RomeApiCredentialsMissing` avec un message clair qui
pointe vers `docs/TODO_MATTEO_APIS.md`.

Scaffold-only : le module est écrit pour démarrer instantanément quand
les clés arrivent (J+1/J+2 probable), pas pour être appelé live avant.

Réf : STRATEGIE_VISION_2026-04-16.md §5 Axe 1 D3, ADR-038.
"""
from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from typing import Any, Optional

import requests

from src.eval.rate_limit import RateLimiter


# --- Endpoints France Travail (docs : https://francetravail.io/data/api) ---

OAUTH_TOKEN_URL = (
    "https://entreprise.francetravail.fr/connexion/oauth2/"
    "access_token?realm=%2Fpartenaire"
)
METIERS_BASE_URL = "https://api.francetravail.io/partenaire/rome-metiers/v1/metiers/metier"
FICHES_METIERS_BASE_URL = (
    "https://api.francetravail.io/partenaire/rome-fiches-metiers/v1/fiches-rome/fiche-metier"
)

# Scopes ROME 4.0 corrects (activés côté app par Jarvis 2026-04-23-1212).
# Les 4 APIs ROME 4.0 : Métiers + Fiches métiers + Compétences + Contextes.
ROME_SCOPES = (
    "api_rome-metiersv1 api_rome-fiches-metiersv1 "
    "api_rome-competencesv1 api_rome-contextes-travailv1 "
    "nomenclatureRome"
)

# Rate limit par défaut — France Travail ROME 4.0 = 1 RPS officiel.
# 50 RPM = ~0.83 RPS : marge 17% sous le cap pour absorber les bursts
# sans se faire rate-limit par le proxy France Travail.
# Si on passe aux APIs Anotéa (8 RPS) ou Marché du travail (10 RPS),
# override via `RomeApiClient(rpm=480)` ou `rpm=600`.
DEFAULT_RPM = 50


# --- Exceptions ---


class RomeApiError(Exception):
    """Base class pour toute erreur côté client ROME API."""


class RomeApiCredentialsMissing(RomeApiError):
    """Credentials OAuth2 absents ou vides dans .env."""


class RomeApiAuthError(RomeApiError):
    """Échec OAuth2 (401/403) après credentials présents."""


# --- Token manager ---


@dataclass
class _TokenState:
    access_token: Optional[str] = None
    expires_at: float = 0.0


def _get_credentials() -> tuple[str, str]:
    client_id = os.environ.get("FT_CLIENT_ID", "").strip()
    client_secret = os.environ.get("FT_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise RomeApiCredentialsMissing(
            "FT_CLIENT_ID/FT_CLIENT_SECRET absents dans .env. "
            "Cf docs/TODO_MATTEO_APIS.md pour le signup francetravail.io."
        )
    return client_id, client_secret


def _call_with_retry(fn, *args, max_retries: int = 4, **kwargs):
    """Retry exponentiel léger — aligne le pattern `src/eval/runner.py`.

    Retrait volontaire : pas de dépendance cross-module pour garder le
    scaffold self-contained.
    """
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            msg = str(exc)
            exc_name = type(exc).__name__
            is_rate_limit = "429" in msg or "rate" in msg.lower()
            is_5xx = bool(re.search(r"\b5\d{2}\b", msg))
            is_transient = any(
                kw in exc_name for kw in ("Timeout", "Connect", "ReadTimeout")
            )
            if not (is_rate_limit or is_5xx or is_transient) or attempt == max_retries:
                raise
            delay = (15.0 if is_rate_limit else 2.0) * (2 ** attempt)
            time.sleep(delay)
    raise last_exc  # pragma: no cover


class RomeApiClient:
    """Client minimal France Travail ROME 4.0.

    Usage typique (après que FT_CLIENT_ID/SECRET soient dans .env) :

        client = RomeApiClient()
        metier = client.get_metier("M1844")        # Analyste cybersécurité
        matches = client.search_metiers("data engineer")
        fiche = client.get_fiche_metier("M1844")
    """

    def __init__(
        self,
        rate_limiter: Optional[RateLimiter] = None,
        session: Optional[requests.Session] = None,
        rpm: int = DEFAULT_RPM,
    ):
        self._session = session or requests.Session()
        self._limiter = rate_limiter or RateLimiter(max_per_minute=rpm)
        self._token = _TokenState()

    # --- auth ---

    def _ensure_token(self) -> str:
        now = time.time()
        # 30s de marge avant expiration pour éviter les races
        if self._token.access_token and self._token.expires_at > now + 30:
            return self._token.access_token
        client_id, client_secret = _get_credentials()
        data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": ROME_SCOPES,
        }
        self._limiter.acquire()
        resp = _call_with_retry(
            self._session.post, OAUTH_TOKEN_URL, data=data, timeout=30
        )
        if resp.status_code in (401, 403):
            raise RomeApiAuthError(
                f"OAuth2 refusé ({resp.status_code}) — scopes ou credentials invalides. "
                f"Body: {resp.text[:200]}"
            )
        resp.raise_for_status()
        payload = resp.json()
        access = payload.get("access_token")
        if not access:
            raise RomeApiAuthError(f"Token absent du payload : {payload}")
        self._token = _TokenState(
            access_token=access,
            expires_at=now + float(payload.get("expires_in", 1200)),
        )
        return access

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._ensure_token()}",
            "Accept": "application/json",
        }

    # --- endpoints publics (scaffold) ---

    def get_metier(self, code_rome: str) -> dict[str, Any]:
        """GET /metiers/{code_rome} — libellé officiel + granularité.

        Réf : https://francetravail.io/data/api/rome-4-0-metiers
        """
        if not code_rome:
            raise ValueError("code_rome vide")
        self._limiter.acquire()
        resp = _call_with_retry(
            self._session.get,
            f"{METIERS_BASE_URL}/{code_rome}",
            headers=self._auth_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def search_metiers(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """GET /metiers?q=... — recherche full-text sur libellés.

        Utile pour matcher les débouchés d'une formation avec des codes
        ROME pertinents sans hard-coder la table `RELEVANT_ROME_CODES`
        de `rome.py`.
        """
        if not query:
            return []
        self._limiter.acquire()
        resp = _call_with_retry(
            self._session.get,
            METIERS_BASE_URL,
            headers=self._auth_headers(),
            params={"q": query, "nombre": limit},
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()
        # Format réponse France Travail : `{"metiers": [...]}` ou liste directe
        if isinstance(payload, dict):
            return payload.get("metiers") or payload.get("resultats") or []
        return payload

    def get_fiche_metier(self, code_rome: str) -> dict[str, Any]:
        """GET /fiches-rome/{code_rome} — fiche métier détaillée.

        Champs attendus : description, activités, compétences, salaires,
        tension marché — ce que `rome.py` (ZIP) ne fournit pas.
        """
        if not code_rome:
            raise ValueError("code_rome vide")
        self._limiter.acquire()
        resp = _call_with_retry(
            self._session.get,
            f"{FICHES_METIERS_BASE_URL}/{code_rome}",
            headers=self._auth_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    # --- helpers haut-niveau (à brancher S+1/S+2 sur le pipeline merge) ---

    def enrich_fiches_with_debouches(
        self, fiches: list[dict], domain_to_queries: dict[str, list[str]]
    ) -> list[dict]:
        """Pour chaque fiche, injecter des débouchés ROME matchés via search.

        Remplace à terme la table `RELEVANT_ROME_CODES` hard-codée quand
        on étend le scope (master, alternance, etc.). Scaffold — logique
        de fusion à affiner S+1 selon qualité matching search_metiers.
        """
        results: list[dict] = []
        for fiche in fiches:
            domain = fiche.get("domaine")
            if not domain or domain not in domain_to_queries:
                results.append(fiche)
                continue
            matched_codes: list[dict] = []
            for q in domain_to_queries[domain]:
                try:
                    found = self.search_metiers(q, limit=5)
                    matched_codes.extend(found)
                except RomeApiError:
                    continue
            results.append({**fiche, "debouches_rome_live": matched_codes})
        return results
