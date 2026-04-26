"""Audit tool_calls.arguments ProfileClarifier sur 48 queries baseline.

TODO Sprint 1 prio 2 (cf docs/SPRINT1_PROFILE_CLARIFIER_VERDICT.md §3.4) :
le LLM Mistral peut inventer des valeurs hors-enum spontanément. Bug
catché in-Sprint 1 sur `professionnel_actif` (age_group invalid 3/15
queries premier run). Audit nécessaire à grande échelle pour décider
strategy validation.

## Méthodo

1. Run ProfileClarifier sur les 48 queries baseline (PR #75 bench
   persona complet — sous-suites personas v4 / DARES / blocs / user_naturel)
2. Pour chaque query : capturer les `tool_call.arguments` brut AVANT
   validation `is_valid()` (= ce que le LLM a réellement émis)
3. Identifier :
   - Valeurs `age_group` hors VALID_AGE_GROUPS
   - Valeurs `education_level` hors VALID_EDUCATION_LEVELS
   - Valeurs `intent_type` hors VALID_INTENT_TYPES
   - Champs hors-schema (clés non déclarées)
   - Types invalides (e.g., string au lieu de array)

## Output

`results/sprint2_profile_clarifier_enum_audit_2026-04-26.json` :
- Liste des extractions par query
- Distribution des enums spontanés (count par valeur)
- Recommandations : élargir enum / Pydantic strict / log+alert

## Coût

48 queries × ~2K tokens × Mistral Large $2/1M = ~$0.20 + sleep
3s entre queries (rate limit caveat Sprint 1) = ~3 min total.
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mistralai.client import Mistral  # noqa: E402

from src.agent.retry import call_with_retry  # noqa: E402
from src.agent.tools.profile_clarifier import (  # noqa: E402
    CLARIFIER_SYSTEM_PROMPT,
    PROFILE_CLARIFIER_TOOL,
    VALID_AGE_GROUPS,
    VALID_EDUCATION_LEVELS,
    VALID_INTENT_TYPES,
)
from src.config import load_config  # noqa: E402

# Source des 48 queries baseline (PR #75 bench persona complet run1)
BASELINE_RESULTS_PATH = REPO_ROOT / "results" / "bench_persona_complet_2026-04-26" / "_ALL_QUERIES.json"

OUT_PATH = REPO_ROOT / "results" / "sprint2_profile_clarifier_enum_audit_2026-04-26.json"


def _extract_raw_args(client: Mistral, query: str) -> dict[str, Any]:
    """Invoque ProfileClarifier mais capture les args BRUTS pré-validation.

    Différent de `ProfileClarifier.clarify()` qui retourne directement
    un Profile validé. Ici on veut voir ce que le LLM émet sans
    validation → audit des enum spontanés.
    """
    messages = [
        {"role": "system", "content": CLARIFIER_SYSTEM_PROMPT},
        {"role": "user", "content": query},
    ]
    response = call_with_retry(
        lambda: client.chat.complete(
            model="mistral-large-latest",
            messages=messages,
            tools=[PROFILE_CLARIFIER_TOOL.to_mistral_schema()],
            tool_choice="any",
        ),
        max_retries=3,
        initial_backoff=2.0,
    )
    msg = response.choices[0].message
    if not msg.tool_calls:
        return {"error": "no_tool_call", "content": (msg.content or "")[:200]}
    tc = msg.tool_calls[0]
    if tc.function.name != PROFILE_CLARIFIER_TOOL.name:
        return {"error": "wrong_tool", "got": tc.function.name}
    try:
        return json.loads(tc.function.arguments)
    except json.JSONDecodeError as e:
        return {"error": "json_parse_failed", "raw": tc.function.arguments[:300]}


def _detect_anomalies(args: dict) -> dict[str, Any]:
    """Compare args raw vs schemas valid. Identifie tout écart."""
    anomalies = []

    # Enum mismatches
    if "age_group" in args and args["age_group"] not in VALID_AGE_GROUPS:
        anomalies.append({
            "field": "age_group",
            "spurious_value": args["age_group"],
            "type": "enum_out_of_range",
        })
    if "education_level" in args and args["education_level"] not in VALID_EDUCATION_LEVELS:
        anomalies.append({
            "field": "education_level",
            "spurious_value": args["education_level"],
            "type": "enum_out_of_range",
        })
    if "intent_type" in args and args["intent_type"] not in VALID_INTENT_TYPES:
        anomalies.append({
            "field": "intent_type",
            "spurious_value": args["intent_type"],
            "type": "enum_out_of_range",
        })

    # sector_interest must be list
    if "sector_interest" in args and not isinstance(args["sector_interest"], list):
        anomalies.append({
            "field": "sector_interest",
            "spurious_value": str(args["sector_interest"])[:200],
            "type": "wrong_type_expected_list",
        })

    # confidence must be 0-1 number
    if "confidence" in args:
        try:
            c = float(args["confidence"])
            if not 0.0 <= c <= 1.0:
                anomalies.append({
                    "field": "confidence",
                    "spurious_value": c,
                    "type": "out_of_bounds_0_1",
                })
        except (ValueError, TypeError):
            anomalies.append({
                "field": "confidence",
                "spurious_value": args["confidence"],
                "type": "not_numeric",
            })

    # Champs hors-schema déclaré
    declared = set(PROFILE_CLARIFIER_TOOL.parameters["properties"].keys())
    extra = set(args.keys()) - declared
    if extra:
        anomalies.append({
            "field": "(extra)",
            "spurious_value": sorted(extra),
            "type": "fields_not_in_schema",
        })

    # Required missing
    required = set(PROFILE_CLARIFIER_TOOL.parameters["required"])
    missing = required - set(args.keys())
    if missing:
        anomalies.append({
            "field": "(missing)",
            "spurious_value": sorted(missing),
            "type": "required_missing",
        })

    return anomalies


def main() -> int:
    if not BASELINE_RESULTS_PATH.exists():
        print(f"❌ {BASELINE_RESULTS_PATH} absent.")
        return 1

    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=60_000)

    baseline = json.loads(BASELINE_RESULTS_PATH.read_text(encoding="utf-8"))
    print(f"Audit ProfileClarifier sur {len(baseline)} queries baseline (run1)")
    print("=" * 60)

    audit_entries = []
    age_group_values: Counter = Counter()
    education_level_values: Counter = Counter()
    intent_type_values: Counter = Counter()
    n_anomalies = 0
    n_success = 0
    n_failure = 0

    for i, q in enumerate(baseline, 1):
        suite = q.get("suite", "?")
        qid = q.get("query_id", f"q{i}")
        text = q.get("query_text", "")
        print(f"\n[{i:2d}/{len(baseline)}] [{suite:<14}] {qid}")
        print(f"    \"{text[:80]}{'...' if len(text) > 80 else ''}\"")

        if i > 1:
            time.sleep(2.5)  # rate limit safety

        try:
            args = _extract_raw_args(client, text)
        except Exception as e:
            print(f"    ❌ {type(e).__name__}: {e}")
            audit_entries.append({
                "query_id": qid,
                "suite": suite,
                "query_text": text,
                "error": f"{type(e).__name__}: {e}",
                "anomalies": [],
            })
            n_failure += 1
            continue

        if "error" in args:
            print(f"    ❌ {args['error']}")
            audit_entries.append({
                "query_id": qid,
                "suite": suite,
                "query_text": text,
                "raw_args": args,
                "anomalies": [],
            })
            n_failure += 1
            continue

        # Capture distributions
        if "age_group" in args:
            age_group_values[args["age_group"]] += 1
        if "education_level" in args:
            education_level_values[args["education_level"]] += 1
        if "intent_type" in args:
            intent_type_values[args["intent_type"]] += 1

        anomalies = _detect_anomalies(args)
        if anomalies:
            n_anomalies += 1
            print(f"    ⚠️  {len(anomalies)} anomalie(s) :")
            for a in anomalies:
                print(f"       - {a['type']} on {a['field']}: {a['spurious_value']}")
        else:
            print(f"    ✅ Aucune anomalie | "
                  f"age={args.get('age_group')} edu={args.get('education_level')} "
                  f"intent={args.get('intent_type')}")

        audit_entries.append({
            "query_id": qid,
            "suite": suite,
            "query_text": text,
            "raw_args": args,
            "anomalies": anomalies,
        })
        n_success += 1

    summary = {
        "n_queries_total": len(baseline),
        "n_success": n_success,
        "n_failure": n_failure,
        "n_with_anomalies": n_anomalies,
        "n_clean": n_success - n_anomalies,
        "age_group_distribution": dict(age_group_values.most_common()),
        "education_level_distribution": dict(education_level_values.most_common()),
        "intent_type_distribution": dict(intent_type_values.most_common()),
        "valid_age_groups": sorted(VALID_AGE_GROUPS),
        "valid_education_levels": sorted(VALID_EDUCATION_LEVELS),
        "valid_intent_types": sorted(VALID_INTENT_TYPES),
    }
    out = {"summary": summary, "queries": audit_entries}
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 60)
    print("=== Audit summary ===")
    print(f"  n_queries: {summary['n_queries_total']}")
    print(f"  n_success: {n_success}")
    print(f"  n_failure: {n_failure}")
    print(f"  n_with_anomalies: {n_anomalies} ({100*n_anomalies/max(1,n_success):.1f}%)")
    print(f"  n_clean: {summary['n_clean']} ({100*summary['n_clean']/max(1,n_success):.1f}%)")
    print()
    print("  age_group spontaneous values :")
    for v, c in summary["age_group_distribution"].items():
        marker = "✅" if v in VALID_AGE_GROUPS else "❌ HORS ENUM"
        print(f"    {marker} {v}: {c}")
    print()
    print("  education_level spontaneous values :")
    for v, c in summary["education_level_distribution"].items():
        marker = "✅" if v in VALID_EDUCATION_LEVELS else "❌ HORS ENUM"
        print(f"    {marker} {v}: {c}")
    print()
    print("  intent_type spontaneous values :")
    for v, c in summary["intent_type_distribution"].items():
        marker = "✅" if v in VALID_INTENT_TYPES else "❌ HORS ENUM"
        print(f"    {marker} {v}: {c}")
    print()
    print(f"✅ Audit sauvegardé → {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
