"""Phase F.4 — GPT-4o judge wrapper.

Same JUDGE_PROMPT as the Claude judge (judge.py), same input/output
contract, but routed through the OpenAI chat.completions API. This
gives Run F two independent judges so we can compute inter-judge
agreement (Cohen's κ) and detect single-judge bias.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock

from src.eval.judge_openai import judge_question_openai, judge_all_openai


def _make_openai_response(content: str) -> MagicMock:
    """Build a mock OpenAI chat.completions response shape."""
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def test_openai_judge_parses_json_response():
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_openai_response(
        json.dumps({
            "A": {"neutralite": 2, "realisme": 3, "sourcage": 2,
                  "diversite_geo": 1, "agentivite": 2, "decouverte": 1,
                  "total": 11, "justification": "ok"},
            "B": {"neutralite": 3, "realisme": 3, "sourcage": 3,
                  "diversite_geo": 3, "agentivite": 3, "decouverte": 3,
                  "total": 18, "justification": "perfect"},
        })
    )
    scores = judge_question_openai(
        mock_client,
        question="test?",
        answers={"A": "answer a", "B": "answer b"},
    )
    assert scores["A"]["total"] == 11
    assert scores["B"]["total"] == 18


def test_openai_judge_handles_seven_answers():
    """Same N-generic contract as the Claude judge — must scale to 7."""
    seven_scores = {
        label: {"neutralite": 2, "realisme": 2, "sourcage": 2,
                "diversite_geo": 2, "agentivite": 2, "decouverte": 2,
                "total": 12, "justification": "ok"}
        for label in ["A", "B", "C", "D", "E", "F", "G"]
    }
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_openai_response(
        json.dumps(seven_scores)
    )
    answers = {l: f"answer {l}" for l in ["A", "B", "C", "D", "E", "F", "G"]}
    scores = judge_question_openai(mock_client, "q?", answers)
    assert set(scores.keys()) == set(answers)
    assert all(v["total"] == 12 for v in scores.values())


def test_openai_judge_uses_gpt4o_by_default():
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_openai_response(
        '{"A": {"neutralite": 0, "realisme": 0, "sourcage": 0, '
        '"diversite_geo": 0, "agentivite": 0, "decouverte": 0, '
        '"total": 0, "justification": ""}, '
        '"B": {"neutralite": 0, "realisme": 0, "sourcage": 0, '
        '"diversite_geo": 0, "agentivite": 0, "decouverte": 0, '
        '"total": 0, "justification": ""}}'
    )
    judge_question_openai(mock_client, "q?", {"A": "x", "B": "y"})
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "gpt-4o"


def test_openai_judge_passes_system_and_user_message():
    """The judge prompt must be sent as a system message; the question
    + answer blocks must be sent as a user message (mirrors Claude path)."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_openai_response(
        '{"A": {"neutralite": 0, "realisme": 0, "sourcage": 0, '
        '"diversite_geo": 0, "agentivite": 0, "decouverte": 0, '
        '"total": 0, "justification": ""}, '
        '"B": {"neutralite": 0, "realisme": 0, "sourcage": 0, '
        '"diversite_geo": 0, "agentivite": 0, "decouverte": 0, '
        '"total": 0, "justification": ""}}'
    )
    judge_question_openai(mock_client, "What?", {"A": "answer a", "B": "answer b"})
    msgs = mock_client.chat.completions.create.call_args.kwargs["messages"]
    roles = [m["role"] for m in msgs]
    assert roles == ["system", "user"]
    assert "RÉPONSE A" in msgs[1]["content"]
    assert "answer a" in msgs[1]["content"]


def test_judge_all_openai_iterates_responses():
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_openai_response(
        json.dumps({
            "A": {"neutralite": 1, "realisme": 1, "sourcage": 1,
                  "diversite_geo": 1, "agentivite": 1, "decouverte": 1,
                  "total": 6, "justification": ""},
            "B": {"neutralite": 1, "realisme": 1, "sourcage": 1,
                  "diversite_geo": 1, "agentivite": 1, "decouverte": 1,
                  "total": 6, "justification": ""},
            "C": {"neutralite": 1, "realisme": 1, "sourcage": 1,
                  "diversite_geo": 1, "agentivite": 1, "decouverte": 1,
                  "total": 6, "justification": ""},
        })
    )
    responses_blind = [
        {"id": "Q1", "category": "biais_marketing", "text": "q1",
         "answers": {"A": "x", "B": "y", "C": "z"}},
        {"id": "Q2", "category": "realisme", "text": "q2",
         "answers": {"A": "x", "B": "y", "C": "z"}},
    ]
    results = judge_all_openai(mock_client, responses_blind)
    assert len(results) == 2
    assert results[0]["id"] == "Q1"
    assert results[1]["id"] == "Q2"
    assert mock_client.chat.completions.create.call_count == 2
