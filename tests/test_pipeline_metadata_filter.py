"""Tests d'intégration Sprint 10 chantier C §8.3-§8.4.

Plug `apply_metadata_filter` dans `OrientIAPipeline.answer()` derrière flag
opt-in `use_metadata_filter`. Auto-expansion k×3 → ×6 → ×10 si filter
trop restrictif. Backward compat strict quand flag False ou criteria empty.

Mock heavy : on n'invoque ni Mistral subprocess, ni FAISS réel — on patch
`retrieve_top_k`, `rerank`, `mmr_select`, `generate` pour vérifier UNIQUEMENT
le wiring du filter et l'auto-expansion.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.rag.metadata_filter import FilterCriteria
from src.rag.pipeline import (
    INITIAL_K_MULTIPLIER,
    MAX_K_MULTIPLIER,
    OrientIAPipeline,
)


# ─────────────────── Fixtures ───────────────────


@pytest.fixture
def fake_fiches():
    """6 fiches mock avec frontmatter divers pour tester filtres composites."""
    return [
        {"id": 1, "region": "occitanie", "niveau": 3, "alternance": True, "secteur": "informatique"},
        {"id": 2, "region": "ile-de-france", "niveau": 3, "alternance": True, "secteur": "informatique"},
        {"id": 3, "region": "occitanie", "niveau": 5, "alternance": False, "secteur": "droit"},
        {"id": 4, "region": "national", "niveau": 6, "alternance": True, "secteur": "informatique"},
        {"id": 5, "region": "occitanie", "niveau": 3, "alternance": False, "secteur": "informatique"},
        {"id": 6, "region": "occitanie", "niveau": 2, "alternance": True, "secteur": "informatique"},
    ]


@pytest.fixture
def pipeline_with_index(fake_fiches):
    """OrientIAPipeline mocké avec index "ready" (pas de réel build/load)."""
    pipe = OrientIAPipeline(
        client=MagicMock(),
        fiches=fake_fiches,
        use_metadata_filter=True,
    )
    pipe.index = MagicMock()  # bypass index check
    return pipe


def _wrap_retrieved(fiches: list[dict]) -> list[dict]:
    """Format retrieve_top_k : list of {fiche, score, base_score, embedding}."""
    return [
        {"fiche": f, "score": 1.0 - i * 0.01, "base_score": 1.0, "embedding": None}
        for i, f in enumerate(fiches)
    ]


# ─────────────────── (a) backward compat ───────────────────


class TestBackwardCompatibility:
    def test_use_metadata_filter_false_default(self, fake_fiches):
        """Sans flag à True, comportement v1 strict (pas de filter même si
        criteria fourni)."""
        pipe = OrientIAPipeline(client=MagicMock(), fiches=fake_fiches)
        assert pipe.use_metadata_filter is False
        pipe.index = MagicMock()

        with patch("src.rag.pipeline.retrieve_top_k", return_value=_wrap_retrieved(fake_fiches)):
            with patch("src.rag.pipeline.rerank", side_effect=lambda r, *a, **k: r):
                with patch("src.rag.pipeline.generate", return_value="answer"):
                    answer, top = pipe.answer(
                        "question test",
                        criteria=FilterCriteria(region="occitanie"),
                    )

        # Le filter ne s'est PAS appliqué : on a tous les 6 (k_eff = k = 30 effectif)
        assert pipe.last_filter_stats["filter_active"] is False
        assert pipe.last_filter_stats["expansions"] == 0

    def test_criteria_none_no_filter_applied(self, pipeline_with_index, fake_fiches):
        """use_metadata_filter=True mais criteria=None → comportement v1."""
        with patch("src.rag.pipeline.retrieve_top_k", return_value=_wrap_retrieved(fake_fiches)):
            with patch("src.rag.pipeline.rerank", side_effect=lambda r, *a, **k: r):
                with patch("src.rag.pipeline.generate", return_value="answer"):
                    pipeline_with_index.answer("q", criteria=None)

        assert pipeline_with_index.last_filter_stats["filter_active"] is False
        assert pipeline_with_index.last_filter_stats["criteria_empty"] is True

    def test_criteria_empty_no_filter_applied(self, pipeline_with_index, fake_fiches):
        """FilterCriteria() avec tous champs None → is_empty() → pas de filter."""
        with patch("src.rag.pipeline.retrieve_top_k", return_value=_wrap_retrieved(fake_fiches)):
            with patch("src.rag.pipeline.rerank", side_effect=lambda r, *a, **k: r):
                with patch("src.rag.pipeline.generate", return_value="answer"):
                    pipeline_with_index.answer("q", criteria=FilterCriteria())

        assert pipeline_with_index.last_filter_stats["filter_active"] is False


# ─────────────────── (b) filter actif basique ───────────────────


class TestFilterActiveBasic:
    def test_filter_applied_with_criteria(self, pipeline_with_index, fake_fiches):
        """criteria region:occitanie → seuls les 4 fiches occitanie+national passent."""
        with patch("src.rag.pipeline.retrieve_top_k", return_value=_wrap_retrieved(fake_fiches)):
            with patch("src.rag.pipeline.rerank", side_effect=lambda r, *a, **k: r):
                with patch("src.rag.pipeline.generate", return_value="answer"):
                    answer, top = pipeline_with_index.answer(
                        "q",
                        k=10,
                        top_k_sources=3,
                        criteria=FilterCriteria(region="occitanie"),
                    )

        stats = pipeline_with_index.last_filter_stats
        assert stats["filter_active"] is True
        # 5 fiches matchent : 4 occitanie (id 1, 3, 5, 6) + 1 national (id 4)
        assert stats["n_after_filter"] == 5
        # Top 3 retournés
        assert len(top) == 3

    def test_filter_composite_AND(self, pipeline_with_index, fake_fiches):
        """region=occitanie + niveau=3 + alternance=True → fiche id=1 uniquement."""
        with patch("src.rag.pipeline.retrieve_top_k", return_value=_wrap_retrieved(fake_fiches)):
            with patch("src.rag.pipeline.rerank", side_effect=lambda r, *a, **k: r):
                with patch("src.rag.pipeline.generate", return_value="answer"):
                    answer, top = pipeline_with_index.answer(
                        "q",
                        k=10,
                        top_k_sources=10,
                        criteria=FilterCriteria(
                            region="occitanie",
                            niveau_min=3,
                            niveau_max=3,
                            alternance=True,
                            secteur=["informatique"],
                        ),
                    )

        # Seule fiche id=1 matche tous les criteria
        assert pipeline_with_index.last_filter_stats["n_after_filter"] == 1
        assert top[0]["fiche"]["id"] == 1


# ─────────────────── (c) auto-expansion §8.4 ───────────────────


class TestAutoExpansion:
    def test_no_expansion_when_enough_results(self, pipeline_with_index, fake_fiches):
        """Si filtered count >= target dès le 1er retrieve, pas d'expansion."""
        # criteria peu restrictif : 4 fiches matchent, target=3 → 1ère passe OK
        with patch("src.rag.pipeline.retrieve_top_k", return_value=_wrap_retrieved(fake_fiches)) as mock_retrieve:
            with patch("src.rag.pipeline.rerank", side_effect=lambda r, *a, **k: r):
                with patch("src.rag.pipeline.generate", return_value="answer"):
                    pipeline_with_index.answer(
                        "q",
                        k=10,
                        top_k_sources=3,
                        criteria=FilterCriteria(region="occitanie"),
                    )

        # retrieve_top_k appelé exactement 1 fois (k_eff = k × 3 = 30)
        assert mock_retrieve.call_count == 1
        assert pipeline_with_index.last_filter_stats["expansions"] == 0
        # k_final = k_eff initial = k × INITIAL_K_MULTIPLIER
        assert pipeline_with_index.last_filter_stats["k_final"] == 10 * INITIAL_K_MULTIPLIER

    def test_expansion_when_filter_too_restrictive(self, fake_fiches):
        """Filter restrictif : retrieve initial donne 6 fiches dont 1 seule
        matche, target=3. Le pipeline doit expand jusqu'à atteindre target
        ou MAX_K_MULTIPLIER."""
        # On va simuler : 1ère passe k=30 → 1 fiche matche / target=3
        # 2ème passe k=60 → 1 fiche matche / target=3 (insuffisant)
        # 3ème passe k=120 → ... etc, eventuellement hit MAX

        pipe = OrientIAPipeline(
            client=MagicMock(), fiches=fake_fiches, use_metadata_filter=True
        )
        pipe.index = MagicMock()

        # criteria très restrictif : niveau=6 + alternance=True + secteur=informatique
        # Seule fiche id=4 matche (region=national, niveau=6, alternance=True, secteur=informatique)
        criteria = FilterCriteria(
            niveau_min=6, niveau_max=6, alternance=True, secteur=["informatique"]
        )

        retrieve_calls = []

        def mock_retrieve(client, index, fiches, question, k):
            retrieve_calls.append(k)
            # Retourne toujours les 6 fiches (mock — pas de vrai FAISS)
            return _wrap_retrieved(fiches)

        with patch("src.rag.pipeline.retrieve_top_k", side_effect=mock_retrieve):
            with patch("src.rag.pipeline.rerank", side_effect=lambda r, *a, **k: r):
                with patch("src.rag.pipeline.generate", return_value="answer"):
                    pipe.answer("q", k=10, top_k_sources=3, criteria=criteria)

        # On a appelé retrieve plusieurs fois (filter trop restrictif → expand)
        assert len(retrieve_calls) >= 2
        # k_eff progresse géométriquement (×3 puis ×6, cap ×10)
        assert retrieve_calls[0] == 10 * INITIAL_K_MULTIPLIER  # = 30
        if len(retrieve_calls) >= 2:
            assert retrieve_calls[1] == 60  # ×6
        # Hit MAX éventuellement
        stats = pipe.last_filter_stats
        assert stats["expansions"] >= 1
        # n_after_filter = 1 (la fiche id=4 ne s'auto-multiplie pas même si k augmente)
        assert stats["n_after_filter"] == 1
        # Hit max si toujours pas atteint target=3
        assert stats["hit_max"] is True

    def test_max_k_multiplier_cap(self, fake_fiches):
        """Le cap MAX_K_MULTIPLIER doit empêcher k de grossir indéfiniment."""
        pipe = OrientIAPipeline(
            client=MagicMock(), fiches=fake_fiches, use_metadata_filter=True
        )
        pipe.index = MagicMock()

        # Criteria impossible : 0 fiche matche → expand jusqu'à MAX
        criteria = FilterCriteria(region="zzz_imaginary_region", alternance=True)
        # Note : avec asymétrie defensive region (fiche sans info passe), cette
        # criteria filtre uniquement les fiches région != zzz ET non-national.
        # Pour forcer 0 match, on combine avec alternance=True qui est strict.

        retrieve_ks = []

        def mock_retrieve(client, index, fiches, question, k):
            retrieve_ks.append(k)
            return _wrap_retrieved(fiches)

        with patch("src.rag.pipeline.retrieve_top_k", side_effect=mock_retrieve):
            with patch("src.rag.pipeline.rerank", side_effect=lambda r, *a, **k: r):
                with patch("src.rag.pipeline.generate", return_value="answer"):
                    pipe.answer("q", k=10, top_k_sources=20, criteria=criteria)

        # k ne doit jamais dépasser k * MAX_K_MULTIPLIER = 100
        assert all(k <= 10 * MAX_K_MULTIPLIER for k in retrieve_ks)
        # Et stats indique hit_max
        assert pipe.last_filter_stats["k_final"] == 10 * MAX_K_MULTIPLIER


# ─────────────────── (d) interaction MMR / reranker ───────────────────


class TestMmrInteraction:
    def test_filter_before_mmr(self, fake_fiches):
        """Le filter s'applique AVANT MMR : MMR sélectionne la diversité
        parmi les fiches déjà filtrées."""
        pipe = OrientIAPipeline(
            client=MagicMock(),
            fiches=fake_fiches,
            use_metadata_filter=True,
            use_mmr=True,
        )
        pipe.index = MagicMock()

        mmr_called_with = []

        def mock_mmr(reranked, k, lambda_):
            mmr_called_with.append([item["fiche"]["id"] for item in reranked])
            return reranked[:k]

        with patch("src.rag.pipeline.retrieve_top_k", return_value=_wrap_retrieved(fake_fiches)):
            with patch("src.rag.pipeline.rerank", side_effect=lambda r, *a, **k: r):
                with patch("src.rag.pipeline.mmr_select", side_effect=mock_mmr):
                    with patch("src.rag.pipeline.generate", return_value="answer"):
                        pipe.answer(
                            "q",
                            k=10,
                            top_k_sources=3,
                            criteria=FilterCriteria(secteur=["informatique"]),
                        )

        # MMR a été appelé avec UNIQUEMENT les fiches secteur=informatique
        # (id 1, 2, 4, 5, 6 — pas id 3 secteur=droit)
        assert len(mmr_called_with) == 1
        ids_passed_to_mmr = mmr_called_with[0]
        assert 3 not in ids_passed_to_mmr  # fiche droit exclue par filter
        assert all(i in {1, 2, 4, 5, 6} for i in ids_passed_to_mmr)


# ─────────────────── (e) injection AnalystAgent profile ───────────────────


class TestAnalystProfileIntegration:
    """Test du flow complet : profile_delta AnalystAgent → criteria → filter."""

    def test_extract_filter_then_apply(self, pipeline_with_index, fake_fiches):
        """Pattern user : on utilise extract_filter_from_profile puis
        on passe criteria à pipeline.answer()."""
        from src.rag.metadata_filter import extract_filter_from_profile

        profile_delta = {
            "region": "Occitanie",
            "niveau_scolaire": "l1_droit",
            "contraintes": ["alternance:true"],
            "interets_detectes": ["informatique"],
        }
        criteria = extract_filter_from_profile(profile_delta)

        with patch("src.rag.pipeline.retrieve_top_k", return_value=_wrap_retrieved(fake_fiches)):
            with patch("src.rag.pipeline.rerank", side_effect=lambda r, *a, **k: r):
                with patch("src.rag.pipeline.generate", return_value="answer"):
                    answer, top = pipeline_with_index.answer("q", criteria=criteria, top_k_sources=10)

        # Le filter doit avoir filtré sur region=occitanie + alternance=True + secteur=informatique
        # + niveau Bac+2-Bac+5 (niveau_min=2, niveau_max=5 dérivé de l1_droit)
        # → fiches matching : id=1 (3, alt=True, info, occ), id=6 (2, alt=True, info, occ)
        ids = [item["fiche"]["id"] for item in top]
        assert 1 in ids
        assert 6 in ids
        # id=3 exclue (secteur=droit, non listé), id=2 exclue (region=ile-de-france)
        assert 3 not in ids
        assert 2 not in ids


# ─────────────────── (f) stats observabilité ───────────────────


class TestFilterStats:
    def test_stats_populated_on_each_answer(self, pipeline_with_index, fake_fiches):
        with patch("src.rag.pipeline.retrieve_top_k", return_value=_wrap_retrieved(fake_fiches)):
            with patch("src.rag.pipeline.rerank", side_effect=lambda r, *a, **k: r):
                with patch("src.rag.pipeline.generate", return_value="answer"):
                    pipeline_with_index.answer(
                        "q1",
                        k=15,
                        criteria=FilterCriteria(region="occitanie"),
                    )

        stats = pipeline_with_index.last_filter_stats
        assert stats is not None
        assert "filter_active" in stats
        assert "k_initial" in stats
        assert "k_final" in stats
        assert "n_retrieved" in stats
        assert "n_after_filter" in stats
        assert "expansions" in stats
        assert stats["k_initial"] == 15
