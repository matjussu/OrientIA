"""Orchestrateur Validator v1 (couches 1 + 2 combinées).

Expose `Validator.validate(answer) -> ValidatorResult`.
Couche 3 fallback LLM (Mistral Small souverain) reportée v2.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.validator.rules import Severity, Violation, apply_rules
from src.validator.corpus_check import CorpusWarning, check_claims_in_corpus
from src.validator.layer3 import Layer3Validator, Layer3Warning


@dataclass
class ValidatorResult:
    honesty_score: float  # 0.0 (pire) .. 1.0 (parfait)
    rule_violations: list[Violation] = field(default_factory=list)
    corpus_warnings: list[CorpusWarning] = field(default_factory=list)
    layer3_warnings: list[Layer3Warning] = field(default_factory=list)
    flagged: bool = False  # True si >= 1 violation BLOCKING ou corpus_warning

    def summary(self) -> str:
        """Résumé lisible pour log / debug."""
        lines = [
            f"honesty_score={self.honesty_score:.2f} "
            f"flagged={self.flagged} "
            f"rules={len(self.rule_violations)} "
            f"corpus={len(self.corpus_warnings)} "
            f"layer3={len(self.layer3_warnings)}"
        ]
        for v in self.rule_violations:
            lines.append(f"  [{v.severity.value}] {v.rule_id}: {v.matched_text!r}")
        for w in self.corpus_warnings:
            lines.append(
                f"  [corpus] {w.claim!r} (sim={w.similarity}, "
                f"closest={w.closest_match!r})"
            )
        for lw in self.layer3_warnings:
            lines.append(f"  [layer3] {lw.claim!r} — {lw.reason}")
        return "\n".join(lines)


# Pondération du score honnêteté
_SCORE_PENALTIES: dict[Severity, float] = {
    Severity.BLOCKING: 0.15,
    Severity.WARNING: 0.05,
    Severity.INFO: 0.02,
}
_CORPUS_PENALTY = 0.10
_LAYER3_PENALTY = 0.05  # warning layer3 = mêmme pondération que WARN rule


class Validator:
    """Orchestrateur règles + corpus-check + (optionnel) couche 3 LLM souverain.

    Usage simple (couches 1+2 uniquement) :
        v = Validator(fiches=corpus)
        result = v.validate(answer_text)

    Usage complet V2 avec couche 3 Mistral Small :
        from src.validator.layer3 import Layer3Validator
        layer3 = Layer3Validator(client=mistral_client)
        v = Validator(fiches=corpus, layer3=layer3)
        result = v.validate(answer_text)
    """

    def __init__(
        self,
        fiches: list[dict],
        corpus_sim_threshold: float = 0.30,
        layer3: Layer3Validator | None = None,
    ):
        self.fiches = fiches
        self.corpus_sim_threshold = corpus_sim_threshold
        self.layer3 = layer3

    def validate(self, answer: str) -> ValidatorResult:
        rule_violations = apply_rules(answer)
        corpus_warnings = check_claims_in_corpus(
            answer, self.fiches, threshold=self.corpus_sim_threshold
        )
        # Couche 3 optionnelle (V2). Si pas de client → return [] graceful.
        layer3_warnings: list[Layer3Warning] = []
        if self.layer3 is not None:
            layer3_warnings = self.layer3.check(answer)

        honesty_score = self._compute_honesty(
            rule_violations, corpus_warnings, layer3_warnings
        )
        flagged = (
            any(v.severity == Severity.BLOCKING for v in rule_violations)
            or len(corpus_warnings) > 0
        )
        # Couche 3 : n'escalade pas à `flagged` en v2 (= WARN severity
        # contribuant juste au score + β Warn footer via policy). Changer
        # le mapping si v3 veut bloquer sur layer3.

        return ValidatorResult(
            honesty_score=honesty_score,
            rule_violations=rule_violations,
            corpus_warnings=corpus_warnings,
            layer3_warnings=layer3_warnings,
            flagged=flagged,
        )

    @staticmethod
    def _compute_honesty(
        violations: list[Violation],
        corpus_warnings: list[CorpusWarning],
        layer3_warnings: list[Layer3Warning] | None = None,
    ) -> float:
        score = 1.0
        for v in violations:
            score -= _SCORE_PENALTIES.get(v.severity, 0.05)
        score -= _CORPUS_PENALTY * len(corpus_warnings)
        if layer3_warnings:
            score -= _LAYER3_PENALTY * len(layer3_warnings)
        return max(0.0, min(1.0, score))
