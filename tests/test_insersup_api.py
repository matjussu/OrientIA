"""Tests pour `src/collect/insersup_api.py` (MESR Opendatasoft API).

Focus : mapping type_diplome → niveau, normalisation record, extraction
des 5 horizons, safe parsers, gestion erreur fetch.

Tests d'intégration réseau **skipped par défaut** (nécessitent accès internet).
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.collect.insersup_api import (
    DEFAULT_WHERE,
    InsersupFetchError,
    TYPE_DIPLOME_TO_NIVEAU,
    _extract_horizons,
    _safe_int,
    _safe_ratio,
    fetch_insersup_records,
    normalize_all,
    normalize_record,
    type_diplome_to_niveau,
)


# --- Mapping type_diplome → niveau ---


@pytest.mark.parametrize(
    "label,expected",
    [
        ("Master LMD", "bac+5"),
        ("Master MEEF", "bac+5"),
        ("Diplôme d'ingénieurs", "bac+5"),
        ("Licence générale", "bac+3"),
        ("Licence LMD", "bac+3"),
        ("Licence professionnelle", "bac+3"),
        ("Bachelor universitaire de technologie", "bac+3"),
        ("DUT", "bac+2"),
        ("BTS", "bac+2"),
        ("Doctorat", "bac+8"),
        ("", None),
        (None, None),
    ],
)
def test_type_diplome_to_niveau_exact(label, expected):
    assert type_diplome_to_niveau(label) == expected


def test_type_diplome_to_niveau_fuzzy_master():
    assert type_diplome_to_niveau("Master MEEF spécialité truc") == "bac+5"
    assert type_diplome_to_niveau("Diplôme ingénieur ENSIBS") == "bac+5"


def test_type_diplome_to_niveau_fuzzy_licence():
    assert type_diplome_to_niveau("Licence pro en banque") == "bac+3"
    assert type_diplome_to_niveau("Licence LMD en informatique") == "bac+3"
    assert type_diplome_to_niveau("Bachelor international") == "bac+3"


def test_type_diplome_to_niveau_unknown():
    assert type_diplome_to_niveau("Formation spéciale inconnue") is None


# --- Safe parsers ---


def test_safe_int():
    assert _safe_int("99") == 99
    assert _safe_int("99.5") == 99
    assert _safe_int("99,5") == 99  # virgule FR
    assert _safe_int("") is None
    assert _safe_int(None) is None
    assert _safe_int("abc") is None


def test_safe_ratio_percentage_vs_float():
    assert _safe_ratio("82.5") == pytest.approx(0.825)
    assert _safe_ratio("82,5") == pytest.approx(0.825)
    assert _safe_ratio(82.5) == pytest.approx(0.825)
    assert _safe_ratio(0.825) == 0.825
    assert _safe_ratio(0.5) == 0.5
    # Valeur limite : "1.01" est un pourcentage (1.01%), pas un ratio 101%
    assert _safe_ratio("1.01") == pytest.approx(0.0101)
    assert _safe_ratio(None) is None
    assert _safe_ratio("") is None


# --- _extract_horizons ---


def test_extract_horizons_all_present():
    record = {
        "tx_sortants_en_emploi_sal_fr_6": "75.5",
        "tx_sortants_en_emploi_sal_fr_12": "80",
        "tx_sortants_en_emploi_sal_fr_18": "82.1",
        "tx_sortants_en_emploi_sal_fr_24": "83",
        "tx_sortants_en_emploi_sal_fr_30": "84.5",
    }
    out = _extract_horizons(record, "tx_sortants_en_emploi_sal_fr")
    assert out["6m"] == pytest.approx(0.755)
    assert out["12m"] == pytest.approx(0.80)
    assert out["30m"] == pytest.approx(0.845)


def test_extract_horizons_partial_missing():
    record = {"tx_sortants_en_emploi_sal_fr_6": "75.5"}  # only 6m
    out = _extract_horizons(record, "tx_sortants_en_emploi_sal_fr")
    assert out["6m"] == pytest.approx(0.755)
    assert out["12m"] is None
    assert out["30m"] is None


# --- normalize_record ---


def test_normalize_record_basic():
    raw = {
        "date_jeu": "2025_S2",
        "reg_nom": "Nouvelle-Aquitaine",
        "aca_nom": "Bordeaux",
        "uo_lib": "Université de Pau et des Pays de l'Adour",
        "type_diplome_long": "Master LMD",
        "dom_lib": "Sciences",
        "discipli_lib": "Informatique",
        "sectdis_lib": "Informatique scientifique",
        "libelle_diplome": "Tout Master LMD",
        "obtention_diplome": "ensemble",
        "genre": "ensemble",
        "nationalite": "ensemble",
        "regime_inscription": "ensemble",
        "nb_sortants": "99",
        "nb_poursuivants": "9",
        "promo": ["2021"],
        "tx_sortants_en_emploi_sal_fr_6": "74.75",
        "tx_sortants_en_emploi_sal_fr_12": "79.80",
        "tx_sortants_en_emploi_sal_fr_18": "77.78",
        "tx_sortants_en_emploi_sal_fr_24": "81.82",
        "tx_sortants_en_emploi_sal_fr_30": "81.82",
        "tx_sortants_en_emploi_non_sal_6": "1.01",
    }
    n = normalize_record(raw)
    assert n["source"] == "insersup"
    assert n["date_jeu"] == "2025_S2"
    assert n["cohorte_promo"] == "2021"
    assert n["region"] == "Nouvelle-Aquitaine"
    assert n["etablissement"] == "Université de Pau et des Pays de l'Adour"
    assert n["type_diplome"] == "Master LMD"
    assert n["niveau_orientia"] == "bac+5"
    assert n["nb_sortants"] == 99
    assert n["nb_poursuivants"] == 9
    assert n["taux_emploi_salarie_fr"]["6m"] == pytest.approx(0.7475)
    assert n["taux_emploi_salarie_fr"]["12m"] == pytest.approx(0.798)
    assert n["taux_emploi_non_salarie"]["6m"] == pytest.approx(0.0101)
    assert n["cohorte_dimensions"]["obtention_diplome"] == "ensemble"


def test_normalize_record_promo_as_string():
    """`promo` peut être string directe au lieu de list."""
    raw = {"type_diplome_long": "Master LMD", "promo": "2020"}
    n = normalize_record(raw)
    assert n["cohorte_promo"] == "2020"


def test_normalize_record_promo_absent():
    raw = {"type_diplome_long": "Licence LMD"}
    n = normalize_record(raw)
    assert n["cohorte_promo"] is None


def test_normalize_all():
    raws = [
        {"type_diplome_long": "Master LMD", "uo_lib": "U1"},
        {"type_diplome_long": "Licence LMD", "uo_lib": "U2"},
    ]
    out = normalize_all(raws)
    assert len(out) == 2
    assert out[0]["niveau_orientia"] == "bac+5"
    assert out[1]["niveau_orientia"] == "bac+3"


# --- fetch_insersup_records (mocked) ---


def test_fetch_uses_default_where():
    session = MagicMock()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = []
    session.get.return_value = resp
    fetch_insersup_records(session=session, max_records=100)
    params = session.get.call_args[1]["params"]
    assert params["where"] == DEFAULT_WHERE
    assert params["limit"] == 100


def test_fetch_uses_custom_where():
    session = MagicMock()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = [{"type_diplome_long": "Master LMD"}]
    session.get.return_value = resp
    custom = 'type_diplome_long:"Master LMD"'
    result = fetch_insersup_records(where=custom, session=session)
    params = session.get.call_args[1]["params"]
    assert params["where"] == custom
    assert len(result) == 1


def test_fetch_raises_on_non_200():
    session = MagicMock()
    resp = MagicMock()
    resp.status_code = 500
    resp.text = "Server error"
    session.get.return_value = resp
    with pytest.raises(InsersupFetchError) as exc:
        fetch_insersup_records(session=session)
    assert "500" in str(exc.value)


def test_fetch_raises_on_unexpected_shape():
    session = MagicMock()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"not": "a list"}
    session.get.return_value = resp
    with pytest.raises(InsersupFetchError) as exc:
        fetch_insersup_records(session=session)
    assert "attendu list" in str(exc.value)


def test_type_diplome_mapping_table_non_empty():
    assert len(TYPE_DIPLOME_TO_NIVEAU) >= 10
