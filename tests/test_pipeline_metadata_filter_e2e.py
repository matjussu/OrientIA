"""Tests E2E intégration metadata_filter sur données réelles — Sprint 10 chantier C activation.

DoD durable post-update `feedback_audit_claudette_rigueur` : tests
intégration AVEC fiches réelles ayant frontmatter standardisé (pas de
mocks data — chantier B `formations_unified.json` requis amont).

Couvre :
- Filter sur criteria region=occitanie : compte attendu cohérent dataset
- Filter composite region+secteur+alternance : count cohérent
- Filter strict (asymétrie) : alternance=True exclut les fiches sans info
- Filter pass-through (asymétrie) : region par défaut inclut national/null

Skip si `formations_unified.json` absent (sera regenerated via
`scripts/normalize_frontmatter.py` post-merge chantier B).
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from src.rag.metadata_filter import (
    FilterCriteria,
    apply_metadata_filter,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
UNIFIED_PATH = REPO_ROOT / "data" / "processed" / "formations_unified.json"


def _wrap(fiches: list[dict]) -> list[dict]:
    """Wrap les fiches normalisées dans le format retrieve_top_k.

    Aligne les noms canonical sur les noms attendus par metadata_filter
    (region/niveau/alternance/budget/secteur)."""
    out = []
    for i, f in enumerate(fiches):
        # Mapping canonical → metadata_filter
        normalized = {
            **f,
            "region": f.get("region_canonical"),
            "niveau": f.get("niveau_int"),
            "alternance": f.get("alternance_inferred"),
            "budget": _budget_to_int(f.get("budget_category")),
            "secteur": f.get("secteur_canonical"),
        }
        out.append({"fiche": normalized, "score": 1.0 - i * 1e-6})
    return out


def _budget_to_int(cat: str | None) -> int | None:
    """Convert budget_category (low/high) → budget int €/an."""
    if cat == "low":
        return 1500
    if cat == "high":
        return 8000
    return None


@pytest.fixture(scope="module")
def real_unified():
    """Charge formations_unified.json complet (55k entries)."""
    if not UNIFIED_PATH.exists():
        pytest.skip(
            f"formations_unified.json absent — run "
            f"`PYTHONPATH=. python3 scripts/normalize_frontmatter.py` first"
        )
    with UNIFIED_PATH.open() as f:
        return json.load(f)


# ──────────────────── Coverage stats sanity (E2E) ────────────────────


class TestE2ECoverageStats:
    """Vérifie que la couverture frontmatter du dataset réel correspond
    aux thresholds attendus pour que le filter soit utile."""

    def test_secteur_coverage_above_80pct(self, real_unified):
        """Chantier B doit produire ≥80% secteur coverage pour que le
        filter sur secteur soit significatif."""
        with_secteur = sum(1 for r in real_unified if r.get("secteur_canonical"))
        pct = 100 * with_secteur / len(real_unified)
        assert pct >= 80.0, f"Secteur coverage : {pct:.1f}% < 80%"

    def test_alternance_coverage_above_30pct(self, real_unified):
        with_alt = sum(1 for r in real_unified if r.get("alternance_inferred") is not None)
        pct = 100 * with_alt / len(real_unified)
        assert pct >= 30.0, f"Alternance coverage : {pct:.1f}% < 30%"

    def test_region_diversity(self, real_unified):
        """Au moins 10 régions différentes représentées."""
        regions = Counter(r.get("region_canonical") for r in real_unified
                          if r.get("region_canonical"))
        assert len(regions) >= 10, f"Diversité régionale insuffisante : {len(regions)}"


# ──────────────────── Filter sur dataset réel (E2E) ────────────────────


class TestE2EFilterOccitanie:
    """Filter region=occitanie : valider count plausible + qualité fiches."""

    def test_filter_region_occitanie_returns_significant_count(self, real_unified):
        wrapped = _wrap(real_unified)
        criteria = FilterCriteria(region="occitanie")
        filtered = apply_metadata_filter(wrapped, criteria)
        # Le dataset réel a des milliers de fiches en Occitanie
        assert len(filtered) >= 100, (
            f"Trop peu de fiches en Occitanie : {len(filtered)}"
        )
        # Mais pas tout le dataset (asymétrie defensive sur region absente
        # passe-through, donc on peut avoir + que les 1500-2000 vraies fiches
        # Occitanie — c'est OK)

    def test_filter_region_occitanie_excludes_other_regions(self, real_unified):
        """Aucune fiche `region_canonical` non-occitanie/non-null/non-national
        ne doit passer le filter."""
        wrapped = _wrap(real_unified)
        criteria = FilterCriteria(region="occitanie")
        filtered = apply_metadata_filter(wrapped, criteria)
        for item in filtered[:1000]:  # spot check
            f_region = item["fiche"].get("region")
            if f_region is not None and f_region != "national":
                assert f_region.lower() == "occitanie", (
                    f"Fiche région {f_region} ne devrait pas passer le filter Occitanie"
                )


class TestE2EFilterStrictAlternance:
    """Filter alternance=True : asymétrie stricte exclut les fiches sans info.

    Sur dataset réel post-chantier B :
    - 36.5% ont `alternance_inferred` non-null (True ou False)
    - Filter alternance=True ne doit retourner QUE les ~7000 fiches True"""

    def test_filter_alternance_true_strict_excludes_unknown(self, real_unified):
        wrapped = _wrap(real_unified)
        criteria = FilterCriteria(alternance=True)
        filtered = apply_metadata_filter(wrapped, criteria)
        # Aucune fiche `alternance=None` ne passe (asymétrie stricte)
        # Aucune fiche `alternance=False` ne passe
        for item in filtered[:500]:
            assert item["fiche"].get("alternance") is True, (
                f"Asymétrie stricte violée : alternance={item['fiche'].get('alternance')}"
            )

    def test_filter_alternance_count_plausible(self, real_unified):
        """Count attendu : approximativement nb de fiches True dans le dataset.
        Peut être un peu plus si certaines fiches ont alternance=None et que
        ça change asymétrie (mais ce test assert is True donc strict OK)."""
        wrapped = _wrap(real_unified)
        criteria = FilterCriteria(alternance=True)
        filtered = apply_metadata_filter(wrapped, criteria)
        # Au moins 5000 fiches alternance=True sur 55k post-chantier B
        # (apprentissage 11k fiches majoritairement True + autres CFA)
        assert len(filtered) >= 5000, (
            f"Trop peu de fiches alternance=True : {len(filtered)}"
        )


class TestE2EFilterCompositeOccitanieAlternance:
    """Filter composite region=occitanie + alternance=True : intersection."""

    def test_composite_returns_subset_of_either(self, real_unified):
        wrapped = _wrap(real_unified)
        criteria_combo = FilterCriteria(region="occitanie", alternance=True)
        filtered_combo = apply_metadata_filter(wrapped, criteria_combo)

        criteria_alt = FilterCriteria(alternance=True)
        filtered_alt = apply_metadata_filter(wrapped, criteria_alt)

        # combo ⊆ alt (par AND)
        assert len(filtered_combo) <= len(filtered_alt)


class TestE2EFilterSecteur:
    """Filter secteur=informatique : remonte les data_ia + cyber + ingenierie..."""

    def test_secteur_informatique_returns_tech_fiches(self, real_unified):
        wrapped = _wrap(real_unified)
        criteria = FilterCriteria(secteur=["informatique"])
        filtered = apply_metadata_filter(wrapped, criteria)
        # Sur dataset post-chantier B, mapping data_ia/cyber → ['informatique', ...]
        # donc les fiches data_ia + cyber doivent passer
        assert len(filtered) >= 500
        # Spot check : les fiches passantes ont bien 'informatique' dans secteur
        for item in filtered[:200]:
            secteurs = item["fiche"].get("secteur") or []
            if isinstance(secteurs, str):
                secteurs = [secteurs]
            assert "informatique" in [s.lower() for s in secteurs]


# ──────────────────── Asymétrie defensive sur dataset réel ────────────────────


class TestE2EAsymetrieDefensive:
    """Le design asymétrie defensive : region/niveau/budget souples (passent
    fiches sans info), alternance/secteur stricts (excluent sans info).

    Validation sur dataset réel."""

    def test_region_pass_through_for_no_info_fiches(self, real_unified):
        """Fiches sans region (44.8% du dataset) doivent passer un filter
        region=occitanie via asymétrie defensive."""
        # Find a fiche without region
        no_region_fiches = [r for r in real_unified if not r.get("region_canonical")]
        if not no_region_fiches:
            pytest.skip("No fiche without region in dataset")

        # Wrap juste cette fiche + appliquer filter
        wrapped = _wrap(no_region_fiches[:10])
        criteria = FilterCriteria(region="occitanie")
        filtered = apply_metadata_filter(wrapped, criteria)
        # Toutes les 10 doivent passer (defensive : region absente = inclut)
        assert len(filtered) == 10

    def test_alternance_strict_excludes_unknown(self, real_unified):
        """Fiches sans alternance_inferred (63.5% du dataset) ne passent PAS
        un filter alternance=True (asymétrie stricte)."""
        no_alt_fiches = [r for r in real_unified if r.get("alternance_inferred") is None]
        if not no_alt_fiches:
            pytest.skip("No fiche without alternance in dataset")
        wrapped = _wrap(no_alt_fiches[:10])
        criteria = FilterCriteria(alternance=True)
        filtered = apply_metadata_filter(wrapped, criteria)
        # 0 doivent passer (strict : alternance absente = exclut)
        assert len(filtered) == 0
