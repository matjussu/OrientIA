import json
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


BLIND_LABELS = ["A", "B", "C"]
"""Legacy 3-label list, kept for backward compatibility with Run 6-10
archives. Phase F+ generalises to N labels via blind_labels(n)."""


def blind_labels(n: int) -> list[str]:
    """Return the N blinding labels used by run_benchmark.

    Run F's 7-system matrix uses N=7 → ["A", "B", "C", "D", "E", "F", "G"].
    The judge prompt is generalised similarly so each label receives an
    independent score.
    """
    if n < 1:
        raise ValueError("Need at least 1 system to label")
    if n > 26:
        raise ValueError(f"Only 26 single-letter labels available, got {n}")
    return [chr(ord("A") + i) for i in range(n)]


def _call_with_retry(fn, *args, max_retries: int = 5, **kwargs):
    """Call `fn(*args, **kwargs)` with exponential backoff on transient errors.

    Handles three classes of transient failure:
    - Timeouts / connection resets (2s base delay)
    - 5xx server errors (2s base delay)
    - 429 rate limit / capacity exceeded (15s base delay — free tier
      recoveries take longer than transient network blips)

    Non-transient exceptions (auth, KeyError, ValueError) bubble up
    immediately. The ChatGPTRecordedSystem is file-local so this is
    effectively a no-op for it.
    """
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            exc_name = type(exc).__name__
            msg = str(exc)

            is_rate_limit = (
                "429" in msg
                or "rate limit" in msg.lower()
                or "capacity" in msg.lower()
                or "RateLimit" in exc_name
            )
            is_transient_network = any(
                kw in exc_name for kw in ("Timeout", "Connect", "Read", "Network", "Remote")
            )
            # Any 5xx (500-599) — includes Cloudflare 520/521/522/523/524/525/526/527
            # which regularly bubble up through api.mistral.ai's proxy.
            is_5xx = bool(re.search(r"\b5\d{2}\b", msg))
            # Cloudflare pages sometimes show up as HTML instead of status codes,
            # with phrases like "Web server returned an unknown error".
            is_cloudflare_html = (
                "cloudflare" in msg.lower()
                or "web server is returning" in msg.lower()
                or "web server returned" in msg.lower()
            )

            is_retriable = (
                is_rate_limit or is_transient_network or is_5xx or is_cloudflare_html
            )

            if not is_retriable or attempt == max_retries:
                raise

            base_delay = 15.0 if is_rate_limit else 2.0
            delay = base_delay * (2 ** attempt)
            kind = "rate-limit" if is_rate_limit else "transient"
            print(f"  [retry {attempt+1}/{max_retries}] {kind} {exc_name}: {msg[:120]}. Waiting {delay:.0f}s...")
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
    n_systems = len(system_names)
    # Phase F.2 — at least 2 systems required (a single system has no
    # comparison value); Phase F itself uses N=7. The previous "==3"
    # invariant is relaxed to accommodate the 7-system matrix.
    assert n_systems >= 2, (
        f"Need at least 2 systems for a comparison benchmark, got {n_systems}"
    )
    labels = blind_labels(n_systems)

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

        mapping = dict(zip(labels, shuffled))
        label_mapping[q["id"]] = mapping

        print(f"  {q['id']} [{q['category']}]: running 3 systems in parallel...")
        # Parallelize the 3 system calls per question via a thread pool.
        # ChatGPTRecordedSystem is file-local (instant), MistralRawSystem +
        # OurRagSystem each hit the Mistral API — running them concurrently
        # collapses question wall-time from ~3 × API_latency to ~1 × API_latency.
        # max_workers=3 is safe on Mistral paid tier (no bursting beyond 3 RPS).
        answers = {}

        def _answer_one(label_sys: tuple[str, str]) -> tuple[str, str]:
            label, sys_name = label_sys
            return label, _call_with_retry(
                systems[sys_name].answer, q["id"], q["text"]
            )

        with ThreadPoolExecutor(max_workers=3) as pool:
            for label, text in pool.map(_answer_one, mapping.items()):
                answers[label] = text

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
