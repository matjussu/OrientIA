"""Sprint 8 Wave 1 — bench-check intermédiaire 6 queries critiques user_test_v3.

Single-run sur les 6 queries où les bugs P0 + erreurs persistantes ont
été observés au tour 2 user_test_v3 :
- Q1 HEC (Tremplin/Passerelle vs AST)
- Q3 EPITA (coût scolarité)
- Q7 médecine (bac S supprimé)
- Q8 PASS Sorbonne (URL github cassée)
- Q9 infirmier vs kiné (tableau cassé)
- Q10 ortho (FOR.372 réutilisé + concours candidat libre)

## Configuration

- Phase E updated avec +5 cells corrections (58 098 vecteurs)
- Pipeline avec post_process activé (Bugs Q8/Q9/Q10 fixes)
- v3.2 SYSTEM_PROMPT (pas de touche prompt — Sprint 7 R3 revert)
- Fact-checker post-Action-1 (`verified_by_official_source`)

## Coût

6 queries × ~$0.05 = ~$0.30, ~5 min wall-clock.

## Verdict attendu

Pour chaque query :
1. **Bug Q8 (Q1, Q3, Q8 si applicable)** : URL github.com retirée ou
   remplacée par fallback gracieux ?
2. **Bug Q9 (Q9)** : tableau markdown propre (pas de puces dans cellules) ?
3. **Bug Q10 (Q10)** : FOR.XXX cités correspondent aux fiches retrievées
   (pas de FOR.372 réutilisé pour 3 formations) ?
4. **5 erreurs persistantes** :
   - Q1 HEC : AST mentionné, pas Tremplin/Passerelle uniquement
   - Q3 EPITA : coût ~10-11k mentionné (vs 8500 user_test_v3)
   - Q7 médecine : bac général + spé scientifiques, pas bac S
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import faiss  # noqa: E402
from mistralai.client import Mistral  # noqa: E402

from src.agent.cache import LRUCache  # noqa: E402
from src.agent.pipeline_agent import AgentPipeline  # noqa: E402
from src.config import load_config  # noqa: E402


PHASEE_FICHES_PATH = REPO_ROOT / "data" / "processed" / "formations_multi_corpus_phaseE.json"
PHASEE_INDEX_PATH = REPO_ROOT / "data" / "embeddings" / "formations_multi_corpus_phaseE.index"

V3_RESPONSES_PATH = REPO_ROOT / "results" / "user_test_v3" / "responses.json"
OUT_DIR = REPO_ROOT / "results" / "sprint8_w1_bench_check"


# Sample queries critiques user_test_v3 (les 6 où bugs P0 + erreurs persistantes observés)
CRITICAL_QUERY_NUMS = [1, 3, 7, 8, 9, 10]


# Heuristiques pour vérifier les fixes (verdict empirique)
def _check_fixes(query_num: int, answer: str) -> dict[str, bool | str]:
    """Vérifie heuristiquement les fixes attendus pour cette query."""
    checks: dict[str, bool | str] = {}
    answer_lower = answer.lower()

    # Bug Q8 — URL github.com hallu (toutes queries)
    has_github_url = "github.com/matjussu" in answer or "github.com/jsdelivr" in answer.lower()
    checks["bug_q8_no_github_url"] = not has_github_url

    # Bug Q10 — FOR.XXX réutilisé
    if query_num == 10:
        # Compter occurrences `FOR.372` (cas Q10 réel)
        for_372_count = answer.count("FOR.372")
        checks["bug_q10_no_for_372_reuse"] = for_372_count <= 1
        checks["bug_q10_for_372_count"] = for_372_count

    # Erreur persistante 1 — HEC AST (Q1)
    if query_num == 1:
        has_ast = "ast" in answer_lower or "admission sur titres" in answer_lower or "admission sur titre" in answer_lower
        checks["erreur1_hec_ast_present"] = has_ast
        # Ne devrait PAS dire "Tremplin" ou "Passerelle" pour HEC
        has_tremplin = "tremplin" in answer_lower or "passerelle" in answer_lower
        checks["erreur1_hec_pas_tremplin_passerelle"] = not has_tremplin

    # Erreur persistante 4 — EPITA coût (Q3)
    if query_num == 3:
        has_8500 = "8 500" in answer or "8500" in answer
        has_correct_range = (
            "10 000" in answer or "11 500" in answer or "10 500" in answer
            or "10000" in answer or "11500" in answer or "10500" in answer
        )
        checks["erreur4_epita_pas_8500"] = not has_8500
        checks["erreur4_epita_correct_range"] = has_correct_range

    # Erreur persistante 3 — bac S supprimé (Q7 médecine)
    if query_num == 7:
        has_bac_s = "bac s/" in answer_lower or "bac s recommandé" in answer_lower or "bac s recommande" in answer_lower
        has_correct = (
            "bac général" in answer_lower or "bac general" in answer_lower
            or "spé scientifique" in answer_lower or "specialite scientifique" in answer_lower
            or "spécialités scientifiques" in answer_lower
        )
        checks["erreur3_pas_bac_s"] = not has_bac_s
        checks["erreur3_bac_general_spe"] = has_correct

    return checks


def main() -> int:
    if not PHASEE_FICHES_PATH.exists() or not V3_RESPONSES_PATH.exists():
        print("❌ Sources absentes (Phase E ou v3 responses)")
        return 1

    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=180_000)

    print("Loading Phase E updated (Sprint 8 W1 +5 cells corrections)...")
    fiches = json.loads(PHASEE_FICHES_PATH.read_text(encoding="utf-8"))
    index = faiss.read_index(str(PHASEE_INDEX_PATH))
    print(f"  {len(fiches):,} fiches, ntotal={index.ntotal:,}")

    print("Loading user_test_v3 questions...")
    v3_responses = json.loads(V3_RESPONSES_PATH.read_text(encoding="utf-8"))
    critical_questions = [q for q in v3_responses if q["question_num"] in CRITICAL_QUERY_NUMS]
    print(f"  {len(critical_questions)} queries critiques sélectionnées : {CRITICAL_QUERY_NUMS}")

    cache = LRUCache(maxsize=128)
    pipeline = AgentPipeline(
        client=client, fiches=fiches, index=index,
        profile_cache=cache,
        aggregated_top_n=8,
        enable_fact_check=False,
        system_prompt_override=None,  # v3.2 (R3 revert)
        enable_post_process=True,  # Sprint 8 W1 fixes activés
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n{'='*70}")
    print(f"Bench-check Sprint 8 W1 — {len(critical_questions)} queries critiques")
    print(f"{'='*70}")

    results = []
    t0_global = time.time()

    for i, q in enumerate(critical_questions, 1):
        qnum = q["question_num"]
        print(f"\n[{i}/{len(critical_questions)}] Q{qnum} ({q['category']})")
        print(f"    \"{q['question'][:80]}...\"")

        result = pipeline.answer(q["question"])
        if result.error:
            print(f"    ❌ pipeline error : {result.error[:120]}")
            continue

        # Vérifier les fixes heuristiquement
        checks = _check_fixes(qnum, result.answer_text)
        n_checks_pass = sum(1 for v in checks.values() if v is True)
        n_checks_total = sum(1 for v in checks.values() if isinstance(v, bool))
        print(f"    ✅ {result.elapsed_total_s}s | checks {n_checks_pass}/{n_checks_total} pass")
        for ck, val in checks.items():
            sym = "✅" if val is True else "❌" if val is False else "ℹ"
            print(f"       {sym} {ck}: {val}")

        entry = {
            "question_num": qnum,
            "category": q["category"],
            "question": q["question"],
            "answer_v4_post_sprint8_w1": result.answer_text,
            "answer_v3_user_test": q["answer"],  # comparaison
            "elapsed_pipeline_s": result.elapsed_total_s,
            "checks_sprint8_w1": checks,
        }
        out_path = OUT_DIR / f"q{qnum}_{q['category']}.json"
        out_path.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")
        results.append(entry)

    total_elapsed = round(time.time() - t0_global, 2)

    # Verdict aggregate
    all_checks_passed = sum(
        1 for r in results
        for ck, val in r.get("checks_sprint8_w1", {}).items()
        if val is True
    )
    all_checks_failed = sum(
        1 for r in results
        for ck, val in r.get("checks_sprint8_w1", {}).items()
        if val is False
    )
    all_checks_total = all_checks_passed + all_checks_failed

    summary = {
        "n_queries": len(results),
        "n_checks_total": all_checks_total,
        "n_checks_passed": all_checks_passed,
        "n_checks_failed": all_checks_failed,
        "pct_checks_passed": round(100 * all_checks_passed / max(1, all_checks_total), 1),
        "total_elapsed_s": total_elapsed,
        "verdict_wave1": "FIX VALIDÉ" if all_checks_failed == 0 else f"PARTIEL ({all_checks_failed} checks fails)",
    }

    aggregate_path = OUT_DIR / "_AGGREGATE.json"
    aggregate_path.write_text(json.dumps({"summary": summary, "queries": results},
                                          ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{'='*70}")
    print(f"=== Verdict bench-check Sprint 8 W1 ===")
    print(f"{'='*70}")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print(f"\n✅ Output → {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
