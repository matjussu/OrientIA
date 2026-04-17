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


# === Vague A — enriched generator context ===

def _vague_a_fiche() -> dict:
    """Fiche with Vague A structured admission block + extended demographics."""
    return {
        "nom": "Master Cybersécurité",
        "etablissement": "Université de Rennes",
        "ville": "Rennes",
        "departement": "Ille-et-Vilaine",
        "statut": "Public",
        "niveau": "bac+5",
        "labels": ["SecNumEdu"],
        "rncp": "37989",
        "cod_aff_form": "42156",
        "lien_form_psup": "https://www.parcoursup.fr/formation/42156",
        "url_onisep": "https://onisep.fr/FOR.9891",
        "admission": {
            "session": 2025,
            "taux_acces": 18.0,
            "places": 24,
            "volumes": {
                "voeux_totaux": 1250,
                "voeux_phase_principale": 800,
                "classes_phase_principale": 600,
            },
            "internat_disponible": True,
        },
        "profil_admis": {
            "mentions_pct": {"tb": 45.0, "b": 30.0, "ab": 20.0, "sans": 5.0},
            "bac_type_pct": {"general": 80.0, "techno": 15.0, "pro": 5.0},
            "boursiers_pct": 20.0,
            "femmes_pct": 24.0,
            "neobacheliers_pct": 85.0,
        },
        "debouches": [{"libelle": "RSSI", "code_rome": "M1812"}],
    }


def test_vague_a_selectivite_includes_volumes_and_internat():
    """New admission.volumes + internat are surfaced to the LLM."""
    results = [{"fiche": _vague_a_fiche(), "score": 0.9}]
    ctx = format_context(results)
    sel_line = next(l for l in ctx.split("\n") if "Sélectivité" in l)
    assert "1250" in sel_line, "voeux_totaux must appear"
    assert "Internat: oui" in sel_line


def test_vague_a_selectivite_falls_back_to_legacy_when_no_admission_block():
    """Backward compat: fiches without admission.* still work via legacy flat fields."""
    legacy = {
        "nom": "M", "etablissement": "E", "ville": "V", "statut": "Public",
        "labels": [],
        "taux_acces_parcoursup_2025": 42.0,
        "nombre_places": 30,
    }
    ctx = format_context([{"fiche": legacy, "score": 0.5}])
    assert "42" in ctx
    assert "Places: 30" in ctx


def test_vague_a_profil_shows_full_bac_type_split():
    """All 3 bac types (général/techno/pro) are surfaced, not just général."""
    results = [{"fiche": _vague_a_fiche(), "score": 0.9}]
    ctx = format_context(results)
    profil_line = next(l for l in ctx.split("\n") if "Profil admis" in l)
    assert "général 80%" in profil_line
    assert "techno 15%" in profil_line
    assert "pro 5%" in profil_line


def test_vague_a_profil_includes_diversity_demographics():
    results = [{"fiche": _vague_a_fiche(), "score": 0.9}]
    ctx = format_context(results)
    profil_line = next(l for l in ctx.split("\n") if "Profil admis" in l)
    assert "Femmes 24%" in profil_line
    assert "Néobacheliers 85%" in profil_line


def test_vague_a_source_line_includes_parcoursup_url_and_identifiers():
    """Parcoursup URL + RNCP + cod_aff_form all appear in one source line."""
    results = [{"fiche": _vague_a_fiche(), "score": 0.9}]
    ctx = format_context(results)
    src_line = next(l for l in ctx.split("\n") if "Source officielle" in l)
    assert "parcoursup.fr/formation/42156" in src_line
    assert "ONISEP" in src_line and "FOR.9891" in src_line
    assert "RNCP 37989" in src_line
    assert "cod_aff_form 42156" in src_line


def test_vague_a_budget_still_eight_lines_per_fiche():
    """Despite richer content, still ≤8 lines per fiche (contract from Phase 1.2)."""
    results = [{"fiche": _vague_a_fiche(), "score": 0.9}]
    ctx = format_context(results)
    non_empty = [l for l in ctx.split("\n") if l.strip()]
    assert len(non_empty) <= 8, (
        f"Vague A must preserve ≤8-lines budget, got {len(non_empty)}: {non_empty}"
    )


# === Vague C — trends folded into selectivity line ===


def _vague_c_fiche_with_trends() -> dict:
    """Fiche with historical trends (taux down, voeux up) — signals a
    formation becoming more selective and more popular 2023→2025."""
    base = _vague_a_fiche()
    base["trends"] = {
        "taux_acces": {
            "direction": "down", "delta_pp": -23.0,
            "start_year": 2023, "end_year": 2025,
            "start_value": 68.0, "end_value": 45.0,
            "interpretation": "taux d'accès en baisse 2023→2025 (68% → 45%) : formation devenue plus sélective",
        },
        "places": {
            "direction": "stable", "delta": 2,
            "start_year": 2023, "end_year": 2025,
            "start_value": 24, "end_value": 26,
            "interpretation": None,
        },
        "voeux": {
            "direction": "up", "delta": 300,
            "start_year": 2023, "end_year": 2025,
            "start_value": 500, "end_value": 800,
            "interpretation": "popularité en hausse 2023→2025 (500 → 800 vœux) : attrait renforcé",
        },
    }
    return base


def test_vague_c_selectivity_line_includes_trend_when_significant():
    results = [{"fiche": _vague_c_fiche_with_trends(), "score": 0.9}]
    ctx = format_context(results)
    sel_line = next(l for l in ctx.split("\n") if "Sélectivité" in l)
    assert "Tendance" in sel_line
    # Taux drop surfaced
    assert "↓23pp" in sel_line
    assert "plus sélective" in sel_line
    # Voeux growth surfaced
    assert "vœux" in sel_line and "+60%" in sel_line
    # Stable places NOT mentioned (direction=stable)
    assert "places ↑" not in sel_line
    assert "places ↓" not in sel_line


def test_vague_c_no_trend_suffix_when_all_stable():
    f = _vague_a_fiche()
    f["trends"] = {
        "taux_acces": {"direction": "stable", "delta_pp": 2.0,
                       "start_year": 2023, "end_year": 2025,
                       "start_value": 50.0, "end_value": 52.0,
                       "interpretation": "taux stable"},
    }
    ctx = format_context([{"fiche": f, "score": 0.9}])
    sel_line = next(l for l in ctx.split("\n") if "Sélectivité" in l)
    assert "Tendance" not in sel_line


def test_vague_c_no_trend_suffix_when_trends_missing():
    """Fiche without trends field — no regression, no trend suffix."""
    f = _vague_a_fiche()
    # explicitly no "trends" key
    ctx = format_context([{"fiche": f, "score": 0.9}])
    sel_line = next(l for l in ctx.split("\n") if "Sélectivité" in l)
    assert "Tendance" not in sel_line


def test_vague_c_budget_preserved_at_eight_lines():
    """Trends folded INTO selectivity line — ≤8-line budget preserved."""
    results = [{"fiche": _vague_c_fiche_with_trends(), "score": 0.9}]
    ctx = format_context(results)
    non_empty = [l for l in ctx.split("\n") if l.strip()]
    assert len(non_empty) <= 8
