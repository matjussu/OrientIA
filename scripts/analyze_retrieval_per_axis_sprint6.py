"""Sprint 6 — Analyse retrieval-side per-axe (Option A décomposition pp).

Demandée par Jarvis : pour chaque query × run du bench Sprint 6, identifier
la contribution de chaque axe au top-K retrieval et estimer leur poids dans
le pct_verified mesuré.

## Méthodologie Option A (retrieval-side, post-hoc)

Limites épistémiques explicites :
- C'est de la **corrélation, pas de la causalité**. La méthodo ground
  truth serait l'ablation (1 run par axe désactivé), mais coût ×6 vs
  l'attribution post-hoc retrieval-side.
- Le LLM gen peut citer une stat sourcée d'une fiche A même quand la
  fiche B (autre axe) était aussi présente dans le top-K. Ce qu'on
  mesure ici = "présence dans le top-K ET claim verifié corrélé", pas
  "axe causalement responsable du verified".
- Acceptable pour Sprint 6 (estimation directionnelle pour orientation
  Sprint 7). Pour ground truth → ablation 6 runs (1 baseline + 5 axe par
  axe désactivé) à faire post-Sprint 6 si gain global suspecté biaisé.

## Identification axes Sprint 6 vs anciens

Mapping `granularity` → axe Sprint 6 :

| Granularity | Axe Sprint 6 |
|---|---|
| `fap_region` | DARES re-agg (axe 1) |
| `formation_france`, `region_diplome` | inserjeunes (axe 3b) |
| `dispositif`, `voie` | financement (axe 4) |
| `territoire`, `synthese_cross` | DROM territorial (axe 2) |
| `bac_pro_domaine`, `cap_domaine`, `type_diplome_synthese` | voie pré-bac (axe 3a) |
| `fap`, `region` | DARES ancien (pre-Sprint-6) |
| autres / absents | base phaseB ou blocs RNCP (pre-Sprint-6) |

## Métriques par axe

Pour chaque axe Sprint 6, on calcule sur l'ensemble des 72 entries
(24 queries × 3 runs) :

- `n_queries_active` : nombre de queries où l'axe est présent dans top-K
- `pct_queries_active` : % du total
- `n_stats_top_k_active` : somme des stats où l'axe contribue au top-K
- `n_stats_verified_with_axis_active` : stats verified parmi les queries
  où l'axe contribue (corrélation indicative)
- `attribution_pp_estimate` : estimation grossière de la contribution
  pp au verified global, prorata `n_stats_verified_with_axis_active /
  n_stats_total`

Axe "muet" si `n_queries_active >= 3` mais `n_stats_verified_with_axis_active == 0`.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "results" / "sprint6_bench_apples_2026-04-27"
OUT_PATH = RESULTS_DIR / "_RETRIEVAL_ANALYSIS_PER_AXIS.json"


# Mapping granularity → axe Sprint 6
GRANULARITY_TO_AXIS: dict[str, str] = {
    # Axe 1 — DARES re-agg
    "fap_region": "axe1_dares_re_agg",
    # Axe 2 — DROM territorial
    "territoire": "axe2_drom_territorial",
    "synthese_cross": "axe2_drom_territorial",
    # Axe 3a — voie pré-bac
    "bac_pro_domaine": "axe3a_voie_pre_bac",
    "cap_domaine": "axe3a_voie_pre_bac",
    "type_diplome_synthese": "axe3a_voie_pre_bac",
    # Axe 3b — inserjeunes
    "formation_france": "axe3b_inserjeunes",
    "region_diplome": "axe3b_inserjeunes",
    # Axe 4 — financement
    "dispositif": "axe4_financement",
    "voie": "axe4_financement",
    # Pre-Sprint-6 (DARES ancien, blocs, formation base)
    "fap": "_pre_dares_global",
    "region": "_pre_dares_region",
}

SPRINT6_AXES = (
    "axe1_dares_re_agg",
    "axe2_drom_territorial",
    "axe3a_voie_pre_bac",
    "axe3b_inserjeunes",
    "axe4_financement",
)


def _classify_granularities(granularities: list[str]) -> set[str]:
    """Retourne l'ensemble des axes Sprint 6 actifs dans ce top-K."""
    axes_active: set[str] = set()
    for g in granularities:
        axe = GRANULARITY_TO_AXIS.get(g)
        if axe and axe in SPRINT6_AXES:
            axes_active.add(axe)
    return axes_active


def analyze_results(results_dir: Path = RESULTS_DIR) -> dict[str, Any]:
    """Charge les 3 runs + agrège la décomposition par axe."""
    if not results_dir.exists():
        raise FileNotFoundError(f"Results dir absent : {results_dir}")

    # Métriques globales
    n_total_entries = 0
    n_total_stats = 0
    n_total_verified = 0
    n_total_halluc = 0

    # Par axe
    per_axis: dict[str, dict[str, int]] = {
        axe: {
            "n_queries_active": 0,
            "n_stats_when_active": 0,
            "n_verified_when_active": 0,
            "n_halluc_when_active": 0,
        }
        for axe in SPRINT6_AXES
    }

    # Per-run details
    runs_breakdown: list[dict[str, Any]] = []

    for run_label in ["run1", "run2", "run3"]:
        all_path = results_dir / run_label / "_ALL_QUERIES.json"
        if not all_path.exists():
            print(f"⚠️  {all_path} absent, skip run {run_label}")
            continue

        data = json.loads(all_path.read_text(encoding="utf-8"))
        run_summary = data.get("summary", {})
        run_queries = data.get("queries", [])

        n_run_stats = run_summary.get("n_total_stats", 0)
        n_run_verified = run_summary.get("n_verified", 0)
        n_run_halluc = run_summary.get("n_hallucinated", 0)

        n_total_stats += n_run_stats
        n_total_verified += n_run_verified
        n_total_halluc += n_run_halluc

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

        runs_breakdown.append({
            "run": run_label,
            "n_queries": len(run_queries),
            "n_stats_total": n_run_stats,
            "pct_verified": run_summary.get("pct_verified"),
            "pct_hallucinated": run_summary.get("pct_hallucinated"),
        })

    # Calcul attribution pp et identification axes muets
    pct_verified_global = round(100 * n_total_verified / max(1, n_total_stats), 1)
    pct_halluc_global = round(100 * n_total_halluc / max(1, n_total_stats), 1)

    axes_breakdown: dict[str, dict[str, Any]] = {}
    for axe, stats in per_axis.items():
        n_active = stats["n_queries_active"]
        pct_active = round(100 * n_active / max(1, n_total_entries), 1)

        # Attribution pp grossière : si l'axe est dans top-K et la query a verified,
        # on attribue prorata (corrélation, pas causalité)
        pct_verified_when_active = round(
            100 * stats["n_verified_when_active"] / max(1, stats["n_stats_when_active"]),
            1,
        )

        # Estimation contribution pp : (n_verified_when_active * pct_active / 100) / n_total_stats
        # Logique : la fraction du global qui est attribuable à cet axe par corrélation présence top-K
        attribution_pp = round(
            100 * stats["n_verified_when_active"] / max(1, n_total_stats),
            2,
        )

        # Axe "muet" : actif >=3 queries mais 0 verified attribuable
        is_mute = n_active >= 3 and stats["n_verified_when_active"] == 0

        axes_breakdown[axe] = {
            **stats,
            "pct_queries_active": pct_active,
            "pct_verified_when_active": pct_verified_when_active,
            "attribution_pp_estimate": attribution_pp,
            "is_mute_candidate": is_mute,
        }

    analysis = {
        "method": "Option A retrieval-side (corrélation, pas causalité — "
                  "ablation ground truth manquante)",
        "n_total_entries": n_total_entries,
        "n_total_stats": n_total_stats,
        "n_total_verified": n_total_verified,
        "n_total_halluc": n_total_halluc,
        "pct_verified_global": pct_verified_global,
        "pct_halluc_global": pct_halluc_global,
        "runs_breakdown": runs_breakdown,
        "axes_breakdown": axes_breakdown,
        "caveat": (
            "Ces chiffres sont des estimations corrélationnelles : un axe "
            "présent dans le top-K et associé à des stats verified n'est "
            "pas pour autant la cause causale de ces verified. Le LLM gen "
            "peut citer une stat sourcée d'une fiche A (autre axe) même "
            "quand l'axe X est aussi présent dans le top-K. Ground truth "
            "= ablation 1 run/axe désactivé (×6 cost). Acceptable Sprint 6 "
            "pour orientation Sprint 7 (priorisation axes muets / axes "
            "fortement contributeurs)."
        ),
    }

    return analysis


def main() -> int:
    analysis = analyze_results()
    OUT_PATH.write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Print summary
    print("=" * 60)
    print("Sprint 6 — Analyse retrieval-side per-axe (Option A)")
    print("=" * 60)
    print(f"\nGlobal : {analysis['n_total_entries']} entries, "
          f"{analysis['n_total_stats']} stats")
    print(f"  pct_verified : {analysis['pct_verified_global']}% "
          f"({analysis['n_total_verified']}/{analysis['n_total_stats']})")
    print(f"  pct_halluc   : {analysis['pct_halluc_global']}% "
          f"({analysis['n_total_halluc']}/{analysis['n_total_stats']})")

    print("\nPer-axe breakdown (corrélation, pas causalité) :")
    print(f"{'Axe':<28} {'active%':>8} {'verif%when':>11} {'attrib_pp':>10} {'muet?':>7}")
    print("-" * 70)
    for axe in SPRINT6_AXES:
        b = analysis["axes_breakdown"][axe]
        muet = "🔇" if b["is_mute_candidate"] else "—"
        print(f"{axe:<28} {b['pct_queries_active']:>7}% "
              f"{b['pct_verified_when_active']:>10}% "
              f"{b['attribution_pp_estimate']:>9}pp "
              f"{muet:>7}")

    print(f"\nRuns IC95 :")
    for r in analysis["runs_breakdown"]:
        print(f"  {r['run']} : verified={r['pct_verified']}%, halluc={r['pct_hallucinated']}% "
              f"(n_stats={r['n_stats_total']})")

    print(f"\n✅ Output → {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
