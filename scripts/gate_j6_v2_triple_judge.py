"""Gate J+6 v2 — triple-judge sur réponses post-Validator V2.

Identique à `gate_j6_triple_judge.py` mais en entrée :
`results/gate_j6/responses_validator_v2_active.json` (post-V2).

Output :
- `results/gate_j6/judges_v2/judge_responses_v2.json`
- `results/gate_j6/judges_v2/scores_aggregated_v2.json`
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Réutilise les fonctions judges + prompts du script v1
sys.path.insert(0, str(Path(__file__).parent))
from gate_j6_triple_judge import (
    ask_claude,
    ask_gpt4o,
    ask_mistral_large,
    build_user_prompt,
)

import time
from anthropic import Anthropic
from openai import OpenAI
from mistralai.client import Mistral

from src.config import load_config


INPUT_PATH = Path("results/gate_j6/responses_validator_v2_active.json")
OUT_DIR = Path("results/gate_j6/judges_v2")
RAW_PATH = OUT_DIR / "judge_responses_v2.json"
AGG_PATH = OUT_DIR / "scores_aggregated_v2.json"


def main() -> None:
    if not INPUT_PATH.exists():
        raise SystemExit(f"Input introuvable : {INPUT_PATH}. Lance `run_gate_j6_v2.py` d'abord.")

    config = load_config()
    claude = Anthropic(api_key=config.anthropic_api_key)
    gpt = OpenAI(api_key=config.openai_api_key)
    mistral = Mistral(api_key=config.mistral_api_key, timeout_ms=120000)

    responses = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    print(f"Loaded {len(responses)} réponses V2 à juger\n")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    judges = [
        ("claude_sonnet_4_5", ask_claude, claude),
        ("gpt_4o", ask_gpt4o, gpt),
        ("mistral_large", ask_mistral_large, mistral),
    ]

    raw_results: list[dict] = []

    for entry in responses:
        q_num = entry["question_num"]
        question = entry["question"]
        category = entry.get("category", "?")
        answer = entry.get("new_answer_with_policy_v2") or "(NO ANSWER)"

        print(f"--- Q{q_num} [{category}] judging V2...")
        judge_data: dict[str, dict] = {}
        for judge_name, ask_fn, client in judges:
            t0 = time.perf_counter()
            try:
                verdict = ask_fn(client, build_user_prompt(question, answer, category))
                elapsed = time.perf_counter() - t0
                judge_data[judge_name] = {**verdict, "latency_s": round(elapsed, 1)}
                print(f"  {judge_name} -> {verdict.get('score')}/5 ({elapsed:.0f}s)")
            except Exception as e:
                judge_data[judge_name] = {
                    "score": None,
                    "reasoning": f"ERROR: {type(e).__name__}: {e}",
                    "main_concerns": [],
                    "latency_s": round(time.perf_counter() - t0, 1),
                }
                print(f"  {judge_name} FAILED: {type(e).__name__}")

        raw_results.append({
            "question_num": q_num,
            "category": category,
            "question": question,
            "policy_applied": entry.get("policy", {}).get("policy", "none"),
            "honesty_score": entry.get("validation", {}).get("honesty_score"),
            "rule_violations_count": len(entry.get("validation", {}).get("rule_violations", [])),
            "layer3_warnings_count": len(entry.get("validation", {}).get("layer3_warnings", [])),
            "judges": judge_data,
        })
        RAW_PATH.write_text(json.dumps(raw_results, ensure_ascii=False, indent=2), encoding="utf-8")

    aggregated: list[dict] = []
    for entry in raw_results:
        scores = [(n, v["score"]) for n, v in entry["judges"].items() if isinstance(v.get("score"), int)]
        vals = [s for _, s in scores]
        avg = round(sum(vals) / len(vals), 2) if vals else None
        spread = max(vals) - min(vals) if vals else 0
        aggregated.append({
            "question_num": entry["question_num"],
            "category": entry["category"],
            "scores": {n: s for n, s in scores},
            "avg_score": avg,
            "spread": spread,
            "disagreement": spread > 1,
            "policy_applied": entry["policy_applied"],
            "honesty_score": entry["honesty_score"],
            "rule_violations_count": entry["rule_violations_count"],
            "layer3_warnings_count": entry["layer3_warnings_count"],
        })
    AGG_PATH.write_text(json.dumps(aggregated, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== AGGREGATED SCORES V2 ===")
    valid = [a for a in aggregated if a["avg_score"] is not None]
    global_avg = sum(a["avg_score"] for a in valid) / len(valid) if valid else None
    print(f"Moyenne globale V2 : {global_avg:.2f}/5")
    print(f"Désaccord juges >1pt : {sum(1 for a in aggregated if a['disagreement'])}/{len(aggregated)}")
    for a in aggregated:
        print(
            f"  Q{a['question_num']} [{a['category']}] avg={a['avg_score']} "
            f"scores={a['scores']} policy={a['policy_applied']} "
            f"rules={a['rule_violations_count']} layer3={a['layer3_warnings_count']}"
        )


if __name__ == "__main__":
    main()
