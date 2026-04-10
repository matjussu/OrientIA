"""Run the Claude judge on the blinded benchmark responses.

DO NOT RUN until src/eval/run_real.py has produced
results/raw_responses/responses_blind.json.

Usage:
    python -m src.eval.run_judge

Outputs:
    results/scores/blind_scores.json
"""
import json
from pathlib import Path
from anthropic import Anthropic
from src.config import load_config
from src.eval.judge import judge_all


BLIND_RESPONSES_PATH = "results/raw_responses/responses_blind.json"
OUT_PATH = "results/scores/blind_scores.json"


def main():
    if not Path(BLIND_RESPONSES_PATH).exists():
        raise RuntimeError(
            f"Expected {BLIND_RESPONSES_PATH} but it doesn't exist. "
            f"Run `python -m src.eval.run_real` first."
        )

    cfg = load_config()
    client = Anthropic(api_key=cfg.anthropic_api_key)

    responses = json.loads(Path(BLIND_RESPONSES_PATH).read_text(encoding="utf-8"))
    print(f"Judging {len(responses)} questions with Claude Sonnet 4.5...")
    print(f"(This costs ~{len(responses) * 0.01:.2f}$ in Anthropic credits)")
    scores = judge_all(client, responses)

    Path(OUT_PATH).parent.mkdir(parents=True, exist_ok=True)
    Path(OUT_PATH).write_text(
        json.dumps(scores, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Saved to {OUT_PATH}")


if __name__ == "__main__":
    main()
