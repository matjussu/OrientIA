"""Bench empirique post-chantiers 1+2 — réponse à la critique expert #3.

Passe les 15 questions baseline (10 hallu observées + 5 stress-test jury)
à travers le pipeline POST-purge prompt + retry-with-hint + SELECT bypass
pour mesurer empiriquement le delta hallu vs pré-chantiers.

## Usage

```bash
cd ~/projets/OrientIA && source .venv/bin/activate
python -m scripts.bench_audit_post_chantiers \\
  --questions data/audit/hallu_questions_baseline.json \\
  --out results/audit_post_chantiers_2026-05-03.md
```

## Coût estimé

- Pipeline = 1-2 calls Mistral medium par question (retry si validator
  flag failed_claims) + validator déterministe (rules + corpus_check)
- 15 questions × ~1.5 calls ≈ 22-25 calls Mistral medium
- Coût : ~$0.30-0.45
- Durée : ~3-5 min

## Output

Rapport markdown structuré avec :
- Métriques agrégées (% via_select, retry_stability moyenne, etc.)
- Réponse complète par question
- Comparaison avant/après chantiers (hallu pré-existantes vs sortie actuelle)
- Verdict qualitatif simple (PROGRESSE / STABLE / RÉGRESSE) — Matteo audit manuel
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from mistralai.client import Mistral

from src.config import load_config
from src.rag.pipeline import OrientIAPipeline
from src.validator import Layer3Validator, Validator


FICHES_PATH = "data/processed/formations.json"
INDEX_PATH = "data/embeddings/formations.index"


def _build_pipeline(client: Mistral, fiches: list[dict]) -> OrientIAPipeline:
    """Instancie le pipeline avec validator + use_intent (SELECT bypass actif)
    + use_mmr. Le retry-with-hint loop se déclenche automatiquement si
    validator flag des failed_claims (chantier 1.B).

    Layer3 LLM (Mistral Small) activé par défaut depuis Sprint refonte
    2026-05-05. Gated par intent côté validator (LAYER3_INTENTS allowlist :
    factual_pointed, geographic, comparaison, realisme). Pour les autres
    intents (passerelles/decouverte/conceptual/general), layer3 est skipped
    pour économiser coût LLM (~$0.001/call) et latence (+2-4s).
    """
    # Layer3 — ping de santé Mistral Small au démarrage. Si fail, fallback
    # graceful sur couches 1+2 (rules + corpus_check + presence).
    print("Ping Mistral Small pour layer 3...")
    layer3 = Layer3Validator(client=client, model="mistral-small-latest")
    try:
        test = client.chat.complete(
            model="mistral-small-latest",
            max_tokens=10,
            messages=[{"role": "user", "content": "ok"}],
        )
        sample = test.choices[0].message.content[:30] if test.choices else "no content"
        print(f"  ✓ Mistral Small OK ({sample!r}...)")
    except Exception as e:
        print(f"  ✗ Mistral Small fail : {type(e).__name__}: {e}")
        print("  → Layer3 désactivée, fallback couches 1+2 uniquement")
        layer3 = None

    validator = Validator(fiches=fiches, layer3=layer3)
    pipeline = OrientIAPipeline(
        client=client,
        fiches=fiches,
        use_mmr=True,
        use_intent=True,
        validator=validator,
    )
    if Path(INDEX_PATH).exists():
        pipeline.load_index_from(INDEX_PATH)
    else:
        raise RuntimeError(f"FAISS index missing at {INDEX_PATH}. "
                           f"Build with: python -m src.rag.embeddings")
    return pipeline


def _format_question_block(idx: int, q: dict, result: dict) -> str:
    """Formate un bloc markdown par question."""
    lines = [
        f"### Q{idx} ({q['id']}) — {q.get('category', '?')}",
        "",
        f"**Question** : {q['text']}",
        "",
    ]
    # Hallu observées pré-chantiers (si dispo)
    if q.get("hallu_observees_pre_purge"):
        lines.append("**Hallu observées pré-chantiers** :")
        for h in q["hallu_observees_pre_purge"]:
            lines.append(f"  - {h}")
        lines.append("")
    if q.get("expected_behavior"):
        lines.append(f"**Expected behavior** : {q['expected_behavior']}")
        lines.append("")
    if q.get("trap_jury"):
        lines.append(f"**Trap jury** : {q['trap_jury']}")
        lines.append("")

    # Stats pipeline
    lines.append("**Stats pipeline** :")
    lines.append(f"  - latence : {result['latency_s']:.1f}s")
    lines.append(f"  - via_select (chantier 2) : {result.get('via_select', False)}")
    if result.get("select_reason"):
        lines.append(f"  - select_reason : {result['select_reason']}")
    if result.get("retries_attempted") is not None:
        lines.append(f"  - retries_attempted : {result['retries_attempted']}")
        lines.append(f"  - retry_stability : {result.get('retry_stability', 1.0):.2f}")
        lines.append(f"  - needs_audit : {result.get('needs_audit', False)}")
    if result.get("retry_skipped_reason"):
        lines.append(f"  - retry_skipped_reason : {result['retry_skipped_reason']}")
    if result.get("honesty_score") is not None:
        lines.append(f"  - honesty_score : {result['honesty_score']:.2f}")
    if result.get("failed_claims_count") is not None:
        lines.append(f"  - failed_claims (final) : {result['failed_claims_count']}")
    lines.append("")

    # Réponse Mistral
    lines.append("**Réponse pipeline** :")
    lines.append("```")
    answer = result.get("answer") or "(error)"
    if len(answer) > 4000:
        answer = answer[:4000] + "\n... [truncated]"
    lines.append(answer)
    lines.append("```")
    lines.append("")
    if result.get("error"):
        lines.append(f"**ERROR** : {result['error']}")
        lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def _run_one(pipeline: OrientIAPipeline, question_text: str) -> dict:
    """Lance pipeline.answer() et collecte les métadonnées d'audit."""
    t0 = time.time()
    result: dict = {"answer": None, "error": None, "latency_s": 0.0}
    try:
        answer, _top = pipeline.answer(question_text)
        result["answer"] = answer
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"
    result["latency_s"] = round(time.time() - t0, 2)

    # Collecte métadonnées des chantiers
    if pipeline.last_select_result is not None:
        result["via_select"] = pipeline.last_select_result.via_select
        result["select_reason"] = pipeline.last_select_result.reason
    else:
        result["via_select"] = False

    if pipeline.last_retry_metadata is not None:
        meta = pipeline.last_retry_metadata
        result["retries_attempted"] = meta.get("retries_attempted")
        result["retry_stability"] = meta.get("retry_stability")
        result["needs_audit"] = meta.get("needs_audit")
        result["retry_skipped_reason"] = meta.get("retry_skipped_reason")

    if pipeline.last_validation is not None:
        result["honesty_score"] = pipeline.last_validation.honesty_score
        result["failed_claims_count"] = (
            len(pipeline.last_validation.corpus_warnings)
            + len(pipeline.last_validation.layer3_warnings)
        )
    return result


def _aggregate_stats(results: list[tuple[dict, dict]]) -> dict:
    """Calcule les métriques agrégées sur tous les résultats."""
    n = len(results)
    if n == 0:
        return {}

    via_select_count = sum(1 for _, r in results if r.get("via_select"))
    retry_attempted_count = sum(1 for _, r in results if r.get("retries_attempted"))
    needs_audit_count = sum(1 for _, r in results if r.get("needs_audit"))
    error_count = sum(1 for _, r in results if r.get("error"))

    latencies = [r["latency_s"] for _, r in results]
    avg_latency = sum(latencies) / n
    max_latency = max(latencies)

    honesty_scores = [
        r["honesty_score"] for _, r in results
        if r.get("honesty_score") is not None
    ]
    avg_honesty = sum(honesty_scores) / len(honesty_scores) if honesty_scores else None

    failed_claims_total = sum(
        r.get("failed_claims_count", 0) or 0 for _, r in results
    )

    return {
        "n_questions": n,
        "n_via_select": via_select_count,
        "pct_via_select": round(via_select_count / n * 100, 1),
        "n_retry_attempted": retry_attempted_count,
        "pct_retry_attempted": round(retry_attempted_count / n * 100, 1),
        "n_needs_audit": needs_audit_count,
        "n_error": error_count,
        "avg_latency_s": round(avg_latency, 2),
        "max_latency_s": round(max_latency, 2),
        "avg_honesty_score": round(avg_honesty, 3) if avg_honesty is not None else None,
        "failed_claims_total": failed_claims_total,
        "failed_claims_avg_per_question": round(failed_claims_total / n, 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--questions",
        default="data/audit/hallu_questions_baseline.json",
        help="Path to questions JSON (default: hallu_questions_baseline.json)",
    )
    parser.add_argument(
        "--out",
        default=f"results/audit_post_chantiers_2026-05-03.md",
        help="Output markdown report path",
    )
    parser.add_argument(
        "--first", type=int, default=0,
        help="Limit to first N questions (for quick test)",
    )
    args = parser.parse_args()

    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=120000)

    print(f"Loading fiches from {FICHES_PATH}...")
    fiches = json.loads(Path(FICHES_PATH).read_text(encoding="utf-8"))
    print(f"  {len(fiches)} fiches loaded")

    print(f"Building pipeline (validator + use_intent + use_mmr)...")
    pipeline = _build_pipeline(client, fiches)

    print(f"Loading questions from {args.questions}...")
    questions = json.loads(Path(args.questions).read_text(encoding="utf-8"))["questions"]
    if args.first > 0:
        questions = questions[:args.first]
    print(f"  {len(questions)} questions to bench")
    print()

    # Run bench
    results: list[tuple[dict, dict]] = []
    for i, q in enumerate(questions, 1):
        print(f"[{i:2d}/{len(questions)}] {q['id']:25s} — {q['text'][:55]}...")
        r = _run_one(pipeline, q["text"])
        select_marker = " 🎯SELECT" if r.get("via_select") else ""
        retry_marker = (
            f" 🔁retry={r.get('retries_attempted', 0)}/stab={r.get('retry_stability', 1):.1f}"
            if r.get("retries_attempted") else ""
        )
        audit_marker = " ⚠️AUDIT" if r.get("needs_audit") else ""
        err_marker = f" ❌{r['error']}" if r.get("error") else ""
        print(
            f"   → {r['latency_s']:5.1f}s | "
            f"failed={r.get('failed_claims_count', '?')} | "
            f"honesty={r.get('honesty_score', '?'):.2f}"
            if r.get('honesty_score') is not None else "honesty=?"
        )
        print(f"   {select_marker}{retry_marker}{audit_marker}{err_marker}")
        results.append((q, r))

    # Aggregate stats
    stats = _aggregate_stats(results)

    # Build report
    out_lines = [
        f"# Bench audit post-chantiers 1+2 (2026-05-03)",
        "",
        f"**Source** : `{args.questions}`",
        f"**Pipeline** : OrientIAPipeline(use_mmr=True, use_intent=True, validator=Validator)",
        f"**Modèle** : Mistral medium (génération) + Mistral-embed (retrieve)",
        "",
        "## Métriques agrégées",
        "",
        f"| Métrique | Valeur |",
        f"|---|---|",
        f"| Questions testées | {stats['n_questions']} |",
        f"| **Via SELECT (chantier 2)** | {stats['n_via_select']} ({stats['pct_via_select']}%) |",
        f"| Retry-with-hint déclenché | {stats['n_retry_attempted']} ({stats['pct_retry_attempted']}%) |",
        f"| Needs audit (retry instable) | {stats['n_needs_audit']} |",
        f"| Erreurs pipeline | {stats['n_error']} |",
        f"| Latence moyenne | {stats['avg_latency_s']}s |",
        f"| Latence max | {stats['max_latency_s']}s |",
        f"| Honesty score moyen | {stats['avg_honesty_score']} |",
        f"| Failed claims total (validator) | {stats['failed_claims_total']} |",
        f"| Failed claims moy/question | {stats['failed_claims_avg_per_question']} |",
        "",
        "## Lecture",
        "",
        "- **Honesty score 1.0** = parfait (aucune affirmation flaguée par validator).",
        "- **Honesty score < 0.5** = au moins 1 corpus_warning/layer3_warning grave.",
        "- **via_select=True** = SELECT bypass déclenché (zéro hallu chiffres garantie).",
        "- **needs_audit=True** = retry-with-hint a cassé >50% claims validés au tour 1 (à inspecter).",
        "",
        "## Réponses détaillées par question",
        "",
    ]
    for i, (q, r) in enumerate(results, 1):
        out_lines.append(_format_question_block(i, q, r))

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(out_lines), encoding="utf-8")

    print()
    print(f"=== Bench terminé ===")
    print(f"  via_select   : {stats['n_via_select']}/{stats['n_questions']} ({stats['pct_via_select']}%)")
    print(f"  retry        : {stats['n_retry_attempted']}/{stats['n_questions']} ({stats['pct_retry_attempted']}%)")
    print(f"  needs_audit  : {stats['n_needs_audit']}")
    print(f"  honesty avg  : {stats['avg_honesty_score']}")
    print(f"  latency avg  : {stats['avg_latency_s']}s (max {stats['max_latency_s']}s)")
    print(f"  errors       : {stats['n_error']}")
    print()
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
