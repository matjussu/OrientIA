"""SynthesizerAgent — on-demand factual layer (Sprint 9).

Wrapper autour de l'AgentPipeline existant (Sprint 4) qui produit la
base factuelle vérifiée pour le mode reco. Invoqué uniquement quand le
Coordinator détecte que le tour requiert une recommandation classée
(tour 3+ ou trigger explicite).

Architecture en couche (cf ADR pivot 2026-04-28 D2 + validation Jarvis
2026-04-28T09:33) : on N'altère PAS l'AgentPipeline, on l'embed.
Préserve structurellement le bench Mode Baseline +7,4pp.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from src.agent.pipeline_agent import AgentAnswer, AgentPipeline
from src.agents.hierarchical.schemas import UserSessionProfile
from src.agents.hierarchical.session import Session


@dataclass
class SynthesizedFactualBase:
    """Base factuelle produite par SynthesizerAgent.

    Contient le texte brut généré par AgentPipeline (qui sera
    re-emballé par EmpathicAgent en posture conseiller) et les sources
    pour audit/transparence.
    """

    raw_factual_text: str
    sources_count: int
    elapsed_s: float
    underlying_agent_answer: AgentAnswer | None = None


@dataclass
class SynthesizerAgent:
    """On-demand RAG-backed reco synthesizer.

    L'instance n'est PAS construite avec un AgentPipeline figé : on prend
    une factory `agent_pipeline_factory` pour permettre :
    1. Lazy instantiation (l'AgentPipeline charge un index FAISS lourd
       — on évite si SynthesizerAgent n'est jamais invoqué)
    2. Mocking en tests (factory renvoie un mock)
    3. Hot-swap pipeline en runtime si besoin
    """

    agent_pipeline_factory: Callable[[], AgentPipeline]
    _pipeline: AgentPipeline | None = None

    @property
    def pipeline(self) -> AgentPipeline:
        if self._pipeline is None:
            self._pipeline = self.agent_pipeline_factory()
        return self._pipeline

    def _build_query_with_profile(
        self, session: Session
    ) -> str:
        """Construit la query enrichie envoyée à l'AgentPipeline.

        L'AgentPipeline existant fait son propre ProfileClarifier sur la
        query — on ne lui passe pas le UserSessionProfile directement
        (il n'a pas cette API). À la place, on enrichit la query avec
        les contraintes connues pour aider le retrieval.
        """
        latest = session.latest_user_message()
        profile = session.profile

        enrichments: list[str] = []
        if profile.niveau_scolaire:
            enrichments.append(f"niveau scolaire : {profile.niveau_scolaire}")
        if profile.region:
            enrichments.append(f"région : {profile.region}")
        if profile.contraintes:
            enrichments.append(f"contraintes : {', '.join(profile.contraintes)}")
        if profile.interets_detectes:
            enrichments.append(f"intérêts : {', '.join(profile.interets_detectes)}")

        if not enrichments:
            return latest

        return f"{latest}\n\n[Contexte profil intra-session : {' ; '.join(enrichments)}]"

    def synthesize(self, session: Session) -> SynthesizedFactualBase:
        """Invoque l'AgentPipeline factuel et renvoie la base brute.

        La base brute n'est PAS user-facing — elle est destinée à
        l'EmpathicAgent qui la re-emballe en posture conseiller.

        Returns:
            SynthesizedFactualBase avec le texte factuel + métadonnées.
            En cas d'erreur AgentPipeline, raw_factual_text est vide
            (caller fallback gracieux côté Coordinator).
        """
        t0 = time.time()
        enriched_query = self._build_query_with_profile(session)
        try:
            agent_answer = self.pipeline.answer(enriched_query)
        except Exception as e:
            return SynthesizedFactualBase(
                raw_factual_text="",
                sources_count=0,
                elapsed_s=time.time() - t0,
                underlying_agent_answer=None,
            )

        return SynthesizedFactualBase(
            raw_factual_text=agent_answer.answer_text,
            sources_count=len(agent_answer.sources_aggregated),
            elapsed_s=time.time() - t0,
            underlying_agent_answer=agent_answer,
        )
