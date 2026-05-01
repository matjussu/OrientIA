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


# ---------- Sprint 12 D5 — _format_insertion_pro schéma InserSup ----------

from src.rag.embeddings import _format_insertion_pro


def test_format_insertion_pro_insersup_complet():
    """Cas standard InserSup MESR : taux + salaires + sortants tous remplis."""
    ip = {
        "source": "insersup",
        "cohorte": "2021",
        "taux_emploi_12m": 78.0,
        "taux_emploi_18m": 81.8,
        "taux_emploi_stable_12m": 65.7,
        "salaire_median_12m": 1850,
        "salaire_median_30m": 2070,
        "nombre_sortants": 247,
        "granularite": "discipline",
        "disclaimer": "agrégation discipline INFORMATIQUE",
        "source_url": "https://...",
    }
    out = _format_insertion_pro(ip)
    assert out is not None
    assert out.startswith("Insertion pro (source InserSup MESR, 2021, discipline détaillée) :")
    assert "taux emploi 12 mois : 78%" in out
    assert "taux emploi 18 mois : 82%" in out  # 81.8 → 82
    assert "taux emploi stable 12 mois : 66%" in out  # 65.7 → 66
    assert "salaire médian net 12 mois : 1850€" in out
    assert "salaire médian net 30 mois : 2070€" in out
    assert "247 sortants suivis" in out


def test_format_insertion_pro_insersup_granularite_agregat():
    """Granularité 'type_diplome_agrege' affiche libellé approprié (vs 'discipline')."""
    ip = {
        "source": "insersup",
        "cohorte": "2020",
        "taux_emploi_12m": 65.0,
        "granularite": "type_diplome_agrege",
    }
    out = _format_insertion_pro(ip)
    assert out is not None
    assert "agrégat type de diplôme établissement" in out
    assert "65%" in out


def test_format_insertion_pro_insersup_partiel_12m_only():
    """Cas où seul taux emploi 12m est connu (autres None) → fragment unique."""
    ip = {
        "source": "insersup",
        "cohorte": "2022",
        "taux_emploi_12m": 80.0,
        "granularite": "discipline",
    }
    out = _format_insertion_pro(ip)
    assert out is not None
    assert "taux emploi 12 mois : 80%" in out
    # Pas de fragments fantômes pour les champs absents
    assert "salaire" not in out
    assert "sortants" not in out


def test_format_insertion_pro_insersup_tous_zeros_returns_none():
    """Si tous les champs valeur sont None ou non-numériques → None
    (pas de pollution avec sections vides)."""
    ip = {
        "source": "insersup",
        "cohorte": "2021",
        "granularite": "discipline",
    }
    assert _format_insertion_pro(ip) is None


def test_format_insertion_pro_insersup_dispatch_priorite_source():
    """Quand source='insersup' explicite, le dispatch prend la branche
    InserSup même si des clés Céreq sont aussi présentes (priorité source)."""
    ip = {
        "source": "insersup",
        "cohorte": "2021",
        "taux_emploi_12m": 70.0,
        # Clés Céreq présentes par accident, mais source dicte
        "taux_emploi_3ans": 0.85,
        "salaire_median_embauche": 1900,
        "granularite": "discipline",
    }
    out = _format_insertion_pro(ip)
    assert out is not None
    assert out.startswith("Insertion pro (source InserSup MESR")
    # La branche Céreq aurait écrit "Insertion pro (source Céreq, ...)"
    assert "Céreq" not in out


def test_fiche_to_text_includes_insersup_insertion_pro_section():
    """Smoke test bout-en-bout : fiche avec insertion_pro source insersup
    voit sa section apparaître dans le texte embedded."""
    fiche = {
        "nom": "Master Cyber",
        "etablissement": "Université Paris-Saclay",
        "ville": "Saclay",
        "insertion_pro": {
            "source": "insersup",
            "cohorte": "2021",
            "taux_emploi_12m": 92.0,
            "salaire_median_12m": 2200,
            "granularite": "discipline",
        },
    }
    text = fiche_to_text(fiche)
    assert "Insertion pro (source InserSup MESR" in text
    assert "92%" in text
    assert "2200€" in text


def test_format_insertion_pro_cereq_branch_preserved():
    """Régression : Céreq schéma toujours fonctionnel (préservation acquis)."""
    ip = {
        "source": "cereq",
        "cohorte": "2020",
        "taux_emploi_3ans": 0.85,
        "taux_emploi_6ans": 0.92,
        "taux_cdi": 0.78,
        "salaire_median_embauche": 1850,
    }
    out = _format_insertion_pro(ip)
    assert out is not None
    assert "Céreq" in out
    assert "85%" in out  # 0.85 → 85%
    assert "1850€" in out


def test_format_insertion_pro_cfa_branch_preserved():
    """Régression : CFA Inserjeunes schéma toujours fonctionnel."""
    ip = {
        "source": "inserjeunes_cfa",
        "annee": "2024",
        "taux_emploi_6m": 0.62,
        "taux_emploi_12m": 0.75,
        "taux_emploi_18m": 0.81,
    }
    out = _format_insertion_pro(ip)
    assert out is not None
    assert "Inserjeunes CFA" in out
    assert "62%" in out


def test_fiche_to_text_vague_b3_excludes_profil_admis():
    """profil_admis stays out of embedding (numbers pollute similarity).
    This is the separation-of-concerns principle from DATA_SCHEMA_V2.

    Note Sprint 12 D5 : ce test passe sur la branche D5 (qui n'a pas
    encore le D1 reversal). Sera supprimé / remplacé quand D1 mergé
    sur main et que D5 est rebased dessus."""
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
