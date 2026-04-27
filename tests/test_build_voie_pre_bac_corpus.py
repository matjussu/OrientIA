"""Tests `src/collect/build_voie_pre_bac_corpus.py`."""
from __future__ import annotations

import json

import pytest

from src.collect.build_voie_pre_bac_corpus import (
    PRE_BAC_TYPES,
    _slug,
    aggregate_by_type_diplome_domaine,
    aggregate_by_type_diplome_global,
    build_corpus,
    filter_pre_bac,
    save_corpus,
)


@pytest.fixture
def onisep_extended_sample():
    """Sample 5 fiches : 3 BAC PRO + 1 CAP + 1 master (à filtrer)."""
    return [
        {
            "type_diplome": "baccalauréat professionnel",
            "nom": "bac pro cybersécurité, informatique et réseaux, électronique",
            "domaine": "cyber",
            "duree": "3 ans",
            "sigle_formation": "CIEL",
            "rncp": 37489,
            "url_onisep": "https://www.onisep.fr/test1",
            "tutelle": "Ministère Éducation Nationale",
        },
        {
            "type_diplome": "baccalauréat professionnel",
            "nom": "bac pro métiers de l'électricité",
            "domaine": "ingenierie_industrielle",
            "duree": "3 ans",
            "sigle_formation": "MELEC",
            "rncp": 12345,
            "url_onisep": "https://www.onisep.fr/test2",
        },
        {
            "type_diplome": "baccalauréat professionnel",
            "nom": "bac pro maintenance",
            "domaine": "ingenierie_industrielle",
            "duree": "3 ans",
            "url_onisep": "https://www.onisep.fr/test3",
        },
        {
            "type_diplome": "certificat d'aptitude professionnelle",
            "nom": "cap cuisine",
            "domaine": "tourisme_hotellerie",
            "duree": "2 ans",
            "url_onisep": "https://www.onisep.fr/test4",
        },
        {
            "type_diplome": "master",
            "nom": "master mathématiques",
            "domaine": "sciences_fondamentales",
            "duree": "2 ans",
            "url_onisep": "https://www.onisep.fr/test5",
        },  # à filtrer (post-bac)
    ]


class TestSlug:
    def test_basic(self):
        assert _slug("BAC PRO") == "bac-pro"
        assert _slug("ingénierie industrielle") == "ingenierie-industrielle"


class TestPreBacTypes:
    def test_only_bac_pro_and_cap(self):
        assert "baccalauréat professionnel" in PRE_BAC_TYPES
        assert "certificat d'aptitude professionnelle" in PRE_BAC_TYPES
        assert "master" not in PRE_BAC_TYPES
        assert "licence" not in PRE_BAC_TYPES


class TestFilterPreBac:
    def test_keeps_only_bac_pro_and_cap(self, onisep_extended_sample):
        out = filter_pre_bac(onisep_extended_sample)
        assert len(out) == 4  # 3 BAC PRO + 1 CAP, master filtré

    def test_master_filtered(self, onisep_extended_sample):
        out = filter_pre_bac(onisep_extended_sample)
        assert all(r["type_diplome"] in PRE_BAC_TYPES for r in out)


class TestAggregateByTypeDiplomeDomaine:
    def test_one_cell_per_couple(self, onisep_extended_sample):
        pre_bac = filter_pre_bac(onisep_extended_sample)
        out = aggregate_by_type_diplome_domaine(pre_bac)
        # Couples : BAC PRO×cyber (1), BAC PRO×ingenierie_industrielle (2), CAP×tourisme_hotellerie (1)
        # 3 cells (2 fiches BAC PRO ingenierie sont dans la même cell)
        assert len(out) == 3

    def test_aggregates_2_specialites_same_domaine(self, onisep_extended_sample):
        pre_bac = filter_pre_bac(onisep_extended_sample)
        out = aggregate_by_type_diplome_domaine(pre_bac)
        bp_ind = next(
            r for r in out
            if r["type_diplome"] == "BAC PRO" and r["domaine"] == "ingenierie_industrielle"
        )
        assert bp_ind["n_specialites"] == 2

    def test_granularity_tag(self, onisep_extended_sample):
        pre_bac = filter_pre_bac(onisep_extended_sample)
        out = aggregate_by_type_diplome_domaine(pre_bac)
        bp = next(r for r in out if r["type_diplome"] == "BAC PRO")
        cap = next(r for r in out if r["type_diplome"] == "CAP")
        assert bp["granularity"] == "bac_pro_domaine"
        assert cap["granularity"] == "cap_domaine"

    def test_text_includes_specialites_with_url(self, onisep_extended_sample):
        pre_bac = filter_pre_bac(onisep_extended_sample)
        out = aggregate_by_type_diplome_domaine(pre_bac)
        bp_ind = next(
            r for r in out
            if r["type_diplome"] == "BAC PRO" and r["domaine"] == "ingenierie_industrielle"
        )
        assert "MELEC" in bp_ind["text"]
        assert "https://www.onisep.fr/test2" in bp_ind["text"]

    def test_skips_records_with_empty_domaine(self):
        records = [{
            "type_diplome": "baccalauréat professionnel",
            "nom": "bac pro test",
            "domaine": "",
            "duree": "3 ans",
        }]
        out = aggregate_by_type_diplome_domaine(records)
        assert out == []


class TestAggregateByTypeDiplomeGlobal:
    def test_one_cell_per_type(self, onisep_extended_sample):
        pre_bac = filter_pre_bac(onisep_extended_sample)
        out = aggregate_by_type_diplome_global(pre_bac)
        # 1 BAC PRO synthèse + 1 CAP synthèse
        assert len(out) == 2
        types = {r["type_diplome"] for r in out}
        assert types == {"BAC PRO", "CAP"}

    def test_n_specialites_total(self, onisep_extended_sample):
        pre_bac = filter_pre_bac(onisep_extended_sample)
        out = aggregate_by_type_diplome_global(pre_bac)
        bp = next(r for r in out if r["type_diplome"] == "BAC PRO")
        assert bp["n_specialites_total"] == 3
        cap = next(r for r in out if r["type_diplome"] == "CAP")
        assert cap["n_specialites_total"] == 1

    def test_n_domaines_couverts(self, onisep_extended_sample):
        pre_bac = filter_pre_bac(onisep_extended_sample)
        out = aggregate_by_type_diplome_global(pre_bac)
        bp = next(r for r in out if r["type_diplome"] == "BAC PRO")
        # cyber + ingenierie_industrielle
        assert bp["n_domaines_couverts"] == 2

    def test_granularity_tag(self, onisep_extended_sample):
        pre_bac = filter_pre_bac(onisep_extended_sample)
        out = aggregate_by_type_diplome_global(pre_bac)
        assert all(r["granularity"] == "type_diplome_synthese" for r in out)

    def test_text_includes_pedagogical_note(self, onisep_extended_sample):
        """Vérifie l'inclusion de la note pédagogique sur durée + insertion."""
        pre_bac = filter_pre_bac(onisep_extended_sample)
        out = aggregate_by_type_diplome_global(pre_bac)
        bp = next(r for r in out if r["type_diplome"] == "BAC PRO")
        cap = next(r for r in out if r["type_diplome"] == "CAP")
        assert "3 ans" in bp["text"]
        assert "Niveau 4" in bp["text"]
        assert "2 ans" in cap["text"]
        assert "Niveau 3" in cap["text"]


def test_build_corpus_combines(onisep_extended_sample):
    pre_bac = filter_pre_bac(onisep_extended_sample)
    corpus = build_corpus(pre_bac)
    # 3 cells couples (BAC PRO×cyber, BAC PRO×ingen, CAP×tourisme) + 2 synthèses = 5
    assert len(corpus) == 5
    assert all(c["domain"] == "voie_pre_bac" for c in corpus)
    assert all(c["source"] == "onisep_formations_extended" for c in corpus)


def test_save_corpus_round_trip(tmp_path, onisep_extended_sample):
    pre_bac = filter_pre_bac(onisep_extended_sample)
    corpus = build_corpus(pre_bac)
    target = tmp_path / "out.json"
    save_corpus(corpus, path=target)
    loaded = json.loads(target.read_text(encoding="utf-8"))
    assert len(loaded) == len(corpus)


def test_real_data_has_bac_pro_and_cap():
    """Smoke test : le vrai onisep_formations_extended contient bien
    des fiches BAC PRO et CAP."""
    from src.collect.build_voie_pre_bac_corpus import load_extended
    records = load_extended()
    pre_bac = filter_pre_bac(records)
    bp = [r for r in pre_bac if PRE_BAC_TYPES.get(r["type_diplome"]) == "BAC PRO"]
    cap = [r for r in pre_bac if PRE_BAC_TYPES.get(r["type_diplome"]) == "CAP"]
    # cible Sprint 6 : 80+ BAC PRO et 80+ CAP
    assert len(bp) >= 80, f"Pas assez de BAC PRO : {len(bp)}"
    assert len(cap) >= 80, f"Pas assez de CAP : {len(cap)}"
