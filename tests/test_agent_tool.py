"""Tests src/agent/tool.py — Tool + ToolRegistry."""
from __future__ import annotations

import pytest

from src.agent.tool import Tool, ToolRegistry


# --- Fixtures ---


@pytest.fixture
def echo_tool():
    """Tool minimal qui renvoie ses paramètres."""
    return Tool(
        name="echo",
        description="Echoes back the message and optional region.",
        parameters={
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "region": {"type": "string"},
            },
            "required": ["message"],
        },
        func=lambda message, region=None: {"echoed": message, "region": region},
    )


@pytest.fixture
def add_tool():
    """Tool qui additionne deux nombres."""
    return Tool(
        name="add",
        description="Adds two integers.",
        parameters={
            "type": "object",
            "properties": {
                "a": {"type": "integer"},
                "b": {"type": "integer"},
            },
            "required": ["a", "b"],
        },
        func=lambda a, b: {"sum": a + b},
    )


# --- Tool ---


class TestTool:
    def test_to_mistral_schema(self, echo_tool):
        schema = echo_tool.to_mistral_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "echo"
        assert schema["function"]["description"].startswith("Echoes")
        assert schema["function"]["parameters"]["required"] == ["message"]

    def test_call_success(self, echo_tool):
        out = echo_tool.call(message="hello", region="Bretagne")
        assert out == {"echoed": "hello", "region": "Bretagne"}

    def test_call_missing_required(self, echo_tool):
        out = echo_tool.call(region="Bretagne")
        assert out["error"] == "missing_required"
        assert "message" in out["missing"]

    def test_call_unexpected_kwarg(self, add_tool):
        # add_tool n'accepte que a, b — un extra kwarg lève TypeError
        out = add_tool.call(a=1, b=2, c=3)
        assert out["error"] == "type_error"

    def test_call_returns_non_dict(self):
        bad = Tool(
            name="bad",
            description="Bad tool that returns a string.",
            parameters={"type": "object", "properties": {}, "required": []},
            func=lambda: "not a dict",
        )
        out = bad.call()
        assert out["error"] == "invalid_return"


# --- ToolRegistry ---


class TestToolRegistry:
    def test_register_and_get(self, echo_tool):
        reg = ToolRegistry()
        reg.register(echo_tool)
        assert "echo" in reg
        assert reg.get("echo") is echo_tool
        assert len(reg) == 1

    def test_register_duplicate_raises(self, echo_tool):
        reg = ToolRegistry()
        reg.register(echo_tool)
        with pytest.raises(ValueError, match="déjà enregistré"):
            reg.register(echo_tool)

    def test_names_sorted(self, echo_tool, add_tool):
        reg = ToolRegistry()
        reg.register(echo_tool)
        reg.register(add_tool)
        assert reg.names() == ["add", "echo"]

    def test_to_mistral_schemas(self, echo_tool, add_tool):
        reg = ToolRegistry()
        reg.register(echo_tool)
        reg.register(add_tool)
        schemas = reg.to_mistral_schemas()
        assert len(schemas) == 2
        names = [s["function"]["name"] for s in schemas]
        assert set(names) == {"echo", "add"}

    def test_dispatch_known_tool(self, add_tool):
        reg = ToolRegistry()
        reg.register(add_tool)
        out = reg.dispatch("add", a=2, b=3)
        assert out == {"sum": 5}

    def test_dispatch_unknown_tool(self, echo_tool):
        reg = ToolRegistry()
        reg.register(echo_tool)
        out = reg.dispatch("nonexistent", foo="bar")
        assert out["error"] == "unknown_tool"
        assert out["available"] == ["echo"]

    def test_empty_registry(self):
        reg = ToolRegistry()
        assert len(reg) == 0
        assert reg.names() == []
        assert reg.to_mistral_schemas() == []
