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


# ────────────────────────── Anti-régression run_real_full step 11.6 ──────────────────────────


def test_run_real_full_uses_make_production_pipeline() -> None:
    """Anti-régression step 11.6 fix critical (2026-05-09).

    AVANT step 11.6 : run_real_full.py:96-98 instanciait `our_rag` via
      OrientIAPipeline(client, fiches, use_mmr=True, use_intent=True)
    PAS via make_production_pipeline → bench Phase D mesurait Run F+G
    historique (nu : use_mmr + use_intent uniquement). 15 commits de la
    refonte router/strict_v4/validator/etc. INVISIBLES dans le bench.

    APRÈS step 11.6 : doit utiliser make_production_pipeline avec
    enable_router_llm=True + enable_validator=True + enable_strict_v4=True.

    Ce test bloque toute régression vers OrientIAPipeline direct.
    """
    import inspect
    from src.eval import run_real_full as rrf

    # 1. L'import OrientIAPipeline ne doit PLUS être au top-level
    src = inspect.getsource(rrf)
    # Tolère mention dans un commentaire mais pas d'import direct
    assert "from src.rag.pipeline import OrientIAPipeline" not in src, (
        "REGRESSION step 11.6 : run_real_full.py importe encore OrientIAPipeline "
        "directement. Doit utiliser make_production_pipeline (cf step 11.6 fix)."
    )

    # 2. make_production_pipeline doit être importé
    assert "from src.rag.factory import make_production_pipeline" in src, (
        "REGRESSION step 11.6 : run_real_full.py n'importe pas "
        "make_production_pipeline. Le bench Phase D mesurera l'ancien pipeline."
    )

    # 3. make_seven_systems doit appeler make_production_pipeline avec
    # enable_router_llm=True (bench mesure la refonte)
    assert "enable_router_llm=True" in src, (
        "REGRESSION step 11.6 : enable_router_llm n'est pas explicitement True. "
        "Le bench Phase D ne testera pas le RouterLLM (refonte step 6)."
    )

    # 4. Garde-fou assert pipeline.router_llm is not None doit être présent
    assert "pipeline.router_llm is not None" in src, (
        "REGRESSION step 11.6 : le garde-fou post-build pipeline manque. "
        "Le bench peut silencieusement basculer sur ancien pipeline si le "
        "défaut factory change un jour."
    )
