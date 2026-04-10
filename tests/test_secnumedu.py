import json
from pathlib import Path
from src.collect.secnumedu import load_secnumedu


def test_load_secnumedu_returns_list_with_label(tmp_path):
    data = [{"nom": "Test", "etablissement": "Univ X", "ville": "Paris"}]
    path = tmp_path / "secnumedu.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    fiches = load_secnumedu(path)
    assert len(fiches) == 1
    assert fiches[0]["labels"] == ["SecNumEdu"]
    assert fiches[0]["source"] == "secnumedu"
    assert fiches[0]["domaine"] == "cyber"
