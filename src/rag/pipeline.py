import numpy as np
import faiss
from mistralai.client import Mistral
from src.rag.embeddings import fiche_to_text, embed_texts_batched
from src.rag.index import build_index, save_index, load_index
from src.rag.retriever import retrieve_top_k
from src.rag.reranker import RerankConfig, rerank
from src.rag.mmr import mmr_select, DEFAULT_LAMBDA
from src.rag.intent import classify_intent, classify_domain_hint, intent_to_config
from src.rag.generator import generate
from src.validator import (
    Validator,
    ValidatorResult,
    PolicyResult,
    apply_policy,
    append_phase_projet,
)


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
        # UX Policy (Gate J+6) — hybride α+β. Appliquée automatiquement quand
        # un validator est fourni. `last_policy_result` expose le verdict +
        # la réponse finale (peut avoir remplacé l'answer si Policy.BLOCK).
        self.last_policy_result: PolicyResult | None = None

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
        # ADR-049 : domain-aware reranker (no-op si hint=None, formation-centric par défaut)
        domain_hint = classify_domain_hint(question)
        reranked = rerank(retrieved, self.rerank_config, domain_hint=domain_hint)
        if self.use_mmr:
            top = mmr_select(reranked, k=effective_top_k, lambda_=effective_lambda)
        else:
            top = reranked[:effective_top_k]
        answer_text = generate(self.client, top, question, model=self.model)
        # Validator v1 + UX Policy (Gate J+6) : si un validator est fourni,
        # on valide puis on applique la policy hybride α+β. La signature
        # .answer() reste (answer, top) pour backward-compat, mais l'answer
        # retourné EST l'answer post-policy (remplacé en cas de Block).
        # Accès à la validation brute via .last_validation, policy via
        # .last_policy_result.
        if self.validator is not None:
            self.last_validation = self.validator.validate(answer_text)
            self.last_policy_result = apply_policy(answer_text, self.last_validation)
            answer_text = self.last_policy_result.final_answer
            # V4 phase projet minimal : append 3 Q réflexion + redirect CIO
            # si la question touche un enjeu fort (HEC/PASS/kiné/etc.).
            answer_text, _ = append_phase_projet(answer_text, question)
        return answer_text, top
