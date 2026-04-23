"""Tests scaffold RomeApiClient (S+1 Axe 1 D3).

Tous les tests mockent `requests` — zéro appel réseau. Les tests
d'intégration réels (avec FT_CLIENT_ID/SECRET en env) viendront dans
`tests/integration/test_rome_api_live.py` quand la clé arrive.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.collect.rome_api import (
    DEFAULT_RPM,
    RomeApiAuthError,
    RomeApiClient,
    RomeApiCredentialsMissing,
)


# --- Helpers ---


def _mock_session(responses: list[MagicMock]) -> MagicMock:
    """Session mock qui renvoie les responses dans l'ordre sur get/post."""
    session = MagicMock()
    session.post.side_effect = [r for r in responses if r._is_post]  # type: ignore[attr-defined]
    session.get.side_effect = [r for r in responses if not r._is_post]  # type: ignore[attr-defined]
    return session


def _resp(status: int = 200, json_body=None, text: str = "", is_post: bool = False):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json_body if json_body is not None else {}
    r.text = text
    r.raise_for_status = MagicMock()
    if status >= 400:
        r.raise_for_status.side_effect = Exception(f"HTTP {status}")
    r._is_post = is_post  # type: ignore[attr-defined]
    return r


# --- Credentials ---


def test_missing_credentials_raises_explicit_error(monkeypatch):
    monkeypatch.delenv("FT_CLIENT_ID", raising=False)
    monkeypatch.delenv("FT_CLIENT_SECRET", raising=False)
    client = RomeApiClient(session=MagicMock())
    with pytest.raises(RomeApiCredentialsMissing) as excinfo:
        client.get_metier("M1844")
    assert "TODO_MATTEO_APIS.md" in str(excinfo.value)


def test_empty_credentials_raise(monkeypatch):
    monkeypatch.setenv("FT_CLIENT_ID", "   ")
    monkeypatch.setenv("FT_CLIENT_SECRET", "")
    client = RomeApiClient(session=MagicMock())
    with pytest.raises(RomeApiCredentialsMissing):
        client.get_metier("M1844")


# --- OAuth2 flow ---


def test_token_acquired_and_reused(monkeypatch):
    monkeypatch.setenv("FT_CLIENT_ID", "cid")
    monkeypatch.setenv("FT_CLIENT_SECRET", "csec")
    session = MagicMock()
    session.post.return_value = _resp(
        200, {"access_token": "tok-xyz", "expires_in": 1200}, is_post=True
    )
    session.get.return_value = _resp(200, {"code": "M1844", "libelle": "Analyste cybersécurité"})
    client = RomeApiClient(session=session)

    first = client.get_metier("M1844")
    second = client.get_metier("M1811")

    assert first["code"] == "M1844"
    assert second == session.get.return_value.json.return_value
    # Token call une seule fois (réutilisé entre appels)
    assert session.post.call_count == 1
    # 2 GET sur endpoints métier
    assert session.get.call_count == 2


def test_auth_failure_raises_rome_auth_error(monkeypatch):
    monkeypatch.setenv("FT_CLIENT_ID", "cid")
    monkeypatch.setenv("FT_CLIENT_SECRET", "bad")
    session = MagicMock()
    session.post.return_value = _resp(401, {"error": "invalid_client"}, is_post=True)
    client = RomeApiClient(session=session)
    with pytest.raises(RomeApiAuthError) as exc:
        client.get_metier("M1844")
    assert "401" in str(exc.value)


def test_token_without_access_token_field_raises(monkeypatch):
    monkeypatch.setenv("FT_CLIENT_ID", "cid")
    monkeypatch.setenv("FT_CLIENT_SECRET", "csec")
    session = MagicMock()
    session.post.return_value = _resp(200, {"expires_in": 1200}, is_post=True)
    client = RomeApiClient(session=session)
    with pytest.raises(RomeApiAuthError):
        client.get_metier("M1844")


# --- Endpoints ---


def _client_with_token(monkeypatch) -> tuple[RomeApiClient, MagicMock]:
    monkeypatch.setenv("FT_CLIENT_ID", "cid")
    monkeypatch.setenv("FT_CLIENT_SECRET", "csec")
    session = MagicMock()
    session.post.return_value = _resp(
        200, {"access_token": "tok-xyz", "expires_in": 1200}, is_post=True
    )
    return RomeApiClient(session=session), session


def test_get_metier_empty_code_raises(monkeypatch):
    client, _ = _client_with_token(monkeypatch)
    with pytest.raises(ValueError):
        client.get_metier("")


def test_search_metiers_returns_list_from_dict_payload(monkeypatch):
    client, session = _client_with_token(monkeypatch)
    session.get.return_value = _resp(
        200, {"metiers": [{"code": "M1405", "libelle": "Data scientist"}]}
    )
    results = client.search_metiers("data")
    assert len(results) == 1
    assert results[0]["code"] == "M1405"


def test_search_metiers_handles_resultats_key(monkeypatch):
    client, session = _client_with_token(monkeypatch)
    session.get.return_value = _resp(
        200, {"resultats": [{"code": "M1844"}]}
    )
    results = client.search_metiers("cyber")
    assert results[0]["code"] == "M1844"


def test_search_metiers_empty_query_returns_empty_list(monkeypatch):
    client, session = _client_with_token(monkeypatch)
    assert client.search_metiers("") == []
    # Aucun appel GET n'a dû être fait
    session.get.assert_not_called()


def test_get_fiche_metier_calls_correct_endpoint(monkeypatch):
    client, session = _client_with_token(monkeypatch)
    session.get.return_value = _resp(200, {"code": "M1844", "salaires": {}})
    fiche = client.get_fiche_metier("M1844")
    assert fiche["code"] == "M1844"
    call_args = session.get.call_args
    assert "fiches-rome" in call_args[0][0] or "fiches-rome" in str(call_args)


# --- Rate limiting ---


def test_rate_limiter_is_acquired_per_call(monkeypatch):
    client, session = _client_with_token(monkeypatch)
    session.get.return_value = _resp(200, {"code": "M1844"})
    acquire_mock = MagicMock()
    client._limiter.acquire = acquire_mock  # type: ignore[method-assign]
    client.get_metier("M1844")
    # Un acquire pour le token + un pour le GET métier
    assert acquire_mock.call_count >= 2


def test_default_rpm_is_conservative():
    # France Travail ROME 4.0 = 1 RPS officiel = 60 RPM cap.
    # DEFAULT_RPM doit être <= 60 pour respecter le cap, mais >= 30 pour
    # rester productif (éviter rate limiter trop timide).
    assert DEFAULT_RPM <= 60, f"DEFAULT_RPM={DEFAULT_RPM} dépasse cap ROME 4.0 = 60 RPM"
    assert DEFAULT_RPM >= 30, f"DEFAULT_RPM={DEFAULT_RPM} trop timide (cap 60 RPM, marge >50%)"
