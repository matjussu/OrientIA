"""Construit `insee_salaan_corpus.json` retrievable aggregé depuis
`insee_salaires_2023.json` (10 050 records granulaires).

Stratégie aggregation (~80 cells) :
- 1 cell France globale (vue d'ensemble salaires PCS)
- 1 cell par cs_libelle (28 cells, France aggregée par PCS détaillée)
- 1 cell par grand groupe PCS × région (5 PCS × top 6 régions = 30 cells)

Total ~60 cells (vs 10 050 raw → 167× réduction de bruit top-K).

Pour chaque cell, le texte retrievable expose les médianes salariales
(brut/net annuel/mensuel) par tranche âge dominante, l'effectif total
pondéré, et la répartition H/F.

Source : `insee_salaires_2023.json` produit par `src/collect/insee_salaan.py`
(PR #41). Source brute : INSEE SALAAN 2023.
"""
from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any


SRC_PATH = Path("data/processed/insee_salaires_2023.json")
CORPUS_PATH = Path("data/processed/insee_salaan_corpus.json")

# Grands groupes PCS (premier chiffre du cs_code)
_PCS_GROUPS = {
    "2": "Cadres et professions intellectuelles supérieures",
    "3": "Professions intermédiaires",
    "4": "Employés",
    "5": "Ouvriers et employés (groupe 5)",
    "6": "Ouvriers et professions de services (groupe 6)",
}

# Top régions ciblées pour le RAG OrientIA (étudiants 17-25)
_TARGET_REGIONS = {
    "Île-de-France",
    "Auvergne-Rhône-Alpes",
    "Hauts-de-France",
    "Occitanie",
    "Nouvelle-Aquitaine",
    "Bretagne",
}


def _slug(text: str) -> str:
    import re
    s = (text or "").lower()
    repl = {"é": "e", "è": "e", "ê": "e", "à": "a", "â": "a",
            "ô": "o", "ö": "o", "ç": "c", "ï": "i", "î": "i", "ù": "u",
            "ÿ": "y"}
    for k, v in repl.items():
        s = s.replace(k, v)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def _weighted_median(records: list[dict], field: str) -> float | None:
    """Médiane pondérée par effectif sur un champ salaire."""
    values_weights = []
    for r in records:
        val = r.get(field)
        eff = r.get("effectif_pondere") or 0
        if val is None or not isinstance(val, (int, float)):
            continue
        if eff <= 0:
            continue
        values_weights.append((float(val), float(eff)))
    if not values_weights:
        return None
    values_weights.sort(key=lambda x: x[0])
    total_w = sum(w for _, w in values_weights)
    cum = 0
    for v, w in values_weights:
        cum += w
        if cum >= total_w / 2:
            return round(v, 0)
    return values_weights[-1][0]


def _aggregate_france_globale(data: list[dict]) -> dict:
    """1 cell vue France globale."""
    n_pcs = len(set(r["cs_libelle"] for r in data if r.get("cs_libelle")))
    n_regions = len(set(r["region_libelle"] for r in data if r.get("region_libelle")))
    eff_total = sum(r.get("effectif_pondere") or 0 for r in data)
    median_annuel = _weighted_median(data, "salaire_net_median_annuel")
    parts = [
        "Salaires nets annuels par PCS et région — France 2023 (INSEE SALAAN)",
        f"Source : INSEE base SALAAN 2023, {n_pcs} catégories socioprofessionnelles, {n_regions} régions",
        f"Effectif total pondéré couvert : {int(eff_total):,}".replace(",", " "),
    ]
    if median_annuel:
        parts.append(f"Salaire net médian annuel France toutes PCS confondues : {int(median_annuel):,} €".replace(",", " "))
    return {
        "id": "insee_salaan:france",
        "domain": "insee_salaire",
        "source": "insee_salaan_2023",
        "n_records_source": len(data),
        "effectif_total": int(eff_total),
        "text": " | ".join(parts),
    }


def _aggregate_by_cs_libelle(data: list[dict]) -> list[dict]:
    """1 cell par cs_libelle (28 cells). France entière par PCS détaillée."""
    by_cs: dict[tuple, list[dict]] = defaultdict(list)
    for r in data:
        cs_code = r.get("cs_code")
        cs_libelle = r.get("cs_libelle")
        if not cs_code or not cs_libelle:
            continue
        by_cs[(cs_code, cs_libelle)].append(r)

    out: list[dict] = []
    for (cs_code, cs_libelle), records in by_cs.items():
        eff_total = sum(r.get("effectif_pondere") or 0 for r in records)
        median_an = _weighted_median(records, "salaire_net_median_annuel")
        median_mois = _weighted_median(records, "salaire_net_median_mensuel")
        # Distribution H/F (pondérée)
        eff_h = sum(r.get("effectif_pondere") or 0 for r in records if r.get("sexe_libelle") == "Hommes")
        eff_f = sum(r.get("effectif_pondere") or 0 for r in records if r.get("sexe_libelle") == "Femmes")
        pct_f = (eff_f / max(1, eff_h + eff_f)) * 100 if (eff_h + eff_f) else 0
        # Région dominante
        regions_eff: dict[str, float] = defaultdict(float)
        for r in records:
            reg = r.get("region_libelle") or ""
            regions_eff[reg] += r.get("effectif_pondere") or 0
        top_regions = sorted(regions_eff.items(), key=lambda kv: -kv[1])[:3]

        parts = [
            f"Salaires PCS {cs_code} : {cs_libelle} (France 2023)",
            f"Effectif pondéré : {int(eff_total):,}".replace(",", " "),
        ]
        if median_an:
            parts.append(f"Salaire net médian annuel : {int(median_an):,} €".replace(",", " "))
        if median_mois:
            parts.append(f"Salaire net médian mensuel : {int(median_mois):,} €".replace(",", " "))
        parts.append(f"Répartition H/F : {pct_f:.0f}% femmes")
        if top_regions:
            tops = ", ".join(f"{reg} ({int(eff)})" for reg, eff in top_regions if reg)
            parts.append(f"Top régions effectif : {tops}")
        parts.append("Source : INSEE SALAAN 2023")

        out.append({
            "id": f"insee_salaan:cs:{cs_code}",
            "domain": "insee_salaire",
            "source": "insee_salaan_2023",
            "cs_code": cs_code,
            "cs_libelle": cs_libelle,
            "effectif_total": int(eff_total),
            "salaire_net_median_annuel": int(median_an) if median_an else None,
            "salaire_net_median_mensuel": int(median_mois) if median_mois else None,
            "pct_femmes": round(pct_f, 1),
            "text": " | ".join(parts),
        })
    return out


def _aggregate_by_pcs_group_x_region(data: list[dict]) -> list[dict]:
    """1 cell par (groupe PCS × région) sur top régions cibles."""
    by_key: dict[tuple, list[dict]] = defaultdict(list)
    for r in data:
        cs_code = (r.get("cs_code") or "").strip()
        if not cs_code:
            continue
        prefix = cs_code[0]
        if prefix not in _PCS_GROUPS:
            continue
        region = r.get("region_libelle") or ""
        if region not in _TARGET_REGIONS:
            continue
        by_key[(prefix, region)].append(r)

    out: list[dict] = []
    for (prefix, region), records in by_key.items():
        group_label = _PCS_GROUPS[prefix]
        eff_total = sum(r.get("effectif_pondere") or 0 for r in records)
        median_an = _weighted_median(records, "salaire_net_median_annuel")
        median_mois = _weighted_median(records, "salaire_net_median_mensuel")
        # Tranche âge dominante (effectif max)
        ages_eff: dict[str, float] = defaultdict(float)
        for r in records:
            ages_eff[r.get("age_tr_libelle", "")] += r.get("effectif_pondere") or 0
        top_age = sorted(ages_eff.items(), key=lambda kv: -kv[1])[:1]
        age_dom = top_age[0][0] if top_age else ""

        parts = [
            f"Salaires {group_label} en {region} (2023)",
            f"Effectif pondéré régional : {int(eff_total):,}".replace(",", " "),
        ]
        if median_an:
            parts.append(f"Salaire net médian annuel : {int(median_an):,} €".replace(",", " "))
        if median_mois:
            parts.append(f"Salaire net médian mensuel : {int(median_mois):,} €".replace(",", " "))
        if age_dom:
            parts.append(f"Tranche d'âge dominante : {age_dom} ans")
        parts.append("Source : INSEE SALAAN 2023")

        out.append({
            "id": f"insee_salaan:group_{prefix}:{_slug(region)}",
            "domain": "insee_salaire",
            "source": "insee_salaan_2023",
            "pcs_group": prefix,
            "pcs_group_label": group_label,
            "region": region,
            "effectif_total": int(eff_total),
            "salaire_net_median_annuel": int(median_an) if median_an else None,
            "salaire_net_median_mensuel": int(median_mois) if median_mois else None,
            "tranche_age_dominante": age_dom,
            "text": " | ".join(parts),
        })
    return out


def build_corpus(data: list[dict] | None = None) -> list[dict]:
    if data is None:
        data = json.loads(SRC_PATH.read_text(encoding="utf-8"))
    out: list[dict] = []
    out.append(_aggregate_france_globale(data))
    out.extend(_aggregate_by_cs_libelle(data))
    out.extend(_aggregate_by_pcs_group_x_region(data))
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
    print(f"[INSEE-CORPUS] loading {SRC_PATH}…")
    corpus = build_corpus()
    out = save_corpus(corpus)
    avg_text = sum(len(c["text"]) for c in corpus) // max(1, len(corpus))
    print(f"[INSEE-CORPUS] {len(corpus)} cells → {out}")
    print(f"[INSEE-CORPUS] longueur texte moyenne : {avg_text} chars")


if __name__ == "__main__":  # pragma: no cover
    main()
