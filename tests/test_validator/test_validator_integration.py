"""Tests intégration de l'orchestrateur Validator."""
from __future__ import annotations

import pytest

from src.validator import Validator, ValidatorResult, Severity


@pytest.fixture
def mini_corpus() -> list[dict]:
    return [
        {"nom": "Master Cybersécurité", "etablissement": "EFREI Paris", "ville": "Paris"},
        {"nom": "BUT Informatique", "etablissement": "IUT de Bourges", "ville": "Bourges"},
        {"nom": "PASS", "etablissement": "Université Lyon 1", "ville": "Lyon"},
    ]


# --- Cas baseline ---


def test_validate_clean_answer_returns_perfect_score(mini_corpus):
    v = Validator(fiches=mini_corpus)
    answer = "Pour ton orientation, parle à un Psy-EN du CIO de ta région."
    result = v.validate(answer)
    assert isinstance(result, ValidatorResult)
    assert result.honesty_score == 1.0
    assert not result.flagged
    assert result.rule_violations == []
    assert result.corpus_warnings == []


def test_validate_empty_answer_no_violation(mini_corpus):
    v = Validator(fiches=mini_corpus)
    result = v.validate("")
    assert result.honesty_score == 1.0
    assert not result.flagged


# --- Détection violation BLOCKING ---


def test_validate_flags_blocking_rule(mini_corpus):
    v = Validator(fiches=mini_corpus)
    answer = "Tu passeras les ECN en 6e année de médecine."
    result = v.validate(answer)
    assert result.flagged
    assert result.honesty_score < 1.0
    assert any(violation.severity == Severity.BLOCKING for violation in result.rule_violations)


def test_validate_warning_does_not_flag_alone(mini_corpus):
    """Une rule WARNING seule ne doit PAS positionner flagged=True
    (mais elle réduit le honesty_score)."""
    v = Validator(fiches=mini_corpus)
    answer = "Le MBA HEC est plus accessible avec expérience professionnelle."
    result = v.validate(answer)
    assert result.honesty_score < 1.0
    # Pas de BLOCKING + pas de corpus_warning → pas flagged
    if not any(w for w in result.corpus_warnings):
        assert not result.flagged


def test_validate_corpus_warning_flags(mini_corpus):
    v = Validator(fiches=mini_corpus)
    answer = (
        "Tu peux faire la Licence Théologie Comparée à l'Université de Nulle-Part."
    )
    result = v.validate(answer)
    assert result.flagged
    assert len(result.corpus_warnings) >= 1


# --- Score honnêteté ---


def test_honesty_score_decreases_with_blocking(mini_corpus):
    v = Validator(fiches=mini_corpus)
    answer1 = "Avec un bac S mention bien."  # 1 BLOCKING
    answer2 = "Avec un bac S mention bien et école 42 gratuite en alternance."  # 2 BLOCKING
    r1 = v.validate(answer1)
    r2 = v.validate(answer2)
    assert r1.honesty_score > r2.honesty_score


def test_honesty_score_floor_zero(mini_corpus):
    """Pile up violations — score reste >= 0.0."""
    v = Validator(fiches=mini_corpus)
    answer = (
        "Pour HEC, tu peux passer le Tremplin vers HEC ou le Passerelle vers HEC. "
        "Tu peux aussi viser MBA HEC plus accessible avec expérience. "
        "Ou faire un bac S et viser ECN. "
        "L'école 42 est gratuite en alternance. "
        "Une prépa privée médecine double les chances. "
        "Et achète Orthophonie pour les Nuls."
    )
    result = v.validate(answer)
    assert 0.0 <= result.honesty_score <= 1.0


# --- Summary readable ---


def test_summary_includes_violations(mini_corpus):
    v = Validator(fiches=mini_corpus)
    answer = "Tu passeras les ECN en 6e année."
    result = v.validate(answer)
    s = result.summary()
    assert "honesty_score" in s
    assert "ECN" in s or "EDN" in s


# --- Wiring pipeline opt-in ---


def test_pipeline_opt_in_validator_sets_last_validation(mini_corpus, monkeypatch):
    """Quand `validator=` est passé au constructeur OrientIAPipeline,
    après .answer() le résultat doit être stocké dans .last_validation.

    On mocke le generator pour éviter l'appel Mistral réel.
    """
    from src.rag.pipeline import OrientIAPipeline
    import src.rag.pipeline as pipeline_mod

    v = Validator(fiches=mini_corpus)

    # Mock generate() pour retourner une réponse contenant une halluc. ECN
    monkeypatch.setattr(
        pipeline_mod,
        "generate",
        lambda *args, **kwargs: "Tu passeras les ECN en 6e année.",
    )
    # Mock retrieve_top_k + rerank pour skip l'appel embed/FAISS
    monkeypatch.setattr(
        pipeline_mod, "retrieve_top_k", lambda *args, **kwargs: mini_corpus
    )
    monkeypatch.setattr(pipeline_mod, "rerank", lambda r, c, **kw: r)

    p = OrientIAPipeline(client=None, fiches=mini_corpus, validator=v)
    # Court-circuiter l'index pour passer le RuntimeError de answer()
    p.index = "mocked-non-none-sentinel"

    answer_text, top = p.answer("question test")
    # Avec Validator + Policy wiring (Gate J+6), l'answer final peut être
    # un refus si Block déclenché. La validation brute reste accessible.
    assert p.last_validation is not None
    assert p.last_validation.flagged
    assert any(viol.rule_id == "ECN_renamed_to_EDN" for viol in p.last_validation.rule_violations)
    # Policy doit avoir bloqué (ECN est une BLOCKING rule)
    assert p.last_policy_result is not None
    assert p.last_policy_result.policy.value == "block"
    # Refus structuré dans answer_text (plus le texte original)
    assert "ONISEP" in answer_text


def test_pipeline_without_validator_keeps_last_validation_none(mini_corpus, monkeypatch):
    """Backward compat : sans validator, le pipeline ne se mêle de rien."""
    from src.rag.pipeline import OrientIAPipeline
    import src.rag.pipeline as pipeline_mod

    monkeypatch.setattr(pipeline_mod, "generate", lambda *args, **kwargs: "OK")
    monkeypatch.setattr(pipeline_mod, "retrieve_top_k", lambda *args, **kwargs: mini_corpus)
    monkeypatch.setattr(pipeline_mod, "rerank", lambda r, c, **kw: r)

    p = OrientIAPipeline(client=None, fiches=mini_corpus)  # PAS de validator
    p.index = "mocked"
    p.answer("question test")
    assert p.last_validation is None
