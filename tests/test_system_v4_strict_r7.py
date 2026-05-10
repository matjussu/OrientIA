"""Tests step 7 — R7 hardlock dans system_v4_strict.py.

Couvre :
- R7 présent dans SYSTEM_PROMPT_V4_STRICT (additif, ne casse pas R1-R6)
- build_system_prompt_v4_strict : empty hardlock = string identique
- build_system_prompt_v4_strict : hardlock prepended en tête
- Generator : hardlock_block kwarg accepté + propagé en mode strict_v4
- Pipeline : last_router_result.hardlock_block_for_prompt() injecté en
  tête du prompt, tour 1 ET tour 2
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import faiss
import numpy as np
import pytest

from src.prompt.system_v4_strict import (
    SYSTEM_PROMPT_V4_STRICT,
    build_system_prompt_v4_strict,
)
from src.rag.metadata_filter import FilterCriteria
from src.rag.pipeline import OrientIAPipeline
from src.rag.router_llm import RouteDecision, RouterLLM


# ────────────────────────── R7 dans le prompt ──────────────────────────


def test_r7_present_in_system_prompt() -> None:
    """R7 est ajouté de façon ADDITIVE — R1-R6 préservés."""
    for marker in ("R1 — Chiffres", "R2 — Identité", "R3 — Citations",
                   "R4 — Style", "R5 — Posture", "R6 — LONGUEUR",
                   "R7 — CONTRAINTES HARDLOCK"):
        assert marker in SYSTEM_PROMPT_V4_STRICT, f"Marker manquant : {marker}"


def test_r7_mentions_region_constraint() -> None:
    """R7 documente la contrainte régionale (cas live #2 ingé cyber Bretagne)."""
    assert "régionale" in SYSTEM_PROMPT_V4_STRICT.lower() or "région" in SYSTEM_PROMPT_V4_STRICT.lower()
    # Texte spécifique : "alternative hors de cette région"
    assert "hors" in SYSTEM_PROMPT_V4_STRICT


def test_r7_mentions_domain_constraint() -> None:
    """R7 documente la contrainte de domaine (cas live #1 superlatif/CROUS)."""
    assert "domaine" in SYSTEM_PROMPT_V4_STRICT.lower()


def test_r7_mentions_violation_section() -> None:
    """Section 'SI VIOLATION' mentionne R7 désormais."""
    # La section finale liste les règles dont la violation est rejetée
    assert "R7" in SYSTEM_PROMPT_V4_STRICT
    # Et précise le verdict
    assert "validator" in SYSTEM_PROMPT_V4_STRICT.lower()


# ────────────────────────── build_system_prompt_v4_strict ──────────────────────────


def test_build_with_empty_hardlock_returns_base() -> None:
    """hardlock_block="" → SYSTEM_PROMPT_V4_STRICT inchangé (backward compat)."""
    assert build_system_prompt_v4_strict() == SYSTEM_PROMPT_V4_STRICT
    assert build_system_prompt_v4_strict(hardlock_block="") == SYSTEM_PROMPT_V4_STRICT


def test_build_with_hardlock_prepends_block() -> None:
    """hardlock_block fourni → bloc en TÊTE du prompt."""
    block = "## CONTRAINTES HARDLOCK (R7)\n- Région imposée : bretagne\n"
    result = build_system_prompt_v4_strict(hardlock_block=block)
    assert result.startswith("## CONTRAINTES HARDLOCK")
    assert "Région imposée : bretagne" in result
    # Le prompt R1-R7 reste présent après le bloc
    assert "Tu es OrientAI" in result
    assert "R7 — CONTRAINTES HARDLOCK" in result


def test_build_with_hardlock_no_double_newline_at_end() -> None:
    """Pas de doubles newlines parasites quand hardlock se termine par \n\n."""
    block = "## CONTRAINTES HARDLOCK (R7)\n- truc\n\n\n"  # trailing newlines
    result = build_system_prompt_v4_strict(hardlock_block=block)
    # Pas de triple newline avant l'identité
    assert "\n\n\nTu es OrientAI" not in result


# ────────────────────────── Generator propage hardlock_block ──────────────────────────


def test_generator_accepts_hardlock_kwarg() -> None:
    """Compat API : generate() accepte hardlock_block sans erreur de signature."""
    from inspect import signature
    from src.rag.generator import generate
    sig = signature(generate)
    assert "hardlock_block" in sig.parameters


def test_generator_passes_hardlock_to_strict_v4_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mode strict_v4 + hardlock_block → bloc apparaît dans le system prompt
    envoyé à Mistral."""
    from src.rag.generator import generate

    captured_messages: list[list[dict]] = []

    def _spy_complete(**kwargs):
        captured_messages.append(kwargs["messages"])
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Réponse stub"))]
        )

    client = MagicMock()
    client.chat.complete.side_effect = _spy_complete

    block = "## CONTRAINTES HARDLOCK (R7)\n- Région imposée : **bretagne**\n"
    generate(
        client=client,
        retrieved=[],
        question="Quelles écoles cyber Bretagne ?",
        use_strict_v4=True,
        hardlock_block=block,
    )

    assert captured_messages, "client.chat.complete pas appelé"
    sys_msg = captured_messages[0][0]
    assert sys_msg["role"] == "system"
    # Le bloc hardlock est en tête du system prompt
    assert sys_msg["content"].startswith("## CONTRAINTES HARDLOCK")
    assert "bretagne" in sys_msg["content"]


def test_generator_strict_v4_without_hardlock_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mode strict_v4 sans hardlock → system prompt = SYSTEM_PROMPT_V4_STRICT (backward compat)."""
    from src.rag.generator import generate

    captured_messages: list[list[dict]] = []

    def _spy_complete(**kwargs):
        captured_messages.append(kwargs["messages"])
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Réponse stub"))]
        )

    client = MagicMock()
    client.chat.complete.side_effect = _spy_complete

    generate(
        client=client,
        retrieved=[],
        question="Test",
        use_strict_v4=True,
    )

    sys_msg = captured_messages[0][0]
    assert sys_msg["content"] == SYSTEM_PROMPT_V4_STRICT


# ────────────────────────── Pipeline injecte hardlock_block ──────────────────────────


def _make_minimal_pipeline_with_router(monkeypatch: pytest.MonkeyPatch) -> tuple[OrientIAPipeline, list[str]]:
    """Pipeline minimal qui capture le system prompt envoyé au LLM."""
    fiches = [
        {"id": f"t-{i}", "nom": f"Form {i}", "etablissement": "X",
         "ville": "Rennes", "region": "Bretagne"}
        for i in range(5)
    ]
    np.random.seed(42)
    embeddings = np.random.randn(len(fiches), 1024).astype("float32")
    index = faiss.IndexFlatL2(1024)
    index.add(embeddings)

    captured_system_prompts: list[str] = []

    def _spy_complete(**kwargs):
        captured_system_prompts.append(kwargs["messages"][0]["content"])
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Réponse stub"))]
        )

    client = MagicMock()
    client.chat.complete.side_effect = _spy_complete

    np.random.seed(7)
    q_emb = np.random.randn(1024).astype("float32")
    monkeypatch.setattr(
        "src.rag.embeddings.embed_texts",
        lambda c, texts, **kwargs: [q_emb for _ in texts],
    )

    router = RouterLLM(client=client)
    pipeline = OrientIAPipeline(
        client=client,
        fiches=fiches,
        use_strict_v4=True,
        use_intent=False,
        router_llm=router,
    )
    pipeline.index = index
    return pipeline, captured_system_prompts


def test_pipeline_injects_hardlock_when_router_decides(monkeypatch: pytest.MonkeyPatch) -> None:
    """Si RouterLLM produit hardlock_region_strict + region, le pipeline
    injecte le bloc en tête du prompt v4 strict."""
    pipeline, captured = _make_minimal_pipeline_with_router(monkeypatch)

    def _fake_route(question, history=None):
        return RouteDecision(
            sub_indexes=["formations"],
            criteria=FilterCriteria(region="bretagne"),
            hardlock_region_strict=True,
            confidence=0.9,
        )
    monkeypatch.setattr(pipeline.router_llm, "route", _fake_route)

    pipeline.answer("Quelles écoles cyber en Bretagne ?")

    assert captured, "generate pas appelé"
    sys_prompt = captured[0]
    # Bloc hardlock en tête
    assert sys_prompt.startswith("## CONTRAINTES HARDLOCK")
    # Région mentionnée
    assert "bretagne" in sys_prompt.lower()
    # R1-R7 toujours présents APRÈS le bloc
    assert "R1 — Chiffres" in sys_prompt
    assert "R7 — CONTRAINTES HARDLOCK" in sys_prompt


def test_pipeline_no_hardlock_when_router_has_no_constraint(monkeypatch: pytest.MonkeyPatch) -> None:
    """Si RouteDecision n'a pas de hardlock, le system prompt = SYSTEM_PROMPT_V4_STRICT
    inchangé (backward compat strict)."""
    pipeline, captured = _make_minimal_pipeline_with_router(monkeypatch)

    def _fake_route(question, history=None):
        # Pas de hardlock_region_strict, pas de domain_lock
        return RouteDecision(
            sub_indexes=["formations"],
            confidence=0.7,
        )
    monkeypatch.setattr(pipeline.router_llm, "route", _fake_route)

    pipeline.answer("Quelques formations en informatique ?")

    sys_prompt = captured[0]
    # Pas de bloc hardlock en tête
    assert not sys_prompt.startswith("## CONTRAINTES HARDLOCK")
    # Le prompt strict est intact (commence par "Tu es OrientIA")
    assert sys_prompt == SYSTEM_PROMPT_V4_STRICT


def test_pipeline_no_router_no_hardlock(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sans router_llm → pas de hardlock injecté (cas baseline / Run F)."""
    fiches = [
        {"id": f"t-{i}", "nom": f"Form {i}", "etablissement": "X", "ville": "Rennes"}
        for i in range(5)
    ]
    np.random.seed(42)
    embeddings = np.random.randn(len(fiches), 1024).astype("float32")
    index = faiss.IndexFlatL2(1024)
    index.add(embeddings)

    captured_system_prompts: list[str] = []

    def _spy_complete(**kwargs):
        captured_system_prompts.append(kwargs["messages"][0]["content"])
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Réponse stub"))]
        )

    client = MagicMock()
    client.chat.complete.side_effect = _spy_complete

    np.random.seed(7)
    q_emb = np.random.randn(1024).astype("float32")
    fake_embed = lambda c, texts, **kwargs: [q_emb for _ in texts]
    # Path v1 passe par src.rag.retriever.embed_texts (import local du module),
    # donc patcher aussi cet alias en plus de src.rag.embeddings.
    monkeypatch.setattr("src.rag.embeddings.embed_texts", fake_embed)
    monkeypatch.setattr("src.rag.retriever.embed_texts", fake_embed)

    # Pas de router_llm
    pipeline = OrientIAPipeline(
        client=client, fiches=fiches, use_strict_v4=True, use_intent=False,
    )
    pipeline.index = index

    pipeline.answer("Test question")
    assert captured_system_prompts[0] == SYSTEM_PROMPT_V4_STRICT
