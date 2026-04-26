"""Bench A/B Mistral Medium vs Large pour ProfileClarifier.

TODO Sprint 1 prio 1 (cf docs/SPRINT1_PROFILE_CLARIFIER_VERDICT.md §3.6) :
ProfileClarifier seul ~2-5s sur Mistral Large. Si Sprint 2-4 empilent
4 tools sur Large = 12-25s end-to-end (UX limite). Test si Medium
suffit pour ProfileClarifier (gain potentiel 5x latence).

## Méthodo A/B

Mêmes 15 queries du subset Sprint 1 integration (3 personas + 3 DARES
+ 3 blocs + 3 user-naturel + 3 edge cases). Run 2 fois :
- Variant `large` : `mistral-large-latest`
- Variant `medium` : `mistral-medium-latest`

Compare :
- Latence par query
- Match age_group / intent_type / region / urgent_concern vs expected
- Distribution profile extracted (sanity)
- Anomalies enum spontanés

## Critère succès

Medium ship-able si :
- match_age_group >= Large match_age_group - 10pp
- match_region >= Large match_region - 10pp
- match_urgent >= Large match_urgent - 10pp
- avg latence Medium <= Large / 3

Si succès → switch ProfileClarifier sur Medium par défaut, capitaliser
gain UX downstream Sprints 3-4.

## Coût

15 queries × 2 variants × ~$0.005 (Medium $0.003, Large $0.008) = ~$0.20.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mistralai.client import Mistral  # noqa: E402

from src.agent.tools.profile_clarifier import (  # noqa: E402
    ProfileClarifier,
    VALID_AGE_GROUPS,
    VALID_EDUCATION_LEVELS,
    VALID_INTENT_TYPES,
)
from src.config import load_config  # noqa: E402

# Reprise du subset Sprint 1 integration
from scripts.test_profile_clarifier_integration import INTEGRATION_QUERIES  # noqa: E402


VARIANTS = {
    "large": "mistral-large-latest",
    "medium": "mistral-medium-latest",
}


def _bench_variant(client: Mistral, variant_label: str, model: str) -> dict:
    """Run all 15 queries for one model variant. Return summary + per-query."""
    clarifier = ProfileClarifier(client=client, model=model)
    print(f"\n{'='*60}\n=== Variant: {variant_label} ({model}) ===\n{'='*60}")

    per_query = []
    n_success = 0
    n_age_match = 0
    n_intent_match = 0
    n_region_match = 0
    n_urgent_match = 0
    n_age_expected = 0
    n_intent_expected = 0
    n_region_expected = 0
    n_urgent_expected = 0
    total_latency = 0.0
    n_anomalies = 0

    for i, q in enumerate(INTEGRATION_QUERIES, 1):
        if i > 1:
            time.sleep(2.5)
        t0 = time.time()
        try:
            profile = clarifier.clarify(q["text"])
            elapsed = round(time.time() - t0, 2)
            total_latency += elapsed
            n_success += 1
            print(f"  [{i:2d}] {q['id']:<32} {elapsed}s | age={profile.age_group} intent={profile.intent_type}")

            # Anomalie check
            has_anomaly = (
                profile.age_group not in VALID_AGE_GROUPS
                or profile.education_level not in VALID_EDUCATION_LEVELS
                or profile.intent_type not in VALID_INTENT_TYPES
            )
            if has_anomaly:
                n_anomalies += 1

            entry = {
                "id": q["id"], "suite": q["suite"], "query": q["text"],
                "elapsed_s": elapsed, "success": True,
                "profile": profile.to_dict(),
                "expected": {k: v for k, v in q.items() if k.startswith("expected_")},
                "has_anomaly": has_anomaly,
            }

            # Match counts
            if "expected_age_group" in q:
                n_age_expected += 1
                if profile.age_group == q["expected_age_group"]:
                    n_age_match += 1
            if "expected_intent_type" in q:
                n_intent_expected += 1
                if profile.intent_type == q["expected_intent_type"]:
                    n_intent_match += 1
            if "expected_region" in q:
                n_region_expected += 1
                if profile.region == q["expected_region"]:
                    n_region_match += 1
            if "expected_urgent_concern" in q:
                n_urgent_expected += 1
                if profile.urgent_concern == q["expected_urgent_concern"]:
                    n_urgent_match += 1
        except Exception as e:
            elapsed = round(time.time() - t0, 2)
            total_latency += elapsed
            print(f"  [{i:2d}] {q['id']:<32} {elapsed}s | ❌ {type(e).__name__}: {str(e)[:80]}")
            entry = {
                "id": q["id"], "suite": q["suite"], "query": q["text"],
                "elapsed_s": elapsed, "success": False,
                "error": f"{type(e).__name__}: {e}",
            }
        per_query.append(entry)

    summary = {
        "variant": variant_label,
        "model": model,
        "n_queries": len(INTEGRATION_QUERIES),
        "n_success": n_success,
        "n_failure": len(INTEGRATION_QUERIES) - n_success,
        "n_anomalies_enum": n_anomalies,
        "match_age_group": f"{n_age_match}/{n_age_expected}",
        "match_intent_type": f"{n_intent_match}/{n_intent_expected}",
        "match_region": f"{n_region_match}/{n_region_expected}",
        "match_urgent_concern": f"{n_urgent_match}/{n_urgent_expected}",
        "match_age_pct": round(100*n_age_match/max(1,n_age_expected),1),
        "match_intent_pct": round(100*n_intent_match/max(1,n_intent_expected),1),
        "avg_latency_s": round(total_latency/len(INTEGRATION_QUERIES),2),
        "total_latency_s": round(total_latency,2),
    }
    return {"summary": summary, "per_query": per_query}


def main() -> int:
    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=60_000)

    out_path = REPO_ROOT / "results" / "sprint2_profile_clarifier_medium_vs_large_2026-04-26.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Bench A/B Mistral Medium vs Large pour ProfileClarifier")
    print(f"15 queries × 2 variants = 30 calls")

    # Run Large d'abord (référence existante Sprint 1)
    large_result = _bench_variant(client, "large", VARIANTS["large"])
    # Pause inter-variants
    print("\n[pause 10s avant medium variant]")
    time.sleep(10)
    medium_result = _bench_variant(client, "medium", VARIANTS["medium"])

    # Comparison
    s_large = large_result["summary"]
    s_medium = medium_result["summary"]
    print("\n" + "=" * 60)
    print("=== Comparison summary ===")
    print(f"  {'Metric':<25} {'Large':<15} {'Medium':<15} {'Delta':<15}")
    print(f"  {'-'*25} {'-'*15} {'-'*15} {'-'*15}")
    for metric in ["match_age_pct", "match_intent_pct", "avg_latency_s",
                   "n_success", "n_anomalies_enum"]:
        l_val = s_large.get(metric, "?")
        m_val = s_medium.get(metric, "?")
        if isinstance(l_val, (int, float)) and isinstance(m_val, (int, float)):
            delta = round(m_val - l_val, 2)
            sign = "+" if delta > 0 else ""
            print(f"  {metric:<25} {l_val:<15} {m_val:<15} {sign}{delta}")
        else:
            print(f"  {metric:<25} {l_val:<15} {m_val:<15}")

    # Ship criteria
    crit_age = s_medium["match_age_pct"] >= s_large["match_age_pct"] - 10
    crit_lat = s_medium["avg_latency_s"] <= s_large["avg_latency_s"] / 3
    success_age = s_medium["n_success"] >= s_large["n_success"] - 1
    print()
    print("=== Critères succès ship Medium ===")
    print(f"  match_age >= Large-10pp : {crit_age} (Medium={s_medium['match_age_pct']} vs Large-10={s_large['match_age_pct']-10})")
    print(f"  avg_latency <= Large/3 : {crit_lat} (Medium={s_medium['avg_latency_s']}s vs Large/3={round(s_large['avg_latency_s']/3,2)}s)")
    print(f"  success_count >= Large-1 : {success_age} (Medium={s_medium['n_success']}, Large={s_large['n_success']})")
    decision = "✅ SHIP Medium" if (crit_age and crit_lat and success_age) else "❌ KEEP Large"
    print(f"\n  Décision : {decision}")

    out = {
        "variants": {
            "large": large_result,
            "medium": medium_result,
        },
        "comparison": {
            "delta_match_age_pp": s_medium["match_age_pct"] - s_large["match_age_pct"],
            "delta_match_intent_pp": s_medium["match_intent_pct"] - s_large["match_intent_pct"],
            "delta_latency_s": s_medium["avg_latency_s"] - s_large["avg_latency_s"],
            "latency_speedup_factor": round(s_large["avg_latency_s"]/max(0.001, s_medium["avg_latency_s"]), 2),
            "criteria_age": crit_age,
            "criteria_latency": crit_lat,
            "criteria_success": success_age,
            "decision_ship_medium": (crit_age and crit_lat and success_age),
        },
    }
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ Output → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
