import json
import random
import time
from pathlib import Path


BLIND_LABELS = ["A", "B", "C"]


def _call_with_retry(fn, *args, max_retries: int = 4, base_delay: float = 2.0, **kwargs):
    """Call `fn(*args, **kwargs)` with exponential backoff on transient errors.

    Mistral and Anthropic API calls occasionally hit ReadTimeout or transient
    5xx errors when the model is cold-starting or under load. Retry with
    2s / 4s / 8s / 16s delays before giving up. The ChatGPTRecordedSystem
    doesn't hit network so this is effectively a no-op for it.
    """
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            exc_name = type(exc).__name__
            # Only retry on transient network / timeout / 5xx errors.
            # Other exceptions (auth, KeyError, ValueError) bubble up immediately.
            is_transient = any(
                kw in exc_name for kw in ("Timeout", "Connect", "Read", "Network", "Remote")
            ) or "503" in str(exc) or "502" in str(exc) or "504" in str(exc)
            if not is_transient or attempt == max_retries:
                raise
            delay = base_delay * (2 ** attempt)
            print(f"  [retry {attempt+1}/{max_retries}] {exc_name}: {exc}. Waiting {delay}s...")
            time.sleep(delay)
    raise last_exc


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

    Supports resuming: if responses_blind.json already exists in output_dir,
    questions already answered are skipped. This makes the benchmark robust
    to mid-run network failures — just rerun and it picks up where it left off.

    Outputs:
      - {output_dir}/responses_blind.json : list of {id, category, text, answers: {A, B, C}}
      - {output_dir}/label_mapping.json   : {qid: {A: sysname, B: sysname, C: sysname}}
      - {output_dir}/seed.txt             : the seed used (for reproducibility)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)

    system_names = list(systems.keys())
    assert len(system_names) == 3, f"Expected exactly 3 systems, got {len(system_names)}"

    # Resume support: load any previously-saved partial state
    responses_path = output_dir / "responses_blind.json"
    mapping_path = output_dir / "label_mapping.json"
    if responses_path.exists() and mapping_path.exists():
        responses_blind = json.loads(responses_path.read_text(encoding="utf-8"))
        label_mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
        done_ids = {e["id"] for e in responses_blind}
        if done_ids:
            print(f"  Resuming: {len(done_ids)} questions already done, skipping them.")
    else:
        responses_blind = []
        label_mapping = {}
        done_ids = set()

    for q in questions:
        # Advance the RNG by the same amount as if we had answered this question,
        # to keep the mapping reproducible even with skip/resume.
        shuffled = system_names[:]
        rng.shuffle(shuffled)

        if q["id"] in done_ids:
            continue

        mapping = dict(zip(BLIND_LABELS, shuffled))
        label_mapping[q["id"]] = mapping

        print(f"  {q['id']} [{q['category']}]: running 3 systems...")
        answers = {}
        for label, sys_name in mapping.items():
            system = systems[sys_name]
            answers[label] = _call_with_retry(system.answer, q["id"], q["text"])

        responses_blind.append({
            "id": q["id"],
            "category": q["category"],
            "text": q["text"],
            "answers": answers,
        })

        # Incremental save after every question — ensures no work is lost
        # if a later question hits a non-retriable failure.
        responses_path.write_text(
            json.dumps(responses_blind, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        mapping_path.write_text(
            json.dumps(label_mapping, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    (output_dir / "seed.txt").write_text(str(seed), encoding="utf-8")
