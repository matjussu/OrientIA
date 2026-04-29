"""Tests pour scripts/judge_faithfulness.py — Sprint 11 P0 Item 3.

Couvre :
1. Ground truth OBLIGATOIRE (Q5 IFSI / Q8 DEAMP / Q10 Terminale L) — 3 hallu
   réelles audit Matteo doivent être détectées (score < 0.5). Sinon FAIL.
2. Cas clean synthétiques — score ≥ 0.8.
3. Edge cases mocked (subprocess timeout / returncode != 0 / VERDICT pattern
   not matched / ELEMENTS JSON malformed / JUSTIFICATION absent / réponse
   vide / fiches vides / claude CLI not found) — fallback graceful sans crash.
4. Parser unit tests (_parse_judge_output, _score_from_parsed,
   build_fiches_text).

Tests réels appelant Haiku via subprocess : skippables via
`OFFLINE_JUDGE_TESTS=1 pytest tests/test_judge_faithfulness.py` pour itération
rapide. Coût : ~$0.001 × 5 tests = $0.005 + ~3 min wall-clock.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.judge_faithfulness import (
    DEFAULT_MODEL,
    FaithfulnessVerdict,
    _parse_judge_output,
    _score_from_parsed,
    build_fiches_text,
    fiche_to_text,
    judge_faithfulness,
)


SKIP_REAL = os.environ.get("OFFLINE_JUDGE_TESTS") == "1"
skip_real = pytest.mark.skipif(
    SKIP_REAL,
    reason="OFFLINE_JUDGE_TESTS=1 — skipping real Haiku calls",
)


# ============================================================================
# Helpers : load chantier E ground truth from real test serving JSONL
# ============================================================================

ROOT = Path(__file__).resolve().parents[1]
JSONL_PATH = ROOT / "docs" / "sprint10-E-raw-results-2026-04-29.jsonl"
FICHES_PATH = ROOT / "data" / "processed" / "formations_unified.json"

# 0-indexed in JSONL
GT_QID_Q5_IFSI = 4
GT_QID_Q8_DEAMP = 7
GT_QID_Q10_TERMINALE_L = 9


@pytest.fixture(scope="module")
def chantier_e_records():
    """Charge les 10 résultats du test serving chantier E (Sprint 10)."""
    if not JSONL_PATH.exists():
        pytest.skip(f"Ground truth JSONL absent : {JSONL_PATH}")
    return [json.loads(line) for line in JSONL_PATH.read_text().splitlines() if line.strip()]


@pytest.fixture(scope="module")
def fiches_lookup():
    """Charge formations_unified.json indexé par id pour reconstruire le contexte fiches."""
    if not FICHES_PATH.exists():
        pytest.skip(f"Fiches unified absent : {FICHES_PATH}")
    fiches = json.loads(FICHES_PATH.read_text())
    return {fi.get("id") or fi.get("identifiant"): fi for fi in fiches}


def _resolve_fiches(record: dict, lookup: dict, max_n: int = 5) -> list[dict]:
    """Reconstruit les fiches retrieved à partir des fiche_id du record JSONL."""
    seen, out = set(), []
    for s in record.get("sources", []):
        fid = s.get("fiche_id")
        if fid and fid in lookup and fid not in seen:
            seen.add(fid)
            out.append(lookup[fid])
            if len(out) >= max_n:
                break
    return out


# ============================================================================
# 1. GROUND TRUTH OBLIGATOIRE — 3 hallu Matteo doivent être détectées
# ============================================================================

@skip_real
def test_ground_truth_q5_ifsi_hallu_detected(chantier_e_records, fiches_lookup):
    """Q5 PASS : la réponse mentionne 'IFSI concours post-bac' → hallu (admission Parcoursup dossier depuis 2019)."""
    record = chantier_e_records[GT_QID_Q5_IFSI]
    fiches = _resolve_fiches(record, fiches_lookup)
    verdict = judge_faithfulness(record["question"], record["answer"], fiches)

    assert verdict.error is None, f"Subprocess error: {verdict.error}"
    assert verdict.raw_verdict == "INFIDELE", \
        f"Expected INFIDELE, got {verdict.raw_verdict}: {verdict.justification}"
    assert verdict.score < 0.5, f"Score {verdict.score} >= 0.5 (ground truth must be detected)"
    assert len(verdict.flagged_entities) >= 1, "At least one element must be flagged"


@skip_real
def test_ground_truth_q8_deamp_hallu_detected(chantier_e_records, fiches_lookup):
    """Q8 reconversion : la réponse mentionne 'DEAMP' → diplôme fantôme (fusionné DEAES en 2016)."""
    record = chantier_e_records[GT_QID_Q8_DEAMP]
    fiches = _resolve_fiches(record, fiches_lookup)
    verdict = judge_faithfulness(record["question"], record["answer"], fiches)

    assert verdict.error is None, f"Subprocess error: {verdict.error}"
    assert verdict.raw_verdict == "INFIDELE", \
        f"Expected INFIDELE, got {verdict.raw_verdict}: {verdict.justification}"
    assert verdict.score < 0.5, f"Score {verdict.score} >= 0.5 (ground truth must be detected)"


@skip_real
def test_ground_truth_q10_terminale_l_hallu_detected(chantier_e_records, fiches_lookup):
    """Q10 Terminale L : série supprimée depuis réforme bac 2021 → hallu d'accepter le cadrage."""
    record = chantier_e_records[GT_QID_Q10_TERMINALE_L]
    fiches = _resolve_fiches(record, fiches_lookup)
    verdict = judge_faithfulness(record["question"], record["answer"], fiches)

    assert verdict.error is None, f"Subprocess error: {verdict.error}"
    assert verdict.raw_verdict == "INFIDELE", \
        f"Expected INFIDELE, got {verdict.raw_verdict}: {verdict.justification}"
    assert verdict.score < 0.5, f"Score {verdict.score} >= 0.5 (ground truth must be detected)"


# ============================================================================
# 2. CAS CLEAN SYNTHÉTIQUES — score ≥ 0.8 attendu
# ============================================================================

@skip_real
def test_clean_short_answer_directly_sourced():
    """Réponse trivialement sourcée : 1 fait, 1 fiche, 1:1 mapping."""
    question = "Quelle est la durée de la PASS à Lille ?"
    answer = "La PASS à l'Université de Lille est une licence d'1 an."
    fiches = [{
        "id": "parcoursup-X",
        "nom": "Licence - Parcours d'Accès Spécifique Santé (PASS)",
        "etablissement": "Université de Lille",
        "type_diplome": "Licence",
        "duree": "1 an",
        "ville": "Lille",
    }]
    verdict = judge_faithfulness(question, answer, fiches)
    assert verdict.error is None
    assert verdict.raw_verdict == "FIDELE", \
        f"Expected FIDELE, got {verdict.raw_verdict}: {verdict.justification}"
    assert verdict.score >= 0.8, f"Score {verdict.score} < 0.8 (clean case)"


@skip_real
def test_clean_explicit_advice_only():
    """Réponse 100% conseil sans affirmation factuelle → ne doit rien flagger."""
    question = "Comment me préparer pour Parcoursup ?"
    answer = (
        "Soigne ton projet motivé : décris tes intérêts et tes expériences. "
        "Prends rendez-vous avec le Psy-EN de ton lycée pour affiner ton projet."
    )
    fiches = [{
        "id": "parcoursup-X",
        "nom": "Licence Sciences",
        "etablissement": "Université Y",
        "type_diplome": "Licence",
    }]
    verdict = judge_faithfulness(question, answer, fiches)
    assert verdict.error is None
    assert verdict.raw_verdict == "FIDELE", \
        f"Expected FIDELE for advice-only, got {verdict.raw_verdict}: {verdict.justification}"
    assert verdict.score >= 0.8


# ============================================================================
# 3. EDGE CASES — fallback graceful sans crash, sans appel réseau
# ============================================================================

def test_edge_empty_answer_returns_fidele():
    """Answer vide → FIDELE 1.0 (rien à juger), pas d'appel subprocess."""
    verdict = judge_faithfulness("question?", "", fiches=[])
    assert verdict.score == 1.0
    assert verdict.raw_verdict == "FIDELE"
    assert verdict.error is None
    assert verdict.flagged_entities == []


def test_edge_whitespace_only_answer_returns_fidele():
    """Answer whitespace → traité comme vide."""
    verdict = judge_faithfulness("question?", "   \n\t  ", fiches=[])
    assert verdict.score == 1.0
    assert verdict.raw_verdict == "FIDELE"


def test_edge_subprocess_timeout_returns_neutral():
    """Subprocess timeout → score 0.5 + error message, pas de crash."""
    with patch("scripts.judge_faithfulness.subprocess.run") as m:
        m.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=120)
        verdict = judge_faithfulness("Q?", "A.", fiches=[{"nom": "X"}])
    assert verdict.score == 0.5
    assert verdict.raw_verdict == "UNKNOWN"
    assert verdict.error == "timeout"


def test_edge_subprocess_returncode_non_zero_returns_neutral():
    """returncode != 0 → score 0.5 + error avec stderr."""
    class FakeResult:
        returncode = 1
        stdout = ""
        stderr = "auth failed"
    with patch("scripts.judge_faithfulness.subprocess.run", return_value=FakeResult()):
        verdict = judge_faithfulness("Q?", "A.", fiches=[{"nom": "X"}])
    assert verdict.score == 0.5
    assert verdict.raw_verdict == "UNKNOWN"
    assert verdict.error and "returncode=1" in verdict.error
    assert "auth failed" in verdict.error


def test_edge_claude_cli_not_found_returns_neutral():
    """FileNotFoundError (CLI absent) → score 0.5 + error explicite."""
    with patch("scripts.judge_faithfulness.subprocess.run", side_effect=FileNotFoundError()):
        verdict = judge_faithfulness("Q?", "A.", fiches=[{"nom": "X"}])
    assert verdict.score == 0.5
    assert verdict.raw_verdict == "UNKNOWN"
    assert verdict.error == "claude CLI not found in PATH"


def test_edge_verdict_pattern_not_matched():
    """Output juge sans VERDICT → UNKNOWN + parse_errors documentés."""
    fake_raw = "Désolé, je ne peux pas évaluer cette réponse."
    parsed = _parse_judge_output(fake_raw)
    assert parsed["verdict"] == "UNKNOWN"
    assert "VERDICT pattern not matched in output" in parsed["parse_errors"]
    assert _score_from_parsed(parsed) == 0.5


def test_edge_elements_json_malformed_falls_back_to_regex():
    """ELEMENTS JSON malformé (quotes manquantes) → fallback regex extract strings."""
    fake_raw = (
        'VERDICT: INFIDELE\n'
        'ELEMENTS_NON_FOUND: ["claim un", "claim "deux" mal échappé"]\n'
        'JUSTIFICATION: Test fallback.'
    )
    parsed = _parse_judge_output(fake_raw)
    assert parsed["verdict"] == "INFIDELE"
    assert any("ELEMENTS JSON decode failed" in e for e in parsed["parse_errors"])
    # Fallback regex must have extracted at least one quoted string
    assert len(parsed["elements"]) >= 1


def test_edge_justification_missing():
    """JUSTIFICATION absent → empty string + parse_errors notés, verdict reste utilisable."""
    fake_raw = 'VERDICT: FIDELE\nELEMENTS_NON_FOUND: []'
    parsed = _parse_judge_output(fake_raw)
    assert parsed["verdict"] == "FIDELE"
    assert parsed["justification"] == ""
    assert "JUSTIFICATION section not found" in parsed["parse_errors"]
    assert _score_from_parsed(parsed) == 1.0  # FIDELE + 0 elements = 1.0 même sans justif


def test_edge_oui_non_alias_accepted():
    """VERDICT: OUI / NON acceptés en alias de FIDELE / INFIDELE."""
    raw_oui = 'VERDICT: OUI\nELEMENTS_NON_FOUND: []\nJUSTIFICATION: ok'
    raw_non = 'VERDICT: NON\nELEMENTS_NON_FOUND: ["x"]\nJUSTIFICATION: hallu'
    p_oui = _parse_judge_output(raw_oui)
    p_non = _parse_judge_output(raw_non)
    assert p_oui["verdict"] == "FIDELE"
    assert p_non["verdict"] == "INFIDELE"


def test_edge_empty_fiches_does_not_crash():
    """fiches=[] → build_fiches_text retourne un placeholder, judge call tente quand même."""
    text = build_fiches_text([])
    assert text == "(aucune fiche retournée par le RAG)"

    with patch("scripts.judge_faithfulness.subprocess.run") as m:
        class FakeResult:
            returncode = 0
            stdout = 'VERDICT: INFIDELE\nELEMENTS_NON_FOUND: ["X"]\nJUSTIFICATION: vide'
            stderr = ""
        m.return_value = FakeResult()
        verdict = judge_faithfulness("Q?", "A factuelle.", fiches=[])
    assert verdict.error is None
    assert verdict.raw_verdict == "INFIDELE"


def test_edge_numeric_claims_handled_by_parser():
    """Claims numériques entre quotes → parser extrait correctement."""
    fake_raw = (
        'VERDICT: INFIDELE\n'
        'ELEMENTS_NON_FOUND: ["27% admis EPF", "8000€/an", "95% insertion"]\n'
        'JUSTIFICATION: chiffres non sourcés.'
    )
    parsed = _parse_judge_output(fake_raw)
    assert parsed["verdict"] == "INFIDELE"
    assert len(parsed["elements"]) == 3
    assert "27% admis EPF" in parsed["elements"]


# ============================================================================
# 4. UNIT TESTS — parser, scoring, fiches helpers (no subprocess)
# ============================================================================

class TestScoring:
    def test_fidele_zero_elements_score_one(self):
        assert _score_from_parsed({"verdict": "FIDELE", "elements": []}) == 1.0

    def test_fidele_with_elements_score_07(self):
        assert _score_from_parsed({"verdict": "FIDELE", "elements": ["x"]}) == 0.7

    def test_infidele_one_element_below_05(self):
        assert _score_from_parsed({"verdict": "INFIDELE", "elements": ["x"]}) == 0.35

    def test_infidele_three_elements_score_005(self):
        s = _score_from_parsed({"verdict": "INFIDELE", "elements": ["a", "b", "c"]})
        assert s == pytest.approx(0.05, abs=1e-6)

    def test_infidele_many_elements_clamped_zero(self):
        assert _score_from_parsed({"verdict": "INFIDELE", "elements": ["a"] * 10}) == 0.0

    def test_unknown_neutral_05(self):
        assert _score_from_parsed({"verdict": "UNKNOWN", "elements": []}) == 0.5

    def test_infidele_zero_elements_doubt(self):
        """INFIDELE sans citation = douteux, score 0.4 (légèrement < 0.5)."""
        assert _score_from_parsed({"verdict": "INFIDELE", "elements": []}) == 0.4


class TestFichesText:
    def test_fiche_to_text_uses_nom(self):
        out = fiche_to_text({"nom": "Licence Maths", "etablissement": "Sorbonne"})
        assert "Licence Maths" in out
        assert "Sorbonne" in out

    def test_fiche_to_text_falls_back_to_title(self):
        out = fiche_to_text({"title": "Master Eco"})
        assert "Master Eco" in out

    def test_fiche_to_text_handles_missing_fields(self):
        out = fiche_to_text({})
        assert "?" in out  # nom fallback

    def test_build_fiches_text_dedupes_by_id(self):
        f1 = {"id": "A", "nom": "X"}
        f2 = {"id": "A", "nom": "X dup"}  # même id
        f3 = {"id": "B", "nom": "Y"}
        text = build_fiches_text([f1, f2, f3])
        assert text.count("[fiche") == 2  # dedupe sur id

    def test_build_fiches_text_max_fiches_respected(self):
        fiches = [{"id": str(i), "nom": f"F{i}"} for i in range(10)]
        text = build_fiches_text(fiches, max_fiches=3)
        assert text.count("[fiche") == 3


class TestVerdictDataclass:
    def test_to_dict_roundtrip(self):
        v = FaithfulnessVerdict(
            score=0.35,
            flagged_entities=["x"],
            justification="test",
            raw_verdict="INFIDELE",
            latency_ms=1234,
        )
        d = v.to_dict()
        assert d["score"] == 0.35
        assert d["flagged_entities"] == ["x"]
        assert d["raw_verdict"] == "INFIDELE"
        assert d["latency_ms"] == 1234
        assert d["model"] == DEFAULT_MODEL  # default
