"""Construit `insersup_corpus.json` retrievable aggregé depuis
`insersup_insertion.json` (48 230 records granulaires MESR).

Stratégie aggregation (~500 cells, plafond) :
- Filter sur la cohorte la plus récente disponible (2023 ou 2024)
- 1 cell par (type_diplome × discipline × région métropolitaine)
- Skip aggregations vides ("Toutes disciplines" / "Tous domaines" /
  "National") → focus sur le détail discipline-régional utile RAG
- Plafond 500 cells (sécurité, sinon embedding cost et dilution)

Pour chaque cell, le texte retrievable expose :
- Cohorte + diplôme + discipline + région
- Effectifs sortants et poursuivants
- Taux d'emploi salarié à 6/12/18/24/30 mois (médian sur les
  établissements de la cellule)
- Médiane salaire nette/brute (si disponible)

Source : InserSup MESR (`src/collect/insersup_api.py`, PR #41).
Pattern dual-output : raw préservé, aggregé exposé via corpus.
"""
from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any


SRC_PATH = Path("data/processed/insersup_insertion.json")
CORPUS_PATH = Path("data/processed/insersup_corpus.json")

# Régions métropolitaines (filtre out DOM-TOM / Étranger / National pour focus)
_METROPOLE_REGIONS = {
    "Auvergne-Rhône-Alpes", "Bourgogne-Franche-Comté", "Bretagne",
    "Centre-Val de Loire", "Corse", "Grand Est", "Hauts-de-France",
    "Normandie", "Nouvelle-Aquitaine", "Occitanie", "Pays de la Loire",
    "Provence-Alpes-Côte d'Azur", "Île-de-France",
}

_GENERIC_DISCIPLINES = {"Toutes disciplines", "Tous secteurs disciplinaires"}
_GENERIC_DOMAINES = {"Tous domaines disciplinaires"}

# Cap sécurité
_MAX_CELLS = 500


def _slug(text: str) -> str:
    import re
    s = (text or "").lower()
    repl = {"é": "e", "è": "e", "ê": "e", "ë": "e", "à": "a", "â": "a",
            "ô": "o", "ö": "o", "ç": "c", "ï": "i", "î": "i", "ù": "u",
            "û": "u", "ÿ": "y"}
    for k, v in repl.items():
        s = s.replace(k, v)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:50]


def _safe_pct(val) -> str | None:
    if val is None:
        return None
    if not isinstance(val, (int, float)):
        return None
    if val != val:  # NaN check
        return None
    return f"{val * 100:.1f}%"


def _median_nullable(values: list) -> float | None:
    """Médiane d'une liste, ignorant None et NaN."""
    nums = [v for v in values if isinstance(v, (int, float)) and v == v]
    if not nums:
        return None
    return statistics.median(nums)


def _aggregate_taux_emploi(records: list[dict], horizon: str) -> float | None:
    """Médiane du taux d'emploi salarié à un horizon donné."""
    vals = []
    for r in records:
        te = r.get("taux_emploi_salarie_fr") or {}
        v = te.get(horizon)
        if v is not None:
            vals.append(v)
    return _median_nullable(vals)


def _select_cohorte_recente(data: list[dict]) -> tuple[str, list[dict]]:
    """Sélectionne la cohorte la plus récente disponible et filtre."""
    cohortes = sorted({r.get("cohorte_promo", "") for r in data if r.get("cohorte_promo")})
    if not cohortes:
        return "", []
    most_recent = cohortes[-1]
    filtered = [r for r in data if r.get("cohorte_promo") == most_recent]
    return most_recent, filtered


def build_corpus(data: list[dict] | None = None) -> list[dict]:
    if data is None:
        data = json.loads(SRC_PATH.read_text(encoding="utf-8"))
    cohorte, filtered = _select_cohorte_recente(data)
    if not filtered:
        return []

    # Group by (type_diplome, discipline, région)
    by_key: dict[tuple, list[dict]] = defaultdict(list)
    for r in filtered:
        type_dipl = r.get("type_diplome", "").strip()
        discipline = r.get("discipline", "").strip()
        region = r.get("region", "").strip()
        if not type_dipl or not discipline or not region:
            continue
        if discipline in _GENERIC_DISCIPLINES:
            continue
        if region not in _METROPOLE_REGIONS:
            continue
        by_key[(type_dipl, discipline, region)].append(r)

    out: list[dict] = []
    keys_sorted = sorted(by_key.keys())
    for (type_dipl, discipline, region) in keys_sorted:
        if len(out) >= _MAX_CELLS:
            break
        records = by_key[(type_dipl, discipline, region)]

        # Effectifs aggregés
        nb_sortants_total = sum(r.get("nb_sortants") or 0 for r in records)
        nb_poursuivants_total = sum(r.get("nb_poursuivants") or 0 for r in records)
        if nb_sortants_total < 50:
            continue  # skip cellules trop petites (peu de signal RAG)

        # Taux d'emploi salarié médians par horizon
        te_6m = _aggregate_taux_emploi(records, "6m")
        te_12m = _aggregate_taux_emploi(records, "12m")
        te_18m = _aggregate_taux_emploi(records, "18m")
        te_24m = _aggregate_taux_emploi(records, "24m")
        te_30m = _aggregate_taux_emploi(records, "30m")

        # Etablissements représentés
        etabs = sorted({r.get("etablissement", "") for r in records if r.get("etablissement")})
        n_etabs = len(etabs)
        sample_etabs = etabs[:3]

        # Niveau orientia (devrait être homogène par type_dipl)
        niveaux = {r.get("niveau_orientia", "") for r in records}
        niveau = "/".join(sorted(n for n in niveaux if n))

        parts = [
            f"Insertion professionnelle MESR — {type_dipl} en {discipline} ({region}, cohorte {cohorte})",
            f"Niveau d'études : {niveau}",
            f"Effectif sortants : {int(nb_sortants_total):,} | Poursuivants : {int(nb_poursuivants_total):,}".replace(",", " "),
            f"Établissements : {n_etabs} ({'/'.join(sample_etabs)})" if sample_etabs else f"Établissements : {n_etabs}",
        ]
        # Taux emploi narratifs
        if te_6m is not None:
            parts.append(f"Taux d'emploi salarié 6 mois après diplôme : {te_6m * 100:.0f}%")
        if te_12m is not None:
            parts.append(f"Taux 12 mois : {te_12m * 100:.0f}%")
        if te_18m is not None:
            parts.append(f"Taux 18 mois : {te_18m * 100:.0f}%")
        if te_24m is not None:
            parts.append(f"Taux 24 mois : {te_24m * 100:.0f}%")
        if te_30m is not None:
            parts.append(f"Taux 30 mois : {te_30m * 100:.0f}%")
        parts.append(f"Source : InserSup MESR enquête {cohorte}+")

        slug = f"{_slug(type_dipl)}:{_slug(discipline)}:{_slug(region)}"
        out.append({
            "id": f"insersup:{slug}",
            "domain": "insertion_pro",
            "source": "insersup_mesr",
            "cohorte": cohorte,
            "type_diplome": type_dipl,
            "niveau_orientia": niveau,
            "discipline": discipline,
            "region": region,
            "n_etablissements": n_etabs,
            "nb_sortants": int(nb_sortants_total),
            "nb_poursuivants": int(nb_poursuivants_total),
            "taux_emploi_6m": round(te_6m, 4) if te_6m else None,
            "taux_emploi_12m": round(te_12m, 4) if te_12m else None,
            "taux_emploi_18m": round(te_18m, 4) if te_18m else None,
            "taux_emploi_24m": round(te_24m, 4) if te_24m else None,
            "taux_emploi_30m": round(te_30m, 4) if te_30m else None,
            "text": " | ".join(parts),
        })

    return out


def save_corpus(records: list[dict], path: Path | None = None) -> Path:
    target = path or CORPUS_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target


def main() -> None:  # pragma: no cover
    print(f"[INSERSUP-CORPUS] loading {SRC_PATH}…")
    corpus = build_corpus()
    out = save_corpus(corpus)
    avg_text = sum(len(c["text"]) for c in corpus) // max(1, len(corpus))
    print(f"[INSERSUP-CORPUS] {len(corpus)} cells → {out}")
    print(f"[INSERSUP-CORPUS] longueur texte moyenne : {avg_text} chars")


if __name__ == "__main__":  # pragma: no cover
    main()
