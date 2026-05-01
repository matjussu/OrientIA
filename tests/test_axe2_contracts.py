"""Tests Pydantic typed contracts Axe 2 — Sprint 12 Phase 1 A1.

Référence ordre : 2026-05-01-1820-claudette-orientia-sprint12-axe-2-agentic-phase-1-A1-A2-A4 (A1).

Couvre :
- Round-trip JSON via `model_dump_json()` + `model_validate_json()` (5 modèles)
- Validation runtime : `extra="forbid"`, `Field(..., ge=, le=)` constraints
- Enums : valeurs strictes, rejet valeurs hors-enum
- Edge cases : champs requis manquants, types invalides, contraintes bornées
- Régression Sprint 9 : assertions `UserSessionProfile` dataclass intact

Pas de bench LLM, pas de coût API. Tests pure validation Pydantic.
"""
from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from src.axe2 import (
    AgentInput,
    AgentOutput,
    AgeGroup,
    EducationLevel,
    IntentType,
    ProfileState,
    SubQuestion,
    ToolCallResult,
)


# =============================================================================
# Round-trip JSON
# =============================================================================


class TestProfileStateRoundtrip:
    def test_minimal_required_fields(self):
        p = ProfileState(
            age_group=AgeGroup.LYCEEN_TERMINALE,
            education_level=EducationLevel.TERMINALE,
            intent_type=IntentType.ORIENTATION_INITIALE,
        )
        # Defaults appliqués
        assert p.sector_interest == []
        assert p.region is None
        assert p.urgent_concern is False
        assert p.confidence == 0.5

    def test_full_roundtrip_json(self):
        original = ProfileState(
            age_group=AgeGroup.BACHELIER_TECHNO,
            education_level=EducationLevel.BAC_OBTENU,
            intent_type=IntentType.COMPARAISON_OPTIONS,
            sector_interest=["informatique", "santé"],
            region="Île-de-France",
            urgent_concern=True,
            confidence=0.85,
        )
        js = original.model_dump_json()
        rebuilt = ProfileState.model_validate_json(js)
        assert rebuilt == original

    def test_dict_roundtrip(self):
        p = ProfileState(
            age_group=AgeGroup.PROFESSIONNEL_ACTIF,
            education_level=EducationLevel.BAC_PLUS_5,
            intent_type=IntentType.RECONVERSION_PRO,
            confidence=0.7,
        )
        d = p.model_dump()
        rebuilt = ProfileState.model_validate(d)
        assert rebuilt == p


class TestSubQuestionRoundtrip:
    def test_minimal(self):
        sq = SubQuestion(id="sq_1", text="Quelles formations cyber ?")
        assert sq.requires_tools == []
        assert sq.depends_on == []

    def test_full_roundtrip(self):
        sq = SubQuestion(
            id="sq_2_a",
            text="Insertion 6m Master MIAGE Tours ?",
            requires_tools=["search_formations", "get_debouches"],
            depends_on=["sq_1"],
        )
        rebuilt = SubQuestion.model_validate_json(sq.model_dump_json())
        assert rebuilt == sq


class TestToolCallResultRoundtrip:
    def test_success_with_payload(self):
        r = ToolCallResult(
            tool_name="search_formations",
            success=True,
            payload={"fiches": [{"nom": "Bachelor cyber EFREI", "score": 0.87}]},
            elapsed_ms=124,
        )
        rebuilt = ToolCallResult.model_validate_json(r.model_dump_json())
        assert rebuilt == r

    def test_failure_with_error(self):
        r = ToolCallResult(
            tool_name="get_debouches",
            success=False,
            error="rncp_not_found",
            elapsed_ms=15,
        )
        rebuilt = ToolCallResult.model_validate_json(r.model_dump_json())
        assert rebuilt == r
        assert rebuilt.payload == {}


class TestAgentInputRoundtrip:
    def test_first_turn(self):
        ai = AgentInput(
            user_query="Je suis en terminale, alternatives à la prépa MPSI ?",
            profile=ProfileState(
                age_group=AgeGroup.LYCEEN_TERMINALE,
                education_level=EducationLevel.TERMINALE,
                intent_type=IntentType.ORIENTATION_INITIALE,
            ),
        )
        assert ai.history == []
        assert ai.max_tool_calls == 4

    def test_with_history_and_max_calls(self):
        ai = AgentInput(
            user_query="Et l'EFREI Bordeaux ?",
            profile=ProfileState(
                age_group=AgeGroup.BACHELIER_GENERAL,
                education_level=EducationLevel.BAC_OBTENU,
                intent_type=IntentType.COMPARAISON_OPTIONS,
            ),
            history=[
                {"role": "user", "content": "Quelles écoles cyber post-bac ?"},
                {"role": "assistant", "content": "Plusieurs options..."},
            ],
            max_tool_calls=6,
        )
        rebuilt = AgentInput.model_validate_json(ai.model_dump_json())
        assert rebuilt == ai
        assert len(rebuilt.history) == 2


class TestAgentOutputRoundtrip:
    def test_with_tool_calls_and_hint(self):
        ao = AgentOutput(
            tool_calls_made=[
                ToolCallResult(
                    tool_name="search_formations",
                    success=True,
                    payload={"fiches_count": 5},
                    elapsed_ms=200,
                ),
                ToolCallResult(
                    tool_name="get_admission_calendar",
                    success=True,
                    payload={"phase": "principale"},
                    elapsed_ms=10,
                ),
            ],
            final_answer_hint="Tu peux explorer 3 pistes : EFREI, ENSIBS, ESIEE.",
            stopped_reason="sonnet_decided_done",
            elapsed_orchestration_ms=850,
        )
        rebuilt = AgentOutput.model_validate_json(ao.model_dump_json())
        assert rebuilt == ao
        assert len(rebuilt.tool_calls_made) == 2

    def test_no_tool_calls_no_hint(self):
        ao = AgentOutput(stopped_reason="error_critical")
        assert ao.tool_calls_made == []
        assert ao.final_answer_hint is None


# =============================================================================
# Validation runtime — extra="forbid"
# =============================================================================


class TestExtraForbid:
    def test_profile_state_rejects_extra_field(self):
        with pytest.raises(ValidationError) as exc:
            ProfileState.model_validate({
                "age_group": "lyceen_terminale",
                "education_level": "terminale",
                "intent_type": "orientation_initiale",
                "secret_field": "should_be_rejected",  # extra
            })
        assert "extra" in str(exc.value).lower() or "secret_field" in str(exc.value)

    def test_subquestion_rejects_extra_field(self):
        with pytest.raises(ValidationError):
            SubQuestion.model_validate({
                "id": "sq_1",
                "text": "?",
                "extra_meta": {"oops": True},
            })

    def test_tool_call_result_rejects_extra_field(self):
        with pytest.raises(ValidationError):
            ToolCallResult.model_validate({
                "tool_name": "search",
                "success": True,
                "extra": "field",
            })

    def test_agent_input_rejects_extra_field(self):
        with pytest.raises(ValidationError):
            AgentInput.model_validate({
                "user_query": "?",
                "profile": {
                    "age_group": "lyceen_terminale",
                    "education_level": "terminale",
                    "intent_type": "orientation_initiale",
                },
                "fake_field": 42,
            })

    def test_agent_output_rejects_extra_field(self):
        with pytest.raises(ValidationError):
            AgentOutput.model_validate({
                "stopped_reason": "ok",
                "extra": "field",
            })


# =============================================================================
# Validation runtime — Field constraints
# =============================================================================


class TestFieldConstraints:
    def test_profile_state_confidence_below_0_rejected(self):
        with pytest.raises(ValidationError) as exc:
            ProfileState(
                age_group=AgeGroup.LYCEEN_TERMINALE,
                education_level=EducationLevel.TERMINALE,
                intent_type=IntentType.ORIENTATION_INITIALE,
                confidence=-0.1,
            )
        assert "confidence" in str(exc.value).lower() or "ge" in str(exc.value).lower()

    def test_profile_state_confidence_above_1_rejected(self):
        with pytest.raises(ValidationError):
            ProfileState(
                age_group=AgeGroup.LYCEEN_TERMINALE,
                education_level=EducationLevel.TERMINALE,
                intent_type=IntentType.ORIENTATION_INITIALE,
                confidence=1.5,
            )

    def test_profile_state_confidence_at_bounds_accepted(self):
        for v in (0.0, 1.0):
            p = ProfileState(
                age_group=AgeGroup.LYCEEN_TERMINALE,
                education_level=EducationLevel.TERMINALE,
                intent_type=IntentType.ORIENTATION_INITIALE,
                confidence=v,
            )
            assert p.confidence == v

    def test_subquestion_id_empty_rejected(self):
        with pytest.raises(ValidationError):
            SubQuestion(id="", text="?")

    def test_subquestion_text_empty_rejected(self):
        with pytest.raises(ValidationError):
            SubQuestion(id="sq_1", text="")

    def test_tool_call_result_elapsed_ms_negative_rejected(self):
        with pytest.raises(ValidationError):
            ToolCallResult(
                tool_name="search",
                success=True,
                elapsed_ms=-5,
            )

    def test_agent_input_max_tool_calls_below_1_rejected(self):
        profile = ProfileState(
            age_group=AgeGroup.LYCEEN_TERMINALE,
            education_level=EducationLevel.TERMINALE,
            intent_type=IntentType.ORIENTATION_INITIALE,
        )
        with pytest.raises(ValidationError):
            AgentInput(user_query="?", profile=profile, max_tool_calls=0)

    def test_agent_input_max_tool_calls_above_10_rejected(self):
        profile = ProfileState(
            age_group=AgeGroup.LYCEEN_TERMINALE,
            education_level=EducationLevel.TERMINALE,
            intent_type=IntentType.ORIENTATION_INITIALE,
        )
        with pytest.raises(ValidationError):
            AgentInput(user_query="?", profile=profile, max_tool_calls=11)

    def test_agent_input_user_query_empty_rejected(self):
        profile = ProfileState(
            age_group=AgeGroup.LYCEEN_TERMINALE,
            education_level=EducationLevel.TERMINALE,
            intent_type=IntentType.ORIENTATION_INITIALE,
        )
        with pytest.raises(ValidationError):
            AgentInput(user_query="", profile=profile)


# =============================================================================
# Validation runtime — Enums stricts
# =============================================================================


class TestEnumValidation:
    def test_profile_state_unknown_age_group_rejected(self):
        with pytest.raises(ValidationError):
            ProfileState.model_validate({
                "age_group": "lyceen_inexistant",  # invalid
                "education_level": "terminale",
                "intent_type": "orientation_initiale",
            })

    def test_profile_state_accepts_string_enum_value(self):
        """Pydantic accepte la valeur string brute pour enum (interop JSON)."""
        p = ProfileState.model_validate({
            "age_group": "bachelier_general",  # string, pas enum object
            "education_level": "bac_obtenu",
            "intent_type": "decouverte_filieres",
        })
        assert p.age_group == AgeGroup.BACHELIER_GENERAL

    def test_all_age_groups_present_match_legacy_enums(self):
        """Régression : valeurs AgeGroup match VALID_AGE_GROUPS Sprint 1 legacy."""
        from src.agent.tools.profile_clarifier import VALID_AGE_GROUPS
        axe2_values = {ag.value for ag in AgeGroup}
        assert axe2_values == VALID_AGE_GROUPS

    def test_all_education_levels_match_legacy(self):
        from src.agent.tools.profile_clarifier import VALID_EDUCATION_LEVELS
        axe2_values = {el.value for el in EducationLevel}
        assert axe2_values == VALID_EDUCATION_LEVELS

    def test_all_intent_types_match_legacy(self):
        from src.agent.tools.profile_clarifier import VALID_INTENT_TYPES
        axe2_values = {it.value for it in IntentType}
        assert axe2_values == VALID_INTENT_TYPES


# =============================================================================
# Validation runtime — Required fields
# =============================================================================


class TestRequiredFields:
    def test_profile_state_age_group_required(self):
        with pytest.raises(ValidationError):
            ProfileState.model_validate({
                "education_level": "terminale",
                "intent_type": "orientation_initiale",
            })

    def test_profile_state_education_level_required(self):
        with pytest.raises(ValidationError):
            ProfileState.model_validate({
                "age_group": "lyceen_terminale",
                "intent_type": "orientation_initiale",
            })

    def test_profile_state_intent_type_required(self):
        with pytest.raises(ValidationError):
            ProfileState.model_validate({
                "age_group": "lyceen_terminale",
                "education_level": "terminale",
            })

    def test_tool_call_result_tool_name_and_success_required(self):
        with pytest.raises(ValidationError):
            ToolCallResult.model_validate({"success": True})  # tool_name missing
        with pytest.raises(ValidationError):
            ToolCallResult.model_validate({"tool_name": "x"})  # success missing

    def test_agent_output_stopped_reason_required(self):
        with pytest.raises(ValidationError):
            AgentOutput.model_validate({})


# =============================================================================
# Régression Sprint 9 — UserSessionProfile dataclass préservé
# =============================================================================


class TestRegressionSprint9:
    def test_user_session_profile_dataclass_unchanged(self):
        """A1 ne doit PAS toucher Sprint 9 hierarchical schemas
        (R3 isolated strict)."""
        from src.agents.hierarchical.schemas import UserSessionProfile

        p = UserSessionProfile()
        # Champs existants Sprint 9 préservés
        assert p.niveau_scolaire is None
        assert p.age_estime is None
        assert p.region is None
        assert p.interets_detectes == []
        assert p.contraintes == []
        assert p.valeurs == []
        assert p.questions_ouvertes == []
        assert p.confidence == 0.0
        assert p.tour_count == 0

    def test_empathic_response_dataclass_unchanged(self):
        from src.agents.hierarchical.schemas import EmpathicResponse

        r = EmpathicResponse(reformulation="Si je te comprends bien...")
        assert r.emotion_recognition is None
        assert r.exploration_or_reco == ""
        assert r.closing_question is None
        assert r.reco_mode_active is False
        assert r.raw_text == ""

    def test_axe2_contracts_module_isolated_from_sprint9(self):
        """Test fumigant : importer src.axe2 ne doit PAS importer ni
        modifier src.agents.hierarchical.schemas (couplage zéro)."""
        import src.axe2.contracts as axe2_contracts
        # Le module Pydantic ne référence aucun symbole Sprint 9
        source = open(axe2_contracts.__file__).read()
        assert "from src.agents.hierarchical" not in source
        assert "from src.agents" not in source


# =============================================================================
# Smoke tests — Sérialisation Anthropic SDK / OpenAI SDK compat
# =============================================================================


class TestSerializationCompat:
    def test_profile_state_json_schema_exportable(self):
        """JSON schema export est utile pour orchestrateur Sonnet 4.5
        (tool definitions). Smoke test."""
        schema = ProfileState.model_json_schema()
        assert "properties" in schema
        assert "age_group" in schema["properties"]
        assert "education_level" in schema["properties"]
        assert "intent_type" in schema["properties"]

    def test_agent_input_json_dump_is_valid_json(self):
        ai = AgentInput(
            user_query="Hello",
            profile=ProfileState(
                age_group=AgeGroup.LYCEEN_TERMINALE,
                education_level=EducationLevel.TERMINALE,
                intent_type=IntentType.ORIENTATION_INITIALE,
            ),
        )
        s = ai.model_dump_json()
        # Re-parse comme JSON brut → assure validité format
        d = json.loads(s)
        assert d["user_query"] == "Hello"
        assert d["profile"]["age_group"] == "lyceen_terminale"

    def test_tool_call_result_payload_complex_types_supported(self):
        """payload est dict[str, Any] — autorise listes imbriquées + nested dicts
        + types primitifs."""
        r = ToolCallResult(
            tool_name="search",
            success=True,
            payload={
                "fiches": [
                    {"nom": "F1", "score": 0.9, "tags": ["a", "b"]},
                    {"nom": "F2", "score": 0.7, "metadata": {"region": "IDF"}},
                ],
                "total": 2,
            },
        )
        rebuilt = ToolCallResult.model_validate_json(r.model_dump_json())
        assert rebuilt == r
        assert rebuilt.payload["fiches"][1]["metadata"]["region"] == "IDF"
