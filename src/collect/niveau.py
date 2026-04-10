"""Infer the French education level (bac+N) from a formation name.

Used by the merge pipeline to enrich fiches with a `niveau` field so the
re-ranking stage can prevent BTS-heavy queries from drowning out
higher-level programs.
"""
import re


def infer_niveau(formation_name: str) -> str | None:
    """Return 'bac+2', 'bac+3', 'bac+5', 'bac+8', or None.

    Matches case-insensitively on word boundaries. Falls through to the
    next check on no match. Default is None (unknown), which the reranker
    treats as a neutral level.
    """
    if not formation_name:
        return None
    name = formation_name.lower()

    # Doctorate level
    if re.search(r"\bdoctorat\b|\bphd\b|\bthese\b", name):
        return "bac+8"

    # bac+5 level — diplome d'ingenieur, master, mastère spécialisé
    if re.search(r"\bmaster\b|\bm1\b|\bm2\b|\bmast[eè]re\b|\bms\b|\bmsc\b", name):
        return "bac+5"
    if re.search(r"\bing[eé]nieur\b|\bing[eé]nierie\b", name) and not re.search(r"\bbachelor\b", name):
        # "ingenieur diplome" → bac+5, but "bachelor ingenierie" → bac+3
        return "bac+5"

    # bac+3 level — licence, BUT, bachelor
    if re.search(r"\bbachelor\b|\blicence\b|\bl3\b|\blicence pro\b", name):
        return "bac+3"
    if re.search(r"\bbut\b", name):
        return "bac+3"

    # bac+2 level — BTS, DUT, DEUST
    if re.search(r"\bbts\b|\bdut\b|\bdeust\b", name):
        return "bac+2"

    return None
