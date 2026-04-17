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


# === Santé D.E. (Diplôme d'État) et DTS — ajout qualité V ===


def test_de_infirmier_returns_bac3():
    assert infer_niveau("D.E Infirmier") == "bac+3"
    assert infer_niveau("D.E. Infirmier - Réservé aux personnes en situation de handicap") == "bac+3"
    assert infer_niveau("D.E Ergothérapeute") == "bac+3"
    assert infer_niveau("D.E Pédicure-Podologue") == "bac+3"
    assert infer_niveau("D.E Psychomotricien") == "bac+3"
    assert infer_niveau("D.E Technicien de Laboratoire Médical") == "bac+3"
    assert infer_niveau("D.E manipulateur/trice en électroradiologie médicale") == "bac+3"


def test_de_long_medical_returns_bac5():
    """Kiné (DEMK) et orthophoniste et sage-femme sont passés à 5 ans."""
    assert infer_niveau("D.E Masseur-Kinésithérapeute") == "bac+5"
    assert infer_niveau("DEMK") == "bac+5"
    assert infer_niveau("D.E Orthophoniste") == "bac+5"
    assert infer_niveau("D.E Sage-Femme") == "bac+5"
    assert infer_niveau("D.E de maïeutique") == "bac+5"


def test_dts_imagerie_medicale_returns_bac3():
    assert infer_niveau("DTS Imagerie médicale et radiologie thérapeutique") == "bac+3"


def test_certificat_capacite_orthoptiste_returns_bac3():
    assert infer_niveau("Certificat de capacité d'Orthoptiste") == "bac+3"
    assert infer_niveau("Certificat de capacité d'Audioprothésiste") == "bac+3"


def test_pass_las_returns_bac3():
    """PASS et L.AS entrent dans le cursus licence — niveau bac+3 pour le reranker."""
    assert infer_niveau("Licence - Parcours d'Accès Spécifique Santé (PASS)") == "bac+3"
    assert infer_niveau("PASS") == "bac+3"
    assert infer_niveau("Licence - L.AS Sciences biomédicales") == "bac+3"
    assert infer_niveau("Licence L.AS biologie") == "bac+3"
