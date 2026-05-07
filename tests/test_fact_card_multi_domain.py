"""Tests d'intégration FactCard ↔ corpora multi-domaines — Phase A.5 du plan corpus v5.

Charge 1 fixture par corpus annexe (15 corpora 100% conformes selon Phase A.4)
et vérifie que `fiche_to_fact_card` produit une FactCard valide pour chacun :

1. **Robustesse** : pas de throw sur les schémas hétérogènes
2. **Identité** : `formation` non-vide grâce à la cascade `_pick_formation_name`
3. **Provenance** : `tier` correctement inféré depuis `source` (ADR-055)
4. **Text retrievable** : `text_libre` populé pour les corpora annexes (qui ont un `text` natif)
5. **Chiffres** : strict v4 R1 préservé — chiffres absents → `null` explicites

Les 2 corpora non-conformes identifiés en Phase A.4 (ONISEP métiers, Doctorat IP)
seront transformés en Phase B.1 (merger v3 Stage 10 APPEND_ANNEXES). Ils sont
explicitement skip ici avec une note.

Les 6 corpora principaux (MonMaster, LBA, Inserjeunes CFA, RNCP, ONISEP extended,
Parcoursup extended) sont testés via fixtures inline représentatives — leur
intégration dans le corpus v5 passera par le merger v3 qui leur ajoutera
`id` / `domain` / `text`.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src.rag.fact_card import (
    FactCard,
    FactProvenance,
    fiche_to_fact_card,
    has_any_chiffres,
)


# ─────────────── Path helpers ───────────────

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"


def _load_first_record(filename: str) -> dict[str, Any] | None:
    """Charge le 1er record du corpus filename, retourne None si absent."""
    path = PROCESSED / filename
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if isinstance(data, list) and data:
        return data[0]
    if isinstance(data, dict):
        for key in ("records", "data", "items"):
            if key in data and isinstance(data[key], list) and data[key]:
                return data[key][0]
    return None


# ─────────────── Test paramétré — corpora annexes conformes ───────────────


# Liste cf Phase A.4 — uniquement les corpora qui sont 100% conformes au schéma
# minimal (`id`, `domain`, `source`, `text`, tier inférable).
ANNEX_CORPORA_CONFORMES = [
    ("DARES Métiers 2030", "dares_corpus.json", "metier_prospective", "tier_1"),
    ("APEC régions", "apec_regions_corpus.json", "apec_region", "tier_2"),
    ("CROUS corpus", "crous_corpus.json", "crous", "tier_1"),
    ("INSEE salaires PCS", "insee_salaan_corpus.json", "insee_salaire", "tier_1"),
    ("France Compétences blocs", "france_comp_blocs_corpus.json", "competences_certif", "tier_1"),
    ("Inserjeunes lycée pro corpus", "inserjeunes_lycee_pro_corpus.json", "formation_insertion", "tier_1"),
    ("InserSup corpus", "insersup_corpus.json", "insertion_pro", "tier_1"),
    ("Métiers IDEO ONISEP", "metiers_corpus.json", "metier", "tier_1"),
    ("Parcours bacheliers", "parcours_bacheliers_corpus.json", "parcours_bacheliers", "tier_1"),
    ("DROM-COM territoires", "domtom_corpus.json", "territoire_drom", "tier_1"),
    ("Voie pré-bac", "voie_pre_bac_corpus.json", "voie_pre_bac", "tier_1"),
    ("Financement", "financement_corpus.json", "financement_etudes", "tier_1"),
    ("Corrections factuelles", "corrections_factuelles_corpus.json", None, "tier_1"),
    ("ROME 4.0 métiers", "rome_metier_corpus.json", "metier_detail", "tier_1"),
]


@pytest.mark.parametrize(
    "label,filename,expected_domain,expected_tier",
    ANNEX_CORPORA_CONFORMES,
    ids=[c[0] for c in ANNEX_CORPORA_CONFORMES],
)
class TestAnnexCorporaProduceValidFactCard:
    """Vérifie que chaque corpus annexe conforme produit une FactCard valide."""

    def test_fiche_to_fact_card_does_not_throw(
        self, label, filename, expected_domain, expected_tier
    ):
        """fiche_to_fact_card doit gérer le schéma sans crash."""
        record = _load_first_record(filename)
        if record is None:
            pytest.skip(f"corpus {filename} absent — à générer avant Phase B")
        # No throw expected
        card = fiche_to_fact_card(record, fact_id="S1")
        assert isinstance(card, FactCard)

    def test_formation_field_is_populated(
        self, label, filename, expected_domain, expected_tier
    ):
        """La cascade `_pick_formation_name` doit trouver un nom non-vide."""
        record = _load_first_record(filename)
        if record is None:
            pytest.skip(f"corpus {filename} absent")
        card = fiche_to_fact_card(record, fact_id="S1")
        assert card.formation, f"{label}: formation vide alors que record={list(record.keys())[:5]}"
        assert card.formation != "(formation sans nom)", (
            f"{label}: cascade a échoué — aucun champ nom/libelle/etc. trouvé. "
            f"Record keys: {list(record.keys())}"
        )

    def test_provenance_tier_inferred_correctly(
        self, label, filename, expected_domain, expected_tier
    ):
        """ADR-055 : tier inféré depuis source ou bloc provenance explicite."""
        record = _load_first_record(filename)
        if record is None:
            pytest.skip(f"corpus {filename} absent")
        card = fiche_to_fact_card(record, fact_id="S1")
        assert card.provenance is not None, (
            f"{label}: provenance None — source '{record.get('source')}' "
            f"non listée dans SOURCE_TO_TIER ?"
        )
        assert card.provenance.tier == expected_tier, (
            f"{label}: tier inféré '{card.provenance.tier}' ≠ attendu '{expected_tier}'"
        )

    def test_domain_field_present_when_expected(
        self, label, filename, expected_domain, expected_tier
    ):
        """Le champ `domain` natif doit être préservé dans la FactCard."""
        if expected_domain is None:
            pytest.skip(f"{label} n'a pas de domain attendu (libre)")
        record = _load_first_record(filename)
        if record is None:
            pytest.skip(f"corpus {filename} absent")
        card = fiche_to_fact_card(record, fact_id="S1")
        assert card.domain == expected_domain, (
            f"{label}: domain '{card.domain}' ≠ attendu '{expected_domain}'"
        )

    def test_text_libre_populated(
        self, label, filename, expected_domain, expected_tier
    ):
        """Les corpora annexes ont un champ `text` natif — doit alimenter `text_libre`."""
        record = _load_first_record(filename)
        if record is None:
            pytest.skip(f"corpus {filename} absent")
        card = fiche_to_fact_card(record, fact_id="S1")
        # Tous les corpora annexes conformes ont `text` non-vide → text_libre populé
        if record.get("text"):
            assert card.text_libre is not None, (
                f"{label}: record a `text` mais FactCard.text_libre est None"
            )
            assert len(card.text_libre) > 0


# ─────────────── Test fixtures inline — corpora principaux (formations) ───────────────


# Pour les 6 corpora "principaux" (formations), fixtures inline représentatives.
# Le merger v3 (Phase B.1) leur ajoutera `id` / `domain` / `text` au moment de
# l'agrégation. Ici on teste que la cascade `_pick_formation_name` les gère bien.


def fiche_monmaster_inline() -> dict:
    """Sample MonMaster — schéma sans `text`, avec `nom` + `etablissement`."""
    return {
        "source": "monmaster",
        "phase": "master",
        "nom": "DROIT DES AFFAIRES — Juriste d'affaires fiscaliste",
        "etablissement": "Université Paris Cité",
        "ville": "Malakoff",
        "niveau": "bac+5",
        "discipline": "Droit, sciences politiques",
    }


def fiche_lba_inline() -> dict:
    """Sample LBA — schéma source = labonnealternance."""
    return {
        "source": "labonnealternance",
        "nom": "BTS Comptabilité Gestion",
        "etablissement": "CFA d'Île-de-France",
        "ville": "Paris",
        "niveau": "bac+2",
    }


def fiche_inserjeunes_cfa_inline() -> dict:
    """Sample Inserjeunes CFA — schéma avec insertion_pro mais sans text."""
    return {
        "source": "inserjeunes_cfa",
        "nom": "BTS Cybersécurité, Informatique et Réseaux",
        "etablissement": "Lycée Vauban",
        "ville": "Brest",
        "niveau": "bac+2",
        "insertion_pro": {
            "source": "inserjeunes_cfa",
            "taux_emploi_6m": 0.65,
            "taux_emploi_12m": 0.78,
        },
    }


def fiche_rncp_inline() -> dict:
    """Sample RNCP titre — schéma avec text mais sans `id` corpus-style."""
    return {
        "source": "rncp",
        "nom": "Mastère spécialisé Cybersécurité",
        "rncp": "RNCP12345",
        "niveau": "bac+5",
        "text": "Titre RNCP de niveau 7 en cybersécurité. Compétences : audit, "
                "pentest, gouvernance SSI, conformité.",
    }


def fiche_onisep_extended_inline() -> dict:
    """Sample ONISEP extended."""
    return {
        "source": "onisep_formations_extended",
        "nom": "BTS Services informatiques aux organisations",
        "type_diplome": "BTS",
        "niveau": "bac+2",
    }


def fiche_parcoursup_extended_inline() -> dict:
    """Sample Parcoursup extended."""
    return {
        "source": "parcoursup_extended",
        "nom": "Cycle ingénieur",
        "etablissement": "EPITA",
        "ville": "Le Kremlin-Bicêtre",
        "niveau": "bac+5",
        "taux_acces_parcoursup_2025": 67.0,
    }


@pytest.mark.parametrize(
    "label,fiche_fn,expected_tier",
    [
        ("MonMaster", fiche_monmaster_inline, "tier_1"),
        ("LBA", fiche_lba_inline, "tier_1"),
        ("Inserjeunes CFA", fiche_inserjeunes_cfa_inline, "tier_1"),
        ("RNCP", fiche_rncp_inline, "tier_1"),
        ("ONISEP extended", fiche_onisep_extended_inline, "tier_1"),
        ("Parcoursup extended", fiche_parcoursup_extended_inline, "tier_1"),
    ],
    ids=lambda x: x if isinstance(x, str) else "fiche",
)
class TestPrimaryCorporaProduceValidFactCard:
    """Vérifie que les 6 corpora principaux (formations) produisent une FactCard
    valide via leurs schémas natifs (cascade `_pick_formation_name`)."""

    def test_does_not_throw(self, label, fiche_fn, expected_tier):
        card = fiche_to_fact_card(fiche_fn(), fact_id="S1")
        assert isinstance(card, FactCard)

    def test_formation_populated_via_nom(self, label, fiche_fn, expected_tier):
        card = fiche_to_fact_card(fiche_fn(), fact_id="S1")
        assert card.formation
        assert card.formation != "(formation sans nom)"

    def test_provenance_tier_correct(self, label, fiche_fn, expected_tier):
        card = fiche_to_fact_card(fiche_fn(), fact_id="S1")
        assert card.provenance is not None
        assert card.provenance.tier == expected_tier


# ─────────────── Test global — chiffres null préservés (R1 strict v4) ───────────────


class TestStrictV4ContractMultiDomain:
    """Garantit que le contrat strict v4 R1 (chiffres null → "info non disponible")
    reste appliqué pour TOUS les corpora annexes — les fiches métiers/blocs/aides
    n'ont pas de taux_acces ou salaire, et c'est exactement ce qu'on veut."""

    @pytest.mark.parametrize(
        "filename",
        ["dares_corpus.json", "apec_regions_corpus.json", "crous_corpus.json",
         "metiers_corpus.json", "rome_metier_corpus.json"],
    )
    def test_annex_corpora_have_no_chiffres(self, filename):
        """Les corpora métiers / régionaux n'ont pas de chiffres formation
        (taux_acces, salaire_median_embauche). Ils servent au qualitatif."""
        record = _load_first_record(filename)
        if record is None:
            pytest.skip(f"corpus {filename} absent")
        card = fiche_to_fact_card(record, fact_id="S1")
        # Note : InserSup corpus a des taux_emploi mais pas exposés dans
        # FactChiffres actuel (c'est Phase B.1 qui adaptera). Pour les corpora
        # métier/régional, has_any_chiffres doit être False.
        assert not has_any_chiffres(card), (
            f"{filename}: corpus annexe ne devrait pas avoir de chiffres "
            f"formation directs (Parcoursup-style). Trouvé : "
            f"{card.chiffres}"
        )


# ─────────────── Tests gracieux — corpora absents ───────────────


class TestGracefulHandlingOfAbsentCorpora:
    """Si un corpus est absent du filesystem (Phase A pas terminée), le test
    skip proprement plutôt que de fail."""

    def test_absent_corpus_skipped_not_failed(self):
        # On charge un fichier inventé pour confirmer le skip
        result = _load_first_record("corpus_inexistant_xyz.json")
        assert result is None  # Skip plutôt que crash


# ─────────────── Tests sécurité — sources hors liste blanche refusées ───────────────


class TestUnknownSourceProvenanceIsNone:
    """Si un corpus annexe utilisait une source non listée (oubli ADR-055
    ou tentative d'introduction d'une source non-officielle), provenance
    doit être None — la FactCard ne ment pas sur le tier."""

    def test_unknown_source_returns_none_provenance(self):
        fiche = {
            "id": "fake:001",
            "domain": "metier",
            "source": "studyrama",  # explicitement exclu ADR-055
            "text": "Sample text",
            "nom": "Test formation Studyrama",
        }
        card = fiche_to_fact_card(fiche, fact_id="S1")
        # provenance None : source hors liste blanche → la FactCard refuse de tier-er
        assert card.provenance is None
