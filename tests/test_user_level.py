"""Rule-based user level classifier — Tier 2.2.

Maps a French orientation question to a user level class so the prompt
can adapt tone and content (terminal = simplified, master = pro language,
reconversion = respects prior experience). Fallback 'inconnu' when the
question lacks signal — critical for not making wrong assumptions.

Classes: terminale / licence / master / reconversion / inconnu.
"""
from __future__ import annotations

import pytest

from src.rag.user_level import (
    LEVEL_TERMINALE,
    LEVEL_LICENCE,
    LEVEL_MASTER,
    LEVEL_RECONVERSION,
    LEVEL_INCONNU,
    classify_user_level,
    level_to_guidance,
    UserLevelGuidance,
)


# --- Terminale ---

@pytest.mark.parametrize("q", [
    "Je suis en terminale générale, que choisir sur Parcoursup ?",
    "En terminale maths + NSI, quelles formations ?",
    "J'ai 11 de moyenne en terminale, puis-je viser HEC ?",
    "J'ai 17 ans, je passe le bac cette année.",
    "Terminale STMG, j'hésite entre BTS et licence.",
    "Je suis lycéen en Tle, quelles spécialités pour cyber ?",
    "Mon fils est en terminale, quelle stratégie Parcoursup ?",
    "Je prépare Parcoursup pour juin, que me conseilles-tu ?",
])
def test_classify_terminale(q):
    assert classify_user_level(q) == LEVEL_TERMINALE


# --- Licence ---

@pytest.mark.parametrize("q", [
    "Je suis en L2 d'économie-gestion à Paris 1.",
    "Étudiante en licence de droit, je veux me réorienter.",
    "En L3 informatique, quels masters viser ?",
    "Je suis en 2ème année de licence STAPS.",
    "Bac+2 en BTS SIO, quelles licences pro ?",
    "Après ma L1 MIASHS, est-ce que je peux passer en info ?",
    "En 3e année de bachelor marketing, je cherche un master.",
])
def test_classify_licence(q):
    assert classify_user_level(q) == LEVEL_LICENCE


# --- Master ---

@pytest.mark.parametrize("q", [
    "Je suis en M1 Informatique à Dauphine.",
    "Étudiant en master 2 de biologie, je veux une thèse.",
    "En M2, je cherche une alternance data scientist.",
    "Je prépare un master en droit public.",
    "Bac+4 en école de commerce, quelle spécialisation ?",
    "Je suis en deuxième année de master mathématiques appliquées.",
])
def test_classify_master(q):
    assert classify_user_level(q) == LEVEL_MASTER


# --- Reconversion ---

@pytest.mark.parametrize("q", [
    "Je veux me reconvertir dans la cybersécurité.",
    "J'ai 35 ans, je travaille depuis 10 ans dans la banque, retour aux études ?",
    "Après 8 ans comme infirmière, je cherche une reconversion.",
    "Je suis actuellement en poste comme comptable, je veux changer de métier.",
    "Reconversion pro vers le dev web à 40 ans, par où commencer ?",
    "Ancien cadre, je cherche une formation courte reconnue.",
    "J'ai quitté mon job, je veux reprendre des études à 30 ans.",
])
def test_classify_reconversion(q):
    assert classify_user_level(q) == LEVEL_RECONVERSION


# --- Inconnu (no signal or ambiguous) ---

@pytest.mark.parametrize("q", [
    "C'est quoi une licence ?",
    "Comment fonctionne Parcoursup ?",
    "Quelles formations pour devenir ingénieur ?",
    "Quels métiers dans la data science ?",
    "Compare ENSEIRB et EPITA.",
    "Je veux faire de l'informatique.",
    "",
    "   ",
])
def test_classify_inconnu(q):
    assert classify_user_level(q) == LEVEL_INCONNU


# --- Priority: reconversion wins over other weak signals ---

def test_reconversion_wins_over_bac_mention():
    """A 35-year-old mentioning 'j'ai eu mon bac il y a 15 ans' should
    still be classified reconversion, not terminale — the age/career
    markers are stronger signals."""
    q = "J'ai 35 ans, j'ai eu mon bac il y a 15 ans, je veux une reconversion en data."
    assert classify_user_level(q) == LEVEL_RECONVERSION


def test_master_wins_over_licence_mention():
    """A master student asking about their past licence should still be
    classified master — the current state takes precedence."""
    q = "Après ma licence de droit, je suis en M1 droit public."
    assert classify_user_level(q) == LEVEL_MASTER


# --- Robustness ---

def test_accent_insensitive():
    assert classify_user_level("terminale generale") == LEVEL_TERMINALE
    assert classify_user_level("TERMINALE") == LEVEL_TERMINALE


def test_whitespace_robust():
    assert classify_user_level("  Je suis en terminale.  ") == LEVEL_TERMINALE


# --- Guidance table (what the prompt gets instructed to do) ---


def test_guidance_has_all_levels():
    """level_to_guidance must return a UserLevelGuidance for every
    level constant — including LEVEL_INCONNU (no-op guidance)."""
    for level in (LEVEL_TERMINALE, LEVEL_LICENCE, LEVEL_MASTER,
                  LEVEL_RECONVERSION, LEVEL_INCONNU):
        g = level_to_guidance(level)
        assert isinstance(g, UserLevelGuidance)


def test_guidance_inconnu_is_non_intrusive():
    """When the level is unknown, the guidance must explicitly say
    'no assumption' — we must not silently default to terminale."""
    g = level_to_guidance(LEVEL_INCONNU)
    assert ("aucune hypothèse" in g.tone_instruction.lower() or
            "pas d'hypothèse" in g.tone_instruction.lower() or
            "n'assume" in g.tone_instruction.lower())


def test_guidance_terminale_mentions_lycee_register():
    """Terminale level guidance must tell the LLM to use a register
    adapted to a 17-year-old (tutoiement, simple vocabulary)."""
    g = level_to_guidance(LEVEL_TERMINALE)
    assert ("tutoi" in g.tone_instruction.lower() or
            "lycéen" in g.tone_instruction.lower() or
            "17 ans" in g.tone_instruction.lower())


def test_guidance_reconversion_respects_experience():
    """Reconversion level guidance must tell the LLM to respect prior
    professional experience (not infantilising, mentioning VAE/VAP)."""
    g = level_to_guidance(LEVEL_RECONVERSION)
    lower = g.tone_instruction.lower()
    assert ("expérience" in lower or "vae" in lower or "vap" in lower or
            "pro" in lower)


def test_build_user_prompt_accepts_guidance_prefix():
    """Tier 2.2 integration: build_user_prompt must accept an optional
    user_guidance parameter and prepend it to the final prompt."""
    from src.prompt.system import build_user_prompt
    result = build_user_prompt(
        "CTX", "Q", user_guidance="Profil détecté : TEST_MARKER."
    )
    assert "TEST_MARKER" in result
    # Guidance must appear before the data reference block
    assert result.index("TEST_MARKER") < result.index("Voici les données")


def test_build_user_prompt_backward_compat_no_guidance():
    """With default guidance="", the prompt structure must be unchanged
    (no empty lines shift, no broken downstream parsers)."""
    from src.prompt.system import build_user_prompt
    result = build_user_prompt("CTX", "Q")
    # No guidance marker
    assert "Profil détecté" not in result
    # Context and question still present
    assert "CTX" in result
    assert "Q" in result


def test_system_prompt_mentions_profil_detecte_rule():
    """T2.8 rule: the system prompt must acknowledge the Profil détecté
    prefix injected by the generator so the LLM actually respects it."""
    from src.prompt.system import SYSTEM_PROMPT
    lower = SYSTEM_PROMPT.lower()
    assert "profil détecté" in lower


def test_guidance_master_assumes_parcoursup_past():
    """At master level, Parcoursup is already behind. Guidance should
    not waste tokens explaining Parcoursup calendar to a M1 student."""
    g = level_to_guidance(LEVEL_MASTER)
    lower = g.tone_instruction.lower()
    assert ("pas parcoursup" in lower or "parcoursup" in lower and
            ("dépassé" in lower or "passé" in lower or "arrière" in lower or
             "non pertinent" in lower))
