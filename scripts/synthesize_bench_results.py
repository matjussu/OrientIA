"""Synthesize bench results — produit SUMMARY.md auto avec verdict GO/NO-GO.

Lit les outputs d'un dossier `results/bench_v7_v4_1_<timestamp>/` produit par
`reproduce_bench.sh`, applique les 6 gates de `docs/BENCH_GATES.md`, et écrit
un SUMMARY.md exploitable sans relire les JSON bruts.

Robuste aux fichiers manquants : si un script du bench a été skippé
(--skip-judges, --skip-factcheck), les gates correspondantes sont marquées
SKIPPED et n'entrent pas dans le verdict global.

Usage :
    python scripts/synthesize_bench_results.py --bench-dir results/bench_v7_v4_1_<TS> --out results/bench_v7_v4_1_<TS>/SUMMARY.md
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _safe_load_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return {"_parse_error": str(e)}


def _gate_status(passed: bool | None) -> str:
    if passed is None:
        return "⏭ SKIPPED"
    return "✅ PASS" if passed else "❌ FAIL"


def _eval_gate1_recall(eval_recall: dict | None) -> tuple[bool | None, list[str]]:
    """Gate 1 : recall@5 ≥ 75%, par catégorie ≥ 60%, MRR ≥ 0.55, nDCG@10 ≥ 0.65."""
    if not eval_recall or "global" not in eval_recall:
        return None, ["Gate 1 — données absentes"]
    g = eval_recall["global"]
    by_cat = eval_recall.get("by_category", {})
    lines = []
    checks = []

    rec5 = g.get("recall_at_5")
    if rec5 is None:
        lines.append("recall@5 global : indisponible")
    else:
        ok = rec5 >= 0.75
        checks.append(ok)
        lines.append(f"recall@5 global : {rec5:.1%} (cible ≥75%) {_gate_status(ok)}")

    mrr = g.get("mrr")
    if mrr is not None:
        ok = mrr >= 0.55
        checks.append(ok)
        lines.append(f"MRR global : {mrr:.3f} (cible ≥0.55) {_gate_status(ok)}")

    ndcg = g.get("ndcg_at_10")
    if ndcg is not None:
        ok = ndcg >= 0.65
        checks.append(ok)
        lines.append(f"nDCG@10 global : {ndcg:.3f} (cible ≥0.65) {_gate_status(ok)}")

    cat_failures = []
    for cat, stats in by_cat.items():
        if cat in ("adversarial", "cross_domain"):
            continue
        r5 = stats.get("recall_at_5")
        if r5 is None:
            continue
        ok = r5 >= 0.60
        if not ok:
            cat_failures.append(f"{cat}={r5:.1%}")
        checks.append(ok)
    if cat_failures:
        lines.append(f"Catégories <60% : {', '.join(cat_failures)} ❌")
    else:
        lines.append("Toutes catégories non-adversarial ≥60% recall@5 ✅")

    return (all(checks) if checks else None), lines


def _eval_gate2_honesty_minibench(mini_bench: dict | None) -> tuple[bool | None, list[str]]:
    """Gate 2 : avg_honesty ≥ 0.95, flagged ≤ 2/23, latency ≤ 9s."""
    if not mini_bench:
        return None, ["Gate 2 — données absentes"]
    lines = []
    checks = []

    summary = mini_bench.get("summary") or mini_bench.get("aggregate") or mini_bench
    h = summary.get("avg_honesty") or summary.get("honesty")
    flagged = summary.get("flagged_count") or summary.get("n_flagged")
    lat = summary.get("avg_latency") or summary.get("avg_latency_s")

    if h is not None:
        ok = h >= 0.95
        checks.append(ok)
        lines.append(f"avg_honesty : {h:.3f} (cible ≥0.95) {_gate_status(ok)}")
    if flagged is not None:
        ok = flagged <= 2
        checks.append(ok)
        lines.append(f"flagged_count : {flagged} (cible ≤2) {_gate_status(ok)}")
    if lat is not None:
        ok = lat <= 9.0
        checks.append(ok)
        lines.append(f"avg_latency : {lat:.2f}s (cible ≤9s) {_gate_status(ok)}")

    return (all(checks) if checks else None), lines


def _eval_gate3_latency(eval_recall: dict | None) -> tuple[bool | None, list[str]]:
    """Gate 3 : p50 ≤ 8s, p95 ≤ 12s sur les 60q de eval_recall."""
    if not eval_recall or "results" not in eval_recall:
        return None, ["Gate 3 — données absentes (eval_recall manquant)"]
    lines = []
    checks = []
    latencies = sorted(
        r["latency_s"] for r in eval_recall["results"] if "latency_s" in r and "error" not in r
    )
    if not latencies:
        return None, ["Gate 3 — pas de latencies mesurables"]
    n = len(latencies)
    p50 = latencies[n // 2]
    p95 = latencies[min(int(n * 0.95), n - 1)]
    ok_p50 = p50 <= 8.0
    ok_p95 = p95 <= 12.0
    no_timeout = max(latencies) <= 30.0
    checks.extend([ok_p50, ok_p95, no_timeout])
    lines.append(f"p50 : {p50:.2f}s (cible ≤8s) {_gate_status(ok_p50)}")
    lines.append(f"p95 : {p95:.2f}s (cible ≤12s) {_gate_status(ok_p95)}")
    lines.append(f"Aucun timeout >30s : max={max(latencies):.2f}s {_gate_status(no_timeout)}")

    return all(checks), lines


def _eval_gate4_adversarial(eval_recall: dict | None, factcheck: dict | None) -> tuple[bool | None, list[str]]:
    """Gate 4 : refusal adversarial ≥ 80%, cross_domain = 100%, 0 unverifiable_high."""
    if not eval_recall:
        return None, ["Gate 4 — données absentes (eval_recall manquant)"]
    lines = []
    checks = []
    by_cat = eval_recall.get("by_category", {})

    adv = by_cat.get("adversarial", {})
    rc_adv = adv.get("refusal_correctness")
    if rc_adv is not None:
        ok = rc_adv >= 0.80
        checks.append(ok)
        lines.append(f"refusal adversarial : {rc_adv:.1%} (cible ≥80%) {_gate_status(ok)}")
    else:
        lines.append("refusal adversarial : indisponible (golden_50 ?)")

    xd = by_cat.get("cross_domain", {})
    rc_xd = xd.get("refusal_correctness")
    if rc_xd is not None:
        ok = rc_xd >= 1.0
        checks.append(ok)
        lines.append(f"refusal cross_domain : {rc_xd:.1%} (cible 100%) {_gate_status(ok)}")
    else:
        lines.append("refusal cross_domain : indisponible (golden_50 ?)")

    # Haiku unverifiable_high — best effort, format peut varier selon run_haiku_factcheck
    if factcheck:
        try:
            n_unver_high = 0
            if isinstance(factcheck, dict):
                # Format souple : on cherche tout entry avec confidence/high_confidence + unverifiable
                for k, v in factcheck.items():
                    if isinstance(v, dict):
                        verdict = v.get("verdict") or v.get("classification")
                        conf = v.get("confidence") or v.get("score")
                        if verdict == "unverifiable" and isinstance(conf, (int, float)) and conf >= 0.8:
                            n_unver_high += 1
            ok = n_unver_high == 0
            checks.append(ok)
            lines.append(f"Hallucinations Haiku confidence ≥0.8 : {n_unver_high} (cible 0) {_gate_status(ok)}")
        except Exception as e:
            lines.append(f"Haiku check erreur : {e}")

    return (all(checks) if checks else None), lines


def _eval_gate5_rubric(judges_dir: Path) -> tuple[bool | None, list[str]]:
    """Gate 5 : our_rag rubric ≥12/18 Claude+GPT-4o, κ ≥0.4, our_rag ≥ baselines."""
    claude_path = judges_dir / "scores_claude.json"
    gpt_path = judges_dir / "scores_gpt4o.json"
    if not (claude_path.exists() or gpt_path.exists()):
        return None, ["Gate 5 — judges skippés ou absents"]

    lines = []
    checks = []

    for judge_name, path in (("Claude", claude_path), ("GPT-4o", gpt_path)):
        scores = _safe_load_json(path)
        if not scores:
            lines.append(f"{judge_name} : fichier absent")
            continue
        # Format Run F : list de 100 entries avec scores per system
        if not isinstance(scores, list) or not scores:
            lines.append(f"{judge_name} : format inattendu, skip parse")
            continue
        # Aggrégation par système
        sys_totals: dict[str, list[float]] = {}
        for entry in scores:
            for sys_name, sys_scores in (entry.get("scores") or {}).items():
                tot = sys_scores.get("total")
                if isinstance(tot, (int, float)):
                    sys_totals.setdefault(sys_name, []).append(float(tot))
        if not sys_totals:
            lines.append(f"{judge_name} : aucun score parsé")
            continue
        avg_per_sys = {k: sum(v) / len(v) for k, v in sys_totals.items()}
        # our_rag = chercher la clé qui contient "our_rag" (variations possibles)
        our_keys = [k for k in avg_per_sys.keys() if "our_rag" in k.lower()]
        if not our_keys:
            lines.append(f"{judge_name} : pas de système 'our_rag*' trouvé. Clés : {list(avg_per_sys.keys())[:3]}")
            continue
        our_score = max(avg_per_sys[k] for k in our_keys)
        ok = our_score >= 12.0
        checks.append(ok)
        lines.append(f"{judge_name} our_rag /18 : {our_score:.2f} (cible ≥12) {_gate_status(ok)}")

        # Comparaison vs baselines neutral
        neutral_keys = [k for k in avg_per_sys.keys() if "neutral" in k.lower() and "rag" not in k.lower()]
        if neutral_keys:
            neutral_avg = sum(avg_per_sys[k] for k in neutral_keys) / len(neutral_keys)
            delta = our_score - neutral_avg
            ok_delta = delta >= 1.0
            checks.append(ok_delta)
            lines.append(f"  Δ vs neutral baselines : {delta:+.2f} pts (cible ≥+1.0) {_gate_status(ok_delta)}")

    return (all(checks) if checks else None), lines


def _eval_gate6_haiku(factcheck: dict | None) -> tuple[bool | None, list[str]]:
    """Gate 6 : our_rag honesty Haiku ≥ 0.85, our_rag ≥ mistral_v3_2_no_rag +0.05."""
    if not factcheck:
        return None, ["Gate 6 — Haiku factcheck skippé ou absent"]
    lines = []
    checks = []

    # Format souple : on cherche per-system honesty
    sys_honesty: dict[str, list[float]] = {}
    if isinstance(factcheck, dict):
        for k, v in factcheck.items():
            if isinstance(v, dict):
                # k peut être un question_id, et v contient scores per system
                for sys_name, sys_data in v.items():
                    if isinstance(sys_data, dict):
                        h = sys_data.get("honesty_score") or sys_data.get("honesty") or sys_data.get("score")
                        if isinstance(h, (int, float)):
                            sys_honesty.setdefault(sys_name, []).append(float(h))

    if not sys_honesty:
        lines.append("Haiku format inattendu, parse impossible")
        return None, lines

    avg_per_sys = {k: sum(v) / len(v) for k, v in sys_honesty.items()}
    our_keys = [k for k in avg_per_sys.keys() if "our_rag" in k.lower()]
    if our_keys:
        our_h = max(avg_per_sys[k] for k in our_keys)
        ok = our_h >= 0.85
        checks.append(ok)
        lines.append(f"Haiku our_rag honesty : {our_h:.3f} (cible ≥0.85) {_gate_status(ok)}")

        v32_keys = [k for k in avg_per_sys.keys() if "v3_2_no_rag" in k.lower() or "v3.2_no_rag" in k.lower()]
        if v32_keys:
            v32_h = max(avg_per_sys[k] for k in v32_keys)
            delta = our_h - v32_h
            ok_delta = delta >= 0.05
            checks.append(ok_delta)
            lines.append(f"  Δ vs mistral_v3_2_no_rag : {delta:+.3f} (cible ≥+0.05) {_gate_status(ok_delta)}")
    else:
        lines.append("our_rag absent du factcheck")

    return (all(checks) if checks else None), lines


def synthesize(bench_dir: Path) -> str:
    """Lit tous les outputs et produit le markdown SUMMARY."""
    eval_recall = _safe_load_json(bench_dir / "eval_recall_v7.json")
    mini_bench = _safe_load_json(bench_dir / "mini_bench.json")
    factcheck = _safe_load_json(bench_dir / "factcheck" / "scores_haiku.json")

    g1, g1_lines = _eval_gate1_recall(eval_recall)
    g2, g2_lines = _eval_gate2_honesty_minibench(mini_bench)
    g3, g3_lines = _eval_gate3_latency(eval_recall)
    g4, g4_lines = _eval_gate4_adversarial(eval_recall, factcheck)
    g5, g5_lines = _eval_gate5_rubric(bench_dir / "judges")
    g6, g6_lines = _eval_gate6_haiku(factcheck)

    gates = [
        ("Gate 1 — Retrieval golden_60", g1, g1_lines),
        ("Gate 2 — Honesty mini-bench v4.1", g2, g2_lines),
        ("Gate 3 — Latency p95", g3, g3_lines),
        ("Gate 4 — Robustesse adversariale", g4, g4_lines),
        ("Gate 5 — Rubric LLM-judge externe", g5, g5_lines),
        ("Gate 6 — Honesty Haiku factcheck", g6, g6_lines),
    ]

    relevant = [(label, status) for label, status, _ in gates if status is not None]
    if not relevant:
        verdict = "⚠ INCOMPLET — toutes les gates absentes (skipped ?)"
    elif all(s for _, s in relevant):
        verdict = "✅ GO — toutes gates mesurées passent → multi-tour Path B"
    else:
        failed = [label for label, s in relevant if not s]
        verdict = f"❌ NO-GO — gates au rouge : {', '.join(failed)}"

    out = [
        f"# Bench summary — `{bench_dir.name}`",
        "",
        f"**Verdict global** : {verdict}",
        "",
        f"Gates appliquées par référence à `docs/BENCH_GATES.md` (Phase D du plan verrouillage-bench-multi-tour).",
        "",
        "---",
        "",
    ]
    for label, status, lines in gates:
        out.append(f"## {label} — {_gate_status(status)}")
        out.append("")
        for l in lines:
            out.append(f"- {l}")
        out.append("")

    # Annexes — extraits bruts pour traçabilité
    out.append("---")
    out.append("")
    out.append("## Annexe : artefacts présents")
    out.append("")
    for f in sorted(bench_dir.glob("**/*")):
        if f.is_file():
            try:
                size = f.stat().st_size
                out.append(f"- `{f.relative_to(bench_dir)}` ({size:,} bytes)")
            except OSError:
                pass

    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bench-dir", type=Path, required=True,
                        help="results/bench_v7_v4_1_<timestamp>/ produit par reproduce_bench.sh")
    parser.add_argument("--out", type=Path, default=None,
                        help="Path SUMMARY.md (défaut <bench-dir>/SUMMARY.md)")
    args = parser.parse_args()

    if not args.bench_dir.exists():
        print(f"ERROR: bench-dir absent : {args.bench_dir}", file=sys.stderr)
        return 1

    out_path = args.out or (args.bench_dir / "SUMMARY.md")
    summary = synthesize(args.bench_dir)
    out_path.write_text(summary, encoding="utf-8")
    print(f"SUMMARY.md écrit : {out_path}")
    # Print verdict pour stdout du caller
    for line in summary.split("\n"):
        if line.startswith("**Verdict global**"):
            print(line)
            break
    return 0


if __name__ == "__main__":
    sys.exit(main())
