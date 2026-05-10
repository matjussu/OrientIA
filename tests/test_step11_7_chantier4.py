"""Tests step 11.7 chantier 4 — UX templates variants + phase_projet contextuel.

Couvre :
- REFUSAL_TEMPLATE_VARIANTS : 3 variants par reason
- select_refusal_template : déterministe, varie selon question
- REFUSAL_TEMPLATES rétrocompat (= variant[0])
- phase_projet skip sur questions factuelles/réalisme/comparaison
- phase_projet footer contextuel (1 question topic-aware au lieu de 3)
- phase_projet ne se déclenche pas sur questions sans topic
"""
from __future__ import annotations

from src.rag.router_llm import (
    REFUSAL_TEMPLATES,
    REFUSAL_TEMPLATE_VARIANTS,
    select_refusal_template,
)
from src.validator.phase_projet import (
    _question_for_topic,
    append_phase_projet,
    detect_high_stakes_topic,
    is_factual_or_realism_question,
)


# ────────────────────────── REFUSAL_TEMPLATE_VARIANTS ──────────────────────────


def test_each_reason_has_3_variants() -> None:
    """3 variants par refusal_reason (cible step 11.7 chantier 4)."""
    for reason in ("superlative_no_data", "cross_domain", "out_of_scope_specific"):
        variants = REFUSAL_TEMPLATE_VARIANTS[reason]
        assert len(variants) == 3, f"{reason} doit avoir 3 variants, pas {len(variants)}"
        for v in variants:
            assert len(v) > 100, "Variant trop court pour être utile"


def test_variants_are_distinct() -> None:
    """Les 3 variants doivent être DIFFÉRENTS (pas de copy-paste)."""
    for reason, variants in REFUSAL_TEMPLATE_VARIANTS.items():
        assert len(set(variants)) == 3, (
            f"{reason} a des variants dupliqués — perd l'effet anti-répétition"
        )


def test_refusal_templates_legacy_compat() -> None:
    """REFUSAL_TEMPLATES (legacy) reste = variant[0] de chaque reason."""
    for reason, variants in REFUSAL_TEMPLATE_VARIANTS.items():
        assert REFUSAL_TEMPLATES[reason] == variants[0]


# ────────────────────────── select_refusal_template ──────────────────────────


def test_select_returns_variant_0_when_no_question() -> None:
    """Question vide ou None → variant[0] (compat)."""
    for reason in ("superlative_no_data", "cross_domain", "out_of_scope_specific"):
        v0 = REFUSAL_TEMPLATE_VARIANTS[reason][0]
        assert select_refusal_template(reason, None) == v0
        assert select_refusal_template(reason, "") == v0


def test_select_deterministic_same_question() -> None:
    """Même question → même variant (reproductible cross-runs)."""
    q = "Quelle est la meilleure école d'ingé ?"
    a = select_refusal_template("superlative_no_data", q)
    b = select_refusal_template("superlative_no_data", q)
    assert a == b


def test_select_distributes_across_variants() -> None:
    """3 questions distinctes ont statistiquement 1/3 de chance de tomber
    sur le même variant. Sur ~30 questions différentes, on attend les
    3 variants représentés."""
    questions = [f"Quelle est la meilleure école {i} en France ?" for i in range(30)]
    selected = {select_refusal_template("superlative_no_data", q) for q in questions}
    # Au moins 2 variants distincts vus sur 30 questions
    assert len(selected) >= 2, (
        "Sur 30 questions distinctes, au moins 2 variants devraient être sélectionnés"
    )


def test_select_unknown_reason_falls_back() -> None:
    """Reason inconnu → fallback gracieux sur out_of_scope_specific."""
    result = select_refusal_template("hallucinated_reason", "Test ?")
    # Doit être un des variants out_of_scope_specific
    assert result in REFUSAL_TEMPLATE_VARIANTS["out_of_scope_specific"]


def test_select_resolves_step10_audit_bug() -> None:
    """Anti-régression : 3 questions différentes du dump step 11.5 ne
    doivent PLUS recevoir la même réponse mot-pour-mot.

    AVANT step 11.7 : L01 + A1 + A3 → identique mot-pour-mot.
    APRÈS : sélection variant hash-based, statistiquement différente.
    """
    questions = [
        "Quelle est la meilleure école de commerce en France ?",  # L01
        "Quelles sont les meilleures formations en cybersécurité ?",  # A1
        "Quelles écoles d'ingénieur informatique choisir ?",  # A3
    ]
    responses = [select_refusal_template("superlative_no_data", q) for q in questions]
    # Au moins une paire doit différer (statistique 1/3 chance d'être 3x identique)
    assert not (responses[0] == responses[1] == responses[2]), (
        "Bug step 11.5 : 3 questions distinctes ont la même réponse mot-pour-mot. "
        "select_refusal_template ne diversifie pas suffisamment."
    )


# ────────────────────────── phase_projet skip patterns ──────────────────────────


def test_skip_realism_question_with_grade() -> None:
    """B1 du dump : "11/20 pour HEC ?" — skip phase_projet (factuel)."""
    assert is_factual_or_realism_question("J'ai 11 de moyenne, est-ce que je peux intégrer HEC ?")


def test_skip_x_sur_20_pattern() -> None:
    assert is_factual_or_realism_question("Je suis à 13/20, Sciences Po réaliste ?")


def test_skip_realiste_word() -> None:
    assert is_factual_or_realism_question("Sciences Po Paris est-ce réaliste ?")


def test_skip_selectivite_factual() -> None:
    assert is_factual_or_realism_question("Quel est le taux d'accès de HEC ?")
    assert is_factual_or_realism_question("Combien de places en médecine ?")


def test_skip_comparison() -> None:
    assert is_factual_or_realism_question("Compare HEC et ESSEC")
    assert is_factual_or_realism_question("ESSEC vs ESCP ?")


def test_skip_information_search() -> None:
    assert is_factual_or_realism_question("Quelles sont les écoles de commerce parisiennes ?")


def test_no_skip_motivation_question() -> None:
    """Question vraiment motivationnelle → pas skip (footer pertinent)."""
    assert not is_factual_or_realism_question(
        "Je veux faire médecine pour aider les gens, c'est une bonne idée ?"
    )


def test_no_skip_career_exploration() -> None:
    assert not is_factual_or_realism_question(
        "J'hésite entre devenir kinésithérapeute ou orthophoniste"
    )


# ────────────────────────── phase_projet footer contextuel ──────────────────────────


def test_topic_question_medical() -> None:
    """Topic médecine/PASS → focus sur observation terrain."""
    q = _question_for_topic("médecine")
    assert "observ" in q.lower() and ("stage" in q.lower() or "consultation" in q.lower())


def test_topic_question_kine() -> None:
    q = _question_for_topic("kin")
    assert "kiné" in q.lower()
    assert "observ" in q.lower()


def test_topic_question_hec() -> None:
    """HEC → focus projet pro commerce/management."""
    q = _question_for_topic("HEC")
    assert "projet" in q.lower()
    assert "commerce" in q.lower() or "management" in q.lower()


def test_topic_question_sciences_po() -> None:
    """Sciences Po → focus enjeu public (PAS métier au quotidien)."""
    q = _question_for_topic("Sciences Po")
    assert "métier" not in q.lower(), (
        "Sciences Po n'est pas un métier — le footer ne doit pas demander "
        "'que sais-tu du métier au quotidien'"
    )
    assert "enjeu" in q.lower() or "public" in q.lower() or "domaine" in q.lower()


def test_topic_question_polytechnique() -> None:
    q = _question_for_topic("Polytechnique")
    assert "scientifique" in q.lower() or "technique" in q.lower()


# ────────────────────────── append_phase_projet end-to-end ──────────────────────────


def test_append_skips_realism_question() -> None:
    """B1 du dump : "11/20 pour HEC ?" → footer N'EST PAS appended."""
    answer = "ISTEC est une option avec 33 % d'accès..."
    out, was_appended = append_phase_projet(
        answer,
        "J'ai 11 de moyenne en terminale générale, est-ce que je peux intégrer HEC ?",
    )
    assert was_appended is False
    assert out == answer  # inchangé


def test_append_skips_sciences_po_realism() -> None:
    """B5 du dump : Sciences Po 13/20 réaliste → skip footer (factuel)."""
    answer = "Avec 13 de moyenne, le bachelor Sciences Po est très sélectif..."
    out, was_appended = append_phase_projet(
        answer,
        "J'ai 13 de moyenne, est-ce que Sciences Po Paris est réaliste ?",
    )
    assert was_appended is False
    assert "Que sais-tu du métier au quotidien" not in out, (
        "Sciences Po n'est pas un métier — boilerplate inadéquat"
    )


def test_append_triggers_on_motivation_question() -> None:
    """Question vraiment motivationnelle sur médecine → footer appended."""
    answer = "La médecine est un parcours long et exigeant..."
    out, was_appended = append_phase_projet(
        answer,
        "Je veux faire médecine pour aider les gens — qu'est-ce que tu en penses ?",
    )
    assert was_appended is True
    assert "observ" in out.lower()  # contextuel topic médecine
    assert "CIO" in out or "Psy-EN" in out


def test_append_no_topic_no_footer() -> None:
    """Pas de topic high-stakes → pas de footer."""
    answer = "Le BUT informatique est un bon choix..."
    out, was_appended = append_phase_projet(answer, "Quelles options en BUT info à Lyon ?")
    assert was_appended is False


def test_append_idempotent_if_already_present() -> None:
    """Si answer contient déjà phase_projet → pas de duplicate."""
    answer = "La médecine est exigeante. 💭 As-tu pu observer ces métiers en stage ?"
    out, was_appended = append_phase_projet(
        answer,
        "Pourquoi faire médecine ?",
    )
    assert was_appended is False


def test_append_footer_is_short() -> None:
    """Step 11.7 chantier 4 — footer concis (1 question + CIO, pas 3)."""
    answer = "La médecine demande beaucoup de motivation."
    out, was_appended = append_phase_projet(answer, "Pourquoi devenir médecin ?")
    assert was_appended is True
    appended_part = out[len(answer):]
    # Pas plus de 1 question dans le footer (1 "?" maximum)
    assert appended_part.count("?") <= 1, (
        f"Footer doit avoir 1 question max, pas {appended_part.count('?')}"
    )
    # Pas la liste 1./2./3. de l'ancien footer
    assert "1." not in appended_part
    assert "2." not in appended_part
    assert "3." not in appended_part


def test_detect_high_stakes_unchanged() -> None:
    """detect_high_stakes_topic toujours fonctionnel (compat)."""
    assert detect_high_stakes_topic("Faut HEC") is not None
    assert detect_high_stakes_topic("Master Cyber Lyon") is None
