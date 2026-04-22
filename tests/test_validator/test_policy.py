"""Tests UX Policy Validator (Gate J+6 — α Block + β Warn hybride)."""
from __future__ import annotations

import pytest

from src.validator import Validator, apply_policy, Policy


@pytest.fixture
def mini_corpus() -> list[dict]:
    return [
        {"nom": "Master Cybersécurité", "etablissement": "EFREI Paris", "ville": "Paris"},
        {"nom": "BUT Informatique", "etablissement": "IUT de Bourges", "ville": "Bourges"},
        {"nom": "PASS", "etablissement": "Université Lyon 1", "ville": "Lyon"},
    ]


# --- Policy passthrough ---


def test_policy_passthrough_when_no_violation(mini_corpus):
    v = Validator(fiches=mini_corpus)
    answer = "Pour ton orientation, consulte un Psy-EN."
    result = apply_policy(answer, v.validate(answer))
    assert result.policy == Policy.PASSTHROUGH
    assert result.final_answer == answer
    assert result.warnings == []


def test_policy_passthrough_empty_answer(mini_corpus):
    v = Validator(fiches=mini_corpus)
    result = apply_policy("", v.validate(""))
    assert result.policy == Policy.PASSTHROUGH
    assert result.final_answer == ""


# --- Policy β Warn ---


def test_policy_warn_on_warning_only(mini_corpus):
    v = Validator(fiches=mini_corpus)
    answer = "Le MBA HEC est plus accessible avec expérience professionnelle."
    result = apply_policy(answer, v.validate(answer))
    assert result.policy == Policy.WARN
    # Le texte original doit rester dans la réponse finale
    assert "MBA HEC" in result.final_answer
    # Le footer doit ajouter un avertissement
    assert "Points à vérifier" in result.final_answer
    assert len(result.warnings) >= 1


def test_policy_warn_does_not_block_answer(mini_corpus):
    v = Validator(fiches=mini_corpus)
    answer = "Une prépa privée médecine double les chances."
    result = apply_policy(answer, v.validate(answer))
    # L'answer original est préservé (juste augmenté d'un footer)
    assert answer in result.final_answer
    assert result.policy == Policy.WARN


# --- Policy α Block ---


def test_policy_block_on_blocking_rule(mini_corpus):
    v = Validator(fiches=mini_corpus)
    answer = "Tu passeras les ECN en 6e année."
    result = apply_policy(answer, v.validate(answer))
    assert result.policy == Policy.BLOCK
    # L'answer original est REMPLACÉ
    assert "ECN" not in result.final_answer or "préférerais ne pas répondre" in result.final_answer.lower() or "préfère ne pas répondre" in result.final_answer.lower()
    # Refus structuré contient pointage vers sources
    assert "ONISEP" in result.final_answer
    assert "Parcoursup" in result.final_answer
    assert len(result.blocked_categories) >= 1


def test_policy_block_on_corpus_warning(mini_corpus):
    v = Validator(fiches=mini_corpus)
    answer = (
        "Tu peux faire la Licence Théologie Comparée à l'Université de Nulle-Part."
    )
    result = apply_policy(answer, v.validate(answer))
    assert result.policy == Policy.BLOCK
    assert "ONISEP" in result.final_answer
    # Mentionne la claim non vérifiée
    assert any("Licence Théologie" in w for w in result.warnings)


def test_policy_block_mentions_specific_sources(mini_corpus):
    v = Validator(fiches=mini_corpus)
    answer = "Avec un bac S mention bien."
    result = apply_policy(answer, v.validate(answer))
    assert result.policy == Policy.BLOCK
    # Sources officielles recommandées
    for source in ["ONISEP", "Parcoursup", "SCUIO", "CIO", "Psy-EN"]:
        assert source in result.final_answer


# --- Priorité Block > Warn si les deux présents ---


def test_policy_block_wins_over_warn(mini_corpus):
    """BLOCKING + WARNING simultanés → Block prend le dessus."""
    v = Validator(fiches=mini_corpus)
    # Contient : BLOCKING (bac S) + WARNING (MBA HEC accessible)
    answer = (
        "Avec un bac S mention bien, tu peux viser MBA HEC plus accessible avec expérience."
    )
    result = apply_policy(answer, v.validate(answer))
    assert result.policy == Policy.BLOCK
