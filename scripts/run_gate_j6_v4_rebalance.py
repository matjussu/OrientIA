"""Gate J+6 V4.1 — re-run UNIQUEMENT les 3 Q hard avec system prompt rééquilibré.

Output : `results/gate_j6/responses_validator_v4_rebalance_active.json`
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from mistralai.client import Mistral

from src.config import load_config
from src.rag.pipeline import OrientIAPipeline
from src.rag.reranker import RerankConfig
from src.validator import Validator, Layer3Validator


PACK_V2_PATH = Path("results/user_test_v2/responses.json")
OUT_PATH = Path("results/gate_j6/responses_validator_v4_rebalance_active.json")
INDEX_PATH = "data/embeddings/formations.index"
CORPUS_PATH = "data/processed/formations.json"
HARD_QUESTIONS = {1, 6, 8}


def main() -> None:
    config = load_config()
    corpus = json.loads(Path(CORPUS_PATH).read_text(encoding="utf-8"))
    client = Mistral(api_key=config.mistral_api_key, timeout_ms=120000)

    layer3 = Layer3Validator(client=client, model="mistral-small-latest")
    try:
        client.chat.complete(
            model="mistral-small-latest",
            max_tokens=5,
            messages=[{"role": "user", "content": "ok"}],
        )
    except Exception:
        layer3 = None

    validator = Validator(fiches=corpus, layer3=layer3)
    pipeline = OrientIAPipeline(
        client=client, fiches=corpus,
        rerank_config=RerankConfig(),
        model="mistral-medium-latest",
        use_mmr=True, use_intent=True,
        validator=validator,
    )
    pipeline.load_index_from(INDEX_PATH)

    pack = json.loads(PACK_V2_PATH.read_text(encoding="utf-8"))
    hard = [entry for entry in pack if entry["question_num"] in HARD_QUESTIONS]
    results = []
    for entry in hard:
        q_num = entry["question_num"]
        q = entry["question"]
        cat = entry["category"]
        print(f"--- Q{q_num} [{cat}]")
        t0 = time.perf_counter()
        try:
            final, _ = pipeline.answer(q)
            val = pipeline.last_validation
            pol = pipeline.last_policy_result
            elapsed = time.perf_counter() - t0
            results.append({
                "question_num": q_num, "category": cat, "question": q,
                "new_answer_rebalance_v4": final,
                "word_count": len(final.split()),
                "validation": {
                    "honesty_score": round(val.honesty_score, 3) if val else None,
                    "rule_violations_count": len(val.rule_violations) if val else 0,
                    "layer3_warnings_count": len(val.layer3_warnings) if val else 0,
                    "presence_warnings_count": len(val.presence_warnings) if val else 0,
                },
                "policy": {"policy": pol.policy.value if pol else "none"},
                "latency_s": round(elapsed, 2),
            })
            print(f"  honesty={val.honesty_score:.2f} policy={pol.policy.value} words={len(final.split())} ({elapsed:.0f}s)")
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {e}")
            results.append({"question_num": q_num, "error": f"{type(e).__name__}: {e}"})
        OUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(results)} to {OUT_PATH}")


if __name__ == "__main__":
    main()
