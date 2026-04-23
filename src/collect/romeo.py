"""ROMEO — API IA matching texte libre → ROME/compétences (ADR-043 P1).

Source : `https://api.francetravail.io/partenaire/romeo/v2` (probable, à confirmer)
Rate limit à confirmer post-activation.

**Usage OrientIA critique pour S+2 Axe 2 agentic** :

Input utilisateur ProfileClarifier : texte libre ("je veux travailler dans la
tech") → ROMEO retourne codes ROME + compétences associées → base de
`ProfileClarifier` agent sans heuristique keywords fragile.

Bascule vers un matching **sémantique officiel France Travail** (vs
`DOMAIN_KEYWORDS` regex custom dans `parcoursup.py`).

Prérequis Matteo : scope ROMEO spécifique à cocher (ou procédure distincte
via portail francetravail.io/romeo-2, à confirmer).
"""
from __future__ import annotations

from typing import Any, Optional

from src.collect.ft_base import FranceTravailClient


class RomeoClient(FranceTravailClient):
    API_NAME = "romeo"
    # Scope exact à confirmer post-activation — `api_romeov2` candidat
    SCOPE = "api_romeov2"
    BASE_URL = "https://api.francetravail.io/partenaire/romeo/v2"
    DEFAULT_RPM = 300  # à confirmer post-activation

    def predict_rome_from_text(
        self, text: str, nb_resultats: int = 5
    ) -> list[dict[str, Any]]:
        """POST /predictionMetiers — matching texte libre → codes ROME + scores.

        Input : texte libre utilisateur (ex "je veux bosser dans le digital
        mais j'aime aussi le social").
        Output : liste top-N métiers prédits avec `codeROME`, `libelle`,
        `score` (confiance IA), `compétences` associées.
        """
        if not text:
            return []
        # ROMEO utilise typiquement POST (texte dans le body) vs GET des autres FT APIs
        import requests

        self._limiter.acquire()
        resp = requests.post(
            f"{self.BASE_URL}/predictionMetiers",
            headers={**self._auth_headers(), "Content-Type": "application/json"},
            json={"nomAppelant": "OrientIA", "contexte": text, "nb_metiers": nb_resultats},
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()
        return payload.get("predictions") or payload.get("metiers") or []

    def get_competences_metier(self, code_rome: str) -> list[dict[str, Any]]:
        """GET /competences/{codeROME} — compétences détaillées par code ROME.

        Complémentaire de ROME 4.0 Compétences v1 (déjà actif) — ROMEO apporte
        le score de pertinence IA vs l'API ROME qui liste brute.
        """
        if not code_rome:
            raise ValueError("code_rome vide")
        payload = self._get(f"/competences/{code_rome}")
        return payload if isinstance(payload, list) else payload.get("competences", [])


def normalize_prediction(record: dict[str, Any]) -> dict[str, Any]:
    """Normalise une prédiction ROMEO pour usage downstream (ProfileClarifier S+2)."""
    return {
        "source": "romeo",
        "code_rome": record.get("codeROME") or record.get("code"),
        "libelle": record.get("libelle"),
        "score": record.get("score") or record.get("scorePrediction"),
        "competences": record.get("competences") or [],
    }
