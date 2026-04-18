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
    """v3 instructs the model to produce structured answers (either
    detailed OR — since sanity-UX Vague — concise-but-dense).

    Post sanity-UX : the ~1000-word target was overridden by a priority
    rule for 300-500 words. The 'detailed/structured' expectation still
    holds — it's now about density, not volume.
    """
    lower = SYSTEM_PROMPT.lower()
    # Either an explicit word count (1000 legacy OR 300-500 override)
    # OR a "detailed/complete/dense" instruction.
    assert (
        "1000 mots" in lower
        or "300-500 mots" in lower
        or "détaillée" in lower
        or "complète" in lower
        or "approfondie" in lower
        or "dense" in lower
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


def test_v3_2_comparison_table_forced():
    """Phase E.2 fix for comparaison gap (-1.40 across run 8 and run 9).

    F-category questions ("Compare ENSEIRB-MATMECA et EPITA", "Dauphine
    vs école de commerce", "BTS SIO vs BUT info") need a clear side-by-side
    structured comparison. our_rag was dropping into Plan A/B/C instead
    of comparing the two named entities head-to-head.
    """
    import re
    flat = re.sub(r"\s+", " ", SYSTEM_PROMPT.lower())
    # Must mention comparison questions specifically
    assert (
        "question de comparaison" in flat
        or "question comparative" in flat
        or "comparaison directe" in flat
        or "compare x et y" in flat
    )
    # Must instruct a table / side-by-side structure
    assert (
        "tableau" in flat
        or "côte à côte" in flat
        or "côte-à-côte" in flat
    )


# === Vague A — structured citation format (stable for RAFT) ===


def test_vague_a_citation_format_documented():
    """Vague A adds a stable delimited citation format (##begin_quote##...)
    for factual chiffred claims. This format will be reused verbatim in
    RAFT training examples — any rename breaks the fine-tuned model."""
    assert "##begin_quote##" in SYSTEM_PROMPT
    assert "##end_quote##" in SYSTEM_PROMPT


def test_vague_a_no_oracle_refusal_documented():
    """Companion to ##begin_quote##: when a chiffred fact is absent from
    fiches, the model uses ##no_oracle##...##end_no_oracle## as a targeted
    exception to ANTI-CONFESSION (only for chiffred gaps, not qualitative)."""
    assert "##no_oracle##" in SYSTEM_PROMPT
    assert "##end_no_oracle##" in SYSTEM_PROMPT


def test_vague_a_citation_identifiers_listed():
    """The prompt must document which stable ids to cite (RNCP,
    cod_aff_form, FOR.XXXXX) so the LLM knows what goes in the
    (Source: ..., id_type: id_value) suffix."""
    assert "RNCP" in SYSTEM_PROMPT
    assert "cod_aff_form" in SYSTEM_PROMPT
    assert "FOR." in SYSTEM_PROMPT


def test_vague_a_no_oracle_does_not_violate_anti_confession():
    """The ##no_oracle## addition must cohabit with ANTI-CONFESSION without
    contradicting it: explicit carve-out (only for chiffred gaps, never
    opening the response, never qualitative)."""
    # The prompt must explicitly flag ##no_oracle## as an exception
    # rather than a general license to confess.
    lower = SYSTEM_PROMPT.lower()
    assert "exception" in lower, (
        "The prompt must mark ##no_oracle## as a targeted exception, "
        "not a general refusal pattern"
    )
    # ANTI-CONFESSION must still be present (no regression)
    assert "ANTI-CONFESSION" in SYSTEM_PROMPT


# === Sanity UX — α brièveté + β exploitation obligatoire des signaux ===


def test_sanity_ux_brevity_override():
    """Post-sanity-UX: priority rule overrides the ~1000 words target
    with a 300-500 words target for lycéen-first concision."""
    lower = SYSTEM_PROMPT.lower()
    assert "300-500 mots" in lower, (
        "Sanity UX must set an explicit 300-500 words override"
    )
    # The brevity rule must be marked as priority / override
    assert "priorit" in lower
    assert "lycéen" in lower


def test_sanity_ux_requires_cod_aff_form_citation():
    """Post-sanity-UX: model is instructed to cite cod_aff_form whenever
    it quotes a Parcoursup figure."""
    lower = SYSTEM_PROMPT.lower()
    assert "cod_aff_form" in lower
    # Explicitly forbidden: bare "Source: Parcoursup" without id
    assert "jamais" in lower or "obligatoire" in lower or "dois" in lower


def test_sanity_ux_requires_mentioning_trends():
    """Post-sanity-UX: the model is explicitly instructed to mention
    Tendance lines when they illuminate the recommendation."""
    lower = SYSTEM_PROMPT.lower()
    assert "tendance" in lower
    # Context: unique signal, no generalist LLM has it
    assert "unique" in lower or "propriétaire" in lower or "signal" in lower


def test_sanity_ux_preserves_plan_abc_structure():
    """Brevity must NOT kill the Plan A/B/C skeleton — only trim each
    plan to 2-3 lines instead of long paragraphs."""
    # Plan A/B/C references still exist somewhere in the prompt
    assert "Plan A" in SYSTEM_PROMPT
    assert "Plan B" in SYSTEM_PROMPT
    assert "Plan C" in SYSTEM_PROMPT


# === Tier 0 — règles dures post-user-feedback 2026-04-18 ===


def test_tier0_bans_femmes_as_positive_argument():
    """Tier 0 : le % de femmes ne doit JAMAIS être argument positif/négatif."""
    lower = SYSTEM_PROMPT.lower()
    # Le prompt doit contenir une interdiction explicite des formulations
    assert ("environnement solidaire" in lower
            or "environnement adapté" in lower
            or "environnement accessible" in lower), (
        "Le prompt doit citer explicitement les formulations interdites"
    )


def test_tier0_bans_admin_codes_in_output():
    """Tier 0 : cod_aff_form / RNCP / FOR.xxx ne doivent pas apparaître en
    clair dans la réponse LLM. Le prompt doit l'interdire explicitement."""
    lower = SYSTEM_PROMPT.lower()
    assert "cod_aff_form" in lower
    assert "codes administratifs" in lower or "pas apparaître" in lower
    # Le prompt recommande l'alternative : liens markdown cliquables
    assert "cliquable" in lower and "parcoursup" in lower


def test_tier0_anti_hallucination_list():
    """Les 6 erreurs factuelles identifiées par les testeurs doivent être
    explicitement listées comme interdites."""
    assert "MBA HEC" in SYSTEM_PROMPT
    assert "École 42" in SYSTEM_PROMPT or "42" in SYSTEM_PROMPT
    assert "VAP" in SYSTEM_PROMPT  # passerelle infirmier→kiné
    # Prépa médecine "2x"
    lower = SYSTEM_PROMPT.lower()
    assert "marketing" in lower or "auto-déclaré" in lower


def test_tier0_allows_realistic_refusal_over_template():
    """Le LLM doit pouvoir refuser un Plan A artificiel quand le profil
    ne le permet pas (ex : 11/20 visant HEC)."""
    lower = SYSTEM_PROMPT.lower()
    assert "fabrique pas" in lower or "pas réaliste" in lower


def test_tier0_includes_human_referral():
    """Renvoi humain (SCUIO / CIO / Psy-EN) doit être obligatoire."""
    lower = SYSTEM_PROMPT.lower()
    assert "psy-en" in lower or "scuio" in lower or "cio" in lower
