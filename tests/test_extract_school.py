from src.collect.onisep import extract_school_from_formation_name


def test_extracts_school_from_parens_suffix():
    assert extract_school_from_formation_name("bachelor cybersécurité (EPITA)") == "EPITA"
    assert extract_school_from_formation_name("bachelor en sciences et ingénierie - cybersécurité (ISEN)") == "ISEN"


def test_extracts_school_from_de_lapostrophe_pattern():
    assert extract_school_from_formation_name("ingénieur diplômé de l'ENSIBS spécialité cybersécurité") == "ENSIBS"


def test_extracts_school_from_de_pattern():
    # "de Télécom Nancy de l'université de Lorraine" — first pattern wins
    result = extract_school_from_formation_name(
        "diplôme d'ingénieur de Télécom Nancy de l'université de Lorraine"
    )
    assert result is not None
    assert "Télécom Nancy" in result or "Nancy" in result


def test_returns_none_for_generic_name():
    assert extract_school_from_formation_name("expert en cybersécurité des systèmes d'information") is None
    assert extract_school_from_formation_name("bachelor cybersécurité et gestion des réseaux") is None


def test_returns_none_for_empty_or_none():
    assert extract_school_from_formation_name("") is None
    assert extract_school_from_formation_name(None) is None
