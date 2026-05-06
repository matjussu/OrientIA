"""Mini-bench reproductible — fil rouge plan refonte produit niveau 2.

Charge tests/mini_bench/questions_20.json (18 unimodal + 2 threads multi-tour),
instancie le pipeline OrientIA selon la phase courante, génère les réponses,
valide chaque réponse standalone pour métriques honesty/flagged, sauvegarde
en JSON pour comparaison cross-phase.

Phase 0 baseline : pipeline tel que dans run_real_full.py
  (use_mmr=True, use_intent=True, validator=None, use_golden_qa=False).
  Multi-tour SKIPPED (single-shot pipeline ne le supporte pas — Phase 4.1
  l'activera via ConversationalSystem).

Usage :
    python scripts/mini_bench.py --out results/mini_bench/baseline_phase0.json
    python scripts/mini_bench.py --phase phase2 --out results/mini_bench/phase2.json
    python scripts/mini_bench.py --sample 3   # smoke test 3 questions
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

# Permet d'exécuter le script directement (python scripts/mini_bench.py)
# sans avoir à set PYTHONPATH ni faire python -m scripts.mini_bench.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mistralai.client import Mistral  # noqa: E402

from src.config import load_config  # noqa: E402
from src.rag.pipeline import OrientIAPipeline  # noqa: E402
from src.rag.factory import make_production_pipeline, golden_qa_artifacts_present  # noqa: E402
from src.validator import Validator  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUESTIONS = REPO_ROOT / "tests" / "mini_bench" / "questions_20.json"
DEFAULT_OUT = REPO_ROOT / "results" / "mini_bench" / "baseline_phase0.json"
FICHES_PATH = REPO_ROOT / "data" / "processed" / "formations.json"
INDEX_PATH = REPO_ROOT / "data" / "embeddings" / "formations.index"


def make_baseline_pipeline(client: Mistral, fiches: list[dict]) -> OrientIAPipeline:
    """Phase 0 baseline — strictement le pipeline de run_real_full.py.
    Aucun validator, golden_qa, post_process, layer3."""
    pipeline = OrientIAPipeline(
        client, fiches,
        use_mmr=True,
        use_intent=True,
    )
    _load_index_or_fail(pipeline)
    return pipeline


def make_phase2_pipeline(client: Mistral, fiches: list[dict]) -> OrientIAPipeline:
    """Phase 2 production — pipeline via factory canonique avec validator
    + golden_qa + post_process actifs (layer3 OFF par défaut, coût)."""
    if not golden_qa_artifacts_present():
        print(
            "[mini_bench] WARNING: Golden QA artifacts absents — few-shot "
            "désactivé pour ce run (fallback gracieux)."
        )
    pipeline = make_production_pipeline(
        client, fiches,
        enable_validator=True,
        enable_layer3=False,  # off pour mesure cost/latency contrôlée
        enable_golden_qa=True,
        enable_post_process=True,
        enable_strict_v4=False,  # explicit : v4 OFF en production (default)
    )
    _load_index_or_fail(pipeline)
    return pipeline


def make_strict_v4_pipeline(client: Mistral, fiches: list[dict]) -> OrientIAPipeline:
    """Étape 2 refonte — pipeline strict v4 (FactCard JSON + SYSTEM_PROMPT_V4_STRICT).

    Mêmes garde-fous que production (validator, post_process, scope) MAIS le
    generator utilise le contrat WHAT/HOW : prose libre des fiches REMPLACÉE
    par tableau JSON tabulaire `<sources>` typé via FactCard. Le LLM ne peut
    citer que ce qui est explicitement dans le tableau."""
    if not golden_qa_artifacts_present():
        print(
            "[mini_bench] WARNING: Golden QA artifacts absents — few-shot "
            "désactivé pour ce run (fallback gracieux)."
        )
    pipeline = make_production_pipeline(
        client, fiches,
        enable_validator=True,
        enable_layer3=False,
        enable_golden_qa=True,
        enable_post_process=True,
        enable_strict_v4=True,  # ← bascule sur le contrat v4
    )
    _load_index_or_fail(pipeline)
    return pipeline


def make_strict_v4_large_pipeline(client: Mistral, fiches: list[dict]) -> OrientIAPipeline:
    """Étape 2 itération — strict v4 + Mistral Large pour la génération.

    Hypothèse : Mistral Large suit plus strictement le contrat v4 (less
    extrapolation hors-source) ET génère des réponses plus concises (limite
    la verbosité +82% mesurée en v4-medium). Trade-off coût ~10× par token.
    """
    if not golden_qa_artifacts_present():
        print(
            "[mini_bench] WARNING: Golden QA artifacts absents — few-shot "
            "désactivé pour ce run (fallback gracieux)."
        )
    pipeline = make_production_pipeline(
        client, fiches,
        enable_validator=True,
        enable_layer3=False,
        enable_golden_qa=True,
        enable_post_process=True,
        enable_strict_v4=True,
        model="mistral-large-latest",  # ← upgrade modèle
    )
    _load_index_or_fail(pipeline)
    return pipeline


def _load_index_or_fail(pipeline: OrientIAPipeline) -> None:
    """Charge l'index FAISS depuis INDEX_PATH ou raise (build coûteux refusé)."""
    if INDEX_PATH.exists():
        pipeline.load_index_from(str(INDEX_PATH))
    else:
        raise FileNotFoundError(
            f"FAISS index manquant : {INDEX_PATH}. Lance d'abord la pipeline "
            "officielle pour le construire (cf README ou run_real_full.py)."
        )


def make_validator(fiches: list[dict]) -> Validator:
    """Validator standalone (rules + corpus_check + presence, sans layer3 LLM).

    Utilisé pour MESURER honesty_score sur les réponses du baseline pipeline
    (qui lui ne fait pas tourner le validator). Layer3 OFF pour économiser
    ~$0.001/q + 2-4s latency."""
    return Validator(fiches=fiches, layer3=None)


def run_question(
    pipeline: OrientIAPipeline,
    validator: Validator,
    q: dict,
    store_sources: bool = False,
) -> dict:
    """Génère + mesure une question unimodale. Retourne le record JSON-able.

    Args:
        store_sources: si True, sérialise top_sources retrievées dans le record
            (pour audit data Phase A — type A/B/C hallu vs corpus). Bloate le
            JSON (~30-50 KB / question), donc opt-in.
    """
    qid = q["id"]
    text = q["text"]

    record: dict = {
        "id": qid,
        "category": q.get("category"),
        "split": q.get("split"),
        "intent_target": q.get("intent_target"),
        "chemin_target": q.get("chemin_target"),
        "scope_target": q.get("scope_target"),
        "question": text,
        "response": None,
        "latency_s": None,
        "response_length_chars": None,
        "response_length_words": None,
        "scope_label": None,
        "scope_via": None,
        "scope_reason": None,
        "select_via": None,
        "select_reason": None,
        "n_sources_top": None,
        "top_sources": None,
        "golden_qa_active": None,
        "golden_qa_matched": None,
        "post_process_applied": None,
        "post_process_n_slugs_corrected": None,
        "post_process_chars_removed": None,
        "honesty_score": None,
        "flagged": None,
        "n_failed_claims": None,
        "retry_metadata": None,
        "error": None,
    }

    t0 = time.time()
    try:
        response, top_sources = pipeline.answer(text)
        record["latency_s"] = round(time.time() - t0, 2)
        record["response"] = response
        record["response_length_chars"] = len(response)
        record["response_length_words"] = len(response.split())
        record["n_sources_top"] = len(top_sources)
        if store_sources:
            # Sérialise un excerpt par source (texte clé, score, id stable) pour
            # audit data — type A/B/C hallu (info dans corpus vs absente).
            record["top_sources"] = []
            for s in top_sources:
                fiche = s.get("fiche") if "fiche" in s else s
                if not isinstance(fiche, dict):
                    continue
                # Construire un texte représentatif de la fiche (nom + détails)
                parts = []
                for key in ("nom", "etablissement", "ville", "niveau", "phase", "domain"):
                    v = fiche.get(key)
                    if v:
                        parts.append(f"{key}={v}")
                # Stats clés si présentes
                for stat_key in ("taux_acces_parcoursup_2025", "nombre_places", "duree", "frais_annuels"):
                    v = fiche.get(stat_key)
                    if v is not None:
                        parts.append(f"{stat_key}={v}")
                # Insertion pro
                ip = fiche.get("insertion_pro")
                if isinstance(ip, dict):
                    for ik, iv in list(ip.items())[:5]:
                        if iv is not None:
                            parts.append(f"insertion.{ik}={iv}")
                # Texte libre (cells multi-corpus) ou détail (formations)
                free_text = fiche.get("text") or fiche.get("detail") or ""
                if free_text:
                    parts.append(f"text={free_text[:400]}")
                record["top_sources"].append({
                    "id": str(fiche.get("id") or fiche.get("numero_fiche") or fiche.get("nom", "?"))[:80],
                    "score": float(s.get("score", 0)) if isinstance(s, dict) else 0.0,
                    "summary": " | ".join(parts)[:1200],
                })
        # Marqueurs pipeline
        # Étape 1 refonte : scope_result (None si scope_classifier non câblé)
        sr = pipeline.last_scope_result
        if sr is not None:
            record["scope_label"] = sr.label
            record["scope_via"] = sr.via
            record["scope_reason"] = sr.reason
        sel = pipeline.last_select_result
        if sel is not None:
            record["select_via"] = sel.via_select
            record["select_reason"] = sel.reason
        else:
            record["select_via"] = False
        gqa = pipeline.last_golden_qa
        if gqa is not None:
            record["golden_qa_active"] = gqa.get("active")
            record["golden_qa_matched"] = gqa.get("matched")
        else:
            record["golden_qa_active"] = False
            record["golden_qa_matched"] = False
        # Phase 2 : post-process stats (None si feature désactivée)
        pp = pipeline.last_post_process_stats
        if pp is not None:
            record["post_process_applied"] = pp.get("applied")
            record["post_process_n_slugs_corrected"] = pp.get("n_onisep_slugs_corrected")
            record["post_process_chars_removed"] = pp.get("chars_removed")
        else:
            record["post_process_applied"] = False
        record["retry_metadata"] = pipeline.last_retry_metadata
        # Validation standalone (pour métrique honesty même quand pipeline n'a pas de validator)
        vr = validator.validate(response)
        record["honesty_score"] = round(vr.honesty_score, 3)
        record["flagged"] = vr.flagged
        record["n_failed_claims"] = (
            len(vr.rule_violations) + len(vr.corpus_warnings) + len(vr.presence_warnings)
        )
    except Exception as e:
        record["latency_s"] = round(time.time() - t0, 2)
        record["error"] = f"{type(e).__name__}: {e}"
        record["error_traceback"] = traceback.format_exc()

    return record


def run_multi_turn_thread(
    pipeline: OrientIAPipeline,  # noqa: ARG001 (placeholder pour Phase 4.1+)
    validator: Validator,         # noqa: ARG001
    thread: dict,
) -> list[dict]:
    """Phase 0 baseline : multi-tour SKIPPED (pipeline single-shot).

    Renvoie 1 record par tour avec error="skipped: multi-turn requires
    ConversationalSystem (Phase 4.1)". Permet de garder la structure
    de sortie homogène cross-phase pour comparaison.
    """
    out = []
    for turn in thread["turns"]:
        out.append({
            "id": turn["id"],
            "thread_id": thread["thread_id"],
            "tour": turn["tour"],
            "intent_target": turn.get("intent_target"),
            "chemin_target": turn.get("chemin_target"),
            "question": turn["text"],
            "expects_reco_mode": turn.get("expects_reco_mode", False),
            "error": "skipped: multi-turn requires ConversationalSystem (Phase 4.1)",
        })
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--questions",
        type=Path,
        default=DEFAULT_QUESTIONS,
        help=f"Path to questions JSON (default: {DEFAULT_QUESTIONS})",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output JSON path (default: {DEFAULT_OUT})",
    )
    parser.add_argument(
        "--phase",
        type=str,
        default="phase0_baseline",
        help="Phase tag stored in metadata (default: phase0_baseline)",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=0,
        help="If >0, only process the first N unimodal questions (smoke test)",
    )
    parser.add_argument(
        "--include-multi-turn",
        action="store_true",
        help="Include multi-turn threads (Phase 4.1+ only — Phase 0 baseline skips them)",
    )
    parser.add_argument(
        "--config",
        type=str,
        choices=["baseline", "production", "strict_v4", "strict_v4_large"],
        default="baseline",
        help="baseline = pipeline run_real_full (use_mmr+use_intent only). "
             "production = via factory (validator + golden_qa + post_process). "
             "strict_v4 = production + contrat strict v4 (FactCard JSON sources). "
             "strict_v4_large = strict_v4 + Mistral Large pour génération. "
             "Default: baseline (Phase 0 reproductible).",
    )
    parser.add_argument(
        "--store-sources",
        action="store_true",
        help="Sérialise top_sources retrievées dans le JSON (pour audit data "
             "Phase A : type A/B/C hallu vs corpus). Bloate le JSON.",
    )
    args = parser.parse_args()

    print(f"[mini_bench] phase={args.phase}")
    print(f"[mini_bench] questions={args.questions}")
    print(f"[mini_bench] out={args.out}")

    # Setup
    cfg = load_config()
    if not cfg.mistral_api_key:
        raise RuntimeError("MISTRAL_API_KEY missing — required for embedding + generation.")
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=120000)
    fiches = json.loads(FICHES_PATH.read_text(encoding="utf-8"))
    print(f"[mini_bench] loaded {len(fiches)} fiches")

    if args.config == "strict_v4_large":
        pipeline = make_strict_v4_large_pipeline(client, fiches)
    elif args.config == "strict_v4":
        pipeline = make_strict_v4_pipeline(client, fiches)
    elif args.config == "production":
        pipeline = make_phase2_pipeline(client, fiches)
    else:
        pipeline = make_baseline_pipeline(client, fiches)
    validator = make_validator(fiches)
    print(
        f"[mini_bench] pipeline ready (config={args.config}, "
        f"use_mmr={pipeline.use_mmr}, use_intent={pipeline.use_intent}, "
        f"validator={pipeline.validator is not None}, "
        f"use_golden_qa={pipeline.use_golden_qa}, "
        f"enable_post_process={pipeline.enable_post_process}, "
        f"use_strict_v4={pipeline.use_strict_v4})"
    )

    # Load questions
    qdata = json.loads(args.questions.read_text(encoding="utf-8"))
    unimodal = qdata.get("questions_unimodal", [])
    multi_turn = qdata.get("questions_multi_turn", [])
    if args.sample > 0:
        unimodal = unimodal[: args.sample]
        print(f"[mini_bench] SAMPLE MODE — first {args.sample} unimodal questions only")

    print(f"[mini_bench] processing {len(unimodal)} unimodal + "
          f"{sum(len(t['turns']) for t in multi_turn) if args.include_multi_turn else 0} multi-turn")

    # Run unimodal
    unimodal_results = []
    for i, q in enumerate(unimodal, 1):
        print(f"  [{i}/{len(unimodal)}] {q['id']}: {q['text'][:60]}...")
        rec = run_question(pipeline, validator, q, store_sources=args.store_sources)
        unimodal_results.append(rec)
        if rec.get("error"):
            print(f"    ✗ {rec['error']}")
        else:
            print(f"    ✓ {rec['latency_s']}s, {rec['response_length_words']}w, "
                  f"honesty={rec['honesty_score']}, flagged={rec['flagged']}, "
                  f"select_via={rec['select_via']}")

    # Run multi-turn (skipped Phase 0)
    multi_turn_results = []
    if args.include_multi_turn:
        for thread in multi_turn:
            multi_turn_results.extend(run_multi_turn_thread(pipeline, validator, thread))
    else:
        # Marker que les multi-turn ont été délibérément skippés (cohérence cross-phase)
        for thread in multi_turn:
            for turn in thread["turns"]:
                multi_turn_results.append({
                    "id": turn["id"],
                    "thread_id": thread["thread_id"],
                    "tour": turn["tour"],
                    "skipped_reason": "phase0_no_multi_turn_support",
                })

    # Aggregate metadata
    n_errors = sum(1 for r in unimodal_results if r.get("error"))
    n_select_via = sum(1 for r in unimodal_results if r.get("select_via") is True)
    n_flagged = sum(1 for r in unimodal_results if r.get("flagged") is True)
    avg_honesty = (
        round(
            sum(r["honesty_score"] for r in unimodal_results if r.get("honesty_score") is not None)
            / max(1, sum(1 for r in unimodal_results if r.get("honesty_score") is not None)),
            3,
        )
        if unimodal_results else None
    )
    avg_latency = (
        round(
            sum(r["latency_s"] for r in unimodal_results if r.get("latency_s") is not None)
            / max(1, sum(1 for r in unimodal_results if r.get("latency_s") is not None)),
            2,
        )
        if unimodal_results else None
    )

    out_payload = {
        "metadata": {
            "phase": args.phase,
            "config": args.config,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "questions_path": str(args.questions),
            "pipeline_config": {
                "use_mmr": pipeline.use_mmr,
                "use_intent": pipeline.use_intent,
                "use_metadata_filter": pipeline.use_metadata_filter,
                "use_golden_qa": pipeline.use_golden_qa,
                "validator_attached_to_pipeline": pipeline.validator is not None,
                "enable_post_process": pipeline.enable_post_process,
                "use_strict_v4": pipeline.use_strict_v4,
                "model": pipeline.model,
            },
            "n_unimodal_processed": len(unimodal_results),
            "n_unimodal_errors": n_errors,
            "n_select_via": n_select_via,
            "n_flagged": n_flagged,
            "avg_honesty_score": avg_honesty,
            "avg_latency_s": avg_latency,
            "include_multi_turn": args.include_multi_turn,
            "n_multi_turn_records": len(multi_turn_results),
        },
        "unimodal_results": unimodal_results,
        "multi_turn_results": multi_turn_results,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[mini_bench] Saved to {args.out}")
    print(f"[mini_bench] Summary: {n_errors} errors, {n_select_via} SELECT bypass, "
          f"{n_flagged} flagged, avg_honesty={avg_honesty}, avg_latency={avg_latency}s")


if __name__ == "__main__":
    main()
