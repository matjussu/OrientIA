"""Tests `src/collect/build_dares_corpus.py`."""
from __future__ import annotations

import json

import pytest

from src.collect.build_dares_corpus import (
    _safe_float,
    _slug,
    aggregate_by_fap,
    aggregate_by_region,
    build_corpus,
    save_corpus,
)


@pytest.fixture
def dares_sample():
    return [
        {
            "code_fap": "J5Z", "fap_libelle": "Agents administratifs",
            "region": "Île-de-France",
            "effectifs_2019_milliers": 50.0, "part_metier_region": 0.01,
            "indice_specificite": 1.2,
            "creations_destructions_milliers": 5.0, "creations_destructions_pct": 0.10,
            "departs_fin_carriere_milliers": 8.0, "departs_fin_carriere_pct": 0.16,
            "jeunes_debutants_milliers": 4.0, "jeunes_debutants_pct": 0.08,
            "solde_mobilites_inter_regions_milliers": 1.0,
            "solde_mobilites_inter_regions_pct": 0.02,
            "desequilibre_milliers": -2.0, "desequilibre_pct": -0.04,
            "postes_a_pourvoir_milliers": 13.0, "postes_a_pourvoir_pct": 0.26,
            "niveau_tension_2019": "3",
        },
        {
            "code_fap": "J5Z", "fap_libelle": "Agents administratifs",
            "region": "Bretagne",
            "effectifs_2019_milliers": 5.0, "part_metier_region": 0.005,
            "indice_specificite": 0.6,
            "creations_destructions_milliers": -1.0, "creations_destructions_pct": -0.05,
            "departs_fin_carriere_milliers": 1.0, "departs_fin_carriere_pct": 0.20,
            "jeunes_debutants_milliers": 0.5, "jeunes_debutants_pct": 0.10,
            "solde_mobilites_inter_regions_milliers": 0.0,
            "solde_mobilites_inter_regions_pct": 0.0,
            "desequilibre_milliers": -0.5, "desequilibre_pct": -0.05,
            "postes_a_pourvoir_milliers": 2.0, "postes_a_pourvoir_pct": 0.20,
            "niveau_tension_2019": "2",
        },
        {
            "code_fap": "P4Z", "fap_libelle": "Armée police pompiers",
            "region": "Île-de-France",
            "effectifs_2019_milliers": 30.0, "part_metier_region": 0.012,
            "indice_specificite": 1.5,
            "creations_destructions_milliers": 2.0, "creations_destructions_pct": 0.05,
            "departs_fin_carriere_milliers": 5.0, "departs_fin_carriere_pct": 0.16,
            "jeunes_debutants_milliers": 3.0, "jeunes_debutants_pct": 0.10,
            "solde_mobilites_inter_regions_milliers": 0.0,
            "solde_mobilites_inter_regions_pct": 0.0,
            "desequilibre_milliers": -3.0, "desequilibre_pct": -0.10,
            "postes_a_pourvoir_milliers": 7.0, "postes_a_pourvoir_pct": 0.23,
            "niveau_tension_2019": "4",
        },
    ]


class TestSafeFloat:
    def test_basic(self):
        assert _safe_float(3.5) == 3.5
        assert _safe_float("3.5") == 3.5

    def test_none_empty(self):
        assert _safe_float(None) is None
        assert _safe_float("") is None

    def test_invalid(self):
        assert _safe_float("abc") is None


def test_slug():
    assert _slug("Île-de-France") == "ile-de-france"
    assert _slug("Auvergne-Rhône-Alpes") == "auvergne-rhone-alpes"


class TestAggregateByFap:
    def test_aggregates_per_fap(self, dares_sample):
        out = aggregate_by_fap(dares_sample)
        # 2 FAPs distincts dans le sample
        assert len(out) == 2
        ids = {r["id"] for r in out}
        assert "dares_fap:J5Z" in ids
        assert "dares_fap:P4Z" in ids

    def test_sums_effectifs(self, dares_sample):
        out = aggregate_by_fap(dares_sample)
        j5z = next(r for r in out if r["code_fap"] == "J5Z")
        # 50 IDF + 5 Bretagne = 55
        assert j5z["effectifs_2019_total_milliers"] == 55.0

    def test_top_3_regions(self, dares_sample):
        out = aggregate_by_fap(dares_sample)
        j5z = next(r for r in out if r["code_fap"] == "J5Z")
        # IDF (50) > Bretagne (5)
        assert j5z["top_3_regions_effectifs"][0] == "Île-de-France"

    def test_text_includes_libelle(self, dares_sample):
        out = aggregate_by_fap(dares_sample)
        j5z = next(r for r in out if r["code_fap"] == "J5Z")
        assert "Agents administratifs" in j5z["text"]
        assert "FAP J5Z" in j5z["text"]


class TestAggregateByRegion:
    def test_aggregates_per_region(self, dares_sample):
        out = aggregate_by_region(dares_sample)
        # 2 régions dans le sample (IDF + Bretagne)
        assert len(out) == 2
        regions = {r["region"] for r in out}
        assert regions == {"Île-de-France", "Bretagne"}

    def test_sums_effectifs(self, dares_sample):
        out = aggregate_by_region(dares_sample)
        idf = next(r for r in out if r["region"] == "Île-de-France")
        # 50 J5Z + 30 P4Z = 80
        assert idf["effectifs_2019_total_milliers"] == 80.0

    def test_top_5_postes(self, dares_sample):
        out = aggregate_by_region(dares_sample)
        idf = next(r for r in out if r["region"] == "Île-de-France")
        # Top par postes_a_pourvoir : J5Z 13.0, P4Z 7.0
        top = idf["top_5_postes_a_pourvoir"]
        assert top[0][0] == "Agents administratifs"
        assert top[0][1] == 13.0


def test_build_corpus_combines(dares_sample):
    corpus = build_corpus(dares_sample)
    # 2 FAP + 2 régions = 4 cells
    assert len(corpus) == 4
    assert all(c["domain"] == "metier_prospective" for c in corpus)
    assert all(c["source"] == "dares_metiers_2030" for c in corpus)


def test_save_corpus_round_trip(tmp_path, dares_sample):
    corpus = build_corpus(dares_sample)
    target = tmp_path / "out.json"
    save_corpus(corpus, path=target)
    loaded = json.loads(target.read_text(encoding="utf-8"))
    # JSON convertit tuples en list — comparer après conversion
    assert len(loaded) == len(corpus)
    for orig, new in zip(corpus, loaded):
        assert new["id"] == orig["id"]
        assert new["text"] == orig["text"]


def test_text_format_includes_dares_source(dares_sample):
    corpus = build_corpus(dares_sample)
    for c in corpus:
        assert "DARES" in c["text"]
