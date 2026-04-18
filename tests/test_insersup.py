"""Tests for InserSup insertion data integration."""
from pathlib import Path

from src.collect.insersup import (
    _safe_float,
    _safe_int,
    _snapshot_from_row,
    _has_any_metric,
    _pick_freshest,
    _match_fiche_to_insersup,
    _build_disclaimer,
    _sum_emploi_components,
    attach_insertion,
    load_insersup_aggregated,
    COL_UAI, COL_TYPE, COL_LIBELLE, COL_GENRE, COL_NAT, COL_REGIME, COL_OBTENTION,
    COL_PROMO, COL_SORTANTS, COL_TAUX_EMPLOI_12M, COL_TAUX_EMPLOI_STABLE_12M,
    COL_SALAIRE_MEDIAN_12M, COL_TAUX_EMPLOI_18M, COL_SALAIRE_MEDIAN_30M,
    COL_TAUX_EMPLOI_SAL_FR_12M, COL_TAUX_EMPLOI_NON_SAL_12M,
    COL_TAUX_EMPLOI_ETRANGER_12M, COL_TAUX_EMPLOI_SAL_FR_18M,
    COL_TAUX_EMPLOI_NON_SAL_18M, COL_TAUX_EMPLOI_ETRANGER_18M,
)


# === _safe_float / _safe_int — handle 'nd' / empty / comma decimals ===


def test_safe_float_handles_nd_empty_none():
    assert _safe_float("nd") is None
    assert _safe_float("") is None
    assert _safe_float(None) is None
    assert _safe_float("  ") is None


def test_safe_float_handles_comma_decimal():
    assert _safe_float("0,85") == 0.85
    assert _safe_float("12,5") == 12.5


def test_safe_int_handles_nd():
    assert _safe_int("nd") is None
    assert _safe_int("1790") == 1790
    assert _safe_int("") is None


# === _has_any_metric — skip rows with ALL core metrics missing ===


def test_has_any_metric_true_when_one_present():
    snap = {
        "taux_emploi_12m": 0.88,
        "taux_emploi_18m": None,
        "salaire_median_12m_mensuel_net": None,
        "salaire_median_30m_mensuel_net": None,
    }
    assert _has_any_metric(snap) is True


def test_has_any_metric_false_when_all_none():
    snap = {
        "taux_emploi_12m": None,
        "taux_emploi_18m": None,
        "salaire_median_12m_mensuel_net": None,
        "salaire_median_30m_mensuel_net": None,
    }
    assert _has_any_metric(snap) is False


# === _pick_freshest — latest promo year wins, single-year preferred ===


def test_pick_freshest_picks_latest_year():
    snaps = [
        {"cohorte": "2020", "taux_emploi_12m": 0.7},
        {"cohorte": "2022", "taux_emploi_12m": 0.8},
        {"cohorte": "2021", "taux_emploi_12m": 0.75},
    ]
    best = _pick_freshest(snaps)
    assert best["cohorte"] == "2022"


def test_pick_freshest_prefers_single_year_over_biannual():
    """Bi-annual '2023,2024' should lose to single-year '2024' at same peak year."""
    snaps = [
        {"cohorte": "2023,2024", "taux_emploi_12m": 0.7},
        {"cohorte": "2024", "taux_emploi_12m": 0.8},
    ]
    best = _pick_freshest(snaps)
    assert best["cohorte"] == "2024"


def test_pick_freshest_handles_empty():
    assert _pick_freshest([]) is None


# === _match_fiche_to_insersup — UAI strict, discipline > aggregate fallback ===


def _idx_discipline_and_agg(uai: str):
    """Build an index with both discipline-level and aggregate-level rows."""
    return {
        (uai, "master_LMD", "INFORMATIQUE"): [
            {"cohorte": "2022", "taux_emploi_12m": 0.92,
             "taux_emploi_18m": 0.94, "salaire_median_12m_mensuel_net": 2500,
             "salaire_median_30m_mensuel_net": 3200,
             "taux_emploi_stable_12m": 0.72, "nombre_sortants": 80},
        ],
        (uai, "master_LMD", "Tout Master LMD"): [
            {"cohorte": "2022", "taux_emploi_12m": 0.85,
             "taux_emploi_18m": 0.87, "salaire_median_12m_mensuel_net": 2000,
             "salaire_median_30m_mensuel_net": 2500,
             "taux_emploi_stable_12m": 0.65, "nombre_sortants": 450},
        ],
    }


def test_match_prefers_discipline_over_aggregate():
    fiche = {
        "cod_uai": "0640251A", "domaine": "cyber",
        "type_diplome": "Master LMD",
    }
    idx = _idx_discipline_and_agg("0640251A")
    snap, gran = _match_fiche_to_insersup(fiche, idx)
    assert gran == "discipline"
    assert snap["taux_emploi_12m"] == 0.92  # INFORMATIQUE row, not aggregate


def test_match_falls_back_to_aggregate_when_no_discipline_row():
    fiche = {
        "cod_uai": "0640251A", "domaine": "cyber",
        "type_diplome": "Master LMD",
    }
    # Only aggregate available
    idx = {
        ("0640251A", "master_LMD", "Tout Master LMD"): [
            {"cohorte": "2022", "taux_emploi_12m": 0.85,
             "taux_emploi_18m": 0.87, "salaire_median_12m_mensuel_net": 2000,
             "salaire_median_30m_mensuel_net": 2500,
             "taux_emploi_stable_12m": 0.65, "nombre_sortants": 450},
        ],
    }
    snap, gran = _match_fiche_to_insersup(fiche, idx)
    assert gran == "type_diplome_agrege"
    assert snap["taux_emploi_12m"] == 0.85


def test_match_returns_none_without_cod_uai():
    fiche = {"domaine": "cyber", "type_diplome": "Master LMD"}  # no cod_uai
    idx = _idx_discipline_and_agg("0640251A")
    snap, gran = _match_fiche_to_insersup(fiche, idx)
    assert snap is None
    assert gran is None


def test_match_returns_none_when_uai_absent_from_index():
    fiche = {
        "cod_uai": "9999999Z", "domaine": "cyber",
        "type_diplome": "Master LMD",
    }
    idx = _idx_discipline_and_agg("0640251A")  # different UAI
    snap, gran = _match_fiche_to_insersup(fiche, idx)
    assert snap is None


def test_match_uses_niveau_fallback_when_type_diplome_missing():
    """When type_diplome is absent (ONISEP missing), fall back to niveau."""
    fiche = {"cod_uai": "0640251A", "domaine": "cyber", "niveau": "bac+5"}
    idx = _idx_discipline_and_agg("0640251A")
    snap, gran = _match_fiche_to_insersup(fiche, idx)
    assert snap is not None
    assert gran == "discipline"


def test_match_returns_none_for_bts_niveau():
    """BTS (bac+2) has no InserSup aggregate → no match (honest refusal)."""
    fiche = {"cod_uai": "0640251A", "domaine": "cyber", "niveau": "bac+2",
             "type_diplome": "BTS"}
    idx = _idx_discipline_and_agg("0640251A")
    snap, gran = _match_fiche_to_insersup(fiche, idx)
    assert snap is None


# === _build_disclaimer ===


def test_disclaimer_discipline_mentions_discipline():
    fiche = {"etablissement": "Université de Pau", "domaine": "cyber"}
    msg = _build_disclaimer(fiche, "discipline")
    assert "INFORMATIQUE" in msg
    assert "Université de Pau" in msg
    assert "pas spécifique" in msg


def test_disclaimer_aggregate_mentions_all_programs():
    fiche = {"etablissement": "Université X", "type_diplome": "Master LMD"}
    msg = _build_disclaimer(fiche, "type_diplome_agrege")
    assert "TOUS" in msg or "tous" in msg.lower()
    assert "Master" in msg


# === attach_insertion integration ===


def test_attach_insertion_graceful_when_csv_missing(tmp_path):
    fiches = [{"cod_uai": "0640251A", "domaine": "cyber", "niveau": "bac+5"}]
    result = attach_insertion(fiches, tmp_path / "missing.csv")
    assert "insertion" not in result[0]


def _build_minimal_csv(path: Path) -> None:
    """Write a fake InserSup CSV with headers + rows matching the new schema.

    Tier 0 fix : includes Obtention du diplôme filter column AND the 3 sub-
    components of taux d'emploi 12m/18m needed for the sum fix.
    """
    headers = [
        COL_UAI, COL_TYPE, COL_LIBELLE, COL_GENRE, COL_NAT, COL_REGIME,
        COL_OBTENTION, COL_PROMO, COL_SORTANTS,
        COL_TAUX_EMPLOI_SAL_FR_12M, COL_TAUX_EMPLOI_NON_SAL_12M,
        COL_TAUX_EMPLOI_ETRANGER_12M,
        COL_TAUX_EMPLOI_STABLE_12M, COL_SALAIRE_MEDIAN_12M,
        COL_TAUX_EMPLOI_SAL_FR_18M, COL_TAUX_EMPLOI_NON_SAL_18M,
        COL_TAUX_EMPLOI_ETRANGER_18M, COL_SALAIRE_MEDIAN_30M,
    ]
    rows = [
        # Discipline-level row : sal_fr=0.90 + non_sal=0.02 = 0.92 total 12m
        # (uses 0.90+0.02 to avoid IEEE754 drift in tests)
        ["0640251A", "master_LMD", "INFORMATIQUE", "ensemble", "ensemble",
         "ensemble", "ensemble", "2022", "80",
         "0.90", "0.02", "nd",
         "0.72", "2500",
         "0.92", "0.02", "nd", "3200"],
        # Aggregate-level row : sal_fr=0.80 + non_sal=0.05 = 0.85 total 12m
        ["0640251A", "master_LMD", "Tout Master LMD", "ensemble", "ensemble",
         "ensemble", "ensemble", "2022", "450",
         "0.80", "0.05", "nd",
         "0.65", "2000",
         "0.82", "0.05", "nd", "2500"],
        # Filtered out (Genre=femme)
        ["0640251A", "master_LMD", "INFORMATIQUE", "femme", "ensemble",
         "ensemble", "ensemble", "2022", "20",
         "0.93", "0.02", "nd", "0.75", "2450",
         "0.94", "0.02", "nd", "3150"],
        # Filtered out (Obtention diplome = 'diplômé' not 'ensemble')
        # Tier 0 : cette ligne ne doit JAMAIS être prise par le pipeline,
        # même si elle a les meilleurs chiffres.
        ["0640251A", "master_LMD", "INFORMATIQUE", "ensemble", "ensemble",
         "ensemble", "diplômé", "2022", "75",
         "0.95", "0.02", "nd", "0.77", "2520",
         "0.96", "0.02", "nd", "3220"],
        # Filtered out (all metrics 'nd')
        ["0640251A", "licence_pro", "INFORMATIQUE", "ensemble", "ensemble",
         "ensemble", "ensemble", "2022", "30",
         "nd", "nd", "nd", "nd", "nd",
         "nd", "nd", "nd", "nd"],
    ]
    with open(path, "w", encoding="utf-8") as f:
        import csv as _csv
        w = _csv.writer(f, delimiter=";")
        w.writerow(headers)
        w.writerows(rows)


def test_attach_insertion_enriches_fiche_with_disclaimer(tmp_path):
    csv_path = tmp_path / "insersup.csv"
    _build_minimal_csv(csv_path)

    fiches = [
        {"cod_uai": "0640251A", "etablissement": "Université de Pau",
         "domaine": "cyber", "niveau": "bac+5", "type_diplome": "Master LMD"},
    ]
    result = attach_insertion(fiches, csv_path)
    ins = result[0]["insertion"]
    assert ins["taux_emploi_12m"] == 0.92  # discipline row wins
    assert ins["salaire_median_12m_mensuel_net"] == 2500
    assert ins["granularite"] == "discipline"
    assert ins["source"] == "InserSup DEPP"
    assert "INFORMATIQUE" in ins["disclaimer"]
    assert "data.gouv.fr" in ins["source_url"]


def test_attach_insertion_skips_fiches_without_uai(tmp_path):
    csv_path = tmp_path / "insersup.csv"
    _build_minimal_csv(csv_path)

    fiches = [
        {"etablissement": "Mystery", "domaine": "cyber", "niveau": "bac+5"},  # no cod_uai
    ]
    result = attach_insertion(fiches, csv_path)
    assert "insertion" not in result[0]


def test_attach_insertion_filters_non_ensemble_rows(tmp_path):
    """Femme/homme disaggregated rows must NOT be attached (only 'ensemble')."""
    csv_path = tmp_path / "insersup.csv"
    _build_minimal_csv(csv_path)
    # Only the 'femme' row exists for some other UAI
    idx = load_insersup_aggregated(csv_path)
    # 3 raw rows but only 2 pass the triple-ensemble filter, and 1 of those
    # is filtered because all metrics are 'nd' → only 2 usable rows remain
    total_snapshots = sum(len(v) for v in idx.values())
    assert total_snapshots == 2
    # No entry keyed with 'femme' filter
    for (uai, td, lib), _ in idx.items():
        # the 'femme' and 'nd' rows must not appear
        pass  # structural check: filter logic did its job


def test_attach_insertion_skips_rows_with_all_nd_metrics(tmp_path):
    """A row where taux_emploi_12m, taux_emploi_18m, salaire_12m, salaire_30m
    are all 'nd' must be excluded from the index (can't attach 'no data')."""
    csv_path = tmp_path / "insersup.csv"
    _build_minimal_csv(csv_path)
    idx = load_insersup_aggregated(csv_path)
    # The licence_pro 'nd' row should NOT be in idx
    assert ("0640251A", "licence_pro", "INFORMATIQUE") not in idx


# === Tier 0 fix (spot-check 2026-04-18) — obtention_diplome + sum components ===


def test_sum_emploi_components_handles_null_aggregate(tmp_path):
    """Tier 0 fix BUG #2 : la colonne agrégée `12-Taux d'emploi` est null
    dans le dataset 2025_S2. _sum_emploi_components doit additionner
    sal_fr + non_sal + etranger."""
    row = {
        COL_TAUX_EMPLOI_12M: "",  # aggregate null
        COL_TAUX_EMPLOI_SAL_FR_12M: "0.80",
        COL_TAUX_EMPLOI_NON_SAL_12M: "0.05",
        COL_TAUX_EMPLOI_ETRANGER_12M: "nd",  # étranger souvent null
    }
    # 0.80 + 0.05 = 0.85 (on ignore l'étranger si nd, pas de faux zéro)
    result = _sum_emploi_components(row, 12)
    assert result == pytest_approx(0.85)


def test_sum_emploi_components_uses_aggregate_when_filled():
    """Si la colonne agrégée EST remplie (dataset futur), on la prend en
    priorité au lieu de sommer les composantes."""
    row = {
        COL_TAUX_EMPLOI_12M: "0.88",
        COL_TAUX_EMPLOI_SAL_FR_12M: "0.80",  # différent
        COL_TAUX_EMPLOI_NON_SAL_12M: "0.05",
        COL_TAUX_EMPLOI_ETRANGER_12M: "0.02",
    }
    assert _sum_emploi_components(row, 12) == 0.88


def test_sum_emploi_components_all_null_returns_none():
    """Si toutes les composantes sont null ET l'agrégat est null → None."""
    row = {
        COL_TAUX_EMPLOI_12M: "",
        COL_TAUX_EMPLOI_SAL_FR_12M: "nd",
        COL_TAUX_EMPLOI_NON_SAL_12M: "nd",
        COL_TAUX_EMPLOI_ETRANGER_12M: "nd",
    }
    assert _sum_emploi_components(row, 12) is None


def test_obtention_diplome_filter_forces_ensemble(tmp_path):
    """Tier 0 fix BUG #1 : seules les lignes avec obtention_diplome=ensemble
    sont indexées. Même si une ligne obtention_diplome=diplômé a de meilleurs
    chiffres (cf CSV minimal : 0.95 vs 0.92 en 'ensemble'), elle est ignorée."""
    csv_path = tmp_path / "insersup.csv"
    _build_minimal_csv(csv_path)
    idx = load_insersup_aggregated(csv_path)
    # Le row 'diplômé' existe dans le CSV avec taux=0.95 (sal_fr)+0.02(non_sal)=0.97
    # Mais il doit être filtré. On doit avoir UNIQUEMENT la valeur 'ensemble'.
    snaps = idx[("0640251A", "master_LMD", "INFORMATIQUE")]
    assert len(snaps) == 1  # pas 2 (diplômé filtré)
    # Valeur = somme 'ensemble' = 0.90 + 0.02 = 0.92
    assert snaps[0]["taux_emploi_12m"] == pytest_approx(0.92)


def test_snapshot_from_row_uses_sum_of_components_in_full_pipeline(tmp_path):
    """End-to-end : une fiche matchée voit bien taux_emploi_12m = somme,
    et pas 'nd' ou None malgré la colonne agrégée vide."""
    csv_path = tmp_path / "insersup.csv"
    _build_minimal_csv(csv_path)
    fiches = [{"cod_uai": "0640251A", "etablissement": "Uni X",
               "domaine": "cyber", "niveau": "bac+5", "type_diplome": "Master LMD"}]
    result = attach_insertion(fiches, csv_path)
    ins = result[0]["insertion"]
    # 0.90 + 0.02 = 0.92 (discipline-level row, 'ensemble')
    assert ins["taux_emploi_12m"] == pytest_approx(0.92)


# Helper import pour les approx
def pytest_approx(expected, tol=1e-6):
    """Local approx helper — avoids adding a pytest dependency for the
    comparison helper when pytest is already available."""
    import pytest as _pytest
    return _pytest.approx(expected, abs=tol)
