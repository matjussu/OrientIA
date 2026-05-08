"""Évaluation systémique recall@k + MRR sur ground-truth 50q.

Sortir du N=13 spot-check pour avoir un set d'évaluation propre permettant
de prioriser Vague 3 (calendriers, URLs, aides) selon le gain réel par axe.

## Métriques mesurées

Pour chaque question :
- **recall@k** (k=1, 5, 10) : 1 si au moins 1 fiche du top-k matche
  `expected_domain` OU `expected_source`, 0 sinon. Aggregé en moyenne par
  catégorie et global.
- **MRR (Mean Reciprocal Rank)** : 1/rang de la première fiche matchante
  dans le top-10. 0 si aucune.
- **answer_keyword_match** : 1 si tous les `expected_keywords_in_answer`
  apparaissent dans la réponse (case-insensitive). Mesure de pertinence
  user-facing complémentaire au retrieval.

## Aggregation

- Par catégorie (lyceen_parcoursup, reorientation, metier, calendaire,
  geographique, vie_etudiante)
- Global (50 questions)

## Output

`results/eval_recall/<timestamp>.json` avec stats détaillées + récap par catégorie.

## Usage

```bash
# Eval sur prod actuelle
python scripts/eval_recall.py

# Eval sur corpus v7 (en construction)
ORIENTIA_CORPUS_PATH=data/processed/formations_v7.json \\
ORIENTIA_INDEX_PATH=data/embeddings/formations_v7.index \\
python scripts/eval_recall.py --out results/eval_recall/v7.json
```

Coût Mistral : ~$0.30-0.50 (50 questions × pipeline call).
Wall-clock : ~5-7 min (latency moyenne 8-9s/question).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from mistralai.client import Mistral

from src.config import load_config
from src.rag.factory import make_production_pipeline


DEFAULT_GOLDEN_PATH = PROJECT_ROOT / "data/golden_eval/golden_50.json"
DEFAULT_OUT_DIR = PROJECT_ROOT / "results/eval_recall"


def _matches_expected(fiche: dict, expected_domain: str | None, expected_source: str | None) -> bool:
    """True si la fiche matche le domain OU la source attendu(e)."""
    if expected_domain:
        if (fiche.get("domain") or "") == expected_domain:
            return True
    if expected_source:
        if (fiche.get("source") or "") == expected_source:
            return True
    # Si aucune cible précisée, le test est vide (tjs True) — convention :
    # une question sans expected_domain/source est juste un check keywords.
    if not expected_domain and not expected_source:
        return True
    return False


def _check_keywords(answer: str, expected_keywords: list[str]) -> tuple[bool, list[str]]:
    """Vérifie que tous les keywords attendus sont dans la réponse (case-insensitive).

    Returns (all_matched, missing_keywords).
    """
    if not expected_keywords:
        return True, []
    answer_lower = (answer or "").lower()
    missing = [k for k in expected_keywords if k.lower() not in answer_lower]
    return (len(missing) == 0, missing)


def _compute_mrr_for_question(top_sources: list[dict], expected_domain: str | None, expected_source: str | None) -> float:
    """MRR = 1/rang de la première fiche matchante (ou 0 si aucune)."""
    if not expected_domain and not expected_source:
        return 1.0  # convention : pas de cible → score parfait (placeholder neutre)
    for rank, src in enumerate(top_sources[:10], start=1):
        fiche = src.get("fiche") if "fiche" in src else src
        if _matches_expected(fiche, expected_domain, expected_source):
            return 1.0 / rank
    return 0.0


def evaluate(
    golden_path: Path,
    out_path: Path,
    corpus_path: Path | None = None,
    index_path: Path | None = None,
    sample: int | None = None,
) -> dict:
    """Run l'évaluation et écrit le rapport JSON."""
    cfg = load_config()
    if not cfg.mistral_api_key:
        raise RuntimeError("MISTRAL_API_KEY manquant")

    # Resolve paths via env vars (override priority)
    corpus_p = corpus_path or Path(os.environ.get(
        "ORIENTIA_CORPUS_PATH", "data/processed/formations.json"
    ))
    index_p = index_path or Path(os.environ.get(
        "ORIENTIA_INDEX_PATH", "data/embeddings/formations.index"
    ))

    print(f"=== Eval recall@k sur ground-truth ===")
    print(f"Corpus : {corpus_p}")
    print(f"Index  : {index_p}")
    print(f"Golden : {golden_path}")

    # Load corpus + golden
    with corpus_p.open() as f:
        fiches = json.load(f)
    with golden_path.open() as f:
        golden = json.load(f)

    questions = golden["questions"]
    if sample:
        questions = questions[:sample]
    print(f"N questions : {len(questions)}")

    # Build pipeline (production config)
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=120000)
    pipeline = make_production_pipeline(client, fiches)
    pipeline.load_index_from(str(index_p))

    # Per-question results
    results: list[dict] = []
    for i, q in enumerate(questions):
        qid = q["id"]
        question_text = q["question"]
        expected_domain = q.get("expected_domain")
        expected_source = q.get("expected_source")
        expected_keywords = q.get("expected_keywords_in_answer", [])

        print(f"\n[{i + 1}/{len(questions)}] {qid} ({q['category']}): {question_text[:60]}...")
        t0 = time.time()
        try:
            answer, top_sources = pipeline.answer(question_text)
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({
                "id": qid,
                "category": q["category"],
                "question": question_text,
                "error": str(e),
            })
            continue
        latency = time.time() - t0

        # Compute metrics
        # Recall@k : 1 si au moins 1 fiche du top-k matche
        recall_at = {}
        for k in (1, 5, 10):
            top_k = top_sources[:k]
            matched = any(
                _matches_expected(src.get("fiche") if "fiche" in src else src,
                                  expected_domain, expected_source)
                for src in top_k
            )
            recall_at[k] = int(matched)

        mrr = _compute_mrr_for_question(top_sources, expected_domain, expected_source)
        kw_match, missing_kw = _check_keywords(answer, expected_keywords)

        # Top-K domains pour debug
        top_5_summary = []
        for src in top_sources[:5]:
            fiche = src.get("fiche") if "fiche" in src else src
            top_5_summary.append({
                "domain": fiche.get("domain"),
                "source": fiche.get("source"),
                "nom": (fiche.get("nom") or fiche.get("libelle_metier") or fiche.get("id"))[:80] if isinstance(fiche.get("nom") or fiche.get("libelle_metier") or fiche.get("id"), str) else None,
            })

        result = {
            "id": qid,
            "category": q["category"],
            "question": question_text,
            "expected_domain": expected_domain,
            "expected_source": expected_source,
            "recall_at_1": recall_at[1],
            "recall_at_5": recall_at[5],
            "recall_at_10": recall_at[10],
            "mrr": round(mrr, 3),
            "answer_kw_match": int(kw_match),
            "missing_keywords": missing_kw,
            "latency_s": round(latency, 2),
            "top_5_summary": top_5_summary,
            "answer_excerpt": (answer or "")[:200],
        }
        results.append(result)

        print(f"  recall@1={recall_at[1]} @5={recall_at[5]} @10={recall_at[10]} MRR={mrr:.2f} kw_match={int(kw_match)} latency={latency:.1f}s")

    # Aggregation par catégorie + global
    categories = sorted(set(q["category"] for q in questions))
    summary_by_cat = {}
    for cat in categories:
        cat_results = [r for r in results if r.get("category") == cat and "error" not in r]
        if not cat_results:
            continue
        n = len(cat_results)
        summary_by_cat[cat] = {
            "n": n,
            "recall_at_1": round(sum(r["recall_at_1"] for r in cat_results) / n, 3),
            "recall_at_5": round(sum(r["recall_at_5"] for r in cat_results) / n, 3),
            "recall_at_10": round(sum(r["recall_at_10"] for r in cat_results) / n, 3),
            "mrr": round(sum(r["mrr"] for r in cat_results) / n, 3),
            "answer_kw_match": round(sum(r["answer_kw_match"] for r in cat_results) / n, 3),
            "avg_latency_s": round(sum(r["latency_s"] for r in cat_results) / n, 2),
        }

    n_ok = len([r for r in results if "error" not in r])
    n_err = len(results) - n_ok
    if n_ok > 0:
        ok_results = [r for r in results if "error" not in r]
        global_summary = {
            "n_total": len(results),
            "n_errors": n_err,
            "n_ok": n_ok,
            "recall_at_1": round(sum(r["recall_at_1"] for r in ok_results) / n_ok, 3),
            "recall_at_5": round(sum(r["recall_at_5"] for r in ok_results) / n_ok, 3),
            "recall_at_10": round(sum(r["recall_at_10"] for r in ok_results) / n_ok, 3),
            "mrr": round(sum(r["mrr"] for r in ok_results) / n_ok, 3),
            "answer_kw_match": round(sum(r["answer_kw_match"] for r in ok_results) / n_ok, 3),
            "avg_latency_s": round(sum(r["latency_s"] for r in ok_results) / n_ok, 2),
        }
    else:
        global_summary = {"n_total": len(results), "n_errors": n_err, "n_ok": 0}

    report = {
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "corpus_path": str(corpus_p),
            "index_path": str(index_p),
            "golden_path": str(golden_path),
            "n_questions": len(questions),
        },
        "global": global_summary,
        "by_category": summary_by_cat,
        "results": results,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # Print summary
    print("\n" + "=" * 70)
    print("RÉSUMÉ GLOBAL")
    print("=" * 70)
    if n_ok > 0:
        print(f"N questions        : {n_ok} (errors: {n_err})")
        print(f"Recall@1           : {global_summary['recall_at_1']:.1%}")
        print(f"Recall@5           : {global_summary['recall_at_5']:.1%}")
        print(f"Recall@10          : {global_summary['recall_at_10']:.1%}")
        print(f"MRR                : {global_summary['mrr']:.3f}")
        print(f"Answer keyword match : {global_summary['answer_kw_match']:.1%}")
        print(f"Avg latency        : {global_summary['avg_latency_s']:.1f}s")
    print(f"\nPar catégorie (recall@5):")
    for cat in categories:
        s = summary_by_cat.get(cat, {})
        if s:
            print(f"  {cat:25s} {s.get('n', 0):>3} questions  recall@5={s.get('recall_at_5', 0):.1%}  MRR={s.get('mrr', 0):.3f}")
    print(f"\nRapport écrit : {out_path}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Recall@k eval sur ground-truth 50q")
    parser.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN_PATH,
                        help=f"Path ground-truth JSON (default {DEFAULT_GOLDEN_PATH})")
    parser.add_argument("--out", type=Path, default=None,
                        help="Output JSON path (default results/eval_recall/<timestamp>.json)")
    parser.add_argument("--sample", type=int, default=None,
                        help="Limiter au sample N premières questions (debug rapide)")
    args = parser.parse_args()

    out_path = args.out
    if out_path is None:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
        out_path = DEFAULT_OUT_DIR / f"v6_baseline_{ts}.json"

    try:
        evaluate(args.golden, out_path, sample=args.sample)
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
