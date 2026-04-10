from src.collect.niveau import infer_niveau


def test_bts_returns_bac2():
    assert infer_niveau("BTS CIEL Cybersécurité") == "bac+2"
    assert infer_niveau("BTS Services Informatiques aux Organisations") == "bac+2"


def test_but_returns_bac3():
    assert infer_niveau("BUT Informatique parcours cybersécurité") == "bac+3"
    assert infer_niveau("BUT R&T Réseaux") == "bac+3"


def test_bachelor_returns_bac3():
    assert infer_niveau("Bachelor Cybersécurité EFREI") == "bac+3"
    assert infer_niveau("Bachelor Ingénierie numérique spécialité Cybersécurité") == "bac+3"


def test_licence_returns_bac3():
    assert infer_niveau("Licence Informatique") == "bac+3"
    assert infer_niveau("Licence Pro Cybersécurité") == "bac+3"


def test_master_returns_bac5():
    assert infer_niveau("Master Cybersécurité") == "bac+5"
    assert infer_niveau("Master IA et Data Science") == "bac+5"
    assert infer_niveau("Mastère Spécialisé Cyber") == "bac+5"
    assert infer_niveau("MS Expert cybersécurité") == "bac+5"


def test_ingenieur_returns_bac5():
    assert infer_niveau("Ingénieur diplômé ENSIBS cybersécurité") == "bac+5"
    assert infer_niveau("Diplôme d'Ingénieur Télécom Paris") == "bac+5"


def test_unknown_returns_none():
    assert infer_niveau("Formation artisanale") is None
    assert infer_niveau("") is None


def test_empty_or_none_returns_none():
    assert infer_niveau("") is None
    assert infer_niveau(None) is None
