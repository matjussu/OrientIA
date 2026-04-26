"""Tests src/agent/tools/profile_clarifier.py — Profile + tool func + clarifier (mocked)."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from src.agent.tools.profile_clarifier import (
    Profile,
    ProfileClarifier,
    PROFILE_CLARIFIER_TOOL,
    VALID_AGE_GROUPS,
    VALID_EDUCATION_LEVELS,
    VALID_INTENT_TYPES,
    _profile_clarifier_tool_func,
)


# --- Profile dataclass ---


class TestProfile:
    def test_minimal_construction(self):
        p = Profile(
            age_group="lyceen_terminale",
            education_level="terminale",
            intent_type="orientation_initiale",
            sector_interest=["informatique"],
        )
        assert p.is_valid()
        assert p.region is None
        assert p.urgent_concern is False
        assert p.confidence == 0.5

    def test_full_construction(self):
        p = Profile(
            age_group="adulte_25_45",
            education_level="bac+5",
            intent_type="reconversion_pro",
            sector_interest=["sante", "education"],
            region="Bretagne",
            urgent_concern=True,
            confidence=0.85,
            notes="Reconversion post-burn-out",
        )
        assert p.is_valid()
        assert p.region == "Bretagne"
        assert p.urgent_concern is True

    def test_invalid_age_group(self):
        p = Profile(
            age_group="alien_visitor",
            education_level="bac+3",
            intent_type="orientation_initiale",
            sector_interest=[],
        )
        assert not p.is_valid()

    def test_invalid_education(self):
        p = Profile(
            age_group="etudiant_l1_l3",
            education_level="bac+42",
            intent_type="orientation_initiale",
            sector_interest=[],
        )
        assert not p.is_valid()

    def test_invalid_intent(self):
        p = Profile(
            age_group="etudiant_l1_l3",
            education_level="bac+2",
            intent_type="something_random",
            sector_interest=[],
        )
        assert not p.is_valid()

    def test_invalid_confidence_above_1(self):
        p = Profile(
            age_group="lyceen_terminale",
            education_level="terminale",
            intent_type="orientation_initiale",
            sector_interest=[],
            confidence=1.5,
        )
        assert not p.is_valid()

    def test_invalid_sector_not_list(self):
        p = Profile(
            age_group="lyceen_terminale",
            education_level="terminale",
            intent_type="orientation_initiale",
            sector_interest="informatique",  # string instead of list
        )
        assert not p.is_valid()

    def test_to_dict_roundtrip(self):
        p = Profile(
            age_group="bachelier_general",
            education_level="bac_obtenu",
            intent_type="comparaison_options",
            sector_interest=["droit"],
            region="Île-de-France",
            urgent_concern=False,
            confidence=0.7,
            notes=None,
        )
        d = p.to_dict()
        p2 = Profile(**d)
        assert p == p2


# --- Tool func wrapper ---


class TestProfileClarifierToolFunc:
    def test_valid_call(self):
        result = _profile_clarifier_tool_func(
            age_group="lyceen_terminale",
            education_level="terminale",
            intent_type="orientation_initiale",
            sector_interest=["numerique"],
            region="La Réunion",
            urgent_concern=False,
            confidence=0.8,
            notes=None,
        )
        assert result["valid"] is True
        assert result["profile"]["age_group"] == "lyceen_terminale"
        assert result["profile"]["region"] == "La Réunion"

    def test_invalid_enum_returns_error(self):
        result = _profile_clarifier_tool_func(
            age_group="invalid_xxx",
            education_level="terminale",
            intent_type="orientation_initiale",
            sector_interest=[],
            urgent_concern=False,
            confidence=0.5,
        )
        assert "error" in result

    def test_missing_required_uses_defaults(self):
        # Le wrapper utilise des defaults sécurisés ('other_or_unknown'
        # / 'unknown' / 'other') quand le LLM omet un champ — pour ne
        # pas crasher. Le profile peut quand même être valid si tous
        # les enums sont valides.
        result = _profile_clarifier_tool_func(sector_interest=[])
        assert result.get("valid") is True
        assert result["profile"]["age_group"] == "other_or_unknown"
        assert result["profile"]["education_level"] == "unknown"
        assert result["profile"]["intent_type"] == "other"

    def test_empty_sector_list(self):
        result = _profile_clarifier_tool_func(
            age_group="lyceen_terminale",
            education_level="terminale",
            intent_type="orientation_initiale",
            sector_interest=[],
            urgent_concern=False,
            confidence=0.5,
        )
        assert result["valid"] is True
        assert result["profile"]["sector_interest"] == []


# --- Mistral PROFILE_CLARIFIER_TOOL definition ---


class TestProfileClarifierToolDefinition:
    def test_tool_name(self):
        assert PROFILE_CLARIFIER_TOOL.name == "extract_user_profile"

    def test_tool_description_clear(self):
        # Description doit mentionner ce qu'extrait le tool
        d = PROFILE_CLARIFIER_TOOL.description.lower()
        assert "profil" in d or "profile" in d

    def test_tool_required_fields(self):
        required = set(PROFILE_CLARIFIER_TOOL.parameters["required"])
        assert "age_group" in required
        assert "education_level" in required
        assert "intent_type" in required
        assert "sector_interest" in required

    def test_tool_enums_valid(self):
        props = PROFILE_CLARIFIER_TOOL.parameters["properties"]
        assert set(props["age_group"]["enum"]) == VALID_AGE_GROUPS
        assert set(props["education_level"]["enum"]) == VALID_EDUCATION_LEVELS
        assert set(props["intent_type"]["enum"]) == VALID_INTENT_TYPES

    def test_to_mistral_schema_format(self):
        schema = PROFILE_CLARIFIER_TOOL.to_mistral_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "extract_user_profile"


# --- ProfileClarifier (mocked Mistral) ---


def _mock_mistral_response(args_dict):
    """Construit un mock de réponse Mistral avec un tool_call sur extract_user_profile."""
    tool_call = MagicMock()
    tool_call.function.name = "extract_user_profile"
    tool_call.function.arguments = json.dumps(args_dict)

    msg = MagicMock()
    msg.tool_calls = [tool_call]
    msg.content = ""

    response = MagicMock()
    response.choices = [MagicMock(message=msg)]
    return response


class TestProfileClarifier:
    def test_clarify_simple_query(self):
        client = MagicMock()
        client.chat.complete.return_value = _mock_mistral_response({
            "age_group": "lyceen_terminale",
            "education_level": "terminale",
            "intent_type": "orientation_initiale",
            "sector_interest": ["informatique"],
            "region": "Île-de-France",
            "urgent_concern": False,
            "confidence": 0.9,
            "notes": "Query explicite avec niveau et région",
        })
        clarifier = ProfileClarifier(client=client)
        profile = clarifier.clarify("Je suis en terminale à Paris, j'aime l'informatique")
        assert profile.age_group == "lyceen_terminale"
        assert profile.region == "Île-de-France"
        assert profile.confidence == 0.9

    def test_clarify_no_tool_call_raises(self):
        client = MagicMock()
        msg = MagicMock()
        msg.tool_calls = None
        msg.content = "Je ne sais pas extraire ce profil"
        response = MagicMock()
        response.choices = [MagicMock(message=msg)]
        client.chat.complete.return_value = response

        clarifier = ProfileClarifier(client=client)
        with pytest.raises(ValueError, match="n'a pas appelé le tool"):
            clarifier.clarify("???")

    def test_clarify_wrong_tool_raises(self):
        client = MagicMock()
        tool_call = MagicMock()
        tool_call.function.name = "some_other_tool"
        tool_call.function.arguments = "{}"
        msg = MagicMock()
        msg.tool_calls = [tool_call]
        msg.content = ""
        response = MagicMock()
        response.choices = [MagicMock(message=msg)]
        client.chat.complete.return_value = response

        clarifier = ProfileClarifier(client=client)
        with pytest.raises(ValueError, match="tool inattendu"):
            clarifier.clarify("test")

    def test_clarify_invalid_json_raises(self):
        client = MagicMock()
        tool_call = MagicMock()
        tool_call.function.name = "extract_user_profile"
        tool_call.function.arguments = "{invalid json"
        msg = MagicMock()
        msg.tool_calls = [tool_call]
        msg.content = ""
        response = MagicMock()
        response.choices = [MagicMock(message=msg)]
        client.chat.complete.return_value = response

        clarifier = ProfileClarifier(client=client)
        with pytest.raises(ValueError, match="JSON parse failed"):
            clarifier.clarify("test")

    def test_clarify_invalid_profile_data_raises(self):
        client = MagicMock()
        client.chat.complete.return_value = _mock_mistral_response({
            "age_group": "invalid_xxx",  # not in VALID_AGE_GROUPS
            "education_level": "terminale",
            "intent_type": "orientation_initiale",
            "sector_interest": [],
            "urgent_concern": False,
            "confidence": 0.5,
        })
        clarifier = ProfileClarifier(client=client)
        with pytest.raises(ValueError, match="returned error"):
            clarifier.clarify("test")
