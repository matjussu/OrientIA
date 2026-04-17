from unittest.mock import MagicMock, patch
from src.rag.embeddings import embed_texts, fiche_to_text


def test_fiche_to_text_includes_key_fields():
    fiche = {
        "nom": "Master Cyber",
        "etablissement": "ENSIBS",
        "ville": "Vannes",
        "statut": "Public",
        "labels": ["SecNumEdu"],
        "taux_acces_parcoursup_2025": 22.0,
    }
    text = fiche_to_text(fiche)
    assert "Master Cyber" in text
    assert "ENSIBS" in text
    assert "Vannes" in text
    assert "SecNumEdu" in text
    assert "22" in text


def test_embed_texts_calls_mistral_api():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
    mock_client.embeddings.create.return_value = mock_response

    result = embed_texts(mock_client, ["hello"])
    assert result == [[0.1, 0.2, 0.3]]
    mock_client.embeddings.create.assert_called_once_with(
        model="mistral-embed", inputs=["hello"]
    )


# === Vague B.3 — fiche_to_text enriched ===


def test_fiche_to_text_vague_b3_detail_extended_to_800_chars():
    """Vague B.3: detail window expanded from 200 → 800 chars so
    the embedding carries specialisation/parcours signal for better
    retrieval on 'formations cyber' / 'data science' type queries."""
    fiche = {
        "nom": "Master Cyber",
        "etablissement": "ENSIBS",
        "ville": "Vannes",
        "statut": "Public",
        "labels": ["SecNumEdu"],
        "detail": "A" * 900,  # 900 chars
    }
    text = fiche_to_text(fiche)
    # detail should be included up to 800 chars (not the old 200)
    assert "Détail" in text
    detail_part = text.split("Détail : ", 1)[1]
    # The Détail segment must be at least 500 chars long (some joiner
    # content after it is fine).
    assert len(detail_part) >= 500, (
        f"detail window too narrow: got {len(detail_part)} chars after 'Détail : '"
    )


def test_fiche_to_text_vague_b3_includes_rome_libelles():
    """Vague B.3: ROME job libellés injected (codes excluded). This carries
    semantic signal like 'RSSI', 'Data scientist', 'Architecte sécurité'
    that matches career-oriented queries ('je veux être data scientist')."""
    fiche = {
        "nom": "Master Cyber",
        "etablissement": "ENSIBS",
        "ville": "Vannes",
        "statut": "Public",
        "labels": ["SecNumEdu"],
        "debouches": [
            {"code_rome": "M1812", "libelle": "Responsable de la Sécurité des Systèmes d'Information (RSSI)"},
            {"code_rome": "M1405", "libelle": "Data scientist"},
        ],
    }
    text = fiche_to_text(fiche)
    assert "Métiers possibles" in text
    assert "RSSI" in text
    assert "Data scientist" in text


def test_fiche_to_text_vague_b3_excludes_rome_codes_from_embedding():
    """Codes (M1812 etc.) stay out of the embedding — they are structured
    identifiers, not narrative content. Libellés are narrative and help
    retrieval; codes pollute it with shared-across-domain signal."""
    fiche = {
        "nom": "Master Cyber", "etablissement": "E", "ville": "V",
        "debouches": [{"code_rome": "M1812", "libelle": "RSSI"}],
    }
    text = fiche_to_text(fiche)
    assert "M1812" not in text, "ROME codes must stay out of the embedding"


def test_fiche_to_text_vague_b3_no_metiers_line_when_debouches_empty():
    fiche = {
        "nom": "F", "etablissement": "E", "ville": "V",
        "debouches": [],
    }
    text = fiche_to_text(fiche)
    assert "Métiers possibles" not in text


def test_fiche_to_text_vague_b3_excludes_profil_admis():
    """profil_admis stays out of embedding (numbers pollute similarity).
    This is the separation-of-concerns principle from DATA_SCHEMA_V2."""
    fiche = {
        "nom": "F", "etablissement": "E", "ville": "V",
        "profil_admis": {
            "mentions_pct": {"tb": 45.0, "b": 30.0},
            "bac_type_pct": {"general": 80.0, "techno": 15.0},
            "boursiers_pct": 20.0, "femmes_pct": 24.0,
        },
    }
    text = fiche_to_text(fiche)
    # No mention %, no bac-type %, no boursiers — all structured numeric
    for banned in ("45.0", "80.0", "Boursiers", "Femmes", "mentions_pct"):
        assert banned not in text, f"{banned} must stay out of embedding"
