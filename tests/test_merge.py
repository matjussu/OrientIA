from src.collect.merge import merge_by_rncp, fuzzy_match_fiches, merge_all


def test_merge_by_rncp_joins_matching_codes():
    parcoursup = [
        {"nom": "Master IA", "ville": "Paris", "rncp": "12345", "taux_acces_parcoursup_2025": 25.0},
    ]
    onisep = [
        {"nom": "Master Intelligence Artificielle", "ville": "Paris", "rncp": "12345",
         "url_onisep": "http://onisep.fr/x"},
    ]
    merged = merge_by_rncp(parcoursup, onisep)
    assert len(merged) == 1
    assert merged[0]["rncp"] == "12345"
    assert merged[0]["taux_acces_parcoursup_2025"] == 25.0
    assert merged[0]["url_onisep"] == "http://onisep.fr/x"


def test_fuzzy_match_joins_similar_names():
    parcoursup_orphans = [
        {"nom": "Master Cybersécurité", "etablissement": "ENSIBS",
         "ville": "Vannes", "rncp": None, "taux_acces_parcoursup_2025": 18.0},
    ]
    onisep_orphans = [
        {"nom": "Master cyber", "etablissement": "ensibs",
         "ville": "vannes", "rncp": None, "url_onisep": "http://x"},
    ]
    merged = fuzzy_match_fiches(parcoursup_orphans, onisep_orphans, threshold=75)
    assert len(merged) == 1
    assert merged[0]["url_onisep"] == "http://x"


def test_merge_all_attaches_secnumedu_labels():
    parcoursup = [{"nom": "Master Cyber", "etablissement": "ENSIBS", "ville": "Vannes",
                   "rncp": None, "taux_acces_parcoursup_2025": 22.0}]
    onisep = []
    secnumedu = [{"nom": "Master Cyber", "etablissement": "ENSIBS", "ville": "Vannes",
                  "labels": ["SecNumEdu"]}]
    merged = merge_all(parcoursup, onisep, secnumedu)
    assert len(merged) == 1
    assert "SecNumEdu" in merged[0]["labels"]


def test_attach_labels_establishment_only_fallback():
    # Different formation names but same establishment — the new fallback should catch it
    from src.collect.merge import attach_labels
    fiches = [
        {"nom": "BUT Informatique parcours cyber",
         "etablissement": "EFREI Bordeaux",
         "ville": "Bordeaux",
         "domaine": "cyber",
         "labels": []},
    ]
    secnumedu = [
        {"nom": "Bachelor Cybersécurité EFREI",
         "etablissement": "EFREI",
         "ville": "",
         "labels": ["SecNumEdu"]},
    ]
    result = attach_labels(fiches, secnumedu)
    assert "SecNumEdu" in result[0]["labels"], \
        f"expected SecNumEdu label via establishment fallback, got {result[0]['labels']}"


def test_attach_labels_fallback_only_fires_for_cyber_domain():
    from src.collect.merge import attach_labels
    fiches = [
        {"nom": "Master IA",
         "etablissement": "EFREI",
         "ville": "Paris",
         "domaine": "data_ia",  # NOT cyber
         "labels": []},
    ]
    secnumedu = [
        {"nom": "Bachelor EFREI",
         "etablissement": "EFREI",
         "ville": "",
         "labels": ["SecNumEdu"]},
    ]
    result = attach_labels(fiches, secnumedu)
    assert "SecNumEdu" not in (result[0]["labels"] or []), \
        "SecNumEdu label should not be attached to data_ia domain via the cyber-only fallback"
