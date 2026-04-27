"""Tests `src/collect/build_financement_corpus.py`."""
from __future__ import annotations

import json

import pytest

from src.collect.build_financement_corpus import (
    VOIE_LABELS,
    _format_montants,
    _slug,
    aggregate_by_dispositif,
    aggregate_by_voie,
    build_corpus,
    load_raw,
    save_corpus,
)


@pytest.fixture
def financement_raw_sample() -> dict:
    return {
        "version": "2026-04-27",
        "note_methodo": "test",
        "dispositifs": [
            {
                "id": "bourse_test_sup",
                "nom": "Bourse test sup",
                "organisme": "CROUS",
                "voies": ["initial"],
                "public_cible": "Étudiants post-bac",
                "montants_approximatifs_eur_an": {"min": 1000, "max": 6000, "annee": "2024-2025"},
                "conditions_cles": ["Plafond de revenus", "Âge max 28 ans"],
                "demande": "DSE",
                "source_officielle": "https://example.com/bourse",
                "specificite": "Cumulable",
            },
            {
                "id": "cpf_test",
                "nom": "Test CPF",
                "organisme": "Caisse des Dépôts",
                "voies": ["continue", "reconversion"],
                "public_cible": "Salariés et demandeurs d'emploi",
                "montants_approximatifs_eur_an": {
                    "abondement_standard": 500,
                    "plafond": 5000,
                    "annee": "2024-2025",
                },
                "conditions_cles": ["Avoir 16 ans+"],
                "source_officielle": "https://example.com/cpf",
            },
            {
                "id": "agefiph_test",
                "nom": "AGEFIPH test",
                "organisme": "AGEFIPH",
                "voies": ["handicap"],
                "public_cible": "RQTH",
                "montants_approximatifs": "Variable selon dispositif",
                "source_officielle": "https://example.com/agefiph",
            },
        ],
    }


class TestSlug:
    def test_basic(self):
        assert _slug("Initial") == "initial"
        assert _slug("Reconversion Pro") == "reconversion-pro"


class TestFormatMontants:
    def test_min_max_pattern(self):
        out = _format_montants({"min": 1000, "max": 6000, "annee": "2024"})
        assert "1000-6000€" in out
        assert "2024" in out

    def test_forfait_pattern(self):
        out = _format_montants({"forfait": 500, "annee": "2024"})
        assert "forfait 500€" in out
        assert "2024" in out

    def test_cpf_abondement_pattern(self):
        out = _format_montants({"abondement_standard": 500, "plafond": 5000})
        assert "500€/an" in out
        assert "plafond 5000€" in out

    def test_max_only(self):
        out = _format_montants({"max": 528})
        assert "max 528€" in out

    def test_none_or_empty(self):
        assert _format_montants(None) is None
        assert _format_montants({}) is None


class TestAggregateByDispositif:
    def test_one_cell_per_dispositif(self, financement_raw_sample):
        out = aggregate_by_dispositif(financement_raw_sample)
        assert len(out) == 3
        ids = {r["id"] for r in out}
        assert "financement_dispositif:bourse_test_sup" in ids
        assert "financement_dispositif:cpf_test" in ids
        assert "financement_dispositif:agefiph_test" in ids

    def test_granularity_tag(self, financement_raw_sample):
        out = aggregate_by_dispositif(financement_raw_sample)
        assert all(r["granularity"] == "dispositif" for r in out)

    def test_text_includes_organisme_and_public(self, financement_raw_sample):
        out = aggregate_by_dispositif(financement_raw_sample)
        bourse = next(r for r in out if r["dispositif_id"] == "bourse_test_sup")
        assert "CROUS" in bourse["text"]
        assert "post-bac" in bourse["text"]
        assert "1000-6000€" in bourse["text"]

    def test_text_includes_voie_labels(self, financement_raw_sample):
        out = aggregate_by_dispositif(financement_raw_sample)
        cpf = next(r for r in out if r["dispositif_id"] == "cpf_test")
        assert "formation continue" in cpf["text"]
        assert "reconversion" in cpf["text"]

    def test_text_includes_source_officielle(self, financement_raw_sample):
        """Anti-hallu : URL source toujours présente pour vérification user."""
        out = aggregate_by_dispositif(financement_raw_sample)
        for r in out:
            assert "Source officielle" in r["text"]
            assert r["source_officielle"] in r["text"]

    def test_text_handles_string_montant(self, financement_raw_sample):
        """AGEFIPH a montants_approximatifs en string lib (non structuré)."""
        out = aggregate_by_dispositif(financement_raw_sample)
        agefiph = next(r for r in out if r["dispositif_id"] == "agefiph_test")
        assert "Variable selon dispositif" in agefiph["text"]


class TestAggregateByVoie:
    def test_one_cell_per_voie(self, financement_raw_sample):
        out = aggregate_by_voie(financement_raw_sample)
        # 3 dispositifs touchent les voies : initial(1), continue(1), reconversion(1), handicap(1)
        assert len(out) == 4
        voies = {r["voie"] for r in out}
        assert voies == {"initial", "continue", "reconversion", "handicap"}

    def test_lists_dispositifs_for_voie(self, financement_raw_sample):
        out = aggregate_by_voie(financement_raw_sample)
        initial = next(r for r in out if r["voie"] == "initial")
        # Seul "bourse_test_sup" est en voie initial
        assert initial["dispositifs_ids"] == ["bourse_test_sup"]
        assert initial["n_dispositifs"] == 1

    def test_dispositif_in_multiple_voies(self, financement_raw_sample):
        """CPF est en {continue, reconversion} → présent dans les 2 cells voie."""
        out = aggregate_by_voie(financement_raw_sample)
        cont = next(r for r in out if r["voie"] == "continue")
        reco = next(r for r in out if r["voie"] == "reconversion")
        assert "cpf_test" in cont["dispositifs_ids"]
        assert "cpf_test" in reco["dispositifs_ids"]

    def test_granularity_tag(self, financement_raw_sample):
        out = aggregate_by_voie(financement_raw_sample)
        assert all(r["granularity"] == "voie" for r in out)

    def test_text_includes_voie_label(self, financement_raw_sample):
        out = aggregate_by_voie(financement_raw_sample)
        handicap = next(r for r in out if r["voie"] == "handicap")
        assert VOIE_LABELS["handicap"] in handicap["text"]


def test_build_corpus_combines(financement_raw_sample):
    corpus = build_corpus(financement_raw_sample)
    # 3 dispositifs + 4 voies (initial, continue, reconversion, handicap) = 7
    assert len(corpus) == 7
    assert all(c["domain"] == "financement_etudes" for c in corpus)
    assert all(c["source"] == "financement_dispositifs_curated" for c in corpus)


def test_save_corpus_round_trip(tmp_path, financement_raw_sample):
    corpus = build_corpus(financement_raw_sample)
    target = tmp_path / "out.json"
    save_corpus(corpus, path=target)
    loaded = json.loads(target.read_text(encoding="utf-8"))
    assert len(loaded) == len(corpus)


def test_real_raw_file_loads():
    """Smoke test : le fichier raw production parse correctement."""
    raw = load_raw()
    assert "dispositifs" in raw
    assert len(raw["dispositifs"]) >= 20  # cible Sprint 6 ~25
    # Chaque dispositif a les champs minimaux requis
    for d in raw["dispositifs"]:
        assert "id" in d
        assert "nom" in d
        assert "voies" in d
        assert "source_officielle" in d
        # Voies sont validées
        for v in d["voies"]:
            assert v in VOIE_LABELS, f"Voie inconnue : {v} dans {d['id']}"


def test_real_raw_file_voies_coverage():
    """Vérifie que les 4 voies sont chacune couvertes par >=1 dispositif."""
    raw = load_raw()
    voies_couvertes: set[str] = set()
    for d in raw["dispositifs"]:
        for v in d["voies"]:
            voies_couvertes.add(v)
    assert voies_couvertes == {"initial", "continue", "reconversion", "handicap"}, (
        f"Une voie n'est pas couverte : {voies_couvertes}"
    )
