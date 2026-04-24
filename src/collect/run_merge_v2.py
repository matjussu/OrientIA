"""Runner v2 — pipeline scope élargi ADR-039.

Produit `data/processed/formations.json` en agrégeant TOUTES les sources
disponibles :
- Parcoursup CSV raw + ONISEP JSON raw → fuzzy merger legacy
- Parcoursup extended (pré-normalisé)
- ONISEP extended (pré-normalisé)
- MonMaster (dédupliqué ADR-044)
- RNCP certifications
- LBA formations (phase réorientation)
- Céreq insertion stats (enrichissement par niveau × domaine)

Les sources manquantes sont gracieusement sautées (no-op). Re-run après
ajout de nouvelles ingestions pour rafraîchir le corpus v2.

Usage :
    python -m src.collect.run_merge_v2

Variables d'environnement :
    ORIENTIA_MERGE_OUT_PATH  : path override (défaut data/processed/formations.json)
"""
from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path
from typing import Any

from src.collect.insersup import attach_insertion
from src.collect.merge import attach_debouches, attach_metadata, merge_all_extended
from src.collect.parcoursup import collect_parcoursup_fiches
from src.collect.secnumedu import load_secnumedu
from src.collect.trends import attach_trends


DATA_RAW = Path("data/raw")
DATA_PROCESSED = Path("data/processed")
DEFAULT_OUT_PATH = DATA_PROCESSED / "formations.json"


def _load_json_if_available(path: Path, label: str) -> list[dict[str, Any]]:
    """Charge un JSON liste, gracieusement vide si absent/malformé."""
    if not path.exists():
        print(f"  [skip] {label}: {path} absent")
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            print(f"  [skip] {label}: {path} n'est pas une liste")
            return []
        return data
    except (json.JSONDecodeError, OSError) as e:
        print(f"  [skip] {label}: erreur lecture {path} ({e})")
        return []


def _load_secnumedu_if_available(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        print(f"  [skip] secnumedu: {path} absent")
        return []
    try:
        return load_secnumedu(path)
    except (OSError, ValueError) as e:
        print(f"  [skip] secnumedu: {e}")
        return []


def _load_parcoursup_raw_if_available(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        print(f"  [skip] parcoursup CSV: {path} absent")
        return []
    try:
        return collect_parcoursup_fiches(str(path))
    except (OSError, ValueError) as e:
        print(f"  [skip] parcoursup CSV: {e}")
        return []


def main() -> int:
    print("Pipeline merge v2 — scope élargi ADR-039")
    print()

    # Sources raw (fuzzy merger legacy)
    print("Chargement sources raw (fuzzy merger Parcoursup × ONISEP) :")
    parcoursup_raw = _load_parcoursup_raw_if_available(DATA_RAW / "parcoursup_2025.csv")
    onisep_raw = _load_json_if_available(DATA_RAW / "onisep_formations.json", "onisep raw")
    secnumedu_raw = _load_secnumedu_if_available(DATA_RAW / "secnumedu.json")
    print(f"  parcoursup raw  : {len(parcoursup_raw)}")
    print(f"  onisep raw      : {len(onisep_raw)}")
    print(f"  secnumedu raw   : {len(secnumedu_raw)}")

    # Sources pré-normalisées (scope élargi)
    print()
    print("Chargement sources pré-normalisées (scope élargi) :")
    parcoursup_ext = _load_json_if_available(DATA_PROCESSED / "parcoursup_extended.json", "parcoursup_extended")
    onisep_ext = _load_json_if_available(DATA_PROCESSED / "onisep_formations_extended.json", "onisep_extended")
    monmaster = _load_json_if_available(DATA_PROCESSED / "monmaster_formations.json", "monmaster")
    rncp = _load_json_if_available(DATA_PROCESSED / "rncp_certifications.json", "rncp")
    lba = _load_json_if_available(DATA_PROCESSED / "lba_formations.json", "lba")
    cereq = _load_json_if_available(DATA_PROCESSED / "cereq_insertion_stats.json", "cereq")
    inserjeunes_cfa = _load_json_if_available(
        DATA_PROCESSED / "inserjeunes_cfa.json", "inserjeunes_cfa"
    )
    print(f"  parcoursup_ext  : {len(parcoursup_ext)}")
    print(f"  onisep_ext      : {len(onisep_ext)}")
    print(f"  monmaster       : {len(monmaster)}")
    print(f"  rncp            : {len(rncp)}")
    print(f"  lba             : {len(lba)}")
    print(f"  cereq stats     : {len(cereq)}")
    print(f"  inserjeunes_cfa : {len(inserjeunes_cfa)}")

    # Manual labels (si présent)
    manual_labels: list[dict[str, Any]] = []
    manual_path = Path("data/manual_labels.json")
    if manual_path.exists():
        manual_data = json.loads(manual_path.read_text(encoding="utf-8"))
        manual_labels = manual_data.get("entries", [])
    print(f"  manual_labels   : {len(manual_labels)}")

    # Merge global
    print()
    print("Merge global via `merge_all_extended()` …")
    merged = merge_all_extended(
        parcoursup=parcoursup_raw,
        onisep=onisep_raw,
        secnumedu=secnumedu_raw,
        monmaster=monmaster,
        rncp=rncp,
        cereq=cereq,
        parcoursup_extended=parcoursup_ext,
        onisep_extended=onisep_ext,
        lba=lba,
        inserjeunes_cfa=inserjeunes_cfa,
        manual_labels=manual_labels,
    )
    print(f"  merged total    : {len(merged)} fiches")

    # Tendances & insertion (si CSVs historiques présents)
    merged = attach_trends(merged, {
        2023: str(DATA_RAW / "parcoursup_2023.csv"),
        2024: str(DATA_RAW / "parcoursup_2024.csv"),
        2025: str(DATA_RAW / "parcoursup_2025.csv"),
    })
    merged = attach_insertion(merged, str(DATA_RAW / "insersup.csv"))

    # Stats de sortie
    print()
    print("Distribution fiches enrichies :")
    phase_counts = Counter(f.get("phase") for f in merged)
    source_counts = Counter(f.get("source") for f in merged)
    with_debouches = sum(1 for f in merged if f.get("debouches"))
    with_insertion_pro = sum(1 for f in merged if f.get("insertion_pro"))
    with_insertion_dares = sum(1 for f in merged if f.get("insertion"))
    with_trends = sum(1 for f in merged if f.get("trends"))
    print(f"  par phase       : {dict(phase_counts)}")
    print(f"  par source      : {dict(source_counts)}")
    print(f"  avec debouches  : {with_debouches}")
    print(f"  avec insertion_pro (Céreq) : {with_insertion_pro}")
    print(f"  avec insertion (InserSup)  : {with_insertion_dares}")
    print(f"  avec trends     : {with_trends}")

    # Écriture
    out_path = Path(os.environ.get("ORIENTIA_MERGE_OUT_PATH", DEFAULT_OUT_PATH))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print()
    print(f"Saved {len(merged)} fiches → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
