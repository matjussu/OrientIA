"""Financement études et formation — corpus retrievable curé.

Source : `data/raw/financement/dispositifs_2026.json` (JSON curé manuellement
depuis sources officielles publiques etudiant.gouv.fr, education.gouv.fr,
moncompteformation.gouv.fr, service-public.fr, France Travail, AGEFIPH).

Licence : sources publiques (Etalab, service-public.fr, etc.).

## Dimension unique apportée à OrientIA

Aucune source d'OrientIA actuelle ne couvre les **dispositifs de financement
des études et de la formation**. C'est l'un des gaps data les plus impactants
identifiés dans le verdict Sprint 5 §4 P1 ("financement études — gap critique").

**Critique pour l'orientation** : un·e étudiant·e ou un·e adulte en
reconversion a besoin de connaître les aides disponibles selon sa
situation (initial/continue/reconversion/handicap). Sans cette info,
le RAG ne peut pas répondre aux queries de financement, qui sont
fréquentes dans le bench.

## Stratégie aggregation

Le JSON raw contient ~25 dispositifs principaux structurés. Le corpus
aggregé produit :

- 1 cell par **dispositif** (granularity: "dispositif") — vue détaillée
  individuelle d'un dispositif (bourse CROUS, CPF, PTP, etc.)
- 1 cell par **voie** (granularity: "voie") — vue synthétique listant
  tous les dispositifs disponibles pour une voie : `initial`, `continue`,
  `reconversion`, `handicap`. Permet à l'intent classifier de cibler par
  cas d'usage user.

Domain `financement_etudes`. Total ~30 cells.

## Anti-hallucination défensive

Les chiffres exacts (montants, plafonds) **changent chaque année**. Le corpus
inclut systématiquement :
- Une fourchette approximative sourcée à une année (ex "2024-2025")
- L'URL officielle pour vérification de l'année en cours
- Un disclaimer "consulter source officielle pour montant exact"

Cette discipline protège contre les hallucinations LLM sur les chiffres
non-verifiés et reste utile pour le RAG (le user peut vérifier le chiffre
à jour sur le lien fourni).
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


RAW_PATH = Path("data/raw/financement/dispositifs_2026.json")
CORPUS_PATH = Path("data/processed/financement_corpus.json")


def _slug(text: str) -> str:
    import re
    s = (text or "").lower()
    repl = {"é": "e", "è": "e", "ê": "e", "ë": "e", "à": "a", "â": "a",
            "ô": "o", "ö": "o", "ç": "c", "ï": "i", "î": "i", "ù": "u",
            "û": "u", "ÿ": "y"}
    for k, v in repl.items():
        s = s.replace(k, v)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:60]


VOIE_LABELS: dict[str, str] = {
    "initial": "formation initiale (lycée, post-bac jusqu'au diplôme)",
    "continue": "formation continue (salariés, agents publics, indépendants)",
    "reconversion": "reconversion professionnelle (changement de métier)",
    "handicap": "formation et insertion en situation de handicap",
}


def load_raw(path: Path | None = None) -> dict[str, Any]:
    """Charge le JSON raw curé."""
    target = path or RAW_PATH
    return json.loads(target.read_text(encoding="utf-8"))


def _format_montants(montants: dict[str, Any] | None) -> str | None:
    """Formate la dict de montants en texte lisible."""
    if not isinstance(montants, dict) or not montants:
        return None
    parts: list[str] = []
    if "min" in montants and "max" in montants:
        annee = montants.get("annee", "")
        parts.append(f"{montants['min']}-{montants['max']}€" + (f" ({annee})" if annee else ""))
    elif "forfait" in montants:
        annee = montants.get("annee", "")
        parts.append(f"forfait {montants['forfait']}€" + (f" ({annee})" if annee else ""))
    elif "max" in montants:
        parts.append(f"max {montants['max']}€")
    elif "abondement_standard" in montants:
        # CPF special
        sub: list[str] = []
        if "abondement_standard" in montants:
            sub.append(f"{montants['abondement_standard']}€/an")
        if "plafond" in montants:
            sub.append(f"plafond {montants['plafond']}€")
        if "abondement_non_qualifie" in montants:
            sub.append(f"non-qualifiés {montants['abondement_non_qualifie']}€/an")
        if "plafond_non_qualifie" in montants:
            sub.append(f"plafond non-qualifiés {montants['plafond_non_qualifie']}€")
        parts.extend(sub)
    note = montants.get("note", "")
    if note:
        parts.append(note)
    return " ; ".join(parts) if parts else None


def aggregate_by_dispositif(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """1 cell par dispositif — vue individuelle détaillée."""
    out: list[dict[str, Any]] = []
    for d in raw.get("dispositifs", []):
        nom = d.get("nom", "")
        organisme = d.get("organisme", "")
        public = d.get("public_cible", "")
        voies = d.get("voies", [])

        parts = [
            f"Financement — {nom}",
            f"Organisme : {organisme}" if organisme else None,
            f"Public cible : {public}" if public else None,
        ]
        if voies:
            voie_labels = ", ".join(VOIE_LABELS.get(v, v) for v in voies)
            parts.append(f"Concerne : {voie_labels}")

        # Montants : 4 patterns possibles dans le JSON raw
        mt_an = _format_montants(d.get("montants_approximatifs_eur_an"))
        mt_mois = _format_montants(d.get("montants_approximatifs_eur_mois"))
        mt_forfait = _format_montants(d.get("montants_approximatifs_eur"))
        mt_text = d.get("montants_approximatifs")
        if mt_an:
            parts.append(f"Montants annuels approximatifs : {mt_an}")
        if mt_mois:
            parts.append(f"Montants mensuels approximatifs : {mt_mois}")
        if mt_forfait:
            parts.append(f"Montant approximatif : {mt_forfait}")
        if mt_text and isinstance(mt_text, str):
            parts.append(f"Montant : {mt_text}")

        # Conditions
        conditions = d.get("conditions_cles", [])
        if conditions:
            parts.append("Conditions principales : " + " ; ".join(conditions))

        # Demande
        demande = d.get("demande", "")
        if demande:
            parts.append(f"Demande : {demande}")

        # Spécificité
        spec = d.get("specificite", "")
        if spec:
            parts.append(f"À noter : {spec}")

        # Source officielle (load-bearing pour anti-hallu)
        source = d.get("source_officielle", "")
        if source:
            parts.append(f"Source officielle (montant exact année en cours) : {source}")

        text = " | ".join(p for p in parts if p)

        out.append({
            "id": f"financement_dispositif:{d['id']}",
            "domain": "financement_etudes",
            "source": "financement_dispositifs_curated",
            "granularity": "dispositif",
            "dispositif_id": d["id"],
            "nom": nom,
            "organisme": organisme,
            "voies": voies,
            "source_officielle": source,
            "text": text,
        })
    return out


def aggregate_by_voie(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """1 cell par voie (initial/continue/reconversion/handicap) — vue synthétique.

    Liste tous les dispositifs disponibles pour la voie. Permet à l'intent
    classifier de cibler les queries cas-d'usage ("comment financer une
    reconversion ?" → cell voie:reconversion).
    """
    by_voie: dict[str, list[dict]] = defaultdict(list)
    for d in raw.get("dispositifs", []):
        for v in d.get("voies", []):
            by_voie[v].append(d)

    out: list[dict[str, Any]] = []
    for voie, dispositifs in sorted(by_voie.items()):
        label = VOIE_LABELS.get(voie, voie)
        n = len(dispositifs)

        # Liste des dispositifs (nom court + organisme)
        items: list[str] = []
        for d in dispositifs:
            nom_court = d.get("nom", "").split(" — ")[0]
            organisme = d.get("organisme", "")
            items.append(f"{nom_court} ({organisme})" if organisme else nom_court)

        parts = [
            f"Dispositifs de financement pour {label}",
            f"{n} dispositifs principaux disponibles",
            "Liste : " + " ; ".join(items),
            "Pour le détail montant, conditions et démarches de chaque dispositif, voir la source officielle correspondante.",
        ]

        out.append({
            "id": f"financement_voie:{_slug(voie)}",
            "domain": "financement_etudes",
            "source": "financement_dispositifs_curated",
            "granularity": "voie",
            "voie": voie,
            "voie_label": label,
            "n_dispositifs": n,
            "dispositifs_ids": [d["id"] for d in dispositifs],
            "text": " | ".join(parts),
        })
    return out


def build_corpus(raw: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    if raw is None:
        raw = load_raw()
    out: list[dict[str, Any]] = []
    out.extend(aggregate_by_dispositif(raw))
    out.extend(aggregate_by_voie(raw))
    return out


def save_corpus(records: list[dict[str, Any]], path: Path | None = None) -> Path:
    target = path or CORPUS_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target


def main() -> None:  # pragma: no cover
    print(f"[FINANCEMENT] loading {RAW_PATH}")
    raw = load_raw()
    n_disp = len(raw.get("dispositifs", []))
    print(f"[FINANCEMENT] {n_disp} dispositifs raw, version {raw.get('version', 'n/a')}")

    corpus = build_corpus(raw)
    save_corpus(corpus)
    avg_text = sum(len(c["text"]) for c in corpus) // max(1, len(corpus))
    granularities: dict[str, int] = defaultdict(int)
    for c in corpus:
        granularities[c["granularity"]] += 1
    print(f"[FINANCEMENT] {len(corpus)} cells aggregées → {CORPUS_PATH}")
    print(f"[FINANCEMENT] décomposition : {dict(granularities)}")
    print(f"[FINANCEMENT] longueur texte moyenne : {avg_text} chars")


if __name__ == "__main__":  # pragma: no cover
    main()
