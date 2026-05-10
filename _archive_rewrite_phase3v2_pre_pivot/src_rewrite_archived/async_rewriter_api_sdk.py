"""Runner async du rewriting Haiku — ADR-060.

Appelle Claude Haiku 4.5 directement via ``anthropic.AsyncAnthropic`` avec :
- ``asyncio.Semaphore`` pour borner la concurrence (default 15)
- retry exponentiel sur 429 / 5xx (3 essais max)
- save incrémental ligne-à-ligne en JSONL pour resume native (skip déjà-faits)
- progress callback optionnel

Pas de Batch API (cf ADR-060 §Rationale §3 : simplicité opérationnelle,
coût additionnel négligeable).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable

from anthropic import AsyncAnthropic
from anthropic._exceptions import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    RateLimitError,
)

from src.rewrite.prompts import build_messages, get_system_prompt

logger = logging.getLogger(__name__)


DEFAULT_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_MAX_TOKENS = 700  # ~250 mots × ~2.5 tokens/mot + marge
DEFAULT_CONCURRENCY = 15
DEFAULT_MAX_RETRIES = 3


# -----------------------------------------------------------------------------
# Types
# -----------------------------------------------------------------------------


@dataclass
class RewriteResult:
    """Résultat d'un rewrite individuel (succès ou échec)."""

    fiche_id: str
    rewritten_text: str | None  # None si erreur
    input_tokens: int = 0
    output_tokens: int = 0
    error: str | None = None
    n_attempts: int = 1

    def to_jsonl_line(self) -> str:
        return json.dumps(
            {
                "fiche_id": self.fiche_id,
                "rewritten_text": self.rewritten_text,
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "error": self.error,
                "n_attempts": self.n_attempts,
            },
            ensure_ascii=False,
        )

    @classmethod
    def from_jsonl_line(cls, line: str) -> "RewriteResult":
        d = json.loads(line)
        return cls(
            fiche_id=d["fiche_id"],
            rewritten_text=d.get("rewritten_text"),
            input_tokens=d.get("input_tokens", 0),
            output_tokens=d.get("output_tokens", 0),
            error=d.get("error"),
            n_attempts=d.get("n_attempts", 1),
        )


@dataclass
class RunStats:
    n_total: int = 0
    n_succeeded: int = 0
    n_failed: int = 0
    n_skipped_resume: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0


# -----------------------------------------------------------------------------
# Resume support
# -----------------------------------------------------------------------------


def load_existing_results(jsonl_path: Path) -> dict[str, RewriteResult]:
    """Charge les résultats déjà produits depuis un JSONL existant.

    Permet de skip les fiches déjà rewrites lors d'un re-run.
    """
    out: dict[str, RewriteResult] = {}
    if not jsonl_path.exists():
        return out
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = RewriteResult.from_jsonl_line(line)
                # Ne resume que les succès (errors → on retente)
                if r.rewritten_text is not None and not r.error:
                    out[r.fiche_id] = r
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Skipping malformed JSONL line: {e}")
    return out


# -----------------------------------------------------------------------------
# Retry
# -----------------------------------------------------------------------------


_RETRY_EXC = (
    RateLimitError,
    APIConnectionError,
    APITimeoutError,
)


async def _call_with_retry(
    client: AsyncAnthropic,
    *,
    model: str,
    max_tokens: int,
    system: str,
    messages: list[dict[str, str]],
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> tuple[Any, int]:
    """Retry exponentiel sur 429 / 5xx / timeouts. Renvoie (msg, n_attempts)."""
    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            msg = await client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
            )
            return msg, attempt
        except _RETRY_EXC as e:
            last_exc = e
            if attempt >= max_retries:
                break
            backoff = (2 ** (attempt - 1)) + random.uniform(0, 1)
            logger.warning(
                f"Retry {attempt}/{max_retries} after {type(e).__name__}: "
                f"sleep {backoff:.1f}s"
            )
            await asyncio.sleep(backoff)
        except APIStatusError as e:
            # 5xx → retry, 4xx → fail fast
            last_exc = e
            if 500 <= e.status_code < 600 and attempt < max_retries:
                backoff = (2 ** (attempt - 1)) + random.uniform(0, 1)
                logger.warning(
                    f"Retry {attempt}/{max_retries} after {e.status_code}: "
                    f"sleep {backoff:.1f}s"
                )
                await asyncio.sleep(backoff)
            else:
                break
    raise last_exc  # type: ignore[misc]


# -----------------------------------------------------------------------------
# Single-fiche rewriter
# -----------------------------------------------------------------------------


async def rewrite_one(
    client: AsyncAnthropic,
    fiche: dict,
    *,
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    with_few_shot: bool = True,
) -> RewriteResult:
    """Rewrite une seule fiche. Capture toutes les exceptions en résultat."""
    fiche_id = fiche.get("id", "")
    try:
        system = get_system_prompt()
        messages = build_messages(fiche, with_few_shot=with_few_shot)
        msg, n_attempts = await _call_with_retry(
            client,
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        )
        text = ""
        for block in msg.content:
            if getattr(block, "type", None) == "text":
                text += block.text
        text = text.strip()
        # Strip éventuels guillemets enveloppants
        if text.startswith('"') and text.endswith('"') and text.count('"') == 2:
            text = text[1:-1].strip()
        return RewriteResult(
            fiche_id=fiche_id,
            rewritten_text=text,
            input_tokens=msg.usage.input_tokens,
            output_tokens=msg.usage.output_tokens,
            n_attempts=n_attempts,
        )
    except Exception as e:  # noqa: BLE001
        logger.error(f"Rewrite failed for {fiche_id}: {type(e).__name__}: {e}")
        return RewriteResult(
            fiche_id=fiche_id,
            rewritten_text=None,
            error=f"{type(e).__name__}: {e}",
        )


# -----------------------------------------------------------------------------
# Batched runner
# -----------------------------------------------------------------------------


ProgressCallback = Callable[[RewriteResult, RunStats], Awaitable[None] | None]


async def run_rewrite_batch(
    fiches: list[dict],
    *,
    api_key: str | None = None,
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    concurrency: int = DEFAULT_CONCURRENCY,
    progress_path: Path | None = None,
    progress_callback: ProgressCallback | None = None,
    with_few_shot: bool = True,
    resume: bool = True,
) -> tuple[dict[str, str], RunStats]:
    """Lance le rewrite async sur ``fiches``.

    Args:
        fiches: liste des fiches à rewriter (uniquement annexes).
        api_key: clé Anthropic (sinon ``ANTHROPIC_API_KEY`` env).
        progress_path: si fourni, écrit chaque résultat en JSONL au fil de
            l'eau (pour resume).
        resume: si True et ``progress_path`` existe, skip les fiches déjà
            faites avec succès.

    Returns:
        (rewrites_dict, stats)
        ``rewrites_dict`` : ``{fiche_id: rewritten_text}`` pour les
        fiches dont le rewrite a abouti. Les échecs n'apparaissent pas.
    """
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY missing")

    stats = RunStats(n_total=len(fiches))

    # Resume
    existing: dict[str, RewriteResult] = {}
    if resume and progress_path is not None:
        existing = load_existing_results(progress_path)
        logger.info(f"Resume : {len(existing)} fiches déjà rewrites trouvées")

    # File for incremental save (append mode)
    f_out = None
    if progress_path is not None:
        progress_path.parent.mkdir(parents=True, exist_ok=True)
        f_out = progress_path.open("a", encoding="utf-8")

    rewrites: dict[str, str] = {
        fid: r.rewritten_text  # type: ignore[misc]
        for fid, r in existing.items()
        if r.rewritten_text is not None
    }
    stats.n_skipped_resume = len(existing)
    stats.n_succeeded = len(existing)
    stats.total_input_tokens = sum(r.input_tokens for r in existing.values())
    stats.total_output_tokens = sum(r.output_tokens for r in existing.values())

    todo = [f for f in fiches if f.get("id") not in existing]
    logger.info(
        f"Run : {len(todo)} fiches à rewriter ({stats.n_skipped_resume} skipped resume)"
    )

    client = AsyncAnthropic(api_key=api_key)
    semaphore = asyncio.Semaphore(concurrency)

    async def worker(fiche: dict) -> RewriteResult:
        async with semaphore:
            return await rewrite_one(
                client,
                fiche,
                model=model,
                max_tokens=max_tokens,
                with_few_shot=with_few_shot,
            )

    try:
        # asyncio.as_completed pour saver dès qu'un résultat tombe
        coros = [worker(f) for f in todo]
        for completed in asyncio.as_completed(coros):
            result = await completed
            if result.rewritten_text is not None:
                rewrites[result.fiche_id] = result.rewritten_text
                stats.n_succeeded += 1
                stats.total_input_tokens += result.input_tokens
                stats.total_output_tokens += result.output_tokens
            else:
                stats.n_failed += 1
            if f_out is not None:
                f_out.write(result.to_jsonl_line() + "\n")
                f_out.flush()
            if progress_callback is not None:
                cb_ret = progress_callback(result, stats)
                if asyncio.iscoroutine(cb_ret):
                    await cb_ret
    finally:
        if f_out is not None:
            f_out.close()
        await client.close()

    return rewrites, stats


def estimate_cost(
    n_fiches: int,
    *,
    avg_input_tokens: int = 1500,
    avg_output_tokens: int = 350,
) -> float:
    """Estimation grossière du coût Haiku 4.5 direct API en USD.

    Tarifs Haiku 4.5 (2026-05) : $1 / MTok input, $5 / MTok output.
    """
    INPUT_PRICE_PER_MTOK = 1.0
    OUTPUT_PRICE_PER_MTOK = 5.0
    cost_in = n_fiches * avg_input_tokens / 1_000_000 * INPUT_PRICE_PER_MTOK
    cost_out = n_fiches * avg_output_tokens / 1_000_000 * OUTPUT_PRICE_PER_MTOK
    return cost_in + cost_out
