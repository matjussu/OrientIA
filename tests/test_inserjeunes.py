"""Tests pour `src/collect/inserjeunes.py` (DEPP/DARES Opendatasoft)."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.collect.inserjeunes import (
    InserjeunesFetchError,
    TYPE_DIPLOME_TO_NIVEAU,
    _extract_taux_horizons,
    _safe_int,
    _safe_ratio,
    fetch_cfa_records,
    fetch_lycee_pro_records,
    normalize_cfa_all,
    normalize_cfa_record,
    normalize_lycee_pro_all,
    normalize_lycee_pro_record,
    type_diplome_to_niveau,
)


# --- Mapping ---


@pytest.mark.parametrize(
    "label,expected",
    [
        ("CAP", "cap-bep"),
        ("CAP boulanger", "cap-bep"),
        ("BEP comptabilité", "cap-bep"),
        ("Bac pro", "bac"),
        ("Bac pro SN", "bac"),
        ("Baccalauréat professionnel Systèmes numériques", "bac"),
        ("BP", "bac"),
        ("Brevet professionnel", "bac"),
        ("Mention complémentaire", "bac"),
        ("BTS", "bac+2"),
        ("BTS SIO", "bac+2"),
        ("Brevet de technicien supérieur", "bac+2"),
        ("", None),
        (None, None),
        ("Formation inconnue", None),
    ],
)
def test_type_diplome_to_niveau(label, expected):
    assert type_diplome_to_niveau(label) == expected


# --- Safe parsers ---


def test_safe_int_fr_virgule():
    assert _safe_int("99") == 99
    assert _safe_int("99,5") == 99
    assert _safe_int("") is None


def test_safe_ratio_pct_threshold():
    assert _safe_ratio("77") == pytest.approx(0.77)
    assert _safe_ratio("77.5") == pytest.approx(0.775)
    assert _safe_ratio("1.0") == 1.0
    assert _safe_ratio(0.5) == 0.5
    assert _safe_ratio(None) is None


def test_extract_taux_horizons():
    r = {
        "taux_emploi_6_mois": "77",
        "taux_emploi_12_mois": "71",
        "taux_emploi_18_mois": None,
        "taux_emploi_24_mois": None,
    }
    out = _extract_taux_horizons(r)
    assert out["6m"] == pytest.approx(0.77)
    assert out["12m"] == pytest.approx(0.71)
    assert out["18m"] is None
    assert out["24m"] is None


# --- Normalize lycée pro ---


def test_normalize_lycee_pro_basic():
    raw = {
        "annee": "2022-2023",
        "uai": "0123456X",
        "libelle": "Lycée Pro Truc",
        "region": "Bretagne",
        "type_diplome": "Bac pro",
        "code_formation_mefstat11": "40025123",
        "libelle_formation": "Systèmes numériques option réseaux",
        "duree_formation": "3 ans",
        "diplome_renove_ou_nouveau": "Non",
        "part_en_poursuite_d_etudes": 55,
        "part_en_emploi_6_mois_apres_la_sortie": 35,
        "part_des_autres_situations": 10,
        "taux_poursuite_etudes": 55,
        "taux_emploi_6_mois": 52,
        "taux_emploi_12_mois": 68,
        "taux_emploi_18_mois": 72,
        "taux_emploi_24_mois": 75,
    }
    n = normalize_lycee_pro_record(raw)
    assert n["source"] == "inserjeunes_lycee_pro"
    assert n["type_diplome"] == "Bac pro"
    assert n["niveau_orientia"] == "bac"
    assert n["libelle_formation"] == "Systèmes numériques option réseaux"
    assert n["part_poursuite_etudes"] == pytest.approx(0.55)
    assert n["taux_emploi"]["6m"] == pytest.approx(0.52)
    assert n["taux_emploi"]["24m"] == pytest.approx(0.75)


def test_normalize_lycee_pro_mapping_bts():
    raw = {"type_diplome": "BTS", "libelle": "Lycée X"}
    n = normalize_lycee_pro_record(raw)
    assert n["niveau_orientia"] == "bac+2"


def test_normalize_lycee_pro_unknown_type():
    raw = {"type_diplome": "Diplôme exotique"}
    n = normalize_lycee_pro_record(raw)
    assert n["niveau_orientia"] is None


def test_normalize_lycee_pro_all():
    raws = [
        {"type_diplome": "CAP", "libelle": "A"},
        {"type_diplome": "BTS", "libelle": "B"},
    ]
    out = normalize_lycee_pro_all(raws)
    assert [x["niveau_orientia"] for x in out] == ["cap-bep", "bac+2"]


# --- Normalize CFA ---


def test_normalize_cfa_basic():
    raw = {
        "annee": "cumul 2022-2023",
        "uai": "0470974D",
        "libelle": "Sud Management",
        "region": "NOUVELLE-AQUITAINE",
        "part_en_poursuite_d_etudes": 49,
        "part_en_emploi_6_mois_apres_la_sortie": 39,
        "part_des_autres_situations": 12,
        "taux_contrats_interrompus": 5.5,
        "taux_poursuite_etudes": 49,
        "taux_emploi_6_mois": 77,
        "taux_emploi_6_mois_attendu": 65,
        "va_emploi_6_mois": 12,
        "taux_emploi_12_mois": 71,
        "taux_emploi_18_mois": None,
        "taux_emploi_24_mois": None,
    }
    n = normalize_cfa_record(raw)
    assert n["source"] == "inserjeunes_cfa"
    assert n["etablissement"] == "Sud Management"
    assert n["region"] == "NOUVELLE-AQUITAINE"
    assert n["taux_emploi"]["6m"] == pytest.approx(0.77)
    assert n["taux_emploi_6_mois_attendu"] == pytest.approx(0.65)
    assert n["valeur_ajoutee_emploi_6_mois"] == pytest.approx(0.12)
    assert n["taux_contrats_interrompus"] == pytest.approx(0.055)
    assert n["niveau_orientia"] is None  # CFA agrégé pas de type_diplome


def test_normalize_cfa_all():
    raws = [{"libelle": "X"}, {"libelle": "Y"}]
    out = normalize_cfa_all(raws)
    assert [r["etablissement"] for r in out] == ["X", "Y"]


# --- Fetch (mocked) ---


def test_fetch_lycee_pro_mocked():
    session = MagicMock()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = [{"type_diplome": "CAP"}]
    session.get.return_value = resp
    result = fetch_lycee_pro_records(max_records=1, session=session)
    assert result == [{"type_diplome": "CAP"}]
    assert session.get.call_args[1]["params"]["limit"] == 1


def test_fetch_cfa_mocked():
    session = MagicMock()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = []
    session.get.return_value = resp
    assert fetch_cfa_records(session=session) == []


def test_fetch_raises_on_500():
    session = MagicMock()
    resp = MagicMock()
    resp.status_code = 500
    resp.text = "Server down"
    session.get.return_value = resp
    with pytest.raises(InserjeunesFetchError):
        fetch_lycee_pro_records(session=session)


def test_fetch_raises_on_unexpected_shape():
    session = MagicMock()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"not": "a list"}
    session.get.return_value = resp
    with pytest.raises(InserjeunesFetchError):
        fetch_cfa_records(session=session)


def test_mapping_table_non_empty():
    assert len(TYPE_DIPLOME_TO_NIVEAU) >= 8
