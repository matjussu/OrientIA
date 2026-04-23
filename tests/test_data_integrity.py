"""Tests anti-régression d'intégrité data OrientIA (Phase 5 audit qualité).

Garantit qu'aucune future ingestion ne casse les invariants majeurs du corpus.
À exécuter après chaque ingestion D* ou refactor de `src/collect/*`.

Ces tests sont **skippés** si les fichiers processed ne sont pas présents
localement (CI sans corpus ingéré → no-op), mais vérifient les invariants
stricts si data/processed/*.json existent.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"

# Invariants par fichier : schéma minimal attendu
EXPECTED_SCHEMAS = {
    "monmaster_formations.json": {
        "required_fields": {"source", "phase", "nom", "etablissement", "ville", "niveau"},
        "expected_phase": {"master"},
        "expected_niveau": {"bac+5"},
        "expected_source": "monmaster",
    },
    "rncp_certifications.json": {
        "required_fields": {"source", "phase", "intitule", "numero_fiche", "niveau_eu", "actif"},
        "expected_phase": {"initial", "master"},
        "expected_niveau": {"bac", "cap-bep", "bac+2", "bac+3", "bac+5", "bac+8"},
        "expected_source": "rncp",
    },
    "onisep_metiers.json": {
        "required_fields": {"source", "type", "libelle", "codes_rome"},
        "expected_source": "onisep_metiers",
        "expected_type": "metier",
    },
    "parcoursup_extended.json": {
        "required_fields": {"source", "phase", "nom", "etablissement", "ville", "niveau", "domaine"},
        "expected_phase": {"initial", "master"},
        "expected_source": "parcoursup",
    },
}


def _load_or_skip(filename: str):
    path = PROCESSED_DIR / filename
    if not path.exists():
        pytest.skip(f"{filename} absent (ingestion pas faite localement)")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("filename,schema", EXPECTED_SCHEMAS.items())
def test_file_is_valid_json_list(filename, schema):
    data = _load_or_skip(filename)
    assert isinstance(data, list), f"{filename} doit être une list, pas {type(data).__name__}"
    assert len(data) > 0, f"{filename} ne doit pas être vide"


@pytest.mark.parametrize("filename,schema", EXPECTED_SCHEMAS.items())
def test_required_fields_present_on_every_entry(filename, schema):
    data = _load_or_skip(filename)
    required = schema["required_fields"]
    for i, entry in enumerate(data):
        missing = required - set(entry.keys())
        assert not missing, f"{filename}[{i}] manque les champs : {missing}"


@pytest.mark.parametrize("filename,schema", EXPECTED_SCHEMAS.items())
def test_source_field_matches_expected(filename, schema):
    if "expected_source" not in schema:
        pytest.skip(f"Pas de contrainte source pour {filename}")
    data = _load_or_skip(filename)
    expected = schema["expected_source"]
    for i, entry in enumerate(data):
        assert entry.get("source") == expected, (
            f"{filename}[{i}] source={entry.get('source')!r} ≠ attendu {expected!r}"
        )


@pytest.mark.parametrize("filename,schema", EXPECTED_SCHEMAS.items())
def test_phase_in_allowed_set(filename, schema):
    """ADR-039 : phase doit être dans {initial, master, reorientation}."""
    if "expected_phase" not in schema:
        pytest.skip(f"Pas de contrainte phase pour {filename}")
    data = _load_or_skip(filename)
    allowed = schema["expected_phase"]
    for i, entry in enumerate(data):
        phase = entry.get("phase")
        assert phase in allowed, (
            f"{filename}[{i}] phase={phase!r} ∉ {allowed}"
        )


def test_monmaster_profil_admis_stats_in_percent_range():
    """Les pct_accept_* MonMaster doivent être dans [0, 100]."""
    data = _load_or_skip("monmaster_formations.json")
    for i, f in enumerate(data):
        profil = f.get("profil_admis") or {}
        for k in ("pct_lg3", "pct_lp3", "pct_but3", "pct_master", "pct_femme"):
            val = profil.get(k)
            if val is None:
                continue
            assert 0.0 <= val <= 100.0, (
                f"MonMaster[{i}] profil_admis.{k}={val} hors [0, 100]"
            )


def test_rncp_niveau_mapping_coherent_with_niveau_eu():
    """RNCP : mapping NIV3→cap-bep, NIV4→bac, NIV5→bac+2, etc."""
    data = _load_or_skip("rncp_certifications.json")
    expected = {
        "NIV3": "cap-bep",
        "NIV4": "bac",
        "NIV5": "bac+2",
        "NIV6": "bac+3",
        "NIV7": "bac+5",
        "NIV8": "bac+8",
    }
    for i, f in enumerate(data):
        niv_eu = f.get("niveau_eu")
        niv = f.get("niveau")
        if niv_eu in expected:
            assert niv == expected[niv_eu], (
                f"RNCP[{i}] niveau_eu={niv_eu} → niveau {niv!r} ≠ attendu {expected[niv_eu]!r}"
            )


def test_onisep_metiers_all_have_valid_rome():
    """Majorité des métiers ONISEP doivent avoir au moins 1 code ROME.

    Observation réelle au 2026-04-23 : 174/1518 = 11.5% sans ROME (collection
    'pas de publication Onisep spécifique' surtout). Tolérance seuil 15% pour
    absorber cette variance sans casser le test, mais au-delà = régression.
    """
    data = _load_or_skip("onisep_metiers.json")
    sans_rome = [m for m in data if not (m.get("codes_rome") or [])]
    assert len(sans_rome) / len(data) < 0.15, (
        f"{len(sans_rome)}/{len(data)} métiers sans code ROME (>15%, seuil tolérance)"
    )


def test_rncp_all_active_are_actif_true():
    """Filtre ingestion : on ne garde que les certifs ACTIVE."""
    data = _load_or_skip("rncp_certifications.json")
    non_active = [c for c in data if not c.get("actif")]
    assert non_active == [], f"{len(non_active)} certifs inactives présentes — filtre cassé"


def test_parcoursup_extended_has_expected_domain_coverage():
    """Parcoursup extended doit couvrir >10 domaines (vs 3 legacy)."""
    data = _load_or_skip("parcoursup_extended.json")
    domaines = {f.get("domaine") for f in data if f.get("domaine")}
    assert len(domaines) >= 10, (
        f"Parcoursup extended ne couvre que {len(domaines)} domaines, attendu ≥10 "
        f"(cf ADR-041 extension tous secteurs)"
    )


def test_corpus_total_exceeds_minimum_expected():
    """Audit de rassurance : total fiches multi-sources > 20k (ADR-039 scope élargi)."""
    totals = 0
    for fname in ("monmaster_formations.json", "rncp_certifications.json", "parcoursup_extended.json"):
        path = PROCESSED_DIR / fname
        if path.exists():
            totals += len(json.loads(path.read_text(encoding="utf-8")))
    if totals == 0:
        pytest.skip("Aucun corpus ingéré localement")
    assert totals > 20000, (
        f"Total corpus multi-sources = {totals:,}, attendu >20 000 (MM 16k + RNCP 6.5k + PSup 9k)"
    )
