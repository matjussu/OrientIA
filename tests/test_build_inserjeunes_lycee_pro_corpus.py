"""Tests `src/collect/build_inserjeunes_lycee_pro_corpus.py`."""
from __future__ import annotations

import json

import pytest

from src.collect.build_inserjeunes_lycee_pro_corpus import (
    MIN_RECORDS_PER_TRIPLET,
    _avg,
    _get_taux_emploi,
    _slug,
    aggregate_by_formation,
    aggregate_by_formation_region_diplome,
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


class TestAggregateByFormationRegionDiplomeSprint7:
    """Sprint 7 Action 4 — granularité 3 (libellé × type × région) avec
    filter MIN_RECORDS_PER_TRIPLET pour éviter dilution top-K."""

    def test_min_records_constant_value(self):
        """Le seuil par défaut est 15 (sweet spot 2 004 cells sur vrai data,
        cohérent target Sprint 5 P1.4 ≤2000)."""
        assert MIN_RECORDS_PER_TRIPLET == 15

    def test_filter_below_min_records_returns_empty(self, inserjeunes_sample):
        """Sample a 1-record-per-triplet → tous filtrés avec min_records=15."""
        out = aggregate_by_formation_region_diplome(inserjeunes_sample)
        # 5 couples (libellé, type, région) distincts dans sample mais tous 1 record
        assert out == []

    def test_filter_below_min_records_with_explicit_min(self, inserjeunes_sample):
        """min_records=1 → tous les couples passent."""
        out = aggregate_by_formation_region_diplome(inserjeunes_sample, min_records=1)
        # 5 couples valides (record vide ignoré pour libellé vide) :
        # macon×CAP×HDF, macon×CAP×IDF, cuisine×CAP×HDF, gestion×BAC PRO×HDF, gestion×BAC PRO×IDF
        assert len(out) == 5
        ids = {r["id"] for r in out}
        assert "inserjeunes_formation_region:cap:macon:hauts-de-france" in ids
        assert "inserjeunes_formation_region:cap:macon:ile-de-france" in ids

    def test_passes_filter_with_enough_records(self):
        """Couple avec ≥15 cohortes (default) → cell créée."""
        records = [
            {
                "libelle_formation": "macon", "type_diplome": "CAP",
                "region": "HAUTS-DE-FRANCE",
                "taux_emploi": {"6m": None, "12m": 0.5 + i * 0.02, "18m": None, "24m": 0.6},
                "taux_poursuite_etudes": 0.10,
            }
            for i in range(16)  # ≥15 records pour passer le filter
        ]
        out = aggregate_by_formation_region_diplome(records)
        assert len(out) == 1
        cell = out[0]
        assert cell["granularity"] == "formation_region_diplome"
        assert cell["libelle_formation"] == "macon"
        assert cell["type_diplome"] == "CAP"
        assert cell["region"] == "HAUTS-DE-FRANCE"
        assert cell["n_records"] == 16

    def test_no_aggregation_just_avg(self):
        """Test l'agrégation par moyenne pondérée (pas SUM). Avec min_records=1."""
        records = [
            {
                "libelle_formation": "test", "type_diplome": "BAC PRO",
                "region": "BRETAGNE",
                "taux_emploi": {"12m": 0.40, "24m": None},
                "taux_poursuite_etudes": None,
            }
            for _ in range(5)
        ] + [{
            "libelle_formation": "test", "type_diplome": "BAC PRO",
            "region": "BRETAGNE",
            "taux_emploi": {"12m": 0.60, "24m": None},
            "taux_poursuite_etudes": None,
        }]
        out = aggregate_by_formation_region_diplome(records, min_records=1)
        assert len(out) == 1
        # 5×0.40 + 1×0.60 / 6 = 2.6/6 ≈ 0.4333
        assert out[0]["taux_emploi_12m_moyen"] == pytest.approx(0.4333, abs=0.001)

    def test_skips_records_with_missing_field(self):
        """Records avec libellé/type/région vide sont ignorés."""
        records = [
            {"libelle_formation": "", "type_diplome": "CAP", "region": "HDF",
             "taux_emploi": None, "taux_poursuite_etudes": None},
        ] * 10
        out = aggregate_by_formation_region_diplome(records)
        assert out == []

    def test_text_includes_libelle_diplome_region(self):
        records = [
            {
                "libelle_formation": "cuisine", "type_diplome": "CAP",
                "region": "OCCITANIE",
                "taux_emploi": {"12m": 0.6, "24m": 0.7},
                "taux_poursuite_etudes": 0.2,
            }
            for _ in range(16)  # ≥15 pour passer le filter par défaut
        ]
        out = aggregate_by_formation_region_diplome(records)
        assert len(out) == 1
        text = out[0]["text"]
        assert "cuisine" in text
        assert "CAP" in text
        assert "OCCITANIE" in text
        assert "Inserjeunes" in text


def test_build_corpus_combines(inserjeunes_sample):
    corpus = build_corpus(inserjeunes_sample)
    # 3 cells formation_france + 4 cells region_diplome = 7
    # (granularité 3 filtré par MIN_RECORDS_PER_TRIPLET=5 sur sample 1-record-per-triplet)
    assert len(corpus) == 7
    assert all(c["domain"] == "formation_insertion" for c in corpus)
    assert all(c["source"] == "inserjeunes_lycee_pro" for c in corpus)
    granularities = {c["granularity"] for c in corpus}
    # Sprint 7 Action 4 : granularité 3 ajoutée mais filtrée sur sample petit
    # (pour vrai data avec ≥5 cohortes par couple, granularité 3 sera présente)
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
