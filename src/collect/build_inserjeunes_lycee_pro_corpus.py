"""Inserjeunes lycée pro — corpus retrievable aggregé insertion bac pro.

Source : `data/processed/inserjeunes_lycee_pro.json` (132 124 records granulaires
ingérés par `src/collect/inserjeunes.py`, gitignored car 90 MB). Open data
Inserjeunes (DEPP / Ministère Éducation Nationale).

Licence : Etalab 2.0 (statistique publique).

## Dimension unique apportée à OrientIA

Inserjeunes lycée pro est l'**unique source d'insertion professionnelle pour
les sortants de bac pro / CAP / BP / Mentions Complémentaires** — segment
17-19 ans qui n'est pas couvert par InserSup (post-bac+2 général) ni Céreq
(génération nationale).

**Critique pour l'orientation** : un·e élève de 3ème qui choisit un CAP/Bac
pro a besoin de stats d'insertion par spécialité et par région. C'est
exactement le **gap data identifié dans le verdict Sprint 5 §4 P1**
(60% claims unsupported = sources insuffisantes).

## Stratégie aggregation (~2000 cells, Sprint 7 Action 4 amplification)

Re-aggregation des 132 124 records granulaires (1 par
établissement × formation × cohorte) en cells retrievable, 3 niveaux :

- 1 cell par **(libellé formation × type diplôme × France)** —
  vue nationale par spécialité (~600 cells, `granularity: "formation_france"`)
- 1 cell par **(région × type diplôme)** — vue régionale agrégée
  (~110 cells, `granularity: "region_diplome"`)
- **NEW Sprint 7** : 1 cell par **(libellé × type diplôme × région)** —
  granularité fine pour queries territoriales spécifiques
  (~1500 cells avec filter ≥`MIN_RECORDS_PER_TRIPLET=5` cohortes,
  `granularity: "formation_region_diplome"`)

Total cible ~2200 cells (vs verdict Sprint 5 P1.4 cible 1500-2000).
Sprint 6 axe 3b livrait 689 cells (granularités 1+2). Sprint 7 Action 4
amplifie via la granularité 3 — diagnostiquée comme axe star Sprint 6
(7.63pp attribution corrélationnelle).

Le filtre `>=MIN_RECORDS_PER_TRIPLET` couples (libellé×type×région) évite la
dilution top-K sur les couples très rares (<5 cohortes mesurées). Pour
les couples rares, la cell région_diplome (granularité 2) reste
disponible pour fournir un signal régional moins précis.

Le `domain` est `formation_insertion` pour permettre intent classifier
de cibler ces cells lors de queries insertion bac pro.

Pattern dual-output cohérent avec `build_dares_corpus.py` :
- Source raw : `data/processed/inserjeunes_lycee_pro.json` (input)
- Corpus aggregé : `data/processed/inserjeunes_lycee_pro_corpus.json` (output)
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


RAW_PATH = Path("data/processed/inserjeunes_lycee_pro.json")
CORPUS_PATH = Path("data/processed/inserjeunes_lycee_pro_corpus.json")

# Sprint 7 Action 4 — seuil minimum de cohortes par couple
# (libellé × type × région) pour l'agrégation granularité 3.
#
# Calibration : sur 132k records → 5 077 couples distincts.
# - min_records=5  : 4 079 cells (trop dilué top-K, risque masquer
#   formation_france Sprint 6 axe star)
# - min_records=10 : 2 701 cells (acceptable mais surdimensionné vs
#   target P1.4 verdict Sprint 5)
# - min_records=15 : **2 004 cells** (cible Sprint 5 P1.4 ≤2000 ✓)
# - min_records=20 : 1 621 cells (perd des couples moyennement peuplés)
#
# 15 = sweet spot statistique : représente ~5 ans × 3 lycées ou ~15 ans
# × 1 lycée minimum. Couples filtrés (<15) restent couverts par
# region_diplome (granularité 2) qui agrège tous les couples par région.
MIN_RECORDS_PER_TRIPLET: int = 15


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


def _avg(values: list[float]) -> float | None:
    """Moyenne simple, ignore None. Retourne None si liste vide."""
    valid = [v for v in values if v is not None]
    if not valid:
        return None
    return sum(valid) / len(valid)


def _get_taux_emploi(record: dict[str, Any], horizon: str) -> float | None:
    """Extrait taux_emploi[horizon] d'un record (dict ou None)."""
    te = record.get("taux_emploi")
    if not isinstance(te, dict):
        return None
    val = te.get(horizon)
    return val if isinstance(val, (int, float)) else None


def load_raw(path: Path | None = None) -> list[dict[str, Any]]:
    """Charge le JSON raw inserjeunes lycée pro."""
    target = path or RAW_PATH
    return json.loads(target.read_text(encoding="utf-8"))


def aggregate_by_formation(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """1 cell par (libellé_formation × type_diplome) — vue France."""
    by_key: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in records:
        libelle = (r.get("libelle_formation") or "").strip()
        diplome = (r.get("type_diplome") or "").strip()
        if not libelle or not diplome:
            continue
        by_key[(libelle, diplome)].append(r)

    out: list[dict[str, Any]] = []
    for (libelle, diplome), rows in sorted(by_key.items()):
        n_records = len(rows)
        regions_couvertes = sorted({r.get("region", "") for r in rows if r.get("region")})

        emploi_12m = _avg([_get_taux_emploi(r, "12m") for r in rows])
        emploi_24m = _avg([_get_taux_emploi(r, "24m") for r in rows])
        poursuite = _avg([
            r.get("taux_poursuite_etudes")
            for r in rows
            if isinstance(r.get("taux_poursuite_etudes"), (int, float))
        ])

        n_with_emploi = sum(
            1 for r in rows
            if _get_taux_emploi(r, "12m") is not None or _get_taux_emploi(r, "24m") is not None
        )

        parts = [
            f"Insertion {diplome} — {libelle} (France)",
            f"Établissements/cohortes mesurés : {n_records}",
        ]
        if emploi_12m is not None:
            parts.append(f"Taux d'emploi 12 mois après diplôme : {emploi_12m * 100:.1f}% (moyenne France)")
        if emploi_24m is not None:
            parts.append(f"Taux d'emploi 24 mois après diplôme : {emploi_24m * 100:.1f}%")
        if poursuite is not None:
            parts.append(f"Taux de poursuite d'études : {poursuite * 100:.1f}%")
        if n_with_emploi == 0:
            parts.append("Note : statistiques d'insertion non disponibles (cohortes récentes ou effectifs trop faibles)")
        if regions_couvertes:
            parts.append(f"Régions couvertes : {len(regions_couvertes)}/17")
        parts.append("Source : Inserjeunes (DEPP/Éducation Nationale), open data")

        out.append({
            "id": f"inserjeunes_formation:{_slug(diplome)}:{_slug(libelle)}",
            "domain": "formation_insertion",
            "source": "inserjeunes_lycee_pro",
            "granularity": "formation_france",
            "libelle_formation": libelle,
            "type_diplome": diplome,
            "n_records": n_records,
            "n_with_emploi_data": n_with_emploi,
            "taux_emploi_12m_moyen": round(emploi_12m, 4) if emploi_12m is not None else None,
            "taux_emploi_24m_moyen": round(emploi_24m, 4) if emploi_24m is not None else None,
            "taux_poursuite_etudes_moyen": round(poursuite, 4) if poursuite is not None else None,
            "n_regions_couvertes": len(regions_couvertes),
            "text": " | ".join(parts),
        })
    return out


def aggregate_by_region_diplome(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """1 cell par (région × type_diplome) — vue régionale agrégée."""
    by_key: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in records:
        region = (r.get("region") or "").strip()
        diplome = (r.get("type_diplome") or "").strip()
        if not region or not diplome:
            continue
        by_key[(region, diplome)].append(r)

    out: list[dict[str, Any]] = []
    for (region, diplome), rows in sorted(by_key.items()):
        n_records = len(rows)

        emploi_12m = _avg([_get_taux_emploi(r, "12m") for r in rows])
        emploi_24m = _avg([_get_taux_emploi(r, "24m") for r in rows])
        poursuite = _avg([
            r.get("taux_poursuite_etudes")
            for r in rows
            if isinstance(r.get("taux_poursuite_etudes"), (int, float))
        ])

        # Top 5 spécialités par effectif (n_records dans la région)
        formations_count: dict[str, int] = defaultdict(int)
        for r in rows:
            lib = (r.get("libelle_formation") or "").strip()
            if lib:
                formations_count[lib] += 1
        top5 = sorted(formations_count.items(), key=lambda x: -x[1])[:5]

        parts = [
            f"Insertion {diplome} — région {region}",
            f"Établissements/cohortes mesurés : {n_records}",
        ]
        if emploi_12m is not None:
            parts.append(f"Taux d'emploi 12 mois : {emploi_12m * 100:.1f}% (moyenne {region})")
        if emploi_24m is not None:
            parts.append(f"Taux d'emploi 24 mois : {emploi_24m * 100:.1f}%")
        if poursuite is not None:
            parts.append(f"Taux de poursuite d'études : {poursuite * 100:.1f}%")
        if top5:
            top5_str = ", ".join(f"{lib} ({n})" for lib, n in top5)
            parts.append(f"Top 5 spécialités {diplome} : {top5_str}")
        parts.append("Source : Inserjeunes (DEPP/Éducation Nationale), open data")

        out.append({
            "id": f"inserjeunes_region_diplome:{_slug(region)}:{_slug(diplome)}",
            "domain": "formation_insertion",
            "source": "inserjeunes_lycee_pro",
            "granularity": "region_diplome",
            "region": region,
            "type_diplome": diplome,
            "n_records": n_records,
            "taux_emploi_12m_moyen": round(emploi_12m, 4) if emploi_12m is not None else None,
            "taux_emploi_24m_moyen": round(emploi_24m, 4) if emploi_24m is not None else None,
            "taux_poursuite_etudes_moyen": round(poursuite, 4) if poursuite is not None else None,
            "top_5_specialites": [(lib, n) for lib, n in top5],
            "text": " | ".join(parts),
        })
    return out


def aggregate_by_formation_region_diplome(
    records: list[dict[str, Any]],
    min_records: int = MIN_RECORDS_PER_TRIPLET,
) -> list[dict[str, Any]]:
    """1 cell par (libellé × type_diplome × région) — granularité 3 fine.

    Sprint 7 Action 4 — amplification axe 3b star Sprint 6 (7.63pp
    attribution corrélationnelle). Filter `min_records` pour éviter
    la dilution top-K sur couples très rares (<5 cohortes).

    Pour les couples filtrés (rares), les cells `region_diplome`
    (granularité 2) restent disponibles pour fournir un signal
    régional moins précis mais toujours utilisable.
    """
    by_key: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for r in records:
        libelle = (r.get("libelle_formation") or "").strip()
        diplome = (r.get("type_diplome") or "").strip()
        region = (r.get("region") or "").strip()
        if not libelle or not diplome or not region:
            continue
        by_key[(libelle, diplome, region)].append(r)

    out: list[dict[str, Any]] = []
    for (libelle, diplome, region), rows in sorted(by_key.items()):
        n_records = len(rows)
        if n_records < min_records:
            continue  # filter dilution top-K

        emploi_12m = _avg([_get_taux_emploi(r, "12m") for r in rows])
        emploi_24m = _avg([_get_taux_emploi(r, "24m") for r in rows])
        poursuite = _avg([
            r.get("taux_poursuite_etudes")
            for r in rows
            if isinstance(r.get("taux_poursuite_etudes"), (int, float))
        ])

        n_with_emploi = sum(
            1 for r in rows
            if _get_taux_emploi(r, "12m") is not None or _get_taux_emploi(r, "24m") is not None
        )

        parts = [
            f"Insertion {diplome} — {libelle} en {region}",
            f"Établissements/cohortes mesurés : {n_records}",
        ]
        if emploi_12m is not None:
            parts.append(f"Taux d'emploi 12 mois : {emploi_12m * 100:.1f}% (en {region})")
        if emploi_24m is not None:
            parts.append(f"Taux d'emploi 24 mois : {emploi_24m * 100:.1f}%")
        if poursuite is not None:
            parts.append(f"Taux de poursuite d'études : {poursuite * 100:.1f}%")
        if n_with_emploi == 0:
            parts.append("Note : statistiques d'insertion non disponibles pour ce couple (cohortes récentes ou effectifs trop faibles)")
        parts.append("Source : Inserjeunes (DEPP/Éducation Nationale), open data")

        out.append({
            "id": f"inserjeunes_formation_region:{_slug(diplome)}:{_slug(libelle)}:{_slug(region)}",
            "domain": "formation_insertion",
            "source": "inserjeunes_lycee_pro",
            "granularity": "formation_region_diplome",
            "libelle_formation": libelle,
            "type_diplome": diplome,
            "region": region,
            "n_records": n_records,
            "n_with_emploi_data": n_with_emploi,
            "taux_emploi_12m_moyen": round(emploi_12m, 4) if emploi_12m is not None else None,
            "taux_emploi_24m_moyen": round(emploi_24m, 4) if emploi_24m is not None else None,
            "taux_poursuite_etudes_moyen": round(poursuite, 4) if poursuite is not None else None,
            "text": " | ".join(parts),
        })
    return out


def build_corpus(records: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    if records is None:
        records = load_raw()
    out: list[dict[str, Any]] = []
    out.extend(aggregate_by_formation(records))
    out.extend(aggregate_by_region_diplome(records))
    out.extend(aggregate_by_formation_region_diplome(records))
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
    print(f"[INSERJEUNES] loading {RAW_PATH}")
    raw = load_raw()
    print(f"[INSERJEUNES] {len(raw):,} records granulaires")

    corpus = build_corpus(raw)
    save_corpus(corpus)
    avg_text = sum(len(c["text"]) for c in corpus) // max(1, len(corpus))
    granularities: dict[str, int] = defaultdict(int)
    for c in corpus:
        granularities[c["granularity"]] += 1
    print(f"[INSERJEUNES] {len(corpus):,} cells aggregées → {CORPUS_PATH}")
    print(f"[INSERJEUNES] décomposition : {dict(granularities)}")
    print(f"[INSERJEUNES] longueur texte moyenne : {avg_text} chars")


if __name__ == "__main__":  # pragma: no cover
    main()
