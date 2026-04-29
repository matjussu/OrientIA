"""Tests Sprint 11 P0 Item 2 — buffer mémoire short-term (history).

Couvre :
- pipeline.answer(history=None) → comportement v1 strict (backward compat)
- pipeline.answer(history=[]) → équivalent None
- pipeline.answer(history=[5 msgs]) → injection correcte dans messages array
- generate(history=...) → format Mistral compliant : system → history → user
- Suivi conversation à tiroirs : "Oui Plan A" → second answer cohérent (mock)
- Filtrage messages malformés (role invalide / content vide)
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.rag.metadata_filter import FilterCriteria
from src.rag.pipeline import OrientIAPipeline


# ─────────────────── Fixtures ───────────────────


@pytest.fixture
def fake_fiches():
    return [
        {"id": 1, "nom": "Test Fiche 1", "etablissement": "Test", "ville": "Lyon"},
        {"id": 2, "nom": "Test Fiche 2", "etablissement": "Test2", "ville": "Paris"},
    ]


@pytest.fixture
def pipeline_mock(fake_fiches):
    pipe = OrientIAPipeline(client=MagicMock(), fiches=fake_fiches)
    pipe.index = MagicMock()
    return pipe


def _wrap(fiches):
    return [{"fiche": f, "score": 0.9, "base_score": 0.9, "embedding": np.zeros(1024)} for f in fiches]


# ─────────────────── (a) backward compat ───────────────────


class TestBackwardCompatNoHistory:
    def test_answer_default_history_none(self, pipeline_mock, fake_fiches):
        """Default `history=None` → comportement v1 strict identique."""
        captured = {}

        def fake_complete(model, temperature, messages):
            captured["messages"] = messages
            r = MagicMock()
            r.choices = [MagicMock(message=MagicMock(content="answer"))]
            return r

        pipeline_mock.client.chat.complete = fake_complete

        with patch("src.rag.pipeline.retrieve_top_k", return_value=_wrap(fake_fiches)):
            with patch("src.rag.pipeline.rerank", side_effect=lambda r, *a, **k: r):
                pipeline_mock.answer("Quelle question ?")

        # messages array = [system, user] uniquement (pas de history)
        roles = [m["role"] for m in captured["messages"]]
        assert roles == ["system", "user"]

    def test_answer_explicit_none_equivalent_default(self, pipeline_mock, fake_fiches):
        captured = {}

        def fake_complete(model, temperature, messages):
            captured["messages"] = messages
            r = MagicMock()
            r.choices = [MagicMock(message=MagicMock(content="answer"))]
            return r

        pipeline_mock.client.chat.complete = fake_complete

        with patch("src.rag.pipeline.retrieve_top_k", return_value=_wrap(fake_fiches)):
            with patch("src.rag.pipeline.rerank", side_effect=lambda r, *a, **k: r):
                pipeline_mock.answer("Q", history=None)

        roles = [m["role"] for m in captured["messages"]]
        assert roles == ["system", "user"]

    def test_answer_empty_list_equivalent_none(self, pipeline_mock, fake_fiches):
        """history=[] → no-op, équivalent à None pour Run F+G reproducibility."""
        captured = {}

        def fake_complete(model, temperature, messages):
            captured["messages"] = messages
            r = MagicMock()
            r.choices = [MagicMock(message=MagicMock(content="answer"))]
            return r

        pipeline_mock.client.chat.complete = fake_complete

        with patch("src.rag.pipeline.retrieve_top_k", return_value=_wrap(fake_fiches)):
            with patch("src.rag.pipeline.rerank", side_effect=lambda r, *a, **k: r):
                pipeline_mock.answer("Q", history=[])

        roles = [m["role"] for m in captured["messages"]]
        assert roles == ["system", "user"]


# ─────────────────── (b) history injection ───────────────────


class TestHistoryInjection:
    def test_5_messages_injected_in_messages_array(self, pipeline_mock, fake_fiches):
        captured = {}

        def fake_complete(model, temperature, messages):
            captured["messages"] = messages
            r = MagicMock()
            r.choices = [MagicMock(message=MagicMock(content="answer 6"))]
            return r

        pipeline_mock.client.chat.complete = fake_complete

        history = [
            {"role": "user", "content": "Bonjour"},
            {"role": "assistant", "content": "Salut, comment puis-je t'aider ?"},
            {"role": "user", "content": "Je veux faire de l'info"},
            {"role": "assistant", "content": "Voici 3 pistes (A, B, C)"},
            {"role": "user", "content": "Plus de détails sur A ?"},
        ]

        with patch("src.rag.pipeline.retrieve_top_k", return_value=_wrap(fake_fiches)):
            with patch("src.rag.pipeline.rerank", side_effect=lambda r, *a, **k: r):
                pipeline_mock.answer("OK go", history=history)

        # 1 system + 5 history + 1 user = 7 messages
        msgs = captured["messages"]
        assert len(msgs) == 7
        roles = [m["role"] for m in msgs]
        assert roles == ["system", "user", "assistant", "user", "assistant", "user", "user"]

        # Premier message system contient SYSTEM_PROMPT
        assert msgs[0]["role"] == "system"

        # Messages 1-5 sont l'history exact
        assert msgs[1]["content"] == "Bonjour"
        assert msgs[5]["content"] == "Plus de détails sur A ?"

        # Dernier message user = question courante (avec context fiches injecté via build_user_prompt)
        last = msgs[-1]
        assert last["role"] == "user"
        assert "OK go" in last["content"]  # question présente dans user prompt


class TestHistoryFiltering:
    def test_invalid_role_filtered(self, pipeline_mock, fake_fiches):
        captured = {}

        def fake_complete(model, temperature, messages):
            captured["messages"] = messages
            r = MagicMock()
            r.choices = [MagicMock(message=MagicMock(content="answer"))]
            return r

        pipeline_mock.client.chat.complete = fake_complete

        history = [
            {"role": "user", "content": "valid"},
            {"role": "system", "content": "INVALID role doit être filtered"},  # ← skip
            {"role": "tool", "content": "INVALID role"},  # ← skip
            {"role": "assistant", "content": "valid response"},
        ]

        with patch("src.rag.pipeline.retrieve_top_k", return_value=_wrap(fake_fiches)):
            with patch("src.rag.pipeline.rerank", side_effect=lambda r, *a, **k: r):
                pipeline_mock.answer("Q", history=history)

        msgs = captured["messages"]
        # 1 system + 2 valid history (user + assistant) + 1 user current = 4
        assert len(msgs) == 4
        roles = [m["role"] for m in msgs[1:-1]]  # entre system et user current
        assert roles == ["user", "assistant"]

    def test_empty_content_filtered(self, pipeline_mock, fake_fiches):
        captured = {}

        def fake_complete(model, temperature, messages):
            captured["messages"] = messages
            r = MagicMock()
            r.choices = [MagicMock(message=MagicMock(content="answer"))]
            return r

        pipeline_mock.client.chat.complete = fake_complete

        history = [
            {"role": "user", "content": "valid"},
            {"role": "assistant", "content": ""},  # ← skip empty
            {"role": "user", "content": None},  # ← skip None (not str)
            {"role": "assistant", "content": "valid 2"},
        ]

        with patch("src.rag.pipeline.retrieve_top_k", return_value=_wrap(fake_fiches)):
            with patch("src.rag.pipeline.rerank", side_effect=lambda r, *a, **k: r):
                pipeline_mock.answer("Q", history=history)

        msgs = captured["messages"]
        # 1 system + 2 valid + 1 user current = 4
        assert len(msgs) == 4


# ─────────────────── (c) suivi conversation à tiroirs (intégration) ───────────────────


class TestConversationFollowUp:
    """Test pattern utilisateur : message 2 = "Oui Plan A" → réponse doit
    développer le Plan A précédemment mentionné. Ici on vérifie que l'history
    contient la réponse précédente du bot (donc Mistral a accès au context Plan A)."""

    def test_followup_oui_plan_a(self, pipeline_mock, fake_fiches):
        captured_messages = []

        def fake_complete(model, temperature, messages):
            captured_messages.append(messages)
            r = MagicMock()
            r.choices = [MagicMock(message=MagicMock(content="developpé Plan A"))]
            return r

        pipeline_mock.client.chat.complete = fake_complete

        with patch("src.rag.pipeline.retrieve_top_k", return_value=_wrap(fake_fiches)):
            with patch("src.rag.pipeline.rerank", side_effect=lambda r, *a, **k: r):
                # Tour 1
                ans1, _ = pipeline_mock.answer("Je veux faire de l'info, alternatives ?")
                # Tour 2 avec history
                history = [
                    {"role": "user", "content": "Je veux faire de l'info, alternatives ?"},
                    {"role": "assistant", "content": ans1},
                ]
                ans2, _ = pipeline_mock.answer("Oui Plan A", history=history)

        # Tour 2 messages doit inclure les 2 messages de history
        msgs_tour2 = captured_messages[1]
        roles_tour2 = [m["role"] for m in msgs_tour2]
        assert roles_tour2 == ["system", "user", "assistant", "user"]

        # Le user message tour 2 contient bien "Oui Plan A"
        assert "Oui Plan A" in msgs_tour2[-1]["content"]
        # Et l'history de tour 1 est présente
        assert "alternatives" in msgs_tour2[1]["content"]


# ─────────────────── (d) generate() history direct ───────────────────


class TestGenerateHistoryDirect:
    """Test direct generate() function (sans pipeline)."""

    def test_generate_default_no_history(self):
        from src.rag.generator import generate

        captured = {}

        def fake_complete(model, temperature, messages):
            captured["messages"] = messages
            r = MagicMock()
            r.choices = [MagicMock(message=MagicMock(content="ok"))]
            return r

        client = MagicMock()
        client.chat.complete = fake_complete

        retrieved = [{"fiche": {"nom": "F"}, "score": 1.0}]
        generate(client, retrieved, "Q?")

        assert len(captured["messages"]) == 2  # system + user

    def test_generate_with_history(self):
        from src.rag.generator import generate

        captured = {}

        def fake_complete(model, temperature, messages):
            captured["messages"] = messages
            r = MagicMock()
            r.choices = [MagicMock(message=MagicMock(content="ok"))]
            return r

        client = MagicMock()
        client.chat.complete = fake_complete

        retrieved = [{"fiche": {"nom": "F"}, "score": 1.0}]
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        generate(client, retrieved, "Q?", history=history)

        msgs = captured["messages"]
        assert len(msgs) == 4  # system + 2 history + user
        assert msgs[1]["role"] == "user" and msgs[1]["content"] == "Hello"
        assert msgs[2]["role"] == "assistant" and msgs[2]["content"] == "Hi"
