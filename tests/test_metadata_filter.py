"""Tests unitaires Sprint 10 chantier C — src/rag/metadata_filter.py.

Couvre §8.1 + §8.2 du design ADR docs/SPRINT10_RAG_FILTRE_DESIGN.md :
- parse_contraintes (3 edge cases)
- infer_niveau_range (8 patterns + fallback)
- FilterCriteria.is_empty
- apply_metadata_filter (5 critères × match/no-match + composite + asymétrie)
- extract_filter_from_profile end-to-end (profile L1 droit Occitanie)

Pas de plug pipeline ici — skeleton standalone (§8.3 attend chantier B
+ review Matteo design).
"""
from __future__ import annotations

import pytest

from src.rag.metadata_filter import (
    BUDGET_BRACKETS,
    INTERESTS_TO_SECTORS,
    FilterCriteria,
    apply_metadata_filter,
    extract_filter_from_profile,
    infer_niveau_range,
    infer_secteurs,
    normalize_region,
    parse_alternance_value,
    parse_contraintes,
)


# ──────────────────── parse_contraintes ────────────────────


class TestParseContraintes:
    def test_basic_key_value(self):
        result = parse_contraintes(["alternance:true", "budget:moderate"])
        assert result == {"alternance": "true", "budget": "moderate"}

    def test_item_without_colon_ignored(self):
        result = parse_contraintes(["alternance:true", "garbage", "budget:low"])
        assert result == {"alternance": "true", "budget": "low"}

    def test_multiple_colons_split_first(self):
        result = parse_contraintes(["region:auvergne-rhone-alpes"])
        assert result == {"region": "auvergne-rhone-alpes"}

    def test_keys_and_values_lowercase_trim(self):
        result = parse_contraintes(["  ALTernance  :  TRUE  "])
        assert result == {"alternance": "true"}

    def test_empty_list(self):
        assert parse_contraintes([]) == {}

    def test_non_string_items_silently_skipped(self):
        result = parse_contraintes(["alternance:true", 42, None, "budget:low"])  # type: ignore
        assert result == {"alternance": "true", "budget": "low"}


# ──────────────────── normalize_region ────────────────────


class TestNormalizeRegion:
    def test_basic(self):
        assert normalize_region("Occitanie") == "occitanie"

    def test_trim(self):
        assert normalize_region("  Île-de-France  ") == "île-de-france"

    def test_none(self):
        assert normalize_region(None) is None

    def test_empty_string(self):
        assert normalize_region("") is None

    def test_whitespace_only(self):
        assert normalize_region("   ") is None


# ──────────────────── infer_niveau_range ────────────────────


class TestInferNiveauRange:
    @pytest.mark.parametrize(
        "niveau_scolaire,expected",
        [
            ("terminale_spe_maths_physique", (1, 5)),
            ("terminale_generale", (1, 5)),
            ("seconde_generale", (1, 3)),
            ("premiere_techno_sti2d", (1, 3)),
            ("l1_droit", (2, 5)),
            ("l1_droit_redoublement", (2, 5)),
            ("Bac+1 économie", (2, 5)),
            ("l2_psycho", (2, 5)),
            ("BTS_compta", (2, 5)),
            ("but_info", (2, 5)),
            ("l3_histoire", (3, 5)),
            ("licence_droit", (3, 5)),
            ("m1_finance", (4, 5)),
            ("Bac+4 mécanique", (4, 5)),
            ("m2_recherche", (5, 5)),
            ("master_data_science", (5, 5)),
            # Mastère Spécialisé = Bac+6 (correction Matteo 2026-04-29)
            ("mastere_spe_cybersecurite", (6, 6)),
            ("mastère_spécialisé_data", (6, 6)),
            ("MS cybersécurité", (6, 6)),
            ("Bac+6 finance", (6, 6)),
            ("actif_marketing", (2, 5)),
            ("professionnel_RH_reconversion", (2, 5)),
            ("salarie_industrie", (2, 5)),
        ],
    )
    def test_known_patterns(self, niveau_scolaire, expected):
        assert infer_niveau_range(niveau_scolaire) == expected

    def test_mastere_vs_master_distinction(self):
        """Régression critique : 'mastère' (CGE label, Bac+6) ne doit
        JAMAIS être confondu avec 'master' (diplôme national, Bac+5).

        Cette distinction a été insistée par Matteo 2026-04-29 — erreur
        factuelle qu'un retrieval mal calibré ferait passer en silence."""
        # Mastère → 6
        assert infer_niveau_range("mastere_spe_X") == (6, 6)
        assert infer_niveau_range("mastère_spécialisé") == (6, 6)
        # Master → 5
        assert infer_niveau_range("master_data") == (5, 5)
        assert infer_niveau_range("m2_finance") == (5, 5)

    def test_unknown_pattern_returns_none(self):
        assert infer_niveau_range("xyz_random_thing") == (None, None)

    def test_none_input(self):
        assert infer_niveau_range(None) == (None, None)

    def test_empty_string_input(self):
        assert infer_niveau_range("") == (None, None)


# ──────────────────── infer_secteurs ────────────────────


class TestInferSecteurs:
    def test_known_interest_maps(self):
        assert "informatique" in (infer_secteurs(["code"]) or [])

    def test_multiple_interests_dedup_and_sort(self):
        result = infer_secteurs(["code", "ia", "data"])
        assert result is not None
        # ia + data + code → tous mappés vers ["informatique", "data_science", "numerique"]
        assert "informatique" in result
        assert "data_science" in result
        assert result == sorted(result)  # tri déterministe

    def test_empty_list_returns_none(self):
        assert infer_secteurs([]) is None

    def test_unknown_interest_returns_none(self):
        assert infer_secteurs(["xyz_unknown"]) is None

    def test_mix_known_unknown_returns_only_known(self):
        result = infer_secteurs(["droit", "xyz_unknown"])
        assert result == ["droit", "juridique"]

    def test_non_string_skipped(self):
        result = infer_secteurs(["droit", 42, None, "code"])  # type: ignore
        assert result is not None
        assert "droit" in result
        assert "informatique" in result


# ──────────────────── parse_alternance_value ────────────────────


class TestParseAlternanceValue:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("true", True),
            ("True", True),
            ("1", True),
            ("yes", True),
            ("oui", True),
            ("false", False),
            ("False", False),
            ("0", False),
            ("no", False),
            ("non", False),
            ("maybe", None),
            ("", None),
            (None, None),
        ],
    )
    def test_truthy_falsy_mappings(self, value, expected):
        assert parse_alternance_value(value) is expected


# ──────────────────── FilterCriteria.is_empty ────────────────────


class TestFilterCriteriaIsEmpty:
    def test_default_constructor_is_empty(self):
        assert FilterCriteria().is_empty() is True

    def test_one_field_set_not_empty(self):
        assert FilterCriteria(region="occitanie").is_empty() is False

    def test_niveau_min_only_not_empty(self):
        assert FilterCriteria(niveau_min=2).is_empty() is False

    def test_secteur_empty_list_not_empty(self):
        # liste vide ≠ None — donc considérée comme "filtre actif" (sera 0 match)
        assert FilterCriteria(secteur=[]).is_empty() is False


# ──────────────────── apply_metadata_filter — single criterion ────────────────────


def _wrap(fiches: list[dict]) -> list[dict]:
    """Wrap les fiches dans la structure {fiche, score} attendue par retrieve_top_k."""
    return [{"fiche": f, "score": 1.0 - i * 0.01} for i, f in enumerate(fiches)]


class TestApplyMetadataFilterSingleCriterion:
    def test_no_criteria_returns_intact(self):
        fiches = _wrap([{"region": "occitanie"}, {"region": "ile-de-france"}])
        result = apply_metadata_filter(fiches, FilterCriteria())
        # is_empty() == True → liste intacte (même référence)
        assert result is fiches

    def test_region_match_with_national_pass_through(self):
        fiches = _wrap([
            {"region": "occitanie"},
            {"region": "ile-de-france"},
            {"region": "national"},
        ])
        result = apply_metadata_filter(fiches, FilterCriteria(region="occitanie"))
        regions = [r["fiche"]["region"] for r in result]
        assert regions == ["occitanie", "national"]  # national passe toujours

    def test_region_match_case_insensitive(self):
        fiches = _wrap([{"region": "Occitanie"}, {"region": "ile-de-france"}])
        result = apply_metadata_filter(fiches, FilterCriteria(region="OCCITANIE"))
        assert len(result) == 1
        assert result[0]["fiche"]["region"] == "Occitanie"

    def test_region_fiche_sans_info_defensive_pass(self):
        fiches = _wrap([{"region": None}, {"region": "occitanie"}, {}])
        result = apply_metadata_filter(fiches, FilterCriteria(region="occitanie"))
        # Defensive : fiches sans region (None ou clé absente) passent
        assert len(result) == 3

    def test_niveau_range(self):
        fiches = _wrap([
            {"niveau": 1},
            {"niveau": 3},
            {"niveau": 5},
            {"niveau": 7},
        ])
        result = apply_metadata_filter(
            fiches, FilterCriteria(niveau_min=2, niveau_max=5)
        )
        niveaux = [r["fiche"]["niveau"] for r in result]
        assert niveaux == [3, 5]

    def test_niveau_min_only(self):
        fiches = _wrap([{"niveau": 1}, {"niveau": 3}, {"niveau": 5}])
        result = apply_metadata_filter(fiches, FilterCriteria(niveau_min=3))
        assert len(result) == 2
        assert [r["fiche"]["niveau"] for r in result] == [3, 5]

    def test_niveau_fiche_sans_info_defensive_pass(self):
        fiches = _wrap([{"niveau": None}, {"niveau": 3}, {}])
        result = apply_metadata_filter(
            fiches, FilterCriteria(niveau_min=2, niveau_max=5)
        )
        assert len(result) == 3

    def test_alternance_strict_excludes_unknown(self):
        fiches = _wrap([
            {"alternance": True},
            {"alternance": False},
            {"alternance": None},
            {},
        ])
        result = apply_metadata_filter(fiches, FilterCriteria(alternance=True))
        # Asymétrie stricte : fiches sans info (None ou clé absente) exclues
        assert len(result) == 1
        assert result[0]["fiche"]["alternance"] is True

    def test_budget_lte_cap(self):
        fiches = _wrap([
            {"budget": 0},
            {"budget": 3000},
            {"budget": 8000},
        ])
        result = apply_metadata_filter(fiches, FilterCriteria(budget_max=5000))
        budgets = [r["fiche"]["budget"] for r in result]
        assert budgets == [0, 3000]

    def test_budget_fiche_sans_info_defensive_pass(self):
        fiches = _wrap([{"budget": None}, {}, {"budget": 3000}, {"budget": 8000}])
        result = apply_metadata_filter(fiches, FilterCriteria(budget_max=5000))
        # Defensive : fiches sans budget passent (formations sans tarif affiché)
        budgets = [r["fiche"].get("budget") for r in result]
        assert budgets == [None, None, 3000]

    def test_secteur_in_list(self):
        fiches = _wrap([
            {"secteur": "informatique"},
            {"secteur": "droit"},
            {"secteur": "sante"},
        ])
        result = apply_metadata_filter(
            fiches, FilterCriteria(secteur=["informatique", "data_science"])
        )
        assert len(result) == 1
        assert result[0]["fiche"]["secteur"] == "informatique"

    def test_secteur_strict_excludes_unknown(self):
        fiches = _wrap([{"secteur": None}, {}, {"secteur": "informatique"}])
        result = apply_metadata_filter(
            fiches, FilterCriteria(secteur=["informatique"])
        )
        # Asymétrie stricte : fiches sans secteur exclues
        assert len(result) == 1
        assert result[0]["fiche"]["secteur"] == "informatique"

    def test_secteur_list_in_fiche(self):
        # fiche peut avoir une liste de secteurs (pluri-disciplinaire)
        fiches = _wrap([
            {"secteur": ["informatique", "data_science"]},
            {"secteur": ["droit"]},
        ])
        result = apply_metadata_filter(
            fiches, FilterCriteria(secteur=["data_science"])
        )
        assert len(result) == 1


# ──────────────────── apply_metadata_filter — composite ────────────────────


class TestApplyMetadataFilterComposite:
    def test_region_alternance_niveau_AND(self):
        fiches = _wrap([
            {"region": "occitanie", "niveau": 3, "alternance": True, "secteur": "informatique"},
            {"region": "occitanie", "niveau": 3, "alternance": False, "secteur": "informatique"},
            {"region": "ile-de-france", "niveau": 3, "alternance": True, "secteur": "informatique"},
            {"region": "occitanie", "niveau": 5, "alternance": True, "secteur": "informatique"},
            {"region": "national", "niveau": 3, "alternance": True, "secteur": "informatique"},
        ])
        criteria = FilterCriteria(
            region="occitanie",
            niveau_min=2,
            niveau_max=4,
            alternance=True,
            secteur=["informatique"],
        )
        result = apply_metadata_filter(fiches, criteria)
        # Match : occitanie + niveau ∈ [2,4] + alternance=True + secteur=informatique
        # idx 0 ✅ ; idx 1 ❌ (alternance False) ; idx 2 ❌ (région) ;
        # idx 3 ❌ (niveau 5 > 4) ; idx 4 ✅ (national passe + autres OK)
        assert len(result) == 2

    def test_empty_result_no_crash(self):
        fiches = _wrap([
            {"region": "ile-de-france", "alternance": False},
        ])
        criteria = FilterCriteria(region="occitanie", alternance=True)
        result = apply_metadata_filter(fiches, criteria)
        assert result == []

    def test_empty_input_returns_empty(self):
        assert apply_metadata_filter([], FilterCriteria(region="occitanie")) == []


# ──────────────────── extract_filter_from_profile (end-to-end) ────────────────────


class TestExtractFilterFromProfile:
    def test_l1_droit_occitanie_typical_profile(self):
        profile_delta = {
            "region": "Occitanie",
            "niveau_scolaire": "l1_droit_redoublement",
            "contraintes": ["alternance:false", "budget:moderate"],
            "interets_detectes": ["droit", "psychologie"],
            "valeurs": ["impact_societal"],
            "questions_ouvertes": [],
            "confidence": 0.85,
        }
        criteria = extract_filter_from_profile(profile_delta)
        assert criteria.region == "occitanie"
        assert criteria.niveau_min == 2
        assert criteria.niveau_max == 5
        assert criteria.alternance is False
        assert criteria.budget_max == BUDGET_BRACKETS["moderate"]
        assert criteria.secteur is not None
        assert "droit" in criteria.secteur
        assert "psychologie" in criteria.secteur

    def test_empty_profile_yields_empty_criteria(self):
        criteria = extract_filter_from_profile({})
        assert criteria.is_empty() is True

    def test_terminale_with_alternance_constraint(self):
        profile_delta = {
            "niveau_scolaire": "terminale_spe_maths_physique",
            "contraintes": ["alternance:oui"],
            "interets_detectes": ["informatique"],
        }
        criteria = extract_filter_from_profile(profile_delta)
        assert criteria.niveau_min == 1
        assert criteria.niveau_max == 5
        assert criteria.alternance is True
        assert criteria.secteur is not None
        assert "informatique" in criteria.secteur

    def test_robust_to_none_values(self):
        profile_delta = {
            "region": None,
            "niveau_scolaire": None,
            "contraintes": None,
            "interets_detectes": None,
            "confidence": 0.0,
        }
        criteria = extract_filter_from_profile(profile_delta)
        assert criteria.is_empty() is True

    def test_budget_high_means_no_cap(self):
        profile_delta = {"contraintes": ["budget:high"]}
        criteria = extract_filter_from_profile(profile_delta)
        assert criteria.budget_max is None  # high → pas de borne

    def test_unknown_budget_value_yields_none(self):
        profile_delta = {"contraintes": ["budget:enormous"]}
        criteria = extract_filter_from_profile(profile_delta)
        assert criteria.budget_max is None


# ──────────────────── Lookup tables sanity ────────────────────


class TestLookupTables:
    def test_budget_brackets_consistent(self):
        assert "low" in BUDGET_BRACKETS
        assert "moderate" in BUDGET_BRACKETS
        assert "high" in BUDGET_BRACKETS
        assert BUDGET_BRACKETS["low"] is not None
        assert BUDGET_BRACKETS["moderate"] is not None
        assert BUDGET_BRACKETS["high"] is None  # high = pas de cap

    def test_interests_to_sectors_no_empty_lists(self):
        for interest, sectors in INTERESTS_TO_SECTORS.items():
            assert isinstance(sectors, list), f"{interest} ne mappe pas vers une liste"
            assert len(sectors) > 0, f"{interest} mappe vers une liste vide"

    def test_interests_keys_lowercase(self):
        for interest in INTERESTS_TO_SECTORS:
            assert interest == interest.lower(), (
                f"clé {interest!r} doit être lowercase pour match"
            )
