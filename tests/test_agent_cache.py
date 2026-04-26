"""Tests src/agent/cache.py — LRUCache."""
from __future__ import annotations

import pytest

from src.agent.cache import LRUCache


class TestLRUCache:
    def test_set_and_get(self):
        c = LRUCache[str, int](maxsize=3)
        c.set("a", 1)
        assert c.get("a") == 1
        assert c.get("missing") is None

    def test_default_value(self):
        c = LRUCache[str, int](maxsize=3)
        assert c.get("missing", default=42) == 42

    def test_lru_eviction(self):
        c = LRUCache[str, int](maxsize=2)
        c.set("a", 1)
        c.set("b", 2)
        c.set("c", 3)  # évince "a" (LRU)
        assert "a" not in c
        assert "b" in c
        assert "c" in c

    def test_get_touches_order(self):
        c = LRUCache[str, int](maxsize=2)
        c.set("a", 1)
        c.set("b", 2)
        c.get("a")  # touch "a" (move to end)
        c.set("c", 3)  # devrait évincer "b" maintenant
        assert "a" in c
        assert "b" not in c
        assert "c" in c

    def test_update_existing_key(self):
        c = LRUCache[str, int](maxsize=2)
        c.set("a", 1)
        c.set("b", 2)
        c.set("a", 99)  # update, pas eviction
        assert c.get("a") == 99
        assert c.get("b") == 2
        assert len(c) == 2

    def test_invalid_maxsize(self):
        with pytest.raises(ValueError, match="maxsize"):
            LRUCache(maxsize=0)
        with pytest.raises(ValueError, match="maxsize"):
            LRUCache(maxsize=-1)

    def test_clear(self):
        c = LRUCache[str, int](maxsize=3)
        c.set("a", 1)
        c.set("b", 2)
        c.clear()
        assert len(c) == 0
        assert c.get("a") is None
        # Stats reset aussi
        assert c.stats()["hits"] == 0
        assert c.stats()["misses"] == 1  # le get juste avant comptait

    def test_stats_hits_misses(self):
        c = LRUCache[str, int](maxsize=3)
        c.set("a", 1)
        c.get("a")  # hit
        c.get("a")  # hit
        c.get("b")  # miss
        s = c.stats()
        assert s["hits"] == 2
        assert s["misses"] == 1
        assert s["evictions"] == 0
        assert s["size"] == 1

    def test_stats_evictions(self):
        c = LRUCache[str, int](maxsize=2)
        c.set("a", 1)
        c.set("b", 2)
        c.set("c", 3)  # évince "a"
        c.set("d", 4)  # évince "b"
        s = c.stats()
        assert s["evictions"] == 2
        assert s["size"] == 2

    def test_hit_rate_zero_lookups(self):
        c = LRUCache[str, int](maxsize=3)
        assert c.hit_rate() == 0.0

    def test_hit_rate_calculation(self):
        c = LRUCache[str, int](maxsize=3)
        c.set("a", 1)
        c.get("a")  # hit
        c.get("a")  # hit
        c.get("b")  # miss
        # 2 hits / 3 lookups = 0.666...
        assert c.hit_rate() == pytest.approx(2 / 3, rel=1e-3)

    def test_thread_safe_basic(self):
        """Stress test simple multi-thread (pas de fuzzing exhaustif)."""
        import threading

        c = LRUCache[str, int](maxsize=100)
        errors = []

        def worker(start, n):
            try:
                for i in range(start, start + n):
                    c.set(f"k{i}", i)
                    c.get(f"k{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i * 10, 10)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert len(c) <= 100  # respecte maxsize sous concurrence


class TestProfileClarifierCacheIntegration:
    """Tests rapide intégration cache dans ProfileClarifier (mocked)."""

    def test_cache_hit_skips_mistral_call(self):
        from unittest.mock import MagicMock
        from src.agent.tools.profile_clarifier import (
            Profile,
            ProfileClarifier,
        )

        client = MagicMock()
        cache = LRUCache[str, Profile](maxsize=10)
        # Pré-populate cache
        cached_profile = Profile(
            age_group="lyceen_terminale",
            education_level="terminale",
            intent_type="orientation_initiale",
            sector_interest=["info"],
        )
        cache.set("Quelle école d'ingé info ?", cached_profile)

        clarifier = ProfileClarifier(client=client, cache=cache)
        result = clarifier.clarify("Quelle école d'ingé info ?")

        # Profile retourné = cached
        assert result is cached_profile
        # Mistral PAS appelé
        client.chat.complete.assert_not_called()
        # Stats : 1 hit, 0 miss
        assert cache.stats()["hits"] == 1

    def test_cache_miss_calls_mistral_then_stores(self):
        import json
        from unittest.mock import MagicMock
        from src.agent.tools.profile_clarifier import (
            Profile,
            ProfileClarifier,
        )

        client = MagicMock()
        # Mock response avec tool_call valide
        tc = MagicMock()
        tc.function.name = "extract_user_profile"
        tc.function.arguments = json.dumps({
            "age_group": "etudiant_l1_l3",
            "education_level": "bac+2",
            "intent_type": "info_metier_specifique",
            "sector_interest": ["compta"],
            "urgent_concern": False,
            "confidence": 0.85,
        })
        msg = MagicMock()
        msg.tool_calls = [tc]
        msg.content = ""
        response = MagicMock()
        response.choices = [MagicMock(message=msg)]
        client.chat.complete.return_value = response

        cache = LRUCache[str, Profile](maxsize=10)
        clarifier = ProfileClarifier(client=client, cache=cache)
        result = clarifier.clarify("Quels blocs valide le BTS compta ?")

        # Mistral appelé
        client.chat.complete.assert_called_once()
        # Stats : 0 hit, 1 miss
        assert cache.stats()["hits"] == 0
        assert cache.stats()["misses"] == 1
        # Cache stocké post-success
        assert "Quels blocs valide le BTS compta ?" in cache
        assert cache.get("Quels blocs valide le BTS compta ?") == result

    def test_cache_none_skips_caching(self):
        """Sans cache fourni, ProfileClarifier appelle toujours Mistral."""
        import json
        from unittest.mock import MagicMock
        from src.agent.tools.profile_clarifier import ProfileClarifier

        client = MagicMock()
        tc = MagicMock()
        tc.function.name = "extract_user_profile"
        tc.function.arguments = json.dumps({
            "age_group": "lyceen_terminale",
            "education_level": "terminale",
            "intent_type": "orientation_initiale",
            "sector_interest": [],
            "urgent_concern": False,
            "confidence": 0.7,
        })
        msg = MagicMock()
        msg.tool_calls = [tc]
        msg.content = ""
        response = MagicMock()
        response.choices = [MagicMock(message=msg)]
        client.chat.complete.return_value = response

        clarifier = ProfileClarifier(client=client, cache=None)
        # Premier appel
        clarifier.clarify("test query")
        # Deuxième appel même query → Mistral re-appelé (pas de cache)
        clarifier.clarify("test query")

        assert client.chat.complete.call_count == 2
