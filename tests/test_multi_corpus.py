"""Tests `src/rag/multi_corpus.py` — loader unifié pour les 4 corpus."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.rag.multi_corpus import (
    DEFAULT_CORPUS_PATHS,
    Corpus,
    MultiCorpusLoader,
    _extract_text,
    extract_texts_for_embedding,
    merge_for_embedding,
)


# --- Fixtures ---


@pytest.fixture
def fake_paths(tmp_path):
    """Crée des fichiers corpus minimaux pour 4 domains."""
    paths: dict[str, Path] = {}

    formations = [
        {"nom": "Licence Math", "domaine": "Sciences"},
        {"nom": "Licence Droit", "domaine": "Droit"},
    ]
    metiers = [
        {
            "id": "metier:MET.1",
            "domain": "metier",
            "nom": "ingénieur math",
            "text": "Métier : ingénieur mathématicien",
        },
        {
            "id": "metier:MET.2",
            "domain": "metier",
            "nom": "actuaire",
            "text": "Métier : actuaire",
        },
    ]
    parcours = [
        {
            "id": "parcours:droit_bac_l_bien",
            "domain": "parcours_bacheliers",
            "text": "Parcours licence en droit",
        }
    ]
    apec = [
        {
            "id": "apec_region:bretagne",
            "domain": "apec_region",
            "text": "Marché du travail cadres en Bretagne",
        }
    ]

    for name, data in (
        ("formations.json", formations),
        ("metiers_corpus.json", metiers),
        ("parcours_bacheliers_corpus.json", parcours),
        ("apec_regions_corpus.json", apec),
    ):
        target = tmp_path / name
        target.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    paths["formation"] = tmp_path / "formations.json"
    paths["metier"] = tmp_path / "metiers_corpus.json"
    paths["parcours_bacheliers"] = tmp_path / "parcours_bacheliers_corpus.json"
    paths["apec_region"] = tmp_path / "apec_regions_corpus.json"
    return paths


# --- Corpus dataclass ---


class TestCorpusDataclass:
    def test_len(self):
        c = Corpus(domain="x", path=Path("/x"), records=[1, 2, 3])
        assert len(c) == 3

    def test_is_empty(self):
        assert Corpus(domain="x", path=Path("/x"), records=[]).is_empty is True
        assert Corpus(domain="x", path=Path("/x"), records=[1]).is_empty is False


# --- _extract_text ---


class TestExtractText:
    def test_formation_uses_nom(self):
        rec = {"nom": "Licence Math", "domaine": "Sciences"}
        assert _extract_text(rec, "formation") == "Licence Math"

    def test_metier_uses_text(self):
        rec = {"text": "Métier : X", "nom": "X"}
        assert _extract_text(rec, "metier") == "Métier : X"

    def test_parcours_uses_text(self):
        rec = {"text": "Parcours en droit"}
        assert _extract_text(rec, "parcours_bacheliers") == "Parcours en droit"

    def test_apec_uses_text(self):
        rec = {"text": "Marché du travail cadres en Bretagne"}
        assert (
            _extract_text(rec, "apec_region")
            == "Marché du travail cadres en Bretagne"
        )

    def test_missing_field_returns_empty(self):
        assert _extract_text({}, "metier") == ""


# --- MultiCorpusLoader ---


class TestMultiCorpusLoader:
    def test_load_all_returns_4_corpora(self, fake_paths):
        loader = MultiCorpusLoader(paths=fake_paths)
        corpora = loader.load_all()
        assert set(corpora.keys()) == {"formation", "metier", "parcours_bacheliers", "apec_region"}

    def test_load_all_counts(self, fake_paths):
        loader = MultiCorpusLoader(paths=fake_paths)
        loader.load_all()
        counts = loader.count_by_domain()
        assert counts["formation"] == 2
        assert counts["metier"] == 2
        assert counts["parcours_bacheliers"] == 1
        assert counts["apec_region"] == 1

    def test_load_all_total(self, fake_paths):
        loader = MultiCorpusLoader(paths=fake_paths)
        loader.load_all()
        assert loader.total() == 6

    def test_load_one_specific_domain(self, fake_paths):
        loader = MultiCorpusLoader(paths=fake_paths)
        c = loader.load_one("metier")
        assert len(c) == 2
        assert c.domain == "metier"

    def test_missing_file_creates_empty_corpus(self, tmp_path):
        paths = {"metier": tmp_path / "missing.json"}
        loader = MultiCorpusLoader(paths=paths)
        c = loader.load_one("metier")
        assert c.is_empty
        assert len(c) == 0
        # Pas de raise — graceful

    def test_invalid_json_creates_empty_corpus(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{not valid json", encoding="utf-8")
        loader = MultiCorpusLoader(paths={"x": bad})
        c = loader.load_one("x")
        assert c.is_empty

    def test_non_list_payload_creates_empty(self, tmp_path):
        bad = tmp_path / "obj.json"
        bad.write_text(json.dumps({"key": "val"}), encoding="utf-8")
        loader = MultiCorpusLoader(paths={"x": bad})
        c = loader.load_one("x")
        assert c.is_empty

    def test_unknown_domain_raises(self):
        loader = MultiCorpusLoader(paths={})
        with pytest.raises(KeyError):
            loader.load_one("inconnu")

    def test_get_lazy_loads(self, fake_paths):
        loader = MultiCorpusLoader(paths=fake_paths)
        # Pas de load_all préalable
        c = loader.get("metier")
        assert len(c) == 2
        # 2e get : pas de re-load (cache via dict)
        assert id(loader.get("metier")) == id(c)

    def test_summary_string(self, fake_paths):
        loader = MultiCorpusLoader(paths=fake_paths)
        loader.load_all()
        s = loader.summary()
        assert "formation" in s
        assert "metier" in s
        assert "TOTAL" in s
        assert "6" in s


# --- extract_texts_for_embedding ---


class TestExtractTextsForEmbedding:
    def test_metier_corpus(self, fake_paths):
        loader = MultiCorpusLoader(paths=fake_paths)
        c = loader.load_one("metier")
        texts = extract_texts_for_embedding(c)
        assert len(texts) == 2
        assert texts[0] == ("metier:MET.1", "Métier : ingénieur mathématicien")

    def test_formation_corpus_uses_nom(self, fake_paths):
        loader = MultiCorpusLoader(paths=fake_paths)
        c = loader.load_one("formation")
        texts = extract_texts_for_embedding(c)
        # formations.json sans `id`, idx-based fallback
        assert len(texts) == 2
        assert texts[0][1] == "Licence Math"

    def test_skip_empty(self, fake_paths):
        loader = MultiCorpusLoader(paths=fake_paths)
        c = loader.load_one("metier")
        c.records[0]["text"] = ""  # vide simulé
        texts = extract_texts_for_embedding(c, skip_empty=True)
        assert len(texts) == 1

    def test_skip_empty_off_includes_all(self, fake_paths):
        loader = MultiCorpusLoader(paths=fake_paths)
        c = loader.load_one("metier")
        c.records[0]["text"] = ""
        texts = extract_texts_for_embedding(c, skip_empty=False)
        assert len(texts) == 2


# --- merge_for_embedding ---


class TestMergeForEmbedding:
    def test_merges_all_corpora(self, fake_paths):
        loader = MultiCorpusLoader(paths=fake_paths)
        loader.load_all()
        merged = merge_for_embedding(loader.corpora.values())
        # 6 records au total avec text non-vide
        assert len(merged) == 6
        domains = {r["domain"] for r in merged}
        assert domains == {"formation", "metier", "parcours_bacheliers", "apec_region"}

    def test_filters_by_domain(self, fake_paths):
        loader = MultiCorpusLoader(paths=fake_paths)
        loader.load_all()
        merged = merge_for_embedding(
            loader.corpora.values(), domains={"metier", "apec_region"}
        )
        assert all(r["domain"] in {"metier", "apec_region"} for r in merged)
        assert len(merged) == 3

    def test_preserves_original_record(self, fake_paths):
        loader = MultiCorpusLoader(paths=fake_paths)
        loader.load_all()
        merged = merge_for_embedding(loader.corpora.values(), domains={"metier"})
        assert merged[0]["original_record"]["nom"] == "ingénieur math"

    def test_skip_empty_text(self, tmp_path):
        # corpus avec text vide doit être skipped
        bad = tmp_path / "x.json"
        bad.write_text(
            json.dumps([{"id": "x:1", "text": ""}, {"id": "x:2", "text": "ok"}]),
            encoding="utf-8",
        )
        loader = MultiCorpusLoader(paths={"x": bad})
        c = loader.load_one("x")
        merged = merge_for_embedding([c])
        assert len(merged) == 1
        assert merged[0]["id"] == "x:2"


# --- DEFAULT_CORPUS_PATHS sanity ---


def test_default_paths_cover_all_domains():
    assert set(DEFAULT_CORPUS_PATHS.keys()) == {
        "formation",
        "metier",
        "parcours_bacheliers",
        "apec_region",
    }
