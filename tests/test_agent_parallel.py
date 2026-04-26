"""Tests src/agent/parallel.py — parallel_map / parallel_apply."""
from __future__ import annotations

import time

import pytest

from src.agent.parallel import parallel_apply, parallel_map


class TestParallelMap:
    def test_simple_map(self):
        results = parallel_map(lambda x: x * 2, [1, 2, 3, 4, 5], max_workers=3)
        assert results == [2, 4, 6, 8, 10]

    def test_empty_list(self):
        assert parallel_map(lambda x: x * 2, []) == []

    def test_invalid_max_workers(self):
        with pytest.raises(ValueError, match="max_workers"):
            parallel_map(lambda x: x, [1, 2], max_workers=0)

    def test_order_preserved(self):
        # Tasks de durée variable — l'ordre du résultat doit suivre items
        def slow(i):
            # Item 0 = lent, item 4 = rapide
            time.sleep(0.05 - i * 0.01)
            return i * 10

        results = parallel_map(slow, list(range(5)), max_workers=5)
        assert results == [0, 10, 20, 30, 40]

    def test_speedup_vs_sequential(self):
        # Vérifie que le parallel est effectivement plus rapide
        def slow_task(x):
            time.sleep(0.1)
            return x

        # Sequential ~ 5 × 0.1 = 0.5s
        t0 = time.time()
        seq_results = [slow_task(i) for i in range(5)]
        seq_time = time.time() - t0

        # Parallel ~ 0.1s + overhead
        t0 = time.time()
        par_results = parallel_map(slow_task, range(5), max_workers=5)
        par_time = time.time() - t0

        assert seq_results == par_results
        # Parallel doit être au moins 2x plus rapide
        assert par_time < seq_time / 2
        # Et finir en ~0.1s (avec overhead)
        assert par_time < 0.3

    def test_exception_raises_by_default(self):
        def fn(x):
            if x == 3:
                raise ValueError("Bad x=3")
            return x

        with pytest.raises(ValueError, match="x=3"):
            parallel_map(fn, [1, 2, 3, 4, 5], max_workers=3)

    def test_return_exceptions_true(self):
        def fn(x):
            if x % 2 == 0:
                raise ValueError(f"Even {x}")
            return x

        results = parallel_map(
            fn, [1, 2, 3, 4, 5],
            max_workers=3,
            return_exceptions=True,
        )
        assert results[0] == 1
        assert isinstance(results[1], ValueError)
        assert results[2] == 3
        assert isinstance(results[3], ValueError)
        assert results[4] == 5

    def test_max_workers_cap_to_items(self):
        # max_workers=10 mais 3 items → effective 3 workers
        results = parallel_map(lambda x: x, [10, 20, 30], max_workers=10)
        assert results == [10, 20, 30]


class TestParallelApply:
    def test_multi_arg_func(self):
        def add(a, b):
            return a + b

        results = parallel_apply(add, [(1, 2), (3, 4), (5, 6)], max_workers=3)
        assert results == [3, 7, 11]

    def test_empty(self):
        assert parallel_apply(lambda x, y: x + y, []) == []
