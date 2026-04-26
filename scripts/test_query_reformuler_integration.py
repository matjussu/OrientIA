"""Test intégration QueryReformuler — Sprint 2 axe B agentique.

Pipeline 2-stages live :
1. ProfileClarifier extrait Profile depuis query
2. QueryReformuler découpe query en N sub-queries selon Profile

Subset : 12 queries balanced du baseline (3 personas v4 + 3 DARES dédiées
+ 3 blocs dédiées + 3 user-naturel). Couvre les 4 sous-suites du
bench persona complet (PR #75 baseline).

## Output

`results/sprint2_query_reformuler_integration_2026-04-26.json`

## Coût

12 queries × 2 calls (clarify + reformulate) × ~$0.01 = ~$0.25 estimé.
Plus sleep ~3s entre queries → ~3-4 min total.
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

from src.agent.tools.profile_clarifier import ProfileClarifier  # noqa: E402
from src.agent.tools.query_reformuler import QueryReformuler  # noqa: E402
from src.config import load_config  # noqa: E402


# Subset balanced 12 queries (3 par sous-suite)
INTEGRATION_QUERIES = [
    # PERSONAS v4
    {"id": "p1_lila_q1", "suite": "personas_v4",
     "text": "Quels sont les principaux débouchés après une licence de lettres modernes ?"},
    {"id": "p2_theo_q2", "suite": "personas_v4",
     "text": "Je n'aime pas du tout le droit, je ne veux pas redoubler. Quelles options pour me réorienter en cours d'année ?"},
    {"id": "p3_emma_q1", "suite": "personas_v4",
     "text": "Quel est le salaire moyen d'un développeur débutant post M2 informatique ?"},
    # DARES dédiées (prospective)
    {"id": "d1_q01_postes_pourvoir", "suite": "dares_dedie",
     "text": "Quels métiers en 2030 vont recruter le plus de postes à pourvoir en France ?"},
    {"id": "d2_q02_perspectives_bretagne", "suite": "dares_dedie",
     "text": "Quelles sont les perspectives de recrutement en Bretagne d'ici 2030 ?"},
    {"id": "d3_q07_niveau_tension", "suite": "dares_dedie",
     "text": "Quel est le niveau de tension 2019 pour le métier d'enseignant ?"},
    # Blocs dédiées (compétences)
    {"id": "b1_q01_BTS_compta", "suite": "blocs_dedie",
     "text": "Quels blocs de compétences valide le BTS comptabilité ?"},
    {"id": "b2_q05_VAE", "suite": "blocs_dedie",
     "text": "Comment valider un titre RNCP par VAE par bloc ?"},
    {"id": "b3_q07_BUT_GEA", "suite": "blocs_dedie",
     "text": "Que permet de faire un BUT GEA dans la pratique ?"},
    # User-naturel (multi-domain)
    {"id": "u1_lycee_reunion", "suite": "user_naturel",
     "text": "Je suis lycéen à La Réunion, j'aimerais étudier le numérique en métropole. Quelles options s'offrent à moi ?"},
    {"id": "u2_reconversion_distrib", "suite": "user_naturel",
     "text": "Je travaille dans la grande distribution depuis 8 ans, je veux changer complètement de secteur. Par où commencer ?"},
    {"id": "u3_cout_ecole_com", "suite": "user_naturel",
     "text": "Combien faut-il prévoir financièrement pour 5 années d'études en école de commerce ?"},
]


def main() -> int:
    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=60_000)
    clarifier = ProfileClarifier(client=client)
    reformuler = QueryReformuler(client=client)

    out_path = REPO_ROOT / "results" / "sprint2_query_reformuler_integration_2026-04-26.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"QueryReformuler integration — {len(INTEGRATION_QUERIES)} queries")
    print("=" * 60)

    results = []
    n_success = 0
    n_failure = 0
    total_subqs = 0
    target_corpus_counts: dict[str, int] = {}

    t0_global = time.time()
    for i, q in enumerate(INTEGRATION_QUERIES, 1):
        print(f"\n[{i:2d}/{len(INTEGRATION_QUERIES)}] [{q['suite']:<13}] {q['id']}")
        print(f"    \"{q['text'][:80]}{'...' if len(q['text']) > 80 else ''}\"")

        if i > 1:
            time.sleep(2.5)

        t0 = time.time()
        try:
            profile = clarifier.clarify(q["text"])
            time.sleep(1)  # brief pause between calls
            plan = reformuler.reformulate(q["text"], profile)
            elapsed = round(time.time() - t0, 2)
            n_success += 1
            print(f"    ✅ {elapsed}s | profile age={profile.age_group} intent={profile.intent_type}")
            print(f"       → {len(plan.sub_queries)} sub-queries :")
            for sq in plan.sub_queries:
                print(f"         [{sq.priority}] [{sq.target_corpus:<20}] {sq.text[:60]}")
                target_corpus_counts[sq.target_corpus] = target_corpus_counts.get(sq.target_corpus, 0) + 1
                total_subqs += 1
            if plan.strategy_note:
                print(f"       Strategy: {plan.strategy_note[:80]}")

            results.append({
                "id": q["id"],
                "suite": q["suite"],
                "query": q["text"],
                "elapsed_s": elapsed,
                "success": True,
                "profile": profile.to_dict(),
                "plan": plan.to_dict(),
            })
        except Exception as e:
            elapsed = round(time.time() - t0, 2)
            print(f"    ❌ {elapsed}s | {type(e).__name__}: {str(e)[:120]}")
            n_failure += 1
            results.append({
                "id": q["id"],
                "suite": q["suite"],
                "query": q["text"],
                "elapsed_s": elapsed,
                "success": False,
                "error": f"{type(e).__name__}: {e}",
            })

    total = round(time.time() - t0_global, 2)
    avg = round(total / len(INTEGRATION_QUERIES), 2)

    summary = {
        "n_queries": len(INTEGRATION_QUERIES),
        "n_success": n_success,
        "n_failure": n_failure,
        "avg_elapsed_s": avg,
        "total_elapsed_s": total,
        "total_sub_queries": total_subqs,
        "avg_sub_queries_per_query": round(total_subqs / max(1, n_success), 2),
        "target_corpus_distribution": dict(sorted(target_corpus_counts.items(), key=lambda x: -x[1])),
        "model": reformuler.model,
    }

    out = {"summary": summary, "queries": results}
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 60)
    print("=== Summary ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print(f"\n✅ Output → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
