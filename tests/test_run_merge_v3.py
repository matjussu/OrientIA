"""Tests src/collect/run_merge_v3.py — Phase B.2 du plan corpus v5.

Couvre :
- Tests unitaires des stages 3-11 (purs, ne nécessitent pas d'I/O lourd)
- Tests d'idempotence (rerun sur même input = mêmes bytes)
- Tests dropouts (compteurs cohérents stage in → out)
- Tests no-Cereq (ADR-054 : aucune fiche output ne porte `source=cereq`)
- Tests gracefulness (corpora annexes absents → skip silencieux)

Les tests d'orchestration full (`run_merge_v3()` end-to-end) ne tournent
pas par défaut car ils nécessitent les CSV/JSON sources (~minutes wall-clock).
À activer manuellement via `RUN_FULL_MERGE_V3=1 pytest`.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import pytest

from src.collect.run_merge_v3 import (
    _canonicalize_niveau,
    _canonicalize_region,
    _canonicalize_statut,
    _norm_text,
    stage_append_annexes,
    stage_dedup,
    stage_drop_empty,
    stage_normalize,
    stage_sort_deterministic,
    stage_write_out,
    run_merge_v3,
    ANNEX_CORPORA,
)


# ─────────────── Fixtures ───────────────


def fiche_parcoursup_sample() -> dict:
    return {
        "source": "parcoursup",
        "nom": "Bachelor Cybersécurité",
        "etablissement": "Lycée Emmanuel d'Alzon",
        "ville": "Nîmes",
        "region": "Occitanie",
        "niveau": "bac+3",
        "statut": "Privé",
        "type_diplome": "formation d'école spécialisée",
        "taux_acces_parcoursup_2025": 52.0,
    }


def fiche_monmaster_sample() -> dict:
    return {
        "source": "monmaster",
        "nom": "Master Droit des affaires",
        "etablissement": "Université Paris Cité",
        "ville": "Malakoff",
        "region": "Ile-de-France",  # casse non-canonique pour test normalize
        "niveau": "Bac+5",  # casse non-canonique
        "statut": "public",  # casse non-canonique
    }


def fiche_duplicate_sample() -> dict:
    """Doublon de fiche_parcoursup_sample avec valeurs en MAJ."""
    return {
        "source": "parcoursup_extended",
        "nom": "BACHELOR CYBERSÉCURITÉ",
        "etablissement": "Lycée Emmanuel D'Alzon",
        "ville": "NÎMES",
        "region": "OCCITANIE",
        "niveau": "bac+3",
    }


def fiche_inserjeunes_cfa_sample() -> dict:
    """Inserjeunes CFA — pas de nom/etab classique, juste UAI + stats."""
    return {
        "source": "inserjeunes_cfa",
        "uai": "0630003L",
        "etablissement": "Cours Supérieurs de Coiffure",
        "annee": "cumul 2023-2024",
        "taux_emploi": {"6m": 0.81, "12m": 0.73},
    }


def fiche_empty_sample() -> dict:
    """Fiche sans aucun champ exploitable — doit être droppée Stage 4."""
    return {"source": "monmaster"}


def fiche_only_nom_sample() -> dict:
    """Fiche avec seulement nom — droppée Stage 4 (pas d'autre signal)."""
    return {"source": "monmaster", "nom": "Test"}


# ─────────────── Tests helpers ───────────────


class TestNormalizeHelpers:
    def test_norm_text_strips_accents_and_case(self):
        assert _norm_text("Île-de-France") == "ile-de-france"
        assert _norm_text("BACHELOR CYBERSÉCURITÉ") == "bachelor cybersecurite"

    def test_canonicalize_region_handles_casse(self):
        assert _canonicalize_region("ILE-DE-FRANCE") == "Île-de-France"
        assert _canonicalize_region("auvergne-rhone-alpes") == "Auvergne-Rhône-Alpes"
        assert _canonicalize_region("Pays de la Loire") == "Pays de la Loire"

    def test_canonicalize_region_returns_none_for_empty(self):
        assert _canonicalize_region(None) is None
        assert _canonicalize_region("") is None

    def test_canonicalize_niveau_handles_variations(self):
        assert _canonicalize_niveau("Bac+5") == "bac+5"
        assert _canonicalize_niveau("bac + 3") == "bac+3"
        assert _canonicalize_niveau("CAP") == "cap-bep"

    def test_canonicalize_statut_normalizes_public_prive(self):
        assert _canonicalize_statut("public") == "Public"
        assert _canonicalize_statut("PRIVÉ") == "Privé"
        # Préserve les statuts spéciaux (CFA Apprentissage, etc.)
        assert _canonicalize_statut("CFA Apprentissage") == "CFA Apprentissage"


# ─────────────── Stage 3 — DEDUP ───────────────


class TestStageDedup:
    def test_no_dups_same_input_output(self):
        fiches = [fiche_parcoursup_sample(), fiche_monmaster_sample()]
        out, stats = stage_dedup(fiches)
        assert len(out) == 2
        assert stats["n_dups_removed"] == 0

    def test_dedup_by_normalized_key(self):
        """Doublons sur (nom_norm, etab_norm, ville_norm) — casse-insensible."""
        fiches = [fiche_parcoursup_sample(), fiche_duplicate_sample()]
        out, stats = stage_dedup(fiches)
        assert len(out) == 1
        assert stats["n_dups_removed"] == 1

    def test_dedup_keeps_more_complete(self):
        """Max-merge : le doublon avec le plus de champs gagne."""
        sparse = {"source": "monmaster", "nom": "X", "etablissement": "Y", "ville": "Z"}
        rich = {
            "source": "parcoursup",
            "nom": "x", "etablissement": "y", "ville": "z",
            "niveau": "bac+3", "statut": "Public", "taux_acces_parcoursup_2025": 50.0,
        }
        out, _ = stage_dedup([sparse, rich])
        assert len(out) == 1
        # rich gagne (plus de champs)
        assert out[0]["niveau"] == "bac+3"

    def test_inserjeunes_cfa_not_deduped_when_no_nom(self):
        """Fiches sans nom (Inserjeunes CFA pure stats) ne sont pas dédupliquées."""
        fiches = [fiche_inserjeunes_cfa_sample(), fiche_inserjeunes_cfa_sample()]
        out, _ = stage_dedup(fiches)
        # Les 2 sont gardées car clé dédup vide
        assert len(out) == 2


# ─────────────── Stage 4 — DROP_EMPTY ───────────────


class TestStageDropEmpty:
    def test_keeps_complete_fiches(self):
        fiches = [fiche_parcoursup_sample(), fiche_monmaster_sample()]
        out, stats = stage_drop_empty(fiches)
        assert len(out) == 2
        assert stats["n_dropped"] == 0

    def test_drops_empty_fiche(self):
        out, stats = stage_drop_empty([fiche_empty_sample()])
        assert len(out) == 0
        assert stats["n_dropped"] == 1

    def test_drops_only_nom_fiche(self):
        """Fiche avec juste `nom` (sans niveau/type/etc.) est droppée."""
        out, stats = stage_drop_empty([fiche_only_nom_sample()])
        assert len(out) == 0
        assert stats["n_dropped"] == 1

    def test_keeps_inserjeunes_cfa_with_uai(self):
        """Inserjeunes CFA stats-only mais avec UAI → gardée pour attach Stage 9."""
        out, _ = stage_drop_empty([fiche_inserjeunes_cfa_sample()])
        assert len(out) == 1


# ─────────────── Stage 5 — NORMALIZE ───────────────


class TestStageNormalize:
    def test_normalize_region_idempotent(self):
        fiche = fiche_monmaster_sample()  # region "Ile-de-France"
        out, stats = stage_normalize([fiche])
        assert out[0]["region"] == "Île-de-France"
        # Re-run = identité (idempotent)
        out2, stats2 = stage_normalize(out)
        assert out2[0]["region"] == "Île-de-France"
        assert stats2["n_region_canonized"] == 0  # déjà canonique

    def test_normalize_niveau_handles_variations(self):
        fiche = fiche_monmaster_sample()  # niveau "Bac+5"
        out, _ = stage_normalize([fiche])
        assert out[0]["niveau"] == "bac+5"

    def test_normalize_statut_handles_casse(self):
        fiche = fiche_monmaster_sample()  # statut "public"
        out, _ = stage_normalize([fiche])
        assert out[0]["statut"] == "Public"

    def test_no_op_when_already_canonical(self):
        """Stage 5 idempotent sur les champs canoniques (region/niveau/statut).
        Vague 1.C (2026-05-08) — Stage 5 ajoute en plus le flag
        `retrieval_eligible` (recalculé à chaque run, donc déterministe).
        Le test vérifie l'idempotence des champs originaux + présence du flag."""
        fiche = fiche_parcoursup_sample()  # tout canonique
        out, _ = stage_normalize([fiche])
        # Champs canoniques inchangés
        assert out[0]["region"] == fiche["region"]
        assert out[0]["niveau"] == fiche["niveau"]
        assert out[0]["statut"] == fiche["statut"]
        # Flag retrieval_eligible ajouté (Parcoursup = True par défaut)
        assert out[0]["retrieval_eligible"] is True

    def test_retrieval_eligible_false_for_excluded_sources(self):
        """Vague 1.C — sources structurellement inadaptées sont taggées false."""
        for excluded_source in ("rncp", "onisep", "labonnealternance", "inserjeunes_cfa"):
            fiche = {"source": excluded_source, "nom": "test"}
            out, _ = stage_normalize([fiche])
            assert out[0]["retrieval_eligible"] is False, \
                f"{excluded_source} doit être retrieval_eligible=false"

    def test_retrieval_eligible_true_for_default_sources(self):
        """Vague 1.C — sources core (Parcoursup, MonMaster) éligibles par défaut."""
        for ok_source in ("parcoursup", "monmaster", "secnumedu"):
            fiche = {"source": ok_source, "nom": "test"}
            out, _ = stage_normalize([fiche])
            assert out[0]["retrieval_eligible"] is True, \
                f"{ok_source} doit être retrieval_eligible=true"


# ─────────────── Stage 10 — APPEND_ANNEXES ───────────────


class TestStageAppendAnnexes:
    def test_appends_existing_annexes(self):
        # Test sur les vrais fichiers (skip si absents)
        n_before = 0
        fiches_in = []
        out, stats = stage_append_annexes(fiches_in)
        # Au moins 14 corpora conformes (Phase A.4)
        n_appended = stats["n_annexes_total"]
        if n_appended == 0:
            pytest.skip("Aucun corpus annexe disponible — environnement minimal")
        assert n_appended > 1000  # 14 corpora ≈ 13k records totaux
        # Vérifie que les domaines attendus sont présents
        domains = stats["by_domain"]
        # Au moins 3 domaines distincts
        assert len(domains) >= 3

    def test_skips_missing_corpora_gracefully(self, tmp_path, monkeypatch):
        # Force tous les paths absents en redirigeant vers tmp
        from src.collect import run_merge_v3
        monkeypatch.setattr(
            run_merge_v3, "ANNEX_CORPORA",
            [("Fake", tmp_path / "absent.json", "fake_domain", None)]
        )
        out, stats = run_merge_v3.stage_append_annexes([])
        assert stats["n_annexes_total"] == 0


# ─────────────── Stage 11 — SORT_DETERMINISTIC ───────────────


class TestStageSort:
    def test_sort_idempotent(self):
        fiches = [fiche_monmaster_sample(), fiche_parcoursup_sample()]
        out_1 = stage_sort_deterministic(fiches)
        out_2 = stage_sort_deterministic(out_1)
        assert json.dumps(out_1, sort_keys=True) == json.dumps(out_2, sort_keys=True)

    def test_sort_groups_by_domain(self):
        fiches = [
            {"source": "parcoursup", "nom": "Z", "etablissement": "Z"},
            {"id": "metier:1", "domain": "metier", "source": "ideo"},
            {"source": "parcoursup", "nom": "A", "etablissement": "A"},
            {"id": "dares:1", "domain": "metier_prospective", "source": "dares"},
        ]
        out = stage_sort_deterministic(fiches)
        # Groupé par domain (les fiches sans domain en premier — domain="")
        domains_order = [f.get("domain") or "" for f in out]
        # Deux fiches sans domain (formations) sont consécutives
        assert domains_order[0] == "" and domains_order[1] == ""
        # Puis les annexes par domain
        assert "metier" in domains_order
        assert "metier_prospective" in domains_order


# ─────────────── No-Cereq invariant (ADR-054) ───────────────


class TestNoCereqInvariant:
    """ADR-054 — aucune fiche output ne doit porter `insertion_pro.source == "cereq"`."""

    def test_stage_2_with_cereq_none_does_not_attach(self):
        """`merge_all_extended(cereq=None)` → no-op sur attach_cereq_insertion."""
        from src.collect.merge import attach_cereq_insertion
        fiches = [fiche_parcoursup_sample(), fiche_monmaster_sample()]
        # Simulate Stage 2 contract : cereq=None → fiches inchangées
        out = attach_cereq_insertion(fiches, None)
        for f in out:
            ip = f.get("insertion_pro") or {}
            assert ip.get("source") != "cereq", (
                f"Fiche {f.get('nom')} a hérité d'un insertion_pro Cereq "
                f"alors que cereq=None"
            )


# ─────────────── Stage 12 — WRITE_OUT (idempotence) ───────────────


class TestStageWriteOutIdempotence:
    def test_same_input_produces_same_bytes(self, tmp_path):
        fiches = [fiche_parcoursup_sample(), fiche_monmaster_sample()]
        out1 = stage_write_out(fiches, tmp_path / "v5_a.json")
        out2 = stage_write_out(fiches, tmp_path / "v5_b.json")
        assert hashlib.sha256(out1.read_bytes()).hexdigest() == \
               hashlib.sha256(out2.read_bytes()).hexdigest()

    def test_sorted_then_written_idempotent(self, tmp_path):
        """Sort + write = bytes stables."""
        fiches = [fiche_monmaster_sample(), fiche_parcoursup_sample()]
        sorted_1 = stage_sort_deterministic(fiches)
        sorted_2 = stage_sort_deterministic(fiches)
        out1 = stage_write_out(sorted_1, tmp_path / "v5_a.json")
        out2 = stage_write_out(sorted_2, tmp_path / "v5_b.json")
        assert out1.read_bytes() == out2.read_bytes()


# ─────────────── Test orchestration full (opt-in) ───────────────


@pytest.mark.skipif(
    os.environ.get("RUN_FULL_MERGE_V3") != "1",
    reason="Set RUN_FULL_MERGE_V3=1 to run the full merge v3 pipeline test",
)
class TestFullPipelineOptIn:
    """Tests end-to-end de `run_merge_v3()`. Nécessite les sources réelles
    et prend ~1-2 min wall-clock. Off par défaut."""

    def test_full_run_produces_v5_corpus(self, tmp_path):
        out_path = tmp_path / "formations_v5_test.json"
        result = run_merge_v3(output_path=out_path, verbose=False)
        assert out_path.exists()
        assert result["n_total"] > 30000  # cible ~45k post Stage 10
        # Aucune fiche ne doit porter Cereq agrégat
        fiches = json.loads(out_path.read_text(encoding="utf-8"))
        for f in fiches:
            ip = f.get("insertion_pro") or {}
            assert ip.get("source") != "cereq"
        # Distribution domain : annexes présentes
        domains = result["domain_distribution"]
        assert "metier_detail" in domains  # ROME 4.0
        assert "metier_prospective" in domains  # DARES

    def test_idempotent_full_run(self, tmp_path):
        """2 runs sur le même filesystem → mêmes bytes (idempotence stricte)."""
        out_a = tmp_path / "v5_a.json"
        out_b = tmp_path / "v5_b.json"
        run_merge_v3(output_path=out_a, verbose=False)
        run_merge_v3(output_path=out_b, verbose=False)
        sha_a = hashlib.sha256(out_a.read_bytes()).hexdigest()
        sha_b = hashlib.sha256(out_b.read_bytes()).hexdigest()
        assert sha_a == sha_b


# ─────────────── ANNEX_CORPORA configuration sanity ───────────────


class TestAnnexCorporaConfiguration:
    def test_no_duplicate_paths(self):
        paths = [c[1] for c in ANNEX_CORPORA]
        assert len(paths) == len(set(paths)), "ANNEX_CORPORA contient des paths dupliqués"

    def test_all_have_expected_domain(self):
        for label, path, expected_domain, _ in ANNEX_CORPORA:
            assert expected_domain, f"{label} (Path {path}) n'a pas de domain attendu"

    def test_paths_are_in_data_processed(self):
        for label, path, _, _ in ANNEX_CORPORA:
            assert "data/processed" in str(path), f"{label}: {path} hors data/processed"
