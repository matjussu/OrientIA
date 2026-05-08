"""Compare side-by-side 2 mini-bench JSON pour spot-check humain.

Affiche par question : la question, la config A, la réponse A, la config B,
la réponse B. Stats Layer3 si disponibles. Markdown stdout pour copy-paste.

Usage :
    python scripts/compare_responses.py \\
        --a results/mini_bench/phase_b1_scope.json \\
        --label-a "v3.2 production" \\
        --b results/mini_bench/phase_b2_strict_v4.json \\
        --label-b "strict v4" \\
        --layer3-a results/mini_bench/phase2_layer3_audit.json \\
        --layer3-b results/mini_bench/phase_b2_layer3_audit.json \\
        --qids F1 B1 X1 X2 Z1
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_layer3(path: Path | None) -> dict:
    if path is None or not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {r["id"]: r for r in data.get("audit_records", [])}


def fmt_layer3(rec: dict | None) -> str:
    if not rec:
        return "—"
    n = rec.get("n_layer3_warnings", 0)
    if n == 0:
        return "✅ 0 warnings"
    out = [f"⚠️ {n} warnings :"]
    for w in rec.get("layer3_warnings", []):
        claim = w.get("claim", "")[:100]
        reason = w.get("reason", "")[:120]
        out.append(f"  - **{claim}** → {reason}")
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a", type=Path, required=True, help="Bench A JSON")
    parser.add_argument("--b", type=Path, required=True, help="Bench B JSON")
    parser.add_argument("--label-a", type=str, default="config A")
    parser.add_argument("--label-b", type=str, default="config B")
    parser.add_argument("--layer3-a", type=Path, default=None)
    parser.add_argument("--layer3-b", type=Path, default=None)
    parser.add_argument("--qids", nargs="+", default=None,
                        help="Subset of question IDs (default: all)")
    parser.add_argument("--out", type=Path, default=None,
                        help="Optional markdown output file")
    args = parser.parse_args()

    a = json.loads(args.a.read_text(encoding="utf-8"))
    b = json.loads(args.b.read_text(encoding="utf-8"))
    a_by_id = {r["id"]: r for r in a["unimodal_results"]}
    b_by_id = {r["id"]: r for r in b["unimodal_results"]}
    l3_a = load_layer3(args.layer3_a)
    l3_b = load_layer3(args.layer3_b)

    qids = args.qids or sorted(set(a_by_id.keys()) & set(b_by_id.keys()))

    lines: list[str] = []
    lines.append(f"# Comparaison side-by-side\n")
    lines.append(f"- A : **{args.label_a}** ({args.a.name})")
    lines.append(f"- B : **{args.label_b}** ({args.b.name})\n")

    for qid in qids:
        ra = a_by_id.get(qid)
        rb = b_by_id.get(qid)
        if ra is None or rb is None:
            continue

        lines.append(f"\n---\n")
        lines.append(f"## {qid} — {ra.get('category', '?')}")
        lines.append(f"\n**Question** : {ra['question']}\n")

        # Stats compactes
        lines.append("| Métrique | A | B |")
        lines.append("|---|---|---|")
        lines.append(f"| latency (s) | {ra.get('latency_s')} | {rb.get('latency_s')} |")
        lines.append(f"| words | {ra.get('response_length_words')} | {rb.get('response_length_words')} |")
        lines.append(f"| flagged | {ra.get('flagged')} | {rb.get('flagged')} |")
        lines.append(f"| honesty (c1+2) | {ra.get('honesty_score')} | {rb.get('honesty_score')} |")
        lines.append(f"| scope_label | {ra.get('scope_label', '—')} | {rb.get('scope_label', '—')} |")

        # Layer3 stats
        lines.append("\n**Layer3 audit** :\n")
        lines.append(f"- A : {fmt_layer3(l3_a.get(qid))}")
        lines.append(f"- B : {fmt_layer3(l3_b.get(qid))}")

        lines.append(f"\n### Réponse A ({args.label_a})\n")
        lines.append(f"```\n{ra.get('response') or '(vide)'}\n```")

        lines.append(f"\n### Réponse B ({args.label_b})\n")
        lines.append(f"```\n{rb.get('response') or '(vide)'}\n```")

    output = "\n".join(lines)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding="utf-8")
        print(f"[compare] Saved to {args.out}")
    else:
        print(output)


if __name__ == "__main__":
    main()
