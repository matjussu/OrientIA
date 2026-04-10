from src.eval.analyze import (
    unblind_scores,
    aggregate_by_system,
    aggregate_by_category,
    CRITERIA,
)


def test_criteria_are_the_six_expected():
    assert CRITERIA == ["neutralite", "realisme", "sourcage", "diversite_geo", "agentivite", "decouverte"]


def test_unblind_scores_maps_labels_to_systems():
    blind_scores = [
        {"id": "A1", "category": "biais_marketing", "scores": {
            "A": {"neutralite": 3, "realisme": 2, "sourcage": 2, "diversite_geo": 1,
                  "agentivite": 2, "decouverte": 1, "total": 11, "justification": ""},
            "B": {"neutralite": 1, "realisme": 1, "sourcage": 0, "diversite_geo": 1,
                  "agentivite": 1, "decouverte": 1, "total": 5, "justification": ""},
            "C": {"neutralite": 2, "realisme": 3, "sourcage": 3, "diversite_geo": 2,
                  "agentivite": 3, "decouverte": 2, "total": 15, "justification": ""},
        }},
    ]
    mapping = {"A1": {"A": "our_rag", "B": "mistral_raw", "C": "chatgpt_recorded"}}

    unblinded = unblind_scores(blind_scores, mapping)
    assert unblinded[0]["systems"]["our_rag"]["total"] == 11
    assert unblinded[0]["systems"]["chatgpt_recorded"]["total"] == 15
    assert unblinded[0]["id"] == "A1"
    assert unblinded[0]["category"] == "biais_marketing"


def test_unblind_scores_excludes_justification_field():
    blind_scores = [
        {"id": "A1", "category": "c", "scores": {
            "A": {"neutralite": 1, "realisme": 1, "sourcage": 1, "diversite_geo": 1,
                  "agentivite": 1, "decouverte": 1, "total": 6, "justification": "some text"},
            "B": {"neutralite": 1, "realisme": 1, "sourcage": 1, "diversite_geo": 1,
                  "agentivite": 1, "decouverte": 1, "total": 6, "justification": ""},
            "C": {"neutralite": 1, "realisme": 1, "sourcage": 1, "diversite_geo": 1,
                  "agentivite": 1, "decouverte": 1, "total": 6, "justification": ""},
        }},
    ]
    mapping = {"A1": {"A": "our_rag", "B": "mistral_raw", "C": "chatgpt_recorded"}}

    unblinded = unblind_scores(blind_scores, mapping)
    # justification should NOT be in the aggregated scores (it's free text, not a criterion)
    assert "justification" not in unblinded[0]["systems"]["our_rag"]


def test_aggregate_by_system_averages_criteria():
    unblinded = [
        {"id": "A1", "category": "biais_marketing", "systems": {
            "our_rag": {"neutralite": 3, "realisme": 2, "sourcage": 2, "diversite_geo": 1,
                        "agentivite": 2, "decouverte": 1, "total": 11},
            "mistral_raw": {"neutralite": 1, "realisme": 1, "sourcage": 0, "diversite_geo": 1,
                            "agentivite": 1, "decouverte": 1, "total": 5},
        }},
        {"id": "A2", "category": "biais_marketing", "systems": {
            "our_rag": {"neutralite": 3, "realisme": 3, "sourcage": 3, "diversite_geo": 2,
                        "agentivite": 2, "decouverte": 2, "total": 15},
            "mistral_raw": {"neutralite": 2, "realisme": 1, "sourcage": 1, "diversite_geo": 1,
                            "agentivite": 1, "decouverte": 1, "total": 7},
        }},
    ]
    agg = aggregate_by_system(unblinded)
    assert agg["our_rag"]["neutralite"] == 3.0
    assert agg["our_rag"]["total"] == 13.0
    assert agg["mistral_raw"]["total"] == 6.0


def test_aggregate_by_category_averages_totals_per_system():
    unblinded = [
        {"id": "A1", "category": "biais_marketing", "systems": {
            "our_rag": {"total": 15},
            "chatgpt_recorded": {"total": 8},
        }},
        {"id": "A2", "category": "biais_marketing", "systems": {
            "our_rag": {"total": 17},
            "chatgpt_recorded": {"total": 6},
        }},
        {"id": "B1", "category": "realisme", "systems": {
            "our_rag": {"total": 16},
            "chatgpt_recorded": {"total": 10},
        }},
    ]
    by_cat = aggregate_by_category(unblinded)
    assert by_cat["biais_marketing"]["our_rag"] == 16.0
    assert by_cat["biais_marketing"]["chatgpt_recorded"] == 7.0
    assert by_cat["realisme"]["our_rag"] == 16.0
