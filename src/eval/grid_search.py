"""Grid search over the secnumedu_boost coefficient.

Sweeps 5 values of secnumedu_boost (from 1.0 = ablation baseline to 2.0 =
strong boost), keeping the other 6 rerank coefficients fixed at their
defaults. For each cell, re-runs the benchmark on the 30 scored questions
(excluding the 2 honesty tests), re-judges via Claude, and records the
aggregate our_rag total score.

The resulting sensitivity curve is the empirical validation of the INRIA
thesis — it shows whether the label boost actually improves scores and
at what coefficient the improvement peaks.

DO NOT RUN unless data/chatgpt_recorded.json is populated and you have
Mistral+Anthropic credits (this costs ~5 * 30 * 2 LLM calls + 5 * 30
Claude judge calls ≈ $1-3).
"""
import json
from pathlib import Path
from mistralai.client import Mistral
from anthropic import Anthropic
from src.config import load_config
from src.rag.reranker import RerankConfig
from src.rag.pipeline import OrientIAPipeline
from src.eval.systems import OurRagSystem, MistralRawSystem, ChatGPTRecordedSystem
from src.eval.runner import run_benchmark
from src.eval.judge import judge_all
from src.eval.analyze import unblind_scores, aggregate_by_system


# The 5 coefficient values sweep from ablation (1.0 = no boost) to
# strong (2.0 = 2× multiplier). 1.5 is the current default verified
# empirically on question A1.
_GRID_VALUES = [1.0, 1.2, 1.5, 1.8, 2.0]


def make_coefficient_grid() -> list[RerankConfig]:
    defaults = RerankConfig()
    return [
        RerankConfig(
            secnumedu_boost=b,
            cti_boost=defaults.cti_boost,
            grade_master_boost=defaults.grade_master_boost,
            public_boost=defaults.public_boost,
            level_boost_bac5=defaults.level_boost_bac5,
            level_boost_bac3=defaults.level_boost_bac3,
            etab_named_boost=defaults.etab_named_boost,
        )
        for b in _GRID_VALUES
    ]


def main():
    cfg_env = load_config()
    mistral = Mistral(api_key=cfg_env.mistral_api_key)
    anthropic = Anthropic(api_key=cfg_env.anthropic_api_key)

    fiches = json.loads(Path("data/processed/formations.json").read_text(encoding="utf-8"))
    pipeline = OrientIAPipeline(mistral, fiches)

    index_path = Path("data/embeddings/formations.index")
    if index_path.exists():
        print(f"Loading cached index from {index_path}...")
        pipeline.load_index_from(str(index_path))
    else:
        print("Building index from scratch...")
        pipeline.build_index()
        pipeline.save_index_to(str(index_path))

    all_questions = json.loads(Path("src/eval/questions.json").read_text(encoding="utf-8"))["questions"]
    # Exclude honesty questions — they're by design not RAG-favorable
    # and would dilute the signal from the scored categories
    scored_questions = [q for q in all_questions if q["category"] != "honnetete"]
    print(f"Grid search over {len(scored_questions)} scored questions × {len(_GRID_VALUES)} coefficient values")

    grid_results = []
    for i, rerank_cfg in enumerate(make_coefficient_grid()):
        print(f"\n=== Grid cell {i+1}/5: secnumedu_boost={rerank_cfg.secnumedu_boost} ===")
        pipeline.rerank_config = rerank_cfg

        systems = {
            "our_rag": OurRagSystem(pipeline),
            "mistral_raw": MistralRawSystem(mistral),
            "chatgpt_recorded": ChatGPTRecordedSystem("data/chatgpt_recorded.json"),
        }

        out_dir = Path(f"results/grid/cell_{i}")
        # Use a different seed per cell so the blind label mapping differs.
        # This avoids a degenerate case where the same label happens to
        # always be our_rag and the judge is unable to distinguish.
        run_benchmark(scored_questions, systems, out_dir, seed=42 + i)

        blind_responses = json.loads((out_dir / "responses_blind.json").read_text(encoding="utf-8"))
        blind_scores = judge_all(anthropic, blind_responses)
        (out_dir / "blind_scores.json").write_text(
            json.dumps(blind_scores, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        mapping = json.loads((out_dir / "label_mapping.json").read_text(encoding="utf-8"))
        unblinded = unblind_scores(blind_scores, mapping)
        summary = aggregate_by_system(unblinded)

        grid_results.append({
            "config": rerank_cfg.as_dict(),
            "summary": summary,
        })

    Path("results/grid").mkdir(parents=True, exist_ok=True)
    Path("results/grid/grid_summary.json").write_text(
        json.dumps(grid_results, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("\n=== GRID SEARCH RESULTS ===")
    print(f"{'boost':<8} {'our_rag total':<15} {'mistral_raw':<15} {'chatgpt':<15}")
    for cell in grid_results:
        boost = cell["config"]["secnumedu_boost"]
        summary = cell["summary"]
        our = summary.get("our_rag", {}).get("total", 0)
        raw = summary.get("mistral_raw", {}).get("total", 0)
        gpt = summary.get("chatgpt_recorded", {}).get("total", 0)
        print(f"{boost:<8.1f} {our:<15.2f} {raw:<15.2f} {gpt:<15.2f}")


if __name__ == "__main__":
    main()
