"""Tests unitaires RouterLLM — étape 1 : dataclasses + tool params + prompts.

Cette étape ne teste PAS l'appel LLM (qui sera implémenté étape 3 + testé
avec mocks là). Ici on valide :
- RouteDecision construction, validation, post_init
- RouteDecision.from_tool_payload tolère les clés manquantes
- RouteDecision.hardlock_block_for_prompt formatte correctement
- ROUTE_DECISION_TOOL.to_mistral_schema() retourne le bon format
- _route_decision_tool_func normalise correctement
- ROUTER_SYSTEM_PROMPT contient les éléments critiques (sub_indexes nommés)
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.rag.metadata_filter import FilterCriteria
from src.rag.router_llm import (
    REFUSAL_REASONS,
    REFUSAL_TEMPLATES,
    ROUTE_DECISION_TOOL,
    ROUTE_DECISION_TOOL_PARAMS,
    ROUTER_SYSTEM_PROMPT,
    RouteDecision,
    SUB_INDEX_NAMES,
    _route_decision_tool_func,
)


# ────────────────────────── Constantes ──────────────────────────


def test_sub_index_names_are_four() -> None:
    """Les 4 sub-indexes attendus sont définis."""
    assert SUB_INDEX_NAMES == (
        "formations",
        "metiers",
        "statistiques",
        "aides_territoires",
    )


def test_refusal_reasons_match_schema() -> None:
    """Les 3 raisons de refus sont définies."""
    assert REFUSAL_REASONS == (
        "superlative_no_data",
        "cross_domain",
        "out_of_scope_specific",
    )


def test_refusal_templates_cover_all_reasons() -> None:
    """Chaque refusal_reason a un template pré-écrit non vide."""
    for reason in REFUSAL_REASONS:
        assert reason in REFUSAL_TEMPLATES
        assert len(REFUSAL_TEMPLATES[reason]) > 50


# ────────────────────────── RouteDecision construction ──────────────────────────


def test_route_decision_default_is_safe_fallback() -> None:
    """Default: tous sub_indexes (pas de routing), confidence=0, no refusal."""
    rd = RouteDecision()
    assert rd.sub_indexes == list(SUB_INDEX_NAMES)
    assert rd.criteria is None
    assert rd.refusal_reason is None
    assert rd.pre_written_response is None
    assert rd.confidence == 0.0
    assert rd.is_fallback is False


def test_route_decision_dedupes_sub_indexes() -> None:
    """sub_indexes dupliqués sont déduplicés en préservant l'ordre."""
    rd = RouteDecision(sub_indexes=["formations", "metiers", "formations", "metiers"])
    assert rd.sub_indexes == ["formations", "metiers"]


def test_route_decision_invalid_sub_index_raises() -> None:
    """sub_indexes hors enum → ValueError."""
    with pytest.raises(ValueError, match="sub_indexes contient des valeurs invalides"):
        RouteDecision(sub_indexes=["formations", "wrong_name"])


def test_route_decision_empty_sub_indexes_falls_back_to_all() -> None:
    """sub_indexes=[] → toutes les routes (filet de sécurité)."""
    rd = RouteDecision(sub_indexes=[])
    assert rd.sub_indexes == list(SUB_INDEX_NAMES)


def test_route_decision_invalid_refusal_reason_raises() -> None:
    """refusal_reason hors enum → ValueError."""
    with pytest.raises(ValueError, match="refusal_reason invalide"):
        RouteDecision(refusal_reason="hallucinated_reason")


def test_route_decision_refusal_auto_populates_pre_written() -> None:
    """Si refusal_reason set sans pre_written_response, le template s'applique."""
    rd = RouteDecision(refusal_reason="superlative_no_data")
    assert rd.pre_written_response is not None
    assert "classement" in rd.pre_written_response.lower()


def test_route_decision_refusal_explicit_response_preserved() -> None:
    """Si pre_written_response est explicitement fourni, il n'est pas écrasé."""
    rd = RouteDecision(
        refusal_reason="cross_domain",
        pre_written_response="Custom refusal text",
    )
    assert rd.pre_written_response == "Custom refusal text"


def test_route_decision_confidence_clamped_above() -> None:
    """confidence > 1.0 → 1.0."""
    rd = RouteDecision(confidence=1.5)
    assert rd.confidence == 1.0


def test_route_decision_confidence_clamped_below() -> None:
    """confidence < 0.0 → 0.0."""
    rd = RouteDecision(confidence=-0.3)
    assert rd.confidence == 0.0


# ────────────────────────── RouteDecision.from_tool_payload ──────────────────────────


def test_from_tool_payload_canonical() -> None:
    """Payload canonique LLM → RouteDecision attendu."""
    payload = {
        "sub_indexes": ["aides_territoires"],
        "region": "Bretagne",
        "niveau_min": None,
        "niveau_max": None,
        "secteur": ["informatique"],
        "domain_lock": ["crous"],
        "refusal_reason": None,
        "hardlock_region_strict": True,
        "hardlock_domain_strict": True,
        "top_k_override": 12,
        "confidence": 0.9,
    }
    rd = RouteDecision.from_tool_payload(payload)
    assert rd.sub_indexes == ["aides_territoires"]
    assert rd.criteria is not None
    assert rd.criteria.region == "bretagne"  # normalize_region lowercases
    assert rd.criteria.secteur == ["informatique"]
    assert rd.domain_lock == ["crous"]
    assert rd.hardlock_region_strict is True
    assert rd.hardlock_domain_strict is True
    assert rd.top_k_override == 12
    assert rd.confidence == 0.9


def test_from_tool_payload_minimal_missing_keys() -> None:
    """Payload minimal (LLM oublie des clés) → defaults safes."""
    payload = {"sub_indexes": ["formations"], "confidence": 0.5}
    rd = RouteDecision.from_tool_payload(payload)
    assert rd.sub_indexes == ["formations"]
    assert rd.criteria is None
    assert rd.domain_lock is None
    assert rd.refusal_reason is None
    assert rd.top_k_override is None
    assert rd.confidence == 0.5


def test_from_tool_payload_no_criteria_when_all_null() -> None:
    """Si region/niveau/secteur tous null, pas de FilterCriteria construit."""
    payload = {
        "sub_indexes": ["formations"],
        "region": None,
        "niveau_min": None,
        "niveau_max": None,
        "secteur": None,
        "confidence": 0.7,
    }
    rd = RouteDecision.from_tool_payload(payload)
    assert rd.criteria is None


def test_from_tool_payload_top_k_out_of_range_dropped() -> None:
    """top_k_override hors [5, 20] → None (défense vs LLM qui hallucine)."""
    payload = {"sub_indexes": ["formations"], "top_k_override": 100, "confidence": 0.8}
    rd = RouteDecision.from_tool_payload(payload)
    assert rd.top_k_override is None

    payload2 = {"sub_indexes": ["formations"], "top_k_override": 2, "confidence": 0.8}
    rd2 = RouteDecision.from_tool_payload(payload2)
    assert rd2.top_k_override is None


def test_from_tool_payload_refusal_with_template() -> None:
    """Payload refusal_reason → pre_written_response auto-populé."""
    payload = {
        "sub_indexes": ["formations"],
        "refusal_reason": "superlative_no_data",
        "confidence": 0.95,
    }
    rd = RouteDecision.from_tool_payload(payload)
    assert rd.refusal_reason == "superlative_no_data"
    assert rd.pre_written_response is not None
    assert "Onisep" in rd.pre_written_response


def test_from_tool_payload_domain_lock_normalized() -> None:
    """domain_lock listé → normalisé (lowercase, strip)."""
    payload = {
        "sub_indexes": ["aides_territoires"],
        "domain_lock": ["CROUS", "  financement_etudes  "],
        "confidence": 0.8,
    }
    rd = RouteDecision.from_tool_payload(payload)
    assert rd.domain_lock == ["crous", "financement_etudes"]


def test_from_tool_payload_invalid_types_safe() -> None:
    """sub_indexes non-list, secteur non-list → fallback safes (pas de crash)."""
    payload = {
        "sub_indexes": "formations",  # string au lieu de list
        "secteur": "informatique",  # string au lieu de list
        "confidence": 0.5,
    }
    rd = RouteDecision.from_tool_payload(payload)
    # sub_indexes string → fallback all
    assert rd.sub_indexes == list(SUB_INDEX_NAMES)
    # secteur string → ignoré (pas de criteria construit si tout None à part secteur invalide)
    assert rd.criteria is None or rd.criteria.secteur is None


# ────────────────────────── hardlock_block_for_prompt ──────────────────────────


def test_hardlock_block_empty_when_no_constraints() -> None:
    """Aucune contrainte hardlock → bloc vide."""
    rd = RouteDecision(sub_indexes=["formations"], confidence=0.8)
    assert rd.hardlock_block_for_prompt() == ""


def test_hardlock_block_region_only() -> None:
    """Hardlock région seule → bloc avec mention région imposée."""
    rd = RouteDecision(
        sub_indexes=["formations"],
        criteria=FilterCriteria(region="bretagne"),
        hardlock_region_strict=True,
        confidence=0.9,
    )
    block = rd.hardlock_block_for_prompt()
    assert "HARDLOCK" in block
    assert "bretagne" in block.lower()
    assert "alternative" in block.lower() or "hors-région" in block.lower()


def test_hardlock_block_domain_only() -> None:
    """Hardlock domaine seul → bloc avec mention domaine imposé."""
    rd = RouteDecision(
        sub_indexes=["aides_territoires"],
        domain_lock=["crous"],
        hardlock_domain_strict=True,
        confidence=0.9,
    )
    block = rd.hardlock_block_for_prompt()
    assert "HARDLOCK" in block
    assert "crous" in block.lower()


def test_hardlock_block_both_region_and_domain() -> None:
    """Hardlock région + domaine → bloc combiné."""
    rd = RouteDecision(
        sub_indexes=["aides_territoires"],
        criteria=FilterCriteria(region="bretagne"),
        domain_lock=["crous"],
        hardlock_region_strict=True,
        hardlock_domain_strict=True,
        confidence=0.95,
    )
    block = rd.hardlock_block_for_prompt()
    assert "bretagne" in block.lower()
    assert "crous" in block.lower()


# ────────────────────────── ROUTE_DECISION_TOOL ──────────────────────────


def test_tool_to_mistral_schema_format() -> None:
    """ROUTE_DECISION_TOOL produit le format Mistral function-calling attendu."""
    schema = ROUTE_DECISION_TOOL.to_mistral_schema()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "decide_route"
    assert "description" in schema["function"]
    assert "parameters" in schema["function"]


def test_tool_required_fields() -> None:
    """Le schema requiert sub_indexes et confidence."""
    assert "required" in ROUTE_DECISION_TOOL_PARAMS
    assert set(ROUTE_DECISION_TOOL_PARAMS["required"]) == {"sub_indexes", "confidence"}


def test_tool_sub_indexes_enum_matches_constant() -> None:
    """L'enum sub_indexes du schema matche SUB_INDEX_NAMES."""
    sub_indexes_schema = ROUTE_DECISION_TOOL_PARAMS["properties"]["sub_indexes"]
    assert sub_indexes_schema["items"]["enum"] == list(SUB_INDEX_NAMES)


def test_tool_func_passthrough_basic() -> None:
    """_route_decision_tool_func normalise les kwargs en dict cohérent."""
    result = _route_decision_tool_func(
        sub_indexes=["formations"],
        region="Bretagne",
        confidence=0.9,
    )
    assert result["sub_indexes"] == ["formations"]
    assert result["region"] == "Bretagne"
    assert result["confidence"] == 0.9
    assert result["hardlock_region_strict"] is False  # default
    assert result["domain_lock"] is None


def test_tool_func_missing_required_via_call() -> None:
    """Tool.call valide les required → erreur si manque."""
    result = ROUTE_DECISION_TOOL.call()  # ni sub_indexes ni confidence
    assert "error" in result
    assert "missing" in result["error"]


# ────────────────────────── ROUTER_SYSTEM_PROMPT sanity ──────────────────────────


def test_system_prompt_mentions_all_sub_indexes() -> None:
    """Le system prompt explique chaque sub-index pour guider le LLM."""
    for name in SUB_INDEX_NAMES:
        assert name in ROUTER_SYSTEM_PROMPT


def test_system_prompt_mentions_all_refusal_reasons() -> None:
    """Le system prompt explique chaque cas de refus."""
    for reason in REFUSAL_REASONS:
        assert reason in ROUTER_SYSTEM_PROMPT


def test_system_prompt_includes_examples() -> None:
    """Le system prompt contient des exemples concrets pour few-shot implicite."""
    assert "Exemples" in ROUTER_SYSTEM_PROMPT or "exemples" in ROUTER_SYSTEM_PROMPT
    # Au moins un cas typique cité
    assert "CROUS" in ROUTER_SYSTEM_PROMPT or "crous" in ROUTER_SYSTEM_PROMPT


# ────────────────────────── JSON Schema authoritative ──────────────────────────


def test_authoritative_schema_loadable() -> None:
    """Le JSON schema authoritative est lisible et bien formé."""
    schema_path = Path(__file__).resolve().parents[1] / "src" / "state" / "route_decision_schema.json"
    assert schema_path.exists(), f"Schema absent : {schema_path}"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert schema["title"] == "RouteDecision"
    assert "sub_indexes" in schema["properties"]
    assert "confidence" in schema["properties"]


def test_authoritative_schema_sub_indexes_match() -> None:
    """L'enum sub_indexes du JSON schema matche SUB_INDEX_NAMES."""
    schema_path = Path(__file__).resolve().parents[1] / "src" / "state" / "route_decision_schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    enum_values = schema["properties"]["sub_indexes"]["items"]["enum"]
    assert set(enum_values) == set(SUB_INDEX_NAMES)
