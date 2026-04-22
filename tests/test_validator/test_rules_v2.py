"""Tests des règles V2 (4 erreurs factuelles disqualifiantes ground truth humain 2026-04-22).

Chaque règle V2.1-V2.4 a :
- Tests de détection (catch du pattern fautif)
- Tests de contexte exception (laisser passer les mentions historiques/pédagogiques)
- Tests sur les 3 Q hard du pack Gate J+6 (Q1 HEC / Q6 kiné / Q8 PASS+bacB)
  qui DOIVENT tous être BLOCK avec V2 actif.

Sources dans docstrings des règles (ADR-036, arrêtés officiels).
"""
from __future__ import annotations

import pytest

from src.validator.rules import apply_rules, Severity


# =========================================================================
# V2.1 — HEC via AST propre, PAS Tremplin/Passerelle
# =========================================================================


class TestV2_1_HEC_AST:

    def test_HEC_plus_Tremplin_same_response_blocks(self):
        txt = (
            "HEC recrute 10% via admissions parallèles. "
            "Vise d'abord un BBA puis tente le concours Tremplin à bac+3."
        )
        violations = apply_rules(txt)
        assert any(v.rule_id == "HEC_not_via_Tremplin_or_Passerelle" for v in violations)

    def test_HEC_plus_Passerelle_same_response_blocks(self):
        txt = "Le concours Passerelle est une bonne option pour rejoindre HEC en 2 ans."
        violations = apply_rules(txt)
        assert any(v.rule_id == "HEC_not_via_Tremplin_or_Passerelle" for v in violations)

    def test_HEC_plus_Tremplin_slash_Passerelle_blocks(self):
        """Pattern type Q1 Gate J+6."""
        txt = "Admission HEC possible via concours Tremplin/Passerelle à bac+3."
        violations = apply_rules(txt)
        assert any(v.rule_id == "HEC_not_via_Tremplin_or_Passerelle" for v in violations)

    def test_HEC_without_Tremplin_OK(self):
        """HEC seul (ex: 'HEC via prépa') ne bloque pas."""
        txt = "Pour HEC, la voie classique est prépa ECG + concours BCE."
        violations = apply_rules(txt)
        assert not any(v.rule_id == "HEC_not_via_Tremplin_or_Passerelle" for v in violations)

    def test_Tremplin_without_HEC_OK(self):
        """Tremplin pour Audencia (légitime) ne bloque pas."""
        txt = "Tu peux viser Audencia via le concours Tremplin en bac+2."
        violations = apply_rules(txt)
        assert not any(v.rule_id == "HEC_not_via_Tremplin_or_Passerelle" for v in violations)

    def test_explicit_denial_is_allowed(self):
        """Mention pédagogique 'pas via Tremplin' ou 'non pas Tremplin' OK."""
        txt = (
            "HEC recrute via son concours propre AST (Admission sur Titres), "
            "pas via Tremplin ni Passerelle."
        )
        violations = apply_rules(txt)
        assert not any(v.rule_id == "HEC_not_via_Tremplin_or_Passerelle" for v in violations)


# =========================================================================
# V2.2 — Redoublement PASS interdit (arrêté 4 nov 2019)
# =========================================================================


class TestV2_2_PASS_redoublement:

    def test_redoublement_PASS_rare_blocks(self):
        """Pattern Q8 Gate J+6."""
        txt = "Le redoublement en PASS est rare : si tu échoues, tu te réorientes."
        violations = apply_rules(txt)
        assert any(v.rule_id == "PASS_no_redoublement" for v in violations)

    def test_redoubler_PASS_blocks(self):
        txt = "Si ça ne marche pas, tu peux redoubler PASS l'année suivante."
        violations = apply_rules(txt)
        assert any(v.rule_id == "PASS_no_redoublement" for v in violations)

    def test_deuxieme_chance_PASS_blocks(self):
        txt = "Tu as une deuxième chance en PASS si tu es ajourné au premier passage."
        violations = apply_rules(txt)
        assert any(v.rule_id == "PASS_no_redoublement" for v in violations)

    def test_redoublement_interdit_OK(self):
        """Mention correcte (arrêté 2019) ne doit pas bloquer."""
        txt = "Le redoublement en PASS est interdit : une seule chance (arrêté 2019)."
        violations = apply_rules(txt)
        assert not any(v.rule_id == "PASS_no_redoublement" for v in violations)

    def test_une_seule_chance_OK(self):
        txt = "En PASS, tu n'as qu'une seule chance. Échec → L.AS ou L2."
        violations = apply_rules(txt)
        assert not any(v.rule_id == "PASS_no_redoublement" for v in violations)


# =========================================================================
# V2.3 — Séries bac A/B/C/D supprimées (1995), L/ES/S supprimées (2021)
# =========================================================================


class TestV2_3_bac_series_obsoletes:

    def test_bac_B_blocks(self):
        """Pattern Q8 Gate J+6 ('42% des admis avaient un bac B')."""
        txt = "42% des admis avaient un bac B comme ton niveau actuel."
        violations = apply_rules(txt)
        assert any(v.rule_id == "bac_series_ABCD_abolished" for v in violations)

    def test_bac_A_blocks(self):
        txt = "Si tu es en terminale bac A littéraire, vise Sciences Po."
        violations = apply_rules(txt)
        assert any(v.rule_id == "bac_series_ABCD_abolished" for v in violations)

    def test_bac_C_blocks(self):
        txt = "Avec un bac C, tu peux viser une prépa MPSI."
        violations = apply_rules(txt)
        assert any(v.rule_id == "bac_series_ABCD_abolished" for v in violations)

    def test_bac_D_blocks(self):
        txt = "Le bac D permet d'accéder aux formations biologie/médecine."
        violations = apply_rules(txt)
        assert any(v.rule_id == "bac_series_ABCD_abolished" for v in violations)

    def test_serie_B_blocks(self):
        txt = "En série B, les maths sont importantes."
        violations = apply_rules(txt)
        assert any(v.rule_id == "bac_series_ABCD_abolished" for v in violations)

    def test_historical_context_OK(self):
        """Mention historique 'avant 1995' / 'ancien' doit passer."""
        txt = "Avant 1995, la série B existait (supprimée par la réforme)."
        violations = apply_rules(txt)
        assert not any(v.rule_id == "bac_series_ABCD_abolished" for v in violations)

    def test_section_A_doesnt_block(self):
        """'section A' dans un contexte d'appel (immatriculation) ne doit pas bloquer —
        on cible 'bac A' / 'série A' spécifiquement."""
        txt = "Dans la section A de ton dossier Parcoursup, précise tes vœux."
        violations = apply_rules(txt)
        assert not any(v.rule_id == "bac_series_ABCD_abolished" for v in violations)


# =========================================================================
# V2.4 — Kiné via IFMK, PAS via licence option/parcours directe
# =========================================================================


class TestV2_4_kine_IFMK:

    def test_licence_option_kinesitherapie_blocks(self):
        """Pattern Q6 Gate J+6."""
        txt = "Licence Sciences de la vie (option Kinésithérapie) à Perpignan."
        violations = apply_rules(txt)
        assert any(v.rule_id == "kine_via_IFMK_not_licence" for v in violations)

    def test_STAPS_parcours_kinesitherapie_blocks(self):
        """Pattern Q6 Gate J+6 (deuxième hallucination du même pack)."""
        txt = "Licence STAPS (parcours Kinésithérapie) à Font-Romeu."
        violations = apply_rules(txt)
        assert any(v.rule_id == "kine_via_IFMK_not_licence" for v in violations)

    def test_licence_menant_DE_kine_blocks(self):
        txt = "Une licence menant directement au DE de kiné en 3 ans."
        violations = apply_rules(txt)
        assert any(v.rule_id == "kine_via_IFMK_not_licence" for v in violations)

    def test_IFMK_mention_OK(self):
        """Mention correcte de l'IFMK ne bloque pas."""
        txt = "Après L.AS validé, tu passes le concours IFMK pour le DE kiné."
        violations = apply_rules(txt)
        assert not any(v.rule_id == "kine_via_IFMK_not_licence" for v in violations)

    def test_STAPS_standalone_OK(self):
        """STAPS sans parcours kiné (standalone) ne bloque pas."""
        txt = "STAPS prépare aux métiers du sport et au professorat d'EPS."
        violations = apply_rules(txt)
        assert not any(v.rule_id == "kine_via_IFMK_not_licence" for v in violations)


# =========================================================================
# Golden Gate J+6 pack hard — les 3 Q ambiguës DOIVENT toutes block V2
# =========================================================================


class TestGateJ6HardPack:
    """Les 3 Q du pack Gate J+6 jugées 2/5 médiane par le panel humain
    doivent TOUTES déclencher au moins 1 violation BLOCKING V2."""

    def test_Q1_HEC_11_moyenne_blocked_by_V2(self):
        """Extrait Q1 Gate J+6 : mention HEC + Tremplin/Passerelle à bac+3."""
        txt = (
            "HEC recrute 10% de ses élèves via admissions parallèles (à bac+3) — "
            "c'est ta meilleure porte d'entrée. Vise d'abord un BBA ou un IAE "
            "(accessible avec ton profil), puis tente le concours Tremplin/Passerelle "
            "à bac+3."
        )
        violations = apply_rules(txt)
        blocking = [v for v in violations if v.severity == Severity.BLOCKING]
        assert len(blocking) >= 1, f"Q1 doit bloquer V2 mais ne trouve que {violations}"

    def test_Q6_Perpignan_blocked_by_V2(self):
        """Extrait Q6 Gate J+6 : deux mentions kiné invalides."""
        txt = (
            "Licence Sciences de la vie (option Kinésithérapie) à Perpignan — "
            "bac+3 public, 9% d'accès (très sélectif). "
            "Licence STAPS (parcours Kinésithérapie) à Font-Romeu — 3% d'accès."
        )
        violations = apply_rules(txt)
        blocking = [v for v in violations if v.severity == Severity.BLOCKING]
        assert len(blocking) >= 1, f"Q6 doit bloquer V2 mais ne trouve que {violations}"

    def test_Q8_PASS_12_moyenne_blocked_by_V2(self):
        """Extrait Q8 Gate J+6 : bac B + redoublement PASS rare."""
        txt = (
            "PASS Le Havre — 42% d'accès. "
            "42% des admis avaient un bac B (comme ton niveau actuel). "
            "Le redoublement en PASS est rare : si tu échoues en 1ère année, "
            "tu devras te réorienter."
        )
        violations = apply_rules(txt)
        blocking = [v for v in violations if v.severity == Severity.BLOCKING]
        # Attend AU MOINS 2 BLOCKING (bac B + redoublement rare)
        assert len(blocking) >= 2, (
            f"Q8 doit bloquer V2 au moins 2x (bac B + redoublement) mais {violations}"
        )
