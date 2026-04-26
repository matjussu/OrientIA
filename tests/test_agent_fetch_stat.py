"""Tests src/agent/tools/fetch_stat_from_source.py — StatVerification + tool func + FetchStatFromSource (mocked)."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from src.agent.tools.fetch_stat_from_source import (
    FETCH_STAT_TOOL,
    FetchStatFromSource,
    Source,
    StatVerification,
    VALID_VERDICTS,
    _fetch_stat_tool_func,
)


# --- StatVerification dataclass ---


class TestStatVerification:
    def test_supported_verdict(self):
        v = StatVerification(
            claim="Master psycho exige bac+5",
            verdict="supported",
            source_excerpt="Le titre de psychologue exige obligatoirement un master bac+5 niveau 7",
            reason="Source mentionne explicit le niveau 7 obligatoire",
            confidence=0.92,
        )
        assert v.is_valid()
        assert v.is_supported is True
        assert v.is_problematic is False

    def test_contradicted_problematic(self):
        v = StatVerification(
            claim="Titre RNCP psycho niveau 6",
            verdict="contradicted",
            source_excerpt="Master bac+5 niveau 7 obligatoire",
            reason="Source contredit le niveau",
            confidence=0.95,
        )
        assert v.is_valid()
        assert v.is_supported is False
        assert v.is_problematic is True

    def test_unsupported_problematic(self):
        v = StatVerification(
            claim="claim aléatoire",
            verdict="unsupported",
            source_excerpt=None,
            reason="Aucune source ne mentionne ce claim",
            confidence=0.8,
        )
        assert v.is_valid()
        assert v.is_problematic is True

    def test_ambiguous_problematic_no(self):
        # Ambiguous = ni clean ni problématique flagrant
        v = StatVerification(
            claim="claim partiel",
            verdict="ambiguous",
            source_excerpt=None,
            reason="Source partielle",
            confidence=0.5,
        )
        assert v.is_valid()
        assert v.is_problematic is False  # ambiguous = pas problématique au sens strict

    def test_invalid_verdict(self):
        v = StatVerification(
            claim="x",
            verdict="invalid_xxx",
            source_excerpt=None,
            reason="",
            confidence=0.5,
        )
        assert not v.is_valid()

    def test_invalid_confidence_out_of_bounds(self):
        v = StatVerification(
            claim="x",
            verdict="supported",
            source_excerpt="src",
            reason="r",
            confidence=1.5,
        )
        assert not v.is_valid()

    def test_empty_claim_invalid(self):
        v = StatVerification(
            claim="",
            verdict="unsupported",
            source_excerpt=None,
            reason="empty",
            confidence=0.5,
        )
        assert not v.is_valid()


# --- Tool func wrapper ---


class TestFetchStatToolFunc:
    def test_valid_supported(self):
        result = _fetch_stat_tool_func(
            verdict="supported",
            source_excerpt="Master niveau 7 obligatoire",
            reason="Source explicit",
            confidence=0.9,
            source_id="rncp_blocs:RNCP12345",
        )
        assert result["valid"] is True
        assert result["verdict"] == "supported"
        assert result["confidence"] == 0.9

    def test_invalid_verdict(self):
        result = _fetch_stat_tool_func(
            verdict="invalid_xxx",
            reason="r",
            confidence=0.8,
        )
        assert "error" in result
        assert result["error"] == "verdict_out_of_enum"

    def test_invalid_confidence_not_numeric(self):
        result = _fetch_stat_tool_func(
            verdict="supported",
            reason="r",
            confidence="not a number",
        )
        assert "error" in result
        assert result["error"] == "confidence_not_numeric"

    def test_invalid_confidence_out_of_bounds(self):
        result = _fetch_stat_tool_func(
            verdict="supported",
            reason="r",
            confidence=2.5,
        )
        assert "error" in result
        assert result["error"] == "confidence_out_of_bounds"

    def test_unsupported_with_null_excerpt(self):
        result = _fetch_stat_tool_func(
            verdict="unsupported",
            source_excerpt=None,
            reason="No source mentions",
            confidence=0.85,
        )
        assert result["valid"] is True
        assert result["source_excerpt"] is None


# --- Source dataclass ---


class TestSource:
    def test_minimal(self):
        s = Source(id="x:1", text="some text content")
        assert s.id == "x:1"
        assert s.domain == "formation"

    def test_to_prompt_format(self):
        s = Source(id="rncp:42", text="Le master niveau 7", domain="competences_certif")
        out = s.to_prompt_format()
        assert "[rncp:42]" in out
        assert "competences_certif" in out
        assert "Le master niveau 7" in out

    def test_text_truncated_in_prompt(self):
        long_text = "x" * 1000
        s = Source(id="x:1", text=long_text)
        out = s.to_prompt_format()
        assert len(out) < 600  # truncated to 500 + prefix


# --- Tool definition ---


class TestToolDefinition:
    def test_tool_name(self):
        assert FETCH_STAT_TOOL.name == "verify_claim_against_sources"

    def test_required_fields(self):
        assert "verdict" in FETCH_STAT_TOOL.parameters["required"]
        assert "reason" in FETCH_STAT_TOOL.parameters["required"]
        assert "confidence" in FETCH_STAT_TOOL.parameters["required"]

    def test_verdict_enum_complete(self):
        verdicts_enum = set(FETCH_STAT_TOOL.parameters["properties"]["verdict"]["enum"])
        assert verdicts_enum == VALID_VERDICTS


# --- FetchStatFromSource (mocked Mistral) ---


def _mock_mistral_verification(verdict, source_excerpt=None, reason="OK",
                                confidence=0.85, source_id=None):
    tc = MagicMock()
    tc.function.name = "verify_claim_against_sources"
    tc.function.arguments = json.dumps({
        "verdict": verdict,
        "source_excerpt": source_excerpt,
        "reason": reason,
        "confidence": confidence,
        "source_id": source_id,
    })
    msg = MagicMock()
    msg.tool_calls = [tc]
    msg.content = ""
    response = MagicMock()
    response.choices = [MagicMock(message=msg)]
    return response


class TestFetchStatFromSourceHighLevel:
    def test_verify_supported(self):
        client = MagicMock()
        client.chat.complete.return_value = _mock_mistral_verification(
            verdict="supported",
            source_excerpt="Master niveau 7 obligatoire",
            reason="Source confirme explicit",
            confidence=0.92,
            source_id="rncp_blocs:RNCP12345",
        )
        sources = [Source(id="rncp_blocs:RNCP12345",
                          text="Master niveau 7 obligatoire pour titre psychologue")]
        fetch = FetchStatFromSource(client=client)
        result = fetch.verify("Master psycho bac+5", sources)
        assert result.is_valid()
        assert result.verdict == "supported"
        assert result.is_supported
        assert result.confidence == 0.92

    def test_verify_contradicted_psy_case(self):
        """Cas cible bench persona PR #75 — erreur réglementaire psy."""
        client = MagicMock()
        client.chat.complete.return_value = _mock_mistral_verification(
            verdict="contradicted",
            source_excerpt="Le titre de psychologue exige obligatoirement un master bac+5 niveau 7",
            reason="Source contredit le claim niveau 6 ; titre protégé exige niveau 7",
            confidence=0.95,
            source_id="rncp_blocs:RNCP38875",
        )
        sources = [Source(
            id="rncp_blocs:RNCP38875",
            text="Le titre de psychologue est protégé en France et exige obligatoirement un master bac+5 niveau 7",
            domain="competences_certif",
        )]
        fetch = FetchStatFromSource(client=client)
        result = fetch.verify(
            "Titre RNCP psychologue niveau 6", sources
        )
        assert result.is_valid()
        assert result.verdict == "contradicted"
        assert result.is_problematic
        assert "niveau 7" in result.source_excerpt

    def test_verify_no_sources_returns_unsupported(self):
        client = MagicMock()
        fetch = FetchStatFromSource(client=client)
        result = fetch.verify("any claim", sources=[])
        assert result.verdict == "unsupported"
        assert result.confidence == 0.95
        # Mistral PAS appelé
        client.chat.complete.assert_not_called()

    def test_verify_empty_claim(self):
        client = MagicMock()
        fetch = FetchStatFromSource(client=client)
        result = fetch.verify("", sources=[Source(id="x", text="t")])
        assert result.verdict == "unsupported"
        # Mistral PAS appelé
        client.chat.complete.assert_not_called()

    def test_verify_no_tool_call_raises(self):
        client = MagicMock()
        msg = MagicMock()
        msg.tool_calls = None
        msg.content = "..."
        response = MagicMock()
        response.choices = [MagicMock(message=msg)]
        client.chat.complete.return_value = response

        sources = [Source(id="x", text="t")]
        fetch = FetchStatFromSource(client=client)
        with pytest.raises(ValueError, match="n'a pas appelé"):
            fetch.verify("test", sources)

    def test_verify_with_cache(self):
        from src.agent.cache import LRUCache

        client = MagicMock()
        client.chat.complete.return_value = _mock_mistral_verification(
            verdict="supported", source_excerpt="src", reason="r", confidence=0.9
        )
        cache = LRUCache(maxsize=10)
        fetch = FetchStatFromSource(client=client, cache=cache)
        sources = [Source(id="x:1", text="t")]

        # 1er call → Mistral appelé, stocké en cache
        r1 = fetch.verify("claim", sources)
        # 2ème call même claim+sources → cache hit, Mistral PAS rappelé
        r2 = fetch.verify("claim", sources)

        assert client.chat.complete.call_count == 1
        assert cache.stats()["hits"] == 1
        assert r1.verdict == r2.verdict
