"""Test intégration ProfileClarifier sur 15 queries baseline subset balanced.

Sprint 1 axe B agentique — verdict empirique du ProfileClarifier face à
la diversité réelle du baseline 48 queries (PR #75).

## Subset balanced (15 queries)

- 3 PERSONAS v4 (formation-centric)
- 3 DARES dédiées (prospective)
- 3 Blocs RNCP dédiées (compétences)
- 3 User-naturel (multi-domain naturel)
- 3 Edge cases (conceptuel / court / stress)

## Output

`results/sprint1_profile_clarifier_integration_2026-04-26.json` —
profil extrait par query + analyse erreurs.

## Coût

~$0.10-0.15 (15 queries × ~3K tokens × $2-3/1M Mistral Large).
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
from src.config import load_config  # noqa: E402


# --- Subset balanced ---

INTEGRATION_QUERIES = [
    # 3 PERSONAS v4 (formation-centric)
    {
        "id": "p1_lila_q1",
        "suite": "personas_v4",
        "expected_age_group": "etudiant_l1_l3",
        "expected_intent_type": "info_metier_specifique",
        "text": "Quels sont les principaux débouchés après une licence de lettres modernes ?",
    },
    {
        "id": "p2_theo_q2",
        "suite": "personas_v4",
        "expected_age_group": "etudiant_l1_l3",
        "expected_intent_type": "reorientation_etude",
        "text": "Je n'aime pas du tout le droit, je ne veux pas redoubler. Quelles options pour me réorienter en cours d'année ?",
    },
    {
        "id": "p3_valerie_q1",
        "suite": "personas_v4",
        "expected_age_group": "parent_lyceen",
        "expected_intent_type": "info_metier_specifique",
        "text": "Quel est le coût moyen d'une année d'école de commerce privée pour mon fils ?",
    },
    # 3 DARES dédiées (prospective)
    {
        "id": "d1_q01_postes_pourvoir",
        "suite": "dares_dedie",
        "expected_intent_type": "info_metier_specifique",
        "text": "Quels métiers en 2030 vont recruter le plus de postes à pourvoir en France ?",
    },
    {
        "id": "d2_q05_btp_idf",
        "suite": "dares_dedie",
        "expected_intent_type": "info_metier_specifique",
        "text": "Quels métiers du bâtiment vont recruter le plus en Île-de-France d'ici 2030 ?",
    },
    {
        "id": "d3_q08_desequilibre",
        "suite": "dares_dedie",
        "expected_intent_type": "info_metier_specifique",
        "text": "Y a-t-il un déséquilibre potentiel sur le marché des conducteurs de véhicules d'ici 2030 ?",
    },
    # 3 Blocs dédiées (compétences)
    {
        "id": "b1_q01_BTS_compta",
        "suite": "blocs_dedie",
        "expected_intent_type": "info_metier_specifique",
        "text": "Quels blocs de compétences valide le BTS comptabilité ?",
    },
    {
        "id": "b2_q05_VAE",
        "suite": "blocs_dedie",
        "expected_intent_type": "demarche_administrative",
        "text": "Comment valider un titre RNCP par VAE par bloc ?",
    },
    {
        "id": "b3_q10_licence_pro",
        "suite": "blocs_dedie",
        "expected_intent_type": "info_metier_specifique",
        "text": "Quelles compétences acquises après une licence pro en communication ?",
    },
    # 3 User-naturel (multi-domain stress)
    {
        "id": "u1_lycee_reunion",
        "suite": "user_naturel",
        "expected_age_group": "lyceen_terminale",
        "expected_region": "La Réunion",
        "text": "Je suis lycéen à La Réunion, j'aimerais étudier le numérique en métropole. Quelles options s'offrent à moi ?",
    },
    {
        "id": "u2_reconversion_distrib",
        "suite": "user_naturel",
        "expected_age_group": "adulte_25_45",
        "expected_intent_type": "reconversion_pro",
        "text": "Je travaille dans la grande distribution depuis 8 ans, je veux changer complètement de secteur. Par où commencer ?",
    },
    {
        "id": "u3_cout_ecole_com",
        "suite": "user_naturel",
        "expected_intent_type": "info_metier_specifique",
        "text": "Combien faut-il prévoir financièrement pour 5 années d'études en école de commerce ?",
    },
    # 3 Edge cases
    {
        "id": "e1_conceptuel",
        "suite": "edge_case",
        "expected_intent_type": "conceptuel_definition",
        "text": "C'est quoi une licence ?",
    },
    {
        "id": "e2_query_courte",
        "suite": "edge_case",
        "expected_age_group": "etudiant_master",
        "expected_region": "Auvergne-Rhône-Alpes",  # Lyon → AURA
        "text": "M2 info Lyon",
    },
    {
        "id": "e3_stress_signal",
        "suite": "edge_case",
        "expected_urgent_concern": True,
        "text": "Je suis en seconde, j'ai vraiment peur de ne pas savoir quoi faire après le bac, je galère.",
    },
]


def main() -> int:
    cfg = load_config()
    if not cfg.mistral_api_key:
        print("❌ MISTRAL_API_KEY absent dans .env")
        return 1

    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=60_000)
    clarifier = ProfileClarifier(client=client)

    out_path = REPO_ROOT / "results" / "sprint1_profile_clarifier_integration_2026-04-26.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"ProfileClarifier integration test — {len(INTEGRATION_QUERIES)} queries")
    print("=" * 60)

    results = []
    n_success = 0
    n_age_match = 0
    n_intent_match = 0
    n_region_match = 0
    n_urgent_match = 0
    n_age_expected = 0
    n_intent_expected = 0
    n_region_expected = 0
    n_urgent_expected = 0

    t0_global = time.time()
    for i, q in enumerate(INTEGRATION_QUERIES, 1):
        print(f"\n[{i:2d}/{len(INTEGRATION_QUERIES)}] [{q['suite']:<13}] {q['id']}")
        print(f"    \"{q['text'][:90]}{'...' if len(q['text']) > 90 else ''}\"")

        # Sleep entre queries pour respecter rate limit Mistral
        if i > 1:
            time.sleep(3)

        t0 = time.time()
        # Retry avec backoff sur 429
        max_retries = 3
        last_error = None
        profile = None
        for retry in range(max_retries):
            try:
                profile = clarifier.clarify(q["text"])
                last_error = None
                break
            except Exception as e:
                last_error = e
                err_str = str(e).lower()
                if "429" in err_str or "rate" in err_str:
                    backoff = 5 * (retry + 1)
                    print(f"    ⏸️  rate limit retry {retry+1}/{max_retries}, sleep {backoff}s")
                    time.sleep(backoff)
                    continue
                else:
                    break
        if profile is not None:
            elapsed = round(time.time() - t0, 2)
            n_success += 1
            entry = {
                "id": q["id"],
                "suite": q["suite"],
                "query": q["text"],
                "elapsed_s": elapsed,
                "success": True,
                "profile": profile.to_dict(),
                "expected": {k: v for k, v in q.items() if k.startswith("expected_")},
            }
            print(f"    ✅ {elapsed}s | age={profile.age_group} | edu={profile.education_level} | intent={profile.intent_type}")
            print(f"       sectors={profile.sector_interest} region={profile.region!r} urgent={profile.urgent_concern} conf={profile.confidence}")

            # Match vs expected (when set)
            if "expected_age_group" in q:
                n_age_expected += 1
                if profile.age_group == q["expected_age_group"]:
                    n_age_match += 1
                else:
                    print(f"       ⚠️  age expected={q['expected_age_group']} got={profile.age_group}")
            if "expected_intent_type" in q:
                n_intent_expected += 1
                if profile.intent_type == q["expected_intent_type"]:
                    n_intent_match += 1
                else:
                    print(f"       ⚠️  intent expected={q['expected_intent_type']} got={profile.intent_type}")
            if "expected_region" in q:
                n_region_expected += 1
                if profile.region == q["expected_region"]:
                    n_region_match += 1
                else:
                    print(f"       ⚠️  region expected={q['expected_region']} got={profile.region}")
            if "expected_urgent_concern" in q:
                n_urgent_expected += 1
                if profile.urgent_concern == q["expected_urgent_concern"]:
                    n_urgent_match += 1
                else:
                    print(f"       ⚠️  urgent expected={q['expected_urgent_concern']} got={profile.urgent_concern}")
        else:
            elapsed = round(time.time() - t0, 2)
            err_msg = f"{type(last_error).__name__}: {last_error}" if last_error else "unknown_failure"
            print(f"    ❌ {elapsed}s | {err_msg[:200]}")
            entry = {
                "id": q["id"],
                "suite": q["suite"],
                "query": q["text"],
                "elapsed_s": elapsed,
                "success": False,
                "error": err_msg,
            }
        results.append(entry)

    total_elapsed = round(time.time() - t0_global, 2)
    avg_elapsed = round(total_elapsed / len(INTEGRATION_QUERIES), 2)

    summary = {
        "n_queries": len(INTEGRATION_QUERIES),
        "n_success": n_success,
        "n_failure": len(INTEGRATION_QUERIES) - n_success,
        "match_age_group": f"{n_age_match}/{n_age_expected}" if n_age_expected else "n/a",
        "match_intent_type": f"{n_intent_match}/{n_intent_expected}" if n_intent_expected else "n/a",
        "match_region": f"{n_region_match}/{n_region_expected}" if n_region_expected else "n/a",
        "match_urgent_concern": f"{n_urgent_match}/{n_urgent_expected}" if n_urgent_expected else "n/a",
        "total_elapsed_s": total_elapsed,
        "avg_elapsed_s": avg_elapsed,
        "model": clarifier.model,
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
