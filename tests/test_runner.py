import json
from pathlib import Path
from unittest.mock import MagicMock
from src.eval.runner import run_benchmark, BLIND_LABELS


def test_blind_labels_is_a_b_c():
    """BLIND_LABELS is the *legacy* triple — kept for backward compat
    with Run 6-10 archives. New runs (Phase F+) use blind_labels(N)."""
    assert BLIND_LABELS == ["A", "B", "C"]


def test_blind_labels_helper_supports_n_systems():
    """Phase F.2 — the runner now generalises to N systems (up to 26)
    via the blind_labels(n) helper. Used by Run F's 7-system matrix."""
    from src.eval.runner import blind_labels
    assert blind_labels(3) == ["A", "B", "C"]
    assert blind_labels(7) == ["A", "B", "C", "D", "E", "F", "G"]
    assert blind_labels(1) == ["A"]
    import pytest
    with pytest.raises(ValueError):
        blind_labels(0)
    with pytest.raises(ValueError):
        blind_labels(27)  # only A-Z available


def test_run_benchmark_produces_blind_mapping(tmp_path):
    questions = [
        {"id": "A1", "category": "biais_marketing", "text": "question 1"},
        {"id": "A2", "category": "biais_marketing", "text": "question 2"},
    ]

    sys1 = MagicMock(name="sys1"); sys1.answer.return_value = "answer from 1"
    sys2 = MagicMock(name="sys2"); sys2.answer.return_value = "answer from 2"
    sys3 = MagicMock(name="sys3"); sys3.answer.return_value = "answer from 3"

    systems = {"our_rag": sys1, "mistral_raw": sys2, "chatgpt_recorded": sys3}
    out_dir = tmp_path / "out"
    run_benchmark(questions, systems, out_dir, seed=42)

    responses = json.loads((out_dir / "responses_blind.json").read_text(encoding="utf-8"))
    mapping = json.loads((out_dir / "label_mapping.json").read_text(encoding="utf-8"))

    assert len(responses) == 2
    for q_entry in responses:
        assert set(q_entry["answers"].keys()) == {"A", "B", "C"}
        assert q_entry["id"] in ("A1", "A2")
        assert q_entry["category"] == "biais_marketing"

    for qid, map_for_q in mapping.items():
        assert set(map_for_q.keys()) == {"A", "B", "C"}
        assert set(map_for_q.values()) == {"our_rag", "mistral_raw", "chatgpt_recorded"}


def test_run_benchmark_saves_seed(tmp_path):
    questions = [{"id": "A1", "category": "biais_marketing", "text": "q"}]
    sys1 = MagicMock(); sys1.answer.return_value = "a"
    sys2 = MagicMock(); sys2.answer.return_value = "b"
    sys3 = MagicMock(); sys3.answer.return_value = "c"
    systems = {"our_rag": sys1, "mistral_raw": sys2, "chatgpt_recorded": sys3}

    run_benchmark(questions, systems, tmp_path, seed=1337)
    assert (tmp_path / "seed.txt").read_text().strip() == "1337"


def test_run_benchmark_accepts_at_least_two_systems(tmp_path):
    """Phase F.2 — relaxed from the historical 3-system assertion
    to ≥ 2. Run F uses 7 systems; Run G also uses 7. The single-
    system case is still rejected (no comparison possible)."""
    questions = [{"id": "A1", "category": "c", "text": "q"}]
    systems = {"only_one": MagicMock()}
    import pytest
    with pytest.raises(AssertionError):
        run_benchmark(questions, systems, tmp_path)


def test_run_benchmark_works_with_seven_systems(tmp_path):
    """Phase F.2 — generalised runner handles arbitrary N (here N=7
    for Run F's full matrix). Each question's answers dict has 7
    entries A-G mapped to the 7 system names."""
    questions = [{"id": "A1", "category": "c", "text": "q"}]
    systems = {}
    for i, name in enumerate(["our_rag", "mistral_neutral", "mistral_v3_2_no_rag",
                              "gpt4o_neutral", "gpt4o_v3_2_no_rag",
                              "claude_neutral", "claude_v3_2_no_rag"]):
        m = MagicMock()
        m.answer.return_value = f"answer from {name}"
        systems[name] = m

    run_benchmark(questions, systems, tmp_path, seed=42)
    responses = json.loads((tmp_path / "responses_blind.json").read_text(encoding="utf-8"))
    mapping = json.loads((tmp_path / "label_mapping.json").read_text(encoding="utf-8"))

    assert len(responses) == 1
    answers = responses[0]["answers"]
    assert set(answers.keys()) == {"A", "B", "C", "D", "E", "F", "G"}
    for label, ans in answers.items():
        assert ans.startswith("answer from")
    assert set(mapping["A1"].keys()) == {"A", "B", "C", "D", "E", "F", "G"}
    assert set(mapping["A1"].values()) == set(systems.keys())


def test_run_benchmark_is_reproducible_with_same_seed(tmp_path):
    """Double-blind reproducibility: same seed → same label mapping.
    Critical for the grid search (Task 4.5) which reruns the benchmark."""
    questions = [
        {"id": "A1", "category": "c", "text": "q1"},
        {"id": "A2", "category": "c", "text": "q2"},
    ]
    sys1 = MagicMock(); sys1.answer.return_value = "a"
    sys2 = MagicMock(); sys2.answer.return_value = "b"
    sys3 = MagicMock(); sys3.answer.return_value = "c"
    systems = {"our_rag": sys1, "mistral_raw": sys2, "chatgpt_recorded": sys3}

    out1 = tmp_path / "run1"
    out2 = tmp_path / "run2"
    run_benchmark(questions, systems, out1, seed=42)
    run_benchmark(questions, systems, out2, seed=42)

    m1 = json.loads((out1 / "label_mapping.json").read_text())
    m2 = json.loads((out2 / "label_mapping.json").read_text())
    assert m1 == m2  # Same seed, same mapping
