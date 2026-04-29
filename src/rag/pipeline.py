import logging
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
from src.rag.metadata_filter import (
    FilterCriteria,
    apply_metadata_filter,
)
from src.validator import (
    Validator,
    ValidatorResult,
    PolicyResult,
    apply_policy,
    append_phase_projet,
)


_logger = logging.getLogger(__name__)


# Sprint 10 chantier C §8.4 — auto-expansion k stratégie
# Quand le filter métadonnées coupe trop, on retry retrieve avec k expanded.
INITIAL_K_MULTIPLIER = 3   # k_eff = k × 3 par défaut
MAX_K_MULTIPLIER = 10      # cap absolu (ratio max sur k passé en arg)


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
        use_metadata_filter: bool = False,
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
        # Sprint 10 chantier C §8.3 — RAG filtré métadonnées (opt-in).
        # False par défaut = backward compat strict (run F+G results
        # reproductibles). True = active le pipeline post-FAISS filter
        # avec auto-expansion k. Doit s'accompagner de fiches avec
        # frontmatter consommable (région/niveau/alternance/budget/secteur)
        # — chantier B textualisation ONISEP/RNCP.
        self.use_metadata_filter = use_metadata_filter
        # Stats du dernier `.answer(criteria=...)` — utiles pour audit
        # F+G (combien d'expansions ont été nécessaires, recall pré/post
        # filter, etc.). None tant qu'aucun call.
        self.last_filter_stats: dict | None = None

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
        criteria: FilterCriteria | None = None,
    ) -> tuple[str, list[dict]]:
        """Génère une réponse depuis FAISS + rerank + MMR + generator.

        Sprint 10 chantier C §8.3 : argument `criteria` opt-in. Quand fourni
        ET `use_metadata_filter=True` à l'init, applique
        `apply_metadata_filter` post-rerank (avec auto-expansion k §8.4 si
        trop restrictif). Sinon comportement strictement identique à v1.

        Args:
            question: requête utilisateur.
            k: nombre initial de candidats FAISS (défaut 30 — preserved
                pour backward compat).
            top_k_sources: nombre de sources passées au generator.
            criteria: FilterCriteria (Sprint 10 §8.3). None ou is_empty() →
                pas de filter (backward compat).
        """
        if self.index is None:
            raise RuntimeError("Pipeline not built — call build_index() or load_index_from() first.")
        effective_top_k = top_k_sources
        effective_lambda = self.mmr_lambda
        if self.use_intent:
            cfg = intent_to_config(classify_intent(question))
            effective_top_k = cfg.top_k_sources
            effective_lambda = cfg.mmr_lambda

        # ADR-049 : domain-aware reranker (no-op si hint=None, formation-centric par défaut)
        domain_hint = classify_domain_hint(question)

        # Sprint 10 §8.3-§8.4 : retrieve avec auto-expansion si filter activé
        reranked = self._retrieve_and_filter(
            question=question,
            k=k,
            domain_hint=domain_hint,
            target=effective_top_k,
            criteria=criteria,
        )

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

    def _retrieve_and_filter(
        self,
        *,
        question: str,
        k: int,
        domain_hint: str | None,
        target: int,
        criteria: FilterCriteria | None,
    ) -> list[dict]:
        """Retrieve + rerank, avec auto-expansion §8.4 si filter actif.

        Sans filter actif (ou criteria empty) : comportement v1 (1 retrieve k).
        Avec filter : retrieve k×INITIAL_K_MULTIPLIER, filter, expand si <target.
        Toujours retourne reranked candidates (même format que v1).
        Stats stockées dans self.last_filter_stats pour audit F+G.
        """
        # Path backward compat : pas de filter activé → comportement v1 strict
        if not self.use_metadata_filter or criteria is None or criteria.is_empty():
            retrieved = retrieve_top_k(self.client, self.index, self.fiches, question, k=k)
            reranked = rerank(retrieved, self.rerank_config, domain_hint=domain_hint)
            self.last_filter_stats = {
                "filter_active": False,
                "criteria_empty": criteria is None or criteria.is_empty(),
                "k_initial": k,
                "k_final": k,
                "n_retrieved": len(retrieved),
                "n_after_filter": len(reranked),
                "expansions": 0,
            }
            return reranked

        # Path filter actif : retrieve avec k_eff = k × INITIAL, expand si nécessaire
        k_eff = k * INITIAL_K_MULTIPLIER
        max_k = k * MAX_K_MULTIPLIER
        expansions = 0
        filtered: list[dict] = []
        retrieved: list[dict] = []
        reranked_full: list[dict] = []

        while True:
            retrieved = retrieve_top_k(
                self.client, self.index, self.fiches, question, k=k_eff
            )
            reranked_full = rerank(retrieved, self.rerank_config, domain_hint=domain_hint)
            filtered = apply_metadata_filter(reranked_full, criteria)
            if len(filtered) >= target:
                break
            if k_eff >= max_k:
                _logger.warning(
                    "metadata_filter MAX_K_MULTIPLIER atteint (k=%d, max=%d) — "
                    "criteria probablement trop restrictifs (n_filtered=%d, target=%d). "
                    "Retour partiel.",
                    k_eff, max_k, len(filtered), target,
                )
                break
            k_eff = min(k_eff * 2, max_k)
            expansions += 1

        self.last_filter_stats = {
            "filter_active": True,
            "criteria_empty": False,
            "k_initial": k,
            "k_final": k_eff,
            "n_retrieved": len(retrieved),
            "n_after_filter": len(filtered),
            "expansions": expansions,
            "hit_max": k_eff >= max_k and len(filtered) < target,
        }
        return filtered
