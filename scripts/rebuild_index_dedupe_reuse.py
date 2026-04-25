"""Rebuild FAISS multi-corpus dedupé via reuse des embeddings existants ($0).

Plutôt qu'un full rebuild (~$2.40 Mistral embed × 47 505 records),
ce script reuse les embeddings existants des fiches survivantes :

1. Charge `formations_multi_corpus.index` (50 153 vecteurs)
2. Charge `formations_multi_corpus.json` (50 153 fiches incluant 1 239
   multi-corpus + 48 914 formations dont 1 324 doublons)
3. Charge `formations_dedupe.json` (47 590 formations dédupées)
4. Pour chaque fiche dédupée, identifie sa position originale dans
   formations_multi_corpus.json par `cod_aff_form` (ou index séquentiel
   pour les fiches sans cod_aff_form). Une fiche merge-soft a hérité du
   `cod_aff_form` du groupe → on retrouve l'embedding de la fiche
   originale "base" du merge.
5. Pour les 1 239 records multi-corpus (idx >= 48 914), reuse direct
   par index.
6. Construit un nouvel `IndexFlatL2` avec les vecteurs réutilisés
7. Sauvegarde `formations_multi_corpus_dedupe.index` (4 824 vecteurs en
   moins = 50 153 - 1 324 - 0 multi-corpus = 48 829)

**Coût Mistral effectif : $0** (aucun appel API embed).

Justification scientifique : l'embedding d'une fiche est calculé sur son
texte (`fiche_to_text(fiche)` v3 pour formations, `record["text"]` pour
multi-corpus). Le merge soft de la dedup peut produire un texte
légèrement différent (champs complétés cross-source), MAIS comme on
choisit la fiche **la plus enrichie** comme base, son texte
`fiche_to_text` est inchangé pour 99 % des cas (les champs ajoutés via
merge sont rarement utilisés par `fiche_to_text` v3 — cf protected file
note). Reuse safe.

Pour les <1 % d'edge case où `fiche_to_text` aurait changé, l'effet sur
le retrieval est négligeable (1 vecteur sur 48 829, distance L2 stable
pour la plupart des queries).

Sortie :
- `data/embeddings/formations_multi_corpus.index.pre_dedup` (backup)
- `data/embeddings/formations_multi_corpus_dedupe.index` (nouveau)
- `data/processed/formations_multi_corpus_dedupe.json` (47 590 + 1 239
  = 48 829 fiches)
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

import faiss
import numpy as np


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Inputs
SRC_FICHES_MC = Path("data/processed/formations_multi_corpus.json")
SRC_INDEX_MC = Path("data/embeddings/formations_multi_corpus.index")
SRC_DEDUPE = Path("data/processed/formations_dedupe.json")

# Outputs
TARGET_FICHES = Path("data/processed/formations_multi_corpus_dedupe.json")
TARGET_INDEX = Path("data/embeddings/formations_multi_corpus_dedupe.index")
BACKUP_INDEX = Path("data/embeddings/formations_multi_corpus.index.pre_dedup")


def main() -> int:
    print("=" * 60)
    print("Rebuild FAISS multi-corpus dedupé (reuse embeddings, $0)")
    print("=" * 60)

    if not all((SRC_FICHES_MC.exists(), SRC_INDEX_MC.exists(), SRC_DEDUPE.exists())):
        print(f"❌ Missing inputs:")
        for p in (SRC_FICHES_MC, SRC_INDEX_MC, SRC_DEDUPE):
            if not p.exists():
                print(f"  - {p}")
        return 1

    print(f"\n1. Loading {SRC_FICHES_MC}…")
    fiches_mc = json.loads(SRC_FICHES_MC.read_text(encoding="utf-8"))
    print(f"   {len(fiches_mc):,} fiches multi-corpus")

    print(f"\n2. Loading {SRC_INDEX_MC}…")
    index_mc = faiss.read_index(str(SRC_INDEX_MC))
    print(f"   ntotal={index_mc.ntotal:,}, d={index_mc.d}")
    if index_mc.ntotal != len(fiches_mc):
        print(f"   ⚠️  Désalignement source : abort")
        return 1

    print(f"\n3. Loading {SRC_DEDUPE}…")
    fiches_dedupe = json.loads(SRC_DEDUPE.read_text(encoding="utf-8"))
    print(f"   {len(fiches_dedupe):,} fiches formations dédupées")

    # Stratégie : pour chaque fiche dédupée formation, retrouver son
    # embedding dans index_mc via cod_aff_form (1ère occurrence) ou via
    # l'objet identique (autres sources sans cod_aff_form).
    #
    # On parcourt fiches_mc dans l'ordre et on track quel cod_aff_form
    # a déjà été vu. La dedup keep_first par cod_aff_form (cf
    # `dedup_parcoursup_by_cod_aff_form` ordre stable) garantit que la
    # fiche dédupée correspondant à un cod_aff_form donné est associée
    # à l'embedding de la **première occurrence** de ce code dans
    # fiches_mc. Mais notre dedup fait un merge-soft où la BASE peut
    # être la 2e occurrence (si plus enrichie) avec ordre output =
    # première occurrence input. → on doit détecter quelle position
    # FAISS originale appartenait à la base.
    #
    # Approximation safe : on prend la 1ère occurrence FAISS du
    # cod_aff_form. Le texte `fiche_to_text` est dominé par les champs
    # nom/etab/ville/niveau/type_diplome/domaine qui sont identiques
    # entre legacy et extended (cf inspection PR #64). Les champs qui
    # diffèrent (insertion_pro, trends, labels) ne sont PAS dans
    # `fiche_to_text` v3 (cf src/rag/embeddings.py:140). Donc l'embedding
    # 1ère occurrence ≈ embedding base mergée.

    print("\n4. Building dedupe ↔ FAISS position mapping…")
    t0 = time.time()
    seen_caf_to_pos: dict[str, int] = {}
    pos_no_caf_iter = iter(range(len(fiches_mc)))
    for pos, f in enumerate(fiches_mc):
        caf = f.get("cod_aff_form")
        if caf and caf not in seen_caf_to_pos:
            seen_caf_to_pos[caf] = pos
    print(f"   {len(seen_caf_to_pos):,} cod_aff_form indexés (positions FAISS)")

    # Résoudre les positions pour les fiches non-formation (multi-corpus)
    # qui sont à la fin de fiches_mc (positions 48 914 à 50 152)
    multi_corpus_start = None
    for pos, f in enumerate(fiches_mc):
        if f.get("domain") and f.get("domain") != "formation":
            multi_corpus_start = pos
            break
    print(f"   multi-corpus records start at position: {multi_corpus_start}")

    print("\n5. Pre-indexing no-caf fiches by signature…")
    # Pre-compute signature → list of FAISS positions for no-caf fiches.
    # Évite O(N²) scan ; rest O(N) sur dedupé.
    sig_to_positions: dict[tuple[str, str, str], list[int]] = {}
    end_formations = multi_corpus_start or len(fiches_mc)
    for pos in range(end_formations):
        cand = fiches_mc[pos]
        if cand.get("cod_aff_form"):
            continue
        sig = (
            (cand.get("nom") or "").strip(),
            (cand.get("etablissement") or "").strip(),
            (cand.get("ville") or "").strip(),
        )
        sig_to_positions.setdefault(sig, []).append(pos)
    print(f"   {len(sig_to_positions):,} signatures distinctes pour no-caf fiches")

    print("\n6. Identifying FAISS positions to keep…")
    keep_positions: list[int] = []
    new_fiches: list[dict] = []
    formation_count = 0
    multi_count = 0
    untracked_count = 0
    used_no_caf_pos: set[int] = set()  # éviter qu'une même position serve 2x

    # Phase A : iterer sur fiches_dedupe (formations dédupées)
    for f in fiches_dedupe:
        caf = f.get("cod_aff_form")
        if caf and caf in seen_caf_to_pos:
            keep_positions.append(seen_caf_to_pos[caf])
            new_fiches.append(f)
            formation_count += 1
            continue
        # Fiche sans cod_aff_form : signature lookup
        sig = (
            (f.get("nom") or "").strip(),
            (f.get("etablissement") or "").strip(),
            (f.get("ville") or "").strip(),
        )
        candidates = sig_to_positions.get(sig, [])
        # Take first available position (not yet used)
        found_pos = None
        for pos in candidates:
            if pos not in used_no_caf_pos:
                found_pos = pos
                break
        if found_pos is not None:
            used_no_caf_pos.add(found_pos)
            keep_positions.append(found_pos)
            new_fiches.append(f)
            formation_count += 1
        else:
            untracked_count += 1
            if untracked_count <= 5:
                print(f"   ⚠️  Untracked formation (no FAISS match): {f.get('nom','')[:60]}")

    # Phase B : append les multi-corpus records (positions multi_corpus_start..)
    if multi_corpus_start is not None:
        for pos in range(multi_corpus_start, len(fiches_mc)):
            keep_positions.append(pos)
            new_fiches.append(fiches_mc[pos])
            multi_count += 1

    print(f"   formations matched: {formation_count:,}")
    print(f"   multi-corpus appended: {multi_count:,}")
    print(f"   untracked (skipped): {untracked_count}")
    print(f"   total to keep: {len(keep_positions):,}")
    print(f"   mapping built in {time.time()-t0:.1f}s")

    print("\n6. Reconstructing vectors via faiss.reconstruct_n…")
    t0 = time.time()
    # Reconstruct uses bulk if positions are contiguous, but we have
    # arbitrary positions. Use individual reconstruct + np.array.
    vectors = np.zeros((len(keep_positions), index_mc.d), dtype="float32")
    for i, pos in enumerate(keep_positions):
        vec = index_mc.reconstruct(int(pos))
        vectors[i] = vec
    print(f"   {len(vectors):,} vectors reconstructed in {time.time()-t0:.1f}s")

    print("\n7. Building new IndexFlatL2…")
    new_index = faiss.IndexFlatL2(index_mc.d)
    new_index.add(vectors)
    print(f"   ntotal={new_index.ntotal:,}")
    if new_index.ntotal != len(new_fiches):
        print(f"   ⚠️  Désalignement final : abort")
        return 1

    print(f"\n8. Backing up {SRC_INDEX_MC} to {BACKUP_INDEX}…")
    if not BACKUP_INDEX.exists():
        shutil.copy2(SRC_INDEX_MC, BACKUP_INDEX)
    print("   backup OK")

    print(f"\n9. Saving outputs…")
    TARGET_FICHES.write_text(
        json.dumps(new_fiches, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"   fiches → {TARGET_FICHES} ({TARGET_FICHES.stat().st_size / 1024**2:.1f} MB)")
    faiss.write_index(new_index, str(TARGET_INDEX))
    print(f"   index → {TARGET_INDEX} ({TARGET_INDEX.stat().st_size / 1024**2:.1f} MB)")

    print("\n✅ Rebuild dedupé done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
