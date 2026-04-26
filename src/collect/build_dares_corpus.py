"""DARES Métiers 2030 — corpus retrievable aggregé prospective recrutement.

Source : DARES "Les métiers en 2030 quelles perspectives de recrutement en
région - Les données.xlsx" (sheet "données", 1 080 records × 19 colonnes).

Licence : Etalab 2.0 (statistique publique).

## Dimension unique apportée à OrientIA

Les autres sources OrientIA (Céreq, InserSup, Inserjeunes, France Travail,
APEC, INSEE) sont **rétrospectives** (insertion / salaires passés). DARES
Métiers 2030 donne des **projections de recrutement** jusqu'en 2030 par
famille professionnelle (FAP 98 codes) × région métropolitaine.

**Critique pour l'orientation** : un·e lycéen·ne qui choisit une formation
en 2025 sort en 2028-2030. La question "quels métiers vont recruter
quand je sortirai" n'est adressable qu'avec cette source.

## Stratégie aggregation (~110 cells)

- 1 cell par **FAP × France** (98 cells, France entière aggregé sur les
  13 régions) — vue par métier
- 1 cell par **région × top FAP locaux** (13 cells) — vue régionale

Total ~110 cells (vs 1 080 raw → 10× réduction de dilution top-K).

Pattern dual-output (cohérent PR #57 parcours / PR #67 Phase B) :
- `data/processed/dares_metiers_2030.json` (raw 1 080 records granulaires)
- `data/processed/dares_corpus.json` (aggregé retrievable)
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


XLSX_PATH = Path(
    "data/raw/Les métiers en 2030 quelles perspectives de recrutement en région - Les données.xlsx"
)
RAW_PATH = Path("data/processed/dares_metiers_2030.json")
CORPUS_PATH = Path("data/processed/dares_corpus.json")


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


def _safe_float(val: Any) -> float | None:
    if val is None or val == "":
        return None
    try:
        f = float(val)
        if f != f:
            return None
        return f
    except (ValueError, TypeError):
        return None


def load_raw(path: Path | None = None) -> list[dict[str, Any]]:
    """Lit le sheet 'données' du XLSX DARES, retourne records granulaires."""
    target = path or XLSX_PATH
    import openpyxl

    wb = openpyxl.load_workbook(target, read_only=True, data_only=True)
    ws = wb["données"]

    records: list[dict[str, Any]] = []
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            continue
        if not row or not row[0]:
            continue
        records.append({
            "code_fap": str(row[0]).strip(),
            "fap_libelle": str(row[1]).strip() if row[1] else "",
            "region": str(row[2]).strip() if row[2] else "",
            "effectifs_2019_milliers": _safe_float(row[3]),
            "part_metier_region": _safe_float(row[4]),
            "indice_specificite": _safe_float(row[5]),
            "creations_destructions_milliers": _safe_float(row[6]),
            "creations_destructions_pct": _safe_float(row[7]),
            "departs_fin_carriere_milliers": _safe_float(row[8]),
            "departs_fin_carriere_pct": _safe_float(row[9]),
            "jeunes_debutants_milliers": _safe_float(row[10]),
            "jeunes_debutants_pct": _safe_float(row[11]),
            "solde_mobilites_inter_regions_milliers": _safe_float(row[12]),
            "solde_mobilites_inter_regions_pct": _safe_float(row[13]),
            "desequilibre_milliers": _safe_float(row[14]),
            "desequilibre_pct": _safe_float(row[15]),
            "postes_a_pourvoir_milliers": _safe_float(row[16]),
            "postes_a_pourvoir_pct": _safe_float(row[17]),
            "niveau_tension_2019": str(row[18]).strip() if row[18] else "",
        })
    return records


# ---------- Aggregation ----------


def aggregate_by_fap(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """1 cell par FAP — données nationales aggrégées sur les régions."""
    by_fap: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        if r["code_fap"]:
            by_fap[r["code_fap"]].append(r)

    out: list[dict[str, Any]] = []
    for code, rows in sorted(by_fap.items()):
        libelle = rows[0].get("fap_libelle") or ""
        # Sums sur effectifs + créations + départs + postes (en milliers)
        eff = sum(r.get("effectifs_2019_milliers") or 0 for r in rows)
        creations = sum(r.get("creations_destructions_milliers") or 0 for r in rows)
        departs = sum(r.get("departs_fin_carriere_milliers") or 0 for r in rows)
        postes = sum(r.get("postes_a_pourvoir_milliers") or 0 for r in rows)
        debutants = sum(r.get("jeunes_debutants_milliers") or 0 for r in rows)

        # Top 3 régions par effectif
        sorted_by_eff = sorted(
            [(r["region"], r.get("effectifs_2019_milliers") or 0) for r in rows],
            key=lambda x: -x[1],
        )
        top3_regions = [reg for reg, _ in sorted_by_eff[:3] if reg]

        # Niveau tension distribution
        tensions = [r.get("niveau_tension_2019") for r in rows if r.get("niveau_tension_2019")]
        tension_dom = max(set(tensions), key=tensions.count) if tensions else ""

        parts = [
            f"Métier 2030 (DARES) — FAP {code} : {libelle}",
            f"Effectifs 2019 France : {int(eff * 1000):,} personnes".replace(",", " "),
        ]
        if creations:
            sign = "+" if creations >= 0 else ""
            parts.append(
                f"Créations/destructions nettes 2019-2030 : {sign}{int(creations * 1000):,} postes".replace(",", " ")
            )
        if departs:
            parts.append(f"Départs en fin de carrière : {int(departs * 1000):,}".replace(",", " "))
        if postes:
            parts.append(
                f"Postes à pourvoir 2019-2030 : {int(postes * 1000):,} postes (national)".replace(",", " ")
            )
        if debutants:
            parts.append(f"Jeunes débutants attendus : {int(debutants * 1000):,}".replace(",", " "))
        if top3_regions:
            parts.append(f"Top 3 régions effectifs : {', '.join(top3_regions)}")
        if tension_dom and tension_dom != "hors champ":
            tension_label = {"1": "très faible", "2": "faible", "3": "moyen",
                             "4": "fort", "5": "très fort"}.get(tension_dom, tension_dom)
            parts.append(f"Niveau de tension dominant 2019 : {tension_label}")
        parts.append("Source : DARES Métiers en 2030, projections par région")

        out.append({
            "id": f"dares_fap:{code}",
            "domain": "metier_prospective",
            "source": "dares_metiers_2030",
            "code_fap": code,
            "fap_libelle": libelle,
            "effectifs_2019_total_milliers": round(eff, 1),
            "creations_destructions_total_milliers": round(creations, 1),
            "departs_fin_carriere_total_milliers": round(departs, 1),
            "postes_a_pourvoir_total_milliers": round(postes, 1),
            "jeunes_debutants_total_milliers": round(debutants, 1),
            "top_3_regions_effectifs": top3_regions,
            "niveau_tension_dominant": tension_dom,
            "n_regions_couvertes": len(rows),
            "text": " | ".join(parts),
        })
    return out


def aggregate_by_region(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """1 cell par région — top FAP par effectif + tension globale."""
    by_region: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        if r["region"] and r["region"] != "":
            by_region[r["region"]].append(r)

    out: list[dict[str, Any]] = []
    for region, rows in sorted(by_region.items()):
        eff_total = sum(r.get("effectifs_2019_milliers") or 0 for r in rows)
        postes_total = sum(r.get("postes_a_pourvoir_milliers") or 0 for r in rows)
        creations_total = sum(r.get("creations_destructions_milliers") or 0 for r in rows)

        # Top 5 FAPs par postes à pourvoir
        sorted_by_postes = sorted(
            rows,
            key=lambda x: -(x.get("postes_a_pourvoir_milliers") or 0),
        )
        top5_postes = [
            (r["fap_libelle"], r.get("postes_a_pourvoir_milliers") or 0)
            for r in sorted_by_postes[:5]
        ]

        # Top 5 FAPs spécifiques (indice spécificité haut = sur-représenté région)
        sorted_by_spec = sorted(
            [r for r in rows if r.get("indice_specificite") is not None],
            key=lambda x: -x.get("indice_specificite", 0),
        )
        top5_spec = [
            (r["fap_libelle"], r.get("indice_specificite") or 0)
            for r in sorted_by_spec[:5]
        ]

        parts = [
            f"Marché du travail prospective 2030 — région {region}",
            f"Effectifs 2019 totaux : {int(eff_total * 1000):,} personnes (toutes FAPs)".replace(",", " "),
            f"Postes à pourvoir 2019-2030 : {int(postes_total * 1000):,} postes".replace(",", " "),
        ]
        if creations_total != 0:
            sign = "+" if creations_total >= 0 else ""
            parts.append(
                f"Créations nettes : {sign}{int(creations_total * 1000):,} postes".replace(",", " ")
            )
        if top5_postes:
            top5_str = ", ".join(
                f"{fap} ({int(p * 1000):,})".replace(",", " ")
                for fap, p in top5_postes if fap
            )
            parts.append(f"Top 5 FAPs postes à pourvoir : {top5_str}")
        if top5_spec:
            spec_str = ", ".join(
                f"{fap} (×{spec:.2f})"
                for fap, spec in top5_spec if fap
            )
            parts.append(f"Top 5 FAPs sur-représentés région (vs reste France) : {spec_str}")
        parts.append("Source : DARES Métiers en 2030 par région")

        out.append({
            "id": f"dares_region:{_slug(region)}",
            "domain": "metier_prospective",
            "source": "dares_metiers_2030",
            "region": region,
            "effectifs_2019_total_milliers": round(eff_total, 1),
            "postes_a_pourvoir_total_milliers": round(postes_total, 1),
            "creations_destructions_total_milliers": round(creations_total, 1),
            "top_5_postes_a_pourvoir": [(f, round(p, 1)) for f, p in top5_postes],
            "top_5_specificite": [(f, round(s, 2)) for f, s in top5_spec],
            "n_faps_couvertes": len(rows),
            "text": " | ".join(parts),
        })
    return out


def build_corpus(records: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    if records is None:
        records = load_raw()
    out: list[dict[str, Any]] = []
    out.extend(aggregate_by_fap(records))
    out.extend(aggregate_by_region(records))
    return out


def save_raw(records: list[dict[str, Any]], path: Path | None = None) -> Path:
    target = path or RAW_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target


def save_corpus(records: list[dict[str, Any]], path: Path | None = None) -> Path:
    target = path or CORPUS_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target


def main() -> None:  # pragma: no cover
    print(f"[DARES] loading {XLSX_PATH}")
    raw = load_raw()
    print(f"[DARES] {len(raw)} records granulaires")
    save_raw(raw)
    print(f"[DARES] raw → {RAW_PATH}")

    corpus = build_corpus(raw)
    save_corpus(corpus)
    avg_text = sum(len(c["text"]) for c in corpus) // max(1, len(corpus))
    print(f"[DARES] {len(corpus)} cells aggregées (FAP + région) → {CORPUS_PATH}")
    print(f"[DARES] longueur texte moyenne : {avg_text} chars")


if __name__ == "__main__":  # pragma: no cover
    main()
