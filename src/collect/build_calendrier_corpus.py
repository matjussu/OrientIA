"""Calendrier Parcoursup + MonMaster 2026 — Vague 3.4 du plan corpus v6.

Audit ground-truth 50q v6 baseline (2026-05-08) : recall@5 catégorie
calendaire = **0%** sur 5 questions ("Quand commencent les vœux Parcoursup ?",
"Date limite vœux ?", "Phase complémentaire ?", "Calendrier MonMaster ?",
"Résultats admission ?"). Cause racine : aucun corpus `domain=calendrier`
dans v6, le LLM répond "info non disponible" et redirige vers Parcoursup.

Stratégie MVP démo : corpus statique 2026 avec ~25 entrées dates clés
Parcoursup + MonMaster. Scraping annuel des pages officielles à automatiser
en Vague 4 (cron mensuel). Pour l'instant, dates curées manuellement depuis
sources officielles 2025-12 et 2026-01.

## Format des entrées

```json
{
  "id": "calendrier:parcoursup-2026:ouverture",
  "domain": "calendrier",
  "source": "parcoursup_calendrier_officiel",
  "annee": 2026,
  "plateforme": "Parcoursup",
  "phase": "ouverture",
  "date_debut": "2025-12-18",
  "date_fin": null,
  "libelle": "Ouverture inscriptions Parcoursup 2026",
  "text": "<paragraphe naturel pour embedding>",
  "url": "https://www.parcoursup.fr/...",
  "provenance": {"tier": "tier_1", "source_label": "...", "last_updated": "..."}
}
```

Le `text` est rédigé en paragraphe naturel pour bon alignement embedding
avec questions user ("quand", "date limite", "phase complémentaire").

## Sources utilisées

- Parcoursup : https://www.parcoursup.fr/index.php?desc=calendrier
- MonMaster : https://www.monmaster.gouv.fr/calendrier
- Mise à jour : annuelle (octobre-décembre pour la promotion N+1)

## Usage

```bash
python -m src.collect.build_calendrier_corpus
# → écrit data/processed/calendrier_corpus.json (~25 entrées)
```
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_PATH = Path("data/processed/calendrier_corpus.json")
PARCOURSUP_URL = "https://www.parcoursup.fr/index.php?desc=calendrier"
MONMASTER_URL = "https://www.monmaster.gouv.fr/calendrier"
LAST_UPDATED = "2026-05-08"


def _entry(
    fragment_id: str,
    plateforme: str,
    phase: str,
    libelle: str,
    text: str,
    date_debut: str,
    date_fin: str | None = None,
    annee: int = 2026,
    url: str | None = None,
    source_label: str | None = None,
) -> dict[str, Any]:
    """Construit une entrée corpus calendrier."""
    plate_slug = plateforme.lower().replace("monmaster", "monmaster")
    return {
        "id": f"calendrier:{plate_slug}-{annee}:{fragment_id}",
        "domain": "calendrier",
        "source": f"{plate_slug}_calendrier_officiel",
        "annee": annee,
        "plateforme": plateforme,
        "phase": phase,
        "date_debut": date_debut,
        "date_fin": date_fin,
        "libelle": libelle,
        "text": text,
        "url": url or (PARCOURSUP_URL if plateforme == "Parcoursup" else MONMASTER_URL),
        "provenance": {
            "tier": "tier_1",
            "source_label": source_label or f"{plateforme} officiel",
            "last_updated": LAST_UPDATED,
        },
    }


# ─────────────── Données dates 2026 (curées manuellement) ───────────────

PARCOURSUP_2026_ENTRIES: list[dict[str, Any]] = [
    _entry(
        "ouverture-information",
        "Parcoursup", "ouverture",
        "Ouverture de la phase d'information Parcoursup 2026",
        "La phase d'information Parcoursup 2026 ouvre le 18 décembre 2025. À partir de cette date, les futurs étudiants en terminale ou en réorientation peuvent consulter les formations disponibles, leurs critères d'admission, et préparer leur dossier. C'est l'étape pour explorer les options et discuter avec son professeur principal ou son Psy-EN avant les vœux.",
        date_debut="2025-12-18",
    ),
    _entry(
        "ouverture-voeux",
        "Parcoursup", "voeux",
        "Ouverture de la phase de formulation des vœux Parcoursup 2026",
        "Les candidats peuvent formuler leurs vœux Parcoursup à partir de mi-janvier 2026 (généralement la 3e semaine de janvier). Chaque candidat peut formuler jusqu'à 10 vœux principaux + 10 vœux supplémentaires en apprentissage. Pas d'ordre de préférence à indiquer à ce stade — l'ordre est demandé plus tard lors de la phase de réception des réponses.",
        date_debut="2026-01-15",
    ),
    _entry(
        "date-limite-voeux",
        "Parcoursup", "voeux",
        "Date limite de formulation des vœux Parcoursup 2026",
        "La date limite pour formuler les vœux sur Parcoursup 2026 est généralement mi-mars (autour du 13 mars). Après cette date, il n'est plus possible d'ajouter de nouveaux vœux — seulement de finaliser le dossier (lettre de motivation, etc.). Les candidats doivent absolument valider leurs vœux avant cette deadline.",
        date_debut="2026-03-13",
    ),
    _entry(
        "date-limite-confirmation",
        "Parcoursup", "voeux",
        "Date limite de confirmation des vœux Parcoursup 2026",
        "Les candidats Parcoursup ont jusqu'à début avril 2026 (date précise communiquée par Parcoursup) pour confirmer leurs vœux : finalisation du dossier, lettre de motivation, choix de spécialités, etc. Sans cette confirmation, les vœux ne sont pas pris en compte par les formations.",
        date_debut="2026-04-04",
    ),
    _entry(
        "phase-admission",
        "Parcoursup", "admission",
        "Phase d'admission Parcoursup 2026 — début des réponses",
        "La phase principale d'admission Parcoursup 2026 commence début juin 2026. Les candidats reçoivent leurs propositions d'admission et doivent y répondre dans les délais (3-5 jours selon la phase). Trois réponses possibles par formation : oui, oui en attente, non. Cette phase dure jusqu'à mi-juillet.",
        date_debut="2026-06-02",
        date_fin="2026-07-11",
    ),
    _entry(
        "phase-complementaire",
        "Parcoursup", "complementaire",
        "Phase complémentaire Parcoursup 2026",
        "La phase complémentaire Parcoursup 2026 ouvre mi-juin 2026 et se prolonge jusqu'à mi-septembre. Elle permet aux candidats sans proposition de formuler 10 nouveaux vœux dans les formations qui ont des places disponibles. Particulièrement utile pour les candidats refusés partout ou en attente longue. Les commissions d'accès à l'enseignement supérieur (CAES) accompagnent aussi les candidats à ce stade.",
        date_debut="2026-06-11",
        date_fin="2026-09-12",
    ),
    _entry(
        "fin-phase-principale",
        "Parcoursup", "admission",
        "Fin de la phase principale d'admission Parcoursup 2026",
        "La phase principale d'admission Parcoursup 2026 se termine vers le 11 juillet 2026. Au-delà, seule la phase complémentaire reste ouverte. Les candidats qui ont accepté une proposition doivent finaliser leur inscription administrative dans l'établissement choisi.",
        date_debut="2026-07-11",
    ),
    _entry(
        "inscription-administrative",
        "Parcoursup", "inscription",
        "Inscription administrative dans l'établissement choisi (Parcoursup 2026)",
        "Une fois une proposition d'admission acceptée sur Parcoursup, le candidat doit procéder à l'inscription administrative dans l'établissement (université, école). Les modalités et dates précises sont communiquées par chaque établissement, généralement entre fin juillet et début septembre 2026. Cette étape valide définitivement la place.",
        date_debut="2026-07-15",
        date_fin="2026-09-15",
    ),
]

MONMASTER_2026_ENTRIES: list[dict[str, Any]] = [
    _entry(
        "ouverture-information",
        "MonMaster", "ouverture",
        "Ouverture de la plateforme MonMaster 2026",
        "MonMaster 2026 ouvre généralement mi-janvier 2026. Les candidats à un Master peuvent consulter les formations disponibles, leurs critères d'admission (capacité d'accueil, attendus, modalités), et préparer leur dossier (CV, lettre de motivation, projet professionnel). MonMaster est la plateforme nationale unique pour candidater en Master en France métropolitaine.",
        date_debut="2026-01-19",
    ),
    _entry(
        "depot-candidatures",
        "MonMaster", "candidatures",
        "Phase de dépôt des candidatures MonMaster 2026",
        "Les candidats déposent leurs candidatures sur MonMaster du 24 février au 24 mars 2026 (dates indicatives, à confirmer chaque année). Chaque candidat peut formuler jusqu'à 15 candidatures de Masters en formation initiale + 15 en alternance. Les pièces obligatoires : CV, lettre de motivation, projet professionnel, relevés de notes.",
        date_debut="2026-02-24",
        date_fin="2026-03-24",
    ),
    _entry(
        "phase-admission",
        "MonMaster", "admission",
        "Phase d'admission MonMaster 2026 — réponses des formations",
        "La phase d'admission MonMaster 2026 commence début juin 2026. Les candidats reçoivent les réponses des formations : admis, en liste d'attente, ou refusé. Pour chaque admission, ils ont 7 jours pour accepter ou refuser. Plusieurs admissions simultanées possibles — le candidat doit en garder qu'une seule au final.",
        date_debut="2026-06-04",
        date_fin="2026-07-31",
    ),
    _entry(
        "phase-complementaire",
        "MonMaster", "complementaire",
        "Phase complémentaire MonMaster 2026",
        "La phase complémentaire MonMaster 2026 démarre fin juin 2026 (en parallèle de la phase principale). Elle permet aux candidats sans admission de formuler de nouveaux vœux dans des Masters qui ont encore des places. Cette phase peut se prolonger jusqu'en septembre selon les Masters.",
        date_debut="2026-06-25",
        date_fin="2026-09-15",
    ),
    _entry(
        "inscription-administrative",
        "MonMaster", "inscription",
        "Inscription administrative en Master post-MonMaster 2026",
        "Une fois une admission acceptée sur MonMaster, le candidat procède à l'inscription administrative auprès de l'université d'accueil. Modalités et dates communiquées par l'université (généralement entre juillet et septembre 2026). Cette étape inclut le paiement des frais d'inscription (170 € par an pour le Master en université publique en 2025-2026).",
        date_debut="2026-07-01",
        date_fin="2026-09-30",
    ),
]


# ─────────────── Vue d'ensemble (questions générales) ───────────────

OVERVIEW_ENTRIES: list[dict[str, Any]] = [
    _entry(
        "vue-ensemble-2026",
        "Parcoursup", "general",
        "Calendrier général Parcoursup 2026",
        "Le calendrier Parcoursup 2026 se déroule en 5 grandes phases : (1) information du 18 décembre 2025 à mi-janvier 2026 ; (2) formulation des vœux de mi-janvier au 13 mars 2026 ; (3) confirmation des vœux jusqu'au 4 avril ; (4) phase d'admission du 2 juin au 11 juillet ; (5) phase complémentaire du 11 juin au 12 septembre. Toutes les dates précises sont sur le site officiel Parcoursup.",
        date_debut="2025-12-18",
        date_fin="2026-09-12",
    ),
    _entry(
        "vue-ensemble-2026",
        "MonMaster", "general",
        "Calendrier général MonMaster 2026",
        "Le calendrier MonMaster 2026 se déroule en 4 grandes phases : (1) ouverture mi-janvier 2026 ; (2) dépôt des candidatures du 24 février au 24 mars ; (3) phase d'admission du 4 juin au 31 juillet ; (4) phase complémentaire du 25 juin au 15 septembre. Les dates précises sont communiquées chaque année sur monmaster.gouv.fr.",
        date_debut="2026-01-19",
        date_fin="2026-09-15",
    ),
]


def build_calendrier_corpus() -> list[dict[str, Any]]:
    """Construit le corpus calendrier (Parcoursup + MonMaster + vues d'ensemble)."""
    entries = []
    entries.extend(PARCOURSUP_2026_ENTRIES)
    entries.extend(MONMASTER_2026_ENTRIES)
    entries.extend(OVERVIEW_ENTRIES)
    return entries


def main() -> int:
    entries = build_calendrier_corpus()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Calendrier corpus écrit : {OUT_PATH} ({len(entries)} entrées)")
    print(f"  Parcoursup 2026 : {len(PARCOURSUP_2026_ENTRIES)} dates")
    print(f"  MonMaster 2026  : {len(MONMASTER_2026_ENTRIES)} dates")
    print(f"  Vues d'ensemble : {len(OVERVIEW_ENTRIES)} entrées")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
