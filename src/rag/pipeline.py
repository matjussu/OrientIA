import numpy as np
import faiss
from mistralai.client import Mistral
from src.rag.embeddings import fiche_to_text, embed_texts_batched
from src.rag.index import build_index, save_index, load_index
from src.rag.retriever import retrieve_top_k
from src.rag.reranker import RerankConfig, rerank
from src.rag.generator import generate


class OrientIAPipeline:
    def __init__(
        self,
        client: Mistral,
        fiches: list[dict],
        rerank_config: RerankConfig | None = None,
        model: str = "mistral-medium-latest",
    ):
        self.client = client
        self.fiches = fiches
        self.rerank_config = rerank_config or RerankConfig()
        self.model = model
        self.index: faiss.IndexFlatL2 | None = None

    def build_index(self) -> None:
        texts = [fiche_to_text(f) for f in self.fiches]
        embeddings = embed_texts_batched(self.client, texts, batch_size=64)
        self.index = build_index(np.array(embeddings, dtype="float32"))

    def load_index_from(self, path: str) -> None:
        """Load a pre-built FAISS index from disk (avoids re-embedding)."""
        self.index = load_index(path)

    def save_index_to(self, path: str) -> None:
        if self.index is None:
            raise RuntimeError("No index to save — call build_index() first.")
        save_index(self.index, path)

    def answer(
        self,
        question: str,
        k: int = 30,
        top_k_sources: int = 10,
    ) -> tuple[str, list[dict]]:
        if self.index is None:
            raise RuntimeError("Pipeline not built — call build_index() or load_index_from() first.")
        retrieved = retrieve_top_k(self.client, self.index, self.fiches, question, k=k)
        reranked = rerank(retrieved, self.rerank_config)
        top = reranked[:top_k_sources]
        answer_text = generate(self.client, top, question, model=self.model)
        return answer_text, top
