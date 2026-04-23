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
    # NOTE V4 : les règles V1 `tremplin_not_HEC` et `passerelle_not_HEC` ont
    # été retirées car supersedées par V2.1 `HEC_not_via_Tremplin_or_Passerelle`
    # qui couvre les 2 patterns avec replacement_text pour γ Modify. Cette
    # consolidation évite le double-firing qui bloquait le γ Modify (une règle
    # V1 sans replacement + une V2 avec replacement → fallback Block indésiré).

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
    # ========================================================================
    # RÈGLES V2 — identifiées par le panel humain ground truth 2026-04-22
    # (5 profils × 3 Q du pack Gate J+6, 4 erreurs disqualifiantes ADR-036)
    # ========================================================================
    {
        # V2.1 — HEC se recrute via son propre concours AST (Admission sur Titres),
        # pas via Tremplin (→ Audencia/Kedge/SKEMA/EM Normandie/etc.) ni Passerelle
        # (→ ESC Clermont/ESSCA/IESEG/EM Strasbourg). Source : site HEC Paris +
        # Psy-EN 22 ans exp. Cf ADR-036.
        "id": "HEC_not_via_Tremplin_or_Passerelle",
        "category": "concours_whitelist",
        "severity": Severity.BLOCKING,
        "pattern": (
            r"(?:\bHEC\b[\s\S]{0,250}?\b(?:Tremplin|Passerelle)\b"
            r"|\b(?:Tremplin|Passerelle)\b[\s\S]{0,250}?\bHEC\b)"
        ),
        "message": (
            "HEC Paris recrute via son concours propre AST (Admission sur Titres), "
            "PAS via Tremplin (→ Audencia/Kedge/SKEMA) ni Passerelle (→ ESC Clermont/ESSCA/IESEG)."
        ),
        "except_context": (
            r"(?:pas\s+via\s+(?:Tremplin|Passerelle)"
            r"|(?:non|ni)\s+(?:par|via)\s+(?:Tremplin|Passerelle)"
            r"|AST\s*\(?Admission\s+sur\s+Titres"
            r"|concours\s+propre)"
        ),
        "replacement_text": (
            "HEC Paris passe par son propre concours AST (Admission sur Titres, bac+3/4), "
            "pas par Tremplin ni Passerelle. Tremplin → Audencia/Kedge/SKEMA/EM Normandie, "
            "Passerelle → ESC Clermont/ESSCA/IESEG/EM Strasbourg."
        ),
        "source": "Site HEC Paris + Psy-EN 22 ans d'expérience (ADR-036)",
    },
    {
        # V2.2 — En PASS, le redoublement est INTERDIT depuis l'arrêté du
        # 4 novembre 2019 (réforme PACES → PASS/L.AS). Une seule chance. Si
        # 60 ECTS validés sans passage MMOP → bascule L.AS ou L2 sur équivalence.
        # Dire "redoublement rare" est trompeur. Cf ADR-036.
        "id": "PASS_no_redoublement",
        "category": "voies_impossibles",
        "severity": Severity.BLOCKING,
        "pattern": (
            r"(?:redoublement\s+(?:en\s+)?PASS[\s\S]{0,40}?\brare\b"
            r"|\bPASS\b[\s\S]{0,40}?redoublement\s+(?:est|reste)?\s*rare"
            r"|redoubler\s+(?:en\s+|la\s+)?(?:PASS|première\s+année\s+de\s+PASS)"
            r"|(?:deuxième|seconde)\s+chance\s+(?:en\s+)?PASS"
            r"|PASS[\s\S]{0,40}?(?:deuxième|seconde)\s+chance)"
        ),
        "message": (
            "Le redoublement en PASS est INTERDIT (arrêté 4 nov 2019, réforme PACES → PASS/L.AS). "
            "Une seule chance. Échec → bascule L.AS ou L2 sur équivalence."
        ),
        "except_context": (
            r"(?:interdit|une\s+seule\s+chance|arrêté\s+(?:du\s+)?\d|"
            r"sans\s+seconde\s+tentative|pas\s+autorisé)"
        ),
        "replacement_text": (
            "le redoublement en PASS est interdit (arrêté du 4 novembre 2019, réforme PACES → PASS/L.AS). "
            "Une seule chance. Si 60 ECTS validés sans passage MMOP → bascule automatique L.AS ou L2 sur équivalence."
        ),
        "source": "Arrêté du 4 novembre 2019 (JORF) — réforme PACES → PASS/L.AS",
    },
    {
        # V2.3 — Séries bac A/B/C/D supprimées en 1995 (réforme Chevènement).
        # Séries ES/S/L supprimées en 2021 (réforme Blanquer, bac S déjà couvert
        # par `bac_S_abolished` V1). Source : réforme Chevènement 1992-1995.
        # Root cause du bug "bac B" dans nos réponses : confusion LLM entre
        # "mention Bien" (B 42%) et "série B" — fixé aussi côté data cleanup
        # dans src/rag/generator.py:_profil_line (cf commit dédié).
        "id": "bac_series_ABCD_abolished",
        "category": "terminology_date",
        "severity": Severity.BLOCKING,
        "pattern": r"\b(?:bac|série|filière|terminale)s?\s+[ABCD]\b",
        "message": (
            "Les séries bac A/B/C/D ont été supprimées en 1995 (réforme Chevènement). "
            "Aujourd'hui : bac général avec spécialités, bac techno, bac pro."
        ),
        "except_context": (
            r"(?:ancien|avant\s+199[0-5]|jusqu'?en\s+199[0-4]|historique|"
            r"réforme\s+Chevènement|ancienne?\s+série)"
        ),
        "replacement_text": (
            "bac général (spécialités Maths/PC/SVT/SES selon profil)"
        ),
        "source": "Réforme Chevènement 1992-1995 — séries A/B/C/D → nouveau bac général/techno/pro",
    },
    {
        # V2.4 — DE kinésithérapie s'obtient en IFMK (Institut de Formation en
        # Masso-Kinésithérapie), pas via licence universitaire directe. Accès
        # IFMK : PASS/L.AS/STAPS/licence scientifique VALIDÉE + concours interne
        # très sélectif (~3% d'accès national). Cf ADR-036 + site ONISEP/IFMK.
        "id": "kine_via_IFMK_not_licence",
        "category": "voies_impossibles",
        "severity": Severity.BLOCKING,
        "pattern": (
            r"(?:"
            r"[Ll]icence[^.\n]{0,60}\(\s*option\s+[Kk]in[eé]sith[eé]rapie"
            r"|STAPS[^.\n]{0,60}\(\s*parcours\s+[Kk]in[eé]sith[eé]rapie"
            r"|[Ll]icence[^.\n]{0,60}(?:menant|direct)[^.\n]{0,40}DE[^.\n]{0,20}kin[eé]"
            r"|STAPS\s+parcours\s+[Kk]in[eé]sith[eé]rapie"
            r")"
        ),
        "message": (
            "Le DE de kinésithérapeute s'obtient via un IFMK (Institut de Formation en "
            "Masso-Kinésithérapie), pas via une licence universitaire directe. Accès IFMK "
            "sur concours très sélectif après PASS/L.AS/STAPS/licence scientifique validée."
        ),
        "except_context": r"(?:via\s+(?:un\s+)?IFMK|concours\s+IFMK|DE\s+via\s+IFMK)",
        "replacement_text": (
            "Kinésithérapie en IFMK (Institut de Formation en Masso-Kinésithérapie) "
            "accessible après PASS/L.AS/STAPS/licence scientifique validée + concours "
            "interne très sélectif (~3% d'accès national)"
        ),
        "source": "Site ONISEP + Ordre des Kinésithérapeutes + réforme PACES 2019",
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
