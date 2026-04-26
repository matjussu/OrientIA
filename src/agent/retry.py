"""Retry exponential backoff helper — partagé pour tools agentiques.

Adresse les caveats Sprint 1 (PR #76 retro) :
- Rate limit 429 Mistral Large hit pendant integration test ProfileClarifier
- Pattern à intégrer dans tous les tools Sprint 2-4 (vs caller-side)

Pattern : `call_with_retry(fn, max_retries=3, initial_backoff=2.0)`
- Détecte 429 / 5xx / timeout via inspection string de l'exception
- Backoff exponentiel : 2s → 4s → 8s (max_backoff cap)
- Re-raise l'exception finale après épuisement des retries
- Exceptions non-retryable propagent immédiatement (validation,
  TypeError, etc.)

Inspirée de `src/eval/rate_limit.py` (déjà utilisé pour OpenAI tier-1)
mais sans dépendance state — appelable ad-hoc autour de n'importe
quelle lambda.
"""
from __future__ import annotations

import time
from typing import Any, Callable, TypeVar


T = TypeVar("T")


# Patterns de détection retryable sur la string de l'exception
RETRYABLE_INDICATORS = (
    "429",        # rate limit explicit
    "rate_limit",
    "rate limit",
    "ratelimit",
    "timeout",
    "timed out",
    "503",        # service unavailable
    "502",        # bad gateway
    "504",        # gateway timeout
    "520",        # cloudflare ADR-047
    "522",
    "524",
    "connection reset",
    "connection refused",
    "temporarily unavailable",
)


def is_retryable_error(exc: BaseException) -> bool:
    """True si l'exception ressemble à une erreur transitoire."""
    err_str = str(exc).lower()
    return any(indicator in err_str for indicator in RETRYABLE_INDICATORS)


def call_with_retry(
    fn: Callable[[], T],
    *,
    max_retries: int = 3,
    initial_backoff: float = 2.0,
    max_backoff: float = 30.0,
    backoff_multiplier: float = 2.0,
    on_retry: Callable[[int, float, BaseException], None] | None = None,
) -> T:
    """Exécute `fn()` avec retry exponential backoff sur erreurs transitoires.

    Args:
        fn: callable sans argument (utiliser lambda pour curry).
        max_retries: nombre total de tentatives (incluant la première).
        initial_backoff: délai après le 1er échec, en secondes.
        max_backoff: cap maximum du délai entre 2 retries.
        backoff_multiplier: facteur d'expansion exponentielle (2.0 = double).
        on_retry: callback optionnel (attempt_index, sleep_s, exception)
            invoqué AVANT chaque retry. Useful pour logging tests.

    Returns:
        Le résultat de fn() en cas de succès.

    Raises:
        L'exception non-retryable immédiatement, ou la dernière
        exception retryable après épuisement de max_retries.
    """
    if max_retries < 1:
        raise ValueError("max_retries doit être >= 1")

    backoff = initial_backoff
    last_exc: BaseException | None = None

    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            if not is_retryable_error(exc):
                raise
            if attempt == max_retries - 1:
                # Dernière tentative déjà faite, on re-raise
                raise
            sleep_s = min(backoff, max_backoff)
            if on_retry is not None:
                on_retry(attempt, sleep_s, exc)
            time.sleep(sleep_s)
            backoff *= backoff_multiplier

    # Unreachable mais sécurise le typage
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("call_with_retry: state inattendu (no exc, no return)")
