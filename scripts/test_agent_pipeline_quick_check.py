"""Quick check intégration agent pipeline Sprint 4 — 2-3 queries live.

OBJECTIF : valider que le pipeline end-to-end est fonctionnel AVANT de
lancer le bench complet 144 calls. Cost-benefit pré-bench (instruction
Jarvis ordre 1652).

Mesure :
- Latence end-to-end (cible 12-18s post-optims Sprint 3)
- Pipeline non-cassé (pas d'exception)
- Pipeline produit un answer_text non vide
- Sources retrievées sanity (≥1 source)

## Output

`results/sprint4_quick_check_2026-04-26.json`

## Coût

3 queries × ~12-18s end-to-end × ~$0.05 par call total = ~$0.20 max.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import faiss  # noqa: E402
from mistralai.client import Mistral  # noqa: E402

from src.agent.cache import LRUCache  # noqa: E402
from src.agent.pipeline_agent import AgentPipeline  # noqa: E402
from src.config import load_config  # noqa: E402


# 3 queries diverses (1 par sous-suite principale + 1 user-naturel)
QUICK_CHECK_QUERIES = [
    {
        "id": "p_lila_q1",
        "suite": "personas_v4",
        "text": "Quels sont les principaux débouchés après une licence de lettres modernes ?",
    },
    {
        "id": "d_q01_postes_pourvoir",
        "suite": "dares_dedie",
        "text": "Quels métiers en 2030 vont recruter le plus de postes à pourvoir en France ?",
    },
    {
        "id": "u_lycee_reunion",
        "suite": "user_naturel",
        "text": "Je suis lycéen à La Réunion, j'aimerais étudier le numérique en métropole. Quelles options ?",
    },
]


PHASED_FICHES_PATH = REPO_ROOT / "data" / "processed" / "formations_multi_corpus_phaseD.json"
PHASED_INDEX_PATH = REPO_ROOT / "data" / "embeddings" / "formations_multi_corpus_phaseD.index"


def main() -> int:
    if not PHASED_FICHES_PATH.exists() or not PHASED_INDEX_PATH.exists():
        print("❌ Phase D index/fiches absent. Run scripts/build_index_phaseD.py")
        return 1

    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=180_000)

    print(f"Loading Phase D index ({PHASED_INDEX_PATH.name})...")
    fiches = json.loads(PHASED_FICHES_PATH.read_text(encoding="utf-8"))
    index = faiss.read_index(str(PHASED_INDEX_PATH))
    print(f"  {len(fiches):,} fiches, ntotal={index.ntotal:,}")

    cache = LRUCache(maxsize=64)
    pipeline = AgentPipeline(
        client=client,
        fiches=fiches,
        index=index,
        profile_cache=cache,
        enable_fact_check=True,  # Quick check = oui (test plein pipeline)
        fact_check_max_claims=3,  # cap pour budget quick check
    )

    print(f"\nQuick check pipeline agent end-to-end ({len(QUICK_CHECK_QUERIES)} queries)")
    print("=" * 60)

    results = []
    for i, q in enumerate(QUICK_CHECK_QUERIES, 1):
        print(f"\n[{i}/{len(QUICK_CHECK_QUERIES)}] [{q['suite']:<13}] {q['id']}")
        print(f"    \"{q['text'][:80]}{'...' if len(q['text']) > 80 else ''}\"")
        # Sleep entre queries
        if i > 1:
            time.sleep(3)

        result = pipeline.answer(q["text"])
        if result.error:
            print(f"    ❌ ERROR : {result.error}")
        else:
            print(f"    ✅ {result.elapsed_total_s}s end-to-end")
            print(f"       clarify={result.elapsed_clarify_s}s + reformulate={result.elapsed_reformulate_s}s")
            print(f"       retrieve={result.elapsed_retrieve_s}s (parallel) + generate={result.elapsed_generate_s}s")
            print(f"       fact_check={result.elapsed_fact_check_s}s ({len(result.fact_check_results)} claims)")
            print(f"       Profile : age={result.profile.age_group} intent={result.profile.intent_type}")
            print(f"       Plan : {len(result.plan.sub_queries)} sub-queries")
            domains = sorted({s["fiche"].get("domain", "formation") for s in result.sources_aggregated})
            print(f"       Top-K aggregated : {len(result.sources_aggregated)} sources, domains : {domains}")
            print(f"       Answer (first 200 chars): {result.answer_text[:200]}...")
            if result.fact_check_results:
                print(f"       Fact-check verdicts: {[fc.verdict for fc in result.fact_check_results]}")
        results.append(result.to_dict())

    # Summary
    avg_total = sum(r["elapsed_total_s"] for r in results) / len(results)
    n_success = sum(1 for r in results if not r["error"])
    n_with_sources = sum(1 for r in results if r["sources_aggregated_count"] > 0)
    print("\n" + "=" * 60)
    print("=== Quick check summary ===")
    print(f"  n_queries: {len(results)}")
    print(f"  n_success: {n_success}/{len(results)}")
    print(f"  n_with_sources: {n_with_sources}/{len(results)}")
    print(f"  avg_total_elapsed: {avg_total:.2f}s")
    print(f"  cache stats: {cache.stats()}")

    out_path = REPO_ROOT / "results" / "sprint4_quick_check_2026-04-26.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out = {
        "summary": {
            "n_queries": len(results),
            "n_success": n_success,
            "avg_total_elapsed_s": round(avg_total, 2),
            "cache_stats": cache.stats(),
        },
        "queries": results,
    }
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ Output → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
