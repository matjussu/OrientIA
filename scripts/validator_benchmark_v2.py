"""Benchmark mini : Validator v1 sur le pack user_test_v2 (10 questions).

Charge `results/user_test_v2/responses.json`, lance Validator sur chaque
answer, et imprime un récapitulatif :
- Nombre de violations BLOCKING / WARNING / corpus_warning par question
- Honesty score moyen
- Pourcentage de questions flaggées (≥1 BLOCKING ou corpus_warning)
- Liste détaillée par question

Usage :
    python scripts/validator_benchmark_v2.py

Ne fait aucun appel LLM externe (Validator v1 est déterministe).
"""
from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

from src.validator import Validator, Severity


RESPONSES_PATH = Path("results/user_test_v2/responses.json")
CORPUS_PATH = Path("data/processed/formations.json")


def main() -> None:
    if not RESPONSES_PATH.exists():
        print(f"[error] {RESPONSES_PATH} introuvable")
        return
    if not CORPUS_PATH.exists():
        print(f"[error] {CORPUS_PATH} introuvable — lancer src.collect.run_merge")
        return

    responses = json.loads(RESPONSES_PATH.read_text(encoding="utf-8"))
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    print(f"Corpus chargé : {len(corpus)} fiches")
    print(f"Pack v2 : {len(responses)} questions\n")

    validator = Validator(fiches=corpus)
    honesty_scores: list[float] = []
    flagged_count = 0
    blocking_count = 0
    warning_count = 0
    corpus_warn_count = 0

    print("=" * 80)
    for r in responses:
        q_num = r.get("question_num")
        category = r.get("category", "?")
        question = r.get("question", "")[:80]
        answer = r.get("answer", "")
        result = validator.validate(answer)

        honesty_scores.append(result.honesty_score)
        if result.flagged:
            flagged_count += 1
        for v in result.rule_violations:
            if v.severity == Severity.BLOCKING:
                blocking_count += 1
            elif v.severity == Severity.WARNING:
                warning_count += 1
        corpus_warn_count += len(result.corpus_warnings)

        flag_marker = "FLAGGED" if result.flagged else "ok"
        print(f"Q{q_num} [{category}] {flag_marker} honesty={result.honesty_score:.2f}")
        print(f"  Question : {question}")
        if result.rule_violations:
            for v in result.rule_violations:
                print(f"  - rule [{v.severity.value}] {v.rule_id}: {v.matched_text!r}")
        if result.corpus_warnings:
            for w in result.corpus_warnings:
                print(f"  - corpus warn (sim={w.similarity}): {w.claim!r}")
                print(f"    closest: {w.closest_match}")
        print()

    print("=" * 80)
    print("RÉCAPITULATIF Validator v1 sur pack user_test_v2 :")
    print(f"  Questions analysées      : {len(responses)}")
    print(f"  Honesty score moyen      : {mean(honesty_scores):.2f}")
    print(f"  Questions flaggées       : {flagged_count}/{len(responses)} "
          f"({100*flagged_count/len(responses):.0f}%)")
    print(f"  Total violations BLOCK   : {blocking_count}")
    print(f"  Total violations WARN    : {warning_count}")
    print(f"  Total corpus warnings    : {corpus_warn_count}")
    print(f"  Total flags (BLOCK+corp) : {blocking_count + corpus_warn_count}")


if __name__ == "__main__":
    main()
