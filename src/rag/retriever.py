import numpy as np
import faiss
from mistralai.client import Mistral
from src.rag.embeddings import embed_texts


def retrieve_top_k(
    client: Mistral,
    index: faiss.IndexFlatL2,
    fiches: list[dict],
    question: str,
    k: int = 10,
) -> list[dict]:
    q_emb = embed_texts(client, [question])[0]
    q_arr = np.array([q_emb], dtype="float32")
    distances, indices = index.search(q_arr, k)

    results = []
    for rank, idx in enumerate(indices[0]):
        if idx < 0 or idx >= len(fiches):
            continue
        dist = float(distances[0][rank])
        score = 1.0 / (1.0 + dist)
        results.append({"fiche": fiches[idx], "score": score, "base_score": score})
    return results
