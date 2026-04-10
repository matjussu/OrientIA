import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.eval.systems import OurRagSystem, MistralRawSystem, ChatGPTRecordedSystem


def test_chatgpt_recorded_returns_stored_answer(tmp_path):
    data = {"_metadata": {"model": "gpt-4o"}, "A1": "answer A1"}
    path = tmp_path / "chatgpt.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    system = ChatGPTRecordedSystem(path)
    assert system.answer("A1", "ignored question") == "answer A1"


def test_chatgpt_recorded_raises_on_missing_id(tmp_path):
    data = {"_metadata": {"model": "gpt-4o"}, "A1": "answer A1"}
    path = tmp_path / "chatgpt.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    system = ChatGPTRecordedSystem(path)
    import pytest
    with pytest.raises(KeyError, match="B1"):
        system.answer("B1", "ignored")


def test_chatgpt_recorded_skips_metadata_key():
    """The _metadata key in the JSON must not be treated as a question id.
    Verified by the fact that accessing it via answer() raises KeyError."""
    import pytest
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump({"_metadata": {"date": "2026-04-10"}, "A1": "x"}, f)
        path = f.name
    system = ChatGPTRecordedSystem(path)
    with pytest.raises(KeyError, match="_metadata"):
        system.answer("_metadata", "ignored")


def test_mistral_raw_uses_same_system_prompt_but_no_context():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="raw answer"))]
    mock_client.chat.complete.return_value = mock_response

    system = MistralRawSystem(mock_client)
    answer = system.answer("A1", "Quelles formations cyber ?")
    assert answer == "raw answer"
    messages = mock_client.chat.complete.call_args.kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert "Quelles formations cyber" in messages[1]["content"]
    # CRITICAL: the raw Mistral system must NOT receive any FICHE context
    # (the whole point of the ablation is to isolate the effect of the RAG)
    assert "FICHE" not in messages[1]["content"]


def test_our_rag_uses_pipeline():
    mock_pipeline = MagicMock()
    mock_pipeline.answer.return_value = ("our answer", [])

    system = OurRagSystem(mock_pipeline)
    assert system.answer("A1", "question") == "our answer"
    mock_pipeline.answer.assert_called_once_with("question")


def test_systems_have_name_attribute():
    """Each system exposes a `name` attribute used by the benchmark runner
    to build the label mapping in Task 4.2."""
    mock_client = MagicMock()
    mock_pipeline = MagicMock()

    assert OurRagSystem(mock_pipeline).name == "our_rag"
    assert MistralRawSystem(mock_client).name == "mistral_raw"
    # ChatGPTRecordedSystem needs a real JSON file so use a tmp file
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump({"_metadata": {}}, f)
        path = f.name
    assert ChatGPTRecordedSystem(path).name == "chatgpt_recorded"
