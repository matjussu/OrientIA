"""Tests `rerank` ADR-049 domain-aware + `classify_domain_hint`."""
from __future__ import annotations

import pytest

from src.rag.intent import (
    DOMAIN_HINT_APEC,
    DOMAIN_HINT_COMPETENCES_CERTIF,
    DOMAIN_HINT_METIER,
    DOMAIN_HINT_PARCOURS,
    classify_domain_hint,
)
from src.rag.reranker import RerankConfig, rerank


# --- classify_domain_hint ---


class TestClassifyDomainHintMetier:
    def test_que_fait_un(self):
        assert classify_domain_hint("Que fait un actuaire ?") == DOMAIN_HINT_METIER

    def test_devenir_developpeur(self):
        assert classify_domain_hint(
            "Comment devenir développeur en cybersécurité ?"
        ) == DOMAIN_HINT_METIER

    def test_metier_artistique_manuel(self):
        assert classify_domain_hint(
            "Je rêve d'un métier artistique qui me permette de travailler de mes mains"
        ) == DOMAIN_HINT_METIER

    def test_difference_entre_metier(self):
        assert classify_domain_hint(
            "Quelle est la différence concrète entre le métier d'ingénieur mathématicien et celui d'actuaire ?"
        ) == DOMAIN_HINT_METIER

    def test_quel_metier(self):
        assert classify_domain_hint("Quel métier après une licence info ?") == DOMAIN_HINT_METIER


class TestClassifyDomainHintParcours:
    def test_taux_reussite_licence(self):
        assert classify_domain_hint(
            "Quel est le taux de réussite en licence de droit pour un BAC L mention Bien ?"
        ) == DOMAIN_HINT_PARCOURS

    def test_passage_l1_l2(self):
        assert classify_domain_hint(
            "Quel taux de passage L1→L2 en éco vs droit ?"
        ) == DOMAIN_HINT_PARCOURS

    def test_redoublement_l1(self):
        assert classify_domain_hint(
            "Risque de redoublement en L1 STAPS pour un bac S ?"
        ) == DOMAIN_HINT_PARCOURS

    def test_reorientation_dut(self):
        assert classify_domain_hint(
            "Réorientation en DUT après L1 droit ?"
        ) == DOMAIN_HINT_PARCOURS


class TestClassifyDomainHintApec:
    def test_marche_du_travail_cadres(self):
        assert classify_domain_hint(
            "Quel est le marché du travail des cadres en Bretagne ?"
        ) == DOMAIN_HINT_APEC

    def test_recrutements_cadres(self):
        assert classify_domain_hint(
            "Volume de recrutements cadres en Île-de-France 2026"
        ) == DOMAIN_HINT_APEC

    def test_region_dynamique_cadres(self):
        assert classify_domain_hint(
            "Dans quelle région les recrutements cadres 2026 sont les plus dynamiques ?"
        ) == DOMAIN_HINT_APEC

    def test_salaire_median_cadres(self):
        assert classify_domain_hint(
            "Salaire médian cadre en Auvergne-Rhône-Alpes ?"
        ) == DOMAIN_HINT_APEC


class TestClassifyDomainHintCompetencesCertif:
    def test_blocs_de_competences_explicit(self):
        assert classify_domain_hint(
            "Quels blocs de compétences sont validés par le BTS comptabilité ?"
        ) == DOMAIN_HINT_COMPETENCES_CERTIF

    def test_que_vais_je_apprendre(self):
        assert classify_domain_hint(
            "Que vais-je apprendre en BUT informatique ?"
        ) == DOMAIN_HINT_COMPETENCES_CERTIF

    def test_quelles_competences(self):
        assert classify_domain_hint(
            "Quelles compétences acquises grâce à un master de cybersécurité ?"
        ) == DOMAIN_HINT_COMPETENCES_CERTIF

    def test_rncp_explicit_number(self):
        assert classify_domain_hint(
            "Que couvre la fiche RNCP35185 ?"
        ) == DOMAIN_HINT_COMPETENCES_CERTIF

    def test_validation_par_blocs_vae(self):
        assert classify_domain_hint(
            "Comment se fait la validation partielle d'un titre RNCP en VAE ?"
        ) == DOMAIN_HINT_COMPETENCES_CERTIF

    def test_savoir_faire_certifie(self):
        assert classify_domain_hint(
            "Quels savoir-faire sont certifiés par un titre professionnel niveau 5 ?"
        ) == DOMAIN_HINT_COMPETENCES_CERTIF


class TestClassifyDomainHintNone:
    def test_formation_centric_query(self):
        # Cette query ne devrait pas trigger le reranker domain
        assert classify_domain_hint(
            "Je suis en CAP cuisine à Marseille, je veux continuer en Bac pro alternance"
        ) is None

    def test_empty(self):
        assert classify_domain_hint("") is None
        assert classify_domain_hint(None) is None

    def test_general_query(self):
        assert classify_domain_hint(
            "Quels sont les principaux débouchés après une licence de lettres ?"
        ) is None


class TestClassifyDomainHintPriority:
    def test_apec_wins_over_metier_when_cadres_keyword(self):
        # "Cadres en 2026" devrait matcher APEC (plus spécifique) même si
        # "que fait" pourrait matcher metier
        result = classify_domain_hint(
            "Cadres en 2026 et que fait un manager au quotidien ?"
        )
        assert result == DOMAIN_HINT_APEC

    def test_parcours_specific_pattern(self):
        # Pattern parcours nettement distinct
        assert classify_domain_hint(
            "Stats sur le passage en L2 après une L1 de psycho ?"
        ) == DOMAIN_HINT_PARCOURS


# --- rerank() avec domain_hint ---


def _mk_result(fiche: dict, base_score: float = 0.5) -> dict:
    return {"fiche": fiche, "base_score": base_score}


class TestRerankWithDomainHint:
    def test_no_hint_no_domain_boost(self):
        """Comportement pre-ADR-049 : sans hint, aucune fiche domain n'est boostée."""
        formation = {"nom": "L Lettres", "phase": "initial"}
        metier = {"nom": "actuaire", "domain": "metier", "text": "x"}
        results = [_mk_result(formation, 0.5), _mk_result(metier, 0.5)]
        out = rerank(results, RerankConfig(), domain_hint=None)
        scores = {r["fiche"].get("nom"): r["score"] for r in out}
        # Stage C etab_named_boost ne s'applique pas (pas d'etab) → scores égaux
        # Variations possibles via Stage A/B mais pas de boost domain.
        # Test : metier ne bénéficie d'aucun boost spécifique
        assert scores["actuaire"] == 0.5  # base_score inchangé (aucun stage applicable)

    def test_domain_boost_metier_only_to_metier_fiches(self):
        formation = {"nom": "L Math", "phase": "initial"}
        metier = {"id": "metier:1", "nom": "actuaire", "domain": "metier", "text": "x"}
        results = [_mk_result(formation, 0.5), _mk_result(metier, 0.5)]
        out = rerank(results, RerankConfig(), domain_hint="metier")
        scores = {(r["fiche"].get("nom"), r["fiche"].get("domain")): r["score"] for r in out}
        assert scores[("L Math", None)] == 0.5  # pas de boost (domain != metier)
        assert scores[("actuaire", "metier")] == 0.5 * 1.3  # boost metier 1.3

    def test_domain_boost_apec_region(self):
        formation = {"nom": "L Eco", "phase": "initial"}
        apec = {"id": "apec:bretagne", "nom": "Bretagne", "domain": "apec_region", "text": "x"}
        results = [_mk_result(formation, 0.5), _mk_result(apec, 0.5)]
        out = rerank(results, RerankConfig(), domain_hint="apec_region")
        scores = {r["fiche"].get("domain"): r["score"] for r in out}
        assert scores["apec_region"] == 0.5 * 1.5
        assert scores[None] == 0.5

    def test_domain_boost_parcours_bacheliers(self):
        formation = {"nom": "L Droit", "phase": "initial"}
        parcours = {"id": "p:1", "domain": "parcours_bacheliers", "text": "x"}
        results = [_mk_result(formation, 0.5), _mk_result(parcours, 0.5)]
        out = rerank(results, RerankConfig(), domain_hint="parcours_bacheliers")
        scores = {r["fiche"].get("domain"): r["score"] for r in out}
        assert scores["parcours_bacheliers"] == 0.5 * 1.3
        assert scores[None] == 0.5

    def test_unknown_hint_no_op(self):
        formation = {"nom": "X"}
        metier = {"nom": "Y", "domain": "metier"}
        results = [_mk_result(formation, 0.5), _mk_result(metier, 0.5)]
        out = rerank(results, RerankConfig(), domain_hint="unknown_domain")
        # Unknown hint → no boost applied to any fiche
        scores = [r["score"] for r in out]
        assert all(s == 0.5 for s in scores)

    def test_domain_boost_compounds_with_other_stages(self):
        """Verify domain boost stacks correctly with label/niveau boosts."""
        # metier with niveau=bac+5 + statut=Public
        metier = {
            "id": "metier:1",
            "domain": "metier",
            "nom": "X",
            "niveau": "bac+5",
            "statut": "Public",
        }
        results = [_mk_result(metier, 1.0)]
        cfg = RerankConfig()
        out = rerank(results, cfg, domain_hint="metier")
        # Expected: 1.0 × public_boost (1.1) × level_boost_bac5 (1.15) × domain_boost_metier (1.3)
        # Note: pas de etab_named_boost (etab vide), pas de label, pas de parcoursup_rich
        expected = 1.0 * 1.1 * 1.15 * 1.3
        assert abs(out[0]["score"] - expected) < 1e-6

    def test_existing_label_boosts_unaffected_by_hint(self):
        """Régression : boosts SecNumEdu / CTI restent intacts post-ADR-049."""
        formation = {
            "nom": "EFREI Cyber",
            "labels": ["SecNumEdu"],
            "etablissement": "EFREI",
        }
        results = [_mk_result(formation, 0.5)]
        out_no_hint = rerank(results, RerankConfig(), domain_hint=None)
        out_with_hint = rerank(results, RerankConfig(), domain_hint="metier")
        # Sans hint OU avec hint metier (formation n'a pas domain=metier),
        # le score doit être identique (= 0.5 × 1.5 [SecNumEdu] × 1.1 [etab named])
        assert out_no_hint[0]["score"] == out_with_hint[0]["score"]
        assert abs(out_no_hint[0]["score"] - 0.5 * 1.5 * 1.1) < 1e-6

    def test_rerank_sorts_by_final_score(self):
        # Scenario : 1 formation avec base_score haut, 1 metier avec base_score bas mais hint actif
        formation = {"nom": "F", "phase": "initial"}
        metier = {"id": "metier:1", "domain": "metier", "nom": "M"}
        results = [_mk_result(formation, 0.6), _mk_result(metier, 0.5)]
        out = rerank(results, RerankConfig(), domain_hint="metier")
        # formation = 0.6 (no boost), metier = 0.5 × 1.3 = 0.65
        # → metier doit être premier
        assert out[0]["fiche"]["nom"] == "M"
        assert out[1]["fiche"]["nom"] == "F"


# --- RerankConfig new fields ---


class TestRerankConfigNewFields:
    def test_defaults(self):
        c = RerankConfig()
        assert c.domain_boost_apec_region == 1.5
        assert c.domain_boost_metier == 1.3
        assert c.domain_boost_parcours_bacheliers == 1.3
        assert c.domain_boost_competences_certif == 1.5

    def test_as_dict_includes_new_fields(self):
        d = RerankConfig().as_dict()
        assert "domain_boost_apec_region" in d
        assert "domain_boost_metier" in d
        assert "domain_boost_parcours_bacheliers" in d
        assert "domain_boost_competences_certif" in d


class TestRerankCompetencesCertifBoost:
    def test_boost_applied_to_competences_certif_domain_only(self):
        formation = {"nom": "Master CS", "domain": "formation"}
        blocs = {"text": "Compétences certifiées (RNCP100)…", "domain": "competences_certif"}
        results = [
            {"fiche": formation, "base_score": 0.5},
            {"fiche": blocs, "base_score": 0.5},
        ]
        out = rerank(
            results, RerankConfig(), domain_hint=DOMAIN_HINT_COMPETENCES_CERTIF
        )
        # blocs doit être en tête (boost ×1.5 vs formation ×1.0 implicite)
        assert out[0]["fiche"]["domain"] == "competences_certif"
        assert out[0]["score"] > out[1]["score"]

    def test_no_boost_when_hint_absent(self):
        # Sans hint, blocs ne doit pas être boostée — formations chiffrées
        # gardent leur priorité naturelle.
        blocs = {"text": "Compétences certifiées", "domain": "competences_certif"}
        results = [{"fiche": blocs, "base_score": 0.5}]
        out = rerank(results, RerankConfig(), domain_hint=None)
        # Score inchangé (juste les boosts génériques s'appliquent, ici aucun)
        assert out[0]["score"] == pytest.approx(0.5)
