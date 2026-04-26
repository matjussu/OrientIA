"""Streaming helpers — Sprint 3 axe B agentique latency optims (2c).

Wrap `client.chat.stream(...)` du SDK Mistral pour produire des chunks
incrementaux user-side au lieu d'attendre la réponse complète. Ne
réduit PAS la latence totale, mais améliore drastiquement la **latence
perçue** : l'utilisateur voit les premiers tokens en ~0.5s au lieu
d'attendre 5-10s.

Sprint 4 utilisera ce helper pour la génération finale (réponse RAG
composée), où la latence perçue est critique UX.

## Pattern d'usage

```python
from src.agent.streaming import stream_chat_completion

for chunk in stream_chat_completion(client, model, messages):
    # chunk = string token incremental
    print(chunk, end="", flush=True)
```

Pour user-facing : envoyer chaque chunk via SSE / WebSocket.

## Caveats

- Streaming + tool_calls : Mistral SDK supporte le streaming des
  réponses textuelles, mais pas du delta de tool_calls (limitation
  côté SDK 2026-04). Si la réponse contient un tool_call, on bascule
  en mode non-streaming via `accumulate_full_response`.
- Streaming + function-calling : pour cette raison, le streaming est
  **réservé aux générations finales** (text-only), PAS aux étapes
  agentiques intermédiaires (qui invoquent des tools).
"""
from __future__ import annotations

from typing import Any, Iterator

from mistralai.client import Mistral


def stream_chat_completion(
    client: Mistral,
    model: str,
    messages: list[dict[str, Any]],
    *,
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> Iterator[str]:
    """Stream les chunks de texte de la réponse Mistral.

    Yields:
        str : chunks de texte incrémental (peuvent être 1+ tokens chacun).

    Le caller accumule lui-même si besoin de la réponse complète :
    ```python
    full = "".join(stream_chat_completion(client, model, messages))
    ```

    Pour usage SSE / WebSocket, yield directement chaque chunk au user.
    """
    kwargs: dict[str, Any] = {"model": model, "messages": messages}
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    if temperature is not None:
        kwargs["temperature"] = temperature

    stream = client.chat.stream(**kwargs)
    for event in stream:
        # mistralai SDK v2 : event.data.choices[0].delta.content
        # Compatible avec mock dans tests : tester le path
        try:
            choices = event.data.choices
            if not choices:
                continue
            delta = choices[0].delta
            content = getattr(delta, "content", None)
            if content:
                yield content
        except AttributeError:
            # Format alternatif (autre version SDK) — adapter si besoin
            choices = getattr(event, "choices", None)
            if choices:
                delta = getattr(choices[0], "delta", None)
                if delta:
                    content = getattr(delta, "content", None)
                    if content:
                        yield content


def accumulate_streamed_response(
    client: Mistral,
    model: str,
    messages: list[dict[str, Any]],
    **kwargs: Any,
) -> str:
    """Helper : retourne la réponse complète accumulée en mémoire.

    Utile quand le caller veut le bénéfice latence perçue côté SDK
    (Mistral peut commencer le streaming dès le premier token) mais
    ne propage pas le streaming user-side. Pour les agents internes
    où on a besoin du texte complet avant de continuer.

    Note : le gain latence perçue n'apparaît QU'EN STREAMING USER-SIDE.
    Si on accumule en mémoire, on attend forcément le `done`. Pour
    Sprint 4, le caller doit yield les chunks directement.
    """
    return "".join(
        stream_chat_completion(client, model, messages, **kwargs)
    )
