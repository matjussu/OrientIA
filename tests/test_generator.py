from unittest.mock import MagicMock
from src.rag.generator import format_context, generate, selectivite_qualitative


def _full_fiche():
    return {
        "nom": "Master Cybersécurité",
        "etablissement": "Université de Rennes",
        "ville": "Rennes",
        "departement": "Ille-et-Vilaine",
        "statut": "Public",
        "niveau": "bac+5",
        "labels": ["SecNumEdu", "CTI"],
        "taux_acces_parcoursup_2025": 18.0,
        "nombre_places": 24,
        "detail": "A" * 600,  # 600 chars to test 500-char truncation
        "profil_admis": {
            "mentions_pct": {"tb": 45.0, "b": 30.0, "ab": 20.0, "sans": 5.0},
            "bac_type_pct": {"general": 80.0, "techno": 15.0, "pro": 5.0},
            "boursiers_pct": 20.0,
        },
        "debouches": [
            {"libelle": "Analyste cyber", "code_rome": "M1812"},
            {"libelle": "Architecte réseaux", "code_rome": "M1803"},
            {"libelle": "RSSI", "code_rome": "M1802"},
            {"libelle": "Admin sécurité", "code_rome": "M1810"},
            {"libelle": "Pentester", "code_rome": "M1809"},
        ],
        "url_onisep": "https://onisep.fr/FOR.1234",
    }


def test_format_context_includes_all_fiches():
    results = [
        {"fiche": {"nom": "Master A", "etablissement": "X", "ville": "Paris",
                   "labels": ["SecNumEdu"], "statut": "Public",
                   "taux_acces_parcoursup_2025": 25.0}, "score": 0.9},
        {"fiche": {"nom": "Master B", "etablissement": "Y", "ville": "Lyon",
                   "labels": [], "statut": "Privé"}, "score": 0.7},
    ]
    context = format_context(results)
    assert "Master A" in context
    assert "Master B" in context
    assert "SecNumEdu" in context


def test_format_context_selectivite_appears_before_detail():
    """Critical info (selectivity) must come before verbose detail text."""
    results = [{"fiche": _full_fiche(), "score": 0.9}]
    ctx = format_context(results)
    sel_idx = ctx.find("Sélectivité")
    detail_idx = ctx.find("Détail")
    assert sel_idx != -1 and detail_idx != -1
    assert sel_idx < detail_idx, (
        "Sélectivité must come before Détail for signal-first ordering"
    )


def test_format_context_detail_truncated_to_500_chars():
    """Phase 1.2: detail window expanded from 250 → 500 chars."""
    results = [{"fiche": _full_fiche(), "score": 0.9}]
    ctx = format_context(results)
    detail_line = next(
        line for line in ctx.split("\n") if line.strip().startswith("Détail")
    )
    detail_body = detail_line.split("Détail:", 1)[1].strip()
    assert 490 <= len(detail_body) <= 520, (
        f"Detail should be ~500 chars, got {len(detail_body)}"
    )


def test_format_context_debouches_limited_to_three():
    """Phase 1.2: top 3 metiers only (vs 5 before) to reduce noise."""
    results = [{"fiche": _full_fiche(), "score": 0.9}]
    ctx = format_context(results)
    debouches_line = next(
        line for line in ctx.split("\n") if "Débouchés" in line
    )
    assert "Analyste cyber" in debouches_line
    assert "Architecte réseaux" in debouches_line
    assert "RSSI" in debouches_line
    assert "Admin sécurité" not in debouches_line, "should stop at 3 metiers"
    assert "Pentester" not in debouches_line


def test_format_context_emits_at_most_eight_lines_per_fiche():
    """Phase 1.2: 1 header + up to 7 content lines = 8 lines max."""
    results = [{"fiche": _full_fiche(), "score": 0.9}]
    ctx = format_context(results)
    non_empty = [l for l in ctx.split("\n") if l.strip()]
    assert len(non_empty) <= 8, (
        f"Expected ≤ 8 lines per fiche, got {len(non_empty)}: {non_empty}"
    )


def test_selectivite_qualitative_thresholds():
    """Qualitative label reflects Parcoursup access rate."""
    assert selectivite_qualitative(10.0) == "Très sélective"
    assert selectivite_qualitative(19.9) == "Très sélective"
    assert selectivite_qualitative(20.0) == "Sélective"
    assert selectivite_qualitative(49.9) == "Sélective"
    assert selectivite_qualitative(50.0) == "Accessible"
    assert selectivite_qualitative(85.0) == "Accessible"
    assert selectivite_qualitative(None) == "non renseignée"


def test_format_context_shows_qualitative_selectivity():
    results = [{"fiche": _full_fiche(), "score": 0.9}]
    ctx = format_context(results)
    # 18% → Très sélective
    assert "18" in ctx and "Très sélective" in ctx


def test_format_context_omits_missing_optional_lines():
    """Lines with no data are omitted rather than printing 'None'."""
    minimal = {
        "nom": "BTS X",
        "etablissement": "Lycée Y",
        "ville": "Paris",
        "statut": "Public",
        "labels": [],
    }
    results = [{"fiche": minimal, "score": 0.5}]
    ctx = format_context(results)
    assert "None" not in ctx
    # Labels line is omitted when there's nothing to say
    assert "Profil admis" not in ctx
    assert "Débouchés" not in ctx
    assert "Détail" not in ctx


def test_format_context_no_labels_shows_explicit_none():
    """When labels list is empty, the labels line is simply omitted."""
    fiche = _full_fiche()
    fiche["labels"] = []
    results = [{"fiche": fiche, "score": 0.9}]
    ctx = format_context(results)
    # No 'Labels officiels:' line when there are none
    assert "Labels officiels" not in ctx


def test_generate_calls_mistral_with_system_and_user_prompts():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Response text"))]
    mock_client.chat.complete.return_value = mock_response

    results = [{"fiche": {"nom": "F", "etablissement": "E", "ville": "V", "labels": [],
                          "statut": "Public"}, "score": 0.5}]
    answer = generate(mock_client, results, "question?", model="mistral-medium-latest")
    assert answer == "Response text"
    call = mock_client.chat.complete.call_args
    messages = call.kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "question?" in messages[1]["content"]
