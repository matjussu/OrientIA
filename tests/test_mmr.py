"""Phase F.3.a — MMR (Maximal Marginal Relevance) post-rerank.

MMR diversifies the top-k selection to fight the "3 Paris EFREI fiches"
failure mode observed in Run 10. It rescores candidates as:

    mmr(i) = λ · relevance(i) − (1 − λ) · max_sim(i, already_selected)

where relevance comes from the label-based reranker (normalised to
[0, 1]) and similarity is cosine similarity between embeddings.

These tests are written BEFORE the implementation (TDD).
"""
from __future__ import annotations

import numpy as np
import pytest

from src.rag.mmr import mmr_select


def _make_candidate(score: float, embedding: list[float], fiche_id: str = "x") -> dict:
    """Helper: build a retriever-shaped result dict with an embedding."""
    return {
        "fiche": {"id": fiche_id, "etablissement": fiche_id},
        "score": score,
        "base_score": score,
        "embedding": np.array(embedding, dtype="float32"),
    }


def test_mmr_empty_candidates_returns_empty():
    assert mmr_select([], k=5) == []


def test_mmr_k_zero_returns_empty():
    c = [_make_candidate(0.9, [1.0, 0.0])]
    assert mmr_select(c, k=0) == []


def test_mmr_k_larger_than_candidates_returns_all():
    c = [
        _make_candidate(0.9, [1.0, 0.0], "A"),
        _make_candidate(0.8, [0.0, 1.0], "B"),
    ]
    result = mmr_select(c, k=10)
    assert len(result) == 2
    assert {r["fiche"]["id"] for r in result} == {"A", "B"}


def test_mmr_picks_highest_relevance_first():
    """The first pick must always be the highest-score item — MMR can
    only differ from pure-relevance at the 2nd pick onward."""
    c = [
        _make_candidate(0.5, [1.0, 0.0], "low"),
        _make_candidate(0.9, [0.0, 1.0], "high"),
        _make_candidate(0.7, [0.5, 0.5], "mid"),
    ]
    result = mmr_select(c, k=1, lambda_=0.7)
    assert result[0]["fiche"]["id"] == "high"


def test_mmr_diversifies_over_pure_relevance():
    """Scenario: top-2 by score are near-duplicates; MMR should skip the
    duplicate in favor of a lower-score but diverse candidate."""
    c = [
        _make_candidate(0.95, [1.0, 0.0, 0.0], "paris_efrei"),
        _make_candidate(0.94, [0.99, 0.01, 0.0], "paris_efrei_near_dup"),
        _make_candidate(0.80, [0.0, 1.0, 0.0], "rennes_ensibs"),
    ]
    result = mmr_select(c, k=2, lambda_=0.5)
    ids = [r["fiche"]["id"] for r in result]
    assert ids[0] == "paris_efrei"
    assert ids[1] == "rennes_ensibs", (
        f"MMR should pick the diverse candidate 2nd, got {ids[1]}"
    )


def test_mmr_lambda_one_is_pure_relevance():
    """λ=1 disables the diversity term → pure top-k by relevance."""
    c = [
        _make_candidate(0.95, [1.0, 0.0, 0.0], "A"),
        _make_candidate(0.94, [0.99, 0.01, 0.0], "B"),
        _make_candidate(0.80, [0.0, 1.0, 0.0], "C"),
    ]
    result = mmr_select(c, k=2, lambda_=1.0)
    ids = [r["fiche"]["id"] for r in result]
    assert ids == ["A", "B"]


def test_mmr_lambda_zero_maximizes_diversity():
    """λ=0 ignores relevance → the 2nd pick is whichever is farthest
    from the 1st (the 1st is still highest-relevance by convention)."""
    c = [
        _make_candidate(0.95, [1.0, 0.0, 0.0], "A"),
        _make_candidate(0.94, [0.99, 0.01, 0.0], "near_A"),
        _make_candidate(0.50, [0.0, 1.0, 0.0], "far_from_A"),
    ]
    result = mmr_select(c, k=2, lambda_=0.0)
    ids = [r["fiche"]["id"] for r in result]
    assert ids[0] == "A"
    assert ids[1] == "far_from_A"


def test_mmr_preserves_result_shape():
    """MMR must not drop fields (fiche, score, base_score, embedding).
    Downstream generator / logging rely on 'fiche' and 'score'."""
    c = [
        _make_candidate(0.9, [1.0, 0.0], "A"),
        _make_candidate(0.8, [0.0, 1.0], "B"),
    ]
    result = mmr_select(c, k=2, lambda_=0.7)
    for r in result:
        assert "fiche" in r
        assert "score" in r
        assert "base_score" in r
        assert "embedding" in r


def test_mmr_handles_zero_norm_embedding():
    """A degenerate zero vector must not cause a divide-by-zero."""
    c = [
        _make_candidate(0.9, [0.0, 0.0], "zero"),
        _make_candidate(0.5, [1.0, 0.0], "normal"),
    ]
    # Must not raise
    result = mmr_select(c, k=2, lambda_=0.5)
    assert len(result) == 2


def test_mmr_default_lambda_is_balanced():
    """Default λ should be in (0, 1) so neither pure-relevance nor
    pure-diversity is the default behaviour."""
    c = [_make_candidate(0.9, [1.0, 0.0])]
    # Just check that the function is callable without lambda and
    # produces a valid single-item result.
    result = mmr_select(c, k=1)
    assert len(result) == 1
