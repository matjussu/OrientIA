"""Tests Layer3Validator (couche 3 LLM souverain Mistral Small)."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.validator.layer3 import Layer3Validator, Layer3Warning


class FakeChatComplete:
    """Mock la chaîne client.chat.complete(...) du SDK Mistral."""

    def __init__(self, content: str):
        self.content = content

    def complete(self, **kwargs):
        msg = MagicMock()
        msg.content = self.content
        choice = MagicMock()
        choice.message = msg
        resp = MagicMock()
        resp.choices = [choice]
        return resp


class FakeMistralClient:
    def __init__(self, content: str):
        self.chat = FakeChatComplete(content)


# --- Smoke / safety ---


def test_layer3_returns_empty_without_client():
    l3 = Layer3Validator(client=None)
    assert l3.check("answer") == []


def test_layer3_returns_empty_on_empty_answer():
    l3 = Layer3Validator(client=FakeMistralClient('{"suspect_claims": []}'))
    assert l3.check("") == []
    assert l3.check("   ") == []


# --- Parsing JSON ---


def test_layer3_parses_valid_json_response():
    content = """{
      "suspect_claims": [
        {"claim": "BBA INSEEC à 10k€/an", "reason": "Coût privé sous-estimé", "severity": "warning"}
      ]
    }"""
    l3 = Layer3Validator(client=FakeMistralClient(content))
    warnings = l3.check("BBA INSEEC à 10k€/an — accessible")
    assert len(warnings) == 1
    assert isinstance(warnings[0], Layer3Warning)
    assert "INSEEC" in warnings[0].claim
    assert warnings[0].reason.startswith("Coût")


def test_layer3_parses_JSON_embedded_in_text():
    """Mistral peut renvoyer 'Voici : {json}' — on parse quand même."""
    content = "Voici l'analyse :\n" + '{"suspect_claims": [{"claim": "X", "reason": "Y"}]}'
    l3 = Layer3Validator(client=FakeMistralClient(content))
    warnings = l3.check("answer contenant X")
    assert len(warnings) == 1


def test_layer3_returns_empty_on_unparseable_response():
    l3 = Layer3Validator(client=FakeMistralClient("rien de JSON ici"))
    assert l3.check("answer") == []


def test_layer3_ignores_malformed_claim_items():
    content = '{"suspect_claims": [{"claim": "", "reason": "no claim"}, {"not_a_dict": 42}]}'
    l3 = Layer3Validator(client=FakeMistralClient(content))
    assert l3.check("answer") == []


# --- Graceful fallback sur erreur API ---


class FakeChatCompleteRaises:
    def complete(self, **kwargs):
        raise Exception("API unreachable")


class FakeMistralClientBroken:
    chat = FakeChatCompleteRaises()


def test_layer3_returns_empty_on_api_error():
    l3 = Layer3Validator(client=FakeMistralClientBroken())
    # Pas de crash, juste return [] (graceful)
    assert l3.check("answer") == []


# --- Validator integration ---


def test_validator_without_layer3_backward_compat():
    """Validator sans layer3 (comportement V1) reste identique."""
    from src.validator import Validator

    v = Validator(fiches=[{"nom": "Master Info", "etablissement": "X"}])
    result = v.validate("Réponse propre")
    assert result.layer3_warnings == []
    assert result.honesty_score == 1.0


def test_validator_with_layer3_exposes_warnings():
    from src.validator import Validator

    content = '{"suspect_claims": [{"claim": "BBA 10k€", "reason": "sous-estimé"}]}'
    layer3 = Layer3Validator(client=FakeMistralClient(content))
    v = Validator(
        fiches=[{"nom": "Master Info", "etablissement": "X"}],
        layer3=layer3,
    )
    result = v.validate("Réponse BBA 10k€")
    assert len(result.layer3_warnings) == 1
    # Score honnêteté pénalisé par layer3 warning (-0.05)
    assert result.honesty_score < 1.0


def test_validator_layer3_does_not_escalate_flagged():
    """Un layer3 warning seul ne doit pas positionner flagged=True
    (cohérent avec policy β Warn — couche 3 = subtil, pas BLOCKING)."""
    from src.validator import Validator

    content = '{"suspect_claims": [{"claim": "claim subtil", "reason": "pattern marketing"}]}'
    layer3 = Layer3Validator(client=FakeMistralClient(content))
    v = Validator(fiches=[], layer3=layer3)
    result = v.validate("Réponse contenant claim subtil")
    assert result.layer3_warnings
    assert not result.flagged  # couche 3 seule = pas de flag
