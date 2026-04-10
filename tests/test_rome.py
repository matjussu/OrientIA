from src.collect.rome import load_rome_job_titles, get_debouches_for_domain


def test_load_rome_returns_code_to_title_mapping(tmp_path):
    csv = tmp_path / "rome.csv"
    csv.write_text(
        '"code_rome","code_fiche_metier","code_ogr","libelle_rome","transition_eco","transition_num","transition_demo","emploi_reglemente","emploi_cadre","code_rome_parent"\n'
        '"M1844","11","6","Analyste en cybersécurité","","","","","","M1844"\n'
        '"M1811","12","7","Data engineer","","","","","","M1811"\n',
        encoding="utf-8",
    )
    mapping = load_rome_job_titles(csv)
    assert mapping["M1844"] == "Analyste en cybersécurité"
    assert mapping["M1811"] == "Data engineer"


def test_get_debouches_for_cyber_returns_rome_codes():
    debouches = get_debouches_for_domain("cyber")
    assert len(debouches) >= 5
    codes = [d["code_rome"] for d in debouches]
    assert "M1844" in codes  # Analyste en cybersécurité
    assert "M1812" in codes  # RSSI
    for d in debouches:
        assert d["libelle"]


def test_get_debouches_for_data_ia_returns_rome_codes():
    debouches = get_debouches_for_domain("data_ia")
    assert len(debouches) >= 3
    codes = [d["code_rome"] for d in debouches]
    assert "M1405" in codes  # Data scientist
    assert "M1811" in codes  # Data engineer


def test_get_debouches_for_unknown_domain_raises():
    import pytest
    with pytest.raises(KeyError):
        get_debouches_for_domain("unknown_domain")
