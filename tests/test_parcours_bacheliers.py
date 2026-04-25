"""Tests `src/collect/parcours_bacheliers.py` — MESRI parcours licence."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from src.collect.parcours_bacheliers import (
    _to_float,
    _to_int,
    aggregate_records,
    build_corpus,
    build_text,
    compute_rates,
    load_raw,
    normalize_to_corpus,
    parse_row,
    save_corpus,
    save_granular,
)


SAMPLE_ROW = [
    "DSA",  # 0 Id Grande discipline
    "Droit, gestion, économie, AES",  # 1 Grande discipline
    "01",  # 2 Id Discipline
    "Droit, sciences politiques",  # 3 Discipline
    "36",  # 4 Id Secteur
    "Sciences juridiques",  # 5 Secteur
    "1",  # 6 Id Bac
    "BAC L",  # 7 Bac
    "R0",  # 8 Id Age
    "A l'heure ou en avance",  # 9 Age
    "1",  # 10 Id Sexe
    "Homme",  # 11 Sexe
    "A",  # 12 Id Mention
    "Très bien",  # 13 Mention
    "2014",  # 14 Cohorte L1
    "40.0",  # 15 Effectif L1
    "32.0",  # 16 Passage L2 1an
    "3.0",  # 17 Redoublement
    "2.0",  # 18 Passage L2 2ans
    "34.0",  # 19 Passage L2 1ou2
    "0.0",  # 20 Reor DUT 1an
    "1.0",  # 21 Reor DUT 2ans
    "1.0",  # 22 Reor DUT 1ou2
    "2012",  # 23 Cohorte Licence
    "24.0",  # 24 Effectif Licence
    "18.0",  # 25 Obtention 3ans
    "3.0",  # 26 Obtention 4ans
    "21.0",  # 27 Obtention 3ou4
]


# --- _to_float / _to_int ---


class TestToFloat:
    def test_basic(self):
        assert _to_float("3.5") == 3.5

    def test_comma_decimal(self):
        assert _to_float("3,5") == 3.5

    def test_empty(self):
        assert _to_float("") is None

    def test_whitespace(self):
        assert _to_float("  ") is None

    def test_invalid(self):
        assert _to_float("abc") is None


def test_to_int():
    assert _to_int("2014") == 2014
    assert _to_int("3.5") == 3
    assert _to_int("") is None


# --- parse_row ---


class TestParseRow:
    def test_full_row(self):
        r = parse_row(SAMPLE_ROW)
        assert r["grande_discipline"] == "Droit, gestion, économie, AES"
        assert r["bac"] == "BAC L"
        assert r["mention"] == "Très bien"
        assert r["sexe"] == "Homme"
        assert r["cohorte_l1_l2"] == 2014
        assert r["effectif_l1"] == 40.0
        assert r["passage_l2_1an"] == 32.0
        assert r["redoublement_l1"] == 3.0
        assert r["cohorte_licence"] == 2012
        assert r["effectif_licence"] == 24.0
        assert r["obtention_3ans"] == 18.0

    def test_handles_empty_cells(self):
        row = list(SAMPLE_ROW)
        row[15] = ""  # effectif_l1 vide
        row[25] = ""
        r = parse_row(row)
        assert r["effectif_l1"] is None
        assert r["obtention_3ans"] is None
        assert r["bac"] == "BAC L"  # le reste passe


# --- compute_rates ---


class TestComputeRates:
    def test_full_rates(self):
        record = parse_row(SAMPLE_ROW)
        rates = compute_rates(record)
        # 32 / 40 = 80%
        assert rates["passage_l2_1an_pct"] == 80.0
        # 34 / 40 = 85%
        assert rates["passage_l2_1ou2ans_pct"] == 85.0
        # 3 / 40 = 7.5%
        assert rates["redoublement_l1_pct"] == 7.5
        # 18 / 24 = 75%
        assert rates["obtention_3ans_pct"] == 75.0

    def test_zero_effectif_skips(self):
        record = parse_row(SAMPLE_ROW)
        record["effectif_l1"] = 0
        record["effectif_licence"] = 0
        rates = compute_rates(record)
        assert rates == {}

    def test_none_field_skipped(self):
        record = parse_row(SAMPLE_ROW)
        record["passage_l2_1an"] = None
        rates = compute_rates(record)
        assert "passage_l2_1an_pct" not in rates
        # mais les autres taux L1 sont calculés
        assert "redoublement_l1_pct" in rates


# --- aggregate_records ---


def _row_with(grande, bac, mention, eff_l1=10.0, passage_1an=5.0):
    """Builder pour récords agrégeables avec dimensions personnalisables."""
    row = list(SAMPLE_ROW)
    row[1] = grande
    row[7] = bac
    row[13] = mention
    row[15] = str(eff_l1)
    row[16] = str(passage_1an)
    return parse_row(row)


def test_aggregate_groups_by_three_keys():
    a = _row_with("DSA", "BAC L", "Très bien")
    b = _row_with("DSA", "BAC L", "Très bien")
    c = _row_with("DSA", "BAC L", "Bien")
    out = aggregate_records([a, b, c])
    assert len(out) == 2
    very_good = [o for o in out if o["mention"] == "Très bien"][0]
    assert very_good["n_rows"] == 2
    assert very_good["effectif_l1"] == 20.0
    assert very_good["passage_l2_1an"] == 10.0


def test_aggregate_recomputes_rates():
    a = _row_with("X", "BAC S", "Bien", eff_l1=10.0, passage_1an=8.0)
    b = _row_with("X", "BAC S", "Bien", eff_l1=20.0, passage_1an=10.0)
    out = aggregate_records([a, b])
    assert len(out) == 1
    # 18 / 30 = 60%
    assert out[0]["taux"]["passage_l2_1an_pct"] == 60.0


def test_aggregate_sorted_output():
    rows = [
        _row_with("Z", "BAC L", "Bien"),
        _row_with("A", "BAC S", "Très bien"),
        _row_with("A", "BAC L", "Bien"),
    ]
    out = aggregate_records(rows)
    keys = [(o["grande_discipline"], o["bac"], o["mention"]) for o in out]
    assert keys == sorted(keys)


# --- build_text ---


class TestBuildText:
    def test_complete(self):
        record = parse_row(SAMPLE_ROW)
        agg = aggregate_records([record])[0]
        text = build_text(agg)
        assert "Parcours licence en Droit, gestion, économie, AES" in text
        assert "Bachelier : BAC L" in text
        assert "Mention au bac : Très bien" in text
        assert "Cohorte 2014 (L1→L2)" in text
        assert "80.0% passent en L2 en 1 an" in text
        assert "Cohorte 2012 (suivi licence)" in text
        assert "75.0% obtiennent la licence en 3 ans" in text

    def test_skip_zero_effectif(self):
        record = parse_row(SAMPLE_ROW)
        record["effectif_l1"] = 0
        record["effectif_licence"] = 0
        agg = aggregate_records([record])[0]
        text = build_text(agg)
        assert "Cohorte" not in text


# --- normalize_to_corpus / build_corpus ---


def test_normalize_to_corpus_id():
    agg = aggregate_records([parse_row(SAMPLE_ROW)])[0]
    rec = normalize_to_corpus(agg)
    assert rec["id"].startswith("parcours:")
    assert rec["domain"] == "parcours_bacheliers"
    assert rec["source"] == "mesri_parcours_bacheliers_licence"
    assert rec["bac"] == "BAC L"
    assert rec["mention"] == "Très bien"
    assert "text" in rec
    assert isinstance(rec["taux"], dict)


def test_build_corpus_round_trip():
    rows = [parse_row(SAMPLE_ROW)]
    aggs = aggregate_records(rows)
    corpus = build_corpus(aggs)
    assert len(corpus) == 1
    assert corpus[0]["domain"] == "parcours_bacheliers"


def test_save_granular_round_trip(tmp_path):
    records = [parse_row(SAMPLE_ROW)]
    target = tmp_path / "g.json"
    save_granular(records, path=target)
    loaded = json.loads(target.read_text(encoding="utf-8"))
    assert loaded == records


def test_save_corpus_round_trip(tmp_path):
    rec = normalize_to_corpus(aggregate_records([parse_row(SAMPLE_ROW)])[0])
    target = tmp_path / "c.json"
    save_corpus([rec], path=target)
    assert json.loads(target.read_text(encoding="utf-8")) == [rec]


# --- load_raw ---


def test_load_raw_from_synthetic_csv(tmp_path):
    headers = (
        "Id Grande discipline;Grande discipline;Id Discipline;Discipline;"
        "Id Secteur disciplinaire;Secteur disciplinaire;Id Série ou type de Bac;"
        "Série ou type de Bac;Id Âge au bac;Âge au bac;Id Sexe;Sexe;"
        "Id Mention au Bac;Mention au Bac;"
        "Année de cohorte des données sur le passage entre L1 et L2;"
        "Effectif de néobacheliers de la cohorte;Passage en L2 en 1 an;"
        "Redoublement en L1;Passage en L2 en 2 ans;Passage en L2 en 1 ou 2 ans;"
        "Réorientation en DUT en 1 an;Réorientation en DUT en 2 ans;"
        "Réorientation en DUT en 1 ou 2 ans;"
        "Année de cohorte des données sur la réussite en licence;"
        "Effectif de néobacheliers de la cohorte;Obtention de la licence en 3 ans;"
        "Obtention de la licence en 4 ans;Obtention de la licence en 3 ou 4 ans"
    )
    body = ";".join(SAMPLE_ROW)
    target = tmp_path / "test.csv"
    target.write_text(headers + "\n" + body + "\n", encoding="utf-8-sig")
    records = load_raw(path=target)
    assert len(records) == 1
    assert records[0]["bac"] == "BAC L"


def test_load_raw_skips_short_rows(tmp_path):
    headers = ";".join([f"col{i}" for i in range(28)])
    valid = ";".join(SAMPLE_ROW)
    short = "DSA;X"  # too short
    target = tmp_path / "test.csv"
    target.write_text(headers + "\n" + valid + "\n" + short + "\n", encoding="utf-8-sig")
    records = load_raw(path=target)
    assert len(records) == 1
