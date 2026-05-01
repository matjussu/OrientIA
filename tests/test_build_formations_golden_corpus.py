"""Tests Sprint 12 axe 2 — corpus combined assembly Golden Pipeline.

Couvre :

- ``scripts/build_formations_golden_corpus.py`` : load + annotate + build + write + main
- ``src/rag/embeddings.corpus_item_to_text`` : routing des 3 corpora + fallback

Plan : ``docs/GOLDEN_PIPELINE_PLAN.md`` étape 1.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.build_formations_golden_corpus import (
    CORPUS_LABELS,
    annotate_corpus,
    build_combined,
    load_corpus,
    main,
    write_combined,
)
from src.rag.embeddings import corpus_item_to_text


# ---- Fixtures ---------------------------------------------------------------


@pytest.fixture
def formations_unified_sample() -> list[dict]:
    """Sample minimal mais représentatif de formations_unified (Sprint 12 D1)."""
    return [
        {
            "id": "psup:42",
            "source": "parcoursup",
            "nom": "Bachelor Cybersécurité",
            "etablissement": "Lycée Test",
            "ville": "Nîmes",
            "type_diplome": "formation d'école spécialisée",
            "niveau": "bac+3",
            "domaine": "cyber",
            "profil_admis": {
                "mentions_pct": {"tb": 10.0, "b": 25.0, "ab": 40.0, "sans": 25.0},
                "bac_type_pct": {"general": 60.0, "techno": 30.0, "pro": 10.0},
                "acces_pct": {"general": 73.0, "techno": 27.0, "pro": 0.0},
                "boursiers_pct": 0.0,
                "femmes_pct": 0.0,
                "neobacheliers_pct": 0.0,
                "origine_academique_idf_pct": 0.0,
            },
        },
        {
            "id": "psup:43",
            "source": "parcoursup",
            "nom": "BTS SIO",
            "etablissement": "Lycée X",
            "ville": "Paris",
            "type_diplome": "BTS",
            "niveau": "bac+2",
            "domaine": "info",
        },
    ]


@pytest.fixture
def dares_sample() -> list[dict]:
    """Sample minimal DARES (champ ``text`` préformaté présent)."""
    return [
        {
            "id": "dares_fap:A0Z",
            "domain": "metier_prospective",
            "source": "dares_metiers_2030",
            "granularity": "fap",
            "code_fap": "A0Z",
            "fap_libelle": "Agriculteurs",
            "text": "Métier 2030 (DARES) — FAP A0Z : Agriculteurs | Effectifs 2019 : 431 659",
        },
        {
            "id": "dares_fap:J5Z",
            "domain": "metier_prospective",
            "source": "dares_metiers_2030",
            "granularity": "fap",
            "code_fap": "J5Z",
            "fap_libelle": "Agents administratifs",
            "text": "Métier 2030 (DARES) — FAP J5Z : Agents administratifs",
        },
    ]


@pytest.fixture
def rncp_blocs_sample() -> list[dict]:
    """Sample minimal RNCP (champ ``text`` préformaté présent)."""
    return [
        {
            "id": "rncp_blocs:RNCP35185",
            "domain": "competences_certif",
            "source": "rncp_blocs",
            "numero_fiche": "RNCP35185",
            "intitule": "Technicien conseil vente alimentation",
            "niveau": "bac",
            "text": "Compétences (RNCP35185) — Technicien conseil vente | Niveau européen 4 | Bloc 1: Communiquer…",
        },
    ]


# ---- TestLoadCorpus ---------------------------------------------------------


class TestLoadCorpus:
    def test_loads_list_of_dicts(self, tmp_path: Path):
        data = [{"id": "x", "value": 1}]
        path = tmp_path / "corpus.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        assert load_corpus(path) == data

    def test_raises_on_missing_file(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            load_corpus(tmp_path / "absent.json")

    def test_raises_on_non_list_payload(self, tmp_path: Path):
        path = tmp_path / "dict.json"
        path.write_text(json.dumps({"top": "level"}), encoding="utf-8")
        with pytest.raises(ValueError, match="liste JSON"):
            load_corpus(path)

    def test_handles_utf8_special_chars(self, tmp_path: Path):
        path = tmp_path / "utf8.json"
        path.write_text(
            json.dumps([{"text": "Métiers — éleveurs (Île-de-France)"}], ensure_ascii=False),
            encoding="utf-8",
        )
        result = load_corpus(path)
        assert result[0]["text"] == "Métiers — éleveurs (Île-de-France)"

    def test_empty_list_is_valid(self, tmp_path: Path):
        path = tmp_path / "empty.json"
        path.write_text("[]", encoding="utf-8")
        assert load_corpus(path) == []


# ---- TestAnnotateCorpus -----------------------------------------------------


class TestAnnotateCorpus:
    def test_adds_corpus_field(self, dares_sample):
        result = annotate_corpus(dares_sample, "dares")
        assert all(item["corpus"] == "dares" for item in result)
        assert len(result) == len(dares_sample)

    def test_does_not_mutate_input(self, dares_sample):
        original = json.loads(json.dumps(dares_sample))  # deep copy
        annotate_corpus(dares_sample, "dares")
        assert dares_sample == original

    def test_idempotent_when_label_matches(self, dares_sample):
        once = annotate_corpus(dares_sample, "dares")
        twice = annotate_corpus(once, "dares")
        assert once == twice

    def test_raises_on_label_collision(self, dares_sample):
        annotated = annotate_corpus(dares_sample, "dares")
        with pytest.raises(ValueError, match="déjà corpus"):
            annotate_corpus(annotated, "rncp_blocs")

    def test_raises_on_unsupported_label(self, dares_sample):
        with pytest.raises(ValueError, match="non supporté"):
            annotate_corpus(dares_sample, "wat")

    def test_preserves_existing_source_field(self, dares_sample):
        result = annotate_corpus(dares_sample, "dares")
        assert result[0]["source"] == "dares_metiers_2030"  # granulaire intacte


# ---- TestBuildCombined ------------------------------------------------------


class TestBuildCombined:
    def test_combines_three_corpora_with_correct_breakdown(
        self, formations_unified_sample, dares_sample, rncp_blocs_sample
    ):
        combined = build_combined(formations_unified_sample, dares_sample, rncp_blocs_sample)
        assert len(combined) == 2 + 2 + 1
        breakdown = {label: sum(1 for it in combined if it["corpus"] == label) for label in CORPUS_LABELS}
        assert breakdown == {"formations_unified": 2, "dares": 2, "rncp_blocs": 1}

    def test_order_preserved(self, formations_unified_sample, dares_sample, rncp_blocs_sample):
        combined = build_combined(formations_unified_sample, dares_sample, rncp_blocs_sample)
        # formations_unified d'abord (ordre du plan)
        assert combined[0]["corpus"] == "formations_unified"
        assert combined[2]["corpus"] == "dares"
        assert combined[-1]["corpus"] == "rncp_blocs"

    def test_handles_empty_corpora(self, formations_unified_sample):
        combined = build_combined(formations_unified_sample, [], [])
        assert len(combined) == len(formations_unified_sample)
        assert all(it["corpus"] == "formations_unified" for it in combined)


# ---- TestWriteCombined ------------------------------------------------------


class TestWriteCombined:
    def test_writes_valid_json_utf8(self, tmp_path: Path):
        items = [{"id": "a", "text": "Métier — éleveur"}]
        out = tmp_path / "deep" / "out.json"
        write_combined(items, out)
        assert out.exists()
        reloaded = json.loads(out.read_text(encoding="utf-8"))
        assert reloaded == items
        # Caractères français préservés (ensure_ascii=False)
        assert "—" in out.read_text(encoding="utf-8")

    def test_creates_parent_dir(self, tmp_path: Path):
        out = tmp_path / "a" / "b" / "c.json"
        write_combined([], out)
        assert out.parent.exists()


# ---- TestMainSmoke ----------------------------------------------------------


class TestMainSmoke:
    def test_end_to_end_via_argv(
        self, tmp_path: Path, formations_unified_sample, dares_sample, rncp_blocs_sample
    ):
        fu_path = tmp_path / "fu.json"
        dares_path = tmp_path / "dares.json"
        rncp_path = tmp_path / "rncp.json"
        out_path = tmp_path / "combined.json"
        fu_path.write_text(json.dumps(formations_unified_sample), encoding="utf-8")
        dares_path.write_text(json.dumps(dares_sample), encoding="utf-8")
        rncp_path.write_text(json.dumps(rncp_blocs_sample), encoding="utf-8")

        rc = main([
            "--formations-unified", str(fu_path),
            "--dares", str(dares_path),
            "--rncp-blocs", str(rncp_path),
            "--out", str(out_path),
        ])
        assert rc == 0
        assert out_path.exists()
        combined = json.loads(out_path.read_text(encoding="utf-8"))
        assert len(combined) == 5
        assert {it["corpus"] for it in combined} == set(CORPUS_LABELS)


# ---- TestCorpusItemToText ---------------------------------------------------


class TestCorpusItemToText:
    def test_routes_dares_to_preformatted_text(self, dares_sample):
        item = annotate_corpus(dares_sample, "dares")[0]
        assert corpus_item_to_text(item) == item["text"]

    def test_routes_rncp_blocs_to_preformatted_text(self, rncp_blocs_sample):
        item = annotate_corpus(rncp_blocs_sample, "rncp_blocs")[0]
        assert corpus_item_to_text(item) == item["text"]

    def test_routes_formations_unified_to_fiche_to_text(self, formations_unified_sample):
        item = annotate_corpus(formations_unified_sample, "formations_unified")[0]
        text = corpus_item_to_text(item)
        # fiche_to_text() construit un format "Formation : … | Établissement : … | …"
        assert "Bachelor Cybersécurité" in text
        assert "Lycée Test" in text
        assert " | " in text  # Format fiche_to_text join séparateur

    def test_falls_back_to_fiche_to_text_when_corpus_missing(self, formations_unified_sample):
        # Backward compat : items legacy formations_unified.index sans champ ``corpus``
        item = formations_unified_sample[0]
        assert "corpus" not in item
        text = corpus_item_to_text(item)
        assert "Bachelor Cybersécurité" in text

    def test_dares_without_text_raises(self):
        broken = {"corpus": "dares", "id": "dares_x", "text": ""}
        with pytest.raises(ValueError, match="préformaté"):
            corpus_item_to_text(broken)

    def test_rncp_without_text_raises(self):
        broken = {"corpus": "rncp_blocs", "id": "rncp_x"}
        with pytest.raises(ValueError, match="préformaté"):
            corpus_item_to_text(broken)
