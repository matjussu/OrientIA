"""Tests src/agent/agent.py — Agent loop with mocked Mistral."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from src.agent.agent import Agent, AgentRunResult
from src.agent.tool import Tool, ToolRegistry


@pytest.fixture
def echo_tool():
    return Tool(
        name="echo",
        description="Echo back.",
        parameters={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
        func=lambda text: {"echoed": text},
    )


def _mock_response_with_tool_call(tool_name: str, args: dict, tool_id: str = "call_1"):
    tc = MagicMock()
    tc.id = tool_id
    tc.function.name = tool_name
    tc.function.arguments = json.dumps(args)

    msg = MagicMock()
    msg.tool_calls = [tc]
    msg.content = ""

    response = MagicMock()
    response.choices = [MagicMock(message=msg)]
    return response


def _mock_response_final(content: str):
    msg = MagicMock()
    msg.tool_calls = None
    msg.content = content
    response = MagicMock()
    response.choices = [MagicMock(message=msg)]
    return response


class TestAgentRun:
    def test_zero_tool_calls_direct_answer(self):
        """L'agent peut composer une réponse directement sans tool."""
        client = MagicMock()
        client.chat.complete.return_value = _mock_response_final(
            "Une licence est un diplôme bac+3."
        )
        agent = Agent(client=client, registry=ToolRegistry())
        result = agent.run("C'est quoi une licence ?")
        assert result.success is True
        assert result.answer == "Une licence est un diplôme bac+3."
        assert result.tool_calls_made == []
        assert result.iterations == 1

    def test_one_tool_call_then_final(self, echo_tool):
        client = MagicMock()
        client.chat.complete.side_effect = [
            _mock_response_with_tool_call("echo", {"text": "hello"}),
            _mock_response_final("Voici l'écho : hello"),
        ]
        registry = ToolRegistry()
        registry.register(echo_tool)
        agent = Agent(client=client, registry=registry)
        result = agent.run("Echo 'hello'")
        assert result.success is True
        assert result.answer == "Voici l'écho : hello"
        assert len(result.tool_calls_made) == 1
        assert result.tool_calls_made[0]["name"] == "echo"
        assert result.tool_calls_made[0]["result"] == {"echoed": "hello"}
        assert result.iterations == 2

    def test_unknown_tool_call_returns_error_in_result(self, echo_tool):
        """Si Mistral hallucine un tool inconnu, le dispatcher renvoie un error dict."""
        client = MagicMock()
        client.chat.complete.side_effect = [
            _mock_response_with_tool_call("nonexistent", {"foo": "bar"}),
            _mock_response_final("Désolé, le tool n'existe pas."),
        ]
        registry = ToolRegistry()
        registry.register(echo_tool)
        agent = Agent(client=client, registry=registry)
        result = agent.run("test")
        assert result.success is True
        assert result.tool_calls_made[0]["result"]["error"] == "unknown_tool"

    def test_max_iterations_reached(self, echo_tool):
        """Si Mistral fait des tool calls en boucle, on arrête à max_iterations."""
        client = MagicMock()
        # Toujours retourner un tool call → boucle infinie virtuelle
        client.chat.complete.return_value = _mock_response_with_tool_call(
            "echo", {"text": "loop"}
        )
        registry = ToolRegistry()
        registry.register(echo_tool)
        agent = Agent(client=client, registry=registry, max_iterations=3)
        result = agent.run("test")
        assert result.success is False
        assert result.error == "max_iterations_reached"
        assert result.iterations == 3
        assert len(result.tool_calls_made) == 3

    def test_mistral_api_exception_handled(self):
        client = MagicMock()
        client.chat.complete.side_effect = ConnectionError("Mistral down")
        agent = Agent(client=client, registry=ToolRegistry())
        result = agent.run("test")
        assert result.success is False
        assert "ConnectionError" in result.error
        assert "Mistral down" in result.error

    def test_tool_call_with_invalid_json_args(self, echo_tool):
        client = MagicMock()
        # Tool call avec args JSON invalides
        tc = MagicMock()
        tc.id = "call_bad"
        tc.function.name = "echo"
        tc.function.arguments = "{invalid json"
        msg = MagicMock()
        msg.tool_calls = [tc]
        msg.content = ""
        bad_response = MagicMock()
        bad_response.choices = [MagicMock(message=msg)]
        client.chat.complete.side_effect = [
            bad_response,
            _mock_response_final("Erreur tool args"),
        ]
        registry = ToolRegistry()
        registry.register(echo_tool)
        agent = Agent(client=client, registry=registry)
        result = agent.run("test")
        assert result.success is True
        assert result.tool_calls_made[0]["result"]["error"] == "json_parse_failed"


class TestAgentRunResult:
    def test_default_values(self):
        r = AgentRunResult(answer="hi")
        assert r.tool_calls_made == []
        assert r.iterations == 0
        assert r.success is True
        assert r.error is None
