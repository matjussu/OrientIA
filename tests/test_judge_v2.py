"""Tests for judge_v2 — post-processing re-weight of judge v1 with fact-check.

Judge v2 does NOT call Claude again. It takes the already-computed v1
scores, the raw answers, the retrieved fiches (for our_rag) or empty
list (for baselines), and the full dataset, and post-weights the
`sourcage` criterion by `fact_check_score`. The `total` is recomputed.

This is the core trick: it makes the methodological reform cost $0
instead of $1.15, because fact-checking is pure Python.
"""
from src.eval.judge_v2 import (
    reweight_v1_scores,
    apply_fact_check_to_blind,
)


def _v1_score(sourcage=3, neutralite=3, realisme=3, diversite_geo=3,
              agentivite=3, decouverte=3):
    return {
        "neutralite": neutralite,
        "realisme": realisme,
        "sourcage": sourcage,
        "diversite_geo": diversite_geo,
        "agentivite": agentivite,
        "decouverte": decouverte,
        "total": (neutralite + realisme + sourcage + diversite_geo
                  + agentivite + decouverte),
        "justification": "baseline",
    }


def test_reweight_perfect_factcheck_keeps_sourcage():
    """Fact-check 1.0 → sourçage unchanged."""
    v1 = _v1_score(sourcage=3)
    v2 = reweight_v1_scores(v1, fact_check_ratio=1.0)
    assert v2["sourcage"] == 3
    assert v2["total"] == v1["total"]


def test_reweight_zero_factcheck_zeroes_sourcage():
    """Fact-check 0.0 → sourçage → 0, total drops by 3."""
    v1 = _v1_score(sourcage=3)
    v2 = reweight_v1_scores(v1, fact_check_ratio=0.0)
    assert v2["sourcage"] == 0
    assert v2["total"] == v1["total"] - 3


def test_reweight_partial_factcheck_rounds_to_nearest_int():
    """Fact-check 0.5 on sourçage 3 → 1.5 → rounds to 2."""
    v1 = _v1_score(sourcage=3)
    v2 = reweight_v1_scores(v1, fact_check_ratio=0.5)
    assert v2["sourcage"] == 2


def test_reweight_preserves_other_criteria():
    v1 = _v1_score(neutralite=2, realisme=3, sourcage=3, diversite_geo=1,
                   agentivite=2, decouverte=0)
    v2 = reweight_v1_scores(v1, fact_check_ratio=0.3)
    assert v2["neutralite"] == 2
    assert v2["realisme"] == 3
    assert v2["diversite_geo"] == 1
    assert v2["agentivite"] == 2
    assert v2["decouverte"] == 0
    # sourçage = round(3 * 0.3) = 1
    assert v2["sourcage"] == 1
    assert v2["total"] == 2 + 3 + 1 + 1 + 2 + 0


def test_reweight_records_fact_check_ratio():
    v1 = _v1_score(sourcage=3)
    v2 = reweight_v1_scores(v1, fact_check_ratio=0.42)
    assert "fact_check_ratio" in v2
    assert abs(v2["fact_check_ratio"] - 0.42) < 1e-6


def test_reweight_tolerates_missing_criterion():
    """Claude occasionally drops a criterion in its JSON output
    (observed: F1/C missing diversite_geo in Run 7). reweight must
    still compute a total without raising KeyError."""
    v1 = {
        "neutralite": 3, "realisme": 3, "sourcage": 3,
        "agentivite": 3, "decouverte": 3, "total": 15,
        "justification": "missing diversite_geo on purpose",
    }
    v2 = reweight_v1_scores(v1, fact_check_ratio=1.0)
    # diversite_geo defaulted to 0, total = 3+3+3+0+3+3 = 15
    assert v2["diversite_geo"] == 0
    assert v2["total"] == 15


def test_apply_fact_check_to_blind_full_flow():
    """Integration: given blind scores + answers + retrieved_by_qid + dataset,
    produces a new list of blind scores with sourçage reweighted per system."""
    blind_v1 = [
        {
            "id": "Q1",
            "category": "test",
            "scores": {
                "A": _v1_score(sourcage=3),
                "B": _v1_score(sourcage=3),
                "C": _v1_score(sourcage=3),
            },
        }
    ]
    label_mapping = {"Q1": {"A": "our_rag", "B": "mistral_raw", "C": "chatgpt"}}
    responses_blind = [
        {
            "id": "Q1",
            "answers": {
                # A = our_rag: verified citations (schools + onisep id in retrieved)
                "A": "EPITA propose un master cyber. Source ONISEP FOR.1577.",
                # B = mistral_raw: fabricated citations (unverifiable report)
                "B": "Selon le rapport ANSSI 2023, le taux est de 87%.",
                # C = chatgpt: no claims → neutral fact_check = 1.0
                "C": "Il est important de bien choisir sa formation.",
            },
        }
    ]
    retrieved_by_qid = {
        "Q1": [
            {"fiche": {"etablissement": "EPITA",
                       "url_onisep": "https://onisep.fr/FOR.1577"}}
        ]
    }
    dataset = [{"etablissement": "EPITA",
                "url_onisep": "https://onisep.fr/FOR.1577"}]

    blind_v2 = apply_fact_check_to_blind(
        blind_v1=blind_v1,
        responses_blind=responses_blind,
        label_mapping=label_mapping,
        retrieved_by_qid=retrieved_by_qid,
        dataset=dataset,
    )

    # A should keep sourçage 3 (everything verified)
    assert blind_v2[0]["scores"]["A"]["sourcage"] == 3
    # B should get sourçage reduced (fabricated rapport + unverified %)
    assert blind_v2[0]["scores"]["B"]["sourcage"] < 3
    # C has no claims → neutral 1.0 → sourçage unchanged
    assert blind_v2[0]["scores"]["C"]["sourcage"] == 3


def test_apply_fact_check_retrieved_only_for_our_rag():
    """For mistral_raw and chatgpt, retrieved is always empty even if
    we have retrieved data for the question. Only our_rag gets to
    'keep its sources'.
    """
    blind_v1 = [{
        "id": "Q1", "category": "test",
        "scores": {"A": _v1_score(sourcage=3), "B": _v1_score(sourcage=3),
                   "C": _v1_score(sourcage=3)},
    }]
    # B = mistral_raw cites EPITA (which is in dataset) — should still be
    # verified because EPITA exists in the dataset fallback.
    responses_blind = [{
        "id": "Q1",
        "answers": {
            "A": "EPITA est une bonne école.",
            "B": "EPITA est une bonne école.",
            "C": "EPITA est une bonne école.",
        },
    }]
    label_mapping = {"Q1": {"A": "our_rag", "B": "mistral_raw", "C": "chatgpt"}}
    retrieved_by_qid = {"Q1": [{"fiche": {"etablissement": "EPITA"}}]}
    dataset = [{"etablissement": "EPITA"}]

    blind_v2 = apply_fact_check_to_blind(
        blind_v1=blind_v1,
        responses_blind=responses_blind,
        label_mapping=label_mapping,
        retrieved_by_qid=retrieved_by_qid,
        dataset=dataset,
    )
    # All three see EPITA in dataset → all verified → all sourçage 3
    for label in ("A", "B", "C"):
        assert blind_v2[0]["scores"][label]["sourcage"] == 3
