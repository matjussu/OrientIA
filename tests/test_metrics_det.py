"""Tests for the three deterministic metrics B3, B5, B6."""

from src.eval.metrics_det import (
    score_actionability,
    score_fraicheur,
    score_citation_precision,
    score_response,
    _has_plan,
    _has_follow_up_question,
    _has_next_step,
    _has_comparison_table,
    _has_passerelles_block,
)


# ========================================================
# B3 — Actionability
# ========================================================


def test_b3_full_score_on_ideal_response():
    """An ideal response with Plan A/B/C + question + next step + passerelles
    scores 6/6."""
    response = """
### Plan A — Réaliste
BUT Informatique Tours

### Plan B — Ambitieux
Master MIAGE

### Plan C — Alternative
BTS SIO en alternance

🔀 Passerelles possibles : BTS SIO → BUT Info...

Prochaine étape : inscription Parcoursup avant le 14 mars.

💡 Question pour toi : tu préfères l'alternance ou la voie classique ?
"""
    result = score_actionability(response)
    assert result["score"] == 6
    assert all(v == 1 for v in result["breakdown"].values())


def test_b3_partial_score_only_plan_a():
    response = "### Plan A — Réaliste\nMaster MIAGE Tours, taux d'accès 42%."
    result = score_actionability(response)
    assert result["score"] == 1
    assert result["breakdown"]["plan_a"] == 1
    assert result["breakdown"]["plan_b"] == 0


def test_b3_plan_detection_case_insensitive():
    response = "voici le **plan b** pour toi"
    assert _has_plan(response, "B") is True
    assert _has_plan(response, "A") is False


def test_b3_follow_up_question_detects_emoji_and_plain():
    assert _has_follow_up_question("💡 Question pour toi : ce qui compte...") is True
    assert _has_follow_up_question("Question pour toi : X ?") is True
    assert _has_follow_up_question("Une question en passant") is False


def test_b3_next_step_detects_variants():
    assert _has_next_step("Prochaine étape : inscris-toi.") is True
    assert _has_next_step("Prochaines étapes : X, Y, Z.") is True
    assert _has_next_step("Action concrète : postule.") is True
    assert _has_next_step("Fait des choses.") is False


def test_b3_comparison_table_detects_markdown_table():
    md_table = """
| Critère | A | B |
|---|---|---|
| Coût | 200€ | 9000€ |
| Labels | CTI | aucun |
"""
    assert _has_comparison_table(md_table) is True


def test_b3_comparison_table_rejects_unstructured_pipes():
    """Random pipe chars shouldn't trigger false positive."""
    response = "voici | une | liste simple sans format markdown"
    assert _has_comparison_table(response) is False


def test_b3_passerelles_detects_emoji_and_plain():
    assert _has_passerelles_block("🔀 Passerelles possibles : ...") is True
    assert _has_passerelles_block("Passerelles possibles : BTS vers BUT") is True
    assert _has_passerelles_block("Pas de passerelle ici") is False


def test_b3_table_OR_passerelles_fulfills_last_point():
    """For comparison questions, a table alone suffices. For choice questions,
    passerelles alone suffices. The slot is either/or."""
    # Only table
    r1 = "| a | b |\n|---|---|\n| 1 | 2 |"
    assert score_actionability(r1)["breakdown"]["table_or_passerelles"] == 1
    # Only passerelles
    r2 = "🔀 Passerelles : x"
    assert score_actionability(r2)["breakdown"]["table_or_passerelles"] == 1
    # Neither
    r3 = "plain text"
    assert score_actionability(r3)["breakdown"]["table_or_passerelles"] == 0


# ========================================================
# B5 — Fraîcheur
# ========================================================


def test_b5_full_score_cites_year_and_anchored_figure():
    response = "En 2025, le taux Parcoursup 2025 était de 52% à Paris."
    result = score_fraicheur(response)
    assert result["score"] == 3
    assert result["breakdown"]["mentions_year"] == 1
    assert result["breakdown"]["anchored_figure"] == 1
    assert result["breakdown"]["no_temporal_confession"] == 1


def test_b5_detects_temporal_confession_and_penalises():
    response = "Le taux en 2025 était X. Pour des données récentes, consulte le site officiel."
    result = score_fraicheur(response)
    # no_temporal_confession = 0 because the confession phrase was detected
    assert result["breakdown"]["no_temporal_confession"] == 0
    assert result["score"] == 2  # year + anchored but confession


def test_b5_no_year_no_anchor():
    response = "Cette formation est bien. C'est une licence."
    result = score_fraicheur(response)
    assert result["breakdown"]["mentions_year"] == 0
    assert result["breakdown"]["anchored_figure"] == 0
    assert result["breakdown"]["no_temporal_confession"] == 1  # no confession detected
    assert result["score"] == 1  # only the negative-no-confession point


def test_b5_year_mention_without_anchored_figure():
    response = "C'est une formation reconnue depuis 2024."
    result = score_fraicheur(response)
    assert result["breakdown"]["mentions_year"] == 1
    assert result["breakdown"]["anchored_figure"] == 0  # year not near a figure
    assert result["score"] == 2


# ========================================================
# B6 — Citation precision
# ========================================================


def _sample_corpus():
    return [
        {"cod_aff_form": "42156", "rncp": "37989",
         "url_onisep": "https://onisep.fr/FOR.12235"},
        {"cod_aff_form": "7856", "rncp": "36855",
         "url_onisep": "https://onisep.fr/FOR.8513"},
        {"cod_aff_form": "49420", "rncp": None,
         "url_onisep": "https://onisep.fr/FOR.9891"},
    ]


def test_b6_all_valid_citations_score_one():
    response = "Source : Parcoursup 2025, cod_aff_form: 42156. Aussi RNCP 37989 et FOR.12235."
    result = score_citation_precision(response, _sample_corpus())
    assert result["score"] == 1.0
    assert result["total_citations"] == 3
    assert result["valid_citations"] == 3
    assert result["invalid_citations"] == []


def test_b6_invalid_cod_aff_form_detected():
    response = "Voici la formation (Source: Parcoursup 2025, cod_aff_form: 99999)."
    result = score_citation_precision(response, _sample_corpus())
    assert result["score"] == 0.0  # 0 valid / 1 total
    assert "99999" in result["invalid_citations"]


def test_b6_mix_valid_invalid():
    response = "cod_aff_form: 42156 est bon, mais cod_aff_form: 99999 n'existe pas."
    result = score_citation_precision(response, _sample_corpus())
    assert result["score"] == 0.5
    assert result["valid_citations"] == 1
    assert result["total_citations"] == 2


def test_b6_no_citations_returns_none():
    """A response with zero citations is 'undefined' — not 0 (which would
    punish responses that legitimately don't need citations, e.g., conceptual
    questions)."""
    response = "Une licence universitaire dure 3 ans et confère le grade de licence."
    result = score_citation_precision(response, _sample_corpus())
    assert result["score"] is None
    assert result["total_citations"] == 0


def test_b6_rncp_format_with_space_and_colon():
    """RNCP can be cited as 'RNCP: 37989' or 'RNCP 37989' or 'RNCP#37989'."""
    for text in ("RNCP: 37989", "RNCP 37989", "RNCP#37989", "RNCP-37989"):
        result = score_citation_precision(text, _sample_corpus())
        assert result["valid_citations"] == 1, f"Failed for: {text!r}"


def test_b6_breakdown_reports_per_category():
    response = "cod_aff_form: 42156 et RNCP: 99999 et FOR.12235"
    result = score_citation_precision(response, _sample_corpus())
    assert result["breakdown"]["cod_aff_form"]["valid"] == 1
    assert result["breakdown"]["rncp"]["valid"] == 0
    assert result["breakdown"]["rncp"]["invalid"] == ["99999"]
    assert result["breakdown"]["onisep_slug"]["valid"] == 1


def test_b6_onisep_slug_detection_inside_url():
    """ONISEP slugs appear inside URLs like '/FOR.12235' — must be detected."""
    response = "Voir https://www.onisep.fr/http/redirection/formation/slug/FOR.12235"
    result = score_citation_precision(response, _sample_corpus())
    assert result["breakdown"]["onisep_slug"]["valid"] == 1


# ========================================================
# Combined score_response
# ========================================================


def test_score_response_returns_all_three_metrics():
    response = """
### Plan A — Réaliste
Master MIAGE Tours, taux Parcoursup 2025 de 42%.
(Source: Parcoursup 2025, cod_aff_form: 42156)

🔀 Passerelles possibles : BTS SIO vers BUT
Prochaine étape : candidate en février.
💡 Question pour toi : préfères-tu la prépa ou le BUT ?
"""
    out = score_response(response, _sample_corpus())
    assert "actionability" in out
    assert "fraicheur" in out
    assert "citation_precision" in out
    # Full action score 4 (plan A, passerelles, next step, question — no plan B/C)
    assert out["actionability"]["score"] == 4
    # Full fraicheur score
    assert out["fraicheur"]["score"] == 3
    # Full citation precision
    assert out["citation_precision"]["score"] == 1.0
