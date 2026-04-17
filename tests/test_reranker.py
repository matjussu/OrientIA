from src.rag.reranker import RerankConfig, rerank


# --- Label boost tests (unchanged from plan) ---

def test_rerank_boosts_secnumedu():
    results = [
        {"fiche": {"labels": ["SecNumEdu"], "statut": "Public"}, "score": 0.5, "base_score": 0.5},
        {"fiche": {"labels": [], "statut": "Privé"}, "score": 0.6, "base_score": 0.6},
    ]
    cfg = RerankConfig(secnumedu_boost=1.5, cti_boost=1.0, public_boost=1.0,
                       level_boost_bac5=1.0, level_boost_bac3=1.0)
    reranked = rerank(results, cfg)
    assert reranked[0]["fiche"]["labels"] == ["SecNumEdu"]
    assert reranked[0]["score"] > reranked[1]["score"]


def test_rerank_with_no_boost_keeps_order_if_equal():
    results = [
        {"fiche": {"labels": [], "statut": "Public"}, "score": 0.5, "base_score": 0.5},
        {"fiche": {"labels": [], "statut": "Public"}, "score": 0.4, "base_score": 0.4},
    ]
    cfg = RerankConfig(secnumedu_boost=1.0, cti_boost=1.0, public_boost=1.0,
                       level_boost_bac5=1.0, level_boost_bac3=1.0)
    reranked = rerank(results, cfg)
    assert reranked[0]["score"] == 0.5
    assert reranked[1]["score"] == 0.4


def test_rerank_public_boost_separates_public_from_private():
    results = [
        {"fiche": {"labels": [], "statut": "Public"}, "score": 0.5, "base_score": 0.5},
        {"fiche": {"labels": [], "statut": "Privé"}, "score": 0.55, "base_score": 0.55},
    ]
    cfg = RerankConfig(secnumedu_boost=1.0, cti_boost=1.0, public_boost=1.3,
                       level_boost_bac5=1.0, level_boost_bac3=1.0)
    reranked = rerank(results, cfg)
    assert reranked[0]["fiche"]["statut"] == "Public"


# --- New niveau boost tests ---

def test_rerank_bac5_boost_lifts_master_over_bts():
    results = [
        {"fiche": {"labels": [], "statut": "Public", "niveau": "bac+2"},
         "score": 0.60, "base_score": 0.60},  # BTS, good vector similarity
        {"fiche": {"labels": [], "statut": "Public", "niveau": "bac+5"},
         "score": 0.55, "base_score": 0.55},  # Master, slightly lower similarity
    ]
    cfg = RerankConfig(
        secnumedu_boost=1.0, cti_boost=1.0, public_boost=1.0,
        level_boost_bac5=1.15, level_boost_bac3=1.05,
    )
    reranked = rerank(results, cfg)
    # With bac+5 boost at 1.15: 0.55 * 1.15 = 0.6325 > 0.60 (BTS)
    assert reranked[0]["fiche"]["niveau"] == "bac+5", \
        f"bac+5 boost should lift Master over BTS, got {reranked[0]['fiche']['niveau']}"


def test_rerank_bac3_gets_smaller_boost_than_bac5():
    results = [
        {"fiche": {"labels": [], "statut": "Public", "niveau": "bac+3"},
         "score": 0.50, "base_score": 0.50},
        {"fiche": {"labels": [], "statut": "Public", "niveau": "bac+5"},
         "score": 0.50, "base_score": 0.50},
    ]
    cfg = RerankConfig(
        secnumedu_boost=1.0, cti_boost=1.0, public_boost=1.0,
        level_boost_bac5=1.15, level_boost_bac3=1.05,
    )
    reranked = rerank(results, cfg)
    # Same base score; bac+5 boost (1.15) > bac+3 boost (1.05) → bac+5 first
    assert reranked[0]["fiche"]["niveau"] == "bac+5"
    assert reranked[1]["fiche"]["niveau"] == "bac+3"


def test_rerank_niveau_none_gets_no_boost():
    results = [
        {"fiche": {"labels": [], "statut": "Public", "niveau": None},
         "score": 0.50, "base_score": 0.50},
        {"fiche": {"labels": [], "statut": "Public", "niveau": "bac+2"},
         "score": 0.49, "base_score": 0.49},
    ]
    cfg = RerankConfig(
        secnumedu_boost=1.0, cti_boost=1.0, public_boost=1.0,
        level_boost_bac5=1.15, level_boost_bac3=1.05,
    )
    reranked = rerank(results, cfg)
    # Both get multiplier 1.0, original order preserved
    assert reranked[0]["fiche"]["niveau"] is None
    assert reranked[1]["fiche"]["niveau"] == "bac+2"


def test_rerank_label_boost_still_dominates_niveau_boost():
    """Critical design check: the SecNumEdu boost (1.5) must win over the
    level boost (1.15). Otherwise the INRIA thesis is broken — we're
    supposed to prove that LABELS re-rank better than raw similarity.
    A bac+2 SecNumEdu formation must outrank a bac+5 unlabeled one when
    base scores are equal."""
    results = [
        {"fiche": {"labels": ["SecNumEdu"], "statut": "Privé", "niveau": "bac+2"},
         "score": 0.50, "base_score": 0.50},  # BTS SecNumEdu (unusual but possible)
        {"fiche": {"labels": [], "statut": "Privé", "niveau": "bac+5"},
         "score": 0.50, "base_score": 0.50},  # Master no label
    ]
    cfg = RerankConfig(
        secnumedu_boost=1.5, cti_boost=1.3, grade_master_boost=1.3,
        public_boost=1.1, level_boost_bac5=1.15, level_boost_bac3=1.05,
    )
    reranked = rerank(results, cfg)
    # 0.50 * 1.5 = 0.75 (SecNumEdu BTS)
    # 0.50 * 1.15 = 0.575 (unlabeled Master)
    assert "SecNumEdu" in reranked[0]["fiche"]["labels"], \
        "SecNumEdu boost must dominate level boost — INRIA thesis"


def test_rerank_config_as_dict_exports_all_fields():
    cfg = RerankConfig()
    d = cfg.as_dict()
    assert "secnumedu_boost" in d
    assert "cti_boost" in d
    assert "grade_master_boost" in d
    assert "public_boost" in d
    assert "level_boost_bac5" in d
    assert "level_boost_bac3" in d
    assert "etab_named_boost" in d


def test_rerank_etab_named_boost_lifts_named_over_empty():
    """Fiches with a populated etablissement rank above fiches with the
    same base score but empty etab (generic ONISEP diploma types)."""
    results = [
        {"fiche": {"labels": [], "statut": "Inconnu", "niveau": "bac+5",
                   "etablissement": ""},
         "score": 0.50, "base_score": 0.50},
        {"fiche": {"labels": [], "statut": "Inconnu", "niveau": "bac+5",
                   "etablissement": "EFREI Paris"},
         "score": 0.50, "base_score": 0.50},
    ]
    cfg = RerankConfig(
        secnumedu_boost=1.0, cti_boost=1.0, public_boost=1.0,
        level_boost_bac5=1.0, level_boost_bac3=1.0,
        etab_named_boost=1.1,
    )
    reranked = rerank(results, cfg)
    assert reranked[0]["fiche"]["etablissement"] == "EFREI Paris"


def test_rerank_etab_named_boost_does_not_dominate_labels():
    """A labeled generic diploma must still beat an unlabeled named school.
    Default etab_named (1.1) < default secnumedu (1.5)."""
    results = [
        {"fiche": {"labels": ["SecNumEdu"], "statut": "Inconnu", "niveau": "bac+5",
                   "etablissement": ""},
         "score": 0.50, "base_score": 0.50},
        {"fiche": {"labels": [], "statut": "Inconnu", "niveau": "bac+5",
                   "etablissement": "EPITA"},
         "score": 0.50, "base_score": 0.50},
    ]
    cfg = RerankConfig()  # defaults: secnumedu=1.5, etab_named=1.1
    reranked = rerank(results, cfg)
    # 0.5 * 1.5 * 1.15 = 0.8625 (labeled generic)
    # 0.5 * 1.1 * 1.15 = 0.63375 (unlabeled EPITA)
    assert "SecNumEdu" in reranked[0]["fiche"]["labels"]


def test_rerank_etab_named_boost_ignores_empty_string_and_whitespace():
    """Empty string and whitespace-only etablissement don't trigger the boost."""
    results = [
        {"fiche": {"labels": [], "statut": "Inconnu", "niveau": None,
                   "etablissement": ""},
         "score": 0.50, "base_score": 0.50},
        {"fiche": {"labels": [], "statut": "Inconnu", "niveau": None,
                   "etablissement": "   "},
         "score": 0.50, "base_score": 0.50},
    ]
    cfg = RerankConfig(
        secnumedu_boost=1.0, cti_boost=1.0, public_boost=1.0,
        level_boost_bac5=1.0, level_boost_bac3=1.0,
        etab_named_boost=1.5,
    )
    reranked = rerank(results, cfg)
    assert reranked[0]["score"] == 0.50
    assert reranked[1]["score"] == 0.50


# === Vague B — Parcoursup-rich boost (Stage D) ===


def _rich_fiche() -> dict:
    """A Parcoursup-rich fiche: has cod_aff_form + populated profil_admis."""
    return {
        "labels": [], "statut": "Inconnu", "niveau": "bac+3",
        "etablissement": "Lycée X", "cod_aff_form": "42156",
        "profil_admis": {
            "bac_type_pct": {"general": 80.0, "techno": 15.0, "pro": 5.0},
        },
    }


def _onisep_only_fiche() -> dict:
    """An ONISEP-only fiche: no cod_aff_form, no admission data."""
    return {
        "labels": [], "statut": "Inconnu", "niveau": "bac+3",
        "etablissement": "Lycée X",
        "rncp": "37989",
    }


def test_rerank_parcoursup_rich_lifts_over_onisep_only():
    """A Parcoursup-rich fiche must rank above an ONISEP-only fiche at
    equal base score — this is the key Vague B move to surface fiches
    with real chiffres instead of generic diploma types."""
    results = [
        {"fiche": _onisep_only_fiche(), "score": 0.50, "base_score": 0.50},
        {"fiche": _rich_fiche(), "score": 0.50, "base_score": 0.50},
    ]
    cfg = RerankConfig(
        secnumedu_boost=1.0, cti_boost=1.0, public_boost=1.0,
        level_boost_bac5=1.0, level_boost_bac3=1.0,
        etab_named_boost=1.0,
        parcoursup_rich_boost=1.2,
    )
    reranked = rerank(results, cfg)
    assert reranked[0]["fiche"].get("cod_aff_form") == "42156", \
        "Parcoursup-rich fiche must rank above ONISEP-only at equal base score"


def test_rerank_parcoursup_rich_requires_non_zero_profil():
    """cod_aff_form alone isn't enough — profil_admis must have at least one
    non-zero bac-type percentage (else all zero means data-poor and the
    boost would mislead the retrieval)."""
    zero_profil = {
        "labels": [], "statut": "Inconnu", "niveau": "bac+3",
        "etablissement": "Lycée X", "cod_aff_form": "42156",
        "profil_admis": {
            "bac_type_pct": {"general": 0.0, "techno": 0.0, "pro": 0.0},
        },
    }
    results = [{"fiche": zero_profil, "score": 0.50, "base_score": 0.50}]
    cfg = RerankConfig(
        secnumedu_boost=1.0, cti_boost=1.0, public_boost=1.0,
        level_boost_bac5=1.0, level_boost_bac3=1.0,
        etab_named_boost=1.0,
        parcoursup_rich_boost=1.2,
    )
    reranked = rerank(results, cfg)
    assert reranked[0]["score"] == 0.50, \
        "zero profil_admis should not trigger parcoursup_rich boost"


def test_rerank_parcoursup_rich_does_not_dominate_secnumedu():
    """SecNumEdu (default 1.5) must still dominate parcoursup_rich (default 1.2)
    — the INRIA label thesis is preserved."""
    rich = _rich_fiche()
    secnumedu_but_poor = {
        "labels": ["SecNumEdu"], "statut": "Inconnu", "niveau": "bac+3",
        "etablissement": "Lycée X",
        "rncp": "37989",  # ONISEP-only, no cod_aff_form
    }
    results = [
        {"fiche": rich, "score": 0.50, "base_score": 0.50},
        {"fiche": secnumedu_but_poor, "score": 0.50, "base_score": 0.50},
    ]
    cfg = RerankConfig()  # defaults: secnumedu=1.5, parcoursup_rich=1.2, etab=1.1
    reranked = rerank(results, cfg)
    # 0.5 * 1.5 * 1.1 * 1.05 = 0.866 (secnumedu + etab + bac+3)
    # 0.5 * 1.2 * 1.1 * 1.05 = 0.693 (rich + etab + bac+3)
    assert "SecNumEdu" in reranked[0]["fiche"]["labels"], \
        "SecNumEdu boost must still dominate parcoursup_rich (INRIA thesis preserved)"


def test_rerank_config_as_dict_includes_parcoursup_rich():
    cfg = RerankConfig()
    d = cfg.as_dict()
    assert "parcoursup_rich_boost" in d
    assert d["parcoursup_rich_boost"] == 1.2  # default


def test_rerank_parcoursup_rich_ignored_when_cod_aff_form_missing():
    """Even with populated profil_admis, no cod_aff_form = no boost
    (cod_aff_form is the citation anchor the LLM needs)."""
    fiche_no_code = {
        "labels": [], "statut": "Inconnu", "niveau": "bac+3",
        "etablissement": "Lycée X",
        "profil_admis": {
            "bac_type_pct": {"general": 80.0, "techno": 15.0, "pro": 5.0},
        },
    }
    results = [{"fiche": fiche_no_code, "score": 0.50, "base_score": 0.50}]
    cfg = RerankConfig(
        secnumedu_boost=1.0, cti_boost=1.0, public_boost=1.0,
        level_boost_bac5=1.0, level_boost_bac3=1.0,
        etab_named_boost=1.0,
        parcoursup_rich_boost=1.2,
    )
    reranked = rerank(results, cfg)
    assert reranked[0]["score"] == 0.50
