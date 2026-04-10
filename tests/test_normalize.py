from src.collect.normalize import normalize_name, normalize_city


def test_normalize_name_removes_accents_and_articles():
    assert normalize_name("Université de Rennes") == "universite rennes"
    assert normalize_name("École d'ingénieurs de Brest") == "ecole ingenieurs brest"
    assert normalize_name("INSA Centre-Val de Loire") == "insa centre val loire"


def test_normalize_name_collapses_whitespace():
    assert normalize_name("  Master    IA  ") == "master ia"


def test_normalize_city_lowercases_strips_accents():
    assert normalize_city("Saint-Étienne") == "saint etienne"
    assert normalize_city("PARIS") == "paris"
