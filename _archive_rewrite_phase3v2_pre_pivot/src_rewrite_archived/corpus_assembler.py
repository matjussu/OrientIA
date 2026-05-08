"""Assembleur corpus v6 — fusionne v5 + rewrites validés (ADR-060).

Préserve les 33 776 fiches main inchangées. Pour les annexes, remplace
``text`` par le rewrite si accepté par les garde-fous, garde l'original
sinon. Ajoute systématiquement ``text_original`` + champs de provenance
(``rewritten_at``, ``rewriter``, éventuel ``rewrite_issues``).
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from src.rewrite.result_validator import is_rewrite_acceptable


@dataclass
class AssemblyStats:
    n_total: int = 0
    n_main_unchanged: int = 0
    n_annex_total: int = 0
    n_annex_accepted: int = 0
    n_annex_rejected: int = 0
    n_annex_no_rewrite: int = 0  # rewrite manquant (échec API ou skip)
    rejection_reasons: dict[str, int] = field(default_factory=dict)
    rejected_per_domain: dict[str, int] = field(default_factory=dict)
    accepted_per_domain: dict[str, int] = field(default_factory=dict)

    def increment_reason(self, reasons: list[str]) -> None:
        for r in reasons:
            self.rejection_reasons[r] = self.rejection_reasons.get(r, 0) + 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_total": self.n_total,
            "n_main_unchanged": self.n_main_unchanged,
            "n_annex_total": self.n_annex_total,
            "n_annex_accepted": self.n_annex_accepted,
            "n_annex_rejected": self.n_annex_rejected,
            "n_annex_no_rewrite": self.n_annex_no_rewrite,
            "acceptance_rate": (
                self.n_annex_accepted / self.n_annex_total
                if self.n_annex_total
                else None
            ),
            "rejection_reasons": dict(self.rejection_reasons),
            "rejected_per_domain": dict(self.rejected_per_domain),
            "accepted_per_domain": dict(self.accepted_per_domain),
        }


def _is_annex(fiche: dict) -> bool:
    """Une fiche annexe a un champ ``domain`` non-vide."""
    return bool(fiche.get("domain"))


def _apply_rewrite(
    fiche: dict,
    rewritten_text: str,
    *,
    rewriter: str,
    rewritten_at: str,
    accepted: bool,
    issues: list[str],
) -> dict:
    """Retourne une nouvelle fiche v6 avec text_original + provenance.

    Si ``accepted=True`` → ``text`` remplacé par ``rewritten_text``,
    sinon ``text`` reste l'original (fallback).
    """
    new_fiche = copy.deepcopy(fiche)
    new_fiche["text_original"] = fiche.get("text", "")
    if accepted:
        new_fiche["text"] = rewritten_text
    # Provenance
    prov = new_fiche.get("provenance")
    if not isinstance(prov, dict):
        prov = {}
    prov["rewritten_at"] = rewritten_at
    prov["rewriter"] = rewriter
    prov["rewrite_accepted"] = bool(accepted)
    if issues:
        prov["rewrite_issues"] = list(issues)
    new_fiche["provenance"] = prov
    return new_fiche


def assemble_v6(
    v5_fiches: list[dict],
    rewrites: dict[str, str],
    *,
    rewriter: str = "claude-haiku-4-5-20251001",
    rewritten_at: str = "",
) -> tuple[list[dict], AssemblyStats]:
    """Construit la liste v6 + stats d'assemblage.

    Args:
        v5_fiches: list de toutes les fiches du corpus v5 (47 193).
        rewrites: dict ``{fiche_id: rewritten_text}`` issu du runner.
        rewriter: identifiant du modèle ayant produit les rewrites.
        rewritten_at: ISO date string du run.

    Returns:
        (v6_fiches, stats)
    """
    stats = AssemblyStats()
    stats.n_total = len(v5_fiches)
    out: list[dict] = []

    for fiche in v5_fiches:
        if not _is_annex(fiche):
            stats.n_main_unchanged += 1
            out.append(fiche)
            continue

        stats.n_annex_total += 1
        fiche_id = fiche.get("id", "")
        domain = fiche.get("domain", "?")
        rewritten = rewrites.get(fiche_id)

        if rewritten is None:
            stats.n_annex_no_rewrite += 1
            # Pas de rewrite produit → on garde la fiche telle quelle
            # mais on tag pour audit
            tagged = copy.deepcopy(fiche)
            tagged["text_original"] = fiche.get("text", "")
            prov = tagged.get("provenance")
            if not isinstance(prov, dict):
                prov = {}
            prov["rewritten_at"] = rewritten_at
            prov["rewriter"] = rewriter
            prov["rewrite_accepted"] = False
            prov["rewrite_issues"] = ["no_rewrite_produced"]
            tagged["provenance"] = prov
            out.append(tagged)
            continue

        accepted, issues = is_rewrite_acceptable(fiche, rewritten)
        new_fiche = _apply_rewrite(
            fiche,
            rewritten,
            rewriter=rewriter,
            rewritten_at=rewritten_at,
            accepted=accepted,
            issues=issues,
        )
        out.append(new_fiche)

        if accepted:
            stats.n_annex_accepted += 1
            stats.accepted_per_domain[domain] = (
                stats.accepted_per_domain.get(domain, 0) + 1
            )
        else:
            stats.n_annex_rejected += 1
            stats.rejected_per_domain[domain] = (
                stats.rejected_per_domain.get(domain, 0) + 1
            )
            stats.increment_reason(issues)

    return out, stats
