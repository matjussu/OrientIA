"""HTTP schemas for the OrientIA FastAPI wrapper.

Contract source of truth :
    OrientAI_Platform/docs/integration/02-http-contract.md

The wrapper is a pure passthrough — sources are returned as raw dicts coming
straight out of `pipeline.answer()`, without any mapping or transformation.
The Next.js platform side adapts via Zod `.passthrough()` on its own
`SourceSchema`.

Direction du contrat : le LLM décide du format, la plateforme s'adapte.
Toute modification ici se réplique dans
`OrientAI_Platform/src/lib/api/schemas.ts` — sinon contract drift au runtime.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class HistoryMessage(BaseModel):
    """Un tour de conversation (Mistral compliant).

    `content.max_length=3000` absorbe les réponses long-tail Mistral
    (max_tokens=800 produit ~2200-2400 chars worst-case) qu'un client peut
    remettre dans `history.content` au tour suivant. Avant 3000, le backend
    rejetait en 422 les long-tails revenus dans l'historique alors que côté
    plateforme Zod ne contraint plus la length depuis PR Zod #24.
    Cf. audit-pont-orientia-platform-2026-05-13 §H1.
    """

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=3000)


class AnswerRequest(BaseModel):
    """Input envoyé par la plateforme.

    `extra="ignore"` : tolère les champs additionnels que la plateforme pourrait
    envoyer (ex : `audience` pas encore consommé par le pipeline en Phase 0).
    Si le pipeline les consomme un jour, on bascule vers une définition
    explicite ici sans rien casser.

    `history` est capé à 6 messages au lieu des 20 du contrat plateforme : on
    réduit la surface d'attaque prompt-injection (un attaquant pourrait sinon
    bourrer 20 messages assistant avec des "ignore previous").
    """

    model_config = ConfigDict(extra="ignore")

    question: str = Field(min_length=3, max_length=500)
    history: list[HistoryMessage] | None = Field(default=None, max_length=6)


class AnswerResponse(BaseModel):
    """Output passe-plat. `sources: list[dict[str, Any]]` est le format brut
    natif du pipeline OrientIA (~20 clés par fiche, variable selon corpus).

    `extra="allow"` : tolère l'ajout futur de clés sans casser ce schéma.
    """

    model_config = ConfigDict(extra="allow")

    answer: str
    sources: list[dict[str, Any]]
    faithfulness_score: float | None = Field(default=None, ge=0.0, le=1.0)
    faithfulness_verdict: Literal["FIDELE", "INFIDELE"] | None = None
    latency_ms: float = Field(ge=0)


class HealthResponse(BaseModel):
    ok: bool
    service: str = "orientia"
    version: str
    pipeline_loaded: bool
    index_size: int | None = None
    time: str  # ISO 8601


class ErrorResponse(BaseModel):
    error: str
    code: str
    request_id: str | None = None
