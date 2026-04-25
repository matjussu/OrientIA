"""Parcours bacheliers en licence — MESRI / data.gouv.fr.

Source : `datagouv_mesre_parcours_bacheliers_licence.csv` (5 508 lignes,
licence Etalab 2.0). Cohortes :
- **L1→L2** : néobacheliers 2014 suivis sur 2 ans (passage L2, redoublement
  L1, réorientation DUT 1 an / 2 ans / 1 ou 2 ans)
- **Licence** : néobacheliers 2012 suivis sur 3-4 ans (obtention licence
  3 ans / 4 ans / 3 ou 4 ans)

Dimensions : Grande discipline (5) × Discipline × Secteur disciplinaire ×
Série Bac (6) × Âge au bac × Sexe × Mention au Bac (6).

## Stratégie OrientIA

5 508 records granulaires sont trop fragmentés pour être directement
retrievables — un bachelier veut "j'ai un BAC ES mention Bien, quel est
mon taux de réussite en licence d'éco ?", pas un croisement âge × sexe.

On produit donc **deux sorties** :
1. `parcours_bacheliers_licence.json` — tous les records granulaires
   (audit + downstream stats)
2. `parcours_bacheliers_corpus.json` — agrégation à
   Grande discipline × Série Bac × Mention au Bac, avec sommes pondérées
   d'effectifs et taux recalculés. Format retrievable (multi-corpus
   pattern, cf metiers_corpus).

ADR-04X RAG multi-corpus : ce dataset s'expose en parallèle de
formations.json + metiers_corpus.json + (futur) apec_regions_corpus.json.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable


RAW_PATH = Path("data/raw/data-gouv/datagouv_mesre_parcours_bacheliers_licence.csv")
PROCESSED_GRANULAR = Path("data/processed/parcours_bacheliers_licence.json")
PROCESSED_CORPUS = Path("data/processed/parcours_bacheliers_corpus.json")


# Ordre des colonnes du CSV (positions stables). On parse par index pour
# gérer la duplication "Effectif de néobacheliers de la cohorte" (col 15
# pour cohorte L1, col 24 pour cohorte Licence).
COL_GRANDE_DISCIPLINE = 1
COL_DISCIPLINE = 3
COL_SECTEUR = 5
COL_BAC = 7
COL_AGE = 9
COL_SEXE = 11
COL_MENTION = 13
COL_COHORTE_L1 = 14
COL_EFFECTIF_L1 = 15
COL_PASSAGE_L2_1AN = 16
COL_REDOUBLEMENT_L1 = 17
COL_PASSAGE_L2_2ANS = 18
COL_PASSAGE_L2_1OU2 = 19
COL_REORIENTATION_DUT_1AN = 20
COL_REORIENTATION_DUT_2ANS = 21
COL_REORIENTATION_DUT_1OU2 = 22
COL_COHORTE_LICENCE = 23
COL_EFFECTIF_LICENCE = 24
COL_OBTENTION_3ANS = 25
COL_OBTENTION_4ANS = 26
COL_OBTENTION_3OU4 = 27


def _to_float(s: str) -> float | None:
    """Parse une cellule CSV float, retourne None si vide ou non-numérique."""
    if not s:
        return None
    s = s.strip().replace(",", ".")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_row(row: list[str]) -> dict[str, Any]:
    """Parse une ligne CSV en record normalisé (granulaire)."""
    return {
        "grande_discipline": row[COL_GRANDE_DISCIPLINE].strip(),
        "discipline": row[COL_DISCIPLINE].strip(),
        "secteur_disciplinaire": row[COL_SECTEUR].strip(),
        "bac": row[COL_BAC].strip(),
        "age_au_bac": row[COL_AGE].strip(),
        "sexe": row[COL_SEXE].strip(),
        "mention": row[COL_MENTION].strip(),
        "cohorte_l1_l2": _to_int(row[COL_COHORTE_L1]),
        "effectif_l1": _to_float(row[COL_EFFECTIF_L1]),
        "passage_l2_1an": _to_float(row[COL_PASSAGE_L2_1AN]),
        "redoublement_l1": _to_float(row[COL_REDOUBLEMENT_L1]),
        "passage_l2_2ans": _to_float(row[COL_PASSAGE_L2_2ANS]),
        "passage_l2_1ou2ans": _to_float(row[COL_PASSAGE_L2_1OU2]),
        "reorientation_dut_1an": _to_float(row[COL_REORIENTATION_DUT_1AN]),
        "reorientation_dut_2ans": _to_float(row[COL_REORIENTATION_DUT_2ANS]),
        "reorientation_dut_1ou2ans": _to_float(row[COL_REORIENTATION_DUT_1OU2]),
        "cohorte_licence": _to_int(row[COL_COHORTE_LICENCE]),
        "effectif_licence": _to_float(row[COL_EFFECTIF_LICENCE]),
        "obtention_3ans": _to_float(row[COL_OBTENTION_3ANS]),
        "obtention_4ans": _to_float(row[COL_OBTENTION_4ANS]),
        "obtention_3ou4ans": _to_float(row[COL_OBTENTION_3OU4]),
    }


def _to_int(s: str) -> int | None:
    v = _to_float(s)
    return int(v) if v is not None else None


def load_raw(path: Path | None = None) -> list[dict[str, Any]]:
    target = path or RAW_PATH
    records: list[dict[str, Any]] = []
    with open(target, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f, delimiter=";")
        next(reader)  # header
        for row in reader:
            if len(row) < 28:
                continue
            records.append(parse_row(row))
    return records


def save_granular(records: list[dict[str, Any]], path: Path | None = None) -> Path:
    target = path or PROCESSED_GRANULAR
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target


# ----- Agrégation Grande discipline × Bac × Mention -----


_AGGREGATE_KEYS = ("grande_discipline", "bac", "mention")
_SUM_FIELDS_L1 = (
    "effectif_l1",
    "passage_l2_1an",
    "redoublement_l1",
    "passage_l2_2ans",
    "passage_l2_1ou2ans",
    "reorientation_dut_1an",
    "reorientation_dut_2ans",
    "reorientation_dut_1ou2ans",
)
_SUM_FIELDS_LIC = (
    "effectif_licence",
    "obtention_3ans",
    "obtention_4ans",
    "obtention_3ou4ans",
)


def _aggregate_key(record: dict[str, Any]) -> tuple[str, str, str]:
    return (record[_AGGREGATE_KEYS[0]], record[_AGGREGATE_KEYS[1]], record[_AGGREGATE_KEYS[2]])


def aggregate_records(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Agrège les records granulaires par (grande_discipline, bac, mention).

    Sommes des effectifs et des passages, recalcule les taux moyens pondérés.
    Conserve la cohorte (assumée cohérente sur l'ensemble du dataset).
    """
    buckets: dict[tuple[str, str, str], dict[str, Any]] = {}
    for r in records:
        key = _aggregate_key(r)
        bucket = buckets.setdefault(
            key,
            {
                "grande_discipline": key[0],
                "bac": key[1],
                "mention": key[2],
                "n_rows": 0,
                "cohorte_l1_l2": r.get("cohorte_l1_l2"),
                "cohorte_licence": r.get("cohorte_licence"),
                **{f: 0.0 for f in _SUM_FIELDS_L1},
                **{f: 0.0 for f in _SUM_FIELDS_LIC},
            },
        )
        bucket["n_rows"] += 1
        for field in _SUM_FIELDS_L1 + _SUM_FIELDS_LIC:
            v = r.get(field)
            if v is not None:
                bucket[field] += v

    out: list[dict[str, Any]] = []
    for bucket in buckets.values():
        bucket["taux"] = compute_rates(bucket)
        out.append(bucket)
    out.sort(key=lambda b: (b["grande_discipline"], b["bac"], b["mention"]))
    return out


def compute_rates(record: dict[str, Any]) -> dict[str, float]:
    """Calcule les taux principaux à partir des effectifs absolus.

    Renvoie un dict de pourcentages arrondis à 1 décimale. Effectifs nuls →
    pas de taux (skip).
    """
    rates: dict[str, float] = {}
    eff_l1 = record.get("effectif_l1") or 0
    eff_lic = record.get("effectif_licence") or 0

    if eff_l1 > 0:
        for field, label in (
            ("passage_l2_1an", "passage_l2_1an"),
            ("passage_l2_1ou2ans", "passage_l2_1ou2ans"),
            ("redoublement_l1", "redoublement_l1"),
            ("reorientation_dut_1ou2ans", "reorientation_dut_1ou2ans"),
        ):
            v = record.get(field)
            if v is not None:
                rates[f"{label}_pct"] = round(100 * v / eff_l1, 1)

    if eff_lic > 0:
        for field, label in (
            ("obtention_3ans", "obtention_3ans"),
            ("obtention_3ou4ans", "obtention_3ou4ans"),
        ):
            v = record.get(field)
            if v is not None:
                rates[f"{label}_pct"] = round(100 * v / eff_lic, 1)

    return rates


# ----- Corpus retrievable -----


def build_text(aggregated: dict[str, Any]) -> str:
    """Texte retrievable pour une cellule (grande_discipline × bac × mention)."""
    parts = [
        f"Parcours licence en {aggregated['grande_discipline']}",
        f"Bachelier : {aggregated['bac']}",
        f"Mention au bac : {aggregated['mention']}",
    ]
    taux = aggregated.get("taux") or {}
    eff_l1 = aggregated.get("effectif_l1") or 0
    if eff_l1 > 0 and aggregated.get("cohorte_l1_l2"):
        cohorte = aggregated["cohorte_l1_l2"]
        passage = taux.get("passage_l2_1an_pct")
        passage_total = taux.get("passage_l2_1ou2ans_pct")
        redoub = taux.get("redoublement_l1_pct")
        reor = taux.get("reorientation_dut_1ou2ans_pct")
        sub = [f"Cohorte {cohorte} (L1→L2) : {int(eff_l1):,} néobacheliers".replace(",", " ")]
        if passage is not None:
            sub.append(f"{passage:.1f}% passent en L2 en 1 an")
        if passage_total is not None:
            sub.append(f"{passage_total:.1f}% en L2 en 1 ou 2 ans")
        if redoub is not None:
            sub.append(f"{redoub:.1f}% redoublent L1")
        if reor is not None:
            sub.append(f"{reor:.1f}% se réorientent en DUT")
        parts.append(" ; ".join(sub))

    eff_lic = aggregated.get("effectif_licence") or 0
    if eff_lic > 0 and aggregated.get("cohorte_licence"):
        cohorte = aggregated["cohorte_licence"]
        sub = [f"Cohorte {cohorte} (suivi licence) : {int(eff_lic):,} néobacheliers".replace(",", " ")]
        l3 = taux.get("obtention_3ans_pct")
        l34 = taux.get("obtention_3ou4ans_pct")
        if l3 is not None:
            sub.append(f"{l3:.1f}% obtiennent la licence en 3 ans")
        if l34 is not None:
            sub.append(f"{l34:.1f}% en 3 ou 4 ans")
        parts.append(" ; ".join(sub))

    return " | ".join(parts)


def normalize_to_corpus(aggregated: dict[str, Any]) -> dict[str, Any]:
    """Convertit un agrégat en record corpus retrievable."""
    grande = aggregated["grande_discipline"]
    bac = aggregated["bac"]
    mention = aggregated["mention"]
    slug = f"{grande}|{bac}|{mention}".lower().replace(" ", "_").replace(",", "")
    return {
        "id": f"parcours:{slug}",
        "domain": "parcours_bacheliers",
        "source": "mesri_parcours_bacheliers_licence",
        "grande_discipline": grande,
        "bac": bac,
        "mention": mention,
        "cohorte_l1_l2": aggregated.get("cohorte_l1_l2"),
        "cohorte_licence": aggregated.get("cohorte_licence"),
        "effectif_l1": aggregated.get("effectif_l1"),
        "effectif_licence": aggregated.get("effectif_licence"),
        "taux": aggregated.get("taux") or {},
        "n_rows_agreges": aggregated.get("n_rows", 0),
        "text": build_text(aggregated),
    }


def build_corpus(aggregated_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_to_corpus(a) for a in aggregated_records]


def save_corpus(records: list[dict[str, Any]], path: Path | None = None) -> Path:
    target = path or PROCESSED_CORPUS
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target


def main() -> None:  # pragma: no cover
    print(f"[PARCOURS] loading {RAW_PATH}")
    granular = load_raw()
    print(f"[PARCOURS] {len(granular)} rows granulaires")
    save_granular(granular)
    print(f"[PARCOURS] granular → {PROCESSED_GRANULAR}")

    aggregated = aggregate_records(granular)
    corpus = build_corpus(aggregated)
    save_corpus(corpus)
    print(f"[PARCOURS] {len(corpus)} cellules agrégées (Grande discipline × Bac × Mention)")
    print(f"[PARCOURS] corpus → {PROCESSED_CORPUS}")


if __name__ == "__main__":  # pragma: no cover
    main()
