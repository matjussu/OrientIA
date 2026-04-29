"""src.agents.hierarchical — Sprint 9 conseiller conversationnel multi-agents.

Architecture (cf ADR `08-Decisions/2026-04-28-orientia-pivot-pipeline-agentique-claude.md`) :

    USER QUERY
        │
        ▼
    Coordinator (orchestre tour par tour)
        ├─→ EmpathicAgent (foreground blocking, persona conseiller, ≤3s)
        │   ↑ injection base factuelle (mode reco)
        ├─→ AnalystAgent (background parallèle, update UserSessionProfile)
        └─→ SynthesizerAgent (on-demand tour 3+ : embed AgentPipeline factuel)

Préserve structurellement le bench Mode Baseline +7,4pp Sprint 7 :
SynthesizerAgent embed AgentPipeline TEL QUEL (pattern strangler fig).
"""

from src.agents.hierarchical.coordinator import Coordinator, CoordinatorTurnResult
from src.agents.hierarchical.empathic_agent import EmpathicAgent, load_persona_prompt
from src.agents.hierarchical.analyst_agent import AnalystAgent
from src.agents.hierarchical.synthesizer_agent import (
    SynthesizedFactualBase,
    SynthesizerAgent,
)
from src.agents.hierarchical.schemas import (
    EmpathicResponse,
    UserSessionProfile,
    load_user_profile_schema,
)
from src.agents.hierarchical.session import Session, Turn


__all__ = [
    "Coordinator",
    "CoordinatorTurnResult",
    "EmpathicAgent",
    "AnalystAgent",
    "SynthesizerAgent",
    "SynthesizedFactualBase",
    "EmpathicResponse",
    "UserSessionProfile",
    "Session",
    "Turn",
    "load_persona_prompt",
    "load_user_profile_schema",
]
