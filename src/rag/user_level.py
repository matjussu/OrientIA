"""Rule-based user level classifier — Tier 2.2 (2026-04-18).

Maps a French orientation question to one of 5 user level classes so
the prompt can adapt tone and content. The classifier is deterministic,
zero API cost, auditable. Order matters: reconversion first (strong
career/age markers), then master (M1/M2/bac+4/5), then licence
(L1-L3/BTS/BUT), then terminale, then inconnu as fallback.

Why rule-based, not a LLM classifier: cost-free, deterministic for the
benchmark, and trivially auditable for the study report. Edge cases
default to LEVEL_INCONNU rather than a wrong assumption — which is the
single most important invariant (infantilising a master student or
forcing Parcoursup on a reconversion is a worse UX failure than
being generic).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


LEVEL_TERMINALE = "terminale"
LEVEL_LICENCE = "licence"
LEVEL_MASTER = "master"
LEVEL_RECONVERSION = "reconversion"
LEVEL_INCONNU = "inconnu"


@dataclass(frozen=True)
class UserLevelGuidance:
    """Prompt-level tone guidance for a detected level. The
    tone_instruction is appended to the user prompt so the LLM adapts
    register / calendar references / pedagogical framing."""
    tone_instruction: str


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s)
        if not unicodedata.combining(c)
    )


# All patterns apply to a lowercase + accent-stripped question, so the
# regex alphabet is ASCII.

_PATTERNS_RECONVERSION = [
    re.compile(r"\breconver[st][a-z]*\b"),
    re.compile(r"\bchange(?:r)?\s+de\s+(?:metier|voie|carriere)\b"),
    re.compile(r"\bretour\s+aux?\s+etudes?\b"),
    re.compile(r"\breprendre\s+(?:des\s+)?etudes?\b"),
    re.compile(r"\btravaill(?:e|ais|ant)\s+depuis\s+\d+\s+ans?\b"),
    re.compile(r"\bapres\s+\d+\s+ans?\s+(?:comme|dans|en|de)\b"),
    re.compile(r"\bactuellement\s+en\s+poste\b"),
    re.compile(r"\bactuellement\s+(?:cadre|ingenieur|salarie|employe|employee)\b"),
    re.compile(r"\b(?:ancien|ancienne)\s+(?:cadre|ingenieur|salarie|comptable|infirmier|infirmiere)\b"),
    re.compile(r"\bj['e]\s*ai\s+(?:[3-6]\d|2[5-9])\s+ans\b"),
    re.compile(r"\ba\s+\d+\s+ans\s+(?:je|pour)\b"),
    re.compile(r"\bj['e]\s*ai\s+quitte\s+mon\s+(?:job|boulot|poste|travail|metier)\b"),
]

_PATTERNS_MASTER = [
    re.compile(r"\b(?:m1|m2)\b"),
    re.compile(r"\ben\s+master\b"),
    re.compile(r"\bmaster\s+[12]\b"),
    re.compile(r"\bdeuxieme\s+annee\s+de\s+master\b"),
    re.compile(r"\betudiant(?:e)?\s+(?:en\s+)?master\b"),
    re.compile(r"\bje\s+(?:suis|prepare|fais)\s+(?:un|en)\s+master\b"),
    re.compile(r"\bbac\s*\+\s*[45]\b"),
]

_PATTERNS_LICENCE = [
    re.compile(r"\b(?:l1|l2|l3)\b"),
    re.compile(r"\bje\s+suis\s+en\s+(?:l[123]|licence|bts|but|bachelor)\b"),
    re.compile(r"\betudiant(?:e)?\s+en\s+(?:licence|bts|but|bachelor)\b"),
    re.compile(r"\ben\s+\d(?:e|er|re|eme)\s+annee\s+de\s+(?:licence|bachelor|bts|but)\b"),
    re.compile(r"\bapres\s+ma\s+(?:l[123]|licence)\b"),
    re.compile(r"\bbac\s*\+\s*[123]\b"),
]

_PATTERNS_TERMINALE = [
    re.compile(r"\bterminale\b"),
    re.compile(r"\ben\s+tle\b"),
    re.compile(r"\blycee[a-z]*\b"),
    re.compile(r"\blyceen(?:ne)?\b"),
    re.compile(r"\bje\s+passe\s+(?:le|mon)\s+bac\b"),
    re.compile(r"\bparcoursup\s+(?:pour|en)\s+(?:juin|mars|avril|mai)\b"),
    re.compile(r"\bprepar(?:e|ation)\s+parcoursup\b"),
    re.compile(r"\bstrategie\s+parcoursup\b"),
    re.compile(r"\bj['e]\s*ai\s+1[67]\s+ans\b"),
    re.compile(r"\b(?:fils|fille)\s+(?:est\s+)?en\s+terminale\b"),
    re.compile(r"\bspecialites?\s+(?:pour|en)\b"),
]


def classify_user_level(question: str) -> str:
    """Return one of LEVEL_* constants for the given question.

    Order of precedence reflects signal strength: reconversion markers
    (career / age 25+) are unambiguous and win over any school-level
    mention; master markers (M1/M2) win over licence markers (which can
    appear in phrases like 'après ma licence'); terminale is the weakest
    since 'lycéen' / 'Parcoursup' can also appear in reconversion
    questions that mention the student's past.
    """
    if not question or not question.strip():
        return LEVEL_INCONNU

    norm = _strip_accents(question.lower())

    if any(p.search(norm) for p in _PATTERNS_RECONVERSION):
        return LEVEL_RECONVERSION
    if any(p.search(norm) for p in _PATTERNS_MASTER):
        return LEVEL_MASTER
    if any(p.search(norm) for p in _PATTERNS_LICENCE):
        return LEVEL_LICENCE
    if any(p.search(norm) for p in _PATTERNS_TERMINALE):
        return LEVEL_TERMINALE

    return LEVEL_INCONNU


_GUIDANCE: dict[str, UserLevelGuidance] = {
    LEVEL_TERMINALE: UserLevelGuidance(
        tone_instruction=(
            "Profil détecté : lycéen en terminale (environ 17 ans, "
            "candidat Parcoursup). Tutoiement, vocabulaire simple, "
            "références concrètes à son cadre (Parcoursup, bac, lycée). "
            "Évite le jargon RH/carrière. Calendrier Parcoursup pertinent."
        )
    ),
    LEVEL_LICENCE: UserLevelGuidance(
        tone_instruction=(
            "Profil détecté : étudiant en licence (bac+1 à bac+3). "
            "Tutoiement, langage courant. Parcoursup est derrière — "
            "les leviers sont admissions parallèles, passerelles, "
            "licences pro et masters. Moins de rappel sur les bases."
        )
    ),
    LEVEL_MASTER: UserLevelGuidance(
        tone_instruction=(
            "Profil détecté : étudiant en master (bac+4/5). Langage "
            "professionnel, références à l'insertion pro, à l'alternance, "
            "aux thèses CIFRE, aux concours post-master. Parcoursup est "
            "dépassé et non pertinent — ne pas y revenir."
        )
    ),
    LEVEL_RECONVERSION: UserLevelGuidance(
        tone_instruction=(
            "Profil détecté : reconversion professionnelle. Respecte "
            "l'expérience pro antérieure — pas d'infantilisation, pas "
            "de Plan A/B/C ado. Mentionne VAE/VAP/CPF quand pertinent, "
            "les formations courtes reconnues (RNCP), l'apprentissage "
            "adulte. Ton d'égal à égal, vouvoiement par défaut."
        )
    ),
    LEVEL_INCONNU: UserLevelGuidance(
        tone_instruction=(
            "Profil détecté : inconnu. N'assume aucune hypothèse sur "
            "l'âge, le niveau d'études ou l'expérience pro. Reste neutre "
            "et cadre ta réponse pour qu'elle soit utile quel que soit "
            "le profil. Si la question l'impose, pose une question de "
            "clarification courte au début pour cibler."
        )
    ),
}


def level_to_guidance(level: str) -> UserLevelGuidance:
    """Map a level constant to its prompt guidance. Unknown levels fall
    back to LEVEL_INCONNU so callers never crash on typos."""
    return _GUIDANCE.get(level, _GUIDANCE[LEVEL_INCONNU])
