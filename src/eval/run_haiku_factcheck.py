"""Phase G.5 — run Claude Haiku fact-check on every blinded answer.

For each (question, label) pair in responses_blind.json, call
claude_fact_check (Phase E.3) with the answer text. We deliberately
pass retrieved=[] so all systems are judged on the SAME criterion :
"is this claim true in Claude's world knowledge ?". This neutralises
the structural asymmetry that favored our_rag in the regex version
(fact_check.py) where baseline systems couldn't possibly "verify"
any claim.

The output is a per-(qid, label) fact-check fraction in [0, 1] that
measures sourcing honesty, independent of the 6-criterion rubric.

Output :
  results/run_F_robust/scores_haiku_factcheck.json — list of
  {id, category, factcheck: {label: {score: f, claims: [...]}}}

Costs : ~$3-4 on Haiku 4.5 for 100 q × 7 labels = 700 calls.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from anthropic import Anthropic

from src.config import load_config
from src.eval.fact_check_claude import claude_fact_check


DEFAULT_RESPONSES = "results/run_F_robust/responses_blind.json"
DEFAULT_OUT = "results/run_F_robust/scores_haiku_factcheck.json"


def _score_claims(claims: list[dict]) -> float:
    """Return verified fraction in [0, 1]. Empty → 1.0 (neutral)."""
    if not claims:
        return 1.0
    verified = sum(
        1 for c in claims
        if c["status"].value in ("verified_fiche", "verified_general")
    )
    return verified / len(claims)


def run_haiku_factcheck(
    client: Anthropic,
    responses_blind: list[dict],
    save_path: str | Path,
    model: str = "claude-haiku-4-5-20251001",
) -> list[dict]:
    """Iterate over (qid, label) pairs, fact-check each answer, save
    incrementally. Resume-safe : existing {id, factcheck} entries skip
    the Haiku call for labels already done.
    """
    save_path = Path(save_path)
    results: list[dict] = []
    done: dict[str, set[str]] = {}
    if save_path.exists():
        try:
            existing = json.loads(save_path.read_text(encoding="utf-8"))
            if isinstance(existing, list):
                results = existing
                for e in existing:
                    done[e["id"]] = set(e.get("factcheck", {}).keys())
                total_done = sum(len(v) for v in done.values())
                print(f"  Resuming: {total_done} (id, label) pairs already done.")
        except Exception as exc:
            print(f"  (could not parse {save_path}: {exc} — starting fresh)")

    by_id = {e["id"]: e for e in results}

    for entry in responses_blind:
        qid, cat, answers = entry["id"], entry["category"], entry["answers"]
        fc_entry = by_id.get(qid) or {"id": qid, "category": cat, "factcheck": {}}
        if qid not in by_id:
            results.append(fc_entry)
            by_id[qid] = fc_entry

        for label, answer in sorted(answers.items()):
            if label in fc_entry["factcheck"]:
                continue
            claims = claude_fact_check(client, answer, retrieved=[], model=model)
            claim_summary = [
                {"text": c["text"], "type": c["type"],
                 "status": c["status"].value, "reason": c["reason"]}
                for c in claims
            ]
            fc_entry["factcheck"][label] = {
                "score": _score_claims(claims),
                "n_claims": len(claims),
                "claims": claim_summary,
            }
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_text(
                json.dumps(results, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--responses", default=DEFAULT_RESPONSES)
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--sample", type=int, default=0,
                        help="If > 0, only fact-check the first N questions.")
    args = parser.parse_args()

    cfg = load_config()
    responses = json.loads(Path(args.responses).read_text(encoding="utf-8"))
    if args.sample > 0:
        responses = responses[: args.sample]
        print(f"SAMPLE MODE — first {len(responses)} questions only")

    n_labels = len(responses[0]["answers"]) if responses else 0
    n_calls = len(responses) * n_labels
    print(f"Fact-checking {len(responses)} questions × {n_labels} labels = {n_calls} calls")
    print(f"Estimated Haiku cost : ~${n_calls * 0.005:.2f}")

    client = Anthropic(api_key=cfg.anthropic_api_key, timeout=120.0)
    run_haiku_factcheck(client, responses, save_path=Path(args.out))
    print(f"Done. Saved to {args.out}")


if __name__ == "__main__":
    main()
