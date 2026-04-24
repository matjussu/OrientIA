"""Tests pour `scripts/backfill_legacy_phase.infer_phase`."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "backfill_legacy_phase.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("backfill_legacy_phase", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mod():
    return _load_module()


def test_niveau_bac_plus_5_to_master(mod):
    assert mod.infer_phase({"niveau": "bac+5"}) == "master"


def test_niveau_bac_plus_3_to_initial(mod):
    assert mod.infer_phase({"niveau": "bac+3"}) == "initial"


def test_niveau_bac_plus_2_to_initial(mod):
    assert mod.infer_phase({"niveau": "bac+2"}) == "initial"


def test_niveau_bac_to_initial(mod):
    assert mod.infer_phase({"niveau": "bac"}) == "initial"


def test_niveau_cap_bep_to_initial(mod):
    assert mod.infer_phase({"niveau": "cap-bep"}) == "initial"


def test_no_niveau_nom_mentions_master(mod):
    assert mod.infer_phase({"niveau": None, "nom": "Master MEEF"}) == "master"
    assert mod.infer_phase({"niveau": None, "nom": "MBA Management"}) == "master"
    assert mod.infer_phase({"niveau": None, "nom": "Mastère spécialisé Cybersec"}) == "master"


def test_no_niveau_no_master_defaults_initial(mod):
    assert mod.infer_phase({"niveau": None, "nom": "D.E Infirmier"}) == "initial"
    assert mod.infer_phase({"niveau": None, "nom": "DTS Imagerie médicale"}) == "initial"
    assert mod.infer_phase({"niveau": None, "nom": "Certificat de Spécialisation Cyber"}) == "initial"


def test_empty_fiche_defaults_initial(mod):
    assert mod.infer_phase({}) == "initial"


def test_backfill_idempotent_preserves_existing_phase(mod):
    fiches = [
        {"niveau": "bac+5", "phase": "master"},  # déjà rempli
        {"niveau": None, "nom": "foo"},  # à back-fill → initial
    ]
    counts = mod.backfill(fiches)
    assert fiches[0]["phase"] == "master"  # inchangé
    assert fiches[1]["phase"] == "initial"  # rempli
    assert counts == {"master": 1, "initial": 1}


def test_backfill_handles_empty_list(mod):
    assert mod.backfill([]) == {}
