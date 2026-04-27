"""Tests `src/collect/build_corrections_factuelles_corpus.py`."""
from __future__ import annotations

import json

import pytest

from src.collect.build_corrections_factuelles_corpus import (
    aggregate_corrections,
    build_corpus,
    load_raw,
    save_corpus,
)


@pytest.fixture
def corrections_raw_sample() -> dict:
    return {
        "version": "test",
        "corrections": [
            {
                "id": "test_correction_1",
                "subject": "Test subject 1",
                "erreur_persistante": "Erreur observée",
                "correction_authoritative": "Information correcte avec fourchette ~10000€",
                "public_cible": "Lycéens test",
                "source_officielle": "https://example-officiel.gouv.fr",
                "ref_user_test": "user_test_v3 Qtest",
            },
            {
                "id": "test_correction_2",
                "subject": "Test subject 2 minimal",
                "correction_authoritative": "Info correcte minimale",
                "source_officielle": "https://other-officiel.fr",
            },
        ],
    }


class TestAggregateCorrections:
    def test_one_cell_per_correction(self, corrections_raw_sample):
        out = aggregate_corrections(corrections_raw_sample)
        assert len(out) == 2

    def test_id_format(self, corrections_raw_sample):
        out = aggregate_corrections(corrections_raw_sample)
        ids = {c["id"] for c in out}
        assert "correction:test_correction_1" in ids
        assert "correction:test_correction_2" in ids

    def test_domain_correction_factuelle(self, corrections_raw_sample):
        out = aggregate_corrections(corrections_raw_sample)
        assert all(c["domain"] == "correction_factuelle" for c in out)

    def test_text_includes_subject_and_correction(self, corrections_raw_sample):
        out = aggregate_corrections(corrections_raw_sample)
        c1 = next(c for c in out if c["id"] == "correction:test_correction_1")
        assert "Test subject 1" in c1["text"]
        assert "Information correcte" in c1["text"]
        assert "fourchette ~10000€" in c1["text"]

    def test_text_includes_source_officielle(self, corrections_raw_sample):
        out = aggregate_corrections(corrections_raw_sample)
        c1 = next(c for c in out if c["id"] == "correction:test_correction_1")
        assert "Source officielle" in c1["text"]
        assert "example-officiel.gouv.fr" in c1["text"]

    def test_text_includes_priority_note(self, corrections_raw_sample):
        out = aggregate_corrections(corrections_raw_sample)
        for c in out:
            assert "prioritaire" in c["text"]

    def test_handles_minimal_correction(self, corrections_raw_sample):
        """Correction sans tous les champs optionnels → ne crash pas."""
        out = aggregate_corrections(corrections_raw_sample)
        c2 = next(c for c in out if c["id"] == "correction:test_correction_2")
        assert "Test subject 2 minimal" in c2["text"]
        assert "Info correcte minimale" in c2["text"]


class TestBuildCorpus:
    def test_build_returns_list_of_dicts(self, corrections_raw_sample):
        out = build_corpus(corrections_raw_sample)
        assert isinstance(out, list)
        assert all(isinstance(c, dict) for c in out)

    def test_build_count_matches_raw(self, corrections_raw_sample):
        out = build_corpus(corrections_raw_sample)
        assert len(out) == len(corrections_raw_sample["corrections"])


class TestSaveCorpus:
    def test_save_round_trip(self, tmp_path, corrections_raw_sample):
        corpus = build_corpus(corrections_raw_sample)
        target = tmp_path / "out.json"
        save_corpus(corpus, path=target)
        loaded = json.loads(target.read_text(encoding="utf-8"))
        assert len(loaded) == len(corpus)
        for orig, new in zip(corpus, loaded):
            assert new["id"] == orig["id"]
            assert new["text"] == orig["text"]


class TestRealRawFile:
    """Smoke test : le vrai JSON raw sprint8_w1 charge correctement."""

    def test_real_file_loads(self):
        raw = load_raw()
        assert "corrections" in raw
        assert len(raw["corrections"]) >= 5  # 5 erreurs persistantes Sprint 8 W1

    def test_real_file_includes_all_5_errors(self):
        """Vérifie les 5 erreurs persistantes spécifiques."""
        raw = load_raw()
        ids = {c["id"] for c in raw["corrections"]}
        # 5 corrections attendues (HEC AST, VAE, bac S, EPITA, BBA INSEEC)
        assert "hec_admission_ast_pas_tremplin_passerelle" in ids
        assert "vae_experience_liee_diplome" in ids
        assert "medecine_bac_s_supprime_2021" in ids
        assert "epita_couts_scolarite_2025" in ids
        assert "bba_inseec_couts_scolarite_2025" in ids

    def test_real_file_all_have_source_officielle(self):
        """Anti-hallu défensif : chaque correction a une URL source."""
        raw = load_raw()
        for c in raw["corrections"]:
            assert c.get("source_officielle"), f"Source manquante pour {c['id']}"
            assert c["source_officielle"].startswith("http"), \
                f"Source URL invalide pour {c['id']}"
