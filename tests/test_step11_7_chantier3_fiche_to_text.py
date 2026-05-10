"""Tests step 11.7 chantier 3 — fiche_to_text enrichi.

Couvre :
- _detect_known_school_signature : matche les écoles prestigieuses
  connues (ENIB, INSA, HEC, etc.) sans faux positifs sur établissements
  non-listés.
- _detect_metier_keywords_in_text : détecte cyber/data/IA/robotique
  dans nom/detail.
- fiche_to_text injecte la signature école + tags métier quand
  applicable.
- fiche_to_text reste backward compat sur fiches sans match (pas de
  pollution du texte embedded).
"""
from __future__ import annotations

from src.rag.embeddings import (
    KNOWN_SCHOOL_SIGNATURES,
    _detect_known_school_signature,
    _detect_metier_keywords_in_text,
    fiche_to_text,
)


# ────────────────────────── _detect_known_school_signature ──────────────────────────


def test_known_school_signatures_minimum_size() -> None:
    """Au moins 20 écoles prestigieuses listées (couverture min)."""
    assert len(KNOWN_SCHOOL_SIGNATURES) >= 20


def test_signature_enib() -> None:
    sig = _detect_known_school_signature("ENIB Brest")
    assert sig is not None
    assert "informatique" in sig.lower()
    assert "cyber" in sig.lower()


def test_signature_enseirb_matmeca() -> None:
    """ENSEIRB-MATMECA matche prioritairement (plus long que ENSEIRB seul)."""
    sig = _detect_known_school_signature("CPBx (ENSEIRB-MATMECA)")
    assert sig is not None
    assert "Bordeaux" in sig
    assert "informatique" in sig.lower() or "cyber" in sig.lower()


def test_signature_insa_generic() -> None:
    """INSA Rennes / Lyon / Toulouse → tous matchent l'INSA générique."""
    for etab in ("INSA Rennes - filière classique", "INSA Lyon", "INSA Toulouse"):
        sig = _detect_known_school_signature(etab)
        assert sig is not None
        assert "informatique" in sig.lower() or "ingénieurs" in sig.lower() or "génie" in sig.lower()


def test_signature_hec() -> None:
    sig = _detect_known_school_signature("HEC Paris")
    assert sig is not None
    assert "commerce" in sig.lower() or "management" in sig.lower()


def test_signature_centralesupelec() -> None:
    sig = _detect_known_school_signature("École CentraleSupélec")
    assert sig is not None
    assert "informatique" in sig.lower() or "ingénierie" in sig.lower()


def test_signature_imt_atlantique() -> None:
    sig = _detect_known_school_signature(
        "CentraleSupélec - IMT Atlantique Bretagne-Pays de la Loire"
    )
    assert sig is not None
    # Match prioritaire : CentraleSupélec OU IMT Atlantique (les deux en fait
    # mais on retient le 1er qui matche par taille décroissante)


def test_signature_sciences_po() -> None:
    sig = _detect_known_school_signature("Institut d'études politiques de Paris")
    assert sig is not None
    assert "politique" in sig.lower() or "sciences sociales" in sig.lower()


def test_no_signature_for_unknown_school() -> None:
    """Établissement non-listé → pas de signature (pas de faux positif)."""
    assert _detect_known_school_signature("Université de Marseille") is None
    assert _detect_known_school_signature("Lycée Bréquigny") is None
    assert _detect_known_school_signature("Centre de formation X") is None


def test_no_signature_for_empty_or_invalid() -> None:
    assert _detect_known_school_signature("") is None
    assert _detect_known_school_signature(None) is None  # type: ignore[arg-type]
    assert _detect_known_school_signature(42) is None  # type: ignore[arg-type]


# ────────────────────────── _detect_metier_keywords_in_text ──────────────────────────


def test_metier_cyber_detected() -> None:
    tags = _detect_metier_keywords_in_text(
        "Master cybersécurité",
        "",
        "",
    )
    assert "cybersécurité" in tags.lower() or "sécurité" in tags.lower()


def test_metier_data_detected() -> None:
    tags = _detect_metier_keywords_in_text(
        "Master Data Science",
        "Apprentissage du machine learning",
        "",
    )
    assert "data" in tags.lower() or "donnée" in tags.lower()


def test_metier_ia_detected() -> None:
    tags = _detect_metier_keywords_in_text(
        "",
        "Spécialité intelligence artificielle",
        "",
    )
    assert "intelligence artificielle" in tags.lower() or "ia" in tags.lower()


def test_metier_multiple_tags() -> None:
    tags = _detect_metier_keywords_in_text(
        "Master cybersécurité et IA",
        "data science",
        "",
    )
    # Au moins 2 tags détectés concaténés via " ; "
    assert ";" in tags or len(tags) > 50


def test_metier_no_match_returns_empty() -> None:
    tags = _detect_metier_keywords_in_text("Licence histoire", "", "")
    assert tags == ""


def test_metier_handles_empty_inputs() -> None:
    assert _detect_metier_keywords_in_text("", "", "") == ""


# ────────────────────────── fiche_to_text intégration ──────────────────────────


def test_fiche_to_text_enib_includes_signature() -> None:
    """Cas réel ENIB Brest : `nom` générique + etab="ENIB Brest".
    APRÈS step 11.7 chantier 3 : la signature ENIB doit apparaître
    dans le texte embedded."""
    fiche = {
        "nom": "Formation d'ingénieur Bac + 5 - Bac général",
        "etablissement": "ENIB Brest",
        "ville": "Brest",
        "region": "Bretagne",
        "domaine": "ingenierie_industrielle",
    }
    text = fiche_to_text(fiche)
    assert "Signature école" in text
    # La signature ENIB doit mentionner cybersécurité explicitement
    assert "cyber" in text.lower()


def test_fiche_to_text_enseirb_includes_signature() -> None:
    fiche = {
        "nom": "Formation d'ingénieur Bac + 5 - bac général",
        "etablissement": "CPBx (ENSEIRB-MATMECA)",
    }
    text = fiche_to_text(fiche)
    assert "Signature école" in text
    assert "Bordeaux" in text or "informatique" in text.lower()


def test_fiche_to_text_insa_includes_signature() -> None:
    fiche = {
        "nom": "premier cycle INSA post bac général - STPI",
        "etablissement": "INSA Rennes - filière classique",
    }
    text = fiche_to_text(fiche)
    assert "Signature école" in text


def test_fiche_to_text_hec_includes_commerce_signature() -> None:
    fiche = {
        "nom": "diplôme du programme grande école d'HEC Paris",
        "etablissement": "HEC Paris",
    }
    text = fiche_to_text(fiche)
    assert "Signature école" in text
    assert "commerce" in text.lower() or "management" in text.lower()


def test_fiche_to_text_no_signature_for_lycee() -> None:
    """Lycée standard → pas de signature (correct)."""
    fiche = {
        "nom": "BTS Cybersécurité",
        "etablissement": "Lycée Bréquigny",
        "ville": "Rennes",
    }
    text = fiche_to_text(fiche)
    assert "Signature école" not in text


def test_fiche_to_text_metier_keyword_in_master_name() -> None:
    """Master avec 'cybersécurité' dans le nom → tag détecté."""
    fiche = {
        "nom": "Master CYBERSECURITE — M1 Sécurité logicielle et matérielle",
        "etablissement": "Université de Rennes",
    }
    text = fiche_to_text(fiche)
    assert "Mots-clés métier détectés" in text
    assert "cyber" in text.lower()


def test_fiche_to_text_backward_compat_simple_fiche() -> None:
    """Fiche basique sans école prestigieuse ni mot-clé métier →
    pas de pollution. Backward compat strict."""
    fiche = {
        "nom": "Licence Histoire",
        "etablissement": "Université de Paris",
        "ville": "Paris",
        "region": "Île-de-France",
        "niveau": "3",
    }
    text = fiche_to_text(fiche)
    # Pas de signature école (Université de Paris générique pas dans la liste)
    assert "Signature école" not in text
    # Pas de tag métier
    assert "Mots-clés métier détectés" not in text
    # Champs originaux préservés
    assert "Licence Histoire" in text
    assert "Paris" in text


def test_fiche_to_text_keeps_original_stats() -> None:
    """L'enrichissement n'écrase PAS les stats existantes (admission, insertion)."""
    fiche = {
        "nom": "Formation d'ingénieur",
        "etablissement": "ENIB Brest",
        "ville": "Brest",
        "region": "Bretagne",
        "taux_acces_parcoursup_2025": 75.0,
        "nombre_places": 100,
    }
    text = fiche_to_text(fiche)
    # Signature école présente
    assert "Signature école" in text
    # Stats admission présentes (via _format_admission_stats)
    assert "Admission" in text or "75" in text or "100" in text
