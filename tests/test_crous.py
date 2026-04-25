"""Tests `src/collect/crous.py` — logements + restaurants universitaires."""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from src.collect.crous import (
    _parse_house_services,
    _parse_opening_pattern,
    _region_from_filename,
    _strip_html,
    iter_restos,
    normalize_all_logements,
    normalize_all_restos,
    normalize_logement,
    normalize_resto,
    save_logements,
    save_restos,
)


# --- Utilitaires ---


class TestStripHtml:
    def test_basic_tags_removed(self):
        assert _strip_html("<p>Bonjour <b>Matteo</b></p>") == "Bonjour Matteo"

    def test_none_returns_empty(self):
        assert _strip_html(None) == ""

    def test_collapses_whitespace(self):
        assert _strip_html("  <p>a  </p>  <br>  b   ") == "a b"


class TestParseHouseServices:
    def test_valid_json_returns_list(self):
        raw = '{"house_service": ["Parking", "Wifi"]}'
        assert _parse_house_services(raw) == ["Parking", "Wifi"]

    def test_empty_returns_empty(self):
        assert _parse_house_services("") == []
        assert _parse_house_services(None) == []

    def test_invalid_json_returns_empty(self):
        assert _parse_house_services("not-json") == []

    def test_list_payload_returns_list(self):
        assert _parse_house_services('["Parking", "Garage"]') == ["Parking", "Garage"]


class TestParseOpeningPattern:
    def test_standard_week_pattern(self):
        result = _parse_opening_pattern("110,110,110,110,110,000,000")
        assert result["lundi"] == "matin+midi"
        assert result["samedi"] == "ferme"
        assert result["dimanche"] == "ferme"

    def test_full_open(self):
        result = _parse_opening_pattern("111,111,111,111,111,111,111")
        assert result["lundi"] == "matin+midi+soir"

    def test_empty_returns_empty(self):
        assert _parse_opening_pattern("") == {}
        assert _parse_opening_pattern(None) == {}

    def test_malformed_triplet_skipped(self):
        result = _parse_opening_pattern("111,xyz,000,000,000,000,000")
        assert "mardi" not in result
        assert result["lundi"] == "matin+midi+soir"


class TestRegionFromFilename:
    def test_simple_region(self):
        assert _region_from_filename(Path("resto_paris.xml")) == "paris"

    def test_compound_region_with_dot(self):
        assert _region_from_filename(Path("resto_aix.marseille.xml")) == "aix-marseille"

    def test_triple_compound(self):
        assert _region_from_filename(Path("resto_nancy.metz.xml")) == "nancy-metz"


# --- Logements ---


FEATURE_SAMPLE = {
    "type": "Feature",
    "geometry": {"type": "Point", "coordinates": [2.795, 50.28]},
    "properties": {
        "id": 492,
        "title": "Résidence de l'Artois",
        "address": "12 rue Raoul François 62000 ARRAS",
        "zone": "Arras",
        "regions": "Hauts-de-France",
        "phone": "03 74 09 13 26",
        "mail": "residence.arras@crous-lille.fr",
        "interneturl": "https://www.crous-lille.fr/",
        "bookingurl": "https://trouverunlogement.lescrous.fr/",
        "appointmenturl": "https://mesrdv.etudiant.gouv.fr/fr",
        "house_services": '{"house_service": ["Parking", "Kitchenette"]}',
        "infos": "<p>Résidence ouverte</p>",
        "short_desc": "12 rue Raoul François - 62000 ARRAS",
    },
}


class TestNormalizeLogement:
    def test_core_fields_extracted(self):
        r = normalize_logement(FEATURE_SAMPLE)
        assert r["id"] == 492
        assert r["nom"] == "Résidence de l'Artois"
        assert r["zone"] == "Arras"
        assert r["region"] == "Hauts-de-France"
        assert r["telephone"] == "03 74 09 13 26"
        assert r["latitude"] == 50.28
        assert r["longitude"] == 2.795

    def test_services_parsed(self):
        r = normalize_logement(FEATURE_SAMPLE)
        assert r["services"] == ["Parking", "Kitchenette"]

    def test_description_html_stripped(self):
        r = normalize_logement(FEATURE_SAMPLE)
        assert r["description"] == "Résidence ouverte"

    def test_missing_geometry_handled(self):
        feat = {"geometry": None, "properties": {"id": 1, "title": "X"}}
        r = normalize_logement(feat)
        assert r["latitude"] is None
        assert r["longitude"] is None

    def test_address_fallback_on_short_desc(self):
        feat = {
            "geometry": {"coordinates": [0, 0]},
            "properties": {"short_desc": "1 rue Test", "address": ""},
        }
        r = normalize_logement(feat)
        assert r["adresse"] == "1 rue Test"


def test_normalize_all_logements_handles_batch():
    features = [FEATURE_SAMPLE, FEATURE_SAMPLE]
    records = normalize_all_logements(features)
    assert len(records) == 2
    assert records[0]["id"] == 492


def test_save_logements_round_trip(tmp_path):
    records = [{"id": 1, "nom": "Test"}]
    target = tmp_path / "out.json"
    save_logements(records, path=target)
    assert json.loads(target.read_text(encoding="utf-8")) == records


# --- Restos ---


RESTO_XML = """
<resto id="r961" title="Cafétéria Le Gingko"
       opening="110,110,110,110,110,000,000" closing="0"
       short_desc="Campus Agroparc 120 places"
       lat="43.9118541" lon="4.8896321"
       zone="Avignon" zone2="" type="Cafétéria">
  <infos><![CDATA[<p>Ouvert 8h-16h</p>]]></infos>
  <contact><![CDATA[<p>301 rue Baruch Avignon</p>]]></contact>
</resto>
"""


class TestNormalizeResto:
    def setup_method(self):
        self.elem = ET.fromstring(RESTO_XML)

    def test_core_attribs(self):
        r = normalize_resto(self.elem)
        assert r["id"] == "r961"
        assert r["nom"] == "Cafétéria Le Gingko"
        assert r["type"] == "Cafétéria"
        assert r["zone"] == "Avignon"
        assert r["latitude"] == pytest.approx(43.9118541)
        assert r["longitude"] == pytest.approx(4.8896321)

    def test_horaires_parsed(self):
        r = normalize_resto(self.elem)
        assert r["horaires_hebdo"]["lundi"] == "matin+midi"
        assert r["horaires_hebdo"]["samedi"] == "ferme"

    def test_infos_html_stripped(self):
        r = normalize_resto(self.elem)
        assert "Ouvert 8h-16h" in r["infos"]
        assert "<p>" not in r["infos"]

    def test_closing_flag_false_by_default(self):
        r = normalize_resto(self.elem)
        assert r["ferme_actuellement"] is False


def test_iter_restos_walks_directory(tmp_path):
    xml_a = tmp_path / "resto_paris.xml"
    xml_b = tmp_path / "resto_lyon.xml"
    xml_a.write_text(f"<root>{RESTO_XML}</root>", encoding="utf-8")
    xml_b.write_text(
        f"<root>{RESTO_XML}{RESTO_XML.replace('r961', 'r999')}</root>",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("x", encoding="utf-8")

    pairs = list(iter_restos(restos_dir=tmp_path))
    assert len(pairs) == 3
    assert {region for region, _ in pairs} == {"paris", "lyon"}


def test_normalize_all_restos_tags_region(tmp_path):
    xml = tmp_path / "resto_paris.xml"
    xml.write_text(f"<root>{RESTO_XML}</root>", encoding="utf-8")
    records = normalize_all_restos(restos_dir=tmp_path)
    assert len(records) == 1
    assert records[0]["region_source"] == "paris"
    assert records[0]["id"] == "r961"


def test_save_restos_round_trip(tmp_path):
    records = [{"id": "r1", "nom": "Test"}]
    target = tmp_path / "restos.json"
    save_restos(records, path=target)
    assert json.loads(target.read_text(encoding="utf-8")) == records
