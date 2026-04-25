"""Tests `dedup_parcoursup_by_cod_aff_form` (ADR-050)."""
from __future__ import annotations

import pytest

from src.collect.merge import dedup_parcoursup_by_cod_aff_form


class TestDedup:
    def test_no_duplicates_passthrough(self):
        fiches = [
            {"cod_aff_form": "1", "nom": "A"},
            {"cod_aff_form": "2", "nom": "B"},
            {"cod_aff_form": "3", "nom": "C"},
        ]
        out = dedup_parcoursup_by_cod_aff_form(fiches)
        assert len(out) == 3
        assert [f["nom"] for f in out] == ["A", "B", "C"]

    def test_simple_pair_keeps_richer(self):
        legacy = {"cod_aff_form": "42", "nom": "X", "labels": ["SecNumEdu"]}
        extended = {
            "cod_aff_form": "42",
            "nom": "X",
            "etablissement": "Lycée Z",
            "ville": "Paris",
            "insertion_pro": {"taux": 0.85},
            "trends": {"y": 1},
        }
        out = dedup_parcoursup_by_cod_aff_form([legacy, extended])
        assert len(out) == 1
        merged = out[0]
        assert merged["cod_aff_form"] == "42"
        # extended is richer (more filled fields) → base
        assert merged["etablissement"] == "Lycée Z"
        assert merged["insertion_pro"] == {"taux": 0.85}
        # labels from legacy preserved
        assert merged["labels"] == ["SecNumEdu"]

    def test_three_fiches_same_caf(self):
        a = {"cod_aff_form": "X", "nom": "n", "field_a": 1}
        b = {"cod_aff_form": "X", "nom": "n", "field_b": 2, "field_c": 3}
        c = {"cod_aff_form": "X", "nom": "n", "field_c": 99}  # field_c overlap
        out = dedup_parcoursup_by_cod_aff_form([a, b, c])
        assert len(out) == 1
        merged = out[0]
        assert merged["field_a"] == 1
        assert merged["field_b"] == 2
        # b is richer than c, b's field_c=3 wins (first non-empty rule, b is base)
        assert merged["field_c"] == 3

    def test_empty_caf_passthrough(self):
        fiches = [
            {"cod_aff_form": "", "nom": "X"},
            {"cod_aff_form": None, "nom": "Y"},
            {"nom": "Z"},  # no cod_aff_form key
        ]
        out = dedup_parcoursup_by_cod_aff_form(fiches)
        assert len(out) == 3

    def test_mixed_caf_and_no_caf(self):
        fiches = [
            {"cod_aff_form": "1", "nom": "A"},
            {"nom": "no-caf-1"},
            {"cod_aff_form": "1", "nom": "A_dup"},  # dup of first
            {"nom": "no-caf-2"},
            {"cod_aff_form": "2", "nom": "B"},
        ]
        out = dedup_parcoursup_by_cod_aff_form(fiches)
        assert len(out) == 4  # 2 unique caf + 2 no-caf
        names = [f["nom"] for f in out]
        assert "no-caf-1" in names
        assert "no-caf-2" in names

    def test_preserves_order_first_caf_seen(self):
        fiches = [
            {"cod_aff_form": "Z", "nom": "z1"},
            {"cod_aff_form": "A", "nom": "a"},
            {"cod_aff_form": "Z", "nom": "z2"},
            {"cod_aff_form": "M", "nom": "m"},
        ]
        out = dedup_parcoursup_by_cod_aff_form(fiches)
        assert [f["cod_aff_form"] for f in out] == ["Z", "A", "M"]

    def test_empty_list(self):
        assert dedup_parcoursup_by_cod_aff_form([]) == []

    def test_legacy_labels_field_preserved(self):
        """Régression : labels est le champ ADR-002 reranker, à préserver."""
        legacy = {
            "cod_aff_form": "10",
            "nom": "n",
            "labels": ["SecNumEdu"],
            "match_method": "rncp",
        }
        extended = {
            "cod_aff_form": "10",
            "nom": "n",
            "ville": "Paris",
            "departement": "75",
            "phase": "initial",
            "niveau": "bac+3",
            "insertion_pro": {"x": 1},
            "trends": {"y": 1},
            "provenance": "ext",
        }
        out = dedup_parcoursup_by_cod_aff_form([legacy, extended])
        assert len(out) == 1
        merged = out[0]
        assert merged["labels"] == ["SecNumEdu"]
        assert merged["match_method"] == "rncp"
        assert merged["insertion_pro"] == {"x": 1}
