"""Gate J+6 V3 — re-simulation humaine via Claude Sonnet 4.5 persona.

5 profils strictement roleplayés × 3 Q hard (Q1 HEC / Q6 Perpignan / Q8 PASS)
sur les réponses V3 de `responses_validator_v3_active.json`.

Output : `results/gate_j6/ground_truth_v3_humain_resimule_claude_sonnet.json`

Pour chaque (persona, question) : score /5 + erreurs factuelles + commentaire.

Caveat : proxy LLM persona, pas humain réel. Mais meilleur proxy disponible
(Claude Sonnet 4.5 était le plus proche du verdict humain ce matin, +0.7 pt).

Usage :
    python scripts/gate_j6_v3_resimu_humain_claude_sonnet.py
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from anthropic import Anthropic

from src.config import load_config


RESPONSES_V3_PATH = Path("results/gate_j6/responses_validator_v3_active.json")
PERSONAS_DIR = Path("results/gate_j6/personas")
OUT_PATH = Path("results/gate_j6/ground_truth_v3_humain_resimule_claude_sonnet.json")


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
    """System prompt strict roleplay : interdit de sortir du persona."""
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


def score_persona_question(
    client: Anthropic,
    persona_key: str,
    persona_label: str,
    persona_md: str,
    question: str,
    answer: str,
    category: str,
) -> dict:
    system = roleplay_system_prompt(persona_md)
    user = build_user_prompt(question, answer, category)
    t0 = time.perf_counter()
    try:
        resp = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=700,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = resp.content[0].text if resp.content else ""
    except Exception as e:
        return {
            "persona_key": persona_key,
            "persona_label": persona_label,
            "score": None,
            "erreurs_factuelles": [],
            "commentaire": f"API_ERROR: {type(e).__name__}: {e}",
            "latency_s": round(time.perf_counter() - t0, 1),
        }

    parsed = _extract_json(text)
    parsed.update({
        "persona_key": persona_key,
        "persona_label": persona_label,
        "latency_s": round(time.perf_counter() - t0, 1),
        "raw_response": text[:1500],  # tronqué pour audit
    })
    return parsed


def main() -> None:
    config = load_config()
    if not config.anthropic_api_key:
        raise SystemExit("ANTHROPIC_API_KEY manquante")

    client = Anthropic(api_key=config.anthropic_api_key)

    # Load V3 answers (3 hard questions)
    v3_responses = json.loads(RESPONSES_V3_PATH.read_text(encoding="utf-8"))
    hard = {r["question_num"]: r for r in v3_responses if r.get("question_num") in HARD_QUESTIONS}
    print(f"V3 hard questions disponibles : {sorted(hard.keys())}")
    if len(hard) != 3:
        print(f"WARNING: missing some hard questions (expected 3, got {len(hard)})")

    # Load personas
    personas_loaded: list[tuple[str, str, str]] = []
    for key, label in PERSONAS:
        md_path = PERSONAS_DIR / f"{key}.md"
        if not md_path.exists():
            print(f"Persona missing: {md_path}")
            continue
        personas_loaded.append((key, label, md_path.read_text(encoding="utf-8")))
    print(f"Personas chargés : {len(personas_loaded)}")

    results: list[dict] = []
    for q_num in sorted(hard.keys()):
        entry = hard[q_num]
        question = entry["question"]
        answer = entry.get("new_answer_with_policy_v3", "")
        category = entry.get("category", "?")
        print(f"\n--- Q{q_num} [{category}] ---")
        for key, label, md in personas_loaded:
            print(f"  Persona {key}...")
            scored = score_persona_question(
                client, key, label, md, question, answer, category
            )
            score = scored.get("score")
            print(f"    -> {score}/5 ({scored['latency_s']}s)")
            results.append({
                "question_num": q_num,
                "category": category,
                "persona_key": scored["persona_key"],
                "persona_label": scored["persona_label"],
                "score": scored.get("score"),
                "erreurs_factuelles": scored.get("erreurs_factuelles", []),
                "commentaire": scored.get("commentaire", ""),
                "raw_response_excerpt": scored.get("raw_response", "")[:500],
                "latency_s": scored.get("latency_s"),
                "policy_v3": entry.get("policy", {}).get("policy"),
            })
            # Incremental save (resume safety)
            OUT_PATH.write_text(
                json.dumps(results, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    # Summary
    print("\n=== MATRICE V3 Claude Sonnet persona ===")
    # Header
    print(f"{'Q':<4}", end="")
    for key, _ in PERSONAS:
        print(f"{key[:10]:>12}", end="")
    print(f"{'médiane':>10}")

    from statistics import median
    for q_num in sorted(hard.keys()):
        line = f"Q{q_num}:  "
        scores_this_q = []
        for key, _ in PERSONAS:
            r = next((x for x in results if x["question_num"] == q_num and x["persona_key"] == key), None)
            s = r.get("score") if r else None
            if isinstance(s, int):
                scores_this_q.append(s)
                line += f"{s:>12}"
            else:
                line += f"{'?':>12}"
        med = median(scores_this_q) if scores_this_q else "?"
        line += f"{str(med):>10}"
        print(line)

    # Global
    all_scores = [r.get("score") for r in results if isinstance(r.get("score"), int)]
    if all_scores:
        print(f"\nMoyenne globale : {sum(all_scores)/len(all_scores):.2f}/5 ({len(all_scores)} evaluations)")
        print(f"Médiane globale : {median(all_scores)}/5")


if __name__ == "__main__":
    main()
