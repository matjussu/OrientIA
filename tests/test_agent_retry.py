"""Tests src/agent/retry.py — retry exponential backoff."""
from __future__ import annotations

import pytest

from src.agent.retry import call_with_retry, is_retryable_error


# --- is_retryable_error ---


class TestIsRetryable:
    def test_429_string(self):
        assert is_retryable_error(Exception("Status 429: rate limited"))

    def test_rate_limit_word(self):
        assert is_retryable_error(Exception("Rate limit exceeded"))

    def test_timeout(self):
        assert is_retryable_error(Exception("Request timed out"))

    def test_503_unavailable(self):
        assert is_retryable_error(Exception("503 Service Unavailable"))

    def test_502_bad_gateway(self):
        assert is_retryable_error(Exception("502 Bad Gateway"))

    def test_cloudflare_520(self):
        assert is_retryable_error(Exception("520 Cloudflare error"))

    def test_connection_reset(self):
        assert is_retryable_error(Exception("Connection reset by peer"))

    def test_value_error_not_retryable(self):
        assert not is_retryable_error(ValueError("Bad input"))

    def test_type_error_not_retryable(self):
        assert not is_retryable_error(TypeError("Wrong type"))

    def test_generic_400_not_retryable(self):
        # 400 est une erreur client, pas transitoire
        assert not is_retryable_error(Exception("400 Bad Request"))


# --- call_with_retry ---


class TestCallWithRetry:
    def test_first_attempt_success(self):
        calls = []

        def fn():
            calls.append(1)
            return "ok"

        result = call_with_retry(fn, max_retries=3, initial_backoff=0.01)
        assert result == "ok"
        assert calls == [1]

    def test_retry_then_success(self):
        calls = []

        def fn():
            calls.append(1)
            if len(calls) < 2:
                raise Exception("Status 429: rate limited")
            return "ok"

        result = call_with_retry(fn, max_retries=3, initial_backoff=0.01)
        assert result == "ok"
        assert len(calls) == 2

    def test_max_retries_then_raise(self):
        calls = []

        def fn():
            calls.append(1)
            raise Exception("429 rate limit")

        with pytest.raises(Exception, match="429"):
            call_with_retry(fn, max_retries=3, initial_backoff=0.01)
        assert len(calls) == 3

    def test_non_retryable_raises_immediately(self):
        calls = []

        def fn():
            calls.append(1)
            raise ValueError("Bad input")

        with pytest.raises(ValueError, match="Bad input"):
            call_with_retry(fn, max_retries=5, initial_backoff=0.01)
        assert len(calls) == 1

    def test_max_retries_invalid(self):
        with pytest.raises(ValueError, match="max_retries"):
            call_with_retry(lambda: "ok", max_retries=0)

    def test_on_retry_callback(self):
        callback_calls = []

        def fn():
            if not callback_calls:
                # première fois, fail
                raise Exception("503 unavailable")
            return "ok"

        def on_retry(attempt, sleep_s, exc):
            callback_calls.append((attempt, sleep_s))

        result = call_with_retry(
            fn,
            max_retries=3,
            initial_backoff=0.01,
            on_retry=on_retry,
        )
        assert result == "ok"
        # 1 retry → 1 callback call avec attempt=0
        assert len(callback_calls) == 1
        assert callback_calls[0][0] == 0

    def test_exponential_backoff_growth(self):
        delays = []

        def fn():
            raise Exception("502 bad gateway")

        def on_retry(attempt, sleep_s, exc):
            delays.append(sleep_s)

        with pytest.raises(Exception):
            call_with_retry(
                fn,
                max_retries=4,
                initial_backoff=0.01,
                backoff_multiplier=2.0,
                max_backoff=10.0,
                on_retry=on_retry,
            )
        # 4 retries → 3 sleeps (avant les 3 derniers attempts)
        assert len(delays) == 3
        # Backoff doit croître : 0.01 → 0.02 → 0.04
        assert delays[0] == pytest.approx(0.01)
        assert delays[1] == pytest.approx(0.02)
        assert delays[2] == pytest.approx(0.04)

    def test_max_backoff_cap(self, monkeypatch):
        # Mock time.sleep pour éviter les vraies pauses (test rapide)
        sleep_calls = []
        monkeypatch.setattr("src.agent.retry.time.sleep",
                            lambda s: sleep_calls.append(s))
        delays = []

        def fn():
            raise Exception("503 unavailable")

        def on_retry(attempt, sleep_s, exc):
            delays.append(sleep_s)

        with pytest.raises(Exception):
            call_with_retry(
                fn,
                max_retries=5,
                initial_backoff=10.0,
                backoff_multiplier=2.0,
                max_backoff=15.0,
                on_retry=on_retry,
            )
        # max_backoff=15 capping les sleeps après le 1er
        assert delays[0] == 10.0
        assert delays[1] == 15.0  # capped (would be 20)
        assert delays[2] == 15.0  # capped
        # Vérifie que time.sleep a bien été appelé avec ces valeurs
        assert sleep_calls == [10.0, 15.0, 15.0, 15.0]
