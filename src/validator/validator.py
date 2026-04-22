"""Orchestrateur Validator v1 (couches 1 + 2 combinées).

Expose `Validator.validate(answer) -> ValidatorResult`.
Couche 3 fallback LLM (Mistral Small souverain) reportée v2.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.validator.rules import Severity, Violation, apply_rules
from src.validator.corpus_check import CorpusWarning, check_claims_in_corpus


@dataclass
class ValidatorResult:
    honesty_score: float  # 0.0 (pire) .. 1.0 (parfait)
    rule_violations: list[Violation] = field(default_factory=list)
    corpus_warnings: list[CorpusWarning] = field(default_factory=list)
    flagged: bool = False  # True si >= 1 violation BLOCKING ou corpus_warning

    def summary(self) -> str:
        """Résumé lisible pour log / debug."""
        lines = [
            f"honesty_score={self.honesty_score:.2f} "
            f"flagged={self.flagged} "
            f"rules={len(self.rule_violations)} "
            f"corpus={len(self.corpus_warnings)}"
        ]
        for v in self.rule_violations:
            lines.append(f"  [{v.severity.value}] {v.rule_id}: {v.matched_text!r}")
        for w in self.corpus_warnings:
            lines.append(
                f"  [corpus] {w.claim!r} (sim={w.similarity}, "
                f"closest={w.closest_match!r})"
            )
        return "\n".join(lines)


# Pondération du score honnêteté
_SCORE_PENALTIES: dict[Severity, float] = {
    Severity.BLOCKING: 0.15,
    Severity.WARNING: 0.05,
    Severity.INFO: 0.02,
}
_CORPUS_PENALTY = 0.10


class Validator:
    """Orchestrateur règles + corpus-check.

    Usage :
        v = Validator(fiches=corpus)
        result = v.validate(answer_text)
        if result.flagged:
            log.warning("validator flagged: %s", result.summary())
    """

    def __init__(
        self,
        fiches: list[dict],
        corpus_sim_threshold: float = 0.30,
    ):
        self.fiches = fiches
        self.corpus_sim_threshold = corpus_sim_threshold

    def validate(self, answer: str) -> ValidatorResult:
        rule_violations = apply_rules(answer)
        corpus_warnings = check_claims_in_corpus(
            answer, self.fiches, threshold=self.corpus_sim_threshold
        )

        honesty_score = self._compute_honesty(rule_violations, corpus_warnings)
        flagged = (
            any(v.severity == Severity.BLOCKING for v in rule_violations)
            or len(corpus_warnings) > 0
        )

        return ValidatorResult(
            honesty_score=honesty_score,
            rule_violations=rule_violations,
            corpus_warnings=corpus_warnings,
            flagged=flagged,
        )

    @staticmethod
    def _compute_honesty(
        violations: list[Violation],
        corpus_warnings: list[CorpusWarning],
    ) -> float:
        score = 1.0
        for v in violations:
            score -= _SCORE_PENALTIES.get(v.severity, 0.05)
        score -= _CORPUS_PENALTY * len(corpus_warnings)
        return max(0.0, min(1.0, score))
