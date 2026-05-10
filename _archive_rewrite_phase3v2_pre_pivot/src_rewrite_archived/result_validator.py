"""Garde-fous post-rewrite Claude (G1-G5) — ADR-060.

Pipeline ``is_rewrite_acceptable`` qui filtre les rewrites avant remplacement
du `text` original. Toute fiche qui échoue un garde-fou conserve son
``text_original`` en fallback.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

# -----------------------------------------------------------------------------
# Constantes
# -----------------------------------------------------------------------------

LENGTH_MIN_WORDS = 30
LENGTH_MAX_WORDS = 300

# Seuil ≥ 100 — capture les chiffres orientationnellement significatifs
# (effectifs, salaires en €, taux ×100, montants) sans être bloqué par les
# sous-comptes mineurs (« Cafétéria 434, Brasserie 28 ») que Claude peut
# légitimement compresser.
NUMBER_SIGNIFICANT_THRESHOLD = 100

# Codes officiels — strict match (case-insensitive substring)
ENTITY_FIELDS_STRICT_CODES = (
    "code_rome",
    "code_fap",
    "cs_code",
    "numero_fiche",
)

# Libellés — au moins un token significatif présent
ENTITY_FIELDS_LIBELLES = (
    "libelle_metier",
    "libelle",
    "fap_libelle",
    "cs_libelle",
    "intitule",
)

# Stopwords FR pour le scoring tokens libellés
_FR_STOPWORDS = {
    "avec", "dans", "pour", "sans", "leur", "leurs", "votre", "notre",
    "cette", "cettes", "celui", "celle", "elle", "elles", "ceux", "celles",
    "selon", "entre", "vers", "chez", "donc", "alors", "ainsi", "encore",
    "aussi", "mais", "telles", "tous", "toutes", "tout", "toute",
    "même", "mêmes", "très", "trop", "plus", "moins", "bien",
}

# Marqueurs d'extrapolation Claude → seuil 2 patterns max
HALLU_REDFLAGS = (
    "généralement",
    "souvent",
    "il est important",
    "il est crucial",
    "il convient",
    "il faut noter",
    "généralement reconnu",
)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _flatten_values(obj: Any) -> Iterable[Any]:
    """Yield every leaf value from a nested dict / list structure."""
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _flatten_values(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _flatten_values(v)
    else:
        yield obj


def _significant_source_numbers(fiche: dict) -> set[int]:
    """Tous les chiffres ≥ ``NUMBER_SIGNIFICANT_THRESHOLD`` dans la fiche.

    Exclut les booléens (sub-class de int en Python). Les floats sont
    tronqués à leur partie entière (les fractions DARES type 431.659
    milliers comptent comme 431).
    """
    out: set[int] = set()
    for v in _flatten_values(fiche):
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)):
            n = abs(int(v))
            if n >= NUMBER_SIGNIFICANT_THRESHOLD:
                out.add(n)
    return out


_NUMBER_TOKEN_RE = re.compile(r"\d{1,3}(?:[\s\u00a0]\d{3})+|\d+")


def _numbers_in_text(text: str) -> set[int]:
    """Tous les entiers ≥ 1 trouvés dans ``text``, en gérant les
    séparateurs de milliers en espace ou espace insécable.
    """
    out: set[int] = set()
    for match in _NUMBER_TOKEN_RE.findall(text):
        cleaned = match.replace(" ", "").replace("\u00a0", "")
        if cleaned:
            out.add(int(cleaned))
    return out


def _significant_libelle_tokens(libelle: str) -> list[str]:
    """Tokens ≥ 4 chars du libellé, hors stopwords."""
    raw = re.findall(r"\b\w{4,}\b", libelle, flags=re.UNICODE)
    return [t for t in raw if t.lower() not in _FR_STOPWORDS]


# -----------------------------------------------------------------------------
# G1 — length
# -----------------------------------------------------------------------------


def validate_length(rewritten_text: str) -> bool:
    """``LENGTH_MIN_WORDS`` ≤ nb mots ≤ ``LENGTH_MAX_WORDS``."""
    n_words = len(rewritten_text.split())
    return LENGTH_MIN_WORDS <= n_words <= LENGTH_MAX_WORDS


# -----------------------------------------------------------------------------
# G2 — numbers preserved
# -----------------------------------------------------------------------------


def validate_numbers_preserved(fiche_source: dict, rewritten_text: str) -> bool:
    """Tous les chiffres ≥ ``NUMBER_SIGNIFICANT_THRESHOLD`` du source
    sont présents dans le rewritten (tolérance "12 000" / "12000").
    """
    source_numbers = _significant_source_numbers(fiche_source)
    if not source_numbers:
        return True
    rewritten_numbers = _numbers_in_text(rewritten_text)
    missing = source_numbers - rewritten_numbers
    return not missing


# -----------------------------------------------------------------------------
# G3 — entities preserved
# -----------------------------------------------------------------------------


def validate_entities_preserved(fiche_source: dict, rewritten_text: str) -> bool:
    """Codes officiels (strict) + libellés (≥1 token significatif).

    - Codes (``code_rome``, ``code_fap``, ``cs_code``, ``numero_fiche``)
      doivent apparaître dans le rewritten en case-insensitive.
    - Libellés : au moins **un** token significatif (≥4 chars, hors
      stopwords FR) du libellé doit apparaître. Les libellés contenant
      « / » (formes m/f) sont OK même si une seule forme est conservée.
    """
    rewritten_lower = rewritten_text.lower()

    # Codes — strict
    for key in ENTITY_FIELDS_STRICT_CODES:
        v = fiche_source.get(key)
        if v is None:
            continue
        v_str = str(v).strip()
        if len(v_str) < 2:
            continue
        if v_str.lower() not in rewritten_lower:
            return False

    # Libellés — soft (≥1 token significatif)
    for key in ENTITY_FIELDS_LIBELLES:
        v = fiche_source.get(key)
        if not isinstance(v, str) or len(v.strip()) < 2:
            continue
        tokens = _significant_libelle_tokens(v)
        if not tokens:
            continue
        if not any(t.lower() in rewritten_lower for t in tokens):
            return False

    return True


# -----------------------------------------------------------------------------
# G4 — anti-hallu lexical
# -----------------------------------------------------------------------------


def validate_anti_hallu(rewritten_text: str) -> bool:
    """Ne pas dépasser 2 patterns d'extrapolation présents."""
    text_lower = rewritten_text.lower()
    n_red = sum(1 for w in HALLU_REDFLAGS if w in text_lower)
    return n_red <= 2


# -----------------------------------------------------------------------------
# G5 — format
# -----------------------------------------------------------------------------


def validate_format(rewritten_text: str) -> bool:
    """Pas de markdown / pipe / bullets multiples / double-newline.

    Détecte aussi la **quasi-copie verbatim** du format ancien : Haiku
    remplace parfois ``|`` par double-espace sans réellement rephraser.
    Symptômes :
    - >4 occurrences de double-espace consécutives
    - démarrage par un header stat type ``Salaires PCS NN :``,
      ``Métier ONISEP :``, ``Insertion BAC PRO —`` (factures du format v5)
    """
    if "**" in rewritten_text or "##" in rewritten_text:
        return False
    if "|" in rewritten_text:
        return False
    if "\n\n" in rewritten_text:
        return False
    if rewritten_text.count("- ") > 2:
        return False

    # Quasi-copie : double-espaces multiples = `|` simplement remplacé
    if rewritten_text.count("  ") > 4:
        return False

    # Quasi-copie : headers stat copiés du format v5
    head = rewritten_text.lstrip()[:60].lower()
    forbidden_starts = (
        "salaires pcs ",
        "métier onisep :",
        "metier onisep :",
        "métier rome ",
        "metier rome ",
        "insertion bac pro",
        "insertion bts",
        "insertion cap",
        "insertion mc4",
        "insertion doctorat",
        "insertion professionnelle mesr",
        "compétences certifiées (rncp",
        "competences certifiees (rncp",
        "vie étudiante crous",
        "vie etudiante crous",
        "marché du travail cadres",
        "marche du travail cadres",
        "métier 2030 ",
        "metier 2030 ",
        "bac pro en ",
        "parcours licence en ",
    )
    if any(head.startswith(p) for p in forbidden_starts):
        return False
    return True


# -----------------------------------------------------------------------------
# Pipeline
# -----------------------------------------------------------------------------


def is_rewrite_acceptable(
    fiche_source: dict, rewritten_text: str
) -> tuple[bool, list[str]]:
    """Retourne ``(accepted, issues)``.

    ``issues`` collecte tous les garde-fous échoués pour log/stats.
    """
    issues: list[str] = []
    if not validate_length(rewritten_text):
        n = len(rewritten_text.split())
        issues.append(
            f"length out of [{LENGTH_MIN_WORDS}, {LENGTH_MAX_WORDS}] words ({n})"
        )
    if not validate_numbers_preserved(fiche_source, rewritten_text):
        issues.append("missing significant numbers from source")
    if not validate_entities_preserved(fiche_source, rewritten_text):
        issues.append("missing named entities from source")
    if not validate_anti_hallu(rewritten_text):
        issues.append("anti-hallu redflags > 2")
    if not validate_format(rewritten_text):
        issues.append("invalid format (markdown / pipe / bullets)")
    return (len(issues) == 0, issues)
