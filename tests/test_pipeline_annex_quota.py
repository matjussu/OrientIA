"""Tests Option C v6 — retrieval annex quota indépendant du domain_hint.

Phase C correctif. Vérifie que `_retrieve_with_annex_quota` :
- Sépare correctement main_pool vs annex_pool selon le champ `domain`
- Active le quota seulement si annexes ont score ≥ seuil
- N'introduit pas de pollution quand toutes les annexes ont score faible
- Retourne top-K avec mix main+annex respectant le quota
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from src.rag.pipeline import (
    ANNEX_QUOTA_K_INITIAL,
    ANNEX_QUOTA_MAX_PER_TOPK,
    ANNEX_QUOTA_MIN_SCORE,
    OrientIAPipeline,
)


# ─────────────── Fixtures retrieved (mock retrieve_top_k output) ───────────────


def _make_result(score: float, domain: str | None, name: str) -> dict:
    """Construit un result fictif (format retrieve_top_k)."""
    return {
        "score": score,
        "base_score": score,
        "fiche": {
            "nom": name,
            "domain": domain,
            "source": "test",
        },
    }


def _make_pipeline_skeleton() -> OrientIAPipeline:
    """Construit un pipeline minimal pour tester la logique de quota.

    On bypasse les attributs lourds (client, index, fiches) en les mock-ant
    avec des objets simples. Seul `_retrieve_with_annex_quota` est testé.
    """
    pipeline = OrientIAPipeline.__new__(OrientIAPipeline)
    # Init minimal : on n'utilise que les attributs nécessaires
    pipeline.client = None
    pipeline.fiches = []
    from src.rag.reranker import RerankConfig
    pipeline.rerank_config = RerankConfig()
    pipeline.use_metadata_filter = False
    pipeline.last_filter_stats = None
    pipeline.index = object()  # placeholder, on patche retrieve_top_k
    # Phase C++ — attributs double-index (mockés)
    pipeline._main_subindex = None
    pipeline._annex_subindex = None
    pipeline._main_subindex_orig_indices = None
    pipeline._annex_subindex_orig_indices = None
    pipeline._double_index_built = True  # skip lazy build
    pipeline._bm25_index = None
    pipeline._bm25_built = True  # skip lazy build BM25
    return pipeline


# ─────────────── Tests structurels (séparation pool) ───────────────


class TestPoolSeparation:
    def test_main_only_when_no_annex_in_results(self):
        """Si retrieve ne ramène aucune annexe → top retourné = full main reranked."""
        pipeline = _make_pipeline_skeleton()
        results = [
            _make_result(1.05, None, "Master Cyber"),
            _make_result(1.02, None, "BUT Info"),
            _make_result(0.95, None, "Licence Pro Cyber"),
        ]
        with patch.object(pipeline, "_retrieve_with_double_subindex",
                          return_value=([r for r in results if not r["fiche"].get("domain")],
                                        [r for r in results if r["fiche"].get("domain")])):
            top = pipeline._retrieve_with_annex_quota("question test", k=30, target=3, domain_hint=None)

        # Retourne main complet (3 fiches), MMR slicera en aval
        assert len(top) == 3
        assert all(not (r["fiche"].get("domain")) for r in top)
        stats = pipeline.last_filter_stats
        assert stats["n_annex_pool"] == 0
        assert stats["annex_quota_active"] is False

    def test_annex_quota_active_when_high_score(self):
        """Si annex top score ≥ seuil → quota activé, top-3 annexes boostées."""
        pipeline = _make_pipeline_skeleton()
        results = [
            _make_result(1.05, None, "Master Cyber"),
            _make_result(1.02, None, "BUT Info"),
            _make_result(0.95, None, "Licence Pro"),
            _make_result(0.85, None, "BTS Cyber"),
            _make_result(0.80, None, "BUT Lyon"),
            # Annexes avec score ≥ 0.6 — quota doit s'activer
            _make_result(0.75, "metier_prospective", "DARES Métier 2030 Lyon"),
            _make_result(0.70, "crous", "CROUS Lyon"),
            _make_result(0.65, "metier", "ONISEP métier ingénieur"),
        ]
        with patch.object(pipeline, "_retrieve_with_double_subindex",
                          return_value=([r for r in results if not r["fiche"].get("domain")],
                                        [r for r in results if r["fiche"].get("domain")])):
            top = pipeline._retrieve_with_annex_quota("question test", k=30, target=5, domain_hint=None)

        stats = pipeline.last_filter_stats
        assert stats["annex_quota_active"] is True
        # 3 annexes >= seuil, max 3 boostées
        assert stats["n_annex_above_threshold"] == 3
        assert stats["n_annex_boosted"] == ANNEX_QUOTA_MAX_PER_TOPK
        # Liste retournée = main + boostées (5 main + 3 annex = 8)
        assert len(top) == 8
        # Top de la liste après tri = annexes boostées (score 1.65, 1.70, 1.75
        # > Master Cyber 1.05)
        assert top[0]["fiche"].get("domain") in ("metier_prospective", "crous", "metier")
        # `_quota_boosted` flag présent sur les boostées
        n_boosted = sum(1 for r in top if r.get("_quota_boosted"))
        assert n_boosted == 3

    def test_annex_below_threshold_not_included(self):
        """Si toutes les annexes ont score < seuil → pas de quota, retour = main only."""
        pipeline = _make_pipeline_skeleton()
        results = [
            _make_result(1.05, None, "Master Cyber"),
            _make_result(1.02, None, "BUT Info"),
            _make_result(0.95, None, "Licence Pro"),
            # Annexes avec score < 0.6 — quota PAS activé
            _make_result(0.55, "metier_prospective", "DARES sans rapport"),
            _make_result(0.50, "crous", "CROUS sans rapport"),
        ]
        with patch.object(pipeline, "_retrieve_with_double_subindex",
                          return_value=([r for r in results if not r["fiche"].get("domain")],
                                        [r for r in results if r["fiche"].get("domain")])):
            top = pipeline._retrieve_with_annex_quota("question test", k=30, target=3, domain_hint=None)

        stats = pipeline.last_filter_stats
        assert stats["annex_quota_active"] is False
        # Retourne main only (pas de pollution annexe hors-sujet)
        assert all(not (r["fiche"].get("domain")) for r in top)


# ─────────────── Tests scénarios concrets ───────────────


class TestScenarioFormationsPures:
    """Question pure formation (prépa, master) — annexes avec score faible
    ne doivent PAS polluer le top-K."""

    def test_no_annex_pollution_for_formation_question(self):
        pipeline = _make_pipeline_skeleton()
        # Top scores = formations pertinentes, annexes avec score très faible
        results = [
            _make_result(1.10, None, "CPGE MPSI Lycée Parc Lyon"),
            _make_result(1.08, None, "CPGE PCSI Henri IV"),
            _make_result(1.05, None, "Prépa Louis-le-Grand"),
            _make_result(0.45, "metier", "Métier ingénieur (générique)"),  # < seuil
            _make_result(0.40, "insee_salaire", "Salaire PCS 38"),  # < seuil
        ]
        with patch.object(pipeline, "_retrieve_with_double_subindex",
                          return_value=([r for r in results if not r["fiche"].get("domain")],
                                        [r for r in results if r["fiche"].get("domain")])):
            top = pipeline._retrieve_with_annex_quota("Quelle prépa MPSI à Lyon ?", k=30, target=3, domain_hint=None)
        # Top-K = 3 prépas, 0 annexe (pas de pollution)
        assert len(top) == 3
        assert all(not r["fiche"].get("domain") for r in top)


class TestScenarioMixteFormationAnnexe:
    """Question mixte (DARES Occitanie 2030) — quota doit ramener
    les fiches DARES dans le top-K."""

    def test_dares_annex_included_when_high_score(self):
        pipeline = _make_pipeline_skeleton()
        results = [
            _make_result(0.85, None, "BTS quelque chose Occitanie"),
            _make_result(0.82, None, "BUT Occitanie"),
            _make_result(0.80, None, "Licence Occitanie"),
            _make_result(0.78, None, "Master Occitanie"),
            _make_result(0.76, None, "DUT Occitanie"),
            # Fiches DARES avec score raisonnable (≥ 0.6)
            _make_result(0.72, "metier_prospective", "DARES Occitanie A1Z"),
            _make_result(0.70, "metier_prospective", "DARES Occitanie B0Z"),
            _make_result(0.65, "metier_prospective", "DARES Occitanie C1Z"),
        ]
        with patch.object(pipeline, "_retrieve_with_double_subindex",
                          return_value=([r for r in results if not r["fiche"].get("domain")],
                                        [r for r in results if r["fiche"].get("domain")])):
            top = pipeline._retrieve_with_annex_quota(
                "Quels métiers en Occitanie 2030 ?", k=30, target=5, domain_hint=None
            )
        stats = pipeline.last_filter_stats
        assert stats["annex_quota_active"] is True
        # Au moins 1 fiche DARES dans top-5 (après boost +1.0, leurs scores 1.65-1.72
        # dépassent largement les formations 0.76-0.85)
        top_5 = top[:5]
        n_dares = sum(1 for r in top_5 if r["fiche"].get("domain") == "metier_prospective")
        assert n_dares >= 1, f"Aucune DARES dans top-5: {[r['fiche']['nom'] for r in top_5]}"


# ─────────────── Tests cap quota ───────────────


class TestQuotaCap:
    def test_max_3_annexes_boosted(self):
        """Même si beaucoup d'annexes ont score ≥ seuil, max 3 boostées."""
        pipeline = _make_pipeline_skeleton()
        # 1 main + 10 annexes haut score
        results = [_make_result(1.0, None, "Formation")] + [
            _make_result(0.85 - i * 0.02, "metier_prospective", f"DARES {i}")
            for i in range(10)
        ]
        with patch.object(pipeline, "_retrieve_with_double_subindex",
                          return_value=([r for r in results if not r["fiche"].get("domain")],
                                        [r for r in results if r["fiche"].get("domain")])):
            top = pipeline._retrieve_with_annex_quota("test", k=30, target=10, domain_hint=None)
        # Compte les boostées (cap à ANNEX_QUOTA_MAX_PER_TOPK=3)
        n_boosted = sum(1 for r in top if r.get("_quota_boosted"))
        assert n_boosted == ANNEX_QUOTA_MAX_PER_TOPK
        # La liste retournée contient main complet + 3 annexes boostées
        # (les autres 7 annexes non boostées sont écartées par le slicing
        # `annex_reranked[:n_annex_quota]`)
        n_annex_total = sum(1 for r in top if r["fiche"].get("domain"))
        assert n_annex_total == ANNEX_QUOTA_MAX_PER_TOPK


# ─────────────── Tests stats audit ───────────────


class TestStatsAudit:
    def test_stats_populated_correctly(self):
        pipeline = _make_pipeline_skeleton()
        results = [
            _make_result(1.0, None, "Main 1"),
            _make_result(0.9, None, "Main 2"),
            _make_result(0.7, "metier", "Annex 1"),
            _make_result(0.65, "metier_detail", "Annex 2"),
        ]
        with patch.object(pipeline, "_retrieve_with_double_subindex",
                          return_value=([r for r in results if not r["fiche"].get("domain")],
                                        [r for r in results if r["fiche"].get("domain")])):
            pipeline._retrieve_with_annex_quota("test", k=30, target=3, domain_hint=None)
        stats = pipeline.last_filter_stats
        assert stats["filter_active"] is False
        assert stats["annex_quota_strategy"] == "v6_double_index_score_threshold"
        assert stats["n_main_pool"] == 2
        assert stats["n_annex_pool"] == 2
        assert stats["annex_top_score"] == 0.7
        assert stats["annex_quota_active"] is True
