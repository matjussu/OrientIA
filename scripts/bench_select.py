"""Bench SELECT-ciblé déterministe (Sprint refonte 2026-05-05).

Mesure le taux d'activation `try_select_or_none` sur un mini-bench de 20
questions factuelles pointues. Aucun appel LLM — pur path déterministe :
extract_field_key → extract_entity_simple → lookup_formation → extract_field
+ garde anti-stale.

## Usage

```bash
cd ~/projets/OrientIA && source .venv/bin/activate
python -m scripts.bench_select \\
  --questions data/audit/select_baseline_v1.json \\
  --out results/bench_select_2026-05-05.md
```

Coût : 0 € (zéro appel LLM, zéro embedding). Durée : <1s pour 20 questions.

## Output

Rapport markdown avec :
- Métriques agrégées (% via_select correct, breakdown par catégorie)
- Détail par question : verdict pass/fail + reason effectif vs attendu
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.lookup.structured_select import try_select_or_none


FICHES_PATH = "data/processed/formations_unified.json"


def _verdict(actual_via: bool, actual_reason: str | None, expected_via: bool,
             expected_reason: str | None) -> tuple[bool, str]:
    """Détermine pass/fail + raison courte."""
    if expected_via:
        if actual_via:
            return True, "OK — via_select=True attendu et obtenu"
        return False, f"FAIL — attendu via_select=True, obtenu False ({actual_reason or 'no_match_pattern'})"
    # expected_via=False
    if actual_via:
        return False, f"FAIL — attendu fallback ({expected_reason}), obtenu via_select=True"
    if expected_reason and actual_reason != expected_reason:
        return False, f"FAIL — attendu reason={expected_reason}, obtenu {actual_reason}"
    return True, f"OK — fallback {actual_reason or 'no_pattern_match'}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", required=True, help="JSON select_baseline_v1")
    parser.add_argument("--out", required=True, help="rapport markdown sortie")
    parser.add_argument("--fiches", default=FICHES_PATH, help="corpus formations")
    args = parser.parse_args()

    fiches = json.loads(Path(args.fiches).read_text(encoding="utf-8"))
    payload = json.loads(Path(args.questions).read_text(encoding="utf-8"))
    questions = payload["questions"]

    results = []
    for q in questions:
        select_result = try_select_or_none(q["text"], fiches)
        if select_result is None:
            actual_via = False
            actual_reason = "no_pattern_match"
            actual_field = None
            actual_score = None
        else:
            actual_via = select_result.via_select
            actual_reason = select_result.reason
            actual_field = select_result.field_key
            actual_score = select_result.fuzzy_score

        passed, verdict_msg = _verdict(
            actual_via=actual_via,
            actual_reason=actual_reason,
            expected_via=q["expected_via_select"],
            expected_reason=q.get("expected_reason"),
        )

        results.append({
            "id": q["id"],
            "category": q["category"],
            "text": q["text"],
            "expected_via_select": q["expected_via_select"],
            "expected_reason": q.get("expected_reason"),
            "expected_field": q.get("expected_field"),
            "actual_via_select": actual_via,
            "actual_reason": actual_reason,
            "actual_field": actual_field,
            "actual_score": actual_score,
            "passed": passed,
            "verdict_msg": verdict_msg,
            "comment": q.get("comment"),
        })

    # Métriques agrégées
    total = len(results)
    passed_count = sum(1 for r in results if r["passed"])
    via_select_actual = sum(1 for r in results if r["actual_via_select"])
    via_select_expected = sum(1 for r in results if r["expected_via_select"])
    fallback_correct = sum(
        1 for r in results
        if not r["expected_via_select"] and r["passed"]
    )

    by_category: dict[str, dict] = {}
    for r in results:
        cat = r["category"]
        by_category.setdefault(cat, {"total": 0, "passed": 0})
        by_category[cat]["total"] += 1
        if r["passed"]:
            by_category[cat]["passed"] += 1

    # Markdown output
    lines = [
        "# Bench SELECT-ciblé (Sprint refonte 2026-05-05)",
        "",
        f"**Source** : `{args.questions}`",
        f"**Pipeline** : `try_select_or_none` (déterministe, no LLM)",
        f"**Fiches** : {len(fiches)} entrées",
        "",
        "## Métriques agrégées",
        "",
        "| Métrique | Valeur |",
        "|---|---|",
        f"| Questions testées | {total} |",
        f"| **Pass** | {passed_count}/{total} ({100*passed_count/total:.0f}%) |",
        f"| via_select=True attendu | {via_select_expected} |",
        f"| via_select=True obtenu | {via_select_actual} |",
        f"| Fallback correctement déclenché | {fallback_correct}/{total - via_select_expected} |",
        "",
        "## Par catégorie",
        "",
        "| Catégorie | Pass | Total |",
        "|---|---|---|",
    ]
    for cat, stats in by_category.items():
        lines.append(f"| {cat} | {stats['passed']} | {stats['total']} |")

    lines.extend([
        "",
        "## Détail par question",
        "",
    ])

    for r in results:
        flag = "✅" if r["passed"] else "❌"
        lines.extend([
            f"### {flag} {r['id']} — {r['category']}",
            "",
            f"**Question** : {r['text']}",
            "",
            f"- Attendu : via_select={r['expected_via_select']}"
            + (f" / reason={r['expected_reason']}" if r['expected_reason'] else "")
            + (f" / field={r['expected_field']}" if r['expected_field'] else ""),
            f"- Obtenu : via_select={r['actual_via_select']} / reason={r['actual_reason']}"
            + (f" / field={r['actual_field']}" if r['actual_field'] else "")
            + (f" / fuzzy_score={r['actual_score']:.0f}" if r['actual_score'] else ""),
            f"- Verdict : {r['verdict_msg']}",
        ])
        if r["comment"]:
            lines.append(f"- Comment : {r['comment']}")
        lines.append("")

    Path(args.out).write_text("\n".join(lines), encoding="utf-8")

    # Console résumé
    print(f"\n=== Bench SELECT terminé ===")
    print(f"  Pass : {passed_count}/{total} ({100*passed_count/total:.0f}%)")
    print(f"  via_select : {via_select_actual}/{via_select_expected} attendus")
    print(f"  Wrote {args.out}")

    return 0 if passed_count == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
