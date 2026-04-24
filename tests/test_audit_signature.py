"""Tests pour `scripts/audit_data_quality._signature()`.

La signature doit distinguer :
- Même IFC MonMaster sur 2 sessions (2024 vs 2025) : snapshots annuels distincts
- ONISEP avec libellé identique mais slug `FOR.XXX` différent : formations
  distinctes qui se partagent un intitulé générique (ex. "data engineer")

Et doit regrouper :
- Même `cod_aff_form` Parcoursup
- Même `id_lba`
- Même `numero_fiche` RNCP
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPT = REPO_ROOT / "scripts" / "audit_data_quality.py"


def _load_sig():
    spec = importlib.util.spec_from_file_location("audit_dq", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod._signature


@pytest.fixture(scope="module")
def sig():
    return _load_sig()


def test_monmaster_same_ifc_different_session_not_duplicate(sig):
    f_2024 = {"id_mon_master": {"ifc": "0900820SRD2N", "session": "2024"}, "nom": "X"}
    f_2025 = {"id_mon_master": {"ifc": "0900820SRD2N", "session": "2025"}, "nom": "X"}
    assert sig(f_2024) != sig(f_2025)
    assert "session=2024" in sig(f_2024)
    assert "session=2025" in sig(f_2025)


def test_monmaster_same_ifc_same_session_is_duplicate(sig):
    f_a = {"id_mon_master": {"ifc": "AAA", "session": "2025"}, "nom": "X"}
    f_b = {"id_mon_master": {"ifc": "AAA", "session": "2025"}, "nom": "X"}
    assert sig(f_a) == sig(f_b)


def test_monmaster_session_missing_does_not_crash(sig):
    f = {"id_mon_master": {"ifc": "BBB"}, "nom": "X"}
    result = sig(f)
    assert "mm_ifc=BBB" in result
    assert "session=" in result


def test_onisep_slug_distinguishes_same_libelle(sig):
    f_a = {
        "source": "onisep",
        "nom": "data engineer",
        "url_onisep": "https://www.onisep.fr/http/redirection/formation/slug/FOR.10713",
    }
    f_b = {
        "source": "onisep",
        "nom": "data engineer",
        "url_onisep": "https://www.onisep.fr/http/redirection/formation/slug/FOR.10070",
    }
    assert sig(f_a) != sig(f_b)
    assert "FOR.10713" in sig(f_a)
    assert "FOR.10070" in sig(f_b)


def test_onisep_same_slug_is_duplicate(sig):
    f_a = {"source": "onisep", "url_onisep": ".../slug/FOR.999", "nom": "A"}
    f_b = {"source": "onisep", "url_onisep": ".../slug/FOR.999", "nom": "B different nom"}
    assert sig(f_a) == sig(f_b)


def test_onisep_without_slug_falls_back_to_libelle(sig):
    f = {"source": "onisep", "nom": "foo", "etablissement": "bar", "ville": "baz"}
    assert sig(f) == "foo|bar|baz"


def test_top_level_id_priority(sig):
    f = {
        "cod_aff_form": "PS123",
        "id_mon_master": {"ifc": "XYZ"},  # ignoré car cod_aff_form présent
        "source": "onisep",
        "url_onisep": ".../slug/FOR.1",  # ignoré aussi
    }
    assert sig(f) == "id:cod_aff_form=PS123"


def test_rncp_numero_fiche(sig):
    assert sig({"numero_fiche": "RNCP38500"}) == "id:numero_fiche=RNCP38500"


def test_lba_id(sig):
    assert sig({"id_lba": "lba-abc"}) == "id:id_lba=lba-abc"


def test_fallback_libelle_etab_ville(sig):
    f = {"nom": "Licence Info", "etablissement": "UPSay", "ville": "Orsay"}
    assert sig(f) == "licence info|upsay|orsay"
