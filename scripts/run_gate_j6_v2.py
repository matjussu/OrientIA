"""Gate J+6 v2 — re-run pack v2 avec Validator V2 (4 règles dures + layer3).

Identique à `run_gate_j6.py` mais avec :
- Règles V2.1-V2.4 actives (HEC AST, PASS pas de redoublement, séries bac ABCD,
  kiné IFMK) via rules.py mis à jour
- Layer3Validator Mistral Small souverain optionnel (si API key OK, fallback
  [] si fail)
- Data cleanup _profil_line effectif (préfixe "mention")

Output : `results/gate_j6/responses_validator_v2_active.json`

Usage :
    python scripts/run_gate_j6_v2.py
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
OUT_DIR = Path("results/gate_j6")
OUT_PATH = OUT_DIR / "responses_validator_v2_active.json"
INDEX_PATH = "data/embeddings/formations.index"
CORPUS_PATH = "data/processed/formations.json"


def main() -> None:
    if not PACK_V2_PATH.exists():
        raise SystemExit(f"Pack v2 introuvable : {PACK_V2_PATH}")
    if not Path(INDEX_PATH).exists():
        raise SystemExit(f"FAISS index introuvable : {INDEX_PATH}")

    config = load_config()
    if not config.mistral_api_key:
        raise SystemExit("MISTRAL_API_KEY absent de .env")

    corpus = json.loads(Path(CORPUS_PATH).read_text(encoding="utf-8"))
    client = Mistral(api_key=config.mistral_api_key, timeout_ms=120000)

    # Layer 3 Mistral Small souverain — test ping first
    print("Ping Mistral Small pour layer 3...")
    layer3 = Layer3Validator(client=client, model="mistral-small-latest")
    try:
        test = client.chat.complete(
            model="mistral-small-latest",
            max_tokens=10,
            messages=[{"role": "user", "content": "ok"}],
        )
        print(f"  ✓ Mistral Small OK ({test.choices[0].message.content[:30] if test.choices else 'no content'}...)")
        layer3_active = True
    except Exception as e:
        print(f"  ✗ Mistral Small fail : {type(e).__name__}: {e}")
        print("  → Layer3 désactivée, fallback couches 1+2 uniquement")
        layer3 = None
        layer3_active = False

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

    pack_v2 = json.loads(PACK_V2_PATH.read_text(encoding="utf-8"))
    print(f"\nPack v2 : {len(pack_v2)} questions")
    print(f"Validator V2 : 4 règles dures + layer3 {'ACTIF' if layer3_active else 'INACTIF'}\n")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []

    for entry in pack_v2:
        q_num = entry["question_num"]
        question = entry["question"]
        category = entry.get("category", "?")
        original = entry.get("answer", "")

        print(f"--- Q{q_num} [{category}] : {question[:70]}")
        t0 = time.perf_counter()
        try:
            final_answer, top = pipeline.answer(question)
            elapsed = time.perf_counter() - t0

            validation = pipeline.last_validation
            policy = pipeline.last_policy_result

            result = {
                "question_num": q_num,
                "category": category,
                "question": question,
                "original_answer_v2": original,
                "new_answer_with_policy_v2": final_answer,
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
                    "layer3_warnings": [
                        {"claim": lw.claim, "reason": lw.reason}
                        for lw in (validation.layer3_warnings if validation else [])
                    ],
                },
                "policy": {
                    "policy": policy.policy.value if policy else "none",
                    "warnings_count": len(policy.warnings) if policy else 0,
                    "blocked_categories": policy.blocked_categories if policy else [],
                },
            }
            results.append(result)
            print(
                f"  honesty={validation.honesty_score:.2f} policy={policy.policy.value} "
                f"rules={len(validation.rule_violations)} corpus={len(validation.corpus_warnings)} "
                f"layer3={len(validation.layer3_warnings)} ({elapsed:.1f}s)\n"
            )
        except Exception as e:
            print(f"  ERROR : {type(e).__name__}: {e}")
            results.append({
                "question_num": q_num,
                "category": category,
                "question": question,
                "error": f"{type(e).__name__}: {e}",
            })

    OUT_PATH.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Saved {len(results)} réponses dans {OUT_PATH}")

    # Summary
    success = [r for r in results if r.get("new_answer_with_policy_v2")]
    block = sum(1 for r in success if r["policy"]["policy"] == "block")
    warn = sum(1 for r in success if r["policy"]["policy"] == "warn")
    pas_ = sum(1 for r in success if r["policy"]["policy"] == "passthrough")
    avg_honesty = sum(r["validation"]["honesty_score"] for r in success) / len(success) if success else 0.0
    total_layer3 = sum(len(r["validation"]["layer3_warnings"]) for r in success)
    print("\n=== SUMMARY V2 ===")
    print(f"Réponses générées : {len(success)}/{len(pack_v2)}")
    print(f"Policy : pass={pas_}  warn={warn}  block={block}")
    print(f"Honesty moyen : {avg_honesty:.2f}")
    print(f"Layer3 warnings totaux : {total_layer3}")


if __name__ == "__main__":
    main()
