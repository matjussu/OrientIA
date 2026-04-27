"""Tests pour le routing intent classifier vers les granularités Sprint 6.

Sprint 7 Action 5 — vérifie que les nouvelles cells curated (axes 2 + 3a)
et re-aggregations (axe 3b) sont bien atteintes par les queries
correspondantes via les 4 nouveaux DOMAIN_HINT.

Préserve la non-régression : les anciens patterns continuent de matcher.
"""
from __future__ import annotations

import pytest

from src.rag.intent import (
    DOMAIN_HINT_FORMATION_INSERTION,
    DOMAIN_HINT_FINANCEMENT_ETUDES,
    DOMAIN_HINT_TERRITOIRE_DROM,
    DOMAIN_HINT_VOIE_PRE_BAC,
    DOMAIN_HINT_APEC,
    DOMAIN_HINT_METIER_PROSPECTIVE,
    DOMAIN_HINT_INSEE_SALAIRE,
    DOMAIN_HINT_INSERTION_PRO,
    DOMAIN_HINT_COMPETENCES_CERTIF,
    DOMAIN_HINT_PARCOURS,
    DOMAIN_HINT_CROUS,
    DOMAIN_HINT_METIER,
    classify_domain_hint,
)
from src.rag.reranker import RerankConfig, _DOMAIN_BOOST_FIELDS, rerank


class TestNewDomainHintsExist:
    """Sprint 7 Action 5 : 4 nouveaux DOMAIN_HINT exposés."""

    def test_formation_insertion_constant(self):
        assert DOMAIN_HINT_FORMATION_INSERTION == "formation_insertion"

    def test_financement_etudes_constant(self):
        assert DOMAIN_HINT_FINANCEMENT_ETUDES == "financement_etudes"

    def test_territoire_drom_constant(self):
        assert DOMAIN_HINT_TERRITOIRE_DROM == "territoire_drom"

    def test_voie_pre_bac_constant(self):
        assert DOMAIN_HINT_VOIE_PRE_BAC == "voie_pre_bac"


class TestRoutingTerritoireDrom:
    """Axe 2 — DROM-COM territorial."""

    @pytest.mark.parametrize("question", [
        "Je suis en Mayotte et je veux faire un master en énergies renouvelables",
        "Quelles études en Guadeloupe pour devenir infirmier ?",
        "Le marché de l'emploi en Martinique pour les jeunes",
        "Comment financer un BTS quand on vit à La Réunion ?",
        "Quels secteurs porteurs en Guyane ?",
        "DROM-COM : où faire un BAC PRO ?",
        "LADOM passeport mobilité comment ça marche ?",
        "Outre-mer : quelles bourses spécifiques ?",
    ])
    def test_drom_questions_route_to_territoire(self, question):
        assert classify_domain_hint(question) == DOMAIN_HINT_TERRITOIRE_DROM


class TestRoutingFinancementEtudes:
    """Axe 4 — financement études et formation."""

    @pytest.mark.parametrize("question", [
        "Comment financer mes études d'ingénieur ?",
        "Bourse CROUS sur critères sociaux quels échelons ?",
        "C'est quoi le CPF et comment l'utiliser pour une formation ?",
        "PTP Transitions Pro pour reconversion : comment ça marche ?",
        "AGEFIPH aide à la formation pour RQTH ?",
        "AFDAS opérateur de compétences spectacle culture",
        "VAE validation des acquis comment financer ?",
        "Combien coûte 5 années en école de commerce ?",
        "Aide au logement étudiant CAF APL",
        "Visale garantie locative pour étudiants",
        "Contrat d'engagement jeune CEJ Mission Locale",
    ])
    def test_financement_questions_route_correctly(self, question):
        assert classify_domain_hint(question) == DOMAIN_HINT_FINANCEMENT_ETUDES


class TestRoutingVoiePreBac:
    """Axe 3a — voie pré-bac (BAC PRO + CAP)."""

    @pytest.mark.parametrize("question", [
        "Quelles spécialités de bac pro en cyber ?",
        "Liste des CAP en hôtellerie restauration",
        "Catalogue bac pro en agriculture",
        "Mention complémentaire après un CAP cuisine",
        "Bac pro métiers de l'électricité contenu programme",
        "Choisir orientation après la troisième : bac pro ou seconde générale",
        "Toutes les spécialités bac pro industrie",
    ])
    def test_voie_pre_bac_questions_route_correctly(self, question):
        assert classify_domain_hint(question) == DOMAIN_HINT_VOIE_PRE_BAC


class TestRoutingFormationInsertion:
    """Axe 3b — Inserjeunes lycée pro (insertion bac pro / CAP / BTS)."""

    @pytest.mark.parametrize("question", [
        "Insertion après un bac pro en gestion administration",
        "Taux d'emploi après un BTS en comptabilité",
        "Que deviennent les sortants de CAP en France ?",
        "Insertion bac pro vente quelles chances ?",
        "Inserjeunes statistiques par spécialité",
        "Continue ses études apres un bac pro c'est possible ?",
        "Poursuite d'études après bac pro vers BTS",
    ])
    def test_formation_insertion_questions_route_correctly(self, question):
        assert classify_domain_hint(question) == DOMAIN_HINT_FORMATION_INSERTION


class TestNonRegressionPriorities:
    """Non-régression : les patterns existants ne sont pas cassés.

    Sprint 7 Action 5 ajoute 4 hints SANS perturber les 8 existants.
    """

    def test_apec_marche_travail_cadres_still_routes_apec(self):
        """APEC reste prio 1 (le plus spécifique)."""
        q = "Marché du travail des cadres dans la région Auvergne-Rhône-Alpes en 2026"
        assert classify_domain_hint(q) == DOMAIN_HINT_APEC

    def test_metier_prospective_still_routes_metier_prospective(self):
        q = "Quels métiers vont recruter en 2030 ? Quelles perspectives FAP J5Z ?"
        assert classify_domain_hint(q) == DOMAIN_HINT_METIER_PROSPECTIVE

    def test_insee_salaire_still_routes_insee(self):
        q = "Quel salaire médian pour un cadre en informatique ?"
        assert classify_domain_hint(q) == DOMAIN_HINT_INSEE_SALAIRE

    def test_competences_certif_still_routes_correctly(self):
        q = "Quels blocs de compétences certifiés dans le BTS comptabilité ?"
        assert classify_domain_hint(q) == DOMAIN_HINT_COMPETENCES_CERTIF

    def test_crous_still_routes_correctly(self):
        q = "Logement CROUS comment faire ma demande ?"
        assert classify_domain_hint(q) == DOMAIN_HINT_CROUS

    def test_metier_still_routes_correctly(self):
        q = "Que fait un actuaire au quotidien ?"
        assert classify_domain_hint(q) == DOMAIN_HINT_METIER

    def test_question_without_specific_pattern_returns_none(self):
        """Non-régression : query générique reste None (formation-centric)."""
        q = "Comment se passe l'année en BUT info ?"
        # Ce pattern ne match aucun des hints → None
        assert classify_domain_hint(q) is None


class TestRerankerConfigSprint7Boosts:
    """Sprint 7 Action 5 : 4 nouveaux boosts dans RerankConfig."""

    def test_default_config_has_new_boosts(self):
        cfg = RerankConfig()
        assert cfg.domain_boost_formation_insertion == 1.4
        assert cfg.domain_boost_financement_etudes == 1.5
        assert cfg.domain_boost_territoire_drom == 1.5
        assert cfg.domain_boost_voie_pre_bac == 1.4

    def test_existing_boosts_unchanged_non_regression(self):
        """Non-régression : les boosts existants gardent leurs valeurs."""
        cfg = RerankConfig()
        assert cfg.domain_boost_apec_region == 1.5
        assert cfg.domain_boost_metier == 1.3
        assert cfg.domain_boost_metier_prospective == 1.0  # tuné à 1.0 le 2026-04-26
        assert cfg.domain_boost_competences_certif == 1.5
        assert cfg.secnumedu_boost == 1.5

    def test_as_dict_includes_new_boosts(self):
        cfg = RerankConfig()
        d = cfg.as_dict()
        assert "domain_boost_formation_insertion" in d
        assert "domain_boost_financement_etudes" in d
        assert "domain_boost_territoire_drom" in d
        assert "domain_boost_voie_pre_bac" in d

    def test_domain_boost_fields_mapping_includes_new_hints(self):
        for hint in (
            "formation_insertion",
            "financement_etudes",
            "territoire_drom",
            "voie_pre_bac",
        ):
            assert hint in _DOMAIN_BOOST_FIELDS, f"hint {hint} non mappé dans reranker"


class TestRerankerAppliesBoostsSelectively:
    """Sprint 7 Action 5 : les nouveaux boosts s'appliquent uniquement sur
    les fiches du bon domain. Non-régression : pas de pénalité hors-domain."""

    def test_boost_financement_applies_only_to_financement(self):
        cfg = RerankConfig()
        results = [
            {"fiche": {"domain": "financement_etudes", "nom": "CPF"}, "base_score": 1.0},
            {"fiche": {"domain": "formation", "nom": "Master Info"}, "base_score": 1.0},
        ]
        out = rerank(results, cfg, domain_hint="financement_etudes")
        # La fiche financement boostée → score = 1.5 (mais autres boosts peuvent
        # s'appliquer si labels présents). Test : la fiche financement > formation.
        scores = {r["fiche"]["nom"]: r["score"] for r in out}
        assert scores["CPF"] > scores["Master Info"]

    def test_no_boost_applied_when_hint_none(self):
        """Non-régression : sans hint, comportement formation-centric inchangé."""
        cfg = RerankConfig()
        results = [
            {"fiche": {"domain": "financement_etudes", "nom": "CPF"}, "base_score": 1.0},
            {"fiche": {"domain": "formation", "nom": "Master Info"}, "base_score": 1.0},
        ]
        out_none = rerank(results, cfg, domain_hint=None)
        # Sans hint, aucun domain_boost appliqué (mais autres boosts oui)
        # Les 2 fiches formation/financement ont les mêmes labels donc même score
        scores_none = {r["fiche"]["nom"]: r["score"] for r in out_none}
        # Pas d'écart de score lié au domain
        assert scores_none["CPF"] == scores_none["Master Info"]

    def test_boost_voie_pre_bac_applies_correctly(self):
        cfg = RerankConfig()
        results = [
            {"fiche": {"domain": "voie_pre_bac", "nom": "Catalogue BAC PRO"}, "base_score": 1.0},
            {"fiche": {"domain": "formation", "nom": "Master Info"}, "base_score": 1.0},
        ]
        out = rerank(results, cfg, domain_hint="voie_pre_bac")
        scores = {r["fiche"]["nom"]: r["score"] for r in out}
        assert scores["Catalogue BAC PRO"] > scores["Master Info"]

    def test_boost_territoire_drom_applies_correctly(self):
        cfg = RerankConfig()
        results = [
            {"fiche": {"domain": "territoire_drom", "nom": "Guadeloupe profil"}, "base_score": 1.0},
            {"fiche": {"domain": "formation", "nom": "BTS Métropole"}, "base_score": 1.0},
        ]
        out = rerank(results, cfg, domain_hint="territoire_drom")
        scores = {r["fiche"]["nom"]: r["score"] for r in out}
        assert scores["Guadeloupe profil"] > scores["BTS Métropole"]

    def test_boost_formation_insertion_applies_correctly(self):
        cfg = RerankConfig()
        results = [
            {"fiche": {"domain": "formation_insertion", "nom": "Inserjeunes BAC PRO"}, "base_score": 1.0},
            {"fiche": {"domain": "formation", "nom": "Master Info"}, "base_score": 1.0},
        ]
        out = rerank(results, cfg, domain_hint="formation_insertion")
        scores = {r["fiche"]["nom"]: r["score"] for r in out}
        assert scores["Inserjeunes BAC PRO"] > scores["Master Info"]
