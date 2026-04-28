"""Coordinator — orchestrateur Sprint 9 multi-agents hiérarchique.

Point d'entrée user. Pour chaque tour :
1. Ajoute le message user à la session (incrémente tour_count, détecte
   trigger reco explicite)
2. Décide si le SynthesizerAgent doit être invoqué (règle 3 tours +
   exception trigger explicite + bench single-shot)
3. Lance EmpathicAgent (foreground, blocking) + AnalystAgent (background,
   parallèle) via ThreadPoolExecutor
4. Si SynthesizerAgent invoqué : produit la base factuelle séquentiellement
   AVANT EmpathicAgent (pour pouvoir l'injecter en system context)
5. Merge le delta AnalystAgent dans le UserSessionProfile (pour le tour
   suivant)
6. Attache la réponse au tour, retourne le texte user-facing

Latency :
- Mode listening (tour 1-2) : max(EmpathicAgent ≤3s, AnalystAgent ~3s) ≈ 3s
- Mode reco (tour 3+) : SynthesizerAgent ~30-40s + EmpathicAgent ~3s + AnalystAgent ~3s
  (parallèle) ≈ 33-43s
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from typing import Callable

from mistralai.client import Mistral

from src.agent.pipeline_agent import AgentPipeline
from src.agents.hierarchical.analyst_agent import AnalystAgent
from src.agents.hierarchical.empathic_agent import EmpathicAgent
from src.agents.hierarchical.session import Session
from src.agents.hierarchical.synthesizer_agent import (
    SynthesizedFactualBase,
    SynthesizerAgent,
)


@dataclass
class CoordinatorTurnResult:
    """Trace structurée d'un tour (debug, telemetry, tests)."""

    response_text: str
    reco_mode_active: bool
    elapsed_total_s: float
    elapsed_synthesizer_s: float = 0.0
    elapsed_empathic_s: float = 0.0
    elapsed_analyst_s: float = 0.0
    factual_sources_count: int = 0
    profile_delta: dict = field(default_factory=dict)


@dataclass
class Coordinator:
    """Orchestrateur Coordinator — entry point user-facing.

    Construit avec :
    - Un client Mistral partagé entre les sub-agents
    - Une factory AgentPipeline pour le SynthesizerAgent (lazy instantiation)
    - Optionnel : EmpathicAgent / AnalystAgent custom (test override)

    Usage typique :
        coord = Coordinator.default(client, agent_pipeline_factory)
        session = Session.new_anonymous()
        result = coord.respond(session, "Je suis en terminale...")
        # result.response_text est la réponse user-facing
    """

    empathic: EmpathicAgent
    analyst: AnalystAgent
    synthesizer: SynthesizerAgent
    parallel_max_workers: int = 2

    @classmethod
    def default(
        cls,
        client: Mistral,
        agent_pipeline_factory: Callable[[], AgentPipeline],
    ) -> "Coordinator":
        """Builder par défaut — instancie les 3 sub-agents avec configs nominales."""
        return cls(
            empathic=EmpathicAgent(client=client),
            analyst=AnalystAgent(client=client),
            synthesizer=SynthesizerAgent(agent_pipeline_factory=agent_pipeline_factory),
        )

    def respond(self, session: Session, user_query: str) -> CoordinatorTurnResult:
        """Produit une réponse pour un tour user.

        Args:
            session: la session courante (mutée — ajout du tour, update profil)
            user_query: le message user pour ce tour

        Returns:
            CoordinatorTurnResult avec response_text + métadonnées télémétrie.
        """
        t0_total = time.time()
        session.add_user_turn(user_query)

        trigger_synthesizer = session.should_trigger_synthesizer()

        # SynthesizerAgent SÉQUENTIEL avant EmpathicAgent (factual base
        # doit être prête avant l'appel EmpathicAgent qui l'injecte en
        # system context). Latency ~30-40s mais uniquement quand reco.
        factual_base: SynthesizedFactualBase | None = None
        elapsed_synth = 0.0
        if trigger_synthesizer:
            factual_base = self.synthesizer.synthesize(session)
            elapsed_synth = factual_base.elapsed_s

        # EmpathicAgent + AnalystAgent EN PARALLÈLE
        with ThreadPoolExecutor(max_workers=self.parallel_max_workers) as pool:
            empathic_future: Future = pool.submit(
                self.empathic.respond,
                session,
                factual_base.raw_factual_text if factual_base else None,
            )
            analyst_future: Future = pool.submit(
                self.analyst.update_profile,
                session,
            )

            # Attendre les deux
            t0_emp = time.time()
            empathic_response = empathic_future.result()
            elapsed_empathic = time.time() - t0_emp

            t0_ana = time.time()
            profile_delta = analyst_future.result()
            elapsed_analyst = time.time() - t0_ana

        # Merge delta profil pour le tour suivant
        if profile_delta:
            session.profile.merge_update(profile_delta)

        # Attache la réponse au tour
        response_text = empathic_response.to_user_text()
        session.attach_assistant_response(
            response_text,
            reco_mode=empathic_response.reco_mode_active,
        )

        return CoordinatorTurnResult(
            response_text=response_text,
            reco_mode_active=empathic_response.reco_mode_active,
            elapsed_total_s=time.time() - t0_total,
            elapsed_synthesizer_s=elapsed_synth,
            elapsed_empathic_s=elapsed_empathic,
            elapsed_analyst_s=elapsed_analyst,
            factual_sources_count=factual_base.sources_count if factual_base else 0,
            profile_delta=profile_delta or {},
        )

    def respond_single_shot(self, query: str) -> CoordinatorTurnResult:
        """Mode bench non-régression : single-shot direct vers SynthesizerAgent.

        Bypass règle 3 tours, force trigger SynthesizerAgent + EmpathicAgent
        re-emballe la base factuelle. Utilisé par
        `src.eval.systems.HierarchicalSystem` pour le bench Mode Baseline.

        Préserve structurellement le pct_verified bench car
        SynthesizerAgent embed AgentPipeline tel quel.
        """
        session = Session.new_for_bench()
        return self.respond(session, query)
