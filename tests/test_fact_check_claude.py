"""Tests for src/eval/fact_check_claude.py — Claude-powered fact-check.

Claude Haiku 4.5 replaces the regex-based fact_check.py for all
factuality checking. It handles:
  * real schools outside the fiches (e.g. "INSA Lyon") → verified
  * fabricated reports ("rapport ANSSI 2023") → contradicted
  * plausible-but-unchecked claims → unverifiable
  * consistency between a number and its entity (47% at Rennes)

The actual Anthropic API is mocked in tests — we only validate the
prompt construction, JSON parsing, and score aggregation.
"""
from unittest.mock import MagicMock
from src.eval.fact_check_claude import (
    build_fact_check_prompt,
    parse_fact_check_response,
    claude_fact_check_score,
    ClaimStatus,
)


def test_build_prompt_includes_answer_and_fiches():
    answer = "EPITA propose un master cyber. Taux 18%."
    retrieved = [{"fiche": {"nom": "Master Cyber", "etablissement": "EPITA",
                            "ville": "Paris", "taux_acces_parcoursup_2025": 18.0}}]
    prompt = build_fact_check_prompt(answer, retrieved)
    assert "EPITA" in prompt
    assert "Master Cyber" in prompt
    assert "18" in prompt
    # Must ask for JSON output
    assert "json" in prompt.lower()


def test_system_prompt_declares_four_statuses_and_report_rigor():
    """The rubric lives in FACT_CHECK_SYSTEM_PROMPT (the Claude system
    message). All four statuses must be explicitly named there, plus
    the rule that hallucinated reports count as contradicted."""
    from src.eval.fact_check_claude import FACT_CHECK_SYSTEM_PROMPT
    assert "verified_fiche" in FACT_CHECK_SYSTEM_PROMPT
    assert "verified_general" in FACT_CHECK_SYSTEM_PROMPT
    assert "unverifiable" in FACT_CHECK_SYSTEM_PROMPT
    assert "contradicted" in FACT_CHECK_SYSTEM_PROMPT
    # Rigor rule on fabricated reports (the whole point of the judge v2)
    low = FACT_CHECK_SYSTEM_PROMPT.lower()
    assert "rapport" in low and "contradicted" in low


def test_build_prompt_empty_retrieved_for_baselines():
    """mistral_raw has no retrieved — prompt must still work."""
    prompt = build_fact_check_prompt("some answer", retrieved=[])
    assert "some answer" in prompt
    assert "aucune fiche" in prompt.lower() or "no fiches" in prompt.lower()


def test_parse_response_extracts_claims_list():
    text = '''{
  "claims": [
    {"text": "EPITA", "type": "school", "status": "verified_fiche", "reason": "in fiche"},
    {"text": "18%", "type": "percentage", "status": "verified_fiche", "reason": "matches taux"},
    {"text": "rapport ANSSI 2023", "type": "report", "status": "contradicted", "reason": "no such report"}
  ]
}'''
    parsed = parse_fact_check_response(text)
    assert len(parsed) == 3
    assert parsed[0]["status"] == ClaimStatus.VERIFIED_FICHE
    assert parsed[2]["status"] == ClaimStatus.CONTRADICTED


def test_parse_response_tolerates_preamble_and_wrapping():
    """Claude sometimes wraps JSON in ```json ... ``` or adds a preamble."""
    text = """Voici mon analyse:
```json
{
  "claims": [
    {"text": "ONISEP FOR.1234", "type": "other", "status": "verified_general", "reason": "real"}
  ]
}
```
Fin."""
    parsed = parse_fact_check_response(text)
    assert len(parsed) == 1
    assert parsed[0]["status"] == ClaimStatus.VERIFIED_GENERAL


def test_parse_response_handles_unknown_status_as_unverifiable():
    """Defensive: if Claude returns a status we don't recognize, treat
    it as unverifiable rather than crashing."""
    text = '{"claims": [{"text": "x", "type": "other", "status": "maybe", "reason": "idk"}]}'
    parsed = parse_fact_check_response(text)
    assert parsed[0]["status"] == ClaimStatus.UNVERIFIABLE


def test_claude_fact_check_score_all_verified_returns_one():
    mock_client = MagicMock()
    resp = MagicMock()
    resp.content = [MagicMock(text='''{
  "claims": [
    {"text": "EPITA", "type": "school", "status": "verified_fiche", "reason": "in fiche"},
    {"text": "ENS Rennes", "type": "school", "status": "verified_general", "reason": "real"}
  ]
}''')]
    mock_client.messages.create.return_value = resp

    retrieved = [{"fiche": {"etablissement": "EPITA"}}]
    score = claude_fact_check_score(
        mock_client, "EPITA et ENS Rennes.", retrieved=retrieved
    )
    assert score == 1.0


def test_claude_fact_check_score_mixed():
    """(verified_fiche + verified_general) / total; unverifiable and
    contradicted count against the ratio."""
    mock_client = MagicMock()
    resp = MagicMock()
    resp.content = [MagicMock(text='''{
  "claims": [
    {"text": "A", "type": "school", "status": "verified_fiche", "reason": ""},
    {"text": "B", "type": "school", "status": "verified_general", "reason": ""},
    {"text": "C", "type": "report", "status": "contradicted", "reason": ""},
    {"text": "D", "type": "percentage", "status": "unverifiable", "reason": ""}
  ]
}''')]
    mock_client.messages.create.return_value = resp
    score = claude_fact_check_score(mock_client, "...", retrieved=[])
    # 2 verified / 4 total = 0.5
    assert score == 0.5


def test_claude_fact_check_score_no_claims_returns_one():
    """Same neutral default as the regex version: answers without any
    factual claim aren't penalized."""
    mock_client = MagicMock()
    resp = MagicMock()
    resp.content = [MagicMock(text='{"claims": []}')]
    mock_client.messages.create.return_value = resp
    score = claude_fact_check_score(mock_client, "Il faut réfléchir.",
                                     retrieved=[])
    assert score == 1.0


def test_claude_fact_check_score_uses_haiku_by_default():
    """Default to Haiku 4.5 — it's 10× cheaper than Sonnet and sufficient
    for structured fact-check."""
    mock_client = MagicMock()
    resp = MagicMock()
    resp.content = [MagicMock(text='{"claims": []}')]
    mock_client.messages.create.return_value = resp
    claude_fact_check_score(mock_client, "x", retrieved=[])
    call = mock_client.messages.create.call_args
    model = call.kwargs.get("model") or (call.args[0] if call.args else "")
    assert "haiku" in model.lower()
