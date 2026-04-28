"""Schemas Sprint 9 hiérarchique — UserSessionProfile + EmpathicResponse.

Cf JSON schema authoritative dans `src/state/user_profile_schema.json`.
Cette dataclass Python est l'API runtime ; le JSON schema est la source
de vérité pour validation cross-agent.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "state" / "user_profile_schema.json"


def load_user_profile_schema() -> dict[str, Any]:
    """Charge le JSON schema authoritative pour validation runtime."""
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


@dataclass
class UserSessionProfile:
    """Profil utilisateur intra-session OrientIA Sprint 9.

    Mis à jour par AnalystAgent à chaque tour, injecté dans le contexte
    EmpathicAgent au tour suivant. Conforme à
    `src/state/user_profile_schema.json`.

    NOTE design : volontairement plus expressif que le `Profile`
    single-shot de `src.agent.tools.profile_clarifier`. Là où Profile
    contraint des enums (age_group, education_level), UserSessionProfile
    autorise du libre-forme structuré (`niveau_scolaire="terminale_spe_maths_physique"`)
    pour capturer la richesse conversationnelle. Trade-off : moins
    typé pour le routing retrieval, plus expressif pour la posture
    conseiller.
    """

    niveau_scolaire: str | None = None
    age_estime: int | None = None
    region: str | None = None
    interets_detectes: list[str] = field(default_factory=list)
    contraintes: list[str] = field(default_factory=list)
    valeurs: list[str] = field(default_factory=list)
    questions_ouvertes: list[str] = field(default_factory=list)
    confidence: float = 0.0
    tour_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserSessionProfile":
        allowed = {f.name for f in cls.__dataclass_fields__.values()}
        kwargs = {k: v for k, v in data.items() if k in allowed}
        return cls(**kwargs)

    def merge_update(self, update: dict[str, Any]) -> None:
        """Merge incrémental d'un update produit par AnalystAgent.

        - Champs scalaires (niveau_scolaire, age_estime, region) :
          remplacés si la nouvelle valeur est non-null + confidence
          de l'update suffisante (laissé au caller, ici on remplace
          inconditionnellement si non-null).
        - Listes (interets_detectes, contraintes, valeurs,
          questions_ouvertes) : union sans doublons, préserve l'ordre
          d'ajout.
        - confidence : moyenne pondérée tour_count.
        """
        for scalar_field in ("niveau_scolaire", "age_estime", "region"):
            new_val = update.get(scalar_field)
            if new_val is not None:
                setattr(self, scalar_field, new_val)

        for list_field in ("interets_detectes", "contraintes", "valeurs", "questions_ouvertes"):
            new_items = update.get(list_field) or []
            existing = getattr(self, list_field)
            for item in new_items:
                if item and item not in existing:
                    existing.append(item)

        new_conf = update.get("confidence")
        if isinstance(new_conf, (int, float)):
            n = max(self.tour_count, 1)
            self.confidence = (self.confidence * (n - 1) + float(new_conf)) / n


@dataclass
class EmpathicResponse:
    """Réponse structurée produite par EmpathicAgent.

    Sert d'API interne entre EmpathicAgent et Coordinator. Sérialisée en
    string final pour l'utilisateur·ice dans le Coordinator.
    """

    reformulation: str
    """Phrase 'Si je te/vous comprends bien...' obligatoire (≥1 ligne)."""

    emotion_recognition: str | None = None
    """Reconnaissance émotion 0-1 phrase. Null si query neutre."""

    exploration_or_reco: str = ""
    """Soit 2-3 questions ouvertes (tour 1-2), soit 3 options pondérées (tour 3+)."""

    closing_question: str | None = None
    """Question ouverte finale qui rend le choix à l'utilisateur·ice."""

    reco_mode_active: bool = False
    """True si SynthesizerAgent a été invoqué et la reco est dans exploration_or_reco."""

    raw_text: str = ""
    """Réponse texte concaténée (debug + serialization)."""

    def to_user_text(self) -> str:
        """Sérialise la réponse structurée en texte naturel pour l'utilisateur·ice."""
        if self.raw_text:
            return self.raw_text
        parts = [self.reformulation.strip()]
        if self.emotion_recognition:
            parts.append(self.emotion_recognition.strip())
        if self.exploration_or_reco:
            parts.append(self.exploration_or_reco.strip())
        if self.closing_question:
            parts.append(self.closing_question.strip())
        return "\n\n".join(p for p in parts if p)
