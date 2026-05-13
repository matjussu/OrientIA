"""Diagnostic latency Q01 — Phase 1.3 (2026-05-14).

Anomalie identifiée par l'ingénieur observability : Q01 ("Quels métiers
vont recruter en Occitanie en 2030 ?") prend 31-40s avec 0 appels
mistral-small dans la trace Langfuse, alors que les autres questions ont
1-2 small calls (scope_classifier + router_llm). Le LLM medium pour la
génération coûte ~5-8s typiquement, laissant ~15-25s non-élucidés.

Hypothèses :
- (a) scope_classifier ou router_llm appels silent error → fallback rapide
  + medium call seul à 25s+
- (b) retry conditionnel post-validator → 2 cycles medium = 12-20s
- (c) backoff réseau / SDK mistral retry interne

Ce script monkey-patch les principales méthodes du pipeline avec timing
perf_counter() et affiche un breakdown step-by-step sur 3 runs de Q01.

Usage :
    python scripts/diag_q01_latency.py
"""
from __future__ import annotations

import json
import time
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from mistralai.client import Mistral
from src.config import load_config
from src.rag.factory import make_production_pipeline


Q01 = "Quels métiers vont recruter en Occitanie en 2030 ?"
N_RUNS = 3


def patch_with_timing(pipeline) -> dict:
    """Monkey-patch les méthodes clés du pipeline pour mesurer leur temps.

    Retourne un dict de listes (1 entrée par appel) qui sera rempli au fur
    et à mesure des appels.
    """
    timings: dict[str, list[float]] = {
        "scope_classify": [],
        "router_route": [],
        "retrieve": [],
        "rerank": [],
        "mmr": [],
        "golden_qa_prefix": [],
        "generate_with_retry": [],
        "validator": [],
        "post_process": [],
    }

    # Wrap each target method
    def wrap(obj, method_name, key):
        orig = getattr(obj, method_name, None)
        if orig is None:
            return
        def wrapped(*args, **kwargs):
            t0 = time.perf_counter()
            res = orig(*args, **kwargs)
            timings[key].append(time.perf_counter() - t0)
            return res
        setattr(obj, method_name, wrapped)

    # ScopeClassifier
    if pipeline.scope_classifier is not None:
        wrap(pipeline.scope_classifier, "classify", "scope_classify")
    # Router LLM
    if pipeline._router_llm is not None:
        wrap(pipeline._router_llm, "route", "router_route")
    # Retrieve
    wrap(pipeline, "retrieve_top_k", "retrieve")
    # Validator
    if pipeline.validator is not None:
        wrap(pipeline.validator, "validate", "validator")
    # Internal helpers
    wrap(pipeline, "_maybe_build_golden_qa_prefix", "golden_qa_prefix")
    wrap(pipeline, "_generate_with_retry", "generate_with_retry")

    return timings


def main() -> int:
    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=120000)
    print(f"==> Chargement corpus + index v5...")
    fiches = json.loads(Path("data/processed/formations_v5.json").read_text(encoding="utf-8"))
    pipeline = make_production_pipeline(client, fiches)
    pipeline.load_index_from("data/embeddings/formations_v5.index")
    print(f"    {len(fiches)} fiches chargées")

    print(f"\n==> Diagnostic Q01 sur {N_RUNS} runs...")
    print(f"    Question : {Q01}\n")

    all_runs = []
    for i in range(N_RUNS):
        # Reset timings dict per run
        timings = patch_with_timing(pipeline)
        t0 = time.time()
        try:
            answer, top = pipeline.answer(Q01, top_k_sources=5)
            total = time.time() - t0
            n_words = len(answer.split())
            run = {
                "run": i + 1,
                "total_s": total,
                "n_words": n_words,
                "timings": {k: round(sum(v), 3) for k, v in timings.items()},
                "n_calls": {k: len(v) for k, v in timings.items()},
            }
            all_runs.append(run)
            print(f"  Run {i+1}: total={total:.2f}s | words={n_words}")
            for k, v in run["timings"].items():
                if v > 0:
                    print(f"    {k:<22} {v:>6.2f}s × {run['n_calls'][k]} call(s)")
            sum_steps = sum(run["timings"].values())
            unaccounted = total - sum_steps
            print(f"    {'TOTAL STEPS':<22} {sum_steps:>6.2f}s")
            print(f"    {'UNACCOUNTED':<22} {unaccounted:>6.2f}s ({100*unaccounted/total:.0f}%)")
            print()
        except Exception as e:
            print(f"  Run {i+1}: ERROR {e}")
            continue

    # Aggregate
    if all_runs:
        print(f"==> Moyennes sur {len(all_runs)} runs :")
        avg_total = sum(r["total_s"] for r in all_runs) / len(all_runs)
        print(f"  Total : {avg_total:.2f}s")
        for k in all_runs[0]["timings"].keys():
            avg = sum(r["timings"][k] for r in all_runs) / len(all_runs)
            n = sum(r["n_calls"][k] for r in all_runs) / len(all_runs)
            if avg > 0.01:
                print(f"  {k:<22} {avg:>6.2f}s avg | {n:.1f} calls avg")

        # Verdict
        print(f"\n==> Verdict")
        avg_gen = sum(r["timings"]["generate_with_retry"] for r in all_runs) / len(all_runs)
        n_gen = sum(r["n_calls"]["generate_with_retry"] for r in all_runs) / len(all_runs)
        avg_validator = sum(r["timings"].get("validator", 0) for r in all_runs) / len(all_runs)
        avg_router = sum(r["timings"].get("router_route", 0) for r in all_runs) / len(all_runs)
        avg_scope = sum(r["timings"].get("scope_classify", 0) for r in all_runs) / len(all_runs)
        print(f"  - generate_with_retry : {avg_gen:.2f}s ({n_gen:.1f} call) — c'est le LLM medium principal")
        print(f"  - validator           : {avg_validator:.2f}s")
        print(f"  - router_llm          : {avg_router:.2f}s")
        print(f"  - scope_classifier    : {avg_scope:.2f}s")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
