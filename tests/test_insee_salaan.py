"""Tests pour `src/collect/insee_salaan.py` (SALAAN 2023 agrégation)."""
from __future__ import annotations

from collections import Counter

import pytest

from src.collect.insee_salaan import (
    AGE_TR_LIBELLE,
    CS_LIBELLE,
    CS_TO_DOMAINE,
    REGT_LIBELLE,
    SEXE_LIBELLE,
    TRNNETO_MIDPOINT_EUR,
    _median_from_distribution,
)


def test_mappings_completeness():
    assert len(CS_LIBELLE) == 29  # PCS-ESE Niveau 2 : 29 modalités
    assert len(CS_TO_DOMAINE) == 29
    assert set(CS_LIBELLE) == set(CS_TO_DOMAINE)
    # Couvre les 17 régions métropole + 5 DROM
    assert len(REGT_LIBELLE) >= 17
    # Tranches d'âge quadriennales : 16 tranches
    assert len(AGE_TR_LIBELLE) == 16
    # 2 sexes
    assert len(SEXE_LIBELLE) == 2


def test_trnneto_midpoints_monotone():
    """Les midpoints tranches doivent être strictement croissants."""
    codes = sorted(TRNNETO_MIDPOINT_EUR.keys())
    values = [TRNNETO_MIDPOINT_EUR[c] for c in codes]
    assert values == sorted(values)
    assert len(TRNNETO_MIDPOINT_EUR) == 24


def test_median_from_distribution_basic():
    # Distribution simple : toute la masse en tranche 14 (18-20k)
    dist = Counter({"14": 100.0})
    med, moy = _median_from_distribution(dist)
    assert med == 19000
    assert moy == 19000.0


def test_median_from_distribution_uniform_low_high():
    # 50% à 10k (code 10), 50% à 40k (code 22) → médiane 10 (seuil atteint
    # exactement au cumul 50%), moyenne = (11000 + 45000) / 2 = 28000
    dist = Counter({"10": 100.0, "22": 100.0})
    med, moy = _median_from_distribution(dist)
    assert med == 11000  # première tranche où cumul >= 50%
    assert moy == 28000.0


def test_median_from_distribution_empty():
    med, moy = _median_from_distribution({})
    assert med is None
    assert moy is None


def test_cs_38_is_cadres_ingenieurs():
    """Sanity : code CS 38 = Ingénieurs et cadres techniques."""
    assert CS_TO_DOMAINE["38"] == "cadres_ingenieurs"
    assert "Ingénieurs" in CS_LIBELLE["38"]


def test_cs_34_enseign():
    assert CS_TO_DOMAINE["34"] == "cadres_enseign_sci"
    assert "Professeurs" in CS_LIBELLE["34"]


def test_regt_11_idf():
    assert REGT_LIBELLE["11"] == "Île-de-France"
    assert REGT_LIBELLE["84"] == "Auvergne-Rhône-Alpes"
