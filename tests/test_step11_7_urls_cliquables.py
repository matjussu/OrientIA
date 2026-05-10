"""Tests step 11.7 chantier 2 — URLs cliquables Markdown.

Couvre :
- R3.bis présent dans SYSTEM_PROMPT_V4_STRICT (additif, R1-R3 préservés)
- R3.bis cite l'exemple `[BUT Informatique à l'IUT Lyon 1](https://...)`
- strip_invented_urls n'enlève PAS les URLs Parcoursup/ONISEP/MonMaster
- strip_invented_urls enlève toujours github.com/matjussu, jsdelivr, localhost
- card.url est dans le JSON `<sources>` envoyé au LLM (déjà testé via fact_card)
"""
from __future__ import annotations

from src.prompt.system_v4_strict import SYSTEM_PROMPT_V4_STRICT
from src.rag.post_process import strip_invented_urls


# ────────────────────────── R3.bis dans le prompt ──────────────────────────


def test_r3_bis_present() -> None:
    """R3.bis est ajouté de façon additive (R1-R3/R4-R7 inchangés)."""
    assert "R3.bis" in SYSTEM_PROMPT_V4_STRICT
    assert "Liens cliquables" in SYSTEM_PROMPT_V4_STRICT or "Markdown link" in SYSTEM_PROMPT_V4_STRICT


def test_r3_bis_keeps_r1_to_r7_intact() -> None:
    """R1-R7 markers préservés byte-identiques."""
    for marker in ("R1 — Chiffres", "R2 — Identité", "R3 — Citations",
                   "R4 — Style", "R5 — Posture", "R6 — LONGUEUR",
                   "R7 — CONTRAINTES HARDLOCK"):
        assert marker in SYSTEM_PROMPT_V4_STRICT, f"Marker manquant : {marker}"


def test_r3_bis_documents_format() -> None:
    """R3.bis documente le format `[Nom](url)` avec exemple."""
    # Format Markdown link doit apparaître
    assert "[Nom de la formation](url)" in SYSTEM_PROMPT_V4_STRICT or \
           "[Nom](url)" in SYSTEM_PROMPT_V4_STRICT
    # Exemple BUT Informatique IUT Lyon 1 (concret pour le LLM)
    assert "BUT Informatique" in SYSTEM_PROMPT_V4_STRICT


def test_r3_bis_handles_null_url() -> None:
    """R3.bis explique que si url=null, on écrit le nom en gras (pas
    de lien hallu)."""
    # Le prompt doit mentionner le cas null
    assert "null" in SYSTEM_PROMPT_V4_STRICT.lower()


def test_r3_bis_warns_about_repetition() -> None:
    """R3.bis dit de citer chaque formation une seule fois avec le lien."""
    assert "1" in SYSTEM_PROMPT_V4_STRICT  # "1ʳᵉ mention" / "une seule fois"
    # Pattern textuel
    assert "une seule fois" in SYSTEM_PROMPT_V4_STRICT or \
           "1ʳᵉ" in SYSTEM_PROMPT_V4_STRICT or \
           "1ère" in SYSTEM_PROMPT_V4_STRICT


# ────────────────────────── strip_invented_urls : Parcoursup/ONISEP épargnés ──────────────────────────


def test_strip_preserves_parcoursup_url() -> None:
    """URL Parcoursup officielle doit survivre au strip."""
    response = (
        "Le [BUT Informatique IUT Lyon 1](https://dossierappel.parcoursup.fr/"
        "Candidats/public/fiches/afficherFicheFormation?g_ta_cod=12345) "
        "propose 60 places [source S1]."
    )
    cleaned = strip_invented_urls(response)
    assert "dossierappel.parcoursup.fr" in cleaned, "URL Parcoursup ne doit PAS être strippée"
    assert "[BUT Informatique IUT Lyon 1]" in cleaned


def test_strip_preserves_onisep_url() -> None:
    """URL ONISEP officielle doit survivre au strip."""
    response = (
        "Voir la fiche [Master Cybersécurité](https://www.onisep.fr/"
        "Ressources/Univers-Formation/Formations/Post-bac/master-cybersecurite) "
        "pour plus de détails."
    )
    cleaned = strip_invented_urls(response)
    assert "onisep.fr" in cleaned


def test_strip_preserves_monmaster_url() -> None:
    """URL MonMaster officielle doit survivre."""
    response = "Voir [Master MIAGE](https://www.monmaster.gouv.fr/master/123)"
    cleaned = strip_invented_urls(response)
    assert "monmaster.gouv.fr" in cleaned


def test_strip_still_removes_github_invented() -> None:
    """github.com/matjussu reste interdit (anti-régression)."""
    response = "Voir [fiche](https://github.com/matjussu/OrientIA/blob/main/data/fiches/123.json)"
    cleaned = strip_invented_urls(response)
    assert "github.com/matjussu" not in cleaned


def test_strip_still_removes_jsdelivr() -> None:
    """jsdelivr sans sous-domaine (forme matchée par INVENTED_URL_REGEX existant)."""
    response = "Voir https://jsdelivr.net/gh/orientia/data/123"
    cleaned = strip_invented_urls(response)
    assert "jsdelivr" not in cleaned


def test_strip_still_removes_localhost() -> None:
    response = "Voir [fiche](http://localhost:8080/api/123)"
    cleaned = strip_invented_urls(response)
    assert "localhost" not in cleaned


def test_strip_mixed_real_and_invented_urls() -> None:
    """Réponse mix : URLs Parcoursup gardées, github strippée."""
    response = (
        "Voir le [BUT Info](https://dossierappel.parcoursup.fr/.../?g_ta_cod=12345) "
        "et la [fiche détaillée](https://github.com/matjussu/OrientIA/data.json)."
    )
    cleaned = strip_invented_urls(response)
    # Parcoursup gardé
    assert "parcoursup.fr" in cleaned
    assert "[BUT Info]" in cleaned
    # github strippé
    assert "github.com/matjussu" not in cleaned
