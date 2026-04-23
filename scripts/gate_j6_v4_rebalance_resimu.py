"""Gate J+6 V4.1 re-simu humaine Claude Sonnet persona sur 3 Q rééquilibrées."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from anthropic import Anthropic

from src.config import load_config


INPUT_PATH = Path("results/gate_j6/responses_validator_v4_rebalance_active.json")
PERSONAS_DIR = Path("results/gate_j6/personas")
OUT_PATH = Path("results/gate_j6/ground_truth_v4_rebalance_resimule.json")

PERSONAS = [
    ("leo_17", "Léo, 17 ans"),
    ("ines_20", "Inès, 20 ans"),
    ("theo_23", "Théo, 23 ans"),
    ("catherine_52", "Catherine, 52 ans"),
    ("psy_en_54", "Isabelle Rousseau Psy-EN 54"),
]


def _extract_json(raw):
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    return {"score": None, "erreurs_factuelles": [], "commentaire": f"PARSE_ERROR: {raw[:150]}"}


def roleplay_sp(md):
    return f"""Tu incarnes STRICTEMENT le persona :

{md}

---

Tu lis une question + réponse de l'outil OrientIA. Tu réagis en persona strict,
JSON uniquement selon ton barème. 1ère personne, pas de meta."""


def user_prompt(q, a, c):
    return f"""## Question\nCatégorie : {c}\n\n> {q}\n\n## Réponse\n\n{a}\n\n---\nRéagis en persona, JSON."""


def main():
    config = load_config()
    client = Anthropic(api_key=config.anthropic_api_key)
    responses = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    personas = [(k, (PERSONAS_DIR / f"{k}.md").read_text(encoding="utf-8")) for k, _ in PERSONAS]

    results = []
    for r in responses:
        q_num = r["question_num"]
        q = r["question"]
        a = r.get("new_answer_rebalance_v4", "")
        cat = r.get("category")
        print(f"\n--- Q{q_num} [{cat}]")
        for key, md in personas:
            t0 = time.perf_counter()
            try:
                resp = client.messages.create(
                    model="claude-sonnet-4-5", max_tokens=600,
                    system=roleplay_sp(md),
                    messages=[{"role": "user", "content": user_prompt(q, a, cat)}],
                )
                text = resp.content[0].text if resp.content else ""
                p = _extract_json(text)
            except Exception as e:
                p = {"score": None, "commentaire": f"ERR: {type(e).__name__}"}
            s = p.get("score")
            print(f"  {key} -> {s}/5")
            results.append({
                "question_num": q_num, "persona_key": key, "score": s,
                "erreurs_factuelles": p.get("erreurs_factuelles", []),
                "commentaire": p.get("commentaire", ""),
                "latency_s": round(time.perf_counter() - t0, 1),
            })
            OUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    # Summary
    from statistics import median
    print("\n=== MATRICE V4.1 rebalance ===")
    for q_num in sorted({r["question_num"] for r in results}):
        line = f"Q{q_num}: "
        sc = []
        for key, _ in PERSONAS:
            r = next((x for x in results if x["question_num"] == q_num and x["persona_key"] == key), None)
            s = r.get("score") if r else None
            if isinstance(s, int):
                sc.append(s)
                line += f"{s:>3}"
            else:
                line += f"  ?"
        med = median(sc) if sc else "?"
        line += f"  med={med}"
        print(line)
    all_s = [r.get("score") for r in results if isinstance(r.get("score"), int)]
    if all_s:
        print(f"\nMoyenne : {sum(all_s)/len(all_s):.2f}/5 ({len(all_s)} eval)")
        print(f"Médiane : {median(all_s)}/5")


if __name__ == "__main__":
    main()
