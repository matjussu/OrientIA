"""Tests src/agent/tools/query_reformuler.py — SubQuery + tool func + QueryReformuler (mocked)."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from src.agent.tools.profile_clarifier import Profile
from src.agent.tools.query_reformuler import (
    QUERY_REFORMULER_TOOL,
    QueryReformuler,
    ReformulationPlan,
    SubQuery,
    VALID_PRIORITIES,
    VALID_TARGET_CORPORA,
    _query_reformuler_tool_func,
)


# --- Fixtures ---


@pytest.fixture
def sample_profile():
    return Profile(
        age_group="lyceen_terminale",
        education_level="terminale",
        intent_type="orientation_initiale",
        sector_interest=["informatique"],
        region="Île-de-France",
        urgent_concern=False,
        confidence=0.9,
    )


# --- SubQuery dataclass ---


class TestSubQuery:
    def test_minimal_construction(self):
        sq = SubQuery(text="formations info IDF", target_corpus="formation")
        assert sq.is_valid()
        assert sq.priority == 2  # default
        assert sq.rationale is None

    def test_full_construction(self):
        sq = SubQuery(
            text="postes à pourvoir 2030 numérique",
            target_corpus="metier_prospective",
            priority=1,
            rationale="couvre l'intent prospective explicit",
        )
        assert sq.is_valid()

    def test_text_too_short(self):
        sq = SubQuery(text="hi", target_corpus="formation")
        assert not sq.is_valid()  # len(text.strip()) < 5

    def test_invalid_corpus(self):
        sq = SubQuery(text="some query text", target_corpus="invalid_xxx")
        assert not sq.is_valid()

    def test_invalid_priority(self):
        sq = SubQuery(text="some query text", target_corpus="formation", priority=4)
        assert not sq.is_valid()

    def test_to_dict(self):
        sq = SubQuery(
            text="blocs de compétences BTS compta",
            target_corpus="competences_certif",
            priority=1,
        )
        d = sq.to_dict()
        assert d["text"] == "blocs de compétences BTS compta"
        assert d["target_corpus"] == "competences_certif"


# --- ReformulationPlan ---


class TestReformulationPlan:
    def test_minimal_valid_plan(self):
        plan = ReformulationPlan(
            original_query="formations info IDF",
            sub_queries=[SubQuery(text="formations info IDF", target_corpus="formation")],
        )
        assert plan.is_valid()

    def test_empty_sub_queries_invalid(self):
        plan = ReformulationPlan(original_query="test", sub_queries=[])
        assert not plan.is_valid()

    def test_invalid_sub_query_invalidates_plan(self):
        plan = ReformulationPlan(
            original_query="test",
            sub_queries=[SubQuery(text="x", target_corpus="formation")],
        )
        assert not plan.is_valid()

    def test_to_dict(self, sample_profile):
        plan = ReformulationPlan(
            original_query="test query",
            sub_queries=[
                SubQuery(text="sub one query text", target_corpus="formation", priority=1),
                SubQuery(text="sub two query text", target_corpus="metier_prospective", priority=2),
            ],
            strategy_note="2 axes complémentaires",
            profile_used=sample_profile.to_dict(),
        )
        d = plan.to_dict()
        assert d["original_query"] == "test query"
        assert len(d["sub_queries"]) == 2
        assert d["strategy_note"] == "2 axes complémentaires"
        assert d["profile_used"]["age_group"] == "lyceen_terminale"


# --- Tool func wrapper ---


class TestQueryReformulerToolFunc:
    def test_valid_call(self):
        result = _query_reformuler_tool_func(
            sub_queries=[
                {"text": "formations cyber IDF", "target_corpus": "formation", "priority": 1},
                {"text": "métiers cyber 2030", "target_corpus": "metier_prospective", "priority": 2},
            ],
            strategy_note="2 axes complémentaires",
        )
        assert result["valid"] is True
        assert len(result["sub_queries"]) == 2
        assert result["strategy_note"] == "2 axes complémentaires"

    def test_empty_sub_queries(self):
        result = _query_reformuler_tool_func(sub_queries=[])
        assert result.get("error") == "no_sub_queries"

    def test_invalid_corpus_returns_error(self):
        result = _query_reformuler_tool_func(
            sub_queries=[{"text": "valid query text", "target_corpus": "xxx", "priority": 1}],
        )
        assert "error" in result
        assert result["error"] == "subquery_validation_failed"

    def test_invalid_priority_returns_error(self):
        result = _query_reformuler_tool_func(
            sub_queries=[{"text": "valid query text", "target_corpus": "formation", "priority": 99}],
        )
        assert "error" in result
        assert result["error"] == "subquery_validation_failed"

    def test_short_text_returns_error(self):
        result = _query_reformuler_tool_func(
            sub_queries=[{"text": "hi", "target_corpus": "formation", "priority": 1}],
        )
        assert "error" in result


# --- Tool definition ---


class TestToolDefinition:
    def test_tool_name(self):
        assert QUERY_REFORMULER_TOOL.name == "reformulate_user_query"

    def test_tool_required(self):
        assert "sub_queries" in QUERY_REFORMULER_TOOL.parameters["required"]

    def test_corpus_enum_complete(self):
        items = QUERY_REFORMULER_TOOL.parameters["properties"]["sub_queries"]["items"]
        corpus_enum = set(items["properties"]["target_corpus"]["enum"])
        assert corpus_enum == VALID_TARGET_CORPORA

    def test_priority_enum(self):
        items = QUERY_REFORMULER_TOOL.parameters["properties"]["sub_queries"]["items"]
        priority_enum = set(items["properties"]["priority"]["enum"])
        assert priority_enum == VALID_PRIORITIES


# --- QueryReformuler (mocked Mistral) ---


def _mock_response_with_subs(sub_list, strategy_note=None):
    tc = MagicMock()
    tc.function.name = "reformulate_user_query"
    tc.function.arguments = json.dumps({
        "sub_queries": sub_list,
        "strategy_note": strategy_note,
    })

    msg = MagicMock()
    msg.tool_calls = [tc]
    msg.content = ""

    response = MagicMock()
    response.choices = [MagicMock(message=msg)]
    return response


class TestQueryReformulerHighLevel:
    def test_reformulate_simple(self, sample_profile):
        client = MagicMock()
        client.chat.complete.return_value = _mock_response_with_subs([
            {"text": "formations informatique en Île-de-France",
             "target_corpus": "formation", "priority": 1, "rationale": "intent core"},
        ])
        reformuler = QueryReformuler(client=client)
        plan = reformuler.reformulate("Que faire avec un goût pour l'info ?", sample_profile)
        assert plan.is_valid()
        assert len(plan.sub_queries) == 1
        assert plan.sub_queries[0].target_corpus == "formation"
        assert plan.profile_used["age_group"] == "lyceen_terminale"

    def test_reformulate_multi_subs(self, sample_profile):
        client = MagicMock()
        client.chat.complete.return_value = _mock_response_with_subs(
            [
                {"text": "formations école commerce", "target_corpus": "formation", "priority": 1},
                {"text": "salaires médians cadres commerce", "target_corpus": "insee_salaire", "priority": 2},
                {"text": "marché travail cadres en France", "target_corpus": "apec_region", "priority": 3},
            ],
            strategy_note="3 axes : offre / salaire / marché",
        )
        reformuler = QueryReformuler(client=client)
        plan = reformuler.reformulate("École de commerce, débouchés ?", sample_profile)
        assert len(plan.sub_queries) == 3
        assert plan.strategy_note == "3 axes : offre / salaire / marché"
        targets = [sq.target_corpus for sq in plan.sub_queries]
        assert "formation" in targets
        assert "insee_salaire" in targets
        assert "apec_region" in targets

    def test_reformulate_no_tool_call_raises(self, sample_profile):
        client = MagicMock()
        msg = MagicMock()
        msg.tool_calls = None
        msg.content = "I cannot reformulate this"
        response = MagicMock()
        response.choices = [MagicMock(message=msg)]
        client.chat.complete.return_value = response

        reformuler = QueryReformuler(client=client)
        with pytest.raises(ValueError, match="n'a pas appelé le tool"):
            reformuler.reformulate("???", sample_profile)

    def test_reformulate_invalid_subquery_raises(self, sample_profile):
        client = MagicMock()
        client.chat.complete.return_value = _mock_response_with_subs([
            {"text": "valid query text", "target_corpus": "INVALID", "priority": 1},
        ])
        reformuler = QueryReformuler(client=client)
        with pytest.raises(ValueError, match="returned error"):
            reformuler.reformulate("test", sample_profile)
