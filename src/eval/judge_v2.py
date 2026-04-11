"""Judge v2 — pure post-processing reweight of v1 with fact-check.

Judge v2 does NOT call Claude again. It reuses the v1 scores and
multiplies the `sourcage` criterion by `fact_check_score`, which is
deterministic Python. This makes the methodological reform cost $0.

Rationale: the published INRIA paper pairs the v1 and v2 numbers to
argue that naïve LLM-as-judge rubrics reward apparent sourcing over
true sourcing (the 2026-04-11 finding). v2 materializes that argument
empirically on the same responses, enabling a direct apples-to-apples
comparison.
"""
from __future__ import annotations

from copy import deepcopy

from src.eval.fact_check import fact_check_score


_CRITERIA = [
    "neutralite",
    "realisme",
    "sourcage",
    "diversite_geo",
    "agentivite",
    "decouverte",
]


def reweight_v1_scores(v1: dict, fact_check_ratio: float) -> dict:
    """Return a new score dict with sourcage = round(sourcage * ratio).

    The v1 input dict is not mutated. The returned dict has:
      * all 6 criteria (neutralite, realisme, sourcage, diversite_geo,
        agentivite, decouverte)
      * total recomputed from the new values
      * a new `fact_check_ratio` field recording the applied weight
      * `justification` preserved from v1
    """
    out = dict(v1)
    new_sourcage = round(v1["sourcage"] * fact_check_ratio)
    out["sourcage"] = max(0, min(3, new_sourcage))
    out["total"] = sum(out[c] for c in _CRITERIA)
    out["fact_check_ratio"] = fact_check_ratio
    return out


def apply_fact_check_to_blind(
    *,
    blind_v1: list[dict],
    responses_blind: list[dict],
    label_mapping: dict,
    retrieved_by_qid: dict,
    dataset: list[dict],
) -> list[dict]:
    """Recompute blind scores with the fact-check reweight per system.

    Arguments:
      blind_v1 — list of {id, category, scores: {A, B, C}} as produced
                 by src.eval.judge.judge_all
      responses_blind — list of {id, category, text, answers: {A,B,C}}
                        from results/raw_responses/responses_blind.json
      label_mapping — {qid: {A: sysname, B: sysname, C: sysname}}
      retrieved_by_qid — {qid: [retrieved fiches]} — only our_rag has
                         meaningful retrieved; mistral_raw/chatgpt get []
                         unconditionally (they had no RAG context).
      dataset — the full list of fiches, used as fallback ground truth
                so that mistral_raw still gets credit for correctly
                naming schools that exist in the dataset.

    Returns:
      A new list of blind scores with the same structure as blind_v1,
      plus `fact_check_ratio` per label.
    """
    answers_by_qid = {e["id"]: e["answers"] for e in responses_blind}
    out: list[dict] = []
    for entry in blind_v1:
        qid = entry["id"]
        new_scores: dict[str, dict] = {}
        mapping = label_mapping.get(qid, {})
        answers = answers_by_qid.get(qid, {})
        for label, v1 in entry["scores"].items():
            sys_name = mapping.get(label, "")
            ans = answers.get(label, "")
            retrieved = (
                retrieved_by_qid.get(qid, []) if sys_name == "our_rag" else []
            )
            ratio = fact_check_score(
                ans, retrieved=retrieved, dataset=dataset
            )
            new_scores[label] = reweight_v1_scores(v1, fact_check_ratio=ratio)
        out.append(
            {
                "id": qid,
                "category": entry["category"],
                "scores": new_scores,
            }
        )
    return out
