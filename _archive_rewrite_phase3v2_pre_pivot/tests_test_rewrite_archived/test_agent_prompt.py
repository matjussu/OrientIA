"""Tests pour ``src.rewrite.agent_prompt``."""

from __future__ import annotations

from pathlib import Path

from src.rewrite.agent_prompt import (
    build_agent_prompt,
    build_agent_prompt_for_chunk,
)


def test_prompt_contains_paths():
    chunk = Path("/tmp/orientia_chunks/chunk_0042.json")
    results = Path("/tmp/orientia_chunks/chunk_0042_results.json")
    prompt = build_agent_prompt(chunk, results)
    assert str(chunk) in prompt
    assert str(results) in prompt


def test_prompt_contains_5_rules():
    prompt = build_agent_prompt(Path("/tmp/x.json"), Path("/tmp/y.json"))
    for rule in ("R1", "R2", "R3", "R4", "R5"):
        assert rule in prompt


def test_prompt_contains_few_shot_example():
    prompt = build_agent_prompt(Path("/tmp/x.json"), Path("/tmp/y.json"))
    # exemple CROUS Lyon doit être présent
    assert "CROUS" in prompt
    assert "12 000" in prompt or "12000" in prompt


def test_prompt_specifies_json_output_format():
    prompt = build_agent_prompt(Path("/tmp/x.json"), Path("/tmp/y.json"))
    assert "fiche_id" in prompt
    assert "rewritten_text" in prompt


def test_prompt_forbids_markdown_and_pipe():
    prompt = build_agent_prompt(Path("/tmp/x.json"), Path("/tmp/y.json"))
    assert "sans `|`" in prompt or "pas de séparateurs" in prompt.lower()


def test_prompt_mentions_null_fallback():
    prompt = build_agent_prompt(Path("/tmp/x.json"), Path("/tmp/y.json"))
    # null pour les fiches qu'on ne peut pas rewriter
    assert "null" in prompt


def test_prompt_for_chunk_helper():
    prompt, c, r = build_agent_prompt_for_chunk(
        Path("/tmp/orientia_chunks_v6"), "chunk_0001"
    )
    assert c == Path("/tmp/orientia_chunks_v6/chunk_0001.json")
    assert r == Path("/tmp/orientia_chunks_v6/chunk_0001_results.json")
    assert "chunk_0001" in prompt
