"""Tests src/collect/insersup_attach.py — Phase A.3 du plan corpus v5.

Couvre la cascade niveau 1/2/3 (UAI×type×discipline / type×discipline×region /
type×discipline national), les edge cases (min_sortants, replace_existing,
type non inférable), et l'idempotence.
"""
from __future__ import annotations

import json
from pathlib import Path

from src.collect.insersup_attach import (
    PARCOURSUP_TO_INSERSUP_TYPE,
    NIVEAU_TO_DEFAULT_TYPE,
    attach_insersup_to_fiches,
    _build_etab_index,
    _build_region_index,
    _build_national_index,
    _infer_insersup_type,
    _norm_key,
    _has_any_taux,
    _pick_freshest_etab,
)


# ─────────────── Fixtures InserSup (raw + corpus) ───────────────


def insersup_raw_records() -> list[dict]:
    """Reproduit le schema `insersup_insertion.json` (raw API)."""
    return [
        # Niveau 1 — Master LMD Droit, Université Paris 1 cohorte 2020
        {
            "source": "insersup",
            "etablissement": "Université Paris 1 Panthéon-Sorbonne",
            "uai": "0751717J",
            "type_diplome": "Master LMD",
            "niveau_orientia": "bac+5",
            "discipline": "Droit, sciences politiques",
            "region": "Île-de-France",
            "cohorte_promo": "2020",
            "nb_sortants": 461,
            "nb_poursuivants": 211,
            "taux_emploi_salarie_fr": {
                "6m": 0.38, "12m": 0.58, "18m": 0.58, "24m": 0.64, "30m": 0.61,
            },
        },
        # Niveau 1 — même UAI mais cohorte 2019 (moins fraîche, à exclure)
        {
            "source": "insersup",
            "etablissement": "Université Paris 1 Panthéon-Sorbonne",
            "uai": "0751717J",
            "type_diplome": "Master LMD",
            "discipline": "Droit, sciences politiques",
            "region": "Île-de-France",
            "cohorte_promo": "2019",
            "nb_sortants": 410,
            "taux_emploi_salarie_fr": {"12m": 0.55, "24m": 0.62},
        },
        # Cohorte avec sortants sous le seuil min (à skipper)
        {
            "source": "insersup",
            "etablissement": "Petit Établissement de Niche",
            "uai": "0999999X",
            "type_diplome": "Master LMD",
            "discipline": "STAPS",
            "region": "Bretagne",
            "cohorte_promo": "2020",
            "nb_sortants": 12,  # < 30 → low_sortants
            "taux_emploi_salarie_fr": {"12m": 0.5},
        },
    ]


def insersup_corpus_records() -> list[dict]:
    """Reproduit le schema `insersup_corpus.json` (agrégé regional + national)."""
    return [
        # Niveau 2 — Master Droit en Auvergne-Rhône-Alpes
        {
            "id": "insersup:master-lmd:droit:auvergne-rhone-alpes",
            "domain": "insertion_pro",
            "source": "insersup_mesr",
            "type_diplome": "Master LMD",
            "discipline": "Droit, sciences politiques",
            "region": "Auvergne-Rhône-Alpes",
            "cohorte": "2020",
            "nb_sortants": 854,
            "taux_emploi_6m": 0.45,
            "taux_emploi_12m": 0.65,
            "taux_emploi_18m": 0.70,
            "taux_emploi_24m": 0.74,
            "taux_emploi_30m": 0.74,
        },
        # Niveau 3 — Master Droit national agrégé
        {
            "id": "insersup:master-lmd:droit:national",
            "domain": "insertion_pro",
            "source": "insersup_mesr",
            "type_diplome": "Master LMD",
            "discipline": "Droit, sciences politiques",
            "region": None,  # national
            "cohorte": "2020",
            "nb_sortants": 12500,
            "taux_emploi_6m": 0.42,
            "taux_emploi_12m": 0.62,
            "taux_emploi_18m": 0.68,
            "taux_emploi_24m": 0.72,
            "taux_emploi_30m": 0.71,
        },
        # Niveau 3 — Sciences éco national (autre discipline)
        {
            "id": "insersup:master-lmd:sciences-eco:national",
            "domain": "insertion_pro",
            "source": "insersup_mesr",
            "type_diplome": "Master LMD",
            "discipline": "Sciences économiques, gestion",
            "region": None,
            "cohorte": "2020",
            "nb_sortants": 9800,
            "taux_emploi_12m": 0.78,
            "taux_emploi_24m": 0.85,
        },
    ]


def _write_fixtures(tmp_path: Path) -> tuple[Path, Path]:
    """Écrit les fixtures dans tmp et retourne (records_path, corpus_path)."""
    records_path = tmp_path / "insersup_insertion.json"
    corpus_path = tmp_path / "insersup_corpus.json"
    records_path.write_text(
        json.dumps(insersup_raw_records()), encoding="utf-8"
    )
    corpus_path.write_text(
        json.dumps(insersup_corpus_records()), encoding="utf-8"
    )
    return records_path, corpus_path


# ─────────────── Fixtures fiches (cibles attach) ───────────────


def fiche_master_paris1_avec_uai() -> dict:
    """Fiche MonMaster Master Droit avec UAI matchant niveau 1."""
    return {
        "source": "monmaster",
        "nom": "Master Droit des affaires",
        "etablissement": "Université Paris 1 Panthéon-Sorbonne",
        "uai": "0751717J",
        "ville": "Paris",
        "region": "Île-de-France",
        "niveau": "bac+5",
        "type_diplome": "Master LMD",
        "discipline": "Droit, sciences politiques",
    }


def fiche_master_lyon3_sans_uai() -> dict:
    """Fiche MonMaster sans UAI matchant InserSup → niveau 2 (region)."""
    return {
        "source": "monmaster",
        "nom": "Master Droit Européen",
        "etablissement": "Université Jean Moulin Lyon 3",
        # uai absent → pas de niveau 1
        "region": "Auvergne-Rhône-Alpes",
        "niveau": "bac+5",
        "type_diplome": "Master LMD",
        "discipline": "Droit, sciences politiques",
    }


def fiche_master_droit_inconnue_region() -> dict:
    """Fiche dans une région non couverte par InserSup → niveau 3 (national)."""
    return {
        "source": "monmaster",
        "nom": "Master Droit",
        "etablissement": "Université Inconnue",
        "region": "Corse",  # pas dans nos fixtures
        "niveau": "bac+5",
        "type_diplome": "Master LMD",
        "discipline": "Droit, sciences politiques",
    }


def fiche_bts_pas_dans_insersup() -> dict:
    """BTS — InserSup ne couvre pas les BTS, doit produire no_match."""
    return {
        "source": "parcoursup",
        "nom": "BTS Cybersécurité",
        "etablissement": "Lycée Vauban",
        "ville": "Brest",
        "region": "Bretagne",
        "niveau": "bac+2",
        "type_diplome": "BTS",
    }


def fiche_sans_discipline() -> dict:
    """Pas de champ discipline → impossible de matcher."""
    return {
        "source": "monmaster",
        "nom": "Formation X",
        "niveau": "bac+5",
        "type_diplome": "Master LMD",
        # pas de discipline
    }


def fiche_avec_insertion_pro_existante() -> dict:
    """Fiche déjà enrichie d'un insertion_pro Cereq."""
    return {
        "source": "monmaster",
        "nom": "Master Droit Pré-attaché",
        "uai": "0751717J",
        "etablissement": "Université Paris 1 Panthéon-Sorbonne",
        "region": "Île-de-France",
        "niveau": "bac+5",
        "type_diplome": "Master LMD",
        "discipline": "Droit, sciences politiques",
        "insertion_pro": {
            "source": "cereq",  # ancien Cereq agrégat
            "taux_emploi_3ans": 0.85,
        },
    }


# ─────────────── _norm_key ───────────────


class TestNormKey:
    def test_strips_accents_and_case(self):
        assert _norm_key("Île-de-France") == "ile-de-france"
        assert _norm_key("AUVERGNE-RHÔNE-ALPES") == _norm_key("Auvergne-Rhône-Alpes")

    def test_handles_none(self):
        assert _norm_key(None) == ""

    def test_handles_whitespace(self):
        assert _norm_key("  Test  ") == "test"


# ─────────────── _infer_insersup_type ───────────────


class TestInferInsersupType:
    def test_master_lmd_passthrough(self):
        assert _infer_insersup_type({"type_diplome": "Master LMD"}) == "Master LMD"

    def test_licence_pro_normalized(self):
        assert _infer_insersup_type({"type_diplome": "Licence pro"}) == "Licence professionnelle"

    def test_fallback_from_niveau_bac5(self):
        assert _infer_insersup_type({"niveau": "bac+5"}) == "Master LMD"

    def test_fallback_from_niveau_bac3(self):
        assert _infer_insersup_type({"niveau": "bac+3"}) == "Licence générale"

    def test_bts_returns_none(self):
        """BTS pas couvert par InserSup."""
        assert _infer_insersup_type({"niveau": "bac+2", "type_diplome": "BTS"}) is None

    def test_unknown_returns_none(self):
        assert _infer_insersup_type({}) is None


# ─────────────── Index inversés ───────────────


class TestIndexBuilders:
    def test_etab_index_built_from_uai(self):
        idx = _build_etab_index(insersup_raw_records())
        # Master LMD × Droit × Paris 1 → 2 records (cohorte 2020 et 2019)
        key = (_norm_key("0751717J"), _norm_key("Master LMD"), _norm_key("Droit, sciences politiques"))
        assert key in idx
        assert len(idx[key]) == 2

    def test_region_index_excludes_national(self):
        idx = _build_region_index(insersup_corpus_records())
        # Doit avoir Auvergne-Rhône-Alpes
        key = (
            _norm_key("Master LMD"),
            _norm_key("Droit, sciences politiques"),
            _norm_key("Auvergne-Rhône-Alpes"),
        )
        assert key in idx
        # Ne doit pas avoir le national
        for k in idx.keys():
            assert k[2]  # region toujours présente

    def test_national_index_only_records_with_null_region(self):
        idx = _build_national_index(insersup_corpus_records())
        key = (_norm_key("Master LMD"), _norm_key("Droit, sciences politiques"))
        assert key in idx
        # Sciences éco aussi
        assert (_norm_key("Master LMD"), _norm_key("Sciences économiques, gestion")) in idx


# ─────────────── _pick_freshest_etab ───────────────


class TestPickFreshest:
    def test_picks_latest_cohorte(self):
        records = [r for r in insersup_raw_records() if r.get("cohorte_promo") in ("2019", "2020")]
        fresh = _pick_freshest_etab(records)
        assert fresh["cohorte_promo"] == "2020"

    def test_handles_empty(self):
        assert _pick_freshest_etab([]) is None


# ─────────────── _has_any_taux ───────────────


class TestHasAnyTaux:
    def test_returns_true_with_one_horizon(self):
        assert _has_any_taux({"taux_emploi_12m": 0.6})

    def test_returns_false_when_all_null(self):
        assert not _has_any_taux({
            "taux_emploi_6m": None, "taux_emploi_12m": None,
            "taux_emploi_18m": None, "taux_emploi_24m": None, "taux_emploi_30m": None,
        })


# ─────────────── attach_insersup_to_fiches — cascade ───────────────


class TestAttachCascade:
    def test_niveau_1_etablissement_x_discipline(self, tmp_path):
        records_path, corpus_path = _write_fixtures(tmp_path)
        fiches = [fiche_master_paris1_avec_uai()]
        enriched, stats = attach_insersup_to_fiches(
            fiches, records_path, corpus_path
        )
        ip = enriched[0]["insertion_pro"]
        assert ip["granularite"] == "etablissement_x_discipline"
        assert ip["match_score"] == 1.0
        assert ip["cohorte"] == "2020"  # freshest
        assert ip["nombre_sortants"] == 461
        assert ip["taux_emploi_12m"] == 0.58
        assert stats["n_attached_etablissement_x_discipline"] == 1

    def test_niveau_2_discipline_region(self, tmp_path):
        records_path, corpus_path = _write_fixtures(tmp_path)
        fiches = [fiche_master_lyon3_sans_uai()]
        enriched, stats = attach_insersup_to_fiches(
            fiches, records_path, corpus_path
        )
        ip = enriched[0]["insertion_pro"]
        assert ip["granularite"] == "discipline_region"
        assert ip["match_score"] == 0.7
        assert ip["nombre_sortants"] == 854
        assert stats["n_attached_discipline_region"] == 1

    def test_niveau_3_discipline_nationale(self, tmp_path):
        records_path, corpus_path = _write_fixtures(tmp_path)
        fiches = [fiche_master_droit_inconnue_region()]
        enriched, stats = attach_insersup_to_fiches(
            fiches, records_path, corpus_path
        )
        ip = enriched[0]["insertion_pro"]
        assert ip["granularite"] == "discipline_nationale"
        assert ip["match_score"] == 0.4
        assert ip["nombre_sortants"] == 12500
        assert stats["n_attached_discipline_nationale"] == 1

    def test_no_match_for_bts(self, tmp_path):
        records_path, corpus_path = _write_fixtures(tmp_path)
        fiches = [fiche_bts_pas_dans_insersup()]
        enriched, stats = attach_insersup_to_fiches(
            fiches, records_path, corpus_path
        )
        assert "insertion_pro" not in enriched[0]
        assert stats["n_no_match"] == 1
        assert stats["n_skipped_no_type_inferable"] == 1  # niveau bac+2 sans BUT

    def test_no_match_when_discipline_missing(self, tmp_path):
        records_path, corpus_path = _write_fixtures(tmp_path)
        fiches = [fiche_sans_discipline()]
        enriched, stats = attach_insersup_to_fiches(
            fiches, records_path, corpus_path
        )
        assert "insertion_pro" not in enriched[0]
        assert stats["n_no_match"] == 1


class TestMinSortants:
    def test_skips_low_sortants_at_niveau_1(self, tmp_path):
        records_path, corpus_path = _write_fixtures(tmp_path)
        # Crée une fiche qui correspondrait à un record avec 12 sortants
        fiche = {
            "source": "monmaster",
            "nom": "Master STAPS",
            "uai": "0999999X",
            "etablissement": "Petit Établissement de Niche",
            "region": "Bretagne",
            "niveau": "bac+5",
            "type_diplome": "Master LMD",
            "discipline": "STAPS",
        }
        enriched, stats = attach_insersup_to_fiches(
            [fiche], records_path, corpus_path, min_sortants=30
        )
        # Niveau 1 skippé (12 < 30) → no_match
        assert "insertion_pro" not in enriched[0]
        assert stats["n_skipped_low_sortants"] >= 1


class TestReplaceExisting:
    def test_skips_existing_by_default(self, tmp_path):
        records_path, corpus_path = _write_fixtures(tmp_path)
        fiches = [fiche_avec_insertion_pro_existante()]
        enriched, stats = attach_insersup_to_fiches(
            fiches, records_path, corpus_path
        )
        # Default replace_existing=False → préserve l'ancien
        assert enriched[0]["insertion_pro"]["source"] == "cereq"
        assert stats["n_with_existing_insertion_pro"] == 1
        assert stats["n_skipped_existing"] == 1

    def test_replaces_when_flag_set(self, tmp_path):
        records_path, corpus_path = _write_fixtures(tmp_path)
        fiches = [fiche_avec_insertion_pro_existante()]
        enriched, stats = attach_insersup_to_fiches(
            fiches, records_path, corpus_path, replace_existing=True
        )
        # Doit remplacer Cereq par InserSup
        assert enriched[0]["insertion_pro"]["source"] == "insersup_mesr"
        assert enriched[0]["insertion_pro"]["granularite"] == "etablissement_x_discipline"
        assert stats["n_replaced"] == 1


# ─────────────── Idempotence (rerun = pareil) ───────────────


class TestIdempotence:
    def test_rerun_same_output(self, tmp_path):
        records_path, corpus_path = _write_fixtures(tmp_path)
        fiches_1 = [fiche_master_paris1_avec_uai()]
        attach_insersup_to_fiches(fiches_1, records_path, corpus_path)

        fiches_2 = [fiche_master_paris1_avec_uai()]
        attach_insersup_to_fiches(fiches_2, records_path, corpus_path)

        assert fiches_1[0]["insertion_pro"] == fiches_2[0]["insertion_pro"]


# ─────────────── Gracieux si fichiers manquants ───────────────


class TestGracefulDegradation:
    def test_no_records_file_returns_no_match(self, tmp_path):
        # Pas de fichiers — l'attach ne crash pas, no_match partout
        fiches = [fiche_master_paris1_avec_uai()]
        absent_records = tmp_path / "absent_records.json"
        absent_corpus = tmp_path / "absent_corpus.json"
        enriched, stats = attach_insersup_to_fiches(
            fiches, absent_records, absent_corpus
        )
        assert "insertion_pro" not in enriched[0]
        assert stats["n_no_match"] == 1


# ─────────────── Provenance / FactCard compat (intégration ADR-055) ───────────────


class TestInsersupAttachProvenanceCompat:
    """Vérifie que les fiches enrichies par InserSup sont compatibles avec
    la FactCard de Phase A.1 (provenance.tier inférée correctement)."""

    def test_enriched_fiche_keeps_original_source_tier(self, tmp_path):
        from src.rag.fact_card import fiche_to_fact_card
        records_path, corpus_path = _write_fixtures(tmp_path)
        fiches = [fiche_master_paris1_avec_uai()]
        enriched, _ = attach_insersup_to_fiches(fiches, records_path, corpus_path)

        # La fiche conserve son `source: monmaster` → tier_1 inféré
        card = fiche_to_fact_card(enriched[0], fact_id="S1")
        assert card.provenance is not None
        assert card.provenance.tier == "tier_1"
        # source_label : la fiche est issue MonMaster
        assert card.provenance.source_label == "MonMaster"
