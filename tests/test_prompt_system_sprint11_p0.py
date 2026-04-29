"""Tests Sprint 11 P0 Item 1 — refonte SYSTEM_PROMPT avec 3 directives prioritaires.

Couvre :
- Strict Grounding directive (anti-hallucination factuelle)
- Glossaire Anti-Amnésie (réformes système éducatif FR récent)
- Progressive Disclosure (TL;DR 3 lignes / 3 pistes A/B/C / question retour)
- Backward compat : SYSTEM_PROMPT_V32_PHASE_F préservé pour Run F+G
- build_user_prompt révisé (instruction "Je n'ai pas l'information" vs ancien "passe directement")

Spec ordre Jarvis : 2026-04-29-1700-claudette-orientia-sprint11-P0-corrections-prompt-buffer-judge (Item 1).
"""
from __future__ import annotations

import pytest

from src.prompt.system import (
    SYSTEM_PROMPT,
    SYSTEM_PROMPT_SPRINT11_P0_PREFIX,
    SYSTEM_PROMPT_V32_PHASE_F,
    build_user_prompt,
)


# ──────────────────── (a) Strict Grounding directive ────────────────────


class TestDirectiveStrictGrounding:
    def test_keyword_exclusivement_present(self):
        assert "EXCLUSIVEMENT" in SYSTEM_PROMPT_SPRINT11_P0_PREFIX

    def test_keyword_strictement_interdit_present(self):
        assert "STRICTEMENT INTERDIT" in SYSTEM_PROMPT_SPRINT11_P0_PREFIX

    def test_pas_d_information_fallback_explicit(self):
        """Fallback explicite quand info manque, pas d'invention."""
        assert "Je n'ai pas l'information" in SYSTEM_PROMPT_SPRINT11_P0_PREFIX

    def test_revoque_connaissance_generale(self):
        """Le préfixe doit explicitement révoquer la permission v3.2."""
        assert "RÉVOQUÉE" in SYSTEM_PROMPT_SPRINT11_P0_PREFIX or "révoque" in SYSTEM_PROMPT_SPRINT11_P0_PREFIX.lower()
        # L'instruction (connaissance générale) du v3.2 doit être désactivée
        assert "connaissance générale" in SYSTEM_PROMPT_SPRINT11_P0_PREFIX  # mention pour la révoquer

    def test_anti_invention_diplomes_modalites_filieres(self):
        """4 catégories d'invention interdites (cf spec ordre Jarvis)."""
        prefix = SYSTEM_PROMPT_SPRINT11_P0_PREFIX
        # Au moins 3 des 4 catégories listées
        categories = ["diplômes", "modalités", "filières", "écoles", "chiffres"]
        present = sum(1 for c in categories if c in prefix.lower())
        assert present >= 4, f"Catégories invention interdites insuffisantes : {present}/5"


# ──────────────────── (b) Glossaire Anti-Amnésie ────────────────────


class TestDirectiveGlossaireAntiAmnesie:
    def test_attention_contexte_recent(self):
        """Marker explicite glossaire."""
        assert "ATTENTION CONTEXTE FRANÇAIS" in SYSTEM_PROMPT_SPRINT11_P0_PREFIX

    def test_series_l_es_s_supprimees(self):
        """Réforme bac 2021 — séries supprimées."""
        prefix = SYSTEM_PROMPT_SPRINT11_P0_PREFIX
        assert "L / ES / S" in prefix or "L/ES/S" in prefix
        assert "SUPPRIMÉES" in prefix or "supprimées" in prefix.lower()
        assert "spécialités" in prefix.lower()

    def test_terminale_l_disparue(self):
        """Cas hallu Q10 chantier E."""
        prefix = SYSTEM_PROMPT_SPRINT11_P0_PREFIX
        assert "Terminale L" in prefix or "« Terminale L »" in prefix

    def test_concours_ifsi_supprime(self):
        """Cas hallu Q5 chantier E — IFSI 2019."""
        prefix = SYSTEM_PROMPT_SPRINT11_P0_PREFIX
        assert "IFSI" in prefix
        assert "2019" in prefix
        assert "Parcoursup" in prefix

    def test_paces_remplacee_pass_las(self):
        """Études santé 2020."""
        prefix = SYSTEM_PROMPT_SPRINT11_P0_PREFIX
        assert "PACES" in prefix
        assert "PASS" in prefix
        assert "L.AS" in prefix

    def test_deamp_fusion_deaes(self):
        """Cas hallu Q8 chantier E — DEAMP fusion 2016."""
        prefix = SYSTEM_PROMPT_SPRINT11_P0_PREFIX
        assert "DEAMP" in prefix
        assert "DEAES" in prefix
        assert "2016" in prefix

    def test_dut_remplace_but(self):
        """Réforme 2021 DUT → BUT."""
        prefix = SYSTEM_PROMPT_SPRINT11_P0_PREFIX
        assert "DUT" in prefix
        assert "BUT" in prefix
        assert "2021" in prefix

    def test_manaa_supprimee_dn_made(self):
        """Métiers d'art 2019."""
        prefix = SYSTEM_PROMPT_SPRINT11_P0_PREFIX
        assert "MANAA" in prefix
        assert "DN MADE" in prefix

    def test_master_vs_mastere_specialise(self):
        """Distinction critique master Bac+5 vs mastère Bac+6 (correction Matteo 2026-04-29)."""
        prefix = SYSTEM_PROMPT_SPRINT11_P0_PREFIX
        assert "Master" in prefix
        assert "Mastère" in prefix
        assert "Bac+5" in prefix
        assert "Bac+6" in prefix

    def test_concours_ecoles_commerce_post_bac(self):
        """Acces / Sesame post-bac."""
        prefix = SYSTEM_PROMPT_SPRINT11_P0_PREFIX
        assert "Acces" in prefix or "Sesame" in prefix

    def test_concours_ecoles_inge_post_bac(self):
        """Geipi Polytech / Puissance Alpha / Avenir / Advance."""
        prefix = SYSTEM_PROMPT_SPRINT11_P0_PREFIX
        assert "Geipi" in prefix or "Puissance Alpha" in prefix


# ──────────────────── (c) Progressive Disclosure ────────────────────


class TestDirectiveProgressiveDisclosure:
    def test_tldr_3_lignes(self):
        prefix = SYSTEM_PROMPT_SPRINT11_P0_PREFIX
        assert "Règle 1" in prefix
        assert "TL;DR" in prefix
        assert "3 lignes" in prefix

    def test_3_pistes_non_detaillees(self):
        prefix = SYSTEM_PROMPT_SPRINT11_P0_PREFIX
        assert "Règle 2" in prefix
        assert "Plan A" in prefix
        assert "Plan B" in prefix
        assert "Plan C" in prefix

    def test_question_retour_obligatoire(self):
        prefix = SYSTEM_PROMPT_SPRINT11_P0_PREFIX
        assert "Règle 3" in prefix
        assert "Question retour" in prefix or "question retour" in prefix.lower()
        assert "OBLIGATOIRE" in prefix.upper()

    def test_interdiction_pavés(self):
        prefix = SYSTEM_PROMPT_SPRINT11_P0_PREFIX
        assert "INTERDICTION ABSOLUE" in prefix
        assert "Pavés" in prefix or "pavés" in prefix

    def test_target_word_count(self):
        """Cible explicite ≤250 mots pour mobile."""
        prefix = SYSTEM_PROMPT_SPRINT11_P0_PREFIX
        assert "250 mots" in prefix or "<= 250 mots" in prefix


# ──────────────────── (d) Backward compat archive v3.2 ────────────────────


class TestBackwardCompatV32:
    def test_v32_archive_exists(self):
        """v3.2 archive accessible pour reproducibilité Run F+G."""
        assert SYSTEM_PROMPT_V32_PHASE_F is not None
        assert isinstance(SYSTEM_PROMPT_V32_PHASE_F, str)
        assert len(SYSTEM_PROMPT_V32_PHASE_F) > 1000

    def test_v32_neutralite_principle_preserved(self):
        """Principes core v3.2 préservés."""
        assert "NEUTRALITÉ" in SYSTEM_PROMPT_V32_PHASE_F
        assert "RÉALISME" in SYSTEM_PROMPT_V32_PHASE_F
        assert "AGENTIVITÉ" in SYSTEM_PROMPT_V32_PHASE_F

    def test_default_system_prompt_includes_prefix_then_v32(self):
        """SYSTEM_PROMPT default = préfixe Sprint 11 P0 + corps v3.2."""
        assert SYSTEM_PROMPT.startswith(SYSTEM_PROMPT_SPRINT11_P0_PREFIX)
        assert SYSTEM_PROMPT_V32_PHASE_F in SYSTEM_PROMPT
        # Préfixe avant corps
        idx_prefix = SYSTEM_PROMPT.find(SYSTEM_PROMPT_SPRINT11_P0_PREFIX)
        idx_v32 = SYSTEM_PROMPT.find(SYSTEM_PROMPT_V32_PHASE_F)
        assert idx_prefix < idx_v32


# ──────────────────── (e) build_user_prompt révisé ────────────────────


class TestBuildUserPromptRevised:
    def test_fiches_rag_xml_balises(self):
        """Le user prompt utilise <fiches_rag> balises (best practice anti-injection)."""
        prompt = build_user_prompt("FICHE 1: Test", "Quelle question ?")
        assert "<fiches_rag>" in prompt
        assert "</fiches_rag>" in prompt

    def test_directives_priorities_referenced(self):
        prompt = build_user_prompt("FICHE 1: Test", "Q ?")
        assert "Strict Grounding" in prompt or "DIRECTIVES PRIORITAIRES" in prompt
        assert "EXCLUSIVEMENT" in prompt
        assert "Progressive Disclosure" in prompt or "TL;DR" in prompt or "≤250 mots" in prompt

    def test_anti_hallucination_explicit_in_user_prompt(self):
        prompt = build_user_prompt("FICHE 1: Test", "Q ?")
        assert "Je n'ai pas l'information" in prompt or "NE FABRIQUE PAS" in prompt

    def test_no_more_passe_directement_connaissances(self):
        """L'ancien wording « passe directement à tes connaissances générales » est SUPPRIMÉ."""
        prompt = build_user_prompt("FICHE 1: Test", "Q ?")
        assert "passe directement à tes connaissances" not in prompt
        assert "connaissances générales marquées" not in prompt

    def test_user_guidance_still_supported(self):
        """Backward compat Tier 2.2 user_guidance prefix."""
        prompt = build_user_prompt("FICHE 1: X", "Q ?", user_guidance="Profil détecté: lycéen indécis.")
        assert "Profil détecté" in prompt
        # Et toujours suivi du context fiches
        assert "<fiches_rag>" in prompt


# ──────────────────── (f) Override path pour Run F+G ────────────────────


class TestOverridePathForRunFG:
    def test_v32_phase_f_preserves_connaissance_generale_permission(self):
        """v3.2 archive préserve l'ancien comportement (connaissance générale autorisé).

        Run F+G futurs peuvent appeler `generate(system_prompt_override=SYSTEM_PROMPT_V32_PHASE_F)`
        pour reproduire l'ancien comportement strict."""
        assert "connaissance générale" in SYSTEM_PROMPT_V32_PHASE_F

    def test_default_system_prompt_revokes_via_prefix(self):
        """Default v4 contient ET la permission v3.2 ET la révocation préfixe."""
        # Permission v3.2 toujours dans le full prompt
        assert "connaissance générale" in SYSTEM_PROMPT
        # Mais préfixe la révoque explicitement (priorité haut du prompt)
        prefix_part = SYSTEM_PROMPT[:len(SYSTEM_PROMPT_SPRINT11_P0_PREFIX)]
        assert "RÉVOQUÉE" in prefix_part or "révoque" in prefix_part.lower()
