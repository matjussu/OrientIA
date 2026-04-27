"""Tests pour l'anti-hallucination Sprint 7 Action 3 :
- `src/prompt/system_strict.py` (levier 1 : prompt v3.3 strict)
- `src/rag/critic_loop.py` (levier 2 : critic loop 2-pass)

Levier 3 (structured output JSON {claim, source} citations inline) en
backlog Sprint 8 (modifs structurelles trop lourdes).
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock

from src.prompt.system import SYSTEM_PROMPT
from src.prompt.system_strict import (
    ANTI_HALLU_STRICT_APPENDIX,
    SYSTEM_PROMPT_V33_STRICT,
)
from src.rag.critic_loop import (
    CRITIC_LOOP_MODEL,
    CRITIC_LOOP_PROMPT,
    CriticLoop,
    CriticReport,
)


class TestSystemStrictExtendsV32:
    """Levier 1 — SYSTEM_PROMPT v3.3 strict = v3.2 + 5 règles."""

    def test_v32_unchanged_non_regression(self):
        """Non-régression critique : SYSTEM_PROMPT v3.2 ne doit PAS être
        modifié (protected file CLAUDE.md projet)."""
        # On vérifie juste qu'il existe et a un contenu non-vide
        assert SYSTEM_PROMPT
        assert len(SYSTEM_PROMPT) > 1000  # v3.2 est ~30k chars

    def test_v33_strict_contains_v32(self):
        """V3.3 strict commence par le contenu de v3.2."""
        assert SYSTEM_PROMPT_V33_STRICT.startswith(SYSTEM_PROMPT)

    def test_v33_strict_appends_anti_hallu_block(self):
        """V3.3 strict ajoute l'appendix anti-hallu après v3.2."""
        assert ANTI_HALLU_STRICT_APPENDIX in SYSTEM_PROMPT_V33_STRICT
        assert SYSTEM_PROMPT_V33_STRICT.endswith(ANTI_HALLU_STRICT_APPENDIX)

    def test_v33_strict_strictly_longer_than_v32(self):
        assert len(SYSTEM_PROMPT_V33_STRICT) > len(SYSTEM_PROMPT)


class TestAntiHalluRulesPresent:
    """Les 6 règles anti-hallu (R1-R6) sont présentes dans le prompt."""

    def test_r1_no_chiffre_without_source(self):
        assert "R1" in ANTI_HALLU_STRICT_APPENDIX
        assert "Aucun chiffre sans source identifiée" in ANTI_HALLU_STRICT_APPENDIX

    def test_r2_marqueur_estimation_obligatoire(self):
        assert "R2" in ANTI_HALLU_STRICT_APPENDIX
        assert "(estimation)" in ANTI_HALLU_STRICT_APPENDIX

    def test_r3_no_invent_sources(self):
        assert "R3" in ANTI_HALLU_STRICT_APPENDIX
        # Mention des sources interdites sans contexte (anti-CEREQ-2023 fabriqué)
        assert "CEREQ" in ANTI_HALLU_STRICT_APPENDIX
        assert "Glassdoor" in ANTI_HALLU_STRICT_APPENDIX

    def test_r4_anti_hallu_defensif_fourchette_url(self):
        assert "R4" in ANTI_HALLU_STRICT_APPENDIX
        assert "fourchette" in ANTI_HALLU_STRICT_APPENDIX.lower()
        assert "URL officielle" in ANTI_HALLU_STRICT_APPENDIX

    def test_r5_reformuler_plutot_inventer(self):
        assert "R5" in ANTI_HALLU_STRICT_APPENDIX
        assert "Reformuler" in ANTI_HALLU_STRICT_APPENDIX or "reformule" in ANTI_HALLU_STRICT_APPENDIX.lower()


class TestR6InlineCitationSprint7Action3b:
    """Sprint 7 Action 3b — R6 format obligatoire `[Source: ...]` après chaque chiffre.

    Variante pragmatique du Levier 3 structured output JSON. La vraie
    JSON parser-friendly reste backlog Sprint 8.
    """

    def test_r6_present_in_appendix(self):
        assert "R6" in ANTI_HALLU_STRICT_APPENDIX
        # Format obligatoire mentionné
        assert "[Source:" in ANTI_HALLU_STRICT_APPENDIX

    def test_r6_format_pattern_documented(self):
        """Le format `[Source: <nom fiche>]` est explicit."""
        assert "[Source: <nom" in ANTI_HALLU_STRICT_APPENDIX or "[Source:" in ANTI_HALLU_STRICT_APPENDIX

    def test_r6_examples_present(self):
        """Au moins 2-3 exemples concrets de citation pour aider le LLM."""
        # Exemples d'identifiants de source
        assert "DARES Métiers 2030" in ANTI_HALLU_STRICT_APPENDIX
        assert "Inserjeunes" in ANTI_HALLU_STRICT_APPENDIX
        assert "moncompteformation.gouv.fr" in ANTI_HALLU_STRICT_APPENDIX or "CPF" in ANTI_HALLU_STRICT_APPENDIX

    def test_r6_estimation_marker_for_unsourced(self):
        """R6 prévoit le cas pas-de-fiche : `[Source: connaissance générale, estimation]`."""
        # Couvre la combinaison R2 + R6
        assert "connaissance générale" in ANTI_HALLU_STRICT_APPENDIX

    def test_r6_explicit_correct_incorrect_examples(self):
        """R6 inclut un exemple correct ET incorrect pour clarifier le format attendu."""
        appendix = ANTI_HALLU_STRICT_APPENDIX
        assert "Exemple correct" in appendix
        assert "Exemple incorrect" in appendix or "incorrect" in appendix.lower()

    def test_r6_does_not_replace_r1_r5(self):
        """R6 s'AJOUTE à R1-R5, ne les remplace pas."""
        appendix = ANTI_HALLU_STRICT_APPENDIX
        # R1-R5 toujours présents (non-régression Action 3 originale)
        for r in ["R1", "R2", "R3", "R4", "R5"]:
            assert r in appendix
        # R6 explique sa relation aux autres
        assert "ne remplace pas R1-R5" in appendix or "s'ajoute" in appendix.lower() or "s'AJOUTE" in appendix


class TestCriticLoopInit:
    def test_default_model(self):
        client = MagicMock()
        critic = CriticLoop(client)
        assert critic.model == CRITIC_LOOP_MODEL
        assert critic.max_chars_fiches == 12000

    def test_custom_model(self):
        client = MagicMock()
        critic = CriticLoop(client, model="custom-model", max_chars_fiches=5000)
        assert critic.model == "custom-model"
        assert critic.max_chars_fiches == 5000


class TestCriticLoopPrompt:
    def test_prompt_mentions_response_corrected(self):
        """Le prompt définit le schéma JSON avec response_corrected."""
        assert "response_corrected" in CRITIC_LOOP_PROMPT
        assert "n_modifications" in CRITIC_LOOP_PROMPT
        assert "modifications_summary" in CRITIC_LOOP_PROMPT

    def test_prompt_anti_hallu_rules(self):
        """Le prompt contient les règles anti-hallu cohérentes avec v3.3 strict."""
        prompt_lower = CRITIC_LOOP_PROMPT.lower()
        assert "ne jamais inventer" in prompt_lower
        assert "(estimation)" in CRITIC_LOOP_PROMPT
        assert "fourchette" in prompt_lower or "anti-hallu" in prompt_lower


class TestCriticLoopReview:
    """Tests le `review()` avec mock Mistral (pas de call API réel)."""

    def _make_mock_client(self, response_corrected: str, n_mods: int = 1, summary: str = "test"):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "response_corrected": response_corrected,
            "n_modifications": n_mods,
            "modifications_summary": summary,
        })
        mock_client.chat.complete.return_value = mock_response
        return mock_client

    def test_review_returns_corrected_response(self):
        client = self._make_mock_client("Le CPF crédite environ 500€/an (estimation).", n_mods=1)
        critic = CriticLoop(client)
        report = critic.review(
            "Le CPF crédite 487€/an précisément.",
            sources=[{"fiche": {"nom": "CPF", "text": "Montants ~500€/an"}}],
        )
        assert "(estimation)" in report.response_corrected
        assert report.n_modifications == 1
        assert report.error is None

    def test_review_passthrough_on_empty_response(self):
        client = MagicMock()
        critic = CriticLoop(client)
        report = critic.review("", sources=[])
        # Pas d'appel Mistral pour empty response
        assert report.response_corrected == ""
        client.chat.complete.assert_not_called()

    def test_review_passthrough_on_api_error(self):
        client = MagicMock()
        client.chat.complete.side_effect = Exception("Network error")
        critic = CriticLoop(client)
        original = "Réponse originale avec 50% taux."
        report = critic.review(original, sources=[])
        # Passthrough : préserve la réponse originale en cas d'erreur
        assert report.response_corrected == original
        assert report.error is not None
        assert "Network error" in report.error

    def test_review_passthrough_on_invalid_json(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "pas du JSON"
        mock_client.chat.complete.return_value = mock_response

        critic = CriticLoop(mock_client)
        original = "Réponse avec 50%."
        report = critic.review(original, sources=[])
        # Passthrough : préserve la réponse originale
        assert report.response_corrected == original
        assert report.error is not None

    def test_review_uses_official_source_pattern(self):
        """Levier 2 cohérent avec Action 1 : reconnaît anti-hallu défensif."""
        sources = [{
            "fiche": {
                "nom": "Bourse CROUS",
                "text": "Montants approximatifs : 1080-5965€/an (2024-2025) ; "
                        "Source officielle : https://www.etudiant.gouv.fr/...",
            }
        }]
        # Le critic loop doit accepter une réponse qui cite la fourchette + URL
        client = self._make_mock_client(
            "La bourse CROUS varie de 1080 à 5965€ selon l'échelon "
            "(voir etudiant.gouv.fr).",
            n_mods=0,
            summary="aucune modification (anti-hallu défensif respecté)",
        )
        critic = CriticLoop(client)
        report = critic.review(
            "La bourse CROUS varie de 1080 à 5965€ selon l'échelon "
            "(voir etudiant.gouv.fr).",
            sources=sources,
        )
        assert report.n_modifications == 0


class TestCriticReportSchema:
    def test_default_values(self):
        report = CriticReport(
            response_corrected="test",
            response_original="test",
        )
        assert report.n_modifications == 0
        assert report.modifications_summary == ""
        assert report.error is None

    def test_with_modifications(self):
        report = CriticReport(
            response_corrected="corrected",
            response_original="original",
            n_modifications=3,
            modifications_summary="3 chiffres marqués (estimation)",
        )
        assert report.n_modifications == 3


class TestFormatFiches:
    """Le _format_fiches gère les 2 patterns de fiche (text dense vs
    formation classique avec champs structurés)."""

    def test_format_fiche_with_text(self):
        client = MagicMock()
        critic = CriticLoop(client)
        sources = [{"fiche": {"nom": "CPF", "text": "Le CPF crédite 500€/an..."}}]
        text = critic._format_fiches(sources)
        assert "CPF" in text
        assert "500€/an" in text

    def test_format_fiche_classique(self):
        client = MagicMock()
        critic = CriticLoop(client)
        sources = [{
            "fiche": {
                "nom": "BTS Compta",
                "etablissement": "Lycée Test",
                "taux_acces_parcoursup_2025": 25.5,
                "nombre_places": 30,
                "detail": "Formation comptabilité",
            },
        }]
        text = critic._format_fiches(sources)
        assert "BTS Compta" in text
        assert "Lycée Test" in text
        assert "25.5" in text or "25,5" in text

    def test_format_fiches_capped_max_chars(self):
        client = MagicMock()
        critic = CriticLoop(client, max_chars_fiches=200)
        sources = [{"fiche": {"nom": f"f{i}", "text": "X" * 500}} for i in range(5)]
        text = critic._format_fiches(sources)
        assert len(text) <= 200 + 50  # 200 + "[... tronqué ...]" suffix
