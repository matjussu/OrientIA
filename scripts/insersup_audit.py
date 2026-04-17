"""InserSup integration audit — generate a report BEFORE merging data.

Per the data-integrity zero-tolerance rule (memory/feedback_data_integrity…),
we audit every new source: coverage, confidence distribution, suspicious
outliers, and manual spot-checks.

Usage:
    python -m scripts.insersup_audit

Outputs:
    results/insersup_audit.md — report for Matteo review
"""
from __future__ import annotations

import json
from pathlib import Path
from collections import Counter

from src.collect.insersup import (
    load_insersup_aggregated,
    attach_insertion,
    _match_fiche_to_insersup,
)


FICHES_PATH = "data/processed/formations.json"
INSERSUP_PATH = "data/raw/insersup.csv"
OUT_PATH = "results/insersup_audit.md"


def main() -> None:
    fiches = json.loads(Path(FICHES_PATH).read_text(encoding="utf-8"))
    print(f"Loaded {len(fiches)} fiches")
    print(f"Loading InserSup CSV (big — wait ~30s)...")
    idx = load_insersup_aggregated(INSERSUP_PATH)
    print(f"InserSup index: {len(idx)} (uai, type, libelle) triples indexed")

    # Dry-run match without mutating fiches
    stats = {
        "total_fiches": len(fiches),
        "with_cod_uai": 0,
        "without_cod_uai": 0,
        "matched_discipline": 0,
        "matched_aggregate": 0,
        "unmatched_with_uai": 0,
    }
    matched_samples = {"discipline": [], "type_diplome_agrege": []}
    uai_present = set()
    uai_missing_in_insersup = set()

    for fiche in fiches:
        uai = (fiche.get("cod_uai") or "").strip()
        if not uai:
            stats["without_cod_uai"] += 1
            continue
        stats["with_cod_uai"] += 1
        snap, gran = _match_fiche_to_insersup(fiche, idx)
        if snap is None:
            stats["unmatched_with_uai"] += 1
            # Check whether UAI itself is present in InserSup at all
            has_uai_in_insersup = any(k[0] == uai for k in idx.keys())
            if not has_uai_in_insersup:
                uai_missing_in_insersup.add(uai)
            continue
        if gran == "discipline":
            stats["matched_discipline"] += 1
            if len(matched_samples["discipline"]) < 15:
                matched_samples["discipline"].append({
                    "nom": fiche.get("nom"),
                    "etablissement": fiche.get("etablissement"),
                    "niveau": fiche.get("niveau"),
                    "cod_uai": uai,
                    "domaine": fiche.get("domaine"),
                    "taux_emploi_12m": snap.get("taux_emploi_12m"),
                    "salaire_median_12m": snap.get("salaire_median_12m_mensuel_net"),
                    "cohorte": snap.get("cohorte"),
                    "nombre_sortants": snap.get("nombre_sortants"),
                })
        else:
            stats["matched_aggregate"] += 1
            if len(matched_samples["type_diplome_agrege"]) < 15:
                matched_samples["type_diplome_agrege"].append({
                    "nom": fiche.get("nom"),
                    "etablissement": fiche.get("etablissement"),
                    "niveau": fiche.get("niveau"),
                    "cod_uai": uai,
                    "domaine": fiche.get("domaine"),
                    "taux_emploi_12m": snap.get("taux_emploi_12m"),
                    "salaire_median_12m": snap.get("salaire_median_12m_mensuel_net"),
                    "cohorte": snap.get("cohorte"),
                    "nombre_sortants": snap.get("nombre_sortants"),
                })

    # Detect outliers: taux_emploi outside [0, 1] and salaire suspect
    matched_fiches = attach_insertion(list(fiches), INSERSUP_PATH)
    outliers = []
    for f in matched_fiches:
        ins = f.get("insertion")
        if not ins:
            continue
        taux = ins.get("taux_emploi_12m")
        if taux is not None and (taux < 0 or taux > 1):
            outliers.append({"nom": f.get("nom"), "etab": f.get("etablissement"),
                            "issue": f"taux_emploi_12m={taux} hors [0,1]"})
        sal = ins.get("salaire_median_12m_mensuel_net")
        if sal is not None and (sal < 500 or sal > 8000):
            outliers.append({"nom": f.get("nom"), "etab": f.get("etablissement"),
                            "issue": f"salaire_median_12m={sal}€ suspect"})

    # Build the report
    md: list[str] = [
        "# InserSup integration audit",
        "",
        f"**Source** : `{INSERSUP_PATH}` + `{FICHES_PATH}`",
        f"**InserSup index size** : {len(idx)} triples (uai, type_diplome, libelle)",
        "",
        "## Coverage",
        "",
        f"| Metric                          | Count | % of total |",
        f"|---------------------------------|-------|------------|",
        f"| Total fiches                    | {stats['total_fiches']} | 100% |",
        f"| With cod_uai                    | {stats['with_cod_uai']} | "
        f"{stats['with_cod_uai']/stats['total_fiches']*100:.1f}% |",
        f"| Without cod_uai (ONISEP-only)   | {stats['without_cod_uai']} | "
        f"{stats['without_cod_uai']/stats['total_fiches']*100:.1f}% |",
        f"| Matched at **discipline** level | {stats['matched_discipline']} | "
        f"{stats['matched_discipline']/stats['total_fiches']*100:.1f}% |",
        f"| Matched at aggregate level      | {stats['matched_aggregate']} | "
        f"{stats['matched_aggregate']/stats['total_fiches']*100:.1f}% |",
        f"| Unmatched (UAI present)         | {stats['unmatched_with_uai']} | "
        f"{stats['unmatched_with_uai']/stats['total_fiches']*100:.1f}% |",
        "",
        f"UAI absent from InserSup entirely : {len(uai_missing_in_insersup)} "
        f"distinct establishments.",
        "",
        "## Discipline-level matched samples (spot-check these !)",
        "",
        "| Établissement | Formation | Niveau | Taux emploi 12m | Salaire médian 12m | Cohorte | N sortants |",
        "|---|---|---|---|---|---|---|",
    ]
    for s in matched_samples["discipline"]:
        taux = f"{s['taux_emploi_12m']*100:.0f}%" if s['taux_emploi_12m'] is not None else "nd"
        sal = f"{s['salaire_median_12m']}€" if s['salaire_median_12m'] is not None else "nd"
        md.append(
            f"| {s['etablissement']} | {s['nom'][:60]} | {s['niveau']} | "
            f"{taux} | {sal} | {s['cohorte']} | {s['nombre_sortants']} |"
        )

    md.extend([
        "",
        "## Aggregate-level matched samples (less specific — spot-check too)",
        "",
        "| Établissement | Formation | Niveau | Taux emploi 12m | Salaire médian 12m | Cohorte | N sortants |",
        "|---|---|---|---|---|---|---|",
    ])
    for s in matched_samples["type_diplome_agrege"]:
        taux = f"{s['taux_emploi_12m']*100:.0f}%" if s['taux_emploi_12m'] is not None else "nd"
        sal = f"{s['salaire_median_12m']}€" if s['salaire_median_12m'] is not None else "nd"
        md.append(
            f"| {s['etablissement']} | {s['nom'][:60]} | {s['niveau']} | "
            f"{taux} | {sal} | {s['cohorte']} | {s['nombre_sortants']} |"
        )

    md.extend([
        "",
        "## Outliers detected",
        "",
    ])
    if outliers:
        md.append("⚠️ Suspicious values detected — MUST be reviewed before merging :")
        for o in outliers[:20]:
            md.append(f"- {o['etab']} — {o['nom'][:80]} : {o['issue']}")
    else:
        md.append("✅ No outliers detected (all taux in [0,1], all salaires in [500€, 8000€]).")

    md.extend([
        "",
        "## Manual verification checklist",
        "",
        "Before this audit is accepted, **manually verify 3-5 of the **discipline-level** samples above**:",
        "",
        "1. Open the ESR / establishment website for each sample",
        "2. Check that the taux d'emploi 12m and salaire médian we extracted match what is published officially",
        "3. If any sample is off by more than a few percentage points → STOP, investigate before merging",
        "",
        "Source officielle à vérifier :",
        "- https://data.enseignementsup-recherche.gouv.fr/explore/dataset/fr-esr-insersup/table/",
        "- https://www.data.gouv.fr/datasets/insertion-professionnelle-des-diplomes-des-etablissements-denseignement-superieur-dispositif-insersup",
    ])

    Path(OUT_PATH).parent.mkdir(parents=True, exist_ok=True)
    Path(OUT_PATH).write_text("\n".join(md), encoding="utf-8")
    print(f"Audit written to {OUT_PATH}")
    print()
    print("=== Summary ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print(f"  outliers detected: {len(outliers)}")


if __name__ == "__main__":
    main()
