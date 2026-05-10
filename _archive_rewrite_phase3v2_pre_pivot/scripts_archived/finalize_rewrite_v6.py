#!/usr/bin/env python3
"""Phase 3 V2 — Étape 3 : assemble formations_v6.json depuis les chunks.

Lit tous les ``chunk_NNNN_results.json`` produits par les sous-agents
Haiku, fusionne les rewrites, applique les garde-fous G1-G5
(``corpus_assembler.assemble_v6``), produit ``formations_v6.json`` + un
rapport stats détaillé.

Usage :
    # Assemble v6 standard
    python scripts/finalize_rewrite_v6.py

    # Override paths
    python scripts/finalize_rewrite_v6.py \\
        --input data/processed/formations_v5.json \\
        --chunks-dir /tmp/orientia_rewrite_chunks_v6 \\
        --output data/processed/formations_v6.json \\
        --stats results/rewrite_v6_stats.json

    # Mode test sur sample
    python scripts/finalize_rewrite_v6.py \\
        --chunks-dir /tmp/orientia_rewrite_test_5 \\
        --output /tmp/orientia_test_v6.json \\
        --strict
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.rewrite.chunk_dispatcher import (  # noqa: E402
    ChunkManifest,
    list_completed_chunks,
    list_pending_chunks,
    load_chunk_results,
)
from src.rewrite.corpus_assembler import assemble_v6  # noqa: E402

logger = logging.getLogger("finalize_rewrite_v6")


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _format_report(
    asm: dict,
    n_treated: int,
    chunk_debug: dict,
    n_pending_chunks: int,
) -> str:
    lines = []
    lines.append("=" * 70)
    lines.append("RAPPORT FINALIZE REWRITE v6 (ADR-060 addendum 2026-05-08)")
    lines.append("=" * 70)
    lines.append("")
    lines.append("## Synthèse corpus")
    lines.append(f"  Total fiches v6           : {asm['n_total']:>6}")
    lines.append(f"  Main fiches inchangées    : {asm['n_main_unchanged']:>6}")
    lines.append(f"  Annexes total             : {asm['n_annex_total']:>6}")
    lines.append(f"  Annexes traitées          : {n_treated:>6}")
    lines.append(f"  Annexes acceptées         : {asm['n_annex_accepted']:>6}")
    lines.append(f"  Annexes rejetées (G échec): {asm['n_annex_rejected']:>6}")
    lines.append(f"  Annexes sans rewrite      : {asm['n_annex_no_rewrite']:>6}")
    lines.append("")
    if n_treated > 0:
        accept_treated = asm["n_annex_accepted"] / n_treated * 100
        lines.append(f"  Taux acceptation (sur traitées) : {accept_treated:.1f}%")
    if asm["n_annex_total"] > 0:
        accept_total = asm["n_annex_accepted"] / asm["n_annex_total"] * 100
        lines.append(f"  Taux acceptation (sur annexes)  : {accept_total:.1f}%")
    lines.append("")
    if n_pending_chunks > 0:
        lines.append(f"⚠ {n_pending_chunks} chunks PENDING (results manquants)")
        lines.append("")
    if asm.get("rejection_reasons"):
        lines.append("## Raisons de rejet")
        for reason, n in sorted(
            asm["rejection_reasons"].items(), key=lambda x: -x[1]
        ):
            lines.append(f"  - {reason}: {n}")
        lines.append("")
    lines.append("## Acceptation par domain")
    accepted = asm.get("accepted_per_domain", {})
    rejected = asm.get("rejected_per_domain", {})
    all_domains = sorted(set(accepted) | set(rejected))
    for d in all_domains:
        acc = accepted.get(d, 0)
        rej = rejected.get(d, 0)
        total = acc + rej
        if total:
            lines.append(
                f"  {d:30s}: {acc:>5} OK / {rej:>4} KO  "
                f"({acc / total * 100:.0f}% accept)"
            )
    lines.append("")
    lines.append("## Chunks débrief")
    n_ok = sum(1 for d in chunk_debug.values() if d.get("status") == "ok")
    n_missing = sum(1 for d in chunk_debug.values() if d.get("status") == "missing")
    n_parse_error = sum(
        1 for d in chunk_debug.values() if d.get("status") == "parse_error"
    )
    lines.append(f"  Chunks OK          : {n_ok}")
    lines.append(f"  Chunks missing     : {n_missing}")
    lines.append(f"  Chunks parse_error : {n_parse_error}")
    if n_parse_error:
        lines.append("  Détail parse errors :")
        for cid, d in chunk_debug.items():
            if d.get("status") == "parse_error":
                lines.append(f"    - {cid}: {d.get('error', '')[:80]}")
    lines.append("")
    lines.append("=" * 70)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Finalize formations_v6.json depuis chunks (ADR-060)",
    )
    parser.add_argument(
        "--input",
        default="data/processed/formations_v5.json",
        help="Corpus v5 source (préservé entièrement)",
    )
    parser.add_argument(
        "--chunks-dir",
        default="/tmp/orientia_rewrite_chunks_v6",
        help="Répertoire des chunks + manifest + results",
    )
    parser.add_argument(
        "--output",
        default="data/processed/formations_v6.json",
        help="Chemin du corpus v6 cible",
    )
    parser.add_argument(
        "--stats",
        default=None,
        help="Chemin JSON pour sauver les stats détaillées",
    )
    parser.add_argument(
        "--rewriter",
        default="claude-haiku-4-5-via-agent",
        help="Identifiant rewriter pour la provenance",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Échoue si un chunk results manque (au lieu de skip)",
    )
    parser.add_argument(
        "--allow-pending",
        action="store_true",
        help="Continue même si certains chunks n'ont pas de results "
        "(mode partial promotion)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    input_path = Path(args.input)
    chunks_dir = Path(args.chunks_dir)
    output_path = Path(args.output)
    stats_path = Path(args.stats) if args.stats else None

    manifest_path = chunks_dir / "manifest.json"
    if not manifest_path.exists():
        logger.error(f"Manifest absent : {manifest_path}")
        logger.error("Lance d'abord scripts/prepare_rewrite_chunks.py")
        return 1
    manifest = ChunkManifest.from_json(manifest_path)
    logger.info(
        f"Manifest : {manifest.n_chunks} chunks de ≤{manifest.chunk_size}, "
        f"{manifest.n_total_fiches} fiches"
    )

    pending = list_pending_chunks(manifest)
    completed = list_completed_chunks(manifest)
    logger.info(f"Chunks completed : {len(completed)}/{manifest.n_chunks}")
    logger.info(f"Chunks pending   : {len(pending)}")

    if pending and not args.allow_pending and not args.strict:
        logger.warning(
            f"⚠ {len(pending)} chunks sans results — relance les Agents ou "
            f"utilise --allow-pending pour assembler partiellement"
        )
        return 2
    if pending and args.strict:
        logger.error("--strict + chunks pending → abort")
        return 3

    rewrites, chunk_debug = load_chunk_results(manifest, strict=args.strict)
    logger.info(f"Loaded {len(rewrites)} rewrites depuis les chunks")

    logger.info(f"Loading v5 corpus : {input_path}")
    v5 = json.loads(input_path.read_text(encoding="utf-8"))
    logger.info(f"  → {len(v5)} fiches v5")

    rewritten_at = _now_iso()
    logger.info("Assembling v6 + applying garde-fous G1-G5")
    v6, asm_stats = assemble_v6(
        v5,
        rewrites,
        rewriter=args.rewriter,
        rewritten_at=rewritten_at,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Saving {output_path}")
    output_path.write_text(
        json.dumps(v6, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    asm_dict = asm_stats.to_dict()
    n_treated = asm_dict["n_annex_accepted"] + asm_dict["n_annex_rejected"]
    report = _format_report(asm_dict, n_treated, chunk_debug, len(pending))
    print(report)

    if stats_path:
        stats_path.parent.mkdir(parents=True, exist_ok=True)
        stats_path.write_text(
            json.dumps(
                {
                    "manifest": {
                        "chunks_dir": manifest.chunks_dir,
                        "n_chunks": manifest.n_chunks,
                        "chunk_size": manifest.chunk_size,
                        "n_total_fiches": manifest.n_total_fiches,
                    },
                    "n_pending_chunks": len(pending),
                    "n_completed_chunks": len(completed),
                    "n_rewrites_loaded": len(rewrites),
                    "n_treated": n_treated,
                    "assembly": asm_dict,
                    "chunk_debug": chunk_debug,
                    "rewriter": args.rewriter,
                    "rewritten_at": rewritten_at,
                    "input_path": str(input_path),
                    "output_path": str(output_path),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        logger.info(f"Stats : {stats_path}")

    if n_treated > 0:
        rate = asm_dict["n_annex_accepted"] / n_treated
        if rate < 0.9:
            logger.warning(
                f"⚠ Taux acceptation {rate * 100:.1f}% < 90% — analyser "
                f"les raisons de rejet avant promotion v6"
            )
            return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
