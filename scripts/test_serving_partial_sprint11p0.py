"""Re-run partiel test serving 3 questions hallu Matteo + 1 baseline — Sprint 11 P0 Item 1.

Re-lance UNIQUEMENT les 3 questions où Matteo a détecté des hallucinations
factuelles dans le chantier E (Q5 IFSI / Q8 DEAMP / Q10 Terminale L)
+ 1 question baseline pour confirmer pas de régression sur cas clean.

Comparaison avant/après prompt v4 Sprint 11 P0 — sample compact pour audit
Jarvis avant industrialisation Item 4 full re-run.

Usage : `PYTHONPATH=. python3 scripts/test_serving_partial_sprint11p0.py`

Coût Mistral API : ~$0.20-0.30 (4 questions × ~$0.05).
ETA wall-clock : ~1-2 min.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from mistralai.client import Mistral

from src.config import load_config
from src.rag.pipeline import OrientIAPipeline


ROOT = Path(__file__).resolve().parents[1]
FICHES_PATH = ROOT / "data" / "processed" / "formations_unified.json"
INDEX_PATH = ROOT / "data" / "embeddings" / "formations_unified.index"
GOLDEN_QA_INDEX_PATH = ROOT / "data" / "embeddings" / "golden_qa.index"
GOLDEN_QA_META_PATH = ROOT / "data" / "processed" / "golden_qa_meta.json"
OUTPUT_DOC = ROOT / "docs" / "sprint11-P0-item1-partial-rerun-2026-04-29.md"


# 3 questions où Matteo a détecté hallu chantier E + 1 baseline post-bac
TEST_QUESTIONS = [
    # Q5 — IFSI concours (chantier E hallu : Mistral parlait du concours IFSI supprimé en 2019)
    "J'ai raté ma PASS, est-ce que je peux quand même faire kiné ou infirmière ?",
    # Q8 — DEAMP (chantier E hallu : Mistral parlait du DEAMP fusionné en DEAES en 2016)
    "Je travaille dans le tertiaire depuis 5 ans, je veux me reconvertir paramédical après un burn-out, par où commencer ?",
    # Q10 — Terminale L (chantier E hallu : Mistral parlait des séries L supprimées en 2021)
    "Je suis en terminale L et tout le monde me dit que ça ne mène à rien, est-ce vrai ?",
    # Baseline — Q1 cas standard, pour confirmer pas de régression
    "Je suis en terminale spé maths-physique mais je sature des maths abstraites, alternatives concrètes à la prépa MPSI ?",
]


def run_one(pipeline, question: str) -> dict:
    t_start = time.time()
    try:
        answer, top = pipeline.answer(question, top_k_sources=10)
        elapsed_ms = (time.time() - t_start) * 1000
        return {
            "question": question,
            "answer": answer,
            "n_sources": len(top),
            "sources_top3_noms": [
                ((s.get("fiche") or {}).get("nom") or (s.get("fiche") or {}).get("title"))
                for s in top[:3]
            ],
            "t_total_ms": round(elapsed_ms),
            "answer_word_count": len(answer.split()),
            "filter_stats": pipeline.last_filter_stats or {},
            "golden_qa": pipeline.last_golden_qa or {},
            "error": None,
        }
    except Exception as e:
        return {
            "question": question,
            "answer": None,
            "error": f"{type(e).__name__}: {e}",
        }


def render_md(results: list[dict]) -> str:
    parts = [
        "# Sprint 11 P0 Item 1 — Re-run partiel test serving (4 questions)",
        "",
        "**Date** : 2026-04-29",
        "**Branche** : `feat/sprint11-P0-prompt-refonte`",
        "**Prompt** : SYSTEM_PROMPT v4 (préfixe Sprint 11 P0 Strict Grounding + Glossaire + Progressive Disclosure)",
        "**Pipeline** : OrientIAPipeline default (use_metadata_filter=True, use_golden_qa=True)",
        "",
        "## Sample audit Jarvis avant Item 4 full re-run",
        "",
        "Re-run uniquement les 3 questions où Matteo a détecté des hallucinations dans le chantier E (test serving) + 1 baseline cas standard pour vérifier pas de régression UX.",
        "",
        "### Stats agrégées",
        "",
    ]

    valid = [r for r in results if not r.get("error")]
    word_counts = [r["answer_word_count"] for r in valid]
    latencies = [r["t_total_ms"] for r in valid]

    if word_counts:
        parts.append(f"- Word count moyen : **{sum(word_counts) // len(word_counts)} mots** (cible Progressive Disclosure ≤250)")
        parts.append(f"- Word count range : {min(word_counts)} - {max(word_counts)}")
        parts.append(f"- Word count <=250 (cible Sprint 11 P0) : {sum(1 for w in word_counts if w <= 250)}/{len(word_counts)}")
    if latencies:
        parts.append(f"- Latence moyenne : {sum(latencies) // len(latencies)} ms")
    parts.append("")
    parts.append("---")
    parts.append("")

    for i, r in enumerate(results, 1):
        parts.append(f"## Q{i} — {r['question'][:90]}{'...' if len(r['question']) > 90 else ''}")
        parts.append("")

        if r.get("error"):
            parts.append(f"❌ ERREUR : {r['error']}")
            parts.append("")
            continue

        parts.append(f"**Mesures** : t_total={r['t_total_ms']}ms | "
                     f"word_count={r['answer_word_count']} mots "
                     f"(cible ≤250 ✅' if {r['answer_word_count'] <= 250} else '⚠️ DÉPASSEMENT')")
        parts.append("")

        gq = r.get("golden_qa", {})
        if gq.get("matched"):
            parts.append(f"**Q&A Golden top-1** : `{gq.get('prompt_id')}` iter {gq.get('iteration')} (score {gq.get('score_total')}, sim {gq.get('retrieve_score', 0):.2f})")
            parts.append("")

        parts.append("**Sources top-3** :")
        for j, nom in enumerate(r.get("sources_top3_noms") or [], 1):
            if nom:
                parts.append(f"  {j}. {nom[:90]}")
        parts.append("")

        parts.append("**Réponse Mistral (post Sprint 11 P0)** :")
        parts.append("")
        parts.append("> " + r["answer"].replace("\n", "\n> "))
        parts.append("")
        parts.append("---")
        parts.append("")

    parts.append("")
    parts.append("## À auditer côté Jarvis")
    parts.append("")
    parts.append("Pour chaque question, vérifier :")
    parts.append("- Q1 (PASS/IFSI) : la réponse mentionne-t-elle un concours IFSI post-bac ? (= hallu si oui)")
    parts.append("- Q2 (DEAMP) : la réponse mentionne-t-elle DEAMP ou propose-t-elle DEAES ? (DEAES = correct)")
    parts.append("- Q3 (Terminale L) : la réponse parle-t-elle de série L ou recadre vers spécialités ? (recadrage = correct)")
    parts.append("- Q4 (baseline MPSI) : pas de régression UX, formats Plan A/B/C ≤250 mots maintenu")
    parts.append("")
    parts.append("Si les 4 réponses sont compliantes Strict Grounding + Glossaire actif → GO Item 2 (buffer mémoire) puis Item 4 (full re-run 10 questions).")
    parts.append("")
    parts.append("*Re-run généré par `scripts/test_serving_partial_sprint11p0.py` sous l'ordre `2026-04-29-1700-claudette-orientia-sprint11-P0-corrections-prompt-buffer-judge` (Item 1 sample audit).*")
    return "\n".join(parts)


def main() -> int:
    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key)
    fiches = json.loads(FICHES_PATH.read_text(encoding="utf-8"))

    pipeline = OrientIAPipeline(
        client, fiches,
        use_metadata_filter=True,
        use_golden_qa=True,
        golden_qa_index_path=str(GOLDEN_QA_INDEX_PATH),
        golden_qa_meta_path=str(GOLDEN_QA_META_PATH),
    )
    pipeline.load_index_from(str(INDEX_PATH))
    print(f"==> Pipeline ready (corpus 55k, Q&A Golden, prompt v4 Sprint 11 P0)")

    print(f"\n==> Running {len(TEST_QUESTIONS)} test questions (3 hallu chantier E + 1 baseline)")
    results = []
    for i, q in enumerate(TEST_QUESTIONS, 1):
        print(f"[{i}/{len(TEST_QUESTIONS)}] {q[:80]}...", flush=True)
        r = run_one(pipeline, q)
        if r.get("error"):
            print(f"    ❌ {r['error']}")
        else:
            print(f"    ✅ t={r['t_total_ms']}ms | {r['answer_word_count']} mots")
        results.append(r)

    OUTPUT_DOC.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_DOC.write_text(render_md(results), encoding="utf-8")
    print(f"\n==> Sample audit : {OUTPUT_DOC}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
