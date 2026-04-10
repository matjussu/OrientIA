import numpy as np
from unittest.mock import MagicMock
from src.rag.index import build_index
from src.rag.retriever import retrieve_top_k


def test_retrieve_top_k_returns_k_fiches_with_scores():
    fiches = [{"id": i, "nom": f"Formation {i}"} for i in range(20)]
    embeddings = np.random.rand(20, 64).astype("float32")
    index = build_index(embeddings)

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=list(embeddings[0]))]
    mock_client.embeddings.create.return_value = mock_response

    results = retrieve_top_k(mock_client, index, fiches, "query", k=5)
    assert len(results) == 5
    assert "fiche" in results[0]
    assert "score" in results[0]
    assert results[0]["fiche"]["id"] == 0
