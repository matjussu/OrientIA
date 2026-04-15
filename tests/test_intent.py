"""Phase F.3.b — Rule-based intent classifier.

The classifier maps a French student question to one of 7 intent
classes. The intent then drives a retrieval strategy (top_k_sources,
mmr_lambda) via intent_to_config().

Intents:
  - comparaison: explicit comparison between named formations
  - geographic:  question scoped to a region/city
  - realisme:    feasibility / selectivity / grades
  - passerelles: cross-domain transition / reconversion
  - decouverte:  open exploration of careers/formations
  - conceptual:  definition / explanation of a concept
  - general:     default fallback

Written BEFORE the implementation (TDD).
"""
from __future__ import annotations

import pytest

from src.rag.intent import (
    classify_intent,
    intent_to_config,
    IntentConfig,
    INTENT_GENERAL,
    INTENT_COMPARAISON,
    INTENT_GEOGRAPHIC,
    INTENT_REALISME,
    INTENT_PASSERELLES,
    INTENT_DECOUVERTE,
    INTENT_CONCEPTUAL,
)


# --- classify_intent unit tests ---


@pytest.mark.parametrize("q", [
    "Compare ENSEIRB-MATMECA et EPITA pour la cybersécurité",
    "EPITA ou EPITECH pour devenir développeur ?",
    "Quelle différence entre un BUT info et une licence info ?",
    "Vaut-il mieux INSA Lyon ou École Centrale Lyon ?",
])
def test_classify_comparaison(q):
    assert classify_intent(q) == INTENT_COMPARAISON


@pytest.mark.parametrize("q", [
    "Quelles bonnes formations existent à Perpignan ?",
    "Je cherche une école de cyber en Bretagne",
    "Formations data science à Toulouse ?",
    "Que faire à Lille en informatique ?",
])
def test_classify_geographic(q):
    assert classify_intent(q) == INTENT_GEOGRAPHIC


@pytest.mark.parametrize("q", [
    "J'ai 11 de moyenne en terminale générale, est-ce que je peux intégrer HEC ?",
    "Avec 13 de moyenne, ai-je une chance pour Sciences Po ?",
    "Quel taux d'admission pour Polytechnique ?",
    "Suis-je accepté à l'INSA avec un dossier moyen ?",
])
def test_classify_realisme(q):
    assert classify_intent(q) == INTENT_REALISME


@pytest.mark.parametrize("q", [
    "Je suis en L2 droit et je veux me réorienter vers l'informatique, comment ?",
    "Reconversion vers la cybersécurité après 5 ans de marketing, possible ?",
    "Quelles passerelles entre médecine et data science ?",
    "Je veux changer de filière, je suis en bac+2 commerce vers info",
])
def test_classify_passerelles(q):
    assert classify_intent(q) == INTENT_PASSERELLES


@pytest.mark.parametrize("q", [
    "J'aime les données et la géopolitique, quels métiers existent ?",
    "Je suis curieux de tech, quels métiers méconnus pourraient me plaire ?",
    "Quels métiers originaux dans le domaine de la data ?",
    "Je m'intéresse à la sécurité, propose-moi des pistes",
])
def test_classify_decouverte(q):
    assert classify_intent(q) == INTENT_DECOUVERTE


@pytest.mark.parametrize("q", [
    "C'est quoi une licence universitaire en France ?",
    "Qu'est-ce qu'un label CTI ?",
    "Comment fonctionne Parcoursup ?",
    "Explique le label SecNumEdu",
])
def test_classify_conceptual(q):
    assert classify_intent(q) == INTENT_CONCEPTUAL


@pytest.mark.parametrize("q", [
    "Quelles sont les meilleures formations en cybersécurité en France ?",
    "Je veux étudier le droit, quels conseils ?",
])
def test_classify_general_fallback(q):
    """Questions that don't match a specific pattern fall back to general."""
    assert classify_intent(q) == INTENT_GENERAL


def test_classify_empty_string_returns_general():
    assert classify_intent("") == INTENT_GENERAL


def test_classify_is_case_insensitive():
    assert classify_intent("COMPARE EPITA ET EPITECH") == INTENT_COMPARAISON


def test_classify_handles_accents_robustly():
    """Reorientation/reconversion must work with or without accents."""
    assert classify_intent("Je veux me reorienter") == INTENT_PASSERELLES
    assert classify_intent("Je veux me réorienter") == INTENT_PASSERELLES


# --- intent_to_config unit tests ---


def test_config_returns_intent_config_dataclass():
    cfg = intent_to_config(INTENT_GENERAL)
    assert isinstance(cfg, IntentConfig)
    assert hasattr(cfg, "top_k_sources")
    assert hasattr(cfg, "mmr_lambda")


def test_comparaison_config_widens_top_k():
    """Comparison questions need a broader candidate pool to surface
    at least the 2-3 named institutions side by side."""
    base = intent_to_config(INTENT_GENERAL)
    cmp_cfg = intent_to_config(INTENT_COMPARAISON)
    assert cmp_cfg.top_k_sources >= base.top_k_sources


def test_realisme_config_focuses_top_k():
    """Realism questions are narrow — same formation, different angle.
    Fewer candidates avoid diluting the answer with distractors."""
    base = intent_to_config(INTENT_GENERAL)
    rea_cfg = intent_to_config(INTENT_REALISME)
    assert rea_cfg.top_k_sources <= base.top_k_sources


def test_decouverte_config_uses_aggressive_mmr():
    """Discovery questions benefit from aggressive diversification —
    we want surprising paths, not 5 variants of the same flagship."""
    base = intent_to_config(INTENT_GENERAL)
    dec_cfg = intent_to_config(INTENT_DECOUVERTE)
    assert dec_cfg.mmr_lambda < base.mmr_lambda


def test_realisme_config_uses_conservative_mmr():
    """Realism questions should NOT diversify — we want all the data
    points on the specific formation the student is targeting."""
    base = intent_to_config(INTENT_GENERAL)
    rea_cfg = intent_to_config(INTENT_REALISME)
    assert rea_cfg.mmr_lambda > base.mmr_lambda


def test_geographic_config_widens_top_k_and_diversifies():
    """Geographic questions want the breadth of the regional offering
    — many candidates + aggressive diversification."""
    base = intent_to_config(INTENT_GENERAL)
    geo_cfg = intent_to_config(INTENT_GEOGRAPHIC)
    assert geo_cfg.top_k_sources >= base.top_k_sources
    assert geo_cfg.mmr_lambda < base.mmr_lambda


def test_unknown_intent_returns_general_config():
    """Defensive: unknown intent strings must not crash, they fall
    back to the general config so the pipeline keeps running."""
    cfg = intent_to_config("totally_unknown_intent")
    base = intent_to_config(INTENT_GENERAL)
    assert cfg == base
