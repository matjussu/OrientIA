"""Tests e2e step 6 : injection RouterLLM dans pipeline.answer().

GATE CRITIQUE (recommandé par l'audit Matteo step 5 → 6) :
- Vérifie que `criteria` injecté par RouterLLM survit jusqu'à
  apply_metadata_filter (lever le verrou principal de la refonte :
  pipeline.py:589-647 receives criteria=None silencieusement).
- Vérifie que refusal_reason court-circuite le pipeline (pas d'appel
  retrieve/generate).
- Vérifie que le quad-subindex path est utilisé quand router cible
  un sous-ensemble strict.
- Vérifie que le path v1 est strictement préservé quand router_llm=None.
- Vérifie que top_k_override est respecté.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import faiss
import numpy as np
import pytest

from src.rag.metadata_filter import FilterCriteria
from src.rag.pipeline import OrientIAPipeline
from src.rag.router_llm import RouteDecision, RouterLLM


# ────────────────────────── Fixtures ──────────────────────────


def _make_test_fiche(idx: int, domain: str | None = None, region: str | None = None) -> dict:
    f: dict = {
        "id": f"test-{idx}",
        "nom": f"Formation {idx}",
        "etablissement": f"Étab {idx}",
        "ville": "Paris",
    }
    if region:
        f["region"] = region
    if domain:
        f["domain"] = domain
    return f


def _make_corpus() -> list[dict]:
    """Mini-corpus mixte pour tester routing."""
    fiches: list[dict] = []
    # 5 formations Bretagne
    for i in range(5):
        fiches.append(_make_test_fiche(i, region="Bretagne"))
    # 5 formations Occitanie
    for i in range(5, 10):
        fiches.append(_make_test_fiche(i, region="Occitanie"))
    # 3 CROUS
    for i in range(10, 13):
        fiches.append(_make_test_fiche(i, domain="crous", region="Auvergne-Rhône-Alpes"))
    # 3 metiers
    for i in range(13, 16):
        fiches.append(_make_test_fiche(i, domain="metier"))
    # 2 statistiques
    for i in range(16, 18):
        fiches.append(_make_test_fiche(i, domain="insee_salaire"))
    return fiches


def _make_pipeline_with_router(monkeypatch: pytest.MonkeyPatch) -> tuple[OrientIAPipeline, MagicMock]:
    """Pipeline minimal avec RouterLLM mocké (pas d'appel API réel)."""
    fiches = _make_corpus()
    np.random.seed(42)
    n = len(fiches)
    embeddings = np.random.randn(n, 1024).astype("float32")
    index = faiss.IndexFlatL2(1024)
    index.add(embeddings)

    # Mock client Mistral
    client = MagicMock()
    # Mock generate (qui sera appelé par answer)
    fake_response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="Réponse mock", tool_calls=None))]
    )
    client.chat.complete.return_value = fake_response

    # Patch embed_texts (utilisé par retrieve)
    np.random.seed(7)
    q_emb = np.random.randn(1024).astype("float32")

    def _fake_embed(c, texts, **kwargs):
        return [q_emb for _ in texts]

    import src.rag.embeddings as embeddings_mod
    monkeypatch.setattr(embeddings_mod, "embed_texts", _fake_embed)
    monkeypatch.setattr(embeddings_mod, "embed_texts_batched", _fake_embed)

    # Pipeline avec RouterLLM mocké (on contrôle directement RouterLLM.route)
    router = RouterLLM(client=client)
    pipeline = OrientIAPipeline(
        client=client,
        fiches=fiches,
        use_metadata_filter=True,
        use_intent=False,  # simplifie le test
        router_llm=router,
    )
    pipeline.index = index
    return pipeline, router


# ────────────────────────── GATE CRITIQUE : criteria survit ──────────────────────────


def test_criteria_from_router_reaches_metadata_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    """LE TEST CLÉ : quand RouterLLM populate criteria, ce criteria DOIT
    arriver à apply_metadata_filter. Levier principal de la refonte
    (cf audit Matteo écart 1 + plan section "FilterCriteria orpheline")."""
    pipeline, router = _make_pipeline_with_router(monkeypatch)

    # Stub RouterLLM.route pour retourner une décision contrôlée
    def _fake_route(question, history=None):
        return RouteDecision(
            sub_indexes=["aides_territoires"],
            criteria=FilterCriteria(
                region="auvergne-rhone-alpes",
                domain=["crous"],
            ),
            domain_lock=["crous"],
            hardlock_region_strict=True,
            hardlock_domain_strict=True,
            top_k_override=10,
            confidence=0.9,
        )
    monkeypatch.setattr(router, "route", _fake_route)

    # Stub generate pour ne pas appeler le LLM
    monkeypatch.setattr(
        "src.rag.pipeline.generate",
        lambda *args, **kwargs: "Réponse stub",
    )

    answer, sources = pipeline.answer("Combien coûte le logement CROUS à Lyon ?")

    # 1. Le pipeline a stocké la route_decision
    assert pipeline.last_router_result is not None
    assert pipeline.last_router_result.sub_indexes == ["aides_territoires"]
    assert pipeline.last_router_result.criteria is not None
    assert pipeline.last_router_result.criteria.region == "auvergne-rhone-alpes"

    # 2. Le filter a été activé avec un criteria non-vide
    assert pipeline.last_filter_stats is not None
    assert pipeline.last_filter_stats["filter_active"] is True
    assert pipeline.last_filter_stats["router_active"] is True
    assert pipeline.last_filter_stats["router_sub_indexes"] == ["aides_territoires"]

    # 3. CRUCIAL : sources retournées sont uniquement du domain crous
    # (apply_metadata_filter a respecté criteria.domain=['crous'])
    for src in sources:
        assert src["fiche"].get("domain") == "crous", (
            f"Fiche hors-domain dans top-K : {src['fiche']!r} — "
            "le filter n'a pas respecté domain_lock !"
        )


def test_router_refusal_short_circuits_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    """refusal_reason → court-circuit pré-pipeline (pas de retrieve/generate)."""
    pipeline, router = _make_pipeline_with_router(monkeypatch)

    pre_written = "Je n'ai pas de classement officiel des écoles dans mes sources."

    def _fake_route(question, history=None):
        return RouteDecision(
            sub_indexes=["formations"],
            refusal_reason="superlative_no_data",
            pre_written_response=pre_written,
            confidence=0.95,
        )
    monkeypatch.setattr(router, "route", _fake_route)

    # Stub generate pour détecter s'il est appelé (il ne devrait pas)
    generate_calls = []
    def _spy_generate(*args, **kwargs):
        generate_calls.append((args, kwargs))
        return "should not be called"
    monkeypatch.setattr("src.rag.pipeline.generate", _spy_generate)

    answer, sources = pipeline.answer("Quelle est la meilleure école de commerce ?")

    assert answer == pre_written
    assert sources == []
    # Aucun appel au générateur
    assert generate_calls == []
    # Marqueurs reset (analogue scope_classifier)
    assert pipeline.last_validation is None
    assert pipeline.last_policy_result is None
    assert pipeline.last_retry_metadata is not None
    assert pipeline.last_retry_metadata["retry_skipped_reason"] == "router_superlative_no_data"


def test_top_k_override_respected(monkeypatch: pytest.MonkeyPatch) -> None:
    """top_k_override du router élargit top_k_sources (max preserved)."""
    pipeline, router = _make_pipeline_with_router(monkeypatch)

    captured_top_k: list[int] = []

    def _fake_route(question, history=None):
        return RouteDecision(
            sub_indexes=["formations"],
            top_k_override=12,
            confidence=0.9,
        )
    monkeypatch.setattr(router, "route", _fake_route)

    # Stub _generate_with_retry pour capturer top_k servi (taille de `top`)
    original_generate = pipeline._generate_with_retry

    def _spy_generate(*, top, **kwargs):
        captured_top_k.append(len(top))
        return "stub", {"retries_attempted": 0, "tour1_failed_claims": [], "tour2_failed_claims": None,
                        "retry_stability": 1.0, "needs_audit": False, "wall_clock_s": 0.0,
                        "retry_skipped_reason": None}

    monkeypatch.setattr(pipeline, "_generate_with_retry", _spy_generate)

    pipeline.answer("Quelles formations en Bretagne ?", top_k_sources=5)

    # Audit Matteo step 6 : durcir l'assert. top_k_override=12 doit être
    # appliqué via max(5, 12)=12. Avec 5 fiches Bretagne dans le corpus
    # test, le top servi au générateur sera donc exactement min(12, len(filter))
    # sources disponibles. On asserte ≥ 12 si le corpus le permet, sinon
    # on vérifie que c'est >= top_k_override (pas seulement >= top_k_sources).
    assert captured_top_k, "generate not called"
    # CRUCIAL : sans le `max(top_k_sources, route.top_k_override)`, on aurait
    # juste 5. Avec, on est ≥ min(12, len(retrieved)).
    n_top = captured_top_k[0]
    # Soit on a 12 (corpus suffisant), soit on a au moins le top_k_override
    # plafonné par les fiches disponibles dans sub-index "formations".
    assert n_top >= 5, f"top_k {n_top} < 5 (top_k_sources de base)"
    # L'assertion stricte qui détecte un bug max(): top doit être > 5 si
    # le corpus a ≥ 6 fiches dans le sub-index visé.
    # Ici sub_index='formations' contient 10 fiches (5 Bretagne + 5 Occitanie).
    # Donc on doit avoir n_top ≥ min(12, 10) = 10.
    assert n_top >= 10, (
        f"top_k_override=12 n'a pas été appliqué : top_k effectif = {n_top}, "
        f"attendu ≥ 10 (min(12, 10 fiches formations dispo)). "
        f"Le `max(top_k_sources, route.top_k_override)` est probablement cassé."
    )


def test_no_router_preserves_v1_behavior(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sans router_llm passé à __init__, comportement v1 strict (last_router_result=None)."""
    fiches = _make_corpus()
    np.random.seed(42)
    embeddings = np.random.randn(len(fiches), 1024).astype("float32")
    index = faiss.IndexFlatL2(1024)
    index.add(embeddings)
    client = MagicMock()

    np.random.seed(7)
    q_emb = np.random.randn(1024).astype("float32")
    monkeypatch.setattr(
        "src.rag.embeddings.embed_texts",
        lambda c, texts, **kwargs: [q_emb for _ in texts],
    )

    # Pipeline sans router (router_llm=None par défaut)
    pipeline = OrientIAPipeline(
        client=client,
        fiches=fiches,
        use_metadata_filter=True,
        use_intent=False,
    )
    pipeline.index = index

    monkeypatch.setattr(
        "src.rag.pipeline.generate",
        lambda *args, **kwargs: "Réponse v1",
    )

    answer, sources = pipeline.answer("Question test")

    # last_router_result reste None (router pas instancié)
    assert pipeline.last_router_result is None
    # filter_stats : router_active absent ou False (path v1)
    if pipeline.last_filter_stats is not None:
        assert pipeline.last_filter_stats.get("router_active", False) is False


def test_router_with_all_sub_indexes_falls_back_to_v1_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Si router renvoie tous les 4 sub_indexes (filet de sécurité), le pipeline
    retombe sur path v1 (pas de routing strict appliqué)."""
    pipeline, router = _make_pipeline_with_router(monkeypatch)

    def _fake_route(question, history=None):
        return RouteDecision(
            sub_indexes=["formations", "metiers", "statistiques", "aides_territoires"],
            confidence=0.4,  # confidence basse → filet de sécurité
            is_fallback=True,
        )
    monkeypatch.setattr(router, "route", _fake_route)

    monkeypatch.setattr(
        "src.rag.pipeline.generate",
        lambda *args, **kwargs: "Réponse v1",
    )

    pipeline.answer("Question vague")

    # router_active doit être False (pas de routing strict)
    if pipeline.last_filter_stats is not None:
        assert pipeline.last_filter_stats.get("router_active", False) is False


def test_router_domain_lock_creates_criteria_when_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Si route_decision a domain_lock mais pas de criteria, le pipeline
    crée un FilterCriteria(domain=domain_lock) pour l'apply_metadata_filter."""
    pipeline, router = _make_pipeline_with_router(monkeypatch)

    def _fake_route(question, history=None):
        return RouteDecision(
            sub_indexes=["metiers"],
            criteria=None,  # Pas de criteria fourni
            domain_lock=["metier"],  # Mais domain_lock présent
            confidence=0.85,
        )
    monkeypatch.setattr(router, "route", _fake_route)

    monkeypatch.setattr(
        "src.rag.pipeline.generate",
        lambda *args, **kwargs: "Réponse stub",
    )

    answer, sources = pipeline.answer("Que fait un actuaire ?")

    # Tous les results sont du domain metier (domain_lock respecté)
    for src in sources:
        assert src["fiche"].get("domain") == "metier"
