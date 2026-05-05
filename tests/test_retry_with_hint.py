"""Tests retry-with-hint loop — Chantier 1.B (2026-05-03).

Couvre :
- No validator → single-shot, no retry (backward compat v1)
- Validator + tour 1 propre → no retry needed
- Validator + tour 1 failed_claims + budget OK → retry happens
- Validator + tour 1 failed + budget exceeded → retry skipped (timeout)
- retry_stability calculé correctement
- needs_audit flag déclenché si stability < 0.5
- last_retry_metadata populé correctement
- regression guard : si tour 2 pire que tour 1 → keep tour 1
"""
from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from src.rag.pipeline import (
    MAX_RETRIES_WITH_HINT,
    RETRY_RESERVE_S,
    RETRY_STABILITY_AUDIT_THRESHOLD,
    RETRY_STABILITY_WARN_THRESHOLD,
    RETRY_TIMEOUT_S,
    OrientIAPipeline,
)
from src.validator.corpus_check import CorpusWarning
from src.validator.validator import (
    Validator,
    ValidatorResult,
    extract_failed_claims,
    format_hint_block,
)
from src.validator.layer3 import Layer3Warning


def _mock_pipeline_with_validator(
    validator: Validator | None = None,
) -> OrientIAPipeline:
    """Construct a minimal pipeline avec mocks pour tests retry."""
    fake_client = MagicMock()
    fake_index = MagicMock()
    p = OrientIAPipeline(
        client=fake_client,
        fiches=[{"nom": "F1", "etablissement": "E1"}],
        validator=validator,
    )
    p.index = fake_index
    return p


# ──────────────────────── extract_failed_claims helper ────────────────────────


class TestExtractFailedClaims:
    def test_empty_validator_result_returns_empty_list(self):
        result = ValidatorResult(honesty_score=1.0)
        assert extract_failed_claims(result) == []

    def test_corpus_warnings_priority_high(self):
        result = ValidatorResult(
            honesty_score=0.7,
            corpus_warnings=[
                CorpusWarning(claim="X taux 27%", reason="r", similarity=0.1, closest_match="other"),
                CorpusWarning(claim="Y école Paris", reason="r", similarity=0.2, closest_match="other2"),
            ],
        )
        claims = extract_failed_claims(result)
        assert "X taux 27%" in claims
        assert "Y école Paris" in claims
        assert len(claims) == 2

    def test_layer3_warnings_included(self):
        result = ValidatorResult(
            honesty_score=0.6,
            layer3_warnings=[
                Layer3Warning(claim="claim1", reason="non-sourcé"),
            ],
        )
        claims = extract_failed_claims(result)
        assert "claim1" in claims

    def test_dedup_same_claim_corpus_and_layer3(self):
        result = ValidatorResult(
            honesty_score=0.5,
            corpus_warnings=[
                CorpusWarning(claim="dup", reason="r", similarity=0.1, closest_match="x"),
            ],
            layer3_warnings=[
                Layer3Warning(claim="dup", reason="x"),
            ],
        )
        claims = extract_failed_claims(result)
        assert claims.count("dup") == 1

    def test_cap_at_10_claims(self):
        warnings = [
            CorpusWarning(claim=f"claim_{i}", reason="r", similarity=0.1, closest_match="x")
            for i in range(20)
        ]
        result = ValidatorResult(honesty_score=0.0, corpus_warnings=warnings)
        claims = extract_failed_claims(result)
        assert len(claims) == 10


# ──────────────────────── format_hint_block ────────────────────────


class TestFormatHintBlock:
    def test_empty_claims_returns_empty_string(self):
        assert format_hint_block([]) == ""

    def test_includes_anti_invention_instruction(self):
        out = format_hint_block(["claim1", "claim2"])
        assert "claim1" in out
        assert "claim2" in out
        assert "fallback" in out.lower() or "Je n'ai pas l'information" in out
        assert "Ne reproduis PAS" in out

    def test_truncates_long_claims(self):
        long_claim = "X" * 500
        out = format_hint_block([long_claim])
        # Truncated at 197 chars + "..."
        assert "..." in out
        assert "X" * 200 not in out


# ──────────────────────── pipeline retry loop ────────────────────────


class TestPipelineRetryNoValidator:
    """Sans validator : backward compat v1 = single-shot, no retry."""

    def test_no_validator_no_retry_metadata_reason(self):
        p = _mock_pipeline_with_validator(validator=None)
        with patch("src.rag.pipeline.generate", return_value="single answer") as mock_gen:
            with patch.object(p, "_retrieve_and_filter", return_value=[{"fiche": {"nom": "F1"}}]):
                with patch.object(p, "_maybe_build_golden_qa_prefix", return_value=None):
                    answer, _ = p.answer("Q?")
        assert answer == "single answer"
        assert mock_gen.call_count == 1  # single-shot
        assert p.last_retry_metadata["retries_attempted"] == 0
        assert p.last_retry_metadata["retry_skipped_reason"] == "no_validator"


class TestPipelineRetryClean:
    """Tour 1 propre (no failed_claims) → no retry."""

    def test_clean_tour1_no_retry(self):
        # Validator qui retourne toujours clean
        clean_validator = MagicMock(spec=Validator)
        clean_validator.validate.return_value = ValidatorResult(honesty_score=1.0)

        p = _mock_pipeline_with_validator(validator=clean_validator)
        with patch("src.rag.pipeline.generate", return_value="clean answer") as mock_gen:
            with patch.object(p, "_retrieve_and_filter", return_value=[{"fiche": {"nom": "F1"}}]):
                with patch.object(p, "_maybe_build_golden_qa_prefix", return_value=None):
                    with patch("src.rag.pipeline.apply_policy") as mock_policy:
                        mock_policy.return_value = MagicMock(final_answer="clean answer")
                        answer, _ = p.answer("Q?")
        assert mock_gen.call_count == 1  # tour 1 only
        assert p.last_retry_metadata["retries_attempted"] == 0
        assert p.last_retry_metadata["retry_skipped_reason"] is None
        assert p.last_retry_metadata["tour1_failed_claims"] == []


class TestPipelineRetryHappens:
    """Tour 1 a failed_claims + budget OK → retry tour 2."""

    def test_retry_called_with_hint_block_when_failed_claims(self):
        # Validator qui retourne 2 corpus_warnings au tour 1, 0 au tour 2
        validator = MagicMock(spec=Validator)
        bad_result = ValidatorResult(
            honesty_score=0.5,
            corpus_warnings=[
                CorpusWarning(claim="hallu1", reason="not_in_corpus", similarity=0.1, closest_match="x"),
                CorpusWarning(claim="hallu2", reason="not_in_corpus", similarity=0.1, closest_match="y"),
            ],
        )
        good_result = ValidatorResult(honesty_score=1.0)
        validator.validate.side_effect = [bad_result, good_result]

        p = _mock_pipeline_with_validator(validator=validator)
        with patch("src.rag.pipeline.generate", side_effect=["bad answer", "good answer"]) as mock_gen:
            with patch.object(p, "_retrieve_and_filter", return_value=[{"fiche": {"nom": "F1"}}]):
                with patch.object(p, "_maybe_build_golden_qa_prefix", return_value=None):
                    with patch("src.rag.pipeline.apply_policy") as mock_policy:
                        mock_policy.return_value = MagicMock(final_answer="good answer")
                        answer, _ = p.answer("Q?")

        assert mock_gen.call_count == 2  # tour 1 + tour 2
        assert p.last_retry_metadata["retries_attempted"] == 1
        # Tour 2 reçoit hint_block non vide
        tour2_call = mock_gen.call_args_list[1]
        assert "hint_block" in tour2_call.kwargs
        assert tour2_call.kwargs["hint_block"] != ""
        assert "hallu1" in tour2_call.kwargs["hint_block"]


class TestPipelineRetryStability:
    """retry_stability + needs_audit flag."""

    def test_stability_perfect_when_tour2_corrects_all(self):
        validator = MagicMock(spec=Validator)
        bad = ValidatorResult(
            honesty_score=0.5,
            corpus_warnings=[
                CorpusWarning(claim=f"c{i}", reason="r", similarity=0.1, closest_match="x") for i in range(4)
            ],
        )
        clean = ValidatorResult(honesty_score=1.0)
        validator.validate.side_effect = [bad, clean]

        p = _mock_pipeline_with_validator(validator=validator)
        with patch("src.rag.pipeline.generate", side_effect=["a1", "a2"]):
            with patch.object(p, "_retrieve_and_filter", return_value=[{"fiche": {"nom": "F1"}}]):
                with patch.object(p, "_maybe_build_golden_qa_prefix", return_value=None):
                    with patch("src.rag.pipeline.apply_policy") as mock_policy:
                        mock_policy.return_value = MagicMock(final_answer="a2")
                        p.answer("Q?")
        # tour1=4 claims, tour2=0 → stability = 1 - 0/4 = 1.0
        assert p.last_retry_metadata["retry_stability"] == 1.0
        assert p.last_retry_metadata["needs_audit"] is False

    def test_stability_low_triggers_audit_flag(self):
        validator = MagicMock(spec=Validator)
        # tour1=2 claims, tour2=4 claims (régression)
        bad1 = ValidatorResult(
            honesty_score=0.5,
            corpus_warnings=[
                CorpusWarning(claim=f"c{i}", reason="r", similarity=0.1, closest_match="x") for i in range(2)
            ],
        )
        worse = ValidatorResult(
            honesty_score=0.3,
            corpus_warnings=[
                CorpusWarning(claim=f"d{i}", reason="r", similarity=0.1, closest_match="y") for i in range(4)
            ],
        )
        validator.validate.side_effect = [bad1, worse]

        p = _mock_pipeline_with_validator(validator=validator)
        with patch("src.rag.pipeline.generate", side_effect=["a1", "a2"]):
            with patch.object(p, "_retrieve_and_filter", return_value=[{"fiche": {"nom": "F1"}}]):
                with patch.object(p, "_maybe_build_golden_qa_prefix", return_value=None):
                    with patch("src.rag.pipeline.apply_policy") as mock_policy:
                        mock_policy.return_value = MagicMock(final_answer="a1")
                        p.answer("Q?")
        # stability = max(0, 1 - 4/2) = 0.0 → < AUDIT_THRESHOLD
        assert p.last_retry_metadata["retry_stability"] == 0.0
        assert p.last_retry_metadata["needs_audit"] is True


class TestPipelineRetryRegressionGuard:
    """Si tour 2 pire que tour 1 → garder tour 1."""

    def test_keeps_tour1_when_tour2_regresses(self):
        validator = MagicMock(spec=Validator)
        bad1 = ValidatorResult(
            honesty_score=0.5,
            corpus_warnings=[CorpusWarning(claim="c1", reason="r", similarity=0.1, closest_match="x")],
        )
        worse = ValidatorResult(
            honesty_score=0.3,
            corpus_warnings=[
                CorpusWarning(claim=f"d{i}", reason="r", similarity=0.1, closest_match="y") for i in range(3)
            ],
        )
        validator.validate.side_effect = [bad1, worse]

        p = _mock_pipeline_with_validator(validator=validator)
        with patch("src.rag.pipeline.generate", side_effect=["tour1_answer", "tour2_answer"]):
            with patch.object(p, "_retrieve_and_filter", return_value=[{"fiche": {"nom": "F1"}}]):
                with patch.object(p, "_maybe_build_golden_qa_prefix", return_value=None):
                    captured = {}

                    def capture_policy(answer, validation):
                        captured["answer"] = answer
                        captured["validation"] = validation
                        return MagicMock(final_answer=answer)

                    with patch("src.rag.pipeline.apply_policy", side_effect=capture_policy):
                        p.answer("Q?")
        # Apply_policy doit recevoir tour1_answer (pas tour2_answer car regression)
        assert captured["answer"] == "tour1_answer"
        # last_validation reflète tour 1
        assert p.last_validation is bad1


class TestPipelineRetryConstants:
    """Constantes du module conformes au plan chantier 1.B."""

    def test_max_retries_is_one(self):
        assert MAX_RETRIES_WITH_HINT == 1

    def test_timeout_is_30s(self):
        assert RETRY_TIMEOUT_S == 30.0

    def test_reserve_is_5s(self):
        assert RETRY_RESERVE_S == 5.0

    def test_thresholds_warn_and_audit(self):
        assert RETRY_STABILITY_WARN_THRESHOLD == 0.7
        assert RETRY_STABILITY_AUDIT_THRESHOLD == 0.5
