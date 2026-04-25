"""Tests `src/collect/apec_regions.py` — corpus retrievable APEC régional."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.collect.apec_regions import (
    _bullets_to_dict,
    _split_regions,
    _strip_emphasis,
    build_corpus,
    build_overview_record,
    build_observations_record,
    build_region_text,
    normalize_region,
    save_corpus,
)


SAMPLE_REGION_BLOCK = """- **Recrutements 2025** : 9 990 (+5 % vs 2024 ; à contre-courant du national -3 %)
- **Prévision 2026** : **10 200** (+2 %) — permettrait de retrouver le record 2023 (10 290)
- **Créations nettes 2025** : 2 910 postes (vs 3 230 en 2024)
- **Top 5 fonctions 2025** (parts régionales) : Exploitation tertiaire 21 %, Commercial-marketing 16 %, Études-R&D 15 %, Informatique 14 %, Production industrielle 8 %
- **Répartition secteurs 2026** : Services à forte VA 31 %, Autres services 30 %, Industrie 19 %, Commerce 12 %, Construction 8 %
- **Contexte régional** : Construction +13,2 %, Industrie +7,2 %, Services marchands -11,1 % en 2026
- **Verbatim délégué (Olivier Maurin)** : "embellie liée à la bonne tenue de l'ingénierie R&D"
"""


SAMPLE_FULL_MD = """# APEC Régional Summary

## 1. Vue d'ensemble — France hexagonale 2026

- **Volume national 2025** : 294 500 recrutements (-3 % vs 2024)
- **Prévision 2026** : reprise nationale **+4 %** (≈ 305 800 recrutements)

---

## 2. Fiches par région

### 2.1 Bretagne

""" + SAMPLE_REGION_BLOCK + """

### 2.2 Normandie

- **Recrutements 2025** : 6 070 (-7 %)
- **Prévision 2026** : 6 140 (+1 %)
- **Top 5 fonctions 2025** : Commercial 16 %, Études-R&D 13 %

---

## 4. Observations cross-régions

1. **Divergence 2025 → convergence 2026** : 4 régions ont crû en 2025, 7 ont reculé.
2. **Aléas géopolitiques** : tous délégués mentionnent les tensions internationales.
"""


# --- Helpers ---


class TestStripEmphasis:
    def test_basic(self):
        assert _strip_emphasis("**foo** bar **baz**") == "foo bar baz"

    def test_no_emphasis(self):
        assert _strip_emphasis("plain text") == "plain text"


class TestBulletsToDict:
    def test_extracts_label_value(self):
        d = _bullets_to_dict(SAMPLE_REGION_BLOCK)
        assert "recrutements_2025" in d
        assert d["recrutements_2025"].startswith("9 990 (+5 %")

    def test_handles_parenthetical_label(self):
        # `**Top 5 fonctions 2025** (parts régionales) : ...`
        d = _bullets_to_dict(SAMPLE_REGION_BLOCK)
        assert "top_5_fonctions_2025" in d
        assert "Exploitation tertiaire 21 %" in d["top_5_fonctions_2025"]

    def test_strips_emphasis_in_values(self):
        d = _bullets_to_dict(SAMPLE_REGION_BLOCK)
        # `**10 200**` doit redevenir `10 200`
        assert "**" not in d["prévision_2026"]
        assert "10 200" in d["prévision_2026"]

    def test_verbatim_captured(self):
        d = _bullets_to_dict(SAMPLE_REGION_BLOCK)
        verbatim_keys = [k for k in d if k.startswith("verbatim")]
        assert len(verbatim_keys) == 1


# --- _split_regions ---


class TestSplitRegions:
    def test_splits_two_regions(self):
        regions = _split_regions(SAMPLE_FULL_MD)
        names = [r[0] for r in regions]
        assert "Bretagne" in names
        assert "Normandie" in names

    def test_block_contains_bullets(self):
        regions = _split_regions(SAMPLE_FULL_MD)
        bret = next(b for n, b in regions if n == "Bretagne")
        assert "Recrutements 2025" in bret
        assert "Verbatim délégué" in bret

    def test_block_stops_at_horizontal_rule(self):
        regions = _split_regions(SAMPLE_FULL_MD)
        norm = next(b for n, b in regions if n == "Normandie")
        # Le bloc Normandie ne doit pas inclure la section "## 4. Observations"
        assert "Observations" not in norm
        assert "Divergence" not in norm


# --- normalize_region ---


class TestNormalizeRegion:
    def test_id_format(self):
        rec = normalize_region("Bretagne", SAMPLE_REGION_BLOCK)
        assert rec["id"] == "apec_region:bretagne"
        assert rec["domain"] == "apec_region"
        assert rec["source"] == "apec_observatoire_emploi_cadre_2026"
        assert rec["region"] == "Bretagne"

    def test_bullets_preserved(self):
        rec = normalize_region("Bretagne", SAMPLE_REGION_BLOCK)
        assert "recrutements_2025" in rec["bullets"]
        assert "verbatim_délégué_olivier_maurin" in rec["bullets"]

    def test_text_includes_region_name(self):
        rec = normalize_region("Bretagne", SAMPLE_REGION_BLOCK)
        assert "Marché du travail cadres en Bretagne" in rec["text"]
        assert "panel APEC 2026" in rec["text"]

    def test_text_includes_top_fonctions(self):
        rec = normalize_region("Bretagne", SAMPLE_REGION_BLOCK)
        assert "Top 5 fonctions" in rec["text"]
        assert "Exploitation tertiaire 21 %" in rec["text"]

    def test_text_includes_verbatim(self):
        rec = normalize_region("Bretagne", SAMPLE_REGION_BLOCK)
        assert "Citation déléguée APEC" in rec["text"]
        assert "embellie" in rec["text"]

    def test_slug_unicode_handling(self):
        rec = normalize_region("Bourgogne-Franche-Comté", SAMPLE_REGION_BLOCK)
        assert rec["id"].startswith("apec_region:bourgogne")
        # Pas d'apostrophe ou de caractères bizarres
        assert "'" not in rec["id"]


# --- build_overview_record ---


def test_build_overview_record():
    rec = build_overview_record(SAMPLE_FULL_MD)
    assert rec["id"] == "apec_region:france-hexagonale"
    assert rec["region"] == "France hexagonale"
    assert "294 500 recrutements" in rec["text"]
    assert "+4 %" in rec["text"]


def test_build_overview_record_empty_when_missing():
    md_without_overview = "## 2. Fiches par région\n\n### 2.1 Bretagne\n"
    rec = build_overview_record(md_without_overview)
    # Construit malgré tout, mais avec bullets vides
    assert rec["bullets"] == {}


# --- build_observations_record ---


def test_build_observations_record():
    rec = build_observations_record(SAMPLE_FULL_MD)
    assert rec is not None
    assert rec["id"] == "apec_region:observations-cross-regions"
    assert "Observations cross-régions APEC 2026" in rec["text"]
    assert "Divergence" in rec["text"]


def test_build_observations_record_returns_none_when_missing():
    md_without_obs = "## 1. Vue\n- **x**: y\n## 2. Régions\n"
    assert build_observations_record(md_without_obs) is None


# --- build_corpus pipeline ---


class TestBuildCorpus:
    def test_full_pipeline(self):
        records = build_corpus(SAMPLE_FULL_MD)
        # 1 overview + 2 régions + 1 observations = 4
        assert len(records) == 4
        ids = [r["id"] for r in records]
        assert "apec_region:france-hexagonale" in ids
        assert "apec_region:bretagne" in ids
        assert "apec_region:normandie" in ids
        assert "apec_region:observations-cross-regions" in ids

    def test_all_records_share_domain(self):
        records = build_corpus(SAMPLE_FULL_MD)
        assert all(r["domain"] == "apec_region" for r in records)

    def test_all_records_have_text(self):
        records = build_corpus(SAMPLE_FULL_MD)
        assert all(r["text"] for r in records)


# --- save round-trip ---


def test_save_corpus_round_trip(tmp_path):
    records = [{"id": "apec_region:test", "domain": "apec_region", "text": "X"}]
    target = tmp_path / "corpus.json"
    save_corpus(records, path=target)
    loaded = json.loads(target.read_text(encoding="utf-8"))
    assert loaded == records


# --- build_region_text ---


def test_build_region_text_skips_missing_fields():
    bullets = {"recrutements_2025": "1 000"}
    text = build_region_text("X", bullets)
    assert "Recrutements 2025 : 1 000" in text
    assert "Prévision 2026" not in text  # absent dans bullets
