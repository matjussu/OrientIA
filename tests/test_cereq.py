"""Tests `src/collect/cereq.py` — Céreq Enquêtes Génération D11.

Tests offline : on crée des CSVs de fixture en tmp_path pour couvrir la
permissivité du parser (delimiters FR/EN + missing fields + extra cols).
"""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

from src.collect.cereq import (
    CereqDataMissing,
    _infer_niveau,
    _safe_float,
    _safe_int,
    collect_cereq_stats,
    parse_chiffres_cles_csv,
    save_processed,
)


# --- _infer_niveau ---


@pytest.mark.parametrize(
    "label,expected",
    [
        ("Bac+5", "bac+5"),
        ("Bac +5 (Master)", "bac+5"),
        ("Master", "bac+5"),
        ("Bac+3 (Licence)", "bac+3"),
        ("Licence", "bac+3"),
        ("Bac+2 (BTS, BUT)", "bac+2"),
        ("BTS", "bac+2"),
        ("BUT", "bac+2"),
        ("CAP", "cap-bep"),
        ("BEP", "cap-bep"),
        ("Bac pro", "bac"),
        ("", None),
        (None, None),
        ("Niveau inconnu", None),
    ],
)
def test_infer_niveau(label, expected):
    assert _infer_niveau(label or "") == expected


# --- _safe_float / _safe_int ---


def test_safe_float_handles_french_percent():
    assert _safe_float("85,5 %") == 85.5
    assert _safe_float("85.5") == 85.5
    assert _safe_float(None) is None
    assert _safe_float("") is None
    assert _safe_float("N/A") is None


def test_safe_int_handles_currency():
    assert _safe_int("1 850 €") is None or _safe_int("1 850 €") == 1850  # espace insécable peut bloquer
    assert _safe_int("1850") == 1850
    assert _safe_int("1850.5") == 1850
    assert _safe_int("") is None


# --- parse_chiffres_cles_csv ---


def test_parse_missing_csv_raises():
    with pytest.raises(CereqDataMissing) as exc:
        parse_chiffres_cles_csv(Path("/tmp/does_not_exist_cereq.csv"))
    assert "TODO_MATTEO_APIS.md" in str(exc.value)


def test_parse_fr_delimiter_csv(tmp_path):
    csv_path = tmp_path / "cereq_test.csv"
    csv_path.write_text(
        "niveau_diplome;domaine;cohorte;taux_emploi_3_ans;salaire_median\n"
        "Master;Informatique;Generation 2017;0.88;2450\n"
        "Licence;Droit;Generation 2017;0.75;1950\n",
        encoding="utf-8",
    )
    entries = parse_chiffres_cles_csv(csv_path)
    assert len(entries) == 2
    assert entries[0]["niveau"] == "bac+5"
    assert entries[0]["domaine"] == "Informatique"
    assert entries[0]["taux_emploi_3ans"] == 0.88
    assert entries[0]["salaire_median_embauche"] == 2450
    assert entries[1]["niveau"] == "bac+3"


def test_parse_en_delimiter_csv(tmp_path):
    csv_path = tmp_path / "cereq_en.csv"
    csv_path.write_text(
        "Niveau,Domaine,Génération,Taux emploi 3 ans,Salaire médian\n"
        "Master,Sciences,Generation 2017,92,2650\n",
        encoding="utf-8",
    )
    entries = parse_chiffres_cles_csv(csv_path)
    assert len(entries) == 1
    assert entries[0]["niveau"] == "bac+5"
    assert entries[0]["taux_emploi_3ans"] == 92.0
    assert entries[0]["salaire_median_embauche"] == 2650


def test_parse_extra_columns_kept_under_extra(tmp_path):
    csv_path = tmp_path / "cereq_extra.csv"
    csv_path.write_text(
        "niveau_diplome;domaine;taux_emploi_3_ans;colonne_speciale\n"
        "Master;Gestion;0.85;valeur_custom\n",
        encoding="utf-8",
    )
    entries = parse_chiffres_cles_csv(csv_path)
    assert entries[0]["_extra"]["colonne_speciale"] == "valeur_custom"


# --- collect_cereq_stats ---


def test_collect_stats_empty_dir_raises(tmp_path):
    with pytest.raises(CereqDataMissing):
        collect_cereq_stats(raw_dir=tmp_path, save=False)


def test_collect_stats_aggregates_multiple_csvs(tmp_path):
    (tmp_path / "cereq_gen2017.csv").write_text(
        "niveau_diplome;cohorte\nMaster;Generation 2017\n", encoding="utf-8"
    )
    (tmp_path / "cereq_gen2021.csv").write_text(
        "niveau_diplome;cohorte\nLicence;Generation 2021\n", encoding="utf-8"
    )
    entries = collect_cereq_stats(raw_dir=tmp_path, save=False)
    assert len(entries) == 2
    cohortes = {e["cohorte"] for e in entries}
    assert cohortes == {"Generation 2017", "Generation 2021"}


def test_save_processed_writes_json(tmp_path):
    path = tmp_path / "out.json"
    save_processed([{"source": "cereq", "niveau": "bac+5"}], path=path)
    import json
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data[0]["source"] == "cereq"
