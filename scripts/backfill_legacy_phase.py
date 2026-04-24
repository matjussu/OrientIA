"""Back-fill `phase` pour `data/processed/formations.json` (corpus legacy).

Corpus legacy : 1 424 fiches (1 324 Parcoursup + 100 ONISEP) prédatant
ADR-039 (scope élargi avec répartition par phase). Champ `phase`
systématiquement None → bloquant audit qualité pour NO-GO D6.

Mapping adopté :
- `niveau ∈ {"bac+5"}`                 → phase = "master"
- `niveau ∈ {"bac+3", "bac+2", "bac"}` → phase = "initial"
- `niveau in {"cap-bep"}`              → phase = "initial"
- `niveau is None`                     → phase = "initial" par défaut
  (558 fiches Parcoursup concernées : D.E santé, DTS, Certificat de
  Spé, FCIL, CC — toutes post-bac en formation initiale). 1 cas ONISEP
  avec nom mentionnant explicitement "master" → phase = "master".

Pas de phase "reorientation" ici : ce corpus vient d'ingestions
initiales (ParcoursUp post-bac + ONISEP général), la réorientation est
portée par les ingestions LBA ultérieures.

Cf :
- ADR-039 (scope élargi initial/réorientation/master-pro parts égales)
- docs/AUDIT_DATA_QUALITY_2026-04-23.md (bloquant initial)
- docs/AUDIT_DATA_QUALITY_2026-04-24.md (bloquant restant post-fix
  MonMaster)
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


PROCESSED_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "formations.json"


NIVEAU_TO_PHASE = {
    "bac+5": "master",
    "bac+3": "initial",
    "bac+2": "initial",
    "bac": "initial",
    "cap-bep": "initial",
}


_MASTER_HINTS = re.compile(r"\bmaster\b|\bM2\b|\bMBA\b|mastère", re.IGNORECASE)


def infer_phase(fiche: dict[str, Any]) -> str:
    """Détermine `phase` pour une fiche legacy.

    Règles :
    1. `niveau` connu → mapping NIVEAU_TO_PHASE
    2. `nom` contient master/M2/MBA/mastère → "master"
    3. Fallback : "initial" (cas majoritaire pour corpus legacy post-bac)
    """
    niveau = fiche.get("niveau")
    if niveau and niveau in NIVEAU_TO_PHASE:
        return NIVEAU_TO_PHASE[niveau]
    nom = fiche.get("nom") or ""
    if _MASTER_HINTS.search(nom):
        return "master"
    return "initial"


def backfill(fiches: list[dict[str, Any]]) -> dict[str, int]:
    """Remplit `phase` in-place. Retourne un compteur phase pour log."""
    counts: Counter[str] = Counter()
    for f in fiches:
        if f.get("phase"):
            counts[f["phase"]] += 1  # déjà rempli (idempotent)
            continue
        phase = infer_phase(f)
        f["phase"] = phase
        counts[phase] += 1
    return dict(counts)


def main() -> int:
    if not PROCESSED_PATH.exists():
        print(f"[backfill] Fichier absent : {PROCESSED_PATH}", file=sys.stderr)
        return 1
    fiches = json.loads(PROCESSED_PATH.read_text(encoding="utf-8"))
    print(f"[backfill] Chargé {len(fiches)} fiches depuis {PROCESSED_PATH}")
    counts = backfill(fiches)
    PROCESSED_PATH.write_text(
        json.dumps(fiches, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[backfill] Phase distribution après back-fill : {counts}")
    print(f"[backfill] Saved → {PROCESSED_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
