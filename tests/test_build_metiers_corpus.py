"""Tests `src/collect/build_metiers_corpus.py` — corpus retrievable métiers."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.collect.build_metiers_corpus import (
    _format_list_libelles,
    _format_niveau,
    _join_libelles,
    build_corpus,
    build_text,
    normalize_to_corpus,
    save_corpus,
)


SAMPLE_RECORD = {
    "identifiant": "MET.7937",
    "nom_metier": "décorateur/trice sur verre",
    "libelle_feminin": "décoratrice sur verre",
    "libelle_masculin": "décorateur sur verre",
    "synonymes": ["verrier/ère décorateur/trice", "graveur sur verre"],
    "codes_rome_v3": ["B1302", "B1303"],
    "niveau_acces_min": {"id": "REF.413", "libelle": "CAP ou équivalent"},
    "formations_min_requise": [
        {"id": "FOR.5333", "libelle": "CAP arts et techniques du verre"},
        {"id": "FOR.2214", "libelle": "BMA verrier décorateur"},
    ],
    "statuts": [
        {"id": "T-ITM.9", "libelle": "salarié"},
        {"id": "T-ITM.2", "libelle": "artisan"},
    ],
    "centres_interet": [
        {"id": "T-IDEO2.4829", "libelle": "je rêve d'un métier artistique"},
        {"id": "T-IDEO2.4806", "libelle": "je veux travailler de mes mains"},
    ],
    "secteurs_activite": [{"id": "T-IDEO2.4830", "libelle": "Artisanat d'art"}],
    "metiers_associes": [],
    "accroche": "Crée et conçoit des motifs sur verre.",
    "format_court": "Description complète " * 100 + "fin.",  # ~2000 chars
    "nature_travail": "Travail manuel minutieux",
    "acces_metier_description": "",
    "condition_travail": "",
    "vie_professionnelle": "",
    "competences": "",
    "sources_numeriques": [
        {"url": "https://example.fr", "commentaire": "Source web"}
    ],
}


# --- Helpers ---


class TestJoinLibelles:
    def test_distinct_f_m(self):
        rec = {"libelle_feminin": "boulangère", "libelle_masculin": "boulanger"}
        assert _join_libelles(rec) == "boulangère / boulanger"

    def test_identical_only_one(self):
        rec = {"libelle_feminin": "x", "libelle_masculin": "x"}
        assert _join_libelles(rec) == "x"

    def test_only_f(self):
        rec = {"libelle_feminin": "salariée", "libelle_masculin": ""}
        assert _join_libelles(rec) == "salariée"

    def test_fallback_nom(self):
        rec = {"libelle_feminin": "", "libelle_masculin": "", "nom_metier": "test"}
        assert _join_libelles(rec) == "test"


class TestFormatNiveau:
    def test_present(self):
        assert _format_niveau({"id": "x", "libelle": "bac+5"}) == "bac+5"

    def test_none(self):
        assert _format_niveau(None) == ""

    def test_empty_libelle(self):
        assert _format_niveau({"id": "x", "libelle": ""}) == ""


class TestFormatListLibelles:
    def test_basic(self):
        items = [{"libelle": "a"}, {"libelle": "b"}, {"libelle": "c"}]
        assert _format_list_libelles(items) == "a, b, c"

    def test_limit(self):
        items = [{"libelle": str(i)} for i in range(10)]
        assert _format_list_libelles(items, limit=3) == "0, 1, 2"

    def test_skips_empty(self):
        items = [{"libelle": "a"}, {"libelle": ""}, {"libelle": "b"}]
        assert _format_list_libelles(items) == "a, b"

    def test_none(self):
        assert _format_list_libelles(None) == ""


# --- build_text ---


class TestBuildText:
    def test_full_record_includes_sections(self):
        text = build_text(SAMPLE_RECORD)
        assert "Métier : décorateur/trice sur verre" in text
        assert "Libellé : décoratrice sur verre / décorateur sur verre" in text
        assert "Synonymes : verrier/ère décorateur/trice" in text
        assert "Accroche : Crée et conçoit des motifs sur verre." in text
        assert "Description : Description complète" in text
        assert "Niveau d'accès minimum : CAP ou équivalent" in text
        assert "Formations minimales : CAP arts et techniques du verre" in text
        assert "Secteurs d'activité : Artisanat d'art" in text
        assert "Centres d'intérêt : je rêve d'un métier artistique" in text
        assert "Statuts : salarié, artisan" in text

    def test_truncates_long_format_court(self):
        rec = {**SAMPLE_RECORD, "format_court": "x " * 5000}
        text = build_text(rec)
        # Find the description section
        desc_pos = text.find("Description : ")
        # extract until next section delimiter
        desc = text[desc_pos:].split(" | ")[0]
        assert desc.endswith("…")
        assert len(desc) < 2100  # padding for the prefix

    def test_minimal_record(self):
        rec = {"nom_metier": "testeur", "identifiant": "MET.X"}
        text = build_text(rec)
        assert text == "Métier : testeur"

    def test_skips_missing_sections(self):
        rec = {"nom_metier": "x"}
        text = build_text(rec)
        assert "Niveau d'accès" not in text
        assert "Centres d'intérêt" not in text


# --- normalize_to_corpus ---


class TestNormalizeToCorpus:
    def test_id_format(self):
        c = normalize_to_corpus(SAMPLE_RECORD)
        assert c["id"] == "metier:MET.7937"
        assert c["domain"] == "metier"
        assert c["source"] == "onisep_ideo_fiches"

    def test_codes_rome_preserved(self):
        c = normalize_to_corpus(SAMPLE_RECORD)
        assert c["codes_rome"] == ["B1302", "B1303"]

    def test_secteurs_centres_extracted_as_strings(self):
        c = normalize_to_corpus(SAMPLE_RECORD)
        assert c["secteurs"] == ["Artisanat d'art"]
        assert "je veux travailler de mes mains" in c["centres_interet"]

    def test_statuts_extracted(self):
        c = normalize_to_corpus(SAMPLE_RECORD)
        assert set(c["statuts"]) == {"salarié", "artisan"}

    def test_text_field_populated(self):
        c = normalize_to_corpus(SAMPLE_RECORD)
        assert c["text"].startswith("Métier : ")
        assert "Description : " in c["text"]

    def test_id_fallback_when_no_identifiant(self):
        rec = {"nom_metier": "test", "identifiant": ""}
        c = normalize_to_corpus(rec)
        assert c["id"] == "metier:test"


# --- build_corpus ---


def test_build_corpus_dedupes_by_id():
    rec1 = {**SAMPLE_RECORD}
    rec2 = {**SAMPLE_RECORD, "nom_metier": "doublon"}  # same identifiant
    rec3 = {**SAMPLE_RECORD, "identifiant": "MET.999", "nom_metier": "autre"}
    out = build_corpus([rec1, rec2, rec3])
    assert len(out) == 2
    assert out[0]["nom"] == "décorateur/trice sur verre"
    assert out[1]["id"] == "metier:MET.999"


def test_build_corpus_preserves_order_for_first_seen():
    a = {**SAMPLE_RECORD, "identifiant": "MET.A", "nom_metier": "A"}
    b = {**SAMPLE_RECORD, "identifiant": "MET.B", "nom_metier": "B"}
    out = build_corpus([a, b])
    assert [c["nom"] for c in out] == ["A", "B"]


# --- save round-trip ---


def test_save_corpus_roundtrip(tmp_path):
    records = [normalize_to_corpus(SAMPLE_RECORD)]
    target = tmp_path / "corpus.json"
    save_corpus(records, path=target)
    loaded = json.loads(target.read_text(encoding="utf-8"))
    assert loaded == records
    assert loaded[0]["domain"] == "metier"
