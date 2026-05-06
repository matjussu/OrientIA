import json
import logging
import time
from pathlib import Path

import numpy as np
import faiss
from mistralai.client import Mistral
from src.rag.embeddings import embed_texts, fiche_to_text, embed_texts_batched
from src.rag.index import build_index, save_index, load_index
from src.rag.retriever import retrieve_top_k
from src.rag.reranker import RerankConfig, rerank
from src.rag.mmr import mmr_select, DEFAULT_LAMBDA
from src.rag.intent import (
    classify_intent,
    classify_domain_hint,
    intent_to_config,
    INTENT_FACTUAL_POINTED,
)
from src.rag.generator import generate
from src.lookup.structured_select import try_select_or_none, SelectResult
from src.rag.metadata_filter import (
    FilterCriteria,
    apply_metadata_filter,
)
from src.rag.post_process import post_process_answer
from src.rag.scope_classifier import ScopeClassifier, ScopeResult
from src.validator import (
    Validator,
    ValidatorResult,
    PolicyResult,
    apply_policy,
    append_phase_projet,
    extract_failed_claims,
    format_hint_block,
)


_logger = logging.getLogger(__name__)


# Sprint 10 chantier C §8.4 — auto-expansion k stratégie
# Quand le filter métadonnées coupe trop, on retry retrieve avec k expanded.
INITIAL_K_MULTIPLIER = 3   # k_eff = k × 3 par défaut
MAX_K_MULTIPLIER = 10      # cap absolu (ratio max sur k passé en arg)


# Chantier 1.B (2026-05-03) — retry-with-hint loop anti-hallucination
# Cap dur à 1 retry au démarrage (cf plan voici-le-retour-de-lively-yao.md) :
# éviter régression sur les claims validés au tour 1 quand le hint pollue.
# Augmentation à 2 conditionnée à mesure de retry_stability sur 10+ questions.
MAX_RETRIES_WITH_HINT = 1

# Timeout wall-clock total .answer() (génération + validation + retry).
# Cible démo INRIA : <15s perçus. Cap à 30s pour tolérer 2 générations Mistral
# de ~10s chacune en heure de pointe + validation + dispatch retry hint.
RETRY_TIMEOUT_S = 30.0

# Marge de sécurité avant retry : on ne lance le tour 2 que s'il reste au moins
# RETRY_RESERVE_S secondes sur le budget timeout. Sinon on garde la réponse
# du tour 1 pour ne pas dépasser le wall-clock.
RETRY_RESERVE_S = 5.0

# Seuils d'alerte retry_stability (ratio des claims validés au tour 1
# encore présents/non-cassés au tour 2). Sans seuil on regarde la métrique
# une fois et on l'oublie — ces seuils déclenchent un signal automatique.
RETRY_STABILITY_WARN_THRESHOLD = 0.7    # >30% claims perdus → log warning
RETRY_STABILITY_AUDIT_THRESHOLD = 0.5   # >50% claims perdus → flag needs_audit


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
        use_metadata_filter: bool = True,
        use_golden_qa: bool = False,
        golden_qa_index_path: str | None = None,
        golden_qa_meta_path: str | None = None,
        enable_post_process: bool = False,
        scope_classifier: ScopeClassifier | None = None,
        use_strict_v4: bool = False,
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
        # Sprint 10 chantier C — RAG filtré métadonnées.
        #
        # Sprint 10 chantier C v1 (PR #102 mergée 10:12) : `False` par défaut.
        # Sprint 10 chantier C activation (cette PR) : **`True` par défaut**.
        #
        # Le default change parce que :
        # 1. Chantier B (PR #105) a normalisé les frontmatter cross-corpus :
        #    secteur 86.7%, budget 55.4%, alternance 36.5% du corpus 55k
        #    couverts. Le filter peut maintenant opérer significativement
        #    (vs quasi-inactif avant B).
        # 2. Backward compat préservée : `_retrieve_and_filter()` prend le
        #    path v1 strict quand `criteria=None` (cf ligne ~170), même avec
        #    `use_metadata_filter=True`. Les call-sites Run F+G qui font
        #    `pipeline.answer(question)` sans criteria continuent à opérer
        #    en comportement v1 strict — Run F+G reproductible sans
        #    configuration explicite.
        # 3. Pour les nouveaux usages avec criteria (chantier E CLI / serving
        #    prod), pas besoin de penser à set le flag — défaut "filter
        #    available, à activer via criteria explicit".
        #
        # Pour explicit opt-out (ex: A/B test sans filter), passer
        # `use_metadata_filter=False`.
        self.use_metadata_filter = use_metadata_filter
        # Stats du dernier `.answer(criteria=...)` — utiles pour audit
        # F+G (combien d'expansions ont été nécessaires, recall pré/post
        # filter, etc.). None tant qu'aucun call.
        self.last_filter_stats: dict | None = None
        # Sprint 10 chantier D — Q&A Golden Dynamic Few-Shot (opt-in).
        # False par défaut = backward compat strict. True = active le
        # triple-retrieve : top-1 Q&A Golden injecté en few-shot prefix
        # avec **séparation stricte Comment/Quoi** (la Q&A est référence
        # ton/structure ; les écoles/chiffres cités dans l'exemple sont
        # IGNORÉS, seules les fiches du context RAG factuel sont sources
        # autorisées pour citer). Lazy-load index/meta au 1er .answer().
        self.use_golden_qa = use_golden_qa
        self._golden_qa_index_path = golden_qa_index_path
        self._golden_qa_meta_path = golden_qa_meta_path
        self._golden_qa_index: faiss.IndexFlatL2 | None = None
        self._golden_qa_meta: list[dict] | None = None
        # Stats du dernier `.answer()` côté Q&A Golden (pour audit F+G).
        self.last_golden_qa: dict | None = None
        # Chantier 2 (2026-05-03) — résultat du dernier SELECT structuré tenté
        # (None si intent != FACTUAL_POINTED OU SELECT pas tenté). Argument
        # démo INRIA : marker visible `via_select=True` pour audit.
        self.last_select_result: SelectResult | None = None
        # Chantier 1.B (2026-05-03) — métadonnées du retry-with-hint loop pour
        # audit / observabilité. None tant qu'aucun call avec validator. Format :
        #   {
        #     "retries_attempted": 0|1,
        #     "tour1_failed_claims": [...],
        #     "tour2_failed_claims": [...] (présent uniquement si retry effectué),
        #     "retry_stability": float in [0,1] (1 = retry n'a cassé aucun bon claim),
        #     "needs_audit": bool (True si retry_stability < AUDIT_THRESHOLD),
        #     "wall_clock_s": float,
        #     "retry_skipped_reason": str|None ("timeout" | "no_validator" | None),
        #   }
        self.last_retry_metadata: dict | None = None
        # Phase 2 refonte (2026-05-06) — post-process déterministe (zéro LLM)
        # Sprint 8 Wave 1 : strip_invented_urls + fix_broken_markdown_tables +
        # validate_onisep_slugs. Appliqué post-validator/policy, pré-phase_projet.
        # Stats du dernier appel exposées via `last_post_process_stats`.
        self.enable_post_process = enable_post_process
        self.last_post_process_stats: dict | None = None
        # Étape 1 refonte (2026-05-06) — ScopeClassifier amont du pipeline.
        # Si fourni, classifie chaque question en {in_scope, out_of_scope, urgent}
        # AVANT tout retrieve/generate. Court-circuit avec réponse pré-écrite si
        # != in_scope. None par défaut = backward compat (toutes questions traitées).
        self.scope_classifier = scope_classifier
        self.last_scope_result: ScopeResult | None = None
        # Étape 2 refonte (2026-05-06) — contrat strict v4 WHAT/HOW.
        # Quand True, la génération utilise SYSTEM_PROMPT_V4_STRICT + JSON
        # tabulaire <sources> via FactCard au lieu de la prose libre v3.2.
        # False par défaut = backward compat (v3.2 + retry-with-hint préservés).
        self.use_strict_v4 = use_strict_v4

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
        history: list[dict] | None = None,
        temperature: float = 0.3,
    ) -> tuple[str, list[dict]]:
        """Génère une réponse depuis FAISS + rerank + MMR + generator.

        Sprint 10 chantier C §8.3 : argument `criteria` opt-in. Quand fourni
        ET `use_metadata_filter=True` à l'init, applique
        `apply_metadata_filter` post-rerank (avec auto-expansion k §8.4 si
        trop restrictif). Sinon comportement strictement identique à v1.

        Sprint 11 P0 Item 2 : argument `history` opt-in pour buffer mémoire
        short-term (suivi de tiroirs "Oui Plan A" → développe). Format
        Mistral compliant `[{"role": "user"|"assistant", "content": str}]`.
        Default `None`/empty = stateless v1 (pas de régression Run F+G).

        Args:
            question: requête utilisateur.
            k: nombre initial de candidats FAISS (défaut 30 — preserved
                pour backward compat).
            top_k_sources: nombre de sources passées au generator.
            criteria: FilterCriteria (Sprint 10 §8.3). None ou is_empty() →
                pas de filter (backward compat).
            history: list[{role, content}] de la conversation précédente
                (Sprint 11 P0 Item 2). None/[] = stateless.
        """
        if self.index is None:
            raise RuntimeError("Pipeline not built — call build_index() or load_index_from() first.")

        # Étape 1 refonte (2026-05-06) — Scope classification AMONT.
        # Court-circuit avec réponse pré-écrite si question hors-scope ou urgent.
        # Cette gate est PRÉ-pipeline : aucun appel retrieve/generate si non in_scope.
        if self.scope_classifier is not None:
            scope_res = self.scope_classifier.classify(question)
            self.last_scope_result = scope_res
            if scope_res.label != "in_scope":
                # Reset les marqueurs pipeline (backward compat consumers)
                self.last_select_result = None
                self.last_validation = None
                self.last_policy_result = None
                self.last_retry_metadata = {
                    "retries_attempted": 0,
                    "tour1_failed_claims": [],
                    "tour2_failed_claims": None,
                    "retry_stability": 1.0,
                    "needs_audit": False,
                    "wall_clock_s": 0.0,
                    "retry_skipped_reason": f"scope_{scope_res.label}",
                }
                self.last_filter_stats = None
                self.last_golden_qa = None
                self.last_post_process_stats = None
                return scope_res.pre_written_response or "", []
        else:
            self.last_scope_result = None

        effective_top_k = top_k_sources
        effective_lambda = self.mmr_lambda
        intent_label = classify_intent(question) if self.use_intent else None
        if self.use_intent:
            cfg = intent_to_config(intent_label)
            effective_top_k = cfg.top_k_sources
            effective_lambda = cfg.mmr_lambda

        # Chantier 2 (2026-05-03) — SELECT structuré bypass pour les questions
        # factuelles pointues sur UNE formation nommée. Si le SELECT réussit
        # (entité reconnue ET fuzzy ≥ 85 ET field présent ET valeur valide),
        # on RETOURNE DIRECTEMENT la réponse déterministe sans appel LLM.
        # Argument démo INRIA : « zéro hallu chiffres par construction ».
        # Sinon (ambigu, no_match, invalid_value), le SelectResult retourné
        # contient déjà un fallback unifié — on le retourne aussi.
        # Si try_select_or_none retourne None (pas une question factual),
        # on continue le pipeline RAG normal.
        if intent_label == INTENT_FACTUAL_POINTED:
            select_result = try_select_or_none(question, self.fiches)
            self.last_select_result = select_result
            if select_result is not None:
                # SELECT a tenté quelque chose (succès OU fallback contrôlé) —
                # on retourne sans appel LLM (zero hallu garanti par construction).
                # `top` est vide car bypass — backward compat tuple shape préservée.
                self.last_retry_metadata = {
                    "retries_attempted": 0,
                    "tour1_failed_claims": [],
                    "tour2_failed_claims": None,
                    "retry_stability": 1.0,
                    "needs_audit": False,
                    "wall_clock_s": 0.0,
                    "retry_skipped_reason": "select_bypass",
                }
                return select_result.text, []
        else:
            self.last_select_result = None

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

        # Sprint 10 chantier D — Q&A Golden few-shot prefix (opt-in)
        golden_qa_prefix = self._maybe_build_golden_qa_prefix(question)

        # Chantier 1.B (2026-05-03) — Retry-with-hint loop anti-hallucination.
        # Pattern : tour 1 generate → validate → si failed_claims non vide ET
        # temps restant suffisant → tour 2 avec hint réinjecté → validate →
        # garder le meilleur. Cap dur MAX_RETRIES_WITH_HINT=1, timeout 30s.
        # Sans validator : pas de retry possible (no-op transparent, comportement v1).
        wall_t0 = time.time()
        answer_text, retry_meta = self._generate_with_retry(
            top=top,
            question=question,
            golden_qa_prefix=golden_qa_prefix,
            history=history,
            temperature=temperature,
            wall_t0=wall_t0,
            intent=intent_label,
        )

        # Validator v1 + UX Policy (Gate J+6) : si un validator est fourni,
        # on valide puis on applique la policy hybride α+β. La signature
        # .answer() reste (answer, top) pour backward-compat, mais l'answer
        # retourné EST l'answer post-policy (remplacé en cas de Block).
        # Accès à la validation brute via .last_validation, policy via
        # .last_policy_result, retry stats via .last_retry_metadata.
        self.last_retry_metadata = retry_meta
        if self.validator is not None:
            # last_validation est déjà set par _generate_with_retry (dernier tour).
            self.last_policy_result = apply_policy(answer_text, self.last_validation)
            answer_text = self.last_policy_result.final_answer
            # V4 phase projet minimal : append 3 Q réflexion + redirect CIO
            # si la question touche un enjeu fort (HEC/PASS/kiné/etc.).
            answer_text, _ = append_phase_projet(answer_text, question)
        # Phase 2 refonte — post-process déterministe (URLs hallu, slugs ONISEP,
        # tableaux markdown cassés). Off par défaut (backward compat). Appliqué
        # APRÈS validator/policy car ces fixes sont silently corrective et
        # n'invalident pas les claims validés (juste cleanup UX).
        if self.enable_post_process:
            answer_text, pp_stats = post_process_answer(answer_text, top)
            self.last_post_process_stats = pp_stats
        else:
            self.last_post_process_stats = None
        return answer_text, top

    def _generate_with_retry(
        self,
        *,
        top: list[dict],
        question: str,
        golden_qa_prefix: str | None,
        history: list[dict] | None,
        temperature: float,
        wall_t0: float,
        intent: str | None = None,
    ) -> tuple[str, dict]:
        """Boucle retry-with-hint anti-hallucination (chantier 1.B).

        Sans validator : single-shot generate (pas de retry possible).
        Avec validator : tour 1 generate → validate → si claims problématiques
        ET temps restant suffisant (>= RETRY_RESERVE_S) → tour 2 avec hint
        réinjecté → validate → garde le meilleur (heuristique : moins de
        failed_claims = meilleur).

        Garde-fous expert :
          - MAX_RETRIES_WITH_HINT = 1 (pas 2 — éviter régression sur
            claims validés au tour 1)
          - Timeout wall-clock 30s — si dépassé, on garde le tour 1
          - Tracker retry_stability avec seuils 0.7 (warn) / 0.5 (audit)

        Returns:
            (answer_text, retry_metadata_dict)
            answer_text est le meilleur tour sélectionné.
        """
        meta: dict = {
            "retries_attempted": 0,
            "tour1_failed_claims": [],
            "tour2_failed_claims": None,
            "retry_stability": 1.0,
            "needs_audit": False,
            "wall_clock_s": 0.0,
            "retry_skipped_reason": None,
        }

        # Tour 1 — génération initiale
        tour1_answer = generate(
            self.client, top, question,
            model=self.model,
            golden_qa_prefix=golden_qa_prefix,
            history=history,
            temperature=temperature,
            use_strict_v4=self.use_strict_v4,
        )

        # Sans validator : pas de retry (no-op transparent)
        if self.validator is None:
            meta["retry_skipped_reason"] = "no_validator"
            meta["wall_clock_s"] = round(time.time() - wall_t0, 2)
            return tour1_answer, meta

        # Validation tour 1 — passe intent pour gating layer3 LLM
        tour1_validation = self.validator.validate(tour1_answer, intent=intent)
        self.last_validation = tour1_validation
        tour1_failed = extract_failed_claims(tour1_validation)
        meta["tour1_failed_claims"] = list(tour1_failed)

        # Décision retry : besoin de claims à corriger ET budget timeout OK
        if not tour1_failed:
            # Tour 1 propre, pas de retry nécessaire
            meta["wall_clock_s"] = round(time.time() - wall_t0, 2)
            return tour1_answer, meta

        elapsed = time.time() - wall_t0
        remaining = RETRY_TIMEOUT_S - elapsed
        if remaining < RETRY_RESERVE_S:
            # Pas assez de budget pour un retry — on garde le tour 1
            _logger.warning(
                "Retry skipped (timeout reserve insufficient: %.1fs remaining, "
                "%.1fs needed). Keeping tour 1 with %d failed_claims.",
                remaining, RETRY_RESERVE_S, len(tour1_failed),
            )
            meta["retry_skipped_reason"] = "timeout"
            meta["wall_clock_s"] = round(time.time() - wall_t0, 2)
            return tour1_answer, meta

        # Tour 2 avec hint réinjecté
        # Note (Étape 2 refonte) : en mode strict_v4, le hint_block est ignoré
        # par generate() car le contrat v4 a sa propre logique de refus honnête.
        # Le retry tour 2 reste utile pour donner au LLM une 2e chance après
        # validator feedback (mais il n'y a pas de hint injecté en v4).
        meta["retries_attempted"] = 1
        hint_block = format_hint_block(tour1_failed)
        tour2_answer = generate(
            self.client, top, question,
            model=self.model,
            golden_qa_prefix=golden_qa_prefix,
            history=history,
            temperature=temperature,
            hint_block=hint_block,
            use_strict_v4=self.use_strict_v4,
        )
        tour2_validation = self.validator.validate(tour2_answer, intent=intent)
        tour2_failed = extract_failed_claims(tour2_validation)
        meta["tour2_failed_claims"] = list(tour2_failed)

        # retry_stability : ratio de claims du tour 1 NON-RÉINTRODUITS au tour 2.
        # Si tour 1 avait 5 failed_claims et que tour 2 en a 3 (les mêmes ou
        # subset), retry_stability = (5-3)/5 = 0.4. Si tour 2 a 3 nouveaux
        # claims (différents), c'est aussi 0.4 (les 5 originaux ont été corrigés
        # mais 3 nouveaux apparus = pollution du hint).
        # Formule simple : 1 - (failed_tour2 / max(failed_tour1, 1)).
        if tour1_failed:
            stability = max(0.0, min(1.0, 1.0 - (len(tour2_failed) / len(tour1_failed))))
        else:
            stability = 1.0
        meta["retry_stability"] = round(stability, 3)

        if stability < RETRY_STABILITY_AUDIT_THRESHOLD:
            meta["needs_audit"] = True
            _logger.warning(
                "Retry stability LOW (%.2f < %.2f) — flag needs_audit=True. "
                "Tour1 had %d claims, tour2 has %d. Hint may be polluting context.",
                stability, RETRY_STABILITY_AUDIT_THRESHOLD,
                len(tour1_failed), len(tour2_failed),
            )
        elif stability < RETRY_STABILITY_WARN_THRESHOLD:
            _logger.warning(
                "Retry stability degraded (%.2f < %.2f). Tour1=%d claims, tour2=%d.",
                stability, RETRY_STABILITY_WARN_THRESHOLD,
                len(tour1_failed), len(tour2_failed),
            )

        # Sélection : on garde le tour avec le moins de failed_claims.
        # Si égal → tour 2 (la dernière instruction a été suivie au moins partiellement).
        if len(tour2_failed) <= len(tour1_failed):
            self.last_validation = tour2_validation
            best_answer = tour2_answer
        else:
            # Tour 2 a régressé → on garde le tour 1
            _logger.warning(
                "Tour 2 regressed (%d claims vs %d at tour 1). Keeping tour 1 answer.",
                len(tour2_failed), len(tour1_failed),
            )
            self.last_validation = tour1_validation
            best_answer = tour1_answer

        meta["wall_clock_s"] = round(time.time() - wall_t0, 2)
        return best_answer, meta

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

    # ─────────────── Sprint 10 chantier D — Q&A Golden Dynamic Few-Shot ───────

    def _lazy_load_golden_qa(self) -> bool:
        """Charge l'index FAISS et le meta JSON Q&A Golden au premier appel.

        Returns True si le load a réussi (index + meta dispos), False si
        configuration manquante ou fichiers absents (fallback gracieux,
        pas d'exception — on désactive juste le few-shot pour ce call).
        """
        if self._golden_qa_index is not None and self._golden_qa_meta is not None:
            return True
        if not self._golden_qa_index_path or not self._golden_qa_meta_path:
            _logger.warning(
                "use_golden_qa=True mais golden_qa_index_path/meta_path "
                "non fournis — few-shot désactivé pour ce call."
            )
            return False
        idx_path = Path(self._golden_qa_index_path)
        meta_path = Path(self._golden_qa_meta_path)
        if not idx_path.exists() or not meta_path.exists():
            _logger.warning(
                "Golden QA files manquants (idx=%s exists=%s ; meta=%s exists=%s) — "
                "few-shot désactivé pour ce call.",
                idx_path, idx_path.exists(), meta_path, meta_path.exists(),
            )
            return False
        self._golden_qa_index = load_index(str(idx_path))
        meta_obj = json.loads(meta_path.read_text(encoding="utf-8"))
        self._golden_qa_meta = meta_obj.get("records") or []
        if len(self._golden_qa_meta) != self._golden_qa_index.ntotal:
            _logger.warning(
                "Mismatch index ntotal (%d) vs meta records (%d) — risque "
                "désynchro mapping. Chargement quand même mais à investiguer.",
                self._golden_qa_index.ntotal, len(self._golden_qa_meta),
            )
        return True

    def _retrieve_golden_qa(self, question: str, top_k: int = 1) -> dict | None:
        """Top-k Q&A Golden via FAISS dédié. Retourne le record meta du top-1
        (incluant `answer_refined`, `score_total`, `decision`, etc.).

        Returns None si flag désactivé OU index non chargeable OU 0 records.
        """
        if not self.use_golden_qa:
            return None
        if not self._lazy_load_golden_qa():
            return None
        # Embed la question via Mistral-embed (même modèle que pour build l'index)
        q_emb = embed_texts(self.client, [question])[0]
        q_arr = np.array([q_emb], dtype="float32")
        distances, indices = self._golden_qa_index.search(q_arr, top_k)
        if indices.size == 0 or indices[0][0] < 0:
            return None
        idx = int(indices[0][0])
        if idx >= len(self._golden_qa_meta):
            return None
        record = self._golden_qa_meta[idx]
        # Annoter avec score retrieve pour audit
        record_copy = dict(record)
        record_copy["_retrieve_score"] = float(1.0 / (1.0 + distances[0][0]))
        record_copy["_retrieve_distance"] = float(distances[0][0])
        return record_copy

    @staticmethod
    def _build_few_shot_prefix(qa_record: dict) -> str:
        """Construit le bloc few-shot prefix avec **séparation stricte Comment/Quoi**.

        Le prefix s'injecte au system prompt via `generate(golden_qa_prefix=...)`.
        Le pattern : la Q&A Golden = RÉFÉRENCE COMPORTEMENTALE (ton, structure,
        empathie, posture). Les écoles, chiffres, dates citées dans cet exemple
        sont **IGNORÉS** côté factuel — seules les fiches du context RAG ci-après
        sont sources autorisées pour citer.

        Validé Matteo dans la sync architecture 2026-04-29.
        """
        seed = (qa_record.get("question_seed") or "").strip()
        refined_q = (qa_record.get("question_refined") or "").strip()
        refined_a = (qa_record.get("answer_refined") or "").strip()
        # Si le record manque l'answer_refined, on ne peut pas faire de few-shot
        if not refined_a:
            return ""
        question_for_prefix = refined_q or seed or "(question similaire)"
        return (
            "=== EXEMPLE EXPERT (RÉFÉRENCE TON/STRUCTURE/EMPATHIE UNIQUEMENT) ===\n"
            f"Question type traitée par un conseiller expert :\n"
            f"« {question_for_prefix} »\n\n"
            "Réponse de référence (style, posture, structure de raisonnement) :\n"
            f"{refined_a}\n\n"
            "⚠️ IMPORTANT — SÉPARATION STRICTE COMMENT vs QUOI :\n"
            "- Cet exemple est une RÉFÉRENCE COMPORTEMENTALE (ton bienveillant,\n"
            "  reformulation active, 3 pistes pondérées, questions d'exploration).\n"
            "- IGNORE complètement les écoles spécifiques, chiffres, dates, noms\n"
            "  de formations cités dans cet exemple.\n"
            "- SEULES les fiches du contexte RAG ci-dessous sont sources\n"
            "  autorisées pour citer des formations factuelles dans ta réponse.\n"
            "- Tu peux donc REPRENDRE le STYLE de cet exemple, mais JAMAIS son CONTENU\n"
            "  factuel. La question user a son propre contexte de fiches à utiliser.\n"
            "=== FIN EXEMPLE EXPERT ===\n"
        )

    def _maybe_build_golden_qa_prefix(self, question: str) -> str | None:
        """Wrapper qui combine retrieve + build_prefix + stats. Retourne None
        si flag désactivé ou pas de match. Utilisé par .answer()."""
        qa = self._retrieve_golden_qa(question, top_k=1)
        if qa is None:
            self.last_golden_qa = {
                "active": self.use_golden_qa,
                "matched": False,
            }
            return None
        prefix = self._build_few_shot_prefix(qa)
        self.last_golden_qa = {
            "active": True,
            "matched": True,
            "prompt_id": qa.get("prompt_id"),
            "category": qa.get("category"),
            "iteration": qa.get("iteration"),
            "score_total": qa.get("score_total"),
            "retrieve_score": qa.get("_retrieve_score"),
            "decision": qa.get("decision"),
        }
        return prefix if prefix else None
