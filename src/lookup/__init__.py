"""Lookup déterministe — Chantier 2 (2026-05-03).

Pour les questions factuelles pointues sur UNE formation nommée
(taux d'accès EFREI Bordeaux ? salaire sortie LEA Sorbonne ?), on
bypasse le RAG et on fait un SELECT déterministe sur formations.json.

Argument démo INRIA : « les chiffres viennent toujours d'un lookup,
jamais d'une génération. Zéro hallu chiffres par construction. »
"""
from src.lookup.structured_select import (
    Entity,
    FUZZY_THRESHOLD,
    INVALID_VALUES,
    SELECT_FIELD_PATTERNS,
    SelectResult,
    extract_entity_simple,
    extract_field,
    format_select_response,
    is_valid_field_value,
    lookup_formation,
    try_select_or_none,
)

__all__ = [
    "Entity",
    "FUZZY_THRESHOLD",
    "INVALID_VALUES",
    "SELECT_FIELD_PATTERNS",
    "SelectResult",
    "extract_entity_simple",
    "extract_field",
    "format_select_response",
    "is_valid_field_value",
    "lookup_formation",
    "try_select_or_none",
]
