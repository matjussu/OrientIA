import numpy as np
import faiss
from mistralai.client import Mistral
from src.rag.embeddings import fiche_to_text, embed_texts_batched
from src.rag.index import build_index, save_index, load_index
from src.rag.retriever import retrieve_top_k
from src.rag.reranker import RerankConfig, rerank
from src.rag.mmr import mmr_select, DEFAULT_LAMBDA
from src.rag.intent import classify_intent, intent_to_config
from src.rag.generator import generate
from src.validator import Validator, ValidatorResult


class OrientIAPipeline:
    def __init__(
        self,
        client: Mistral,
        fiches: list[dict],
        rerank_config: RerankConfig | None = None,
        model: str = "mistral-medium-latest",
        use_mmr: bool = False,
        mmr_lambda: float = DEFAULT_LAMBDA,
        use_intent: bool = False,
        validator: Validator | None = None,
    ):
        self.client = client
        self.fiches = fiches
        self.rerank_config = rerank_config or RerankConfig()
        self.model = model
        self.use_mmr = use_mmr
        self.mmr_lambda = mmr_lambda
        self.use_intent = use_intent
        self.index: faiss.IndexFlatL2 | None = None
        # Validator v1 — optionnel, opt-in. Si fourni, .answer() le lance après
        # generate() et stocke le résultat dans .last_validation (backward-compat
        # — la signature de .answer() n'est PAS modifiée).
        self.validator = validator
        self.last_validation: ValidatorResult | None = None

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
        effective_top_k = top_k_sources
        effective_lambda = self.mmr_lambda
        if self.use_intent:
            cfg = intent_to_config(classify_intent(question))
            effective_top_k = cfg.top_k_sources
            effective_lambda = cfg.mmr_lambda

        retrieved = retrieve_top_k(self.client, self.index, self.fiches, question, k=k)
        reranked = rerank(retrieved, self.rerank_config)
        if self.use_mmr:
            top = mmr_select(reranked, k=effective_top_k, lambda_=effective_lambda)
        else:
            top = reranked[:effective_top_k]
        answer_text = generate(self.client, top, question, model=self.model)
        # Validator v1 (opt-in) : append en sortie generator (cf Ordre B
        # 2026-04-22). Pas de re-prompt ni de blocage en v1, juste détection.
        if self.validator is not None:
            self.last_validation = self.validator.validate(answer_text)
        return answer_text, top
