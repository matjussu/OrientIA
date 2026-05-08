"""Split + manifest pour le workflow Agent-based (ADR-060 addendum 2026-05-08).

Le SDK API direct (anthropic.AsyncAnthropic) facture en API standard, hors
abonnement Max. Pivot : on prépare des chunks de fiches sur disque ;
l'orchestration des invocations Agent Haiku se fait depuis la session
Claude Code (cf docs/HANDOFF_REWRITE_ANNEX_TEXTS.md addendum).
"""

from __future__ import annotations

import json
import random
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_CHUNK_SIZE = 50


@dataclass
class ChunkManifest:
    """Manifest décrivant les chunks à traiter."""

    chunks_dir: str
    chunk_size: int
    n_total_fiches: int
    n_chunks: int
    chunk_ids: list[str] = field(default_factory=list)
    seed: int | None = None
    note: str = ""

    def to_json(self) -> str:
        return json.dumps(
            {
                "chunks_dir": self.chunks_dir,
                "chunk_size": self.chunk_size,
                "n_total_fiches": self.n_total_fiches,
                "n_chunks": self.n_chunks,
                "chunk_ids": self.chunk_ids,
                "seed": self.seed,
                "note": self.note,
            },
            ensure_ascii=False,
            indent=2,
        )

    @classmethod
    def from_json(cls, path: Path) -> "ChunkManifest":
        d = json.loads(path.read_text(encoding="utf-8"))
        return cls(**d)


def split_into_chunks(
    fiches: list[dict],
    chunks_dir: Path,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    seed: int | None = None,
) -> ChunkManifest:
    """Découpe ``fiches`` en chunks de ``chunk_size`` et écrit chaque chunk
    sous forme de JSON dans ``chunks_dir``.

    - Mélange optionnel par ``seed`` pour répartir les domains.
    - Pour chaque chunk : ``{chunks_dir}/chunk_NNNN.json`` contient une
      liste de fiches (uniquement les champs nécessaires au rewriting).

    Renvoie un ``ChunkManifest`` qui décrit les chunks et est aussi écrit
    sur disque pour traçabilité.
    """
    chunks_dir.mkdir(parents=True, exist_ok=True)

    ordered = list(fiches)
    if seed is not None:
        rng = random.Random(seed)
        rng.shuffle(ordered)

    chunk_ids: list[str] = []
    n_chunks = (len(ordered) + chunk_size - 1) // chunk_size
    for i in range(n_chunks):
        chunk_id = f"chunk_{i + 1:04d}"
        chunk_path = chunks_dir / f"{chunk_id}.json"
        slice_ = ordered[i * chunk_size : (i + 1) * chunk_size]
        # On préserve toute la fiche pour que le sous-agent ait
        # tout le contexte structurel disponible.
        chunk_path.write_text(
            json.dumps(slice_, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        chunk_ids.append(chunk_id)

    manifest = ChunkManifest(
        chunks_dir=str(chunks_dir),
        chunk_size=chunk_size,
        n_total_fiches=len(ordered),
        n_chunks=n_chunks,
        chunk_ids=chunk_ids,
        seed=seed,
        note="Phase 3 V2 — corpus v6 rewrite Haiku via Agent Claude Code",
    )
    (chunks_dir / "manifest.json").write_text(manifest.to_json(), encoding="utf-8")
    return manifest


def list_pending_chunks(manifest: ChunkManifest) -> list[str]:
    """Renvoie les chunk_id qui n'ont PAS encore de fichier results.

    Utilisé par l'orchestration pour skip ceux déjà traités (resume).
    """
    chunks_dir = Path(manifest.chunks_dir)
    pending = []
    for cid in manifest.chunk_ids:
        results_path = chunks_dir / f"{cid}_results.json"
        if not results_path.exists():
            pending.append(cid)
    return pending


def list_completed_chunks(manifest: ChunkManifest) -> list[str]:
    chunks_dir = Path(manifest.chunks_dir)
    return [
        cid
        for cid in manifest.chunk_ids
        if (chunks_dir / f"{cid}_results.json").exists()
    ]


def load_chunk_results(
    manifest: ChunkManifest, *, strict: bool = False
) -> tuple[dict[str, str], dict[str, Any]]:
    """Charge tous les fichiers ``chunk_NNNN_results.json``.

    Format attendu de chaque results.json :
        [{"fiche_id": "...", "rewritten_text": "..." | null}, ...]

    Renvoie :
        (rewrites_dict, debug_stats)
        rewrites_dict : ``{fiche_id: rewritten_text}`` pour les non-null.
        debug_stats : par chunk, n_fiches_in / n_results / n_null / parse_error.
    """
    chunks_dir = Path(manifest.chunks_dir)
    rewrites: dict[str, str] = {}
    debug: dict[str, Any] = {}

    for cid in manifest.chunk_ids:
        chunk_path = chunks_dir / f"{cid}.json"
        results_path = chunks_dir / f"{cid}_results.json"
        if not results_path.exists():
            debug[cid] = {"status": "missing", "n_fiches_in": _safe_count(chunk_path)}
            if strict:
                raise FileNotFoundError(f"Missing results for {cid}")
            continue

        try:
            results = json.loads(results_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            debug[cid] = {"status": "parse_error", "error": str(e)}
            if strict:
                raise
            continue

        if not isinstance(results, list):
            debug[cid] = {"status": "not_a_list"}
            if strict:
                raise ValueError(f"{cid} results not a list")
            continue

        n_null = 0
        n_kept = 0
        n_skip_format = 0
        for entry in results:
            if not isinstance(entry, dict):
                n_skip_format += 1
                continue
            fid = entry.get("fiche_id")
            text = entry.get("rewritten_text")
            if not fid:
                n_skip_format += 1
                continue
            if not text:
                n_null += 1
                continue
            rewrites[fid] = text
            n_kept += 1

        debug[cid] = {
            "status": "ok",
            "n_fiches_in": _safe_count(chunk_path),
            "n_results": len(results),
            "n_kept": n_kept,
            "n_null": n_null,
            "n_skip_format": n_skip_format,
        }

    return rewrites, debug


def _safe_count(chunk_path: Path) -> int:
    if not chunk_path.exists():
        return 0
    try:
        return len(json.loads(chunk_path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError):
        return 0


def chunk_distribution(manifest: ChunkManifest) -> dict[str, int]:
    """Compte le nombre total de fiches par domain à travers tous les
    chunks (pour reporting amont)."""
    chunks_dir = Path(manifest.chunks_dir)
    counter: Counter[str] = Counter()
    for cid in manifest.chunk_ids:
        path = chunks_dir / f"{cid}.json"
        if not path.exists():
            continue
        for f in json.loads(path.read_text(encoding="utf-8")):
            counter[f.get("domain", "?")] += 1
    return dict(counter)
