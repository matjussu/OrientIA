"""Tests règles de PRÉSENCE V4."""
from __future__ import annotations

import pytest

from src.validator.presence import PRESENCE_RULES, PresenceWarning, check_presence


def test_no_topic_mentioned_no_warning():
    """Si aucun topic détecté (texte sur maths pure), aucun warning."""
    txt = "Pour révéler un polynôme, factorise d'abord."
    assert check_presence(txt) == []


def test_PASS_without_redoublement_info_flagged():
    txt = "Le PASS est une voie exigeante, il faut bien travailler."
    warnings = check_presence(txt)
    assert any(w.topic == "PASS_redoublement_info" for w in warnings)


def test_PASS_with_redoublement_interdit_ok():
    txt = (
        "Le PASS est exigeant. Attention : le redoublement est interdit "
        "(arrêté 4 novembre 2019)."
    )
    warnings = check_presence(txt)
    assert not any(w.topic == "PASS_redoublement_info" for w in warnings)


def test_PASS_with_une_seule_chance_ok():
    txt = "En PASS, tu n'as qu'une seule chance en PASS avant bascule L.AS."
    warnings = check_presence(txt)
    assert not any(w.topic == "PASS_redoublement_info" for w in warnings)


def test_HEC_without_AST_flagged():
    txt = "Pour HEC, prépa ECG obligatoire puis concours BCE."
    warnings = check_presence(txt)
    assert any(w.topic == "HEC_admission_info" for w in warnings)


def test_HEC_with_AST_ok():
    txt = "HEC recrute aussi via AST (Admission sur Titres) à bac+3/4."
    warnings = check_presence(txt)
    assert not any(w.topic == "HEC_admission_info" for w in warnings)


def test_kine_without_IFMK_flagged():
    txt = "Pour devenir kiné, il faut viser les écoles kiné de ta région."
    warnings = check_presence(txt)
    assert any(w.topic == "kine_IFMK_info" for w in warnings)


def test_kine_with_IFMK_ok():
    txt = "Kiné se prépare en IFMK après PASS/L.AS/STAPS."
    warnings = check_presence(txt)
    assert not any(w.topic == "kine_IFMK_info" for w in warnings)


def test_parcoursup_taux_without_nuance_flagged():
    txt = "Taux d'accès Parcoursup de 46% pour cette formation."
    warnings = check_presence(txt)
    assert any(w.topic == "parcoursup_taux_info" for w in warnings)


def test_parcoursup_taux_with_rang_dernier_ok():
    txt = (
        "Taux d'accès Parcoursup 46% — rang du dernier candidat appelé, "
        "pas le taux d'admission stricto sensu."
    )
    warnings = check_presence(txt)
    assert not any(w.topic == "parcoursup_taux_info" for w in warnings)


# --- Registre ---


def test_registry_has_expected_topics():
    ids = {r["topic_id"] for r in PRESENCE_RULES}
    assert ids == {
        "PASS_redoublement_info",
        "HEC_admission_info",
        "kine_IFMK_info",
        "parcoursup_taux_info",
    }


def test_warning_dataclass_shape():
    txt = "PASS est exigeant."
    warnings = check_presence(txt)
    assert warnings
    w = warnings[0]
    assert isinstance(w, PresenceWarning)
    assert w.topic and w.message and w.missing_pattern_label
