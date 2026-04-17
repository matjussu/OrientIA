"""Phase F.4 — Thread-safe RPM rate limiter.

OpenAI tier-1 caps gpt-4o at 15 RPM (1 call every 4s). Our 7-system
matrix issues 2 OpenAI generation calls per question in parallel,
plus a GPT-4o judge pass. Without throttling, parallel bursts cause
429s and exponential SDK backoff that turns a 30-min run into 8h.

The RateLimiter enforces a minimum interval between acquisitions
across all threads, so the pipeline stays under the provider cap by
construction (no 429s, no backoff).
"""
from __future__ import annotations

import threading
import time

import pytest

from src.eval.rate_limit import RateLimiter


def test_first_acquire_does_not_block():
    limiter = RateLimiter(max_per_minute=60)  # 1 per second
    t0 = time.monotonic()
    limiter.acquire()
    assert time.monotonic() - t0 < 0.05


def test_second_acquire_waits_for_min_interval():
    """At 60 RPM the minimum gap is 1.0s — the second acquire should
    block until that gap has elapsed."""
    limiter = RateLimiter(max_per_minute=60)
    limiter.acquire()
    t0 = time.monotonic()
    limiter.acquire()
    elapsed = time.monotonic() - t0
    assert 0.95 <= elapsed <= 1.15, f"Expected ~1s wait, got {elapsed:.3f}s"


def test_concurrent_acquires_serialise():
    """Three threads each acquiring twice should take ~5 inter-call
    gaps for 6 calls at 60 RPM = ~5s, NOT overlap concurrently."""
    limiter = RateLimiter(max_per_minute=60)

    def worker():
        limiter.acquire()
        limiter.acquire()

    t0 = time.monotonic()
    threads = [threading.Thread(target=worker) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.monotonic() - t0
    # 6 acquires total at 1s min gap = 5 inter-call gaps = ~5s.
    # Allow generous slack for thread scheduling jitter.
    assert 4.5 <= elapsed <= 6.5, f"Expected ~5s, got {elapsed:.2f}s"


def test_high_rpm_has_negligible_overhead():
    """At 6000 RPM the gap is 10ms — overhead must stay tiny so
    high-throughput callers (Mistral, Anthropic) aren't slowed."""
    limiter = RateLimiter(max_per_minute=6000)
    limiter.acquire()
    t0 = time.monotonic()
    for _ in range(10):
        limiter.acquire()
    elapsed = time.monotonic() - t0
    # 10 acquires at 10ms gap = ~100ms total.
    assert elapsed < 0.25, f"Overhead too high: {elapsed:.3f}s"


def test_zero_rpm_raises():
    with pytest.raises(ValueError):
        RateLimiter(max_per_minute=0)


def test_negative_rpm_raises():
    with pytest.raises(ValueError):
        RateLimiter(max_per_minute=-5)


def test_unbounded_limiter_never_blocks():
    """When max_per_minute is None, acquire is a no-op — useful for
    providers without tier-1 limits (Mistral, Anthropic paid)."""
    limiter = RateLimiter(max_per_minute=None)
    t0 = time.monotonic()
    for _ in range(50):
        limiter.acquire()
    assert time.monotonic() - t0 < 0.05
