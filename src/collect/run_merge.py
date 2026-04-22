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
from src.collect.merge import merge_all, attach_debouches, attach_metadata
from src.collect.trends import attach_trends
from src.collect.insersup import attach_insertion



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


def _load_secnumedu_if_available(path: str | Path) -> list[dict]:
    """Cohérent avec `_load_onisep_if_available` — graceful no-op si fichier
    absent (workflow GHA D7 : fixture committée mais defensive si supprimée)."""
    p = Path(path)
    if not p.exists():
        print(f"SecNumEdu data not found at {p}, proceeding with empty list")
        return []
    try:
        return load_secnumedu(p)
    except (OSError, ValueError) as e:
        print(f"Failed to load SecNumEdu data from {p}: {e}; proceeding with empty list")
        return []


def main():
    parcoursup_fiches = collect_parcoursup_fiches("data/raw/parcoursup_2025.csv")
    onisep_fiches = _load_onisep_if_available("data/raw/onisep_formations.json")
    secnumedu_fiches = _load_secnumedu_if_available("data/raw/secnumedu.json")

    # NEW: load manual labels table
    manual_labels_path = Path("data/manual_labels.json")
    if manual_labels_path.exists():
        manual_data = json.loads(manual_labels_path.read_text(encoding="utf-8"))
        manual_labels = manual_data.get("entries", [])
    else:
        manual_labels = []
    print(f"Manual labels:   {len(manual_labels)}")

    print(f"Parcoursup input: {len(parcoursup_fiches)}")
    print(f"ONISEP input:     {len(onisep_fiches)}")
    print(f"SecNumEdu input:  {len(secnumedu_fiches)}")

    merged = merge_all(parcoursup_fiches, onisep_fiches, secnumedu_fiches, manual_labels=manual_labels)
    print(f"Merged output:    {len(merged)}")

    # Vague A — post-merge enrichment pipeline (integrated in-repo,
    # was previously an out-of-pipeline one-off)
    merged = attach_debouches(merged)
    merged = attach_metadata(merged)
    with_debouches = sum(1 for f in merged if f.get("debouches"))
    print(f"With debouches:   {with_debouches}")

    # Vague C — historical trends (2023/2024/2025) joined by cod_aff_form.
    # Gracefully skipped if historical CSVs are missing.
    merged = attach_trends(merged, {
        2023: "data/raw/parcoursup_2023.csv",
        2024: "data/raw/parcoursup_2024.csv",
        2025: "data/raw/parcoursup_2025.csv",
    })
    with_hist = sum(1 for f in merged if (f.get("admission") or {}).get("historique"))
    with_trend = sum(1 for f in merged if f.get("trends"))
    print(f"With historique:  {with_hist}")
    print(f"With trends:      {with_trend}")

    # Vague D — InserSup insertion pro (joined by cod_uai, discipline preferred,
    # then type_diplome aggregate fallback). Graceful no-op if CSV missing.
    merged = attach_insertion(merged, "data/raw/insersup.csv")
    with_insertion = sum(1 for f in merged if f.get("insertion"))
    print(f"With insertion:   {with_insertion}")

    method_counts = Counter(f.get("match_method", "unknown") for f in merged)
    print(f"Match methods:    {dict(method_counts)}")

    labelled = sum(1 for f in merged if f.get("labels"))
    secnumedu_labelled = sum(1 for f in merged if "SecNumEdu" in (f.get("labels") or []))
    print(f"With any label:   {labelled}")
    print(f"With SecNumEdu:   {secnumedu_labelled}")

    statut_counts = Counter(f.get("statut") for f in merged)
    print(f"Statut breakdown: {dict(statut_counts)}")

    niveau_counts = Counter(f.get("niveau") for f in merged)
    print(f"Niveau breakdown: {dict(niveau_counts)}")

    label_counts = Counter()
    for f in merged:
        for l in (f.get("labels") or []):
            label_counts[l] += 1
    print(f"Label breakdown:  {dict(label_counts)}")

    out_path = Path("data/processed/formations.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
