#!/usr/bin/env python3
"""Re-rédaction Phase 3 V2 — orchestrateur CLI (ADR-060).

Lance le rewrite Haiku sur les fiches annexes du corpus v5, valide via
les garde-fous (G1-G5), assemble le corpus v6 et produit un rapport
stats par domain.

Usage :
    # Sample 50 fiches stratifié sur les domains critiques (smoke test)
    python scripts/rewrite_annex_texts.py --sample 50 \\
        --output /tmp/sample_v6.json

    # Run complet 13 417 fiches
    python scripts/rewrite_annex_texts.py

    # Resume sur run interrompu (lit progress JSONL automatiquement)
    python scripts/rewrite_annex_texts.py --resume

    # Override paths
    python scripts/rewrite_annex_texts.py \\
        --input data/processed/formations_v5.json \\
        --output data/processed/formations_v6.json \\
        --progress /tmp/orientia_rewrite_v6_progress.jsonl
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import random
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# Permet de lancer ce script depuis la racine du repo
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import load_config  # noqa: E402
from src.rewrite.async_rewriter import (  # noqa: E402
    DEFAULT_CONCURRENCY,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL,
    RewriteResult,
    RunStats,
    estimate_cost,
    run_rewrite_batch,
)
from src.rewrite.corpus_assembler import assemble_v6  # noqa: E402

logger = logging.getLogger("rewrite_annex_texts")


# -----------------------------------------------------------------------------
# Stratification
# -----------------------------------------------------------------------------

# Domains critiques du handoff (priorité 1) qu'on veut sur-représenter
# dans un sample
PRIORITY_DOMAINS = (
    "crous",
    "insee_salaire",
    "parcours_bacheliers",
    "apec_region",
    "territoire_drom",
    "voie_pre_bac",
    "financement_etudes",
)


def _stratified_sample(fiches: list[dict], n: int, seed: int = 42) -> list[dict]:
    """Échantillonne ``n`` fiches en couvrant tous les domains, avec
    sur-représentation des PRIORITY_DOMAINS. Si un domain n'a pas assez
    d'éléments, on prend tout ce qu'il a."""
    if n >= len(fiches):
        return fiches

    rng = random.Random(seed)
    by_domain: dict[str, list[dict]] = {}
    for f in fiches:
        by_domain.setdefault(f.get("domain", "?"), []).append(f)

    domains = sorted(by_domain.keys())
    n_domains = len(domains)
    out: list[dict] = []
    used_ids: set[str] = set()

    # 1) Au moins 1 fiche par domain présent
    for d in domains:
        candidates = [f for f in by_domain[d] if f["id"] not in used_ids]
        if candidates:
            picked = rng.choice(candidates)
            out.append(picked)
            used_ids.add(picked["id"])

    # 2) Compléter en privilégiant les PRIORITY_DOMAINS
    remaining = n - len(out)
    if remaining <= 0:
        return out[:n]

    priority_pool: list[dict] = []
    for d in PRIORITY_DOMAINS:
        priority_pool.extend(
            f for f in by_domain.get(d, []) if f["id"] not in used_ids
        )
    rng.shuffle(priority_pool)
    for f in priority_pool:
        if remaining <= 0:
            break
        out.append(f)
        used_ids.add(f["id"])
        remaining -= 1

    # 3) Tout autre domain (proportionnel)
    other_pool = [f for f in fiches if f["id"] not in used_ids]
    rng.shuffle(other_pool)
    out.extend(other_pool[:remaining])

    return out


# -----------------------------------------------------------------------------
# Reporting
# -----------------------------------------------------------------------------


def _format_stats(run_stats: RunStats, assembly_stats: dict) -> str:
    lines = []
    lines.append("=" * 70)
    lines.append("RAPPORT REWRITE ANNEXES — Phase 3 V2 (ADR-060)")
    lines.append("=" * 70)
    lines.append("")
    lines.append("## Run async Haiku")
    lines.append(f"  Total fiches  : {run_stats.n_total:>6}")
    lines.append(f"  Succeeded     : {run_stats.n_succeeded:>6}")
    lines.append(f"  Failed (API)  : {run_stats.n_failed:>6}")
    lines.append(f"  Skipped resume: {run_stats.n_skipped_resume:>6}")
    lines.append(f"  Tokens input  : {run_stats.total_input_tokens:>10,}")
    lines.append(f"  Tokens output : {run_stats.total_output_tokens:>10,}")
    cost_in = run_stats.total_input_tokens / 1_000_000 * 1.0
    cost_out = run_stats.total_output_tokens / 1_000_000 * 5.0
    lines.append(f"  Coût estimé   : ${cost_in + cost_out:.2f}")
    lines.append("")
    lines.append("## Validation garde-fous (G1-G5)")
    lines.append(f"  Fiches main inchangées       : {assembly_stats['n_main_unchanged']:>6}")
    lines.append(f"  Fiches annexes total         : {assembly_stats['n_annex_total']:>6}")
    lines.append(f"  Fiches annexes acceptées     : {assembly_stats['n_annex_accepted']:>6}")
    lines.append(f"  Fiches annexes rejetées      : {assembly_stats['n_annex_rejected']:>6}")
    lines.append(f"  Fiches annexes sans rewrite  : {assembly_stats['n_annex_no_rewrite']:>6}")
    rate = assembly_stats.get("acceptance_rate") or 0
    lines.append(f"  Taux acceptation             : {rate * 100:.1f}%")
    lines.append("")
    if assembly_stats.get("rejection_reasons"):
        lines.append("## Raisons de rejet (G échoués)")
        for reason, n in sorted(
            assembly_stats["rejection_reasons"].items(),
            key=lambda x: -x[1],
        ):
            lines.append(f"  - {reason}: {n}")
        lines.append("")
    lines.append("## Acceptation par domain")
    accepted = assembly_stats.get("accepted_per_domain", {})
    rejected = assembly_stats.get("rejected_per_domain", {})
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
    lines.append("=" * 70)
    return "\n".join(lines)


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


async def amain(args: argparse.Namespace) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    cfg = load_config()

    input_path = Path(args.input)
    output_path = Path(args.output)
    progress_path = Path(args.progress) if args.progress else None
    stats_path = Path(args.stats) if args.stats else None

    logger.info(f"Loading {input_path}")
    v5 = json.loads(input_path.read_text(encoding="utf-8"))
    logger.info(f"  → {len(v5)} fiches v5 totales")

    annex_fiches = [f for f in v5 if f.get("domain")]
    logger.info(f"  → {len(annex_fiches)} fiches annexes (domain non-vide)")

    if args.sample is not None:
        sampled = _stratified_sample(annex_fiches, args.sample, seed=args.seed)
        logger.info(f"  → sample stratifié de {len(sampled)} fiches")
        targets = sampled
    else:
        targets = annex_fiches

    target_count = len(targets)
    estimate = estimate_cost(target_count)
    domain_breakdown = Counter(f.get("domain") for f in targets)
    logger.info(f"Cible : {target_count} rewrites Haiku")
    logger.info(f"  Coût estimé : ~${estimate:.2f}")
    logger.info(f"  Distribution : {dict(domain_breakdown)}")

    if not args.yes and target_count > 200:
        confirm = input(
            f"\nLancer le rewrite de {target_count} fiches "
            f"(~${estimate:.2f}) ? [y/N] "
        )
        if confirm.lower() != "y":
            logger.info("Aborté par utilisateur")
            return 1

    rewrites, run_stats = await run_rewrite_batch(
        targets,
        api_key=cfg.anthropic_api_key,
        model=args.model,
        max_tokens=args.max_tokens,
        concurrency=args.concurrency,
        progress_path=progress_path,
        with_few_shot=not args.no_few_shot,
        resume=args.resume,
    )

    logger.info(
        f"Rewrites produits : {len(rewrites)} / {target_count} "
        f"(failed={run_stats.n_failed})"
    )

    rewritten_at = _now_iso()
    logger.info("Assembling v6 corpus + validating G1-G5")
    v6, asm_stats = assemble_v6(
        v5,
        rewrites,
        rewriter=args.model,
        rewritten_at=rewritten_at,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Saving {output_path}")
    output_path.write_text(
        json.dumps(v6, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    asm_dict = asm_stats.to_dict()
    report = _format_stats(run_stats, asm_dict)
    print(report)

    if stats_path:
        stats_path.parent.mkdir(parents=True, exist_ok=True)
        stats_path.write_text(
            json.dumps(
                {
                    "run": {
                        "n_total": run_stats.n_total,
                        "n_succeeded": run_stats.n_succeeded,
                        "n_failed": run_stats.n_failed,
                        "n_skipped_resume": run_stats.n_skipped_resume,
                        "total_input_tokens": run_stats.total_input_tokens,
                        "total_output_tokens": run_stats.total_output_tokens,
                    },
                    "assembly": asm_dict,
                    "rewriter": args.model,
                    "rewritten_at": rewritten_at,
                    "input_path": str(input_path),
                    "output_path": str(output_path),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    rate = asm_dict.get("acceptance_rate") or 0
    if rate < 0.9 and asm_dict["n_annex_total"] > 100:
        logger.warning(
            f"⚠ Taux acceptation {rate * 100:.1f}% < 90% — analyser les raisons "
            f"de rejet avant le run complet ou le re-embed"
        )
        return 2
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Re-rédaction Phase 3 V2 des fiches annexes corpus v5 (ADR-060)",
    )
    parser.add_argument(
        "--input",
        default="data/processed/formations_v5.json",
        help="Chemin du corpus v5 source",
    )
    parser.add_argument(
        "--output",
        default="data/processed/formations_v6.json",
        help="Chemin du corpus v6 cible",
    )
    parser.add_argument(
        "--progress",
        default="/tmp/orientia_rewrite_v6_progress.jsonl",
        help="Chemin JSONL pour save incrémental + resume",
    )
    parser.add_argument(
        "--stats",
        default=None,
        help="Chemin JSON pour sauver les stats (optionnel)",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Si fourni, ne traite qu'un sample stratifié de N fiches",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Seed pour le sampling stratifié",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Modèle Anthropic (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_MAX_TOKENS,
        help="max_tokens output Anthropic",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULT_CONCURRENCY,
        help=f"Concurrence async (default {DEFAULT_CONCURRENCY})",
    )
    parser.add_argument(
        "--no-few-shot",
        action="store_true",
        help="Désactive les few-shot examples (économie tokens)",
    )
    parser.add_argument(
        "--no-resume",
        dest="resume",
        action="store_false",
        help="Désactive le resume depuis progress JSONL",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=True,
        help="Active le resume (par défaut)",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Skip confirmation pour les runs > 200 fiches",
    )
    args = parser.parse_args()
    return asyncio.run(amain(args))


if __name__ == "__main__":
    sys.exit(main())
