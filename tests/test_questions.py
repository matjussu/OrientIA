import json
from pathlib import Path


def test_questions_file_exists_and_valid():
    path = Path("src/eval/questions.json")
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "questions" in data
    assert data.get("version"), "version field is missing or empty"
    assert len(data["questions"]) == 32

    ids = [q["id"] for q in data["questions"]]
    assert len(ids) == len(set(ids)), "duplicate question ids"

    categories = {q["category"] for q in data["questions"]}
    assert categories == {
        "biais_marketing", "realisme", "decouverte",
        "diversite_geo", "passerelles", "comparaison", "honnetete"
    }

    REQUIRED_KEYS = {"id", "category", "text"}
    for q in data["questions"]:
        assert set(q.keys()) == REQUIRED_KEYS, f"unexpected keys in {q.get('id', '?')}: {set(q.keys()) ^ REQUIRED_KEYS}"
        assert q["text"].strip()
        assert q["id"][0] in "ABCDEFH"


def test_ideal_answers_reference_valid_ids():
    questions = json.loads(Path("src/eval/questions.json").read_text(encoding="utf-8"))
    ideal = json.loads(Path("src/eval/ideal_answers.json").read_text(encoding="utf-8"))
    valid_ids = {q["id"] for q in questions["questions"]}
    for qid in ideal:
        assert qid in valid_ids, f"ideal_answers references unknown id: {qid}"
