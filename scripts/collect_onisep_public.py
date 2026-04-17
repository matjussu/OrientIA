"""Collect ONISEP fiches via the public endpoint (no credentials required).

Writes data/raw/onisep_formations.json — overwrites the existing snapshot
with the 3-domain version (cyber + data_ia + sante).
"""
import json
from pathlib import Path
from src.collect.onisep import collect_onisep_fiches_public


OUT_PATH = "data/raw/onisep_formations.json"


def main() -> None:
    print(f"Fetching ONISEP via public endpoint (cyber + data_ia + sante)...")
    fiches = collect_onisep_fiches_public()
    print(f"Total unique ONISEP fiches : {len(fiches)}")
    from collections import Counter
    by_domain = Counter(f["domaine"] for f in fiches)
    print(f"Breakdown : {dict(by_domain)}")

    Path(OUT_PATH).parent.mkdir(parents=True, exist_ok=True)
    Path(OUT_PATH).write_text(
        json.dumps(fiches, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Written to {OUT_PATH}")


if __name__ == "__main__":
    main()
