"""Runner that executes the full merge pipeline and writes data/processed/formations.json.

Consumes: Parcoursup CSV, ONISEP JSON (if available), SecNumEdu JSON.
Produces: data/processed/formations.json (committed, not gitignored).

ONISEP data is optional — if data/raw/onisep_formations.json doesn't exist
or is unreadable, runs with an empty list. The merge still produces a valid
output using Parcoursup fiches with SecNumEdu labels attached. Re-run after
ONISEP data becomes available to add type_diplome / url_onisep enrichment.
"""
import json
from pathlib import Path
from collections import Counter
from src.collect.parcoursup import collect_parcoursup_fiches
from src.collect.secnumedu import load_secnumedu
from src.collect.merge import merge_all


def _load_onisep_if_available(path: str | Path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        print(f"ONISEP data not found at {p}, proceeding with empty list")
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"Failed to load ONISEP data from {p}: {e}; proceeding with empty list")
        return []


def main():
    parcoursup_fiches = collect_parcoursup_fiches("data/raw/parcoursup_2025.csv")
    onisep_fiches = _load_onisep_if_available("data/raw/onisep_formations.json")
    secnumedu_fiches = load_secnumedu("data/raw/secnumedu.json")

    print(f"Parcoursup input: {len(parcoursup_fiches)}")
    print(f"ONISEP input:     {len(onisep_fiches)}")
    print(f"SecNumEdu input:  {len(secnumedu_fiches)}")

    merged = merge_all(parcoursup_fiches, onisep_fiches, secnumedu_fiches)
    print(f"Merged output:    {len(merged)}")

    method_counts = Counter(f.get("match_method", "unknown") for f in merged)
    print(f"Match methods:    {dict(method_counts)}")

    labelled = sum(1 for f in merged if f.get("labels"))
    secnumedu_labelled = sum(1 for f in merged if "SecNumEdu" in (f.get("labels") or []))
    print(f"With any label:   {labelled}")
    print(f"With SecNumEdu:   {secnumedu_labelled}")

    statut_counts = Counter(f.get("statut") for f in merged)
    print(f"Statut breakdown: {dict(statut_counts)}")

    out_path = Path("data/processed/formations.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
