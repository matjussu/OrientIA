"""Sprint 12 D5 — enrichissement formations_unified.json avec InserSup MESR.

Référence ordre : 2026-05-01-1659-claudette-orientia-sprint12-D5-inserjeunes-insersup-data-gouv (S3).

Wire `attach_to_insertion_pro` (insersup.py Sprint 12 D5) sur le corpus
existant. Sortie : audit % match par niveau + corpus enrichi sauvegardé.

Stratégie :
- Charge `data/processed/formations_unified.json`
- Run `attach_to_insertion_pro(fiches, csv_path='data/raw/insersup.csv')`
- Sauvegarde le résultat (overwrite formations_unified.json) + audit_stats
- Imprime distribution des sources insertion_pro post-enrichissement

Politique d'overwrite : InserSup > Céreq pour les fiches niveau master/LP/DUT
(plus granulaire, source officielle MESR par établissement). Tracé dans
audit_stats {overwritten_cereq, overwritten_cfa}.

Usage :
    PYTHONPATH=. python3 scripts/enrich_with_insersup_d5.py

Threshold spec ordre : si match RNCP <30 % des fiches corpus → flag pour
discussion. Adapté UAI : si match <30 % des fiches niveau univ master/LP/
DUT → flag.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from src.collect.insersup import attach_to_insertion_pro


ROOT = Path(__file__).resolve().parents[1]
FORMATIONS_PATH = ROOT / "data" / "processed" / "formations_unified.json"
INSERSUP_CSV = ROOT / "data" / "raw" / "insersup.csv"
BACKUP_PATH = ROOT / "data" / "processed" / "formations_unified.pre_d5_backup.json"


def _is_university_level(fiche: dict) -> bool:
    """Heuristique : niveau master/LP/DUT (universitaire) où InserSup
    a couverture pertinente."""
    type_d_raw = fiche.get("type_diplome") or ""
    niveau_raw = fiche.get("niveau") or ""
    type_d = str(type_d_raw).lower()
    niveau = str(niveau_raw).lower()
    keywords = ("master", "licence", "but", "dut")
    return any(k in type_d for k in keywords) or any(k in niveau for k in keywords)


def main() -> int:
    print(f"[D5] loading corpus : {FORMATIONS_PATH}")
    with FORMATIONS_PATH.open(encoding="utf-8") as f:
        fiches = json.load(f)
    n_total = len(fiches)
    print(f"[D5] {n_total} formations chargées")

    # Snapshot pré-enrichissement (pour audit overwrite vs new)
    pre_sources = Counter()
    for f in fiches:
        ip = f.get("insertion_pro")
        if isinstance(ip, dict):
            pre_sources[ip.get("source") or "unknown"] += 1
    n_pre_with_ip = sum(pre_sources.values())
    print(f"[D5] PRE  : insertion_pro = {n_pre_with_ip}/{n_total} = {100*n_pre_with_ip/n_total:.1f}%")
    print(f"[D5] PRE  : sources distribution = {dict(pre_sources)}")

    # Backup si pas déjà fait (idempotent re-run)
    if not BACKUP_PATH.exists():
        print(f"[D5] backup pré-enrichissement → {BACKUP_PATH.name}")
        BACKUP_PATH.write_text(
            json.dumps(fiches, ensure_ascii=False), encoding="utf-8"
        )
    else:
        print(f"[D5] backup déjà présent (re-run safe), skip")

    # Run enrichissement
    print(f"[D5] enrichissement en cours via attach_to_insertion_pro...")
    fiches, audit = attach_to_insertion_pro(fiches, INSERSUP_CSV)

    # Audit % match par niveau
    n_univ = sum(1 for f in fiches if _is_university_level(f))
    print(f"\n[D5] audit_stats : {audit}")
    print(f"[D5] fiches univ (master/LP/DUT/licence) : {n_univ}")
    if n_univ > 0:
        match_rate_univ = audit["matched"] / n_univ
        print(f"[D5] match rate univ : {audit['matched']}/{n_univ} = {100*match_rate_univ:.1f}%")
        if match_rate_univ < 0.30:
            print(f"[D5] ⚠️ THRESHOLD : match univ <30% → flag à Jarvis pour discussion")
        else:
            print(f"[D5] ✅ THRESHOLD : match univ ≥30% acceptable")

    # Distribution sources post-enrichissement
    post_sources = Counter()
    for f in fiches:
        ip = f.get("insertion_pro")
        if isinstance(ip, dict):
            post_sources[ip.get("source") or "unknown"] += 1
    n_post_with_ip = sum(post_sources.values())
    print(f"\n[D5] POST : insertion_pro = {n_post_with_ip}/{n_total} = {100*n_post_with_ip/n_total:.1f}%")
    print(f"[D5] POST : sources distribution = {dict(post_sources)}")

    delta_pp = 100 * (n_post_with_ip - n_pre_with_ip) / n_total
    print(f"[D5] Δ coverage absolue : +{delta_pp:.1f}pp ({n_post_with_ip - n_pre_with_ip} fiches +)")
    print(f"[D5] overwrites : {audit['overwritten_cereq']} cereq, {audit['overwritten_cfa']} cfa")
    print(f"[D5] net unique add : {audit['matched'] - audit['overwritten_cereq'] - audit['overwritten_cfa']}")

    # Sauvegarde
    print(f"\n[D5] saving enriched corpus → {FORMATIONS_PATH}")
    with FORMATIONS_PATH.open("w", encoding="utf-8") as f:
        json.dump(fiches, f, ensure_ascii=False)
    print(f"[D5] done")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
