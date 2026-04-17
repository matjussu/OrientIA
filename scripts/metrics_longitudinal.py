"""Apply B3 / B5 / B6 retroactively to all historical diffs.

Reads the snapshot response.md files stored in results/vague_a_diff/ and
produces a longitudinal comparison — Vague A baseline → post-B → post-C →
post-sanity → post-D.

No LLM calls. Reads raw saved responses and re-runs the three deterministic
metrics. Output goes to stdout as a markdown table.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from src.eval.metrics_det import score_response


DIFF_DIR = Path("results/vague_a_diff")
CORPUS_PATH = Path("data/processed/formations.json")


# Map of snapshot file → label
SNAPSHOTS = [
    ("responses_vague_a_baseline.md", "Vague A baseline"),
    ("responses_pre_vague_c.md",      "post-Vague B"),
    ("responses_pre_sanity.md",       "post-Vague C"),
    ("responses_pre_insersup.md",     "post-sanity UX α+β"),
    ("responses.md",                  "post-Vague D (current)"),
]


QUESTION_ORDER = ["B1", "A1", "F1", "H1", "E1", "D1"]


def parse_responses_md(path: Path) -> dict[str, str]:
    """Extract per-question responses from the markdown diff format.

    Sections are delimited by `## [category] QID` headers. Response body is
    everything after `### Réponse générée` within that section, up to the
    next `## [` header. The top-level `---` inter-section marker is
    unreliable because LLM responses often contain their own `---` lines.
    """
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    out: dict[str, str] = {}
    # Split on top-level question headers
    sections = re.split(r"^## \[[^\]]+\] (\w+)\s*$", text, flags=re.MULTILINE)
    # sections = [preamble, qid1, body1, qid2, body2, ...]
    for i in range(1, len(sections), 2):
        qid = sections[i].strip()
        body = sections[i + 1] if i + 1 < len(sections) else ""
        m = re.search(
            r"### Réponse générée\s*\n(.*?)(?=\n##\s*\[|\Z)",
            body,
            flags=re.DOTALL,
        )
        if m:
            # Trim a final "---" if present at section end
            resp = m.group(1).strip()
            resp = re.sub(r"\n---\s*$", "", resp).strip()
            out[qid] = resp
    return out


def _avg(values: list[float | int]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def main() -> None:
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    print(f"Corpus: {len(corpus)} fiches loaded\n")

    # Header
    header = (
        f"{'Snapshot':<28} | "
        f"{'B3 avg/6':<10} | "
        f"{'B5 avg/3':<10} | "
        f"{'B6 avg (cit prec)':<20} | "
        f"{'avg words':<10}"
    )
    print(header)
    print("-" * len(header))

    for fname, label in SNAPSHOTS:
        responses = parse_responses_md(DIFF_DIR / fname)
        if not responses:
            print(f"{label:<28} | (no snapshot)")
            continue

        b3_scores: list[float] = []
        b5_scores: list[float] = []
        b6_scores: list[float] = []
        words: list[int] = []

        for qid in QUESTION_ORDER:
            if qid not in responses:
                continue
            r = responses[qid]
            sc = score_response(r, corpus)
            b3_scores.append(sc["actionability"]["score"])
            b5_scores.append(sc["fraicheur"]["score"])
            cp = sc["citation_precision"]["score"]
            if cp is not None:
                b6_scores.append(cp)
            words.append(len(r.split()))

        avg_b3 = _avg(b3_scores)
        avg_b5 = _avg(b5_scores)
        avg_b6 = _avg(b6_scores) if b6_scores else None
        avg_words = _avg(words)

        b6_str = f"{avg_b6:.2f} (n={len(b6_scores)})" if avg_b6 is not None else "— (0 citations)"
        print(
            f"{label:<28} | "
            f"{avg_b3:<10.2f} | "
            f"{avg_b5:<10.2f} | "
            f"{b6_str:<20} | "
            f"{int(avg_words):<10}"
        )


if __name__ == "__main__":
    main()
