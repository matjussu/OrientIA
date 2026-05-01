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


def test_fiche_to_text_sprint12_d1_includes_profil_admis():
    """Sprint 12 D1 (2026-05-01) — REVERSAL explicite du choix
    Vague B.3 d'exclure profil_admis. Cf
    docs/sprint12-D1-profil-admis-audit-champs-2026-05-01.md.

    Rationale du reversal : v3 admission_stats (Run F, 2026-04-24) avait
    déjà commencé à injecter des chiffres dans l'embedding (taux d'accès
    Parcoursup, salaire médian Céreq). Le principe "numbers pollute
    similarity" du test précédent était théorique ; en pratique, Sprint
    11 P1.1 a montré que NE PAS exposer les chiffres profil-spécifiques
    cause des hallucinations LLM (Q1 Paris-Saclay 27 % inventé, EPF 95 %
    inventé) = problème pire que la pollution similarité hypothétique.
    """
    fiche = {
        "nom": "F", "etablissement": "E", "ville": "V",
        "profil_admis": {
            "mentions_pct": {"tb": 45.0, "b": 30.0},
            "bac_type_pct": {"general": 80.0, "techno": 15.0},
            "boursiers_pct": 20.0, "femmes_pct": 24.0,
        },
    }
    text = fiche_to_text(fiche)
    # Profil des admis section présente
    assert "Profil des admis" in text
    # Mentions au bac présentes (skip ab=0 et sans=0)
    assert "45 % très bien" in text
    assert "30 % bien" in text
    # Type bac présent (skip pro=0)
    assert "80 % bac général" in text
    assert "15 % bac techno" in text
    # Démographie présente (skip ce qui = 0)
    assert "20 % boursiers" in text
    assert "24 % femmes" in text


# ---------- Sprint 12 D1 — _format_profil_admis helper unit tests ----------

from src.rag.embeddings import _format_profil_admis


def test_format_profil_admis_riche_complet():
    """Cas EFREI Bordeaux Bachelor cyber (sample audit S1) — 7 sous-champs
    tous remplis et meaningful → 4 sections dans la chaîne."""
    pa = {
        "mentions_pct": {"tb": 4.0, "b": 12.0, "ab": 29.0, "sans": 54.0},
        "bac_type_pct": {"general": 71.0, "techno": 17.0, "pro": 12.0},
        "acces_pct":    {"general": 79.0, "techno": 14.0, "pro": 6.0},
        "boursiers_pct": 21.0,
        "femmes_pct": 10.0,
        "neobacheliers_pct": 77.0,
        "origine_academique_idf_pct": 58.0,
    }
    out = _format_profil_admis(pa)
    assert out is not None
    assert out.startswith("Profil des admis (Parcoursup 2025) :")
    # 4 sections séparées par " — "
    assert "mentions au bac : 4 % très bien, 12 % bien, 29 % assez bien, 54 % sans mention" in out
    assert "type de bac admis : 71 % bac général, 17 % bac techno, 12 % bac pro" in out
    assert "taux d'accès par profil : 79 % pour bac général, 14 % pour bac techno, 6 % pour bac pro" in out
    assert "profil démographique : 21 % boursiers, 10 % femmes, 77 % néobacheliers, 58 % origine académique Île-de-France" in out


def test_format_profil_admis_partiel_mentions_seule():
    """Sous-champ mentions_pct rempli, le reste vide ou tous-zéros → on
    garde mentions seule, on skip le reste."""
    pa = {
        "mentions_pct": {"tb": 10.0, "b": 25.0, "ab": 40.0, "sans": 25.0},
        "bac_type_pct": {"general": 0, "techno": 0, "pro": 0},
        "acces_pct": {},
        "boursiers_pct": 0,
        "femmes_pct": 0.0,
    }
    out = _format_profil_admis(pa)
    assert out is not None
    assert "mentions au bac" in out
    # Pas de section vide (skip)
    assert "type de bac admis" not in out
    assert "taux d'accès par profil" not in out
    assert "profil démographique" not in out


def test_format_profil_admis_partiel_bac_type_seul():
    pa = {
        "bac_type_pct": {"general": 65.0, "techno": 30.0, "pro": 5.0},
        # autres champs absents
    }
    out = _format_profil_admis(pa)
    assert out is not None
    assert "type de bac admis" in out
    assert "65 % bac général" in out
    assert "mentions au bac" not in out


def test_format_profil_admis_tous_zeros_returns_none():
    """Cas placeholder Parcoursup ~81 % du corpus — retourne None,
    aucune pollution embedding avec des "0 %" non-informatifs."""
    pa = {
        "mentions_pct": {"tb": 0.0, "b": 0.0, "ab": 0.0, "sans": 0.0},
        "bac_type_pct": {"general": 0.0, "techno": 0.0, "pro": 0.0},
        "acces_pct": {"general": 0.0, "techno": 0.0, "pro": 0.0},
        "boursiers_pct": 0.0,
        "femmes_pct": 0.0,
        "neobacheliers_pct": 0.0,
        "origine_academique_idf_pct": 0.0,
    }
    assert _format_profil_admis(pa) is None


def test_format_profil_admis_absent_returns_none():
    assert _format_profil_admis(None) is None
    assert _format_profil_admis({}) is None


def test_format_profil_admis_valeurs_limites():
    """100 % et 0.5 % doivent être correctement formatés (arrondi entier
    pour stabilité retrieval, cohérent avec _safe_pct)."""
    pa = {
        "mentions_pct": {"tb": 100.0, "b": 0.5},  # 0.5 → arrondi à 0 → skip
        "boursiers_pct": 0.7,  # arrondi à 1 % → garder
    }
    out = _format_profil_admis(pa)
    assert out is not None
    assert "100 % très bien" in out
    # 0.5 → round(0.5) = 0 (banker's rounding) ou 1 selon Python ; les deux acceptables
    # le test ne fixe pas le comportement exact pour ce edge case
    assert "1 % boursiers" in out


def test_format_profil_admis_type_invalid_returns_none():
    """Robustesse : profil_admis = string ou int ne crash pas, retourne None."""
    assert _format_profil_admis("not a dict") is None  # type: ignore[arg-type]
    assert _format_profil_admis(42) is None  # type: ignore[arg-type]


def test_format_profil_admis_sous_champ_invalid_skip_silently():
    """Si mentions_pct est une string au lieu de dict (donnée corrompue),
    on skip ce sous-champ proprement sans crash."""
    pa = {
        "mentions_pct": "corrupted",
        "bac_type_pct": {"general": 50.0, "techno": 50.0, "pro": 0},
    }
    out = _format_profil_admis(pa)
    assert out is not None
    assert "type de bac admis" in out
    assert "mentions au bac" not in out
