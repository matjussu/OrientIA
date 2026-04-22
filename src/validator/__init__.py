"""Validator v1 — déterministe, sans LLM externe.

Deux couches :
- `rules` : regex anti-hallucinations + nomenclature dates/diplômes (Tier 0 ADR-025).
- `corpus_check` : extracteur de claims 'formation à établissement' + vérif corpus indexé.

Orchestré par `Validator` qui retourne un `ValidatorResult` avec
`honesty_score`, `rule_violations`, `corpus_warnings`, `flagged`.

Latence cible : <400ms pour les deux couches combinées.
Fallback LLM (couche 3) reporté v2.

Usage :
    from src.validator import Validator
    v = Validator(fiches=corpus)
    result = v.validate(answer_text)
    if result.flagged:
        # rule BLOCKING ou corpus_warning détecté
        ...
"""
from src.validator.rules import Violation, Severity, RULES, apply_rules
from src.validator.corpus_check import (
    FormationClaim,
    CorpusWarning,
    extract_claims,
    check_formation_exists,
    check_claims_in_corpus,
)
from src.validator.validator import Validator, ValidatorResult
from src.validator.policy import Policy, PolicyResult, apply_policy

__all__ = [
    "Validator",
    "ValidatorResult",
    "Violation",
    "Severity",
    "RULES",
    "apply_rules",
    "FormationClaim",
    "CorpusWarning",
    "extract_claims",
    "check_formation_exists",
    "check_claims_in_corpus",
    "Policy",
    "PolicyResult",
    "apply_policy",
]
