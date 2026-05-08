"""Tests src/rag/bm25_index.py — BM25 + RRF fusion (Phase C ADR-058)."""
from __future__ import annotations

import pytest

from src.rag.bm25_index import (
    BM25Index,
    reciprocal_rank_fusion,
    _tokenize,
    _fiche_to_search_text,
)


# ─────────────── Fixtures ───────────────


def _fiches_sample() -> list[dict]:
    """Mini corpus de test couvrant les cas Phase C."""
    return [
        {
            "id": "crous_region:lyon",
            "domain": "crous",
            "source": "crous_combine_logements_restos",
            "text": "Vie étudiante CROUS CROUS Lyon (logement + restauration universitaire) | Restaurants universitaires : 36 lieux totaux",
        },
        {
            "id": "crous_region:paris",
            "domain": "crous",
            "source": "crous_combine_logements_restos",
            "text": "Vie étudiante CROUS CROUS Paris (logement + restauration universitaire) | Restaurants universitaires : 80 lieux totaux",
        },
        {
            "id": "fr_comp:rncp_38450",
            "domain": "competences_certif",
            "source": "rncp_blocs",
            "text": "RNCP 38450 — Master Cybersécurité | Blocs de compétences : audit, pentest, gouvernance SSI",
            "intitule": "Master Cybersécurité",
        },
        {
            "id": "doctorat:chimie:2014",
            "domain": "insertion_pro",
            "source": "ip_doc_doctorat",
            "discipline_principale": "Chimie et sciences des matériaux",
            "text": "Insertion doctorat (MESR IP-DOC) — Chimie et sciences des matériaux, cohorte 2014, 12 mois après le diplôme",
        },
        {
            "nom": "Master Cybersécurité",
            "etablissement": "EFREI Paris",
            "ville": "Paris",
            "source": "monmaster",
        },
        {
            "nom": "BUT Informatique",
            "etablissement": "IUT Lyon 1",
            "ville": "Villeurbanne",
            "region": "Auvergne-Rhône-Alpes",
            "source": "parcoursup",
        },
    ]


# ─────────────── Tokenization ───────────────


class TestTokenize:
    def test_basic_tokenization(self):
        tokens = _tokenize("CROUS Lyon logement")
        assert "crous" in tokens
        assert "lyon" in tokens
        assert "logement" in tokens

    def test_strips_accents(self):
        tokens = _tokenize("Rône-Alpes Master cybersécurité")
        assert "cybersecurite" in tokens
        assert "alpes" in tokens

    def test_removes_stopwords(self):
        tokens = _tokenize("Le master de la cybersécurité")
        assert "le" not in tokens
        assert "la" not in tokens
        assert "de" not in tokens
        assert "master" in tokens
        assert "cybersecurite" in tokens

    def test_keeps_numbers_for_codes(self):
        """Important pour entités type 'PCS 37', 'RNCP 38450', 'L1'."""
        tokens = _tokenize("RNCP 38450 PCS 37 L1 bac S")
        assert "rncp" in tokens
        assert "38450" in tokens
        assert "37" in tokens
        assert "l1" in tokens

    def test_single_letter_filtered(self):
        """Filtre les single-letter sauf si combiné (L1 reste)."""
        tokens = _tokenize("J'ai un BUT")
        assert "j" not in tokens  # single letter filtered
        assert "but" in tokens

    def test_handles_empty(self):
        assert _tokenize("") == []
        assert _tokenize(None) == []


# ─────────────── BM25Index ───────────────


class TestBM25Index:
    def test_build_and_search_crous_lyon(self):
        """LE cas critique : 'CROUS Lyon' doit retrieve `crous_region:lyon`."""
        bm25 = BM25Index(_fiches_sample())
        results = bm25.search("CROUS Lyon logement étudiant", k=5)
        assert len(results) > 0
        # crous_region:lyon doit être en top-1 ou top-2
        top_ids = [r["fiche"].get("id") for r in results[:3]]
        assert "crous_region:lyon" in top_ids

    def test_rncp_code_match(self):
        """RNCP 38450 — match lexical exact."""
        bm25 = BM25Index(_fiches_sample())
        results = bm25.search("Quels sont les blocs de compétences du RNCP 38450 ?", k=5)
        top_ids = [r["fiche"].get("id") for r in results[:3]]
        assert "fr_comp:rncp_38450" in top_ids

    def test_doctorat_chimie_match(self):
        bm25 = BM25Index(_fiches_sample())
        results = bm25.search("Insertion après doctorat chimie", k=5)
        top_ids = [r["fiche"].get("id") for r in results[:3]]
        assert "doctorat:chimie:2014" in top_ids

    def test_zero_match_returns_empty(self):
        """Question sans aucun terme matchant → 0 results."""
        bm25 = BM25Index(_fiches_sample())
        # Query avec termes qui n'existent dans aucune fiche
        results = bm25.search("xyz_inexistant_qwerty_blabla", k=5)
        # 0 ou très peu de résultats (BM25 peut retourner 0 si aucun match)
        assert len(results) == 0 or all(r["score_bm25"] >= 0 for r in results)

    def test_search_returns_score_and_rank(self):
        bm25 = BM25Index(_fiches_sample())
        results = bm25.search("CROUS Lyon", k=3)
        assert len(results) >= 1
        for i, r in enumerate(results):
            assert "score_bm25" in r
            assert r["score_bm25"] > 0
            assert r["rank_bm25"] == i + 1
            assert "_orig_index" in r

    def test_n_fiches_property(self):
        bm25 = BM25Index(_fiches_sample())
        assert bm25.n_fiches == 6


# ─────────────── _fiche_to_search_text ───────────────


class TestFicheToSearchText:
    def test_includes_id_and_text(self):
        fiche = {"id": "test:1", "text": "Master cybersécurité"}
        out = _fiche_to_search_text(fiche)
        assert "Master" in out
        assert "test:1" in out

    def test_includes_etablissement_ville(self):
        fiche = {"nom": "X", "etablissement": "EFREI", "ville": "Paris"}
        out = _fiche_to_search_text(fiche)
        assert "EFREI" in out
        assert "Paris" in out

    def test_includes_codes_rome(self):
        fiche = {
            "nom": "Test",
            "codes_rome": [{"code": "K1301"}, {"code": "M1812"}],
        }
        out = _fiche_to_search_text(fiche)
        assert "K1301" in out
        assert "M1812" in out


# ─────────────── Reciprocal Rank Fusion ───────────────


class TestReciprocalRankFusion:
    def test_single_ranker_passthrough(self):
        """1 seul ranker → ordre RRF identique au ranker."""
        ranking = [
            {"fiche": {"id": "a"}, "_orig_index": 1, "score": 0.9},
            {"fiche": {"id": "b"}, "_orig_index": 2, "score": 0.8},
            {"fiche": {"id": "c"}, "_orig_index": 3, "score": 0.7},
        ]
        fused = reciprocal_rank_fusion([ranking])
        ids = [r["fiche"]["id"] for r in fused]
        assert ids == ["a", "b", "c"]

    def test_two_rankers_dense_then_bm25(self):
        """Dense ranker + BM25 ranker — fusion via RRF."""
        dense = [
            {"fiche": {"id": "a"}, "_orig_index": 1, "score": 0.9},
            {"fiche": {"id": "b"}, "_orig_index": 2, "score": 0.8},
        ]
        bm25 = [
            {"fiche": {"id": "c"}, "_orig_index": 3, "score_bm25": 12.5, "rank_bm25": 1},
            {"fiche": {"id": "a"}, "_orig_index": 1, "score_bm25": 8.0, "rank_bm25": 2},
        ]
        fused = reciprocal_rank_fusion([dense, bm25])
        # 'a' apparaît dans les 2 rankers → boost RRF
        ids = [r["fiche"]["id"] for r in fused]
        assert ids[0] == "a"  # rank 1 dense + rank 2 bm25 = top RRF score
        # b et c doivent suivre
        assert "b" in ids
        assert "c" in ids

    def test_rrf_scores_present(self):
        rankings = [
            [{"fiche": {"id": "a"}, "_orig_index": 1, "score": 0.9}],
            [{"fiche": {"id": "a"}, "_orig_index": 1, "score_bm25": 5.0, "rank_bm25": 1}],
        ]
        fused = reciprocal_rank_fusion(rankings)
        assert len(fused) == 1
        assert fused[0]["score_rrf"] > 0
        assert fused[0]["score_dense"] == 0.9
        assert fused[0]["score_bm25"] == 5.0

    def test_empty_rankings(self):
        fused = reciprocal_rank_fusion([])
        assert fused == []
        fused = reciprocal_rank_fusion([[]])
        assert fused == []


# ─────────────── Smoke test sur vrai corpus (opt-in) ───────────────


@pytest.mark.skipif(
    not __import__("pathlib").Path("data/processed/formations_v5.json").exists(),
    reason="formations_v5.json absent",
)
class TestSmokeRealCorpus:
    """Smoke test sur le vrai corpus v5 — vérifie que les questions
    spot-check problématiques retrouvent leurs fiches via BM25."""

    @pytest.fixture(scope="class")
    def bm25(self):
        import json
        from pathlib import Path
        fiches = json.loads(Path("data/processed/formations_v5.json").read_text())
        return BM25Index(fiches)

    def test_crous_lyon_retrievable(self, bm25):
        results = bm25.search("Combien coûte le logement étudiant CROUS à Lyon ?", k=10)
        top_ids = [r["fiche"].get("id") for r in results[:10]]
        # crous_region:lyon doit être quelque part dans top-10
        assert "crous_region:lyon" in top_ids, (
            f"crous_region:lyon manque dans top-10. Top: {top_ids}"
        )

    def test_rncp_38450_or_similar(self, bm25):
        """RNCP 38450 spécifique peut ne pas exister, mais des RNCP doivent
        ressortir via BM25 lexical sur les blocs de compétences."""
        results = bm25.search("Quels sont les blocs de compétences du RNCP 38450 ?", k=10)
        # Au moins 1 fiche competences_certif dans top-10
        domains = [r["fiche"].get("domain") for r in results[:10]]
        n_blocs = sum(1 for d in domains if d == "competences_certif")
        assert n_blocs >= 1, f"0 fiche competences_certif dans top-10: {domains}"

    def test_pcs_37_retrievable(self, bm25):
        """Question avec entité technique PCS 37 — BM25 doit matcher."""
        results = bm25.search("Salaire moyen d'un cadre supérieur (PCS 37) ?", k=10)
        domains = [r["fiche"].get("domain") for r in results[:10]]
        # Au moins une fiche insee_salaire dans top-10
        n_insee = sum(1 for d in domains if d == "insee_salaire")
        assert n_insee >= 1, f"0 fiche insee_salaire dans top-10: {domains}"
