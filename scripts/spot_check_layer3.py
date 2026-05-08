"""Phase 2.5 honnêteté — passe Layer3 LLM Mistral Small sur les réponses
déjà générées par le mini-bench (pas de re-génération, juste analyse).

Compare la liste de claims jugés douteux par Layer3 vs ce que le validator
couches 1+2 a flagué (rules + corpus_check + presence). L'objectif : voir si
Layer3 trouve des hallu sémantiques que les couches déterministes ratent.

Usage :
    python scripts/spot_check_layer3.py \\
        --in results/mini_bench/phase2_factory.json \\
        --out results/mini_bench/phase2_layer3_audit.json

Coût : ~$0.001 / réponse (Mistral Small) × 18 = ~$0.02. Latency ~2-4s/réponse.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mistralai.client import Mistral  # noqa: E402

from src.config import load_config  # noqa: E402
from src.validator.layer3 import Layer3Validator  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in", dest="in_path", type=Path, required=True,
                        help="Chemin vers un mini-bench JSON existant")
    parser.add_argument("--out", dest="out_path", type=Path, required=True,
                        help="Chemin du JSON audit Layer3 à produire")
    args = parser.parse_args()

    cfg = load_config()
    if not cfg.mistral_api_key:
        raise RuntimeError("MISTRAL_API_KEY missing — required for Layer3.")
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=120000)
    layer3 = Layer3Validator(client=client)

    bench = json.loads(args.in_path.read_text(encoding="utf-8"))
    results = bench.get("unimodal_results", [])
    print(f"[layer3-audit] processing {len(results)} responses from {args.in_path.name}")

    audit_records = []
    n_with_warnings = 0
    n_warnings_total = 0

    for i, rec in enumerate(results, 1):
        qid = rec["id"]
        question = rec["question"]
        response = rec.get("response") or ""
        if not response:
            print(f"  [{i}/{len(results)}] {qid}: SKIP (no response)")
            continue
        t0 = time.time()
        warnings = layer3.check(response)
        elapsed = round(time.time() - t0, 2)
        warning_dicts = [
            {"claim": w.claim, "reason": w.reason, "severity": w.severity}
            for w in warnings
        ]
        n_warnings = len(warning_dicts)
        n_warnings_total += n_warnings
        if n_warnings > 0:
            n_with_warnings += 1
        print(f"  [{i}/{len(results)}] {qid}: {n_warnings} warnings ({elapsed}s)")
        for w in warning_dicts:
            print(f"      ! {w['claim'][:80]}... → {w['reason'][:80]}")
        audit_records.append({
            "id": qid,
            "category": rec.get("category"),
            "intent_target": rec.get("intent_target"),
            "question": question,
            "response_excerpt": response[:300] + ("..." if len(response) > 300 else ""),
            "n_layer3_warnings": n_warnings,
            "layer3_warnings": warning_dicts,
            "layer3_latency_s": elapsed,
            "couche12_honesty_score": rec.get("honesty_score"),
            "couche12_flagged": rec.get("flagged"),
            "couche12_n_failed_claims": rec.get("n_failed_claims"),
        })

    out_payload = {
        "metadata": {
            "source_bench": str(args.in_path),
            "source_phase": bench.get("metadata", {}).get("phase"),
            "n_processed": len(audit_records),
            "n_with_layer3_warnings": n_with_warnings,
            "n_layer3_warnings_total": n_warnings_total,
            "model": layer3.model,
        },
        "audit_records": audit_records,
    }
    args.out_path.parent.mkdir(parents=True, exist_ok=True)
    args.out_path.write_text(json.dumps(out_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[layer3-audit] Saved to {args.out_path}")
    print(f"[layer3-audit] Summary: {n_with_warnings}/{len(audit_records)} responses have Layer3 warnings, "
          f"total {n_warnings_total} claims flagged.")


if __name__ == "__main__":
    main()
