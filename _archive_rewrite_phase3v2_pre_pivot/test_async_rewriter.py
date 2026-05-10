"""Tests pour ``src.rewrite.async_rewriter`` (avec mocks Anthropic SDK)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.rewrite.async_rewriter import (
    DEFAULT_MODEL,
    RewriteResult,
    RunStats,
    estimate_cost,
    load_existing_results,
    rewrite_one,
    run_rewrite_batch,
)


# -----------------------------------------------------------------------------
# RewriteResult JSONL roundtrip
# -----------------------------------------------------------------------------


class TestRewriteResultJsonl:
    def test_roundtrip(self):
        r = RewriteResult(
            fiche_id="rome:M1402",
            rewritten_text="Le métier...",
            input_tokens=1200,
            output_tokens=180,
            n_attempts=1,
        )
        line = r.to_jsonl_line()
        r2 = RewriteResult.from_jsonl_line(line)
        assert r2.fiche_id == r.fiche_id
        assert r2.rewritten_text == r.rewritten_text
        assert r2.input_tokens == r.input_tokens
        assert r2.output_tokens == r.output_tokens

    def test_error_roundtrip(self):
        r = RewriteResult(
            fiche_id="x:1",
            rewritten_text=None,
            error="RateLimitError: too many",
        )
        line = r.to_jsonl_line()
        r2 = RewriteResult.from_jsonl_line(line)
        assert r2.error == "RateLimitError: too many"
        assert r2.rewritten_text is None


# -----------------------------------------------------------------------------
# load_existing_results
# -----------------------------------------------------------------------------


class TestLoadExisting:
    def test_returns_empty_dict_if_no_file(self, tmp_path):
        path = tmp_path / "no.jsonl"
        out = load_existing_results(path)
        assert out == {}

    def test_loads_successful_results_only(self, tmp_path):
        path = tmp_path / "p.jsonl"
        path.write_text(
            "\n".join(
                [
                    json.dumps({"fiche_id": "a", "rewritten_text": "ok", "input_tokens": 1, "output_tokens": 1}),
                    json.dumps({"fiche_id": "b", "rewritten_text": None, "error": "fail"}),
                    json.dumps({"fiche_id": "c", "rewritten_text": "ok2", "input_tokens": 1, "output_tokens": 1}),
                ]
            ),
            encoding="utf-8",
        )
        out = load_existing_results(path)
        assert set(out.keys()) == {"a", "c"}  # 'b' skipped (error)

    def test_skips_malformed_lines(self, tmp_path):
        path = tmp_path / "p.jsonl"
        path.write_text(
            "\n".join(
                [
                    json.dumps({"fiche_id": "a", "rewritten_text": "ok"}),
                    "not_valid_json{{",
                    "",
                    json.dumps({"fiche_id": "c", "rewritten_text": "ok2"}),
                ]
            ),
            encoding="utf-8",
        )
        out = load_existing_results(path)
        assert set(out.keys()) == {"a", "c"}


# -----------------------------------------------------------------------------
# rewrite_one (mock client)
# -----------------------------------------------------------------------------


def _make_mock_msg(text: str, in_tok: int = 1000, out_tok: int = 200):
    msg = MagicMock()
    block = MagicMock()
    block.type = "text"
    block.text = text
    msg.content = [block]
    msg.usage.input_tokens = in_tok
    msg.usage.output_tokens = out_tok
    return msg


def test_rewrite_one_success():
    async def _run():
        client = MagicMock()
        client.messages.create = AsyncMock(
            return_value=_make_mock_msg("Le CROUS de Lyon gère 12000 logements.")
        )
        fiche = {"id": "crous:lyon", "domain": "crous", "n_logements": 12000}
        result = await rewrite_one(client, fiche, with_few_shot=False)
        assert result.fiche_id == "crous:lyon"
        assert "12000" in result.rewritten_text
        assert result.error is None
        assert result.input_tokens == 1000
        assert result.output_tokens == 200

    asyncio.run(_run())


def test_rewrite_one_strips_wrapping_quotes():
    async def _run():
        client = MagicMock()
        client.messages.create = AsyncMock(
            return_value=_make_mock_msg('"Le CROUS de Lyon gère 12000 logements."')
        )
        fiche = {"id": "crous:lyon", "domain": "crous"}
        result = await rewrite_one(client, fiche, with_few_shot=False)
        assert not result.rewritten_text.startswith('"')
        assert not result.rewritten_text.endswith('"')

    asyncio.run(_run())


def test_rewrite_one_captures_exception():
    async def _run():
        client = MagicMock()
        client.messages.create = AsyncMock(side_effect=ValueError("boom"))
        fiche = {"id": "x:1", "domain": "crous"}
        result = await rewrite_one(client, fiche, with_few_shot=False)
        assert result.rewritten_text is None
        assert result.error is not None
        assert "boom" in result.error

    asyncio.run(_run())


# -----------------------------------------------------------------------------
# run_rewrite_batch (mock + tmp_path)
# -----------------------------------------------------------------------------


def test_run_batch_basic_success(tmp_path, monkeypatch):
    """Mock AsyncAnthropic to return canned results, vérifie agrégation."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")

    async def _run():
        fiches = [
            {"id": "a", "domain": "crous", "n": 100},
            {"id": "b", "domain": "crous", "n": 200},
            {"id": "c", "domain": "crous", "n": 300},
        ]

        async def fake_create(**kwargs):
            return _make_mock_msg(
                "Rewrite simulé pour test.", in_tok=500, out_tok=100
            )

        fake_client_instance = MagicMock()
        fake_client_instance.messages.create = AsyncMock(side_effect=fake_create)
        fake_client_instance.close = AsyncMock()

        with patch(
            "src.rewrite.async_rewriter.AsyncAnthropic",
            return_value=fake_client_instance,
        ):
            progress_path = tmp_path / "progress.jsonl"
            rewrites, stats = await run_rewrite_batch(
                fiches,
                progress_path=progress_path,
                with_few_shot=False,
                concurrency=2,
                resume=False,
            )

        assert stats.n_total == 3
        assert stats.n_succeeded == 3
        assert stats.n_failed == 0
        assert len(rewrites) == 3
        assert all(fid in rewrites for fid in ("a", "b", "c"))
        assert progress_path.exists()
        lines = [l for l in progress_path.read_text().splitlines() if l.strip()]
        assert len(lines) == 3

    asyncio.run(_run())


def test_run_batch_resume_skips_done(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")

    progress_path = tmp_path / "progress.jsonl"
    progress_path.write_text(
        json.dumps(
            {
                "fiche_id": "a",
                "rewritten_text": "OK pré-existant",
                "input_tokens": 100,
                "output_tokens": 50,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    async def _run():
        fiches = [
            {"id": "a", "domain": "crous"},
            {"id": "b", "domain": "crous"},
            {"id": "c", "domain": "crous"},
        ]

        n_calls = 0

        async def fake_create(**kwargs):
            nonlocal n_calls
            n_calls += 1
            return _make_mock_msg("Rewrite test.", in_tok=200, out_tok=80)

        fake_client_instance = MagicMock()
        fake_client_instance.messages.create = AsyncMock(side_effect=fake_create)
        fake_client_instance.close = AsyncMock()

        with patch(
            "src.rewrite.async_rewriter.AsyncAnthropic",
            return_value=fake_client_instance,
        ):
            rewrites, stats = await run_rewrite_batch(
                fiches,
                progress_path=progress_path,
                with_few_shot=False,
                resume=True,
            )

        assert n_calls == 2
        assert stats.n_skipped_resume == 1
        assert rewrites["a"] == "OK pré-existant"
        assert "b" in rewrites and "c" in rewrites

    asyncio.run(_run())


def test_run_batch_partial_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")

    async def _run():
        fiches = [{"id": str(i), "domain": "crous"} for i in range(5)]
        call_count = 0

        async def fake_create(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:
                raise ValueError("simulated failure")
            return _make_mock_msg("OK", in_tok=100, out_tok=30)

        fake_client_instance = MagicMock()
        fake_client_instance.messages.create = AsyncMock(side_effect=fake_create)
        fake_client_instance.close = AsyncMock()

        with patch(
            "src.rewrite.async_rewriter.AsyncAnthropic",
            return_value=fake_client_instance,
        ):
            rewrites, stats = await run_rewrite_batch(
                fiches,
                progress_path=tmp_path / "p.jsonl",
                with_few_shot=False,
                concurrency=1,
                resume=False,
            )

        assert stats.n_total == 5
        assert stats.n_succeeded + stats.n_failed == 5
        assert stats.n_failed >= 1

    asyncio.run(_run())


# -----------------------------------------------------------------------------
# Cost estimate
# -----------------------------------------------------------------------------


class TestEstimateCost:
    def test_baseline_run(self):
        # 13 417 fiches × 1500 in × 350 out
        cost = estimate_cost(13417)
        # 13417 * 1500 / 1M * 1 = $20.13 input
        # 13417 * 350 / 1M * 5 = $23.48 output
        # ~$43.6 → mais Haiku réel est plus bas (les fiches sont courtes)
        assert 5 < cost < 50

    def test_zero_fiches_zero_cost(self):
        assert estimate_cost(0) == 0.0
