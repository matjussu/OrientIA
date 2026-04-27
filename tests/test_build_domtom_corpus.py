"""Tests `src/collect/build_domtom_corpus.py`."""
from __future__ import annotations

import json

import pytest

from src.collect.build_domtom_corpus import (
    _format_indicator,
    _slug,
    aggregate_by_territoire,
    aggregate_synthese_cross,
    build_corpus,
    load_raw,
    save_corpus,
)


@pytest.fixture
def domtom_raw_sample() -> dict:
    return {
        "version": "2026-04-27",
        "note_methodo": "test",
        "territoires": [
            {
                "id": "test-drom-1",
                "code_insee": "971",
                "nom": "Test DROM 1",
                "zone": "Test Zone",
                "population_approximative_2024": 100000,
                "densite_hab_km2": 200,
                "part_jeunes_15_24_pct": 15,
                "taux_chomage_global_pct": {"approx": 18, "annee": "2023", "comparaison_france_metro": 7},
                "taux_chomage_jeunes_15_24_pct": {"approx": 35, "annee": "2023"},
                "pib_par_habitant_eur": {"approx": 22000, "annee": "2022", "comparaison_france_metro": 38000},
                "salaire_median_net_mensuel_eur": {"approx": 1700, "annee": "2022"},
                "secteurs_dominants": ["tourisme", "BTP"],
                "specificites_orientation": ["Insularité"],
                "sources_officielles": ["https://example.com"],
            },
            {
                "id": "test-drom-2",
                "code_insee": "972",
                "nom": "Test DROM 2",
                "zone": "Test Zone B",
                "population_approximative_2024": 50000,
                "densite_hab_km2": 100,
                "secteurs_dominants": ["agriculture"],
                "sources_officielles": ["https://example.com/b"],
            },
        ],
        "synthese_cross_drom": {
            "id": "synthese_test",
            "nom": "DROM synthèse test",
            "indicateurs_communs": {
                "ecart_pib": "Tous DROM ont PIB inférieur métro",
                "chomage_eleve": "Chômage 4-7× supérieur",
            },
            "dispositifs_specifiques_drom": [
                "LADOM passeport mobilité",
                "SMA insertion",
            ],
            "sources_officielles_synthese": ["https://insee.fr"],
        },
    }


class TestSlug:
    def test_basic(self):
        assert _slug("La Réunion") == "la-reunion"
        assert _slug("Île-de-France") == "ile-de-france"


class TestFormatIndicator:
    def test_dict_with_approx(self):
        out = _format_indicator(
            "Test (%)",
            {"approx": 18, "annee": "2023", "comparaison_france_metro": 7},
        )
        assert "~18" in out
        assert "2023" in out
        assert "France métro ~7" in out

    def test_dict_without_comparaison(self):
        out = _format_indicator("Test", {"approx": 35, "annee": "2023"})
        assert "~35" in out
        assert "2023" in out
        assert "France métro" not in out

    def test_dict_without_approx_returns_none(self):
        assert _format_indicator("Test", {"annee": "2023"}) is None

    def test_int_value(self):
        out = _format_indicator("Test", 42)
        assert "42" in out

    def test_none_or_empty(self):
        assert _format_indicator("Test", None) is None


class TestAggregateByTerritoire:
    def test_one_cell_per_territoire(self, domtom_raw_sample):
        out = aggregate_by_territoire(domtom_raw_sample)
        assert len(out) == 2
        ids = {r["id"] for r in out}
        assert "domtom_territoire:test-drom-1" in ids
        assert "domtom_territoire:test-drom-2" in ids

    def test_granularity_tag(self, domtom_raw_sample):
        out = aggregate_by_territoire(domtom_raw_sample)
        assert all(r["granularity"] == "territoire" for r in out)

    def test_text_includes_nom_zone_population(self, domtom_raw_sample):
        out = aggregate_by_territoire(domtom_raw_sample)
        d1 = next(r for r in out if r["territoire_id"] == "test-drom-1")
        assert "Test DROM 1" in d1["text"]
        assert "Test Zone" in d1["text"]
        assert "100 000" in d1["text"]
        assert "971" in d1["text"]

    def test_text_includes_chomage_and_comparaison_france(self, domtom_raw_sample):
        """Anti-hallu : la comparaison vs France métro est explicite."""
        out = aggregate_by_territoire(domtom_raw_sample)
        d1 = next(r for r in out if r["territoire_id"] == "test-drom-1")
        assert "~18" in d1["text"]  # taux chômage approx
        assert "France métro ~7" in d1["text"]

    def test_text_includes_secteurs(self, domtom_raw_sample):
        out = aggregate_by_territoire(domtom_raw_sample)
        d1 = next(r for r in out if r["territoire_id"] == "test-drom-1")
        assert "tourisme" in d1["text"]
        assert "BTP" in d1["text"]

    def test_text_includes_specificites(self, domtom_raw_sample):
        out = aggregate_by_territoire(domtom_raw_sample)
        d1 = next(r for r in out if r["territoire_id"] == "test-drom-1")
        assert "Insularité" in d1["text"]

    def test_text_includes_sources_officielles(self, domtom_raw_sample):
        """Anti-hallu : URL source toujours présente."""
        out = aggregate_by_territoire(domtom_raw_sample)
        for r in out:
            assert "Sources officielles" in r["text"]

    def test_handles_minimal_territoire(self, domtom_raw_sample):
        """Territoire avec seulement les champs minimaux ne crash pas."""
        out = aggregate_by_territoire(domtom_raw_sample)
        d2 = next(r for r in out if r["territoire_id"] == "test-drom-2")
        assert "Test DROM 2" in d2["text"]
        assert "agriculture" in d2["text"]


class TestAggregateSyntheseCross:
    def test_one_cell_synthese(self, domtom_raw_sample):
        out = aggregate_synthese_cross(domtom_raw_sample)
        assert len(out) == 1
        assert out[0]["id"] == "domtom_synthese:synthese_test"

    def test_granularity_tag(self, domtom_raw_sample):
        out = aggregate_synthese_cross(domtom_raw_sample)
        assert out[0]["granularity"] == "synthese_cross"

    def test_text_includes_indicateurs(self, domtom_raw_sample):
        out = aggregate_synthese_cross(domtom_raw_sample)
        text = out[0]["text"]
        assert "PIB inférieur" in text
        assert "4-7" in text

    def test_text_includes_dispositifs(self, domtom_raw_sample):
        out = aggregate_synthese_cross(domtom_raw_sample)
        text = out[0]["text"]
        assert "LADOM" in text
        assert "SMA" in text

    def test_no_synthese_returns_empty(self):
        out = aggregate_synthese_cross({"territoires": []})
        assert out == []


def test_build_corpus_combines(domtom_raw_sample):
    corpus = build_corpus(domtom_raw_sample)
    # 2 territoires + 1 synthèse + 10 dispositifs_etendus (Sprint 8 W2) = 13
    # Note : aggregate_dispositifs_etendus() lit le vrai fichier prod
    # (data/raw/domtom/dispositifs_etendus_2026.json) qui contient 10 cells.
    assert len(corpus) >= 3  # au moins territoires + synthèse du sample
    assert all(c["domain"] == "territoire_drom" for c in corpus)
    assert all(c["source"] == "domtom_curated" for c in corpus)
    granularities = {c["granularity"] for c in corpus}
    # Sample fournit territoire + synthese_cross. dispositif_etendu vient
    # du fichier prod (10 cells réelles Sprint 8 W2).
    assert "territoire" in granularities
    assert "synthese_cross" in granularities


def test_save_corpus_round_trip(tmp_path, domtom_raw_sample):
    corpus = build_corpus(domtom_raw_sample)
    target = tmp_path / "out.json"
    save_corpus(corpus, path=target)
    loaded = json.loads(target.read_text(encoding="utf-8"))
    assert len(loaded) == len(corpus)


def test_real_raw_file_loads():
    """Smoke test : le fichier raw production parse correctement."""
    raw = load_raw()
    assert "territoires" in raw
    assert len(raw["territoires"]) == 5  # 5 DROM (Guadeloupe, Martinique, Guyane, Réunion, Mayotte)
    # Tous les DROM ciblés
    ids = {t["id"] for t in raw["territoires"]}
    assert ids == {"guadeloupe", "martinique", "guyane", "la-reunion", "mayotte"}
    # Synthèse cross-DROM présente
    assert "synthese_cross_drom" in raw


def test_real_raw_file_mayotte_covered():
    """Spécifique : Mayotte (gap noted dans 3b) doit être couverte ici."""
    raw = load_raw()
    mayotte = next((t for t in raw["territoires"] if t["id"] == "mayotte"), None)
    assert mayotte is not None
    assert mayotte["code_insee"] == "976"
    assert mayotte["nom"] == "Mayotte"
