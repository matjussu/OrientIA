"""Tests router_fallback — déterministe, zéro dépendance LLM.

Couvre les 6 cas du fallback :
1. Question vide → safe default (confidence 0.3)
2. Cross-domain manifeste → refusal_reason='cross_domain'
3. Superlatif → refusal_reason='superlative_no_data'
4. domain_hint matché → mapping sub_indexes + domain_lock
5. Intent géographique seul → sub_indexes=['formations'] + region
6. Fallback final → sub_indexes=tous, confidence 0.4
"""
from __future__ import annotations

import pytest

from src.rag.router_fallback import (
    DOMAIN_HINT_TO_DOMAIN_LOCK,
    DOMAIN_HINT_TO_SUB_INDEXES,
    _detect_cross_domain,
    _detect_region,
    _detect_superlative,
    deterministic_route,
)
from src.rag.router_llm import SUB_INDEX_NAMES


# ────────────────────────── Cas 1 — question vide ──────────────────────────


def test_empty_question_safe_default() -> None:
    rd = deterministic_route("")
    assert rd.sub_indexes == list(SUB_INDEX_NAMES)
    assert rd.refusal_reason is None
    assert rd.confidence == 0.3
    assert rd.is_fallback is True


def test_whitespace_only_question() -> None:
    rd = deterministic_route("   \t  \n  ")
    assert rd.sub_indexes == list(SUB_INDEX_NAMES)
    assert rd.confidence == 0.3
    assert rd.is_fallback is True


# ────────────────────────── Cas 2 — cross-domain ──────────────────────────


def test_cross_domain_medical() -> None:
    rd = deterministic_route("Comment soigner une angine de poitrine ?")
    assert rd.refusal_reason == "cross_domain"
    assert rd.confidence == 0.9
    assert rd.pre_written_response is not None


def test_cross_domain_recipe() -> None:
    rd = deterministic_route("Recette de cookies au chocolat")
    assert rd.refusal_reason == "cross_domain"


def test_cross_domain_celebrity() -> None:
    rd = deterministic_route("Qui est Macron ?")
    assert rd.refusal_reason == "cross_domain"


def test_cross_domain_does_NOT_catch_legit_orientation() -> None:
    """Le pattern cross-domain ne doit PAS attraper 'métier de cuisinier'."""
    rd = deterministic_route("Que fait un cuisinier au quotidien ?")
    # Pas refusal — c'est une question métier légitime
    assert rd.refusal_reason != "cross_domain"


# ────────────────────────── Cas 3 — superlatif ──────────────────────────


def test_superlative_meilleure() -> None:
    """Cas live #1 : 'meilleure école de commerce' doit être refusée."""
    rd = deterministic_route("Quelle est la meilleure école de commerce en France ?")
    assert rd.refusal_reason == "superlative_no_data"
    assert rd.confidence == 0.9
    assert "Onisep" in rd.pre_written_response


def test_superlative_top_n() -> None:
    rd = deterministic_route("Top 5 des écoles d'ingénieur ?")
    assert rd.refusal_reason == "superlative_no_data"


def test_superlative_classement() -> None:
    rd = deterministic_route("Quel est le classement des universités françaises ?")
    assert rd.refusal_reason == "superlative_no_data"


def test_superlative_palmares() -> None:
    rd = deterministic_route("Palmarès des prépas BCPST")
    assert rd.refusal_reason == "superlative_no_data"


def test_superlative_best() -> None:
    rd = deterministic_route("What is the best engineering school in France?")
    assert rd.refusal_reason == "superlative_no_data"


def test_meilleur_pluriel() -> None:
    rd = deterministic_route("Quels sont les meilleurs masters en data science ?")
    assert rd.refusal_reason == "superlative_no_data"


def test_no_superlative_in_legit_question() -> None:
    """'mieux que' ne doit pas matcher (c'est une comparaison, pas un superlatif)."""
    rd = deterministic_route("Vaut-il mieux faire un BUT ou un BTS ?")
    assert rd.refusal_reason != "superlative_no_data"


# ────────────────────────── Cas 4 — domain_hint matché ──────────────────────────


def test_crous_routes_to_aides_territoires() -> None:
    """Q live spot-check : logement CROUS Lyon."""
    rd = deterministic_route("Combien coûte le logement CROUS à Lyon ?")
    assert "aides_territoires" in rd.sub_indexes
    assert rd.domain_lock == ["crous"]
    assert rd.hardlock_domain_strict is True
    assert rd.criteria is not None
    assert rd.criteria.region == "auvergne-rhone-alpes"  # via _CITY_TO_REGION (sans accent)
    assert rd.hardlock_region_strict is True


def test_rncp_routes_to_aides_territoires() -> None:
    """Q live spot-check : RNCP 38450 blocs."""
    rd = deterministic_route("Quels sont les blocs de compétences du RNCP 38450 ?")
    assert "aides_territoires" in rd.sub_indexes
    assert rd.domain_lock == ["competences_certif"]
    assert rd.hardlock_domain_strict is True


def test_insee_salaire_routes_to_statistiques() -> None:
    """Q live spot-check : salaire PCS 37."""
    rd = deterministic_route("Quel est le salaire moyen d'un cadre supérieur PCS 37 ?")
    assert "statistiques" in rd.sub_indexes
    assert rd.domain_lock == ["insee_salaire"]


def test_metier_routes_to_metiers() -> None:
    """Q live spot-check : que fait un actuaire."""
    rd = deterministic_route("Que fait un actuaire au quotidien ?")
    assert "metiers" in rd.sub_indexes
    assert rd.domain_lock == ["metier", "metier_detail"]


def test_drom_routes_to_aides_territoires() -> None:
    """Q live spot-check : formations Guadeloupe."""
    rd = deterministic_route("Quelles formations en Guadeloupe ?")
    assert "aides_territoires" in rd.sub_indexes
    assert rd.domain_lock == ["territoire_drom"]
    assert rd.hardlock_domain_strict is True


def test_metier_prospective_routes_correctly() -> None:
    rd = deterministic_route("Quels métiers vont recruter en Occitanie en 2030 ?")
    assert "metiers" in rd.sub_indexes
    assert rd.domain_lock == ["metier_prospective"]


def test_apec_routes_to_statistiques() -> None:
    """Pattern APEC d'intent.py exige 'marche du travail|emploi' sans
    'de l'' interposé. On teste une formulation qui matche vraiment."""
    rd = deterministic_route("Recrutement des cadres en Bretagne ?")
    assert "statistiques" in rd.sub_indexes
    assert rd.domain_lock == ["apec_region"]


def test_apec_paraphrase_falls_back_gracefully() -> None:
    """Une paraphrase APEC qui rate le pattern strict d'intent.py tombe
    en cas géographique (pas de plantage). Le LLM rattrapera ce cas."""
    rd = deterministic_route("Marché de l'emploi cadres en Bretagne ?")
    # Pas de plantage, criteria.region populé
    assert rd.criteria is not None
    assert rd.criteria.region == "bretagne"


def test_calendrier_routes_to_aides_territoires() -> None:
    rd = deterministic_route("Quand est la deadline Parcoursup 2026 ?")
    assert "aides_territoires" in rd.sub_indexes
    assert rd.domain_lock == ["calendrier"]


# ────────────────────────── Cas 5 — géographique seul ──────────────────────────


def test_geographic_only_routes_to_formations_with_region() -> None:
    """Q live #2 : 'ingé cyber Bretagne' — pas de domain_hint, juste géo."""
    rd = deterministic_route("Quelles écoles d'ingénieur en cybersécurité en Bretagne ?")
    # Pas de domain_hint matché → tombe en cas 5 (géographique formations)
    assert rd.sub_indexes == ["formations"]
    assert rd.criteria is not None
    assert rd.criteria.region == "bretagne"
    assert rd.hardlock_region_strict is True
    assert rd.top_k_override == 12  # critique pour BTS Rennes / BUT Brest


def test_geographic_with_city() -> None:
    rd = deterministic_route("Formations informatique à Toulouse ?")
    assert rd.sub_indexes == ["formations"]
    assert rd.criteria is not None
    assert rd.criteria.region == "occitanie"


def test_alias_region_normalized() -> None:
    """Alias historique 'aquitaine' → 'nouvelle-aquitaine'."""
    rd = deterministic_route("Formations en Aquitaine ?")
    assert rd.criteria is not None
    assert "nouvelle-aquitaine" in rd.criteria.region


# ────────────────────────── Cas 6 — fallback final ──────────────────────────


def test_generic_question_falls_back_to_all_sub_indexes() -> None:
    """Question générique sans signal → tous sub_indexes, confidence basse."""
    rd = deterministic_route("Comment choisir son orientation ?")
    assert set(rd.sub_indexes) == set(SUB_INDEX_NAMES)
    assert rd.confidence <= 0.5
    assert rd.refusal_reason is None


def test_fallback_preserves_region_if_detected() -> None:
    """Si une région est détectée mais aucun domain_hint, criteria conservé."""
    # Question vague mais avec région
    rd = deterministic_route("Que faire après le bac dans le Centre ?")
    # Soit cas 5 (géographique formations) soit cas 6 (fallback avec region)
    assert rd.criteria is not None
    assert rd.criteria.region is not None


# ────────────────────────── Helpers internes ──────────────────────────


def test_detect_region_canonical() -> None:
    assert _detect_region("formations en bretagne") == "bretagne"
    assert _detect_region("ecoles en occitanie") == "occitanie"


def test_detect_region_via_city() -> None:
    assert _detect_region("logement a lyon") == "auvergne-rhone-alpes"
    assert _detect_region("ecoles a paris") == "ile-de-france"


def test_detect_region_drom() -> None:
    assert _detect_region("formations en guadeloupe") == "guadeloupe"


def test_detect_region_none() -> None:
    assert _detect_region("comment choisir son master") is None


def test_detect_superlative_meilleure() -> None:
    assert _detect_superlative("meilleure ecole de commerce")
    assert _detect_superlative("la meilleure formation")
    assert _detect_superlative("les meilleurs masters")


def test_detect_superlative_top_n() -> None:
    assert _detect_superlative("top 5 des prepas")
    assert _detect_superlative("top 10")


def test_detect_superlative_negative_cases() -> None:
    assert not _detect_superlative("vaut-il mieux but ou bts")
    assert not _detect_superlative("comment choisir entre 2 formations")


def test_detect_cross_domain_medical() -> None:
    assert _detect_cross_domain("comment soigner une angine")
    assert _detect_cross_domain("comment guerir un rhume")


def test_detect_cross_domain_negatives() -> None:
    assert not _detect_cross_domain("metier de cuisinier")
    assert not _detect_cross_domain("formation en medecine")


# ────────────────────────── Property : toujours non-bloquant ──────────────────────────


@pytest.mark.parametrize("question", [
    "",
    "?",
    "🎓",  # emoji uniquement
    "a" * 5000,  # question très longue
    "SELECT * FROM formations",  # injection SQL
    "<script>alert(1)</script>",  # XSS
    "Quel est le {{template}} de la {{variable}} ?",  # template injection
    "What's up?",  # anglais courant
])
def test_route_never_raises(question: str) -> None:
    """Property : deterministic_route ne doit JAMAIS lever d'exception."""
    rd = deterministic_route(question)
    assert rd is not None
    assert rd.is_fallback is True


# ────────────────────────── Mappings validity ──────────────────────────


def test_all_domain_hints_map_to_valid_sub_indexes() -> None:
    """Chaque domain_hint mappe vers ≥1 sub_index valide."""
    for hint, sub_idx_list in DOMAIN_HINT_TO_SUB_INDEXES.items():
        assert sub_idx_list, f"{hint} maps to empty list"
        for s in sub_idx_list:
            assert s in SUB_INDEX_NAMES, f"{hint} → invalid sub_index '{s}'"


def test_all_domain_hints_have_domain_lock() -> None:
    """Chaque domain_hint mappe vers ≥1 domain_lock valide."""
    for hint, locks in DOMAIN_HINT_TO_DOMAIN_LOCK.items():
        assert locks, f"{hint} maps to empty domain_lock"
