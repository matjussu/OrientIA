"""Tests phase projet minimal V4."""
from __future__ import annotations

from src.validator.phase_projet import (
    HIGH_STAKES_TRIGGERS,
    append_phase_projet,
    detect_high_stakes_topic,
)


# --- Detection triggers ---


def test_detect_HEC_trigger():
    assert detect_high_stakes_topic("Est-ce que je peux intégrer HEC ?") is not None


def test_detect_PASS_trigger():
    assert detect_high_stakes_topic("Mes chances en PASS avec 12 de moyenne") is not None


def test_detect_kine_trigger():
    assert detect_high_stakes_topic("Comment devenir kiné ?") is not None
    assert detect_high_stakes_topic("Études de kinésithérapie") is not None


def test_detect_veto_trigger():
    assert detect_high_stakes_topic("Je veux devenir vétérinaire") is not None


def test_detect_sciences_po_trigger():
    assert detect_high_stakes_topic("Concours Sciences Po Paris") is not None


def test_no_detect_on_neutral_question():
    assert detect_high_stakes_topic("Comment bien réviser le bac ?") is None
    assert detect_high_stakes_topic("Quelles sont les formations à Perpignan ?") is None


# --- Append logic ---


def test_append_phase_projet_on_high_stakes():
    question = "Je veux intégrer HEC avec 11 de moyenne."
    answer = "Voici mes conseils..."
    augmented, appended = append_phase_projet(answer, question)
    assert appended is True
    assert "CIO" in augmented
    assert "Psy-EN" in augmented
    assert "Avant de décider" in augmented


def test_no_append_on_neutral():
    question = "Quelles sont les formations à Perpignan ?"
    answer = "Voici les formations..."
    augmented, appended = append_phase_projet(answer, question)
    assert appended is False
    assert augmented == answer


def test_no_append_if_already_present():
    """Si le generator a déjà inclus les questions projet, ne pas duppler."""
    question = "Comment devenir kiné ?"
    answer = (
        "Voici mes conseils. Avant de décider : Qu'est-ce qui te motive ? "
        "As-tu rencontré quelqu'un qui fait ce métier ?"
    )
    augmented, appended = append_phase_projet(answer, question)
    assert appended is False


def test_registry_not_empty():
    assert len(HIGH_STAKES_TRIGGERS) >= 10
