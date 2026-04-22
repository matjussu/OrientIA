"""Golden suite — chaque hallucination factuelle recensée dans `user_test_v2`
DOIT être détectée par au moins une règle ou un corpus_warning du Validator v1.

Source : `results/user_test_v2/test_orientia_5_profils.md` (5 profils Léo, Sarah,
Thomas, Catherine, Dominique) + ADR-025 (Tier 0 anti-hallucinations) +
ADR-029 (verdict v2 "non recommandable mineur autonomie").

Convention : chaque test prend un texte courtisé et assert que le Validator
le flag (rule violation ou corpus warning). Si une règle attendue ne catch
pas, le test échoue → indication claire du gap à combler.

Hallucinations COUVERTES en v1 (10 cas) :
- ECN/EDN, bac S, Tremplin/Passerelle HEC, VAE/VAP, VAP Infirmier→Kiné,
  école 42 alternance, MBA HEC accessible, prépas privées 2x chances,
  X pour les Nuls concours sélectif, Licence Humanités-Orthophonie inventée.

Hallucinations REPORTÉES v2 (4 cas, structurellement plus difficiles) :
- Distances géographiques (nécessite geocoding)
- Coûts privés sous-estimés (nécessite source de vérité par école)
- Certificat de Spécialisation présenté comme standalone (contextuel)
- CentraleSupélec en "Plan A" (positionnel)
"""
from __future__ import annotations

import pytest

from src.validator import Validator


@pytest.fixture
def corpus_user_test_v2() -> list[dict]:
    """Mini-corpus représentatif des fiches que le pipeline produit pour
    les 10 questions du pack v2. On se concentre sur formations cyber +
    santé pour matcher les domaines testés."""
    return [
        {"nom": "PASS", "etablissement": "Université Paris Cité", "ville": "Paris"},
        {"nom": "L.AS Droit", "etablissement": "Université Lyon 3", "ville": "Lyon"},
        {"nom": "Master Cybersécurité", "etablissement": "EFREI Paris", "ville": "Villejuif"},
        {"nom": "Diplôme d'ingénieur cybersécurité", "etablissement": "ENSIBS", "ville": "Vannes"},
        {"nom": "BUT Informatique", "etablissement": "IUT de Bourges", "ville": "Bourges"},
        {"nom": "BTS SIO", "etablissement": "Lycée Vitry", "ville": "Vitry-sur-Seine"},
        {"nom": "Master MIAGE", "etablissement": "Université de Tours", "ville": "Tours"},
        {"nom": "Diplôme d'ingénieur Polytech", "etablissement": "Polytech Tours", "ville": "Tours"},
    ]


# ---- Cas BLOCKING : 100% de catch requis ----


GOLDEN_BLOCKING_CASES = [
    pytest.param(
        "ECN_in_current_context",
        "Pour PASS, tu passeras les ECN en fin de 6e année de médecine.",
        "ECN_renamed_to_EDN",
        id="ECN_cited_as_current",
    ),
    pytest.param(
        "bac_S_in_current_context",
        "Avec un bac S mention bien spécialité Maths, tu peux viser une prépa MPSI.",
        "bac_S_abolished",
        id="bac_S_cited_as_current",
    ),
    pytest.param(
        "Tremplin_to_HEC",
        "Après ton bac+3, tu peux passer le concours Tremplin pour HEC.",
        "tremplin_not_HEC",
        id="Tremplin_attribué_HEC",
    ),
    pytest.param(
        "Passerelle_to_HEC",
        "Le concours Passerelle est une bonne option pour intégrer HEC en 2 ans.",
        "passerelle_not_HEC",
        id="Passerelle_attribuée_HEC",
    ),
    pytest.param(
        "VAP_infirmier_to_kine",
        "Tu peux passer la passerelle VAP Infirmier vers kiné en 2 ans à temps partiel.",
        "VAP_infirmier_kine",
        id="VAP_infirmier_kine_quasi_impossible",
    ),
    pytest.param(
        "ecole42_gratuite_alternance",
        "L'école 42 est gratuite en alternance, idéale pour se former tout en travaillant.",
        "ecole42_gratuite_alternance",
        id="ecole42_alternance_marketing_faux",
    ),
    pytest.param(
        "licence_humanites_orthophonie_invented",
        "Tu peux préparer le concours en Licence Humanités-Parcours Orthophonie à Poitiers.",
        "licence_humanites_orthophonie_invented",
        id="formation_inventee_humanites_orthophonie",
    ),
]


@pytest.mark.parametrize("label,answer,expected_rule_id", GOLDEN_BLOCKING_CASES)
def test_golden_blocking_hallucination_catched(label, answer, expected_rule_id, corpus_user_test_v2):
    v = Validator(fiches=corpus_user_test_v2)
    result = v.validate(answer)
    rule_ids = {viol.rule_id for viol in result.rule_violations}
    assert expected_rule_id in rule_ids, (
        f"[{label}] Hallucination NON catchée : '{answer[:70]}...'\n"
        f"Violations détectées : {rule_ids}\n"
        f"Règle attendue : {expected_rule_id}\n"
        f"Result summary :\n{result.summary()}"
    )
    assert result.flagged, f"[{label}] Validator devrait flag (BLOCKING)"


# ---- Cas WARNING : doivent réduire honesty_score ----


GOLDEN_WARNING_CASES = [
    pytest.param(
        "MBA HEC est plus accessible avec expérience professionnelle.",
        "MBA_HEC_accessible_experience",
        id="MBA_HEC_accessible_marketing",
    ),
    pytest.param(
        "Une prépa privée médecine double les chances de passer le concours.",
        "prepa_medecine_2x_chances",
        id="prepa_privee_medecine_2x_marketing",
    ),
    pytest.param(
        "Achète 'Orthophonie pour les Nuls' pour réviser le concours CEO.",
        "pour_les_nuls_concours_selectif",
        id="orthophonie_pour_les_nuls_concours_selectif",
    ),
    pytest.param(
        "Tu peux utiliser une VAE pour reprendre tes études en L3 psychologie.",
        "VAE_VAP_confusion",
        id="VAE_au_lieu_de_VAP",
    ),
]


@pytest.mark.parametrize("answer,expected_rule_id", GOLDEN_WARNING_CASES)
def test_golden_warning_hallucination_catched(answer, expected_rule_id, corpus_user_test_v2):
    v = Validator(fiches=corpus_user_test_v2)
    result = v.validate(answer)
    rule_ids = {viol.rule_id for viol in result.rule_violations}
    assert expected_rule_id in rule_ids, (
        f"WARNING NON catché : '{answer[:70]}...'\n"
        f"Violations : {rule_ids}\nRègle attendue : {expected_rule_id}"
    )
    assert result.honesty_score < 1.0, "WARNING doit réduire honesty_score"


# ---- Récapitulatif coverage ----


def test_golden_coverage_count():
    """Sanity : on couvre bien 11 hallucinations en v1.
    7 BLOCKING + 4 WARNING = 11 total. Si ce nombre baisse, gap intro.
    """
    assert len(GOLDEN_BLOCKING_CASES) == 7, "7 BLOCKING attendus en golden v1"
    assert len(GOLDEN_WARNING_CASES) == 4, "4 WARNING attendus en golden v1"
    assert len(GOLDEN_BLOCKING_CASES) + len(GOLDEN_WARNING_CASES) == 11
