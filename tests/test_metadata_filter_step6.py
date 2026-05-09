"""Tests step 6 — extensions FilterCriteria pour router :
- nouveau champ `domain` (verrouillage par domaine, sémantique stricte)
- _match_region insensible aux accents (fix audit Matteo écart 2)
- Composite avec les 6 critères

Ne touche pas tests/test_metadata_filter.py (qui couvre v1).
"""
from __future__ import annotations

from src.rag.metadata_filter import (
    FilterCriteria,
    _match_domain,
    _match_region,
    _norm_region,
    apply_metadata_filter,
)


# ────────────────────────── _norm_region ──────────────────────────


def test_norm_region_strips_accents() -> None:
    assert _norm_region("Provence-Alpes-Côte d'Azur") == "provence-alpes-cote d'azur"
    assert _norm_region("Auvergne-Rhône-Alpes") == "auvergne-rhone-alpes"
    assert _norm_region("Bretagne") == "bretagne"


def test_norm_region_handles_none() -> None:
    assert _norm_region(None) == ""


def test_norm_region_handles_non_string() -> None:
    assert _norm_region(42) == "42"


# ────────────────────────── _match_region accent-insensitive ──────────────────────────


def test_match_region_accent_insensitive_match() -> None:
    """Fiche avec accents matche criteria sans accents (cas LLM-routed)."""
    assert _match_region("Auvergne-Rhône-Alpes", "auvergne-rhone-alpes") is True


def test_match_region_accent_insensitive_inverse() -> None:
    """L'inverse aussi : criteria avec accents matche fiche normalisée."""
    assert _match_region("auvergne-rhone-alpes", "Auvergne-Rhône-Alpes") is True


def test_match_region_no_match_different_region() -> None:
    assert _match_region("Bretagne", "occitanie") is False


def test_match_region_national_passes() -> None:
    """fiche.region='national' → toujours match (formations nationales)."""
    assert _match_region("national", "bretagne") is True


def test_match_region_none_fiche_passes() -> None:
    """fiche sans région → defensive pass-through."""
    assert _match_region(None, "bretagne") is True


def test_match_region_no_criteria_passes() -> None:
    assert _match_region("any", None) is True


# ────────────────────────── _match_domain (nouveau, step 6) ──────────────────────────


def test_match_domain_no_criteria_passes() -> None:
    assert _match_domain("crous", None) is True
    assert _match_domain(None, None) is True


def test_match_domain_match_in_list() -> None:
    assert _match_domain("crous", ["crous"]) is True
    assert _match_domain("metier", ["metier", "metier_detail"]) is True


def test_match_domain_no_match() -> None:
    """Domain strict : si la fiche n'est pas dans la liste, exclu."""
    assert _match_domain("formation_insertion", ["crous"]) is False


def test_match_domain_excludes_no_domain_fiches_by_default() -> None:
    """Sémantique stricte : fiche sans domain (= formation pure) EXCLUE
    si on demande explicitement un domain (ex CROUS).
    Différent de _match_region asymmetric defensive."""
    assert _match_domain(None, ["crous"]) is False


def test_match_domain_accepts_no_domain_when_formations_in_list() -> None:
    """Cas spécial : 'formations' dans c_domains accepte les fiches sans
    domain (cohérent avec build_quad_subindexes mapping no-domain →
    formations group)."""
    assert _match_domain(None, ["formations"]) is True
    assert _match_domain(None, ["formations", "metier"]) is True


def test_match_domain_case_insensitive() -> None:
    assert _match_domain("CROUS", ["crous"]) is True
    assert _match_domain("crous", ["CROUS"]) is True


def test_match_domain_non_string_fiche_excluded() -> None:
    """Si fiche.domain est un int ou un objet bizarre → exclu (pas crash)."""
    assert _match_domain(42, ["crous"]) is False


# ────────────────────────── FilterCriteria.domain integration ──────────────────────────


def test_filter_criteria_domain_default_none() -> None:
    c = FilterCriteria()
    assert c.domain is None
    assert c.is_empty() is True


def test_filter_criteria_with_domain_not_empty() -> None:
    c = FilterCriteria(domain=["crous"])
    assert c.is_empty() is False


def test_apply_metadata_filter_domain_lock_only() -> None:
    """Filtrage par domain seul : exclut les fiches d'autres domaines."""
    items = [
        {"fiche": {"domain": "crous", "nom": "Logement Lyon"}, "score": 0.9},
        {"fiche": {"domain": "metier", "nom": "Actuaire"}, "score": 0.85},
        {"fiche": {"nom": "Master Truc"}, "score": 0.8},  # no domain
        {"fiche": {"domain": "crous", "nom": "Resto U Paris"}, "score": 0.75},
    ]
    criteria = FilterCriteria(domain=["crous"])
    filtered = apply_metadata_filter(items, criteria)
    assert len(filtered) == 2
    assert all(it["fiche"]["domain"] == "crous" for it in filtered)


def test_apply_metadata_filter_domain_lock_with_formations_pseudo() -> None:
    """Si 'formations' dans domain_lock → accepte les fiches sans domain."""
    items = [
        {"fiche": {"domain": "crous"}, "score": 0.9},
        {"fiche": {"nom": "Master Truc"}, "score": 0.85},  # no domain
        {"fiche": {"domain": "metier"}, "score": 0.8},
    ]
    criteria = FilterCriteria(domain=["formations"])
    filtered = apply_metadata_filter(items, criteria)
    assert len(filtered) == 1
    assert filtered[0]["fiche"]["nom"] == "Master Truc"


def test_apply_metadata_filter_composite_region_plus_domain() -> None:
    """Composite : region=Bretagne ET domain=['crous'] → AND strict."""
    items = [
        {"fiche": {"domain": "crous", "region": "Bretagne"}, "score": 0.9},
        {"fiche": {"domain": "crous", "region": "Occitanie"}, "score": 0.85},
        {"fiche": {"domain": "metier", "region": "Bretagne"}, "score": 0.8},
        {"fiche": {"domain": "crous"}, "score": 0.75},  # no region — defensive pass
    ]
    criteria = FilterCriteria(region="bretagne", domain=["crous"])
    filtered = apply_metadata_filter(items, criteria)
    # Match : crous Bretagne + crous (no region defensive)
    # Exclu : crous Occitanie (region mismatch), metier Bretagne (domain mismatch)
    assert len(filtered) == 2
    assert all(it["fiche"]["domain"] == "crous" for it in filtered)


def test_apply_metadata_filter_region_with_accents_in_fiche() -> None:
    """Fix audit écart 2 : criteria 'auvergne-rhone-alpes' (sans accent)
    matche fiche.region 'Auvergne-Rhône-Alpes' (avec accent)."""
    items = [
        {"fiche": {"region": "Auvergne-Rhône-Alpes", "nom": "BUT Lyon"}, "score": 0.9},
        {"fiche": {"region": "Bretagne", "nom": "BUT Brest"}, "score": 0.85},
    ]
    criteria = FilterCriteria(region="auvergne-rhone-alpes")
    filtered = apply_metadata_filter(items, criteria)
    assert len(filtered) == 1
    assert filtered[0]["fiche"]["nom"] == "BUT Lyon"
