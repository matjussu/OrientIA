"""Tests `src/collect/ideo_fiches.py` — fiches métiers ONISEP éditorialisées."""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from src.collect.ideo_fiches import (
    _extract_id_libelle_list,
    _extract_niveau_acces,
    _extract_romes,
    _extract_sources,
    _extract_synonymes,
    _strip_html,
    _text_or_empty,
    build_rome_to_metiers_index,
    load_metiers,
    normalize_all_metiers,
    normalize_metier,
    save_processed,
)


METIER_FULL_XML = """
<metier>
    <identifiant>MET.7937</identifiant>
    <nom_metier>décorateur/trice sur verre</nom_metier>
    <libelle_feminin>décoratrice sur verre</libelle_feminin>
    <libelle_masculin>décorateur sur verre</libelle_masculin>
    <synonymes>
        <synonyme>
            <nom_metier>verrier/ère décorateur/trice</nom_metier>
            <libelle_feminin>verrière décoratrice</libelle_feminin>
        </synonyme>
        <synonyme>
            <nom_metier>graveur sur verre</nom_metier>
        </synonyme>
    </synonymes>
    <romesV3>
        <romeV3>B1302</romeV3>
        <romeV3>B1303</romeV3>
    </romesV3>
    <accroche_metier><![CDATA[<p>Crée des motifs sur verre.</p>]]></accroche_metier>
    <format_court><![CDATA[<p>Description longue</p><h4>Durée</h4><p>2 ans CAP</p>]]></format_court>
    <nature_travail><![CDATA[<p>Travail manuel minutieux</p>]]></nature_travail>
    <acces_metier/>
    <condition_travail/>
    <vie_professionnelle/>
    <competences/>
    <niveau_acces_min>
        <id>REF.413</id>
        <libelle>CAP ou équivalent</libelle>
    </niveau_acces_min>
    <formations_min_requise>
        <formation_min_requise>
            <id>FOR.5333</id>
            <libelle>CAP arts et techniques du verre</libelle>
        </formation_min_requise>
        <formation_min_requise>
            <id>FOR.2214</id>
            <libelle>BMA verrier décorateur</libelle>
        </formation_min_requise>
    </formations_min_requise>
    <statuts>
        <statut>
            <id>T-ITM.9</id>
            <libelle>salarié</libelle>
        </statut>
        <statut>
            <id>T-ITM.2</id>
            <libelle>artisan</libelle>
        </statut>
    </statuts>
    <centres_interet>
        <centre_interet id="T-IDEO2.4829" libelle="je rêve d'un métier artistique"/>
        <centre_interet id="T-IDEO2.4806" libelle="je veux travailler de mes mains"/>
    </centres_interet>
    <secteurs_activite>
        <secteur_activite id="T-IDEO2.4830" libelle="Artisanat d'art"/>
    </secteurs_activite>
    <metiers_associes/>
    <sources_numeriques>
        <source>
            <valeur>https://www.institut-savoirfaire.fr/</valeur>
            <commentaire>Institut pour les savoirs-faire français</commentaire>
        </source>
    </sources_numeriques>
</metier>
"""


# --- Utilitaires ---


class TestStripHtml:
    def test_basic(self):
        assert _strip_html("<p>Bonjour <b>Matteo</b></p>") == "Bonjour Matteo"

    def test_none(self):
        assert _strip_html(None) == ""

    def test_collapses_ws(self):
        assert _strip_html("  <p>a</p>\n\n<br>\tb  ") == "a b"


class TestTextOrEmpty:
    def test_found(self):
        el = ET.fromstring("<p><x>hello</x></p>")
        assert _text_or_empty(el, "x") == "hello"

    def test_missing(self):
        el = ET.fromstring("<p><x>hello</x></p>")
        assert _text_or_empty(el, "y") == ""

    def test_elem_none(self):
        assert _text_or_empty(None, "x") == ""

    def test_empty_tag(self):
        el = ET.fromstring("<p><x/></p>")
        assert _text_or_empty(el, "x") == ""


# --- Extracteurs ---


class TestExtractSynonymes:
    def test_multiple(self):
        m = ET.fromstring(METIER_FULL_XML)
        syns = _extract_synonymes(m)
        assert syns == ["verrier/ère décorateur/trice", "graveur sur verre"]

    def test_empty(self):
        m = ET.fromstring("<metier><synonymes/></metier>")
        assert _extract_synonymes(m) == []

    def test_missing_container(self):
        m = ET.fromstring("<metier></metier>")
        assert _extract_synonymes(m) == []


class TestExtractRomes:
    def test_multiple(self):
        m = ET.fromstring(METIER_FULL_XML)
        assert _extract_romes(m) == ["B1302", "B1303"]

    def test_empty_container(self):
        m = ET.fromstring("<metier><romesV3/></metier>")
        assert _extract_romes(m) == []


class TestExtractIdLibelleList:
    def test_formations(self):
        m = ET.fromstring(METIER_FULL_XML)
        items = _extract_id_libelle_list(
            m, "formations_min_requise", "formation_min_requise"
        )
        assert items == [
            {"id": "FOR.5333", "libelle": "CAP arts et techniques du verre"},
            {"id": "FOR.2214", "libelle": "BMA verrier décorateur"},
        ]

    def test_statuts(self):
        m = ET.fromstring(METIER_FULL_XML)
        items = _extract_id_libelle_list(m, "statuts", "statut")
        assert {i["libelle"] for i in items} == {"salarié", "artisan"}

    def test_centres_interet_from_attributes(self):
        m = ET.fromstring(METIER_FULL_XML)
        items = _extract_id_libelle_list(m, "centres_interet", "centre_interet")
        assert len(items) == 2
        assert items[0]["id"] == "T-IDEO2.4829"
        assert items[0]["libelle"] == "je rêve d'un métier artistique"


class TestExtractNiveauAcces:
    def test_present(self):
        m = ET.fromstring(METIER_FULL_XML)
        nv = _extract_niveau_acces(m)
        assert nv == {"id": "REF.413", "libelle": "CAP ou équivalent"}

    def test_missing(self):
        m = ET.fromstring("<metier></metier>")
        assert _extract_niveau_acces(m) is None

    def test_empty_tag(self):
        m = ET.fromstring("<metier><niveau_acces_min/></metier>")
        assert _extract_niveau_acces(m) is None


class TestExtractSources:
    def test_with_commentaire(self):
        m = ET.fromstring(METIER_FULL_XML)
        srcs = _extract_sources(m)
        assert srcs == [
            {
                "url": "https://www.institut-savoirfaire.fr/",
                "commentaire": "Institut pour les savoirs-faire français",
            }
        ]


# --- Normalize + Index + Save ---


class TestNormalizeMetier:
    def test_full_roundtrip(self):
        m = ET.fromstring(METIER_FULL_XML)
        r = normalize_metier(m)
        assert r["identifiant"] == "MET.7937"
        assert r["nom_metier"] == "décorateur/trice sur verre"
        assert r["libelle_feminin"] == "décoratrice sur verre"
        assert r["codes_rome_v3"] == ["B1302", "B1303"]
        assert r["niveau_acces_min"]["libelle"] == "CAP ou équivalent"
        assert len(r["synonymes"]) == 2
        assert len(r["formations_min_requise"]) == 2
        assert "Crée des motifs sur verre" in r["accroche"]
        assert "Durée" in r["format_court"]
        assert r["nature_travail"] == "Travail manuel minutieux"
        assert r["condition_travail"] == ""

    def test_minimal(self):
        minimal = (
            "<metier>"
            "<identifiant>MET.1</identifiant>"
            "<nom_metier>testeur</nom_metier>"
            "</metier>"
        )
        r = normalize_metier(ET.fromstring(minimal))
        assert r["identifiant"] == "MET.1"
        assert r["nom_metier"] == "testeur"
        assert r["codes_rome_v3"] == []
        assert r["synonymes"] == []
        assert r["niveau_acces_min"] is None
        assert r["sources_numeriques"] == []


def test_normalize_all_metiers_batch():
    m1 = ET.fromstring(METIER_FULL_XML)
    m2 = ET.fromstring(METIER_FULL_XML.replace("MET.7937", "MET.0002"))
    records = normalize_all_metiers([m1, m2])
    assert len(records) == 2
    assert records[1]["identifiant"] == "MET.0002"


def test_build_rome_to_metiers_index():
    records = [
        {"nom_metier": "métier A", "codes_rome_v3": ["B1302", "B1303"]},
        {"nom_metier": "métier B", "codes_rome_v3": ["B1302"]},
        {"nom_metier": "métier C", "codes_rome_v3": []},
    ]
    idx = build_rome_to_metiers_index(records)
    assert set(idx.keys()) == {"B1302", "B1303"}
    assert set(idx["B1302"]) == {"métier A", "métier B"}
    assert idx["B1303"] == ["métier A"]


def test_load_metiers_from_file(tmp_path):
    xml_file = tmp_path / "fiches.xml"
    xml_file.write_text(
        f"<metiers>{METIER_FULL_XML}{METIER_FULL_XML.replace('MET.7937', 'MET.0042')}</metiers>",
        encoding="utf-8",
    )
    metiers = load_metiers(path=xml_file)
    assert len(metiers) == 2


def test_save_processed_round_trip(tmp_path):
    records = [{"identifiant": "MET.1", "nom_metier": "test"}]
    target = tmp_path / "out.json"
    save_processed(records, path=target)
    assert json.loads(target.read_text(encoding="utf-8")) == records
