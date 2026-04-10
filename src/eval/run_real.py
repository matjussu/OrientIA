"""Run the full benchmark on the 32 questions × 3 systems.

DO NOT RUN until data/chatgpt_recorded.json has been manually filled in.
Running with empty ChatGPT responses will produce useless output.

Usage:
    python -m src.eval.run_real

Outputs:
    results/raw_responses/responses_blind.json
    results/raw_responses/label_mapping.json
    results/raw_responses/seed.txt
"""
import json
from pathlib import Path
from mistralai.client import Mistral
from src.config import load_config
from src.rag.pipeline import OrientIAPipeline
from src.eval.systems import OurRagSystem, MistralRawSystem, ChatGPTRecordedSystem
from src.eval.runner import run_benchmark


FICHES_PATH = "data/processed/formations.json"
INDEX_PATH = "data/embeddings/formations.index"
CHATGPT_PATH = "data/chatgpt_recorded.json"
QUESTIONS_PATH = "src/eval/questions.json"
OUT_DIR = "results/raw_responses"


def _validate_chatgpt_stub(path: str) -> None:
    """Refuse to run if the ChatGPT stub still has empty strings."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    empty = [k for k, v in data.items() if k != "_metadata" and not v]
    if empty:
        raise RuntimeError(
            f"data/chatgpt_recorded.json has {len(empty)} unfilled entries: "
            f"{empty[:5]}... Fill in manually from chat.openai.com before running."
        )


def main():
    _validate_chatgpt_stub(CHATGPT_PATH)

    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key)

    fiches = json.loads(Path(FICHES_PATH).read_text(encoding="utf-8"))
    pipeline = OrientIAPipeline(client, fiches)

    if Path(INDEX_PATH).exists():
        print(f"Loading cached index from {INDEX_PATH}...")
        pipeline.load_index_from(INDEX_PATH)
    else:
        print(f"Building index for {len(fiches)} fiches...")
        pipeline.build_index()
        pipeline.save_index_to(INDEX_PATH)

    systems = {
        "our_rag": OurRagSystem(pipeline),
        "mistral_raw": MistralRawSystem(client),
        "chatgpt_recorded": ChatGPTRecordedSystem(CHATGPT_PATH),
    }

    questions = json.loads(Path(QUESTIONS_PATH).read_text(encoding="utf-8"))["questions"]
    print(f"Running benchmark on {len(questions)} questions × {len(systems)} systems...")
    print(f"(This calls Mistral ~{len(questions) * 2} times for our_rag + mistral_raw)")
    run_benchmark(questions, systems, OUT_DIR, seed=42)
    print(f"Done. Saved to {OUT_DIR}/")


if __name__ == "__main__":
    main()
