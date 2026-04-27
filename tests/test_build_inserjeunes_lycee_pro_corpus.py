"""Tests `src/collect/build_inserjeunes_lycee_pro_corpus.py`."""
from __future__ import annotations

import json

import pytest

from src.collect.build_inserjeunes_lycee_pro_corpus import (
    _avg,
    _get_taux_emploi,
    _slug,
    aggregate_by_formation,
    aggregate_by_region_diplome,
    build_corpus,
    save_corpus,
)


@pytest.fixture
def inserjeunes_sample():
    """Sample 6 records, 3 formations × 2 régions × 2 diplômes."""
    return [
        {
            "libelle_formation": "macon", "type_diplome": "CAP",
            "region": "HAUTS-DE-FRANCE",
            "taux_emploi": {"6m": 0.50, "12m": 0.62, "18m": 0.65, "24m": 0.70},
            "taux_poursuite_etudes": 0.10, "niveau_orientia": "cap-bep",
        },
        {
            "libelle_formation": "macon", "type_diplome": "CAP",
            "region": "ILE-DE-FRANCE",
            "taux_emploi": {"6m": None, "12m": 0.55, "18m": None, "24m": 0.60},
            "taux_poursuite_etudes": 0.15, "niveau_orientia": "cap-bep",
        },
        {
            "libelle_formation": "cuisine", "type_diplome": "CAP",
            "region": "HAUTS-DE-FRANCE",
            "taux_emploi": {"6m": None, "12m": 0.70, "18m": None, "24m": None},
            "taux_poursuite_etudes": 0.20, "niveau_orientia": "cap-bep",
        },
        {
            "libelle_formation": "gestion-administration", "type_diplome": "BAC PRO",
            "region": "ILE-DE-FRANCE",
            "taux_emploi": {"6m": None, "12m": 0.45, "18m": None, "24m": 0.55},
            "taux_poursuite_etudes": 0.40, "niveau_orientia": "bac",
        },
        {
            "libelle_formation": "gestion-administration", "type_diplome": "BAC PRO",
            "region": "HAUTS-DE-FRANCE",
            "taux_emploi": {"6m": None, "12m": None, "18m": None, "24m": None},
            "taux_poursuite_etudes": None, "niveau_orientia": "bac",
        },
        {
            "libelle_formation": "", "type_diplome": "CAP",
            "region": "HAUTS-DE-FRANCE",
            "taux_emploi": None, "taux_poursuite_etudes": None,
        },  # à ignorer (libelle vide)
    ]


class TestSlug:
    def test_basic(self):
        assert _slug("HAUTS-DE-FRANCE") == "hauts-de-france"
        assert _slug("Île-de-France") == "ile-de-france"
        assert _slug("Mâcon") == "macon"


class TestAvg:
    def test_basic(self):
        assert _avg([1.0, 2.0, 3.0]) == 2.0

    def test_ignores_none(self):
        assert _avg([1.0, None, 3.0]) == 2.0

    def test_all_none(self):
        assert _avg([None, None]) is None

    def test_empty(self):
        assert _avg([]) is None


class TestGetTauxEmploi:
    def test_extracts_horizon(self):
        rec = {"taux_emploi": {"12m": 0.62, "24m": 0.70}}
        assert _get_taux_emploi(rec, "12m") == 0.62
        assert _get_taux_emploi(rec, "24m") == 0.70

    def test_none_horizon(self):
        rec = {"taux_emploi": {"12m": None}}
        assert _get_taux_emploi(rec, "12m") is None

    def test_missing_taux_emploi(self):
        assert _get_taux_emploi({}, "12m") is None
        assert _get_taux_emploi({"taux_emploi": None}, "12m") is None


class TestAggregateByFormation:
    def test_one_cell_per_formation_diplome(self, inserjeunes_sample):
        out = aggregate_by_formation(inserjeunes_sample)
        # 3 formations × diplôme distincts (macon CAP, cuisine CAP, gestion-administration BAC PRO)
        # le record vide est ignoré
        assert len(out) == 3
        ids = {r["id"] for r in out}
        assert "inserjeunes_formation:cap:macon" in ids
        assert "inserjeunes_formation:cap:cuisine" in ids
        assert "inserjeunes_formation:bac-pro:gestion-administration" in ids

    def test_averages_emploi_across_records(self, inserjeunes_sample):
        out = aggregate_by_formation(inserjeunes_sample)
        macon = next(r for r in out if r["libelle_formation"] == "macon")
        # macon × 2 records : 12m = avg(0.62, 0.55) = 0.585
        assert macon["taux_emploi_12m_moyen"] == pytest.approx(0.585, abs=0.001)
        # 24m = avg(0.70, 0.60) = 0.65
        assert macon["taux_emploi_24m_moyen"] == pytest.approx(0.65, abs=0.001)

    def test_handles_no_emploi_data(self, inserjeunes_sample):
        """gestion-administration BAC PRO a 1 record avec data, 1 sans."""
        out = aggregate_by_formation(inserjeunes_sample)
        ga = next(r for r in out if r["libelle_formation"] == "gestion-administration")
        # 12m : avg(0.45, None) = 0.45 (None ignoré)
        assert ga["taux_emploi_12m_moyen"] == pytest.approx(0.45, abs=0.001)
        # n_with_emploi_data : 1/2 records ont au moins 1 horizon non-None
        assert ga["n_with_emploi_data"] == 1

    def test_skips_records_with_empty_libelle(self, inserjeunes_sample):
        out = aggregate_by_formation(inserjeunes_sample)
        # le record vide (libelle="") est skippé
        ids = [r["id"] for r in out]
        assert all("::" not in i for i in ids)  # pas de double colon (slug vide)

    def test_granularity_tag(self, inserjeunes_sample):
        out = aggregate_by_formation(inserjeunes_sample)
        assert all(r["granularity"] == "formation_france" for r in out)

    def test_text_includes_diplome_and_libelle(self, inserjeunes_sample):
        out = aggregate_by_formation(inserjeunes_sample)
        macon = next(r for r in out if r["libelle_formation"] == "macon")
        assert "macon" in macon["text"]
        assert "CAP" in macon["text"]
        assert "France" in macon["text"]


class TestAggregateByRegionDiplome:
    def test_one_cell_per_region_diplome(self, inserjeunes_sample):
        out = aggregate_by_region_diplome(inserjeunes_sample)
        # Couples (région, diplôme) :
        # (HAUTS-DE-FRANCE, CAP) — macon + cuisine
        # (ILE-DE-FRANCE, CAP) — macon
        # (ILE-DE-FRANCE, BAC PRO) — gestion-administration
        # (HAUTS-DE-FRANCE, BAC PRO) — gestion-administration
        # le record vide est skippé sur libelle mais a région+diplôme — il est dans le set ?
        # Note : ce test agrège par (région, diplôme) sans vérifier libelle, donc le record vide compte
        # (HAUTS-DE-FRANCE, CAP) inclut macon + cuisine + le record vide = 3 records
        out_ids = {r["id"] for r in out}
        assert "inserjeunes_region_diplome:hauts-de-france:cap" in out_ids
        assert "inserjeunes_region_diplome:ile-de-france:cap" in out_ids
        assert "inserjeunes_region_diplome:ile-de-france:bac-pro" in out_ids
        assert "inserjeunes_region_diplome:hauts-de-france:bac-pro" in out_ids
        assert len(out) == 4

    def test_averages_emploi(self, inserjeunes_sample):
        out = aggregate_by_region_diplome(inserjeunes_sample)
        hdf_cap = next(
            r for r in out
            if r["region"] == "HAUTS-DE-FRANCE" and r["type_diplome"] == "CAP"
        )
        # macon HDF (12m=0.62) + cuisine HDF (12m=0.70) + vide (12m=None) → avg = 0.66
        assert hdf_cap["taux_emploi_12m_moyen"] == pytest.approx(0.66, abs=0.001)

    def test_top_5_specialites(self, inserjeunes_sample):
        out = aggregate_by_region_diplome(inserjeunes_sample)
        hdf_cap = next(
            r for r in out
            if r["region"] == "HAUTS-DE-FRANCE" and r["type_diplome"] == "CAP"
        )
        # 2 spécialités CAP en HDF : macon (1) + cuisine (1)
        # le record vide a libelle=" " donc ignoré dans top_5
        top = hdf_cap["top_5_specialites"]
        libs = {lib for lib, _ in top}
        assert libs == {"macon", "cuisine"}

    def test_granularity_tag(self, inserjeunes_sample):
        out = aggregate_by_region_diplome(inserjeunes_sample)
        assert all(r["granularity"] == "region_diplome" for r in out)


def test_build_corpus_combines(inserjeunes_sample):
    corpus = build_corpus(inserjeunes_sample)
    # 3 cells formation_france + 4 cells region_diplome = 7
    assert len(corpus) == 7
    assert all(c["domain"] == "formation_insertion" for c in corpus)
    assert all(c["source"] == "inserjeunes_lycee_pro" for c in corpus)
    granularities = {c["granularity"] for c in corpus}
    assert granularities == {"formation_france", "region_diplome"}


def test_save_corpus_round_trip(tmp_path, inserjeunes_sample):
    corpus = build_corpus(inserjeunes_sample)
    target = tmp_path / "out.json"
    save_corpus(corpus, path=target)
    loaded = json.loads(target.read_text(encoding="utf-8"))
    assert len(loaded) == len(corpus)
    for orig, new in zip(corpus, loaded):
        assert new["id"] == orig["id"]
        assert new["text"] == orig["text"]


def test_text_format_includes_inserjeunes_source(inserjeunes_sample):
    corpus = build_corpus(inserjeunes_sample)
    for c in corpus:
        assert "Inserjeunes" in c["text"]
