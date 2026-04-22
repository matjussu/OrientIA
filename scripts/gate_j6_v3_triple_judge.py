"""Gate J+6 v3 — triple-judge sur réponses post-Validator V2 + Policy V3."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from gate_j6_triple_judge import ask_claude, ask_gpt4o, ask_mistral_large, build_user_prompt

from anthropic import Anthropic
from openai import OpenAI
from mistralai.client import Mistral

from src.config import load_config


INPUT_PATH = Path("results/gate_j6/responses_validator_v3_active.json")
OUT_DIR = Path("results/gate_j6/judges_v3")
RAW_PATH = OUT_DIR / "judge_responses_v3.json"
AGG_PATH = OUT_DIR / "scores_aggregated_v3.json"


def main() -> None:
    config = load_config()
    claude = Anthropic(api_key=config.anthropic_api_key)
    gpt = OpenAI(api_key=config.openai_api_key)
    mistral = Mistral(api_key=config.mistral_api_key, timeout_ms=120000)

    responses = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    judges = [("claude", ask_claude, claude), ("gpt_4o", ask_gpt4o, gpt), ("mistral_large", ask_mistral_large, mistral)]
    raw_results: list[dict] = []

    for entry in responses:
        q_num = entry["question_num"]
        answer = entry.get("new_answer_with_policy_v3") or "(NO ANSWER — pipeline error)"
        if answer == "(NO ANSWER — pipeline error)":
            print(f"Q{q_num} : skip judge (no answer)")
            raw_results.append({
                "question_num": q_num,
                "category": entry.get("category"),
                "judges": {},
                "skipped": True,
            })
            continue
        print(f"--- Q{q_num} [{entry.get('category')}]")
        jd: dict[str, dict] = {}
        for name, fn, client in judges:
            t0 = time.perf_counter()
            try:
                v = fn(client, build_user_prompt(entry.get("question", ""), answer, entry.get("category", "?")))
                jd[name] = {**v, "latency_s": round(time.perf_counter() - t0, 1)}
                print(f"  {name} -> {v.get('score')}/5")
            except Exception as e:
                jd[name] = {"score": None, "reasoning": f"ERROR: {type(e).__name__}", "latency_s": round(time.perf_counter() - t0, 1)}
                print(f"  {name} FAILED: {type(e).__name__}")
        raw_results.append({
            "question_num": q_num,
            "category": entry.get("category"),
            "question": entry.get("question"),
            "policy_applied": entry.get("policy", {}).get("policy"),
            "honesty_score": entry.get("validation", {}).get("honesty_score"),
            "footer_items_visible": entry.get("policy", {}).get("footer_items_visible", 0),
            "rule_violations_count": entry.get("validation", {}).get("rule_violations_count", 0),
            "layer3_warnings_count": entry.get("validation", {}).get("layer3_warnings_count", 0),
            "judges": jd,
        })
        RAW_PATH.write_text(json.dumps(raw_results, ensure_ascii=False, indent=2), encoding="utf-8")

    # Agg
    aggregated = []
    for r in raw_results:
        if r.get("skipped"):
            aggregated.append({
                "question_num": r["question_num"],
                "category": r.get("category"),
                "avg_score": None,
                "scores": {},
                "spread": 0,
                "disagreement": False,
                "skipped": True,
            })
            continue
        scores = [(n, v["score"]) for n, v in r["judges"].items() if isinstance(v.get("score"), int)]
        vals = [s for _, s in scores]
        avg = round(sum(vals) / len(vals), 2) if vals else None
        spread = max(vals) - min(vals) if vals else 0
        aggregated.append({
            "question_num": r["question_num"],
            "category": r.get("category"),
            "scores": {n: s for n, s in scores},
            "avg_score": avg,
            "spread": spread,
            "disagreement": spread > 1,
            "policy_applied": r.get("policy_applied"),
            "honesty_score": r.get("honesty_score"),
            "footer_items_visible": r.get("footer_items_visible", 0),
            "rule_violations_count": r.get("rule_violations_count", 0),
            "layer3_warnings_count": r.get("layer3_warnings_count", 0),
        })
    AGG_PATH.write_text(json.dumps(aggregated, ensure_ascii=False, indent=2), encoding="utf-8")

    valid = [a for a in aggregated if a.get("avg_score") is not None]
    global_avg = sum(a["avg_score"] for a in valid) / len(valid) if valid else None
    print(f"\n=== V3 AGG ===")
    print(f"Moyenne globale ({len(valid)}/{len(aggregated)}) : {global_avg:.2f}/5" if global_avg else "No valid scores")
    print(f"Désaccord >1pt : {sum(1 for a in aggregated if a.get('disagreement'))}/{len(aggregated)}")
    for a in aggregated:
        if a.get("skipped"):
            print(f"  Q{a['question_num']} [SKIPPED]")
        else:
            print(f"  Q{a['question_num']} [{a['category']}] avg={a['avg_score']} scores={a['scores']} policy={a.get('policy_applied')}")


if __name__ == "__main__":
    main()
