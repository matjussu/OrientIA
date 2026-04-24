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
        self,
        text: str,
        nb_resultats: int = 5,
        contexte: Optional[str] = None,
        identifiant: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """POST /predictionMetiers — matching texte libre → codes ROME + scores.

        Format payload conforme à l'OpenAPI ROMEO v2 (référence :
        `data/raw/france-travail/romeo.json` — schéma AppellationDTO) :

            {
                "appellations": [
                    {"intitule": "<texte>", "identifiant": "<id>",
                     "contexte": "<NAF/SIRET/texte libre>"}  # optionnel
                ],
                "options": {
                    "nomAppelant": "OrientIA",  # REQUIRED
                    "nbResultats": 5,
                    "seuilScorePrediction": 0.0  # optionnel, 0-1
                }
            }

        Input : texte libre utilisateur (ex "je veux bosser dans le digital").
        Le `contexte` est optionnel mais améliore la prédiction (secteur
        d'activité NAF, code SIRET, ou texte libre).

        Output : liste top-N prédictions avec `codeROME`, `libelle`,
        `score` (confiance IA).
        """
        if not text:
            return []
        import requests

        appellation = {
            "intitule": text,
            "identifiant": identifiant or "orientia_query",
        }
        if contexte:
            appellation["contexte"] = contexte

        payload = {
            "appellations": [appellation],
            "options": {
                "nomAppelant": "OrientIA",
                "nbResultats": nb_resultats,
            },
        }

        self._limiter.acquire()
        resp = requests.post(
            f"{self.BASE_URL}/predictionMetiers",
            headers={**self._auth_headers(), "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        # Réponse ROMEO v2 réelle (probe 2026-04-24) :
        # [
        #   {
        #     "metiersRome": [
        #       {"libelleAppellation": "...", "codeAppellation": "...",
        #        "libelleRome": "...", "codeRome": "M1855",
        #        "scorePrediction": 0.763},
        #       ...
        #     ],
        #     "uuidInference": "...",
        #     "identifiant": "test1",
        #     "intitule": "..."
        #   }
        # ]
        if isinstance(data, list):
            # Mono-appellation : renvoyer directement la liste metiersRome
            if len(data) == 1:
                return data[0].get("metiersRome") or data[0].get("metiersPredits") or []
            # Multi-appellations : agréger chaque bloc
            return data
        return data.get("metiersRome") or data.get("predictions") or []

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
    """Normalise une prédiction ROMEO pour usage downstream (ProfileClarifier S+2).

    Schéma ROMEO v2 réel (probe 2026-04-24) :
        codeRome, libelleRome, codeAppellation, libelleAppellation, scorePrediction
    """
    return {
        "source": "romeo",
        "code_rome": record.get("codeRome") or record.get("codeROME") or record.get("code"),
        "libelle_rome": record.get("libelleRome"),
        "code_appellation": record.get("codeAppellation"),
        "libelle_appellation": record.get("libelleAppellation") or record.get("libelle"),
        "score": record.get("scorePrediction") or record.get("score"),
        "competences": record.get("competences") or [],
    }
