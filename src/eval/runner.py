import json
import random
from pathlib import Path


BLIND_LABELS = ["A", "B", "C"]


def run_benchmark(
    questions: list[dict],
    systems: dict,
    output_dir: str | Path,
    seed: int = 42,
) -> None:
    """Run each system on every question with randomized blind labels.

    For each question, the three systems are shuffled and assigned labels
    A, B, C. The label → system mapping is saved separately from the
    responses so the Claude judge (Task 4.3) sees only A/B/C and cannot
    bias toward the known system names.

    Outputs:
      - {output_dir}/responses_blind.json : list of {id, category, text, answers: {A, B, C}}
      - {output_dir}/label_mapping.json   : {qid: {A: sysname, B: sysname, C: sysname}}
      - {output_dir}/seed.txt             : the seed used (for reproducibility)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)

    responses_blind = []
    label_mapping = {}

    system_names = list(systems.keys())
    assert len(system_names) == 3, f"Expected exactly 3 systems, got {len(system_names)}"

    for q in questions:
        shuffled = system_names[:]
        rng.shuffle(shuffled)
        mapping = dict(zip(BLIND_LABELS, shuffled))
        label_mapping[q["id"]] = mapping

        answers = {}
        for label, sys_name in mapping.items():
            system = systems[sys_name]
            answers[label] = system.answer(q["id"], q["text"])

        responses_blind.append({
            "id": q["id"],
            "category": q["category"],
            "text": q["text"],
            "answers": answers,
        })

    (output_dir / "responses_blind.json").write_text(
        json.dumps(responses_blind, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "label_mapping.json").write_text(
        json.dumps(label_mapping, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "seed.txt").write_text(str(seed), encoding="utf-8")
