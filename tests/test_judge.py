import json
from unittest.mock import MagicMock
from src.eval.judge import judge_question, judge_all, JUDGE_PROMPT


def test_judge_prompt_defines_six_criteria():
    for crit in ["neutralite", "realisme", "sourcage", "diversite_geo", "agentivite", "decouverte"]:
        assert crit in JUDGE_PROMPT.lower() or crit.replace("_", " ") in JUDGE_PROMPT.lower()


def test_judge_prompt_forbids_system_identification():
    """The judge must be told explicitly that labels are anonymized
    and it should not try to guess which system produced which answer."""
    assert "deviner" in JUDGE_PROMPT.lower() or "anonymis" in JUDGE_PROMPT.lower() or "identifier" in JUDGE_PROMPT.lower()


def test_judge_prompt_specifies_json_output():
    assert "JSON" in JUDGE_PROMPT or "json" in JUDGE_PROMPT


def test_judge_question_parses_json_response():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps({
        "A": {"neutralite": 2, "realisme": 3, "sourcage": 2, "diversite_geo": 1,
              "agentivite": 2, "decouverte": 1, "total": 11, "justification": "ok"},
        "B": {"neutralite": 1, "realisme": 1, "sourcage": 0, "diversite_geo": 1,
              "agentivite": 2, "decouverte": 1, "total": 6, "justification": "weak"},
        "C": {"neutralite": 3, "realisme": 3, "sourcage": 3, "diversite_geo": 2,
              "agentivite": 3, "decouverte": 2, "total": 16, "justification": "strong"},
    }))]
    mock_client.messages.create.return_value = mock_response

    scores = judge_question(
        mock_client,
        question="test?",
        answers={"A": "answer a", "B": "answer b", "C": "answer c"},
    )
    assert scores["A"]["total"] == 11
    assert scores["B"]["total"] == 6
    assert scores["C"]["total"] == 16


def test_judge_question_handles_json_wrapped_in_text():
    """Some LLMs prepend explanatory text before the JSON block.
    The judge must extract the JSON portion robustly."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    fake_output = (
        "Here is my evaluation:\n\n"
        + json.dumps({
            "A": {"neutralite": 2, "realisme": 2, "sourcage": 2, "diversite_geo": 2,
                  "agentivite": 2, "decouverte": 2, "total": 12, "justification": "ok"},
            "B": {"neutralite": 1, "realisme": 1, "sourcage": 1, "diversite_geo": 1,
                  "agentivite": 1, "decouverte": 1, "total": 6, "justification": "meh"},
            "C": {"neutralite": 3, "realisme": 3, "sourcage": 3, "diversite_geo": 3,
                  "agentivite": 3, "decouverte": 3, "total": 18, "justification": "perfect"},
        })
        + "\n\nHope this helps!"
    )
    mock_response.content = [MagicMock(text=fake_output)]
    mock_client.messages.create.return_value = mock_response

    scores = judge_question(
        mock_client,
        question="test?",
        answers={"A": "a", "B": "b", "C": "c"},
    )
    assert scores["A"]["total"] == 12
    assert scores["C"]["total"] == 18


def test_judge_question_raises_on_missing_json():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="I cannot evaluate this.")]
    mock_client.messages.create.return_value = mock_response

    import pytest
    with pytest.raises(ValueError, match="No JSON"):
        judge_question(
            mock_client,
            question="test?",
            answers={"A": "a", "B": "b", "C": "c"},
        )


def test_judge_all_iterates_responses():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps({
        "A": {"neutralite": 1, "realisme": 1, "sourcage": 1, "diversite_geo": 1,
              "agentivite": 1, "decouverte": 1, "total": 6, "justification": ""},
        "B": {"neutralite": 1, "realisme": 1, "sourcage": 1, "diversite_geo": 1,
              "agentivite": 1, "decouverte": 1, "total": 6, "justification": ""},
        "C": {"neutralite": 1, "realisme": 1, "sourcage": 1, "diversite_geo": 1,
              "agentivite": 1, "decouverte": 1, "total": 6, "justification": ""},
    }))]
    mock_client.messages.create.return_value = mock_response

    responses_blind = [
        {"id": "A1", "category": "biais_marketing", "text": "q1",
         "answers": {"A": "x", "B": "y", "C": "z"}},
        {"id": "B1", "category": "realisme", "text": "q2",
         "answers": {"A": "x", "B": "y", "C": "z"}},
    ]

    results = judge_all(mock_client, responses_blind)
    assert len(results) == 2
    assert results[0]["id"] == "A1"
    assert results[0]["category"] == "biais_marketing"
    assert "scores" in results[0]
    assert mock_client.messages.create.call_count == 2


# --- Phase F.2 — judge generalization for N answers (Run F: N=7) ---


def test_judge_question_handles_seven_answers():
    """Phase F.2 — same judge prompt now scores 7 anonymized answers
    in a single call, using labels A through G. Keeps the per-question
    blinded design (judge sees random label order)."""
    mock_client = MagicMock()
    seven_scores = {
        label: {"neutralite": i + 1 if i < 3 else 2, "realisme": 2,
                "sourcage": 2, "diversite_geo": 2, "agentivite": 2,
                "decouverte": 2, "total": 12, "justification": "ok"}
        for i, label in enumerate(["A", "B", "C", "D", "E", "F", "G"])
    }
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps(seven_scores))]
    mock_client.messages.create.return_value = mock_response

    answers = {label: f"answer {label}"
               for label in ["A", "B", "C", "D", "E", "F", "G"]}
    scores = judge_question(mock_client, "test?", answers)

    assert set(scores.keys()) == set(answers.keys())
    for label in answers:
        assert scores[label]["total"] == 12


def test_judge_question_includes_all_labels_in_user_message():
    """The user message must contain a 'RÉPONSE X' block for each
    of the N labels passed in. Generic over N."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"A": {"neutralite": 0, "realisme": 0, "sourcage": 0, "diversite_geo": 0, "agentivite": 0, "decouverte": 0, "total": 0, "justification": ""}, "B": {"neutralite": 0, "realisme": 0, "sourcage": 0, "diversite_geo": 0, "agentivite": 0, "decouverte": 0, "total": 0, "justification": ""}, "C": {"neutralite": 0, "realisme": 0, "sourcage": 0, "diversite_geo": 0, "agentivite": 0, "decouverte": 0, "total": 0, "justification": ""}, "D": {"neutralite": 0, "realisme": 0, "sourcage": 0, "diversite_geo": 0, "agentivite": 0, "decouverte": 0, "total": 0, "justification": ""}, "E": {"neutralite": 0, "realisme": 0, "sourcage": 0, "diversite_geo": 0, "agentivite": 0, "decouverte": 0, "total": 0, "justification": ""}, "F": {"neutralite": 0, "realisme": 0, "sourcage": 0, "diversite_geo": 0, "agentivite": 0, "decouverte": 0, "total": 0, "justification": ""}, "G": {"neutralite": 0, "realisme": 0, "sourcage": 0, "diversite_geo": 0, "agentivite": 0, "decouverte": 0, "total": 0, "justification": ""}}')]
    mock_client.messages.create.return_value = mock_response

    answers = {label: f"my distinctive answer {label}"
               for label in ["A", "B", "C", "D", "E", "F", "G"]}
    judge_question(mock_client, "test?", answers)

    user_content = mock_client.messages.create.call_args.kwargs[
        "messages"
    ][0]["content"]
    for label in answers:
        assert f"RÉPONSE {label}" in user_content
        assert f"my distinctive answer {label}" in user_content


def test_judge_question_max_tokens_scales_with_n():
    """Larger N needs more output room. Default scales linearly so
    a 7-system call doesn't get truncated mid-JSON."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"A": {"neutralite": 1, "realisme": 1, "sourcage": 1, "diversite_geo": 1, "agentivite": 1, "decouverte": 1, "total": 6, "justification": "x"}, "B": {"neutralite": 1, "realisme": 1, "sourcage": 1, "diversite_geo": 1, "agentivite": 1, "decouverte": 1, "total": 6, "justification": "x"}, "C": {"neutralite": 1, "realisme": 1, "sourcage": 1, "diversite_geo": 1, "agentivite": 1, "decouverte": 1, "total": 6, "justification": "x"}, "D": {"neutralite": 1, "realisme": 1, "sourcage": 1, "diversite_geo": 1, "agentivite": 1, "decouverte": 1, "total": 6, "justification": "x"}, "E": {"neutralite": 1, "realisme": 1, "sourcage": 1, "diversite_geo": 1, "agentivite": 1, "decouverte": 1, "total": 6, "justification": "x"}, "F": {"neutralite": 1, "realisme": 1, "sourcage": 1, "diversite_geo": 1, "agentivite": 1, "decouverte": 1, "total": 6, "justification": "x"}, "G": {"neutralite": 1, "realisme": 1, "sourcage": 1, "diversite_geo": 1, "agentivite": 1, "decouverte": 1, "total": 6, "justification": "x"}}')]
    mock_client.messages.create.return_value = mock_response

    # 7 answers
    answers = {label: "x" for label in ["A", "B", "C", "D", "E", "F", "G"]}
    judge_question(mock_client, "q?", answers)
    max_tokens_7 = mock_client.messages.create.call_args.kwargs["max_tokens"]

    # Reset mock and try with 3 answers
    mock_client.reset_mock()
    mock_response.content = [MagicMock(text='{"A": {"neutralite": 1, "realisme": 1, "sourcage": 1, "diversite_geo": 1, "agentivite": 1, "decouverte": 1, "total": 6, "justification": "x"}, "B": {"neutralite": 1, "realisme": 1, "sourcage": 1, "diversite_geo": 1, "agentivite": 1, "decouverte": 1, "total": 6, "justification": "x"}, "C": {"neutralite": 1, "realisme": 1, "sourcage": 1, "diversite_geo": 1, "agentivite": 1, "decouverte": 1, "total": 6, "justification": "x"}}')]
    mock_client.messages.create.return_value = mock_response
    judge_question(mock_client, "q?", {label: "x" for label in ["A", "B", "C"]})
    max_tokens_3 = mock_client.messages.create.call_args.kwargs["max_tokens"]

    # 7 should request more output space than 3
    assert max_tokens_7 > max_tokens_3
