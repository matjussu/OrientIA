from src.eval.grid_search import make_coefficient_grid
from src.rag.reranker import RerankConfig


def test_grid_contains_five_values():
    grid = make_coefficient_grid()
    assert len(grid) == 5


def test_grid_contains_baseline_and_default_and_extreme():
    grid = make_coefficient_grid()
    boosts = [cfg.secnumedu_boost for cfg in grid]
    assert 1.0 in boosts  # no-boost baseline (ablation)
    assert 1.5 in boosts  # current default
    assert 2.0 in boosts  # strong boost (over-emphasis test)


def test_grid_is_sorted_ascending():
    grid = make_coefficient_grid()
    boosts = [cfg.secnumedu_boost for cfg in grid]
    assert boosts == sorted(boosts), f"expected ascending order, got {boosts}"


def test_grid_holds_other_coefficients_fixed():
    """Only secnumedu_boost varies. The other 6 fields stay at their defaults
    so that the sensitivity analysis isolates exactly one variable."""
    grid = make_coefficient_grid()
    defaults = RerankConfig()
    for cfg in grid:
        assert cfg.cti_boost == defaults.cti_boost
        assert cfg.grade_master_boost == defaults.grade_master_boost
        assert cfg.public_boost == defaults.public_boost
        assert cfg.level_boost_bac5 == defaults.level_boost_bac5
        assert cfg.level_boost_bac3 == defaults.level_boost_bac3
        assert cfg.etab_named_boost == defaults.etab_named_boost


def test_grid_configs_are_all_different():
    """No duplicate secnumedu_boost values."""
    grid = make_coefficient_grid()
    boosts = [cfg.secnumedu_boost for cfg in grid]
    assert len(set(boosts)) == len(boosts)
