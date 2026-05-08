"""Tests src/rag/scope_classifier.py — gating amont pipeline.

Tests :
- Pré-filter regex urgent (signaux forts non-ambigus)
- Mode dégradé sans LLM (default in_scope safe)
- Réponses pré-écrites cohérentes
- Format JSON parsing robuste
- Mock LLM Mistral pour les 3 verdicts
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from src.rag.scope_classifier import (
    OUT_OF_SCOPE_RESPONSE,
    URGENT_RESPONSE,
    ScopeClassifier,
    ScopeResult,
    detect_urgent_signals_regex,
)


# ─────────────── Regex urgent pré-filter ───────────────


class TestRegexUrgent:
    def test_suicide_explicit_matched(self):
        assert detect_urgent_signals_regex("je veux me suicider")
        assert detect_urgent_signals_regex("j'ai des pensées suicidaires")
        assert detect_urgent_signals_regex("je vais en finir avec la vie")

    def test_violence_explicit_matched(self):
        assert detect_urgent_signals_regex("je suis battu par mon père")
        assert detect_urgent_signals_regex("violences conjugales depuis 2 ans")

    def test_disparaitre_pour_de_bon_matched(self):
        assert detect_urgent_signals_regex("je veux disparaître pour de bon")

    def test_normal_question_not_matched(self):
        assert not detect_urgent_signals_regex("je veux faire un BTS info")
        assert not detect_urgent_signals_regex("comment intégrer Sciences Po ?")
        assert not detect_urgent_signals_regex("j'ai 11 de moyenne pour HEC ?")

    def test_indirect_distress_NOT_caught_by_regex(self):
        """Les formulations indirectes type 'à quoi bon' doivent passer
        par le LLM, pas le regex (qui est conservateur sur les signaux clairs)."""
        assert not detect_urgent_signals_regex("à quoi bon faire des études")
        assert not detect_urgent_signals_regex("j'en peux plus de l'école")


# ─────────────── ScopeClassifier sans LLM (mode dégradé) ───────────────


class TestScopeClassifierWithoutClient:
    def test_urgent_regex_caught_without_llm(self):
        clf = ScopeClassifier(client=None)
        res = clf.classify("je veux me suicider")
        assert res.label == "urgent"
        assert res.via == "regex_urgent"
        assert res.pre_written_response == URGENT_RESPONSE

    def test_no_llm_default_in_scope(self):
        """Sans LLM, défaut conservateur = in_scope (laisse le pipeline gérer)."""
        clf = ScopeClassifier(client=None)
        res = clf.classify("quelle est la météo demain ?")
        assert res.label == "in_scope"
        assert res.via == "fallback_in_scope"
        assert res.pre_written_response is None

    def test_empty_question_out_of_scope(self):
        clf = ScopeClassifier(client=None)
        res = clf.classify("")
        assert res.label == "out_of_scope"
        assert res.pre_written_response == OUT_OF_SCOPE_RESPONSE


# ─────────────── ScopeClassifier avec LLM mocké ───────────────


def _mock_llm_returning(label: str, reason: str = "test"):
    """Construit un client Mistral mocké qui retourne le label voulu."""
    client = MagicMock()
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(
        content=json.dumps({"label": label, "reason": reason})
    ))]
    client.chat.complete.return_value = response
    return client


class TestScopeClassifierWithLLM:
    def test_in_scope_passes_through(self):
        client = _mock_llm_returning("in_scope", "orientation question")
        clf = ScopeClassifier(client=client)
        res = clf.classify("Quelles écoles d'ingénieur en Bretagne ?")
        assert res.label == "in_scope"
        assert res.via == "llm"
        assert res.pre_written_response is None

    def test_out_of_scope_returns_pre_written(self):
        client = _mock_llm_returning("out_of_scope", "cooking")
        clf = ScopeClassifier(client=client)
        res = clf.classify("recette de gâteau au chocolat ?")
        assert res.label == "out_of_scope"
        assert res.via == "llm"
        assert res.pre_written_response == OUT_OF_SCOPE_RESPONSE

    def test_urgent_via_llm_indirect(self):
        """LLM rattrape les formulations indirectes type 'j'en peux plus'."""
        client = _mock_llm_returning("urgent", "detresse psychologique")
        clf = ScopeClassifier(client=client)
        res = clf.classify("j'en peux plus, à quoi bon continuer")
        assert res.label == "urgent"
        assert res.via == "llm"
        assert res.pre_written_response == URGENT_RESPONSE

    def test_llm_error_falls_back_to_in_scope(self):
        """LLM API échoue → default in_scope (pipeline gère honnêtement)."""
        client = MagicMock()
        client.chat.complete.side_effect = RuntimeError("API down")
        clf = ScopeClassifier(client=client)
        res = clf.classify("quelle formation choisir ?")
        assert res.label == "in_scope"
        assert res.via == "fallback_in_scope"

    def test_llm_returns_invalid_label_falls_back(self):
        client = _mock_llm_returning("garbage_label", "test")
        clf = ScopeClassifier(client=client)
        res = clf.classify("test ?")
        assert res.label == "in_scope"  # safe default

    def test_llm_returns_invalid_json_falls_back(self):
        client = MagicMock()
        response = MagicMock()
        response.choices = [MagicMock(message=MagicMock(content="not json at all"))]
        client.chat.complete.return_value = response
        clf = ScopeClassifier(client=client)
        res = clf.classify("test ?")
        assert res.label == "in_scope"

    def test_regex_urgent_short_circuits_before_llm(self):
        """Si regex match urgent, on ne fait PAS appel LLM (gain latency)."""
        client = MagicMock()
        clf = ScopeClassifier(client=client)
        res = clf.classify("je veux me suicider")
        assert res.label == "urgent"
        assert res.via == "regex_urgent"
        client.chat.complete.assert_not_called()


# ─────────────── Réponses pré-écrites ───────────────


class TestPreWrittenResponses:
    def test_urgent_response_lists_3114(self):
        assert "3114" in URGENT_RESPONSE

    def test_urgent_response_lists_3919(self):
        assert "3919" in URGENT_RESPONSE

    def test_urgent_response_lists_119(self):
        assert "119" in URGENT_RESPONSE

    def test_urgent_response_recognizes_distress(self):
        assert "détresse" in URGENT_RESPONSE.lower()

    def test_out_of_scope_response_redirects_to_orientation(self):
        assert "orientation" in OUT_OF_SCOPE_RESPONSE.lower()
        assert "post-bac" in OUT_OF_SCOPE_RESPONSE.lower()

    def test_out_of_scope_gives_examples(self):
        """Pour aider l'utilisateur à reformuler, on donne 3 exemples concrets."""
        assert OUT_OF_SCOPE_RESPONSE.count("«") >= 3
