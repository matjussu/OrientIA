"""Construit `metiers_corpus.json` retrievable depuis `ideo_fiches_metiers.json`.

Ce module transforme l'index éditorialisé ONISEP (1 075 fiches métiers
riches) en un corpus parallèle retrievable pour le RAG OrientIA — sans
toucher à `formations.json` ni à `fiche_to_text` (cf ADR-046 et CLAUDE.md
fichiers protégés).

Motivation (ADR-04X RAG multi-corpus) :
- Jointure ROME formations × ideo_fiches : <5 % couverture (8 codes inter
  sur 25 dans formations, 408 dans ideo)
- Match libellé exact : 3 libellés distincts (specialités vs métiers
  génériques)
- Conclusion : les 2 corpus ne s'intègrent pas par jointure forcée, ils
  s'alimentent mieux comme **corpus retrievables parallèles**

Format de sortie aligné sur l'API que `multi_corpus.py` attendra
(domaine + texte retrievable + métadonnées préservées) :

```json
{
  "id": "metier:MET.7937",
  "domain": "metier",
  "nom": "décorateur/trice sur verre",
  "libelle_humain": "décoratrice sur verre / décorateur sur verre",
  "codes_rome": ["B1302"],
  "niveau_acces": {"id": "REF.413", "libelle": "CAP ou équivalent"},
  "secteurs": ["Artisanat d'art"],
  "text": "Métier : ... | Accroche : ... | Description : ...",
  "sources": [{"url": "...", "commentaire": "..."}]
}
```

Le champ `text` est conçu pour être embeddé directement (comme l'output
de `fiche_to_text` côté formations).

Sortie : `data/processed/metiers_corpus.json`
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


IDEO_PROCESSED_PATH = Path("data/processed/ideo_fiches_metiers.json")
METIERS_CORPUS_PATH = Path("data/processed/metiers_corpus.json")

# Cap pour éviter de gonfler l'embedding (limite tokens Mistral pratique
# autour de 8 000 chars / record). format_court moyen = 1 486 chars,
# laissons-lui assez de marge pour les petits champs additionnels.
_FORMAT_COURT_MAX = 2000


def _join_libelles(record: dict[str, Any]) -> str:
    """Concatène libellé féminin et masculin si distincts (humanisation)."""
    f = (record.get("libelle_feminin") or "").strip()
    m = (record.get("libelle_masculin") or "").strip()
    if f and m and f != m:
        return f"{f} / {m}"
    return f or m or (record.get("nom_metier") or "").strip()


def _format_niveau(niveau: dict[str, Any] | None) -> str:
    if not niveau:
        return ""
    libelle = (niveau.get("libelle") or "").strip()
    return libelle


def _format_list_libelles(items: list[dict[str, Any]] | None, limit: int = 6) -> str:
    if not items:
        return ""
    libelles = [
        (i.get("libelle") or "").strip() for i in items if i.get("libelle")
    ]
    if not libelles:
        return ""
    return ", ".join(libelles[:limit])


def build_text(record: dict[str, Any]) -> str:
    """Construit le texte retrievable (analogue de `fiche_to_text` côté formations).

    Composition :
    - Métier (libellé humain F/M)
    - Synonymes (titres alternatifs)
    - Accroche (hook ~270 chars)
    - Description (format_court tronqué à 2000 chars)
    - Niveau d'accès minimum
    - Formations minimales requises (libellés diplômes)
    - Secteurs d'activité
    - Centres d'intérêt taxonomiques
    - Statuts professionnels (salarié / artisan / libéral / fonctionnaire)
    """
    parts = []

    nom = (record.get("nom_metier") or "").strip()
    if nom:
        parts.append(f"Métier : {nom}")

    humain = _join_libelles(record)
    if humain and humain != nom:
        parts.append(f"Libellé : {humain}")

    synonymes = record.get("synonymes") or []
    if synonymes:
        parts.append(f"Synonymes : {', '.join(synonymes[:5])}")

    accroche = (record.get("accroche") or "").strip()
    if accroche:
        parts.append(f"Accroche : {accroche}")

    description = (record.get("format_court") or "").strip()
    if description:
        if len(description) > _FORMAT_COURT_MAX:
            description = description[:_FORMAT_COURT_MAX].rsplit(" ", 1)[0] + "…"
        parts.append(f"Description : {description}")

    niveau = _format_niveau(record.get("niveau_acces_min"))
    if niveau:
        parts.append(f"Niveau d'accès minimum : {niveau}")

    formations = _format_list_libelles(record.get("formations_min_requise"), limit=6)
    if formations:
        parts.append(f"Formations minimales : {formations}")

    secteurs = _format_list_libelles(record.get("secteurs_activite"), limit=5)
    if secteurs:
        parts.append(f"Secteurs d'activité : {secteurs}")

    centres = _format_list_libelles(record.get("centres_interet"), limit=5)
    if centres:
        parts.append(f"Centres d'intérêt : {centres}")

    statuts = _format_list_libelles(record.get("statuts"), limit=5)
    if statuts:
        parts.append(f"Statuts : {statuts}")

    return " | ".join(parts)


def normalize_to_corpus(record: dict[str, Any]) -> dict[str, Any]:
    """Convertit une fiche ONISEP normalisée en record corpus retrievable."""
    identifiant = (record.get("identifiant") or "").strip()
    nom = (record.get("nom_metier") or "").strip()

    return {
        "id": f"metier:{identifiant}" if identifiant else f"metier:{nom}",
        "domain": "metier",
        "source": "onisep_ideo_fiches",
        "nom": nom,
        "libelle_humain": _join_libelles(record),
        "synonymes": list(record.get("synonymes") or []),
        "codes_rome": list(record.get("codes_rome_v3") or []),
        "niveau_acces": record.get("niveau_acces_min"),
        "formations_min_requise": list(record.get("formations_min_requise") or []),
        "secteurs": [
            (s.get("libelle") or "").strip()
            for s in (record.get("secteurs_activite") or [])
            if s.get("libelle")
        ],
        "centres_interet": [
            (c.get("libelle") or "").strip()
            for c in (record.get("centres_interet") or [])
            if c.get("libelle")
        ],
        "statuts": [
            (s.get("libelle") or "").strip()
            for s in (record.get("statuts") or [])
            if s.get("libelle")
        ],
        "text": build_text(record),
        "sources": list(record.get("sources_numeriques") or []),
    }


def build_corpus(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map normalize sur tous les records, dédoublonne par id (premier gagne)."""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for r in records:
        c = normalize_to_corpus(r)
        if c["id"] in seen:
            continue
        seen.add(c["id"])
        out.append(c)
    return out


def load_ideo(path: Path | None = None) -> list[dict[str, Any]]:
    target = path or IDEO_PROCESSED_PATH
    return json.loads(target.read_text(encoding="utf-8"))


def save_corpus(records: list[dict[str, Any]], path: Path | None = None) -> Path:
    target = path or METIERS_CORPUS_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target


def main() -> None:  # pragma: no cover
    print(f"[METIERS-CORPUS] loading {IDEO_PROCESSED_PATH}")
    raw = load_ideo()
    corpus = build_corpus(raw)
    out = save_corpus(corpus)
    avg_text_len = sum(len(c["text"]) for c in corpus) // max(1, len(corpus))
    with_rome = sum(1 for c in corpus if c["codes_rome"])
    print(f"[METIERS-CORPUS] {len(corpus)} records → {out}")
    print(f"[METIERS-CORPUS] longueur texte moyenne : {avg_text_len} chars")
    print(f"[METIERS-CORPUS] avec codes ROME : {with_rome}/{len(corpus)}")


if __name__ == "__main__":  # pragma: no cover
    main()
