"""Fallback déterministe du RouterLLM — utilisé quand le LLM fail.

Pattern : si `RouterLLM.route()` lève une exception (timeout, JSON
invalide, 5xx Mistral) ou retourne un payload manifestement cassé, on
appelle `deterministic_route()` à la place pour ne JAMAIS planter le
pipeline (passthrough non-bloquant calqué sur AnalystAgent ligne 177-180).

Couvre les patterns canoniques :
- Superlatifs ("meilleur·e", "top N", "classement", "best") → refusal
- Régions / villes françaises → `region` + `hardlock_region_strict`
- domain_hint déjà classifié → mapping vers sub_indexes + domain_lock
- Sinon : sub_indexes = tous (filet de sécurité), confidence = 0.4

Par construction, un fallback déterministe a une confidence basse
(0.4-0.7) pour signaler au pipeline que c'est un fallback. La logique
d'appel doit être : si `is_fallback=True`, le pipeline peut décider
d'élargir le filtrage (preferring recall over precision).

Cf docs/ADR-064-router-llm-leger.md.
"""
from __future__ import annotations

import re
from typing import Iterable

from src.rag.intent import (
    DOMAIN_HINT_APEC,
    DOMAIN_HINT_CALENDRIER,
    DOMAIN_HINT_COMPETENCES_CERTIF,
    DOMAIN_HINT_CROUS,
    DOMAIN_HINT_FINANCEMENT_ETUDES,
    DOMAIN_HINT_FORMATION_INSERTION,
    DOMAIN_HINT_INSEE_SALAIRE,
    DOMAIN_HINT_INSERTION_PRO,
    DOMAIN_HINT_METIER,
    DOMAIN_HINT_METIER_PROSPECTIVE,
    DOMAIN_HINT_PARCOURS,
    DOMAIN_HINT_TERRITOIRE_DROM,
    DOMAIN_HINT_VOIE_PRE_BAC,
    classify_domain_hint,
    classify_intent,
    INTENT_GEOGRAPHIC,
    _FRENCH_REGIONS,
    _strip_accents,
)
from src.rag.metadata_filter import FilterCriteria
from src.rag.router_llm import RouteDecision, SUB_INDEX_NAMES


# ────────────────────────── Mappings ──────────────────────────


# Mapping domain_hint → liste de sub_indexes à privilégier.
# Une question CROUS doit attaquer en priorité aides_territoires.
DOMAIN_HINT_TO_SUB_INDEXES: dict[str, list[str]] = {
    DOMAIN_HINT_METIER: ["metiers"],
    DOMAIN_HINT_METIER_PROSPECTIVE: ["metiers"],
    DOMAIN_HINT_PARCOURS: ["statistiques"],
    DOMAIN_HINT_APEC: ["statistiques"],
    DOMAIN_HINT_INSEE_SALAIRE: ["statistiques"],
    DOMAIN_HINT_INSERTION_PRO: ["statistiques"],
    DOMAIN_HINT_CROUS: ["aides_territoires"],
    DOMAIN_HINT_FINANCEMENT_ETUDES: ["aides_territoires"],
    DOMAIN_HINT_TERRITOIRE_DROM: ["aides_territoires"],
    DOMAIN_HINT_COMPETENCES_CERTIF: ["aides_territoires"],
    DOMAIN_HINT_CALENDRIER: ["aides_territoires"],
    DOMAIN_HINT_FORMATION_INSERTION: ["formations"],
    DOMAIN_HINT_VOIE_PRE_BAC: ["formations"],
}


# Mapping domain_hint → liste de `domain` exacts à verrouiller dans la fiche.
# Utilisé pour `domain_lock` quand l'intent est ferme sur le type d'objet.
DOMAIN_HINT_TO_DOMAIN_LOCK: dict[str, list[str]] = {
    DOMAIN_HINT_METIER: ["metier", "metier_detail"],
    DOMAIN_HINT_METIER_PROSPECTIVE: ["metier_prospective"],
    DOMAIN_HINT_PARCOURS: ["parcours_bacheliers"],
    DOMAIN_HINT_APEC: ["apec_region"],
    DOMAIN_HINT_INSEE_SALAIRE: ["insee_salaire"],
    DOMAIN_HINT_INSERTION_PRO: ["insertion_pro"],
    DOMAIN_HINT_CROUS: ["crous"],
    DOMAIN_HINT_FINANCEMENT_ETUDES: ["financement_etudes"],
    DOMAIN_HINT_TERRITOIRE_DROM: ["territoire_drom"],
    DOMAIN_HINT_COMPETENCES_CERTIF: ["competences_certif"],
    DOMAIN_HINT_CALENDRIER: ["calendrier"],
}


# Mapping ville → région canonique (pour quand la question dit "Lyon"
# mais le filtre region attend "auvergne-rhône-alpes"). Liste minimale
# couvrant les villes les plus fréquentes des questions OrientIA.
_CITY_TO_REGION: dict[str, str] = {
    "paris": "île-de-france",
    "lyon": "auvergne-rhône-alpes",
    "marseille": "provence-alpes-côte d'azur",
    "toulouse": "occitanie",
    "nice": "provence-alpes-côte d'azur",
    "nantes": "pays de la loire",
    "strasbourg": "grand est",
    "montpellier": "occitanie",
    "bordeaux": "nouvelle-aquitaine",
    "lille": "hauts-de-france",
    "rennes": "bretagne",
    "reims": "grand est",
    "saint-etienne": "auvergne-rhône-alpes",
    "toulon": "provence-alpes-côte d'azur",
    "grenoble": "auvergne-rhône-alpes",
    "dijon": "bourgogne-franche-comté",
    "angers": "pays de la loire",
    "nimes": "occitanie",
    "aix-en-provence": "provence-alpes-côte d'azur",
    "brest": "bretagne",
    "le mans": "pays de la loire",
    "amiens": "hauts-de-france",
    "tours": "centre-val de loire",
    "limoges": "nouvelle-aquitaine",
    "clermont-ferrand": "auvergne-rhône-alpes",
    "besancon": "bourgogne-franche-comté",
    "metz": "grand est",
    "perpignan": "occitanie",
    "orleans": "centre-val de loire",
    "mulhouse": "grand est",
    "rouen": "normandie",
    "caen": "normandie",
    "nancy": "grand est",
    "vannes": "bretagne",
    "lorient": "bretagne",
    "quimper": "bretagne",
    "la rochelle": "nouvelle-aquitaine",
    "pau": "nouvelle-aquitaine",
    "valence": "auvergne-rhône-alpes",
    "annecy": "auvergne-rhône-alpes",
    "chambery": "auvergne-rhône-alpes",
    "poitiers": "nouvelle-aquitaine",
    "avignon": "provence-alpes-côte d'azur",
    "calais": "hauts-de-france",
    "dunkerque": "hauts-de-france",
    "le havre": "normandie",
    "saint-nazaire": "pays de la loire",
}


# Région canonique normalisée — pour matcher le libellé du fiche.region.
# _FRENCH_REGIONS de intent.py contient les libellés courts (sans accents).
# Ici on accepte les deux formes (ancien + nouveau) avec mapping vers
# canonique INSEE post-2016.
_REGION_ALIASES: dict[str, str] = {
    "rhone-alpes": "auvergne-rhône-alpes",
    "auvergne": "auvergne-rhône-alpes",
    "provence": "provence-alpes-côte d'azur",
    "languedoc": "occitanie",
    "midi-pyrenees": "occitanie",
    "aquitaine": "nouvelle-aquitaine",
    "limousin": "nouvelle-aquitaine",
    "poitou": "nouvelle-aquitaine",
    "alsace": "grand est",
    "lorraine": "grand est",
    "champagne": "grand est",
    "franche-comte": "bourgogne-franche-comté",
    "bourgogne": "bourgogne-franche-comté",
    "nord": "hauts-de-france",
    "picardie": "hauts-de-france",
    "centre": "centre-val de loire",
}


# ────────────────────────── Patterns regex ──────────────────────────


# Superlatif : "meilleur(e)(s)", "le meilleur", "top N", "classement", "best"
# AUDIT 2026-05-08 : ce pattern est l'AJOUT clé identifié dans l'audit
# (intent.py ne le détecte PAS). Sans ce pattern, "meilleure école commerce"
# tombe en INTENT_GENERAL et le LLM fabrique une réponse.
_PATTERN_SUPERLATIVE = re.compile(
    r"\b("
    r"meilleur[ex]?s?"
    r"|meilleure[s]?"
    r"|le[s]?\s+meilleur[e]?[s]?"
    r"|la\s+meilleure"
    r"|top\s+\d+"
    r"|classement[s]?\b"
    r"|palmare[s]"
    r"|best"
    r"|n[°o]\s*1"
    r"|numero\s+un"
    r")\b"
)


# Patterns cross-domain conservatifs (haute spécificité, faible rappel
# attendu — le LLM fera mieux quand il sera dispo). On flag UNIQUEMENT
# les cas évidents pour éviter les faux positifs sur "métier de cuisinier"
# ou "que faire avec un BAC santé".
_PATTERN_CROSS_DOMAIN = re.compile(
    r"\b("
    r"comment\s+(?:soigner|guerir|diagnostiquer)"
    r"|recette\s+(?:de|pour)\b"
    r"|comment\s+(?:cuisiner|preparer)\b"
    r"|meteo\s+(?:de|pour|a)\b"
    r"|qui\s+est\s+(?:macron|le\s+president|trump|musk|biden)\b"
    r"|score\s+(?:de|du)\s+(?:psg|om|matchs?)\b"
    r")"
)


# ────────────────────────── Helpers ──────────────────────────


def _detect_region(question_norm: str) -> str | None:
    """Détecte une région française canonique dans la question normalisée.

    Priorité :
    1. Match direct sur région canonique post-2016 (ex 'bretagne', 'occitanie')
    2. Match sur alias historique (ex 'aquitaine' → 'nouvelle-aquitaine')
    3. Match sur ville (ex 'lyon' → 'auvergne-rhône-alpes')

    Returns:
        Libellé canonique normalisé (lowercase, sans accent pour matching
        downstream avec FilterCriteria.region) ou None.
    """
    tokens = re.findall(r"[a-z][a-z\-]+", question_norm)

    # 1. Région canonique directe (parmi les 13 régions post-2016 + DROM)
    canonical_regions = {
        "bretagne", "normandie", "occitanie", "corse",
        "ile-de-france", "auvergne-rhone-alpes", "auvergne-rhône-alpes",
        "provence-alpes-cote d'azur", "provence-alpes-côte d'azur",
        "hauts-de-france", "nouvelle-aquitaine", "grand est",
        "bourgogne-franche-comte", "bourgogne-franche-comté",
        "centre-val de loire", "pays de la loire",
        "guadeloupe", "martinique", "guyane", "la reunion", "la réunion",
        "mayotte",
    }
    for region in canonical_regions:
        if region in question_norm:
            # Retourne la version sans accent (cohérent avec strip_accents)
            return region

    # 2. Alias historiques → canonique
    for alias, canonical in _REGION_ALIASES.items():
        if alias in tokens or alias in question_norm:
            # On retourne le canonique (qui peut contenir des accents,
            # mais FilterCriteria.region est lowercase de toute façon)
            return _strip_accents(canonical)

    # 3. Ville → région
    for city, region in _CITY_TO_REGION.items():
        if city in tokens or city in question_norm:
            return _strip_accents(region)

    # 4. Région historique non-mappée (ex 'lorraine' isolé) → utiliser
    # _FRENCH_REGIONS d'intent.py
    for region in _FRENCH_REGIONS:
        if region in question_norm:
            # Pas dans les alias mappés → retourne tel quel (cas rare)
            return region

    return None


def _detect_superlative(question_norm: str) -> bool:
    """True si la question contient un superlatif sans données corpus.

    Détecte 'meilleur·e', 'top N', 'classement', 'best', 'palmares', etc.
    """
    return bool(_PATTERN_SUPERLATIVE.search(question_norm))


def _detect_cross_domain(question_norm: str) -> bool:
    """True si la question est manifestement hors-orientation.

    Pattern conservatif (haute précision, faible rappel) — n'attrape
    que les cas très évidents pour éviter les faux positifs.
    """
    return bool(_PATTERN_CROSS_DOMAIN.search(question_norm))


def _has_geographic_context(domain_hint: str | None, question_norm: str) -> bool:
    """True si la question impose une contrainte géographique forte.

    Conditions :
    - domain_hint = TERRITOIRE_DROM (toujours géographique fort)
    - OU une région/ville détectée + intent géographique
    """
    if domain_hint == DOMAIN_HINT_TERRITOIRE_DROM:
        return True
    return _detect_region(question_norm) is not None


# ────────────────────────── Entrée publique ──────────────────────────


def deterministic_route(question: str) -> RouteDecision:
    """Route déterministe — toujours non-bloquante (jamais d'exception).

    Stratégie :
    1. Question vide → fallback safe (tous sub_indexes, confidence 0.3)
    2. Cross-domain manifeste → refusal_reason='cross_domain', confidence 0.9
    3. Superlatif détecté → refusal_reason='superlative_no_data', confidence 0.9
    4. domain_hint matché par patterns intent.py existants → mapping
       sub_indexes + domain_lock + confidence 0.7
    5. Sinon : intent géographique seul → sub_indexes=['formations'] +
       region detected, confidence 0.6
    6. Fallback final : sub_indexes=tous, confidence 0.4 (filet de sécurité,
       le retrieval verra tout le corpus).

    Args:
        question: la question utilisateur brute (libre-forme).

    Returns:
        RouteDecision avec is_fallback=True.
    """
    if not question or not question.strip():
        return RouteDecision(
            sub_indexes=list(SUB_INDEX_NAMES),
            confidence=0.3,
            is_fallback=True,
        )

    norm = _strip_accents(question.lower())

    # Cas 2 : cross-domain manifeste
    if _detect_cross_domain(norm):
        from src.rag.router_llm import select_refusal_template
        rd = RouteDecision(
            sub_indexes=list(SUB_INDEX_NAMES),  # ignoré côté pipeline (refus)
            refusal_reason="cross_domain",
            confidence=0.9,
            is_fallback=True,
        )
        # Step 11.7 chantier 4 : variant template hash-selected
        rd.pre_written_response = select_refusal_template("cross_domain", question)
        return rd

    # Cas 3 : superlatif → refus structuré
    if _detect_superlative(norm):
        from src.rag.router_llm import select_refusal_template
        rd = RouteDecision(
            sub_indexes=list(SUB_INDEX_NAMES),  # ignoré côté pipeline (refus)
            refusal_reason="superlative_no_data",
            confidence=0.9,
            is_fallback=True,
        )
        rd.pre_written_response = select_refusal_template("superlative_no_data", question)
        return rd

    # Cas 4 : domain_hint matché par les patterns existants intent.py
    domain_hint = classify_domain_hint(question)
    region = _detect_region(norm)
    intent_label = classify_intent(question)

    if domain_hint is not None:
        sub_indexes = DOMAIN_HINT_TO_SUB_INDEXES.get(
            domain_hint, list(SUB_INDEX_NAMES)
        )
        domain_lock = DOMAIN_HINT_TO_DOMAIN_LOCK.get(domain_hint)

        criteria: FilterCriteria | None = None
        hardlock_region_strict = False
        if region:
            criteria = FilterCriteria(region=region)
            hardlock_region_strict = True

        return RouteDecision(
            sub_indexes=sub_indexes,
            criteria=criteria,
            domain_lock=domain_lock,
            hardlock_region_strict=hardlock_region_strict,
            hardlock_domain_strict=domain_lock is not None,
            top_k_override=12 if (region and domain_hint) else None,
            confidence=0.7,
            is_fallback=True,
        )

    # Cas 5 : intent géographique sans domain_hint → recherche formations
    # avec contrainte région. C'est le cas "ingé cyber Bretagne" sans
    # mots-clés CROUS / RNCP / etc.
    if intent_label == INTENT_GEOGRAPHIC and region:
        return RouteDecision(
            sub_indexes=["formations"],
            criteria=FilterCriteria(region=region),
            hardlock_region_strict=True,
            top_k_override=12,
            confidence=0.65,
            is_fallback=True,
        )

    # Cas 6 : fallback final — filet de sécurité (tous sub_indexes)
    return RouteDecision(
        sub_indexes=list(SUB_INDEX_NAMES),
        criteria=FilterCriteria(region=region) if region else None,
        confidence=0.4,
        is_fallback=True,
    )
