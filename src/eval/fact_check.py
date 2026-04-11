"""Automatic fact-check scorer for free-form French orientation answers.

This module extracts verifiable claims from a generated answer and checks
them against the retrieved fiches (for our_rag) or the full dataset (for
baselines with no retrieval). It produces a ratio in [0, 1] that judge v2
uses to post-weight the Claude sourçage score.

Claim types:
  * ONISEP_ID — fiche identifiers like "FOR.1577" (from the URL or cited
    directly) — verified when the ID appears in any retrieved/dataset fiche.
  * PERCENTAGE — selectivity-like percentages (0-100%) — verified when the
    value is within `pct_tolerance` of a known `taux_acces_parcoursup_2025`,
    `pct_tb/b/ab`, or `profil_admis.*` value from a relevant fiche.
  * SCHOOL — establishment names — verified via fuzzy matching against the
    retrieved/dataset fiche `etablissement` values.
  * REPORT — external rapport/étude/enquête references — always flagged as
    unverifiable (we have no external ground truth database). This is what
    catches mistral_raw citing fabricated sources like "rapport ANSSI 2023".

`verify_claim` returns one of three strings:
  * "verified"     — claim maps to a concrete datum in retrieved/dataset
  * "unverifiable" — we cannot confirm or refute it
  * "contradicted" — (reserved, currently unused) — the claim is provably
    wrong. Could be added later for percentage mismatches.

`fact_check_score` returns `verified_count / total_claims`. When the answer
has no claims at all, it returns 1.0 (neutral) rather than 0.0, so
qualitative/conceptual answers aren't penalized for not citing anything.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ClaimType(str, Enum):
    ONISEP_ID = "onisep_id"
    PERCENTAGE = "percentage"
    SCHOOL = "school"
    REPORT = "report"


@dataclass(frozen=True)
class Claim:
    type: ClaimType
    value: str | float
    raw: str


# --- Patterns --------------------------------------------------------------

_ONISEP_ID_RE = re.compile(r"FOR\.(\d+)", re.IGNORECASE)

# Percentages — require explicit '%' sign so we don't match random years
# ('2023') or counts ('1577 étudiants'). Allow spaces, commas, dots.
_PERCENT_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*%",
)

# External reports — the model prefixes them with "rapport", "étude",
# "enquête", "selon", "source". Value is the institution/organization name
# that follows the keyword.
_REPORT_RE = re.compile(
    r"(?:rapport|étude|enquête|étude statistique|baromètre)\s+"
    r"([A-ZÀ-Ÿ][\w\-]+(?:\s+\d{4})?(?:\s+[A-ZÀ-Ÿ][\w\-]+)?)",
    re.IGNORECASE,
)


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def extract_claims(text: str, dataset: list[dict] | None = None) -> list[Claim]:
    """Parse `text` into a list of verifiable claims.

    `dataset` — optional list of fiches used to extract school names via
    simple substring match. Passing None skips school extraction entirely.
    """
    claims: list[Claim] = []

    for m in _ONISEP_ID_RE.finditer(text):
        claims.append(
            Claim(type=ClaimType.ONISEP_ID, value=m.group(1), raw=m.group(0))
        )

    for m in _PERCENT_RE.finditer(text):
        raw = m.group(1).replace(",", ".")
        try:
            val = float(raw)
        except ValueError:
            continue
        if 0 <= val <= 100:
            claims.append(
                Claim(type=ClaimType.PERCENTAGE, value=val, raw=m.group(0))
            )

    for m in _REPORT_RE.finditer(text):
        claims.append(
            Claim(
                type=ClaimType.REPORT,
                value=m.group(1).strip(),
                raw=m.group(0),
            )
        )

    if dataset:
        # Collect unique establishment names from dataset, longest first to
        # avoid matching "EPITA" inside "EPITA Bordeaux" twice.
        etabs = sorted(
            {
                (f.get("etablissement") or "").strip()
                for f in dataset
                if (f.get("etablissement") or "").strip()
            },
            key=lambda s: -len(s),
        )
        text_lower = text.lower()
        seen: set[str] = set()
        for etab in etabs:
            if not etab:
                continue
            etab_low = etab.lower()
            if etab_low in seen:
                continue
            if etab_low in text_lower:
                claims.append(
                    Claim(type=ClaimType.SCHOOL, value=etab, raw=etab)
                )
                seen.add(etab_low)
    return claims


# --- Verify ---------------------------------------------------------------


def _fiche_of(container: dict) -> dict:
    """Normalize retrieved-style dicts (with 'fiche' key) to raw fiche."""
    return container.get("fiche", container)


def _onisep_ids_in(fiches: list[dict]) -> set[str]:
    ids: set[str] = set()
    for f in fiches:
        url = f.get("url_onisep") or ""
        for m in _ONISEP_ID_RE.finditer(url):
            ids.add(m.group(1))
    return ids


def _schools_in(fiches: list[dict]) -> set[str]:
    return {
        _normalize(f.get("etablissement") or "")
        for f in fiches
        if (f.get("etablissement") or "").strip()
    }


def _percentages_in(fiches: list[dict]) -> list[float]:
    """All known numeric percentages across fiches — selectivity, mentions,
    bac types, boursiers. Used to accept percentages cited in answers
    when they match any documented value within tolerance."""
    values: list[float] = []
    for f in fiches:
        taux = f.get("taux_acces_parcoursup_2025")
        if isinstance(taux, (int, float)):
            values.append(float(taux))
        profil = f.get("profil_admis") or {}
        for key in ("mentions_pct", "bac_type_pct", "acces_pct"):
            sub = profil.get(key) or {}
            for v in sub.values():
                if isinstance(v, (int, float)):
                    values.append(float(v))
        b = profil.get("boursiers_pct")
        if isinstance(b, (int, float)):
            values.append(float(b))
    return values


def verify_claim(
    claim: Claim,
    retrieved: list[dict],
    dataset: list[dict],
    pct_tolerance: float = 2.0,
) -> str:
    """Return "verified", "unverifiable", or "contradicted".

    `retrieved` is the list of fiches that were actually shown to the
    generator for this question (preferred ground truth). `dataset` is the
    full list of fiches (fallback — the generator might legitimately cite
    a school known from training even if it wasn't in top-k).
    """
    retrieved_fiches = [_fiche_of(r) for r in retrieved]
    # Union of retrieved + dataset for "exists somewhere in the project" check
    all_fiches = retrieved_fiches + list(dataset)

    if claim.type == ClaimType.ONISEP_ID:
        if str(claim.value) in _onisep_ids_in(all_fiches):
            return "verified"
        return "unverifiable"

    if claim.type == ClaimType.SCHOOL:
        target = _normalize(str(claim.value))
        schools = _schools_in(all_fiches)
        for s in schools:
            if target in s or s in target:
                return "verified"
        return "unverifiable"

    if claim.type == ClaimType.PERCENTAGE:
        percentages = _percentages_in(all_fiches)
        val = float(claim.value)
        for p in percentages:
            if abs(p - val) <= pct_tolerance:
                return "verified"
        return "unverifiable"

    if claim.type == ClaimType.REPORT:
        # No external ground truth — reports are always unverifiable.
        # This is the intended asymmetry: our_rag cites ONISEP/Parcoursup IDs
        # that are in the dataset → verified. Mistral_raw cites rapports /
        # études / enquêtes that are not in the dataset → unverifiable.
        return "unverifiable"

    return "unverifiable"


# --- Score ----------------------------------------------------------------


def fact_check_score(
    answer: str,
    retrieved: list[dict],
    dataset: list[dict],
    pct_tolerance: float = 2.0,
) -> float:
    """Return the verified / total ratio in [0, 1].

    When there are no claims at all, return 1.0 (neutral) so that
    qualitative answers with no numeric content aren't penalized.
    """
    claims = extract_claims(answer, dataset=dataset)
    if not claims:
        return 1.0
    verified = 0
    for c in claims:
        status = verify_claim(c, retrieved, dataset, pct_tolerance=pct_tolerance)
        if status == "verified":
            verified += 1
    return verified / len(claims)
