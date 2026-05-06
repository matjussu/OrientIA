"""Tests src/rag/fact_card.py — extraction structurée fiches pour contrat v4."""
from __future__ import annotations

import json

from src.rag.fact_card import (
    FactCard,
    FactChiffres,
    fiche_to_fact_card,
    format_sources_for_llm,
    has_any_chiffres,
)


# ─────────────── Fixtures de fiches réalistes ───────────────


def fiche_parcoursup_riche() -> dict:
    """Fiche typique sous-corpus Parcoursup (21.5%) avec tous les chiffres."""
    return {
        "source": "parcoursup",
        "domaine": "cyber",
        "nom": "Bachelor Cybersécurité des systèmes industriels",
        "etablissement": "Lycée Emmanuel d'Alzon",
        "ville": "Nîmes",
        "region": "Occitanie",
        "niveau": "bac+3",
        "statut": "Privé",
        "type_diplome": "formation d'école spécialisée",
        "duree": "3 ans",
        "taux_acces_parcoursup_2025": 52.0,
        "nombre_places": 25,
        "propositions_totales": 53,
        "pct_acceptes_debut_pp": 0.0,
        "selectivite_code": "formation sélective",
        "lien_form_psup": "https://dossierappel.parcoursup.fr/?g_ta_cod=39320",
        "url_onisep": "https://www.onisep.fr/.../FOR.9891",
        "admission": {
            "session": 2025,
            "taux_acces": 52.0,
            "places": 25,
        },
        "insertion_pro": {
            "taux_emploi_3ans": 0.86,
            "taux_emploi_6ans": 0.91,
            "taux_cdi": 0.83,
            "salaire_median_embauche": 1740,
            "source": "cereq",
        },
        "debouches": [
            {"code_rome": "M1812", "libelle": "RSSI"},
            {"code_rome": "M1817", "libelle": "Administrateur sécurité"},
            {"code_rome": "M1819", "libelle": "Ingénieur sécurité"},
        ],
        "collected_at": {"parcoursup": "2026-04-24"},
    }


def fiche_monmaster_simple() -> dict:
    """Fiche MonMaster (master) sans chiffres Parcoursup, juste insertion_pro."""
    return {
        "source": "monmaster",
        "phase": "master",
        "nom": "DROIT DES AFFAIRES — Juriste d'affaires fiscaliste",
        "etablissement": "Université Paris Cité",
        "ville": "MALAKOFF",
        "niveau": "bac+5",
        "insertion_pro": {
            "taux_emploi_3ans": 0.85,
            "salaire_median_embauche": 2570,
        },
        "url_onisep": "https://www.onisep.fr/.../FOR.10535",
    }


def fiche_rncp_minimal() -> dict:
    """Fiche RNCP nationale sans école nommée — cas des fiches multi-corpus."""
    return {
        "source": "rncp",
        "nom": "Cybersécurité",
        "rncp": "RNCP12345",
        "niveau": "bac+5",
        "text": "Titre RNCP de niveau 7 en cybersécurité. Compétences : audit, "
                "pentest, gouvernance SSI, conformité. Reconnu par l'État.",
    }


def fiche_corrupted() -> dict:
    """Fiche avec champs corrompus (None, NaN, strings vides)."""
    return {
        "nom": "  Test Formation  ",  # whitespace à trim
        "etablissement": "",
        "ville": "non renseigné",
        "niveau": None,
        "taux_acces_parcoursup_2025": "abc",  # non parsable
        "nombre_places": "25",  # str → int OK
        "insertion_pro": {
            "taux_emploi_3ans": "0.86",  # str → float OK
            "salaire_median_embauche": float("nan"),  # NaN → None
        },
        "debouches": [
            {"libelle": ""},  # vide → skip
            {"libelle": "Métier valide"},
            "non-dict-item",  # type wrong → skip
        ],
    }


# ─────────────── Tests fiche_to_fact_card ───────────────


class TestFicheToFactCardParcoursupRiche:
    def test_extracts_identity(self):
        card = fiche_to_fact_card(fiche_parcoursup_riche(), "S1")
        assert card.id == "S1"
        assert card.formation == "Bachelor Cybersécurité des systèmes industriels"
        assert card.etablissement == "Lycée Emmanuel d'Alzon"
        assert card.ville == "Nîmes"
        assert card.region == "Occitanie"
        assert card.niveau == "bac+3"
        assert card.statut == "Privé"

    def test_extracts_chiffres_parcoursup(self):
        card = fiche_to_fact_card(fiche_parcoursup_riche(), "S1")
        assert card.chiffres.taux_acces_parcoursup_2025 == 52.0
        assert card.chiffres.nombre_places == 25
        assert card.chiffres.duree == "3 ans"
        assert card.chiffres.propositions_totales == 53

    def test_extracts_chiffres_insertion_pro(self):
        card = fiche_to_fact_card(fiche_parcoursup_riche(), "S1")
        assert card.chiffres.taux_emploi_3ans == 0.86
        assert card.chiffres.taux_emploi_6ans == 0.91
        assert card.chiffres.taux_cdi == 0.83
        assert card.chiffres.salaire_median_embauche == 1740

    def test_extracts_debouches_libelles(self):
        card = fiche_to_fact_card(fiche_parcoursup_riche(), "S1")
        assert "RSSI" in card.debouches
        assert "Administrateur sécurité" in card.debouches
        assert len(card.debouches) == 3

    def test_picks_parcoursup_url_in_priority(self):
        card = fiche_to_fact_card(fiche_parcoursup_riche(), "S1")
        assert card.url == "https://dossierappel.parcoursup.fr/?g_ta_cod=39320"

    def test_picks_annee_from_admission_session(self):
        card = fiche_to_fact_card(fiche_parcoursup_riche(), "S1")
        assert card.annee_donnees == 2025


class TestFicheToFactCardMonMaster:
    def test_extracts_identity_without_parcoursup_chiffres(self):
        card = fiche_to_fact_card(fiche_monmaster_simple(), "S1")
        assert card.formation == "DROIT DES AFFAIRES — Juriste d'affaires fiscaliste"
        assert card.etablissement == "Université Paris Cité"
        assert card.niveau == "bac+5"

    def test_chiffres_parcoursup_are_none(self):
        card = fiche_to_fact_card(fiche_monmaster_simple(), "S1")
        assert card.chiffres.taux_acces_parcoursup_2025 is None
        assert card.chiffres.nombre_places is None

    def test_chiffres_insertion_pro_present(self):
        card = fiche_to_fact_card(fiche_monmaster_simple(), "S1")
        assert card.chiffres.taux_emploi_3ans == 0.85
        assert card.chiffres.salaire_median_embauche == 2570

    def test_url_falls_back_to_onisep(self):
        card = fiche_to_fact_card(fiche_monmaster_simple(), "S1")
        assert card.url == "https://www.onisep.fr/.../FOR.10535"


class TestFicheToFactCardRNCPMinimal:
    def test_extracts_text_libre_when_no_etab(self):
        card = fiche_to_fact_card(fiche_rncp_minimal(), "S1")
        assert card.formation == "Cybersécurité"
        assert card.etablissement is None
        assert card.text_libre is not None
        assert "audit" in card.text_libre.lower()

    def test_no_chiffres_disponibles(self):
        card = fiche_to_fact_card(fiche_rncp_minimal(), "S1")
        assert not has_any_chiffres(card)


class TestFicheToFactCardCorrupted:
    def test_trims_whitespace(self):
        card = fiche_to_fact_card(fiche_corrupted(), "S1")
        assert card.formation == "Test Formation"

    def test_empty_strings_to_none(self):
        card = fiche_to_fact_card(fiche_corrupted(), "S1")
        assert card.etablissement is None  # was ""

    def test_non_renseigne_to_none(self):
        card = fiche_to_fact_card(fiche_corrupted(), "S1")
        assert card.ville is None  # was "non renseigné"

    def test_unparseable_int_to_none(self):
        card = fiche_to_fact_card(fiche_corrupted(), "S1")
        assert card.chiffres.taux_acces_parcoursup_2025 is None  # was "abc"

    def test_str_int_parsed(self):
        card = fiche_to_fact_card(fiche_corrupted(), "S1")
        assert card.chiffres.nombre_places == 25  # was "25"

    def test_str_float_parsed(self):
        card = fiche_to_fact_card(fiche_corrupted(), "S1")
        assert card.chiffres.taux_emploi_3ans == 0.86

    def test_nan_to_none(self):
        card = fiche_to_fact_card(fiche_corrupted(), "S1")
        assert card.chiffres.salaire_median_embauche is None

    def test_bad_debouches_filtered(self):
        card = fiche_to_fact_card(fiche_corrupted(), "S1")
        assert card.debouches == ["Métier valide"]

    def test_no_url_returns_none(self):
        card = fiche_to_fact_card(fiche_corrupted(), "S1")
        assert card.url is None


# ─────────────── Tests has_any_chiffres ───────────────


class TestHasAnyChiffres:
    def test_parcoursup_riche_has_chiffres(self):
        card = fiche_to_fact_card(fiche_parcoursup_riche(), "S1")
        assert has_any_chiffres(card)

    def test_monmaster_with_insertion_has_chiffres(self):
        card = fiche_to_fact_card(fiche_monmaster_simple(), "S1")
        assert has_any_chiffres(card)

    def test_rncp_minimal_no_chiffres(self):
        card = fiche_to_fact_card(fiche_rncp_minimal(), "S1")
        assert not has_any_chiffres(card)


# ─────────────── Tests format_sources_for_llm (sérialisation JSON) ───────────────


class TestFormatSourcesForLLM:
    def test_handles_list_of_score_fiche_dicts(self):
        """Format pipeline : list[{score: float, fiche: dict}]."""
        sources = [
            {"score": 0.9, "fiche": fiche_parcoursup_riche()},
            {"score": 0.7, "fiche": fiche_monmaster_simple()},
        ]
        out = format_sources_for_llm(sources)
        parsed = json.loads(out)
        assert len(parsed) == 2
        assert parsed[0]["id"] == "S1"
        assert parsed[1]["id"] == "S2"
        assert parsed[0]["formation"].startswith("Bachelor Cyber")

    def test_handles_list_of_raw_fiches(self):
        """Format alternatif : la liste contient les fiches directement."""
        sources = [fiche_parcoursup_riche(), fiche_monmaster_simple()]
        out = format_sources_for_llm(sources)
        parsed = json.loads(out)
        assert len(parsed) == 2

    def test_caps_at_max_sources(self):
        sources = [fiche_parcoursup_riche()] * 15
        out = format_sources_for_llm(sources, max_sources=10)
        parsed = json.loads(out)
        assert len(parsed) == 10
        # IDs séquentiels S1..S10
        assert parsed[0]["id"] == "S1"
        assert parsed[-1]["id"] == "S10"

    def test_chiffres_block_always_present_even_if_all_null(self):
        """Le LLM doit voir les `null` explicites pour décider 'info non disponible'."""
        sources = [fiche_rncp_minimal()]
        out = format_sources_for_llm(sources)
        parsed = json.loads(out)
        # `chiffres` doit être présent, avec tous les champs null
        assert "chiffres" in parsed[0]
        for v in parsed[0]["chiffres"].values():
            assert v is None

    def test_none_fields_stripped_except_chiffres(self):
        """Les champs None hors `chiffres` ne polluent pas le JSON."""
        sources = [fiche_rncp_minimal()]
        out = format_sources_for_llm(sources)
        parsed = json.loads(out)
        # etablissement absent (was None) ; chiffres présent (block conservé)
        assert "etablissement" not in parsed[0]
        assert "chiffres" in parsed[0]

    def test_skips_non_dict_sources(self):
        """Items malformés ne crashent pas, sont skippés silencieusement."""
        sources = [
            {"score": 0.9, "fiche": fiche_parcoursup_riche()},
            "not-a-dict",
            None,
            {"fiche": "not-a-dict-either"},
        ]
        out = format_sources_for_llm(sources)
        parsed = json.loads(out)
        # Seule la 1re carte est valide
        assert len(parsed) == 1

    def test_caps_debouches_per_card(self):
        f = fiche_parcoursup_riche()
        f["debouches"] = [{"libelle": f"Métier {i}"} for i in range(20)]
        sources = [f]
        out = format_sources_for_llm(sources, max_debouches_per_card=3)
        parsed = json.loads(out)
        assert len(parsed[0]["debouches"]) == 3
