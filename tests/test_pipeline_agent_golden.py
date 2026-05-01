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


# ---- TestRetrieveWithMetadataBoost (Sprint 12 axe 2 v2) --------------------


class TestRetrieveWithMetadataBoost:
    """Sprint 12 axe 2 v2 — `_retrieve_for_subquery` applique `apply_metadata_boost`
    quand `_current_filter_criteria` set ET `enable_metadata_filter=True`.

    Différence étape 4 (strict) → étape 6 (boost soft) :
    - Pas d'over-retrieve ×2 (k=sub_query_top_k tel quel)
    - Pas de drop : tous les candidats préservés, seulement boost score sur match
    - `apply_metadata_boost` appelé au lieu de `apply_metadata_filter`
    """

    @patch("src.agent.pipeline_agent.retrieve_top_k")
    def test_no_boost_when_criteria_none(self, mock_retrieve, mock_client, fake_fiches, fake_retrieved):
        mock_retrieve.return_value = fake_retrieved
        p = _build_pipeline(mock_client, fake_fiches)
        p._current_filter_criteria = None  # explicit
        sq = SubQuery(text="x", target_corpus="formation", priority=2)
        result = p._retrieve_for_subquery(sq)
        assert mock_retrieve.call_args.kwargs["k"] == p.sub_query_top_k
        assert result["retrieved"] == fake_retrieved

    @patch("src.agent.pipeline_agent.retrieve_top_k")
    def test_no_boost_when_disabled(self, mock_retrieve, mock_client, fake_fiches, fake_retrieved):
        mock_retrieve.return_value = fake_retrieved
        p = _build_pipeline(mock_client, fake_fiches, enable_metadata_filter=False)
        from src.rag.metadata_filter import FilterCriteria
        p._current_filter_criteria = FilterCriteria(region="Île-de-France")  # set mais flag OFF
        sq = SubQuery(text="x", target_corpus="formation", priority=2)
        result = p._retrieve_for_subquery(sq)
        assert mock_retrieve.call_args.kwargs["k"] == p.sub_query_top_k
        assert result["retrieved"] == fake_retrieved

    @patch("src.agent.pipeline_agent.retrieve_top_k")
    @patch("src.agent.pipeline_agent.apply_metadata_boost")
    def test_boost_applied_when_active(self, mock_boost, mock_retrieve, mock_client, fake_fiches, fake_retrieved):
        # Sprint 12 v2 : k=sub_query_top_k normal (pas ×2), boost soft.
        mock_retrieve.return_value = fake_retrieved
        mock_boost.return_value = list(reversed(fake_retrieved))  # ordre changé pour vérifier le re-tri
        from src.rag.metadata_filter import FilterCriteria
        p = _build_pipeline(mock_client, fake_fiches, enable_metadata_filter=True)
        p._current_filter_criteria = FilterCriteria(region="Île-de-France")
        sq = SubQuery(text="x", target_corpus="formation", priority=2)
        result = p._retrieve_for_subquery(sq)
        assert mock_retrieve.call_args.kwargs["k"] == p.sub_query_top_k
        # boost appelé avec criteria + boost_factor
        mock_boost.assert_called_once()
        call_kwargs = mock_boost.call_args.kwargs
        assert call_kwargs["boost_factor"] == p.metadata_boost_factor
        # Le retour est celui de apply_metadata_boost (re-trié)
        assert result["retrieved"] == list(reversed(fake_retrieved))

    @patch("src.agent.pipeline_agent.retrieve_top_k")
    def test_no_boost_when_criteria_empty(self, mock_retrieve, mock_client, fake_fiches, fake_retrieved):
        mock_retrieve.return_value = fake_retrieved
        from src.rag.metadata_filter import FilterCriteria
        p = _build_pipeline(mock_client, fake_fiches, enable_metadata_filter=True)
        p._current_filter_criteria = FilterCriteria()  # vide → is_empty() True
        sq = SubQuery(text="x", target_corpus="formation", priority=2)
        result = p._retrieve_for_subquery(sq)
        assert mock_retrieve.call_args.kwargs["k"] == p.sub_query_top_k
        assert result["retrieved"] == fake_retrieved

    @patch("src.agent.pipeline_agent.retrieve_top_k")
    def test_no_boost_when_factor_one(self, mock_retrieve, mock_client, fake_fiches, fake_retrieved):
        """boost_factor=1.0 → no-op équivalent à enable_metadata_filter=False."""
        mock_retrieve.return_value = fake_retrieved
        from src.rag.metadata_filter import FilterCriteria
        p = _build_pipeline(
            mock_client, fake_fiches,
            enable_metadata_filter=True,
            metadata_boost_factor=1.0,  # no-op
        )
        p._current_filter_criteria = FilterCriteria(region="Île-de-France")
        sq = SubQuery(text="x", target_corpus="formation", priority=2)
        result = p._retrieve_for_subquery(sq)
        assert result["retrieved"] == fake_retrieved


class TestBoostPreservesDiversite:
    """Sprint 12 axe 2 v2 garde-fou — `apply_metadata_boost` n'amende JAMAIS
    la liste de candidats (pas de drop).

    Cible : prévenir la régression `diversite_geo` -11 observée étape 4
    avec `apply_metadata_filter` strict. Le boost soft doit préserver tous
    les candidats régionaux variés ; seul le re-tri par score change.
    """

    def test_diversite_geo_preservee_question_nationale(self):
        """Sur une query nationale (criteria=region=IDF), tous les candidats
        régionaux sont conservés ; seuls les matchs IDF sont boostés."""
        from src.rag.metadata_filter import FilterCriteria, apply_metadata_boost
        retrieved = [
            {"score": 0.90, "fiche": {"id": "f1", "region": "île-de-france", "nom": "École IDF 1"}},
            {"score": 0.85, "fiche": {"id": "f2", "region": "occitanie", "nom": "École Toulouse"}},
            {"score": 0.80, "fiche": {"id": "f3", "region": "auvergne-rhône-alpes", "nom": "École Lyon"}},
            {"score": 0.75, "fiche": {"id": "f4", "region": "île-de-france", "nom": "École IDF 2"}},
            {"score": 0.70, "fiche": {"id": "f5", "region": "bretagne", "nom": "École Rennes"}},
        ]
        criteria = FilterCriteria(region="Île-de-France")
        boosted = apply_metadata_boost(retrieved, criteria, boost_factor=1.3)
        # Aucun drop
        assert len(boosted) == 5
        # IDs préservés (set)
        assert {it["fiche"]["id"] for it in boosted} == {"f1", "f2", "f3", "f4", "f5"}
        # 2 boostés (IDF), 3 non
        boosted_ids = {it["fiche"]["id"] for it in boosted if it.get("_boosted")}
        assert boosted_ids == {"f1", "f4"}
        # Scores boostés ×1.3
        f1 = next(it for it in boosted if it["fiche"]["id"] == "f1")
        assert f1["score"] == pytest.approx(0.90 * 1.3)
        # Scores non-boostés intacts
        f2 = next(it for it in boosted if it["fiche"]["id"] == "f2")
        assert f2["score"] == 0.85
        # Re-tri : f1 (0.90×1.3=1.17) en tête, f4 (0.75×1.3=0.975) avant f2 (0.85)
        assert boosted[0]["fiche"]["id"] == "f1"
        assert boosted[1]["fiche"]["id"] == "f4"

    def test_no_match_preserves_all_unboosted(self):
        """Si AUCUNE fiche ne match (ex region IDF sur fiches Bretagne uniquement),
        toutes les fiches restent à leur score d'origine — l'utilisateur n'est
        jamais privé du retrieval brut FAISS."""
        from src.rag.metadata_filter import FilterCriteria, apply_metadata_boost
        retrieved = [
            {"score": 0.90, "fiche": {"id": "f1", "region": "bretagne"}},
            {"score": 0.80, "fiche": {"id": "f2", "region": "occitanie"}},
        ]
        criteria = FilterCriteria(region="Île-de-France")
        boosted = apply_metadata_boost(retrieved, criteria, boost_factor=1.3)
        assert len(boosted) == 2
        assert all(not it.get("_boosted") for it in boosted)
        # Ordre + scores intacts
        assert boosted[0]["fiche"]["id"] == "f1"
        assert boosted[0]["score"] == 0.90
        assert boosted[1]["score"] == 0.80

    def test_empty_criteria_returns_input_unchanged(self):
        from src.rag.metadata_filter import FilterCriteria, apply_metadata_boost
        retrieved = [{"score": 0.5, "fiche": {"id": "f1"}}]
        boosted = apply_metadata_boost(retrieved, FilterCriteria(), boost_factor=1.3)
        assert boosted == retrieved

    def test_boost_factor_one_returns_input_unchanged(self):
        from src.rag.metadata_filter import FilterCriteria, apply_metadata_boost
        retrieved = [{"score": 0.5, "fiche": {"id": "f1", "region": "île-de-france"}}]
        boosted = apply_metadata_boost(retrieved, FilterCriteria(region="Île-de-France"), boost_factor=1.0)
        assert boosted == retrieved


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
