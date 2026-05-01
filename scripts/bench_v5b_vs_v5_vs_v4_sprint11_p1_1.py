"""Bench Sprint 11 P1.1 Sous-étape 4.3 — v5b investigation vs v5 vs v4 baseline.

Re-run 11 q (10 Item 4 + 1 q piège) avec prompt v5b (Directive 1 scaffolding
+ few-shots + OBLIGATION majuscules + scope élargi MAIS SANS balises XML
brouillon — hypothèse coupable format dégradé v5).

Compare aux raws existants :
- v4 baseline : Sous-étape 1 raw temp=0.1
- v5 (avec balises XML) : Sous-étape 3 raw

**Fixes méthodologiques Sous-étape 4.1 appliqués** :
- Regex classifier ignorance étendu (matche "d'information", "ne sont pas couvertes par les fiches")
- Format compliance recalculé en excluant Q4 (off-topic boursière) + Q11 (piège)
  → 8 q ON-TOPIC seulement pour mesurer format Plans A/B/C
- Re-classification ignorance v4 + v5 raw avec nouveau pattern pour comparaison équitable

Coût estimé : ~$0.51 (11 Mistral + 22 Haiku judges).
ETA : ~15-20 min wall-clock.

Usage : `PYTHONPATH=. python3 scripts/bench_v5b_vs_v5_vs_v4_sprint11_p1_1.py`

Spec ordre : 2026-05-01-0000-claudette-orientia-sprint11-P1-1-substep-4-v5b-investigation
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
    QUESTIONS, PIEGE_QUESTION,
    measure_format_compliance, classify_piege_response,  # v2 patterns post-fix
)


ROOT = Path(__file__).resolve().parents[1]
FICHES_PATH = ROOT / "data" / "processed" / "formations_unified.json"
INDEX_PATH = ROOT / "data" / "embeddings" / "formations_unified.index"
GOLDEN_QA_INDEX_PATH = ROOT / "data" / "embeddings" / "golden_qa.index"
GOLDEN_QA_META_PATH = ROOT / "data" / "processed" / "golden_qa_meta.json"

V4_RAW = ROOT / "docs" / "sprint11-P1-1-ab-temperature-raw-2026-04-30.jsonl"
V5_RAW = ROOT / "docs" / "sprint11-P1-1-rerun-v5-raw-2026-04-30.jsonl"
OUTPUT_DOC = ROOT / "docs" / "sprint11-P1-1-rerun-e2e-v5b-vs-v5-vs-v4-2026-04-30.md"
OUTPUT_RAW = ROOT / "docs" / "sprint11-P1-1-rerun-v5b-raw-2026-05-01.jsonl"

TEMP_OPTIMALE = 0.1

# Q4 (boursière logement) + Q11 (piège ignorance) = OFF-TOPIC corpus
# → exclus du calcul format compliance (qui mesure pattern Plans A/B/C ON-TOPIC)
OFF_TOPIC_QIDS = {4, 11}
ON_TOPIC_QIDS = {q for q in range(1, 12) if q not in OFF_TOPIC_QIDS}


def load_raw_temp01(path: Path, filter_temp: bool = False) -> list[dict]:
    if not path.exists():
        raise SystemExit(f"Missing raw : {path}")
    records = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if filter_temp:
        records = [r for r in records if r.get("temp") == TEMP_OPTIMALE]
    return records


def re_classify_ignorance_with_fix(records: list[dict]) -> dict:
    """Re-applique le classifier ignorance v2 (fix Sous-étape 4.1) sur les raws.
    Returns {qid: new_class} pour les Q piège."""
    out = {}
    for r in records:
        if r.get("is_piege"):
            new_class = classify_piege_response(r.get("answer") or "")
            out[r["qid"]] = new_class
    return out


def aggregate_metrics_v2(records: list[dict], piege_class_override: str | None = None) -> dict:
    """Agrégation avec fixes Sous-étape 4.1 :
    - Format compliance calculé sur ON_TOPIC_QIDS uniquement (8 q, exclut Q4+Q11)
    - Format compliance "ancienne formule" préservée pour transparence (10 q baseline hors Q11)
    - Ignorance class du piège : utilise override si fourni (post-re-classification)
    """
    valid = [r for r in records if r.get("error") is None]
    baseline_10 = [r for r in valid if not r.get("is_piege")]
    on_topic_8 = [r for r in valid if r["qid"] in ON_TOPIC_QIDS and not r.get("is_piege")]
    piege = [r for r in valid if r.get("is_piege")]

    # Faithfulness mean + FIDELE/10 (sur 10 baseline hors piège, comme avant)
    faith = [r["faithfulness"]["score"] for r in baseline_10]
    faith_mean = sum(faith) / len(faith) if faith else 0
    fidele_count = sum(1 for s in faith if s >= 0.5)

    # Empathie mean (sur 10 baseline)
    emp = [r["empathie"]["score"] for r in baseline_10]
    emp_mean = sum(emp) / len(emp) if emp else 0

    # Format compliance — 2 versions
    fmt_old = [r["format"]["compliance_pct"] for r in baseline_10]
    fmt_old_mean = sum(fmt_old) / len(fmt_old) if fmt_old else 0
    fmt_new = [r["format"]["compliance_pct"] for r in on_topic_8]
    fmt_new_mean = sum(fmt_new) / len(fmt_new) if fmt_new else 0

    # Ignorance piège
    if piege_class_override is not None:
        piege_class = piege_class_override
    else:
        piege_class = piege[0].get("ignorance_class", "-") if piege else "-"

    return {
        "n_valid": len(valid),
        "n_baseline_10": len(baseline_10),
        "n_on_topic_8": len(on_topic_8),
        "faith_mean": faith_mean,
        "fidele_count": fidele_count,
        "emp_mean": emp_mean,
        "format_old_mean_10q": fmt_old_mean,
        "format_new_mean_8q": fmt_new_mean,
        "piege_class": piege_class,
    }


def run_v5b_bench() -> list[dict]:
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
    print(f"==> Bench v5b prompt × temp={TEMP_OPTIMALE} × {len(QUESTIONS)} q")
    print(f"    Coût estimé ~$0.51, ETA ~15-20 min wall-clock\n")

    results = []
    for i_q, question in enumerate(QUESTIONS):
        qid = i_q + 1
        is_piege = (qid == 11)
        label = "PIEGE" if is_piege else f"Q{qid}"
        print(f"[v5b {label}] {question[:60]}...", flush=True)

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
            "error": None,
        })

    return results


def render_verdict(v5b_results: list[dict], v5_results: list[dict], v4_results: list[dict],
                   stats_v5b: dict, stats_v5: dict, stats_v4: dict,
                   piege_v4_new: str, piege_v5_new: str) -> str:
    parts = [
        "# Sprint 11 P1.1 Sous-étape 4 — Verdict v5b vs v5 vs v4 baseline",
        "",
        "**Date** : 2026-05-01",
        "**Branche** : `feat/sprint11-P1-1-strict-grounding-stats` (PR #112)",
        "**Ordre Jarvis** : `2026-05-01-0000-claudette-orientia-sprint11-P1-1-substep-4-v5b-investigation`",
        "",
        "## §1 Setup et changements v5b vs v5",
        "",
        "**v5b = v5 - balises XML brouillon** :",
        "- ✅ GARDÉ : scaffolding 2 étapes (vérification source / reformulation qualitative)",
        "- ✅ GARDÉ : 4 few-shots concrets ❌→✅ (IFSI / Master Droit / Salaire LEA / L.AS Sorbonne)",
        "- ✅ GARDÉ : clause OBLIGATION en MAJUSCULES",
        "- ✅ GARDÉ : scope élargi tous types factuels",
        "- ❌ RETIRÉ : section \"STRUCTURE DE RÉPONSE OBLIGATOIRE — BALISES XML\" (instruction `<brouillon>`/`<reponse_finale>`)",
        "- Température fixée : **0.1** (idem v5)",
        "",
        "**Hypothèse Matteo** : balises XML ont surchargé instruction-following Mistral medium → format Plans A/B/C sacrifié pour respecter split XML. Ablation préalable obligatoire avant escalation backstop B.",
        "",
        "**Fixes méthodologiques Sous-étape 4.1 appliqués** :",
        "- Regex classifier `classify_piege_response()` v2 étendu (matche \"d'information\", \"ne sont pas couvertes par les fiches\")",
        "- Format compliance recalculé sur 8 q ON-TOPIC seulement (exclut Q4 boursière logement + Q11 piège ignorance, OFF-TOPIC corpus)",
        "- Re-classification ignorance v4 + v5 raw avec pattern v2 pour comparaison équitable",
        "",
        "## §2 Tableau comparatif tri-version per-question",
        "",
        "| Q | Type | Faith v4 | Faith v5 | Faith v5b | Format v4 | Format v5 | Format v5b |",
        "|---|---|---|---|---|---|---|---|",
    ]

    v4_by_qid = {r["qid"]: r for r in v4_results}
    v5_by_qid = {r["qid"]: r for r in v5_results}
    v5b_by_qid = {r["qid"]: r for r in v5b_results}

    for qid in range(1, 12):
        r4 = v4_by_qid.get(qid)
        r5 = v5_by_qid.get(qid)
        rb = v5b_by_qid.get(qid)
        if not (r4 or r5 or rb):
            continue
        is_off = qid in OFF_TOPIC_QIDS
        type_label = "OFF-TOPIC" if is_off else "ON-TOPIC"
        if qid == 11:
            type_label = "PIEGE"

        def fmt_faith(r):
            if r is None or r.get("error"): return "—"
            return f"{r['faithfulness']['score']:.2f}"
        def fmt_fmt(r):
            if r is None or r.get("error"): return "—"
            return f"{r['format']['compliance_pct']:.0f}%"

        parts.append(
            f"| Q{qid} | {type_label} | {fmt_faith(r4)} | {fmt_faith(r5)} | {fmt_faith(rb)} | "
            f"{fmt_fmt(r4)} | {fmt_fmt(r5)} | {fmt_fmt(rb)} |"
        )

    parts += [
        "",
        "## §3 Stats agrégées tri-version (avec fixes Sous-étape 4.1)",
        "",
        "| Métrique | v4 baseline | v5 (avec XML) | v5b (sans XML) | Critère succès |",
        "|---|---|---|---|---|",
        f"| **Faithfulness mean** (10 q) | {stats_v4['faith_mean']:.3f} | {stats_v5['faith_mean']:.3f} | **{stats_v5b['faith_mean']:.3f}** | ≥ 0.30 |",
        f"| **FIDELE/10** (score ≥ 0.5) | {stats_v4['fidele_count']}/10 | {stats_v5['fidele_count']}/10 | **{stats_v5b['fidele_count']}/10** | ≥ 5/10 |",
        f"| **Empathie mean** (10 q) | {stats_v4['emp_mean']:.2f} | {stats_v5['emp_mean']:.2f} | **{stats_v5b['emp_mean']:.2f}** | ≥ 3.0 |",
        f"| **Format compliance ANCIEN** (10 q) | {stats_v4['format_old_mean_10q']:.1f}% | {stats_v5['format_old_mean_10q']:.1f}% | **{stats_v5b['format_old_mean_10q']:.1f}%** | > 80% |",
        f"| **Format compliance NOUVEAU** (8 q ON-TOPIC) | {stats_v4['format_new_mean_8q']:.1f}% | {stats_v5['format_new_mean_8q']:.1f}% | **{stats_v5b['format_new_mean_8q']:.1f}%** | > 80% |",
        f"| **Ignorance Q11 piège** (post-fix v2) | {piege_v4_new} | {piege_v5_new} | **{stats_v5b['piege_class']}** | IGNORANCE_OK |",
        "",
        "**Note transparence formule format** : ancienne formule (10 q baseline hors Q11) incluait Q4 boursière logement (off-topic, fallback ressources externes correct) qui ne suit pas le pattern Plans A/B/C par nature. Nouvelle formule (8 q ON-TOPIC) exclut Q4 + Q11 pour mesurer le pattern Plans A/B/C uniquement où il s'applique.",
        "",
        "## §4 Verdict critères succès v3 enrichi (avec NOUVELLE formule format)",
        "",
    ]

    crit_faith = stats_v5b["faith_mean"] >= 0.30
    crit_fidele = stats_v5b["fidele_count"] >= 5
    crit_empat = stats_v5b["emp_mean"] >= 3.0
    crit_format = stats_v5b["format_new_mean_8q"] > 80
    crit_ignorance = stats_v5b["piege_class"] == "IGNORANCE_OK"
    crits_ok_count = sum([int(crit_faith), int(crit_fidele), int(crit_empat),
                          int(crit_format), int(crit_ignorance)])

    parts += [
        f"- Faithfulness mean v5b = **{stats_v5b['faith_mean']:.3f}** (≥ 0.30) : {'✅ OK' if crit_faith else '❌ KO'}",
        f"- FIDELE/10 = **{stats_v5b['fidele_count']}/10** (≥ 5/10) : {'✅ OK' if crit_fidele else '❌ KO'}",
        f"- Empathie mean = **{stats_v5b['emp_mean']:.2f}** (≥ 3.0) : {'✅ OK' if crit_empat else '❌ KO'}",
        f"- Format compliance NOUVEAU 8 q = **{stats_v5b['format_new_mean_8q']:.1f}%** (> 80%) : {'✅ OK' if crit_format else '❌ KO'}",
        f"- Ignorance Q11 piège = **{stats_v5b['piege_class']}** (IGNORANCE_OK) : {'✅ OK' if crit_ignorance else '❌ KO'}",
        "",
        f"### Score : {crits_ok_count}/5 critères atteints",
        "",
    ]

    # Reco honnête
    parts += [
        "## §5 Reco honnête Claudette",
        "",
    ]
    if crits_ok_count >= 4:
        parts += [
            f"**SHIP v5b** ({crits_ok_count}/5 critères). v5b restaure le format compliance dégradé par v5 sans perdre l'IGNORANCE benefit OFF-TOPIC. Hypothèse Matteo (balises XML coupables format) **CONFIRMÉE empiriquement**.",
            "",
            "Recommandation : merge-approval Matteo via Jarvis pour ship v5b en remplacement v4. Pas d'escalation backstop B nécessaire dans cette voie.",
            "",
        ]
    elif crits_ok_count >= 2 and stats_v5b["format_new_mean_8q"] > stats_v5["format_new_mean_8q"]:
        parts += [
            f"**AMÉLIORATION PARTIELLE v5b vs v5** ({crits_ok_count}/5 critères). v5b restaure partiellement le format mais d'autres critères restent KO.",
            "",
            f"Hypothèse Matteo (balises XML coupables format) **PARTIELLEMENT confirmée** : delta format v5b vs v5 = {stats_v5b['format_new_mean_8q'] - stats_v5['format_new_mean_8q']:+.1f}pp. Le scaffolding seul ne suffit pas à corriger l'invention chiffres systémique.",
            "",
            "Recommandation : escalation Sous-étape 5 backstop B confirmée nécessaire (post-filter chiffres en cascade après v5b). v5b reste utile en couche 1, B en couche 2.",
            "",
        ]
    else:
        parts += [
            f"**INSUFFISANT** ({crits_ok_count}/5 critères). v5b ne restaure pas significativement vs v5. Hypothèse Matteo (balises XML coupables format) **INFIRMÉE** : la cause format dégradé est ailleurs (probablement scaffolding 2 étapes ou OBLIGATION majuscules ou prompt trop long).",
            "",
            "Recommandation : escalation backstop B obligatoire OU pivot modèle plus capable (Sonnet 4.6, souveraineté FR impactée). v5/v5b à abandonner si on retient B ou pivot.",
            "",
        ]

    parts += [
        "## §6 Captures qualitatives 3 sample (audit Matteo manuel)",
        "",
    ]

    # Sample 3 réponses : 1 Q4 (off-topic succès), 1 Q10 (ON-TOPIC régression persistante), 1 Q11 (piège)
    for sample_qid, sample_label in [(4, "Q4 OFF-TOPIC succès attendu"),
                                       (10, "Q10 ON-TOPIC régression persistante (framing Terminale L)"),
                                       (11, "Q11 PIEGE ignorance")]:
        rb = v5b_by_qid.get(sample_qid)
        if rb and not rb.get("error"):
            parts += [
                f"### {sample_label} — v5b faith={rb['faithfulness']['score']:.2f} ({rb['faithfulness']['raw_verdict']}) | format={rb['format']['compliance_pct']:.0f}%",
                "",
                "> " + (rb["answer"][:800].replace("\n", "\n> ")),
                "",
            ]

    parts += [
        "---",
        "",
        f"*Verdict v5b vs v5 vs v4 généré par `scripts/bench_v5b_vs_v5_vs_v4_sprint11_p1_1.py`. Standby arbitrage Matteo via Jarvis sur ship v5b / escalation B / pivot.*",
    ]

    return "\n".join(parts)


def main() -> int:
    print("=" * 70)
    print("Sprint 11 P1.1 Sous-étape 4 — Bench v5b vs v5 vs v4")
    print("=" * 70)

    print("\n==> Load v4 baseline raw temp=0.1")
    v4_results = load_raw_temp01(V4_RAW, filter_temp=True)
    print(f"    {len(v4_results)} records")

    print("\n==> Load v5 raw")
    v5_results = load_raw_temp01(V5_RAW, filter_temp=False)
    print(f"    {len(v5_results)} records")

    # Re-classifier ignorance v4 + v5 avec pattern v2 (fix Sous-étape 4.1)
    piege_v4_new_dict = re_classify_ignorance_with_fix(v4_results)
    piege_v5_new_dict = re_classify_ignorance_with_fix(v5_results)
    piege_v4_new = piege_v4_new_dict.get(11, "-")
    piege_v5_new = piege_v5_new_dict.get(11, "-")
    print(f"\n==> Re-classification ignorance Q11 avec fix Sous-étape 4.1 :")
    print(f"    v4 baseline Q11 : ancien PARTIAL_FUZZY → nouveau {piege_v4_new}")
    print(f"    v5 Q11 : ancien PARTIAL_FUZZY → nouveau {piege_v5_new}")

    print("\n==> Run v5b bench")
    v5b_results = run_v5b_bench()

    OUTPUT_RAW.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_RAW.open("w", encoding="utf-8") as f:
        for r in v5b_results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n==> Raw v5b JSONL : {OUTPUT_RAW}")

    # Aggregate
    stats_v4 = aggregate_metrics_v2(v4_results, piege_class_override=piege_v4_new)
    stats_v5 = aggregate_metrics_v2(v5_results, piege_class_override=piege_v5_new)
    stats_v5b = aggregate_metrics_v2(v5b_results)

    md = render_verdict(v5b_results, v5_results, v4_results,
                        stats_v5b, stats_v5, stats_v4,
                        piege_v4_new, piege_v5_new)
    OUTPUT_DOC.write_text(md, encoding="utf-8")
    print(f"==> Verdict tri-version : {OUTPUT_DOC} ({len(md.splitlines())} lignes)")

    print(f"\n=== STATS v5b ===")
    print(f"  Faith mean : {stats_v5b['faith_mean']:.3f} (vs v5 {stats_v5['faith_mean']:.3f}, v4 {stats_v4['faith_mean']:.3f})")
    print(f"  FIDELE/10  : {stats_v5b['fidele_count']}/10 (vs v5 {stats_v5['fidele_count']}/10, v4 {stats_v4['fidele_count']}/10)")
    print(f"  Empathie   : {stats_v5b['emp_mean']:.2f} (vs v5 {stats_v5['emp_mean']:.2f}, v4 {stats_v4['emp_mean']:.2f})")
    print(f"  Format 8q  : {stats_v5b['format_new_mean_8q']:.1f}% (vs v5 {stats_v5['format_new_mean_8q']:.1f}%, v4 {stats_v4['format_new_mean_8q']:.1f}%)")
    print(f"  Format 10q : {stats_v5b['format_old_mean_10q']:.1f}% (vs v5 {stats_v5['format_old_mean_10q']:.1f}%, v4 {stats_v4['format_old_mean_10q']:.1f}%)")
    print(f"  Ignorance Q11 v5b : {stats_v5b['piege_class']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
