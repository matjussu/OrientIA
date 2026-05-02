#!/usr/bin/env python3
"""Sprint 12 axe 2 — Corpus combined assembly Golden Pipeline.

Assemble les 3 corpora utilisés en parallèle dans la stack Sprint 9-12 :

- ``data/processed/formations_unified.json`` (~55 606 fiches Parcoursup-style
  avec ``profil_admis`` Sprint 12 D1 exposé au RAG)
- ``data/processed/dares_corpus.json`` (~1 160 entrées métiers prospectifs
  DARES Métiers 2030, granularité ``fap`` / ``fap×region`` / ``region``)
- ``data/processed/france_comp_blocs_corpus.json`` (~4 891 fiches RNCP avec
  blocs de compétences, voies d'accès, codes ROME/NSF)

Output : ``data/processed/formations_golden_pipeline.json`` (~61 657 entrées).

Discriminateur ajouté : champ ``corpus`` macro
(``formations_unified`` | ``dares`` | ``rncp_blocs``) qui permet à
``corpus_item_to_text()`` (cf. ``src/rag/embeddings.py``) de router chaque
item vers son formatter natif.

Le champ ``corpus`` ne collisionne pas avec le champ ``source`` existant :
``formations_unified`` items portent ``source='parcoursup'`` (granulaire),
``dares`` portent ``source='dares_metiers_2030'``, ``rncp_blocs`` portent
``source='rncp_blocs'``. ``corpus`` est la macro-catégorie discriminante.

Usage:
    python scripts/build_formations_golden_corpus.py [--out PATH]

Plan : ``docs/GOLDEN_PIPELINE_PLAN.md`` étape 1.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_FORMATIONS_UNIFIED = REPO_ROOT / "data" / "processed" / "formations_unified.json"
DEFAULT_DARES = REPO_ROOT / "data" / "processed" / "dares_corpus.json"
DEFAULT_RNCP = REPO_ROOT / "data" / "processed" / "france_comp_blocs_corpus.json"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "processed" / "formations_golden_pipeline.json"

CORPUS_LABELS = ("formations_unified", "dares", "rncp_blocs")


def load_corpus(path: Path) -> list[dict[str, Any]]:
    """Charge un corpus JSON (liste d'objets). Lève si fichier absent ou format invalide."""
    if not path.exists():
        raise FileNotFoundError(f"corpus introuvable : {path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(
            f"{path} doit être une liste JSON, reçu {type(data).__name__}"
        )
    return data


def annotate_corpus(items: Iterable[dict], corpus_label: str) -> list[dict]:
    """Ajoute le champ ``corpus`` discriminant à chaque item.

    Idempotent : un item déjà annoté avec le même ``corpus_label`` est laissé
    tel quel. Lève si annoté avec un label différent (état incohérent).

    Ne mute jamais l'item d'entrée (copie superficielle).
    """
    if corpus_label not in CORPUS_LABELS:
        raise ValueError(
            f"corpus_label={corpus_label!r} non supporté, attendu un de {CORPUS_LABELS}"
        )

    annotated = []
    for item in items:
        existing = item.get("corpus")
        if existing is not None and existing != corpus_label:
            raise ValueError(
                f"item id={item.get('id')!r} a déjà corpus={existing!r}, "
                f"incompatible avec {corpus_label!r}"
            )
        new_item = dict(item)
        new_item["corpus"] = corpus_label
        annotated.append(new_item)
    return annotated


def build_combined(
    formations_unified: list[dict],
    dares: list[dict],
    rncp_blocs: list[dict],
) -> list[dict]:
    """Assemble les 3 corpora annotés en une liste combinée."""
    return (
        annotate_corpus(formations_unified, "formations_unified")
        + annotate_corpus(dares, "dares")
        + annotate_corpus(rncp_blocs, "rncp_blocs")
    )


def write_combined(combined: list[dict], out_path: Path) -> None:
    """Écrit le corpus combiné en JSON compact UTF-8."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, separators=(",", ":"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--formations-unified", type=Path, default=DEFAULT_FORMATIONS_UNIFIED)
    parser.add_argument("--dares", type=Path, default=DEFAULT_DARES)
    parser.add_argument("--rncp-blocs", type=Path, default=DEFAULT_RNCP)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    print(f"Loading {args.formations_unified}…", flush=True)
    fu = load_corpus(args.formations_unified)
    print(f"  {len(fu):,} fiches formations_unified")

    print(f"Loading {args.dares}…", flush=True)
    dares = load_corpus(args.dares)
    print(f"  {len(dares):,} entrées DARES")

    print(f"Loading {args.rncp_blocs}…", flush=True)
    rncp = load_corpus(args.rncp_blocs)
    print(f"  {len(rncp):,} fiches RNCP blocs")

    combined = build_combined(fu, dares, rncp)
    print(f"\nTotal combined : {len(combined):,} entrées")

    counts = {label: sum(1 for it in combined if it.get("corpus") == label) for label in CORPUS_LABELS}
    print(f"  Breakdown : {counts}")

    write_combined(combined, args.out)
    print(f"\nWrote → {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
