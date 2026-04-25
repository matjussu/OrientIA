"""Build FAISS index multi-corpus en mode APPEND (préserve baseline v4).

Stratégie ADR-048 + consensus Jarvis+Claudette 2026-04-25 : on N'effectue
PAS un full rebuild de l'index FAISS formations (coût + bruit
d'embedding regenerative). On charge l'index existant et on lui
**append** les 1 239 nouveaux records des 3 corpus retrievables :

- `metiers_corpus.json` (1 075 records, ONISEP Idéo-Fiches)
- `parcours_bacheliers_corpus.json` (151 records, MESRI cohortes)
- `apec_regions_corpus.json` (13 records, APEC observatoire 2026)

Total final : 48 914 + 1 239 = 50 153 records dans l'index étendu.

## Préservation v4 baseline

Pour garantir l'isolation scientifique d'UNE variable (le pivot
multi-corpus) en v4 → v5 :

- `data/processed/formations.json` reste **inchangé** (48 914 fiches)
- `data/embeddings/formations.index` reste **inchangé** (48 914 vecteurs)
- Nouveau livrable : `data/processed/formations_multi_corpus.json` =
  formations.json + 1 239 nouveaux records normalisés (avec `domain`)
- Nouveau livrable : `data/embeddings/formations_multi_corpus.index` =
  copie de formations.index + embeddings 1 239 nouveaux records

Le bench v5 utilisera les fichiers `*_multi_corpus*`, le bench v3/v4
historique reste reproductible.

## Coût

- 1 239 records × ~500 tokens/record en moyenne = ~620 K tokens d'embed
- Mistral embed = $0.10 / 1M tokens → **~$0.06**
- Largement sous le budget Matteo $5-10 validé.

## Usage

```bash
source .venv/bin/activate
python scripts/build_multi_corpus_index.py
```

Idempotent : si `formations_multi_corpus.index` existe déjà avec ntotal
correct, le script skippe.
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

from src.config import load_config  # noqa: E402
from src.rag.embeddings import embed_texts_batched  # noqa: E402
from src.rag.multi_corpus import (  # noqa: E402
    DEFAULT_CORPUS_PATHS,
    MultiCorpusLoader,
)


# Inputs (préservés)
SOURCE_FICHES = Path("data/processed/formations.json")
SOURCE_INDEX = Path("data/embeddings/formations.index")

# Outputs
TARGET_FICHES = Path("data/processed/formations_multi_corpus.json")
TARGET_INDEX = Path("data/embeddings/formations_multi_corpus.index")

# Domains additifs (formations existantes restent en domain="formation"
# mais sans le champ explicite ; les nouveaux records ont `domain` set
# par leurs builders).
ADDITIONAL_DOMAINS = ("metier", "parcours_bacheliers", "apec_region")


def _load_existing(verbose: bool = True) -> tuple[list[dict], faiss.Index]:
    if not SOURCE_FICHES.exists():
        raise FileNotFoundError(f"{SOURCE_FICHES} absent — exécute d'abord le merger v2")
    if not SOURCE_INDEX.exists():
        raise FileNotFoundError(
            f"{SOURCE_INDEX} absent — exécute d'abord python -m src.rag.embeddings"
        )
    fiches = json.loads(SOURCE_FICHES.read_text(encoding="utf-8"))
    index = faiss.read_index(str(SOURCE_INDEX))
    if verbose:
        print(f"  source fiches: {len(fiches):,}")
        print(f"  source index ntotal: {index.ntotal:,} (d={index.d})")
    if len(fiches) != index.ntotal:
        raise ValueError(
            f"Désalignement source : {len(fiches)} fiches vs {index.ntotal} vecteurs"
        )
    return fiches, index


def _annotate_existing_domain(fiches: list[dict]) -> None:
    """Ajoute `domain="formation"` à chaque fiche existante in-place
    (ne modifie pas le file source, seulement la list en mémoire).
    """
    for f in fiches:
        f.setdefault("domain", "formation")


def _gather_additional_records() -> list[dict]:
    """Charge les 3 corpus additifs et retourne la liste consolidée
    avec leur `text` + `domain` + `id` (champs déjà présents).
    """
    loader = MultiCorpusLoader(
        paths={d: DEFAULT_CORPUS_PATHS[d] for d in ADDITIONAL_DOMAINS}
    )
    loader.load_all()
    additional: list[dict] = []
    for domain in ADDITIONAL_DOMAINS:
        corpus = loader.corpora[domain]
        for record in corpus.records:
            text = record.get("text") or ""
            if not text:
                continue
            additional.append(record)
    print(f"  additional records: {len(additional):,}")
    return additional


def _embed_additional(client, records: list[dict]) -> np.ndarray:
    """Embed les `text` des records additifs en batch (Mistral embed)."""
    texts = [r["text"] for r in records]
    print(f"  embedding {len(texts):,} texts via Mistral mistral-embed…")
    t0 = time.time()
    vectors = embed_texts_batched(client, texts, batch_size=64)
    arr = np.array(vectors, dtype="float32")
    print(f"  embedded shape: {arr.shape} in {time.time()-t0:.1f}s")
    return arr


def _extend_index(source_index: faiss.Index, new_vectors: np.ndarray) -> faiss.Index:
    """Crée un IndexFlatL2 étendu (copie source + append nouveaux)."""
    if new_vectors.shape[1] != source_index.d:
        raise ValueError(
            f"Mismatch dim : index d={source_index.d} vs vectors d={new_vectors.shape[1]}"
        )
    extended = faiss.IndexFlatL2(source_index.d)
    # Reconstruct des vecteurs source (IndexFlatL2 stocke en clair, possible)
    src_vectors = source_index.reconstruct_n(0, source_index.ntotal)
    extended.add(src_vectors)
    extended.add(new_vectors)
    print(f"  extended index ntotal: {extended.ntotal:,}")
    return extended


def _save_outputs(fiches: list[dict], index: faiss.Index) -> None:
    TARGET_FICHES.parent.mkdir(parents=True, exist_ok=True)
    TARGET_FICHES.write_text(
        json.dumps(fiches, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  saved fiches → {TARGET_FICHES} ({TARGET_FICHES.stat().st_size / 1024**2:.1f} MB)")

    TARGET_INDEX.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(TARGET_INDEX))
    print(f"  saved index  → {TARGET_INDEX} ({TARGET_INDEX.stat().st_size / 1024**2:.1f} MB)")


def main() -> int:
    print("=" * 60)
    print("Build multi-corpus FAISS index (append mode)")
    print("=" * 60)

    if TARGET_INDEX.exists() and TARGET_FICHES.exists():
        try:
            existing_idx = faiss.read_index(str(TARGET_INDEX))
            existing_fiches = json.loads(TARGET_FICHES.read_text(encoding="utf-8"))
            if len(existing_fiches) == existing_idx.ntotal and existing_idx.ntotal > 48_914:
                print(
                    f"  Idempotent skip : {TARGET_INDEX} déjà à jour avec "
                    f"{existing_idx.ntotal:,} vecteurs."
                )
                return 0
        except Exception as e:  # noqa: BLE001
            print(f"  Output existant invalide ({e}) — rebuild.")

    print("\n1. Loading source (formations.json + formations.index)…")
    fiches, source_index = _load_existing()

    print("\n2. Gathering additional records (3 corpora)…")
    additional = _gather_additional_records()
    if not additional:
        print("  Aucun record additif — abort.")
        return 1

    print("\n3. Embedding additional records…")
    cfg = load_config()
    from mistralai.client import Mistral

    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=180000)
    new_vectors = _embed_additional(client, additional)

    print("\n4. Extending index…")
    extended_index = _extend_index(source_index, new_vectors)

    print("\n5. Building extended fiches list…")
    _annotate_existing_domain(fiches)
    fiches_extended = fiches + additional
    print(f"  fiches_extended length: {len(fiches_extended):,}")
    if len(fiches_extended) != extended_index.ntotal:
        print(
            f"  ⚠️  Désalignement après extension : "
            f"{len(fiches_extended)} fiches vs {extended_index.ntotal} vecteurs"
        )
        return 1

    print("\n6. Saving outputs…")
    _save_outputs(fiches_extended, extended_index)

    print("\n✅ Build complete.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
