"""Tests pour result_validator.py (G1-G5 + pipeline is_rewrite_acceptable).

Cf ADR-060 — garde-fous obligatoires avant remplacement de text.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.rewrite.result_validator import (
    is_rewrite_acceptable,
    validate_anti_hallu,
    validate_entities_preserved,
    validate_format,
    validate_length,
    validate_numbers_preserved,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fiche(domain: str) -> dict:
    return json.loads((FIXTURES_DIR / f"{domain}.json").read_text(encoding="utf-8"))


# -----------------------------------------------------------------------------
# G1 — length
# -----------------------------------------------------------------------------


class TestG1Length:
    def test_too_short_rejected(self):
        text = "Trop court."
        assert validate_length(text) is False

    def test_below_30_words_rejected(self):
        text = " ".join(["mot"] * 29)
        assert validate_length(text) is False

    def test_exactly_30_words_accepted(self):
        # Seuil bas assoupli à 30 (vs 60 initial) — fiches Inserjeunes
        # sans data ne fournissent pas assez de matière pour 60 mots.
        text = " ".join(["mot"] * 30)
        assert validate_length(text) is True

    def test_within_range_accepted(self):
        text = " ".join(["mot"] * 150)
        assert validate_length(text) is True

    def test_exactly_300_words_accepted(self):
        text = " ".join(["mot"] * 300)
        assert validate_length(text) is True

    def test_over_300_words_rejected(self):
        text = " ".join(["mot"] * 301)
        assert validate_length(text) is False


# -----------------------------------------------------------------------------
# G2 — numbers preserved (seuil ≥ 100, tolérance espaces)
# -----------------------------------------------------------------------------


class TestG2NumbersPreserved:
    def test_all_significant_numbers_present(self):
        fiche = {"effectif": 51780, "salaire": 19000, "n_petit": 13}
        rewritten = "Effectif de 51780 personnes pour un salaire de 19000 euros."
        assert validate_numbers_preserved(fiche, rewritten) is True

    def test_with_thousand_separator_space_accepted(self):
        fiche = {"effectif": 51780, "salaire": 19000}
        rewritten = "Effectif de 51 780 personnes pour un salaire de 19 000 euros."
        assert validate_numbers_preserved(fiche, rewritten) is True

    def test_missing_significant_number_rejected(self):
        fiche = {"effectif": 51780, "salaire": 19000}
        rewritten = "Effectif de 51780 personnes."  # 19000 manquant
        assert validate_numbers_preserved(fiche, rewritten) is False

    def test_small_numbers_below_100_ignored(self):
        # 13, 25, 78 (sub-comptes) ignorés — seuil 100
        fiche = {"effectif": 51780, "n_femmes_pct": 13, "n_alt": 25}
        rewritten = "Effectif de 51 780 personnes."
        assert validate_numbers_preserved(fiche, rewritten) is True

    def test_negative_significant_number_preserved(self):
        # DARES négatifs : -23227 destructions → abs >= 100
        fiche = {"creations_destructions": -23227, "postes": 157400}
        rewritten = "Bilan de -23227 emplois et 157400 postes à pourvoir."
        assert validate_numbers_preserved(fiche, rewritten) is True

    def test_negative_significant_number_missing_rejected(self):
        fiche = {"creations_destructions": -23227, "postes": 157400}
        rewritten = "Bilan de 157400 postes à pourvoir."
        assert validate_numbers_preserved(fiche, rewritten) is False

    def test_floats_truncated_to_int(self):
        # DARES uses floats like 431.659 milliers — on ne préserve que la partie entière
        fiche = {"effectif_milliers": 431.659}
        rewritten = "Effectif de 431 milliers de personnes."
        assert validate_numbers_preserved(fiche, rewritten) is True

    def test_nested_dicts_walked(self):
        fiche = {"provenance": {"year": 2023, "n": 51780}, "extra": [{"sub": 19000}]}
        rewritten = "En 2023, effectif 51 780 et 19 000 euros."
        # 2023 < 100? non, 2023 ≥ 100, doit être présent
        assert validate_numbers_preserved(fiche, rewritten) is True


# -----------------------------------------------------------------------------
# G3 — entities preserved (codes officiels + libellés clés)
# -----------------------------------------------------------------------------


class TestG3EntitiesPreserved:
    def test_code_rome_present(self):
        fiche = {"code_rome": "M1402", "libelle_metier": "Conseil en organisation"}
        rewritten = "Le métier (code ROME M1402) consiste à Conseil en organisation."
        assert validate_entities_preserved(fiche, rewritten) is True

    def test_code_rome_missing_rejected(self):
        fiche = {"code_rome": "M1402", "libelle_metier": "Conseil en organisation"}
        rewritten = "Le métier consiste à conseiller des entreprises."
        assert validate_entities_preserved(fiche, rewritten) is False

    def test_libelle_case_insensitive(self):
        fiche = {"libelle_metier": "Conducteur d'engins agricoles"}
        rewritten = "Le métier de conducteur d'engins agricoles est..."
        assert validate_entities_preserved(fiche, rewritten) is True

    def test_cs_code_present(self):
        fiche = {"cs_code": "21", "cs_libelle": "Artisans"}
        rewritten = "La PCS 21 (Artisans) regroupe les indépendants."
        assert validate_entities_preserved(fiche, rewritten) is True

    def test_code_fap_required(self):
        fiche = {"code_fap": "A0Z", "fap_libelle": "Agriculteurs"}
        rewritten = "La famille FAP A0Z (Agriculteurs) regroupe..."
        assert validate_entities_preserved(fiche, rewritten) is True

    def test_no_entity_fields_passes(self):
        # Si la fiche n'a aucun champ identifiant → validate passe
        fiche = {"text": "stuff", "domain": "crous"}
        rewritten = "Le CROUS gère le logement étudiant."
        assert validate_entities_preserved(fiche, rewritten) is True

    def test_short_libelle_ignored(self):
        # libellé < 2 chars ignoré
        fiche = {"libelle": "X"}
        rewritten = "Quelque chose."
        assert validate_entities_preserved(fiche, rewritten) is True


# -----------------------------------------------------------------------------
# G4 — anti-hallu redflags
# -----------------------------------------------------------------------------


class TestG4AntiHallu:
    def test_clean_text_passes(self):
        text = "Le métier consiste à analyser des données et rédiger des rapports."
        assert validate_anti_hallu(text) is True

    def test_two_redflags_passes(self):
        text = (
            "Le métier est généralement exercé en équipe. Il convient d'avoir "
            "un bac+5 pour y accéder."
        )
        assert validate_anti_hallu(text) is True

    def test_three_redflags_rejected(self):
        text = (
            "Le métier est généralement exercé en équipe. Souvent il faut un "
            "bac+5. Il convient d'avoir une expérience préalable."
        )
        assert validate_anti_hallu(text) is False

    def test_case_insensitive(self):
        text = (
            "GÉNÉRALEMENT le métier est en équipe. SOUVENT bac+5. IL CONVIENT "
            "d'avoir une expérience."
        )
        assert validate_anti_hallu(text) is False


# -----------------------------------------------------------------------------
# G5 — format (no markdown / no pipe / no bullets)
# -----------------------------------------------------------------------------


class TestG5Format:
    def test_clean_paragraph_passes(self):
        text = "Le CROUS de Lyon gère 12 000 logements et 36 restaurants universitaires."
        assert validate_format(text) is True

    def test_markdown_bold_rejected(self):
        text = "Le **CROUS** de Lyon gère 12 000 logements."
        assert validate_format(text) is False

    def test_markdown_heading_rejected(self):
        text = "## CROUS Lyon\n\nLe CROUS gère 12 000 logements."
        assert validate_format(text) is False

    def test_pipe_separator_rejected(self):
        # canari format ancien (séparateurs | du v5)
        text = "CROUS Lyon | 12 000 logements | 36 restos"
        assert validate_format(text) is False

    def test_double_newline_rejected(self):
        text = "Le CROUS gère 12 000 logements.\n\n36 restaurants disponibles."
        assert validate_format(text) is False

    def test_many_bullets_rejected(self):
        text = "Le CROUS Lyon propose : - 12 000 logements - 36 restos U - tarifs réduits - aides DSE."
        assert validate_format(text) is False

    def test_one_dash_in_phrase_passes(self):
        # Tirets normaux dans la phrase autorisés
        text = "Le CROUS - opérateur public - gère 12 000 logements à Lyon."
        assert validate_format(text) is True

    def test_quasi_copy_double_space_rejected(self):
        # Symptôme : Haiku remplace `|` par double-espace sans rephraser
        text = (
            "Salaires PCS 38 : Ingénieurs (France 2023)  Effectif "
            "pondéré : 1 765 764  Salaire net médian annuel : 45 000 €  "
            "Salaire net médian mensuel : 3 750 €  Répartition H/F : 25%"
        )
        assert validate_format(text) is False

    def test_starts_with_v5_format_header_rejected(self):
        text = (
            "Métier ONISEP : reporter-photographe Codes ROME E1106 dans le "
            "domaine information-communication, audiovisuel."
        )
        assert validate_format(text) is False

    def test_starts_with_insertion_header_rejected(self):
        text = (
            "Insertion BAC PRO menuiserie aluminium-verre en ILE-DE-FRANCE "
            "32 établissements 30% poursuite d'études Inserjeunes DEPP."
        )
        assert validate_format(text) is False

    def test_natural_paragraph_with_few_double_spaces_passes(self):
        # 1-2 double-espaces accidentels dans un paragraphe naturel = OK
        text = (
            "Le CROUS Lyon  gère 12 000 logements et propose la "
            "restauration universitaire à tarif social pour les étudiants "
            "boursiers de la région Auvergne-Rhône-Alpes."
        )
        assert validate_format(text) is True


# -----------------------------------------------------------------------------
# Pipeline is_rewrite_acceptable
# -----------------------------------------------------------------------------


class TestIsRewriteAcceptable:
    def test_all_pass(self):
        fiche = {
            "id": "crous_region:lyon",
            "domain": "crous",
            "n_logements": 12000,
            "regions_principales": ["Auvergne-Rhône-Alpes"],
        }
        rewritten = (
            "Le CROUS de Lyon, en région Auvergne-Rhône-Alpes, gère 12 000 "
            "logements en résidence universitaire pour les étudiants. Il "
            "propose également une restauration universitaire à tarif "
            "social ainsi que des aides spécifiques pour les boursiers. "
            "Cet opérateur public couvre l'ensemble des établissements "
            "supérieurs de la région et permet aux étudiants de Lyon, "
            "Villeurbanne et leurs alentours de se loger dans des "
            "résidences sécurisées avec des loyers modérés. L'accès au "
            "logement CROUS est conditionné par les critères sociaux "
            "(revenus de la famille, distance au lieu d'études)."
        )
        accepted, issues = is_rewrite_acceptable(fiche, rewritten)
        assert accepted is True
        assert issues == []

    def test_multiple_issues_collected(self):
        fiche = {"code_rome": "M1402", "libelle_metier": "Conseil"}
        rewritten = "**Trop court** | et plein de problèmes."
        accepted, issues = is_rewrite_acceptable(fiche, rewritten)
        assert accepted is False
        # Au moins length + format + entities manquantes
        assert len(issues) >= 3
        assert any("length" in i for i in issues)
        assert any("format" in i for i in issues)


# -----------------------------------------------------------------------------
# Smoke test sur fixtures réelles
# -----------------------------------------------------------------------------


class TestSmokeFixtures:
    def test_crous_acceptable_rewrite(self):
        """Un rewrite plausible pour CROUS doit passer tous les G."""
        fiche = load_fiche("crous")
        rewritten = (
            "Le réseau CROUS regroupe 820 résidences universitaires et "
            "999 restaurants ou cafétérias universitaires en France. Cet "
            "opérateur public gère le logement étudiant et la restauration "
            "à tarif social, accessibles en priorité aux boursiers. Les "
            "lieux de restauration se déclinent en plusieurs formats : "
            "cafétérias, restaurants traditionnels, restaurants agréés, "
            "libre-service et brasseries. Le réseau couvre tout le "
            "territoire métropolitain, avec une présence forte en "
            "Île-de-France et en Auvergne-Rhône-Alpes. Les étudiants y "
            "trouvent des loyers modérés, des repas à prix social, des "
            "aides spécifiques (DSE, ALS) et des services associés "
            "comme l'accompagnement administratif ou culturel."
        )
        accepted, issues = is_rewrite_acceptable(fiche, rewritten)
        assert accepted is True, f"Issues: {issues}"

    def test_insee_salaire_acceptable_rewrite(self):
        fiche = load_fiche("insee_salaire")
        rewritten = (
            "La catégorie socioprofessionnelle PCS 21 regroupe les "
            "Artisans qui sont salariés de leur propre entreprise en "
            "France. En 2023, l'INSEE recense un effectif pondéré de "
            "51 780 artisans dans cette catégorie, avec un salaire net "
            "médian annuel de 19 000 euros, soit 1 583 euros par mois. "
            "Les femmes représentent 10 pour cent de cet effectif. Les "
            "principales régions concentrant ces artisans sont "
            "l'Île-de-France, l'Auvergne-Rhône-Alpes et l'Occitanie. "
            "Cette catégorie regroupe les chefs d'entreprise artisanale "
            "qui se versent un salaire en tant que dirigeant, par "
            "opposition aux artisans non-salariés qui relèvent d'une "
            "autre catégorie statistique."
        )
        accepted, issues = is_rewrite_acceptable(fiche, rewritten)
        assert accepted is True, f"Issues: {issues}"
