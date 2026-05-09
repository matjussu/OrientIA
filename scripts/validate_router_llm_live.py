"""Validation live du RouterLLM sur 10 questions diverses (Mistral Small).

Run manuel hors pytest. Coût ~$0.001 (10 calls Mistral Small).

Usage :
    cd ~/projets/OrientIA && source .venv/bin/activate
    python scripts/validate_router_llm_live.py

Critères pass (gate étape 3 du plan) :
- confidence moyenne ≥ 0.7
- latence p95 ≤ 1 s
- 0 exception non-rattrapée (toutes les questions retournent un RouteDecision)
- Routage cohérent sur les 10 questions (vérification visuelle)
"""
from __future__ import annotations

import os
import statistics
import sys
import time
from pathlib import Path

# Resolve project root et inject in PYTHONPATH si lancé direct.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mistralai.client import Mistral

from src.config import load_config  # noqa: E402
from src.rag.router_llm import RouterLLM  # noqa: E402


# 10 questions couvrant les 4 sub-indexes + cas adversariaux.
LIVE_QUESTIONS = [
    # 1-2 — formations + géographique fort
    ("Quelles écoles d'ingénieur en cybersécurité existent en Bretagne ?", "formations"),
    ("Combien de places en BUT informatique à Lyon ?", "formations"),
    # 3-4 — aides_territoires (CROUS + DROM)
    ("Combien coûte le logement CROUS à Lyon ?", "aides_territoires"),
    ("Quelles formations en Guadeloupe ?", "aides_territoires"),
    # 5-6 — statistiques (INSEE + APEC)
    ("Quel salaire après un Master Droit en région PACA ?", "statistiques"),
    ("Quel est le marché de l'emploi cadres en Bretagne ?", "statistiques"),
    # 7 — metiers
    ("Que fait un actuaire au quotidien ?", "metiers"),
    # 8 — superlatif → refus
    ("Quelle est la meilleure école de commerce en France ?", "REFUSAL"),
    # 9 — cross-domain → refus
    ("Comment soigner une angine ?", "REFUSAL"),
    # 10 — paraphrase CROUS sans le mot "CROUS"
    ("Combien ça coûte de vivre dans une chambre étudiante à Lyon ?", "aides_territoires"),
]


def main() -> int:
    cfg = load_config()
    if not cfg.mistral_api_key:
        print("ERREUR : MISTRAL_API_KEY absent du .env", file=sys.stderr)
        return 1

    client = Mistral(api_key=cfg.mistral_api_key)
    router = RouterLLM(client=client)

    latencies: list[float] = []
    confidences: list[float] = []
    fallbacks: int = 0
    refusals: int = 0
    print("=" * 80)
    print("VALIDATION LIVE RouterLLM — 10 questions, Mistral Small")
    print("=" * 80)

    for i, (question, expected_route) in enumerate(LIVE_QUESTIONS, start=1):
        t0 = time.time()
        try:
            decision = router.route(question)
        except Exception as e:
            print(f"\n[{i}/10] EXCEPTION non-rattrapée : {e}")
            return 2
        latency_s = time.time() - t0
        latencies.append(latency_s)
        confidences.append(decision.confidence)
        if decision.is_fallback:
            fallbacks += 1
        if decision.refusal_reason:
            refusals += 1

        print(f"\n[{i}/10] {question}")
        print(f"   → sub_indexes : {decision.sub_indexes}")
        print(f"   → criteria    : {decision.criteria}")
        print(f"   → domain_lock : {decision.domain_lock}")
        print(f"   → refusal     : {decision.refusal_reason}")
        print(f"   → top_k_over  : {decision.top_k_override}")
        print(f"   → confidence  : {decision.confidence:.2f}")
        print(f"   → fallback    : {decision.is_fallback}")
        print(f"   → latency     : {latency_s * 1000:.0f} ms")
        print(f"   → expected    : {expected_route}")

    print("\n" + "=" * 80)
    print("RÉSUMÉ")
    print("=" * 80)
    avg_conf = statistics.mean(confidences)
    p50 = statistics.median(latencies)
    p95 = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies)
    print(f"Confidence moyenne : {avg_conf:.2f}    (gate : ≥ 0.70)")
    print(f"Latence p50        : {p50 * 1000:.0f} ms")
    print(f"Latence p95        : {p95 * 1000:.0f} ms (gate : ≤ 1000 ms)")
    print(f"Fallbacks utilisés : {fallbacks} / 10")
    print(f"Refus structurés   : {refusals} / 10")

    pass_conf = avg_conf >= 0.70
    pass_latency = p95 <= 1.0
    pass_zero_exc = True  # déjà vérifié sinon return 2
    print()
    print(f"Confidence ≥ 0.70 : {'✓' if pass_conf else '✗'}")
    print(f"p95 ≤ 1 s         : {'✓' if pass_latency else '✗'}")
    print(f"Zéro exception    : {'✓' if pass_zero_exc else '✗'}")

    if pass_conf and pass_latency and pass_zero_exc:
        print("\nGATE ÉTAPE 3 PASS ✅")
        return 0
    print("\nGATE ÉTAPE 3 FAIL ❌")
    return 3


if __name__ == "__main__":
    sys.exit(main())
