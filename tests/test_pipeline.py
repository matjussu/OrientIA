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
