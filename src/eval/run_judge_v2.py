"""Run judge v2 (fact-check reweight) on existing judge v1 scores.

Judge v2 is a pure post-process — it does NOT call Anthropic. It reuses
`results/scores/blind_scores.json` (v1) and post-weights the `sourcage`
criterion by `fact_check_score` computed per-answer against the
retrieved fiches (for our_rag) and the full dataset (fallback).

Retrieved fiches per question are regenerated from scratch locally by
running the pipeline's retrieve + rerank stages (no chat.complete call
— cheap Mistral embedding only). This avoids the need to have saved
them during the initial benchmark run.

Usage:
    python -m src.eval.run_judge_v2

Outputs:
    results/scores/blind_scores_v2.json
    results/raw_responses/retrieved_by_qid.json
"""
import json
import time
from pathlib import Path

from anthropic import Anthropic
from mistralai.client import Mistral

from src.config import load_config
from src.eval.judge_v2 import apply_fact_check_to_blind
from src.eval.fact_check_claude import claude_fact_check_score
from src.rag.pipeline import OrientIAPipeline
from src.rag.retriever import retrieve_top_k
from src.rag.reranker import rerank


FICHES_PATH = "data/processed/formations.json"
INDEX_PATH = "data/embeddings/formations.index"
QUESTIONS_PATH = "src/eval/questions.json"
BLIND_V1_PATH = "results/scores/blind_scores.json"
RESPONSES_PATH = "results/raw_responses/responses_blind.json"
MAPPING_PATH = "results/raw_responses/label_mapping.json"
RETRIEVED_OUT_PATH = "results/raw_responses/retrieved_by_qid.json"
V2_OUT_PATH = "results/scores/blind_scores_v2.json"


def _regenerate_retrieved(
    client: Mistral,
    fiches: list[dict],
    questions: list[dict],
    index_path: str,
) -> dict:
    """Recompute retrieved fiches per question via the current pipeline.

    This reruns retrieve_top_k + rerank (no LLM generation) for each of
    the 32 questions and saves a {qid: [fiches...]} dict. Used as ground
    truth for the our_rag fact-check.
    """
    pipeline = OrientIAPipeline(client, fiches)
    pipeline.load_index_from(index_path)
    out: dict[str, list[dict]] = {}
    for q in questions:
        print(f"  [{q['id']}] regenerating retrieved for: {q['text'][:55]}...")
        retrieved = retrieve_top_k(
            client, pipeline.index, pipeline.fiches, q["text"], k=30
        )
        reranked = rerank(retrieved, pipeline.rerank_config)
        top = reranked[:10]
        # Strip to a JSON-serializable subset
        out[q["id"]] = [
            {
                "score": float(r["score"]),
                "fiche": {
                    "nom": r["fiche"].get("nom"),
                    "etablissement": r["fiche"].get("etablissement"),
                    "ville": r["fiche"].get("ville"),
                    "url_onisep": r["fiche"].get("url_onisep"),
                    "taux_acces_parcoursup_2025": r["fiche"].get(
                        "taux_acces_parcoursup_2025"
                    ),
                    "labels": r["fiche"].get("labels") or [],
                    "profil_admis": r["fiche"].get("profil_admis"),
                },
            }
            for r in top
        ]
    return out


def main() -> None:
    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=120000)

    fiches = json.loads(Path(FICHES_PATH).read_text(encoding="utf-8"))
    questions = json.loads(Path(QUESTIONS_PATH).read_text(encoding="utf-8"))["questions"]

    # 1. Regenerate retrieved_by_qid locally (or load cached)
    if Path(RETRIEVED_OUT_PATH).exists():
        print(f"Loading cached retrieved from {RETRIEVED_OUT_PATH}")
        retrieved_by_qid = json.loads(
            Path(RETRIEVED_OUT_PATH).read_text(encoding="utf-8")
        )
    else:
        print("Regenerating retrieved fiches per question...")
        retrieved_by_qid = _regenerate_retrieved(
            client, fiches, questions, INDEX_PATH
        )
        Path(RETRIEVED_OUT_PATH).parent.mkdir(parents=True, exist_ok=True)
        Path(RETRIEVED_OUT_PATH).write_text(
            json.dumps(retrieved_by_qid, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Saved to {RETRIEVED_OUT_PATH}")

    # 2. Load v1 scores, responses, label mapping
    blind_v1 = json.loads(Path(BLIND_V1_PATH).read_text(encoding="utf-8"))
    responses = json.loads(Path(RESPONSES_PATH).read_text(encoding="utf-8"))
    mapping = json.loads(Path(MAPPING_PATH).read_text(encoding="utf-8"))

    # 3. Build the Claude-backed scorer. Claude Haiku 4.5 handles the
    #    semantic verifications the regex version can't:
    #    - real schools outside the fiches (INSA Lyon, etc.)
    #    - fabricated reports (rapport ANSSI 2023) → contradicted
    #    - entity/number consistency (the 47% at Rennes case)
    #
    #    Cost: ~$1.25 for 96 answers (32q × 3 systems) at Haiku 4.5
    #    pricing. Retry logic handles transient Anthropic errors in the
    #    batch (rate limit / 5xx) without losing partial progress.
    anthropic = Anthropic(api_key=cfg.anthropic_api_key)

    _scorer_cache: dict[tuple[str, int], float] = {}

    def _claude_scorer_with_retry(
        answer: str, retrieved: list[dict], _dataset: list[dict]
    ) -> float:
        # Cache by (answer hash, retrieved count) — reweighting on the same
        # run_judge_v2 invocation might call the same (qid, label) twice;
        # caching avoids paying twice.
        cache_key = (answer[:200], len(retrieved))
        if cache_key in _scorer_cache:
            return _scorer_cache[cache_key]

        last_exc = None
        for attempt in range(6):
            try:
                score = claude_fact_check_score(
                    anthropic, answer, retrieved=retrieved
                )
                _scorer_cache[cache_key] = score
                return score
            except Exception as exc:
                last_exc = exc
                msg = str(exc)
                is_rate_limit = (
                    "429" in msg
                    or "rate_limit" in msg.lower()
                    or "overloaded" in msg.lower()
                )
                is_5xx = any(f" {c} " in f" {msg} " for c in ("500", "502", "503", "504"))
                is_transient = is_rate_limit or is_5xx or "timeout" in msg.lower()
                if not is_transient or attempt == 5:
                    print(
                        f"  fact-check error (final): {type(exc).__name__}: {msg[:200]}"
                    )
                    # Default to 1.0 (neutral) rather than crash — one bad
                    # answer shouldn't kill the whole run.
                    _scorer_cache[cache_key] = 1.0
                    return 1.0
                delay = (15.0 if is_rate_limit else 2.0) * (2 ** attempt)
                print(
                    f"  fact-check retry {attempt+1}/5 in {delay:.0f}s "
                    f"({type(exc).__name__})"
                )
                time.sleep(delay)
        if last_exc is not None:
            raise last_exc
        return 1.0  # unreachable

    # 3. Apply fact-check reweight using the Claude-backed scorer
    print(f"Reweighting {len(blind_v1)} questions with Claude Haiku fact-check...")
    blind_v2 = apply_fact_check_to_blind(
        blind_v1=blind_v1,
        responses_blind=responses,
        label_mapping=mapping,
        retrieved_by_qid=retrieved_by_qid,
        dataset=fiches,
        scorer=_claude_scorer_with_retry,
    )

    Path(V2_OUT_PATH).parent.mkdir(parents=True, exist_ok=True)
    Path(V2_OUT_PATH).write_text(
        json.dumps(blind_v2, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Saved to {V2_OUT_PATH}")

    # 4. Quick delta summary (per-system aggregate on sourçage + total)
    # We need to unblind using label_mapping to show per-system stats.
    from collections import defaultdict

    def aggregate(blind: list[dict]) -> dict:
        per_sys: dict[str, dict] = defaultdict(
            lambda: {"sourcage_sum": 0, "total_sum": 0, "n": 0}
        )
        for entry in blind:
            qid = entry["id"]
            m = mapping.get(qid, {})
            for label, scores in entry["scores"].items():
                sys_name = m.get(label, "?")
                per_sys[sys_name]["sourcage_sum"] += scores.get("sourcage", 0)
                per_sys[sys_name]["total_sum"] += scores.get("total", 0)
                per_sys[sys_name]["n"] += 1
        return {
            s: {
                "sourcage_mean": v["sourcage_sum"] / v["n"],
                "total_mean": v["total_sum"] / v["n"],
            }
            for s, v in per_sys.items()
        }

    v1_agg = aggregate(blind_v1)
    v2_agg = aggregate(blind_v2)
    print("\n=== Delta v1 → v2 (naïf juge vs fact-check juge) ===")
    for sys_name in sorted(v1_agg):
        v1 = v1_agg[sys_name]
        v2 = v2_agg[sys_name]
        ds = v2["sourcage_mean"] - v1["sourcage_mean"]
        dt = v2["total_mean"] - v1["total_mean"]
        print(
            f"  {sys_name:20s} | sourçage {v1['sourcage_mean']:.2f}→{v2['sourcage_mean']:.2f} ({ds:+.2f})"
            f" | total {v1['total_mean']:.2f}→{v2['total_mean']:.2f} ({dt:+.2f})"
        )

    # 5. Full analyze pipeline on v2 scores (summary + radar chart)
    from src.eval.analyze import main_v2
    print("\n=== Full analyze (judge v2) ===")
    main_v2()


if __name__ == "__main__":
    main()
