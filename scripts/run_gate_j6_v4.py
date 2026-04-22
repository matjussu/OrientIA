"""Gate J+6 V4 — re-run pack v2 avec Validator V4 (γ Modify + presence + phase projet).

Identique à run_gate_j6_v3.py — les changements V4 sont dans le Validator
et le pipeline (append_phase_projet).

Output : `results/gate_j6/responses_validator_v4_active.json`
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
OUT_PATH = Path("results/gate_j6/responses_validator_v4_active.json")
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
        client=client, fiches=corpus,
        rerank_config=RerankConfig(),
        model="mistral-medium-latest",
        use_mmr=True, use_intent=True,
        validator=validator,
    )
    pipeline.load_index_from(INDEX_PATH)

    pack = json.loads(PACK_V2_PATH.read_text(encoding="utf-8"))
    results = []
    for entry in pack:
        q_num = entry["question_num"]
        q = entry["question"]
        cat = entry["category"]
        print(f"--- Q{q_num} [{cat}]")
        t0 = time.perf_counter()
        try:
            final_answer, _ = pipeline.answer(q)
            val = pipeline.last_validation
            pol = pipeline.last_policy_result
            elapsed = time.perf_counter() - t0

            phase_projet_appended = "Avant de décider" in final_answer[-1000:]

            results.append({
                "question_num": q_num,
                "category": cat,
                "question": q,
                "original_answer_v2": entry.get("answer", ""),
                "new_answer_with_policy_v4": final_answer,
                "pipeline_latency_s": round(elapsed, 2),
                "word_count_new": len(final_answer.split()),
                "validation": {
                    "honesty_score": round(val.honesty_score, 3) if val else None,
                    "flagged": val.flagged if val else False,
                    "rule_violations_count": len(val.rule_violations) if val else 0,
                    "corpus_warnings_count": len(val.corpus_warnings) if val else 0,
                    "layer3_warnings_count": len(val.layer3_warnings) if val else 0,
                    "presence_warnings_count": len(val.presence_warnings) if val else 0,
                    "rule_violations": [
                        {"rule_id": v.rule_id, "severity": v.severity.value, "matched_text": v.matched_text}
                        for v in (val.rule_violations if val else [])
                    ],
                    "presence_warnings": [
                        {"topic": pw.topic, "label": pw.missing_pattern_label}
                        for pw in (val.presence_warnings if val else [])
                    ],
                },
                "policy": {
                    "policy": pol.policy.value if pol else "none",
                    "phase_projet_appended": phase_projet_appended,
                },
            })
            print(
                f"  honesty={val.honesty_score:.2f} policy={pol.policy.value} "
                f"rules={len(val.rule_violations)} presence={len(val.presence_warnings)} "
                f"layer3={len(val.layer3_warnings)} phase_projet={phase_projet_appended} ({elapsed:.0f}s)"
            )
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {e}")
            results.append({"question_num": q_num, "error": f"{type(e).__name__}: {e}"})

    OUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved {len(results)} to {OUT_PATH}")

    success = [r for r in results if r.get("new_answer_with_policy_v4")]
    if success:
        dist = {"pass": 0, "warn": 0, "modify": 0, "block": 0, "none": 0}
        for r in success:
            dist[r["policy"]["policy"]] = dist.get(r["policy"]["policy"], 0) + 1
        avg_honesty = sum(r["validation"]["honesty_score"] for r in success) / len(success)
        modify_count = dist.get("modify", 0)
        print(f"\n=== V4 SUMMARY ===")
        print(f"Réponses : {len(success)}/{len(pack)}")
        print(f"Policy : {dist}")
        print(f"Honesty moyen : {avg_honesty:.2f}")
        print(f"γ Modify appliqué sur {modify_count} questions")


if __name__ == "__main__":
    main()
