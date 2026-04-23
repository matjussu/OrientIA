"""Tests `src/collect/rncp.py` — ingestion France Compétences RNCP D9.

Focus :
- Normalisation (mapping niveau EU → OrientIA + phase ADR-039)
- Join relationnel des 5 tables par Numero_Fiche
- Filtre active vs inactive
- Entrée principale `collect_rncp_certifications` avec ZIP réel (integration léger).

Tests OFFLINE — le ZIP est lu depuis `data/raw/rncp/` s'il existe, sinon skip
(pas de download en CI).
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.collect.rncp import (
    NIVEAU_EU_TO_ORIENTIA,
    NIVEAU_EU_TO_PHASE,
    _index_by_fiche,
    build_certifications,
    fetch_latest_csv_zip_url,
    normalize_rncp_certification,
)


STD_ACTIVE_MASTER = {
    "Id_Fiche": "9999",
    "Numero_Fiche": "RNCP99999",
    "Intitule": "Manager en cybersécurité",
    "Abrege_Libelle": "M",
    "Abrege_Intitule": "Titre RNCP niveau Master",
    "Nomenclature_Europe_Niveau": "NIV7",
    "Nomenclature_Europe_Intitule": "Niveau 7",
    "Type_Enregistrement": "Enregistrement sur demande",
    "Validation_Partielle": "Non",
    "Actif": "ACTIVE",
    "Date_dernier_jo": "15/03/2024",
    "Date_Effet": "01/04/2024",
    "Date_Fin_Enregistrement": "01/04/2027",
}

STD_INACTIVE_BAC = {
    **STD_ACTIVE_MASTER,
    "Numero_Fiche": "RNCP77777",
    "Intitule": "CAP Boulangerie (historique)",
    "Nomenclature_Europe_Niveau": "NIV3",
    "Actif": "INACTIVE",
}


# --- Mapping ---


def test_niveau_mapping_complete():
    """Tous les niveaux EU standards ont un mapping OrientIA."""
    for niv in ["NIV3", "NIV4", "NIV5", "NIV6", "NIV7", "NIV8"]:
        assert niv in NIVEAU_EU_TO_ORIENTIA
        assert NIVEAU_EU_TO_ORIENTIA[niv] is not None


def test_phase_mapping_master_vs_initial():
    """ADR-039 : NIV7 + NIV8 = phase master, les autres = initial."""
    assert NIVEAU_EU_TO_PHASE["NIV7"] == "master"
    assert NIVEAU_EU_TO_PHASE["NIV8"] == "master"
    assert NIVEAU_EU_TO_PHASE["NIV3"] == "initial"
    assert NIVEAU_EU_TO_PHASE["NIV4"] == "initial"
    assert NIVEAU_EU_TO_PHASE["NIV5"] == "initial"
    assert NIVEAU_EU_TO_PHASE["NIV6"] == "initial"


# --- Index ---


def test_index_by_fiche_groups_multiple_rows():
    rows = [
        {"Numero_Fiche": "RNCP1", "Codes_Rome_Code": "M1844"},
        {"Numero_Fiche": "RNCP1", "Codes_Rome_Code": "M1819"},
        {"Numero_Fiche": "RNCP2", "Codes_Rome_Code": "J1501"},
    ]
    idx = _index_by_fiche(rows)
    assert len(idx["RNCP1"]) == 2
    assert len(idx["RNCP2"]) == 1
    assert idx["RNCP1"][0]["Codes_Rome_Code"] == "M1844"


def test_index_by_fiche_ignores_rows_without_numero():
    rows = [{"Numero_Fiche": "", "Codes_Rome_Code": "X"}]
    assert _index_by_fiche(rows) == {}


# --- Normalisation ---


def test_normalize_active_master():
    fiche = normalize_rncp_certification(
        std_row=STD_ACTIVE_MASTER,
        voies=[
            {"Numero_Fiche": "RNCP99999", "Si_Jury": "Par candidature individuelle"},
            {"Numero_Fiche": "RNCP99999", "Si_Jury": "Par expérience"},
        ],
        rome=[
            {"Numero_Fiche": "RNCP99999", "Codes_Rome_Code": "M1844", "Codes_Rome_Libelle": "Analyste cybersécurité"},
        ],
        nsf=[
            {"Numero_Fiche": "RNCP99999", "Nsf_Code": "326", "Nsf_Intitule": "Informatique, traitement de l'information"},
        ],
        certificateurs=[
            {
                "Numero_Fiche": "RNCP99999",
                "Siret_Certificateur": "12345678900001",
                "Nom_Certificateur": "Université de la Cyber",
            }
        ],
    )
    assert fiche["source"] == "rncp"
    assert fiche["phase"] == "master"
    assert fiche["niveau"] == "bac+5"
    assert fiche["niveau_eu"] == "NIV7"
    assert fiche["actif"] is True
    assert fiche["intitule"] == "Manager en cybersécurité"
    assert "Par expérience" in fiche["voies_acces"]
    assert "Par candidature individuelle" in fiche["voies_acces"]
    assert fiche["codes_rome"][0]["code"] == "M1844"
    assert fiche["codes_nsf"][0]["code"] == "326"
    assert fiche["certificateurs"][0]["nom"] == "Université de la Cyber"


def test_normalize_strips_whitespace_intitule():
    std = {**STD_ACTIVE_MASTER, "Intitule": "  Intitulé avec espaces  "}
    fiche = normalize_rncp_certification(std, [], [], [], [])
    assert fiche["intitule"] == "Intitulé avec espaces"


def test_normalize_voies_acces_deduplicated_and_sorted():
    fiche = normalize_rncp_certification(
        STD_ACTIVE_MASTER,
        voies=[
            {"Numero_Fiche": "RNCP99999", "Si_Jury": "Apprentissage"},
            {"Numero_Fiche": "RNCP99999", "Si_Jury": "Apprentissage"},
            {"Numero_Fiche": "RNCP99999", "Si_Jury": "VAE"},
        ],
        rome=[], nsf=[], certificateurs=[],
    )
    assert fiche["voies_acces"] == ["Apprentissage", "VAE"]


def test_normalize_empty_lookups_give_empty_lists():
    fiche = normalize_rncp_certification(STD_ACTIVE_MASTER, [], [], [], [])
    assert fiche["voies_acces"] == []
    assert fiche["codes_rome"] == []
    assert fiche["codes_nsf"] == []
    assert fiche["certificateurs"] == []


def test_normalize_validation_partielle_bool():
    fiche = normalize_rncp_certification(
        {**STD_ACTIVE_MASTER, "Validation_Partielle": "Oui"}, [], [], [], []
    )
    assert fiche["validation_partielle"] is True


# --- Build certifications ---


def test_build_active_only_filters_inactive():
    parsed = {
        "standard": [STD_ACTIVE_MASTER, STD_INACTIVE_BAC],
        "voies_acces": [],
        "rome": [],
        "nsf": [],
        "certificateurs": [],
    }
    out = build_certifications(parsed, only_active=True)
    assert len(out) == 1
    assert out[0]["numero_fiche"] == "RNCP99999"


def test_build_include_inactive_keeps_both():
    parsed = {
        "standard": [STD_ACTIVE_MASTER, STD_INACTIVE_BAC],
        "voies_acces": [],
        "rome": [],
        "nsf": [],
        "certificateurs": [],
    }
    out = build_certifications(parsed, only_active=False)
    assert len(out) == 2
    assert {f["numero_fiche"] for f in out} == {"RNCP99999", "RNCP77777"}


def test_build_joins_relational_data():
    """La fiche doit recevoir ses voies + rome + nsf + certificateurs
    associés par Numero_Fiche."""
    parsed = {
        "standard": [STD_ACTIVE_MASTER, {**STD_ACTIVE_MASTER, "Numero_Fiche": "RNCP88888"}],
        "voies_acces": [
            {"Numero_Fiche": "RNCP99999", "Si_Jury": "Par expérience"},
            # RNCP88888 n'a pas de voie d'accès dans ce test
        ],
        "rome": [
            {"Numero_Fiche": "RNCP99999", "Codes_Rome_Code": "M1844", "Codes_Rome_Libelle": "X"},
            {"Numero_Fiche": "RNCP88888", "Codes_Rome_Code": "J1501", "Codes_Rome_Libelle": "Y"},
        ],
        "nsf": [],
        "certificateurs": [],
    }
    out = build_certifications(parsed, only_active=True)
    assert len(out) == 2
    by_numero = {f["numero_fiche"]: f for f in out}
    assert by_numero["RNCP99999"]["voies_acces"] == ["Par expérience"]
    assert by_numero["RNCP88888"]["voies_acces"] == []  # pas de voie associée
    assert by_numero["RNCP99999"]["codes_rome"][0]["code"] == "M1844"
    assert by_numero["RNCP88888"]["codes_rome"][0]["code"] == "J1501"


# --- fetch_latest_csv_zip_url ---


def test_fetch_latest_csv_zip_url_fallback_on_api_error():
    """Si data.gouv.fr répond KO, retourne l'URL par défaut (pas une exception)."""
    session = MagicMock()
    session.get.side_effect = Exception("network down")
    url = fetch_latest_csv_zip_url(session=session)
    assert url.startswith("https://static.data.gouv.fr/")


def test_fetch_latest_csv_zip_url_picks_csv_resource():
    session = MagicMock()
    resp = MagicMock()
    resp.json.return_value = {
        "resources": [
            {"title": "export-fiches-rncp-v4-1-xxx", "format": "zip", "url": "http://WRONG"},
            {"title": "export-fiches-csv-2026-04-23.zip", "format": "zip", "url": "http://CORRECT"},
            {"title": "export-fiches-rs-v4-1-yyy", "format": "zip", "url": "http://WRONG2"},
        ]
    }
    resp.raise_for_status = MagicMock()
    session.get.return_value = resp
    url = fetch_latest_csv_zip_url(session=session)
    assert url == "http://CORRECT"


# --- Integration (optional — skip si ZIP absent) ---


@pytest.mark.integration
def test_real_zip_parses_and_yields_active_certifs():
    """Test integration léger sur le ZIP réel (si présent localement).

    N'exécute pas en CI normale (marker `integration` à skipper).
    Utile pour valider qu'une ingestion future ne casse pas le schéma.
    """
    zip_candidates = sorted(Path("data/raw/rncp").glob("export-fiches-csv-*.zip"))
    if not zip_candidates:
        pytest.skip("Pas de ZIP RNCP local — run `python -m src.collect.rncp` pour downloader.")

    from src.collect.rncp import parse_rncp_zip

    parsed = parse_rncp_zip(zip_candidates[-1])
    assert parsed["standard"], "Standard CSV ne doit pas être vide"
    assert any(r.get("Actif") == "ACTIVE" for r in parsed["standard"])
    certifs = build_certifications(parsed, only_active=True)
    assert len(certifs) > 1000, f"Attendu >1000 certifs actives, reçu {len(certifs)}"
    # Sanity schema
    first = certifs[0]
    required = {"source", "phase", "numero_fiche", "intitule", "niveau_eu", "actif"}
    assert required.issubset(first.keys())
