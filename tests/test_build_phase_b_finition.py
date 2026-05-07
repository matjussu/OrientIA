"""Tests des transformers Phase B finalisation.

- src/collect/build_onisep_metiers_corpus.py (gap fixé)
- src/collect/build_doctorat_corpus.py (gap fixé)
- Mapping ville → région dans run_merge_v3.py NORMALIZE
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.collect.build_onisep_metiers_corpus import (
    _extract_codes_rome,
    _extract_slug_from_url,
    build_corpus as build_onisep_corpus,
    normalize_to_corpus as normalize_onisep,
)
from src.collect.build_doctorat_corpus import (
    _format_pct,
    _slug,
    build_corpus as build_doctorat_corpus,
    normalize_to_corpus as normalize_doctorat,
)
from src.collect.run_merge_v3 import (
    _infer_region_from_ville,
    stage_normalize,
)


# ─────────────── ONISEP métiers fixtures ───────────────


def fiche_onisep_metier_complete() -> dict:
    return {
        "source": "onisep_metiers",
        "type": "metier",
        "libelle": "accompagnant éducatif et social",
        "codes_rome": [
            {"code": "K1301", "libelle": "Accompagnement médicosocial"},
            {"code": "K1302", "libelle": "Assistance auprès d'adultes"},
        ],
        "rome_link": "https://candidat.francetravail.fr/metierscope/fiche-metier/K1301",
        "url_onisep": "https://www.onisep.fr/http/redirection/metier/slug/MET.782",
        "gfe": "GFE R : santé, social, soins personnels",
        "domaine": "santé, social",
        "publication": "Travail social",
        "collection": "Parcours",
        "annee": 2024,
        "date_de_modification": "05/03/2026",
    }


def fiche_onisep_metier_minimal() -> dict:
    return {
        "source": "onisep_metiers",
        "libelle": "ingénieur informaticien",
        "codes_rome": [],
    }


def fiche_onisep_metier_malformed() -> dict:
    """Sans libelle → doit retourner None."""
    return {"source": "onisep_metiers", "libelle": ""}


class TestOnisepMetiersHelpers:
    def test_extract_slug_from_url(self):
        assert _extract_slug_from_url(
            "https://www.onisep.fr/http/redirection/metier/slug/MET.782"
        ) == "MET.782"
        assert _extract_slug_from_url(None) is None
        assert _extract_slug_from_url("https://example.com") is None

    def test_extract_codes_rome(self):
        codes, libs = _extract_codes_rome(fiche_onisep_metier_complete())
        assert codes == ["K1301", "K1302"]
        assert "Accompagnement médicosocial" in libs


class TestOnisepMetiersNormalize:
    def test_complete_fiche_produces_record(self):
        rec = normalize_onisep(fiche_onisep_metier_complete())
        assert rec is not None
        assert rec["id"] == "onisep_metier:MET.782"
        assert rec["domain"] == "metier"
        assert rec["source"] == "onisep_metiers"
        assert rec["libelle"] == "accompagnant éducatif et social"
        assert "K1301" in rec["codes_rome"]

    def test_provenance_tier_1(self):
        rec = normalize_onisep(fiche_onisep_metier_complete())
        assert rec["provenance"]["tier"] == "tier_1"
        assert rec["provenance"]["source_label"] == "ONISEP — métiers"
        # last_updated converti DD/MM/YYYY → YYYY-MM-DD
        assert rec["provenance"]["last_updated"] == "2026-03-05"

    def test_text_includes_codes_rome_and_gfe(self):
        rec = normalize_onisep(fiche_onisep_metier_complete())
        assert "K1301" in rec["text"]
        assert "GFE R" in rec["text"]

    def test_minimal_fiche_still_works(self):
        rec = normalize_onisep(fiche_onisep_metier_minimal())
        assert rec is not None
        assert rec["codes_rome"] == []

    def test_malformed_returns_none(self):
        assert normalize_onisep(fiche_onisep_metier_malformed()) is None


class TestOnisepMetiersBuildCorpus:
    def test_dedup_by_id(self):
        # Même MET.X présent 2 fois (différentes éditions) → 1 record
        f1 = fiche_onisep_metier_complete()
        f2 = fiche_onisep_metier_complete()
        f2["annee"] = 2025  # version plus récente, mais même MET.782
        out = build_onisep_corpus([f1, f2])
        assert len(out) == 1

    def test_sort_deterministic(self):
        f1 = fiche_onisep_metier_complete()  # MET.782
        f2 = fiche_onisep_metier_minimal()   # id slug-based
        out = build_onisep_corpus([f1, f2])
        # Tri par id : "onisep_metier:MET.782" < "onisep_metier:ingenieur..."
        # mais en fait MET.782 < ingenieur lexicographically (M < i en ASCII = M=77, i=105)
        # Donc MET.782 vient avant
        assert out[0]["id"].startswith("onisep_metier:MET")


# ─────────────── Doctorat IP fixtures ───────────────


def fiche_doctorat_complete() -> dict:
    return {
        "source": "ip_doc_doctorat",
        "annee": "2014",
        "situation": "12 mois après le diplôme",
        "discipline_agregee": "Sciences et leurs interactions",
        "discipline_principale": "Chimie et sciences des matériaux",
        "domaine_orientia": "sciences_fondamentales",
        "niveau_orientia": "bac+8",
        "genre": "hommes",
        "nb_repondants": 452,
        "taux_insertion": 0.81,
        "part_cadre": 0.94,
        "part_temps_plein": 0.97,
        "part_stable": 0.46,
        "salaire_net_median_mensuel": 2125,
        "salaire_net_q1_mensuel": 1875,
        "salaire_net_q3_mensuel": 2345,
    }


def fiche_doctorat_24m() -> dict:
    """Même discipline mais situation différente — id distinct attendu."""
    f = fiche_doctorat_complete()
    f["situation"] = "24 mois après le diplôme"
    return f


class TestDoctoratHelpers:
    def test_format_pct(self):
        assert _format_pct(0.81) == "81%"
        assert _format_pct(None) == "n/d"

    def test_slug(self):
        assert _slug("Chimie et sciences des matériaux") == "chimie-et-sciences-des-materiaux"
        assert _slug(None) == "unknown"
        assert _slug("") == "unknown"


class TestDoctoratNormalize:
    def test_complete_fiche_produces_record(self):
        rec = normalize_doctorat(fiche_doctorat_complete())
        assert rec is not None
        assert rec["domain"] == "insertion_pro"
        assert rec["source"] == "ip_doc_doctorat"
        assert rec["niveau"] == "bac+8"
        assert rec["taux_insertion"] == 0.81

    def test_id_includes_situation_no_collision(self):
        """Bug fix : situation 12m vs 24m → ids distincts."""
        rec_12m = normalize_doctorat(fiche_doctorat_complete())
        rec_24m = normalize_doctorat(fiche_doctorat_24m())
        assert rec_12m["id"] != rec_24m["id"]

    def test_provenance_tier_1_mesr(self):
        rec = normalize_doctorat(fiche_doctorat_complete())
        assert rec["provenance"]["tier"] == "tier_1"
        assert "MESR" in rec["provenance"]["source_label"]

    def test_text_includes_chiffres(self):
        rec = normalize_doctorat(fiche_doctorat_complete())
        assert "Insertion doctorat" in rec["text"]
        assert "81%" in rec["text"]  # taux_insertion formaté
        assert "2125" in rec["text"]  # salaire médian

    def test_no_discipline_returns_none(self):
        f = fiche_doctorat_complete()
        f["discipline_principale"] = ""
        assert normalize_doctorat(f) is None


class TestDoctoratBuildCorpus:
    def test_no_collisions_with_situation(self):
        """Le fix : situation dans l'id permet de garder les deux records."""
        out = build_doctorat_corpus([
            fiche_doctorat_complete(),
            fiche_doctorat_24m(),
        ])
        assert len(out) == 2

    def test_dedup_exact_duplicates(self):
        out = build_doctorat_corpus([
            fiche_doctorat_complete(),
            fiche_doctorat_complete(),
        ])
        assert len(out) == 1


# ─────────────── Mapping ville → région ───────────────


class TestVilleToRegion:
    def test_paris_inferred_idf(self):
        assert _infer_region_from_ville("Paris") == "Île-de-France"

    def test_lyon_inferred_aura(self):
        assert _infer_region_from_ville("Lyon") == "Auvergne-Rhône-Alpes"

    def test_marseille_inferred_paca(self):
        assert _infer_region_from_ville("Marseille") == "Provence-Alpes-Côte d'Azur"

    def test_brest_inferred_bretagne(self):
        assert _infer_region_from_ville("Brest") == "Bretagne"

    def test_handles_casse_and_accents(self):
        assert _infer_region_from_ville("AIX-EN-PROVENCE") == "Provence-Alpes-Côte d'Azur"
        assert _infer_region_from_ville("Évry") == "Île-de-France"

    def test_handles_dash_variations(self):
        # "saint-denis" vs "saint denis"
        assert _infer_region_from_ville("Saint-Denis") == "Île-de-France"
        assert _infer_region_from_ville("Saint Denis") == "Île-de-France"

    def test_drom_communes(self):
        assert _infer_region_from_ville("Fort-de-France") == "Martinique"
        assert _infer_region_from_ville("Cayenne") == "Guyane"

    def test_unknown_ville_returns_none(self):
        assert _infer_region_from_ville("Petit Village Inconnu") is None
        assert _infer_region_from_ville(None) is None
        assert _infer_region_from_ville("") is None


class TestNormalizeStageInfersRegion:
    """Stage 5 doit combler les régions absentes via _infer_region_from_ville."""

    def test_fills_region_when_missing(self):
        fiche = {"nom": "Test", "ville": "Lyon"}  # pas de region
        out, stats = stage_normalize([fiche])
        assert out[0]["region"] == "Auvergne-Rhône-Alpes"
        assert stats["n_region_inferred_from_ville"] == 1

    def test_does_not_override_existing_region(self):
        fiche = {"nom": "Test", "ville": "Lyon", "region": "Pays de la Loire"}
        out, _ = stage_normalize([fiche])
        # Garde la région existante (canonisée mais pas écrasée)
        assert out[0]["region"] == "Pays de la Loire"

    def test_no_op_when_ville_unknown(self):
        fiche = {"nom": "Test", "ville": "Village Inconnu XYZ"}
        out, stats = stage_normalize([fiche])
        assert out[0].get("region") is None
        assert stats["n_region_inferred_from_ville"] == 0


# ─────────────── Smoke test sur vraies sources (opt-in) ───────────────


@pytest.mark.skipif(
    not Path("data/processed/onisep_metiers.json").exists(),
    reason="onisep_metiers.json absent (env minimal)"
)
class TestSmokeOnisepMetiers:
    def test_real_data_produces_records(self):
        raw = json.loads(Path("data/processed/onisep_metiers.json").read_text())
        corpus = build_onisep_corpus(raw)
        # 1518 RAW → ~1075 après dédup par MET.X (multiples éditions par métier)
        assert 800 <= len(corpus) <= 1518
        # Tous ont domain=metier + tier_1
        for rec in corpus:
            assert rec["domain"] == "metier"
            assert rec["provenance"]["tier"] == "tier_1"


@pytest.mark.skipif(
    not Path("data/processed/ip_doc_doctorat.json").exists(),
    reason="ip_doc_doctorat.json absent (env minimal)"
)
class TestSmokeDoctorat:
    def test_real_data_produces_240_records(self):
        raw = json.loads(Path("data/processed/ip_doc_doctorat.json").read_text())
        corpus = build_doctorat_corpus(raw)
        # 240 RAW → 240 après fix situation dans l'id
        assert len(corpus) == 240
        # Tous ont taux_insertion (le filtre _has_any_metric n'est pas appliqué
        # en build_doctorat_corpus — tous les records sont conservés)
        for rec in corpus:
            assert rec["taux_insertion"] is not None
