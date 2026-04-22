"""Gate J+6 v3 — re-run pack v2 avec Validator V2 (rules+layer3) + Policy V3
(footer β Warn limité à top 2 warnings max, priority ordering).

Identique à `run_gate_j6_v2.py` — l'implémentation V3 est dans
`src/validator/policy.py:_format_warn_footer` qui limite maintenant le
footer. Le Validator détecte exactement les mêmes choses qu'en V2 ; seul
l'affichage change.

Output : `results/gate_j6/responses_validator_v3_active.json`
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
OUT_PATH = Path("results/gate_j6/responses_validator_v3_active.json")
INDEX_PATH = "data/embeddings/formations.index"
CORPUS_PATH = "data/processed/formations.json"


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
        print("Layer3 (Mistral Small) OK")
    except Exception as e:
        print(f"Layer3 fail : {type(e).__name__} → désactivée")
        layer3 = None

    validator = Validator(fiches=corpus, layer3=layer3)
    pipeline = OrientIAPipeline(
        client=client,
        fiches=corpus,
        rerank_config=RerankConfig(),
        model="mistral-medium-latest",
        use_mmr=True,
        use_intent=True,
        validator=validator,
    )
    pipeline.load_index_from(INDEX_PATH)

    pack = json.loads(PACK_V2_PATH.read_text(encoding="utf-8"))
    results = []
    for entry in pack:
        q_num = entry["question_num"]
        question = entry["question"]
        print(f"--- Q{q_num} [{entry['category']}]")
        t0 = time.perf_counter()
        try:
            final_answer, _ = pipeline.answer(question)
            val = pipeline.last_validation
            pol = pipeline.last_policy_result
            elapsed = time.perf_counter() - t0

            # Compte les items visibles dans le footer (pour stats v3)
            footer_items_visible = 0
            if pol and pol.policy.value == "warn":
                footer = final_answer.split("Points à vérifier", 1)
                if len(footer) > 1:
                    footer_items_visible = sum(
                        1 for line in footer[1].splitlines()
                        if line.startswith("- ") and "autre point" not in line.lower()
                    )

            results.append({
                "question_num": q_num,
                "category": entry["category"],
                "question": question,
                "original_answer_v2": entry.get("answer", ""),
                "new_answer_with_policy_v3": final_answer,
                "pipeline_latency_s": round(elapsed, 2),
                "word_count_new": len(final_answer.split()),
                "validation": {
                    "honesty_score": round(val.honesty_score, 3) if val else None,
                    "flagged": val.flagged if val else False,
                    "rule_violations_count": len(val.rule_violations) if val else 0,
                    "corpus_warnings_count": len(val.corpus_warnings) if val else 0,
                    "layer3_warnings_count": len(val.layer3_warnings) if val else 0,
                    "rule_violations": [
                        {"rule_id": v.rule_id, "severity": v.severity.value}
                        for v in (val.rule_violations if val else [])
                    ],
                },
                "policy": {
                    "policy": pol.policy.value if pol else "none",
                    "footer_items_visible": footer_items_visible,
                },
            })
            print(
                f"  honesty={val.honesty_score:.2f} policy={pol.policy.value} "
                f"rules={len(val.rule_violations)} corpus={len(val.corpus_warnings)} "
                f"layer3={len(val.layer3_warnings)} footer_visible={footer_items_visible} ({elapsed:.0f}s)"
            )
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {e}")
            results.append({"question_num": q_num, "error": f"{type(e).__name__}: {e}"})

    OUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved {len(results)} to {OUT_PATH}")


if __name__ == "__main__":
    main()
