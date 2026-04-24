"""Tests intégration Inserjeunes CFA dans merger v2.

Focus : adapter `inserjeunes_cfa_to_fiche()`, phase="reorientation" par
défaut, et nouvel argument `inserjeunes_cfa` de `merge_all_extended()`.
"""
from __future__ import annotations

import pytest

from src.collect.merge import (
    inserjeunes_cfa_to_fiche,
    merge_all_extended,
)


def test_cfa_to_fiche_phase_reorientation():
    """Tous les CFA partent en phase reorientation (ADR-039 rééquilibrage)."""
    rec = {
        "source": "inserjeunes_cfa",
        "etablissement": "CFA Test",
        "region": "IDF",
        "uai": "0750000X",
        "taux_emploi": {"6m": 0.8, "12m": 0.85, "18m": None, "24m": None},
    }
    f = inserjeunes_cfa_to_fiche(rec)
    assert f["phase"] == "reorientation"
    assert f["source"] == "inserjeunes_cfa"
    assert f["nom"] == "CFA Test"
    assert f["etablissement"] == "CFA Test"
    assert f["domaine"] == "apprentissage"
    assert f["niveau"] is None


def test_cfa_to_fiche_insertion_pro_schema():
    rec = {
        "etablissement": "CFA X",
        "annee": "cumul 2022-2023",
        "taux_emploi": {"6m": 0.77, "12m": 0.71, "18m": None, "24m": None},
        "taux_emploi_6_mois_attendu": 0.65,
        "valeur_ajoutee_emploi_6_mois": 0.12,
        "taux_contrats_interrompus": 0.055,
        "part_poursuite_etudes": 0.49,
        "part_emploi_6_mois_post": 0.39,
        "part_autres_situations": 0.12,
    }
    f = inserjeunes_cfa_to_fiche(rec)
    ip = f["insertion_pro"]
    assert ip["source"] == "inserjeunes_cfa"
    assert ip["taux_emploi_6m"] == 0.77
    assert ip["taux_emploi_12m"] == 0.71
    assert ip["taux_emploi_18m"] is None
    assert ip["valeur_ajoutee_emploi_6m"] == 0.12
    assert ip["taux_contrats_interrompus"] == 0.055
    assert ip["part_poursuite_etudes"] == 0.49


def test_cfa_to_fiche_handles_missing_etablissement():
    """Pas de libellé CFA → fallback string pour éviter None dans nom."""
    f = inserjeunes_cfa_to_fiche({"uai": "0999999Z"})
    assert "CFA" in f["nom"]  # "CFA (libellé manquant)"
    assert f["phase"] == "reorientation"


def test_merge_all_extended_accepts_cfa_param():
    result = merge_all_extended(
        parcoursup=[], onisep=[], secnumedu=[],
        inserjeunes_cfa=[
            {"etablissement": "CFA A", "taux_emploi": {"6m": 0.8}},
            {"etablissement": "CFA B", "taux_emploi": {"6m": 0.7}},
        ],
    )
    assert len(result) == 2
    phases = {f["phase"] for f in result}
    assert phases == {"reorientation"}
    names = {f["nom"] for f in result}
    assert names == {"CFA A", "CFA B"}


def test_merge_all_extended_cfa_default_none():
    """Backward-compat : nouveau param optionnel, None par défaut → no-op."""
    result = merge_all_extended(parcoursup=[], onisep=[], secnumedu=[])
    assert result == []


def test_merge_all_extended_combines_lba_and_cfa_for_reorientation():
    """LBA + CFA ensemble → 2 sources de phase reorientation."""
    result = merge_all_extended(
        parcoursup=[], onisep=[], secnumedu=[],
        lba=[{"source": "labonnealternance", "nom": "Forma LBA",
              "niveau": "bac+2", "phase": "reorientation"}],
        inserjeunes_cfa=[{"etablissement": "CFA X", "taux_emploi": {}}],
    )
    assert len(result) == 2
    phases = [f["phase"] for f in result]
    assert phases.count("reorientation") == 2
