"""Step 11 — Mini-bench non-régression A/B router_llm on/off.

Lance les 23 questions unimodales du mini-bench sur le pipeline complet
(génération Mistral medium + validator + post_process) en 2 modes
(`enable_router_llm=True` puis `=False`), pour mesurer :

- honesty score moyen (cible 1.0 — pas de régression vs baseline v4.1)
- flagged_count (cible 0)
- latency p50/p95 pipeline complet (cible p95 ≤ 8s)
- Routing actif par question (last_router_result quand True)
- Filter stats (router_active quand True)
- Delta net router_on vs router_off (réponse, latency, honesty)

Output : results/mini_bench_step11/{responses.jsonl, summary.md}

Coût estimé : 23 × 2 × ~$0.005 = ~$0.23 (pipeline complet, generate inclus)
Wall-clock : ~5-7 min selon latence Mistral

Usage :
    cd ~/projets/OrientIA && source .venv/bin/activate
    python scripts/validate_step11_mini_bench.py
    python scripts/validate_step11_mini_bench.py --sample 5    # smoke test
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mistralai.client import Mistral

from src.config import load_config
from src.rag.factory import make_production_pipeline
from src.validator import Validator


DEFAULT_QUESTIONS = PROJECT_ROOT / "tests" / "mini_bench" / "questions_20.json"
DEFAULT_OUT_DIR = PROJECT_ROOT / "results" / "mini_bench_step11"
DEFAULT_CORPUS = PROJECT_ROOT / "data" / "processed" / "formations_v7.json"
DEFAULT_INDEX = PROJECT_ROOT / "data" / "embeddings" / "formations.index"


# ────────────────────────── Helpers ──────────────────────────


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    sv = sorted(values)
    k = (len(sv) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sv) - 1)
    return sv[f] + (sv[c] - sv[f]) * (k - f) if f != c else sv[f]


def _serialize_route_decision(rd) -> dict | None:
    if rd is None:
        return None
    return {
        "sub_indexes": list(rd.sub_indexes),
        "criteria_region": (rd.criteria.region if rd.criteria else None),
        "criteria_domain": (rd.criteria.domain if rd.criteria else None),
        "domain_lock": rd.domain_lock,
        "refusal_reason": rd.refusal_reason,
        "hardlock_region_strict": rd.hardlock_region_strict,
        "hardlock_domain_strict": rd.hardlock_domain_strict,
        "top_k_override": rd.top_k_override,
        "confidence": rd.confidence,
        "is_fallback": rd.is_fallback,
    }


def _validate_response(validator: Validator, response: str, intent: str | None = None) -> dict:
    """Mesure honesty + flagged sur une réponse (validator standalone)."""
    if not response:
        return {"honesty_score": 0.0, "flagged": True, "n_failed_claims": 0}
    try:
        result = validator.validate(response, intent=intent)
    except Exception as e:
        return {"honesty_score": None, "flagged": True, "error": str(e)}
    flagged = bool(getattr(result, "flagged", False))
    honesty = float(getattr(result, "honesty_score", 0.0) or 0.0)
    n_failed = len(getattr(result, "failed_claims", []) or [])
    return {
        "honesty_score": round(honesty, 3),
        "flagged": flagged,
        "n_failed_claims": n_failed,
    }


# ────────────────────────── Run ──────────────────────────


def run_one(pipeline, validator, q: dict, mode_label: str) -> dict:
    qid = q["id"]
    text = q["text"]
    record: dict = {
        "id": qid,
        "category": q.get("category"),
        "split": q.get("split"),
        "question": text,
        "mode": mode_label,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    t0 = time.time()
    try:
        response, top_sources = pipeline.answer(text)
    except Exception as e:
        record["error"] = f"pipeline.answer() exception: {e}"
        record["latency_total_s"] = round(time.time() - t0, 2)
        return record
    latency = time.time() - t0

    record["latency_total_s"] = round(latency, 2)
    record["response_excerpt"] = (response or "")[:300]
    record["response_n_words"] = len((response or "").split())
    record["n_sources_top"] = len(top_sources)
    record["route_decision"] = _serialize_route_decision(
        getattr(pipeline, "last_router_result", None)
    )
    record["filter_stats"] = getattr(pipeline, "last_filter_stats", None)
    record["scope_label"] = getattr(getattr(pipeline, "last_scope_result", None), "label", None)

    # Validation honesty/flagged sur la réponse retournée (post-policy)
    validation = _validate_response(validator, response or "")
    record.update(validation)
    return record


def run_mode(
    cfg, fiches: list[dict], questions: list[dict],
    index_path: Path, enable_router: bool,
) -> list[dict]:
    label = "router_ON" if enable_router else "router_OFF"
    print(f"\n{'=' * 78}\nMODE : {label}\n{'=' * 78}")
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=120000)
    pipeline = make_production_pipeline(
        client, fiches,
        enable_router_llm=enable_router,
        # Aligner avec configuration prod actuelle
        enable_validator=True,
        enable_layer3=False,
        enable_golden_qa=True,
        enable_post_process=True,
        enable_strict_v4=True,
    )
    pipeline.load_index_from(str(index_path))
    validator = Validator(fiches=fiches, layer3=None)

    records: list[dict] = []
    for i, q in enumerate(questions, start=1):
        print(f"  [{i}/{len(questions)}] {q['id']} ({q.get('category', '?')}): {q['text'][:60]}...")
        rec = run_one(pipeline, validator, q, label)
        if "error" in rec:
            print(f"    ERROR: {rec['error']}")
        else:
            rd = rec.get("route_decision") or {}
            sub = rd.get("sub_indexes") if rd else None
            ref = rd.get("refusal_reason") if rd else None
            print(
                f"    lat={rec['latency_total_s']}s honesty={rec['honesty_score']} "
                f"flagged={rec['flagged']} sub={sub} refusal={ref}"
            )
        records.append(rec)
    return records


# ────────────────────────── Summary ──────────────────────────


def aggregate(records: list[dict]) -> dict:
    valid = [r for r in records if "error" not in r]
    if not valid:
        return {"n": 0}
    honesty = [r["honesty_score"] for r in valid if r.get("honesty_score") is not None]
    lats = [r["latency_total_s"] for r in valid if r.get("latency_total_s") is not None]
    n_flagged = sum(1 for r in valid if r.get("flagged"))
    n_with_router = sum(1 for r in valid if r.get("route_decision"))
    n_router_active = sum(
        1 for r in valid
        if r.get("filter_stats", {}) and r["filter_stats"].get("router_active")
    )
    return {
        "n": len(valid),
        "honesty_avg": round(statistics.mean(honesty), 3) if honesty else None,
        "honesty_min": min(honesty) if honesty else None,
        "n_flagged": n_flagged,
        "latency_p50": round(_percentile(lats, 50), 2),
        "latency_p95": round(_percentile(lats, 95), 2),
        "latency_max": round(max(lats), 2) if lats else None,
        "latency_mean": round(statistics.mean(lats), 2) if lats else None,
        "n_with_router_decision": n_with_router,
        "n_router_active_in_filter": n_router_active,
    }


def write_summary(
    records_on: list[dict],
    records_off: list[dict],
    out_path: Path,
) -> None:
    agg_on = aggregate(records_on)
    agg_off = aggregate(records_off)

    lines: list[str] = []
    lines.append("# Step 11 — Mini-bench non-régression A/B router_llm")
    lines.append(f"\n_Run: {datetime.now(timezone.utc).isoformat()}_")
    lines.append(f"_Questions: {len(records_on)} (mini-bench unimodal)_\n")

    lines.append("## A/B aggregates")
    lines.append("| Metric | router_ON | router_OFF | Δ (ON - OFF) | Gate |")
    lines.append("|---|---:|---:|---:|---|")
    h_on = agg_on.get("honesty_avg")
    h_off = agg_off.get("honesty_avg")
    delta_h = (h_on - h_off) if (h_on is not None and h_off is not None) else None
    h_gate = "✓" if h_on == 1.0 else ("✗" if h_on is not None and h_on < 1.0 else "—")
    lines.append(f"| honesty_avg | {h_on} | {h_off} | {delta_h} | {h_gate} (cible 1.0) |")

    f_on = agg_on.get("n_flagged", 0)
    f_off = agg_off.get("n_flagged", 0)
    lines.append(
        f"| n_flagged | {f_on} | {f_off} | {f_on - f_off} | "
        f"{'✓' if f_on == 0 else '✗'} (cible 0) |"
    )

    p95_on = agg_on.get("latency_p95")
    p95_off = agg_off.get("latency_p95")
    delta_p95 = (p95_on - p95_off) if (p95_on is not None and p95_off is not None) else None
    p95_gate = "✓" if p95_on is not None and p95_on <= 8.0 else "✗"
    lines.append(
        f"| latency_p95 (s) | {p95_on} | {p95_off} | {delta_p95} | "
        f"{p95_gate} (cible ≤ 8.0) |"
    )

    p50_on = agg_on.get("latency_p50")
    p50_off = agg_off.get("latency_p50")
    lines.append(f"| latency_p50 (s) | {p50_on} | {p50_off} | — | — |")
    lines.append(f"| latency_max (s) | {agg_on.get('latency_max')} | {agg_off.get('latency_max')} | — | — |")
    lines.append(f"| n_router_decisions | {agg_on.get('n_with_router_decision', 0)} | {agg_off.get('n_with_router_decision', 0)} | — | — |")
    lines.append(f"| n_router_active_in_retrieval | {agg_on.get('n_router_active_in_filter', 0)} | — | — | — |")

    # Détail par question (router_ON)
    lines.append("\n## Détail par question (mode router_ON)")
    lines.append("| ID | category | latency | honesty | flagged | sub_indexes | refusal |")
    lines.append("|---|---|---:|---:|:-:|---|---|")
    for r in records_on:
        if "error" in r:
            lines.append(f"| {r['id']} | {r.get('category', '?')} | ERROR | — | — | — | — |")
            continue
        rd = r.get("route_decision") or {}
        sub = ",".join(rd.get("sub_indexes", [])) if rd else "—"
        ref = rd.get("refusal_reason") if rd else "—"
        lines.append(
            f"| {r['id']} | {r.get('category', '?')} | {r['latency_total_s']}s | "
            f"{r.get('honesty_score', '—')} | "
            f"{'✗' if r.get('flagged') else '✓'} | {sub} | {ref or '—'} |"
        )

    # Verdict gates
    lines.append("\n## Verdict gates step 11")
    gate_h = h_on == 1.0
    gate_f = f_on == 0
    gate_lat = p95_on is not None and p95_on <= 8.0
    all_pass = gate_h and gate_f and gate_lat
    lines.append(f"\n- honesty_avg == 1.0 : {'✓' if gate_h else '✗'} ({h_on})")
    lines.append(f"- n_flagged == 0 : {'✓' if gate_f else '✗'} ({f_on})")
    lines.append(f"- latency_p95 ≤ 8.0s : {'✓' if gate_lat else '✗'} ({p95_on}s)")
    if delta_h is not None:
        lines.append(f"- Δ honesty (ON - OFF) : {delta_h:+.3f}")
    if delta_p95 is not None:
        lines.append(f"- Δ p95 (ON - OFF) : {delta_p95:+.2f}s (overhead routing)")
    lines.append(f"\n**{'GATE STEP 11 PASS ✅' if all_pass else 'GATE STEP 11 FAIL ❌'}**")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n📄 Summary écrit : {out_path}")


# ────────────────────────── CLI ──────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--corpus-path", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--index-path", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument(
        "--sample", type=int, default=0,
        help="Si >0, ne traite que les N premières questions (smoke test).",
    )
    parser.add_argument(
        "--mode", choices=["both", "on", "off"], default="both",
        help="both = run router_ON puis router_OFF (cible step 11). "
             "on/off = un seul mode (économie ~$0.12).",
    )
    args = parser.parse_args()

    cfg = load_config()
    if not cfg.mistral_api_key:
        print("ERREUR : MISTRAL_API_KEY absent du .env", file=sys.stderr)
        return 1
    for p in (args.questions, args.corpus_path, args.index_path):
        if not p.exists():
            print(f"ERREUR : fichier manquant {p}", file=sys.stderr)
            return 1

    args.out_dir.mkdir(parents=True, exist_ok=True)

    # Load
    questions_data = json.loads(args.questions.read_text(encoding="utf-8"))
    questions = questions_data["questions_unimodal"]
    if args.sample:
        questions = questions[: args.sample]
    print(f"Questions : {len(questions)}")
    fiches = json.loads(args.corpus_path.read_text(encoding="utf-8"))
    print(f"Corpus : {len(fiches)} fiches")

    # Run
    records_on: list[dict] = []
    records_off: list[dict] = []
    if args.mode in ("both", "on"):
        records_on = run_mode(cfg, fiches, questions, args.index_path, enable_router=True)
    if args.mode in ("both", "off"):
        records_off = run_mode(cfg, fiches, questions, args.index_path, enable_router=False)

    # Output
    jsonl = args.out_dir / "responses.jsonl"
    with jsonl.open("w", encoding="utf-8") as f:
        for r in records_on + records_off:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n📄 JSONL écrit : {jsonl}")

    summary = args.out_dir / "summary.md"
    write_summary(records_on, records_off, summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
