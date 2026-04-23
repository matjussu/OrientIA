"""Tests `src/collect/onisep_metiers.py` — D12 ONISEP ideo-métiers."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.collect.onisep_metiers import (
    _parse_codes_rome,
    _parse_domaine,
    _parse_libelles_rome,
    build_rome_to_metiers_index,
    normalize_all,
    normalize_metier,
    save_processed,
)


SAMPLE_RECORD = {
    "libelle_metier": "accompagnant éducatif et social",
    "lien_site_onisepfr": "https://www.onisep.fr/http/redirection/metier/slug/MET.782",
    "nom_publication": "Travail social",
    "collection": "Parcours",
    "annee": "2024",
    "gencod": "9782273016827",
    "gfe": "GFE R : santé, social, soins personnels",
    "code_rome": "K1301 | K1302",
    "libelle_rome": "Accompagnement médicosocial | Action sociale",
    "lien_rome": "https://francetravail.fr/...",
    "domainesous-domaine": "santé, social, sport > travail social",
    "date_creation": "15/01/2024",
    "date_de_modification": "10/04/2025",
}


# --- Parsers ---


def test_parse_codes_rome_splits_pipe_separated():
    assert _parse_codes_rome("K1301 | K1302") == ["K1301", "K1302"]


def test_parse_codes_rome_trims_whitespace():
    assert _parse_codes_rome("  M1405  |   M1419  ") == ["M1405", "M1419"]


def test_parse_codes_rome_empty_returns_empty_list():
    assert _parse_codes_rome("") == []
    assert _parse_codes_rome(None) == []


def test_parse_codes_rome_single():
    assert _parse_codes_rome("J1501") == ["J1501"]


def test_parse_libelles_rome_aligned():
    out = _parse_libelles_rome("Data scientist | Data engineer")
    assert out == ["Data scientist", "Data engineer"]


def test_parse_domaine_splits_arrow():
    result = _parse_domaine("santé, social, sport > travail social")
    assert result["domaine"] == "santé, social, sport"
    assert result["sous_domaine"] == "travail social"


def test_parse_domaine_no_arrow_sous_domaine_none():
    result = _parse_domaine("santé, social, sport")
    assert result["domaine"] == "santé, social, sport"
    assert result["sous_domaine"] is None


def test_parse_domaine_empty():
    assert _parse_domaine("") == {"domaine": None, "sous_domaine": None}


# --- Normalisation ---


def test_normalize_metier_preserves_libelle():
    fiche = normalize_metier(SAMPLE_RECORD)
    assert fiche["libelle"] == "accompagnant éducatif et social"
    assert fiche["source"] == "onisep_metiers"
    assert fiche["type"] == "metier"


def test_normalize_metier_zips_rome_codes_and_libelles():
    fiche = normalize_metier(SAMPLE_RECORD)
    assert len(fiche["codes_rome"]) == 2
    assert fiche["codes_rome"][0]["code"] == "K1301"
    assert fiche["codes_rome"][0]["libelle"] == "Accompagnement médicosocial"
    assert fiche["codes_rome"][1]["code"] == "K1302"


def test_normalize_metier_mismatched_lengths_fallback_to_codes_only():
    rec = {**SAMPLE_RECORD, "code_rome": "K1301", "libelle_rome": "A | B | C"}
    fiche = normalize_metier(rec)
    assert len(fiche["codes_rome"]) == 1
    assert fiche["codes_rome"][0]["code"] == "K1301"
    assert fiche["codes_rome"][0]["libelle"] is None


def test_normalize_metier_extracts_domaine_sous_domaine():
    fiche = normalize_metier(SAMPLE_RECORD)
    assert fiche["domaine"] == "santé, social, sport"
    assert fiche["sous_domaine"] == "travail social"


def test_normalize_metier_preserves_gfe():
    fiche = normalize_metier(SAMPLE_RECORD)
    assert "GFE R" in fiche["gfe"]


def test_normalize_all_maps_every_record():
    out = normalize_all([SAMPLE_RECORD, {**SAMPLE_RECORD, "libelle_metier": "data scientist"}])
    assert len(out) == 2
    assert out[1]["libelle"] == "data scientist"


# --- Index inverse ROME → métiers ---


def test_build_rome_index_groups_metiers_by_code():
    metiers = [
        {"libelle": "A", "codes_rome": [{"code": "K1301", "libelle": "X"}]},
        {"libelle": "B", "codes_rome": [{"code": "K1301", "libelle": "Y"}, {"code": "K1302"}]},
    ]
    index = build_rome_to_metiers_index(metiers)
    assert len(index["K1301"]) == 2
    libelles = {m["libelle"] for m in index["K1301"]}
    assert libelles == {"A", "B"}
    assert len(index["K1302"]) == 1


def test_build_rome_index_ignores_metiers_without_rome():
    metiers = [{"libelle": "X", "codes_rome": []}]
    index = build_rome_to_metiers_index(metiers)
    assert index == {}


# --- Save ---


def test_save_processed_writes_json(tmp_path):
    path = tmp_path / "out.json"
    save_processed([{"libelle": "A", "source": "onisep_metiers"}], path=path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data[0]["libelle"] == "A"
