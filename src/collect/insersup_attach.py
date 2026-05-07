"""InserSup attach v2 — matching cascade Phase A.3 du plan corpus v5.

Remplace `attach_cereq_insertion` (ADR-054 — Cereq agrégats par niveau supprimés)
par un attachement de chiffres InserSup MESR, plus granulaires.

## Cascade de matching (3 niveaux décroissants)

Pour chaque fiche du corpus principal, on tente le matching dans cet ordre :

| Niveau | Clé matching                                                    | Granularité output       | Score |
|--------|-----------------------------------------------------------------|--------------------------|-------|
| 1 (best) | `(uai_etablissement × type_diplome_normalisé × discipline)`   | etablissement_x_discipline | 1.0 |
| 2        | `(type_diplome_normalisé × discipline × region)`              | discipline_region          | 0.7 |
| 3 (last) | `(type_diplome_normalisé × discipline)` national agrégé       | discipline_nationale       | 0.4 |
| —        | aucun match                                                   | None (insertion_pro absent) | —   |

Conformément à ADR-054, **pas de fallback Cereq** — si pas de match,
`fiche["insertion_pro"]` reste absent / null. Le contrat strict v4 R1 force
alors le LLM à écrire "information non disponible".

## Sources data

- `data/processed/insersup_insertion.json` (48 230 records bruts,
  granularité `établissement × type_diplome × discipline × région × cohorte`)
  → utilisé pour le niveau 1 (UAI exact).
- `data/processed/insersup_corpus.json` (368 entrées agrégées,
  granularité `type_diplome × discipline × région`) → utilisé pour
  les niveaux 2 et 3.

## Robustesse statistique

Critère `min_sortants` : on n'attache que si la cohorte InserSup matchée
a au moins N sortants (défaut 30). Sinon snapshot bruité, on tente le
niveau suivant.

## Schema enrichi `fiche["insertion_pro"]` après attach

```json
{
  "source": "insersup_mesr",
  "granularite": "etablissement_x_discipline",
  "match_score": 1.0,
  "cohorte": "2020",
  "nombre_sortants": 461,
  "taux_emploi_6m": 0.38,
  "taux_emploi_12m": 0.58,
  "taux_emploi_18m": 0.58,
  "taux_emploi_24m": 0.64,
  "taux_emploi_30m": 0.61,
  "url_source": "https://www.data.gouv.fr/datasets/insertion-..."
}
```

Le module ne modifie pas la `FactCard` directement — le merger v3 (Phase B.1)
adaptera `fiche_to_fact_card` pour exposer `granularite` et `nombre_sortants`
via les nouveaux champs `FactChiffres.insertion_pro_granularite` et
`FactChiffres.nombre_sortants` (déjà ajoutés en Phase A.1).
"""
from __future__ import annotations

import json
import logging
import unicodedata
from pathlib import Path
from typing import Any

_logger = logging.getLogger(__name__)


INSERSUP_RECORDS_PATH = Path("data/processed/insersup_insertion.json")
INSERSUP_CORPUS_PATH = Path("data/processed/insersup_corpus.json")
INSERSUP_DATASET_URL = (
    "https://www.data.gouv.fr/datasets/insertion-professionnelle-des-diplomes-"
    "des-etablissements-denseignement-superieur-dispositif-insersup"
)

# ─────────────── Mapping type_diplome ────────────────
#
# Mappe le champ `type_diplome` de la fiche source (MonMaster, Parcoursup,
# ONISEP, etc.) vers le libellé InserSup canonique. Les libellés InserSup
# proviennent du dataset MESR (cf `data/processed/insersup_corpus.json`).

PARCOURSUP_TO_INSERSUP_TYPE: dict[str, str] = {
    # Masters
    "Master LMD": "Master LMD",
    "Master": "Master LMD",
    "Master MEEF": "Master MEEF",
    # Licences
    "Licence professionnelle": "Licence professionnelle",
    "Licence pro": "Licence professionnelle",
    "Licence générale": "Licence générale",
    "Licence": "Licence générale",
    "Licence LMD": "Licence générale",
    # BUT
    "BUT": "Bachelor universitaire de technologie",
    "Bachelor universitaire de technologie": "Bachelor universitaire de technologie",
    "Bachelor Universitaire de Technologie": "Bachelor universitaire de technologie",
    # Ingénieurs
    "Diplôme d'ingénieur": "Diplôme d'ingénieurs",
    "Diplôme d'ingénieurs": "Diplôme d'ingénieurs",
    "formation d'école spécialisée": "Diplôme d'ingénieurs",  # approximation pour les écoles d'ingé
    # Diplômes visés (écoles spécialisées labellisées)
    "Bachelor": "Diplôme visé niveau bac+3 grade Licence",
    "Diplôme visé bac+5": "Diplôme visé niveau bac+5 grade Master",
    "Diplôme visé bac+3": "Diplôme visé niveau bac+3 grade Licence",
    # Management (BSB, ICN, etc.)
    "Diplôme grade Master management": "Diplôme gradé ou visé management niveau bac+5",
}

# Fallback depuis `niveau` quand `type_diplome` absent ou inconnu.
NIVEAU_TO_DEFAULT_TYPE: dict[str, str] = {
    "bac+5": "Master LMD",
    "bac+3": "Licence générale",
    # bac+2 : InserSup ne couvre que les BUT (3 ans, niveau bac+3 LMD désormais).
    # Les BTS ne sont pas dans InserSup. → no fallback.
}


# ─────────────── Helpers ────────────────


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s)
        if not unicodedata.combining(c)
    )


def _norm_key(s: Any) -> str:
    """Normalisation pour les clés de matching : lowercase, strip accents/whitespace.

    Les libellés InserSup et MonMaster ont parfois des variations de casse,
    accents (Île-de-France vs Ile-de-France), ou whitespace. Cette
    normalisation rend le matching robuste sans introduire de fuzzy.
    """
    raw = _safe_str(s)
    if not raw:
        return ""
    return _strip_accents(raw).lower().strip()


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
        if f != f or f == float("inf") or f == float("-inf"):
            return None
        return f
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        # Tolère les floats (e.g. 461.0)
        return int(float(value))
    except (TypeError, ValueError):
        return None


# ─────────────── Construction des index inversés ────────────────


def _build_etab_index(
    records: list[dict[str, Any]],
) -> dict[tuple[str, str, str], list[dict[str, Any]]]:
    """Index niveau 1 — clé `(uai_normalisé, type_diplome_normalisé, discipline_normalisée)`.

    Note : les records `insersup_insertion.json` ont `etablissement` (nom) mais
    pas systématiquement de champ `uai` direct. On tente d'utiliser `uai` si
    présent, sinon on fallback sur `_norm_key(etablissement)`.
    """
    idx: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for r in records:
        if not isinstance(r, dict):
            continue
        # Clé établissement : UAI prioritaire, fallback nom normalisé
        uai_raw = r.get("uai") or r.get("code_uai") or r.get("etablissement")
        uai = _norm_key(uai_raw)
        type_dip = _norm_key(r.get("type_diplome"))
        discipline = _norm_key(r.get("discipline"))
        if not uai or not type_dip or not discipline:
            continue
        idx.setdefault((uai, type_dip, discipline), []).append(r)
    return idx


def _build_region_index(
    corpus: list[dict[str, Any]],
) -> dict[tuple[str, str, str], dict[str, Any]]:
    """Index niveau 2 — clé `(type_diplome_normalisé, discipline_normalisée, region_normalisée)`.

    Les entrées de `insersup_corpus.json` avec `region != null` ont déjà
    le bon grain (1 entrée par triplet).
    """
    idx: dict[tuple[str, str, str], dict[str, Any]] = {}
    for r in corpus:
        if not isinstance(r, dict):
            continue
        region = _safe_str(r.get("region"))
        if not region:
            continue
        type_dip = _norm_key(r.get("type_diplome"))
        discipline = _norm_key(r.get("discipline"))
        region_norm = _norm_key(region)
        if not type_dip or not discipline or not region_norm:
            continue
        idx[(type_dip, discipline, region_norm)] = r
    return idx


def _build_national_index(
    corpus: list[dict[str, Any]],
) -> dict[tuple[str, str], dict[str, Any]]:
    """Index niveau 3 — clé `(type_diplome_normalisé, discipline_normalisée)`.

    Les entrées InserSup national agrégé ont `region` null. Si plusieurs
    entrées matchent (ne devrait pas arriver avec `insersup_corpus.json` mais
    on est défensif), on garde celle avec le plus de sortants.
    """
    idx: dict[tuple[str, str], dict[str, Any]] = {}
    for r in corpus:
        if not isinstance(r, dict):
            continue
        region = _safe_str(r.get("region"))
        if region:
            continue  # entrée régionale, pas pour cet index
        type_dip = _norm_key(r.get("type_diplome"))
        discipline = _norm_key(r.get("discipline"))
        if not type_dip or not discipline:
            continue
        existing = idx.get((type_dip, discipline))
        nb_sortants_new = _safe_int(r.get("nb_sortants")) or 0
        if existing is None or nb_sortants_new > (_safe_int(existing.get("nb_sortants")) or 0):
            idx[(type_dip, discipline)] = r
    return idx


# ─────────────── Inférence type_diplome / clé fiche ────────────────


def _infer_insersup_type(fiche: dict[str, Any]) -> str | None:
    """Détermine le libellé InserSup `type_diplome` cible pour une fiche.

    Priorité : champ `type_diplome` explicite mappé via PARCOURSUP_TO_INSERSUP_TYPE,
    sinon fallback sur `niveau`.
    """
    raw_type = _safe_str(fiche.get("type_diplome"))
    if raw_type:
        mapped = PARCOURSUP_TO_INSERSUP_TYPE.get(raw_type)
        if mapped:
            return mapped
        # Tentative casse-insensitive
        for key, val in PARCOURSUP_TO_INSERSUP_TYPE.items():
            if key.lower() == raw_type.lower():
                return val
    niveau = _safe_str(fiche.get("niveau"))
    return NIVEAU_TO_DEFAULT_TYPE.get(niveau)


def _fiche_uai_key(fiche: dict[str, Any]) -> str:
    """Clé établissement normalisée — UAI si dispo, sinon nom etablissement."""
    return _norm_key(
        fiche.get("uai")
        or fiche.get("cod_uai")
        or fiche.get("etablissement")
    )


# ─────────────── Construction du snapshot insertion_pro ────────────────


def _snapshot_from_etab_record(record: dict[str, Any], match_score: float, granularite: str) -> dict[str, Any]:
    """Construit le bloc insertion_pro depuis un record `insersup_insertion.json`
    (RAW établissement). Les chiffres `taux_emploi_*` sont dans
    `taux_emploi_salarie_fr` (dict 5 horizons).
    """
    sal_fr = record.get("taux_emploi_salarie_fr") or {}
    if not isinstance(sal_fr, dict):
        sal_fr = {}
    snapshot = {
        "source": "insersup_mesr",
        "granularite": granularite,
        "match_score": match_score,
        "cohorte": _safe_str(record.get("cohorte_promo")) or None,
        "nombre_sortants": _safe_int(record.get("nb_sortants")),
        "taux_emploi_6m": _safe_float(sal_fr.get("6m")),
        "taux_emploi_12m": _safe_float(sal_fr.get("12m")),
        "taux_emploi_18m": _safe_float(sal_fr.get("18m")),
        "taux_emploi_24m": _safe_float(sal_fr.get("24m")),
        "taux_emploi_30m": _safe_float(sal_fr.get("30m")),
        "url_source": INSERSUP_DATASET_URL,
    }
    return snapshot


def _snapshot_from_corpus_record(record: dict[str, Any], match_score: float, granularite: str) -> dict[str, Any]:
    """Construit le bloc insertion_pro depuis un record `insersup_corpus.json`
    (déjà transformé, taux_emploi_* en clés top-level).
    """
    snapshot = {
        "source": "insersup_mesr",
        "granularite": granularite,
        "match_score": match_score,
        "cohorte": _safe_str(record.get("cohorte")) or None,
        "nombre_sortants": _safe_int(record.get("nb_sortants")),
        "taux_emploi_6m": _safe_float(record.get("taux_emploi_6m")),
        "taux_emploi_12m": _safe_float(record.get("taux_emploi_12m")),
        "taux_emploi_18m": _safe_float(record.get("taux_emploi_18m")),
        "taux_emploi_24m": _safe_float(record.get("taux_emploi_24m")),
        "taux_emploi_30m": _safe_float(record.get("taux_emploi_30m")),
        "url_source": INSERSUP_DATASET_URL,
    }
    return snapshot


def _has_any_taux(snapshot: dict[str, Any]) -> bool:
    """True si au moins un horizon emploi est non-null (snapshot exploitable)."""
    return any(
        snapshot.get(k) is not None
        for k in ("taux_emploi_6m", "taux_emploi_12m", "taux_emploi_18m",
                  "taux_emploi_24m", "taux_emploi_30m")
    )


def _pick_freshest_etab(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Choix du record InserSup le plus frais parmi les matches niveau 1.

    Critère : cohorte_promo la plus récente, puis nb_sortants le plus élevé en
    cas d'égalité. Tolérant aux cohortes "année" simples ou "2023,2024" (cumul).
    """
    if not records:
        return None

    def _sort_key(r: dict[str, Any]) -> tuple[int, int]:
        cohorte = _safe_str(r.get("cohorte_promo")) or "0"
        # Cumul "2023,2024" → on prend la dernière année
        if "," in cohorte:
            try:
                last = int(cohorte.split(",")[-1])
            except ValueError:
                last = 0
        else:
            try:
                last = int(cohorte)
            except ValueError:
                last = 0
        nb_s = _safe_int(r.get("nb_sortants")) or 0
        return (last, nb_s)

    return max(records, key=_sort_key)


# ─────────────── API publique ────────────────


def attach_insersup_to_fiches(
    fiches: list[dict[str, Any]],
    insersup_records_path: Path | None = None,
    insersup_corpus_path: Path | None = None,
    min_sortants: int = 30,
    replace_existing: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Attache `insertion_pro` InserSup aux fiches via cascade niveau 1/2/3.

    Args:
        fiches: liste de fiches du corpus (modifiées en place ET retournées).
        insersup_records_path: path vers `insersup_insertion.json` (RAW).
            Si None, défaut `data/processed/insersup_insertion.json`.
        insersup_corpus_path: path vers `insersup_corpus.json` (agrégé).
            Si None, défaut `data/processed/insersup_corpus.json`.
        min_sortants: critère statistique — n'attache que si la cohorte
            InserSup matchée a au moins N sortants. Défaut 30.
        replace_existing: si True, remplace `fiche["insertion_pro"]` existant.
            Si False (défaut Phase A.3), n'attache que si absent. Phase B.1
            (refonte merger v3) utilisera True après purge Cereq (ADR-054).

    Returns:
        (fiches_enrichies, stats_dict) — stats expose les compteurs par
        granularité pour audit.

    Le module est **idempotent** : rerun sur un corpus déjà attaché ne change
    rien (avec `replace_existing=False`). Avec `replace_existing=True`, le
    rerun produit le même output déterministe (pas de `datetime.now()` ni
    aléatoire).
    """
    records_path = insersup_records_path or INSERSUP_RECORDS_PATH
    corpus_path = insersup_corpus_path or INSERSUP_CORPUS_PATH

    # Chargement gracieux : si un fichier manque, on log et on skip.
    records: list[dict[str, Any]] = []
    corpus: list[dict[str, Any]] = []
    if records_path.exists():
        try:
            records = json.loads(records_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            _logger.warning("InserSup records illisibles (%s): %s", records_path, e)
    else:
        _logger.warning("InserSup records absent: %s", records_path)

    if corpus_path.exists():
        try:
            corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            _logger.warning("InserSup corpus illisible (%s): %s", corpus_path, e)
    else:
        _logger.warning("InserSup corpus absent: %s", corpus_path)

    # Construction des 3 index inversés
    idx_etab = _build_etab_index(records)
    idx_region = _build_region_index(corpus)
    idx_national = _build_national_index(corpus)

    stats = {
        "n_fiches_in": len(fiches),
        "n_with_existing_insertion_pro": 0,
        "n_skipped_existing": 0,
        "n_replaced": 0,
        "n_attached_etablissement_x_discipline": 0,
        "n_attached_discipline_region": 0,
        "n_attached_discipline_nationale": 0,
        "n_no_match": 0,
        "n_skipped_low_sortants": 0,
        "n_skipped_no_type_inferable": 0,
    }

    for fiche in fiches:
        if not isinstance(fiche, dict):
            continue

        had_existing = "insertion_pro" in fiche and fiche.get("insertion_pro")
        if had_existing:
            stats["n_with_existing_insertion_pro"] += 1
            if not replace_existing:
                stats["n_skipped_existing"] += 1
                continue

        # Inférence type_diplome cible InserSup
        target_type = _infer_insersup_type(fiche)
        if not target_type:
            stats["n_skipped_no_type_inferable"] += 1
            stats["n_no_match"] += 1
            continue

        target_type_norm = _norm_key(target_type)
        discipline_norm = _norm_key(fiche.get("discipline"))
        if not discipline_norm:
            # Sans discipline, aucun matching possible (même niveau 3)
            stats["n_no_match"] += 1
            continue

        snapshot: dict[str, Any] | None = None

        # Niveau 1 — UAI × type × discipline
        uai_norm = _fiche_uai_key(fiche)
        if uai_norm:
            etab_records = idx_etab.get((uai_norm, target_type_norm, discipline_norm))
            if etab_records:
                fresh = _pick_freshest_etab(etab_records)
                if fresh and (_safe_int(fresh.get("nb_sortants")) or 0) >= min_sortants:
                    candidate = _snapshot_from_etab_record(
                        fresh, match_score=1.0, granularite="etablissement_x_discipline"
                    )
                    if _has_any_taux(candidate):
                        snapshot = candidate
                        stats["n_attached_etablissement_x_discipline"] += 1
                elif fresh:
                    stats["n_skipped_low_sortants"] += 1

        # Niveau 2 — type × discipline × region
        if snapshot is None:
            region_norm = _norm_key(fiche.get("region"))
            if region_norm:
                region_record = idx_region.get((target_type_norm, discipline_norm, region_norm))
                if region_record and (_safe_int(region_record.get("nb_sortants")) or 0) >= min_sortants:
                    candidate = _snapshot_from_corpus_record(
                        region_record, match_score=0.7, granularite="discipline_region"
                    )
                    if _has_any_taux(candidate):
                        snapshot = candidate
                        stats["n_attached_discipline_region"] += 1
                elif region_record:
                    stats["n_skipped_low_sortants"] += 1

        # Niveau 3 — type × discipline national
        if snapshot is None:
            national_record = idx_national.get((target_type_norm, discipline_norm))
            if national_record and (_safe_int(national_record.get("nb_sortants")) or 0) >= min_sortants:
                candidate = _snapshot_from_corpus_record(
                    national_record, match_score=0.4, granularite="discipline_nationale"
                )
                if _has_any_taux(candidate):
                    snapshot = candidate
                    stats["n_attached_discipline_nationale"] += 1
            elif national_record:
                stats["n_skipped_low_sortants"] += 1

        if snapshot is None:
            stats["n_no_match"] += 1
            continue

        # Attach (ou replace si demandé)
        if had_existing and replace_existing:
            stats["n_replaced"] += 1
        fiche["insertion_pro"] = snapshot

    stats["n_fiches_out"] = len(fiches)
    stats["n_with_insertion_pro_after"] = sum(
        1 for f in fiches if isinstance(f, dict) and f.get("insertion_pro")
    )
    return fiches, stats


def main() -> None:  # pragma: no cover
    """CLI utilitaire : applique attach sur formations.json (lecture seule par défaut).

    Usage : `python -m src.collect.insersup_attach` — affiche les stats sans
    écrire le résultat. Pour écriture, voir le merger v3 (Phase B.1).
    """
    print("[INSERSUP-ATTACH] dry-run sur formations.json")
    raw = json.loads(Path("data/processed/formations.json").read_text(encoding="utf-8"))
    enriched, stats = attach_insersup_to_fiches(raw)
    for k, v in stats.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":  # pragma: no cover
    main()
