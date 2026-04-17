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


def test_attach_labels_manual_table_ignores_non_tech_domains():
    """Vague santé fix : the manual_labels.json is all cyber-oriented
    (SecNumEdu, CTI, CGE, Grade Master). It must NOT leak to santé
    or other non-tech domains just because the establishment is shared
    (e.g., Université de Limoges hosts both cyber AND PASS santé —
    the cyber label entry must only apply to the cyber fiche)."""
    from src.collect.merge import attach_labels
    fiches = [
        {"nom": "Licence PASS",
         "etablissement": "Université de Limoges",
         "ville": "Limoges", "domaine": "sante", "labels": []},
        {"nom": "Master Cybersécurité",
         "etablissement": "Université de Limoges",
         "ville": "Limoges", "domaine": "cyber", "labels": []},
    ]
    # etab_normalized must match the output of normalize_name (stopwords removed)
    manual = [
        {"etab_normalized": "universite limoges", "labels": ["SecNumEdu", "CTI"]}
    ]
    result = attach_labels(fiches, [], manual_table=manual)
    # The santé fiche must NOT receive SecNumEdu
    assert result[0]["domaine"] == "sante"
    assert "SecNumEdu" not in (result[0]["labels"] or [])
    # The cyber fiche correctly receives the manual labels
    assert "SecNumEdu" in result[1]["labels"]


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


# === Vague A — attach_debouches + attach_metadata integration in pipeline ===


def test_attach_debouches_injects_rome_codes_per_domain():
    from src.collect.merge import attach_debouches
    fiches = [
        {"nom": "Master Cyber", "domaine": "cyber"},
        {"nom": "Master IA", "domaine": "data_ia"},
    ]
    enriched = attach_debouches(fiches)
    cyber = enriched[0]["debouches"]
    data = enriched[1]["debouches"]
    assert len(cyber) == 9, f"cyber domain should have 9 ROME codes, got {len(cyber)}"
    assert len(data) == 6, f"data_ia domain should have 6 ROME codes, got {len(data)}"
    assert all("code_rome" in d and "libelle" in d for d in cyber)
    # Sanity: known cyber RSSI code must be present
    assert any(d["code_rome"] == "M1812" for d in cyber)


def test_attach_debouches_does_not_clobber_existing():
    from src.collect.merge import attach_debouches
    preset = [{"code_rome": "X9999", "libelle": "custom"}]
    fiches = [{"nom": "x", "domaine": "cyber", "debouches": preset}]
    enriched = attach_debouches(fiches)
    assert enriched[0]["debouches"] == preset, \
        "attach_debouches must not overwrite pre-existing debouches"


def test_attach_debouches_empty_for_missing_domain():
    from src.collect.merge import attach_debouches
    fiches = [{"nom": "Unclassified"}]
    enriched = attach_debouches(fiches)
    assert enriched[0]["debouches"] == []


def test_attach_metadata_populates_provenance_and_dates():
    from src.collect.merge import attach_metadata
    fiches = [{
        "nom": "M", "domaine": "cyber",
        "cod_aff_form": "42",
        "taux_acces_parcoursup_2025": 18.0,
        "url_onisep": "http://x", "type_diplome": "master",
        "labels": ["SecNumEdu"],
        "admission": {"session": 2025},
        "profil_admis": {"mentions_pct": {"tb": 45.0}},
        "debouches": [{"code_rome": "M1812", "libelle": "RSSI"}],
        "match_method": "rncp",
    }]
    enriched = attach_metadata(fiches, collection_date="2026-04-17")
    f = enriched[0]
    # provenance: maps each enriched field to its origin
    assert f["provenance"]["admission"] == "parcoursup_2025"
    assert f["provenance"]["profil_admis"] == "parcoursup_2025"
    assert f["provenance"]["debouches"] == "rome_4_0"
    assert f["provenance"]["type_diplome"] == "onisep"
    assert f["provenance"]["labels"] == "secnumedu+manual"
    # collected_at: date per source
    assert f["collected_at"]["parcoursup"] == "2026-04-17"
    assert f["collected_at"]["onisep"] == "2026-04-17"
    assert f["collected_at"]["rome"] == "2026-04-17"
    # merge_confidence: 1.0 for RNCP match
    assert f["merge_confidence"]["parcoursup"] == 1.0
    assert f["merge_confidence"]["onisep"] == 1.0


def test_attach_metadata_fuzzy_confidence_reflects_score():
    from src.collect.merge import attach_metadata
    fiches = [{
        "nom": "M", "domaine": "cyber",
        "url_onisep": "http://x",
        "taux_acces_parcoursup_2025": 30.0,
        "match_method": "fuzzy_87.5",
    }]
    enriched = attach_metadata(fiches, collection_date="2026-04-17")
    assert enriched[0]["merge_confidence"]["onisep"] == 0.88  # round(0.875, 2)


def test_attach_metadata_parcoursup_only_marks_onisep_null():
    from src.collect.merge import attach_metadata
    fiches = [{
        "nom": "M", "domaine": "cyber",
        "taux_acces_parcoursup_2025": 30.0,
        "match_method": "parcoursup_only",
    }]
    enriched = attach_metadata(fiches, collection_date="2026-04-17")
    # parcoursup_only = ONISEP was not joined; confidence.onisep must be null (=None)
    assert enriched[0]["merge_confidence"]["parcoursup"] == 1.0
    assert enriched[0]["merge_confidence"].get("onisep") is None
