"""Metadata filter for retrieval — Sprint 10 chantier C.

Filtre Mongo-style appliqué APRÈS FAISS top-k (Option B du design ADR
docs/SPRINT10_RAG_FILTRE_DESIGN.md). 5 critères v1 : region, niveau,
alternance, budget, secteur. Tous optionnels (None = pas de filtre).

Source des critères : `profile_delta` produit par AnalystAgent (PR #100).

Skeleton v1 : §8.1 + §8.2 du design. Plug pipeline (§8.3+) en attente
review Matteo + chantier B (textualisation ONISEP/RNCP frontmatter).
"""
from __future__ import annotations

import dataclasses
import re
from dataclasses import dataclass
from typing import Any


# ────────────────────────── Lookup tables ──────────────────────────


BUDGET_BRACKETS: dict[str, int | None] = {
    "low": 2000,
    "moderate": 5000,
    "high": None,  # pas de borne sup
}

# Mapping intérêts AnalystAgent → secteurs canoniques (à enrichir au fil
# des logs sessions réelles — cf §9 risque "mapping incomplet").
INTERESTS_TO_SECTORS: dict[str, list[str]] = {
    "informatique": ["informatique", "numerique"],
    "code": ["informatique", "numerique"],
    "programmation": ["informatique", "numerique"],
    "developpement": ["informatique", "numerique"],
    "cybersecurite": ["informatique", "securite"],
    "data": ["informatique", "data_science"],
    "ia": ["informatique", "data_science"],
    "ingenierie": ["ingenierie", "industriel"],
    "mecanique": ["ingenierie", "industriel"],
    "electronique": ["ingenierie", "industriel"],
    "biologie": ["sante", "vivant"],
    "medecine": ["sante"],
    "pharmacie": ["sante"],
    "psychologie": ["psychologie", "sante"],
    "droit": ["droit", "juridique"],
    "justice": ["droit", "juridique"],
    "marketing": ["commerce", "communication"],
    "communication": ["commerce", "communication"],
    "commerce": ["commerce"],
    "finance": ["finance", "economie"],
    "economie": ["finance", "economie"],
    "art": ["art", "design"],
    "design": ["design", "art"],
    "lettres": ["lettres", "humanites"],
    "histoire": ["histoire", "humanites"],
    "langues": ["langues", "humanites"],
    "sport": ["sport"],
    "education": ["education", "enseignement"],
    "enseignement": ["education", "enseignement"],
}


# Patterns niveau_scolaire → (niveau_min, niveau_max). Bac+N (1-5).
# Ordre matter : on prend le 1er match.
NIVEAU_PATTERNS: list[tuple[re.Pattern[str], tuple[int, int]]] = [
    (re.compile(r"^(seconde|premiere)", re.IGNORECASE), (1, 3)),
    (re.compile(r"^terminale", re.IGNORECASE), (1, 5)),
    (re.compile(r"^(l1|bac\+?1)", re.IGNORECASE), (2, 5)),
    (re.compile(r"^(l2|bac\+?2|bts|but)", re.IGNORECASE), (2, 5)),
    (re.compile(r"^(l3|bac\+?3|licence)", re.IGNORECASE), (3, 5)),
    (re.compile(r"^(m1|bac\+?4)", re.IGNORECASE), (4, 5)),
    (re.compile(r"^(m2|bac\+?5|master)", re.IGNORECASE), (5, 5)),
    (re.compile(r"^(actif|professionnel|salarie|reconversion)", re.IGNORECASE), (2, 5)),
]


# ────────────────────────── Datatypes ──────────────────────────


@dataclass
class FilterCriteria:
    """Critères filtre v1 — tous optionnels (None = pas de filtre)."""

    region: str | None = None
    niveau_min: int | None = None
    niveau_max: int | None = None
    alternance: bool | None = None
    budget_max: int | None = None  # €/an
    secteur: list[str] | None = None  # liste OR

    def is_empty(self) -> bool:
        """True si tous critères None (équivaut à pas de filtre)."""
        return all(
            getattr(self, f.name) is None for f in dataclasses.fields(self)
        )


# ────────────────────────── Parsing utilitaires ──────────────────────────


def parse_contraintes(items: list[str]) -> dict[str, str]:
    """Parse les `contraintes: list[str]` AnalystAgent format `clé:valeur`.

    Edge cases :
    - item sans `:` → ignoré silencieusement
    - item avec multiple `:` → split sur le premier (`region:auvergne-rhone-alpes` OK)
    - clés et valeurs trim + lowercase
    """
    out: dict[str, str] = {}
    for item in items:
        if not isinstance(item, str) or ":" not in item:
            continue
        key, val = item.split(":", 1)
        out[key.strip().lower()] = val.strip().lower()
    return out


def normalize_region(region: str | None) -> str | None:
    """Normalise libellé région (lowercase, trim, fallback None sur empty)."""
    if not region:
        return None
    s = region.strip().lower()
    return s if s else None


def infer_niveau_range(niveau_scolaire: str | None) -> tuple[int | None, int | None]:
    """Mappe niveau_scolaire libre-forme → range (niveau_min, niveau_max).

    Voir tableau §3.2 du design. Fallback (None, None) si aucun pattern ne match.
    """
    if not niveau_scolaire:
        return (None, None)
    for pattern, range_tuple in NIVEAU_PATTERNS:
        if pattern.search(niveau_scolaire):
            return range_tuple
    return (None, None)


def infer_secteurs(interets_detectes: list[str]) -> list[str] | None:
    """Mappe les intérêts détectés vers la liste de secteurs candidats.

    Returns None si aucun intérêt mappé (équivaut à pas de filter sur secteur).
    """
    if not interets_detectes:
        return None
    out: set[str] = set()
    for interest in interets_detectes:
        if not isinstance(interest, str):
            continue
        key = interest.strip().lower()
        secteurs = INTERESTS_TO_SECTORS.get(key)
        if secteurs:
            out.update(secteurs)
    return sorted(out) if out else None


def parse_alternance_value(val: str | None) -> bool | None:
    """Parse la valeur 'alternance' du contraintes dict en bool optional.

    'true'/'1'/'yes'/'oui' → True
    'false'/'0'/'no'/'non' → False
    autre / None → None (pas de filter)
    """
    if val is None:
        return None
    v = val.strip().lower()
    if v in ("true", "1", "yes", "oui"):
        return True
    if v in ("false", "0", "no", "non"):
        return False
    return None


# ────────────────────────── Extraction profile → criteria ──────────────────────────


def extract_filter_from_profile(profile_delta: dict[str, Any]) -> FilterCriteria:
    """Extrait les FilterCriteria depuis un profile_delta AnalystAgent.

    Robuste aux clés manquantes : un profile vide → FilterCriteria.is_empty() == True.
    """
    contraintes_dict = parse_contraintes(profile_delta.get("contraintes") or [])
    niveau_min, niveau_max = infer_niveau_range(profile_delta.get("niveau_scolaire"))
    return FilterCriteria(
        region=normalize_region(profile_delta.get("region")),
        niveau_min=niveau_min,
        niveau_max=niveau_max,
        alternance=parse_alternance_value(contraintes_dict.get("alternance")),
        budget_max=BUDGET_BRACKETS.get(contraintes_dict.get("budget", "")),
        secteur=infer_secteurs(profile_delta.get("interets_detectes") or []),
    )


# ────────────────────────── Filter application ──────────────────────────


def _match_region(fiche_region: Any, c_region: str | None) -> bool:
    """`$eq` avec passe-toujours pour fiche_region == 'national' ou None.

    Asymétrie defensive (§5.2 design) : fiche sans région → on prend
    (formations nationales + manque d'info ≠ exclusion automatique).
    """
    if c_region is None:
        return True
    if fiche_region is None:
        return True
    fr = str(fiche_region).strip().lower()
    if fr == "" or fr == "national":
        return True
    return fr == c_region.strip().lower()


def _match_niveau(
    fiche_niveau: Any, c_min: int | None, c_max: int | None
) -> bool:
    """`$gte/$lte` range. Fiche sans niveau → defensive pass-through."""
    if c_min is None and c_max is None:
        return True
    if fiche_niveau is None:
        return True
    try:
        n = int(fiche_niveau)
    except (TypeError, ValueError):
        return True
    if c_min is not None and n < c_min:
        return False
    if c_max is not None and n > c_max:
        return False
    return True


def _match_alternance(fiche_alt: Any, c_alt: bool | None) -> bool:
    """`$eq` bool. Asymétrie : fiche sans info → exclue (contrainte stricte)."""
    if c_alt is None:
        return True
    if fiche_alt is None:
        return False
    return bool(fiche_alt) == c_alt


def _match_budget(fiche_budget: Any, c_max: int | None) -> bool:
    """`$lte` budget €/an. Fiche sans budget → defensive pass-through."""
    if c_max is None:
        return True
    if fiche_budget is None:
        return True
    try:
        b = int(fiche_budget)
    except (TypeError, ValueError):
        return True
    return b <= c_max


def _match_secteur(fiche_secteur: Any, c_secteurs: list[str] | None) -> bool:
    """`$in` secteur. Asymétrie : fiche sans secteur → exclue (contrainte stricte)."""
    if not c_secteurs:
        return True
    if fiche_secteur is None:
        return False
    if isinstance(fiche_secteur, str):
        return fiche_secteur.strip().lower() in [s.strip().lower() for s in c_secteurs]
    if isinstance(fiche_secteur, (list, tuple, set)):
        fs_lower = [str(s).strip().lower() for s in fiche_secteur]
        c_lower = [s.strip().lower() for s in c_secteurs]
        return any(f in c_lower for f in fs_lower)
    return False


def _matches(fiche: dict[str, Any], c: FilterCriteria) -> bool:
    """Composite AND sur les 5 critères."""
    return (
        _match_region(fiche.get("region"), c.region)
        and _match_niveau(fiche.get("niveau"), c.niveau_min, c.niveau_max)
        and _match_alternance(fiche.get("alternance"), c.alternance)
        and _match_budget(fiche.get("budget"), c.budget_max)
        and _match_secteur(fiche.get("secteur"), c.secteur)
    )


def apply_metadata_filter(
    fiches_with_score: list[dict[str, Any]],
    criteria: FilterCriteria,
) -> list[dict[str, Any]]:
    """Filtre les résultats retrievés sur les critères. Préserve l'ordre.

    Args:
        fiches_with_score: list[dict] avec clés "fiche" (le dict formation
            avec frontmatter region/niveau/alternance/budget/secteur) et
            "score" (float). Format compatible `retrieve_top_k`.
        criteria: FilterCriteria.

    Returns:
        Sous-liste filtrée (l'ordre du retrieved est conservé). Si
        `criteria.is_empty()`, retourne la liste intacte (pas de copie).
    """
    if criteria.is_empty():
        return fiches_with_score
    return [item for item in fiches_with_score if _matches(item.get("fiche") or {}, criteria)]
