"""Tests pour `scripts/sprint7_queries.py` — bench enrichi 36q balanced.

Vérifie :
- 14 nouvelles queries (DROM + financement + voie pré-bac + multi-axes)
- Balance par axe (chaque axe Sprint 6 a au moins 2-3 queries dédiées)
- Pas de leakage évident (queries en langage user-naturel)
- Combine baseline 22q + nouvelles → 36 queries totales
"""
from __future__ import annotations

from scripts.sprint7_queries import (
    DROM_QUERIES,
    FINANCEMENT_QUERIES,
    VOIE_PRE_BAC_QUERIES,
    MULTI_AXES_QUERIES,
    build_sprint7_queries,
    select_baseline_subset_22q,
    get_query_count_per_axis_target,
)


class TestQueriesCounts:
    """Vérifie le décompte exact des queries Sprint 7."""

    def test_drom_queries_count(self):
        assert len(DROM_QUERIES) == 4

    def test_financement_queries_count(self):
        assert len(FINANCEMENT_QUERIES) == 4

    def test_voie_pre_bac_queries_count(self):
        assert len(VOIE_PRE_BAC_QUERIES) == 3

    def test_multi_axes_queries_count(self):
        assert len(MULTI_AXES_QUERIES) == 3

    def test_total_new_queries(self):
        total = (
            len(DROM_QUERIES) + len(FINANCEMENT_QUERIES)
            + len(VOIE_PRE_BAC_QUERIES) + len(MULTI_AXES_QUERIES)
        )
        assert total == 14, f"Expected 14 new Sprint 7 queries, got {total}"


class TestQueriesUniqueIds:
    """Pas de duplicate ID dans les queries Sprint 7."""

    def test_unique_ids_across_all_sprint7(self):
        all_qs = DROM_QUERIES + FINANCEMENT_QUERIES + VOIE_PRE_BAC_QUERIES + MULTI_AXES_QUERIES
        ids = [q["id"] for q in all_qs]
        assert len(ids) == len(set(ids)), f"Duplicate IDs in Sprint 7 queries"


class TestQueriesSchema:
    """Chaque query a les champs minimaux requis."""

    def _check_query_schema(self, queries):
        for q in queries:
            assert "id" in q
            assert "suite" in q
            assert "axe_target" in q
            assert "text" in q
            assert q["text"], f"Empty text in query {q['id']}"
            assert len(q["text"]) >= 30, f"Query {q['id']} text too short"

    def test_drom_schema(self):
        self._check_query_schema(DROM_QUERIES)

    def test_financement_schema(self):
        self._check_query_schema(FINANCEMENT_QUERIES)

    def test_voie_pre_bac_schema(self):
        self._check_query_schema(VOIE_PRE_BAC_QUERIES)

    def test_multi_axes_schema(self):
        self._check_query_schema(MULTI_AXES_QUERIES)


class TestBalancePerAxis:
    """Sprint 7 cible : chaque axe Sprint 6 a un minimum de queries
    dédiées pour permettre une mesure significative."""

    def test_each_axis_has_minimum_queries(self):
        counts = get_query_count_per_axis_target()
        # Axes Sprint 6 ciblés explicitement par les nouvelles queries
        # (axe 1 DARES re-agg : couvert via baseline DARES_QUERIES + 1 multi-axe)
        assert counts.get("axe2_drom_territorial", 0) >= 4, "Axe 2 DROM mal couvert"
        assert counts.get("axe4_financement", 0) >= 4, "Axe 4 financement mal couvert"
        assert counts.get("axe3a_voie_pre_bac", 0) >= 3, "Axe 3a voie pré-bac mal couvert"
        assert counts.get("axe3b_inserjeunes", 0) >= 3, "Axe 3b inserjeunes mal couvert"

    def test_at_least_one_axe1_dares_query_in_multi_axes(self):
        """Axe 1 DARES re-agg devrait apparaître dans au moins 1 multi-axe."""
        counts = get_query_count_per_axis_target()
        assert counts.get("axe1_dares_re_agg", 0) >= 1


class TestBuildSprint7Queries:
    """Vérifie l'intégration avec la baseline."""

    def _make_baseline_22q(self):
        """Mock des 22 queries baseline Sprint 5/6."""
        baseline = []
        for i in range(6):
            baseline.append({"id": f"persona_q{i+1}", "suite": "personas_v4", "text": f"persona {i+1}"})
        for i in range(6):
            baseline.append({"id": f"dares_q{i+1:02d}", "suite": "dares_dedie", "text": f"dares {i+1}"})
        for i in range(6):
            baseline.append({"id": f"blocs_q{i+1:02d}", "suite": "blocs_dedie", "text": f"blocs {i+1}"})
        for i in range(4):
            baseline.append({"id": f"user_naturel_q{i+11}", "suite": "user_naturel", "text": f"user {i+1}"})
        return baseline

    def test_build_returns_36_queries(self):
        baseline = self._make_baseline_22q()
        out = build_sprint7_queries(baseline)
        assert len(out) == 36

    def test_build_preserves_baseline_queries(self):
        """Non-régression : les 22 baseline queries ne sont pas modifiées."""
        baseline = self._make_baseline_22q()
        out = build_sprint7_queries(baseline)
        # Les 22 premières doivent être les baseline
        assert out[:22] == baseline

    def test_build_appends_new_queries_after_baseline(self):
        baseline = self._make_baseline_22q()
        out = build_sprint7_queries(baseline)
        new_part = out[22:]
        assert len(new_part) == 14
        # Suites Sprint 7 présentes
        suites = {q["suite"] for q in new_part}
        assert "drom_dedie" in suites
        assert "financement_dedie" in suites
        assert "voie_pre_bac_dedie" in suites
        assert "multi_axes" in suites


class TestSelectBaselineSubset22q:
    """Vérifie la sélection baseline figée."""

    def test_returns_22_queries(self):
        # Mock unified queries
        all_qs = []
        for i in range(18):
            all_qs.append({
                "id": f"persona_{i}_q{(i % 3) + 1}",  # q1, q2, q3 alternés
                "suite": "personas_v4",
                "text": f"persona {i}",
            })
        for i in range(10):
            all_qs.append({"id": f"dares_q{i+1:02d}", "suite": "dares_dedie", "text": f"dares {i+1}"})
        for i in range(10):
            all_qs.append({"id": f"blocs_q{i+1:02d}", "suite": "blocs_dedie", "text": f"blocs {i+1}"})
        for i in range(10):
            all_qs.append({"id": f"user_naturel_q{i+11}", "suite": "user_naturel", "text": f"user {i+1}"})

        subset = select_baseline_subset_22q(all_qs)
        assert len(subset) == 22

    def test_personas_filter_q1_only(self):
        """Personas : seulement les queries qui finissent par _q1."""
        all_qs = [
            {"id": "p1_q1", "suite": "personas_v4", "text": "..."},
            {"id": "p1_q2", "suite": "personas_v4", "text": "..."},
            {"id": "p2_q1", "suite": "personas_v4", "text": "..."},
        ]
        subset = select_baseline_subset_22q(all_qs)
        ids = [q["id"] for q in subset]
        assert "p1_q1" in ids
        assert "p2_q1" in ids
        assert "p1_q2" not in ids


class TestNoLeakageHeuristic:
    """Heuristique anti-leakage : queries en langage user-naturel,
    pas de mention des champs JSON / acronymes techniques OrientIA."""

    LEAKAGE_TERMS_FORBIDDEN = [
        "granularity",
        "fap_region",
        "taux_emploi_12m",
        "domain_hint",
        "domain_boost",
        "phaseE",
        "verified_by_official_source",
        "anti-hallu",
        "RerankConfig",
    ]

    def _check_no_leakage(self, queries):
        for q in queries:
            text_lower = q["text"].lower()
            for term in self.LEAKAGE_TERMS_FORBIDDEN:
                assert term.lower() not in text_lower, (
                    f"Leakage term '{term}' dans query {q['id']}"
                )

    def test_drom_no_leakage(self):
        self._check_no_leakage(DROM_QUERIES)

    def test_financement_no_leakage(self):
        self._check_no_leakage(FINANCEMENT_QUERIES)

    def test_voie_pre_bac_no_leakage(self):
        self._check_no_leakage(VOIE_PRE_BAC_QUERIES)

    def test_multi_axes_no_leakage(self):
        self._check_no_leakage(MULTI_AXES_QUERIES)


class TestQueryStyleHumanLike:
    """Vérifie que les queries sont formulées de façon user-naturelle :
    longueur raisonnable + tournure question / situation perso."""

    def _check_human_like(self, queries):
        for q in queries:
            text = q["text"]
            # Longueur raisonnable (pas trop courte pour cas d'usage réaliste)
            assert 30 <= len(text) <= 300, f"Query {q['id']} length {len(text)} hors plage"
            # Pas en majuscules toutes
            assert not text.isupper()

    def test_drom_human_like(self):
        self._check_human_like(DROM_QUERIES)

    def test_financement_human_like(self):
        self._check_human_like(FINANCEMENT_QUERIES)

    def test_voie_pre_bac_human_like(self):
        self._check_human_like(VOIE_PRE_BAC_QUERIES)

    def test_multi_axes_human_like(self):
        self._check_human_like(MULTI_AXES_QUERIES)
