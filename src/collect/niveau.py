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

    # === Health formations — added in quality-gaps fix ===
    # Match by profession keyword directly (the "D.E." prefix is unreliable
    # — some names use "D.E. Infirmier", others "D.E Infirmier", or
    # "Masseur-Kinésithérapeute" without any prefix).
    # Kiné (DEMK) / Orthophoniste / Sage-femme / Maïeutique → bac+5
    if re.search(r"\b(?:kin[eé]sith[eé]rap|demk|orthophoniste|sage[-\s]femme|ma[iï]eutique)",
                 name):
        return "bac+5"
    # Infirmier / Ergothérapeute / Podologue / Manipulateur radio /
    # Psychomotricien / Audioprothésiste / Orthoptiste / Technicien labo médical → bac+3
    if re.search(r"\b(?:infirmier|infirmi[eè]re|ergoth[eé]rap|p[eé]dicure|podolog|"
                 r"psychomotric|audioproth|orthoptiste|"
                 r"technicien\s+de\s+laboratoire\s+m[eé]dical)",
                 name):
        return "bac+3"
    # Manipulateur radio/électroradiologie — nom variable, match en 2 temps
    if re.search(r"\bmanipulateur\b", name) and re.search(
            r"radiolog|[eé]lectroradiolog|imagerie\s+m[eé]dical", name):
        return "bac+3"
    # DTS (Diplôme de Technicien Supérieur — 3 ans, ex: Imagerie médicale)
    if re.search(r"\bdts\b", name):
        return "bac+3"
    # Certificat de capacité (orthoptiste, audioprothésiste) → 3 ans
    if re.search(r"certificat\s+de\s+capacit[eé]", name):
        return "bac+3"
    # PASS / L.AS — Parcours d'Accès Spécifique Santé / Licence Accès Santé
    # → bac+3 parce que partie du cursus licence (l'étudiant passe en L2/L3 ensuite)
    if re.search(r"\b(?:pass|p\.?a\.?s\.?s\.?|l\.?\s?as)\b", name):
        return "bac+3"

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
