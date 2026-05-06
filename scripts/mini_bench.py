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
    if INDEX_PATH.exists():
        pipeline.load_index_from(str(INDEX_PATH))
    else:
        # Fail-fast — pas de raison qu'on construise l'index ici (cher).
        raise FileNotFoundError(
            f"FAISS index manquant : {INDEX_PATH}. Lance d'abord la pipeline "
            "officielle pour le construire (cf README ou run_real_full.py)."
        )
    return pipeline


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
) -> dict:
    """Génère + mesure une question unimodale. Retourne le record JSON-able."""
    qid = q["id"]
    text = q["text"]

    record: dict = {
        "id": qid,
        "category": q.get("category"),
        "split": q.get("split"),
        "intent_target": q.get("intent_target"),
        "chemin_target": q.get("chemin_target"),
        "question": text,
        "response": None,
        "latency_s": None,
        "response_length_chars": None,
        "response_length_words": None,
        "select_via": None,
        "select_reason": None,
        "n_sources_top": None,
        "golden_qa_active": None,
        "golden_qa_matched": None,
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
        # Marqueurs pipeline
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

    pipeline = make_baseline_pipeline(client, fiches)
    validator = make_validator(fiches)
    print(f"[mini_bench] pipeline ready (use_mmr={pipeline.use_mmr}, use_intent={pipeline.use_intent})")

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
        rec = run_question(pipeline, validator, q)
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
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "questions_path": str(args.questions),
            "pipeline_config": {
                "use_mmr": pipeline.use_mmr,
                "use_intent": pipeline.use_intent,
                "use_metadata_filter": pipeline.use_metadata_filter,
                "use_golden_qa": pipeline.use_golden_qa,
                "validator_attached_to_pipeline": pipeline.validator is not None,
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
