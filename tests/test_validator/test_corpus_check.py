"""Tests couche 2 — claim extractor + corpus-check."""
from __future__ import annotations

import pytest

from src.validator.corpus_check import (
    FormationClaim,
    CorpusWarning,
    check_claims_in_corpus,
    check_formation_exists,
    extract_claims,
)


@pytest.fixture
def mini_corpus() -> list[dict]:
    """Mini-corpus de 5 fiches pour tester extract + check."""
    return [
        {
            "nom": "Licence Informatique",
            "etablissement": "Université de Poitiers",
            "ville": "Poitiers",
        },
        {
            "nom": "Master Cybersécurité et défense",
            "etablissement": "EFREI Paris",
            "ville": "Villejuif",
        },
        {
            "nom": "BUT Informatique",
            "etablissement": "IUT de Bourges",
            "ville": "Bourges",
        },
        {
            "nom": "Diplôme d'ingénieur spécialité cybersécurité",
            "etablissement": "ENSIBS",
            "ville": "Vannes",
        },
        {
            "nom": "PASS Parcours Accès Santé Spécifique",
            "etablissement": "Université Lyon 1",
            "ville": "Lyon",
        },
    ]


# --- extract_claims ---


def test_extract_no_claim_on_empty():
    assert extract_claims("") == []


def test_extract_no_claim_on_generic_text():
    txt = "Pour ton orientation, réfléchis à tes envies et tes compétences."
    assert extract_claims(txt) == []


def test_extract_master_at_etablissement():
    txt = "Tu peux viser le Master Cybersécurité à EFREI Paris."
    claims = extract_claims(txt)
    assert len(claims) >= 1
    claim = claims[0]
    assert "Master" in claim.formation_name
    assert "Cybersécurité" in claim.formation_name
    assert "EFREI" in claim.etablissement


def test_extract_multiple_claims():
    txt = (
        "Tu peux faire un BUT Informatique à IUT de Bourges ou une "
        "Licence Informatique à l'Université de Poitiers."
    )
    claims = extract_claims(txt)
    assert len(claims) >= 2
    types = {c.formation_name.split()[0] for c in claims}
    assert "BUT" in types and "Licence" in types


# --- check_formation_exists ---


def test_check_exact_match(mini_corpus):
    found, closest, sim = check_formation_exists(
        "Master Cybersécurité", "EFREI Paris", mini_corpus
    )
    assert found
    assert sim > 0.5
    assert "EFREI" in closest


def test_check_paraphrase_passes(mini_corpus):
    """Un paraphrase proche doit être trouvé au seuil défaut 0.55."""
    found, closest, sim = check_formation_exists(
        "Master Cybersécurité et défense", "EFREI", mini_corpus
    )
    assert found
    assert sim > 0.55


def test_check_invented_formation_returns_low_sim(mini_corpus):
    """Une formation complètement inventée doit échouer au seuil défaut 0.55,
    même si l'établissement cité existe (poids 0.85 nom / 0.15 etab)."""
    found, closest, sim = check_formation_exists(
        "Licence Humanités-Parcours Orthophonie",
        "Université de Poitiers",
        mini_corpus,
    )
    assert not found
    # Sim composite reste sous 0.55 car le nom "Humanités-Orthophonie"
    # diverge trop de "Informatique" (85% du score).
    assert sim < 0.55


# --- check_claims_in_corpus ---


def test_no_warning_on_clean_answer(mini_corpus):
    answer = "Pour ton projet, pense à discuter avec un conseiller d'orientation."
    warnings = check_claims_in_corpus(answer, mini_corpus)
    assert warnings == []


def test_invented_formation_triggers_warning(mini_corpus):
    answer = (
        "Tu peux t'inscrire à la Licence Humanités-Parcours Orthophonie "
        "à l'Université de Poitiers pour préparer le concours."
    )
    warnings = check_claims_in_corpus(answer, mini_corpus)
    assert len(warnings) >= 1
    w = warnings[0]
    assert isinstance(w, CorpusWarning)
    assert w.reason == "formation_not_found_in_corpus"


def test_warning_reports_closest_match(mini_corpus):
    answer = "Licence Théologie Comparée à l'Université de Nulle-Part."
    warnings = check_claims_in_corpus(answer, mini_corpus)
    assert len(warnings) >= 1
    # Le closest_match doit être rempli même si basse similarité
    assert warnings[0].closest_match is not None
