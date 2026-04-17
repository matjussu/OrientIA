"""Audit the santé domain extension.

Reports coverage (total fiches, by niveau, with insertion, labels), lists
10 random samples for manual verification, and flags any data integrity
issues per the zero-tolerance rule.
"""
from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path


def main() -> None:
    fiches = json.loads(Path("data/processed/formations.json").read_text(encoding="utf-8"))
    sante = [f for f in fiches if f.get("domaine") == "sante"]
    print(f"Santé fiches: {len(sante)} / {len(fiches)} total "
          f"({len(sante)/len(fiches)*100:.1f}%)")

    # Breakdown by niveau
    niveau_counter = Counter(f.get("niveau") or "None" for f in sante)
    print(f"\nNiveau distribution:")
    for n in sorted(niveau_counter):
        print(f"  {n}: {niveau_counter[n]}")

    # Breakdown by type_diplome
    td_counter = Counter(f.get("type_diplome") or "absent" for f in sante)
    print(f"\nType_diplome top 15:")
    for t, n in td_counter.most_common(15):
        print(f"  {t[:60]}: {n}")

    # Insertion coverage
    with_insertion = [f for f in sante if f.get("insertion")]
    print(f"\nWith insertion: {len(with_insertion)} / {len(sante)} "
          f"({len(with_insertion)/len(sante)*100:.1f}%)")
    gran_counter = Counter((f.get("insertion") or {}).get("granularite")
                           for f in with_insertion)
    print(f"  granularité: {dict(gran_counter)}")

    # Trends coverage
    with_trends = [f for f in sante if f.get("trends")]
    print(f"\nWith trends: {len(with_trends)} / {len(sante)}")

    # Labels
    labels_count = Counter()
    for f in sante:
        for l in f.get("labels") or []:
            labels_count[l] += 1
    print(f"\nLabels: {dict(labels_count) if labels_count else 'none'}")

    # Sample 10 fiches for manual verification
    random.seed(42)
    samples = random.sample(sante, min(10, len(sante)))
    print(f"\n=== 10 random sample fiches (manual spot-check) ===")
    for i, f in enumerate(samples, 1):
        ins = f.get("insertion") or {}
        print(f"\n{i}. {f.get('nom', '?')[:90]}")
        print(f"   Établissement : {f.get('etablissement', '')[:70]}")
        print(f"   Ville / niveau : {f.get('ville', '?')} / {f.get('niveau', 'None')}")
        print(f"   cod_uai : {f.get('cod_uai', 'absent')} | cod_aff_form : {f.get('cod_aff_form', 'absent')}")
        if ins:
            taux = ins.get("taux_emploi_12m")
            sal = ins.get("salaire_median_12m_mensuel_net")
            print(f"   Insertion ({ins.get('granularite')}): "
                  f"taux_12m={taux}, salaire_12m={sal}€, cohorte={ins.get('cohorte')}")

    # Outliers check
    outliers = []
    for f in with_insertion:
        ins = f["insertion"]
        taux = ins.get("taux_emploi_12m")
        sal = ins.get("salaire_median_12m_mensuel_net")
        if taux is not None and (taux < 0 or taux > 1):
            outliers.append(f"  {f['nom'][:60]}: taux_12m={taux}")
        if sal is not None and (sal < 500 or sal > 8000):
            outliers.append(f"  {f['nom'][:60]}: salaire_12m={sal}€")
    if outliers:
        print(f"\n⚠️ Outliers detected ({len(outliers)}):")
        for o in outliers[:10]:
            print(o)
    else:
        print(f"\n✅ No outliers — all taux in [0,1], salaires in [500€, 8000€]")


if __name__ == "__main__":
    main()
