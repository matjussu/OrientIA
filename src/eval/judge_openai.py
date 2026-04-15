"""GPT-4o judge — same rubric and contract as the Claude judge.

Reuses JUDGE_PROMPT and the message-building helpers from judge.py
to guarantee both judges see the *exact* same instructions and the
*exact* same anonymised answer blocks. Only the underlying API
client differs. This makes inter-judge agreement (Cohen's κ) a clean
measurement of judge variance, not prompt variance.
"""
from __future__ import annotations

from src.eval.judge import (
    JUDGE_PROMPT,
    _build_user_content,
    _extract_json,
    _max_tokens_for_n,
)


DEFAULT_OPENAI_JUDGE_MODEL = "gpt-4o"


def judge_question_openai(
    client,
    question: str,
    answers: dict[str, str],
    model: str = DEFAULT_OPENAI_JUDGE_MODEL,
) -> dict:
    """Score N answers in a single GPT-4o call. Generic over N."""
    user_content = _build_user_content(question, answers)
    response = client.chat.completions.create(
        model=model,
        max_tokens=_max_tokens_for_n(len(answers)),
        messages=[
            {"role": "system", "content": JUDGE_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )
    text = response.choices[0].message.content
    return _extract_json(text)


def judge_all_openai(
    client,
    responses_blind: list[dict],
    model: str = DEFAULT_OPENAI_JUDGE_MODEL,
) -> list[dict]:
    """Iterate over the blinded responses and produce one score dict
    per question. Mirrors judge.judge_all() exactly so downstream
    aggregation code is judge-agnostic."""
    all_scores = []
    for entry in responses_blind:
        scores = judge_question_openai(
            client, entry["text"], entry["answers"], model=model
        )
        all_scores.append({
            "id": entry["id"],
            "category": entry["category"],
            "scores": scores,
        })
    return all_scores
