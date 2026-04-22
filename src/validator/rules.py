"""Règles déterministes (Validator v1 couche 1).

Liste des interdictions Tier 0 (ADR-025) + nomenclatures dates/diplômes +
patterns marketing trompeurs. Zéro dépendance LLM — uniquement regex + règles.

Chaque règle a un `except_context` optionnel : si la fenêtre ±80 chars autour
du match contient ce pattern, le match est ignoré (permet de laisser passer
"ancien nom : ECN" tout en catchant "passe les ECN en 6e année").
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    BLOCKING = "blocking"  # erreur factuelle grave, 100% catch requis
    WARNING = "warning"    # signal, pas bloquant
    INFO = "info"          # amélioration suggérée


@dataclass
class Violation:
    rule_id: str
    severity: Severity
    message: str
    matched_text: str
    category: str


# Registre des règles. Chaque entrée :
#   id, category, severity, pattern, message, except_context (optionnel)
#
# Les patterns sont appliqués avec re.IGNORECASE | re.UNICODE.
RULES: list[dict] = [
    # === Terminologie & dates (ADR-025 anti-halluc #1-#2 + user_test_v2) ===
    {
        "id": "ECN_renamed_to_EDN",
        "category": "terminology_date",
        "severity": Severity.BLOCKING,
        "pattern": r"\b(?:épreuves\s+classantes\s+nationales|ECN)\b",
        "message": (
            "'ECN' a été remplacé par 'EDN' (Épreuves Dématérialisées Nationales) "
            "depuis 2023 via la réforme R2C. Utiliser 'EDN'."
        ),
        "except_context": r"(EDN|ancien\s+nom|avant\s+2023|depuis\s+2023|réforme\s+R2C)",
    },
    {
        "id": "bac_S_abolished",
        "category": "terminology_date",
        "severity": Severity.BLOCKING,
        "pattern": r"\b(?:bac|filière|terminale|série)\s+S\b",
        "message": (
            "Le 'bac S' a été supprimé en 2021 (réforme Blanquer). "
            "Utiliser 'bac général avec spécialités Maths/PC/SVT'."
        ),
        "except_context": r"(ancien|avant\s+2021|supprimé|réforme\s+Blanquer|jusqu'en\s+2020)",
    },
    {
        "id": "VAE_VAP_confusion",
        "category": "terminology_date",
        "severity": Severity.WARNING,
        "pattern": r"\bVAE\b[^.\n]{0,80}?(?:reprendre?\s+(?:ses?|tes?|mes?|vos?|nos?|les|des)?\s*études|projet\s+étudiant|entrer\s+(?:en|à)\s+(?:L1|L2|L3)|reprise\s+d['’]études)",
        "message": (
            "VAE = Validation des Acquis de l'Expérience (diplôme, 3 ans d'exp pro). "
            "Pour reprendre des études : c'est VAP (Validation des Acquis Professionnels). Vérifier."
        ),
    },
    # === Concours HEC whitelist (ADR-025 anti-halluc #7) ===
    {
        "id": "tremplin_not_HEC",
        "category": "concours_whitelist",
        "severity": Severity.BLOCKING,
        "pattern": r"(?:concours\s+)?Tremplin\b[^.\n]{0,80}?(?:pour|vers|à|d'accès\s+à)\s+(?:[\wÀ-ÿ']+\s+){0,3}HEC\b",
        "message": (
            "Le concours Tremplin mène à Audencia/ESC Dijon/Rennes, PAS à HEC. "
            "HEC admissions parallèles = AST (bac+3/4), pas Tremplin."
        ),
    },
    {
        "id": "passerelle_not_HEC",
        "category": "concours_whitelist",
        "severity": Severity.BLOCKING,
        "pattern": r"(?:concours\s+)?Passerelle\b[^.\n]{0,80}?(?:pour|vers|à|d'accès\s+à)\s+(?:[\wÀ-ÿ']+\s+){0,3}HEC\b",
        "message": (
            "Le concours Passerelle mène à ESC autres que HEC (Audencia, EM Lyon, etc.). "
            "HEC admissions parallèles = AST uniquement."
        ),
    },
    # === Voies impossibles (ADR-025 anti-halluc #3) ===
    {
        "id": "VAP_infirmier_kine",
        "category": "voies_impossibles",
        "severity": Severity.BLOCKING,
        "pattern": r"(?:passerelle|VAP)\s+[^.\n]{0,100}infirmi(?:er|ère)[^.\n]{0,40}(?:vers|pour|→|->|en)\s+kiné",
        "message": (
            "Passerelle VAP Infirmier → Kiné est quasi-impossible en pratique "
            "(aucun cas sur 22 ans selon conseiller d'orientation pro)."
        ),
    },
    # === Marketing trompeur (ADR-025 anti-halluc #4-#8) ===
    {
        "id": "ecole42_gratuite_alternance",
        "category": "marketing_false",
        "severity": Severity.BLOCKING,
        "pattern": r"(?:école\s+)?42\s+[^.\n]{0,40}gratuite\s+en\s+alternance",
        "message": "École 42 est gratuite (tout court). Elle n'est PAS 'gratuite en alternance' — c'est une formulation trompeuse.",
    },
    {
        "id": "MBA_HEC_accessible_experience",
        "category": "marketing_false",
        "severity": Severity.WARNING,
        "pattern": r"MBA\s+HEC\s+[^.\n]{0,80}(?:plus\s+accessible|facilement\s+accessible|accessible\s+aux?\s+pros?)",
        "message": (
            "MBA HEC exige 5-8 ans d'exp cadre + GMAT 700+ + ~80 000€. "
            "Ne pas présenter comme 'plus accessible' — c'est au contraire très sélectif et onéreux."
        ),
    },
    {
        "id": "prepa_medecine_2x_chances",
        "category": "marketing_false",
        "severity": Severity.WARNING,
        "pattern": r"prépa(?:s)?\s+(?:privée(?:s)?\s+)?(?:de\s+)?médecine[^.\n]{0,40}(?:2x|double|doubler?\s+(?:les?\s+)?chances?)",
        "message": (
            "Le 'prépa privée double les chances médecine' est un argument marketing "
            "avec biais de sélection (cohortes filtrées sur dossier). À éviter."
        ),
    },
    {
        "id": "pour_les_nuls_concours_selectif",
        "category": "marketing_false",
        "severity": Severity.WARNING,
        "pattern": r"\b(?:Orthophonie|Médecine|Kinésithérapie|Kiné|Dentaire|Pharmacie|Vétérinaire)\s+pour\s+les\s+Nuls\b",
        "message": (
            "Recommander une collection 'X pour les Nuls' pour un concours "
            "<20% d'admission est un conseil catastrophique — ces ouvrages "
            "couvrent rarement le niveau requis."
        ),
    },
    # === Inventions notables (user_test_v2) ===
    {
        "id": "licence_humanites_orthophonie_invented",
        "category": "invented_formation",
        "severity": Severity.BLOCKING,
        "pattern": r"Licence\s+Humanités(?:\s*[-–—]\s*(?:Parcours\s+)?Orthophonie|\s+parcours\s+Orthophonie)",
        "message": (
            "'Licence Humanités-Parcours Orthophonie' n'existe pas. "
            "Orthophonie passe par le concours CEO après bac (5 ans)."
        ),
    },
]


def _context_around(text: str, match: re.Match, window: int = 80) -> str:
    """Retourne la fenêtre ±`window` chars autour du match."""
    start = max(0, match.start() - window)
    end = min(len(text), match.end() + window)
    return text[start:end]


def apply_rules(answer: str, rules: list[dict] | None = None) -> list[Violation]:
    """Applique toutes les règles sur `answer` et retourne les violations.

    Une règle avec `except_context` est désactivée si ce pattern apparaît
    dans la fenêtre ±80 chars autour du match principal.
    """
    rules = rules if rules is not None else RULES
    violations: list[Violation] = []
    for rule in rules:
        pattern = re.compile(rule["pattern"], re.IGNORECASE | re.UNICODE)
        for match in pattern.finditer(answer):
            except_ctx = rule.get("except_context")
            if except_ctx:
                ctx = _context_around(answer, match, window=80)
                if re.search(except_ctx, ctx, re.IGNORECASE | re.UNICODE):
                    continue
            violations.append(
                Violation(
                    rule_id=rule["id"],
                    severity=rule["severity"],
                    message=rule["message"],
                    matched_text=match.group(0),
                    category=rule["category"],
                )
            )
    return violations
