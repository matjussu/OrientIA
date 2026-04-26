"""Tests src/agent/streaming.py — stream_chat_completion (mocked)."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.agent.streaming import (
    accumulate_streamed_response,
    stream_chat_completion,
)


def _mock_chunk(content: str | None):
    """Mock un event Mistral stream avec event.data.choices[0].delta.content."""
    delta = MagicMock()
    delta.content = content
    choice = MagicMock()
    choice.delta = delta
    data = MagicMock()
    data.choices = [choice]
    event = MagicMock()
    event.data = data
    return event


def _mock_chunk_alt(content: str | None):
    """Mock un event sans event.data (format alternatif/legacy)."""
    delta = MagicMock()
    delta.content = content
    choice = MagicMock()
    choice.delta = delta
    event = MagicMock(spec=["choices"])
    event.choices = [choice]
    # Pas d'attr `data`
    return event


class TestStreamChatCompletion:
    def test_yields_chunks(self):
        client = MagicMock()
        client.chat.stream.return_value = iter([
            _mock_chunk("Hello"),
            _mock_chunk(" "),
            _mock_chunk("world"),
        ])
        chunks = list(stream_chat_completion(client, "test-model", [{"role": "user", "content": "hi"}]))
        assert chunks == ["Hello", " ", "world"]

    def test_skips_empty_content(self):
        client = MagicMock()
        client.chat.stream.return_value = iter([
            _mock_chunk("Hello"),
            _mock_chunk(None),  # delta sans content
            _mock_chunk(""),  # content vide → skip aussi
            _mock_chunk("world"),
        ])
        chunks = list(stream_chat_completion(client, "m", []))
        assert chunks == ["Hello", "world"]

    def test_skips_empty_choices(self):
        client = MagicMock()
        # Event sans choices
        event_no_choices = MagicMock()
        event_no_choices.data.choices = []
        client.chat.stream.return_value = iter([
            event_no_choices,
            _mock_chunk("Hello"),
        ])
        chunks = list(stream_chat_completion(client, "m", []))
        assert chunks == ["Hello"]

    def test_passes_max_tokens_temperature(self):
        client = MagicMock()
        client.chat.stream.return_value = iter([])
        list(stream_chat_completion(
            client, "m", [], max_tokens=100, temperature=0.7
        ))
        # Vérifie que les kwargs ont été passés
        call_kwargs = client.chat.stream.call_args[1]
        assert call_kwargs["max_tokens"] == 100
        assert call_kwargs["temperature"] == 0.7

    def test_omits_optional_kwargs_when_none(self):
        client = MagicMock()
        client.chat.stream.return_value = iter([])
        list(stream_chat_completion(client, "m", []))
        call_kwargs = client.chat.stream.call_args[1]
        assert "max_tokens" not in call_kwargs
        assert "temperature" not in call_kwargs


class TestAccumulateStreamedResponse:
    def test_accumulate_basic(self):
        client = MagicMock()
        client.chat.stream.return_value = iter([
            _mock_chunk("Bon"),
            _mock_chunk("jour "),
            _mock_chunk("Matteo"),
        ])
        result = accumulate_streamed_response(client, "m", [])
        assert result == "Bonjour Matteo"

    def test_accumulate_empty_stream(self):
        client = MagicMock()
        client.chat.stream.return_value = iter([])
        assert accumulate_streamed_response(client, "m", []) == ""

    def test_accumulate_passes_kwargs(self):
        client = MagicMock()
        client.chat.stream.return_value = iter([_mock_chunk("X")])
        result = accumulate_streamed_response(client, "m", [], max_tokens=50)
        assert result == "X"
        assert client.chat.stream.call_args[1]["max_tokens"] == 50
