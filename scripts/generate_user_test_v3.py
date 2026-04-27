"""Sprint 7 — user_test_v3 generation (clôture, retour UX humain).

Reuse les 10 questions de `results/user_test_v2/responses.json` (format
identique pour comparison apples-to-apples avec v2) et regénère les
réponses avec **Mode Baseline post-Sprint 7** :
- Phase E corpus updated (58 093 vecteurs avec Sprint 6 + 7 Action 4)
- Intent classifier Sprint 7 (Action 5 : 4 nouveaux DOMAIN_HINT)
- Fact-checker Sprint 7 (Action 1 : `verified_by_official_source`)
- v3.2 SYSTEM_PROMPT (PAS v3.3 strict — R3 revert verdict Sprint 7)
- Pas de critic loop (R3 revert)

= le mode qui marche +7,4pp solide vs Sprint 6 (verdict §4).

## Output

`results/user_test_v3/` :
- `responses.json` : format identique v2 (`[{question_num, category,
  question, answer, word_count}, ...]`)
- `answers_to_show.md` : format markdown lisible humain

## Coût estimé

10 inférences × ~$0.05 = ~$0.50. Wall-clock ~5-7 min.

## Distribution

Matteo distribue manuellement aux 5 profils du test v2 (Léo 17,
Sarah 20, Thomas 23, Catherine 52, Dominique 48). Pas de LLM-judge,
retour qualitatif humain pour Sprint 8 priorisation.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import faiss  # noqa: E402
from mistralai.client import Mistral  # noqa: E402

from src.agent.cache import LRUCache  # noqa: E402
from src.agent.pipeline_agent import AgentPipeline  # noqa: E402
from src.config import load_config  # noqa: E402


PHASEE_FICHES_PATH = REPO_ROOT / "data" / "processed" / "formations_multi_corpus_phaseE.json"
PHASEE_INDEX_PATH = REPO_ROOT / "data" / "embeddings" / "formations_multi_corpus_phaseE.index"

V2_RESPONSES_PATH = REPO_ROOT / "results" / "user_test_v2" / "responses.json"
OUT_DIR = REPO_ROOT / "results" / "user_test_v3"


def _word_count(text: str) -> int:
    return len(text.split())


def _build_markdown(responses: list[dict], generated_at: str) -> str:
    """Construit answers_to_show.md format identique v2."""
    lines = [
        "# OrientIA — Réponses test utilisateur v3 (post-Sprint 7)",
        "",
        f"*Généré le {generated_at} — Mode Baseline post-Sprint 7 "
        "(SYSTEM_PROMPT v3.2 + Phase E 58 093 vecteurs + intent Sprint 7 + "
        "fact-checker `verified_by_official_source`)*",
        "",
        "Ce document contient les **10 mêmes questions** que le pack v2 "
        "(2026-04-18) re-générées avec le système Mode Baseline post-Sprint 7 "
        "= le mode qui marche +7,4pp solide vs Sprint 6 (verdict §4).",
        "",
        "**Objectif** : retour qualitatif humain de comparaison v2 vs v3 par "
        "les 5 profils (Léo 17, Sarah 20, Thomas 23, Catherine 52, "
        "Dominique 48). Critères de succès :",
        "- Précision factuelle stabilisée vs v2 (ne casse rien)",
        "- Couverture améliorée sur queries DROM / financement / bac pro "
        "(Sprint 7 axes amplifiés)",
        "- Format pyramide inversée v2 préservé (instructions Tier 2 inchangées)",
        "",
        "**Verdict bench Sprint 7 final** :",
        "- Mode Baseline (= v3) : 30,8% verified ± IC95 1,03pp",
        "- vs Sprint 6 : 23,4% (= +7,4pp gain solide IC95 ×8,6 plus serré)",
        "- vs baseline figée Sprint 5 : 39,4% (gap résiduel -8,6pp)",
        "",
        "---",
        "",
    ]
    for r in responses:
        lines.append(f"## Question {r['question_num']} — [{r['category']}]")
        lines.append("")
        lines.append(f"> **{r['question']}**")
        lines.append("")
        lines.append(f"*Word count : {r['word_count']} mots*")
        lines.append("")
        lines.append("### Réponse OrientIA v3")
        lines.append("")
        lines.append(r["answer"])
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    if not PHASEE_FICHES_PATH.exists() or not PHASEE_INDEX_PATH.exists():
        print("❌ Phase E index/fiches absent.")
        return 1
    if not V2_RESPONSES_PATH.exists():
        print(f"❌ V2 responses absent : {V2_RESPONSES_PATH}")
        return 1

    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=180_000)

    print("Loading Phase E (58 093 vecteurs Sprint 7 final)...")
    fiches = json.loads(PHASEE_FICHES_PATH.read_text(encoding="utf-8"))
    index = faiss.read_index(str(PHASEE_INDEX_PATH))
    print(f"  {len(fiches):,} fiches, ntotal={index.ntotal:,}")

    print("Loading 10 questions de user_test_v2...")
    v2_responses = json.loads(V2_RESPONSES_PATH.read_text(encoding="utf-8"))
    print(f"  {len(v2_responses)} questions chargées")

    cache = LRUCache(maxsize=128)
    # Mode Baseline post-Sprint 7 (v3.2 + critic OFF — R3 revert verdict Sprint 7)
    pipeline = AgentPipeline(
        client=client, fiches=fiches, index=index,
        profile_cache=cache,
        aggregated_top_n=8,
        enable_fact_check=False,
        system_prompt_override=None,  # v3.2, pas v3.3 strict
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n{'='*60}")
    print(f"Génération user_test_v3 — 10 questions × Mode Baseline Sprint 7")
    print(f"{'='*60}")

    responses_v3: list[dict] = []
    t0_global = time.time()

    for i, q in enumerate(v2_responses, 1):
        print(f"\n[{i}/{len(v2_responses)}] Q{q['question_num']} ({q['category']})")
        print(f"    \"{q['question'][:80]}...\"")

        result = pipeline.answer(q["question"])
        if result.error:
            print(f"    ❌ pipeline error : {result.error[:120]}")
            answer_text = f"[ERREUR PIPELINE : {result.error[:200]}]"
            wc = 0
        else:
            answer_text = result.answer_text
            wc = _word_count(answer_text)
            print(f"    ✅ {result.elapsed_total_s}s, {wc} mots")

        responses_v3.append({
            "question_num": q["question_num"],
            "category": q["category"],
            "question": q["question"],
            "answer": answer_text,
            "word_count": wc,
        })

        # Save incremental (sécurité)
        out_path = OUT_DIR / "responses.json"
        out_path.write_text(json.dumps(responses_v3, ensure_ascii=False, indent=2),
                            encoding="utf-8")

        if i < len(v2_responses):
            time.sleep(2)  # rate limit pause

    total_elapsed = round(time.time() - t0_global, 2)

    # Generate markdown
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    md_content = _build_markdown(responses_v3, generated_at)
    md_path = OUT_DIR / "answers_to_show.md"
    md_path.write_text(md_content, encoding="utf-8")

    # Final summary
    avg_wc = sum(r["word_count"] for r in responses_v3) / max(1, len(responses_v3))
    print(f"\n{'='*60}")
    print(f"=== user_test_v3 généré ===")
    print(f"{'='*60}")
    print(f"  N questions : {len(responses_v3)}")
    print(f"  Word count moyen : {avg_wc:.0f} mots/réponse")
    print(f"  Total wall-clock : {total_elapsed}s ({total_elapsed/60:.1f} min)")
    print(f"\n  Outputs :")
    print(f"    - {OUT_DIR / 'responses.json'}")
    print(f"    - {OUT_DIR / 'answers_to_show.md'}")
    print(f"\n✅ Prêt à distribuer aux profils humains")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
