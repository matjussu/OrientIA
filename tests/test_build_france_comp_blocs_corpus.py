"""Tests `src/collect/build_france_comp_blocs_corpus.py`."""
from __future__ import annotations

import json

import pytest

from src.collect.build_france_comp_blocs_corpus import (
    _format_blocs_text,
    _index_blocs_by_fiche,
    aggregate_by_fiche,
    build_corpus,
    save_corpus,
)


@pytest.fixture
def certifs_sample():
    """Échantillon de fiches RNCP normalisées (cf src/collect/rncp.py)."""
    return [
        {
            "source": "rncp",
            "phase": "initial",
            "numero_fiche": "RNCP100",
            "intitule": "Technicien frigoriste",
            "abrege_type": "BTS",
            "niveau_eu": "NIV5",
            "niveau": "bac+2",
            "niveau_intitule": "Niveau 5",
            "actif": True,
            "voies_acces": ["Apprentissage", "Formation continue"],
            "codes_rome": [{"code": "I1306", "libelle": "Installation maintenance frigorifique"}],
            "codes_nsf": [{"code": "227", "libelle": "227 : Energie, génie climatique"}],
        },
        {
            "source": "rncp",
            "phase": "initial",
            "numero_fiche": "RNCP200",
            "intitule": "Master Informatique",
            "niveau_eu": "NIV7",
            "niveau": "bac+5",
            "niveau_intitule": "Niveau 7",
            "actif": True,
            "voies_acces": ["VAE"],
            "codes_rome": [
                {"code": "M1805", "libelle": "Études et développement informatique"},
            ],
            "codes_nsf": [{"code": "326", "libelle": "326 : Informatique"}],
        },
        {
            # Inactive — must be filtered out
            "source": "rncp",
            "phase": "initial",
            "numero_fiche": "RNCP999",
            "intitule": "Diplôme désactivé",
            "actif": False,
            "voies_acces": [],
            "codes_rome": [],
            "codes_nsf": [],
        },
        {
            # Active mais aucun bloc associé — doit être filtré
            "source": "rncp",
            "phase": "initial",
            "numero_fiche": "RNCP300",
            "intitule": "Certif sans blocs",
            "actif": True,
            "voies_acces": [],
            "codes_rome": [],
            "codes_nsf": [],
        },
    ]


@pytest.fixture
def blocs_sample():
    """Rows brutes du CSV Blocs_De_Compétences (3 colonnes)."""
    return [
        {
            "Numero_Fiche": "RNCP100",
            "Bloc_Competences_Code": "RNCP100BC02",
            "Bloc_Competences_Libelle": "Assurer la maintenance des installations frigorifiques",
        },
        {
            "Numero_Fiche": "RNCP100",
            "Bloc_Competences_Code": "RNCP100BC01",
            "Bloc_Competences_Libelle": "Monter et mettre en service des installations frigorifiques",
        },
        {
            "Numero_Fiche": "RNCP200",
            "Bloc_Competences_Code": "RNCP200BC01",
            "Bloc_Competences_Libelle": "Concevoir et développer des systèmes informatiques distribués",
        },
        {
            "Numero_Fiche": "RNCP200",
            "Bloc_Competences_Code": "RNCP200BC02",
            "Bloc_Competences_Libelle": "Piloter une équipe d'ingénieurs en environnement agile",
        },
        {
            # Cette fiche n'est pas active dans certifs_sample → ignorée
            "Numero_Fiche": "RNCP999",
            "Bloc_Competences_Code": "RNCP999BC01",
            "Bloc_Competences_Libelle": "Bloc d'une certif désactivée",
        },
    ]


class TestIndexBlocsByFiche:
    def test_groups_by_numero(self, blocs_sample):
        idx = _index_blocs_by_fiche(blocs_sample)
        assert "RNCP100" in idx
        assert len(idx["RNCP100"]) == 2
        assert len(idx["RNCP200"]) == 2

    def test_skips_empty_numero(self):
        rows = [
            {"Numero_Fiche": "", "Bloc_Competences_Code": "X", "Bloc_Competences_Libelle": "y"},
            {"Numero_Fiche": "RNCP1", "Bloc_Competences_Code": "X", "Bloc_Competences_Libelle": "y"},
        ]
        idx = _index_blocs_by_fiche(rows)
        assert "" not in idx
        assert "RNCP1" in idx


class TestFormatBlocsText:
    def test_sorts_by_code(self):
        blocs = [
            {"Bloc_Competences_Code": "RNCP100BC02", "Bloc_Competences_Libelle": "Deuxième"},
            {"Bloc_Competences_Code": "RNCP100BC01", "Bloc_Competences_Libelle": "Premier"},
        ]
        text = _format_blocs_text(blocs)
        assert text.index("Premier") < text.index("Deuxième")
        assert "Bloc 1 : Premier" in text
        assert "Bloc 2 : Deuxième" in text

    def test_empty_blocs(self):
        assert _format_blocs_text([]) == ""

    def test_skips_empty_libelle(self):
        blocs = [
            {"Bloc_Competences_Code": "BC01", "Bloc_Competences_Libelle": ""},
            {"Bloc_Competences_Code": "BC02", "Bloc_Competences_Libelle": "Réel"},
        ]
        text = _format_blocs_text(blocs)
        assert "Réel" in text
        assert text.count("Bloc") == 1


class TestAggregateByFiche:
    def test_filters_inactive(self, certifs_sample, blocs_sample):
        idx = _index_blocs_by_fiche(blocs_sample)
        out = aggregate_by_fiche(certifs_sample, idx)
        numeros = {c["numero_fiche"] for c in out}
        assert "RNCP999" not in numeros  # inactif
        assert "RNCP300" not in numeros  # active mais 0 blocs

    def test_keeps_active_with_blocs(self, certifs_sample, blocs_sample):
        idx = _index_blocs_by_fiche(blocs_sample)
        out = aggregate_by_fiche(certifs_sample, idx)
        numeros = {c["numero_fiche"] for c in out}
        assert numeros == {"RNCP100", "RNCP200"}

    def test_text_includes_intitule_niveau(self, certifs_sample, blocs_sample):
        idx = _index_blocs_by_fiche(blocs_sample)
        out = aggregate_by_fiche(certifs_sample, idx)
        c100 = next(c for c in out if c["numero_fiche"] == "RNCP100")
        assert "Technicien frigoriste" in c100["text"]
        assert "RNCP100" in c100["text"]
        assert "bac+2" in c100["text"]
        # Pas de double prefix "RNCP RNCP" dans le texte (numero_fiche
        # contient déjà le prefix RNCP).
        assert "RNCP RNCP100" not in c100["text"]

    def test_text_includes_blocs(self, certifs_sample, blocs_sample):
        idx = _index_blocs_by_fiche(blocs_sample)
        out = aggregate_by_fiche(certifs_sample, idx)
        c100 = next(c for c in out if c["numero_fiche"] == "RNCP100")
        assert "Monter et mettre en service" in c100["text"]
        assert "Assurer la maintenance" in c100["text"]
        # Les deux blocs présents
        assert c100["text"].count("Bloc ") == 2

    def test_text_includes_rome_nsf(self, certifs_sample, blocs_sample):
        idx = _index_blocs_by_fiche(blocs_sample)
        out = aggregate_by_fiche(certifs_sample, idx)
        c100 = next(c for c in out if c["numero_fiche"] == "RNCP100")
        assert "I1306" in c100["text"]  # ROME
        assert "Energie" in c100["text"] or "227" in c100["text"]  # NSF

    def test_text_includes_voies(self, certifs_sample, blocs_sample):
        idx = _index_blocs_by_fiche(blocs_sample)
        out = aggregate_by_fiche(certifs_sample, idx)
        c100 = next(c for c in out if c["numero_fiche"] == "RNCP100")
        assert "Apprentissage" in c100["text"]

    def test_n_blocs_field(self, certifs_sample, blocs_sample):
        idx = _index_blocs_by_fiche(blocs_sample)
        out = aggregate_by_fiche(certifs_sample, idx)
        c100 = next(c for c in out if c["numero_fiche"] == "RNCP100")
        assert c100["n_blocs"] == 2

    def test_domain_and_source(self, certifs_sample, blocs_sample):
        idx = _index_blocs_by_fiche(blocs_sample)
        out = aggregate_by_fiche(certifs_sample, idx)
        for c in out:
            assert c["domain"] == "competences_certif"
            assert c["source"] == "rncp_blocs"

    def test_id_format(self, certifs_sample, blocs_sample):
        idx = _index_blocs_by_fiche(blocs_sample)
        out = aggregate_by_fiche(certifs_sample, idx)
        ids = {c["id"] for c in out}
        assert "rncp_blocs:RNCP100" in ids
        assert "rncp_blocs:RNCP200" in ids


def test_build_corpus_with_inputs(certifs_sample, blocs_sample):
    corpus = build_corpus(certifs=certifs_sample, blocs=blocs_sample)
    assert len(corpus) == 2  # RNCP100 + RNCP200
    assert all(c["domain"] == "competences_certif" for c in corpus)
    assert all(c["source"] == "rncp_blocs" for c in corpus)


def test_save_corpus_round_trip(tmp_path, certifs_sample, blocs_sample):
    corpus = build_corpus(certifs=certifs_sample, blocs=blocs_sample)
    target = tmp_path / "out.json"
    save_corpus(corpus, path=target)
    loaded = json.loads(target.read_text(encoding="utf-8"))
    assert len(loaded) == len(corpus)
    for orig, new in zip(corpus, loaded):
        assert new["id"] == orig["id"]
        assert new["text"] == orig["text"]
        assert new["n_blocs"] == orig["n_blocs"]


def test_text_format_includes_france_competences_source(certifs_sample, blocs_sample):
    corpus = build_corpus(certifs=certifs_sample, blocs=blocs_sample)
    for c in corpus:
        assert "France Compétences" in c["text"]
        assert "RNCP" in c["text"]
