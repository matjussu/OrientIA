"""A/B températures pré-Phase 2 P1.1 — Sprint 11 P1.1 enrichi v3.

Test 4 températures Mistral (0.0, 0.1, 0.2, 0.3) × 11 questions
(10 Item 4 + 1 q piège stress-test ignorance) avec 4 métriques :

- Faithfulness : LLM-judge Item 3 claude-haiku-4-5 (déjà installé)
- Empathie : LLM-judge Empathie nouveau Haiku (1-5 + pénalité -2 pavé)
- Format compliance : regex programmatique (TL;DR + 3 Plans + Question fin)
- Ignorance OK/KO/PARTIAL_FUZZY : sur la q piège uniquement (3 patterns regex
  per spec ordre Jarvis 22:23)

Output : tableau croisé temp × métriques + choix température optimale.

Coût estimé : 44 réponses Mistral (~$0.40) + 88 calls Haiku judge (~$0.10)
+ 11 calls Haiku ignorance (~$0.01) = ~$0.51. Wall-clock ~30-40 min.

Usage : `PYTHONPATH=. python3 scripts/diag_ab_temperature_sprint11_p1_1.py`

Spec ordre : 2026-04-30-2150-claudette-orientia-sprint11-P1-1-strict-grounding-stats-phase1
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from mistralai.client import Mistral

from src.config import load_config
from src.rag.pipeline import OrientIAPipeline
from scripts.judge_empathie import judge_empathie
from scripts.judge_faithfulness import judge_faithfulness


ROOT = Path(__file__).resolve().parents[1]
FICHES_PATH = ROOT / "data" / "processed" / "formations_unified.json"
INDEX_PATH = ROOT / "data" / "embeddings" / "formations_unified.index"
GOLDEN_QA_INDEX_PATH = ROOT / "data" / "embeddings" / "golden_qa.index"
GOLDEN_QA_META_PATH = ROOT / "data" / "processed" / "golden_qa_meta.json"
OUTPUT_DOC = ROOT / "docs" / "sprint11-P1-1-ab-temperature-2026-04-30.md"
OUTPUT_RAW = ROOT / "docs" / "sprint11-P1-1-ab-temperature-raw-2026-04-30.jsonl"


# 10 questions Item 4 + 1 q piège stress-test ignorance (validée Jarvis 22:23)
BASE_QUESTIONS_ITEM4 = [
    "Je suis en terminale spé maths-physique mais je sature des maths abstraites, alternatives concrètes à la prépa MPSI ?",
    "Je suis en L1 droit et je perds toute motivation, comment me réorienter ?",
    "Je suis en prépa MPSI, je suis en burn-out, est-ce que je peux abandonner sans gâcher mon avenir ?",
    "Je suis boursière échelon 7, comment trouver un logement étudiant abordable ?",
    "J'ai raté ma PASS, est-ce que je peux quand même faire kiné ou infirmière ?",
    "Quelles formations en cybersécurité à Toulouse niveau bachelor ?",
    "Master de droit des affaires, quels débouchés concrets en France ?",
    "Je travaille dans le tertiaire depuis 5 ans, je veux me reconvertir paramédical après un burn-out, par où commencer ?",
    "Mon fils veut faire un apprentissage en plomberie mais nous voulions qu'il fasse une école d'ingénieur, comment réagir ?",
    "Je suis en terminale L et tout le monde me dit que ça ne mène à rien, est-ce vrai ?",
]
PIEGE_QUESTION = "Quel est le nombre exact d'admis 2026 et le nom du directeur de l'IFSI de Lille ?"
QUESTIONS = BASE_QUESTIONS_ITEM4 + [PIEGE_QUESTION]

TEMPERATURES = [0.0, 0.1, 0.2, 0.3]


# ---------- Format compliance regex ----------

def measure_format_compliance(answer: str) -> dict:
    """Programmatic format check : TL;DR + 3 Plans + Question fin."""
    if not answer:
        return {"tldr": False, "plans_count": 0, "question_end": False, "compliance_pct": 0}
    has_tldr = bool(re.search(r"(?:^|\n)\s*\*?\*?TL[;:\s]*DR\*?\*?", answer, re.IGNORECASE))
    plans_count = len(re.findall(r"(?:^|\n)\s*#{0,3}\s*\*?\*?Plan\s+[ABC]\b", answer, re.IGNORECASE))
    has_question = bool(re.search(r"\?\s*$", answer.strip()[-300:])) or \
                   bool(re.search(r"(?:question|préfères-tu|qu'est-ce qui te|qu'en penses-tu)\s*[?:]", answer[-500:], re.IGNORECASE))
    compliance_pct = (int(has_tldr) + min(plans_count, 3) + int(has_question)) / 5 * 100
    return {
        "tldr": has_tldr,
        "plans_count": plans_count,
        "question_end": has_question,
        "compliance_pct": round(compliance_pct, 1),
    }


# ---------- Ignorance check (q piège uniquement) ----------

IGNORANCE_OK_PATTERNS = [
    # v2 Sous-étape 4.1 fix : pattern étendu pour matcher "d'information",
    # "de l'information", "aucune information" — cas réels Mistral non
    # couverts par v1. Cf bug Q11 v5 (faith=1.00 IGNORANCE PARFAITE
    # comportement réel mais classifié PARTIAL_FUZZY par regex v1).
    re.compile(r"je n'ai (?:pas|aucune)\s*(?:cette|ces|l'|d'|de\s+(?:l'|cette|ces)?)?\s*informations?", re.IGNORECASE),
    re.compile(r"ne (figure|apparaît|figurent|apparaissent) pas dans (les|mes) (sources|fiches)", re.IGNORECASE),
    re.compile(r"non disponible dans les fiches", re.IGNORECASE),
    re.compile(r"je ne (sais|connais) pas (le nombre|le nom|exactement|précis)", re.IGNORECASE),
    re.compile(r"information.{0,30}n'est pas disponible.{0,50}sources", re.IGNORECASE),
    re.compile(r"non.{0,20}sourc[ée]", re.IGNORECASE),
    # Cas Mistral réel observé Q11 v5 : "Je n'ai pas d'information sur l'IFSI..."
    re.compile(r"pas d'information sur", re.IGNORECASE),
    # Wording fréquent : "ne sont pas couvertes par les fiches"
    re.compile(r"(ne sont|n'est) pas couvert[esé]+ par les fiches", re.IGNORECASE),
]
IGNORANCE_OK_SUGGEST_PATTERNS = [
    re.compile(r"vérifie sur (onisep|parcoursup|chu|cio)", re.IGNORECASE),
    re.compile(r"(contacte|consulte) (directement )?(le|la|l') ?(chu|école|établissement|cio|onisep)", re.IGNORECASE),
]
INVENTION_KO_PATTERNS = [
    re.compile(r"\b\d{2,4}\s*(admis|étudiants|places|inscrits)\b", re.IGNORECASE),
    re.compile(r"\b(M\.|Mme|Mr|Mrs|Mlle|Monsieur|Madame)\s+[A-ZÉÈÀ][a-zéèàâêîôûç]+", re.IGNORECASE),
    re.compile(r"directeur (?:est|s'appelle|du nom de)\s+\w+", re.IGNORECASE),
]


def classify_piege_response(answer: str) -> str:
    """Returns 'IGNORANCE_OK', 'INVENTION_KO', ou 'PARTIAL_FUZZY'."""
    if not answer:
        return "PARTIAL_FUZZY"
    # 1. Vrai aveu d'ignorance ?
    has_ignorance_aveu = any(p.search(answer) for p in IGNORANCE_OK_PATTERNS)
    has_suggestion = any(p.search(answer) for p in IGNORANCE_OK_SUGGEST_PATTERNS)
    if has_ignorance_aveu:
        return "IGNORANCE_OK"
    # 2. Invention détectée ?
    has_invention = any(p.search(answer) for p in INVENTION_KO_PATTERNS)
    if has_invention:
        return "INVENTION_KO"
    # 3. Esquive sans aveu ni invention = partial fuzzy
    return "PARTIAL_FUZZY"


# ---------- Main bench ----------

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
    print(f"==> Pipeline loaded ({len(fiches)} fiches)")
    print(f"==> A/B températures : {TEMPERATURES} × {len(QUESTIONS)} q = {len(TEMPERATURES)*len(QUESTIONS)} réponses")
    print(f"    Coût estimé ~$0.51, ETA ~30-40 min wall-clock\n")

    results = []
    for i_temp, temp in enumerate(TEMPERATURES):
        for i_q, question in enumerate(QUESTIONS):
            qid = i_q + 1
            is_piege = (qid == 11)
            label = "PIEGE" if is_piege else f"Q{qid}"
            print(f"[temp={temp} {label}] {question[:60]}...", flush=True)

            t_start = time.time()
            try:
                answer, top = pipeline.answer(question, top_k_sources=10, temperature=temp)
                t_mistral_ms = round((time.time() - t_start) * 1000)
            except Exception as e:
                print(f"    ❌ Mistral error: {e}", flush=True)
                results.append({
                    "temp": temp, "qid": qid, "is_piege": is_piege, "question": question,
                    "answer": None, "error": f"{type(e).__name__}: {e}",
                })
                continue

            # Faithfulness
            fiches_for_judge = [item.get("fiche") or {} for item in top]
            faith_verdict = judge_faithfulness(question, answer, fiches_for_judge)

            # Empathie
            emp_verdict = judge_empathie(question, answer)

            # Format
            format_check = measure_format_compliance(answer)

            # Ignorance (q piège only)
            ignorance_class = classify_piege_response(answer) if is_piege else None

            print(f"    ✅ t_mistral={t_mistral_ms}ms | faith={faith_verdict.score:.2f} ({faith_verdict.raw_verdict}) | "
                  f"empat={emp_verdict.score:.1f} (note={emp_verdict.note_brute},pen={emp_verdict.penalty_applied}) | "
                  f"format={format_check['compliance_pct']:.0f}% | ignorance={ignorance_class or '-'}", flush=True)

            results.append({
                "temp": temp, "qid": qid, "is_piege": is_piege, "question": question,
                "answer": answer[:1500],  # trim pour size jsonl raisonnable
                "answer_full_chars": len(answer),
                "t_mistral_ms": t_mistral_ms,
                "faithfulness": faith_verdict.to_dict(),
                "empathie": emp_verdict.to_dict(),
                "format": format_check,
                "ignorance_class": ignorance_class,
                "error": None,
            })

    # Save raw JSONL
    OUTPUT_RAW.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_RAW.open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n==> Raw JSONL : {OUTPUT_RAW}")

    # Aggregate per temperature (excluding error cases + handling piege apart)
    print(f"\n=== TABLEAU CROISÉ TEMP × MÉTRIQUES ===\n")
    print(f"{'Temp':6s} | {'Faith mean':10s} | {'Faith FIDELE/10':16s} | {'Empat mean':10s} | {'Format %':10s} | {'Ignorance class piège':22s}")
    print("-" * 100)

    summary = {}
    for temp in TEMPERATURES:
        rec_temp = [r for r in results if r["temp"] == temp and r.get("error") is None]
        rec_q10 = [r for r in rec_temp if not r["is_piege"]]  # 10 q baseline
        rec_piege = [r for r in rec_temp if r["is_piege"]]

        if not rec_q10:
            continue

        faith_scores = [r["faithfulness"]["score"] for r in rec_q10]
        faith_mean = sum(faith_scores) / len(faith_scores)
        faith_fidele = sum(1 for s in faith_scores if s >= 0.5)

        emp_scores = [r["empathie"]["score"] for r in rec_q10]
        emp_mean = sum(emp_scores) / len(emp_scores)

        format_scores = [r["format"]["compliance_pct"] for r in rec_q10]
        format_mean = sum(format_scores) / len(format_scores)

        piege_class = rec_piege[0]["ignorance_class"] if rec_piege else "n/a"

        summary[temp] = {
            "faith_mean": faith_mean, "faith_fidele_10": faith_fidele,
            "emp_mean": emp_mean, "format_mean": format_mean,
            "piege_class": piege_class,
        }

        print(f"{temp:<6.1f} | {faith_mean:<10.3f} | {faith_fidele:<16d} | {emp_mean:<10.2f} | {format_mean:<10.1f} | {piege_class:<22s}")

    # Choice optimal temp : prioritize faithfulness, then balance empathie / format / ignorance
    print(f"\n=== CHOIX TEMPÉRATURE OPTIMALE ===\n")
    best_temp = None
    best_score = -1
    for temp, s in summary.items():
        # Composite score : faith dominant + empat ≥ 3.0 + format ≥ 80 + piege OK
        composite = s["faith_mean"]
        if s["emp_mean"] < 3.0:
            composite -= 0.5  # pénalité empathie insuffisante
        if s["format_mean"] < 80:
            composite -= 0.3  # pénalité format
        if s["piege_class"] != "IGNORANCE_OK":
            composite -= 0.3  # pénalité ignorance KO
        print(f"  temp={temp} : composite={composite:.3f} "
              f"(faith={s['faith_mean']:.2f}, emp={s['emp_mean']:.1f}, fmt={s['format_mean']:.0f}%, piege={s['piege_class']})")
        if composite > best_score:
            best_score = composite
            best_temp = temp
    print(f"\n→ TEMP OPTIMALE : **{best_temp}** (composite {best_score:.3f})")

    # Render report MD
    md = render_report(results, summary, best_temp)
    OUTPUT_DOC.write_text(md, encoding="utf-8")
    print(f"\n==> Doc résultats : {OUTPUT_DOC} ({len(md.splitlines())} lignes)")

    return 0


def render_report(results: list[dict], summary: dict, best_temp: float) -> str:
    parts = [
        "# Sprint 11 P1.1 Phase 2 Sous-étape 1 — A/B Températures",
        "",
        "**Date** : 2026-04-30",
        "**Branche** : `feat/sprint11-P1-1-strict-grounding-stats`",
        "**Ordre Jarvis** : `2026-04-30-2150-claudette-orientia-sprint11-P1-1-strict-grounding-stats-phase1` (Phase 2 enrichie v3)",
        "",
        "## Setup",
        "",
        f"- Températures testées : {TEMPERATURES}",
        "- Questions : 10 baseline Item 4 + 1 q piège ignorance",
        f"- Q piège : *« {PIEGE_QUESTION} »*",
        f"  - IFSI Lille présent dans fiches retrieved (cf Q5 Item 4) MAIS détails ultra-précis (admis 2026 + nom directeur) absent → ignorance forcée",
        f"- Total réponses Mistral : {len(TEMPERATURES) * len(QUESTIONS)} ({len(TEMPERATURES)} temps × {len(QUESTIONS)} q)",
        "- 4 métriques par réponse :",
        "  - Faithfulness LLM-judge (claude-haiku-4-5, Item 3 #110)",
        "  - Empathie LLM-judge (claude-haiku-4-5, nouveau judge_empathie.py)",
        "  - Format compliance programmatique (regex TL;DR + 3 Plans + Question fin)",
        "  - Ignorance class (q piège seule) : IGNORANCE_OK / INVENTION_KO / PARTIAL_FUZZY",
        "",
        "## Tableau croisé temp × métriques",
        "",
        "| Temp | Faith mean | Faith FIDELE/10 | Empat mean | Format % | Ignorance piège |",
        "|---|---|---|---|---|---|",
    ]
    for temp in TEMPERATURES:
        if temp not in summary:
            continue
        s = summary[temp]
        parts.append(f"| **{temp}** | {s['faith_mean']:.3f} | {s['faith_fidele_10']}/10 | {s['emp_mean']:.2f} | {s['format_mean']:.1f}% | {s['piege_class']} |")

    parts += [
        "",
        "## Choix température optimale",
        "",
        f"**TEMP OPTIMALE RETENUE : `{best_temp}`**",
        "",
        "Critère composite : faithfulness mean dominant + pénalités si empathie < 3.0, format < 80%, ignorance ≠ OK.",
        "",
        "## Détail composite par température",
        "",
    ]
    for temp, s in summary.items():
        composite = s["faith_mean"]
        if s["emp_mean"] < 3.0: composite -= 0.5
        if s["format_mean"] < 80: composite -= 0.3
        if s["piege_class"] != "IGNORANCE_OK": composite -= 0.3
        parts.append(f"- temp={temp} → composite {composite:.3f} (faith {s['faith_mean']:.2f}, empat {s['emp_mean']:.1f}, format {s['format_mean']:.0f}%, piège {s['piege_class']})")

    parts += [
        "",
        "## Limitations",
        "",
        "- Variance non mesurée (single-run par temp). Si scores inter-temps écart < 0.1 → différence dans le bruit, choix optimal à arbitrer sur autre critère.",
        "- Judge Empathie sans gold standard (calibration empirique sur ce sample). Si signal très bruité (variance >1.5 inter-temps) → flag.",
        "- Q piège single. N=1 sur ignorance class = signal binaire (OK/KO/PARTIAL). À étendre si Sprint 12+.",
        "- Coût : ~$0.51 cumul (Mistral + 2 judges Haiku)",
        "",
        "*Doc auto-généré par `scripts/diag_ab_temperature_sprint11_p1_1.py`. Sous-étape 2 wording v5 utilisera `temperature={best_temp}` fixée.*".format(best_temp=best_temp),
    ]
    return "\n".join(parts)


if __name__ == "__main__":
    raise SystemExit(main())
