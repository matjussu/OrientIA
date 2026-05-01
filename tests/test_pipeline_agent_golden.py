"""Tests Sprint 12 axe 2 golden pipeline — adaptations `AgentPipeline`.

Couvre les nouveaux flags ajoutés étape 3 :

- ``enable_metadata_filter`` : bridge ``Profile`` → ``ProfileState`` →
  ``FilterCriteria``, wrap de ``retrieve_top_k`` avec ``apply_metadata_filter``
- ``golden_qa_prefix`` : passé à ``generate(golden_qa_prefix=...)``
- ``history_buffer_size`` + ``add_turn_to_history()`` : cap N derniers tours
  passés à ``generate(history=...)``
- ``enable_backstop_b`` + ``backstop_b_corpus_index`` : appel
  ``annotate_response`` post-fact-check
- ``AgentAnswer.profile_state`` / ``metadata_filter_filtered_count`` /
  ``backstop_b_applied`` : nouveaux champs télémétrie

Pas d'appel Mistral réel — mocks sur ProfileClarifier, QueryReformuler,
retrieve_top_k, generate, FetchStatFromSource, CorpusFactIndex.

Plan : ``docs/GOLDEN_PIPELINE_PLAN.md`` étape 3.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.agent.pipeline_agent import AgentAnswer, AgentPipeline
from src.agent.tools.profile_clarifier import Profile
from src.agent.tools.query_reformuler import ReformulationPlan, SubQuery


# ---- Fixtures ---------------------------------------------------------------


@pytest.fixture
def mock_client():
    return MagicMock()


@pytest.fixture
def fake_fiches() -> list[dict]:
    """Sample corpus combined avec champ `corpus` discriminant."""
    return [
        {
            "id": "psup:1",
            "corpus": "formations_unified",
            "nom": "BTS SIO",
            "etablissement": "Lycée Test",
            "ville": "Paris",
            "region": "Île-de-France",
            "niveau_int": 2,
        },
        {
            "id": "psup:2",
            "corpus": "formations_unified",
            "nom": "BUT info",
            "etablissement": "IUT X",
            "ville": "Toulouse",
            "region": "Occitanie",
            "niveau_int": 3,
        },
        {
            "id": "dares_fap:M2Z",
            "corpus": "dares",
            "domain": "metier_prospective",
            "text": "Métier 2030 (DARES) — informaticiens, data scientists.",
        },
    ]


@pytest.fixture
def fake_profile() -> Profile:
    return Profile(
        age_group="lyceen_terminale",
        education_level="terminale",
        intent_type="orientation_initiale",
        sector_interest=["informatique"],
        region="Île-de-France",
        urgent_concern=False,
        confidence=0.8,
    )


@pytest.fixture
def fake_plan() -> ReformulationPlan:
    return ReformulationPlan(
        original_query="query test",
        sub_queries=[
            SubQuery(text="formations info Paris", target_corpus="formation", priority=2),
        ],
    )


@pytest.fixture
def fake_retrieved() -> list[dict]:
    return [
        {"score": 0.9, "fiche": {"id": "psup:1", "nom": "BTS SIO", "region": "Île-de-France", "niveau_int": 2}},
        {"score": 0.8, "fiche": {"id": "psup:2", "nom": "BUT info", "region": "Occitanie", "niveau_int": 3}},
    ]


def _build_pipeline(client, fiches, **flags) -> AgentPipeline:
    """Helper qui construit un AgentPipeline en court-circuitant les
    composants non-pertinents pour le test (clarifier, reformuler...)."""
    return AgentPipeline(client=client, fiches=fiches, index=MagicMock(), **flags)


# ---- TestNewAttributesDefaults ----------------------------------------------


class TestNewAttributesDefaults:
    """Backward compat strict : les nouveaux flags par défaut OFF."""

    def test_defaults_are_off(self, mock_client, fake_fiches):
        p = _build_pipeline(mock_client, fake_fiches)
        assert p.enable_metadata_filter is False
        assert p.golden_qa_prefix is None
        assert p.enable_backstop_b is False
        assert p.history_buffer_size == 0
        assert p.backstop_b_corpus_index is None

    def test_history_buffer_starts_empty(self, mock_client, fake_fiches):
        p = _build_pipeline(mock_client, fake_fiches, history_buffer_size=3)
        assert p._history_buffer == []

    def test_current_filter_criteria_starts_none(self, mock_client, fake_fiches):
        p = _build_pipeline(mock_client, fake_fiches)
        assert p._current_filter_criteria is None

    def test_agentanswer_new_fields_defaults(self):
        a = AgentAnswer(query="q", answer_text="a", profile=None, plan=None)
        assert a.profile_state is None
        assert a.metadata_filter_filtered_count == -1
        assert a.backstop_b_applied is False
        assert a.elapsed_backstop_b_s == 0.0


# ---- TestHistoryBuffer ------------------------------------------------------


class TestHistoryBuffer:
    """Cap N derniers tours user+assistant via add_turn_to_history()."""

    def test_disabled_when_size_zero(self, mock_client, fake_fiches):
        p = _build_pipeline(mock_client, fake_fiches, history_buffer_size=0)
        p.add_turn_to_history("u1", "a1")
        assert p._history_buffer == []

    def test_appends_turn_user_then_assistant(self, mock_client, fake_fiches):
        p = _build_pipeline(mock_client, fake_fiches, history_buffer_size=3)
        p.add_turn_to_history("hello", "hi there")
        assert p._history_buffer == [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi there"},
        ]

    def test_caps_to_n_turns(self, mock_client, fake_fiches):
        p = _build_pipeline(mock_client, fake_fiches, history_buffer_size=2)
        for i in range(5):
            p.add_turn_to_history(f"u{i}", f"a{i}")
        # 2 tours = 4 messages, garde les 2 derniers tours (i=3, i=4)
        assert len(p._history_buffer) == 4
        assert p._history_buffer[0]["content"] == "u3"
        assert p._history_buffer[-1]["content"] == "a4"

    def test_preserves_order_within_cap(self, mock_client, fake_fiches):
        p = _build_pipeline(mock_client, fake_fiches, history_buffer_size=3)
        p.add_turn_to_history("u1", "a1")
        p.add_turn_to_history("u2", "a2")
        roles = [m["role"] for m in p._history_buffer]
        assert roles == ["user", "assistant", "user", "assistant"]


# ---- TestRetrieveWithMetadataFilter -----------------------------------------


class TestRetrieveWithMetadataFilter:
    """`_retrieve_for_subquery` wrap retrieve_top_k avec apply_metadata_filter
    quand `_current_filter_criteria` est set."""

    @patch("src.agent.pipeline_agent.retrieve_top_k")
    def test_no_filter_when_criteria_none(self, mock_retrieve, mock_client, fake_fiches, fake_retrieved):
        mock_retrieve.return_value = fake_retrieved
        p = _build_pipeline(mock_client, fake_fiches)
        p._current_filter_criteria = None  # explicit
        sq = SubQuery(text="x", target_corpus="formations", priority=1.0)
        result = p._retrieve_for_subquery(sq)
        # k = sub_query_top_k (pas ×2)
        assert mock_retrieve.call_args.kwargs["k"] == p.sub_query_top_k
        assert result["retrieved"] == fake_retrieved

    @patch("src.agent.pipeline_agent.retrieve_top_k")
    def test_no_filter_when_disabled(self, mock_retrieve, mock_client, fake_fiches, fake_retrieved):
        mock_retrieve.return_value = fake_retrieved
        p = _build_pipeline(mock_client, fake_fiches, enable_metadata_filter=False)
        from src.rag.metadata_filter import FilterCriteria
        p._current_filter_criteria = FilterCriteria(region="Île-de-France")  # set mais flag OFF
        sq = SubQuery(text="x", target_corpus="formations", priority=1.0)
        result = p._retrieve_for_subquery(sq)
        assert mock_retrieve.call_args.kwargs["k"] == p.sub_query_top_k
        assert result["retrieved"] == fake_retrieved

    @patch("src.agent.pipeline_agent.retrieve_top_k")
    @patch("src.agent.pipeline_agent.apply_metadata_filter")
    def test_filter_applied_when_active(self, mock_filter, mock_retrieve, mock_client, fake_fiches, fake_retrieved):
        mock_retrieve.return_value = fake_retrieved * 2  # ×2 pour over-retrieve
        mock_filter.return_value = fake_retrieved[:1]  # filter laisse 1 résultat
        from src.rag.metadata_filter import FilterCriteria
        p = _build_pipeline(mock_client, fake_fiches, enable_metadata_filter=True)
        p._current_filter_criteria = FilterCriteria(region="Île-de-France")
        sq = SubQuery(text="x", target_corpus="formations", priority=1.0)
        result = p._retrieve_for_subquery(sq)
        # k = sub_query_top_k × 2 (over-retrieve pour absorber drops)
        assert mock_retrieve.call_args.kwargs["k"] == p.sub_query_top_k * 2
        # filter appelé avec criteria
        mock_filter.assert_called_once()
        assert result["retrieved"] == fake_retrieved[:1]

    @patch("src.agent.pipeline_agent.retrieve_top_k")
    def test_no_filter_when_criteria_empty(self, mock_retrieve, mock_client, fake_fiches, fake_retrieved):
        mock_retrieve.return_value = fake_retrieved
        from src.rag.metadata_filter import FilterCriteria
        p = _build_pipeline(mock_client, fake_fiches, enable_metadata_filter=True)
        p._current_filter_criteria = FilterCriteria()  # vide → is_empty() True
        sq = SubQuery(text="x", target_corpus="formations", priority=1.0)
        result = p._retrieve_for_subquery(sq)
        assert mock_retrieve.call_args.kwargs["k"] == p.sub_query_top_k
        assert result["retrieved"] == fake_retrieved


# ---- TestAnswerEnableMetadataFilter -----------------------------------------


class TestAnswerEnableMetadataFilter:
    """`answer()` produit un ProfileState typé + FilterCriteria si flag ON."""

    @patch("src.agent.pipeline_agent.generate")
    @patch("src.agent.pipeline_agent.retrieve_top_k")
    def test_profile_state_set_when_enabled(
        self, mock_retrieve, mock_generate,
        mock_client, fake_fiches, fake_profile, fake_plan, fake_retrieved,
    ):
        mock_retrieve.return_value = fake_retrieved
        mock_generate.return_value = "answer_text"
        p = _build_pipeline(mock_client, fake_fiches, enable_metadata_filter=True)
        p.clarifier = MagicMock()
        p.clarifier.clarify.return_value = fake_profile
        p.reformuler = MagicMock()
        p.reformuler.reformulate.return_value = fake_plan

        result = p.answer("query test")
        assert result.profile_state is not None
        assert result.profile_state.region == "Île-de-France"
        assert result.profile_state.education_level.value == "terminale"
        # FilterCriteria dérivé doit être posé
        assert p._current_filter_criteria is not None

    @patch("src.agent.pipeline_agent.generate")
    @patch("src.agent.pipeline_agent.retrieve_top_k")
    def test_profile_state_none_when_disabled(
        self, mock_retrieve, mock_generate,
        mock_client, fake_fiches, fake_profile, fake_plan, fake_retrieved,
    ):
        mock_retrieve.return_value = fake_retrieved
        mock_generate.return_value = "answer_text"
        p = _build_pipeline(mock_client, fake_fiches, enable_metadata_filter=False)
        p.clarifier = MagicMock()
        p.clarifier.clarify.return_value = fake_profile
        p.reformuler = MagicMock()
        p.reformuler.reformulate.return_value = fake_plan

        result = p.answer("query test")
        assert result.profile_state is None
        assert p._current_filter_criteria is None


# ---- TestGoldenQAPrefixWiring -----------------------------------------------


class TestGoldenQAPrefixWiring:
    """`golden_qa_prefix` est passé à `generate(golden_qa_prefix=...)`."""

    @patch("src.agent.pipeline_agent.generate")
    @patch("src.agent.pipeline_agent.retrieve_top_k")
    def test_prefix_passed_to_generate(
        self, mock_retrieve, mock_generate,
        mock_client, fake_fiches, fake_profile, fake_plan, fake_retrieved,
    ):
        mock_retrieve.return_value = fake_retrieved
        mock_generate.return_value = "answer"
        prefix = "## Q&A Golden Example\nQ: ... A: ..."
        p = _build_pipeline(mock_client, fake_fiches, golden_qa_prefix=prefix)
        p.clarifier = MagicMock()
        p.clarifier.clarify.return_value = fake_profile
        p.reformuler = MagicMock()
        p.reformuler.reformulate.return_value = fake_plan

        p.answer("q")
        assert mock_generate.call_args.kwargs["golden_qa_prefix"] == prefix

    @patch("src.agent.pipeline_agent.generate")
    @patch("src.agent.pipeline_agent.retrieve_top_k")
    def test_no_prefix_passed_by_default(
        self, mock_retrieve, mock_generate,
        mock_client, fake_fiches, fake_profile, fake_plan, fake_retrieved,
    ):
        mock_retrieve.return_value = fake_retrieved
        mock_generate.return_value = "answer"
        p = _build_pipeline(mock_client, fake_fiches)
        p.clarifier = MagicMock()
        p.clarifier.clarify.return_value = fake_profile
        p.reformuler = MagicMock()
        p.reformuler.reformulate.return_value = fake_plan

        p.answer("q")
        assert mock_generate.call_args.kwargs["golden_qa_prefix"] is None


# ---- TestHistoryWiring ------------------------------------------------------


class TestHistoryWiring:
    """`_history_buffer` est passé à `generate(history=...)`."""

    @patch("src.agent.pipeline_agent.generate")
    @patch("src.agent.pipeline_agent.retrieve_top_k")
    def test_history_none_when_buffer_empty(
        self, mock_retrieve, mock_generate,
        mock_client, fake_fiches, fake_profile, fake_plan, fake_retrieved,
    ):
        mock_retrieve.return_value = fake_retrieved
        mock_generate.return_value = "answer"
        p = _build_pipeline(mock_client, fake_fiches, history_buffer_size=3)
        p.clarifier = MagicMock()
        p.clarifier.clarify.return_value = fake_profile
        p.reformuler = MagicMock()
        p.reformuler.reformulate.return_value = fake_plan

        p.answer("q")
        # Buffer vide → history=None passé à generate
        assert mock_generate.call_args.kwargs["history"] is None

    @patch("src.agent.pipeline_agent.generate")
    @patch("src.agent.pipeline_agent.retrieve_top_k")
    def test_history_passed_when_populated(
        self, mock_retrieve, mock_generate,
        mock_client, fake_fiches, fake_profile, fake_plan, fake_retrieved,
    ):
        mock_retrieve.return_value = fake_retrieved
        mock_generate.return_value = "answer"
        p = _build_pipeline(mock_client, fake_fiches, history_buffer_size=3)
        p.clarifier = MagicMock()
        p.clarifier.clarify.return_value = fake_profile
        p.reformuler = MagicMock()
        p.reformuler.reformulate.return_value = fake_plan

        p.add_turn_to_history("prev_user", "prev_answer")
        p.answer("q")
        history_arg = mock_generate.call_args.kwargs["history"]
        assert history_arg is not None
        assert len(history_arg) == 2
        assert history_arg[0]["role"] == "user"
        assert history_arg[1]["role"] == "assistant"


# ---- TestBackstopBWiring ----------------------------------------------------


class TestBackstopBWiring:
    """`enable_backstop_b` + `backstop_b_corpus_index` → annotate_response post."""

    @patch("src.agent.pipeline_agent.generate")
    @patch("src.agent.pipeline_agent.retrieve_top_k")
    def test_backstop_skipped_when_disabled(
        self, mock_retrieve, mock_generate,
        mock_client, fake_fiches, fake_profile, fake_plan, fake_retrieved,
    ):
        mock_retrieve.return_value = fake_retrieved
        mock_generate.return_value = "raw answer with 42%"
        p = _build_pipeline(mock_client, fake_fiches, enable_backstop_b=False)
        p.clarifier = MagicMock()
        p.clarifier.clarify.return_value = fake_profile
        p.reformuler = MagicMock()
        p.reformuler.reformulate.return_value = fake_plan

        result = p.answer("q")
        assert result.backstop_b_applied is False
        assert result.answer_text == "raw answer with 42%"

    @patch("src.agent.pipeline_agent.generate")
    @patch("src.agent.pipeline_agent.retrieve_top_k")
    def test_backstop_applied_when_enabled(
        self, mock_retrieve, mock_generate,
        mock_client, fake_fiches, fake_profile, fake_plan, fake_retrieved,
    ):
        mock_retrieve.return_value = fake_retrieved
        mock_generate.return_value = "raw answer with 42% taux d'admission"
        # Mock CorpusFactIndex pré-construit
        mock_index = MagicMock()
        p = _build_pipeline(
            mock_client, fake_fiches,
            enable_backstop_b=True,
            backstop_b_corpus_index=mock_index,
        )
        p.clarifier = MagicMock()
        p.clarifier.clarify.return_value = fake_profile
        p.reformuler = MagicMock()
        p.reformuler.reformulate.return_value = fake_plan

        with patch("src.backstop.annotate_response") as mock_annotate:
            mock_annotate.return_value = "raw answer with <span>42%</span> taux d'admission [DISCLAIMER]"
            result = p.answer("q")
        assert result.backstop_b_applied is True
        assert "<span>" in result.answer_text
        # annotate_response a reçu l'index pré-construit
        mock_annotate.assert_called_once()
        assert mock_annotate.call_args.args[1] is mock_index

    @patch("src.agent.pipeline_agent.generate")
    @patch("src.agent.pipeline_agent.retrieve_top_k")
    def test_backstop_raises_when_no_index_provided(
        self, mock_retrieve, mock_generate,
        mock_client, fake_fiches, fake_profile, fake_plan, fake_retrieved,
    ):
        mock_retrieve.return_value = fake_retrieved
        mock_generate.return_value = "raw answer"
        p = _build_pipeline(
            mock_client, fake_fiches,
            enable_backstop_b=True,
            backstop_b_corpus_index=None,  # pas d'index pré-construit
        )
        p.clarifier = MagicMock()
        p.clarifier.clarify.return_value = fake_profile
        p.reformuler = MagicMock()
        p.reformuler.reformulate.return_value = fake_plan

        result = p.answer("q")
        # Backstop B échoue gracieusement (post-process best-effort)
        assert result.backstop_b_applied is False
        assert result.error and "backstop_b_warning" in result.error
        # La génération est intacte
        assert result.answer_text == "raw answer"
