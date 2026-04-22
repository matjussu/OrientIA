"""Règles de PRÉSENCE (Validator V4).

Paradigme inverse des règles classiques : au lieu de "flag si pattern fautif
détecté", on flag "si topic détecté MAIS information obligatoire ABSENTE".

Exemple : si un answer mentionne PASS sans mentionner l'arrêté 2019 ou
"redoublement interdit", on flag la réponse comme incomplète.

Cas d'usage (ordre V4 du 2026-04-22-1751) :
- PASS → doit contenir "arrêté 2019" OU "redoublement interdit" OU "une seule chance"
- HEC → doit contenir "AST" (Admission sur Titres)
- kiné → doit contenir "IFMK" + "concours"
- "taux d'accès Parcoursup" → doit contenir "rang du dernier appelé" OU similaire

Le flag produit un `PresenceWarning` (severity WARNING) qui contribue
au footer β Warn sans déclencher BLOCK/MODIFY.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class PresenceWarning:
    topic: str
    message: str
    missing_pattern_label: str


# Chaque règle de présence :
#   topic_id        : identifiant stable
#   topic_pattern   : regex qui détecte si le topic est abordé
#   required_any_of : liste de patterns — au moins UN doit matcher
#   message         : texte d'alerte côté utilisateur
#   missing_label   : label court pour le footer
PRESENCE_RULES: list[dict] = [
    {
        "topic_id": "PASS_redoublement_info",
        "topic_pattern": r"\bPASS\b",
        "required_any_of": [
            r"arrêté\s+(?:du\s+)?\d+\s+nov(?:embre)?\s+2019",
            r"arrêté\s+(?:du\s+)?(?:4|quatre)\s+nov(?:embre)?\s+2019",
            r"redoublement\s+(?:en\s+PASS\s+)?(?:est\s+)?interdit",
            r"une\s+seule\s+chance\s+(?:en\s+|pour\s+)?PASS",
            r"pas\s+de\s+redoublement\s+(?:en\s+)?PASS",
        ],
        "message": (
            "La réponse parle de PASS mais ne précise pas que le redoublement "
            "est interdit (arrêté du 4 novembre 2019). C'est une information "
            "obligatoire pour un lycéen en autonomie."
        ),
        "missing_label": "Mention manquante : interdit de redoublement PASS (arrêté 2019)",
    },
    {
        "topic_id": "HEC_admission_info",
        "topic_pattern": r"\bHEC\b",
        "required_any_of": [
            r"\bAST\b",
            r"Admission\s+sur\s+Titres",
            r"concours\s+propre",
            r"admission(?:s)?\s+parall[èe]les?",
        ],
        "message": (
            "La réponse mentionne HEC mais ne cite pas la voie d'admission "
            "parallèle AST (Admission sur Titres, bac+3/4), qui est l'unique "
            "alternative à la prépa ECG pour un bac+3."
        ),
        "missing_label": "Mention manquante : voie AST pour HEC",
    },
    {
        "topic_id": "kine_IFMK_info",
        "topic_pattern": r"\bkin[eé]",
        "required_any_of": [
            r"\bIFMK\b",
            r"Institut\s+de\s+Formation\s+en\s+Masso-Kin[eé]sith[eé]rapie",
            r"concours\s+kin[eé]",
        ],
        "message": (
            "La réponse parle de kiné mais ne mentionne pas l'IFMK (Institut "
            "de Formation en Masso-Kinésithérapie) ni le concours d'accès. "
            "Ce sont les étapes obligatoires pour devenir kiné en France."
        ),
        "missing_label": "Mention manquante : IFMK + concours pour kiné",
    },
    {
        "topic_id": "parcoursup_taux_info",
        # Détecte une mention de taux d'accès sans explication
        "topic_pattern": r"taux\s+d['’]acc[èe]s\s+(?:Parcoursup|en\s+Parcoursup|Parcoursup\s+de)?",
        "required_any_of": [
            r"rang\s+du\s+dernier\s+appel[eé]",
            r"dernier\s+(?:candidat|appelé)\s+appel[eé]",
            r"pas\s+le\s+taux\s+d['’]admission",
            r"\(et\s+non\s+le\s+taux",
            r"ne\s+signifie\s+pas\s+(?:un\s+)?taux\s+d['’]admission",
        ],
        "message": (
            "La réponse cite un 'taux d'accès Parcoursup' sans préciser que "
            "c'est le rang du dernier candidat appelé (pas le taux d'admission). "
            "Nuance critique pour un lycéen."
        ),
        "missing_label": "Mention manquante : 'taux d'accès' = rang du dernier appelé",
    },
]


def check_presence(
    answer: str,
    rules: list[dict] | None = None,
) -> list[PresenceWarning]:
    """Applique les règles de présence : pour chaque topic détecté dans
    `answer`, vérifie qu'au moins un des patterns `required_any_of` matche.
    Si aucun ne matche → PresenceWarning.
    """
    rules = rules if rules is not None else PRESENCE_RULES
    warnings: list[PresenceWarning] = []
    for rule in rules:
        topic_pat = re.compile(rule["topic_pattern"], re.IGNORECASE | re.UNICODE)
        if not topic_pat.search(answer):
            continue  # topic non mentionné → rien à vérifier
        # Topic détecté : au moins un required pattern doit matcher
        found = False
        for req_pat in rule["required_any_of"]:
            if re.search(req_pat, answer, re.IGNORECASE | re.UNICODE):
                found = True
                break
        if not found:
            warnings.append(
                PresenceWarning(
                    topic=rule["topic_id"],
                    message=rule["message"],
                    missing_pattern_label=rule["missing_label"],
                )
            )
    return warnings
