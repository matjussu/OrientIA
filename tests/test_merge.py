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


def test_attach_labels_manual_table_labels_known_school():
    from src.collect.merge import attach_labels
    fiches = [
        {"nom": "Ingénieur Cybersécurité", "etablissement": "ENSIBS",
         "ville": "Vannes", "domaine": "cyber", "labels": []},
    ]
    manual = [{"etab_normalized": "ensibs", "labels": ["SecNumEdu", "CTI"]}]
    result = attach_labels(fiches, [], manual_table=manual)
    assert "SecNumEdu" in result[0]["labels"]
    assert "CTI" in result[0]["labels"]


def test_attach_labels_manual_table_explicitly_blocks_unlabeled_school():
    from src.collect.merge import attach_labels
    fiches = [
        {"nom": "Master Cyber", "etablissement": "EPITA Paris",
         "ville": "Paris", "domaine": "cyber", "labels": []},
    ]
    manual = [{"etab_normalized": "epita", "labels": []}]
    # Empty secnumedu list so stages 1/2 can't fire
    result = attach_labels(fiches, [], manual_table=manual)
    assert result[0]["labels"] == []  # Correctly no label attached


def test_attach_labels_manual_table_overrides_earlier_stages():
    """Manual table must override labels from Stages 1/2.

    Before this fix, Stage 3 only appended to existing_labels, so a fuzzy
    match in Stage 1 could attach SecNumEdu to an EPITA fiche and Stage 3's
    blocklist entry wouldn't remove it.
    """
    from src.collect.merge import attach_labels
    fiches = [
        {"nom": "bachelor cybersecurite epita",
         "etablissement": "EPITA",
         "ville": "Paris", "domaine": "cyber", "labels": []},
    ]
    # Non-empty SecNumEdu list with a near-identical entry — will match Stage 1
    secnumedu = [
        {"nom": "bachelor cybersecurite epita",
         "etablissement": "EPITA",
         "ville": "Paris",
         "labels": ["SecNumEdu"]},
    ]
    manual = [{"etab_normalized": "epita", "labels": []}]
    result = attach_labels(fiches, secnumedu, manual_table=manual)
    assert result[0]["labels"] == [], \
        f"EPITA manual blocklist didn't override Stage 1 match: got {result[0]['labels']}"


def test_attach_labels_manual_table_replaces_not_appends():
    """Manual-table labels REPLACE prior labels (they don't merge)."""
    from src.collect.merge import attach_labels
    fiches = [
        {"nom": "bachelor cybersecurite efrei",
         "etablissement": "EFREI Bordeaux",
         "ville": "Bordeaux", "domaine": "cyber", "labels": ["SomeStaleLabel"]},
    ]
    manual = [{"etab_normalized": "efrei", "labels": ["SecNumEdu", "CTI"]}]
    result = attach_labels(fiches, [], manual_table=manual)
    # Final labels must be exactly what the manual table says (order-insensitive),
    # not the union of stale + manual labels
    assert set(result[0]["labels"]) == {"SecNumEdu", "CTI"}
    assert "SomeStaleLabel" not in result[0]["labels"]


def test_attach_labels_manual_table_substring_match_both_ways():
    from src.collect.merge import attach_labels
    # Fiche etab is longer than manual entry ("telecom paris" in "telecom paris institut")
    fiches1 = [{"nom": "MS Cyber", "etablissement": "Télécom Paris Institut",
                "ville": "Palaiseau", "domaine": "cyber", "labels": []}]
    manual = [{"etab_normalized": "telecom paris", "labels": ["SecNumEdu"]}]
    result = attach_labels(fiches1, [], manual_table=manual)
    assert "SecNumEdu" in result[0]["labels"]

    # Fiche etab is shorter than manual entry ("efrei" in "efrei paris")
    fiches2 = [{"nom": "Bachelor", "etablissement": "EFREI",
                "ville": "Villejuif", "domaine": "cyber", "labels": []}]
    manual2 = [{"etab_normalized": "efrei paris pantheon", "labels": ["SecNumEdu"]}]
    result2 = attach_labels(fiches2, [], manual_table=manual2)
    assert "SecNumEdu" in result2[0]["labels"]
