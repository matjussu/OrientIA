"""Tests A2 — mapping rules libre-forme Sprint 9 → enums Pydantic Axe 2.

Référence ordre : 2026-05-01-1820-claudette-orientia-sprint12-axe-2-agentic-phase-1-A1-A2-A4 (A2).

Couvre :
- `map_niveau_scolaire_to_education_level` : tous les patterns + fallback UNKNOWN
- `map_niveau_scolaire_to_age_group` : combinaisons niveau + age_estime + fallback OTHER_OR_UNKNOWN
- `infer_intent_type` : 9 enums + fallback ORIENTATION_INITIALE
- `infer_urgent_concern` : détection stress/urgence
- `derive_profile_state` : pipeline bout-en-bout via Session
- Régression Sprint 9 : `AnalystAgent.update_profile()` préservé bit-à-bit
- Bridge `AnalystAgent.analyze_for_routing()` mocké Mistral

Pas d'appel Mistral réel — tous les tests utilisent mocks ou fonctions pures.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.agents.hierarchical.analyst_agent import AnalystAgent
from src.agents.hierarchical.schemas import UserSessionProfile
from src.agents.hierarchical.session import Session
from src.axe2.contracts import (
    AgeGroup,
    EducationLevel,
    IntentType,
    ProfileState,
)
from src.axe2.profile_mapping import (
    derive_profile_state,
    infer_intent_type,
    infer_urgent_concern,
    map_niveau_scolaire_to_age_group,
    map_niveau_scolaire_to_education_level,
)


# =============================================================================
# map_niveau_scolaire_to_education_level
# =============================================================================


class TestMapEducationLevel:
    @pytest.mark.parametrize("niveau,expected", [
        ("terminale_spe_maths_physique", EducationLevel.TERMINALE),
        ("terminale_techno_sti2d", EducationLevel.TERMINALE),
        ("premiere_generale", EducationLevel.INFRA_BAC),
        ("seconde", EducationLevel.INFRA_BAC),
        ("l1_droit", EducationLevel.BAC_PLUS_1),
        ("l2_informatique", EducationLevel.BAC_PLUS_2),
        ("l3_eco_gestion", EducationLevel.BAC_PLUS_3),
        ("licence_3_droit", EducationLevel.BAC_PLUS_3),
        ("m1_droit_affaires", EducationLevel.BAC_PLUS_4),
        ("m2_cybersecurite", EducationLevel.BAC_PLUS_5),
        ("master_meef", EducationLevel.BAC_PLUS_5),
        ("doctorat_physique", EducationLevel.BAC_PLUS_8_DOCTORAT),
        ("phd_neurosciences", EducationLevel.BAC_PLUS_8_DOCTORAT),
        ("bts_compta", EducationLevel.BAC_PLUS_2),
        ("but_info", EducationLevel.BAC_PLUS_2),
        ("dut_meca", EducationLevel.BAC_PLUS_2),
        ("prepa_mpsi", EducationLevel.BAC_PLUS_1),
        ("prepa_pcsi", EducationLevel.BAC_PLUS_1),
        ("professionnel_actif_dev", EducationLevel.PROFESSIONNEL_ACTIF),
        ("salarie_marketing", EducationLevel.PROFESSIONNEL_ACTIF),
        ("bachelier_general", EducationLevel.BAC_OBTENU),
        ("bac+5_ingenieur", EducationLevel.BAC_PLUS_5),
        ("bac+3_licence", EducationLevel.BAC_PLUS_3),
    ])
    def test_known_patterns(self, niveau, expected):
        assert map_niveau_scolaire_to_education_level(niveau) == expected

    def test_none_returns_unknown(self):
        assert map_niveau_scolaire_to_education_level(None) == EducationLevel.UNKNOWN

    def test_empty_string_returns_unknown(self):
        assert map_niveau_scolaire_to_education_level("") == EducationLevel.UNKNOWN

    def test_unknown_pattern_returns_unknown(self):
        assert map_niveau_scolaire_to_education_level("inventé_inconnu") == EducationLevel.UNKNOWN


# =============================================================================
# map_niveau_scolaire_to_age_group
# =============================================================================


class TestMapAgeGroup:
    @pytest.mark.parametrize("niveau,age,expected", [
        # Lycéens
        ("terminale_spe_maths_physique", None, AgeGroup.LYCEEN_TERMINALE),
        ("terminale_techno_sti2d", None, AgeGroup.BACHELIER_TECHNO),
        ("terminale_pro_commerce", None, AgeGroup.BACHELIER_PRO),
        ("seconde_generale", None, AgeGroup.LYCEEN_2NDE),
        ("premiere_techno", None, AgeGroup.LYCEEN_2NDE),  # premiere → lyceen_2nde catch-all
        # Post-bac universitaire
        ("l1_droit", None, AgeGroup.ETUDIANT_L1_L3),
        ("l3_info", None, AgeGroup.ETUDIANT_L1_L3),
        ("licence_eco", None, AgeGroup.ETUDIANT_L1_L3),
        ("m1_cybersecurite", None, AgeGroup.ETUDIANT_MASTER),
        ("m2_droit_affaires", None, AgeGroup.ETUDIANT_MASTER),
        ("master_lmd_info", None, AgeGroup.ETUDIANT_MASTER),
        ("doctorat_neurosciences", None, AgeGroup.ETUDIANT_MASTER),  # approximation
        # BUT/BTS/Prépa
        ("but_info_data", None, AgeGroup.BACHELIER_GENERAL),
        ("bts_compta", None, AgeGroup.BACHELIER_GENERAL),
        ("prepa_mpsi", None, AgeGroup.BACHELIER_GENERAL),
        # Professionnels
        ("professionnel_actif_marketing", None, AgeGroup.PROFESSIONNEL_ACTIF),
        ("salarie_juriste", None, AgeGroup.PROFESSIONNEL_ACTIF),
        # Parents
        ("parent_lyceen_concerned", None, AgeGroup.PARENT_LYCEEN),
        # Fallback age_estime quand pas de niveau
        (None, 15, AgeGroup.LYCEEN_2NDE),
        (None, 17, AgeGroup.LYCEEN_TERMINALE),
        (None, 20, AgeGroup.ETUDIANT_L1_L3),
        (None, 24, AgeGroup.ETUDIANT_MASTER),
        (None, 35, AgeGroup.ADULTE_25_45),
        # Fallback OTHER_OR_UNKNOWN
        (None, None, AgeGroup.OTHER_OR_UNKNOWN),
        ("inventé_inconnu", None, AgeGroup.OTHER_OR_UNKNOWN),
    ])
    def test_known_combinations(self, niveau, age, expected):
        assert map_niveau_scolaire_to_age_group(niveau, age) == expected

    def test_niveau_overrides_age_estime(self):
        # Si niveau matche, on ignore age_estime
        assert map_niveau_scolaire_to_age_group("terminale_generale", 35) == AgeGroup.LYCEEN_TERMINALE


# =============================================================================
# infer_intent_type
# =============================================================================


class TestInferIntentType:
    @pytest.mark.parametrize("query,expected", [
        # Reconversion
        ("Je veux me reconvertir vers le paramédical", IntentType.RECONVERSION_PRO),
        ("Comment changer de carrière à 35 ans ?", IntentType.RECONVERSION_PRO),
        ("Je cherche un changement de métier", IntentType.RECONVERSION_PRO),
        # Réorientation étude
        ("Comment me réorienter en L1 droit ?", IntentType.REORIENTATION_ETUDE),
        ("Je veux changer de filière post-bac", IntentType.REORIENTATION_ETUDE),
        ("Pivoter vers du concret après MPSI", IntentType.REORIENTATION_ETUDE),
        # Comparaison
        ("Comparer EFREI et ENSIBS pour cyber", IntentType.COMPARAISON_OPTIONS),
        ("BUT info ou BTS SIO ?", IntentType.COMPARAISON_OPTIONS),
        ("Master cyber vs ingé cyber", IntentType.COMPARAISON_OPTIONS),
        # Définition / conceptuel
        ("Qu'est-ce que la prépa MPSI ?", IntentType.CONCEPTUEL_DEFINITION),
        ("C'est quoi un BUT ?", IntentType.CONCEPTUEL_DEFINITION),
        ("Définition de RNCP", IntentType.CONCEPTUEL_DEFINITION),
        # Métier spécifique
        ("Métier de data scientist débouchés", IntentType.INFO_METIER_SPECIFIQUE),
        ("Profession d'ingénieur cyber", IntentType.INFO_METIER_SPECIFIQUE),
        # Démarche administrative
        ("Comment s'inscrire sur Parcoursup ?", IntentType.DEMARCHE_ADMINISTRATIVE),
        ("Démarche dossier inscription Master", IntentType.DEMARCHE_ADMINISTRATIVE),
        ("Parcoursup deadline calendrier 2026", IntentType.DEMARCHE_ADMINISTRATIVE),
        # Conseil stratégique
        ("Que me conseilles-tu pour un bac+5 ?", IntentType.CONSEIL_STRATEGIQUE),
        ("Quelle stratégie pour intégrer une prépa ?", IntentType.CONSEIL_STRATEGIQUE),
        # Découverte filières
        ("Quelles formations existe en cyber ?", IntentType.DECOUVERTE_FILIERES),
        ("Découvrir les filières scientifiques", IntentType.DECOUVERTE_FILIERES),
        # Default ORIENTATION_INITIALE
        ("Je suis en terminale, je cherche une formation", IntentType.ORIENTATION_INITIALE),
        ("J'aimerais faire de l'informatique", IntentType.ORIENTATION_INITIALE),
    ])
    def test_known_patterns(self, query, expected):
        assert infer_intent_type(query) == expected

    def test_none_returns_other(self):
        assert infer_intent_type(None) == IntentType.OTHER

    def test_empty_returns_other(self):
        assert infer_intent_type("") == IntentType.OTHER


# =============================================================================
# infer_urgent_concern
# =============================================================================


class TestInferUrgentConcern:
    def test_stress_in_query_detected(self):
        assert infer_urgent_concern(None, None, "Je suis stressée par l'orientation") is True

    def test_burnout_in_query(self):
        assert infer_urgent_concern(None, None, "Je suis en burn-out post-MPSI") is True

    def test_panic_word(self):
        assert infer_urgent_concern(None, None, "Je panique pour Parcoursup") is True

    def test_stress_in_valeurs(self):
        assert infer_urgent_concern(["stress_lyceen", "perdue"], None, "Hello") is True

    def test_in_questions_ouvertes(self):
        assert infer_urgent_concern(None, ["urgence d'agir avant fin janvier"], "Hello") is True

    def test_no_urgent_signals(self):
        assert infer_urgent_concern(["impact_societal"], ["budget_etudes"], "Quelles formations cyber ?") is False

    def test_all_none_returns_false(self):
        assert infer_urgent_concern(None, None, None) is False


# =============================================================================
# derive_profile_state — pipeline bout-en-bout
# =============================================================================


class TestDeriveProfileState:
    def test_full_session_with_profile_and_query(self):
        session = Session.new_anonymous()
        session.profile.niveau_scolaire = "terminale_spe_maths_physique"
        session.profile.region = "Île-de-France"
        session.profile.interets_detectes = ["informatique", "math_pure"]
        session.profile.confidence = 0.7
        session.add_user_turn("Je veux comparer EFREI et ENSIBS pour cyber post-bac")

        ps = derive_profile_state(session)

        assert ps.age_group == AgeGroup.LYCEEN_TERMINALE
        assert ps.education_level == EducationLevel.TERMINALE
        assert ps.intent_type == IntentType.COMPARAISON_OPTIONS
        assert ps.sector_interest == ["informatique", "math_pure"]
        assert ps.region == "Île-de-France"
        assert ps.urgent_concern is False
        assert ps.confidence == 0.7

    def test_explicit_user_query_overrides_session(self):
        session = Session.new_anonymous()
        session.profile.niveau_scolaire = "l1_droit"
        session.add_user_turn("Hello")

        ps = derive_profile_state(session, user_query="Comment me reconvertir au paramédical ?")

        assert ps.intent_type == IntentType.RECONVERSION_PRO
        assert ps.age_group == AgeGroup.ETUDIANT_L1_L3

    def test_empty_session_falls_back_to_other_unknown(self):
        session = Session.new_anonymous()
        ps = derive_profile_state(session)
        assert ps.age_group == AgeGroup.OTHER_OR_UNKNOWN
        assert ps.education_level == EducationLevel.UNKNOWN
        assert ps.intent_type == IntentType.OTHER  # query None

    def test_urgent_concern_propagated_from_query(self):
        session = Session.new_anonymous()
        session.profile.niveau_scolaire = "prepa_mpsi"
        session.add_user_turn("Je suis en burn-out total, j'ai peur de tout abandonner")

        ps = derive_profile_state(session)
        assert ps.urgent_concern is True
        assert ps.age_group == AgeGroup.BACHELIER_GENERAL


# =============================================================================
# Régression Sprint 9 — update_profile préservé bit-à-bit
# =============================================================================


class TestRegressionUpdateProfile:
    def test_update_profile_signature_unchanged(self):
        """Vérifie que update_profile ne nécessite que session (Sprint 9 API)."""
        import inspect
        sig = inspect.signature(AnalystAgent.update_profile)
        params = list(sig.parameters.keys())
        # ['self', 'session']
        assert params == ["self", "session"]

    def test_update_profile_returns_dict_when_no_turns(self):
        agent = AnalystAgent(client=MagicMock())
        session = Session.new_anonymous()
        # Pas de tour user → update retourne {}
        assert agent.update_profile(session) == {}

    def test_analyze_for_routing_signature_added_not_replacing(self):
        """analyze_for_routing existe ET update_profile aussi (additif)."""
        assert hasattr(AnalystAgent, "update_profile")
        assert hasattr(AnalystAgent, "analyze_for_routing")
        import inspect
        sig = inspect.signature(AnalystAgent.analyze_for_routing)
        params = list(sig.parameters.keys())
        assert params == ["self", "session", "user_query"]


# =============================================================================
# Bridge analyze_for_routing — mocked Mistral
# =============================================================================


class TestAnalyzeForRouting:
    def test_mocked_full_flow_terminale_compare(self):
        """Mock Mistral retourne un delta UserSessionProfile pour
        terminale spé maths-physique. analyze_for_routing produit le
        ProfileState typed correspondant."""
        # Mock le Mistral response avec tool_call
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_msg = MagicMock()
        mock_tool_call = MagicMock()
        mock_tool_call.function.name = "update_session_profile"
        mock_tool_call.function.arguments = (
            '{"niveau_scolaire": "terminale_spe_maths_physique", '
            '"age_estime": 17, '
            '"region": "Île-de-France", '
            '"interets_detectes": ["informatique", "math_appliquee"], '
            '"contraintes": [], '
            '"valeurs": [], '
            '"questions_ouvertes": [], '
            '"confidence": 0.8}'
        )
        mock_msg.tool_calls = [mock_tool_call]
        mock_choice.message = mock_msg
        mock_response.choices = [mock_choice]
        mock_client.chat.complete.return_value = mock_response

        agent = AnalystAgent(client=mock_client, max_retries=1)
        session = Session.new_anonymous()
        session.add_user_turn("Comparer EFREI et ENSIBS pour cyber post-bac ?")

        ps = agent.analyze_for_routing(session)

        assert isinstance(ps, ProfileState)
        assert ps.age_group == AgeGroup.LYCEEN_TERMINALE
        assert ps.education_level == EducationLevel.TERMINALE
        assert ps.intent_type == IntentType.COMPARAISON_OPTIONS
        assert ps.sector_interest == ["informatique", "math_appliquee"]
        assert ps.region == "Île-de-France"
        assert ps.confidence == pytest.approx(0.8, rel=0.01)

        # Side effect : session.profile mutée par merge_update
        assert session.profile.niveau_scolaire == "terminale_spe_maths_physique"
        assert session.profile.region == "Île-de-France"

    def test_mocked_mistral_error_falls_back_to_existing_profile(self):
        """Si Mistral plante, update_profile retourne {} (passthrough),
        mais analyze_for_routing dérive ProfileState depuis le profile
        actuel session (potentiellement OTHER_OR_UNKNOWN)."""
        mock_client = MagicMock()
        mock_client.chat.complete.side_effect = Exception("API blip")

        agent = AnalystAgent(client=mock_client, max_retries=1)
        session = Session.new_anonymous()
        # Pré-remplir le profile (simule un tour précédent)
        session.profile.niveau_scolaire = "l2_informatique"
        session.profile.confidence = 0.6
        session.add_user_turn("Comment trouver un stage ?")

        ps = agent.analyze_for_routing(session)
        # Pas crash, ProfileState dérivé depuis state existant
        assert isinstance(ps, ProfileState)
        assert ps.education_level == EducationLevel.BAC_PLUS_2
        assert ps.age_group == AgeGroup.ETUDIANT_L1_L3

    def test_mocked_no_tool_call_produces_other_unknown(self):
        """Si Mistral répond sans tool_call (rare), update_profile
        retourne {}, profile reste vide, ProfileState = OTHER_OR_UNKNOWN /
        UNKNOWN."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_msg = MagicMock()
        mock_msg.tool_calls = None  # No tool call
        mock_choice.message = mock_msg
        mock_response.choices = [mock_choice]
        mock_client.chat.complete.return_value = mock_response

        agent = AnalystAgent(client=mock_client, max_retries=1)
        session = Session.new_anonymous()
        session.add_user_turn("Bonjour")

        ps = agent.analyze_for_routing(session)
        assert ps.age_group == AgeGroup.OTHER_OR_UNKNOWN
        assert ps.education_level == EducationLevel.UNKNOWN
