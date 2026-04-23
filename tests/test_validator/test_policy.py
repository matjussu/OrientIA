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


# =========================================================================
# V3 polish footer — top 2 warnings max + priority ordering
# =========================================================================


class TestV3FooterPolish:
    """V3 (ordre 2026-04-22-1308) : footer β Warn limité à top 2 items max
    avec priorité rule WARN > corpus > layer3. Au-delà : suffix masqué."""

    @pytest.fixture
    def mini_corpus_v3(self) -> list[dict]:
        return [
            {"nom": "Master Info", "etablissement": "X"},
        ]

    def test_footer_zero_items_passthrough(self, mini_corpus_v3):
        v = Validator(fiches=mini_corpus_v3)
        result = apply_policy("Réponse propre.", v.validate("Réponse propre."))
        assert result.policy == Policy.PASSTHROUGH
        # Pas de footer
        assert "Points à vérifier" not in result.final_answer

    def test_footer_one_item_shown_fully(self, mini_corpus_v3):
        """1 warning unique → affiché + pas de suffix masqué."""
        v = Validator(fiches=mini_corpus_v3)
        answer = "Le MBA HEC est plus accessible avec expérience."
        result = apply_policy(answer, v.validate(answer))
        assert result.policy == Policy.WARN
        assert "Points à vérifier" in result.final_answer
        assert "masqué" not in result.final_answer
        assert "MBA" in result.final_answer  # answer preserved

    def test_footer_three_items_truncated_with_suffix(self, mini_corpus_v3):
        """3 WARN rules → top 2 affichés + suffix "+1 autre point...".
        On utilise un input qui déclenche 3 WARN rules existantes."""
        v = Validator(fiches=mini_corpus_v3)
        answer = (
            "Le MBA HEC est plus accessible avec expérience. "
            "Une prépa privée médecine double les chances. "
            "Achète Orthophonie pour les Nuls pour réviser."
        )
        result = apply_policy(answer, v.validate(answer))
        assert result.policy == Policy.WARN
        # Vérifie présence du suffix masqué
        assert ("autre point" in result.final_answer.lower()
                or "autres points" in result.final_answer.lower())
        assert "masqué" in result.final_answer or "masqués" in result.final_answer
        # Le footer original doit être tronqué : certains messages ne sont PAS présents
        # On compte combien de "- " (puces) apparaissent après "Points à vérifier"
        footer_start = result.final_answer.find("Points à vérifier")
        footer = result.final_answer[footer_start:]
        # Compte des puces "- " dans le footer (avant le suffix)
        bullet_count = sum(1 for line in footer.splitlines() if line.startswith("- "))
        # Attendu : 2 items visibles + 1 ligne suffix = 3 total, dont 2 puces warnings
        # (le suffix commence par "- *(+" donc aussi une puce mais matchable autrement)
        assert bullet_count <= 3  # 2 visibles + 1 suffix au pire

    def test_footer_priority_rules_before_layer3(self, mini_corpus_v3):
        """Rule WARN prioritaire sur layer3 dans les 2 items visibles."""
        # Rule WARN actif
        answer = "Le MBA HEC est plus accessible avec expérience."
        # Fake ValidatorResult avec 1 WARN + 3 layer3 (force overflow)
        from src.validator import ValidatorResult, Violation, Severity, Layer3Warning
        rule_v = Violation(
            rule_id="MBA_HEC_accessible_experience",
            severity=Severity.WARNING,
            message="MBA HEC exige 5-8 ans exp — pas plus accessible.",
            matched_text="MBA HEC est plus accessible",
            category="marketing_false",
        )
        l3_warnings = [
            Layer3Warning(claim="X", reason="reason X"),
            Layer3Warning(claim="Y", reason="reason Y"),
            Layer3Warning(claim="Z", reason="reason Z"),
        ]
        fake = ValidatorResult(
            honesty_score=0.8,
            rule_violations=[rule_v],
            corpus_warnings=[],
            layer3_warnings=l3_warnings,
            flagged=False,
        )
        result = apply_policy(answer, fake)
        assert result.policy == Policy.WARN
        # La rule WARN doit apparaître dans les 2 items visibles
        assert "MBA HEC exige" in result.final_answer
        # Suffix masqué car 1 WARN + 3 layer3 = 4 items > 2
        assert "autre" in result.final_answer.lower()

    def test_footer_max_2_items_visible(self, mini_corpus_v3):
        """Au plus 2 items détaillés dans le footer, quoi qu'il arrive."""
        from src.validator import ValidatorResult, Layer3Warning
        l3 = [Layer3Warning(claim=f"C{i}", reason=f"R{i}") for i in range(5)]
        fake = ValidatorResult(
            honesty_score=0.7,
            rule_violations=[],
            corpus_warnings=[],
            layer3_warnings=l3,
            flagged=False,
        )
        result = apply_policy("Réponse", fake)
        # Compte les claims exposés : doit être <= 2
        exposed = sum(1 for c in ["C0", "C1", "C2", "C3", "C4"] if c in result.final_answer)
        assert exposed <= 2
        # Suffix mentionne les masqués
        assert "3" in result.final_answer  # 5 - 2 = 3 masqués


# =========================================================================
# V4 γ Modify — chirurgical replacement, pas de refus total
# =========================================================================


class TestV4GammaModify:
    """V4 (ordre 2026-04-22-1751) : BLOCKING rules AVEC replacement_text
    → remplacement chirurgical du segment fautif, pas refus total.

    Priority V4 : corpus_warning → Block / BLOCKING+replacement → Modify /
    BLOCKING sans replacement → Block fallback."""

    @pytest.fixture
    def mini_corpus_v4(self) -> list[dict]:
        return [{"nom": "PASS", "etablissement": "Université Lyon 1"}]

    def test_V2_4_kine_licence_option_triggers_modify_not_block(self, mini_corpus_v4):
        """Q6 pattern 'Licence option Kinésithérapie' DOIT produire une
        réponse modifiée (γ Modify) avec reformulation IFMK, pas refus total."""
        v = Validator(fiches=mini_corpus_v4)
        answer = (
            "Pour devenir kiné, tu peux viser la Licence Sciences de la vie "
            "(option Kinésithérapie) à Perpignan."
        )
        result = apply_policy(answer, v.validate(answer))
        assert result.policy == Policy.MODIFY
        # La reformulation IFMK est présente
        assert "IFMK" in result.final_answer
        # Le matched_text fautif est remplacé (l'expression exacte qui matchait)
        # doit être absente — vérifie que "(option Kinésithérapie)" littéral n'est plus là
        assert "option Kinésithérapie" not in result.final_answer
        # Footer traçabilité
        assert "modification de sécurité" in result.final_answer.lower() or "modifications de sécurité" in result.final_answer.lower()

    def test_V2_1_HEC_Tremplin_triggers_modify(self, mini_corpus_v4):
        v = Validator(fiches=mini_corpus_v4)
        answer = "Tu peux tenter le concours Tremplin à bac+3 pour intégrer HEC."
        result = apply_policy(answer, v.validate(answer))
        assert result.policy == Policy.MODIFY
        # Reformulation AST + Audencia/Kedge
        assert "AST" in result.final_answer
        assert "Audencia" in result.final_answer or "Kedge" in result.final_answer

    def test_V2_2_PASS_redoublement_triggers_modify(self, mini_corpus_v4):
        v = Validator(fiches=mini_corpus_v4)
        answer = "Si ça ne marche pas, tu peux redoubler PASS l'année suivante."
        result = apply_policy(answer, v.validate(answer))
        assert result.policy == Policy.MODIFY
        assert "interdit" in result.final_answer.lower()
        assert "2019" in result.final_answer

    def test_V1_ECN_rule_without_replacement_falls_back_to_block(self, mini_corpus_v4):
        """Les règles V1 (ECN, bac S v1) n'ont pas de replacement_text
        → Policy γ ne peut pas Modify, fallback Block."""
        v = Validator(fiches=mini_corpus_v4)
        answer = "Tu passeras les ECN en 6e année."
        result = apply_policy(answer, v.validate(answer))
        # V1 ECN pas de replacement → fallback Block
        assert result.policy == Policy.BLOCK

    def test_corpus_warning_still_blocks_cannot_modify(self, mini_corpus_v4):
        """Une formation inventée (corpus_warning) ne peut pas être modifiée
        → Block maintenu."""
        v = Validator(fiches=mini_corpus_v4)
        answer = (
            "Tu peux faire la Licence Imaginaire-Parcours X à l'Université de Nulle-Part."
        )
        result = apply_policy(answer, v.validate(answer))
        # Corpus warning → Block, jamais Modify
        assert result.policy == Policy.BLOCK
