"""Sprint 7 — Analyse retrieval-side per-axe et per-mode (Option A décomposition).

Étend `analyze_retrieval_per_axis_sprint6.py` avec :
- Décomposition par mode (Baseline vs Both)
- Comptabilisation `verified_strict` vs `verified_by_official_source`
  pour mesurer la contribution Action 1 (unmute axe 4)
- Tracker `critic_n_modifications` pour mesurer impact critic loop

## Mapping granularité → axe Sprint 6 (rappel)

| Granularity | Axe Sprint 6 |
|---|---|
| `fap_region` | DARES re-agg (axe 1) |
| `formation_france`, `region_diplome`, `formation_region_diplome` | inserjeunes (axe 3b) |
| `dispositif`, `voie` | financement (axe 4) |
| `territoire`, `synthese_cross` | DROM territorial (axe 2) |
| `bac_pro_domaine`, `cap_domaine`, `type_diplome_synthese` | voie pré-bac (axe 3a) |
| `fap`, `region` | DARES ancien (pre-Sprint-6) |
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "results" / "sprint7_bench_final_2026-04-27"


GRANULARITY_TO_AXIS: dict[str, str] = {
    "fap_region": "axe1_dares_re_agg",
    "territoire": "axe2_drom_territorial",
    "synthese_cross": "axe2_drom_territorial",
    "bac_pro_domaine": "axe3a_voie_pre_bac",
    "cap_domaine": "axe3a_voie_pre_bac",
    "type_diplome_synthese": "axe3a_voie_pre_bac",
    "formation_france": "axe3b_inserjeunes",
    "region_diplome": "axe3b_inserjeunes",
    "formation_region_diplome": "axe3b_inserjeunes",  # NEW Sprint 7 Action 4
    "dispositif": "axe4_financement",
    "voie": "axe4_financement",
}

SPRINT6_AXES = (
    "axe1_dares_re_agg",
    "axe2_drom_territorial",
    "axe3a_voie_pre_bac",
    "axe3b_inserjeunes",
    "axe4_financement",
)


def _classify_granularities(granularities: list[str]) -> set[str]:
    axes_active: set[str] = set()
    for g in granularities:
        axe = GRANULARITY_TO_AXIS.get(g)
        if axe and axe in SPRINT6_AXES:
            axes_active.add(axe)
    return axes_active


def _analyze_mode(mode_dir: Path) -> dict[str, Any]:
    """Charge les 3 runs d'un mode + agrège per-axe."""
    if not mode_dir.exists():
        return {"error": f"Mode dir absent : {mode_dir}"}

    n_total_entries = 0
    n_total_stats = 0
    n_total_verified = 0
    n_total_strict = 0
    n_total_by_source = 0
    n_total_halluc = 0
    n_total_disclaimer = 0
    total_critic_modifs = 0

    per_axis: dict[str, dict[str, int]] = {
        axe: {
            "n_queries_active": 0,
            "n_stats_when_active": 0,
            "n_verified_when_active": 0,
            "n_halluc_when_active": 0,
        }
        for axe in SPRINT6_AXES
    }

    for run_label in ["run1", "run2", "run3"]:
        all_path = mode_dir / run_label / "_ALL_QUERIES.json"
        if not all_path.exists():
            continue

        data = json.loads(all_path.read_text(encoding="utf-8"))
        run_summary = data.get("summary", {})
        run_queries = data.get("queries", [])

        n_total_stats += run_summary.get("n_total_stats", 0)
        n_total_verified += run_summary.get("n_verified", 0)
        n_total_strict += run_summary.get("n_verified_strict", 0)
        n_total_by_source += run_summary.get("n_verified_by_source", 0)
        n_total_halluc += run_summary.get("n_hallucinated", 0)
        n_total_disclaimer += run_summary.get("n_with_disclaimer", 0)
        total_critic_modifs += run_summary.get("total_critic_modifications", 0)

        for entry in run_queries:
            n_total_entries += 1
            grans = entry.get("granularities_top_k", [])
            axes_active = _classify_granularities(grans)
            fc_summary = entry.get("fact_check_summary") or {}
            n_stats_q = fc_summary.get("n_stats_total", 0)
            n_verified_q = fc_summary.get("n_verified", 0)
            n_halluc_q = fc_summary.get("n_hallucinated", 0)

            for axe in axes_active:
                per_axis[axe]["n_queries_active"] += 1
                per_axis[axe]["n_stats_when_active"] += n_stats_q
                per_axis[axe]["n_verified_when_active"] += n_verified_q
                per_axis[axe]["n_halluc_when_active"] += n_halluc_q

    # Calculs derivés
    pct_verified_global = round(100 * n_total_verified / max(1, n_total_stats), 1)
    pct_halluc_global = round(100 * n_total_halluc / max(1, n_total_stats), 1)
    pct_by_source_share = round(100 * n_total_by_source / max(1, n_total_verified), 1) if n_total_verified else 0.0

    axes_breakdown: dict[str, dict[str, Any]] = {}
    for axe, stats in per_axis.items():
        n_active = stats["n_queries_active"]
        pct_active = round(100 * n_active / max(1, n_total_entries), 1)
        pct_verified_when_active = round(
            100 * stats["n_verified_when_active"] / max(1, stats["n_stats_when_active"]),
            1,
        )
        attribution_pp = round(100 * stats["n_verified_when_active"] / max(1, n_total_stats), 2)
        is_mute = n_active >= 3 and stats["n_verified_when_active"] == 0

        axes_breakdown[axe] = {
            **stats,
            "pct_queries_active": pct_active,
            "pct_verified_when_active": pct_verified_when_active,
            "attribution_pp_estimate": attribution_pp,
            "is_mute_candidate": is_mute,
        }

    return {
        "n_total_entries": n_total_entries,
        "n_total_stats": n_total_stats,
        "n_total_verified": n_total_verified,
        "n_total_verified_strict": n_total_strict,
        "n_total_verified_by_source": n_total_by_source,
        "n_total_halluc": n_total_halluc,
        "n_total_disclaimer": n_total_disclaimer,
        "pct_verified_global": pct_verified_global,
        "pct_halluc_global": pct_halluc_global,
        "pct_by_source_share_of_verified": pct_by_source_share,
        "total_critic_modifications": total_critic_modifs,
        "axes_breakdown": axes_breakdown,
    }


def main() -> int:
    if not RESULTS_DIR.exists():
        print(f"❌ Results dir absent : {RESULTS_DIR}")
        return 1

    print("=" * 70)
    print("Sprint 7 — Analyse retrieval-side per-axe (Option A) × 2 modes")
    print("=" * 70)

    analysis = {
        "method": "Option A retrieval-side (corrélation, pas causalité — "
                  "ablation ground truth manquante). Décomposition per-axe + per-mode.",
        "modes": {
            "baseline": _analyze_mode(RESULTS_DIR / "mode_baseline"),
            "both": _analyze_mode(RESULTS_DIR / "mode_both"),
        },
    }

    # Verdict delta cumul Sprint 7
    bl = analysis["modes"]["baseline"]
    bo = analysis["modes"]["both"]

    delta = {
        "delta_pct_verified": round(bo["pct_verified_global"] - bl["pct_verified_global"], 1),
        "delta_pct_halluc": round(bo["pct_halluc_global"] - bl["pct_halluc_global"], 1),
        "delta_n_by_source": bo["n_total_verified_by_source"] - bl["n_total_verified_by_source"],
        "critic_modifs_in_both": bo["total_critic_modifications"],
    }
    analysis["delta_both_vs_baseline"] = delta

    out_path = RESULTS_DIR / "_RETRIEVAL_ANALYSIS_PER_AXIS_SPRINT7.json"
    out_path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")

    # Print summary
    print(f"\n--- Mode Baseline (v3.2 + critic OFF) ---")
    print(f"  Total : {bl['n_total_entries']} entries, {bl['n_total_stats']} stats")
    print(f"  pct_verified : {bl['pct_verified_global']}% "
          f"({bl['n_total_verified']} verified, {bl['n_total_verified_strict']} strict + "
          f"{bl['n_total_verified_by_source']} by_source)")
    print(f"  pct_halluc : {bl['pct_halluc_global']}%")

    print(f"\n--- Mode Both (v3.3 strict R1-R6 + critic ON) ---")
    print(f"  Total : {bo['n_total_entries']} entries, {bo['n_total_stats']} stats")
    print(f"  pct_verified : {bo['pct_verified_global']}% "
          f"({bo['n_total_verified']} verified, {bo['n_total_verified_strict']} strict + "
          f"{bo['n_total_verified_by_source']} by_source)")
    print(f"  pct_halluc : {bo['pct_halluc_global']}%")
    print(f"  critic modifications totales : {bo['total_critic_modifications']}")

    print(f"\n--- DELTA Both vs Baseline ---")
    print(f"  delta verified : {delta['delta_pct_verified']:+.1f}pp")
    print(f"  delta halluc : {delta['delta_pct_halluc']:+.1f}pp")
    print(f"  delta n_by_source : +{delta['delta_n_by_source']}")

    print(f"\n--- Per-axe breakdown ---")
    print(f"{'Axe':<28} {'BL act%':>8} {'BL verif%':>10} {'BO act%':>8} {'BO verif%':>10}")
    print("-" * 70)
    for axe in SPRINT6_AXES:
        bl_a = bl["axes_breakdown"][axe]
        bo_a = bo["axes_breakdown"][axe]
        print(f"{axe:<28} {bl_a['pct_queries_active']:>7}% "
              f"{bl_a['pct_verified_when_active']:>9}% "
              f"{bo_a['pct_queries_active']:>7}% "
              f"{bo_a['pct_verified_when_active']:>9}%")

    print(f"\n✅ Output → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
