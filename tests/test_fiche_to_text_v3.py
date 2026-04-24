"""Tests `fiche_to_text()` v3 — injection stats insertion_pro + admission.

Motivation : bench v2 (bench_personas_2026-04-24) a révélé que le modèle
hallucinait des stats précises parce que le retrieval ne les exposait
pas. Ces tests verrouillent l'injection v3 pour que les stats deviennent
retrievables.
"""
from __future__ import annotations

import pytest

from src.rag.embeddings import (
    _format_admission_stats,
    _format_insertion_pro,
    fiche_to_text,
)


# --- _format_insertion_pro : schéma Céreq ---


def test_insertion_pro_cereq_complet():
    ip = {
        "source": "cereq",
        "cohorte": "Generation 2017",
        "taux_emploi_3ans": 0.85,
        "taux_emploi_6ans": 0.91,
        "taux_cdi": 0.83,
        "salaire_median_embauche": 2080,
    }
    out = _format_insertion_pro(ip)
    assert out is not None
    assert "Céreq" in out
    assert "Generation 2017" in out
    assert "85%" in out
    assert "91%" in out
    assert "83%" in out
    assert "2080€" in out


def test_insertion_pro_cereq_partiel():
    """Certains champs absents → ne crash pas, concatène ce qu'on a."""
    ip = {
        "source": "cereq",
        "cohorte": "Generation 2017",
        "taux_emploi_3ans": 0.75,
        "taux_emploi_6ans": None,  # absent
        "taux_cdi": None,
        "salaire_median_embauche": 1650,
    }
    out = _format_insertion_pro(ip)
    assert out is not None
    assert "75%" in out
    assert "1650€" in out
    assert "None" not in out  # pas de fuite de None en texte


def test_insertion_pro_cereq_tous_none_returns_none():
    ip = {
        "source": "cereq",
        "taux_emploi_3ans": None,
        "taux_emploi_6ans": None,
        "taux_cdi": None,
        "salaire_median_embauche": None,
    }
    assert _format_insertion_pro(ip) is None


# --- _format_insertion_pro : schéma CFA ---


def test_insertion_pro_cfa_complet():
    ip = {
        "source": "inserjeunes_cfa",
        "annee": "cumul 2023-2024",
        "taux_emploi_6m": 0.81,
        "taux_emploi_12m": 0.73,
        "taux_emploi_18m": None,
        "taux_emploi_24m": None,
        "taux_emploi_6m_attendu": 0.73,
        "valeur_ajoutee_emploi_6m": 0.08,
        "taux_contrats_interrompus": 0.05,
        "part_poursuite_etudes": 0.3,
    }
    out = _format_insertion_pro(ip)
    assert out is not None
    assert "CFA" in out
    assert "cumul 2023-2024" in out
    assert "6 mois 81%" in out
    assert "12 mois 73%" in out
    assert "valeur ajoutée" in out.lower() or "8pp" in out
    assert "5%" in out  # rupture
    assert "30%" in out  # poursuite


def test_insertion_pro_cfa_horizons_partiels():
    """Si seulement 6m présent, le formateur inclut juste ça."""
    ip = {
        "source": "inserjeunes_cfa",
        "annee": "2023",
        "taux_emploi_6m": 0.77,
        "taux_emploi_12m": None,
        "taux_emploi_18m": None,
        "taux_emploi_24m": None,
    }
    out = _format_insertion_pro(ip)
    assert out is not None
    assert "6 mois 77%" in out
    assert "None" not in out


def test_insertion_pro_non_dict_returns_none():
    assert _format_insertion_pro(None) is None
    assert _format_insertion_pro([]) is None
    assert _format_insertion_pro("text") is None


# --- _format_admission_stats ---


def test_admission_parcoursup():
    f = {
        "source": "parcoursup",
        "taux_acces_parcoursup_2025": 52.0,
        "nombre_places": 150,
    }
    out = _format_admission_stats(f)
    assert out is not None
    assert "52%" in out
    assert "150 places" in out


def test_admission_monmaster():
    f = {
        "source": "monmaster",
        "taux_admission": 0.25,  # 25% admis
        "n_candidats_pp": 120,
        "n_acceptes_total": 30,
    }
    out = _format_admission_stats(f)
    assert out is not None
    assert "25%" in out
    assert "120 candidats" in out
    assert "30 acceptés" in out


def test_admission_sans_stats_returns_none():
    f = {"source": "rncp", "nom": "X"}  # pas de taux
    assert _format_admission_stats(f) is None


# --- fiche_to_text intégration ---


def test_fiche_to_text_injects_insertion_cereq():
    fiche = {
        "nom": "Licence Informatique",
        "etablissement": "Université Test",
        "ville": "Paris",
        "niveau": "bac+3",
        "phase": "initial",
        "domaine": "data_ia",
        "insertion_pro": {
            "source": "cereq",
            "cohorte": "Generation 2017",
            "taux_emploi_3ans": 0.78,
            "salaire_median_embauche": 1950,
        },
    }
    text = fiche_to_text(fiche)
    assert "Licence Informatique" in text
    assert "Université Test" in text
    assert "Insertion pro" in text
    assert "78%" in text  # taux retrievable !
    assert "1950€" in text  # salaire retrievable !


def test_fiche_to_text_injects_monmaster_admission():
    fiche = {
        "nom": "Master Droit",
        "etablissement": "Univ X",
        "ville": "Lyon",
        "source": "monmaster",
        "niveau": "bac+5",
        "phase": "master",
        "taux_admission": 0.15,
        "n_candidats_pp": 200,
        "n_acceptes_total": 30,
    }
    text = fiche_to_text(fiche)
    assert "Admission" in text
    assert "15%" in text
    assert "200 candidats" in text


def test_fiche_to_text_injects_cfa_horizons():
    fiche = {
        "nom": "CFA Test",
        "etablissement": "CFA Test",
        "ville": "",
        "source": "inserjeunes_cfa",
        "domaine": "apprentissage",
        "phase": "reorientation",
        "insertion_pro": {
            "source": "inserjeunes_cfa",
            "annee": "2023",
            "taux_emploi_6m": 0.80,
            "taux_emploi_12m": 0.85,
            "taux_emploi_18m": None,
            "taux_emploi_24m": None,
        },
    }
    text = fiche_to_text(fiche)
    assert "Insertion apprentissage" in text
    assert "6 mois 80%" in text
    assert "12 mois 85%" in text


def test_fiche_to_text_no_insertion_pro_doesnt_crash():
    """Fiche sans insertion_pro → pas de section insertion, pas de crash."""
    fiche = {
        "nom": "X", "etablissement": "Y", "ville": "Z",
        "niveau": "bac+3", "phase": "initial",
    }
    text = fiche_to_text(fiche)
    assert "Insertion pro" not in text
    assert "Insertion apprentissage" not in text
    assert text  # non-vide


def test_fiche_to_text_ordre_parts_conserve():
    """L'ordre nom/etab/ville reste en tête, stats en queue."""
    fiche = {
        "nom": "Formation N",
        "etablissement": "Etab E",
        "ville": "Ville V",
        "insertion_pro": {
            "source": "cereq", "cohorte": "G17",
            "taux_emploi_3ans": 0.7,
        },
    }
    text = fiche_to_text(fiche)
    idx_nom = text.find("Formation N")
    idx_ins = text.find("Insertion pro")
    assert 0 <= idx_nom < idx_ins


def test_fiche_to_text_region_injected():
    """v3 ajoute région pour queries géographiques."""
    fiche = {
        "nom": "X", "etablissement": "Y", "ville": "Bordeaux",
        "region": "Nouvelle-Aquitaine",
    }
    text = fiche_to_text(fiche)
    assert "Nouvelle-Aquitaine" in text
