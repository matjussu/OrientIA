"""Bench agent pipeline end-to-end vs baseline figée — Sprint 4.

48 queries baseline (PR #75 unified) sur le pipeline agentique
(ProfileClarifier → QueryReformuler → retrieval parallel → generation
+ fact-check parallel post-gen).

## Comparaison

vs baseline figée `results/bench_persona_complet_2026-04-26/run1/`
(triple-run mean 39.4% verified / 17.9% halluc, IC95 ±3.66/3.90pp).

## Single-run caveat (validé Jarvis Phase 3)

Pour des raisons budget + latence inattendue (44s avg quick check vs
12-18s projeté), single-run choisi vs triple-run IC95 habituel.
Documenté dans verdict Sprint 4 comme caveat épistémique.

## Output

`results/bench_agent_pipeline_2026-04-26/run1/`
+ `_ALL_QUERIES.json` summary unified

## Coût

48 queries × ~36.7s × ~$0.03 = ~$1.6 Mistral.
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

# Réutilise les 48 queries du bench persona complet PR #75
from scripts.run_bench_persona_complet import _build_unified_queries  # noqa: E402


PHASED_FICHES_PATH = REPO_ROOT / "data" / "processed" / "formations_multi_corpus_phaseD.json"
PHASED_INDEX_PATH = REPO_ROOT / "data" / "embeddings" / "formations_multi_corpus_phaseD.index"

OUT_DIR = REPO_ROOT / "results" / "bench_agent_pipeline_2026-04-26" / "run1"


def main() -> int:
    if not PHASED_FICHES_PATH.exists() or not PHASED_INDEX_PATH.exists():
        print("❌ Phase D index/fiches absent.")
        return 1

    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=180_000)

    print(f"Loading Phase D index ({PHASED_INDEX_PATH.name})...")
    fiches = json.loads(PHASED_FICHES_PATH.read_text(encoding="utf-8"))
    index = faiss.read_index(str(PHASED_INDEX_PATH))
    print(f"  {len(fiches):,} fiches, ntotal={index.ntotal:,}")

    cache = LRUCache(maxsize=128)
    pipeline = AgentPipeline(
        client=client,
        fiches=fiches,
        index=index,
        profile_cache=cache,
        aggregated_top_n=8,  # post-optim Sprint 4
        parallel_fact_check_workers=3,
        enable_fact_check=True,
        fact_check_max_claims=5,
    )

    queries = _build_unified_queries()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\nBench agent pipeline single-run — {len(queries)} queries baseline")
    print("=" * 70)

    all_results = []
    suite_emoji = {"personas_v4": "👤", "dares_dedie": "📊",
                   "blocs_dedie": "🎓", "user_naturel": "🗣️"}

    t0_global = time.time()
    for idx, query in enumerate(queries, 1):
        emoji = suite_emoji.get(query["suite"], "?")
        print(f"\n[{idx:2d}/{len(queries)}] {emoji} [{query['suite']:<13}] {query['id']}")
        print(f"    \"{query['text'][:80]}{'...' if len(query['text']) > 80 else ''}\"")

        # Sleep entre queries pour rate limit safety
        if idx > 1:
            time.sleep(2)

        result = pipeline.answer(query["text"])

        if result.error:
            print(f"    ❌ {result.error[:120]}")
        else:
            domains = sorted({s["fiche"].get("domain", "formation") for s in result.sources_aggregated})
            verdicts = [fc.verdict for fc in result.fact_check_results]
            n_supported = sum(1 for v in verdicts if v == "supported")
            n_contradicted = sum(1 for v in verdicts if v == "contradicted")
            n_unsupported = sum(1 for v in verdicts if v == "unsupported")
            n_ambiguous = sum(1 for v in verdicts if v == "ambiguous")
            print(f"    ✅ {result.elapsed_total_s}s "
                  f"(clarify={result.elapsed_clarify_s} "
                  f"reformule={result.elapsed_reformulate_s} "
                  f"retrieve={result.elapsed_retrieve_s} "
                  f"gen={result.elapsed_generate_s} "
                  f"fact={result.elapsed_fact_check_s})")
            print(f"       Profile : age={result.profile.age_group} intent={result.profile.intent_type}")
            print(f"       Plan : {len(result.plan.sub_queries)} sub-queries | "
                  f"Sources top-{len(result.sources_aggregated)} domains : {domains}")
            print(f"       Fact-check {len(verdicts)} claims : "
                  f"{n_supported}✅ / {n_contradicted}🔴 / {n_unsupported}🟡 / {n_ambiguous}🟠")

        # Save per-query
        entry = result.to_dict()
        entry["suite"] = query["suite"]
        entry["query_id"] = query["id"]
        entry["persona_id"] = query.get("persona_id")
        entry["pattern_target"] = query.get("pattern_target")
        entry["gap_target"] = query.get("gap_target")
        all_results.append(entry)

        out_path = OUT_DIR / f"query_{idx:02d}_{query['suite']}_{query['id']}.json"
        out_path.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")

    total = round(time.time() - t0_global, 2)
    avg = round(total / len(queries), 2)

    # Summary
    n_success = sum(1 for r in all_results if not r["error"])
    n_failure = len(all_results) - n_success

    # Aggregate fact-check verdicts
    all_verdicts = []
    for r in all_results:
        all_verdicts.extend([fc["verdict"] for fc in r.get("fact_check_results", [])])
    verdict_counts = {
        v: all_verdicts.count(v)
        for v in ["supported", "contradicted", "unsupported", "ambiguous"]
    }
    n_total_claims = len(all_verdicts)
    pct_supported = (
        round(100 * verdict_counts["supported"] / n_total_claims, 1) if n_total_claims else 0
    )
    pct_contradicted = (
        round(100 * verdict_counts["contradicted"] / n_total_claims, 1) if n_total_claims else 0
    )
    pct_unsupported = (
        round(100 * verdict_counts["unsupported"] / n_total_claims, 1) if n_total_claims else 0
    )

    # Latency stats
    latencies = [r["elapsed_total_s"] for r in all_results if not r["error"]]
    latency_avg = round(sum(latencies) / max(1, len(latencies)), 2)
    latency_min = round(min(latencies), 2) if latencies else 0
    latency_max = round(max(latencies), 2) if latencies else 0

    # Domain coverage
    domain_count = {}
    for r in all_results:
        # On agrège les top-K aggregated counts par domain
        # Stocké dans sources_aggregated_count seulement, pas la liste détaillée
        # Pour granularité, parser depuis sub_query_retrievals si présent
        pass  # on regarde plutôt le bench output JSON pour analyse fine

    summary = {
        "n_queries": len(queries),
        "n_success": n_success,
        "n_failure": n_failure,
        "total_elapsed_s": total,
        "avg_elapsed_s": avg,
        "latency_min_s": latency_min,
        "latency_max_s": latency_max,
        "fact_check": {
            "n_total_claims": n_total_claims,
            "verdicts": verdict_counts,
            "pct_supported": pct_supported,
            "pct_contradicted": pct_contradicted,
            "pct_unsupported": pct_unsupported,
        },
        "cache_stats": cache.stats(),
    }

    out = {"summary": summary, "queries": all_results}
    all_path = OUT_DIR / "_ALL_QUERIES.json"
    all_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 70)
    print("=== Summary single-run ===")
    print(f"  n_queries: {len(queries)}")
    print(f"  n_success: {n_success}/{len(queries)}")
    print(f"  total_elapsed: {total}s ({total/60:.1f} min)")
    print(f"  avg_elapsed: {avg}s")
    print(f"  latency range: [{latency_min}, {latency_max}]s")
    print(f"  fact_check claims totaux: {n_total_claims}")
    print(f"    ✅ supported: {verdict_counts['supported']} ({pct_supported}%)")
    print(f"    🔴 contradicted: {verdict_counts['contradicted']} ({pct_contradicted}%)")
    print(f"    🟡 unsupported: {verdict_counts['unsupported']} ({pct_unsupported}%)")
    print(f"    🟠 ambiguous: {verdict_counts['ambiguous']}")
    print(f"  cache stats: {cache.stats()}")
    print(f"\n✅ Output → {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
