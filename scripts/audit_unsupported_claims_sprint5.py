"""Audit qualitatif claims unsupported — Sprint 5 Phase 3.

Sample 10 claims "halluc" StatFactChecker (Sprint 5 apples-to-apples)
+ 10 claims "unsupported" FetchStatFromSource (Sprint 4 bench original).
Catégorisation via Claude Sonnet 4.5 (TOOL eval épistémiquement
séparé, hors stack prod Mistral souverain).

3 catégories :
- A) LLM hallucine : claim dans answer pas dans sources retrievées
- B) LLM-judge trop strict : claim valide, source utilise synonyme
- C) Sources insuffisantes : claim valide, top-K ne couvre pas

## Output

`results/sprint5_audit_qualitatif_2026-04-26.json`

## Coût

~20 evals × ~3K tokens × Claude Sonnet 4.5 ($3/1M input + $15/1M output)
= ~$0.20 max.
"""
from __future__ import annotations

import json
import random
import sys
import time
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from anthropic import Anthropic  # noqa: E402

from src.config import load_config  # noqa: E402

SPRINT5_RUNS_DIR = REPO_ROOT / "results" / "sprint5_bench_apples_2026-04-26"
SPRINT4_BENCH_DIR = REPO_ROOT / "results" / "bench_agent_pipeline_2026-04-26" / "run1"
OUT_PATH = REPO_ROOT / "results" / "sprint5_audit_qualitatif_2026-04-26.json"


AUDIT_PROMPT_TEMPLATE = """Tu es auditeur qualitatif de claims unsupported / hallucinés dans un système RAG agentique d'orientation académique français (OrientIA).

Contexte du claim :
- Method : {method}
- Verdict du fact-checker : {verdict}
- Question utilisateur : {query}
- Réponse RAG complète (extrait) :
---
{answer_excerpt}
---
- Claim spécifique sous audit : "{claim}"
- Sources retrievées (top-K excerpts) :
---
{sources_excerpt}
---

Évalue ce claim et catégorise SA cause d'être flaggé "{verdict}" en UNE des 3 catégories :

- **A) LLM hallucine** : le claim n'est PAS dans les sources retrievées (le LLM a fabriqué le chiffre / l'affirmation).
- **B) LLM-judge trop strict** : le claim est VALIDE mais formulé différemment des sources (synonyme, paraphrase, calcul dérivé).
- **C) Sources insuffisantes** : le claim est PROBABLEMENT VRAI mais aucune des sources retrievées ne le couvre (gap data).

Réponds STRICTEMENT en JSON :
{{
  "category": "A" | "B" | "C",
  "reason": "<1-2 phrases d'explication, max 50 mots>",
  "confidence": 0.0-1.0
}}

Réponds UNIQUEMENT le JSON, rien d'autre."""


def _load_sprint5_halluc_claims() -> list[dict]:
    """Sample claims marked 'unsourced_unsafe' (= halluc) across 3 Sprint 5 runs.

    NOTE : StatFactChecker utilise les verdicts {`verified`,
    `unsourced_with_disclaimer`, `unsourced_unsafe`}. `unsourced_unsafe`
    correspond conceptuellement aux 'hallucinated' (claim avec stat
    précise sans source/disclaimer = potentiel halluc).
    """
    claims = []
    for run in ["run1", "run2", "run3"]:
        run_dir = SPRINT5_RUNS_DIR / run
        if not run_dir.exists():
            continue
        for query_file in run_dir.glob("query_*.json"):
            data = json.loads(query_file.read_text(encoding="utf-8"))
            for stat in data.get("fact_check_stats", []) or []:
                if stat.get("verdict") == "unsourced_unsafe":
                    claims.append({
                        "method": "StatFactChecker (Sprint 5 apples-to-apples)",
                        "verdict": "unsourced_unsafe",
                        "run": run,
                        "query_id": data.get("query_id"),
                        "suite": data.get("suite"),
                        "query": data.get("query_text"),
                        "answer_text": data.get("answer_text", ""),
                        "claim": stat.get("context", "") or stat.get("stat_text", ""),
                        "stat_text": stat.get("stat_text", ""),
                        "stat_value": stat.get("stat_value"),
                        "source_excerpt": stat.get("source_excerpt", ""),
                    })
    return claims


def _load_sprint4_unsupported_claims() -> list[dict]:
    """Sample claims marked 'unsupported' from Sprint 4 bench (FetchStatFromSource)."""
    claims = []
    if not SPRINT4_BENCH_DIR.exists():
        return claims
    for query_file in SPRINT4_BENCH_DIR.glob("query_*.json"):
        if query_file.name == "_ALL_QUERIES.json":
            continue
        data = json.loads(query_file.read_text(encoding="utf-8"))
        for fc in data.get("fact_check_results", []) or []:
            if fc.get("verdict") == "unsupported":
                claims.append({
                    "method": "FetchStatFromSource (Sprint 4 bench)",
                    "verdict": "unsupported",
                    "query_id": data.get("query_id"),
                    "suite": data.get("suite"),
                    "query": data.get("query"),
                    "answer_text": data.get("answer_text", ""),
                    "claim": fc.get("claim", ""),
                    "reason": fc.get("reason", ""),
                    "source_excerpt": fc.get("source_excerpt", ""),
                    "confidence": fc.get("confidence"),
                })
    return claims


def main() -> int:
    cfg = load_config()
    if not cfg.anthropic_api_key:
        print("❌ ANTHROPIC_API_KEY absent")
        return 1
    client = Anthropic(api_key=cfg.anthropic_api_key)

    # Sample
    sprint5_claims = _load_sprint5_halluc_claims()
    sprint4_claims = _load_sprint4_unsupported_claims()
    print(f"Total halluc claims Sprint 5 disponibles : {len(sprint5_claims)}")
    print(f"Total unsupported claims Sprint 4 disponibles : {len(sprint4_claims)}")

    # Random sample 10 each
    random.seed(42)
    sprint5_sample = random.sample(sprint5_claims, min(10, len(sprint5_claims)))
    sprint4_sample = random.sample(sprint4_claims, min(10, len(sprint4_claims)))

    all_samples = sprint5_sample + sprint4_sample
    print(f"\nAudit qualitatif : {len(all_samples)} claims (10 Sprint 5 halluc + 10 Sprint 4 unsupported)")
    print("=" * 60)

    audit_results = []
    for i, claim in enumerate(all_samples, 1):
        if i > 1:
            time.sleep(1)
        # Compose prompt
        answer_excerpt = (claim.get("answer_text") or "")[:1500]
        sources_excerpt = (claim.get("source_excerpt") or "")[:600]
        prompt = AUDIT_PROMPT_TEMPLATE.format(
            method=claim["method"],
            verdict=claim["verdict"],
            query=claim["query"],
            answer_excerpt=answer_excerpt,
            claim=claim.get("claim", "")[:300],
            sources_excerpt=sources_excerpt or "(aucune source verbatim attachée)",
        )

        print(f"\n[{i:2d}/{len(all_samples)}] [{claim['method'][:25]:<25}] {claim.get('query_id', '?')}")
        print(f"    claim: {(claim.get('claim') or claim.get('stat_text', ''))[:120]}")

        try:
            response = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
            output = response.content[0].text.strip()
            # Clean potential markdown fences
            if output.startswith("```"):
                output = output.split("```")[1].lstrip("json").strip()
            audit = json.loads(output)
            print(f"    → {audit.get('category')} (conf={audit.get('confidence')}) {audit.get('reason', '')[:100]}")
        except Exception as e:
            audit = {"error": f"{type(e).__name__}: {e}"}
            print(f"    ❌ {audit['error'][:100]}")

        audit_results.append({
            "method": claim["method"],
            "verdict_original": claim["verdict"],
            "query_id": claim.get("query_id"),
            "claim_excerpt": (claim.get("claim") or claim.get("stat_text", ""))[:300],
            "category": audit.get("category"),
            "audit_reason": audit.get("reason"),
            "confidence": audit.get("confidence"),
        })

    # Aggregate distribution
    sprint5_categories = Counter(r["category"] for r in audit_results
                                  if r["method"].startswith("StatFactChecker") and r.get("category"))
    sprint4_categories = Counter(r["category"] for r in audit_results
                                  if r["method"].startswith("FetchStatFromSource") and r.get("category"))
    overall = Counter(r["category"] for r in audit_results if r.get("category"))

    print("\n" + "=" * 60)
    print("=== Distribution catégories ===")
    print(f"\nSprint 5 StatFactChecker halluc (n=10) :")
    for cat in ["A", "B", "C"]:
        c = sprint5_categories.get(cat, 0)
        print(f"  {cat}) {c} ({100*c/max(1,sum(sprint5_categories.values())):.0f}%)")
    print(f"\nSprint 4 FetchStatFromSource unsupported (n=10) :")
    for cat in ["A", "B", "C"]:
        c = sprint4_categories.get(cat, 0)
        print(f"  {cat}) {c} ({100*c/max(1,sum(sprint4_categories.values())):.0f}%)")
    print(f"\nOverall (n=20) :")
    for cat in ["A", "B", "C"]:
        c = overall.get(cat, 0)
        print(f"  {cat}) {c} ({100*c/max(1,sum(overall.values())):.0f}%)")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out = {
        "summary": {
            "n_sprint5_halluc_audited": 10,
            "n_sprint4_unsupported_audited": 10,
            "sprint5_distribution": dict(sprint5_categories),
            "sprint4_distribution": dict(sprint4_categories),
            "overall_distribution": dict(overall),
        },
        "evaluations": audit_results,
    }
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ Output → {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
