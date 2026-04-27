"""Sprint 7 — Bench enrichi 38 queries balanced (Action 2).

Étend le bench Sprint 5/6 (24 queries) à **38 queries balanced** pour
mesurer correctement les 5 axes Sprint 6 (DARES re-agg / DROM territorial
/ voie pré-bac / Inserjeunes / financement) qui étaient sous-représentés.

**Patch méthodo Jarvis cross-check (option C)** : la baseline 24q
Sprint 5/6 est **strictement préservée** (6 personas + 6 DARES + 6 blocs
+ 6 user_naturel) pour garantir la **comparabilité directe** mean
Sprint 7 vs mean Sprint 5/6 baseline 39,4% ± IC95 3,66pp. Les 14 nouvelles
queries Sprint 7 s'ajoutent SANS retirer aucune query baseline.

## Méthodologie (rappel discipline scientifique R3)

Le verdict Sprint 6 a identifié que le bench 24q originel **biaisait
l'évaluation des nouveaux axes** :
- 0/24 query DROM-spécifique → axe 2 non-mesuré
- 1/24 query bac pro-spécifique → axe 3a sous-représenté
- 3/24 queries financement → axe 4 muet (renforcé par méthodo, fixée
  par Sprint 7 Action 1)

Sprint 7 Action 2 corrige ce biais en ajoutant 14 queries ciblant
explicitement les 5 axes + multi-axes, **sans casser les 24 queries
de baseline** qui restent figées comme référence parallèle.

## Composition

| Sous-suite | n | Provenance | Préservation Sprint 5/6 |
|---|---|---|---|
| personas_v4 (q1) | 6 | Sprint 5 baseline | FIGÉE |
| dares_dedie (q01-06) | 6 | Sprint 5 baseline | FIGÉE |
| blocs_dedie (q01-06) | 6 | Sprint 5 baseline | FIGÉE |
| user_naturel (q11-16) | 6 | Sprint 5 baseline | FIGÉE |
| **NEW drom_dedie** | 4 | Sprint 7 | nouveau |
| **NEW financement_dedie** | 4 | Sprint 7 | nouveau (Action 1 unmute) |
| **NEW voie_pre_bac_dedie** | 3 | Sprint 7 | nouveau |
| **NEW multi_axes** | 3 | Sprint 7 | queries cross-axes |
| **TOTAL** | **38** | — | 24 figées + 14 nouvelles |

## Critère anti-leakage

Toutes les queries sont formulées en **langage user-naturel** (questions
qu'un·e étudiant·e ou un·e jeune en réorientation poserait spontanément),
PAS comme des prompts ingéniérisés pour matcher un corpus précis. La
formulation imite la diversité de Reddit-orientation / Forum-AdmissionsParallel /
Mission Locale.

Vérification anti-leakage manuelle : aucune query ne mentionne le nom
des champs JSON des fiches (ex `granularity:fap_region`, `taux_emploi_12m`)
ni les acronymes techniques d'OrientIA.
"""
from __future__ import annotations

from typing import Any


# --- Sprint 7 NEW : DROM-COM territorial (axe 2) ---
# Justification : axe 2 a 0/24 query active dans bench Sprint 6 → non-mesuré.
# Ces 4 queries couvrent les 4 DROM avec données factuelles dans corpus :
# Guadeloupe (BAC PRO 26.4% emploi 12m), Martinique (BTS), La Réunion (énergies
# renouvelables filière spécifique), Mayotte (cas spécifique gap Sprint 6 +
# Action 2 explicite : Mayotte couverte par axe 2 mais pas axe 3b inserjeunes).
# Pattern user-naturel : situation perso + question concrete. Pas de leakage.
DROM_QUERIES: list[dict[str, Any]] = [
    {
        "id": "drom_q01_mayotte_ingenieur_financement",
        "suite": "drom_dedie",
        "axe_target": "axe2_drom_territorial + axe4_financement",
        "text": "Je suis lycéen·ne à Mayotte et je veux faire une école d'ingénieur en métropole. Comment je peux financer ça ?",
    },
    {
        "id": "drom_q02_guadeloupe_bac_pro_insertion",
        "suite": "drom_dedie",
        "axe_target": "axe2_drom_territorial + axe3b_inserjeunes",
        "text": "En Guadeloupe, est-ce que ça vaut le coup de faire un bac pro gestion administration ? Quelles débouchés ?",
    },
    {
        "id": "drom_q03_reunion_energies_renouvelables",
        "suite": "drom_dedie",
        "axe_target": "axe2_drom_territorial",
        "text": "Quelles études faire à La Réunion pour travailler dans les énergies renouvelables localement ?",
    },
    {
        "id": "drom_q04_martinique_chomage_jeunes",
        "suite": "drom_dedie",
        "axe_target": "axe2_drom_territorial",
        "text": "Le chômage des jeunes en Martinique est de combien ? Quels secteurs recrutent vraiment ?",
    },
]


# --- Sprint 7 NEW : Financement études (axe 4 unmute Action 1) ---
# Justification : axe 4 muet par méthodo Sprint 6 → débloqué par Action 1
# (verdict `verified_by_official_source` quand fourchette + URL officielle).
# Ces 4 queries ciblent les dispositifs principaux du corpus financement
# avec des situations user-naturelles. Pattern : question de moyen-âge
# adulte ou parent/jeune.
FINANCEMENT_QUERIES: list[dict[str, Any]] = [
    {
        "id": "financement_q01_cpf_reconversion_dev",
        "suite": "financement_dedie",
        "axe_target": "axe4_financement",
        "text": "Je suis salarié de 30 ans et je veux me reconvertir en développeur web. Mon CPF peut financer combien ?",
    },
    {
        "id": "financement_q02_bourse_crous_echelons",
        "suite": "financement_dedie",
        "axe_target": "axe4_financement",
        "text": "Comment fonctionnent les échelons de la bourse CROUS ? Combien je peux toucher ?",
    },
    {
        "id": "financement_q03_handicap_etudes_aides",
        "suite": "financement_dedie",
        "axe_target": "axe4_financement",
        "text": "Mon fils a une RQTH et veut faire des études supérieures, quelles aides spécifiques existe-t-il ?",
    },
    {
        "id": "financement_q04_ptp_reconversion_salarie",
        "suite": "financement_dedie",
        "axe_target": "axe4_financement",
        "text": "Le projet de transition professionnelle PTP, c'est pour qui exactement ? Salaire maintenu pendant la formation ?",
    },
]


# --- Sprint 7 NEW : Voie pré-bac BAC PRO + CAP (axe 3a) ---
# Justification : axe 3a 1/24 query active Sprint 6 → sous-représenté.
# Ces 3 queries ciblent le catalogue / découverte / programme des bac pro
# et CAP (pas la transition individuelle). User-naturel : élève de 3ème,
# parent, ou conseiller orientation.
VOIE_PRE_BAC_QUERIES: list[dict[str, Any]] = [
    {
        "id": "voie_pre_bac_q01_bac_pro_industrie_liste",
        "suite": "voie_pre_bac_dedie",
        "axe_target": "axe3a_voie_pre_bac",
        "text": "Quels sont tous les bac pro dans le domaine industriel ? Mon fils en 3ème veut faire de la mécanique.",
    },
    {
        "id": "voie_pre_bac_q02_cap_petite_enfance_apres",
        "suite": "voie_pre_bac_dedie",
        "axe_target": "axe3a_voie_pre_bac + axe3b_inserjeunes",
        "text": "Liste des CAP en petite enfance et social. Quelles débouchés après ?",
    },
    {
        "id": "voie_pre_bac_q03_bac_pro_cyber_existe",
        "suite": "voie_pre_bac_dedie",
        "axe_target": "axe3a_voie_pre_bac",
        "text": "Est-ce qu'il existe un bac pro en cybersécurité ? Programme et débouchés ?",
    },
]


# --- Sprint 7 NEW : Multi-axes (cross-cutting) ---
# Justification : tester la cohabitation multi-corpus quand une query
# touche naturellement 2-3 axes simultanément. Pattern user-naturel :
# situation complexe avec plusieurs dimensions (orientation +
# financement + insertion + parfois territoire).
MULTI_AXES_QUERIES: list[dict[str, Any]] = [
    {
        "id": "multi_q01_decrocheur_reconversion_aide",
        "suite": "multi_axes",
        "axe_target": "axe4_financement + axe3b_inserjeunes",
        "text": "J'ai 22 ans, j'ai abandonné la fac il y a 1 an, je n'ai pas de diplôme. Quelles aides pour reprendre une formation et quels débouchés ?",
    },
    {
        "id": "multi_q02_bac_pro_drom_metropole",
        "suite": "multi_axes",
        "axe_target": "axe3a_voie_pre_bac + axe2_drom_territorial + axe4_financement",
        "text": "Je suis en bac pro maintenance en Guyane. Si je veux continuer en BTS en métropole, quelles aides à la mobilité ?",
    },
    {
        "id": "multi_q03_metiers_2030_bac_pro",
        "suite": "multi_axes",
        "axe_target": "axe1_dares_re_agg + axe3a_voie_pre_bac + axe3b_inserjeunes",
        "text": "Quels métiers vont recruter d'ici 2030 et qui sont accessibles avec un bac pro ?",
    },
]


def build_sprint7_queries(baseline_queries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Combine la baseline 24q figée + les 14 nouvelles queries Sprint 7.

    Args:
        baseline_queries: les 24 queries figées Sprint 5/6 (filtrer le set
            unifié via `select_baseline_subset_24q` : 6 personas_v4 q1 +
            6 dares_dedie + 6 blocs_dedie + 6 user_naturel q11-q16).

    Returns:
        38 queries = 24 baseline (figées strictement Sprint 5/6) + 14
        nouvelles Sprint 7. Comparabilité directe mean Sprint 7 vs
        mean Sprint 5/6 baseline figée 39,4% préservée.
    """
    out: list[dict[str, Any]] = list(baseline_queries)
    out.extend(DROM_QUERIES)
    out.extend(FINANCEMENT_QUERIES)
    out.extend(VOIE_PRE_BAC_QUERIES)
    out.extend(MULTI_AXES_QUERIES)
    return out


def select_baseline_subset_24q(all_queries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sélectionne le subset 24q figé Sprint 5/6 depuis l'ensemble unifié.

    Pattern identique au `_select_balanced_subset` du bench Sprint 5/6 :
    6 personas q1 + 6 dares + 6 blocs + 6 user_naturel = 24q.

    Sprint 7 Action 2 patch (option C Jarvis cross-check) : conservation
    stricte des 24q baseline pour garantir la comparabilité directe
    mean Sprint 7 vs mean Sprint 5/6 baseline 39,4% ± IC95 3,66pp.
    """
    by_suite: dict[str, list[dict[str, Any]]] = {}
    for q in all_queries:
        s = q.get("suite", "")
        by_suite.setdefault(s, []).append(q)

    personas = [q for q in by_suite.get("personas_v4", []) if q["id"].endswith("_q1")][:6]
    dares = by_suite.get("dares_dedie", [])[:6]
    blocs = by_suite.get("blocs_dedie", [])[:6]
    user_naturel = by_suite.get("user_naturel", [])[:6]  # q11-q16 (Sprint 5/6 strict)
    return personas + dares + blocs + user_naturel


# Alias backward compat (Sprint 7 Action 2 patch — option C)
# Garde l'ancien nom mais redirige vers la version 24q correcte.
def select_baseline_subset_22q(all_queries: list[dict[str, Any]]) -> list[dict[str, Any]]:  # noqa: D103
    """DEPRECATED Sprint 7 Action 2 patch — utilise `select_baseline_subset_24q`.

    Conservé pour compat tests anciens, mais renvoie 24q (option C Jarvis
    cross-check : préserver baseline Sprint 5/6 strict pour comparabilité).
    """
    return select_baseline_subset_24q(all_queries)


def get_query_count_per_axis_target() -> dict[str, int]:
    """Retourne le nombre de queries qui ciblent chaque axe Sprint 6.

    Permet de vérifier la balance du bench enrichi : chaque axe doit
    avoir un minimum de queries pour être mesurable correctement.
    """
    counts: dict[str, int] = {}
    for queries in (DROM_QUERIES, FINANCEMENT_QUERIES, VOIE_PRE_BAC_QUERIES, MULTI_AXES_QUERIES):
        for q in queries:
            target = q.get("axe_target", "")
            for part in [t.strip() for t in target.replace("+", ",").split(",")]:
                if part:
                    counts[part] = counts.get(part, 0) + 1
    return counts
