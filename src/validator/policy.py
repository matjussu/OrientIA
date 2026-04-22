"""UX Policy runtime pour Validator v1 (Gate J+6).

Prend un answer + ValidatorResult → applique une policy (Block / Warn /
passthrough) et retourne le texte final + métadonnées pour l'API.

Policy hybride α+β :
- **passthrough** : aucune violation → answer inchangé
- **β Warn** : uniquement WARN rules → answer + footer "⚠️ points à vérifier"
- **α Block** : ≥1 BLOCKING rule OU ≥1 corpus_warning → refus structuré
  remplace la réponse (pointage source officielle : ONISEP / SCUIO / Psy-EN / CIO)

Stratégie conservatrice : on privilégie l'abstention au claim faux quand
le Validator détecte un risque factuel grave, plutôt qu'un simple avertissement
que les mineurs pourraient ignorer (feedback user_test v2 : 3/5 profils ne
recommandaient pas à un mineur en autonomie).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from src.validator.rules import Severity, Violation
from src.validator.corpus_check import CorpusWarning
from src.validator.layer3 import Layer3Warning
from src.validator.validator import ValidatorResult


class Policy(str, Enum):
    PASSTHROUGH = "passthrough"
    WARN = "warn"
    BLOCK = "block"


@dataclass
class PolicyResult:
    final_answer: str
    policy: Policy
    warnings: list[str] = field(default_factory=list)
    blocked_categories: list[str] = field(default_factory=list)


def _format_warn_footer(
    violations: list[Violation],
    corpus_warnings: list[CorpusWarning],
    layer3_warnings: list[Layer3Warning] | None = None,
) -> str:
    """Footer avertissement pour la policy β Warn (non-bloquantes)."""
    lines = ["", "---", "⚠️ **Points à vérifier dans ma réponse** :"]
    for v in violations:
        lines.append(f"- {v.message}")
    for w in corpus_warnings:
        lines.append(
            f"- Affirmation non vérifiable dans notre corpus : *{w.claim}*. "
            f"Plus proche dans la base : {w.closest_match}."
        )
    if layer3_warnings:
        for lw in layer3_warnings:
            lines.append(f"- *{lw.claim}* — {lw.reason}")
    lines.append("")
    lines.append(
        "Ces points sont des patterns que nous surveillons. Vérifie "
        "directement sur [ONISEP](https://www.onisep.fr) ou [Parcoursup]"
        "(https://www.parcoursup.fr) avant toute décision."
    )
    return "\n".join(lines)


def _format_block_refusal(
    violations: list[Violation],
    corpus_warnings: list[CorpusWarning],
) -> tuple[str, list[str]]:
    """Refus structuré pour la policy α Block (BLOCKING ou corpus_warning).

    Retourne (refusal_text, blocked_categories).
    """
    blocking = [v for v in violations if v.severity == Severity.BLOCKING]
    categories = sorted({v.category for v in blocking})
    reason_tags: list[str] = []

    if blocking:
        for v in blocking:
            reason_tags.append(f"• {v.message}")
    if corpus_warnings:
        for w in corpus_warnings:
            reason_tags.append(
                f"• Formation citée non présente dans notre base de données vérifiée : *{w.claim}*."
            )

    body = [
        "Je préfère ne pas répondre sur ce point de manière détaillée, car ma réponse "
        "contiendrait des imprécisions factuelles importantes qui pourraient t'induire en erreur.",
        "",
        "Détails :",
    ]
    body.extend(reason_tags)
    body.extend([
        "",
        "Pour avoir une information fiable sur ton orientation, je te conseille :",
        "- **ONISEP** : catalogue officiel des formations françaises — https://www.onisep.fr",
        "- **Parcoursup** : procédures et taux d'accès officiels — https://www.parcoursup.fr",
        "- **SCUIO** : service d'orientation de ton université (si étudiant·e)",
        "- **CIO** / **Psy-EN** : conseiller·ères d'orientation en lycée",
        "",
        "Tu peux aussi me reposer la question autrement (par exemple avec un profil "
        "plus précis ou sur un sujet plus ciblé) et je ferai de mon mieux pour répondre "
        "dans la limite de ce que nos données vérifient.",
    ])
    return "\n".join(body), categories


def apply_policy(
    answer: str,
    validation: ValidatorResult,
) -> PolicyResult:
    """Applique la policy hybride α+β sur l'answer selon ValidatorResult.

    Ordre de décision :
    1. BLOCKING rule ou corpus_warning → Block (α)
    2. Seulement WARN rule → Warn (β)
    3. Aucune violation → passthrough

    Backward-safe : answer vide ou validation sans violation → passthrough.
    """
    has_blocking = any(v.severity == Severity.BLOCKING for v in validation.rule_violations)
    has_corpus = len(validation.corpus_warnings) > 0
    has_warn = any(v.severity == Severity.WARNING for v in validation.rule_violations)
    has_layer3 = len(validation.layer3_warnings) > 0

    if has_blocking or has_corpus:
        refusal, categories = _format_block_refusal(
            validation.rule_violations, validation.corpus_warnings
        )
        warnings_list = [v.message for v in validation.rule_violations if v.severity == Severity.BLOCKING]
        warnings_list.extend([f"[corpus] {w.claim}" for w in validation.corpus_warnings])
        return PolicyResult(
            final_answer=refusal,
            policy=Policy.BLOCK,
            warnings=warnings_list,
            blocked_categories=categories,
        )

    if has_warn or has_layer3:
        footer = _format_warn_footer(
            validation.rule_violations,
            validation.corpus_warnings,
            validation.layer3_warnings,
        )
        warn_messages = [
            v.message for v in validation.rule_violations
            if v.severity == Severity.WARNING
        ]
        warn_messages.extend(f"[layer3] {lw.claim}" for lw in validation.layer3_warnings)
        return PolicyResult(
            final_answer=answer.rstrip() + "\n" + footer,
            policy=Policy.WARN,
            warnings=warn_messages,
        )

    return PolicyResult(
        final_answer=answer,
        policy=Policy.PASSTHROUGH,
    )
