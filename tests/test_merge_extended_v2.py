"""Tests pour l'extension v2 de `merge_all_extended()` (ADR-039 scope élargi).

Focus : nouvelles sources pré-normalisées (`parcoursup_extended`,
`onisep_extended`, `lba`), enrichissement Céreq compatible xlsx +
csv schémas, phase par défaut.
"""
from __future__ import annotations

import pytest

from src.collect.merge import (
    _cereq_stats_flat,
    attach_cereq_insertion,
    merge_all_extended,
)


# --- attach_cereq_insertion : 2 schémas supportés ---


def test_attach_cereq_insertion_xlsx_schema():
    """Schéma xlsx : horizon_3ans + horizon_6ans sous-dicts."""
    fiches = [{"niveau": "bac+5", "domaine": "sciences_fondamentales"}]
    cereq = [{
        "niveau": "bac+5",
        "domaine": None,  # Ensemble Masters (pas de domaine spécifique)
        "cohorte": "Generation 2017",
        "horizon_3ans": {"taux_emploi": 85, "taux_edi": 83, "revenu_travail": 2080},
        "horizon_6ans": {"taux_emploi": 91, "revenu_travail": 2500},
    }]
    out = attach_cereq_insertion(fiches, cereq)
    assert out[0]["insertion_pro"]["taux_emploi_3ans"] == 0.85
    assert out[0]["insertion_pro"]["taux_emploi_6ans"] == 0.91
    assert out[0]["insertion_pro"]["taux_cdi"] == 0.83
    assert out[0]["insertion_pro"]["salaire_median_embauche"] == 2080
    assert out[0]["insertion_pro"]["source"] == "cereq"


def test_attach_cereq_insertion_csv_legacy_schema():
    """Schéma CSV legacy : champs plats à la racine."""
    fiches = [{"niveau": "bac+3", "domaine": "informatique"}]
    cereq = [{
        "niveau": "bac+3",
        "domaine": "informatique",
        "cohorte": "Generation 2017",
        "taux_emploi_3ans": 0.78,
        "taux_emploi_6ans": 0.84,
        "taux_cdi": 0.72,
        "salaire_median_embauche": 1850,
    }]
    out = attach_cereq_insertion(fiches, cereq)
    assert out[0]["insertion_pro"]["taux_emploi_3ans"] == 0.78
    assert out[0]["insertion_pro"]["salaire_median_embauche"] == 1850


def test_attach_cereq_insertion_niveau_seul_fallback():
    """Match fallback niveau seul si fiche n'a pas de domaine matchable."""
    fiches = [{"niveau": "bac+5", "domaine": "domaine_inexistant"}]
    cereq = [{
        "niveau": "bac+5",
        "domaine": None,
        "cohorte": "Generation 2017",
        "horizon_3ans": {"taux_emploi": 85},
    }]
    out = attach_cereq_insertion(fiches, cereq)
    # Le niveau seul "bac+5" doit être trouvé en fallback
    assert out[0].get("insertion_pro") is not None
    assert out[0]["insertion_pro"]["taux_emploi_3ans"] == 0.85


def test_attach_cereq_insertion_empty_cereq_noop():
    fiches = [{"niveau": "bac+5", "domaine": "x"}]
    out = attach_cereq_insertion(fiches, [])
    assert "insertion_pro" not in out[0]


def test_attach_cereq_insertion_fiche_sans_niveau():
    fiches = [{"niveau": None, "domaine": "x"}]
    cereq = [{"niveau": "bac+5", "horizon_3ans": {"taux_emploi": 85}}]
    out = attach_cereq_insertion(fiches, cereq)
    assert "insertion_pro" not in out[0]


def test_cereq_stats_flat_partial_horizon():
    """Si horizon_6ans absent → taux_emploi_6ans None, pas d'erreur."""
    entry = {
        "cohorte": "G17",
        "horizon_3ans": {"taux_emploi": 80, "revenu_travail": 2000},
        "horizon_6ans": None,
    }
    result = _cereq_stats_flat(entry)
    assert result["taux_emploi_3ans"] == 0.80
    assert result["taux_emploi_6ans"] is None
    assert result["salaire_median_embauche"] == 2000


# --- merge_all_extended v2 : nouvelles sources ---


def test_merge_all_extended_accepts_new_sources_empty():
    """Backward-compat : signature acceptes parcoursup_extended / onisep_extended /
    lba sans casser le pipeline legacy."""
    result = merge_all_extended(
        parcoursup=[],
        onisep=[],
        secnumedu=[],
        parcoursup_extended=None,
        onisep_extended=None,
        lba=None,
    )
    assert result == []


def test_merge_all_extended_appends_pre_normalized_sources():
    """Les 3 sources pré-normalisées sont appendées et enrichies avec phase."""
    result = merge_all_extended(
        parcoursup=[],
        onisep=[],
        secnumedu=[],
        parcoursup_extended=[
            {"source": "parcoursup", "nom": "PE1", "niveau": "bac+3", "phase": "initial"},
        ],
        onisep_extended=[
            {"source": "onisep", "nom": "OE1", "niveau": "bac+5", "phase": "master"},
        ],
        lba=[
            {"source": "labonnealternance", "nom": "L1", "niveau": "bac+2", "phase": "reorientation"},
        ],
    )
    assert len(result) == 3
    names = {f["nom"] for f in result}
    assert names == {"PE1", "OE1", "L1"}
    phases = {f["phase"] for f in result}
    assert phases == {"initial", "master", "reorientation"}


def test_merge_all_extended_fills_missing_phase():
    """Une fiche sans phase dans un corpus extended doit en obtenir une par
    défaut via le fallback étape 8."""
    result = merge_all_extended(
        parcoursup=[],
        onisep=[],
        secnumedu=[],
        parcoursup_extended=[
            {"source": "parcoursup", "nom": "NoPhase", "niveau": "bac+5"},  # pas de phase
        ],
    )
    assert len(result) == 1
    assert result[0]["phase"] == "master"  # niveau bac+5 → master


def test_merge_all_extended_enriches_with_cereq():
    """Intégration : cereq fournis en param → fiches enrichies via insertion_pro."""
    result = merge_all_extended(
        parcoursup=[],
        onisep=[],
        secnumedu=[],
        parcoursup_extended=[
            {"source": "parcoursup", "nom": "Master Info", "niveau": "bac+5", "domaine": "data_ia"},
        ],
        cereq=[
            {"niveau": "bac+5", "domaine": None, "cohorte": "G17",
             "horizon_3ans": {"taux_emploi": 85}},
        ],
    )
    assert len(result) == 1
    assert result[0].get("insertion_pro") is not None
    assert result[0]["insertion_pro"]["taux_emploi_3ans"] == 0.85
