"""Tests unitaires des règles déterministes (couche 1)."""
from __future__ import annotations

import pytest

from src.validator.rules import apply_rules, RULES, Severity, Violation


# --- Coverage basique ---


def test_rules_registry_not_empty():
    assert len(RULES) >= 10, "Au moins 10 règles attendues (ADR-025 + user_test_v2)"


def test_rules_have_required_fields():
    required = {"id", "category", "severity", "pattern", "message"}
    for rule in RULES:
        missing = required - set(rule.keys())
        assert not missing, f"règle {rule.get('id')} manque: {missing}"


def test_rule_ids_are_unique():
    ids = [r["id"] for r in RULES]
    assert len(ids) == len(set(ids)), f"rule_ids dupliqués détectés: {ids}"


def test_no_violation_on_empty_string():
    assert apply_rules("") == []


def test_no_violation_on_clean_answer():
    clean = (
        "Pour la cybersécurité, l'ESEA à Pau forme en bac+5 avec 85% d'insertion à 6 mois. "
        "Les candidatures se font sur Parcoursup entre janvier et mars 2026."
    )
    assert apply_rules(clean) == []


# --- Terminologie & dates ---


def test_ECN_cited_as_current_is_blocking():
    violations = apply_rules("Tu passeras les ECN en 6ème année de médecine.")
    assert any(v.rule_id == "ECN_renamed_to_EDN" for v in violations)
    blocking = [v for v in violations if v.rule_id == "ECN_renamed_to_EDN"]
    assert blocking[0].severity == Severity.BLOCKING


def test_ECN_historical_context_is_allowed():
    """'ECN (ancien nom d'EDN)' ne doit pas être flaggé."""
    txt = "L'EDN (ancien nom ECN, réforme R2C 2023) a lieu en 6e année."
    violations = apply_rules(txt)
    assert not any(v.rule_id == "ECN_renamed_to_EDN" for v in violations)


def test_bac_S_cited_as_current_is_blocking():
    violations = apply_rules("Avec un bac S mention bien, tu peux viser prépa MPSI.")
    assert any(v.rule_id == "bac_S_abolished" for v in violations)


def test_bac_S_historical_context_is_allowed():
    txt = "Avant 2021, l'ancienne filière S était la voie royale pour prépa MPSI."
    violations = apply_rules(txt)
    assert not any(v.rule_id == "bac_S_abolished" for v in violations)


def test_VAE_VAP_confusion_warns():
    txt = "Tu peux utiliser une VAE pour reprendre tes études en L3 psycho."
    violations = apply_rules(txt)
    assert any(v.rule_id == "VAE_VAP_confusion" for v in violations)


# --- Concours HEC whitelist ---


def test_Tremplin_to_HEC_is_blocking():
    txt = "Après ton bac+3 tu peux passer le concours Tremplin vers HEC."
    violations = apply_rules(txt)
    assert any(v.rule_id == "tremplin_not_HEC" for v in violations)


def test_Passerelle_to_HEC_is_blocking():
    txt = "Le concours Passerelle est une bonne option pour HEC."
    violations = apply_rules(txt)
    assert any(v.rule_id == "passerelle_not_HEC" for v in violations)


def test_Tremplin_to_Audencia_is_allowed():
    """Tremplin vers Audencia est un vrai parcours — ne pas flagger."""
    txt = "Tu peux viser Audencia via le concours Tremplin en bac+2."
    violations = apply_rules(txt)
    assert not any(v.rule_id == "tremplin_not_HEC" for v in violations)


# --- Voies impossibles ---


def test_VAP_infirmier_kine_is_blocking():
    txt = "La passerelle VAP Infirmier vers kiné est une option en 2 ans."
    violations = apply_rules(txt)
    assert any(v.rule_id == "VAP_infirmier_kine" for v in violations)


# --- Marketing trompeur ---


def test_ecole42_gratuite_alternance_is_blocking():
    txt = "L'école 42 est gratuite en alternance, idéal pour se former."
    violations = apply_rules(txt)
    assert any(v.rule_id == "ecole42_gratuite_alternance" for v in violations)


def test_ecole42_gratuite_tout_court_is_allowed():
    txt = "L'école 42 est entièrement gratuite, finance par Xavier Niel."
    violations = apply_rules(txt)
    assert not any(v.rule_id == "ecole42_gratuite_alternance" for v in violations)


def test_MBA_HEC_plus_accessible_warns():
    txt = "Le MBA HEC est plus accessible avec de l'expérience pro que HEC direct."
    violations = apply_rules(txt)
    assert any(v.rule_id == "MBA_HEC_accessible_experience" for v in violations)


def test_prepa_privee_medecine_double_chances_warns():
    txt = "Une prépa privée médecine double les chances de passer."
    violations = apply_rules(txt)
    assert any(v.rule_id == "prepa_medecine_2x_chances" for v in violations)


def test_pour_les_nuls_concours_warns():
    txt = "Je te conseille le livre 'Orthophonie pour les Nuls' pour réviser."
    violations = apply_rules(txt)
    assert any(v.rule_id == "pour_les_nuls_concours_selectif" for v in violations)


# --- Formation inventée (user_test_v2 Sarah) ---


def test_licence_humanites_orthophonie_is_blocking():
    txt = (
        "Tu peux faire la Licence Humanités-Parcours Orthophonie à Poitiers "
        "pour préparer le concours."
    )
    violations = apply_rules(txt)
    assert any(v.rule_id == "licence_humanites_orthophonie_invented" for v in violations)


# --- Output sémantique ---


def test_violation_dataclass_exposes_expected_fields():
    violations = apply_rules("ECN en 6e année")
    assert violations
    v = violations[0]
    assert isinstance(v, Violation)
    assert v.matched_text
    assert v.message
    assert v.category
    assert isinstance(v.severity, Severity)
