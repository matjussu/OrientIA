from src.prompt.system import SYSTEM_PROMPT, build_user_prompt


def test_system_prompt_contains_neutrality_rules():
    assert "SecNumEdu" in SYSTEM_PROMPT or "labels officiels" in SYSTEM_PROMPT
    assert "biais marketing" in SYSTEM_PROMPT.lower()


def test_system_prompt_contains_realism_thresholds():
    assert "10" in SYSTEM_PROMPT and "30" in SYSTEM_PROMPT
    assert "taux d'accès" in SYSTEM_PROMPT.lower()


def test_system_prompt_forbids_yes_man():
    assert "tout est possible" in SYSTEM_PROMPT.lower()


def test_build_user_prompt_injects_context():
    context = "FICHE 1: Master Cyber Rennes..."
    question = "Quelles formations cyber ?"
    result = build_user_prompt(context, question)
    assert context in result
    assert question in result


# --- Phase 1.3 — system prompt v3 ---


def test_v3_removes_shouting_jamais():
    """Phase 1.3: the 'ne devine JAMAIS' mantra must be gone.

    Shouted 'JAMAIS' repeated 3+ times created a reflex of confession
    and hedging that cost 1-8 points on orthogonal questions. Kept as
    lowercase 'jamais' for the few prohibitions (e.g., 'jamais de
    jugement de valeur') it's fine, but no more CAPS shouting.
    """
    caps_count = SYSTEM_PROMPT.count("JAMAIS")
    assert caps_count <= 1, (
        f"Expected ≤ 1 'JAMAIS' in caps, found {caps_count} "
        "(reflex of confession comes from repeated shouting)"
    )


def test_v3_forbids_confession_phrases():
    """v3 must explicitly call out confession phrases to avoid."""
    lower = SYSTEM_PROMPT.lower()
    # The prompt must mention at least one of the banned opening phrases
    # so the LLM knows not to produce them.
    banned_markers = [
        "n'apparaît pas",
        "ne peux pas te répondre",
        "fiches ne couvrent",
        "non disponible dans la fiche",
    ]
    assert any(m in lower for m in banned_markers), (
        "v3 must explicitly ban at least one confession pattern by name"
    )


def test_v3_mentions_general_knowledge_fallback():
    """v3 instructs the model to generalise rather than refuse."""
    assert "(connaissance générale)" in SYSTEM_PROMPT, (
        "v3 must still mark general-knowledge content explicitly"
    )
    lower = SYSTEM_PROMPT.lower()
    # The v3 anti-confession rule should push toward generalisation
    assert "généralise" in lower or "connaissances générales" in lower


def test_v3_forces_geographic_diversity():
    """v3 pushes ≥ 3 regions whenever the question allows it."""
    lower = SYSTEM_PROMPT.lower()
    assert (
        "3 régions" in lower
        or "trois régions" in lower
        or "3 villes" in lower
        or "au moins 3" in lower
    ), "v3 must instruct the model to cover ≥ 3 distinct locations"


def test_v3_proposes_plan_a_b_c():
    """v3 structures the answer as Plan A / Plan B / Plan C."""
    assert "Plan A" in SYSTEM_PROMPT
    assert "Plan B" in SYSTEM_PROMPT
    assert "Plan C" in SYSTEM_PROMPT


def test_v3_asks_for_substantial_answers():
    """v3 instructs the model to produce detailed, structured responses.

    Our run-6 baseline averaged 788 words/response vs mistral_raw 1062.
    v3 asks for ~1000 words to close that verbosity gap.
    """
    lower = SYSTEM_PROMPT.lower()
    # Either an explicit word count or a "detailed/complete" instruction
    assert (
        "1000 mots" in lower
        or "détaillée" in lower
        or "complète" in lower
        or "approfondie" in lower
    )


def test_v3_preserves_numeric_anchor():
    """v3 keeps the one non-negotiable: the numeric ground truth of fiches."""
    lower = SYSTEM_PROMPT.lower()
    # The model must still honor the exact numbers from retrieved fiches
    assert "source de vérité" in lower or "chiffres des fiches" in lower


# --- Phase C (v3.1) — targeted rules for the 3 weak categories ---


def test_v3_1_conceptual_question_bypass():
    """Phase C fix for honnetete H2 (-4 gap on 'how does Parcoursup work').

    When the question asks about a concept / definition / mechanism
    (Parcoursup itself, licence LMD, the French education system),
    the model should answer didactically in (connaissance générale)
    WITHOUT forcing the retrieved fiches as examples.
    """
    import re
    # Normalize whitespace so markdown wrapping doesn't break substring matches.
    flat = re.sub(r"\s+", " ", SYSTEM_PROMPT.lower())
    # Must explicitly call out conceptual/definition questions
    assert (
        "question conceptuelle" in flat
        or "question de définition" in flat
        or "question sur un concept" in flat
        or "concept ou une définition" in flat
    )
    # Must instruct to NOT treat fiches as examples for these
    assert (
        "pas les fiches comme" in flat
        or "sans citer les fiches" in flat
        or "n'utilise pas les fiches" in flat
    )


def test_v3_1_decouverte_interdisciplinary():
    """Phase C fix for decouverte C3 (-4 gap on writing + sciences).

    Our fiches are all cyber/data. When the student asks about an
    interdisciplinary intersection that the fiches don't cover, the
    model should go broad via (connaissance générale) — not anchor
    on cyber/data metiers.
    """
    import re
    flat = re.sub(r"\s+", " ", SYSTEM_PROMPT.lower())
    assert (
        "interdisciplinaire" in flat
        or "métiers méconnus" in flat
        or "intersection de deux" in flat
    )


def test_v3_1_distinct_ville_forced():
    """Phase C fix for diversite_geo: each cited formation must be
    in a distinct city whenever possible. The old rule '≥ 3 régions'
    was too weak — the LLM cited 3 Rennes schools under Bretagne."""
    import re
    flat = re.sub(r"\s+", " ", SYSTEM_PROMPT.lower())
    assert (
        "ville différente" in flat
        or "villes distinctes" in flat
        or "ville distincte" in flat
        or "pas deux fois la même ville" in flat
    )
