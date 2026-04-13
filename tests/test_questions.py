"""Tests for src/eval/questions.json — Phase F.1 schema v2.0.

The dataset went from 32 questions (Run 6-10) to 100 questions
(Run F onward), with explicit dev/test split and type marker
(normal / adversarial / cross_domain). All headline numbers in
the study report are computed on the test set (68 questions),
hold-out from prompt v3.x calibration.
"""
import json
from pathlib import Path


REQUIRED_KEYS = {"id", "category", "text", "split", "type"}
NORMAL_CATEGORIES = {
    "biais_marketing", "realisme", "decouverte",
    "diversite_geo", "passerelles", "comparaison", "honnetete",
}
ALL_CATEGORIES = NORMAL_CATEGORIES | {"adversarial", "cross_domain"}
VALID_TYPES = {"normal", "adversarial", "cross_domain"}
VALID_SPLITS = {"dev", "test"}


def _load_questions():
    return json.loads(
        Path("src/eval/questions.json").read_text(encoding="utf-8")
    )


def test_questions_file_exists_and_total_is_100():
    data = _load_questions()
    assert "questions" in data
    assert data.get("version") == "2.0"
    assert len(data["questions"]) == 100


def test_questions_have_required_keys():
    """All questions carry the v2 schema fields (split + type)."""
    data = _load_questions()
    for q in data["questions"]:
        missing = REQUIRED_KEYS - set(q.keys())
        assert not missing, f"{q.get('id', '?')} is missing {missing}"
        assert q["text"].strip(), f"{q['id']} has empty text"


def test_question_ids_are_unique_and_well_prefixed():
    data = _load_questions()
    ids = [q["id"] for q in data["questions"]]
    assert len(ids) == len(set(ids)), "duplicate question ids"
    for q in data["questions"]:
        assert q["id"][0] in "ABCDEFHXZ", f"unexpected prefix: {q['id']}"


def test_categories_cover_normal_plus_adversarial_plus_cross_domain():
    data = _load_questions()
    cats = {q["category"] for q in data["questions"]}
    assert cats == ALL_CATEGORIES


def test_dev_split_has_32_questions_test_has_68():
    """The 32 dev questions are exactly the ones from Run 6-10
    (already used for prompt v3.x calibration). The 68 test
    questions are the hold-out set introduced in Phase F.1.
    """
    data = _load_questions()
    by_split = {"dev": [], "test": []}
    for q in data["questions"]:
        assert q["split"] in VALID_SPLITS, q["id"]
        by_split[q["split"]].append(q)
    assert len(by_split["dev"]) == 32
    assert len(by_split["test"]) == 68


def test_test_split_includes_adversarial_and_cross_domain():
    """All adversarial and cross_domain questions live in the
    test set — they were never seen during prompt calibration."""
    data = _load_questions()
    for q in data["questions"]:
        if q["type"] in ("adversarial", "cross_domain"):
            assert q["split"] == "test", (
                f"{q['id']} is {q['type']} but in dev split"
            )


def test_adversarial_count_at_least_10():
    """Phase F.1 spec: at least 10 adversarial questions."""
    data = _load_questions()
    adv = [q for q in data["questions"] if q["type"] == "adversarial"]
    assert len(adv) >= 10


def test_cross_domain_count_at_least_5():
    """Phase F.1 spec: at least 5 cross-domain questions."""
    data = _load_questions()
    cd = [q for q in data["questions"] if q["type"] == "cross_domain"]
    assert len(cd) >= 5


def test_normal_categories_are_balanced_in_test_split():
    """Each of the 7 normal categories should have at least 5 test
    questions to support per-category aggregation with reasonable
    confidence intervals."""
    data = _load_questions()
    from collections import Counter
    cats = Counter(
        q["category"]
        for q in data["questions"]
        if q["split"] == "test" and q["type"] == "normal"
    )
    for c in NORMAL_CATEGORIES:
        assert cats.get(c, 0) >= 5, f"{c} only has {cats.get(c, 0)} test"


def test_dev_questions_match_historical_set():
    """The 32 dev questions are the exact ones used in Runs 6-10,
    so the historical results remain comparable. Verify the
    well-known ids A1, B4, C1, D1, E4, F1, H1, H2 are present."""
    data = _load_questions()
    dev_ids = {q["id"] for q in data["questions"] if q["split"] == "dev"}
    must_have = {"A1", "A5", "B1", "B4", "C1", "C3", "C5", "D1",
                 "D5", "E1", "E4", "F1", "F5", "H1", "H2"}
    assert must_have <= dev_ids, f"missing dev ids: {must_have - dev_ids}"


def test_ideal_answers_reference_valid_ids():
    questions = _load_questions()
    ideal = json.loads(
        Path("src/eval/ideal_answers.json").read_text(encoding="utf-8")
    )
    valid_ids = {q["id"] for q in questions["questions"]}
    for qid in ideal:
        assert qid in valid_ids, f"ideal_answers references unknown id: {qid}"
