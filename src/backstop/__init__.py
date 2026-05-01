"""Backstop layer — post-LLM filters for hallucination mitigation.

Sprint 11 P1-1 backstop B soft : annotation des chiffres non-sourcés
(taux, salaires) sans effacement, via post-filter Python + cross-ref
corpus. La réponse Mistral reste lisible, le frontend interprète les
balises pour soulignement pointillé Spellcheck-like.
"""
from src.backstop.soft_annotator import (
    CorpusFactIndex,
    DISCLAIMER,
    annotate_response,
)

__all__ = ["CorpusFactIndex", "DISCLAIMER", "annotate_response"]
