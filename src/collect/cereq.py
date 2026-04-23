"""Céreq Enquêtes Génération — insertion professionnelle jeunes diplômés (D11 Axe 1).

Source : https://www.cereq.fr/datavisualisation/insertion-professionnelle-des-jeunes/
Licence : statistique publique / Etalab 2.0 (données agrégées publiques).
Scope élargi ADR-039 : phase (c) insertion pro 17-25 ans.

**Particularité ingestion** : Céreq ne publie pas d'API bulk-download standardisée
pour les données agrégées insertion. Le portail `datavisualisation` affiche les
chiffres en dashboards, et les exports CSV/Excel sont accessibles via des boutons
"Télécharger" mais les URLs de ces exports sont générées côté client et changent
entre enquêtes.

Stratégie OrientIA :
1. Matteo télécharge manuellement les 2-3 CSVs clés via le portail Céreq
   (procédure dans `docs/TODO_MATTEO_APIS.md` §4).
2. Claudette lit ces CSVs depuis `data/raw/cereq/` et normalise vers le schéma
   OrientIA (`phase=master/initial` + `taux_insertion_*` + `salaire_median`).
3. Enrichissement des fiches OrientIA par niveau+domaine (pas par RNCP direct —
   Céreq agrégé ne descend pas à la granularité formation).

Alternative future : bascule vers l'enquête `Génération 2021` (publication fin
2024 / début 2025) dès que les CSVs sont publics.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Optional


RAW_DIR = Path("data/raw/cereq")
PROCESSED_PATH = Path("data/processed/cereq_insertion_stats.json")


class CereqDataMissing(Exception):
    """Les CSVs Céreq attendus ne sont pas présents dans `data/raw/cereq/`.

    Pointe vers `docs/TODO_MATTEO_APIS.md` pour la procédure de download
    manuel depuis le portail Céreq.
    """


# --- Schéma attendu après normalisation ---
#
# Chaque entrée = 1 combinaison (niveau, domaine, cohorte) avec :
# - niveau : "bac+2" / "bac+3" / "bac+5" / ...  (aligné OrientIA)
# - domaine : label Céreq traduit en domaine OrientIA
# - cohorte : "Generation 2017" / "Generation 2021" / ...
# - taux_emploi_3ans, taux_emploi_6ans : float 0-1
# - taux_cdi : float 0-1
# - salaire_median_embauche : int (EUR mensuel brut)
# - delai_premier_emploi_mois : int (médiane)
# - source_url : str (lien Céreq)


def _infer_niveau(cereq_label: str) -> Optional[str]:
    """Mapping label Céreq → niveau OrientIA.

    Céreq groupe typiquement par : "Bac+5", "Bac+3", "Bac+2 et moins", etc.
    """
    if not cereq_label:
        return None
    l = cereq_label.lower().strip()
    if "bac+5" in l or "bac +5" in l or "master" in l:
        return "bac+5"
    if "bac+3" in l or "bac +3" in l or "licence" in l:
        return "bac+3"
    if "bac+2" in l or "bac +2" in l or "bts" in l or "but" in l:
        return "bac+2"
    if "cap" in l or "bep" in l:
        return "cap-bep"
    if "bac" in l and "+" not in l:
        return "bac"
    return None


def parse_chiffres_cles_csv(csv_path: Path) -> list[dict[str, Any]]:
    """Parse un CSV Céreq type 'Chiffres clés par diplôme'.

    Le schéma exact dépend du CSV téléchargé. Cette fonction est
    volontairement **permissive** : elle mappe ce qu'elle peut
    reconnaître et retourne les champs inconnus tels quels sous `_extra`.
    """
    if not csv_path.exists():
        raise CereqDataMissing(
            f"CSV Céreq absent : {csv_path}. "
            "Cf docs/TODO_MATTEO_APIS.md §4 pour la procédure download manuel."
        )
    with open(csv_path, encoding="utf-8") as f:
        # Céreq publie parfois en ; (FR), parfois en , (EN). On sniff.
        sample = f.read(2048)
        f.seek(0)
        delimiter = ";" if sample.count(";") > sample.count(",") else ","
        reader = csv.DictReader(f, delimiter=delimiter)
        rows = list(reader)

    out: list[dict[str, Any]] = []
    for row in rows:
        niveau_label = row.get("niveau_diplome") or row.get("Niveau") or row.get("Diplôme")
        domaine = row.get("domaine") or row.get("Domaine") or row.get("Spécialité")
        entry = {
            "source": "cereq",
            "cohorte": row.get("cohorte") or row.get("Génération") or "Generation 2017",
            "niveau": _infer_niveau(niveau_label or ""),
            "niveau_label": niveau_label,
            "domaine": domaine,
            "taux_emploi_3ans": _safe_float(row.get("taux_emploi_3_ans") or row.get("Taux emploi 3 ans")),
            "taux_emploi_6ans": _safe_float(row.get("taux_emploi_6_ans") or row.get("Taux emploi 6 ans")),
            "taux_cdi": _safe_float(row.get("taux_cdi") or row.get("% CDI")),
            "salaire_median_embauche": _safe_int(row.get("salaire_median") or row.get("Salaire médian")),
            "delai_premier_emploi_mois": _safe_int(row.get("delai_emploi_mois") or row.get("Délai accès premier emploi")),
            "_extra": {k: v for k, v in row.items() if k not in {
                "niveau_diplome", "Niveau", "Diplôme", "domaine", "Domaine",
                "Spécialité", "cohorte", "Génération", "taux_emploi_3_ans",
                "Taux emploi 3 ans", "taux_emploi_6_ans", "Taux emploi 6 ans",
                "taux_cdi", "% CDI", "salaire_median", "Salaire médian",
                "delai_emploi_mois", "Délai accès premier emploi",
            }},
        }
        out.append(entry)
    return out


def _safe_float(val: Any) -> Optional[float]:
    if val is None or val == "":
        return None
    try:
        return float(str(val).replace(",", ".").replace("%", "").strip())
    except (ValueError, TypeError):
        return None


def _safe_int(val: Any) -> Optional[int]:
    if val is None or val == "":
        return None
    try:
        return int(float(str(val).replace(",", ".").replace("€", "").strip()))
    except (ValueError, TypeError):
        return None


def save_processed(
    entries: list[dict[str, Any]], path: Path = PROCESSED_PATH
) -> Path:
    """Dump les stats insertion normalisées (commité)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return path


def collect_cereq_stats(
    raw_dir: Path = RAW_DIR, save: bool = True
) -> list[dict[str, Any]]:
    """Parse tous les CSVs Céreq présents dans `data/raw/cereq/`.

    Pattern : `cereq_<nom>_<cohorte>.csv` (ex: `cereq_chiffres_cles_gen2017.csv`).
    Si aucun CSV présent → exception avec pointeur vers TODO.
    """
    csvs = sorted(raw_dir.glob("*.csv"))
    if not csvs:
        raise CereqDataMissing(
            f"Aucun CSV dans {raw_dir}. "
            "Cf docs/TODO_MATTEO_APIS.md §4 pour la procédure download manuel."
        )
    all_entries: list[dict[str, Any]] = []
    for p in csvs:
        all_entries.extend(parse_chiffres_cles_csv(p))
    if save:
        path = save_processed(all_entries)
        print(f"  [cereq] {len(all_entries)} entrées stats insertion → {path}")
    return all_entries


if __name__ == "__main__":
    try:
        entries = collect_cereq_stats()
        print(f"  [cereq] total entries : {len(entries)}")
    except CereqDataMissing as e:
        print(f"  [cereq] ⚠️  {e}")
        print("  [cereq] Procédure : télécharger manuellement depuis")
        print("  [cereq]   https://www.cereq.fr/datavisualisation/")
        print(f"  [cereq]   vers {RAW_DIR}/")
