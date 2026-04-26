"""Caching helpers — Sprint 3 axe B agentique latency optims.

Fournit un cache LRU bounded en mémoire pour les calls Mistral
coûteux (e.g., ProfileClarifier sur queries répétées). Gain estimé :
~2-5s économisés par hit cache.

## Pattern d'usage

```python
from src.agent.cache import LRUCache

cache = LRUCache(maxsize=128)

cached_profile = cache.get(query)
if cached_profile is None:
    profile = clarifier.clarify(query)  # call Mistral
    cache.set(query, profile)
else:
    profile = cached_profile  # cache hit, ~$0 + ~0ms
```

## Caveat

Cache in-memory uniquement (pas persistance disque). Réinitialisé à
chaque restart du process. Pour Sprint 4 prod, considérer Redis si
déploiement multi-process. Pour MVP Sprint 3, in-memory suffit.
"""
from __future__ import annotations

from collections import OrderedDict
from threading import RLock
from typing import Any, Generic, Hashable, TypeVar


K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


class LRUCache(Generic[K, V]):
    """LRU cache bounded en mémoire, thread-safe.

    Implémentation OrderedDict + RLock pour usage multi-thread (utile
    quand l'agent fait du batching parallèle Sprint 3 (2a)).
    """

    def __init__(self, maxsize: int = 128):
        if maxsize < 1:
            raise ValueError("maxsize doit être >= 1")
        self._maxsize = maxsize
        self._data: OrderedDict[K, V] = OrderedDict()
        self._lock = RLock()
        self._stats = {"hits": 0, "misses": 0, "evictions": 0}

    def get(self, key: K, default: Any = None) -> V | Any:
        """Retourne la valeur si présente, sinon `default` (None par défaut).

        Touch (move-to-end) le key sur cache hit.
        """
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
                self._stats["hits"] += 1
                return self._data[key]
            self._stats["misses"] += 1
            return default

    def set(self, key: K, value: V) -> None:
        """Set ou update la valeur. Évince le plus ancien si maxsize atteint."""
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
                self._data[key] = value
                return
            self._data[key] = value
            if len(self._data) > self._maxsize:
                self._data.popitem(last=False)  # évince LRU
                self._stats["evictions"] += 1

    def __contains__(self, key: K) -> bool:
        with self._lock:
            return key in self._data

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
            self._stats = {"hits": 0, "misses": 0, "evictions": 0}

    def stats(self) -> dict[str, int]:
        """Retourne {hits, misses, evictions, size}. Snapshot copy."""
        with self._lock:
            return {
                **self._stats,
                "size": len(self._data),
                "maxsize": self._maxsize,
            }

    def hit_rate(self) -> float:
        """Hit rate 0-1. Retourne 0.0 si aucun lookup encore fait."""
        with self._lock:
            total = self._stats["hits"] + self._stats["misses"]
            if total == 0:
                return 0.0
            return self._stats["hits"] / total
