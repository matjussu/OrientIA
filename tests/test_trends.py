"""Tests for Vague C historical trends."""
from pathlib import Path

from src.collect.trends import (
    compute_trends,
    attach_trends,
    _trend_direction,
    SIGNIFICANT_TAUX_ACCES_DELTA,
    SIGNIFICANT_PLACES_DELTA_PCT,
    SIGNIFICANT_VOEUX_DELTA_PCT,
)


# === _trend_direction ===


def test_trend_direction_stable_single_year():
    assert _trend_direction([(2025, 50.0)], mode="abs", sig_threshold=10) == "stable"


def test_trend_direction_abs_up_threshold_boundary():
    # Exactly at threshold = up
    assert _trend_direction([(2023, 40.0), (2025, 50.0)],
                            mode="abs", sig_threshold=10) == "up"
    # Below threshold = stable
    assert _trend_direction([(2023, 40.0), (2025, 49.9)],
                            mode="abs", sig_threshold=10) == "stable"


def test_trend_direction_abs_down():
    assert _trend_direction([(2023, 70.0), (2025, 45.0)],
                            mode="abs", sig_threshold=10) == "down"


def test_trend_direction_pct_mode_ignores_abs_change_when_small_pct():
    # 10 abs change but on 500 base = 2% = not significant
    assert _trend_direction([(2023, 500), (2025, 510)],
                            mode="pct", sig_threshold=20) == "stable"
    # 50% relative growth = significant
    assert _trend_direction([(2023, 500), (2025, 750)],
                            mode="pct", sig_threshold=20) == "up"


def test_trend_direction_handles_zero_start():
    # Division by zero guard
    assert _trend_direction([(2023, 0), (2025, 500)],
                            mode="pct", sig_threshold=20) == "stable"


def test_trend_direction_handles_none_values():
    assert _trend_direction([(2023, None), (2025, 50.0)],
                            mode="abs", sig_threshold=10) == "stable"


# === compute_trends ===


def _three_year_hist(taux, places, voeux):
    return {
        2023: {"taux_acces": taux[0], "places": places[0], "voeux_totaux": voeux[0]},
        2024: {"taux_acces": taux[1], "places": places[1], "voeux_totaux": voeux[1]},
        2025: {"taux_acces": taux[2], "places": places[2], "voeux_totaux": voeux[2]},
    }


def test_compute_trends_taux_acces_down_gives_selectivity_message():
    """A formation where taux_acces drops from 70% to 45% is becoming
    more selective — surface that to the LLM."""
    hist = _three_year_hist(taux=[70.0, 55.0, 45.0], places=[24, 24, 24],
                             voeux=[400, 500, 550])
    trends = compute_trends(hist)
    assert "taux_acces" in trends
    assert trends["taux_acces"]["direction"] == "down"
    assert trends["taux_acces"]["delta_pp"] == -25.0
    assert "plus sélective" in trends["taux_acces"]["interpretation"]


def test_compute_trends_places_up_gives_capacity_message():
    hist = _three_year_hist(taux=[50.0, 50.0, 50.0], places=[20, 25, 30],
                             voeux=[300, 310, 320])
    trends = compute_trends(hist)
    assert trends["places"]["direction"] == "up"
    assert trends["places"]["delta"] == 10
    assert "capacité" in trends["places"]["interpretation"]


def test_compute_trends_voeux_popularity_message():
    hist = _three_year_hist(taux=[50.0, 50.0, 50.0], places=[24, 24, 24],
                             voeux=[300, 500, 800])
    trends = compute_trends(hist)
    assert trends["voeux"]["direction"] == "up"
    assert "attrait renforcé" in trends["voeux"]["interpretation"]


def test_compute_trends_stable_small_changes():
    """Changes below thresholds → direction 'stable', no narrative for places/voeux."""
    hist = _three_year_hist(taux=[50.0, 52.0, 53.0], places=[24, 24, 25],
                             voeux=[300, 310, 320])
    trends = compute_trends(hist)
    # taux diff = 3 pp < 10 → stable, but still reports with neutral message
    assert trends["taux_acces"]["direction"] == "stable"
    # places: stable + no interpretation (the message is None so LLM ignores)
    assert trends["places"]["direction"] == "stable"
    assert trends["places"]["interpretation"] is None


def test_compute_trends_empty_on_single_year():
    hist = {2025: {"taux_acces": 50.0, "places": 24, "voeux_totaux": 400}}
    trends = compute_trends(hist)
    assert trends == {}


def test_compute_trends_skips_missing_fields():
    """If taux_acces is missing in one of the two years, no trend computed."""
    hist = {
        2023: {"taux_acces": None, "places": 24, "voeux_totaux": 400},
        2025: {"taux_acces": 50.0, "places": 30, "voeux_totaux": 550},
    }
    trends = compute_trends(hist)
    # Only 1 year of taux_acces data → cannot compute trend
    assert "taux_acces" not in trends
    # Places and voeux have both years → trends computed
    assert "places" in trends
    assert "voeux" in trends


# === attach_trends integration ===


def test_attach_trends_skips_fiches_without_cod_aff_form(tmp_path):
    """ONISEP-only fiches (no cod_aff_form) are left untouched."""
    fiches = [
        {"nom": "ONISEP-only", "rncp": "37989"},
        {"nom": "Parcoursup", "cod_aff_form": "2601"},
    ]
    # Build a minimal historical CSV
    csv_2024 = tmp_path / "p_2024.csv"
    csv_2024.write_text(
        "cod_aff_form;taux_acces_ens;capa_fin;voe_tot;nb_voe_pp;"
        "pct_bg;pct_bt;pct_bp;pct_tb;pct_b;pct_bours;pct_f\n"
        "2601;40.0;24;500;500;60;30;10;20;30;40;35\n",
        encoding="utf-8",
    )
    csv_2025 = tmp_path / "p_2025.csv"
    csv_2025.write_text(
        "cod_aff_form;taux_acces_ens;capa_fin;voe_tot;nb_voe_pp;"
        "pct_bg;pct_bt;pct_bp;pct_tb;pct_b;pct_bours;pct_f\n"
        "2601;25.0;24;700;700;65;25;10;25;35;40;38\n",
        encoding="utf-8",
    )
    result = attach_trends(fiches, {2024: csv_2024, 2025: csv_2025})
    # ONISEP-only fiche untouched
    assert "admission" not in result[0]
    assert "trends" not in result[0]
    # Parcoursup fiche has historique + trends
    assert result[1]["admission"]["historique"]["2024"]["taux_acces"] == 40.0
    assert result[1]["admission"]["historique"]["2025"]["taux_acces"] == 25.0
    assert result[1]["trends"]["taux_acces"]["direction"] == "down"


def test_attach_trends_graceful_when_no_historical_csv(tmp_path):
    fiches = [{"nom": "x", "cod_aff_form": "2601"}]
    # Paths that don't exist
    result = attach_trends(fiches, {2024: tmp_path / "missing.csv"})
    assert "trends" not in result[0]
    # No admission.historique either
    assert "historique" not in result[0].get("admission", {})


def test_attach_trends_only_one_year_available_no_trend(tmp_path):
    """When only 1 year is available, historique is recorded but trends empty."""
    fiches = [{"nom": "x", "cod_aff_form": "2601"}]
    csv = tmp_path / "p_2025.csv"
    csv.write_text(
        "cod_aff_form;taux_acces_ens;capa_fin;voe_tot;nb_voe_pp;"
        "pct_bg;pct_bt;pct_bp;pct_tb;pct_b;pct_bours;pct_f\n"
        "2601;25.0;24;700;700;65;25;10;25;35;40;38\n",
        encoding="utf-8",
    )
    result = attach_trends(fiches, {2025: csv})
    assert "historique" in result[0]["admission"]
    assert "trends" not in result[0]  # can't compute with 1 point
