"""Gate J+6 — re-run pack v2 avec Validator + UX Policy actifs.

Recharge les 10 questions de `results/user_test_v2/responses.json`, les
rejoue via `OrientIAPipeline(validator=...)` et sauvegarde les nouvelles
réponses + métadonnées Validator/Policy dans
`results/gate_j6/responses_validator_active.json`.

Pas de bench rubric ici — ce script produit juste les réponses à noter
par le triple-judge (cf `gate_j6_triple_judge.py`).

Usage :
    python scripts/run_gate_j6.py

Ne re-build PAS le FAISS index (coût Mistral ~$5-10 évité). Utilise
l'index `data/embeddings/formations.index` existant.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from mistralai.client import Mistral

from src.config import load_config
from src.rag.pipeline import OrientIAPipeline
from src.rag.reranker import RerankConfig
from src.validator import Validator


PACK_V2_PATH = Path("results/user_test_v2/responses.json")
OUT_DIR = Path("results/gate_j6")
OUT_PATH = OUT_DIR / "responses_validator_active.json"
INDEX_PATH = "data/embeddings/formations.index"
CORPUS_PATH = "data/processed/formations.json"


def main() -> None:
    # Sanity
    if not PACK_V2_PATH.exists():
        raise SystemExit(f"Pack v2 introuvable : {PACK_V2_PATH}")
    if not Path(INDEX_PATH).exists():
        raise SystemExit(
            f"FAISS index introuvable : {INDEX_PATH}. "
            "Run `python -m src.rag.embeddings` pour rebuild (~$5-10 Mistral)."
        )

    config = load_config()
    if not config.mistral_api_key:
        raise SystemExit("MISTRAL_API_KEY absent de .env")

    # Charge corpus + init pipeline
    corpus = json.loads(Path(CORPUS_PATH).read_text(encoding="utf-8"))
    print(f"Corpus chargé : {len(corpus)} fiches")

    client = Mistral(api_key=config.mistral_api_key, timeout_ms=120000)
    validator = Validator(fiches=corpus)

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

    # Charge pack v2
    pack_v2 = json.loads(PACK_V2_PATH.read_text(encoding="utf-8"))
    print(f"Pack v2 : {len(pack_v2)} questions\n")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []

    for entry in pack_v2:
        q_num = entry["question_num"]
        question = entry["question"]
        category = entry.get("category", "?")
        original_answer = entry.get("answer", "")

        print(f"--- Q{q_num} [{category}] : {question[:70]}")
        t0 = time.perf_counter()
        try:
            final_answer, top = pipeline.answer(question)
            elapsed = time.perf_counter() - t0

            validation = pipeline.last_validation
            policy_result = pipeline.last_policy_result

            entry_result = {
                "question_num": q_num,
                "category": category,
                "question": question,
                "original_answer_v2": original_answer,
                "new_answer_with_policy": final_answer,
                "pipeline_latency_s": round(elapsed, 2),
                "word_count_new": len(final_answer.split()),
                "validation": {
                    "honesty_score": round(validation.honesty_score, 3) if validation else None,
                    "flagged": validation.flagged if validation else False,
                    "rule_violations": [
                        {
                            "rule_id": v.rule_id,
                            "severity": v.severity.value,
                            "matched_text": v.matched_text,
                            "category": v.category,
                        }
                        for v in (validation.rule_violations if validation else [])
                    ],
                    "corpus_warnings": [
                        {
                            "claim": w.claim,
                            "closest_match": w.closest_match,
                            "similarity": w.similarity,
                        }
                        for w in (validation.corpus_warnings if validation else [])
                    ],
                },
                "policy": {
                    "policy": policy_result.policy.value if policy_result else "none",
                    "warnings_count": len(policy_result.warnings) if policy_result else 0,
                    "blocked_categories": policy_result.blocked_categories if policy_result else [],
                },
            }
            results.append(entry_result)
            print(f"  honesty={validation.honesty_score:.2f} policy={policy_result.policy.value} latency={elapsed:.1f}s\n")
        except Exception as e:
            print(f"  ERROR : {type(e).__name__}: {e}")
            results.append({
                "question_num": q_num,
                "category": category,
                "question": question,
                "original_answer_v2": original_answer,
                "new_answer_with_policy": None,
                "error": f"{type(e).__name__}: {e}",
            })

    OUT_PATH.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Saved {len(results)} réponses dans {OUT_PATH}")

    # Quick summary
    success = [r for r in results if r.get("new_answer_with_policy")]
    block_count = sum(1 for r in success if r["policy"]["policy"] == "block")
    warn_count = sum(1 for r in success if r["policy"]["policy"] == "warn")
    pass_count = sum(1 for r in success if r["policy"]["policy"] == "passthrough")
    avg_honesty = (
        sum(r["validation"]["honesty_score"] for r in success) / len(success)
        if success else 0.0
    )
    print("\n=== SUMMARY ===")
    print(f"Réponses générées : {len(success)}/{len(pack_v2)}")
    print(f"Policy distribution : pass={pass_count}  warn={warn_count}  block={block_count}")
    print(f"Honesty score moyen : {avg_honesty:.2f}")


if __name__ == "__main__":
    main()
