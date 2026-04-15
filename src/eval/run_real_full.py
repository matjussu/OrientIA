"""Run F — 7-system benchmark with the full baseline matrix.

Built in Phase F.2. The 7 systems compared:
  1. our_rag                 — v3.2 prompt + RAG (full stack)
  2. mistral_neutral         — NEUTRAL prompt, no RAG
  3. mistral_v3_2_no_rag     — v3.2 prompt, no RAG (isolates RAG)
  4. gpt4o_neutral           — NEUTRAL prompt, no RAG
  5. gpt4o_v3_2_no_rag       — v3.2 prompt, no RAG
  6. claude_neutral          — NEUTRAL prompt, no RAG
  7. claude_v3_2_no_rag      — v3.2 prompt, no RAG

Usage:
  # Full Run F (~$15-20 generation + judge separately):
  python -m src.eval.run_real_full

  # Sample mode for cost validation (5 questions × 7 systems, ~$0.50):
  python -m src.eval.run_real_full --sample 5

Outputs:
  results/raw_responses_F/responses_blind.json  (100 q × 7 labels A-G)
  results/raw_responses_F/label_mapping.json
  results/raw_responses_F/seed.txt

Subsequent step: src.eval.run_judge consumes the same path and produces
the per-judge scores. Run F uses 2 judges (Claude Sonnet + GPT-4o).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from anthropic import Anthropic
from mistralai.client import Mistral

from src.config import load_config
from src.eval.systems import (
    OurRagSystem,
    MistralWithCustomPromptSystem,
    OpenAIBaseline,
    ClaudeBaseline,
    NEUTRAL_MISTRAL_PROMPT,
)
from src.prompt.system import SYSTEM_PROMPT  # = v3.2 (current)
from src.eval.runner import run_benchmark
from src.rag.pipeline import OrientIAPipeline


FICHES_PATH = "data/processed/formations.json"
INDEX_PATH = "data/embeddings/formations.index"
QUESTIONS_PATH = "src/eval/questions.json"
OUT_DIR = "results/raw_responses_F"


def make_seven_systems(
    cfg,
) -> dict:
    """Build the 7-system dict for Run F.

    Mistral and Anthropic clients are mandatory (we already use them).
    OpenAI client is required for the gpt4o_* baselines — refuse to
    build the dict if OPENAI_API_KEY is missing.
    """
    if not cfg.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY missing — cannot build the gpt4o_* baselines. "
            "Add it to .env to run the full 7-system matrix."
        )

    # Lazy import so the module stays import-safe in environments that
    # don't have openai installed (e.g., during pytest collection).
    from openai import OpenAI

    mistral_client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=120000)
    anthropic_client = Anthropic(api_key=cfg.anthropic_api_key, timeout=120.0)
    openai_client = OpenAI(api_key=cfg.openai_api_key, timeout=120.0)

    # Build our_rag pipeline with Phase F.3 method extensions enabled:
    #   - use_mmr=True       → diversifies top-k against near-duplicates
    #   - use_intent=True    → per-question top_k and λ via classify_intent
    fiches = json.loads(Path(FICHES_PATH).read_text(encoding="utf-8"))
    pipeline = OrientIAPipeline(
        mistral_client, fiches, use_mmr=True, use_intent=True,
    )
    if Path(INDEX_PATH).exists():
        print(f"Loading cached FAISS index from {INDEX_PATH}...")
        pipeline.load_index_from(INDEX_PATH)
    else:
        print(f"Building index for {len(fiches)} fiches...")
        pipeline.build_index()
        pipeline.save_index_to(INDEX_PATH)

    # Note: insertion order is preserved in dict — the runner shuffles
    # the labels per question, so the order here doesn't bias anything.
    return {
        "our_rag": OurRagSystem(pipeline),
        "mistral_neutral": MistralWithCustomPromptSystem(
            client=mistral_client,
            system_prompt=NEUTRAL_MISTRAL_PROMPT,
            name="mistral_neutral",
        ),
        "mistral_v3_2_no_rag": MistralWithCustomPromptSystem(
            client=mistral_client,
            system_prompt=SYSTEM_PROMPT,
            name="mistral_v3_2_no_rag",
        ),
        "gpt4o_neutral": OpenAIBaseline(
            client=openai_client,
            model="gpt-4o",
            system_prompt=NEUTRAL_MISTRAL_PROMPT,
            name="gpt4o_neutral",
        ),
        "gpt4o_v3_2_no_rag": OpenAIBaseline(
            client=openai_client,
            model="gpt-4o",
            system_prompt=SYSTEM_PROMPT,
            name="gpt4o_v3_2_no_rag",
        ),
        "claude_neutral": ClaudeBaseline(
            client=anthropic_client,
            model="claude-sonnet-4-5",
            system_prompt=NEUTRAL_MISTRAL_PROMPT,
            name="claude_neutral",
        ),
        "claude_v3_2_no_rag": ClaudeBaseline(
            client=anthropic_client,
            model="claude-sonnet-4-5",
            system_prompt=SYSTEM_PROMPT,
            name="claude_v3_2_no_rag",
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sample",
        type=int,
        default=0,
        help="If > 0, only run on the first N questions (cost validation).",
    )
    parser.add_argument(
        "--out-dir",
        default=OUT_DIR,
        help=f"Output directory (default: {OUT_DIR}).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="RNG seed for label shuffling (default: 42).",
    )
    args = parser.parse_args()

    cfg = load_config()
    systems = make_seven_systems(cfg)
    print(f"Built {len(systems)} systems: {list(systems.keys())}")

    questions = json.loads(Path(QUESTIONS_PATH).read_text(encoding="utf-8"))[
        "questions"
    ]
    if args.sample > 0:
        questions = questions[: args.sample]
        print(f"SAMPLE MODE — only first {len(questions)} questions")
    else:
        print(f"FULL MODE — all {len(questions)} questions")

    n_calls = len(questions) * len(systems)
    print(
        f"Will issue ~{n_calls} generation calls "
        f"({len(questions)} questions × {len(systems)} systems). "
        f"Mistral + OpenAI + Anthropic costs apply."
    )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    run_benchmark(questions, systems, out_dir, seed=args.seed)
    print(f"Done. Saved to {out_dir}/")


if __name__ == "__main__":
    main()
