"""OrientIA Agent — pivot agentique adaptatif (axe B INRIA J-23).

Architecture Mistral function-calling : Tool registry + Agent loop.
Cf ADR-051 dans docs/DECISION_LOG.md.

Sprint 1 : ProfileClarifier MVP.
Sprint 2 (à venir) : QueryReformuler.
Sprint 3 (à venir) : FetchStatFromSource.
Sprint 4 (à venir) : intégration end-to-end + bench vs baseline figée.
"""
from src.agent.tool import Tool, ToolRegistry
from src.agent.agent import Agent

__all__ = ["Tool", "ToolRegistry", "Agent"]
