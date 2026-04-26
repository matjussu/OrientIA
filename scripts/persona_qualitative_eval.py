"""Persona qualitative eval — Claude-sonnet TOOL hors stack prod Mistral.

Pour chaque persona v4 (6 personas × 3 queries = 18 evals), envoie au
LLM Claude Sonnet 4.5 :
- Description du persona (POV utilisateur)
- Question posée
- Réponse RAG OrientIA (run1 du bench persona complet)

Demande verdict qualitatif (claire/utile/incomplet/hallu détecté) +
suggestion amélioration en ~100 mots max.

## Distinction épistémique

Claude-sonnet utilisé comme **outil d'évaluation méthodologique**,
distinct de la stack RAG prod 100% Mistral souverain. Cohérent avec
le pattern judge multi-LLM (cf src/eval/judge.py) — Claude juge ne
participe pas à la génération.

## Coût

~$0.10-0.20 estimé : 18 evals × ~5K tokens input × $3/1M + ~300 tokens
output × $15/1M.

## Output

`results/bench_persona_complet_2026-04-26/_persona_qualitative_eval.json`
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from anthropic import Anthropic  # noqa: E402
from src.config import load_config  # noqa: E402
from scripts.run_bench_personas_v3 import PERSONAS  # noqa: E402

RESULTS_PATH = REPO_ROOT / "results" / "bench_persona_complet_2026-04-26" / "_ALL_QUERIES.json"
OUT_PATH = REPO_ROOT / "results" / "bench_persona_complet_2026-04-26" / "_persona_qualitative_eval.json"

EVAL_PROMPT_TEMPLATE = """Tu es {persona_id} : {persona_description}

Tu as posé cette question à un assistant d'orientation OrientIA :

> {query_text}

Voici la réponse de l'assistant :

---
{answer}
---

Évalue qualitativement la réponse de TON POINT DE VUE de {persona_id}.

Tu réponds STRICTEMENT en JSON dans ce format :
{{
  "verdict": "claire" | "utile_partielle" | "incomplet" | "hallu_detecte" | "off_topic",
  "comprehensible": true/false,
  "actionnable": true/false,
  "hallu_flag_text": "<phrase suspecte si hallu_detecte sinon null>",
  "suggestion": "<1 phrase de suggestion concrète d'amélioration max 30 mots>"
}}

Critères :
- "claire" : réponse précise, sourcée, actionnable, sans flou
- "utile_partielle" : réponse correcte mais incomplète (manque info clé pour décider)
- "incomplet" : manque trop d'info pour être actionnable
- "hallu_detecte" : tu repères une stat/fait qui te paraît faux ou inventé
- "off_topic" : la réponse parle d'autre chose que ta question

Réponds UNIQUEMENT le JSON, rien d'autre.
"""


def _truncate_answer(answer: str, max_chars: int = 3000) -> str:
    """Truncate answer to keep input tokens reasonable."""
    if len(answer) <= max_chars:
        return answer
    return answer[:max_chars] + "\n[...truncated for brevity...]"


def main() -> int:
    if not RESULTS_PATH.exists():
        print(f"❌ {RESULTS_PATH} absent. Run bench persona complet d'abord.")
        return 1

    cfg = load_config()
    if not cfg.anthropic_api_key:
        print("❌ ANTHROPIC_API_KEY absent dans .env")
        return 1

    client = Anthropic(api_key=cfg.anthropic_api_key)
    results = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))

    # Index results by query_id
    results_by_id = {r["query_id"]: r for r in results}

    evaluations = []
    total_personas = len(PERSONAS)
    print(f"Persona qualitative eval : {total_personas} personas × 3 queries = {total_personas * 3} evals")
    print("=" * 60)

    for p_idx, persona in enumerate(PERSONAS, 1):
        persona_id = persona["id"]
        persona_desc = persona.get("description", persona_id)
        print(f"\n[{p_idx}/{total_personas}] Persona: {persona_id}")
        print(f"    Description: {persona_desc[:120]}")

        for q in persona["queries"]:
            qid = f"{persona_id}_{q['id']}"
            res = results_by_id.get(qid)
            if not res:
                print(f"  ⚠️  Query {qid} absente des résultats")
                continue
            answer = res.get("answer_annotated") or res.get("answer_raw") or ""
            if not answer:
                print(f"  ⚠️  Query {qid} sans réponse")
                continue

            prompt = EVAL_PROMPT_TEMPLATE.format(
                persona_id=persona_id,
                persona_description=persona_desc,
                query_text=q["text"],
                answer=_truncate_answer(answer),
            )

            try:
                response = client.messages.create(
                    model="claude-sonnet-4-5-20250929",
                    max_tokens=400,
                    messages=[{"role": "user", "content": prompt}],
                )
                output = response.content[0].text.strip()
                # Clean potential markdown fences
                if output.startswith("```"):
                    output = output.split("```")[1].lstrip("json").strip()
                eval_data = json.loads(output)
            except Exception as e:
                print(f"  ❌ {qid}: error {type(e).__name__}: {e}")
                eval_data = {"error": f"{type(e).__name__}: {e}"}

            evaluations.append({
                "persona_id": persona_id,
                "query_id": qid,
                "query_text": q["text"],
                "verdict": eval_data.get("verdict"),
                "comprehensible": eval_data.get("comprehensible"),
                "actionnable": eval_data.get("actionnable"),
                "hallu_flag_text": eval_data.get("hallu_flag_text"),
                "suggestion": eval_data.get("suggestion"),
                "raw_eval": eval_data if "error" in eval_data else None,
            })

            verdict_str = eval_data.get("verdict", "?")
            print(f"  [{q['id']:<4}] verdict={verdict_str:<18} actionnable={eval_data.get('actionnable')}")

    OUT_PATH.write_text(
        json.dumps(evaluations, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n✅ {len(evaluations)} évaluations sauvegardées → {OUT_PATH}")

    # Aggregate stats
    print("\n=== Aggregate verdict ===")
    verdicts = [e.get("verdict") for e in evaluations if e.get("verdict")]
    from collections import Counter
    counter = Counter(verdicts)
    for v, count in counter.most_common():
        print(f"  {v}: {count}/{len(evaluations)}")
    n_actionnable = sum(1 for e in evaluations if e.get("actionnable") is True)
    n_comprehensible = sum(1 for e in evaluations if e.get("comprehensible") is True)
    print(f"  Actionnable: {n_actionnable}/{len(evaluations)}")
    print(f"  Compréhensible: {n_comprehensible}/{len(evaluations)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
