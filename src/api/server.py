"""OrientIA FastAPI HTTP wrapper — pure passthrough bridge.

Expose le pipeline RAG OrientIA via HTTP pour la plateforme Next.js
(`OrientAI_Platform`). Le wrapper est un **passe-plat** : il sérialise
`pipeline.answer()` tel quel, sans aucun mapping créatif. La plateforme
adapte via Zod `.passthrough()`.

Contract source of truth :
    OrientAI_Platform/docs/integration/02-http-contract.md

Boot local :
    ./scripts/run_api.sh
    curl -H "Authorization: Bearer $ORIENTIA_API_KEY" \
         -H "Content-Type: application/json" \
         -d '{"question": "..."}' http://localhost:8000/answer

Deploy Railway via Dockerfile + persistent volume `/app/data/embeddings/`.

Sécurité MVP propre :
- Bearer token via `ORIENTIA_API_KEY` (timing-safe `hmac.compare_digest`)
- CORS strict en prod (uniquement `PLATFORM_ORIGIN`, pas de wildcard)
- Rate limit inline 10 req/min par IP sur `/answer` (pas de dep externe)
- Sanitization input (refus prompt-injection grossier)
- Single worker uvicorn (`_pipeline` global non thread-safe entre workers)
- Logs JSON sans PII (jamais la `question`, juste les métriques)
"""
from __future__ import annotations

import hmac
import json
import logging
import os
import re
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mistralai.client import Mistral

from src.api.schemas import (
    AnswerRequest,
    AnswerResponse,
    ErrorResponse,
    HealthResponse,
)
from src.rag.factory import make_production_pipeline

# ───────────────────────────── Logging ──────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("orientia.api")

# ───────────────────────────── Config / globals ─────────────────────────────

_VERSION = "v4.1"
_FICHES_PATH = Path(os.environ.get("ORIENTIA_FICHES_PATH", "data/processed/formations.json"))
_INDEX_PATH = os.environ.get("ORIENTIA_INDEX_PATH", "data/embeddings/formations.index")

# Pipeline global, chargé une seule fois au lifespan startup.
# `_pipeline.last_validation` est un état mutable — on garde --workers 1 en prod
# pour éviter les races (cf docs/integration/03-orientia-fastapi-spec.md).
_pipeline: Any = None
_index_size: int | None = None

# ───────────────────────────── Lifespan ─────────────────────────────────────


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Charge le pipeline + index une seule fois au démarrage."""
    global _pipeline, _index_size

    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise RuntimeError(
            "MISTRAL_API_KEY env var is required to load the OrientIA pipeline. "
            "Set it via Railway dashboard or .env locally."
        )

    logger.info(f"Loading OrientIA pipeline (v={_VERSION})...")
    client = Mistral(api_key=api_key)

    if not _FICHES_PATH.exists():
        raise RuntimeError(
            f"Fiches file not found: {_FICHES_PATH}. "
            "Mount the persistent volume on Railway, or run from repo root."
        )

    fiches = json.loads(_FICHES_PATH.read_text())
    _index_size = len(fiches)

    # Defaults are correct as of 2026-05-08 :
    # enable_strict_v4=True (v4.1 ≤250 mots), enable_validator=True,
    # enable_scope_classifier=True, enable_golden_qa=True, enable_post_process=True.
    pipeline = make_production_pipeline(client, fiches)

    if not Path(_INDEX_PATH).exists():
        raise RuntimeError(
            f"FAISS index not found: {_INDEX_PATH}. "
            "Bootstrap the persistent volume with formations.index (185 MB)."
        )
    pipeline.load_index_from(_INDEX_PATH)

    _pipeline = pipeline
    logger.info(f"Pipeline ready, {_index_size} fiches indexed")
    yield
    logger.info("Shutting down OrientIA pipeline")
    _pipeline = None


# ───────────────────────────── App + middleware ─────────────────────────────

app = FastAPI(
    title="OrientIA API",
    version=_VERSION,
    lifespan=lifespan,
)

# CORS — uniquement `PLATFORM_ORIGIN` en prod, ajout de localhost en dev.
_env = os.environ.get("ENV", "dev")
_platform_origin = os.environ.get("PLATFORM_ORIGIN")
_cors_origins: list[str]
if _env == "prod":
    if not _platform_origin:
        logger.warning(
            "ENV=prod but PLATFORM_ORIGIN not set — CORS will reject all browser calls. "
            "Set PLATFORM_ORIGIN to your Vercel domain."
        )
        _cors_origins = []
    else:
        _cors_origins = [_platform_origin]
else:
    _cors_origins = ["http://localhost:3000"]
    if _platform_origin:
        _cors_origins.append(_platform_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-Id"],
)


# ───────────────────────────── Auth Bearer ──────────────────────────────────


async def verify_bearer(authorization: str | None = Header(default=None)):
    """Auth Bearer optionnelle (active uniquement si `ORIENTIA_API_KEY` set).

    Comparaison `hmac.compare_digest` pour éviter les timing attacks.
    """
    expected = os.environ.get("ORIENTIA_API_KEY")
    if not expected:
        return  # auth désactivée en dev local

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    provided = authorization.removeprefix("Bearer ")
    if not hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8")):
        raise HTTPException(status_code=401, detail="Invalid Bearer token")


# ───────────────────────────── Rate limit inline ────────────────────────────

# 10 req / 60s par IP — protection minimale contre le scraping qui consommerait
# la clé Mistral (chère). In-memory only ; pour prod multi-instance, swap vers
# Redis (Upstash) post-INRIA.
_RATE_LIMIT_WINDOW_S = 60
_RATE_LIMIT_MAX = 10
_rate_buckets: dict[str, deque[float]] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    # Railway met l'IP réelle dans `x-forwarded-for` (premier item).
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "anon"


def _check_rate_limit(request: Request) -> None:
    """Raise 429 si l'IP a dépassé son quota fenêtre glissante."""
    ip = _client_ip(request)
    now = time.monotonic()
    bucket = _rate_buckets[ip]
    # Drop les hits hors-fenêtre
    while bucket and bucket[0] < now - _RATE_LIMIT_WINDOW_S:
        bucket.popleft()
    if len(bucket) >= _RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Rate limit exceeded: max {_RATE_LIMIT_MAX} requests per "
                f"{_RATE_LIMIT_WINDOW_S}s. Retry shortly."
            ),
        )
    bucket.append(now)


# ───────────────────────────── Sanitization ─────────────────────────────────

# Regex de défense légère contre prompt-injection. Pas une garantie — c'est
# Mistral qui doit faire le gros du travail via son alignement, mais on filtre
# les tentatives les plus grossières pour réduire les démos qui plantent.
_INJECTION_PATTERNS = [
    re.compile(
        r"ignore\s+(previous|above|all|prior)\s+(instructions?|prompts?|rules?|directives?)",
        re.IGNORECASE,
    ),
    re.compile(r"disregard\s+(previous|above|all|prior)\s+(instructions?|prompts?)", re.IGNORECASE),
    re.compile(r"system\s*:\s*you\s+are\s+now", re.IGNORECASE),
]
# Strip des séquences de control-tokens Mistral pour ne pas que l'utilisateur
# puisse forger un faux delimiter.
_MISTRAL_CONTROL_TOKENS = re.compile(r"\[/?INST\]|<\/?s>|<<SYS>>|<</SYS>>", re.IGNORECASE)


def _to_jsonable(obj: Any) -> Any:
    """Recursively coerce numpy types to JSON-serializable Python natives.

    Le pipeline retourne parfois des fiches avec des `numpy.ndarray` (scores,
    agrégats stat) que Pydantic v2 ne sait pas sérialiser. Cette fonction
    marche sur les dict / list / scalars et convertit en place.
    """
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(v) for v in obj]
    return obj


# Champs internes du retriever à exposer comme métadonnées de score (préfixés
# `_` pour signaler à la plateforme que c'est du sidecar non-fonctionnel).
_RETRIEVER_SCORE_FIELDS = ("score", "score_rrf", "score_bm25", "base_score")
# Champs internes du retriever à toujours dropper (volumineux ou non utilisables UI).
_RETRIEVER_DROP_FIELDS = ("embedding", "_orig_index", "_quota_boosted", "rank_bm25")


def _extract_source_fiche(retrieved: dict[str, Any]) -> dict[str, Any]:
    """Déballe la fiche brute depuis la structure retriever-internal.

    Le pipeline retourne `pipeline.answer(...)[1]` sous forme de
    `[{fiche: {...}, score, score_rrf, embedding, ...}, ...]`. La plateforme
    attend la fiche brute directement (`{source, nom, etablissement, ville,
    ...}`). On déballe + on ajoute en sidecar les scores utiles préfixés `_`
    (que la plateforme peut afficher en debug ou trier dans le futur).

    Ce déballage n'est PAS un mapping créatif (on n'invente aucun champ) —
    c'est juste l'opération minimale pour passer du modèle retriever-interne
    au modèle "fiche brute" exposé dans le contrat HTTP.
    """
    if "fiche" not in retrieved or not isinstance(retrieved["fiche"], dict):
        # Fallback safe : si la structure n'est pas celle attendue, on filtre
        # juste les champs lourds et on retourne tel quel.
        return {k: v for k, v in retrieved.items() if k not in _RETRIEVER_DROP_FIELDS}

    fiche = dict(retrieved["fiche"])  # copy défensive

    # Alias minimal : certains corpora (rncp_blocs, certains référentiels
    # RNCP) utilisent `intitule` plutôt que `nom`. Le contrat plateforme
    # exige `nom`. On promote sans muter l'original (la clé `intitule`
    # reste disponible côté UI si besoin).
    if "nom" not in fiche and "intitule" in fiche:
        fiche["nom"] = fiche["intitule"]

    # Sidecar metadata : les scores du retriever, préfixés `_` pour signaler
    # que c'est de la métadonnée (pas du contenu de fiche)
    sidecar = {
        f"_{name}": retrieved[name]
        for name in _RETRIEVER_SCORE_FIELDS
        if name in retrieved
    }
    fiche.update(sidecar)
    return fiche


def _sanitize_question(question: str) -> str:
    """Refuse les tentatives évidentes de prompt-injection, strip control tokens."""
    if any(p.search(question) for p in _INJECTION_PATTERNS):
        raise HTTPException(
            status_code=400,
            detail=(
                "Question rejected by safety filter (potential prompt injection). "
                "Reformule simplement ta demande d'orientation."
            ),
        )
    cleaned = _MISTRAL_CONTROL_TOKENS.sub("", question)
    return cleaned.strip()


# ───────────────────────────── Error handler ────────────────────────────────


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Standardize error response shape pour matcher le contrat."""
    code_map = {
        400: "INVALID_QUESTION",
        401: "UNAUTHORIZED",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMITED",
        500: "INTERNAL",
        503: "SERVICE_UNAVAILABLE",
    }
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=str(exc.detail) if exc.detail else "Internal error",
            code=code_map.get(exc.status_code, "INTERNAL"),
            request_id=getattr(request.state, "request_id", None),
        ).model_dump(),
    )


# ───────────────────────────── Routes ───────────────────────────────────────


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        ok=_pipeline is not None,
        version=_VERSION,
        pipeline_loaded=_pipeline is not None,
        index_size=_index_size,
        time=datetime.now(timezone.utc).isoformat(),
    )


@app.post(
    "/answer",
    response_model=AnswerResponse,
    dependencies=[Depends(verify_bearer)],
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def answer(request: AnswerRequest, http_request: Request) -> AnswerResponse:
    """Synchronous Q→A endpoint. Pure passthrough wrapper around `pipeline.answer()`."""
    _check_rate_limit(http_request)

    if _pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not loaded")

    request_id = http_request.headers.get("x-request-id") or str(uuid.uuid4())
    http_request.state.request_id = request_id

    sanitized = _sanitize_question(request.question)

    t0 = time.perf_counter_ns()
    try:
        history_dicts = (
            [m.model_dump() for m in request.history] if request.history else None
        )
        answer_text, sources_raw = _pipeline.answer(
            sanitized,
            history=history_dicts,
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 (top-level catch is intentional)
        logger.exception(f"Pipeline crash for request {request_id}")
        raise HTTPException(status_code=500, detail=f"Pipeline error: {exc}") from exc

    latency_ms = (time.perf_counter_ns() - t0) / 1_000_000.0

    # Faithfulness mapping : honesty_score continu + flagged.
    # `last_validation` est None quand ScopeClassifier short-circuite
    # (out_of_scope, urgent) — on retourne alors None/None proprement.
    score: float | None = None
    verdict: str | None = None
    last_validation = getattr(_pipeline, "last_validation", None)
    if last_validation is not None:
        score = float(last_validation.honesty_score)
        verdict = "INFIDELE" if last_validation.flagged else "FIDELE"

    # 1. Déballe la fiche brute depuis chaque structure retriever-internal
    # 2. Coerce les types numpy en Python natifs JSON-safe
    sources_clean = [_to_jsonable(_extract_source_fiche(s)) for s in sources_raw]

    response = AnswerResponse(
        answer=answer_text,
        sources=sources_clean,
        faithfulness_score=score,
        faithfulness_verdict=verdict,
        latency_ms=latency_ms,
    )

    logger.info(
        json.dumps(
            {
                "level": "info",
                "request_id": request_id,
                "route": "/answer",
                "latency_ms": round(latency_ms, 2),
                "sources_count": len(sources_raw),
                "honesty_score": score,
                "flagged": last_validation.flagged if last_validation else None,
                "question_len": len(sanitized),
                "history_len": len(request.history) if request.history else 0,
            }
        )
    )

    return response
