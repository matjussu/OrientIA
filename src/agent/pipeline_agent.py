"""AgentPipeline — Sprint 4 axe B intégration end-to-end.

Pipeline agentique complet qui chaîne les 3 tools agentiques (Sprints 1-3)
+ les composants RAG existants (retrieval FAISS + génération Mistral) :

```
query
  → ProfileClarifier (Sprint 1, cacheable)
  → [golden_mode] Bridge Profile → ProfileState typed (Sprint 12 A2)
  → [golden_mode] FilterCriteria dérivé pour metadata filter
  → QueryReformuler (Sprint 2, sub-queries multi-corpus)
  → Retrieval FAISS par sub-query (parallel via parallel_map Sprint 3)
    → [enable_metadata_filter] apply_metadata_filter wrap
  → Aggregation cross-corpus (dedupe + top-N)
  → Génération finale Mistral
    → [golden_mode] system_prompt_v4 (4 directives Sprint 11 P0)
    → [golden_mode] golden_qa_prefix (Q&A Golden cap 1 example)
    → [golden_mode] history (buffer N=3 short-term)
  → enable_post_process (Sprint 8 W1, déjà actif)
  → enable_fact_check FetchStatFromSource (Sprint 4)
  → [enable_backstop_b] annotate_response (Sprint 11 P1.1 soft)
  → AgentAnswer
```

Architecture cible bench Sprint 4 vs baseline figée 39.4% verified /
17.9% halluc (PR #75 baseline).

Sprint 12 axe 2 (golden pipeline 2026-05-01) — extension du pipeline
pour fusion agentic Sprint 1-4 + acquis Sprint 9-12. Voir
`docs/GOLDEN_PIPELINE_PLAN.md`.

Cf ADR-051 + verdicts Sprints 1-3 dans `docs/`.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from mistralai.client import Mistral

from src.agent.cache import LRUCache
from src.agent.parallel import parallel_apply
from src.agent.tools.profile_clarifier import Profile, ProfileClarifier
from src.agent.tools.query_reformuler import (
    QueryReformuler,
    ReformulationPlan,
    SubQuery,
)
from src.agent.tools.fetch_stat_from_source import (
    FetchStatFromSource,
    Source,
    StatVerification,
)
from src.rag.generator import generate
from src.rag.metadata_filter import (
    FilterCriteria,
    apply_metadata_boost,
    apply_metadata_filter,
)
from src.rag.retriever import retrieve_top_k

# Note : `src.axe2.profile_mapping` + `src.axe2.contracts` sont importés
# lazily (méthode `answer()`) pour briser le circular import via
# `src.agents.hierarchical.coordinator` → `src.agent.pipeline_agent`. Le
# bridge A2 reste optionnel (golden_mode opt-in) donc late binding OK.
# Les annotations type `ProfileState` dans les dataclasses restent en
# string-form grâce à `from __future__ import annotations`.


@dataclass
class AgentAnswer:
    """Résultat d'une invocation `pipeline.answer(query)`."""

    query: str
    answer_text: str
    profile: Profile | None
    plan: ReformulationPlan | None
    sources_aggregated: list[dict] = field(default_factory=list)
    sub_query_retrievals: list[dict] = field(default_factory=list)
    fact_check_results: list[StatVerification] = field(default_factory=list)
    elapsed_total_s: float = 0.0
    elapsed_clarify_s: float = 0.0
    elapsed_reformulate_s: float = 0.0
    elapsed_retrieve_s: float = 0.0
    elapsed_generate_s: float = 0.0
    elapsed_fact_check_s: float = 0.0
    elapsed_backstop_b_s: float = 0.0  # Sprint 12 axe 2 golden
    cache_hit_profile: bool = False
    # Sprint 12 axe 2 golden — typed profile state (None si golden_mode=False).
    profile_state: ProfileState | None = None
    # Sprint 12 axe 2 golden — nb sources filtrées par metadata_filter
    # (-1 si filter pas activé). Permet de tracer l'impact du filtering.
    metadata_filter_filtered_count: int = -1
    # Sprint 12 axe 2 golden — flag annotations Backstop B appliquées.
    backstop_b_applied: bool = False
    error: str | None = None

    def to_dict(self, include_sources: bool = False) -> dict:
        """Serialize AgentAnswer.

        `include_sources=True` (Sprint 5) sérialise les sources_aggregated
        complètes (texte + score + domain + id + nom etc.) pour permettre
        un fact-check post-hoc avec StatFactChecker (apples-to-apples
        baseline). Coût taille fichier : ~10-50 KB par query si activé.
        """
        out = {
            "query": self.query,
            "answer_text": self.answer_text,
            "profile": self.profile.to_dict() if self.profile else None,
            "plan": self.plan.to_dict() if self.plan else None,
            "sources_aggregated_count": len(self.sources_aggregated),
            "sub_query_retrievals_count": len(self.sub_query_retrievals),
            "fact_check_results": [v.to_dict() for v in self.fact_check_results],
            "elapsed_total_s": self.elapsed_total_s,
            "elapsed_clarify_s": self.elapsed_clarify_s,
            "elapsed_reformulate_s": self.elapsed_reformulate_s,
            "elapsed_retrieve_s": self.elapsed_retrieve_s,
            "elapsed_generate_s": self.elapsed_generate_s,
            "elapsed_fact_check_s": self.elapsed_fact_check_s,
            "cache_hit_profile": self.cache_hit_profile,
            "error": self.error,
        }
        if include_sources:
            # Sérialise format compatible StatFactChecker (existant `src/rag/fact_checker.py`).
            # StatFactChecker.verify(answer, sources) attend list[dict] avec
            # `fiche` key contenant le texte recherchable.
            out["sources_aggregated"] = [
                {
                    "score": float(s.get("score", 0)),
                    "fiche": s.get("fiche", {}),
                }
                for s in self.sources_aggregated
            ]
        return out


@dataclass
class AgentPipeline:
    """Orchestrateur agentique end-to-end Sprint 4 (étendu Sprint 12 golden)."""

    client: Mistral
    fiches: list[dict]  # phaseD index data (54 297 cells) ou golden corpus (61 657)
    index: Any  # faiss.IndexFlatL2 — loaded externally
    profile_cache: LRUCache | None = None
    sub_query_top_k: int = 6  # top-K par sub-query (6 × ~5 sub-queries = ~30 candidates)
    aggregated_top_n: int = 8  # top-N final agrégé (optim Sprint 4 : 12→8 -33% gen tokens)
    parallel_max_workers: int = 3  # threadpool pour retrieval
    parallel_fact_check_workers: int = 3  # parallel fact-check Sprint 4 optim
    enable_fact_check: bool = False  # opt-in pour Sprint 4 bench
    fact_check_max_claims: int = 5  # cap claims fact-check pour budget
    generation_model: str = "mistral-medium-latest"  # gen finale model
    # Sprint 7 Action 3 — anti-hallu LLM
    system_prompt_override: str | None = None  # None = SYSTEM_PROMPT v3.2 (default)
    # Pour activer v3.3 strict (R1-R6) : passer SYSTEM_PROMPT_V33_STRICT
    # depuis src.prompt.system_strict.
    # Sprint 8 Wave 1 — post-process anti-hallu (bugs P0 user_test_v3)
    enable_post_process: bool = True  # default ON : fix Bugs Q8, Q9, Q10
    # Désactivable pour bench apples-to-apples Sprint 5/6/7 si besoin.
    # Post-process déterministe non-LLM (≠ critic loop Sprint 7 OFF par
    # défaut), ne risque pas de régression LLM-driven.

    # ---- Sprint 12 axe 2 golden pipeline (2026-05-01) ----
    # Cf docs/GOLDEN_PIPELINE_PLAN.md étape 3.
    enable_metadata_filter: bool = False
    """Sprint 12 axe 2 v2 (2026-05-01) — sémantique passée de filter strict
    à **boost score soft** (×`metadata_boost_factor`).

    Quand `True` ET `ProfileState` typé dérivé du `Profile`, applique
    `apply_metadata_boost()` post-retrieve : les fiches matchant le
    `FilterCriteria` voient leur score multiplié par `metadata_boost_factor`
    (default 1.3), les autres restent à leur score d'origine. Pas de drop.

    Motivation du switch : bench validation étape 4 a montré que le filter
    strict tuait l'aspect `diversite_geo` (-11 cumul vs enriched, golden
    monopolisait 1 région). Le boost soft préserve la diversité.

    No-op si `FilterCriteria` vide ou `metadata_boost_factor=1.0`. Le flag
    legacy filter strict reste accessible via `metadata_filter_mode="strict"`
    (à wirer si besoin A/B futur — non implémenté MVP)."""

    metadata_boost_factor: float = 1.3
    """Multiplicateur de score appliqué aux fiches matchant `FilterCriteria`
    quand `enable_metadata_filter=True`. Default 1.3 (Sprint 12 v2).
    Cible : remonter `diversite_geo` golden de 5 → 12+ sans tuer la
    pertinence profil. 1.0 = no-op équivalent à `enable_metadata_filter=False`."""

    golden_qa_prefix: str | None = None
    """Q&A Golden cap 1 example pré-construit (Sprint 10 chantier D),
    injecté en prefix du system prompt de la génération finale. None =
    pas de Q&A Golden (default). Le caller construit le prefix
    déterministiquement (typiquement via le générateur Q&A Golden)."""

    enable_backstop_b: bool = False
    """Active le post-process Backstop B soft (`src/backstop/soft_annotator`)
    qui annote les chiffres non-sourcés sans les effacer. En série après
    `FetchStatFromSource` (FetchStat in-loop top-N + Backstop annote
    les claims chiffrés restants). Voir Sprint 11 P1.1 PR #113."""

    backstop_b_corpus_index: Any | None = None
    """Pré-construit `CorpusFactIndex` (`src/backstop/soft_annotator`)
    pour cross-ref des chiffres dans le corpus golden. Réutilisable cross-
    queries pour amortir le coût de construction. None et
    `enable_backstop_b=True` → l'index est construit lazy à la 1ʳᵉ query."""

    history_buffer_size: int = 0
    """Capacité du buffer mémoire short-term (cap N derniers tours
    user+assistant). 0 = disabled (single-turn, default). Plan golden
    pipeline : N=3 derniers tours injectés via `generate(history=...)`."""

    def __post_init__(self) -> None:
        self.clarifier = ProfileClarifier(
            client=self.client, cache=self.profile_cache,
        )
        self.reformuler = QueryReformuler(client=self.client)
        if self.enable_fact_check:
            self.fact_checker = FetchStatFromSource(client=self.client)
        else:
            self.fact_checker = None

        # Sprint 12 axe 2 golden — buffer mémoire short-term (turn history).
        # Stocke list[{"role": str, "content": str}] format Mistral.
        self._history_buffer: list[dict] = []

        # Sprint 12 axe 2 golden — `FilterCriteria` courant pour wrap retrieve.
        # Posé en début d'`answer()` quand enable_metadata_filter=True, lu
        # par `_retrieve_for_subquery` (évite de muter la signature interne).
        self._current_filter_criteria: FilterCriteria | None = None

        # Sprint 12 axe 2 golden — lazy CorpusFactIndex pour Backstop B.
        self._backstop_b_index_cache = self.backstop_b_corpus_index

    def add_turn_to_history(self, user_msg: str, assistant_msg: str) -> None:
        """Append un tour au buffer mémoire short-term (cap `history_buffer_size`).

        Format Mistral : list[{"role": "user"|"assistant", "content": str}].
        Si `history_buffer_size == 0`, no-op (mémoire désactivée).
        """
        if self.history_buffer_size <= 0:
            return
        self._history_buffer.append({"role": "user", "content": user_msg})
        self._history_buffer.append({"role": "assistant", "content": assistant_msg})
        # Cap = history_buffer_size derniers TOURS (chacun = 1 user + 1 assistant
        # = 2 messages). On garde donc 2*N messages.
        max_messages = 2 * self.history_buffer_size
        if len(self._history_buffer) > max_messages:
            self._history_buffer = self._history_buffer[-max_messages:]

    def _get_backstop_index(self) -> Any:
        """Retourne le `CorpusFactIndex` pré-construit, ou raise si manquant.

        Le caller (e.g. `src/eval/systems.py`) doit construire l'index via
        `CorpusFactIndex.from_unified_json(corpus_path)` puis le passer au
        constructeur via `backstop_b_corpus_index=`. On évite la dépendance
        path filesystem dans `AgentPipeline` (anti-coupling) et on amortit
        le coût build cross-queries.
        """
        if self._backstop_b_index_cache is None:
            raise ValueError(
                "enable_backstop_b=True mais backstop_b_corpus_index non fourni. "
                "Construire via CorpusFactIndex.from_unified_json(corpus_path) "
                "puis passer en config AgentPipeline."
            )
        return self._backstop_b_index_cache

    def _retrieve_for_subquery(self, sub_query: SubQuery) -> dict:
        """Retrieve top-K depuis FAISS pour une sub-query.

        Pas de filtering par target_corpus (les vecteurs sont mêlés
        dans phaseD). Le rerank du domain_hint Sprint 1+ se fait au
        niveau aggregation. Pour MVP Sprint 4, on prend top-K L2 brut
        par sub-query, on dédupe à l'aggregation.

        Sprint 12 axe 2 v2 (2026-05-01) — si `enable_metadata_filter=True` ET
        `_current_filter_criteria` set, applique `apply_metadata_boost()`
        post-retrieve : boost ×`metadata_boost_factor` (default 1.3) sur les
        fiches matchant le profil, **aucun drop**. Les K candidats de retour
        sont les `sub_query_top_k` originaux re-triés. No-op si
        `criteria.is_empty()` ou `metadata_boost_factor=1.0`.

        Différence vs étape 4 (filter strict) : pas de sur-retrieve ×2, plus
        économique en API embed calls car aucun candidat n'est droppé. Le
        re-tri par score boosté préserve la diversité géographique
        (cf bench validation étape 6).
        """
        criteria = self._current_filter_criteria
        boost_active = (
            self.enable_metadata_filter
            and criteria is not None
            and not criteria.is_empty()
            and self.metadata_boost_factor != 1.0
        )
        retrieved = retrieve_top_k(
            self.client,
            self.index,
            self.fiches,
            sub_query.text,
            k=self.sub_query_top_k,
        )
        if boost_active:
            retrieved = apply_metadata_boost(
                retrieved, criteria, boost_factor=self.metadata_boost_factor
            )
        return {
            "sub_query_id": id(sub_query),  # référence Python (dispo dans plan.sub_queries)
            "sub_query_text": sub_query.text,
            "target_corpus": sub_query.target_corpus,
            "priority": sub_query.priority,
            "retrieved": retrieved,
        }

    def _aggregate_sources(
        self, sub_query_retrievals: list[dict]
    ) -> list[dict]:
        """Dedupe sources cross-sub-query par id stable + score max."""
        # Index par id stable. Pour formation: cod_aff_form + nom + etab.
        # Pour autres corpus: id explicit dans la fiche.
        by_id: dict[str, dict] = {}
        for retrieval in sub_query_retrievals:
            for r in retrieval["retrieved"]:
                fiche = r["fiche"]
                source_id = (
                    fiche.get("id")
                    or fiche.get("numero_fiche")
                    or f"{fiche.get('nom', '')[:40]}|{fiche.get('etablissement', '')[:40]}"
                )
                # Garde le meilleur score (max) si plusieurs sub-queries
                # font remonter la même fiche
                if source_id in by_id:
                    if r.get("score", 0) > by_id[source_id].get("score", 0):
                        by_id[source_id] = r
                else:
                    by_id[source_id] = r
        # Sort par score desc, top_N
        sorted_sources = sorted(
            by_id.values(),
            key=lambda r: r.get("score", 0),
            reverse=True,
        )
        return sorted_sources[: self.aggregated_top_n]

    def _extract_claims_for_fact_check(
        self, answer_text: str
    ) -> list[str]:
        """Extract claims chiffrés / réglementaires de la réponse.

        Stratégie naïve MVP : split sur phrases, garde celles avec
        des chiffres ou des termes réglementaires explicit (RNCP,
        niveau, certifié, validation, etc.).
        """
        import re
        sentences = re.split(r"(?<=[.!?])\s+", answer_text)
        claims = []
        # Pattern : phrase avec nombre OU mot réglementaire
        regex_chiffre = re.compile(r"\d{2,}|\d+\s*%|\d+\s*€")
        regex_reg = re.compile(
            r"\b(?:RNCP|niveau\s+\d|certifié|validé|protégé|obligatoire|requis|exige)\b",
            re.IGNORECASE,
        )
        for s in sentences:
            s_clean = s.strip()
            if len(s_clean) < 15:
                continue
            if regex_chiffre.search(s_clean) or regex_reg.search(s_clean):
                claims.append(s_clean)
            if len(claims) >= self.fact_check_max_claims:
                break
        return claims

    def answer(self, query: str) -> AgentAnswer:
        """Pipeline end-to-end query → AgentAnswer."""
        t0_total = time.time()
        result = AgentAnswer(query=query, answer_text="", profile=None, plan=None)

        try:
            # Étape 1 : ProfileClarifier
            t0 = time.time()
            cache_size_before = (
                len(self.profile_cache) if self.profile_cache else 0
            )
            profile = self.clarifier.clarify(query)
            result.elapsed_clarify_s = round(time.time() - t0, 2)
            result.profile = profile
            # Heuristique cache hit : si le cache a la même size avant/après
            # ET que stats hits > 0 (donc le call a touché le cache)
            if self.profile_cache:
                cache_stats = self.profile_cache.stats()
                # Si latence quasi-nulle = cache hit
                result.cache_hit_profile = result.elapsed_clarify_s < 0.1

            # Sprint 12 axe 2 golden — bridge Profile → ProfileState typed +
            # FilterCriteria dérivé pour metadata filter wrap. Coût $0
            # (pure-function déterministe), exécuté seulement si feature opt-in.
            # Late import : évite circular via src.agents.hierarchical.
            if self.enable_metadata_filter and profile is not None:
                from src.axe2.profile_mapping import (
                    derive_filter_criteria_from_profile_state,
                    profile_to_profile_state,
                )
                profile_state = profile_to_profile_state(profile)
                result.profile_state = profile_state
                self._current_filter_criteria = (
                    derive_filter_criteria_from_profile_state(profile_state)
                )
            else:
                self._current_filter_criteria = None

            # Étape 2 : QueryReformuler
            t0 = time.time()
            plan = self.reformuler.reformulate(query, profile)
            result.elapsed_reformulate_s = round(time.time() - t0, 2)
            result.plan = plan

            # Étape 3 : Retrieval parallel par sub-query
            t0 = time.time()
            retrievals = parallel_apply(
                lambda sq: (self._retrieve_for_subquery(sq),),
                [(sq,) for sq in plan.sub_queries],
                max_workers=self.parallel_max_workers,
                return_exceptions=True,
            )
            # Unpack (parallel_apply wraps in tuple to handle multi-arg) —
            # ici lambda takes one arg, return est un tuple (result,). Adapt.
            sub_query_retrievals = []
            for r in retrievals:
                if isinstance(r, Exception):
                    continue
                # r est le retour de _retrieve_for_subquery (dict)
                if isinstance(r, tuple):
                    r = r[0]
                sub_query_retrievals.append(r)
            result.elapsed_retrieve_s = round(time.time() - t0, 2)
            result.sub_query_retrievals = sub_query_retrievals

            # Étape 4 : Aggregation
            sources_agg = self._aggregate_sources(sub_query_retrievals)
            result.sources_aggregated = sources_agg
            # Sprint 12 axe 2 golden — télémétrie metadata filter (nb sources
            # finales agrégées si filter actif, -1 sinon). Sert au bench A/B
            # pour mesurer l'impact du filtering sur le retrieval.
            if (
                self.enable_metadata_filter
                and self._current_filter_criteria is not None
                and not self._current_filter_criteria.is_empty()
            ):
                result.metadata_filter_filtered_count = len(sources_agg)

            # Étape 5 : Génération finale (golden-aware)
            t0 = time.time()
            answer_text = generate(
                self.client,
                sources_agg,
                query,
                model=self.generation_model,
                temperature=0.3,
                system_prompt_override=self.system_prompt_override,
                # Sprint 12 axe 2 golden — Q&A Golden cap 1 example +
                # buffer mémoire short-term (cap N tours).
                golden_qa_prefix=self.golden_qa_prefix,
                history=list(self._history_buffer) if self._history_buffer else None,
            )
            result.elapsed_generate_s = round(time.time() - t0, 2)

            # Sprint 8 Wave 1 — post-process anti-hallu (bugs P0)
            if self.enable_post_process:
                from src.rag.post_process import post_process_answer
                answer_text, _ = post_process_answer(answer_text, sources_agg)

            result.answer_text = answer_text

            # Étape 6 (optionnelle) : fact-check post-gen — PARALLEL Sprint 4 optim
            if self.enable_fact_check and self.fact_checker:
                t0 = time.time()
                claims = self._extract_claims_for_fact_check(answer_text)
                # Convert sources_agg en list[Source] pour FetchStatFromSource
                source_objs = [
                    Source(
                        id=str(s["fiche"].get("id") or s["fiche"].get("numero_fiche") or "?"),
                        text=(s["fiche"].get("text") or s["fiche"].get("nom", "")[:300]),
                        domain=s["fiche"].get("domain", "formation"),
                        score=float(s.get("score", 0)),
                    )
                    for s in sources_agg
                ]
                if claims:
                    # Parallel fact-check via parallel_apply Sprint 3
                    fact_results_raw = parallel_apply(
                        self.fact_checker.verify,
                        [(claim, source_objs) for claim in claims],
                        max_workers=self.parallel_fact_check_workers,
                        return_exceptions=True,
                    )
                    fact_results = [
                        r for r in fact_results_raw
                        if not isinstance(r, Exception)
                    ]
                else:
                    fact_results = []
                result.fact_check_results = fact_results
                result.elapsed_fact_check_s = round(time.time() - t0, 2)

            # Sprint 12 axe 2 golden — Étape 7 : Backstop B soft post-process.
            # En série après FetchStatFromSource (FetchStat in-loop top-N
            # vérifie quelques claims, Backstop annote les chiffres restants
            # non-sourcés sans les effacer + ajoute le disclaimer global).
            # Skip si fact-check est explicitement OFF — même architecture
            # complémentaire que prévue dans le plan.
            if self.enable_backstop_b:
                t0 = time.time()
                try:
                    from src.backstop import annotate_response
                    corpus_idx = self._get_backstop_index()
                    annotated = annotate_response(result.answer_text, corpus_idx)
                    result.answer_text = annotated
                    result.backstop_b_applied = True
                except Exception as bs_err:
                    # Backstop B est non-bloquant (post-process best-effort) :
                    # une erreur ici ne doit pas faire échouer la query.
                    result.backstop_b_applied = False
                    # Trace dans `error` uniquement si pas d'erreur amont.
                    if not result.error:
                        result.error = f"backstop_b_warning: {type(bs_err).__name__}: {bs_err}"
                result.elapsed_backstop_b_s = round(time.time() - t0, 2)

        except Exception as e:
            result.error = f"{type(e).__name__}: {e}"

        result.elapsed_total_s = round(time.time() - t0_total, 2)
        return result
