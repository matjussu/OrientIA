"""Tests `src/collect/labonnealternance.py` — scaffold D10 Axe 1.

Tests 100% mockés (requests) — activation live quand LBA_API_TOKEN arrive.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.collect.labonnealternance import (
    DEFAULT_RPM,
    LabonneAlternanceClient,
    LabonneAlternanceCredentialsMissing,
    normalize_formation,
    normalize_job_offer,
)


def test_missing_token_raises(monkeypatch):
    monkeypatch.delenv("LBA_API_TOKEN", raising=False)
    client = LabonneAlternanceClient(session=MagicMock())
    with pytest.raises(LabonneAlternanceCredentialsMissing) as exc:
        client.search_formations(rome="M1844")
    assert "TODO_MATTEO_APIS.md" in str(exc.value)


def test_empty_token_raises(monkeypatch):
    monkeypatch.setenv("LBA_API_TOKEN", "   ")
    client = LabonneAlternanceClient(session=MagicMock())
    with pytest.raises(LabonneAlternanceCredentialsMissing):
        client.search_formations(rome="M1844")


def test_search_formations_calls_endpoint(monkeypatch):
    monkeypatch.setenv("LBA_API_TOKEN", "test-tok")
    session = MagicMock()
    resp = MagicMock()
    # Format réel LBA : {"data": [...], "pagination": {...}}
    # On accepte aussi le format legacy {"formations": [...]} pour compat.
    resp.json.return_value = {"formations": [{"id": "f1", "intitule": "BTS CG"}]}
    resp.raise_for_status = MagicMock()
    session.get.return_value = resp
    client = LabonneAlternanceClient(session=session)
    out = client.search_formations(rome="M1203", departement="75")
    assert len(out) == 1
    assert out[0]["id"] == "f1"
    call = session.get.call_args
    # URL corrigée post-swagger : /api/formation/v1/search (singular resource)
    assert "formation" in call[0][0]
    assert "/v1/search" in call[0][0]
    assert call[1]["params"]["rome"] == "M1203"
    assert call[1]["params"]["departement"] == "75"


def test_search_jobs_joins_rome_codes(monkeypatch):
    monkeypatch.setenv("LBA_API_TOKEN", "test-tok")
    session = MagicMock()
    resp = MagicMock()
    resp.json.return_value = {"jobs": [{"id": "j1"}]}
    resp.raise_for_status = MagicMock()
    session.get.return_value = resp
    client = LabonneAlternanceClient(session=session)
    out = client.search_jobs(rome_codes=["M1844", "M1819"], geo="75001")
    assert len(out) == 1
    call = session.get.call_args
    assert call[1]["params"]["romes"] == "M1844,M1819"
    assert call[1]["params"]["insee"] == "75001"


def test_rate_limiter_acquired(monkeypatch):
    monkeypatch.setenv("LBA_API_TOKEN", "test-tok")
    session = MagicMock()
    resp = MagicMock()
    resp.json.return_value = {"formations": []}
    resp.raise_for_status = MagicMock()
    session.get.return_value = resp
    limiter = MagicMock()
    client = LabonneAlternanceClient(session=session, rate_limiter=limiter)
    client.search_formations(rome="M1844")
    limiter.acquire.assert_called()


def test_default_rpm_is_reasonable():
    assert 60 <= DEFAULT_RPM <= 300


# --- Normalisation ---


def test_normalize_formation_sets_phase_reorientation():
    rec = {
        "id": "lba-42",
        "intitule_long": "BTS Comptabilité Gestion en alternance",
        "etablissement_formateur_raison_sociale": "CFA Paris",
        "etablissement_formateur_localite": "Paris",
        "etablissement_formateur_code_postal": "75015",
        "rncp_code": "RNCP35521",
        "romes": ["M1203"],
        "niveau": "NIV5",
    }
    fiche = normalize_formation(rec)
    assert fiche["source"] == "labonnealternance"
    assert fiche["phase"] == "reorientation"  # ADR-039 phase (b)
    assert fiche["modalite"] == "alternance"
    assert fiche["departement"] == "75"
    assert fiche["rome_codes"] == ["M1203"]


def test_normalize_job_offer_is_offre_alternance():
    rec = {
        "id": "job-7",
        "title": "Alternant(e) comptable",
        "company_name": "Cabinet Expert",
        "rome_code": "M1203",
        "place": "Lyon",
        "start_date": "2026-09-01",
        "duration": 24,
    }
    job = normalize_job_offer(rec)
    assert job["type"] == "offre_alternance"
    assert job["rome_code"] == "M1203"
    assert job["duree_contrat_mois"] == 24
