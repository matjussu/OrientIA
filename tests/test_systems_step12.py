"""Tests step 12 — OurRagWithoutRouterSystem variant pour A/B Phase D.

Couvre :
- Classe instanciable, name="our_rag_no_router"
- answer() retourne un string (pas (text, sources))
- Garde-fou warning si pipeline.router_llm est non-None
- Pipeline avec router_llm=None ne déclenche PAS le warning
"""
from __future__ import annotations

import warnings
from unittest.mock import MagicMock

import pytest

from src.eval.systems import OurRagSystem, OurRagWithoutRouterSystem


def _make_mock_pipeline(with_router: bool = False):
    """Pipeline mock minimal — answer() retourne (text, sources)."""
    pipeline = MagicMock()
    pipeline.answer.return_value = ("Réponse mock", [{"fiche": {"id": "x"}}])
    pipeline.router_llm = MagicMock() if with_router else None
    return pipeline


# ────────────────────────── Class basics ──────────────────────────


def test_no_router_system_name() -> None:
    """name = 'our_rag_no_router' (cf plan section 3.2.5)."""
    pipeline = _make_mock_pipeline(with_router=False)
    system = OurRagWithoutRouterSystem(pipeline)
    assert system.name == "our_rag_no_router"


def test_no_router_system_distinct_from_our_rag() -> None:
    """Les noms 'our_rag' et 'our_rag_no_router' sont distincts (pas de
    collision dans le label_mapping du bench)."""
    pipeline = _make_mock_pipeline(with_router=False)
    a = OurRagSystem(pipeline)
    b = OurRagWithoutRouterSystem(pipeline)
    assert a.name != b.name


def test_no_router_answer_returns_str() -> None:
    """answer() retourne UN string (le bench attend ce contrat, pas un tuple)."""
    pipeline = _make_mock_pipeline(with_router=False)
    system = OurRagWithoutRouterSystem(pipeline)
    result = system.answer("Q1", "Test question")
    assert isinstance(result, str)
    assert result == "Réponse mock"


def test_no_router_calls_pipeline_answer() -> None:
    """answer() délègue au pipeline.answer()."""
    pipeline = _make_mock_pipeline(with_router=False)
    system = OurRagWithoutRouterSystem(pipeline)
    system.answer("Q1", "Test question")
    pipeline.answer.assert_called_once_with("Test question")


# ────────────────────────── Garde-fou A/B ──────────────────────────


def test_no_router_warns_if_pipeline_has_router() -> None:
    """Si le pipeline a router_llm défini → warning explicite (sinon le
    test A/B serait faussé silencieusement)."""
    pipeline_with_router = _make_mock_pipeline(with_router=True)
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        OurRagWithoutRouterSystem(pipeline_with_router)
        assert len(captured) == 1
        assert "router_llm" in str(captured[0].message)
        assert "FAUSSÉ" in str(captured[0].message) or "faussé" in str(captured[0].message).lower()


def test_no_router_no_warning_when_pipeline_clean() -> None:
    """Pipeline sans router (le cas correct) → AUCUN warning."""
    pipeline_clean = _make_mock_pipeline(with_router=False)
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        OurRagWithoutRouterSystem(pipeline_clean)
        assert len(captured) == 0


# ────────────────────────── Test compat OurRagSystem (régression) ──────────────────────────


def test_our_rag_system_unchanged() -> None:
    """OurRagSystem (notre system de référence) n'a pas changé : name =
    'our_rag', answer() = pass-through pipeline."""
    pipeline = _make_mock_pipeline()
    system = OurRagSystem(pipeline)
    assert system.name == "our_rag"
    result = system.answer("Q1", "Test")
    assert isinstance(result, str)
    pipeline.answer.assert_called_once_with("Test")
