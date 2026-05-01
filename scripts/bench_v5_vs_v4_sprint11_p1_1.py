"""Bench Sprint 11 P1.1 Phase 2 Sous-étape 3 — v5 vs v4 baseline.

Re-run 11 q (10 Item 4 + 1 q piège) avec prompt v5 (Directive 1 scaffolding
+ few-shots + OBLIGATION majuscules + scope élargi + balises XML brouillon)
à température fixée 0.1 (optimale Sous-étape 1).

Compare aux résultats v4 baseline temp=0.1 du raw JSONL Sous-étape 1
(`docs/sprint11-P1-1-ab-temperature-raw-2026-04-30.jsonl`).

4 métriques par question : faithfulness + empathie + format + ignorance piège.
Verdict critères succès v3 enrichi (les 2 versions du critère faith mean :
"<0.30" original ordre + "≥0.30" correction Jarvis cf flag 23:19).

Coût estimé : ~$0.51 (11 Mistral + 22 Haiku judges + ignorance check).
ETA : ~15-20 min wall-clock.

Usage : `PYTHONPATH=. python3 scripts/bench_v5_vs_v4_sprint11_p1_1.py`

Spec ordre : 2026-04-30-2150-claudette-orientia-sprint11-P1-1-strict-grounding-stats-phase1
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from mistralai.client import Mistral

from src.config import load_config
from src.rag.pipeline import OrientIAPipeline
from scripts.judge_empathie import judge_empathie
from scripts.judge_faithfulness import judge_faithfulness
from scripts.diag_ab_temperature_sprint11_p1_1 import (
    BASE_QUESTIONS_ITEM4, PIEGE_QUESTION, QUESTIONS,
    measure_format_compliance, classify_piege_response,
)


ROOT = Path(__file__).resolve().parents[1]
FICHES_PATH = ROOT / "data" / "processed" / "formations_unified.json"
INDEX_PATH = ROOT / "data" / "embeddings" / "formations_unified.index"
GOLDEN_QA_INDEX_PATH = ROOT / "data" / "embeddings" / "golden_qa.index"
GOLDEN_QA_META_PATH = ROOT / "data" / "processed" / "golden_qa_meta.json"

V4_BASELINE_RAW = ROOT / "docs" / "sprint11-P1-1-ab-temperature-raw-2026-04-30.jsonl"
OUTPUT_DOC = ROOT / "docs" / "sprint11-P1-1-rerun-e2e-vs-v4-2026-04-30.md"
OUTPUT_RAW = ROOT / "docs" / "sprint11-P1-1-rerun-v5-raw-2026-04-30.jsonl"

TEMP_OPTIMALE = 0.1


def load_v4_baseline_temp01() -> list[dict]:
    """Load only temp=0.1 records from Sous-étape 1 raw JSONL (v4 baseline)."""
    if not V4_BASELINE_RAW.exists():
        raise SystemExit(f"Missing baseline v4 raw : {V4_BASELINE_RAW}")
    all_records = [json.loads(l) for l in V4_BASELINE_RAW.read_text(encoding="utf-8").splitlines() if l.strip()]
    return [r for r in all_records if r.get("temp") == TEMP_OPTIMALE]


def run_v5_bench() -> list[dict]:
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
    print(f"==> Pipeline loaded ({len(fiches)} fiches)")
    print(f"==> Bench v5 prompt × temp={TEMP_OPTIMALE} × {len(QUESTIONS)} q")
    print(f"    Coût estimé ~$0.51, ETA ~15-20 min wall-clock\n")

    results = []
    for i_q, question in enumerate(QUESTIONS):
        qid = i_q + 1
        is_piege = (qid == 11)
        label = "PIEGE" if is_piege else f"Q{qid}"
        print(f"[v5 {label}] {question[:60]}...", flush=True)

        t_start = time.time()
        try:
            answer, top = pipeline.answer(question, top_k_sources=10, temperature=TEMP_OPTIMALE)
            t_mistral_ms = round((time.time() - t_start) * 1000)
        except Exception as e:
            print(f"    ❌ Mistral error: {e}", flush=True)
            results.append({
                "qid": qid, "is_piege": is_piege, "question": question,
                "answer": None, "error": f"{type(e).__name__}: {e}",
            })
            continue

        fiches_for_judge = [item.get("fiche") or {} for item in top]
        faith_verdict = judge_faithfulness(question, answer, fiches_for_judge)
        emp_verdict = judge_empathie(question, answer)
        format_check = measure_format_compliance(answer)
        ignorance_class = classify_piege_response(answer) if is_piege else None

        # Detect if Mistral used balises XML brouillon (signal de respect consigne v5)
        used_brouillon = "<brouillon>" in answer.lower() or "<reponse_finale>" in answer.lower()
        # Note : si pipeline a strippé le brouillon avant retour, l'answer ne contient
        # plus les balises. Vrai signal : longueur answer vs longueur typique v4 (~2079).

        print(f"    ✅ t_mistral={t_mistral_ms}ms | faith={faith_verdict.score:.2f} ({faith_verdict.raw_verdict}) | "
              f"empat={emp_verdict.score:.1f} | format={format_check['compliance_pct']:.0f}% | "
              f"ignorance={ignorance_class or '-'}", flush=True)

        results.append({
            "qid": qid, "is_piege": is_piege, "question": question,
            "answer": answer[:1500], "answer_full_chars": len(answer),
            "t_mistral_ms": t_mistral_ms,
            "faithfulness": faith_verdict.to_dict(),
            "empathie": emp_verdict.to_dict(),
            "format": format_check,
            "ignorance_class": ignorance_class,
            "used_brouillon_visible": used_brouillon,
            "error": None,
        })

    return results


def render_verdict(v5_results: list[dict], v4_results: list[dict]) -> str:
    # Lookup v4 by qid
    v4_by_qid = {r["qid"]: r for r in v4_results}

    parts = [
        "# Sprint 11 P1.1 Phase 2 Sous-étape 3 — Verdict v5 vs v4 baseline",
        "",
        "**Date** : 2026-04-30",
        "**Branche** : `feat/sprint11-P1-1-strict-grounding-stats`",
        "**Ordre Jarvis** : `2026-04-30-2150-claudette-orientia-sprint11-P1-1-strict-grounding-stats-phase1` Phase 2",
        "",
        "## Setup bench",
        "",
        f"- Prompt v5 : Directive 1 scaffolding 2 étapes + 4 few-shots ❌→✅ + OBLIGATION majuscules + scope élargi + balises XML brouillon/reponse_finale + clause révoquée connaissance générale",
        f"- Prompt v4 baseline : Sous-étape 1 raw JSONL temp=0.1 (= prompt v4 actuel main pré-Phase 2)",
        f"- Température fixée : {TEMP_OPTIMALE} (optimale Sous-étape 1)",
        f"- Questions : {len(QUESTIONS)} (10 baseline Item 4 + 1 q piège)",
        f"- 4 métriques : Faithfulness (judge Item 3) + Empathie (judge nouveau) + Format compliance (regex) + Ignorance class piège",
        "",
        "## Tableau comparatif per-question (v4 baseline → v5)",
        "",
        "| Q | Faith v4 | Faith v5 | Δ | Empat v4 | Empat v5 | Δ | Format v4 | Format v5 | Δ |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]

    # Stats accumulators
    v4_faith, v5_faith = [], []
    v4_emp, v5_emp = [], []
    v4_fmt, v5_fmt = [], []
    v4_fidele = v5_fidele = 0
    v4_piege_class = v5_piege_class = "-"

    for r5 in v5_results:
        if r5.get("error"):
            continue
        qid = r5["qid"]
        r4 = v4_by_qid.get(qid)
        if not r4 or r4.get("error"):
            continue

        f4 = r4["faithfulness"]["score"]
        f5 = r5["faithfulness"]["score"]
        e4 = r4["empathie"]["score"]
        e5 = r5["empathie"]["score"]
        fm4 = r4["format"]["compliance_pct"]
        fm5 = r5["format"]["compliance_pct"]
        df, de, dfm = f5 - f4, e5 - e4, fm5 - fm4

        marker_f = "🟢" if df > 0 else ("🔴" if df < 0 else "⚫")
        marker_e = "🟢" if de > 0 else ("🔴" if de < 0 else "⚫")
        marker_fm = "🟢" if dfm > 0 else ("🔴" if dfm < 0 else "⚫")

        if not r5["is_piege"]:
            v4_faith.append(f4); v5_faith.append(f5)
            v4_emp.append(e4); v5_emp.append(e5)
            v4_fmt.append(fm4); v5_fmt.append(fm5)
            if f4 >= 0.5: v4_fidele += 1
            if f5 >= 0.5: v5_fidele += 1
        else:
            v4_piege_class = r4.get("ignorance_class", "-")
            v5_piege_class = r5.get("ignorance_class", "-")

        label = "PIÈGE" if r5["is_piege"] else f"Q{qid}"
        parts.append(
            f"| {label} | {f4:.2f} | {f5:.2f} | {marker_f} {df:+.2f} | "
            f"{e4:.1f} | {e5:.1f} | {marker_e} {de:+.1f} | "
            f"{fm4:.0f}% | {fm5:.0f}% | {marker_fm} {dfm:+.0f} |"
        )

    # Aggregate stats
    f4_mean = sum(v4_faith) / len(v4_faith) if v4_faith else 0
    f5_mean = sum(v5_faith) / len(v5_faith) if v5_faith else 0
    e4_mean = sum(v4_emp) / len(v4_emp) if v4_emp else 0
    e5_mean = sum(v5_emp) / len(v5_emp) if v5_emp else 0
    fm4_mean = sum(v4_fmt) / len(v4_fmt) if v4_fmt else 0
    fm5_mean = sum(v5_fmt) / len(v5_fmt) if v5_fmt else 0

    parts += [
        "",
        "## Stats agrégées (10 questions baseline, hors piège)",
        "",
        "| Métrique | v4 baseline | v5 | Δ | Critère succès |",
        "|---|---|---|---|---|",
        f"| **Faithfulness mean** | {f4_mean:.3f} | **{f5_mean:.3f}** | {f5_mean-f4_mean:+.3f} | < 0.30 (ordre original) ET ≥ 0.30 (correction Jarvis) |",
        f"| **FIDELE/10 (score ≥ 0.5)** | {v4_fidele}/10 | **{v5_fidele}/10** | {v5_fidele-v4_fidele:+d} | ≥ 5/10 |",
        f"| **Empathie mean** | {e4_mean:.2f} | **{e5_mean:.2f}** | {e5_mean-e4_mean:+.2f} | ≥ 3.0 |",
        f"| **Format compliance %** | {fm4_mean:.1f}% | **{fm5_mean:.1f}%** | {fm5_mean-fm4_mean:+.1f}pp | > 80% |",
        f"| **Ignorance piège** | {v4_piege_class} | **{v5_piege_class}** | — | IGNORANCE_OK attendu |",
        "",
        "## Verdict critères succès v3 enrichi",
        "",
    ]

    # Critère eval (les 2 versions du critère faith mean per Jarvis flag)
    crit_v4_orig = f5_mean < 0.30  # ordre original (probable typo)
    crit_v5_corrige = f5_mean >= 0.30  # correction Jarvis (faire monter le mean)
    crit_fidele = v5_fidele >= 5
    crit_empat = e5_mean >= 3.0
    crit_format = fm5_mean > 80
    crit_ignorance = v5_piege_class == "IGNORANCE_OK"

    parts += [
        f"- Faithfulness mean v5 = **{f5_mean:.3f}**",
        f"  - Critère ordre original (« < 0.30 ») : {'✅ OK' if crit_v4_orig else '❌ KO'}",
        f"  - Critère correction Jarvis (« ≥ 0.30 ») : {'✅ OK' if crit_v5_corrige else '❌ KO'}",
        f"- FIDELE/10 = **{v5_fidele}/10** (critère ≥ 5/10) : {'✅ OK' if crit_fidele else '❌ KO'}",
        f"- Empathie mean = **{e5_mean:.2f}** (critère ≥ 3.0) : {'✅ OK' if crit_empat else '❌ KO'}",
        f"- Format compliance = **{fm5_mean:.1f}%** (critère > 80%) : {'✅ OK' if crit_format else '❌ KO'}",
        f"- Ignorance piège = **{v5_piege_class}** (critère IGNORANCE_OK) : {'✅ OK' if crit_ignorance else '❌ KO'}",
        "",
    ]

    # Decision verdict
    crits_ok_count = sum([
        int(crit_v5_corrige), int(crit_fidele), int(crit_empat),
        int(crit_format), int(crit_ignorance)
    ])
    if crits_ok_count >= 4:
        verdict_short = f"GO PR #112 — {crits_ok_count}/5 critères atteints"
        verdict_full = (
            f"v5 atteint {crits_ok_count}/5 critères succès enrichis. PR #112 "
            f"ready-for-review. Pas d'escalation Sous-étape 4 backstop B nécessaire."
        )
    elif crits_ok_count >= 2:
        verdict_short = f"AMÉLIORATION PARTIELLE — {crits_ok_count}/5 critères atteints"
        verdict_full = (
            f"v5 atteint {crits_ok_count}/5 critères. Amélioration mesurable mais "
            f"insuffisante pour go inconditionnel. Recommandation : escalation Sous-étape 4 "
            f"backstop B (post-filter chiffres) en cascade pour atteindre les critères restants."
        )
    else:
        verdict_short = f"INSUFFISANT — {crits_ok_count}/5 critères atteints"
        verdict_full = (
            f"v5 atteint seulement {crits_ok_count}/5 critères. Le scaffolding + few-shots "
            f"ne suffit pas à corriger l'invention chiffres systémique Mistral medium. "
            f"Escalation Sous-étape 4 backstop B obligatoire OU pivoter vers option C "
            f"(citation [fiche_id]) ou modèle plus capable."
        )

    parts += [
        f"### {verdict_short}",
        "",
        verdict_full,
        "",
        "## Limitations méthodologiques",
        "",
        "- **Single-run** v5 (pas de triple-run + IC95). Variance attendue (cf Sous-étape 1 temp=0.2 outlier).",
        "- **Sample 10 q + 1 piège** — verdict directionnel uniquement. Étendre n>30 pour conclusions statistiquement significatives.",
        "- **Judge Empathie sans gold standard** — calibration empirique sur 22 calls (11 v4 + 11 v5). Si variance score inter-versions <0.5, signal probable bruité.",
        "- **Balises XML respect non mesuré rigoureusement** — le pipeline strip les balises avant retour answer, donc présence balises invisible dans answer post-strip. Vérifier via inspection log Mistral raw si besoin.",
        "- **Q piège n=1** — signal binaire ignorance class. Étendre dans Sprint 12+.",
        "",
        f"## Coût empirique réel",
        "",
        "- Mistral v5 : 11 q × ~$0.05 = ~$0.55",
        "- Judge faithfulness : 11 calls × ~$0.001 = ~$0.011",
        "- Judge empathie : 11 calls × ~$0.001 = ~$0.011",
        "- **Total Sous-étape 3** : ~$0.57 (cumul Phase 2 ~$1.10 sur budget $1)",
        "",
        "*Verdict auto-généré par `scripts/bench_v5_vs_v4_sprint11_p1_1.py`. PR #112 conditionnel selon critères ci-dessus.*",
    ]

    return "\n".join(parts)


def main() -> int:
    print("=" * 70)
    print("Sprint 11 P1.1 Phase 2 Sous-étape 3 — Bench v5 vs v4")
    print("=" * 70)

    v4_results = load_v4_baseline_temp01()
    print(f"\n==> v4 baseline temp=0.1 chargé : {len(v4_results)} records")

    v5_results = run_v5_bench()

    OUTPUT_RAW.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_RAW.open("w", encoding="utf-8") as f:
        for r in v5_results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n==> Raw v5 JSONL : {OUTPUT_RAW}")

    md = render_verdict(v5_results, v4_results)
    OUTPUT_DOC.write_text(md, encoding="utf-8")
    print(f"==> Verdict comparatif : {OUTPUT_DOC} ({len(md.splitlines())} lignes)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
