"""Base OAuth2 France Travail — factorise auth + retry + rate limit.

Partagé par les clients des 4 APIs FT non-ROME (Marché du travail, Sortants
de formation, Accès à l'emploi demandeurs, Offres d'emploi). Pour ROME 4.0,
`src/collect/rome_api.py` reste indépendant (il préexistait avec ses
spécificités scopes).

Chaque client dérivé définit :
- `API_NAME` (pour logs)
- `SCOPE` OAuth2 à demander
- `BASE_URL` endpoint principal
- `DEFAULT_RPM` selon rate limit de l'API

Utilise :
    class MarcheTravailClient(FranceTravailClient):
        API_NAME = "marche-travail"
        SCOPE = "api_marchedutravailv1"
        BASE_URL = "https://api.francetravail.io/partenaire/marche-du-travail/v1"
        DEFAULT_RPM = 500  # 10 RPS officiel
"""
from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from typing import Any, ClassVar, Optional

import requests

from src.eval.rate_limit import RateLimiter


OAUTH_TOKEN_URL = (
    "https://entreprise.francetravail.fr/connexion/oauth2/"
    "access_token?realm=%2Fpartenaire"
)


class FranceTravailError(Exception):
    """Erreur côté client FT (non-ROME)."""


class FranceTravailCredentialsMissing(FranceTravailError):
    """FT_CLIENT_ID / FT_CLIENT_SECRET absents du `.env`."""


class FranceTravailScopeInvalid(FranceTravailError):
    """Le scope demandé est invalide ou pas activé côté dashboard app.

    Si raise : Matteo doit cocher le scope dans son app OrientIA
    (cf `docs/TODO_MATTEO_APIS.md`).
    """


@dataclass
class _TokenState:
    access_token: Optional[str] = None
    expires_at: float = 0.0


def _get_credentials() -> tuple[str, str]:
    cid = os.environ.get("FT_CLIENT_ID", "").strip()
    csec = os.environ.get("FT_CLIENT_SECRET", "").strip()
    if not cid or not csec:
        raise FranceTravailCredentialsMissing(
            "FT_CLIENT_ID/FT_CLIENT_SECRET absents dans .env. "
            "Cf docs/TODO_MATTEO_APIS.md §1 (France Travail signup)."
        )
    return cid, csec


def _call_with_retry(fn, *args, max_retries: int = 4, **kwargs):
    last = None
    for attempt in range(max_retries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            last = exc
            msg = str(exc)
            exc_name = type(exc).__name__
            is_rate_limit = "429" in msg or "rate" in msg.lower()
            is_5xx = bool(re.search(r"\b5\d{2}\b", msg))
            is_transient = any(k in exc_name for k in ("Timeout", "Connect", "ReadTimeout"))
            if not (is_rate_limit or is_5xx or is_transient) or attempt == max_retries:
                raise
            time.sleep((15.0 if is_rate_limit else 2.0) * (2 ** attempt))
    raise last  # pragma: no cover


class FranceTravailClient:
    """Client OAuth2 générique pour les APIs France Travail (hors ROME).

    Sous-classes doivent override :
    - `API_NAME: str` — nom court pour logs
    - `SCOPE: str` — scope OAuth2 requis (ex "api_marchedutravailv1")
    - `BASE_URL: str` — URL base de l'API
    - `DEFAULT_RPM: int` — rate limit safe (marge sous cap officiel)
    """

    API_NAME: ClassVar[str] = "ft_base"
    SCOPE: ClassVar[str] = ""
    BASE_URL: ClassVar[str] = ""
    DEFAULT_RPM: ClassVar[int] = 60

    def __init__(
        self,
        session: Optional[requests.Session] = None,
        rate_limiter: Optional[RateLimiter] = None,
        rpm: Optional[int] = None,
    ):
        self._session = session or requests.Session()
        self._limiter = rate_limiter or RateLimiter(
            max_per_minute=rpm or self.DEFAULT_RPM
        )
        self._token = _TokenState()

    def _ensure_token(self) -> str:
        now = time.time()
        if self._token.access_token and self._token.expires_at > now + 30:
            return self._token.access_token
        cid, csec = _get_credentials()
        data = {
            "grant_type": "client_credentials",
            "client_id": cid,
            "client_secret": csec,
            "scope": self.SCOPE,
        }
        self._limiter.acquire()
        resp = _call_with_retry(
            self._session.post, OAUTH_TOKEN_URL, data=data, timeout=30
        )
        if resp.status_code in (400, 401, 403):
            body = resp.text[:200]
            if "invalid_scope" in body or "unknown" in body.lower():
                raise FranceTravailScopeInvalid(
                    f"Scope {self.SCOPE!r} invalide/non-activé pour app OrientIA. "
                    f"Cocher dans dashboard FT. HTTP {resp.status_code}: {body}"
                )
            raise FranceTravailError(
                f"OAuth2 refusé ({resp.status_code}): {body}"
            )
        resp.raise_for_status()
        payload = resp.json()
        token = payload.get("access_token")
        if not token:
            raise FranceTravailError(f"Token absent du payload : {payload}")
        self._token = _TokenState(
            access_token=token, expires_at=now + float(payload.get("expires_in", 1200))
        )
        return token

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._ensure_token()}",
            "Accept": "application/json",
        }

    def _get(self, path: str, params: Optional[dict] = None, timeout: int = 30):
        """GET {BASE_URL}{path} avec auth + rate limit + retry."""
        self._limiter.acquire()
        url = f"{self.BASE_URL}{path}"
        resp = _call_with_retry(
            self._session.get, url, headers=self._auth_headers(), params=params or {}, timeout=timeout
        )
        resp.raise_for_status()
        return resp.json()
