"""Run F — multi-judge orchestration (Claude Sonnet + GPT-4o).

Reads a blinded responses file produced by run_real_full and judges
each question with BOTH judges. Each judge sees the exact same prompt
and the exact same anonymised answer blocks (per-question A-G label
shuffle is preserved from the responses file), so disagreement is
attributable to judge variance, not input variance.

Outputs:
  <out_dir>/scores_claude.json   — Claude Sonnet 4.5 scores
  <out_dir>/scores_gpt4o.json    — GPT-4o scores

Usage:
  python -m src.eval.run_judge_multi
  python -m src.eval.run_judge_multi --responses results/run_F_robust/responses_blind.json
  python -m src.eval.run_judge_multi --judges claude  # single-judge subset
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from anthropic import Anthropic

from src.config import load_config
from src.eval.judge import judge_all
from src.eval.judge_openai import judge_all_openai
from src.eval.rate_limit import RateLimiter


# Same RPM cap as run_real_full so a tier-1 OpenAI key never sees a 429.
OPENAI_JUDGE_RPM = 12


DEFAULT_RESPONSES = "results/raw_responses_F/responses_blind.json"
DEFAULT_OUT_DIR = "results/raw_responses_F"


def _run_claude(responses: list[dict], out_path: Path, api_key: str) -> None:
    print(f"  Claude Sonnet 4.5: judging {len(responses)} questions...")
    client = Anthropic(api_key=api_key, timeout=120.0)
    scores = judge_all(client, responses)
    out_path.write_text(
        json.dumps(scores, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  → wrote {out_path}")


def _run_gpt4o(responses: list[dict], out_path: Path, api_key: str) -> None:
    from openai import OpenAI
    print(f"  GPT-4o: judging {len(responses)} questions (≤{OPENAI_JUDGE_RPM} RPM)...")
    client = OpenAI(api_key=api_key, timeout=120.0)
    limiter = RateLimiter(max_per_minute=OPENAI_JUDGE_RPM)
    scores = judge_all_openai(client, responses, rate_limiter=limiter)
    out_path.write_text(
        json.dumps(scores, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  → wrote {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--responses", default=DEFAULT_RESPONSES)
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument(
        "--judges", default="claude,gpt4o",
        help="Comma-separated subset of {claude, gpt4o}. Default: both."
    )
    args = parser.parse_args()

    responses_path = Path(args.responses)
    if not responses_path.exists():
        raise RuntimeError(
            f"Missing {responses_path} — run_real_full must run first."
        )

    cfg = load_config()
    judges = {j.strip() for j in args.judges.split(",") if j.strip()}
    if "gpt4o" in judges and not cfg.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY missing — cannot run GPT-4o judge.")

    responses = json.loads(responses_path.read_text(encoding="utf-8"))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    n = len(responses)
    n_labels = len(responses[0]["answers"]) if responses else 0
    print(f"Judging {n} questions × {n_labels} labels with: {sorted(judges)}")
    print(
        f"Estimated cost: "
        f"Claude ~${n * 0.012 * (n_labels/3):.2f}, "
        f"GPT-4o ~${n * 0.020 * (n_labels/3):.2f}"
    )

    if "claude" in judges:
        _run_claude(responses, out_dir / "scores_claude.json", cfg.anthropic_api_key)
    if "gpt4o" in judges:
        _run_gpt4o(responses, out_dir / "scores_gpt4o.json", cfg.openai_api_key)
    print("Done.")


if __name__ == "__main__":
    main()
