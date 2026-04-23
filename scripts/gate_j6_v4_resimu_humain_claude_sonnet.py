"""Gate J+6 V4 re-simu humaine Claude Sonnet persona (self-contained)."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from anthropic import Anthropic

from src.config import load_config


INPUT_PATH = Path("results/gate_j6/responses_validator_v4_active.json")
PERSONAS_DIR = Path("results/gate_j6/personas")
OUT_PATH = Path("results/gate_j6/ground_truth_v4_humain_resimule_claude_sonnet.json")

PERSONAS = [
    ("leo_17", "Léo, 17 ans (lycéen terminale)"),
    ("ines_20", "Inès, 20 ans (L2 socio en réorientation)"),
    ("theo_23", "Théo, 23 ans (M1 IAE)"),
    ("catherine_52", "Catherine, 52 ans (parent, DRH ingénieure)"),
    ("psy_en_54", "Isabelle Rousseau, 54 ans (Psy-EN 22 ans d'expérience)"),
]

HARD_QUESTIONS = {1, 6, 8}


def _extract_json(raw: str) -> dict:
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", raw)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return {"score": None, "erreurs_factuelles": [], "commentaire": f"PARSE_ERROR: {raw[:200]}"}


def roleplay_system_prompt(persona_md: str) -> str:
    return f"""Tu incarnes STRICTEMENT le persona suivant. Tu ne sors PAS du rôle,
tu ne fais pas d'analyse méta, tu ne présentes pas "l'outil" — tu réagis comme
cette personne réagirait en lisant la réponse d'un outil d'orientation.

{persona_md}

---

Tu vas lire une question + la réponse de l'outil OrientIA. Tu réponds UNIQUEMENT
au format JSON strict demandé dans le persona, avec TA voix, TON niveau de
langue, TON niveau d'exigence tel que décrit ci-dessus.

IMPORTANT :
- Reste en 1ère personne ("je", "tu" vers l'outil), jamais à la 3e personne
- Ton niveau de détail et ton français correspondent à ton âge / statut
- Note strictement selon ton barème
- Pas de meta ("en tant qu'IA...") — tu es Léo/Inès/Théo/Catherine/Isabelle
"""


def build_user_prompt(question: str, answer: str, category: str) -> str:
    return f"""## Question posée à OrientIA
Catégorie : {category}

> {question}

## Réponse de l'outil

{answer}

---

À toi : réagis en persona strict. JSON uniquement selon ton barème."""


def score_persona_question(client, persona_key, persona_label, persona_md, question, answer, category):
    t0 = time.perf_counter()
    try:
        resp = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=700,
            system=roleplay_system_prompt(persona_md),
            messages=[{"role": "user", "content": build_user_prompt(question, answer, category)}],
        )
        text = resp.content[0].text if resp.content else ""
    except Exception as e:
        return {"score": None, "erreurs_factuelles": [], "commentaire": f"API_ERROR: {type(e).__name__}: {e}",
                "latency_s": round(time.perf_counter() - t0, 1)}
    parsed = _extract_json(text)
    parsed["latency_s"] = round(time.perf_counter() - t0, 1)
    parsed["raw_response"] = text[:1500]
    return parsed


def main() -> None:
    config = load_config()
    client = Anthropic(api_key=config.anthropic_api_key)

    v4_responses = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    hard = {r["question_num"]: r for r in v4_responses if r.get("question_num") in HARD_QUESTIONS}
    print(f"V4 hard Q : {sorted(hard.keys())}")

    personas_loaded = [(k, l, (PERSONAS_DIR / f"{k}.md").read_text(encoding="utf-8")) for k, l in PERSONAS]

    results = []
    for q_num in sorted(hard.keys()):
        entry = hard[q_num]
        q = entry["question"]
        a = entry.get("new_answer_with_policy_v4", "")
        cat = entry.get("category", "?")
        print(f"\n--- Q{q_num} [{cat}]")
        for key, label, md in personas_loaded:
            print(f"  {key}...")
            s = score_persona_question(client, key, label, md, q, a, cat)
            print(f"    -> {s.get('score')}/5")
            results.append({
                "question_num": q_num, "category": cat, "persona_key": key, "persona_label": label,
                "score": s.get("score"),
                "erreurs_factuelles": s.get("erreurs_factuelles", []),
                "commentaire": s.get("commentaire", ""),
                "raw_response_excerpt": s.get("raw_response", "")[:500],
                "latency_s": s.get("latency_s"),
                "policy_v4": entry.get("policy", {}).get("policy"),
            })
            OUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    from statistics import median
    print("\n=== MATRICE V4 ===")
    print(f"{'Q':<4}", end="")
    for key, _ in PERSONAS:
        print(f"{key[:10]:>12}", end="")
    print(f"{'médiane':>10}")
    for q_num in sorted(hard.keys()):
        line = f"Q{q_num}:  "
        sc = []
        for key, _ in PERSONAS:
            r = next((x for x in results if x["question_num"] == q_num and x["persona_key"] == key), None)
            s = r.get("score") if r else None
            if isinstance(s, int):
                sc.append(s)
                line += f"{s:>12}"
            else:
                line += f"{'?':>12}"
        med = median(sc) if sc else "?"
        line += f"{str(med):>10}"
        print(line)

    all_s = [r.get("score") for r in results if isinstance(r.get("score"), int)]
    if all_s:
        print(f"\nMoyenne V4 : {sum(all_s)/len(all_s):.2f}/5 ({len(all_s)} eval)")
        print(f"Médiane V4 : {median(all_s)}/5")


if __name__ == "__main__":
    main()
