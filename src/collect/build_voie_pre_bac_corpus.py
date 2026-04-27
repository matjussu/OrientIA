"""Voie pré-bac (BAC PRO + CAP) — corpus retrievable agrégé par domaine.

Source : `data/processed/onisep_formations_extended.json` (4 775 fiches
ONISEP étendues, déjà ingérées). Re-aggregation focalisée sur les
fiches `baccalauréat professionnel` (87 fiches) et `certificat
d'aptitude professionnelle` (86 fiches).

## Dimension unique apportée à OrientIA

Les fiches BAC PRO et CAP existent déjà dans `formations.json` (corpus
multi-source). Mais elles y sont noyées dans 48 914 cells dont la
majorité est post-bac. Ce corpus dédié pré-bac permet à l'**intent
classifier** de cibler les queries bac pro / CAP avec un signal fort
(domain `voie_pre_bac`, granularity tagged), améliorant le top-K
retrieval pour les queries du segment 14-18 ans.

L'axe 3b (PR #82 inserjeunes) couvre déjà la **dimension insertion
quantitative** des bac pro/CAP (taux d'emploi par spécialité × région).
Cet axe complète avec la **dimension catalogue qualitatif** :
quelles spécialités existent dans quel domaine, leurs RNCP, leurs URL
ONISEP pour fiche complète.

Pas de crawl externe nouveau — re-aggregation locale pattern axe 1
DARES + axe 3b inserjeunes.

## Stratégie aggregation (~20 cells)

- 1 cell par couple **(type_diplome × domaine NSF)** — vue par domaine
  d'études bac pro / CAP. Ex : "BAC PRO en ingénierie industrielle" ;
  "CAP en hôtellerie restauration".
- ~10 domaines distincts × 2 types = ~20 cells max (en pratique moins
  car tous les couples ne sont pas peuplés).

Domain `voie_pre_bac`. Granularity `bac_pro_domaine` ou `cap_domaine`.

Chaque cell liste les spécialités du domaine avec leur sigle + URL
ONISEP pour la fiche détaillée. Le RAG retournera la vue agrégée et
pointera vers les fiches précises via `formations.json`.

## Pourquoi pas de cells individuelles

Chaque fiche bac pro/CAP est déjà dans `formations.json` avec son
`fiche_to_text`. Faire une cell par fiche dupliquerait le retrieval
sans valeur ajoutée. La vue agrégée par domaine est le complément
manquant.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


SRC_PATH = Path("data/processed/onisep_formations_extended.json")
CORPUS_PATH = Path("data/processed/voie_pre_bac_corpus.json")


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


# Filtres types diplômes pré-bac
PRE_BAC_TYPES: dict[str, str] = {
    "baccalauréat professionnel": "BAC PRO",
    "certificat d'aptitude professionnelle": "CAP",
}


def load_extended(path: Path | None = None) -> list[dict[str, Any]]:
    target = path or SRC_PATH
    return json.loads(target.read_text(encoding="utf-8"))


def filter_pre_bac(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Garde uniquement les fiches BAC PRO et CAP."""
    return [r for r in records if r.get("type_diplome") in PRE_BAC_TYPES]


def aggregate_by_type_diplome_domaine(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """1 cell par (type_diplome × domaine NSF)."""
    by_key: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in records:
        td_raw = r.get("type_diplome", "")
        td_short = PRE_BAC_TYPES.get(td_raw, td_raw)
        domaine = (r.get("domaine") or "").strip()
        if not domaine:
            continue
        by_key[(td_short, domaine)].append(r)

    out: list[dict[str, Any]] = []
    for (td_short, domaine), fiches in sorted(by_key.items()):
        n = len(fiches)
        # Liste des spécialités (nom court + sigle si dispo)
        items: list[str] = []
        for f in sorted(fiches, key=lambda x: x.get("nom", "")):
            nom = f.get("nom", "").strip()
            sigle = (f.get("sigle_formation") or "").strip()
            url = f.get("url_onisep", "").strip()
            label = nom + (f" ({sigle})" if sigle else "")
            if url:
                label += f" — {url}"
            items.append(label)

        domaine_label = domaine.replace("_", " ")
        parts = [
            f"{td_short} en {domaine_label}",
            f"{n} spécialité{'s' if n > 1 else ''} référencée{'s' if n > 1 else ''} (ONISEP)",
            f"Liste : {' ; '.join(items)}",
            f"Pour la fiche complète de chaque spécialité (programme, débouchés, "
            f"poursuite d'études), consulter l'URL ONISEP correspondante.",
            "Source : ONISEP, base données formations (extended)",
        ]

        granularity = "bac_pro_domaine" if td_short == "BAC PRO" else "cap_domaine"
        out.append({
            "id": f"voie_pre_bac:{_slug(td_short)}:{_slug(domaine)}",
            "domain": "voie_pre_bac",
            "source": "onisep_formations_extended",
            "granularity": granularity,
            "type_diplome": td_short,
            "domaine": domaine,
            "n_specialites": n,
            "specialite_noms": [f.get("nom", "") for f in fiches],
            "text": " | ".join(parts),
        })
    return out


def aggregate_by_type_diplome_global(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """1 cell de synthèse par type_diplome (BAC PRO et CAP) — vue catalogue."""
    by_type: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        td_raw = r.get("type_diplome", "")
        td_short = PRE_BAC_TYPES.get(td_raw, td_raw)
        if td_short in ("BAC PRO", "CAP"):
            by_type[td_short].append(r)

    out: list[dict[str, Any]] = []
    for td_short, fiches in sorted(by_type.items()):
        n_total = len(fiches)
        # Distribution par domaine
        by_dom: dict[str, int] = defaultdict(int)
        for f in fiches:
            d = (f.get("domaine") or "").strip()
            if d:
                by_dom[d] += 1
        top = sorted(by_dom.items(), key=lambda x: -x[1])

        parts = [
            f"Catalogue {td_short} (synthèse globale)",
            f"{n_total} spécialités référencées sur ONISEP",
            f"{len(by_dom)} domaines couverts",
        ]
        if top:
            top_str = ", ".join(f"{d.replace('_', ' ')} ({n})" for d, n in top)
            parts.append(f"Distribution par domaine : {top_str}")

        # Note pédagogique commune
        if td_short == "BAC PRO":
            parts.append(
                "Niveau 4 (équivalent baccalauréat). Durée 3 ans après la classe de 3ème "
                "(seconde + première + terminale pro). Permet d'entrer dans la vie active "
                "ou de poursuivre en BTS/BUT (insertion immédiate moyenne ~37% à 12 mois, "
                "poursuite d'études ~60% — cf corpus inserjeunes)."
            )
        else:  # CAP
            parts.append(
                "Niveau 3. Durée 2 ans après la classe de 3ème. Diplôme professionnel "
                "court orienté insertion immédiate ou poursuite en BAC PRO / Mention "
                "Complémentaire (insertion 12 mois ~16-26% selon spécialité)."
            )

        parts.append("Source : ONISEP, base données formations (extended)")

        out.append({
            "id": f"voie_pre_bac_synthese:{_slug(td_short)}",
            "domain": "voie_pre_bac",
            "source": "onisep_formations_extended",
            "granularity": "type_diplome_synthese",
            "type_diplome": td_short,
            "n_specialites_total": n_total,
            "n_domaines_couverts": len(by_dom),
            "text": " | ".join(parts),
        })
    return out


def build_corpus(records: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    if records is None:
        records = filter_pre_bac(load_extended())
    out: list[dict[str, Any]] = []
    out.extend(aggregate_by_type_diplome_domaine(records))
    out.extend(aggregate_by_type_diplome_global(records))
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
    print(f"[VOIE_PRE_BAC] loading {SRC_PATH}")
    records = load_extended()
    pre_bac = filter_pre_bac(records)
    print(f"[VOIE_PRE_BAC] {len(records):,} fiches totales, {len(pre_bac)} pré-bac (BAC PRO + CAP)")

    corpus = build_corpus(pre_bac)
    save_corpus(corpus)
    avg_text = sum(len(c["text"]) for c in corpus) // max(1, len(corpus))
    granularities: dict[str, int] = defaultdict(int)
    for c in corpus:
        granularities[c["granularity"]] += 1
    print(f"[VOIE_PRE_BAC] {len(corpus)} cells aggregées → {CORPUS_PATH}")
    print(f"[VOIE_PRE_BAC] décomposition : {dict(granularities)}")
    print(f"[VOIE_PRE_BAC] longueur texte moyenne : {avg_text} chars")


if __name__ == "__main__":  # pragma: no cover
    main()
