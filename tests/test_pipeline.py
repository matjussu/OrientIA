from unittest.mock import MagicMock
import numpy as np
from src.rag.reranker import RerankConfig
from src.rag.pipeline import OrientIAPipeline


def test_pipeline_end_to_end_mock():
    fiches = [
        {"nom": "Master Cyber ENSIBS", "etablissement": "ENSIBS", "ville": "Vannes",
         "statut": "Public", "labels": ["SecNumEdu"]},
        {"nom": "Master Commerce", "etablissement": "X", "ville": "Paris",
         "statut": "Privé", "labels": []},
    ]
    mock_client = MagicMock()

    emb_response = MagicMock()
    emb_response.data = [MagicMock(embedding=[0.1, 0.2]), MagicMock(embedding=[0.11, 0.21])]
    q_response = MagicMock()
    q_response.data = [MagicMock(embedding=[0.1, 0.2])]
    mock_client.embeddings.create.side_effect = [emb_response, q_response]

    chat_response = MagicMock()
    chat_response.choices = [MagicMock(message=MagicMock(content="Recommandation..."))]
    mock_client.chat.complete.return_value = chat_response

    pipeline = OrientIAPipeline(mock_client, fiches, rerank_config=RerankConfig())
    pipeline.build_index()
    answer, sources = pipeline.answer("Quelles formations cyber ?", k=2)
    assert "Recommandation" in answer
    assert len(sources) == 2


def test_pipeline_answer_raises_before_build_index():
    mock_client = MagicMock()
    pipeline = OrientIAPipeline(mock_client, [{"nom": "x"}])
    import pytest
    with pytest.raises(RuntimeError, match="build_index"):
        pipeline.answer("question")


def test_pipeline_mmr_enabled_reorders_near_duplicates():
    """Phase F.3.a — with use_mmr=True, the pipeline should diversify
    the top sources: near-duplicate reranker winners get penalised in
    favor of semantically distinct fiches, improving diversite_geo."""
    # 3 fiches: A and A_dup are nearly identical semantically (Paris EFREI
    # variants), B is distinct (Rennes ENSIBS). The reranker would pick
    # A then A_dup; MMR should prefer A then B.
    fiches = [
        {"nom": "EFREI Paris Cyber", "etablissement": "EFREI", "ville": "Paris",
         "statut": "Privé", "labels": []},
        {"nom": "EFREI Paris Cyber (alt)", "etablissement": "EFREI", "ville": "Paris",
         "statut": "Privé", "labels": []},
        {"nom": "ENSIBS Vannes Cyber", "etablissement": "ENSIBS", "ville": "Vannes",
         "statut": "Public", "labels": []},
    ]
    mock_client = MagicMock()

    # Index embeddings: A and A_dup are near-identical, B is far away.
    emb_response = MagicMock()
    emb_response.data = [
        MagicMock(embedding=[1.0, 0.0, 0.0]),
        MagicMock(embedding=[0.99, 0.01, 0.0]),
        MagicMock(embedding=[0.0, 1.0, 0.0]),
    ]
    # Query embedding matches A (and A_dup) best.
    q_response = MagicMock()
    q_response.data = [MagicMock(embedding=[1.0, 0.0, 0.0])]
    mock_client.embeddings.create.side_effect = [emb_response, q_response]

    chat_response = MagicMock()
    chat_response.choices = [MagicMock(message=MagicMock(content="ok"))]
    mock_client.chat.complete.return_value = chat_response

    pipeline = OrientIAPipeline(
        mock_client, fiches, rerank_config=RerankConfig(),
        use_mmr=True, mmr_lambda=0.3,
    )
    pipeline.build_index()
    _, sources = pipeline.answer("cyber", k=3, top_k_sources=2)
    names = [s["fiche"]["nom"] for s in sources]
    assert "EFREI Paris Cyber" in names
    assert "ENSIBS Vannes Cyber" in names, (
        f"MMR should have picked the diverse Vannes fiche; got {names}"
    )


def test_pipeline_intent_routing_uses_intent_config():
    """Phase F.3.b — when use_intent=True, the pipeline classifies
    the question and overrides top_k_sources + mmr_lambda with the
    intent-specific config. A geographic question should request
    the wider top_k (12) instead of the default 10."""
    fiches = [
        {"nom": f"Formation {i}", "etablissement": f"Etab{i}", "ville": "X",
         "statut": "Privé", "labels": []}
        for i in range(15)
    ]
    mock_client = MagicMock()
    emb_data = [MagicMock(embedding=[float(i % 5), float(i // 5), 0.0])
                for i in range(15)]
    emb_response = MagicMock(); emb_response.data = emb_data
    q_response = MagicMock(); q_response.data = [MagicMock(embedding=[1.0, 0.0, 0.0])]
    mock_client.embeddings.create.side_effect = [emb_response, q_response]
    chat_response = MagicMock()
    chat_response.choices = [MagicMock(message=MagicMock(content="ok"))]
    mock_client.chat.complete.return_value = chat_response

    pipeline = OrientIAPipeline(
        mock_client, fiches, rerank_config=RerankConfig(),
        use_mmr=True, use_intent=True,
    )
    pipeline.build_index()
    # Geographic intent: config = top_k_sources=12, mmr_lambda=0.4
    _, sources = pipeline.answer("Formations en Bretagne ?", k=15)
    assert len(sources) == 12, (
        f"Geographic intent should yield 12 sources, got {len(sources)}"
    )


def test_pipeline_mmr_disabled_by_default_preserves_ranking():
    """When use_mmr is not set, the pipeline must behave exactly as
    before (pure rerank) — backward compatibility for existing runs."""
    fiches = [
        {"nom": "A", "etablissement": "E", "ville": "V",
         "statut": "Privé", "labels": []},
        {"nom": "B", "etablissement": "E", "ville": "V",
         "statut": "Privé", "labels": []},
    ]
    mock_client = MagicMock()
    emb_response = MagicMock()
    emb_response.data = [
        MagicMock(embedding=[1.0, 0.0]),
        MagicMock(embedding=[0.99, 0.01]),
    ]
    q_response = MagicMock()
    q_response.data = [MagicMock(embedding=[1.0, 0.0])]
    mock_client.embeddings.create.side_effect = [emb_response, q_response]
    chat_response = MagicMock()
    chat_response.choices = [MagicMock(message=MagicMock(content="ok"))]
    mock_client.chat.complete.return_value = chat_response

    pipeline = OrientIAPipeline(mock_client, fiches, rerank_config=RerankConfig())
    assert pipeline.use_mmr is False
    pipeline.build_index()
    _, sources = pipeline.answer("q", k=2, top_k_sources=2)
    assert len(sources) == 2
