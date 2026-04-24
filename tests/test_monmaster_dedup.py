"""Tests pour la dédup MonMaster par session + clamp taux_admission (ADR-044).

- Dédup par `id_mon_master.ifc` en conservant la session la plus récente
- `_compute_taux_admission` clampe à [0, 1] pour les records source dont
  `n_accept_total > n_can_pp` (cf 6 cas LANGUES LITTERATURES identifiés
  dans l'audit 2026-04-23)
"""
from __future__ import annotations

import pytest

from src.collect.monmaster import (
    _compute_taux_admission,
    dedupe_keep_latest_session,
)


def test_dedup_keeps_latest_session():
    fiches = [
        {"id_mon_master": {"ifc": "A", "session": "2024"}, "nom": "A-2024"},
        {"id_mon_master": {"ifc": "A", "session": "2025"}, "nom": "A-2025"},
        {"id_mon_master": {"ifc": "B", "session": "2025"}, "nom": "B"},
    ]
    out = dedupe_keep_latest_session(fiches)
    assert len(out) == 2
    names = {f["nom"] for f in out}
    assert names == {"A-2025", "B"}


def test_dedup_preserves_first_appearance_order():
    fiches = [
        {"id_mon_master": {"ifc": "A", "session": "2024"}, "nom": "A1"},
        {"id_mon_master": {"ifc": "B", "session": "2025"}, "nom": "B"},
        {"id_mon_master": {"ifc": "A", "session": "2025"}, "nom": "A2"},
    ]
    out = dedupe_keep_latest_session(fiches)
    # Order = première apparition ; A déjà vu index 0, B index 1
    assert [f["nom"] for f in out] == ["A2", "B"]


def test_dedup_old_session_variant_earlier_in_list():
    fiches = [
        {"id_mon_master": {"ifc": "A", "session": "2025"}, "nom": "new"},
        {"id_mon_master": {"ifc": "A", "session": "2024"}, "nom": "old"},
    ]
    out = dedupe_keep_latest_session(fiches)
    assert len(out) == 1
    assert out[0]["nom"] == "new"


def test_dedup_no_ifc_preserved():
    fiches = [
        {"id_mon_master": {"ifc": None}, "nom": "orphan1"},
        {"id_mon_master": {"ifc": "X", "session": "2025"}, "nom": "X"},
        {"id_mon_master": {"ifc": None}, "nom": "orphan2"},
    ]
    out = dedupe_keep_latest_session(fiches)
    assert len(out) == 3


def test_dedup_empty_list():
    assert dedupe_keep_latest_session([]) == []


def test_dedup_single_record():
    f = [{"id_mon_master": {"ifc": "A", "session": "2025"}, "nom": "solo"}]
    assert dedupe_keep_latest_session(f) == f


def test_taux_admission_clamp_at_1():
    # Cas réel audit 2026-04-23 : n_accept > n_can
    assert _compute_taux_admission({"n_can_pp": 1, "n_accept_total": 2}) == 1.0
    assert _compute_taux_admission({"n_can_pp": 9, "n_accept_total": 12}) == 1.0
    assert _compute_taux_admission({"n_can_pp": 5, "n_accept_total": 7}) == 1.0


def test_taux_admission_normal_range():
    assert _compute_taux_admission({"n_can_pp": 100, "n_accept_total": 40}) == 0.4
    assert _compute_taux_admission({"n_can_pp": 50, "n_accept_total": 50}) == 1.0
    assert _compute_taux_admission({"n_can_pp": 200, "n_accept_total": 0}) == 0.0


def test_taux_admission_zero_candidates():
    assert _compute_taux_admission({"n_can_pp": 0, "n_accept_total": 2}) is None
    assert _compute_taux_admission({"n_can_pp": None, "n_accept_total": 2}) is None
