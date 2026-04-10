from unittest.mock import MagicMock
from src.rag.generator import format_context, generate


def test_format_context_includes_all_fiches():
    results = [
        {"fiche": {"nom": "Master A", "etablissement": "X", "ville": "Paris",
                   "labels": ["SecNumEdu"], "statut": "Public",
                   "taux_acces_parcoursup_2025": 25.0}, "score": 0.9},
        {"fiche": {"nom": "Master B", "etablissement": "Y", "ville": "Lyon",
                   "labels": [], "statut": "Privé"}, "score": 0.7},
    ]
    context = format_context(results)
    assert "Master A" in context
    assert "Master B" in context
    assert "SecNumEdu" in context


def test_generate_calls_mistral_with_system_and_user_prompts():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Response text"))]
    mock_client.chat.complete.return_value = mock_response

    results = [{"fiche": {"nom": "F", "etablissement": "E", "ville": "V", "labels": [],
                          "statut": "Public"}, "score": 0.5}]
    answer = generate(mock_client, results, "question?", model="mistral-medium-latest")
    assert answer == "Response text"
    call = mock_client.chat.complete.call_args
    messages = call.kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "question?" in messages[1]["content"]
