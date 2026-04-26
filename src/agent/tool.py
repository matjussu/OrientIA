"""Tool abstraction + ToolRegistry — base de l'architecture agentique.

Chaque outil concret (ProfileClarifier, QueryReformuler, etc.) déclare :
- `name` : identifiant utilisé par Mistral pour appeler l'outil
- `description` : explication NL injectée dans le system prompt
- `parameters` : JSON Schema des paramètres attendus
- `func` : implémentation Python qui reçoit `**kwargs` et retourne dict

Le ToolRegistry catalogue les tools, expose le format Mistral
function-calling (`as_mistral_schema()`) et dispatch les calls.

Cf ADR-051 pour le rationale architectural.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class Tool:
    """Définition d'un outil agentique pour Mistral function-calling.

    Pattern d'usage :
        def my_func(query: str, region: str | None = None) -> dict:
            return {"result": ...}

        tool = Tool(
            name="my_tool",
            description="Cherche X par query+region.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "..."},
                    "region": {"type": "string", "description": "..."},
                },
                "required": ["query"],
            },
            func=my_func,
        )
    """

    name: str
    description: str
    parameters: dict[str, Any]
    func: Callable[..., dict[str, Any]]

    def to_mistral_schema(self) -> dict[str, Any]:
        """Sérialise au format Mistral function-calling (`tools=[...]`)."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def call(self, **kwargs: Any) -> dict[str, Any]:
        """Invoque le tool avec validation minimale des paramètres requis."""
        required = self.parameters.get("required", []) or []
        missing = [k for k in required if k not in kwargs]
        if missing:
            return {
                "error": "missing_required",
                "missing": missing,
                "tool": self.name,
            }
        try:
            result = self.func(**kwargs)
        except TypeError as e:
            return {
                "error": "type_error",
                "message": str(e),
                "tool": self.name,
            }
        if not isinstance(result, dict):
            return {
                "error": "invalid_return",
                "message": f"Tool {self.name} doit retourner un dict, "
                           f"pas {type(result).__name__}",
            }
        return result


@dataclass
class ToolRegistry:
    """Catalogue des tools disponibles pour un Agent.

    Append-only via `register()`. Le SDK Mistral attend la liste
    sérialisée via `to_mistral_schemas()`.
    """

    tools: dict[str, Tool] = field(default_factory=dict)

    def register(self, tool: Tool) -> None:
        if tool.name in self.tools:
            raise ValueError(
                f"Tool '{tool.name}' déjà enregistré dans ce registry"
            )
        self.tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self.tools.get(name)

    def __contains__(self, name: str) -> bool:
        return name in self.tools

    def __len__(self) -> int:
        return len(self.tools)

    def names(self) -> list[str]:
        return sorted(self.tools.keys())

    def to_mistral_schemas(self) -> list[dict[str, Any]]:
        """Liste sérialisée pour `client.chat.complete(tools=...)`."""
        return [t.to_mistral_schema() for t in self.tools.values()]

    def dispatch(self, name: str, **kwargs: Any) -> dict[str, Any]:
        """Invoque le tool nommé. Retourne un dict d'erreur si absent."""
        tool = self.get(name)
        if tool is None:
            return {
                "error": "unknown_tool",
                "tool": name,
                "available": self.names(),
            }
        return tool.call(**kwargs)
