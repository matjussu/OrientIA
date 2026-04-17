"""Thread-safe RPM rate limiter for outbound API calls.

Enforces a minimum interval between acquires across all threads. Used
to stay below provider-side request-per-minute caps (notably OpenAI
tier-1 = 15 RPM for gpt-4o) so the SDK never sees a 429 and never
triggers exponential backoff.

Usage:
    limiter = RateLimiter(max_per_minute=12)
    ...
    limiter.acquire()
    response = openai_client.chat.completions.create(...)
"""
from __future__ import annotations

import threading
import time
from typing import Optional


class RateLimiter:
    """Serialise calls so that no more than max_per_minute happen
    in any 60-second window.

    Implementation: track the last acquire timestamp under a lock,
    sleep just long enough to honor the minimum interval before
    releasing the next caller. Simpler and less leaky than a token
    bucket for the steady-state workload we have here.
    """

    def __init__(self, max_per_minute: Optional[int]):
        if max_per_minute is None:
            self._min_interval = 0.0
        elif max_per_minute <= 0:
            raise ValueError(
                f"max_per_minute must be positive or None, got {max_per_minute}"
            )
        else:
            self._min_interval = 60.0 / max_per_minute
        self._lock = threading.Lock()
        self._last_call = 0.0

    def acquire(self) -> None:
        if self._min_interval == 0.0:
            return
        with self._lock:
            now = time.monotonic()
            wait = self._min_interval - (now - self._last_call)
            if wait > 0:
                time.sleep(wait)
                self._last_call = time.monotonic()
            else:
                self._last_call = now
