"""Step 10 — Validation live A/B router_llm on/off sur 15 questions cassantes.

Lance les 15 questions sélectionnées via le pipeline production complet,
en 2 modes (enable_router_llm=True puis False), et compare :
- Latence p50/p95
- Confidence moyenne du router (mode True)
- Sub-index choisi par question (mode True)
- Refusal rate sur adversarial/cross-domain/superlatifs
- Routing correctness vs `expected_routing` du golden_60.json v3

Output :
- results/router_validation_step10/responses.jsonl  (1 ligne / question / mode)
- results/router_validation_step10/summary.md      (table A/B + verdict gates)

Coût estimé :
- Sans --router-only (full pipeline) : 15 q × 2 modes × ~$0.005/q = ~$0.15
- Avec --router-only (route() seul, pas generate) : 15 q × 1 mode × $0.0001 = $0.0015
  (le mode False n'a pas de route() à appeler — skip)

Usage :
    cd ~/projets/OrientIA && source .venv/bin/activate

    # Validation complète A/B (cible step 10) :
    python scripts/validate_step10_router_live.py

    # Routing seul (économie) :
    python scripts/validate_step10_router_live.py --router-only

    # Sous-ensemble :
    python scripts/validate_step10_router_live.py --question-ids L01,L02,P01

Cf docs/SESSION_HANDOFF / plan section 3 step 10.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mistralai.client import Mistral

from src.config import load_config
from src.rag.factory import make_production_pipeline
from src.rag.router_llm import SUB_INDEX_NAMES


# ────────────────────────── 15 questions sélectionnées ──────────────────────────


# Couverture des axes critiques (cf plan step 10) :
# - 5 simples typées (testent quad-subindex routing)
# - 4 live + paraphrase (testent vraie compréhension LLM)
# - 4 adversarial / cross-domain (testent refus structurés)
# - 2 formation classique (baseline path v1)
DEFAULT_QUESTION_IDS: list[str] = [
    # 5 simples typées (1 par sub-index + cas critiques)
    "G46",  # CROUS Lyon (vie_etudiante → aides_territoires + crous lock)
    "G29",  # Salaire PCS 37 (metier → statistiques + insee_salaire lock)
    "G21",  # Actuaire (metier_detail → metiers + metier lock)
    "G23",  # Métiers Occitanie 2030 (metier_prospective → metiers)
    "G36",  # Formations Guadeloupe (geographique → aides_territoires + drom)
    # 2 formation classique (baseline)
    "G02",  # BUT info Lyon (formations sans domain_lock)
    "G45",  # École commerce Lyon (formations sans superlatif)
    # 4 live / paraphrase (différentielle RouterLLM vs fallback)
    "L01",  # SUPERLATIF live "meilleure école commerce" → refusal
    "L02",  # GEO live "ingé cyber Bretagne" → BTS Rennes/BUT Brest doivent atteindre top
    "P01",  # PARAPHRASE "chambre étudiante Lyon" sans mot CROUS
    "P02",  # PARAPHRASE "jobs aime les chiffres" sans mot-clé métier
    # 4 adversarial / cross-domain (refus structurés)
    "A07",  # Henri-IV Toulouse (fausse prémisse géographique)
    "A09",  # Top 3 prépas (variant superlatif)
    "A10",  # Meilleurs avocats Paris (superlatif statistiques)
    "X01",  # Comment soigner grippe (cross-domain médical)
]


# ────────────────────────── Helpers ──────────────────────────


def _percentile(values: list[float], p: float) -> float:
    """Calcule un percentile [0,100] sans numpy (statistics.quantiles fragile sur petits N)."""
    if not values:
        return 0.0
    sorted_v = sorted(values)
    k = (len(sorted_v) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_v) - 1)
    if f == c:
        return sorted_v[f]
    return sorted_v[f] + (sorted_v[c] - sorted_v[f]) * (k - f)


def _serialize_route_decision(rd) -> dict:
    """Convertit RouteDecision en dict JSON-serializable (sans la fonction)."""
    if rd is None:
        return None
    return {
        "sub_indexes": list(rd.sub_indexes),
        "criteria": (
            None if rd.criteria is None
            else {
                "region": rd.criteria.region,
                "niveau_min": rd.criteria.niveau_min,
                "niveau_max": rd.criteria.niveau_max,
                "secteur": rd.criteria.secteur,
                "domain": rd.criteria.domain,
            }
        ),
        "domain_lock": rd.domain_lock,
        "refusal_reason": rd.refusal_reason,
        "hardlock_region_strict": rd.hardlock_region_strict,
        "hardlock_domain_strict": rd.hardlock_domain_strict,
        "top_k_override": rd.top_k_override,
        "confidence": rd.confidence,
        "is_fallback": rd.is_fallback,
    }


def _summarize_top_sources(top_sources: list[dict], n: int = 5) -> list[dict]:
    """Top-N résumé compact pour debug/audit."""
    summary = []
    for src in top_sources[:n]:
        fiche = src.get("fiche") if "fiche" in src else src
        summary.append({
            "domain": (fiche or {}).get("domain"),
            "nom": ((fiche or {}).get("nom") or (fiche or {}).get("libelle_metier") or "")[:80],
            "region": (fiche or {}).get("region"),
            "score": round(float(src.get("score", 0.0)), 4),
        })
    return summary


# ────────────────────────── Run ──────────────────────────


def run_one_question(
    pipeline,
    question: dict,
    enable_router: bool,
    router_only: bool,
) -> dict:
    """Exécute UNE question via le pipeline (ou juste route si router_only).

    Returns un dict structuré avec routing + answer + sources + latence.
    """
    qid = question["id"]
    q_text = question["question"]
    expected = {
        "domain": question.get("expected_domain"),
        "source": question.get("expected_source"),
        "refusal": bool(question.get("expected_refusal")),
        "routing": question.get("expected_routing"),
        "confidence_min": question.get("expected_routing_confidence_min", 0.5),
        "category": question["category"],
    }

    record: dict = {
        "id": qid,
        "category": question["category"],
        "question": q_text,
        "expected": expected,
        "enable_router_llm": enable_router,
        "router_only": router_only,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Path router-only : évite l'appel generate() coûteux
    if router_only:
        if not enable_router or pipeline.router_llm is None:
            record["error"] = "router_only=True nécessite enable_router_llm=True"
            return record
        t0 = time.time()
        try:
            decision = pipeline.router_llm.route(q_text)
            record["latency_route_s"] = round(time.time() - t0, 3)
            record["route_decision"] = _serialize_route_decision(decision)
        except Exception as e:
            record["error"] = f"route() exception: {e}"
        return record

    # Path full pipeline (route + retrieve + generate + validator + post_process)
    t0 = time.time()
    try:
        answer, top_sources = pipeline.answer(q_text)
    except Exception as e:
        record["error"] = f"pipeline.answer() exception: {e}"
        return record
    latency = time.time() - t0

    record["latency_total_s"] = round(latency, 3)
    record["answer_excerpt"] = (answer or "")[:300]
    record["answer_n_chars"] = len(answer or "")
    record["top_sources_n"] = len(top_sources)
    record["top_5_summary"] = _summarize_top_sources(top_sources, n=5)
    record["route_decision"] = _serialize_route_decision(getattr(pipeline, "last_router_result", None))
    record["filter_stats"] = getattr(pipeline, "last_filter_stats", None)
    record["scope_label"] = getattr(getattr(pipeline, "last_scope_result", None), "label", None)
    return record


def evaluate_record(record: dict) -> dict:
    """Compute pass/fail flags pour un record (cf gates step 10)."""
    eval_result = {}
    expected = record["expected"]

    # 1. Routing correctness (router on uniquement)
    if record["enable_router_llm"] and record.get("route_decision"):
        rd = record["route_decision"]
        # Confidence atteint le seuil min
        eval_result["confidence_ok"] = rd["confidence"] >= expected["confidence_min"]
        # Sub-index attendu présent dans la décision
        if expected["routing"]:
            expected_subs = set(expected["routing"]["sub_indexes"])
            actual_subs = set(rd["sub_indexes"])
            eval_result["routing_match"] = bool(expected_subs & actual_subs)
        else:
            eval_result["routing_match"] = None  # pas d'attente définie
        # Refusal cohérent
        if expected["refusal"]:
            eval_result["refusal_handled"] = rd["refusal_reason"] is not None
        else:
            eval_result["refusal_handled"] = rd["refusal_reason"] is None
    else:
        eval_result["confidence_ok"] = None
        eval_result["routing_match"] = None
        eval_result["refusal_handled"] = None

    return eval_result


def run_mode(
    cfg,
    fiches: list[dict],
    questions: list[dict],
    index_path: Path,
    enable_router: bool,
    router_only: bool,
) -> list[dict]:
    """Lance le pipeline pour TOUTES les questions dans un mode (router on/off)."""
    print(f"\n{'=' * 78}")
    print(f"MODE : enable_router_llm={enable_router}, router_only={router_only}")
    print(f"{'=' * 78}")
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=120000)
    pipeline = make_production_pipeline(
        client, fiches,
        enable_router_llm=enable_router,
    )
    pipeline.load_index_from(str(index_path))

    records: list[dict] = []
    for i, q in enumerate(questions, start=1):
        print(f"  [{i}/{len(questions)}] {q['id']} ({q['category']}): {q['question'][:60]}...")
        rec = run_one_question(pipeline, q, enable_router, router_only)
        rec["evaluation"] = evaluate_record(rec)
        if "error" in rec:
            print(f"    ERROR: {rec['error']}")
        else:
            ev = rec["evaluation"]
            lat_key = "latency_route_s" if router_only else "latency_total_s"
            lat = rec.get(lat_key, 0)
            rd = rec.get("route_decision") or {}
            conf = rd.get("confidence") if rd else None
            sub = rd.get("sub_indexes") if rd else None
            ref = rd.get("refusal_reason") if rd else None
            print(
                f"    lat={lat}s conf={conf} sub={sub} refusal={ref} "
                f"routing_match={ev.get('routing_match')} "
                f"refusal_handled={ev.get('refusal_handled')}"
            )
        records.append(rec)
    return records


# ────────────────────────── Summary ──────────────────────────


def write_summary_md(
    records_on: list[dict],
    records_off: list[dict],
    out_path: Path,
    router_only: bool,
) -> None:
    """Produit un résumé Markdown A/B + gates pass/fail."""
    lines: list[str] = []
    lines.append("# Step 10 — Validation live A/B router_llm")
    lines.append(f"\n_Run: {datetime.now(timezone.utc).isoformat()}_")
    lines.append(f"_Mode: {'router-only (cheap)' if router_only else 'full pipeline'}_")
    lines.append(f"_Questions: {len(records_on)}_\n")

    # ── A/B latency ──
    lines.append("## A/B latency")
    lines.append("| Mode | n_ok | p50 (s) | p95 (s) | mean (s) |")
    lines.append("|---|---:|---:|---:|---:|")
    for label, recs in (("router=ON", records_on), ("router=OFF", records_off)):
        if not recs:
            lines.append(f"| {label} | 0 | — | — | — |")
            continue
        lat_key = "latency_route_s" if router_only else "latency_total_s"
        lats = [r[lat_key] for r in recs if lat_key in r and "error" not in r]
        if not lats:
            lines.append(f"| {label} | 0 | — | — | — |")
            continue
        lines.append(
            f"| {label} | {len(lats)} | {_percentile(lats, 50):.2f} | "
            f"{_percentile(lats, 95):.2f} | {statistics.mean(lats):.2f} |"
        )

    # ── Routing correctness (router=ON) ──
    if records_on:
        lines.append("\n## Routing correctness (mode router=ON)")
        confs = []
        n_routing_match = 0
        n_routing_evaluable = 0
        n_refusal_handled = 0
        n_refusal_evaluable = 0
        for r in records_on:
            if "error" in r:
                continue
            ev = r.get("evaluation", {})
            rd = r.get("route_decision") or {}
            if rd.get("confidence") is not None:
                confs.append(rd["confidence"])
            if ev.get("routing_match") is not None:
                n_routing_evaluable += 1
                if ev["routing_match"]:
                    n_routing_match += 1
            if ev.get("refusal_handled") is not None:
                n_refusal_evaluable += 1
                if ev["refusal_handled"]:
                    n_refusal_handled += 1
        lines.append(
            f"- Confidence moyenne : "
            f"**{statistics.mean(confs):.2f}** sur {len(confs)} questions "
            f"(gate plan ≥ 0.7)"
        )
        if n_routing_evaluable:
            lines.append(
                f"- Routing match (sub_index attendu présent) : "
                f"**{n_routing_match}/{n_routing_evaluable}** "
                f"({100 * n_routing_match / n_routing_evaluable:.0f} %)"
            )
        if n_refusal_evaluable:
            lines.append(
                f"- Refusal handled correctly : "
                f"**{n_refusal_handled}/{n_refusal_evaluable}** "
                f"({100 * n_refusal_handled / n_refusal_evaluable:.0f} %)"
            )

    # ── Sub-index distribution (router=ON) ──
    if records_on:
        lines.append("\n## Sub-index choisi par question (mode router=ON)")
        lines.append("| ID | category | question | sub_indexes | conf | refusal | match |")
        lines.append("|---|---|---|---|---:|---|:-:|")
        for r in records_on:
            if "error" in r:
                lines.append(f"| {r['id']} | {r['category']} | ERROR | — | — | — | ❌ |")
                continue
            rd = r.get("route_decision") or {}
            ev = r.get("evaluation", {})
            sub = rd.get("sub_indexes") or []
            sub_str = ",".join(sub) if sub else "—"
            ref = rd.get("refusal_reason") or "—"
            conf = rd.get("confidence")
            match = ev.get("routing_match")
            match_str = "✓" if match is True else ("✗" if match is False else "—")
            q_short = r["question"][:55].replace("|", "\\|")
            lines.append(
                f"| {r['id']} | {r['category']} | {q_short}... | {sub_str} | "
                f"{conf if conf is not None else '—'} | {ref} | {match_str} |"
            )

    # ── Verdict gate step 10 ──
    lines.append("\n## Verdict gate step 10")
    if not records_on:
        lines.append("\nMode router=OFF only — pas de gate à valider.\n")
    else:
        confs = [r["route_decision"]["confidence"] for r in records_on
                 if r.get("route_decision") and "error" not in r]
        avg_conf = statistics.mean(confs) if confs else 0
        lats_on = [r.get("latency_route_s" if router_only else "latency_total_s", 0)
                   for r in records_on if "error" not in r]
        p95_lat = _percentile(lats_on, 95) if lats_on else 0
        gate_p95_s = 1.0 if router_only else 12.0

        gate_conf = avg_conf >= 0.7
        gate_lat = p95_lat <= gate_p95_s
        gate_routing = (n_routing_match / n_routing_evaluable >= 0.85) if n_routing_evaluable else True
        gate_refusal = (n_refusal_handled / n_refusal_evaluable >= 0.85) if n_refusal_evaluable else True
        all_pass = gate_conf and gate_lat and gate_routing and gate_refusal

        lines.append(f"\n- Confidence ≥ 0.70 : {'✓' if gate_conf else '✗'} ({avg_conf:.2f})")
        lines.append(f"- Latency p95 ≤ {gate_p95_s}s : {'✓' if gate_lat else '✗'} ({p95_lat:.2f}s)")
        if n_routing_evaluable:
            lines.append(
                f"- Routing match ≥ 85 % : {'✓' if gate_routing else '✗'} "
                f"({n_routing_match}/{n_routing_evaluable})"
            )
        if n_refusal_evaluable:
            lines.append(
                f"- Refusal handled ≥ 85 % : {'✓' if gate_refusal else '✗'} "
                f"({n_refusal_handled}/{n_refusal_evaluable})"
            )
        lines.append(f"\n**{'GATE STEP 10 PASS ✅' if all_pass else 'GATE STEP 10 FAIL ❌'}**")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n📄 Summary écrit : {out_path}")


# ────────────────────────── CLI ──────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--question-ids",
        type=str,
        default=None,
        help="Liste comma-separated d'IDs (ex 'L01,L02,P01'). Default = 15 sélectionnés.",
    )
    parser.add_argument(
        "--router-only",
        action="store_true",
        help="N'exécute que RouterLLM.route() (pas le pipeline complet). "
             "Coût $0.0015. Mode OFF non disponible (rien à comparer).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=PROJECT_ROOT / "results" / "router_validation_step10",
    )
    parser.add_argument(
        "--corpus-path",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "formations_v7.json",
    )
    parser.add_argument(
        "--index-path",
        type=Path,
        default=PROJECT_ROOT / "data" / "embeddings" / "formations.index",
    )
    parser.add_argument(
        "--golden-path",
        type=Path,
        default=PROJECT_ROOT / "data" / "golden_eval" / "golden_60.json",
    )
    args = parser.parse_args()

    cfg = load_config()
    if not cfg.mistral_api_key:
        print("ERREUR : MISTRAL_API_KEY absent du .env", file=sys.stderr)
        return 1
    for p in (args.corpus_path, args.index_path, args.golden_path):
        if not p.exists():
            print(f"ERREUR : fichier manquant {p}", file=sys.stderr)
            return 1

    args.out_dir.mkdir(parents=True, exist_ok=True)

    # Load golden
    golden = json.loads(args.golden_path.read_text(encoding="utf-8"))
    all_questions: list[dict] = golden["questions"]
    if args.question_ids:
        wanted_ids = {x.strip() for x in args.question_ids.split(",") if x.strip()}
    else:
        wanted_ids = set(DEFAULT_QUESTION_IDS)
    questions = [q for q in all_questions if q["id"] in wanted_ids]
    if not questions:
        print(f"ERREUR : aucune question trouvée parmi {wanted_ids}", file=sys.stderr)
        return 1
    print(f"Questions sélectionnées : {len(questions)} / {len(all_questions)}")

    # Load corpus
    fiches = json.loads(args.corpus_path.read_text(encoding="utf-8"))
    print(f"Corpus chargé : {len(fiches)} fiches")

    # Run mode router=ON (toujours)
    records_on = run_mode(cfg, fiches, questions, args.index_path,
                          enable_router=True, router_only=args.router_only)

    # Run mode router=OFF (sauf si router_only)
    records_off: list[dict] = []
    if not args.router_only:
        records_off = run_mode(cfg, fiches, questions, args.index_path,
                               enable_router=False, router_only=False)

    # Write JSONL
    jsonl_path = args.out_dir / "responses.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as f:
        for r in records_on:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        for r in records_off:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n📄 JSONL écrit : {jsonl_path}")

    # Write summary
    summary_path = args.out_dir / "summary.md"
    write_summary_md(records_on, records_off, summary_path, args.router_only)
    return 0


if __name__ == "__main__":
    sys.exit(main())
