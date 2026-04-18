"""Rule-based intent classifier for student questions.

Maps a French orientation question to one of 7 intent classes. The
intent then drives a retrieval strategy (top_k_sources, mmr_lambda)
via intent_to_config().

Why rule-based: deterministic, zero API cost, auditable in the study
report. The 7 classes map cleanly to observable surface patterns
(comparison particles, geographic NER, grade mentions, etc.).

Order matters in classify_intent — checks are done from most specific
to least specific, with general as the catch-all fallback.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


INTENT_COMPARAISON = "comparaison"
INTENT_GEOGRAPHIC = "geographic"
INTENT_REALISME = "realisme"
INTENT_PASSERELLES = "passerelles"
INTENT_DECOUVERTE = "decouverte"
INTENT_CONCEPTUAL = "conceptual"
INTENT_GENERAL = "general"


@dataclass(frozen=True)
class IntentConfig:
    top_k_sources: int
    mmr_lambda: float


_CONFIGS: dict[str, IntentConfig] = {
    INTENT_GENERAL:     IntentConfig(top_k_sources=10, mmr_lambda=0.7),
    INTENT_COMPARAISON: IntentConfig(top_k_sources=12, mmr_lambda=0.6),
    INTENT_GEOGRAPHIC:  IntentConfig(top_k_sources=12, mmr_lambda=0.4),
    INTENT_REALISME:    IntentConfig(top_k_sources=6,  mmr_lambda=0.85),
    INTENT_PASSERELLES: IntentConfig(top_k_sources=10, mmr_lambda=0.6),
    INTENT_DECOUVERTE:  IntentConfig(top_k_sources=12, mmr_lambda=0.3),
    INTENT_CONCEPTUAL:  IntentConfig(top_k_sources=4,  mmr_lambda=0.9),
}


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s)
        if not unicodedata.combining(c)
    )


_FRENCH_CITIES = {
    "paris", "lyon", "marseille", "toulouse", "nice", "nantes", "strasbourg",
    "montpellier", "bordeaux", "lille", "rennes", "reims", "saint-etienne",
    "toulon", "grenoble", "dijon", "angers", "nimes", "villeurbanne",
    "aix-en-provence", "brest", "le mans", "amiens", "tours", "limoges",
    "clermont-ferrand", "besancon", "metz", "perpignan", "orleans",
    "mulhouse", "rouen", "caen", "nancy", "argenteuil", "boulogne-billancourt",
    "saint-denis", "vannes", "lorient", "quimper", "la rochelle", "pau",
    "valence", "annecy", "chambery", "poitiers", "avignon", "calais",
    "dunkerque", "le havre", "saint-nazaire",
}
_FRENCH_REGIONS = {
    "bretagne", "normandie", "alsace", "lorraine", "provence", "occitanie",
    "aquitaine", "auvergne", "bourgogne", "champagne", "franche-comte",
    "ile-de-france", "nord", "picardie", "pays de la loire", "rhone-alpes",
    "centre", "limousin", "poitou", "languedoc", "corse", "midi-pyrenees",
}


_PATTERNS_COMPARAISON_NORM = [
    re.compile(r"\bcompar(e[rz]?|aison)\b"),
    re.compile(r"\bdifferenc[a-z]*\s+entre\b"),
    re.compile(r"\bvaut[\s-]il\s+mieux\b"),
    re.compile(r"\bplutot que\b"),
    re.compile(r"\bmieux\s+(?:que|entre)\b"),
]
# Detected on the ORIGINAL question (case-sensitive) — catches the
# "EPITA ou EPITECH" / "INSA et CENTRALE" pattern where both sides
# are named institutions written as acronyms.
_PATTERNS_COMPARAISON_RAW = [
    re.compile(r"\b[A-Z][A-Z\-]{2,}\s+(?:ou|et)\s+[A-Z][A-Z\-]{2,}\b"),
]

_PATTERNS_REALISME = [
    re.compile(r"\b\d{1,2}[,.]?\d?\s+de\s+moyenne\b"),
    re.compile(r"\bavec\s+\d{1,2}\b"),
    re.compile(r"\btaux\s+(?:d['e]\s*)?(?:admission|acceptation|reussite)\b"),
    re.compile(r"\bselectivit[a-z]*\b"),
    re.compile(r"\baccessib[a-z]*\b"),
    re.compile(r"\b(?:est-ce que je peux|ai-je une chance|suis-je accept[a-z]+|puis-je integrer)\b"),
    re.compile(r"\bdossier\s+(?:moyen|faible|bon)\b"),
]

_PATTERNS_PASSERELLES = [
    re.compile(r"\breorient[a-z]*\b"),
    re.compile(r"\breconvers[a-z]*\b"),
    re.compile(r"\bpasserelle[sx]?\b"),
    re.compile(r"\bchanger\s+de\s+(?:filiere|voie|domaine|orientation)\b"),
    re.compile(r"\bapres\s+(?:mon|mes|\d)\s+(?:ans?|annee)"),
    re.compile(r"\btransition\s+(?:vers|professionnelle)\b"),
]

_PATTERNS_DECOUVERTE = [
    re.compile(r"\bquels metiers\b"),
    re.compile(r"\bdecouvr[a-z]*\b"),
    re.compile(r"\bmeconnu[sx]?\b"),
    re.compile(r"\boriginal[a-z]*\b"),
    re.compile(r"\bpiste[sx]?\b"),
    re.compile(r"\bj['e]\s*aime\b"),
    re.compile(r"\bje\s+(?:suis\s+)?(?:curieu[xs]|interess[a-z]+|passionn[a-z]+)\b"),
    re.compile(r"\bje\s+m['e]\s*interesse\s+(?:a|au|aux)\b"),
    re.compile(r"\bpropose[\-z]?[\-z]?moi\b"),
]

_PATTERNS_CONCEPTUAL = [
    re.compile(r"\bc['e]\s*est\s+quoi\b"),
    re.compile(r"\bqu['e]\s*est-ce\b"),
    re.compile(r"\bcomment\s+fonctionne\b"),
    re.compile(r"\bexpli(?:que[rz]?|cation)\b"),
    re.compile(r"\bdefini(?:tion|s|r)\b"),
]


def _has_geographic_marker(question_norm: str) -> bool:
    """Detect a French city or region by token match. Uses a closed
    set rather than NER for speed and determinism."""
    tokens = re.findall(r"[a-z][a-z\-]+", question_norm)
    if any(t in _FRENCH_CITIES for t in tokens):
        return True
    for region in _FRENCH_REGIONS:
        if region in question_norm:
            return True
    return False


def classify_intent(question: str) -> str:
    """Return one of the INTENT_* constants for the given question."""
    if not question or not question.strip():
        return INTENT_GENERAL

    norm = _strip_accents(question.lower())

    # Specific patterns first — order matters where intents could
    # overlap (e.g. a comparison between two cities should still be
    # classified as comparaison, not geographic).
    if any(p.search(norm) for p in _PATTERNS_COMPARAISON_NORM):
        return INTENT_COMPARAISON
    if any(p.search(question) for p in _PATTERNS_COMPARAISON_RAW):
        return INTENT_COMPARAISON

    # Realisme: grade mentions and selectivity language are unambiguous.
    if any(p.search(norm) for p in _PATTERNS_REALISME):
        return INTENT_REALISME

    if any(p.search(norm) for p in _PATTERNS_PASSERELLES):
        return INTENT_PASSERELLES

    if any(p.search(norm) for p in _PATTERNS_CONCEPTUAL):
        return INTENT_CONCEPTUAL

    if any(p.search(norm) for p in _PATTERNS_DECOUVERTE):
        return INTENT_DECOUVERTE

    # Geographic last because a city mention inside a comparison or
    # realisme question shouldn't override the more specific intent.
    if _has_geographic_marker(norm):
        return INTENT_GEOGRAPHIC

    return INTENT_GENERAL


def intent_to_config(intent: str) -> IntentConfig:
    """Map an intent class to its retrieval strategy. Unknown intents
    fall back to INTENT_GENERAL so callers never crash on typos."""
    return _CONFIGS.get(intent, _CONFIGS[INTENT_GENERAL])


# --- Tier 2.3 : format guidance injected into the user prompt ---

_FORMAT_GUIDANCE: dict[str, str] = {
    INTENT_COMPARAISON: (
        "Type de question détecté : comparaison. Utilise obligatoirement "
        "un tableau côte-à-côte pour contraster les options, pas un "
        "Plan A/B/C. Termine par une synthèse de 2-3 lignes qui oriente "
        "selon le profil."
    ),
    INTENT_CONCEPTUAL: (
        "Type de question détecté : conceptuelle / définitionnelle. "
        "Réponds de façon didactique et concise (100-200 mots). Pas de "
        "Plan A/B/C, pas de fiches comme exemples — explique le concept, "
        "son fonctionnement, et les cas typiques."
    ),
    INTENT_DECOUVERTE: (
        "Type de question détecté : découverte / exploration. Les fiches "
        "couvrent cyber / data / santé — si la question sort de ces "
        "domaines, sors du corpus et propose en (connaissance générale) "
        "des métiers interdisciplinaires ou au-delà du périmètre actuel. "
        "Ne restreins pas la réponse aux seules fiches disponibles."
    ),
    INTENT_REALISME: (
        "Type de question détecté : réalisme / faisabilité. Sois direct "
        "et cash sur la faisabilité du projet. Appuie-toi sur les taux, "
        "les chiffres, les profils admis. Si l'objectif n'est pas réaliste, "
        "dis-le d'abord, puis propose des alternatives chiffrées."
    ),
    INTENT_GEOGRAPHIC: (
        "Type de question détecté : géographique. Privilégie la proximité "
        "demandée, mais cite au moins 3 villes distinctes si la question "
        "laisse du jeu. Mentionne les distances ou temps de transport "
        "quand pertinent."
    ),
    INTENT_PASSERELLES: (
        "Type de question détecté : passerelles / réorientation. Décris "
        "les chemins intermédiaires étape par étape (Étape 1 → Étape 2 → "
        "Étape 3). Inclus admissions parallèles, VAE/VAP, validation "
        "d'acquis, calendriers clés."
    ),
    INTENT_GENERAL: (
        "Type de question détecté : générale. Structure en Plan A/B/C "
        "condensé (1-2 lignes par plan). Termine par une section "
        "« Attention aux pièges » (1-3 puces)."
    ),
}


def intent_to_format_guidance(intent: str) -> str:
    """Map an intent class to a format hint injected into the user
    prompt. The rules themselves are in SYSTEM_PROMPT — this classifier
    only tells the LLM which rule applies. Unknown intents fall back
    to INTENT_GENERAL."""
    return _FORMAT_GUIDANCE.get(intent, _FORMAT_GUIDANCE[INTENT_GENERAL])
