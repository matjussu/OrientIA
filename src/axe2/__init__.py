"""Axe 2 — Architecture agentic Phase 1 (Sprint 12).

Pivot stratégique 2026-05-01 : passage du pipeline single-shot Mistral
medium prompt long (qui plafonne capacitaire, cf verdict v5b 1/5
critères stricts + D5 noop empirique) vers une architecture agentic
multi-step orchestrée par Sonnet 4.5 + Mistral générateur final
(souveraineté FR préservée).

Modules :
- `contracts` : Pydantic v2 typed contracts (ProfileState, SubQuestion,
    ToolCallResult, AgentInput, AgentOutput). Couche ADDITIVE qui
    coexiste avec les dataclasses Sprint 9 hierarchical sans les
    remplacer (R3 isolated strict).

Phase 1 minimal : A1 (contracts) + A2 (ProfileClarifier extension
AnalystAgent) + A4 (3 tools core) + bench gate empirique GO/NO-GO.
Phase 2 (A3 SubQuestionDecomposer / A5 Composer / A6 Validator /
A7 streaming) hors scope, conditionnelle GO bench S4.

Cf `docs/sprint12-axe-2-agentic-audit-existing-2026-05-01.md` (S0 audit)
et `2026-05-01-1820-claudette-orientia-sprint12-axe-2-agentic-phase-1-A1-A2-A4`
(ordre Jarvis).
"""
from src.axe2.contracts import (
    AgentInput,
    AgentOutput,
    AgeGroup,
    EducationLevel,
    IntentType,
    ProfileState,
    SubQuestion,
    ToolCallResult,
)

__all__ = [
    "AgentInput",
    "AgentOutput",
    "AgeGroup",
    "EducationLevel",
    "IntentType",
    "ProfileState",
    "SubQuestion",
    "ToolCallResult",
]
