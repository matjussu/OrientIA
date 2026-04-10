import json
from pathlib import Path


def test_questions_file_exists_and_valid():
    path = Path("src/eval/questions.json")
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "questions" in data
    assert len(data["questions"]) == 32

    ids = [q["id"] for q in data["questions"]]
    assert len(ids) == len(set(ids)), "duplicate question ids"

    categories = {q["category"] for q in data["questions"]}
    assert categories == {
        "biais_marketing", "realisme", "decouverte",
        "diversite_geo", "passerelles", "comparaison", "honnetete"
    }

    for q in data["questions"]:
        assert q["text"].strip()
        assert q["id"][0] in "ABCDEFH"
