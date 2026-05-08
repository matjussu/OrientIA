"""Prompts pour la re-rédaction des fiches annexes (ADR-060).

Les règles R1-R5 et le ton « Wikipédia neutre » sont fixés par ADR-060.
Le module expose ``build_messages(fiche)`` qui produit la liste de
messages à passer à Claude (system + user + few-shot conditionnel).
"""

from __future__ import annotations

import json
from typing import Any

# -----------------------------------------------------------------------------
# Système prompt — règles R1-R5 + ton
# -----------------------------------------------------------------------------

SYSTEM_PROMPT = """Tu es un rédacteur expert en orientation académique et professionnelle française.

Tu reçois une fiche issue d'un corpus officiel français (data.gouv.fr,
ONISEP, France Travail, INSEE, MESR, DARES, CROUS, RNCP, etc.). Ta
mission : réécrire son contenu en un paragraphe naturel français, calibré
pour qu'il puisse être correctement retrouvé par un système RAG quand un
lycéen pose une question naturelle d'orientation post-bac.

## RÈGLES NON-NÉGOCIABLES

### R1 — Préservation des faits
Tu préserves **tous les chiffres, codes, noms officiels et libellés
exacts** présents dans la fiche source. Tu n'inventes rien : tu n'ajoutes
aucune information qui n'est pas dans la fiche. Si un champ est null,
vide ou absent, tu ne mentionnes pas le sujet correspondant.

### R2 — Format
- Paragraphe unique de **40 à 250 mots** (cap dur 300, plancher conseillé 60
  mais accepté à partir de 40 si la fiche source est très pauvre).
- Français correct, ponctuation soignée, phrases pleines avec verbes
  conjugués (pas de listes énumérées en prose).
- **Tu RÉÉCRIS, tu ne nettoies pas.** Ne te contente JAMAIS de remplacer
  les `|` du format ancien par des espaces ou des virgules. Le résultat
  doit être un paragraphe NARRATIF avec des verbes, des connecteurs
  logiques, des phrases articulées — pas une suite de mots-clés et de
  chiffres séparés par de la ponctuation.
- **Ne commence JAMAIS** par un header type « Salaires PCS NN : »,
  « Métier ONISEP : », « Insertion BAC PRO — », « Vie étudiante CROUS »,
  « Compétences certifiées (RNCP… »…  Démarre par une phrase narrative
  qui contextualise (« La catégorie des artisans salariés (PCS 21)
  regroupe… », « Le métier de reporter-photographe consiste à… »,
  « En Île-de-France, la formation BAC PRO en menuiserie aluminium-verre
  affiche en 2024… »).
- **Pas de markdown** : pas de gras, pas de titres, pas de listes à puces.
- **Pas de séparateurs `|`** dans le rewrite.
- **Pas de guillemets autour de la réponse**, pas de préambule
  (« Voici… », « D'après la fiche… »).
- **Pas de fallback type « Ce métier. »** ou autre placeholder court.
  Si tu n'arrives pas à rewriter, indique-le par ``null`` côté output
  (pas par un texte tronqué).
- Inclus au moins une entité nommée exacte si présente dans la source
  (code, ville, nom officiel, intitulé).

### R3 — Vocabulaire
Tu écris dans un **français clair et accessible**, ton informatif neutre,
proche d'un article Wikipédia bien rédigé. **Pas d'argot, pas de
familiarité artificielle**, pas de tournures « comme un jeune ». Pas de
jargon administratif inutile non plus : si un terme officiel a une
expression courante équivalente, utilise-la (ex. « salaire » plutôt que
« rémunération brute moyenne »), tout en gardant l'expression officielle
si elle est distinctive (ex. « PCS 21 », « code ROME M1402 »).

### R4 — Public cible
Tu écris pour un lycéen en terminale ou un étudiant en réorientation.
Tu présentes l'information de façon factuelle et utilisable, pas pour
un statisticien ni un économiste. Privilégie les phrases courtes et les
articulations logiques (« qui », « ce qui permet », « avec », plutôt
que les pavés énumératifs).

### R5 — Pas de fluff
Tu ne dis pas « ce métier est passionnant », « voici une formation
intéressante », « il convient de ». Tu ne fais pas de jugement, tu
n'invites pas à « se renseigner davantage ». Tu présentes les faits, c'est
tout. Évite les marqueurs d'extrapolation (« généralement », « souvent »,
« il est important de »).

## FORMAT DE RÉPONSE

Tu réponds **uniquement** par le paragraphe rewritten, sans préambule,
sans markdown, sans guillemets autour."""


# -----------------------------------------------------------------------------
# Few-shot examples — calibration du ton
# -----------------------------------------------------------------------------

FEW_SHOT_EXAMPLES: list[dict[str, str]] = [
    {
        "input": json.dumps(
            {
                "id": "crous_region:lyon",
                "domain": "crous",
                "source": "crous_combine_logements_restos",
                "n_logements_total": 12000,
                "n_restos_total": 36,
                "regions_principales": ["Auvergne-Rhône-Alpes"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        "output": (
            "Le CROUS Auvergne-Rhône-Alpes gère le logement étudiant et la "
            "restauration universitaire pour les étudiants de la région, et "
            "couvre principalement les villes de Lyon, Saint-Étienne, "
            "Grenoble et Clermont-Ferrand. Il propose 12 000 logements en "
            "résidences universitaires, accessibles en priorité aux "
            "boursiers selon les critères sociaux (revenus de la famille, "
            "distance au lieu d'études). Côté restauration, le réseau "
            "comprend 36 restaurants ou cafétérias universitaires qui "
            "servent des repas à tarif social. Le CROUS gère également les "
            "demandes de bourse sur critères sociaux (DSE), les aides "
            "d'urgence ponctuelles et l'accompagnement social des étudiants. "
            "Pour postuler à un logement ou demander une bourse, les "
            "étudiants passent par le portail messervices.etudiant.gouv.fr."
        ),
    },
    {
        "input": json.dumps(
            {
                "id": "rome_metier:M1402",
                "domain": "metier_detail",
                "source": "rome_api_v4",
                "code_rome": "M1402",
                "libelle_metier": "Conseil en organisation et management d'entreprise",
                "competences_par_enjeu": [
                    {
                        "enjeu": "Conseil",
                        "competences": [
                            "Réaliser un audit organisationnel",
                            "Élaborer des préconisations",
                        ],
                    },
                    {
                        "enjeu": "Communication",
                        "competences": [
                            "Présenter des orientations stratégiques",
                        ],
                    },
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        "output": (
            "Le métier de conseil en organisation et management d'entreprise "
            "(code ROME M1402) consiste à accompagner les entreprises dans "
            "l'optimisation de leur fonctionnement. Au quotidien, un "
            "consultant en organisation réalise des audits organisationnels "
            "pour identifier les points de friction internes, élabore des "
            "préconisations stratégiques adaptées au contexte du client, et "
            "présente ces orientations aux dirigeants. C'est un métier qui "
            "demande à la fois une bonne capacité d'analyse, des qualités "
            "relationnelles solides et un sens aigu de la pédagogie. Il est "
            "exercé en cabinet de conseil (les grands cabinets type Big Four "
            "ou les boutiques spécialisées) ou en interne chez de grandes "
            "entreprises. L'accès se fait classiquement après un bac+5 école "
            "de commerce, école d'ingénieur ou master en management, sciences "
            "humaines ou économie."
        ),
    },
]


# -----------------------------------------------------------------------------
# Message builders
# -----------------------------------------------------------------------------


USER_PROMPT_TEMPLATE = """Voici une fiche annexe à réécrire. Source officielle : {source_label}, domain : {domain}.

```json
{fiche_json}
```

Réécris son contenu en un paragraphe naturel français de 80 à 250 mots, en respectant les règles R1-R5. Préserve tous les chiffres et entités nommées présents dans la fiche."""


def _serialize_fiche(fiche: dict[str, Any]) -> str:
    """Sérialise une fiche en JSON, en omettant les champs internes de
    Phase B/C qui ne servent pas au contenu (provenance interne, raw_*).
    """
    SKIP_KEYS = {"text", "text_original", "_phase", "_internal"}
    cleaned = {k: v for k, v in fiche.items() if k not in SKIP_KEYS}
    return json.dumps(cleaned, ensure_ascii=False, indent=2, default=str)


def build_messages(
    fiche: dict[str, Any], *, with_few_shot: bool = True
) -> list[dict[str, str]]:
    """Liste de messages prête pour ``client.messages.create(messages=...)``.

    ``system`` est passé séparément à l'API Anthropic, donc on retourne
    uniquement la liste user/assistant. Quand ``with_few_shot`` est True,
    les ``FEW_SHOT_EXAMPLES`` sont injectés en paires user/assistant
    avant le user final.
    """
    messages: list[dict[str, str]] = []

    if with_few_shot:
        for ex in FEW_SHOT_EXAMPLES:
            messages.append(
                {
                    "role": "user",
                    "content": USER_PROMPT_TEMPLATE.format(
                        source_label="exemple de référence",
                        domain="example",
                        fiche_json=ex["input"],
                    ),
                }
            )
            messages.append({"role": "assistant", "content": ex["output"]})

    messages.append(
        {
            "role": "user",
            "content": USER_PROMPT_TEMPLATE.format(
                source_label=fiche.get("source", "?"),
                domain=fiche.get("domain", "?"),
                fiche_json=_serialize_fiche(fiche),
            ),
        }
    )
    return messages


def get_system_prompt() -> str:
    return SYSTEM_PROMPT
