import numpy as np
from src.rag.index import build_index, save_index, load_index


def test_build_index_returns_searchable_faiss_index(tmp_path):
    embeddings = np.random.rand(10, 128).astype("float32")
    index = build_index(embeddings)
    assert index.ntotal == 10

    query = embeddings[0:1]
    distances, indices = index.search(query, k=3)
    assert indices[0][0] == 0


def test_save_and_load_index_roundtrip(tmp_path):
    embeddings = np.random.rand(5, 64).astype("float32")
    index = build_index(embeddings)
    path = tmp_path / "test.index"

    save_index(index, path)
    loaded = load_index(path)
    assert loaded.ntotal == 5
