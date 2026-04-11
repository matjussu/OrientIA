"""Tests for src/eval/fact_check.py — automatic citation verification.

The fact-check scorer extracts verifiable claims from a free-form answer
(ONISEP IDs, Parcoursup percentages, school names, report/study mentions)
and cross-checks them against the retrieved fiches (for our_rag) or the
full dataset (for mistral_raw / chatgpt). The result is a ratio in [0, 1]
that can post-weight the Claude judge's sourçage score in judge v2.
"""
from src.eval.fact_check import (
    Claim,
    ClaimType,
    extract_claims,
    verify_claim,
    fact_check_score,
)


# --- extract_claims ---


def test_extract_onisep_id_full_format():
    claims = extract_claims("Voir la fiche ONISEP FOR.1577 pour plus de détails.")
    ids = [c for c in claims if c.type == ClaimType.ONISEP_ID]
    assert any(c.value == "1577" for c in ids)


def test_extract_onisep_id_url_format():
    text = "Source : https://www.onisep.fr/formation/slug/FOR.9891"
    claims = extract_claims(text)
    ids = [c for c in claims if c.type == ClaimType.ONISEP_ID]
    assert any(c.value == "9891" for c in ids)


def test_extract_percentage_with_unit():
    claims = extract_claims("Le taux d'accès est de 23% pour ce BTS.")
    pcts = [c for c in claims if c.type == ClaimType.PERCENTAGE]
    assert any(23.0 == c.value for c in pcts)


def test_extract_multiple_percentages():
    claims = extract_claims("TB 45%, B 30%, boursiers 20% et taux accès 75%")
    pcts = [c for c in claims if c.type == ClaimType.PERCENTAGE]
    values = sorted(c.value for c in pcts)
    assert values == [20.0, 30.0, 45.0, 75.0]


def test_extract_report_reference():
    claims = extract_claims(
        "Selon le rapport ANSSI 2023, la cybersécurité est prioritaire."
    )
    reports = [c for c in claims if c.type == ClaimType.REPORT]
    assert len(reports) >= 1
    assert any("ANSSI" in c.value for c in reports)


def test_extract_school_name_from_dataset():
    dataset = [
        {"etablissement": "EPITA", "nom": "Master Cyber"},
        {"etablissement": "Université de Rennes", "nom": "Master IA"},
    ]
    claims = extract_claims(
        "EPITA propose un master cyber très reconnu.", dataset=dataset
    )
    schools = [c for c in claims if c.type == ClaimType.SCHOOL]
    assert any(c.value.lower() == "epita" for c in schools)


def test_extract_ignores_plain_numbers_without_percent():
    claims = extract_claims("L'année 2023 a vu 1577 étudiants inscrits.")
    pcts = [c for c in claims if c.type == ClaimType.PERCENTAGE]
    assert not pcts


# --- verify_claim ---


def test_verify_onisep_id_matches_retrieved():
    retrieved = [
        {
            "fiche": {
                "url_onisep": "https://www.onisep.fr/formation/slug/FOR.1577",
                "nom": "BTS Cyber",
            }
        }
    ]
    claim = Claim(type=ClaimType.ONISEP_ID, value="1577", raw="ONISEP FOR.1577")
    assert verify_claim(claim, retrieved, dataset=[]) == "verified"


def test_verify_onisep_id_not_in_retrieved_but_in_dataset():
    retrieved = []
    dataset = [{"url_onisep": "https://www.onisep.fr/formation/slug/FOR.9891"}]
    claim = Claim(type=ClaimType.ONISEP_ID, value="9891", raw="ONISEP FOR.9891")
    assert verify_claim(claim, retrieved, dataset=dataset) == "verified"


def test_verify_onisep_id_unknown():
    retrieved = [{"fiche": {"url_onisep": "FOR.1234"}}]
    claim = Claim(type=ClaimType.ONISEP_ID, value="9999", raw="ONISEP FOR.9999")
    assert verify_claim(claim, retrieved, dataset=[]) == "unverifiable"


def test_verify_school_in_retrieved():
    retrieved = [{"fiche": {"etablissement": "EPITA", "nom": "X"}}]
    claim = Claim(type=ClaimType.SCHOOL, value="EPITA", raw="EPITA")
    assert verify_claim(claim, retrieved, dataset=[]) == "verified"


def test_verify_school_in_dataset_only():
    retrieved = []
    dataset = [{"etablissement": "Université de Rennes", "nom": "Master"}]
    claim = Claim(type=ClaimType.SCHOOL, value="Université de Rennes", raw="")
    assert verify_claim(claim, retrieved, dataset=dataset) == "verified"


def test_verify_school_unknown():
    retrieved = [{"fiche": {"etablissement": "EPITA"}}]
    claim = Claim(type=ClaimType.SCHOOL, value="Université Imaginaire", raw="")
    assert verify_claim(claim, retrieved, dataset=[]) == "unverifiable"


def test_verify_report_always_unverifiable():
    """We can't verify external reports (no ground-truth source) — mark as
    unverifiable. This is what penalizes mistral_raw's fabricated citations
    like 'rapport ANSSI 2023'."""
    claim = Claim(type=ClaimType.REPORT, value="ANSSI 2023", raw="rapport ANSSI 2023")
    assert verify_claim(claim, [], dataset=[]) == "unverifiable"


def test_verify_percentage_matches_taux():
    retrieved = [
        {"fiche": {"taux_acces_parcoursup_2025": 23.0, "nom": "BTS"}}
    ]
    claim = Claim(type=ClaimType.PERCENTAGE, value=23.0, raw="taux 23%")
    assert verify_claim(claim, retrieved, dataset=[]) == "verified"


def test_verify_percentage_within_tolerance():
    retrieved = [{"fiche": {"taux_acces_parcoursup_2025": 23.0}}]
    claim = Claim(type=ClaimType.PERCENTAGE, value=24.0, raw="~24%")
    assert verify_claim(claim, retrieved, dataset=[], pct_tolerance=2.0) == "verified"


def test_verify_percentage_beyond_tolerance():
    retrieved = [{"fiche": {"taux_acces_parcoursup_2025": 23.0}}]
    claim = Claim(type=ClaimType.PERCENTAGE, value=75.0, raw="75%")
    assert verify_claim(retrieved=retrieved, dataset=[], claim=claim) == "unverifiable"


# --- fact_check_score ---


def test_fact_check_score_perfect_match():
    retrieved = [
        {
            "fiche": {
                "etablissement": "EPITA",
                "url_onisep": "https://onisep.fr/FOR.1577",
                "taux_acces_parcoursup_2025": 18.0,
            }
        }
    ]
    answer = "EPITA propose un BTS cyber, taux d'accès 18%. Source ONISEP FOR.1577"
    score = fact_check_score(answer, retrieved=retrieved, dataset=[])
    assert score >= 0.75  # at least 3 of 3+ claims verified


def test_fact_check_score_fabricated_citation_low():
    """Mistral_raw cites 'rapport ANSSI 2023' and fake percentages that
    don't match any retrieved fiche — should score low."""
    answer = (
        "Selon le rapport ANSSI 2023, le taux d'admission à l'École "
        "Cyber Élite est de 87%."
    )
    score = fact_check_score(answer, retrieved=[], dataset=[])
    assert score <= 0.25


def test_fact_check_score_no_claims_returns_one():
    """Empty-claim answers get a neutral 1.0 (nothing to penalize).

    This prevents penalizing qualitative / conceptual answers that don't
    need to cite anything."""
    answer = "Il est important de bien choisir sa formation."
    score = fact_check_score(answer, retrieved=[], dataset=[])
    assert score == 1.0


def test_fact_check_score_mixed_verified_and_invented():
    retrieved = [{"fiche": {"etablissement": "EPITA", "url_onisep": "FOR.1577"}}]
    answer = (
        "EPITA est une bonne école (Source: ONISEP FOR.1577). "
        "Selon le rapport Cyber France 2024, le taux est de 95%."
    )
    score = fact_check_score(answer, retrieved=retrieved, dataset=[])
    # ~2 verified (EPITA + FOR.1577), ~2 unverified (report + 95%) → ~0.5
    assert 0.3 <= score <= 0.7
