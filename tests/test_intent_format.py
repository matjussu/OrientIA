"""Tier 2.3 — intent-to-format guidance.

classify_intent already drives retrieval (top_k_sources + mmr_lambda).
Tier 2.3 adds a parallel function intent_to_format_guidance that drives
the generation format (table vs Plan A/B/C, didactic vs actionable,
etc.) by injecting a hint into the user prompt.

The format rules themselves are already in SYSTEM_PROMPT (comparaison
→ tableau, conceptual → didactique, découverte → sortir des fiches,
etc.). This classifier only *tells the LLM which rule applies* — the
LLM can otherwise struggle to self-detect the intent reliably.
"""
from __future__ import annotations

import pytest

from src.rag.intent import (
    INTENT_COMPARAISON,
    INTENT_CONCEPTUAL,
    INTENT_DECOUVERTE,
    INTENT_GENERAL,
    INTENT_GEOGRAPHIC,
    INTENT_PASSERELLES,
    INTENT_REALISME,
    intent_to_format_guidance,
)


ALL_INTENTS = [
    INTENT_COMPARAISON,
    INTENT_CONCEPTUAL,
    INTENT_DECOUVERTE,
    INTENT_GEOGRAPHIC,
    INTENT_PASSERELLES,
    INTENT_REALISME,
    INTENT_GENERAL,
]


@pytest.mark.parametrize("intent", ALL_INTENTS)
def test_every_intent_has_guidance(intent):
    """Every intent constant must map to a non-empty guidance string."""
    g = intent_to_format_guidance(intent)
    assert isinstance(g, str)
    assert len(g) > 20, f"Guidance for {intent} is suspiciously short"


def test_unknown_intent_falls_back_to_general():
    """Typo-safe: unknown intent returns the general guidance."""
    assert intent_to_format_guidance("bogus") == intent_to_format_guidance(
        INTENT_GENERAL
    )


def test_comparaison_guidance_mentions_table():
    g = intent_to_format_guidance(INTENT_COMPARAISON).lower()
    assert "tableau" in g or "côte à côte" in g or "côte-à-côte" in g


def test_conceptual_guidance_forbids_plan_abc():
    g = intent_to_format_guidance(INTENT_CONCEPTUAL).lower()
    assert "plan a" not in g or "pas de plan" in g or "sans plan" in g
    # Must indicate didactic / explanation mode
    assert ("didactique" in g or "explication" in g or
            "définition" in g or "concept" in g)


def test_decouverte_guidance_allows_out_of_corpus():
    """Découverte questions often don't match the fiches — the guidance
    must encourage the LLM to go broad in (connaissance générale)."""
    g = intent_to_format_guidance(INTENT_DECOUVERTE).lower()
    assert ("sors du corpus" in g or "hors" in g or
            "interdisciplinaire" in g or
            "connaissance générale" in g or
            "au-delà" in g)


def test_realisme_guidance_wants_direct_chiffré():
    g = intent_to_format_guidance(INTENT_REALISME).lower()
    assert ("direct" in g or "cash" in g or "franc" in g)
    assert ("chiffr" in g or "taux" in g or "données" in g)


def test_geographic_guidance_enforces_distinct_cities():
    g = intent_to_format_guidance(INTENT_GEOGRAPHIC).lower()
    assert ("villes distinctes" in g or "ville distincte" in g or
            "≥ 3" in g or "au moins 3" in g or
            "proximit" in g)


def test_passerelles_guidance_names_intermediate_steps():
    g = intent_to_format_guidance(INTENT_PASSERELLES).lower()
    assert ("passerelle" in g or "étape" in g or
            "intermédiaire" in g or "chemin" in g)


# --- System prompt must acknowledge the Intent marker (T2.9) ---


def test_system_prompt_has_t2_9_intent_rule():
    """System prompt must tell the LLM to respect the 'Type de question
    détecté' marker injected by the generator."""
    from src.prompt.system import SYSTEM_PROMPT
    lower = SYSTEM_PROMPT.lower()
    assert ("type de question détecté" in lower or
            "intention détectée" in lower or
            "intent détecté" in lower or
            "question détectée" in lower)
