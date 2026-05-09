"""Build des 4 sub-indexes FAISS par groupes de domaines (étape 4 du plan).

Partitionne `data/embeddings/formations.index` (FAISS unifié, 47 214 vecteurs
1024 dims) en 4 sub-indexes selon le champ `domain` des fiches dans
`data/processed/formations_v7.json`.

**Sans re-embedding** : utilise `index.reconstruct(i)` pour extraire les
vecteurs déjà calculés. Coût : $0 (pas d'appel Mistral).

Mapping domain → group :
- formations         : (no domain), formation_insertion, voie_pre_bac
- metiers            : metier, metier_detail, metier_prospective
- statistiques       : insee_salaire, insertion_pro, parcours_bacheliers, apec_region
- aides_territoires  : crous, financement_etudes, territoire_drom,
                       competences_certif, calendrier, correction_factuelle

Exclus (Vague 1.C) : `retrieval_eligible=False` → 18 012 fiches non indexées
(cohérent avec `_build_double_subindices` actuel).

Sortie :
- `data/embeddings/formations_v7_formations.index`     (~145 MB)
- `data/embeddings/formations_v7_metiers.index`        (~20 MB)
- `data/embeddings/formations_v7_statistiques.index`   (~3 MB)
- `data/embeddings/formations_v7_aides_territoires.index` (~20 MB)
- `data/embeddings/formations_partition_manifest.json` (~50 KB)

Usage :
    python scripts/build_quad_subindexes.py [--dry-run] [--validate-only]
        [--source-index PATH] [--source-fiches PATH] [--out-dir DIR]

Modes :
- (default)        : build complet + écriture
- --dry-run        : affiche les stats sans écrire
- --validate-only  : vérifie que les sub-indexes existants matchent
                     le manifest (pour CI / pre-bench)

Cf docs/ADR-065-quad-subindexes-partition.md (à créer).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import faiss
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ────────────────────────── Mapping domain → group ──────────────────────────


DOMAIN_TO_GROUP: dict[str, str] = {
    # formations (incluant l'absence de domain)
    "": "formations",  # str vide → fallback
    "formation_insertion": "formations",
    "voie_pre_bac": "formations",
    # metiers
    "metier": "metiers",
    "metier_detail": "metiers",
    "metier_prospective": "metiers",
    # statistiques
    "insee_salaire": "statistiques",
    "insertion_pro": "statistiques",
    "parcours_bacheliers": "statistiques",
    "apec_region": "statistiques",
    # aides_territoires
    "crous": "aides_territoires",
    "financement_etudes": "aides_territoires",
    "territoire_drom": "aides_territoires",
    "competences_certif": "aides_territoires",
    "calendrier": "aides_territoires",
    "correction_factuelle": "aides_territoires",
}

GROUP_NAMES = ("formations", "metiers", "statistiques", "aides_territoires")


# ────────────────────────── Paths par défaut ──────────────────────────


DEFAULT_SOURCE_INDEX = ROOT / "data" / "embeddings" / "formations.index"
DEFAULT_SOURCE_FICHES = ROOT / "data" / "processed" / "formations_v7.json"
DEFAULT_OUT_DIR = ROOT / "data" / "embeddings"
MANIFEST_NAME = "formations_partition_manifest.json"


# ────────────────────────── Logique partition ──────────────────────────


def _classify_fiche(fiche: dict) -> str | None:
    """Retourne le group d'une fiche, ou None si exclue (retrieval_eligible=False).

    - retrieval_eligible=False → None (exclu, Vague 1.C)
    - domain=None / "" → 'formations'
    - domain dans DOMAIN_TO_GROUP → le group correspondant
    - domain inconnu → 'formations' (fallback safe, log warning)
    """
    if not isinstance(fiche, dict):
        return None
    if fiche.get("retrieval_eligible") is False:
        return None
    domain = fiche.get("domain") or ""
    if domain in DOMAIN_TO_GROUP:
        return DOMAIN_TO_GROUP[domain]
    # Domain inconnu — fallback formations (safer que skip)
    return "formations"


def partition_indices(fiches: list[dict]) -> tuple[
    dict[str, list[int]], list[int], dict[str, int]
]:
    """Calcule la partition fiches → 4 groupes + exclus.

    Returns:
        (group_to_orig_indices, excluded_indices, unknown_domains_count)
    """
    group_to_orig: dict[str, list[int]] = {g: [] for g in GROUP_NAMES}
    excluded: list[int] = []
    unknown_domains: dict[str, int] = {}

    for i, fiche in enumerate(fiches):
        if not isinstance(fiche, dict):
            excluded.append(i)
            continue
        if fiche.get("retrieval_eligible") is False:
            excluded.append(i)
            continue
        domain = fiche.get("domain") or ""
        if domain in DOMAIN_TO_GROUP:
            group_to_orig[DOMAIN_TO_GROUP[domain]].append(i)
        else:
            # Domain inconnu (jamais vu pour v7) → fallback formations + log
            group_to_orig["formations"].append(i)
            unknown_domains[domain] = unknown_domains.get(domain, 0) + 1

    return group_to_orig, excluded, unknown_domains


def build_subindex(
    source_index: faiss.IndexFlatL2,
    orig_indices: list[int],
) -> faiss.IndexFlatL2:
    """Extrait les vecteurs des indices listés via reconstruct() et bâtit
    un nouvel IndexFlatL2 (même dim que la source). Sans re-embedding.
    """
    if not orig_indices:
        return faiss.IndexFlatL2(source_index.d)
    embs = np.array(
        [source_index.reconstruct(int(i)) for i in orig_indices],
        dtype="float32",
    )
    sub = faiss.IndexFlatL2(source_index.d)
    sub.add(embs)
    return sub


# ────────────────────────── Manifest I/O ──────────────────────────


def write_manifest(
    out_dir: Path,
    source_index_path: Path,
    source_fiches_path: Path,
    group_to_orig: dict[str, list[int]],
    excluded: list[int],
    total_fiches: int,
    sub_index_paths: dict[str, Path],
) -> Path:
    """Écrit le manifest JSON décrivant la partition + chemins fichiers."""
    manifest = {
        "version": "v7_quad_index",
        "build_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "source_index": str(source_index_path.relative_to(ROOT)),
        "source_fiches": str(source_fiches_path.relative_to(ROOT)),
        "total_fiches_in_source": total_fiches,
        "excluded_count": len(excluded),
        "exclude_reason": "retrieval_eligible=False (Vague 1.C)",
        "groups": {
            name: {
                "path": str(sub_index_paths[name].relative_to(ROOT)),
                "fiches_count": len(group_to_orig[name]),
                "orig_indices": group_to_orig[name],
            }
            for name in GROUP_NAMES
        },
        "domain_to_group_mapping": DOMAIN_TO_GROUP,
    }
    manifest_path = out_dir / MANIFEST_NAME
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest_path


def load_manifest(out_dir: Path) -> dict:
    return json.loads((out_dir / MANIFEST_NAME).read_text(encoding="utf-8"))


# ────────────────────────── Modes ──────────────────────────


def run_build(
    source_index_path: Path,
    source_fiches_path: Path,
    out_dir: Path,
    dry_run: bool,
) -> int:
    """Build complet (ou dry-run)."""
    if not source_index_path.exists():
        print(f"ERREUR : index source absent : {source_index_path}", file=sys.stderr)
        return 1
    if not source_fiches_path.exists():
        print(f"ERREUR : fiches source absentes : {source_fiches_path}", file=sys.stderr)
        return 1

    print(f"=== Build quad sub-indexes ===")
    print(f"Source index  : {source_index_path}")
    print(f"Source fiches : {source_fiches_path}")
    print(f"Out dir       : {out_dir}")
    print(f"Mode          : {'DRY-RUN' if dry_run else 'BUILD'}")
    print()

    fiches = json.loads(source_fiches_path.read_text(encoding="utf-8"))
    print(f"Loaded {len(fiches)} fiches.")

    if not dry_run:
        source_index = faiss.read_index(str(source_index_path))
        print(f"Loaded FAISS index : {source_index.ntotal} vecteurs, dim={source_index.d}")
        if source_index.ntotal != len(fiches):
            print(
                f"⚠ WARN : index ntotal ({source_index.ntotal}) != fiches "
                f"count ({len(fiches)}). Vérifier la cohérence avant de continuer.",
                file=sys.stderr,
            )

    print()
    group_to_orig, excluded, unknown_domains = partition_indices(fiches)

    print("=== Partition stats ===")
    total_grouped = 0
    for name in GROUP_NAMES:
        count = len(group_to_orig[name])
        pct = 100.0 * count / len(fiches) if fiches else 0
        print(f"  {name:20s} : {count:>6d} fiches ({pct:5.2f}%)")
        total_grouped += count
    print(f"  {'EXCLUS (retrieval_eligible=False)':20s} : {len(excluded):>6d}")
    print(f"  {'TOTAL grouped + excluded':20s} : {total_grouped + len(excluded):>6d}")
    print(f"  {'ATTENDU (= len(fiches))':20s} : {len(fiches):>6d}")

    if total_grouped + len(excluded) != len(fiches):
        print(
            f"\n⚠ ERREUR : somme partition ({total_grouped + len(excluded)}) "
            f"!= len(fiches) ({len(fiches)})",
            file=sys.stderr,
        )
        return 2

    if unknown_domains:
        print(f"\n⚠ Domaines inconnus (fallback formations) :")
        for d, c in sorted(unknown_domains.items(), key=lambda kv: -kv[1]):
            print(f"    {d!r}: {c}")

    if dry_run:
        print("\nDRY-RUN — pas de fichier écrit.")
        return 0

    # Build effectif des 4 sub-indexes
    print("\n=== Build sub-indexes ===")
    out_dir.mkdir(parents=True, exist_ok=True)
    sub_index_paths: dict[str, Path] = {}
    for name in GROUP_NAMES:
        orig_indices = group_to_orig[name]
        if not orig_indices:
            print(f"  {name:20s} : skip (0 fiches)")
            sub_index_paths[name] = out_dir / f"formations_v7_{name}.index"
            continue
        t0 = time.time()
        sub = build_subindex(source_index, orig_indices)
        path = out_dir / f"formations_v7_{name}.index"
        faiss.write_index(sub, str(path))
        size_mb = path.stat().st_size / (1024 * 1024)
        elapsed = time.time() - t0
        print(
            f"  {name:20s} : {len(orig_indices):>6d} vecteurs, "
            f"{size_mb:>6.1f} MB, {elapsed:.1f}s → {path.name}"
        )
        sub_index_paths[name] = path

    # Manifest
    manifest_path = write_manifest(
        out_dir, source_index_path, source_fiches_path,
        group_to_orig, excluded, len(fiches), sub_index_paths,
    )
    print(f"\nManifest écrit : {manifest_path}")

    print("\n=== ✅ BUILD COMPLETE ===")
    return 0


def run_validate(out_dir: Path) -> int:
    """Vérifie que les sub-indexes existants matchent le manifest."""
    manifest_path = out_dir / MANIFEST_NAME
    if not manifest_path.exists():
        print(f"ERREUR : manifest absent : {manifest_path}", file=sys.stderr)
        return 1

    manifest = load_manifest(out_dir)
    print(f"=== Validate from manifest {manifest_path} ===")
    print(f"  version      : {manifest['version']}")
    print(f"  build_date   : {manifest['build_date']}")
    print(f"  total_fiches : {manifest['total_fiches_in_source']}")
    print(f"  excluded     : {manifest['excluded_count']}")
    print()

    all_ok = True
    for name in GROUP_NAMES:
        info = manifest["groups"].get(name, {})
        path = ROOT / info["path"]
        if not path.exists():
            print(f"  ✗ {name:20s} : index absent {path}")
            all_ok = False
            continue
        idx = faiss.read_index(str(path))
        expected = info["fiches_count"]
        if idx.ntotal != expected:
            print(
                f"  ✗ {name:20s} : ntotal={idx.ntotal} mais manifest={expected}"
            )
            all_ok = False
            continue
        size_mb = path.stat().st_size / (1024 * 1024)
        print(
            f"  ✓ {name:20s} : {idx.ntotal:>6d} vecteurs, {size_mb:>6.1f} MB"
        )

    if all_ok:
        print("\n=== ✅ VALIDATE OK ===")
        return 0
    print("\n=== ❌ VALIDATE FAIL ===")
    return 3


# ────────────────────────── CLI ──────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-index",
        type=Path,
        default=DEFAULT_SOURCE_INDEX,
        help="Path FAISS index source (default formations.index).",
    )
    parser.add_argument(
        "--source-fiches",
        type=Path,
        default=DEFAULT_SOURCE_FICHES,
        help="Path JSON fiches source (default formations_v7.json).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="Répertoire de sortie (default data/embeddings/).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Affiche les stats sans écrire les fichiers.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Vérifie que les sub-indexes matchent le manifest existant.",
    )
    args = parser.parse_args()

    if args.validate_only:
        return run_validate(args.out_dir)
    return run_build(
        args.source_index, args.source_fiches, args.out_dir, args.dry_run
    )


if __name__ == "__main__":
    sys.exit(main())
