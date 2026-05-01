"""Mapping rules libre-forme Sprint 9 → enums Pydantic Axe 2.

Référence ordre : 2026-05-01-1820-claudette-orientia-sprint12-axe-2-agentic-phase-1-A1-A2-A4 (A2).

Convertit un `UserSessionProfile` (Sprint 9 hierarchical, libre-forme
structuré) en `ProfileState` (Axe 2, enum-routable). **Déterministe,
pure-function, $0 supplémentaire** — pas d'appel Mistral, on capitalise
le travail déjà fait par `AnalystAgent.update_profile()`.

## Choix design

- **Mapping rules string-based** (regex / startswith) sur
    `niveau_scolaire` libre-forme structuré documenté Sprint 9
    (e.g. `"terminale_spe_maths_physique"`, `"l1_droit_redoublement"`).
- **Fallback `OTHER_OR_UNKNOWN` / `UNKNOWN` / `OTHER`** si pattern non
    matché → pas d'invention, transparence sur la limite.
- **`intent_type` heuristique** sur `user_query` (mot-clé matching) —
    Phase 1 minimal acceptable, à remplacer Phase 2 par classifier
    LLM dédié si bench S4 GO.
- **`urgent_concern` heuristique** sur valeurs/questions_ouvertes
    (mots-clés "stress", "peur", "urgence", "perdu·e").

## Fonctions publiques

- `map_niveau_scolaire_to_education_level(niveau_str) → EducationLevel`
- `map_niveau_scolaire_to_age_group(niveau_str, age_estime) → AgeGroup`
- `infer_intent_type(user_query) → IntentType`
- `infer_urgent_concern(valeurs, questions_ouvertes, user_query) → bool`
- `derive_profile_state(session, user_query) → ProfileState` —
    fonction de bout-en-bout invoquée par `AnalystAgent.analyze_for_routing()`
"""
from __future__ import annotations

import re
import unicodedata

from src.agents.hierarchical.session import Session
from src.axe2.contracts import (
    AgeGroup,
    EducationLevel,
    IntentType,
    ProfileState,
)


# ---------- niveau_scolaire → EducationLevel ----------

# Mapping ordonné : on teste les patterns plus spécifiques d'abord.
# Les patterns sont anchored startswith() ou substring selon clarté.
_EDUCATION_LEVEL_PATTERNS: list[tuple[re.Pattern, EducationLevel]] = [
    # Patterns appliqués sur niveau normalisé (`_` → ` `, lower).
    (re.compile(r"\b(?:doctorat|phd|these)\b"), EducationLevel.BAC_PLUS_8_DOCTORAT),
    (re.compile(r"\bm2\b|\bmaster\s+2\b"), EducationLevel.BAC_PLUS_5),
    (re.compile(r"\bm1\b|\bmaster\s+1\b"), EducationLevel.BAC_PLUS_4),
    (re.compile(r"\bmaster\b"), EducationLevel.BAC_PLUS_5),
    (re.compile(r"\bl3\b|\blicence\s+3\b"), EducationLevel.BAC_PLUS_3),
    (re.compile(r"\bl2\b|\blicence\s+2\b"), EducationLevel.BAC_PLUS_2),
    (re.compile(r"\bl1\b|\blicence\s+1\b"), EducationLevel.BAC_PLUS_1),
    (re.compile(r"\b(?:bts|but|dut)\b"), EducationLevel.BAC_PLUS_2),
    (re.compile(r"\bprepa\b"), EducationLevel.BAC_PLUS_1),
    (re.compile(r"\bterminale\b|\bterm\b"), EducationLevel.TERMINALE),
    (re.compile(r"\b(?:premiere|seconde|2nde|1ere)\b"), EducationLevel.INFRA_BAC),
    (re.compile(r"\bbac\+5\b"), EducationLevel.BAC_PLUS_5),
    (re.compile(r"\bbac\+4\b"), EducationLevel.BAC_PLUS_4),
    (re.compile(r"\bbac\+3\b"), EducationLevel.BAC_PLUS_3),
    (re.compile(r"\bbac\+2\b"), EducationLevel.BAC_PLUS_2),
    (re.compile(r"\bbac\+1\b"), EducationLevel.BAC_PLUS_1),
    (re.compile(r"\bbachelier\b|\bbac\b"), EducationLevel.BAC_OBTENU),
    (re.compile(r"\bprofessionnel\b|\bpro\s+actif\b|\bsalarie\b"), EducationLevel.PROFESSIONNEL_ACTIF),
]


def _strip_accents(s: str) -> str:
    """Supprime les accents Unicode pour matching robuste FR.

    `é` → `e`, `à` → `a`, etc. Préserve `+` (utile pour bac+5).
    """
    return "".join(
        c for c in unicodedata.normalize("NFKD", s)
        if not unicodedata.combining(c)
    )


def _normalize_for_boundary(niveau: str) -> str:
    """Transforme `_` → ` ` ET strip accents pour que `\\b` regex
    fonctionne sur les tokens séparés par underscore et tolère les
    accents FR.

    `_` étant un word-char en regex Python, `\\bterminale\\b` ne matche
    pas dans `terminale_spe_maths_physique` sans cette normalisation.
    """
    return _strip_accents(niveau.lower().replace("_", " "))


def map_niveau_scolaire_to_education_level(niveau: str | None) -> EducationLevel:
    """Convertit niveau_scolaire libre-forme → EducationLevel enum.

    Retourne `UNKNOWN` si pattern non matché ou input None/vide.
    """
    if not niveau:
        return EducationLevel.UNKNOWN
    text = _normalize_for_boundary(niveau)
    for pattern, level in _EDUCATION_LEVEL_PATTERNS:
        if pattern.search(text):
            return level
    return EducationLevel.UNKNOWN


# ---------- niveau_scolaire + age_estime → AgeGroup ----------


def map_niveau_scolaire_to_age_group(
    niveau: str | None,
    age_estime: int | None = None,
) -> AgeGroup:
    """Convertit niveau_scolaire libre-forme (+ optionnellement age_estime)
    → AgeGroup enum.

    Logique :
    1. Patterns lycéens explicites (terminale, premiere, seconde) → bachelier_*
        ou lyceen_terminale selon contexte
    2. Patterns post-bac (l1/l2/l3 → etudiant_l1_l3, m1/m2 → etudiant_master)
    3. Patterns professionnels → professionnel_actif
    4. Fallback age_estime si fourni
    5. OTHER_OR_UNKNOWN sinon
    """
    if niveau:
        nl = _normalize_for_boundary(niveau)

        # Lycéens (terminale + spé bac type)
        if re.search(r"\bterminale\b|\bterm\b", nl):
            if re.search(r"\b(?:techno|sti2d|stmg|st2s)\b", nl):
                return AgeGroup.BACHELIER_TECHNO
            if re.search(r"\bpro\b|\bprofessionnelle?\b", nl):
                return AgeGroup.BACHELIER_PRO
            return AgeGroup.LYCEEN_TERMINALE

        if re.search(r"\b(?:seconde|2nde|premiere|1ere)\b", nl):
            return AgeGroup.LYCEEN_2NDE

        # Post-bac universitaire
        if re.search(r"\b(?:l1|l2|l3)\b|\blicence\b", nl):
            return AgeGroup.ETUDIANT_L1_L3
        if re.search(r"\b(?:m1|m2|master)\b", nl):
            return AgeGroup.ETUDIANT_MASTER
        if re.search(r"\b(?:doctorat|phd|these)\b", nl):
            return AgeGroup.ETUDIANT_MASTER  # approximation, pas d'enum doctorat

        # BUT/BTS/DUT/Prépa → bachelier_general (post-bac court)
        if re.search(r"\b(?:bts|but|dut|prepa)\b", nl):
            return AgeGroup.BACHELIER_GENERAL

        # Professionnels actifs
        if re.search(r"\bprofessionnel\b|\bsalarie\b|\bpro\s+actif\b", nl):
            return AgeGroup.PROFESSIONNEL_ACTIF

        if re.search(r"\bparent\b", nl):
            return AgeGroup.PARENT_LYCEEN

    # Fallback age_estime si fourni et pas de niveau matché
    if isinstance(age_estime, int):
        if age_estime <= 16:
            return AgeGroup.LYCEEN_2NDE
        if age_estime <= 18:
            return AgeGroup.LYCEEN_TERMINALE
        if age_estime <= 22:
            return AgeGroup.ETUDIANT_L1_L3
        if age_estime <= 25:
            return AgeGroup.ETUDIANT_MASTER
        if age_estime <= 45:
            return AgeGroup.ADULTE_25_45

    return AgeGroup.OTHER_OR_UNKNOWN


# ---------- user_query → IntentType (heuristique) ----------

# Patterns ordonnés : plus spécifique d'abord. Si plusieurs matchent, on
# prend le premier.
_INTENT_PATTERNS: list[tuple[re.Pattern, IntentType]] = [
    (re.compile(
        r"\b(?:reconvertir|reconversion|changer\s+de\s+carriere|changement\s+de\s+metier)\b",
        re.IGNORECASE,
    ), IntentType.RECONVERSION_PRO),
    (re.compile(
        r"\b(?:reorienter|reorientation|pivoter|changer\s+de\s+(?:filiere|cursus|formation))\b",
        re.IGNORECASE,
    ), IntentType.REORIENTATION_ETUDE),
    (re.compile(
        r"\b(?:comparer|comparaison|ou\s+choisir|vs\.?|versus|entre\s+\w+\s+et\s+\w+)\b",
        re.IGNORECASE,
    ), IntentType.COMPARAISON_OPTIONS),
    # Pattern "X ou Y" sur formations courantes (BUT info ou BTS SIO,
    # Master cyber ou Ingé cyber, etc.) — ancré sur formation type pour
    # éviter faux positifs sur "ou" générique.
    (re.compile(
        r"\b(?:bts|but|dut|master|licence|prepa|bac\+\d|bachelor|m1|m2|l1|l2|l3)\b"
        r"[\s\w]*?\bou\b\s*"
        r"(?:bts|but|dut|master|licence|prepa|bac\+\d|bachelor|m1|m2|l1|l2|l3)\b",
        re.IGNORECASE,
    ), IntentType.COMPARAISON_OPTIONS),
    (re.compile(
        r"\b(?:c'est\s+quoi|qu'est[- ]ce\s+que|definition|que\s+signifie|comment\s+(?:on\s+)?(?:appelle|definit))\b",
        re.IGNORECASE,
    ), IntentType.CONCEPTUEL_DEFINITION),
    (re.compile(
        r"\b(?:metier|profession|debouche)\s+(?:de|du|d')",
        re.IGNORECASE,
    ), IntentType.INFO_METIER_SPECIFIQUE),
    (re.compile(
        r"\b(?:demarche|inscription|dossier|parcoursup\s+(?:date|deadline|calendrier)|comment\s+(?:s'inscrire|candidater))\b",
        re.IGNORECASE,
    ), IntentType.DEMARCHE_ADMINISTRATIVE),
    (re.compile(
        r"\b(?:strategie|conseil|que\s+(?:me|m')\s+conseilles?[- ]tu|qu'est[- ]ce\s+que\s+je\s+devrais)\b",
        re.IGNORECASE,
    ), IntentType.CONSEIL_STRATEGIQUE),
    (re.compile(
        r"\b(?:decouvrir|panorama|quelles?\s+(?:formations?|filieres?)\s+(?:existe|y\s+a))\b",
        re.IGNORECASE,
    ), IntentType.DECOUVERTE_FILIERES),
]


def infer_intent_type(user_query: str | None) -> IntentType:
    """Heuristique mot-clé sur la query. Fallback ORIENTATION_INITIALE
    par défaut (vs OTHER) car c'est l'intent dominant dans le corpus
    user OrientIA.

    Application sur query strippée d'accents (matching robuste sur
    "réorienter" / "carrière" / "métier" / "filière" etc.).

    Phase 1 minimal — Phase 2 pourra remplacer par classifier LLM
    dédié si bench S4 GO et que le mismatch d'intent dégrade la qualité.
    """
    if not user_query:
        return IntentType.OTHER
    text = _strip_accents(user_query)
    for pattern, intent in _INTENT_PATTERNS:
        if pattern.search(text):
            return intent
    return IntentType.ORIENTATION_INITIALE


# ---------- Heuristique urgent_concern ----------

_URGENT_PATTERNS = [
    re.compile(r"\b(?:stress|stresse[er]?|panique[er]?|peur|angoisse[er]?|deteste|deprime)\b", re.IGNORECASE),
    re.compile(r"\b(?:perdu[ee]?s?|sature[er]?|saturee?|epuise[er]?|au\s+bord)\b", re.IGNORECASE),
    re.compile(r"\b(?:urgent|urgence|tout\s+de\s+suite|au\s+plus\s+vite|rapidement)\b", re.IGNORECASE),
    re.compile(r"\b(?:burnout|burn[- ]out|craquer|tenir\s+le\s+coup)\b", re.IGNORECASE),
    re.compile(r"\bsais\s+pas\s+(?:quoi\s+faire|comment)\b", re.IGNORECASE),
]


def infer_urgent_concern(
    valeurs: list[str] | None,
    questions_ouvertes: list[str] | None,
    user_query: str | None,
) -> bool:
    """True si stress/urgence détectée dans la query ou les valeurs/
    questions_ouvertes accumulées dans la session.

    Application sur texte strippé d'accents pour matching robuste
    ("stressée" → "stressee" → match `\\bstresse\\b`).
    """
    sources: list[str] = []
    if user_query:
        sources.append(user_query)
    sources.extend(valeurs or [])
    sources.extend(questions_ouvertes or [])
    text = _strip_accents(" ".join(sources))
    return any(p.search(text) for p in _URGENT_PATTERNS)


# ---------- derive_profile_state — bout-en-bout ----------


def derive_profile_state(
    session: Session,
    user_query: str | None = None,
) -> ProfileState:
    """Pipeline complet `UserSessionProfile` → `ProfileState`.

    Args:
        session : Sprint 9 Session avec `profile` (UserSessionProfile)
            mis à jour par `AnalystAgent.update_profile()`.
        user_query : la query du tour courant (pour intent_type +
            urgent_concern). Si None et session a au moins 1 tour user,
            on prend le dernier message user de la session.

    Returns:
        ProfileState typed enum-routable, prêt à être consommé par
        l'orchestrateur Sonnet 4.5 Phase 1.
    """
    profile = session.profile
    # Récupération user_query depuis session si non fourni — utilise
    # l'API publique latest_user_message() (Sprint 9 Session.Turn structure
    # = `user: str, assistant: str | None`, pas role/content).
    if not user_query:
        latest = session.latest_user_message()
        user_query = latest if latest else None

    age_group = map_niveau_scolaire_to_age_group(
        profile.niveau_scolaire,
        profile.age_estime,
    )
    education_level = map_niveau_scolaire_to_education_level(profile.niveau_scolaire)
    intent_type = infer_intent_type(user_query)
    urgent_concern = infer_urgent_concern(
        profile.valeurs,
        profile.questions_ouvertes,
        user_query,
    )

    return ProfileState(
        age_group=age_group,
        education_level=education_level,
        intent_type=intent_type,
        sector_interest=list(profile.interets_detectes or []),
        region=profile.region,
        urgent_concern=urgent_concern,
        confidence=float(profile.confidence or 0.0),
    )
