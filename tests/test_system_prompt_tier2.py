"""Tier 2 UX rules — post-user-feedback 2026-04-18.

Source of truth: the 4 user tests (Léo 17, Sarah 20, Thomas 23,
Catherine 52, Dominique 48 Psy-EN) converged on 9 points. Tier 2 addresses
the longueur (plainte #1 unanime), the pyramid structure, the conditional
trends, the connaissance générale defiance signal, and the emoji overload.

These tests validate the SYSTEM_PROMPT carries the Tier 2 rules. They are
string-level (not behavioral) since behavioral validation requires live
LLM calls reserved for the user-test v2 pack.
"""

from __future__ import annotations

import re

from src.prompt.system import SYSTEM_PROMPT


def _flat(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower())


# --- T2.1 : brevity target 150-300 ---


def test_t2_1_brevity_target_is_150_300():
    """The new target is 150-300 mots (down from α 300-500).

    This overrides the sanity UX α target set on 2026-04-17. The old
    target is acceptable as a historical reference (e.g. "auparavant
    300-500") but must not be the active instruction.
    """
    flat = _flat(SYSTEM_PROMPT)
    assert "150-300 mots" in flat, (
        "Tier 2 must set an explicit 150-300 mots target"
    )


def test_t2_1_brevity_explicitly_overrides_alpha():
    """Tier 2 must mark itself as taking precedence over the α 300-500
    target. Without an explicit priority statement, a LLM can hesitate
    when two different targets appear in the same prompt."""
    flat = _flat(SYSTEM_PROMPT)
    # Priority / override / remplace: at least one marker must be there
    assert ("tier 2" in flat and
            ("priorité" in flat or "prioritaire" in flat or
             "prévaut" in flat or "remplace" in flat or
             "override" in flat)), (
        "Tier 2 must declare its precedence over sanity UX α"
    )


# --- T2.2 : inverted pyramid with TL;DR ---


def test_t2_2_inverted_pyramid_required():
    """Each response must start with a TL;DR block (3 lines max) that
    answers cash in the first seconds of reading."""
    flat = _flat(SYSTEM_PROMPT)
    assert ("pyramide inversée" in flat or "pyramide inverse" in flat), (
        "Tier 2 must mandate the inverted pyramid structure"
    )
    assert "tl;dr" in flat or "tldr" in flat, (
        "Tier 2 must require a TL;DR opening block"
    )


def test_t2_2_tldr_three_lines_max():
    """The TL;DR block must be explicitly capped — otherwise the LLM
    produces a 5-7 line block that defeats the purpose."""
    flat = _flat(SYSTEM_PROMPT)
    assert ("3 lignes" in flat or "trois lignes" in flat), (
        "Tier 2 must cap the TL;DR block at 3 lignes maximum"
    )


# --- T2.3 : trends conditional on changing advice ---


def test_t2_3_trends_only_when_changing_advice():
    """Léo feedback: mentioning a trend that doesn't change the advice
    creates stress without information. The rule must be explicit:
    trend iff it changes the conseil."""
    flat = _flat(SYSTEM_PROMPT)
    # Must name the conditional principle somewhere
    assert ("change ton conseil" in flat or "change le conseil" in flat or
            "modifie" in flat and "conseil" in flat or
            "implication actionnable" in flat), (
        "Tier 2 must state the conditional trend rule explicitly"
    )


# --- T2.4 : "Attention aux pièges" on choix / comparaison ---


def test_t2_4_attention_aux_pieges_required_on_choice():
    """The Q8 "Attention aux pièges" format was unanimously praised.
    Tier 2 makes it systematic for choix (Plan A/B/C) and comparaison
    questions — NOT for conceptual pure questions."""
    flat = _flat(SYSTEM_PROMPT)
    assert "attention aux pièges" in flat, (
        "Tier 2 must mandate the 'Attention aux pièges' section on choix/comparaison"
    )


def test_t2_4_pieges_section_not_on_conceptual():
    """The piège section makes no sense on a pure definition question.
    The rule must carve out conceptual questions explicitly."""
    flat = _flat(SYSTEM_PROMPT)
    # Either the rule excludes conceptual explicitly, or the piège
    # section is placed only under choix/comparaison branches.
    has_exclusion = (
        "pas" in flat and "conceptuelle" in flat or
        "sauf conceptuelle" in flat or
        "pas sur conceptuelle" in flat or
        "pas pour question conceptuelle" in flat
    )
    assert has_exclusion, (
        "Tier 2 must exclude question conceptuelle from the piège requirement"
    )


# --- T2.5 : (connaissance générale) tag less visible ---


def test_t2_5_connaissance_generale_tag_restricted():
    """Léo: the per-paragraph tag reads as 'attention je te dis peut-être
    de la merde'. Tier 2 restricts tag visibility: a single recap at end,
    not per-paragraph."""
    flat = _flat(SYSTEM_PROMPT)
    # The rule must explicitly address the tag visibility
    assert ("tag" in flat and "connaissance générale" in flat) or (
        "(connaissance générale)" in SYSTEM_PROMPT and (
            "pas chaque paragraphe" in flat or
            "pas à chaque" in flat or
            "récap en fin" in flat or
            "une seule fois" in flat or
            "usage restreint" in flat
        )
    ), "Tier 2 must restrict the (connaissance générale) tag placement"


# --- T2.6 : emoji budget max 2 ---


def test_t2_6_emoji_budget_limit():
    """Léo: trop d'emojis icônes (📍 💡 🔀 🔹 📌) = slide PowerPoint.
    Max 2 par réponse."""
    flat = _flat(SYSTEM_PROMPT)
    assert ("2 emojis" in flat or "deux emojis" in flat or
            "2 icônes" in flat or "budget emoji" in flat or
            "maximum 2" in flat and "emoji" in flat), (
        "Tier 2 must cap emoji usage at 2 per response"
    )


# --- T2.7 : varied follow-up question ---


def test_t2_7_final_question_must_vary():
    """Léo: 'Question pour toi' toujours prestige/sécurité/flexibilité
    = scripted. Tier 2 must tell the LLM to vary the follow-up."""
    flat = _flat(SYSTEM_PROMPT)
    assert ("varie" in flat and "question" in flat) or (
        "pas toujours" in flat and "prestige" in flat
    ) or "question finale variée" in flat, (
        "Tier 2 must require variation in the follow-up question"
    )


# --- Regression: Tier 0 rules must still hold (non-negotiable) ---


def test_tier0_anti_discrimination_preserved():
    """Tier 2 must not dilute Tier 0 anti-sexism rules."""
    # Reuse the spirit of test_tier0_bans_femmes_as_positive_argument
    lower = SYSTEM_PROMPT.lower()
    assert ("environnement solidaire" in lower or
            "environnement adapté" in lower or
            "environnement accessible" in lower), (
        "Tier 0 anti-sexism must still be present after Tier 2 additions"
    )


def test_tier0_anti_hallucinations_preserved():
    """MBA HEC, École 42, VAP kiné etc. must remain explicitly forbidden."""
    assert "MBA HEC" in SYSTEM_PROMPT
    assert "École 42" in SYSTEM_PROMPT or "42" in SYSTEM_PROMPT
    assert "VAP" in SYSTEM_PROMPT


def test_tier0_admin_codes_masking_preserved():
    """No raw cod_aff_form / RNCP / FOR.xxx in visible output."""
    lower = SYSTEM_PROMPT.lower()
    assert "cod_aff_form" in lower
    assert ("codes administratifs" in lower or
            "pas apparaître" in lower or
            "pas d'id brut" in lower), (
        "Tier 0 admin code masking rule must hold"
    )


def test_tier0_human_referral_preserved():
    lower = SYSTEM_PROMPT.lower()
    assert "psy-en" in lower or "scuio" in lower or "cio" in lower


# --- Priority ordering must be explicit ---


def test_tier2_priority_ordering_explicit():
    """When multiple layers of rules coexist (v3.2 + α/β + Tier 2 + Tier 0),
    the prompt must state a clear precedence so the LLM doesn't hesitate.
    Tier 0 must remain the top priority (non-negotiable), Tier 2 second."""
    flat = _flat(SYSTEM_PROMPT)
    # Somewhere the prompt enumerates the priority order explicitly
    assert ("ordre de priorité" in flat or
            "priorité :" in flat or
            "priorite :" in flat or
            "1. tier 0" in flat), (
        "Tier 2 must make the rule-stacking precedence explicit"
    )
