"""Session Sprint 9 — état conversationnel multi-tour.

Contient :
- L'historique des tours (user / assistant)
- Le UserSessionProfile mis à jour par AnalystAgent
- Les flags de routage (reco_requested_explicit pour bypass règle 3 tours)
- Le mode bench single-shot pour la non-régression Mode Baseline

Pas de persistance cross-session (Sprint 9-10 = intra-session uniquement,
cf D9 ADR pivot 2026-04-28). Sprint 11 ajoutera LocalStorage côté UI.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Literal

from src.agents.hierarchical.schemas import UserSessionProfile


# Triggers explicites de demande de reco — déclenchent SynthesizerAgent
# dès le tour 2 (bypass règle 3 tours, exception cadrée du persona prompt).
_EXPLICIT_RECO_PATTERNS = (
    r"\bdonne[ -]?moi (?:des?|3|trois)?\s*(?:recos?|propositions?|options?|suggestions?|formations?)\b",
    r"\bje veux (?:des?|3|trois)?\s*(?:recos?|options?|propositions?|suggestions?)\b",
    r"\baide[ -]?moi à trancher\b",
    r"\bquelles? (?:sont les )?(?:meilleures? )?(?:formations?|écoles?|voies?)\b",
    r"\bpropose[ -]?moi (?:des?|3|trois)?\s*",
    r"\bquel[le]?s? (?:formation|école|métier|voie)",
)
_EXPLICIT_RECO_REGEX = re.compile("|".join(_EXPLICIT_RECO_PATTERNS), re.IGNORECASE)


@dataclass
class Turn:
    """Un tour conversation : message user + réponse assistant."""

    user: str
    assistant: str | None = None
    reco_mode_active: bool = False  # True si SynthesizerAgent invoqué ce tour


@dataclass
class Session:
    """Session conversationnelle intra-session OrientIA Sprint 9."""

    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    profile: UserSessionProfile = field(default_factory=UserSessionProfile)
    turns: list[Turn] = field(default_factory=list)
    reco_requested_explicit: bool = False
    """True si l'utilisateur·ice a explicitement demandé des reco (bypass règle 3 tours)."""
    bench_single_shot: bool = False
    """True si la session est utilisée pour le bench non-régression (force tour=3+ + reco)."""

    @classmethod
    def new_anonymous(cls) -> "Session":
        return cls()

    @classmethod
    def new_for_bench(cls) -> "Session":
        """Session forcée en mode reco single-shot pour bench non-régression."""
        s = cls(bench_single_shot=True)
        s.profile.tour_count = 3  # bypass règle 3 tours
        return s

    def add_user_turn(self, message: str) -> None:
        """Ajoute un nouveau tour user (sans réponse assistant pour l'instant)."""
        self.turns.append(Turn(user=message))
        self.profile.tour_count += 1
        if _EXPLICIT_RECO_REGEX.search(message):
            self.reco_requested_explicit = True

    def attach_assistant_response(self, response: str, reco_mode: bool) -> None:
        """Attache la réponse assistant au dernier tour ouvert."""
        if not self.turns or self.turns[-1].assistant is not None:
            raise RuntimeError("attach_assistant_response: no open turn")
        self.turns[-1].assistant = response
        self.turns[-1].reco_mode_active = reco_mode

    def should_trigger_synthesizer(self) -> bool:
        """Décide si le SynthesizerAgent doit être invoqué pour le tour courant.

        Règles :
        - bench_single_shot=True → toujours True (compat bench Mode Baseline)
        - reco_requested_explicit=True ET tour_count ≥ 2 → True (exception
          cadrée du persona prompt : "donne-moi des reco maintenant")
        - tour_count ≥ 3 ET profil confidence ≥ 0.5 → True (règle nominale)
        - sinon → False (rester en mode listening EmpathicAgent)
        """
        if self.bench_single_shot:
            return True
        if self.reco_requested_explicit and self.profile.tour_count >= 2:
            return True
        if self.profile.tour_count >= 3 and self.profile.confidence >= 0.5:
            return True
        return False

    def history_messages(self, role_format: Literal["mistral", "openai"] = "mistral") -> list[dict]:
        """Sérialise l'historique en format messages LLM (sans le tour ouvert)."""
        msgs: list[dict] = []
        for turn in self.turns:
            msgs.append({"role": "user", "content": turn.user})
            if turn.assistant is not None:
                msgs.append({"role": "assistant", "content": turn.assistant})
        return msgs

    def latest_user_message(self) -> str:
        """Renvoie le dernier message user (tour ouvert ou clos)."""
        if not self.turns:
            return ""
        return self.turns[-1].user

    def is_empty(self) -> bool:
        return len(self.turns) == 0
