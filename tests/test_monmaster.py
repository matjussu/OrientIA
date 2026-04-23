"""Tests `src/collect/monmaster.py` — ingestion MonMaster D8 Axe 1.

Tous les appels réseau sont mockés. Les tests de bout en bout live
(avec requests réels vers data.enseignementsup-recherche.gouv.fr)
sont dans `tests/integration/` et non exécutés par CI par défaut.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.collect.monmaster import (
    _compute_taux_admission,
    _extract_profil_admis_stats,
    _parse_ville,
    fetch_all_records,
    fetch_records_page,
    normalize_all,
    normalize_record,
    save_processed,
    save_raw_records,
)


# --- Fixture représentative (shape API réel observé 2026-04-23) ---


SAMPLE_RECORD = {
    "session": "2025",
    "eta_uai": "0755976N",
    "eta_nom": "Université Paris Cité",
    "acad": "A01",
    "acad_lib": "Paris",
    "acad_reg": "R11",
    "acad_reg_lib": "Île-de-France",
    "ifc": "0900820SVFY8",
    "inm": "0900820S",
    "mention": "BIO-INFORMATIQUE",
    "inmp": "0900820-06Z",
    "parcours": "Biologie Informatique - Ingénierie de Plateforme en Biologie",
    "alternance": "0",
    "modalite_enseignement": ["INITIALE", "CONTINUE"],
    "lieux": "Université Paris Cité - PARIS (75)|UFR SDV - Campus Grands Moulins - PARIS (75)",
    "lieu_acad_lib": "Paris",
    "lieu_reg_acad_lib": "Île-de-France",
    "disci_master": "Sc. fondamentales et appliquées",
    "discipline": "09",
    "disci_lib": "Sciences de la vie, de la terre et de l'univers",
    "secteur_disci": "06",
    "secteur_disci_lib": "Sciences de la vie, biologie, santé",
    "col": 30,
    "n_can_pp": 406,
    "n_accept_total": 19,
    "rang_dernier_appele_pp": 59,
    "pct_accept_femme": 84.2,
    "pct_accept_etab": 47.4,
    "pct_accept_lieu_acad": 63.2,
    "pct_accept_lg3": 89.5,
    "pct_accept_lp3": 0.0,
    "pct_accept_but3": 0.0,
    "pct_accept_master": 0.0,
    "pct_accept_autre": 5.3,
    "pct_accept_noninscri": 5.3,
    "id_paysage": "5cZyU",
}


# --- Helpers bas niveau ---


def test_parse_ville_extracts_first_city():
    ville = _parse_ville(
        "Université Paris Cité - PARIS (75)|UFR SDV - Campus Grands Moulins - PARIS (75)"
    )
    assert ville == "PARIS"


def test_parse_ville_handles_simple_format():
    assert _parse_ville("UPPA - PAU (64)") == "PAU"


def test_parse_ville_empty_returns_empty_string():
    assert _parse_ville("") == ""
    assert _parse_ville(None) == ""


def test_compute_taux_admission():
    assert _compute_taux_admission({"n_can_pp": 406, "n_accept_total": 19}) == pytest.approx(
        19 / 406
    )


def test_compute_taux_admission_zero_candidates():
    assert _compute_taux_admission({"n_can_pp": 0, "n_accept_total": 0}) is None


def test_compute_taux_admission_missing_fields():
    assert _compute_taux_admission({}) is None


def test_extract_profil_admis_stats_includes_all_profiles():
    stats = _extract_profil_admis_stats(SAMPLE_RECORD)
    # LG3 = Licence générale = profil d'entrée principal master
    assert stats["pct_lg3"] == 89.5
    assert stats["pct_lp3"] == 0.0
    assert stats["pct_but3"] == 0.0
    assert stats["pct_master"] == 0.0
    assert stats["pct_femme"] == 84.2


# --- Normalisation ---


def test_normalize_record_schema_keys_present():
    fiche = normalize_record(SAMPLE_RECORD)
    required = {
        "source",
        "phase",
        "nom",
        "etablissement",
        "ville",
        "niveau",
        "mention",
        "parcours",
        "discipline",
        "modalite_enseignement",
        "alternance",
        "capacite",
        "taux_admission",
        "profil_admis",
        "id_mon_master",
    }
    assert required.issubset(fiche.keys())


def test_normalize_record_phase_is_master():
    """ADR-039 : MonMaster = phase (c) scope élargi."""
    fiche = normalize_record(SAMPLE_RECORD)
    assert fiche["phase"] == "master"
    assert fiche["niveau"] == "bac+5"


def test_normalize_record_source_is_monmaster():
    assert normalize_record(SAMPLE_RECORD)["source"] == "monmaster"


def test_normalize_record_name_combines_mention_parcours():
    fiche = normalize_record(SAMPLE_RECORD)
    assert "BIO-INFORMATIQUE" in fiche["nom"]
    assert "Biologie Informatique" in fiche["nom"]


def test_normalize_record_alternance_bool():
    assert normalize_record(SAMPLE_RECORD)["alternance"] is False
    rec_alt = {**SAMPLE_RECORD, "alternance": "1"}
    assert normalize_record(rec_alt)["alternance"] is True


def test_normalize_record_ville_extracted():
    assert normalize_record(SAMPLE_RECORD)["ville"] == "PARIS"


def test_normalize_all_maps_every_record():
    recs = [SAMPLE_RECORD, {**SAMPLE_RECORD, "inmp": "other"}]
    out = normalize_all(recs)
    assert len(out) == 2
    assert out[0]["id_mon_master"]["inmp"] == SAMPLE_RECORD["inmp"]
    assert out[1]["id_mon_master"]["inmp"] == "other"


# --- Fetch (mocké) ---


def test_fetch_records_page_calls_correct_url():
    session = MagicMock()
    resp = MagicMock()
    resp.json.return_value = {"total_count": 1, "results": [SAMPLE_RECORD]}
    resp.raise_for_status = MagicMock()
    session.get.return_value = resp

    payload = fetch_records_page(offset=0, limit=100, session=session)
    assert payload["total_count"] == 1
    call_args = session.get.call_args
    assert "fr-esr-mon_master" in call_args[0][0]
    assert call_args[1]["params"] == {"limit": 100, "offset": 0}


def test_fetch_all_records_stops_at_total_count():
    session = MagicMock()
    # Page 1 : 2 records, total_count = 2 → pas de page 2
    resp = MagicMock()
    resp.json.return_value = {
        "total_count": 2,
        "results": [SAMPLE_RECORD, SAMPLE_RECORD],
    }
    resp.raise_for_status = MagicMock()
    session.get.return_value = resp

    out = list(
        fetch_all_records(
            limit_per_call=100,
            session=session,
            rate_limiter=MagicMock(acquire=MagicMock()),
        )
    )
    assert len(out) == 2
    assert session.get.call_count == 1


def test_fetch_all_records_respects_max_records():
    session = MagicMock()
    resp = MagicMock()
    resp.json.return_value = {
        "total_count": 100,
        "results": [SAMPLE_RECORD] * 50,
    }
    resp.raise_for_status = MagicMock()
    session.get.return_value = resp

    out = list(
        fetch_all_records(
            limit_per_call=50,
            max_records=10,
            session=session,
            rate_limiter=MagicMock(acquire=MagicMock()),
        )
    )
    assert len(out) == 10


def test_fetch_all_records_handles_empty_results():
    session = MagicMock()
    resp = MagicMock()
    resp.json.return_value = {"total_count": 0, "results": []}
    resp.raise_for_status = MagicMock()
    session.get.return_value = resp

    out = list(
        fetch_all_records(
            session=session,
            rate_limiter=MagicMock(acquire=MagicMock()),
        )
    )
    assert out == []


# --- Sauvegarde ---


def test_save_processed_writes_json(tmp_path):
    path = tmp_path / "processed.json"
    save_processed([normalize_record(SAMPLE_RECORD)], path=path)
    import json as _json
    data = _json.loads(path.read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["source"] == "monmaster"


def test_save_raw_records_writes_json(tmp_path):
    path = tmp_path / "raw.json"
    save_raw_records([SAMPLE_RECORD], path=path)
    import json as _json
    data = _json.loads(path.read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["mention"] == "BIO-INFORMATIQUE"
