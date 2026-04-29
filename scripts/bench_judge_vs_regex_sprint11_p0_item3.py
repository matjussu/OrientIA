"""Bench A/B comparatif — LLM-Judge Faithfulness vs regex naïf — Sprint 11 P0 Item 3.

Utilise les 10 réponses Mistral cachées du test serving chantier E
(`docs/sprint10-E-raw-results-2026-04-29.jsonl`) pour comparer deux métriques :
- (A) Regex naïve `measure_pollution()` (test_serving_e2e.py) — string matching entités
- (B) LLM-Judge `judge_faithfulness()` (claude-haiku-4-5)

Sortie : tableau MD per question + faux positifs/négatifs vs ground truth Matteo
(Q5 IFSI / Q8 DEAMP / Q10 Terminale L = INFIDELE attendu, autres = NON-FLAGGED
attendu sauf si LLM hallu non détectée par audit qualitatif initial).

Décision data-driven : remplace regex (judge couvre tout) OU complémentaire
(regex catch ce que judge manque) OU regex retiré purement.

Coût : ~10 × $0.001 = $0.01 + ~5 min wall-clock (10 × ~30s subprocess).

Usage : `PYTHONPATH=. python3 scripts/bench_judge_vs_regex_sprint11_p0_item3.py`

Spec ordre : 2026-04-29-2055-claudette-orientia-sprint11-P0-item3-llm-judge-faithfulness
"""
from __future__ import annotations

import json
import time
from pathlib import Path

# Reuse the regex measure from test_serving_e2e
from scripts.judge_faithfulness import judge_faithfulness
from scripts.test_serving_e2e import measure_pollution


ROOT = Path(__file__).resolve().parents[1]
JSONL_PATH = ROOT / "docs" / "sprint10-E-raw-results-2026-04-29.jsonl"
FICHES_PATH = ROOT / "data" / "processed" / "formations_unified.json"
OUTPUT_DOC = ROOT / "docs" / "sprint11-P0-item3-bench-judge-vs-regex-2026-04-29.md"
OUTPUT_JSONL = ROOT / "docs" / "sprint11-P0-item3-bench-raw-2026-04-29.jsonl"


# Ground truth Matteo — 0-indexed in JSONL
HUMAN_GROUND_TRUTH = {
    0: ("UNKNOWN", "Q1 maths-physique — pas audit Matteo"),
    1: ("UNKNOWN", "Q2 L1 droit réorientation — pas audit Matteo"),
    2: ("UNKNOWN", "Q3 prépa MPSI burn-out — pas audit Matteo"),
    3: ("UNKNOWN", "Q4 boursière logement — Matteo non flagué (off-topic corpus formations)"),
    4: ("INFIDELE", "Q5 PASS/IFSI — Matteo flagué : 'concours post-bac' inexistant (Parcoursup dossier depuis 2019)"),
    5: ("UNKNOWN", "Q6 cybersécu Toulouse — pas audit Matteo"),
    6: ("UNKNOWN", "Q7 master droit affaires — pas audit Matteo"),
    7: ("INFIDELE", "Q8 reconversion paramédical — Matteo flagué : DEAMP fantôme (fusionné DEAES 2016)"),
    8: ("UNKNOWN", "Q9 fils plomberie ingé — pas audit Matteo"),
    9: ("INFIDELE", "Q10 Terminale L — Matteo flagué : série supprimée réforme bac 2021"),
}


def _load_fiches_lookup() -> dict:
    fiches = json.loads(FICHES_PATH.read_text())
    return {fi.get("id") or fi.get("identifiant"): fi for fi in fiches}


def _resolve_fiches(record: dict, lookup: dict, max_n: int = 5) -> list[dict]:
    seen, out = set(), []
    for s in record.get("sources", []):
        fid = s.get("fiche_id")
        if fid and fid in lookup and fid not in seen:
            seen.add(fid)
            out.append(lookup[fid])
            if len(out) >= max_n:
                break
    return out


def _full_sources(record: dict, lookup: dict) -> list[dict]:
    """Reconstruit la liste sources avec fiche complète (pour regex measure_pollution)."""
    out = []
    for s in record.get("sources", []):
        fid = s.get("fiche_id")
        fi = lookup.get(fid) or {"nom": s.get("fiche_nom", "?")}
        out.append({"score": s.get("score"), "fiche": fi})
    return out


def main() -> int:
    print(f"==> Bench A/B sur {JSONL_PATH.name}")
    records = [json.loads(line) for line in JSONL_PATH.read_text().splitlines() if line.strip()]
    print(f"    {len(records)} records loaded")

    lookup = _load_fiches_lookup()
    print(f"    Fiches lookup : {len(lookup)} fiches indexées")

    bench_results = []
    for idx, record in enumerate(records):
        question = record["question"]
        answer = record.get("answer") or ""
        sources_full = _full_sources(record, lookup)
        fiches_for_judge = _resolve_fiches(record, lookup, max_n=5)

        print(f"\n[{idx+1}/{len(records)}] {question[:70]}...", flush=True)

        # Metric A — regex naïf (existant)
        t0 = time.time()
        regex_result = measure_pollution(answer, sources_full, golden_qa_record=None)
        regex_latency = round((time.time() - t0) * 1000)
        # On déclare "FLAGGED par regex" si pollution_rate > 0.10 (seuil chantier E "5-15%" du middle)
        regex_flagged = regex_result["pollution_rate"] > 0.10
        regex_verdict = "INFIDELE" if regex_flagged else "FIDELE"

        # Metric B — LLM-Judge
        verdict = judge_faithfulness(question, answer, fiches_for_judge)
        judge_verdict = verdict.raw_verdict
        # On déclare "FLAGGED par juge" si score < 0.5
        judge_flagged = verdict.score < 0.5

        # Ground truth Matteo
        human_verdict, human_note = HUMAN_GROUND_TRUTH[idx]

        print(f"    REGEX  : pollution_rate={regex_result['pollution_rate']*100:.0f}% "
              f"({regex_result['polluted_count']} entities) → flagged={regex_flagged}")
        print(f"    JUDGE  : verdict={judge_verdict} score={verdict.score} "
              f"({len(verdict.flagged_entities)} elements) → flagged={judge_flagged} "
              f"latency={verdict.latency_ms}ms")
        print(f"    HUMAN  : {human_verdict} — {human_note}")

        bench_results.append({
            "qid": idx + 1,
            "question": question,
            "regex": {
                "pollution_rate": regex_result["pollution_rate"],
                "polluted_count": regex_result["polluted_count"],
                "polluted_entities": regex_result["polluted_entities"][:10],
                "flagged": regex_flagged,
                "verdict": regex_verdict,
                "latency_ms": regex_latency,
            },
            "judge": {
                "verdict": judge_verdict,
                "score": verdict.score,
                "n_flagged": len(verdict.flagged_entities),
                "flagged_entities": verdict.flagged_entities[:5],
                "justification": verdict.justification,
                "flagged": judge_flagged,
                "latency_ms": verdict.latency_ms,
                "parse_errors": verdict.parse_errors,
                "error": verdict.error,
            },
            "human": {"verdict": human_verdict, "note": human_note},
        })

    # Save raw JSONL
    OUTPUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_JSONL.open("w", encoding="utf-8") as f:
        for r in bench_results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n==> Raw bench data : {OUTPUT_JSONL}")

    # Render report MD
    md = render_report(bench_results)
    OUTPUT_DOC.write_text(md, encoding="utf-8")
    print(f"==> Bench report MD : {OUTPUT_DOC} ({len(md.splitlines())} lignes)")
    return 0


def render_report(results: list[dict]) -> str:
    """Render bench A/B comparison MD report, lisible mobile."""
    n = len(results)

    # Compute confusion vs ground truth (only for known cases)
    known = [r for r in results if r["human"]["verdict"] in ("FIDELE", "INFIDELE")]
    n_known = len(known)

    # Regex confusion
    regex_tp = sum(1 for r in known if r["regex"]["flagged"] and r["human"]["verdict"] == "INFIDELE")
    regex_fn = sum(1 for r in known if not r["regex"]["flagged"] and r["human"]["verdict"] == "INFIDELE")
    regex_tn = sum(1 for r in known if not r["regex"]["flagged"] and r["human"]["verdict"] == "FIDELE")
    regex_fp = sum(1 for r in known if r["regex"]["flagged"] and r["human"]["verdict"] == "FIDELE")

    # Judge confusion
    judge_tp = sum(1 for r in known if r["judge"]["flagged"] and r["human"]["verdict"] == "INFIDELE")
    judge_fn = sum(1 for r in known if not r["judge"]["flagged"] and r["human"]["verdict"] == "INFIDELE")
    judge_tn = sum(1 for r in known if not r["judge"]["flagged"] and r["human"]["verdict"] == "FIDELE")
    judge_fp = sum(1 for r in known if r["judge"]["flagged"] and r["human"]["verdict"] == "FIDELE")

    # Latence stats
    judge_lat = [r["judge"]["latency_ms"] for r in results]
    regex_lat = [r["regex"]["latency_ms"] for r in results]

    parts = [
        "# Sprint 11 P0 Item 3 — Bench A/B : LLM-Judge vs Regex naïf",
        "",
        "**Date** : 2026-04-29",
        "**Branche** : `feat/sprint11-P0-llm-judge-faithfulness`",
        "**Données** : 10 réponses Mistral cachées du test serving chantier E (`docs/sprint10-E-raw-results-2026-04-29.jsonl`)",
        "**Modèle juge** : `claude-haiku-4-5` via subprocess",
        "",
        "## TL;DR",
        "",
        f"- Ground truth Matteo audit qualitatif : **3 hallu connues** (Q5 IFSI, Q8 DEAMP, Q10 Terminale L)",
        f"- **Judge LLM** : {judge_tp}/{judge_tp + judge_fn} hallu détectées (recall {100*judge_tp/max(1,judge_tp+judge_fn):.0f}%) | "
        f"{judge_fp} faux positifs sur les FIDELE connus",
        f"- **Regex naïf** : {regex_tp}/{regex_tp + regex_fn} hallu détectées (recall {100*regex_tp/max(1,regex_tp+regex_fn):.0f}%) | "
        f"{regex_fp} faux positifs sur les FIDELE connus",
        f"- **Latence judge** : médiane {sorted(judge_lat)[n//2]}ms (vs regex <50ms)",
        "",
        "## Confusion matrix vs ground truth Matteo (n=3 INFIDELE connus)",
        "",
        "| Métrique | Vrais Positifs (hallu détecté) | Faux Négatifs (hallu manqué) | Recall |",
        "|---|---|---|---|",
        f"| **LLM-Judge** | {judge_tp} | {judge_fn} | **{100*judge_tp/max(1,judge_tp+judge_fn):.0f}%** |",
        f"| **Regex naïf** | {regex_tp} | {regex_fn} | {100*regex_tp/max(1,regex_tp+regex_fn):.0f}% |",
        "",
        "## Tableau per-question complet",
        "",
        "| Q | Question | Regex flagged | Regex pollution_rate | Judge verdict | Judge score | Judge n_flagged | Human |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for r in results:
        q_short = r["question"][:60].replace("|", "\\|")
        regex_f = "🚩 OUI" if r["regex"]["flagged"] else "✅ non"
        judge_f = f"🚩 {r['judge']['verdict']}" if r["judge"]["flagged"] else f"✅ {r['judge']['verdict']}"
        human = f"⚠️ {r['human']['verdict']}" if r["human"]["verdict"] == "INFIDELE" else r["human"]["verdict"]
        parts.append(
            f"| Q{r['qid']} | {q_short}... | {regex_f} | {r['regex']['pollution_rate']*100:.0f}% | "
            f"{judge_f} | {r['judge']['score']:.2f} | {r['judge']['n_flagged']} | {human} |"
        )

    parts += [
        "",
        "## Détail des 3 hallucinations Matteo (test discriminant)",
        "",
    ]

    for r in results:
        if r["human"]["verdict"] != "INFIDELE":
            continue
        parts += [
            f"### Q{r['qid']} — {r['human']['note']}",
            "",
            f"**Regex naïf** : pollution_rate={r['regex']['pollution_rate']*100:.0f}% — "
            f"{'✅ DÉTECTÉ' if r['regex']['flagged'] else '❌ MANQUÉ'}",
            f"  - Top entities flaggées (regex) : {', '.join(r['regex']['polluted_entities'][:5])}",
            "",
            f"**LLM-Judge** : verdict={r['judge']['verdict']} score={r['judge']['score']:.2f} — "
            f"{'✅ DÉTECTÉ' if r['judge']['flagged'] else '❌ MANQUÉ'}",
            f"  - Justification : {r['judge']['justification'][:300]}",
            f"  - Top elements flagués (judge) :",
        ]
        for el in r["judge"]["flagged_entities"][:3]:
            parts.append(f"     - {str(el)[:200]}")
        parts.append("")

    parts += [
        "## Coût + latence empirique",
        "",
        f"- LLM-Judge : médiane {sorted(judge_lat)[n//2]}ms, max {max(judge_lat)}ms (subprocess `claude --print --model claude-haiku-4-5`)",
        f"- Regex naïf : <{max(regex_lat)+1}ms (CPU pur)",
        f"- Coût total ce bench : 10 × ~$0.001 = ~$0.01 (Haiku tokens)",
        f"- Pour CI/dev offline : acceptable (~5 min wall-clock par bench complet)",
        f"- Pour runtime prod : **PAS APPROPRIÉ** (latence + souveraineté FR — utiliser Mistral si transfert prod Sprint 12+)",
        "",
        "## Recommandation Item 3",
        "",
    ]

    if judge_tp >= regex_tp and judge_fp <= regex_fp:
        recommendation = (
            "**REMPLACER** le regex naïf par le LLM-Judge dans `test_serving_e2e.py`. "
            "Le judge a un recall équivalent ou supérieur sur les 3 hallu connues, sans excès de faux positifs sur les cas non-flaggés."
        )
    elif judge_tp > regex_tp and judge_fp > regex_fp:
        recommendation = (
            "**COMPLÉMENTAIRE** : garder le regex (rapide, déterministe) + ajouter le judge "
            "(sémantique, catche ce que regex manque). Trade-off recall/precision à arbitrer Matteo."
        )
    else:
        recommendation = (
            "**REGEX SUFFISANT** (étonnamment) — le judge n'apporte pas de gain mesurable sur ce sample. "
            "Étendre le ground truth audit Matteo avant de revoir."
        )
    parts.append(recommendation)

    parts += [
        "",
        "## Limitations méthodologiques",
        "",
        "- Sample size : seulement 3 hallu ground truth (Matteo audit qualitatif n=10). Recall calculé sur n=3 = signal faible.",
        "- Les 7 autres questions ne sont pas \"FIDELE\" certifiées — Matteo n'a pas audité chacune. Donc les FP/FN sur ces 7 sont indicatifs, pas définitifs.",
        "- Le seuil regex 'pollution_rate > 10%' est arbitraire (chantier E parlait 5-15% comme zone trouble).",
        "- Le seuil judge 'score < 0.5' est calibré pour respecter la spec (ground truth doit être < 0.5).",
        "",
        "*Bench généré par `scripts/bench_judge_vs_regex_sprint11_p0_item3.py` "
        "sous l'ordre `2026-04-29-2055-claudette-orientia-sprint11-P0-item3-llm-judge-faithfulness`.*",
    ]

    return "\n".join(parts)


if __name__ == "__main__":
    raise SystemExit(main())
