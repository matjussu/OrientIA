"""Maximal Marginal Relevance post-rerank selection.

MMR picks k items from a candidate list, greedily maximising:

    mmr(i) = λ · relevance(i) − (1 − λ) · max_sim(i, already_selected)

where relevance is the reranker score (normalised to [0, 1]) and
similarity is cosine similarity between candidate embeddings.

Purpose (Phase F.3.a): the label reranker often returns 3+ near-duplicate
fiches at the top (e.g. "EFREI Paris" × 3 with slight variants). MMR
diversifies by penalising candidates that are too similar to what has
already been picked, improving the `diversite_geo` and `comparaison`
criteria without hurting overall relevance.
"""
from __future__ import annotations

import numpy as np


DEFAULT_LAMBDA = 0.7


def mmr_select(
    candidates: list[dict],
    k: int,
    lambda_: float = DEFAULT_LAMBDA,
) -> list[dict]:
    """Select k items from candidates using MMR.

    Each candidate must be a dict with keys:
      - 'score': float — relevance signal from the reranker
      - 'embedding': np.ndarray — dense vector used for similarity

    Returns a list of the original candidate dicts in MMR selection
    order (not reverse-sorted by score). All original fields are
    preserved.
    """
    if not candidates or k <= 0:
        return []
    if k >= len(candidates):
        return list(candidates)

    scores = np.array([c["score"] for c in candidates], dtype="float32")
    score_max = float(scores.max()) if scores.max() > 0 else 1.0
    relevance = scores / score_max

    embeddings = np.stack([c["embedding"] for c in candidates]).astype("float32")
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.where(norms == 0.0, 1.0, norms)
    normed = embeddings / norms

    remaining = list(range(len(candidates)))
    first = int(np.argmax(relevance))
    selected = [first]
    remaining.remove(first)

    while len(selected) < k and remaining:
        sel_emb = normed[selected]
        rem_emb = normed[remaining]
        sims = rem_emb @ sel_emb.T
        max_sims = sims.max(axis=1)

        rem_rel = relevance[remaining]
        mmr_scores = lambda_ * rem_rel - (1.0 - lambda_) * max_sims
        best_local = int(np.argmax(mmr_scores))
        best_global = remaining[best_local]
        selected.append(best_global)
        remaining.remove(best_global)

    return [candidates[i] for i in selected]
