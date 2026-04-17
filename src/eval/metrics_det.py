"""Deterministic metrics — no LLM calls, no cost.

Three complementary metrics that measure what matters for a lycéen / étudiant
reader, independent of any judge's subjective opinion :

- B3 **Actionability** : does the response contain the structural elements
  that make it actionable (Plan A/B/C, next step, follow-up question,
  comparison table) ?
- B5 **Fraîcheur** (freshness) : does the response cite time-anchored data
  that LLM generalists can't fabricate (Parcoursup 2025, trend 2023→2025) ?
- B6 **Citation precision** : every cod_aff_form / RNCP / ONISEP FOR.xxxxx
  cited in the response must exist in the corpus. Fabrication is a bug.

Run these after every generation — they are effectively free unit tests
on response quality that keep us honest about progress.
"""
from __future__ import annotations

import re
from typing import Iterable


# ============================================================
# B3 — Actionability (0-6 points)
# ============================================================


def _has_plan(response: str, plan: str) -> bool:
    """Return True if the response explicitly names `Plan <plan>`."""
    # Match "Plan A", "**Plan A**", "### Plan A — Réaliste" etc.
    pattern = rf"\bPlan\s+{re.escape(plan)}\b"
    return bool(re.search(pattern, response, flags=re.IGNORECASE))


def _has_follow_up_question(response: str) -> bool:
    """Markdown patterns for the final '💡 Question pour toi' / 'Question retour'."""
    patterns = [
        r"💡\s*Question\s+pour\s+toi",
        r"Question\s+pour\s+toi\s*[:：]",
        r"Question\s+de\s+suivi",
        r"Question\s+retour",
    ]
    return any(re.search(p, response, flags=re.IGNORECASE) for p in patterns)


def _has_next_step(response: str) -> bool:
    """Markdown patterns for 'Prochaine étape' / 'Action concrète'."""
    patterns = [
        r"Prochaine[s]?\s+étape",
        r"Action\s+concrète",
        r"Étape\s+suivante",
        r"À\s+faire\s+maintenant",
    ]
    return any(re.search(p, response, flags=re.IGNORECASE) for p in patterns)


def _has_comparison_table(response: str) -> bool:
    """Detect a markdown table with ≥ 2 rows (header + separator + data)."""
    # A markdown table row looks like: |col1|col2|
    # We need at least 3 pipe-lines in sequence: header, separator, data
    lines = response.split("\n")
    pipe_streak = 0
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and stripped.count("|") >= 2:
            pipe_streak += 1
            if pipe_streak >= 3:
                return True
        else:
            pipe_streak = 0
    return False


def _has_passerelles_block(response: str) -> bool:
    """Detect an explicit passerelles / alternatives block (differentiator)."""
    patterns = [
        r"🔀\s*Passerelles",
        r"\bPasserelle[s]?\s+possible",
        r"\bPasserelle[s]?\s*[:：]",
    ]
    return any(re.search(p, response, flags=re.IGNORECASE) for p in patterns)


def score_actionability(response: str) -> dict:
    """Return per-dimension actionability score (0-6 total).

    Scoring:
      +1 Plan A named
      +1 Plan B named
      +1 Plan C named
      +1 Follow-up question (💡 Question pour toi / équivalent)
      +1 Next step (Prochaine étape / Action concrète)
      +1 Either a comparison table (for comparaison questions) OR a
           passerelles block (for choice questions)
    """
    has_a = _has_plan(response, "A")
    has_b = _has_plan(response, "B")
    has_c = _has_plan(response, "C")
    has_q = _has_follow_up_question(response)
    has_ns = _has_next_step(response)
    has_tab = _has_comparison_table(response)
    has_pas = _has_passerelles_block(response)

    breakdown = {
        "plan_a": 1 if has_a else 0,
        "plan_b": 1 if has_b else 0,
        "plan_c": 1 if has_c else 0,
        "follow_up_question": 1 if has_q else 0,
        "next_step": 1 if has_ns else 0,
        "table_or_passerelles": 1 if (has_tab or has_pas) else 0,
    }
    return {
        "score": sum(breakdown.values()),
        "max": 6,
        "breakdown": breakdown,
    }


# ============================================================
# B5 — Fraîcheur (0-3 points)
# ============================================================


_FRESH_YEAR_PAT = re.compile(r"\b(202[3-6])\b")
_ANCHORED_FIGURE_PAT = re.compile(
    r"(taux|places?|vœux|voeux|salaire|insertion)[^\n]{0,40}"
    r"\b(202[3-6])\b",
    flags=re.IGNORECASE,
)
_CONFESSION_PAT = re.compile(
    r"(pour\s+des?\s+données\s+récentes|consulte[rz]?\s+(?:le\s+)?site\s+officiel|"
    r"données\s+peuvent\s+avoir\s+changé|je\s+n'ai\s+pas\s+accès\s+à\s+des\s+données\s+récentes|"
    r"mes\s+connaissances\s+ne\s+sont\s+pas\s+à\s+jour)",
    flags=re.IGNORECASE,
)


def score_fraicheur(response: str) -> dict:
    """0-3 score on time-anchoring signals.

    +1 any reference to 2023/2024/2025/2026
    +1 at least one chiffre anchored with a year ("taux 2025", "vœux 2024", etc.)
    +1 no temporal-confession phrase ("je n'ai pas de données récentes", etc.)
    """
    has_year = bool(_FRESH_YEAR_PAT.search(response))
    has_anchored = bool(_ANCHORED_FIGURE_PAT.search(response))
    has_confession = bool(_CONFESSION_PAT.search(response))

    breakdown = {
        "mentions_year": 1 if has_year else 0,
        "anchored_figure": 1 if has_anchored else 0,
        "no_temporal_confession": 0 if has_confession else 1,
    }
    return {
        "score": sum(breakdown.values()),
        "max": 3,
        "breakdown": breakdown,
    }


# ============================================================
# B6 — Citation precision
# ============================================================


_COD_AFF_FORM_PAT = re.compile(r"cod_aff_form\s*[:：=]?\s*(\d{2,7})", flags=re.IGNORECASE)
_RNCP_PAT = re.compile(r"\bRNCP[\s:#-]*(\d{4,6})\b", flags=re.IGNORECASE)
_ONISEP_SLUG_PAT = re.compile(r"\bFOR\.(\d{2,6})\b")


def _build_corpus_indexes(corpus: list[dict]) -> tuple[set[str], set[str], set[str]]:
    """Extract the sets of valid cod_aff_form, RNCP, ONISEP slugs in corpus."""
    cod_affs: set[str] = set()
    rncps: set[str] = set()
    slugs: set[str] = set()
    for f in corpus:
        c = f.get("cod_aff_form")
        if isinstance(c, str) and c.strip():
            cod_affs.add(c.strip())
        r = f.get("rncp")
        if isinstance(r, str) and r.strip():
            rncps.add(r.strip())
        url = f.get("url_onisep") or ""
        m = _ONISEP_SLUG_PAT.search(url)
        if m:
            slugs.add(m.group(1))
    return cod_affs, rncps, slugs


def score_citation_precision(
    response: str,
    corpus: list[dict],
) -> dict:
    """For every cod_aff_form, RNCP, ONISEP slug cited in the response,
    verify it exists in the corpus. Return per-category ratio + invalid list.

    A response with NO citations at all is reported with score=None (not 0,
    not 1) — the metric is undefined for responses that don't cite.
    """
    cod_affs_corpus, rncps_corpus, slugs_corpus = _build_corpus_indexes(corpus)

    cited_cod = [m.group(1) for m in _COD_AFF_FORM_PAT.finditer(response)]
    cited_rncp = [m.group(1) for m in _RNCP_PAT.finditer(response)]
    cited_slugs = [m.group(1) for m in _ONISEP_SLUG_PAT.finditer(response)]

    def _check(cited: list[str], valid: set[str]) -> tuple[int, int, list[str]]:
        if not cited:
            return 0, 0, []
        valid_count = sum(1 for c in cited if c in valid)
        invalid = [c for c in cited if c not in valid]
        return valid_count, len(cited), invalid

    cod_valid, cod_total, cod_invalid = _check(cited_cod, cod_affs_corpus)
    rncp_valid, rncp_total, rncp_invalid = _check(cited_rncp, rncps_corpus)
    slug_valid, slug_total, slug_invalid = _check(cited_slugs, slugs_corpus)

    total = cod_total + rncp_total + slug_total
    valid = cod_valid + rncp_valid + slug_valid

    return {
        "score": (valid / total) if total > 0 else None,
        "total_citations": total,
        "valid_citations": valid,
        "invalid_citations": cod_invalid + rncp_invalid + slug_invalid,
        "breakdown": {
            "cod_aff_form": {"valid": cod_valid, "total": cod_total,
                             "invalid": cod_invalid},
            "rncp": {"valid": rncp_valid, "total": rncp_total,
                     "invalid": rncp_invalid},
            "onisep_slug": {"valid": slug_valid, "total": slug_total,
                            "invalid": slug_invalid},
        },
    }


# ============================================================
# Combined score for a response
# ============================================================


def score_response(response: str, corpus: list[dict]) -> dict:
    """Run all three metrics on a single response."""
    return {
        "actionability": score_actionability(response),
        "fraicheur": score_fraicheur(response),
        "citation_precision": score_citation_precision(response, corpus),
    }
