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

from src.validator.rules import Severity, Violation, RULES
from src.validator.corpus_check import CorpusWarning
from src.validator.layer3 import Layer3Warning
from src.validator.validator import ValidatorResult


class Policy(str, Enum):
    PASSTHROUGH = "passthrough"
    WARN = "warn"
    MODIFY = "modify"   # V4 γ Modify — reformule la phrase fautive
    BLOCK = "block"


def _rule_replacement_lookup() -> dict[str, dict]:
    """Map rule_id → rule dict (avec replacement_text + source si présents)."""
    return {r["id"]: r for r in RULES}


@dataclass
class PolicyResult:
    final_answer: str
    policy: Policy
    warnings: list[str] = field(default_factory=list)
    blocked_categories: list[str] = field(default_factory=list)


_MAX_FOOTER_ITEMS = 2


def _format_warn_footer(
    violations: list[Violation],
    corpus_warnings: list[CorpusWarning],
    layer3_warnings: list[Layer3Warning] | None = None,
    presence_warnings: list | None = None,
) -> str:
    """Footer β Warn v3 (polish) : top 2 warnings max, priorité ordering.

    V4 ajoute presence_warnings dans l'ordering (entre WARN rules et layer3).
    V3 polish : top 2 items max avec priorité rules > presence > corpus > layer3.
    Au-delà, suffix "⚠️ N autres points à vérifier (masqués)".
    """
    # Collecte tous les items dans l'ordre de priorité (V4: presence avant corpus)
    items: list[str] = []
    for v in violations:
        items.append(f"- {v.message}")
    if presence_warnings:
        for pw in presence_warnings:
            items.append(f"- {pw.missing_pattern_label} — {pw.message}")
    for w in corpus_warnings:
        items.append(
            f"- Affirmation non vérifiable dans notre corpus : *{w.claim}*. "
            f"Plus proche dans la base : {w.closest_match}."
        )
    if layer3_warnings:
        for lw in layer3_warnings:
            items.append(f"- *{lw.claim}* — {lw.reason}")

    # Top 2 + suffix si overflow
    visible = items[:_MAX_FOOTER_ITEMS]
    hidden_count = max(0, len(items) - _MAX_FOOTER_ITEMS)

    lines = ["", "---", "⚠️ **Points à vérifier dans ma réponse** :"]
    lines.extend(visible)
    if hidden_count > 0:
        lines.append(
            f"- *(+ {hidden_count} autre"
            f"{'s' if hidden_count > 1 else ''} point"
            f"{'s' if hidden_count > 1 else ''} détecté"
            f"{'s' if hidden_count > 1 else ''} et masqué"
            f"{'s' if hidden_count > 1 else ''} pour lisibilité)*"
        )
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


def _apply_gamma_modify(
    answer: str,
    blocking_violations: list[Violation],
) -> tuple[str, list[str], int]:
    """V4 γ Modify : remplace `matched_text` de chaque violation BLOCKING
    par son `replacement_text` (si défini dans la règle). Retourne
    (answer_modifié, sources_list, nb_modifs).

    Remplacement littéral (pas regex) → sûr contre les artefacts. Les
    règles sans `replacement_text` forcent un fallback vers Block côté
    caller.
    """
    lookup = _rule_replacement_lookup()
    modified = answer
    sources: list[str] = []
    count = 0
    for v in blocking_violations:
        rule = lookup.get(v.rule_id, {})
        replacement = rule.get("replacement_text")
        if not replacement:
            continue  # règle sans replacement → caller fera Block
        # Remplacement littéral (le matched_text est exact car vient du regex match)
        if v.matched_text and v.matched_text in modified:
            modified = modified.replace(v.matched_text, replacement, 1)
            count += 1
            src = rule.get("source", "source non-documentée")
            sources.append(f"[{v.rule_id}] {src}")
    return modified, sources, count


def _format_modify_footer(sources: list[str], count: int) -> str:
    """Footer traçabilité V4 γ Modify."""
    s_word = "source" if len(sources) == 1 else "sources"
    m_word = "modification" if count == 1 else "modifications"
    lines = [
        "",
        "---",
        f"⚠️ **{count} {m_word} de sécurité** appliquée{'s' if count > 1 else ''} à ma réponse pour corriger des imprécisions factuelles. "
        f"{s_word.capitalize()} :",
    ]
    for s in sources:
        lines.append(f"- {s}")
    lines.append("")
    lines.append(
        "Vérifie directement sur [ONISEP](https://www.onisep.fr) ou [Parcoursup]"
        "(https://www.parcoursup.fr) avant toute décision."
    )
    return "\n".join(lines)


def apply_policy(
    answer: str,
    validation: ValidatorResult,
) -> PolicyResult:
    """Applique la policy V4 hybride γ Modify + α Block + β Warn.

    Priority ordering (V4) :
    1. **corpus_warning** → Block (α) — formation inventée, on ne peut pas corriger
    2. **BLOCKING rule AVEC replacement_text** → **Modify (γ)** — remplacement chirurgical
    3. **BLOCKING rule SANS replacement_text** → Block (α) fallback
    4. **WARN rule ou layer3** → Warn (β) avec footer top 2
    5. **Aucune violation** → passthrough

    Backward-safe : answer vide ou validation sans violation → passthrough.
    """
    blocking = [v for v in validation.rule_violations if v.severity == Severity.BLOCKING]
    has_corpus = len(validation.corpus_warnings) > 0
    has_warn = any(v.severity == Severity.WARNING for v in validation.rule_violations)
    has_layer3 = len(validation.layer3_warnings) > 0

    # (1) Block si corpus_warning (on ne peut pas corriger une formation inventée)
    if has_corpus:
        refusal, categories = _format_block_refusal(
            validation.rule_violations, validation.corpus_warnings
        )
        warnings_list = [v.message for v in blocking]
        warnings_list.extend(f"[corpus] {w.claim}" for w in validation.corpus_warnings)
        return PolicyResult(
            final_answer=refusal,
            policy=Policy.BLOCK,
            warnings=warnings_list,
            blocked_categories=categories,
        )

    # (2) + (3) BLOCKING rules : γ Modify si toutes ont replacement_text, sinon Block
    if blocking:
        lookup = _rule_replacement_lookup()
        all_have_replacement = all(
            lookup.get(v.rule_id, {}).get("replacement_text") for v in blocking
        )
        if all_have_replacement:
            modified_text, sources, count = _apply_gamma_modify(answer, blocking)
            if count > 0:
                footer = _format_modify_footer(sources, count)
                # Ajout layer3/WARN dans le footer modify aussi si présents
                combined = modified_text.rstrip() + "\n" + footer
                return PolicyResult(
                    final_answer=combined,
                    policy=Policy.MODIFY,
                    warnings=[f"[modify] {v.rule_id}: {v.matched_text!r}" for v in blocking],
                    blocked_categories=sorted({v.category for v in blocking}),
                )
        # Fallback Block (rule sans replacement OU replacement n'a rien matché)
        refusal, categories = _format_block_refusal(
            validation.rule_violations, validation.corpus_warnings
        )
        return PolicyResult(
            final_answer=refusal,
            policy=Policy.BLOCK,
            warnings=[v.message for v in blocking],
            blocked_categories=categories,
        )

    # (4) WARN ou layer3 ou presence (V4)
    has_presence = len(validation.presence_warnings) > 0
    if has_warn or has_layer3 or has_presence:
        footer = _format_warn_footer(
            validation.rule_violations,
            validation.corpus_warnings,
            validation.layer3_warnings,
            validation.presence_warnings,
        )
        warn_messages = [
            v.message for v in validation.rule_violations
            if v.severity == Severity.WARNING
        ]
        warn_messages.extend(f"[presence] {pw.topic}" for pw in validation.presence_warnings)
        warn_messages.extend(f"[layer3] {lw.claim}" for lw in validation.layer3_warnings)
        return PolicyResult(
            final_answer=answer.rstrip() + "\n" + footer,
            policy=Policy.WARN,
            warnings=warn_messages,
        )

    # (5) Passthrough
    return PolicyResult(
        final_answer=answer,
        policy=Policy.PASSTHROUGH,
    )
