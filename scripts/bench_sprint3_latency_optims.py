"""Bench latence avant/après — Sprint 3 axe B agentique.

Mesure l'impact des 3 optimisations latence livrées Sprint 3 :
- (2b) Profile caching in-memory : speedup sur queries répétées
- (2a) Parallel batching via ThreadPool : speedup sur N tasks indépendantes
- (2c) Streaming gen wrapper : prep Sprint 4 (pas de bench live, helper testé unit)

## Méthodologie

### Bench A : Caching profile speedup

10 queries baseline sample. Run 2 fois consécutives :
- 1ère passe : cold cache, mesure latence ProfileClarifier
- 2ème passe : warm cache (queries identiques), mesure speedup

### Bench B : Parallel fact-check speedup

5 claims fact-check (pré-définis pour avoir des sources cohérentes).
Run 2 modes :
- Sequential : 5 calls en série via FetchStatFromSource
- Parallel : 5 calls via parallel_map(max_workers=5)

Mesure speedup wall-clock.

## Output

`results/sprint3_latency_bench_2026-04-26.json`

## Coût

- Bench A : 10 queries × 1 call (warm n'appelle pas Mistral) ≈ $0.10
- Bench B : 5 claims × 2 (seq + par) = 10 calls ≈ $0.10
- Total : ~$0.20
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

from src.agent.cache import LRUCache  # noqa: E402
from src.agent.parallel import parallel_apply  # noqa: E402
from src.agent.tools.fetch_stat_from_source import FetchStatFromSource, Source  # noqa: E402
from src.agent.tools.profile_clarifier import Profile, ProfileClarifier  # noqa: E402
from src.config import load_config  # noqa: E402


# 10 queries pour bench A caching (mix baseline)
CACHING_QUERIES = [
    "Quelles formations en informatique en Île-de-France ?",
    "Comment se réorienter après une L1 droit ?",
    "Quel est le coût d'une école de commerce ?",
    "Que vais-je apprendre en BUT GEA ?",
    "Quels métiers vont recruter en 2030 ?",
    "Comment valider un titre RNCP par VAE ?",
    "Je suis en seconde, j'ai peur, que faire ?",
    "Mon fils veut faire du droit, combien ça coûte ?",
    "Salaire médian d'un développeur post M2 ?",
    "Logements CROUS à Bretagne ?",
]


# 5 claims + sources pour bench B parallel fact-check
FACT_CHECK_CASES = [
    {
        "claim": "Le titre de psychologue exige obligatoirement un master bac+5",
        "sources": [Source(
            id="rncp_blocs:RNCP38875",
            text="Le titre de psychologue est protégé en France et exige obligatoirement un master bac+5 niveau 7",
            domain="competences_certif",
        )],
    },
    {
        "claim": "Le BTS comptabilité valide 4 blocs de compétences principaux",
        "sources": [Source(
            id="rncp_blocs:RNCP35185",
            text="BTS Comptabilité Gestion comporte 4 blocs : contrôle gestion, fiscalité, paie, communication",
            domain="competences_certif",
        )],
    },
    {
        "claim": "Le coût moyen d'une école de commerce est 12 000€/an",
        "sources": [Source(
            id="formation:edhec_lille",
            text="EDHEC : frais de scolarité 18 500€/an pour le PGE Master in Management",
            domain="formation",
        )],
    },
    {
        "claim": "Les agents d'entretien (FAP T4Z) auront 488 700 postes à pourvoir d'ici 2030",
        "sources": [Source(
            id="dares_fap:T4Z",
            text="FAP T4Z agents d'entretien : 488 700 postes à pourvoir 2019-2030 (national)",
            domain="metier_prospective",
        )],
    },
    {
        "claim": "Le master MIAGE est accessible directement après le bac",
        "sources": [Source(
            id="formation:miage",
            text="Master MIAGE — Méthodes Informatiques Appliquées à la Gestion. Accès post-licence informatique (bac+3)",
            domain="formation",
        )],
    },
]


def _bench_caching(client: Mistral) -> dict:
    """Bench A : caching profile speedup."""
    print("\n" + "=" * 60)
    print("=== Bench A : Profile caching speedup ===")
    print("=" * 60)
    cache = LRUCache[str, Profile](maxsize=20)
    clarifier = ProfileClarifier(client=client, cache=cache)

    # 1ère passe : cold cache
    print("\n[Cold cache pass]")
    cold_latencies = []
    for i, q in enumerate(CACHING_QUERIES, 1):
        if i > 1:
            time.sleep(2)  # rate limit
        t0 = time.time()
        try:
            profile = clarifier.clarify(q)
            elapsed = round(time.time() - t0, 2)
            cold_latencies.append(elapsed)
            print(f"  [{i:2d}] {elapsed}s | age={profile.age_group}")
        except Exception as e:
            print(f"  [{i:2d}] ERR {type(e).__name__}: {e}")
            cold_latencies.append(0)

    # 2ème passe : warm cache (mêmes queries)
    print("\n[Warm cache pass]")
    warm_latencies = []
    for i, q in enumerate(CACHING_QUERIES, 1):
        t0 = time.time()
        profile = clarifier.clarify(q)
        elapsed = round(time.time() - t0, 4)
        warm_latencies.append(elapsed)
        print(f"  [{i:2d}] {elapsed}s | (cache hit)")

    cold_avg = sum(cold_latencies) / max(1, len(cold_latencies))
    warm_avg = sum(warm_latencies) / max(1, len(warm_latencies))
    speedup = cold_avg / max(0.0001, warm_avg)

    return {
        "n_queries": len(CACHING_QUERIES),
        "cold_avg_s": round(cold_avg, 2),
        "warm_avg_s": round(warm_avg, 4),
        "speedup_factor": round(speedup, 1),
        "cache_stats": cache.stats(),
        "cold_latencies": cold_latencies,
        "warm_latencies": warm_latencies,
    }


def _bench_parallel(client: Mistral) -> dict:
    """Bench B : parallel fact-check vs sequential."""
    print("\n" + "=" * 60)
    print("=== Bench B : Parallel fact-check speedup ===")
    print("=" * 60)
    fetcher = FetchStatFromSource(client=client)

    # Sequential
    print(f"\n[Sequential ({len(FACT_CHECK_CASES)} fact-checks)]")
    t0 = time.time()
    seq_results = []
    for i, case in enumerate(FACT_CHECK_CASES, 1):
        if i > 1:
            time.sleep(2)
        try:
            v = fetcher.verify(case["claim"], case["sources"])
            seq_results.append(v)
            print(f"  [{i}] verdict={v.verdict} conf={v.confidence}")
        except Exception as e:
            print(f"  [{i}] ERR {type(e).__name__}: {e}")
            seq_results.append(None)
    seq_total = round(time.time() - t0, 2)
    print(f"  Sequential total : {seq_total}s")

    # Pause entre les 2 modes
    print("\n[pause 5s]")
    time.sleep(5)

    # Parallel
    print(f"\n[Parallel max_workers=5]")
    t0 = time.time()
    try:
        par_results = parallel_apply(
            fetcher.verify,
            [(c["claim"], c["sources"]) for c in FACT_CHECK_CASES],
            max_workers=5,
            return_exceptions=True,
        )
        par_total = round(time.time() - t0, 2)
        for i, r in enumerate(par_results, 1):
            if isinstance(r, Exception):
                print(f"  [{i}] ERR {type(r).__name__}: {r}")
            else:
                print(f"  [{i}] verdict={r.verdict} conf={r.confidence}")
    except Exception as e:
        par_total = round(time.time() - t0, 2)
        par_results = []
        print(f"  Parallel batch failed: {e}")
    print(f"  Parallel total : {par_total}s")

    speedup = seq_total / max(0.001, par_total)
    return {
        "n_calls": len(FACT_CHECK_CASES),
        "sequential_total_s": seq_total,
        "parallel_total_s": par_total,
        "speedup_factor": round(speedup, 2),
        "max_workers": 5,
    }


def main() -> int:
    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=60_000)

    out_path = REPO_ROOT / "results" / "sprint3_latency_bench_2026-04-26.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print("Sprint 3 latency optims bench")
    print(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    bench_a = _bench_caching(client)
    print("\n[pause 5s]")
    time.sleep(5)
    bench_b = _bench_parallel(client)

    print("\n" + "=" * 60)
    print("=== SUMMARY Sprint 3 latency optims ===")
    print("=" * 60)
    print(f"\n(2b) Profile caching :")
    print(f"  Cold avg : {bench_a['cold_avg_s']}s")
    print(f"  Warm avg : {bench_a['warm_avg_s']}s")
    print(f"  Speedup : {bench_a['speedup_factor']}×")
    print(f"\n(2a) Parallel fact-check (max_workers=5) :")
    print(f"  Sequential : {bench_b['sequential_total_s']}s")
    print(f"  Parallel   : {bench_b['parallel_total_s']}s")
    print(f"  Speedup    : {bench_b['speedup_factor']}×")

    out = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "bench_a_caching": bench_a,
        "bench_b_parallel": bench_b,
    }
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ Output → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
