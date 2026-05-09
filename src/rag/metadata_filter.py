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
import unicodedata
from dataclasses import dataclass
from typing import Any


def _norm_region(s: Any) -> str:
    """Normalise un libellé région : strip + lowercase + sans accents.

    Utilisé pour matcher des libellés produits par sources hétérogènes
    (Parcoursup avec accents 'Provence-Alpes-Côte d'Azur', RouterLLM
    avec accents stripped 'provence-alpes-cote d'azur', etc.).
    Étape 6 refonte router (2026-05-09) — fix audit Matteo écart 2.
    """
    if s is None:
        return ""
    s_str = str(s).strip().lower()
    return "".join(
        c for c in unicodedata.normalize("NFKD", s_str)
        if not unicodedata.combining(c)
    )


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


# Patterns niveau_scolaire → (niveau_min, niveau_max). Bac+N (0-6).
# Ordre matter : on prend le 1er match.
#
# CORRECTION Matteo via Jarvis 2026-04-29 : Mastère Spécialisé (MS) ≠ Master.
# - Master = diplôme national Bac+5 (M1+M2)
# - Mastère Spécialisé (MS) = label CGE post-Master, **Bac+6**
# Mastère pattern AVANT master pour éviter que `master` matche "mastere"
# via préfixe partagé (regex left-to-right).
NIVEAU_PATTERNS: list[tuple[re.Pattern[str], tuple[int, int]]] = [
    (re.compile(r"^(seconde|premiere)", re.IGNORECASE), (1, 3)),
    (re.compile(r"^terminale", re.IGNORECASE), (1, 5)),
    (re.compile(r"^(l1|bac\+?1)", re.IGNORECASE), (2, 5)),
    (re.compile(r"^(l2|bac\+?2|bts|but)", re.IGNORECASE), (2, 5)),
    (re.compile(r"^(l3|bac\+?3|licence)", re.IGNORECASE), (3, 5)),
    (re.compile(r"^(m1|bac\+?4)", re.IGNORECASE), (4, 5)),
    # Mastère Spé / MS / Bac+6 — formation ciblée niveau 6 (cycle court post-Master)
    (re.compile(r"^(mastere|mastère|ms\b|bac\+?6)", re.IGNORECASE), (6, 6)),
    # Master / M2 / Bac+5 — diplôme national, distinct du Mastère
    (re.compile(r"^(m2|bac\+?5|master)", re.IGNORECASE), (5, 5)),
    (re.compile(r"^(actif|professionnel|salarie|reconversion)", re.IGNORECASE), (2, 5)),
]


# ────────────────────────── Datatypes ──────────────────────────


@dataclass
class FilterCriteria:
    """Critères filtre v1+v2 — tous optionnels (None = pas de filtre).

    Étape 6 refonte router (2026-05-09) : ajout du champ `domain` pour
    permettre au RouterLLM de verrouiller un sous-ensemble de domaines
    (ex `["crous"]` quand la question est explicitement sur le logement
    étudiant). Cf docs/ADR-064-router-llm-leger.md.
    """

    region: str | None = None
    niveau_min: int | None = None
    niveau_max: int | None = None
    alternance: bool | None = None
    budget_max: int | None = None  # €/an
    secteur: list[str] | None = None  # liste OR
    # Étape 6 — domain lock (router-driven). Liste OR sur la valeur du
    # champ `domain` de chaque fiche (ex ['crous'], ['metier','metier_detail']).
    # None = pas de verrouillage par domaine (backward compat strict).
    domain: list[str] | None = None

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

    Étape 6 (2026-05-09) : matching insensible aux accents via
    _norm_region (fix audit Matteo écart 2). RouterLLM normalise les
    accents en sortie ('auvergne-rhone-alpes'), mais les libellés Parcoursup
    contiennent des accents ('Auvergne-Rhône-Alpes') → mismatch silencieux
    sans cette normalisation.
    """
    if c_region is None:
        return True
    if fiche_region is None:
        return True
    fr = _norm_region(fiche_region)
    if fr == "" or fr == "national":
        return True
    return fr == _norm_region(c_region)


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
    """`$in` secteur. Defensive : fiche sans secteur → passe (pass-through).

    Étape 11 fix critique (2026-05-09, audit Matteo mini-bench A/B) :
    bascule de la sémantique stricte (Sprint 10 design) → defensive
    (cohérent avec `_match_region`).

    Pourquoi : le RouterLLM (étape 6) populate `criteria.secteur` opportunistiquement
    pour toute question évoquant un domaine professionnel (informatique, droit, etc.).
    Or 0 / 15 764 fiches `formations` ont `secteur` populé dans le corpus v7
    (mesure 2026-05-09). Le filter strict `fiche_secteur is None → False`
    excluait donc 100 % des fiches `formations` dès que le router posait
    secteur=["informatique"], ce qui produisait des "Je n'ai pas de
    formation pertinente" sur 10/23 questions du mini-bench step 11
    (cf summary.md → 'ON refuse, OFF répond').

    Sémantique nouvelle : si la fiche n'a pas le champ `secteur`, on
    suppose qu'elle est compatible avec n'importe quel secteur demandé
    (defensive). Les fiches qui ont `secteur` populé continuent d'être
    matchées strictement. Cohérent avec `_match_region` qui a la même
    logique pour la région ('national' ou None → passe).

    Risque V2 : si Vague 4+ enrichit massivement `secteur`, le filter
    pourra à nouveau être strict via un flag opt-in `secteur_strict=True`
    sur FilterCriteria. Hors scope step 11.
    """
    if not c_secteurs:
        return True
    if fiche_secteur is None:
        # Defensive pass-through (fix step 11 — voir docstring)
        return True
    if isinstance(fiche_secteur, str):
        return fiche_secteur.strip().lower() in [s.strip().lower() for s in c_secteurs]
    if isinstance(fiche_secteur, (list, tuple, set)):
        fs_lower = [str(s).strip().lower() for s in fiche_secteur]
        c_lower = [s.strip().lower() for s in c_secteurs]
        return any(f in c_lower for f in fs_lower)
    # Type inattendu (int, dict, etc.) : conservateur, exclure
    return False


def _match_domain(fiche_domain: Any, c_domains: list[str] | None) -> bool:
    """`$in` domain (router-driven, étape 6).

    Step 11.7 (2026-05-10) — politique defensive corrigée.

    Bug observé via dump intermédiaire post-chantiers 1+2+4 (B1 "HEC 11/20") :
    le RouterLLM hallucine parfois `domain_lock=['metier']` sur des questions
    qui cherchent clairement une formation (HEC, Sciences Po, école...).
    L'ancien comportement strict (fiche.domain=None → exclu si 'formations'
    pas dans c_domains) faisait alors n_after_filter=0 → pipeline retourne
    fallback "pas de formation pertinente" alors que les fiches sont là.

    Politique step 11.7 : pass-through defensive si fiche.domain is None
    (cohérent avec _match_region step 11.7 et _match_secteur step 11
    fix précédent). Une fiche sans domain (= formation pure) passe TOUJOURS
    le filter, indépendamment de c_domains.

    Une fiche avec domain populé reste matchée strictement (mismatch
    explicite = exclusion). Pour une vraie restriction "uniquement domain X",
    le routing via sub_indexes (étape 5) donne déjà la sélection ciblée
    en amont — pas besoin que le filter aval soit strict.
    """
    if not c_domains:
        return True
    if fiche_domain is None:
        # Defensive pass-through (fix step 11.7 — voir docstring) :
        # fiche sans domain (= formation pure dans build_quad_subindexes)
        # passe TOUJOURS, peu importe c_domains.
        return True
    if not isinstance(fiche_domain, str):
        return False
    fd = fiche_domain.strip().lower()
    return fd in [d.strip().lower() for d in c_domains]


def _matches(fiche: dict[str, Any], c: FilterCriteria) -> bool:
    """Composite AND sur les 6 critères (region, niveau, alternance, budget,
    secteur, domain)."""
    return (
        _match_region(fiche.get("region"), c.region)
        and _match_niveau(fiche.get("niveau"), c.niveau_min, c.niveau_max)
        and _match_alternance(fiche.get("alternance"), c.alternance)
        and _match_budget(fiche.get("budget"), c.budget_max)
        and _match_secteur(fiche.get("secteur"), c.secteur)
        and _match_domain(fiche.get("domain"), c.domain)
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
