"""Tests scaffolds 5 modules FT — `ft_marche_travail` + `ft_sortants_formation`
+ `ft_acces_emploi` + `ft_offres_emploi` + `romeo` (ADR-042 / ADR-043).

Tests 100% mockés (requests). Scopes pas encore activés côté Matteo dashboard
→ tests valident structure code + error handling (CredentialsMissing,
ScopeInvalid, endpoints correctement appelés). Ingestion live = post-activation.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.collect.ft_base import (
    FranceTravailClient,
    FranceTravailCredentialsMissing,
    FranceTravailScopeInvalid,
)
from src.collect.ft_marche_travail import MarcheTravailClient, normalize_tension
from src.collect.ft_sortants_formation import SortantsFormationClient, normalize_insertion
from src.collect.ft_acces_emploi import AccesEmploiClient, normalize_taux_acces
from src.collect.ft_offres_emploi import OffresEmploiClient, normalize_offre
from src.collect.romeo import RomeoClient, normalize_prediction


# --- ft_base ---


def test_base_credentials_missing_raises(monkeypatch):
    monkeypatch.delenv("FT_CLIENT_ID", raising=False)
    monkeypatch.delenv("FT_CLIENT_SECRET", raising=False)
    c = MarcheTravailClient(session=MagicMock())
    with pytest.raises(FranceTravailCredentialsMissing) as exc:
        c._ensure_token()
    assert "TODO_MATTEO_APIS.md" in str(exc.value)


def test_base_invalid_scope_raises_explicit(monkeypatch):
    monkeypatch.setenv("FT_CLIENT_ID", "cid")
    monkeypatch.setenv("FT_CLIENT_SECRET", "csec")
    session = MagicMock()
    resp = MagicMock()
    resp.status_code = 400
    resp.text = '{"error":"invalid_scope","error_description":"Unknown/invalid scope(s)"}'
    session.post.return_value = resp
    c = MarcheTravailClient(session=session)
    with pytest.raises(FranceTravailScopeInvalid) as exc:
        c._ensure_token()
    assert "invalide/non-activé" in str(exc.value)
    assert "dashboard FT" in str(exc.value)


def test_base_token_refresh_logic(monkeypatch):
    monkeypatch.setenv("FT_CLIENT_ID", "cid")
    monkeypatch.setenv("FT_CLIENT_SECRET", "csec")
    session = MagicMock()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"access_token": "tok-abc", "expires_in": 1200}
    resp.raise_for_status = MagicMock()
    session.post.return_value = resp
    c = MarcheTravailClient(session=session)
    t1 = c._ensure_token()
    t2 = c._ensure_token()
    assert t1 == "tok-abc"
    assert t2 == "tok-abc"
    # Token endpoint called une fois seulement (cached)
    assert session.post.call_count == 1


# --- Marché du travail ---


def test_marche_travail_scope_name():
    assert MarcheTravailClient.SCOPE.startswith("api_")
    assert "marche" in MarcheTravailClient.SCOPE.lower()
    assert MarcheTravailClient.BASE_URL.startswith("https://api.francetravail.io")


def test_marche_travail_get_tensions_builds_params(monkeypatch):
    monkeypatch.setenv("FT_CLIENT_ID", "cid")
    monkeypatch.setenv("FT_CLIENT_SECRET", "csec")
    session = MagicMock()
    token_resp = MagicMock()
    token_resp.status_code = 200
    token_resp.json.return_value = {"access_token": "t", "expires_in": 1200}
    token_resp.raise_for_status = MagicMock()
    session.post.return_value = token_resp
    data_resp = MagicMock()
    data_resp.status_code = 200
    data_resp.json.return_value = {"tensions": [{"codeROME": "M1844", "tension": 2.4}]}
    data_resp.raise_for_status = MagicMock()
    session.get.return_value = data_resp
    c = MarcheTravailClient(session=session)
    out = c.get_tensions(code_rome="M1844", region="IDF")
    assert len(out) == 1
    call_params = session.get.call_args[1]["params"]
    assert call_params["codeROME"] == "M1844"
    assert call_params["region"] == "IDF"


def test_normalize_tension_schema():
    n = normalize_tension({"codeROME": "M1844", "tension": 2.5, "offresActives": 100})
    assert n["source"] == "ft_marche_travail"
    assert n["code_rome"] == "M1844"
    assert n["tension_score"] == 2.5


# --- Sortants formation ---


def test_sortants_formation_complements_cereq():
    """Schema normalize_insertion doit avoir clés alignées Céreq (taux_emploi_6m)."""
    rec = {"codeROME": "M1405", "tauxAccesEmploi6Mois": 0.88, "tauxCDI": 0.55}
    n = normalize_insertion(rec)
    assert n["source"] == "ft_sortants_formation"
    assert n["taux_emploi_6m"] == 0.88
    assert n["taux_cdi"] == 0.55


# --- Accès emploi demandeurs ---


def test_acces_emploi_scope_validity():
    assert "acces" in AccesEmploiClient.SCOPE.lower()
    assert "demandeurs" in AccesEmploiClient.SCOPE.lower() or "demandeur" in AccesEmploiClient.SCOPE.lower()


def test_normalize_taux_acces_schema():
    n = normalize_taux_acces({"codeROME": "M1844", "trancheAge": "16-25", "tauxAcces": 0.72})
    assert n["source"] == "ft_acces_emploi"
    assert n["tranche_age"] == "16-25"
    assert n["taux_emploi_6m"] == 0.72


# --- Offres d'emploi v2 ---


def test_offres_emploi_scope():
    # Nom compacté (pas de tiret) confirmé par probe OAuth2 2026-04-24.
    # Le nom avec tiret `api_offresdemploi-v2` retourne invalid_scope.
    assert OffresEmploiClient.SCOPE == "api_offresdemploiv2"
    assert OffresEmploiClient.BASE_URL.endswith("/offresdemploi/v2")


def test_offres_emploi_search_range_param(monkeypatch):
    monkeypatch.setenv("FT_CLIENT_ID", "cid")
    monkeypatch.setenv("FT_CLIENT_SECRET", "csec")
    session = MagicMock()
    tok = MagicMock()
    tok.status_code = 200
    tok.json.return_value = {"access_token": "t", "expires_in": 1200}
    tok.raise_for_status = MagicMock()
    session.post.return_value = tok
    dr = MagicMock()
    dr.status_code = 200
    dr.json.return_value = {"resultats": []}
    dr.raise_for_status = MagicMock()
    session.get.return_value = dr
    c = OffresEmploiClient(session=session)
    c.search(code_rome="M1844")
    params = session.get.call_args[1]["params"]
    # Le param range est obligatoire "start-end"
    assert "-" in params["range"]


def test_normalize_offre_maps_nested_fields():
    rec = {
        "id": "abc123",
        "intitule": "Dev Python",
        "metier": {"code": "M1811", "libelle": "Data engineer"},
        "entreprise": {"nom": "ACME"},
        "lieuTravail": {"libelle": "Paris 75", "codePostal": "75001"},
        "typeContrat": "CDI",
    }
    n = normalize_offre(rec)
    assert n["code_rome"] == "M1811"
    assert n["entreprise"] == "ACME"
    assert n["lieu"] == "Paris 75"
    assert n["type_contrat"] == "CDI"


# --- ROMEO ---


def test_romeo_scope_and_url():
    assert "romeo" in RomeoClient.SCOPE.lower()
    assert RomeoClient.BASE_URL.endswith("/romeo/v2")


def test_romeo_predict_empty_text_returns_empty():
    c = RomeoClient(session=MagicMock())
    assert c.predict_rome_from_text("") == []


def test_normalize_prediction_handles_score_alternatives():
    n = normalize_prediction({"codeROME": "M1844", "libelle": "Analyste cybersécurité", "score": 0.92})
    assert n["code_rome"] == "M1844"
    assert n["score"] == 0.92
    # Test variante scorePrediction
    n2 = normalize_prediction({"code": "M1405", "scorePrediction": 0.85})
    assert n2["code_rome"] == "M1405"
    assert n2["score"] == 0.85


# --- Sanity : tous les clients partagent la base ---


@pytest.mark.parametrize(
    "client_cls",
    [
        MarcheTravailClient,
        SortantsFormationClient,
        AccesEmploiClient,
        OffresEmploiClient,
        RomeoClient,
    ],
)
def test_all_ft_clients_inherit_base(client_cls):
    assert issubclass(client_cls, FranceTravailClient)
    assert client_cls.SCOPE, f"{client_cls.__name__} doit définir un SCOPE"
    assert client_cls.BASE_URL.startswith("https://"), f"{client_cls.__name__} BASE_URL invalide"
    assert client_cls.DEFAULT_RPM > 0
