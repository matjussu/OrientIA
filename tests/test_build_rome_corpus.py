"""Tests src/collect/build_rome_corpus.py — Phase A.2 du plan corpus v5."""
from __future__ import annotations

import json
from pathlib import Path

from src.collect.build_rome_corpus import (
    build_corpus,
    build_text,
    load_rome_fiches,
    normalize_to_corpus,
    save_corpus,
    _extract_competences,
    _extract_savoirs,
)


# ─────────────── Fixtures ───────────────


def fiche_rome_complete() -> dict:
    """Fiche ROME 4.0 RAW typique (échantillon A1101 simplifié)."""
    return {
        "obsolete": False,
        "code": "A1101",
        "metier": {
            "code": "A1101",
            "libelle": "Conducteur / Conductrice d'engins agricoles",
        },
        "groupesCompetencesMobilisees": [
            {
                "enjeu": {"code": "15", "libelle": "Aménagement"},
                "competences": [
                    {"type": "COMPETENCE-DETAILLEE", "code": "1", "libelle": "Contrôler l'état d'une plantation"},
                    {"type": "COMPETENCE-DETAILLEE", "code": "2", "libelle": "Débroussailler une plantation"},
                ],
            },
            {
                "enjeu": {"code": "14", "libelle": "Production, Fabrication"},
                "competences": [
                    {"type": "MACRO-SAVOIR-FAIRE", "code": "3", "libelle": "Préparer du matériel"},
                    {"type": "COMPETENCE-DETAILLEE", "code": "4", "libelle": "Régler systèmes hydrauliques"},
                ],
            },
        ],
        "groupesSavoirs": [
            {
                "categorieSavoirs": {"code": "2", "libelle": "Domaines d'expertise"},
                "savoirs": [
                    {"type": "SAVOIR", "code": "1", "libelle": "Agronomie"},
                    {"type": "SAVOIR", "code": "2", "libelle": "Biologie végétale"},
                    {"type": "SAVOIR", "code": "3", "libelle": "Caractéristiques des écosystèmes"},
                ],
            },
        ],
    }


def fiche_rome_obsolete() -> dict:
    """Fiche obsolète — doit être filtrée par normalize_to_corpus."""
    return {
        "obsolete": True,
        "code": "X9999",
        "metier": {"code": "X9999", "libelle": "Métier obsolète"},
        "groupesCompetencesMobilisees": [],
        "groupesSavoirs": [],
    }


def fiche_rome_minimal() -> dict:
    """Fiche minimale (juste métier sans compétences ni savoirs)."""
    return {
        "obsolete": False,
        "code": "Z0000",
        "metier": {"code": "Z0000", "libelle": "Test métier minimal"},
        "groupesCompetencesMobilisees": [],
        "groupesSavoirs": [],
    }


def fiche_rome_malformed_metier() -> dict:
    """Fiche avec libellé métier vide → doit retourner None."""
    return {
        "obsolete": False,
        "code": "M0000",
        "metier": {"code": "M0000", "libelle": ""},
        "groupesCompetencesMobilisees": [],
        "groupesSavoirs": [],
    }


# ─────────────── _extract_competences ───────────────


class TestExtractCompetences:
    def test_extracts_enjeu_and_competences(self):
        fiche = fiche_rome_complete()
        result = _extract_competences(fiche["groupesCompetencesMobilisees"])
        assert len(result) == 2
        assert result[0]["enjeu"] == "Aménagement"
        assert "Contrôler l'état d'une plantation" in result[0]["competences"]

    def test_skips_empty_enjeu(self):
        groupes = [{"enjeu": {"libelle": ""}, "competences": []}]
        result = _extract_competences(groupes)
        assert result == []

    def test_skips_empty_competences(self):
        groupes = [{"enjeu": {"libelle": "Test"}, "competences": []}]
        result = _extract_competences(groupes)
        assert result == []

    def test_handles_none_input(self):
        assert _extract_competences(None) == []

    def test_handles_non_list_input(self):
        assert _extract_competences("not a list") == []


# ─────────────── _extract_savoirs ───────────────


class TestExtractSavoirs:
    def test_extracts_categorie_and_savoirs(self):
        fiche = fiche_rome_complete()
        result = _extract_savoirs(fiche["groupesSavoirs"])
        assert len(result) == 1
        assert result[0]["categorie"] == "Domaines d'expertise"
        assert "Agronomie" in result[0]["savoirs"]

    def test_handles_none(self):
        assert _extract_savoirs(None) == []


# ─────────────── normalize_to_corpus ───────────────


class TestNormalizeToCorpus:
    def test_complete_fiche_produces_record(self):
        record = normalize_to_corpus(fiche_rome_complete())
        assert record is not None
        assert record["id"] == "rome_metier:A1101"
        assert record["domain"] == "metier_detail"
        assert record["source"] == "rome_api_v4"
        assert record["code_rome"] == "A1101"
        assert record["libelle_metier"] == "Conducteur / Conductrice d'engins agricoles"
        assert record["obsolete"] is False
        assert len(record["competences_par_enjeu"]) == 2
        assert len(record["savoirs_par_categorie"]) == 1

    def test_obsolete_fiche_returns_none(self):
        assert normalize_to_corpus(fiche_rome_obsolete()) is None

    def test_malformed_metier_returns_none(self):
        assert normalize_to_corpus(fiche_rome_malformed_metier()) is None

    def test_minimal_fiche_still_produces_record(self):
        record = normalize_to_corpus(fiche_rome_minimal())
        assert record is not None
        assert record["competences_par_enjeu"] == []
        assert record["savoirs_par_categorie"] == []
        assert record["text"]  # text est non-vide même pour fiche minimale (libellé seul)

    def test_url_is_francetravail(self):
        record = normalize_to_corpus(fiche_rome_complete())
        assert record["url"] == "https://candidat.francetravail.fr/metierscope/fiche-metier/A1101"

    def test_provenance_tier_1_with_label(self):
        """ADR-055 : provenance.tier doit être tier_1 + label France Travail."""
        record = normalize_to_corpus(fiche_rome_complete())
        prov = record["provenance"]
        assert prov["tier"] == "tier_1"
        assert prov["source_label"] == "France Travail ROME 4.0"
        assert "francetravail" in prov["source_url"]

    def test_last_updated_added_when_provided(self):
        record = normalize_to_corpus(fiche_rome_complete(), last_updated="2026-04-23")
        assert record["provenance"]["last_updated"] == "2026-04-23"

    def test_last_updated_omitted_when_none(self):
        record = normalize_to_corpus(fiche_rome_complete(), last_updated=None)
        assert "last_updated" not in record["provenance"]

    def test_handles_non_dict_input(self):
        assert normalize_to_corpus("not a dict") is None
        assert normalize_to_corpus(None) is None
        assert normalize_to_corpus([]) is None


# ─────────────── build_text ───────────────


class TestBuildText:
    def test_includes_libelle_metier(self):
        text = build_text(normalize_to_corpus(fiche_rome_complete()))
        assert "Conducteur / Conductrice d'engins agricoles" in text
        assert "Métier ROME A1101" in text

    def test_includes_competences_par_enjeu(self):
        text = build_text(normalize_to_corpus(fiche_rome_complete()))
        assert "Aménagement" in text
        assert "Contrôler l'état d'une plantation" in text

    def test_includes_savoirs(self):
        text = build_text(normalize_to_corpus(fiche_rome_complete()))
        assert "Agronomie" in text

    def test_minimal_fiche_text_just_libelle(self):
        text = build_text(normalize_to_corpus(fiche_rome_minimal()))
        assert "Test métier minimal" in text


# ─────────────── build_corpus ───────────────


class TestBuildCorpus:
    def test_filters_obsolete(self):
        raw = [fiche_rome_complete(), fiche_rome_obsolete()]
        corpus = build_corpus(raw)
        assert len(corpus) == 1
        assert corpus[0]["code_rome"] == "A1101"

    def test_dedup_by_id(self):
        raw = [fiche_rome_complete(), fiche_rome_complete()]
        corpus = build_corpus(raw)
        assert len(corpus) == 1

    def test_sort_deterministic(self):
        """Idempotence : ordre stable par code ROME."""
        raw = [fiche_rome_minimal(), fiche_rome_complete()]  # Z0000 puis A1101
        corpus = build_corpus(raw)
        assert corpus[0]["code_rome"] == "A1101"  # tri lexicographique
        assert corpus[1]["code_rome"] == "Z0000"

    def test_empty_input_returns_empty(self):
        assert build_corpus([]) == []

    def test_propagates_last_updated(self):
        corpus = build_corpus([fiche_rome_complete()], last_updated="2026-04-23")
        assert corpus[0]["provenance"]["last_updated"] == "2026-04-23"


# ─────────────── load_rome_fiches + save_corpus (filesystem) ───────────────


class TestLoadAndSave:
    def test_load_from_directory(self, tmp_path):
        # Crée une fixture filesystem
        d = tmp_path / "fiches"
        d.mkdir()
        (d / "A1101.json").write_text(
            json.dumps(fiche_rome_complete()), encoding="utf-8"
        )
        (d / "Z0000.json").write_text(
            json.dumps(fiche_rome_minimal()), encoding="utf-8"
        )
        loaded = load_rome_fiches(d)
        assert len(loaded) == 2

    def test_load_handles_missing_dir(self, tmp_path):
        absent = tmp_path / "absent"
        assert load_rome_fiches(absent) == []

    def test_load_skips_malformed_json(self, tmp_path):
        d = tmp_path / "fiches"
        d.mkdir()
        (d / "broken.json").write_text("not valid json", encoding="utf-8")
        (d / "ok.json").write_text(
            json.dumps(fiche_rome_complete()), encoding="utf-8"
        )
        loaded = load_rome_fiches(d)
        assert len(loaded) == 1  # broken skipped

    def test_save_round_trip(self, tmp_path):
        out = tmp_path / "rome_corpus.json"
        corpus = build_corpus([fiche_rome_complete(), fiche_rome_minimal()])
        save_corpus(corpus, out)
        assert out.exists()
        reloaded = json.loads(out.read_text(encoding="utf-8"))
        assert len(reloaded) == 2
        assert reloaded[0]["code_rome"] == "A1101"

    def test_save_idempotent(self, tmp_path):
        """Rerun save_corpus produit le même bytes (déterministe)."""
        out = tmp_path / "rome_corpus.json"
        corpus = build_corpus([fiche_rome_complete()])
        save_corpus(corpus, out)
        bytes_1 = out.read_bytes()
        save_corpus(corpus, out)
        bytes_2 = out.read_bytes()
        assert bytes_1 == bytes_2


# ─────────────── Tests intégration FactCard (le record corpus passe-t-il proprement ?) ───────────────


class TestRomeCorpusFactCardCompat:
    """Vérifie que les records ROME corpus produisent une FactCard valide."""

    def test_fiche_to_fact_card_handles_rome_record(self):
        from src.rag.fact_card import fiche_to_fact_card
        record = normalize_to_corpus(fiche_rome_complete(), last_updated="2026-04-23")
        # Le merger v3 utilisera ces records comme fiches du corpus principal.
        # On vérifie que fiche_to_fact_card ne plante pas sur ce schema.
        card = fiche_to_fact_card(record, fact_id="S1")
        assert card.id == "S1"
        assert card.formation == "Conducteur / Conductrice d'engins agricoles"
        assert card.domain == "metier_detail"
        assert card.text_libre is not None  # populé depuis le champ `text`
        # Provenance tier_1 doit être inférée correctement
        assert card.provenance is not None
        assert card.provenance.tier == "tier_1"
        assert card.provenance.source_label == "France Travail ROME 4.0"

    def test_no_chiffres_for_rome_metier(self):
        """ROME 4.0 fiches métiers ne contiennent pas de chiffres
        (taux_acces, salaire, etc.) — le LLM doit voir tous null."""
        from src.rag.fact_card import fiche_to_fact_card, has_any_chiffres
        record = normalize_to_corpus(fiche_rome_complete())
        card = fiche_to_fact_card(record, fact_id="S1")
        assert not has_any_chiffres(card)
