"""Tests unitaires pour scripts/build_quad_subindexes.py — étape 4.

Couvre :
- _classify_fiche : mapping fiche → group avec edge cases
- partition_indices : exhaustivité + exclus + domaines inconnus
- Validation que le manifest produit est lisible (test integration léger
  qui dépend de la présence des sub-indexes sur disque, skipped sinon).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add scripts/ to path pour importer build_quad_subindexes
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_quad_subindexes import (  # type: ignore  # noqa: E402
    DOMAIN_TO_GROUP,
    GROUP_NAMES,
    MANIFEST_NAME,
    _classify_fiche,
    load_manifest,
    partition_indices,
)


# ────────────────────────── _classify_fiche ──────────────────────────


def test_classify_fiche_no_domain_to_formations() -> None:
    """Fiche sans `domain` → formations."""
    fiche = {"nom": "Master Truc", "etablissement": "Univ X"}
    assert _classify_fiche(fiche) == "formations"


def test_classify_fiche_empty_domain_to_formations() -> None:
    """Fiche avec `domain=""` → formations."""
    fiche = {"nom": "Master Truc", "domain": ""}
    assert _classify_fiche(fiche) == "formations"


def test_classify_fiche_metier() -> None:
    fiche = {"domain": "metier", "nom": "actuaire"}
    assert _classify_fiche(fiche) == "metiers"


def test_classify_fiche_metier_detail() -> None:
    fiche = {"domain": "metier_detail"}
    assert _classify_fiche(fiche) == "metiers"


def test_classify_fiche_metier_prospective() -> None:
    fiche = {"domain": "metier_prospective"}
    assert _classify_fiche(fiche) == "metiers"


def test_classify_fiche_insee_salaire() -> None:
    fiche = {"domain": "insee_salaire"}
    assert _classify_fiche(fiche) == "statistiques"


def test_classify_fiche_insertion_pro() -> None:
    fiche = {"domain": "insertion_pro"}
    assert _classify_fiche(fiche) == "statistiques"


def test_classify_fiche_apec_region() -> None:
    fiche = {"domain": "apec_region"}
    assert _classify_fiche(fiche) == "statistiques"


def test_classify_fiche_parcours_bacheliers() -> None:
    fiche = {"domain": "parcours_bacheliers"}
    assert _classify_fiche(fiche) == "statistiques"


def test_classify_fiche_crous() -> None:
    fiche = {"domain": "crous"}
    assert _classify_fiche(fiche) == "aides_territoires"


def test_classify_fiche_competences_certif() -> None:
    fiche = {"domain": "competences_certif"}
    assert _classify_fiche(fiche) == "aides_territoires"


def test_classify_fiche_territoire_drom() -> None:
    fiche = {"domain": "territoire_drom"}
    assert _classify_fiche(fiche) == "aides_territoires"


def test_classify_fiche_calendrier() -> None:
    fiche = {"domain": "calendrier"}
    assert _classify_fiche(fiche) == "aides_territoires"


def test_classify_fiche_correction_factuelle() -> None:
    fiche = {"domain": "correction_factuelle"}
    assert _classify_fiche(fiche) == "aides_territoires"


def test_classify_fiche_voie_pre_bac() -> None:
    fiche = {"domain": "voie_pre_bac"}
    assert _classify_fiche(fiche) == "formations"


def test_classify_fiche_formation_insertion() -> None:
    fiche = {"domain": "formation_insertion"}
    assert _classify_fiche(fiche) == "formations"


def test_classify_fiche_excluded_when_retrieval_eligible_false() -> None:
    """Vague 1.C : retrieval_eligible=False → exclusion (None)."""
    fiche = {"domain": "metier", "retrieval_eligible": False}
    assert _classify_fiche(fiche) is None


def test_classify_fiche_kept_when_retrieval_eligible_true() -> None:
    fiche = {"domain": "metier", "retrieval_eligible": True}
    assert _classify_fiche(fiche) == "metiers"


def test_classify_fiche_kept_when_retrieval_eligible_absent() -> None:
    """Backward compat : pas de flag → considéré éligible."""
    fiche = {"domain": "metier"}
    assert _classify_fiche(fiche) == "metiers"


def test_classify_fiche_unknown_domain_falls_back_to_formations() -> None:
    """Domain non listé dans DOMAIN_TO_GROUP → fallback formations."""
    fiche = {"domain": "hallucinated_domain"}
    assert _classify_fiche(fiche) == "formations"


def test_classify_fiche_non_dict_returns_none() -> None:
    """Si fiche n'est pas un dict (corruption) → None (skip safe)."""
    assert _classify_fiche(None) is None  # type: ignore[arg-type]
    assert _classify_fiche("malformed") is None  # type: ignore[arg-type]
    assert _classify_fiche(42) is None  # type: ignore[arg-type]


# ────────────────────────── partition_indices ──────────────────────────


def test_partition_indices_exhaustive() -> None:
    """Toute fiche est soit dans un group, soit dans excluded — total = len."""
    fiches = [
        {"nom": "A"},  # → formations
        {"domain": "metier"},  # → metiers
        {"domain": "insee_salaire"},  # → statistiques
        {"domain": "crous"},  # → aides_territoires
        {"domain": "metier", "retrieval_eligible": False},  # → exclus
    ]
    groups, excluded, _unknown = partition_indices(fiches)
    total = sum(len(idxs) for idxs in groups.values()) + len(excluded)
    assert total == len(fiches)
    assert groups["formations"] == [0]
    assert groups["metiers"] == [1]
    assert groups["statistiques"] == [2]
    assert groups["aides_territoires"] == [3]
    assert excluded == [4]


def test_partition_indices_unknown_domains_tracked() -> None:
    fiches = [
        {"domain": "weird1"},
        {"domain": "weird1"},
        {"domain": "weird2"},
        {"domain": "metier"},
    ]
    _groups, _excl, unknown = partition_indices(fiches)
    assert unknown == {"weird1": 2, "weird2": 1}


def test_partition_indices_all_4_groups_present() -> None:
    """Le dict de retour contient toujours les 4 groupes (même si vides)."""
    fiches: list[dict] = []
    groups, _excl, _unknown = partition_indices(fiches)
    assert set(groups.keys()) == set(GROUP_NAMES)


# ────────────────────────── DOMAIN_TO_GROUP integrity ──────────────────────────


def test_all_groups_in_mapping_are_known() -> None:
    """Tous les groupes du mapping sont dans GROUP_NAMES."""
    for group in DOMAIN_TO_GROUP.values():
        assert group in GROUP_NAMES, f"Unknown group {group!r} in mapping"


def test_no_duplicate_domains_in_mapping() -> None:
    """Aucun domain dupliqué (clé unique = mapping cohérent)."""
    keys = list(DOMAIN_TO_GROUP.keys())
    assert len(keys) == len(set(keys))


# ────────────────────────── Manifest integration ──────────────────────────


def _has_built_subindexes() -> bool:
    """True si les 4 sub-indexes + manifest existent sur disque."""
    out_dir = ROOT / "data" / "embeddings"
    if not (out_dir / MANIFEST_NAME).exists():
        return False
    return all(
        (out_dir / f"formations_v7_{name}.index").exists()
        for name in GROUP_NAMES
    )


@pytest.mark.skipif(
    not _has_built_subindexes(),
    reason="Sub-indexes pas encore buildés — run scripts/build_quad_subindexes.py first",
)
def test_manifest_loads_and_total_consistent() -> None:
    """Le manifest doit être lisible et la somme groups + excluded =
    total_fiches_in_source."""
    manifest = load_manifest(ROOT / "data" / "embeddings")
    total_groups = sum(g["fiches_count"] for g in manifest["groups"].values())
    assert total_groups + manifest["excluded_count"] == manifest["total_fiches_in_source"]


@pytest.mark.skipif(
    not _has_built_subindexes(),
    reason="Sub-indexes pas encore buildés",
)
def test_manifest_paths_exist_on_disk() -> None:
    """Tous les chemins listés dans le manifest existent réellement."""
    manifest = load_manifest(ROOT / "data" / "embeddings")
    for name, info in manifest["groups"].items():
        path = ROOT / info["path"]
        assert path.exists(), f"Manifest référence {path} qui n'existe pas"


@pytest.mark.skipif(
    not _has_built_subindexes(),
    reason="Sub-indexes pas encore buildés",
)
def test_manifest_groups_match_GROUP_NAMES() -> None:
    """Le manifest doit lister exactement les 4 groupes attendus."""
    manifest = load_manifest(ROOT / "data" / "embeddings")
    assert set(manifest["groups"].keys()) == set(GROUP_NAMES)
