"""Tests Sprint 9 — archi multi-agents hiérarchique.

Couvre :
- Schemas (UserSessionProfile merge update lists/scalars/confidence)
- Session (trigger détection + règle 3 tours + bypass explicite + bench mode)
- Persona prompt (marqueurs obligatoires présents)
- EmpathicAgent (messages format, injection factual_base, profile context)
- AnalystAgent (passthrough non-bloquant en cas d'erreur)
- SynthesizerAgent (lazy factory, query enrichie avec profil)
- Coordinator (orchestration listening / reco / bench single-shot)
- Non-régression bench (HierarchicalSystem.respond_single_shot délègue
  à AgentPipeline mocké et propage la réponse)
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from src.agents.hierarchical import (
    AnalystAgent,
    Coordinator,
    EmpathicAgent,
    EmpathicResponse,
    Session,
    SynthesizedFactualBase,
    SynthesizerAgent,
    UserSessionProfile,
    load_persona_prompt,
    load_user_profile_schema,
)


# ──────────────────────────────────────────────────────────────────────
# Helpers : mock Mistral responses
# ──────────────────────────────────────────────────────────────────────


def _mock_chat_text_response(text: str):
    msg = MagicMock()
    msg.tool_calls = None
    msg.content = text
    response = MagicMock()
    response.choices = [MagicMock(message=msg)]
    return response


def _mock_chat_tool_response(tool_name: str, args: dict):
    tc = MagicMock()
    tc.id = "call_test"
    tc.function.name = tool_name
    tc.function.arguments = json.dumps(args)
    msg = MagicMock()
    msg.tool_calls = [tc]
    msg.content = ""
    response = MagicMock()
    response.choices = [MagicMock(message=msg)]
    return response


# ──────────────────────────────────────────────────────────────────────
# Schemas : UserSessionProfile.merge_update
# ──────────────────────────────────────────────────────────────────────


class TestUserSessionProfileMerge:
    def test_merge_lists_dedupe_preserve_order(self):
        p = UserSessionProfile(interets_detectes=["sciences", "concret"])
        p.merge_update({
            "interets_detectes": ["concret", "design"],  # "concret" déjà présent
            "contraintes": [], "valeurs": [], "questions_ouvertes": [],
            "confidence": 0.5,
        })
        # tour_count est 0 ici, divisor min = 1, donc moyenne = 0.5
        assert p.interets_detectes == ["sciences", "concret", "design"]

    def test_merge_scalars_replaced_when_non_null(self):
        p = UserSessionProfile(niveau_scolaire=None, region=None)
        p.merge_update({
            "niveau_scolaire": "terminale_spe_maths_physique",
            "region": "Occitanie",
            "interets_detectes": [], "contraintes": [], "valeurs": [],
            "questions_ouvertes": [], "confidence": 0.6,
        })
        assert p.niveau_scolaire == "terminale_spe_maths_physique"
        assert p.region == "Occitanie"

    def test_merge_scalars_null_does_not_overwrite(self):
        p = UserSessionProfile(niveau_scolaire="terminale_es", region="Bretagne")
        p.merge_update({
            "niveau_scolaire": None,
            "region": None,
            "interets_detectes": [], "contraintes": [], "valeurs": [],
            "questions_ouvertes": [], "confidence": 0.6,
        })
        assert p.niveau_scolaire == "terminale_es"
        assert p.region == "Bretagne"

    def test_merge_confidence_weighted_by_tour_count(self):
        p = UserSessionProfile(confidence=0.4, tour_count=2)
        p.merge_update({
            "interets_detectes": [], "contraintes": [], "valeurs": [],
            "questions_ouvertes": [], "confidence": 0.8,
        })
        # n=2, (0.4 * 1 + 0.8) / 2 = 0.6
        assert p.confidence == pytest.approx(0.6, abs=0.01)


# ──────────────────────────────────────────────────────────────────────
# Session : trigger détection
# ──────────────────────────────────────────────────────────────────────


class TestSessionTriggerDetection:
    def test_explicit_reco_trigger_detected(self):
        s = Session.new_anonymous()
        s.add_user_turn("Donne-moi des recos maintenant stp")
        assert s.reco_requested_explicit is True

    def test_no_explicit_reco_in_open_question(self):
        s = Session.new_anonymous()
        s.add_user_turn("Je suis en terminale et je ne sais pas quoi faire")
        assert s.reco_requested_explicit is False

    def test_should_not_trigger_synthesizer_at_tour_1_listening(self):
        s = Session.new_anonymous()
        s.add_user_turn("J'ai pris maths-physique, je veux pas faire ingé")
        assert s.profile.tour_count == 1
        assert s.should_trigger_synthesizer() is False

    def test_should_trigger_synthesizer_at_tour_3_with_confidence(self):
        s = Session.new_anonymous()
        s.add_user_turn("turn1"); s.attach_assistant_response("a1", reco_mode=False)
        s.add_user_turn("turn2"); s.attach_assistant_response("a2", reco_mode=False)
        s.add_user_turn("turn3")
        s.profile.confidence = 0.7
        assert s.profile.tour_count == 3
        assert s.should_trigger_synthesizer() is True

    def test_should_not_trigger_at_tour_3_with_low_confidence(self):
        s = Session.new_anonymous()
        for i in range(3):
            s.add_user_turn(f"t{i}")
            if i < 2:
                s.attach_assistant_response(f"a{i}", reco_mode=False)
        s.profile.confidence = 0.2  # profil encore flou
        assert s.should_trigger_synthesizer() is False

    def test_should_trigger_explicit_at_tour_2(self):
        s = Session.new_anonymous()
        s.add_user_turn("turn1")
        s.attach_assistant_response("a1", reco_mode=False)
        s.add_user_turn("Donne-moi 3 options stp, je veux trancher")
        assert s.reco_requested_explicit is True
        assert s.profile.tour_count == 2
        assert s.should_trigger_synthesizer() is True

    def test_bench_single_shot_always_triggers(self):
        s = Session.new_for_bench()
        assert s.bench_single_shot is True
        assert s.profile.tour_count == 3
        assert s.should_trigger_synthesizer() is True


# ──────────────────────────────────────────────────────────────────────
# Persona prompt : marqueurs obligatoires
# ──────────────────────────────────────────────────────────────────────


class TestPersonaPrompt:
    """Vérifie que le prompt système charge et contient les marqueurs
    obligatoires de la spec ordre Sprint 9."""

    def test_persona_prompt_loads_non_empty(self):
        p = load_persona_prompt()
        assert len(p) > 1000

    def test_contains_active_listening_marker(self):
        p = load_persona_prompt()
        assert "Active listening" in p or "active listening" in p
        assert "reformule" in p.lower()

    def test_contains_3_tours_rule(self):
        p = load_persona_prompt()
        assert "3 tours" in p.lower() or "3 échanges" in p.lower() or "tour 3" in p.lower()

    def test_contains_non_jugement_filieres_rule(self):
        p = load_persona_prompt()
        assert "non-jugement" in p.lower() or "aucune hiérarchie" in p.lower()

    def test_contains_5_few_shot_examples(self):
        p = load_persona_prompt()
        # 5 examples encadrés <example>...</example>
        assert p.count("<example>") == 5
        assert p.count("</example>") == 5

    def test_contains_tutoiement_adaptatif(self):
        p = load_persona_prompt()
        assert "tutoiement" in p.lower()

    def test_user_profile_schema_loads_valid(self):
        s = load_user_profile_schema()
        assert s["title"] == "UserSessionProfile"
        assert "niveau_scolaire" in s["properties"]
        assert "interets_detectes" in s["properties"]
        assert "contraintes" in s["properties"]
        assert "valeurs" in s["properties"]
        assert "questions_ouvertes" in s["properties"]


# ──────────────────────────────────────────────────────────────────────
# EmpathicAgent : messages format
# ──────────────────────────────────────────────────────────────────────


class TestEmpathicAgent:
    def test_build_messages_includes_persona_system_prompt(self):
        client = MagicMock()
        agent = EmpathicAgent(client=client)
        s = Session.new_anonymous()
        s.add_user_turn("Bonjour, je suis en terminale.")
        msgs = agent._build_messages(s)
        assert msgs[0]["role"] == "system"
        assert "OrientIA" in msgs[0]["content"]
        assert "Active listening" in msgs[0]["content"] or "active listening" in msgs[0]["content"]

    def test_build_messages_injects_profile_context_when_non_empty(self):
        client = MagicMock()
        agent = EmpathicAgent(client=client)
        s = Session.new_anonymous()
        s.profile.niveau_scolaire = "terminale_spe_maths_physique"
        s.profile.contraintes = ["region:occitanie", "budget:moderate"]
        s.profile.tour_count = 2
        s.add_user_turn("Question tour 3")
        msgs = agent._build_messages(s)
        sys_content = msgs[0]["content"]
        assert "terminale_spe_maths_physique" in sys_content
        assert "region:occitanie" in sys_content

    def test_build_messages_does_not_inject_profile_when_empty(self):
        client = MagicMock()
        agent = EmpathicAgent(client=client)
        s = Session.new_anonymous()
        s.add_user_turn("first message")
        msgs = agent._build_messages(s)
        assert "CONTEXTE PROFIL UTILISATEUR" not in msgs[0]["content"]

    def test_build_messages_injects_factual_base_when_provided(self):
        client = MagicMock()
        agent = EmpathicAgent(client=client)
        s = Session.new_anonymous()
        s.add_user_turn("test")
        msgs = agent._build_messages(s, factual_base="FICHE 1: BUT info Lyon...")
        assert "BASE FACTUELLE FOURNIE PAR LE SYNTHESIZERAGENT" in msgs[0]["content"]
        assert "FICHE 1: BUT info Lyon" in msgs[0]["content"]

    def test_respond_returns_empathic_response_with_text(self):
        client = MagicMock()
        client.chat.complete.return_value = _mock_chat_text_response(
            "Si je te comprends bien, tu hésites entre plusieurs voies. Qu'est-ce qui te repousse en ingé ?"
        )
        agent = EmpathicAgent(client=client)
        s = Session.new_anonymous()
        s.add_user_turn("J'ai maths-physique mais je veux pas faire ingé")
        resp = agent.respond(s)
        assert isinstance(resp, EmpathicResponse)
        assert "Si je te comprends bien" in resp.raw_text
        assert resp.reco_mode_active is False

    def test_respond_with_factual_base_marks_reco_mode_active(self):
        client = MagicMock()
        client.chat.complete.return_value = _mock_chat_text_response("Reco re-emballée...")
        agent = EmpathicAgent(client=client)
        s = Session.new_anonymous()
        s.add_user_turn("test")
        resp = agent.respond(s, factual_base="Base factuelle synthesizer")
        assert resp.reco_mode_active is True


# ──────────────────────────────────────────────────────────────────────
# AnalystAgent : passthrough non-bloquant
# ──────────────────────────────────────────────────────────────────────


class TestAnalystAgent:
    def test_update_profile_returns_empty_on_no_tool_call(self):
        client = MagicMock()
        # Pas de tool_calls → analyst doit renvoyer {} sans crash
        client.chat.complete.return_value = _mock_chat_text_response("texte sans tool")
        agent = AnalystAgent(client=client)
        s = Session.new_anonymous()
        s.add_user_turn("Je suis en terminale spé maths-physique")
        delta = agent.update_profile(s)
        assert delta == {}

    def test_update_profile_returns_empty_when_session_empty(self):
        client = MagicMock()
        agent = AnalystAgent(client=client)
        s = Session.new_anonymous()
        delta = agent.update_profile(s)
        assert delta == {}
        client.chat.complete.assert_not_called()

    def test_update_profile_returns_delta_on_valid_tool_call(self):
        client = MagicMock()
        client.chat.complete.return_value = _mock_chat_tool_response(
            "update_session_profile",
            {
                "niveau_scolaire": "terminale_spe_maths_physique",
                "interets_detectes": ["sciences", "concret"],
                "contraintes": ["region:occitanie"],
                "valeurs": ["impact_societal"],
                "questions_ouvertes": ["rapport au théorique pur ?"],
                "confidence": 0.6,
            },
        )
        agent = AnalystAgent(client=client)
        s = Session.new_anonymous()
        s.add_user_turn("turn 1")
        delta = agent.update_profile(s)
        assert delta["niveau_scolaire"] == "terminale_spe_maths_physique"
        assert delta["interets_detectes"] == ["sciences", "concret"]
        assert delta["confidence"] == 0.6

    def test_update_profile_swallows_exception(self):
        client = MagicMock()
        client.chat.complete.side_effect = RuntimeError("API down")
        agent = AnalystAgent(client=client, max_retries=0, initial_backoff=0.0)
        s = Session.new_anonymous()
        s.add_user_turn("test")
        # Ne doit JAMAIS raise — passthrough non-bloquant
        delta = agent.update_profile(s)
        assert delta == {}


# ──────────────────────────────────────────────────────────────────────
# SynthesizerAgent : embed AgentPipeline
# ──────────────────────────────────────────────────────────────────────


class TestSynthesizerAgent:
    def test_lazy_pipeline_instantiation(self):
        factory_calls = []
        mock_pipeline = MagicMock()

        def factory():
            factory_calls.append(1)
            return mock_pipeline

        agent = SynthesizerAgent(agent_pipeline_factory=factory)
        # Pas d'instantiation au construct
        assert factory_calls == []

        # Instantiation au premier accès
        _ = agent.pipeline
        assert factory_calls == [1]

        # Pas de re-instantiation au 2e accès (cache)
        _ = agent.pipeline
        assert factory_calls == [1]

    def test_synthesize_calls_agent_pipeline_with_enriched_query(self):
        mock_pipeline = MagicMock()
        from src.agent.pipeline_agent import AgentAnswer
        mock_pipeline.answer.return_value = AgentAnswer(
            query="anything",
            answer_text="Plan A : BUT Info Lyon...",
            profile=None,
            plan=None,
            sources_aggregated=[{"score": 0.9, "fiche": {"id": "F1"}}],
        )

        agent = SynthesizerAgent(agent_pipeline_factory=lambda: mock_pipeline)
        s = Session.new_anonymous()
        s.profile.region = "Occitanie"
        s.profile.contraintes = ["budget:moderate"]
        s.add_user_turn("Quelles formations en info ?")

        result = agent.synthesize(s)
        assert result.raw_factual_text == "Plan A : BUT Info Lyon..."
        assert result.sources_count == 1
        # La query enrichie doit contenir le contexte profil
        called_query = mock_pipeline.answer.call_args[0][0]
        assert "Quelles formations en info" in called_query
        assert "Occitanie" in called_query
        assert "budget:moderate" in called_query

    def test_synthesize_passthrough_on_pipeline_error(self):
        mock_pipeline = MagicMock()
        mock_pipeline.answer.side_effect = RuntimeError("FAISS index missing")
        agent = SynthesizerAgent(agent_pipeline_factory=lambda: mock_pipeline)
        s = Session.new_anonymous()
        s.add_user_turn("test")
        result = agent.synthesize(s)
        assert result.raw_factual_text == ""
        assert result.sources_count == 0


# ──────────────────────────────────────────────────────────────────────
# Coordinator : orchestration end-to-end (mocks)
# ──────────────────────────────────────────────────────────────────────


def _make_coordinator_with_mocks(synthesizer_response_text: str = "Factual base..."):
    """Builder de Coordinator avec sub-agents mockés."""
    empathic = MagicMock(spec=EmpathicAgent)
    analyst = MagicMock(spec=AnalystAgent)
    synthesizer = MagicMock(spec=SynthesizerAgent)

    empathic.respond.return_value = EmpathicResponse(
        reformulation="Si je te comprends bien...",
        exploration_or_reco="texte conseiller",
        reco_mode_active=False,
        raw_text="Si je te comprends bien... texte conseiller",
    )
    analyst.update_profile.return_value = {
        "niveau_scolaire": "terminale_spe_maths_physique",
        "interets_detectes": ["sciences"],
        "contraintes": [], "valeurs": [], "questions_ouvertes": [],
        "confidence": 0.4,
    }
    synthesizer.synthesize.return_value = SynthesizedFactualBase(
        raw_factual_text=synthesizer_response_text,
        sources_count=3,
        elapsed_s=2.5,
    )

    coord = Coordinator(empathic=empathic, analyst=analyst, synthesizer=synthesizer)
    return coord, empathic, analyst, synthesizer


class TestCoordinator:
    def test_listening_mode_does_not_call_synthesizer_at_tour_1(self):
        coord, empathic, analyst, synthesizer = _make_coordinator_with_mocks()
        s = Session.new_anonymous()
        result = coord.respond(s, "Je suis en terminale, je sais pas quoi faire")

        # Tour 1 + pas de trigger explicite → pas de SynthesizerAgent
        synthesizer.synthesize.assert_not_called()
        # EmpathicAgent appelé sans factual_base
        empathic.respond.assert_called_once()
        call_kwargs = empathic.respond.call_args
        assert call_kwargs.args[1] is None  # factual_base=None
        # AnalystAgent appelé toujours
        analyst.update_profile.assert_called_once()

        assert result.reco_mode_active is False
        assert result.factual_sources_count == 0

    def test_reco_mode_invokes_synthesizer_when_explicit_trigger_at_tour_2(self):
        coord, empathic, analyst, synthesizer = _make_coordinator_with_mocks(
            synthesizer_response_text="Plan A: BUT Info..."
        )
        # Mock empathic to mark reco mode when factual_base provided
        def empathic_respond(session, factual_base):
            return EmpathicResponse(
                reformulation="...",
                exploration_or_reco="reco re-emballée",
                reco_mode_active=factual_base is not None,
                raw_text="reco re-emballée",
            )
        empathic.respond.side_effect = empathic_respond

        s = Session.new_anonymous()
        # Tour 1
        coord.respond(s, "test tour 1")
        # Tour 2 avec trigger explicite
        result = coord.respond(s, "Donne-moi 3 options de formations stp")

        # SynthesizerAgent invoqué au tour 2 (trigger explicite)
        synthesizer.synthesize.assert_called_once()
        assert result.reco_mode_active is True
        assert "Plan A" not in result.response_text  # EmpathicAgent re-emballe
        assert result.factual_sources_count == 3

    def test_single_shot_mode_for_bench_invokes_synthesizer_directly(self):
        coord, empathic, analyst, synthesizer = _make_coordinator_with_mocks()

        def empathic_respond(session, factual_base):
            return EmpathicResponse(
                reformulation="",
                exploration_or_reco="",
                reco_mode_active=factual_base is not None,
                raw_text="reco re-emballée single-shot",
            )
        empathic.respond.side_effect = empathic_respond

        result = coord.respond_single_shot("Quelles écoles d'ingé en info à Lyon ?")
        synthesizer.synthesize.assert_called_once()
        assert result.reco_mode_active is True
        assert "single-shot" in result.response_text

    def test_profile_delta_merged_into_session(self):
        coord, empathic, analyst, synthesizer = _make_coordinator_with_mocks()
        s = Session.new_anonymous()
        coord.respond(s, "Je suis en terminale spé maths-physique en Occitanie")
        # Le delta retourné par le mock analyst doit être fusionné
        assert s.profile.niveau_scolaire == "terminale_spe_maths_physique"
        assert "sciences" in s.profile.interets_detectes


# ──────────────────────────────────────────────────────────────────────
# Non-régression bench : SynthesizerAgent propage la réponse AgentPipeline
# (proxy 10q gratuit avant full bench $11)
# ──────────────────────────────────────────────────────────────────────


class TestNonRegressionBenchProxy:
    """Le SynthesizerAgent embed AgentPipeline TEL QUEL — la réponse
    factual_text propagée doit être structurellement identique à ce que
    AgentPipeline.answer().answer_text aurait produit en single-shot.
    Ces tests valident le contract de propagation, pas la qualité de la
    réponse Mistral réelle (mockée)."""

    def test_synthesizer_propagates_agent_pipeline_text_verbatim(self):
        from src.agent.pipeline_agent import AgentAnswer
        mock_pipeline = MagicMock()
        verbatim_answer = (
            "Plan A — BUT Informatique (taux 35%, 2 ans, source Parcoursup)\n"
            "Plan B — Licence Info Sorbonne (taux 60%, 3 ans, source ONISEP FOR.1577)\n"
        )
        mock_pipeline.answer.return_value = AgentAnswer(
            query="bench query",
            answer_text=verbatim_answer,
            profile=None, plan=None,
            sources_aggregated=[
                {"score": 0.95, "fiche": {"id": "F1"}},
                {"score": 0.88, "fiche": {"id": "F2"}},
            ],
        )

        agent = SynthesizerAgent(agent_pipeline_factory=lambda: mock_pipeline)
        s = Session.new_for_bench()
        s.add_user_turn("Quelles formations info après terminale ?")

        result = agent.synthesize(s)
        # Texte verbatim propagé sans altération — garantie bench non-régression
        assert result.raw_factual_text == verbatim_answer
        assert result.sources_count == 2

    def test_coordinator_single_shot_uses_synthesizer_factual_base(self):
        """Le bench single-shot doit toujours router via SynthesizerAgent
        (pas de fallback listening-only même si profile vide). Garantit
        la cohabitation avec systems.py:HierarchicalSystem."""
        from src.agent.pipeline_agent import AgentAnswer
        mock_pipeline = MagicMock()
        mock_pipeline.answer.return_value = AgentAnswer(
            query="x", answer_text="factual reco baseline mode",
            profile=None, plan=None, sources_aggregated=[],
        )
        client = MagicMock()
        client.chat.complete.return_value = _mock_chat_text_response("repacked reco")

        coord = Coordinator(
            empathic=EmpathicAgent(client=client),
            analyst=AnalystAgent(client=client),
            synthesizer=SynthesizerAgent(agent_pipeline_factory=lambda: mock_pipeline),
        )
        result = coord.respond_single_shot("bench query")
        # AgentPipeline a bien été invoqué (preuve non-régression structurelle)
        mock_pipeline.answer.assert_called_once()
        # Coordinator a propagé la réponse EmpathicAgent (qui re-emballe)
        assert result.response_text == "repacked reco"
        assert result.reco_mode_active is True
