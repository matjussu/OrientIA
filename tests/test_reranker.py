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
