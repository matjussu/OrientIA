"""Tests `src/collect/insee_emploi.py` — D14 INSEE BTS.

Tests scaffold — l'agrégation live sur ~2.5M rows CSV INSEE est hors périmètre
CI (poids fichier + compute). On teste :
- build_pcs_index (pur logic)
- save_processed (IO)
- aggregate_salaries_by_pcs_age sur un CSV fixture minimal in-memory
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.collect.insee_emploi import (
    InseeDataMissing,
    aggregate_salaries_by_pcs_age,
    build_pcs_index,
    collect_insee_salaries,
    save_processed,
)


def test_missing_csv_raises_explicit_error(tmp_path):
    fake = tmp_path / "missing.csv"
    with pytest.raises(InseeDataMissing):
        collect_insee_salaries(csv_path=fake, download_if_missing=False)


def test_aggregate_simple_csv(tmp_path):
    csv_path = tmp_path / "bts.csv"
    csv_path.write_text(
        "PCS;AGE_TR;SNHM\n"
        "372a;20-23;18.50\n"
        "372a;20-23;19.00\n"
        "372a;20-23;20.00\n"
        "372a;28-31;25.00\n"
        "372a;28-31;27.00\n"
        "543a;20-23;14.00\n",
        encoding="utf-8",
    )
    entries = aggregate_salaries_by_pcs_age(csv_path)
    # 3 groupes distincts (372a×20-23, 372a×28-31, 543a×20-23)
    assert len(entries) == 3
    pcs_20_23 = next(e for e in entries if e["code_pcs"] == "372a" and e["tranche_age"] == "20-23")
    assert pcs_20_23["n_salaries"] == 3
    # median de [18.50, 19.00, 20.00] = 19.00
    assert pcs_20_23["salaire_median"] == 19.00
    # mean = (18.5 + 19 + 20) / 3 ≈ 19.17
    assert 19.16 <= pcs_20_23["salaire_mean"] <= 19.17


def test_aggregate_missing_columns_raises(tmp_path):
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text("other;cols;here\n1;2;3\n", encoding="utf-8")
    with pytest.raises(ValueError) as exc:
        aggregate_salaries_by_pcs_age(csv_path)
    assert "Colonnes manquantes" in str(exc.value)


def test_build_pcs_index_nests_by_pcs_and_age():
    entries = [
        {"code_pcs": "372a", "tranche_age": "20-23", "salaire_median": 19.0},
        {"code_pcs": "372a", "tranche_age": "28-31", "salaire_median": 26.0},
        {"code_pcs": "543a", "tranche_age": "20-23", "salaire_median": 14.0},
    ]
    index = build_pcs_index(entries)
    assert index["372a"]["20-23"]["salaire_median"] == 19.0
    assert index["372a"]["28-31"]["salaire_median"] == 26.0
    assert index["543a"]["20-23"]["salaire_median"] == 14.0
    assert "28-31" not in index["543a"]


def test_build_pcs_index_ignores_entries_without_pcs():
    entries = [{"code_pcs": "", "tranche_age": "20-23"}]
    assert build_pcs_index(entries) == {}


def test_save_processed_writes_json(tmp_path):
    path = tmp_path / "out.json"
    save_processed([{"code_pcs": "372a", "tranche_age": "20-23"}], path=path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data[0]["code_pcs"] == "372a"


def test_collect_insee_salaries_aggregates_and_saves(tmp_path):
    csv_path = tmp_path / "bts.csv"
    csv_path.write_text(
        "PCS;AGE_TR;SNHM\n"
        "372a;20-23;18.50\n"
        "372a;20-23;19.50\n",
        encoding="utf-8",
    )
    out_path = tmp_path / "out.json"
    # On override PROCESSED_PATH via save_processed direct — fonction collect
    # sauve par défaut dans data/processed/. On teste save puis aggregate
    # séparément pour éviter d'écrire dans le vrai data/processed pendant les tests.
    entries = aggregate_salaries_by_pcs_age(csv_path)
    save_processed(entries, path=out_path)
    assert out_path.exists()
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["code_pcs"] == "372a"
