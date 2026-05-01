"""Tests classify_piege_response v3 — Sprint 11 P1-1 Sous-étape 0.

Référence ordre : 2026-05-01-1334-claudette-orientia-sprint11-P1-1-backstop-b-soft-classifier-v3.

Apprentissage #4 méta capitalisé feedback_pr_patterns.md : tester regex
classifier avec exemples réels variés AVANT déployer. Q11 v5b est
l'exemple réel de référence (extrait du jsonl raw bench v5b).

Cas couverts :
- IGNORANCE_OK : Q11 v5b (réel) + 5 paraphrases (donnée/info/statistique +
  ne concernent pas + ne couvrent pas)
- INVENTION_KO : 2 cas (chiffres précis + nom directeur)
- PARTIAL_FUZZY : 2 cas (esquive + redirection neutre sans aveu explicite)

Régression : préserve les patterns v2 (Q11 v5 wording "pas d'information sur").
"""
from __future__ import annotations

from scripts.diag_ab_temperature_sprint11_p1_1 import classify_piege_response


# ---------- IGNORANCE_OK : Q11 v5b réel (depuis jsonl raw bench) ----------

Q11_V5B_REEL = (
    "**TL;DR**\n"
    "1. Les fiches fournies ne concernent **pas l'IFSI de Lille** (institut de "
    "formation en soins infirmiers).\n"
    "2. Je n'ai **aucune donnée** sur le nombre d'admis 2026 ou le nom du "
    "directeur dans mes sources.\n"
    "3. Pour des infos officielles, consulte **l'IFSI de Lille directement** ou "
    "le site de l'**ARS Hauts-de-France**."
)


def test_q11_v5b_reel_classifie_ignorance_ok():
    """Cas réel observé bench v5b 2026-05-01 : la wording 'aucune donnée' +
    'ne concernent pas' doit déclencher IGNORANCE_OK. Avec v2, ce cas
    était PARTIAL_FUZZY (signal mort)."""
    assert classify_piege_response(Q11_V5B_REEL) == "IGNORANCE_OK"


# ---------- IGNORANCE_OK : 5 paraphrases supplémentaires ----------

def test_paraphrase_aucune_donnee_directe():
    answer = (
        "Les statistiques d'admission de l'IFSI de Lille ne sont pas dans mes "
        "sources. Aucune donnée disponible sur le directeur."
    )
    assert classify_piege_response(answer) == "IGNORANCE_OK"


def test_paraphrase_aucune_statistique():
    answer = "Je ne dispose d'aucune statistique sur l'IFSI de Lille."
    assert classify_piege_response(answer) == "IGNORANCE_OK"


def test_paraphrase_ne_couvrent_pas():
    answer = (
        "Mes fiches officielles ne couvrent pas les IFSI parisiens, donc je "
        "ne peux pas te donner ces chiffres."
    )
    assert classify_piege_response(answer) == "IGNORANCE_OK"


def test_paraphrase_aucune_precision():
    answer = (
        "Aucune précision n'est disponible sur l'identité du directeur ou les "
        "places ouvertes en 2026."
    )
    assert classify_piege_response(answer) == "IGNORANCE_OK"


def test_paraphrase_ne_contiennent_pas():
    answer = (
        "Les sources que j'utilise ne contiennent pas les données de l'IFSI "
        "de Lille."
    )
    assert classify_piege_response(answer) == "IGNORANCE_OK"


# ---------- IGNORANCE_OK : régression patterns v2 préservés ----------

def test_v2_pattern_pas_d_information_sur_preserve():
    """Q11 v5 wording (référence v2 fix Sous-étape 4.1) doit toujours
    classifier IGNORANCE_OK avec v3."""
    answer = (
        "Je n'ai pas d'information sur l'IFSI de Lille (admis 2026, directeur) "
        "dans les sources officielles fournies."
    )
    assert classify_piege_response(answer) == "IGNORANCE_OK"


def test_v2_pattern_ne_figurent_pas_preserve():
    answer = "Ces données ne figurent pas dans les fiches que j'utilise."
    assert classify_piege_response(answer) == "IGNORANCE_OK"


# ---------- INVENTION_KO : ne doit PAS classifier IGNORANCE_OK ----------

def test_invention_chiffres_precis_classifie_invention_ko():
    """Réponse fabriquée avec chiffres précis = INVENTION_KO, malgré
    aucun pattern d'aveu."""
    answer = (
        "L'IFSI de Lille a accueilli 250 admis en 2026, dirigé par Mme Dupont "
        "depuis 2023."
    )
    assert classify_piege_response(answer) == "INVENTION_KO"


def test_invention_nom_directeur_classifie_invention_ko():
    answer = "Le directeur s'appelle Pierre Martin selon les dernières infos."
    assert classify_piege_response(answer) == "INVENTION_KO"


# ---------- PARTIAL_FUZZY : esquive sans aveu ni invention ----------

def test_esquive_redirection_seule_classifie_partial_fuzzy():
    """Réponse qui redirige vers source officielle SANS aveu explicite et
    SANS invention chiffrée = PARTIAL_FUZZY (signal d'esquive ambiguë)."""
    answer = (
        "Pour ces informations spécifiques, je te recommande de consulter "
        "directement le site de l'IFSI ou de contacter l'ARS Hauts-de-France."
    )
    assert classify_piege_response(answer) == "PARTIAL_FUZZY"


def test_esquive_question_relancee_classifie_partial_fuzzy():
    answer = (
        "Préfères-tu que je te parle des modalités d'admission générales aux "
        "IFSI plutôt que des chiffres précis pour Lille ?"
    )
    assert classify_piege_response(answer) == "PARTIAL_FUZZY"


# ---------- Edge case : input vide ----------

def test_empty_answer_classifie_partial_fuzzy():
    assert classify_piege_response("") == "PARTIAL_FUZZY"
    assert classify_piege_response(None) == "PARTIAL_FUZZY"  # type: ignore[arg-type]
