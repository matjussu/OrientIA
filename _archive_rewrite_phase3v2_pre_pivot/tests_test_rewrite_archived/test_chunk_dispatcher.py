"""Tests pour ``src.rewrite.chunk_dispatcher``."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.rewrite.chunk_dispatcher import (
    ChunkManifest,
    chunk_distribution,
    list_completed_chunks,
    list_pending_chunks,
    load_chunk_results,
    split_into_chunks,
)


def _make_fiches(n: int) -> list[dict]:
    return [
        {
            "id": f"fiche:{i}",
            "domain": "crous" if i % 2 == 0 else "insee_salaire",
            "text": f"text{i}",
        }
        for i in range(n)
    ]


class TestSplitIntoChunks:
    def test_basic_split(self, tmp_path):
        fiches = _make_fiches(125)
        manifest = split_into_chunks(fiches, tmp_path, chunk_size=50)
        assert manifest.n_chunks == 3  # 50 + 50 + 25
        assert manifest.n_total_fiches == 125
        assert len(manifest.chunk_ids) == 3
        for cid in manifest.chunk_ids:
            assert (tmp_path / f"{cid}.json").exists()

    def test_chunk_sizes_correct(self, tmp_path):
        fiches = _make_fiches(125)
        split_into_chunks(fiches, tmp_path, chunk_size=50)
        sizes = [
            len(json.loads((tmp_path / f"chunk_{i:04d}.json").read_text()))
            for i in range(1, 4)
        ]
        assert sizes == [50, 50, 25]

    def test_manifest_written(self, tmp_path):
        fiches = _make_fiches(10)
        split_into_chunks(fiches, tmp_path, chunk_size=5)
        manifest_path = tmp_path / "manifest.json"
        assert manifest_path.exists()
        m = ChunkManifest.from_json(manifest_path)
        assert m.n_chunks == 2
        assert m.chunk_size == 5

    def test_seed_shuffles_deterministic(self, tmp_path):
        fiches = _make_fiches(10)
        split_into_chunks(fiches, tmp_path, chunk_size=5, seed=42)
        # Re-split avec même seed → même contenu chunk_0001
        first_chunk_a = (tmp_path / "chunk_0001.json").read_text()
        # Cleanup et recommencer
        for f in tmp_path.glob("*"):
            f.unlink()
        split_into_chunks(fiches, tmp_path, chunk_size=5, seed=42)
        first_chunk_b = (tmp_path / "chunk_0001.json").read_text()
        assert first_chunk_a == first_chunk_b

    def test_no_seed_keeps_input_order(self, tmp_path):
        fiches = _make_fiches(5)
        split_into_chunks(fiches, tmp_path, chunk_size=5)
        chunk = json.loads((tmp_path / "chunk_0001.json").read_text())
        assert [f["id"] for f in chunk] == [f"fiche:{i}" for i in range(5)]


class TestPendingCompleted:
    def test_no_results_all_pending(self, tmp_path):
        fiches = _make_fiches(10)
        m = split_into_chunks(fiches, tmp_path, chunk_size=5)
        assert list_pending_chunks(m) == m.chunk_ids
        assert list_completed_chunks(m) == []

    def test_partial_results_split(self, tmp_path):
        fiches = _make_fiches(15)
        m = split_into_chunks(fiches, tmp_path, chunk_size=5)
        # Mark chunk_0001 done
        (tmp_path / "chunk_0001_results.json").write_text(
            json.dumps([{"fiche_id": f"fiche:{i}", "rewritten_text": "ok"} for i in range(5)]),
            encoding="utf-8",
        )
        assert list_pending_chunks(m) == ["chunk_0002", "chunk_0003"]
        assert list_completed_chunks(m) == ["chunk_0001"]


class TestLoadChunkResults:
    def test_load_basic(self, tmp_path):
        fiches = _make_fiches(10)
        m = split_into_chunks(fiches, tmp_path, chunk_size=5)
        # Create both result files
        (tmp_path / "chunk_0001_results.json").write_text(
            json.dumps(
                [{"fiche_id": f"fiche:{i}", "rewritten_text": f"rewrite_{i}"} for i in range(5)]
            ),
            encoding="utf-8",
        )
        (tmp_path / "chunk_0002_results.json").write_text(
            json.dumps(
                [{"fiche_id": f"fiche:{i}", "rewritten_text": f"rewrite_{i}"} for i in range(5, 10)]
            ),
            encoding="utf-8",
        )
        rewrites, debug = load_chunk_results(m)
        assert len(rewrites) == 10
        assert rewrites["fiche:3"] == "rewrite_3"
        assert all(d["status"] == "ok" for d in debug.values())

    def test_null_text_skipped(self, tmp_path):
        fiches = _make_fiches(5)
        m = split_into_chunks(fiches, tmp_path, chunk_size=5)
        (tmp_path / "chunk_0001_results.json").write_text(
            json.dumps(
                [
                    {"fiche_id": "fiche:0", "rewritten_text": "ok"},
                    {"fiche_id": "fiche:1", "rewritten_text": None},
                    {"fiche_id": "fiche:2", "rewritten_text": ""},
                    {"fiche_id": "fiche:3", "rewritten_text": "ok3"},
                    {"fiche_id": "fiche:4", "rewritten_text": "ok4"},
                ]
            ),
            encoding="utf-8",
        )
        rewrites, debug = load_chunk_results(m)
        assert set(rewrites.keys()) == {"fiche:0", "fiche:3", "fiche:4"}
        assert debug["chunk_0001"]["n_null"] == 2

    def test_missing_chunk_results_non_strict(self, tmp_path):
        fiches = _make_fiches(10)
        m = split_into_chunks(fiches, tmp_path, chunk_size=5)
        # Only chunk_0001 has results
        (tmp_path / "chunk_0001_results.json").write_text(
            json.dumps([{"fiche_id": "fiche:0", "rewritten_text": "ok"}]),
            encoding="utf-8",
        )
        rewrites, debug = load_chunk_results(m, strict=False)
        assert "fiche:0" in rewrites
        assert debug["chunk_0002"]["status"] == "missing"

    def test_missing_chunk_results_strict_raises(self, tmp_path):
        fiches = _make_fiches(10)
        m = split_into_chunks(fiches, tmp_path, chunk_size=5)
        with pytest.raises(FileNotFoundError):
            load_chunk_results(m, strict=True)

    def test_parse_error_handled(self, tmp_path):
        fiches = _make_fiches(5)
        m = split_into_chunks(fiches, tmp_path, chunk_size=5)
        (tmp_path / "chunk_0001_results.json").write_text(
            "INVALID JSON {{{", encoding="utf-8"
        )
        rewrites, debug = load_chunk_results(m)
        assert rewrites == {}
        assert debug["chunk_0001"]["status"] == "parse_error"

    def test_skip_malformed_entries(self, tmp_path):
        fiches = _make_fiches(5)
        m = split_into_chunks(fiches, tmp_path, chunk_size=5)
        (tmp_path / "chunk_0001_results.json").write_text(
            json.dumps(
                [
                    {"fiche_id": "fiche:0", "rewritten_text": "ok"},
                    "not_a_dict",
                    {"missing_fiche_id": True, "rewritten_text": "x"},
                    {"fiche_id": "fiche:1", "rewritten_text": "ok1"},
                ]
            ),
            encoding="utf-8",
        )
        rewrites, debug = load_chunk_results(m)
        assert set(rewrites.keys()) == {"fiche:0", "fiche:1"}
        assert debug["chunk_0001"]["n_skip_format"] == 2


class TestChunkDistribution:
    def test_basic(self, tmp_path):
        fiches = _make_fiches(10)
        m = split_into_chunks(fiches, tmp_path, chunk_size=5)
        dist = chunk_distribution(m)
        assert dist == {"crous": 5, "insee_salaire": 5}
