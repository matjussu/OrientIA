"""GPT-4o judge — same rubric and contract as the Claude judge.

Reuses JUDGE_PROMPT and the message-building helpers from judge.py
to guarantee both judges see the *exact* same instructions and the
*exact* same anonymised answer blocks. Only the underlying API
client differs. This makes inter-judge agreement (Cohen's κ) a clean
measurement of judge variance, not prompt variance.
"""
from __future__ import annotations

import json
from pathlib import Path

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
    rate_limiter=None,
) -> dict:
    """Score N answers in a single GPT-4o call. Generic over N.

    rate_limiter: optional RateLimiter — caller passes one to keep
    judge calls under the OpenAI tier-1 RPM cap (15 for gpt-4o)."""
    if rate_limiter is not None:
        rate_limiter.acquire()
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
    rate_limiter=None,
    save_path: str | Path | None = None,
) -> list[dict]:
    """Iterate over the blinded responses and produce one score dict
    per question. Mirrors judge.judge_all() exactly so downstream
    aggregation code is judge-agnostic.

    If save_path is given, the full accumulated list is atomically
    rewritten after EACH question so killing the process mid-run
    never loses already-paid-for scores. Also enables resume : if
    save_path exists, its entries skip the judge call.
    """
    done_ids: set[str] = set()
    all_scores: list[dict] = []
    if save_path is not None:
        save_path = Path(save_path)
        if save_path.exists():
            try:
                existing = json.loads(save_path.read_text(encoding="utf-8"))
                if isinstance(existing, list):
                    all_scores = existing
                    done_ids = {e["id"] for e in existing}
                    print(f"  Resuming: {len(done_ids)} already judged, skipping them.")
            except Exception as exc:
                print(f"  (could not parse existing {save_path}: {exc} — starting fresh)")

    for entry in responses_blind:
        if entry["id"] in done_ids:
            continue
        scores = judge_question_openai(
            client, entry["text"], entry["answers"], model=model,
            rate_limiter=rate_limiter,
        )
        all_scores.append({
            "id": entry["id"],
            "category": entry["category"],
            "scores": scores,
        })
        if save_path is not None:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_text(
                json.dumps(all_scores, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
    return all_scores
