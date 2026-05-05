"""Fallback unifié — Chantier 1.C (2026-05-03).

Format unique pour tous les paths "je ne sais pas" du pipeline OrientIA.

## Motivation

Aujourd'hui, 4 paths produisent 4 messages différents pour signifier
l'absence d'info :
- Validator block (`validator/policy.py` → BLOCK)
- Retry-with-hint exhausted (chantier 1.B `pipeline.py`)
- SELECT no-match / confidence basse (chantier 2 `lookup/structured_select.py`)
- RAG vide (top-k filtré tout exclu)

Cette incohérence est désastreuse en démo INRIA — le jury remarque les
4 formulations différentes et perd confiance.

## Format unique imposé

```
Je n'ai pas l'information [précise sur X] dans mes sources vérifiées.
[Optionnel : ce qui est proche dans les fiches retrievées, en 1 phrase]
[Optionnel : suggestion — « Vérifie sur Parcoursup officiel / ONISEP / CIO »]
```

## Argument démo INRIA

« Savoir dire je ne sais pas » = différenciateur fort vs wrappers
ChatGPT qui inventent. C'est aussi le filet de sécurité pour les
questions vicieuses du jury (chiffre absent, formation ambiguë,
hors-scope).
"""
from __future__ import annotations

from dataclasses import dataclass


DEFAULT_SUGGESTION = (
    "Vérifie sur Parcoursup officiel (parcoursup.fr), ONISEP "
    "(onisep.fr) ou prends RDV avec le Psy-EN de ton lycée / le "
    "SCUIO de ta fac / le CIO le plus proche."
)


@dataclass(frozen=True)
class FallbackResponse:
    """Wrapper transparent pour différencier un fallback unifié d'une
    réponse normale dans les logs et l'audit (chantier 5 monitoring)."""

    text: str
    reason: str  # 'validator_block' | 'retry_exhausted' | 'select_no_match' | 'rag_empty' | 'out_of_scope' | 'select_invalid_value'
    missing_field: str | None = None
    near_match: str | None = None


def format_unknown_response(
    missing_field: str | None = None,
    near_match: str | None = None,
    suggestion: str | None = DEFAULT_SUGGESTION,
) -> str:
    """Templater déterministe — format unique pour les 4 paths de fallback.

    Args:
        missing_field: ce que l'utilisateur cherchait (ex: "le taux d'insertion
            à 18 mois pour le Master Droit International d'Assas"). Si None,
            on dit juste "cette information".
        near_match: 1 phrase indiquant ce qui est proche dans les fiches
            retrievées (ex: "j'ai trouvé un Master Droit Affaires à Bourgogne
            mais pas Assas"). Si None, on n'ajoute rien.
        suggestion: redirection vers source externe. Default = ONISEP/Parcoursup/CIO.
            Passer None pour omettre.

    Returns:
        String formatée selon le template unique.

    Examples:
        >>> format_unknown_response("le taux d'insertion à 18 mois pour le Master Droit Assas")
        "Je n'ai pas l'information sur le taux d'insertion à 18 mois pour le Master Droit Assas dans mes sources vérifiées.\\n\\nVérifie sur Parcoursup officiel..."

        >>> format_unknown_response()
        "Je n'ai pas cette information dans mes sources vérifiées.\\n\\nVérifie sur Parcoursup officiel..."
    """
    if missing_field:
        opening = f"Je n'ai pas l'information sur {missing_field} dans mes sources vérifiées."
    else:
        opening = "Je n'ai pas cette information dans mes sources vérifiées."

    parts = [opening]

    if near_match:
        parts.append(near_match)

    if suggestion:
        parts.append(suggestion)

    return "\n\n".join(parts)


def format_out_of_scope_response(
    detected_scope: str = "post-bac",
) -> str:
    """Fallback spécifique pour les questions hors scope (ex: orientation
    en 3ème, collège, lycée pré-bac). OrientIA est spécialisé post-bac.

    Args:
        detected_scope: scope que la question a déclenché (ex: "collège/3ème").
            Défaut "post-bac" si l'on veut juste rappeler le scope.

    Returns:
        String formatée — clean, redirige vers Psy-EN / ONISEP collège.
    """
    return (
        f"OrientIA est spécialisé dans l'orientation **{detected_scope}** "
        f"(formations supérieures et insertion professionnelle).\n\n"
        f"Pour une orientation en collège ou pré-bac (3ème → seconde, "
        f"voie pro, CAP, etc.), je te recommande :\n"
        f"- Le Psy-EN de l'établissement\n"
        f"- ONISEP collège (onisep.fr/college)\n"
        f"- Le CIO le plus proche pour un RDV personnalisé"
    )
