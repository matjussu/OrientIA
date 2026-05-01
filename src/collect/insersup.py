"""InserSup DEPP — insertion professionnelle des diplômés.

Source : https://www.data.gouv.fr/datasets/insertion-professionnelle-des-diplomes-
des-etablissements-denseignement-superieur-dispositif-insersup

Granularité disponible :
- Agrégation par (Code UAI établissement, type de diplôme, discipline)
- PAS au niveau "formation Parcoursup individuelle" → on ne peut pas attacher
  "le taux d'insertion du Master Cybersécurité ENSIBS spécifiquement".
- Le libellé le plus fin disponible est "INFORMATIQUE", "DROIT", "CHIMIE", etc.
  (discipline) ou "Tout Master LMD" / "Tout diplôme d'ingénieurs" (agrégat
  établissement × type_diplome).

Politique de matching (zéro tolérance erreur, cf memory/feedback_data_integrity) :

1. Match STRICT par Code UAI (col 83) — clé commune avec Parcoursup cod_uai.
2. Filtrage obligatoire Genre=ensemble × Nationalité=ensemble × Régime=ensemble
   pour avoir les chiffres agrégés (pas les désagrégations par sous-groupe).
3. Deux niveaux de granularité — meilleur d'abord :
   a. **Discipline** : INFORMATIQUE pour fiches cyber/data_ia → le plus précis
   b. **Type_diplome agrégé** : "Tout Master LMD" si pas de discipline match
4. Chaque fiche enrichie porte :
   - `granularite`: "discipline" | "type_diplome_agrege"
   - `disclaimer`: texte explicite sur ce que couvre le chiffre
   - `cohorte`: année de sortie (promo)
   - `nombre_sortants`: base statistique pour juger la robustesse
5. Valeurs 'nd' ou vides → skip (pas d'invention).
6. Si aucun match UAI → pas d'attachement (pas de fallback discipline nationale).
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable


# Mapping Parcoursup type_diplome → InserSup type_diplome normalisé
# (col 85 "type_diplome" en minuscules avec underscores)
PARCOURSUP_TO_INSERSUP_TYPE = {
    # Masters
    "Master LMD": "master_LMD",
    "Master": "master_LMD",
    "Master MEEF": "master_MEEF",
    # Licences
    "Licence professionnelle": "licence_pro",
    "Licence pro": "licence_pro",
    "Licence générale": "licence_generale",
    "Licence": "licence_generale",
    # BUT
    "BUT": "but",
    "Bachelor Universitaire de Technologie": "but",
    # Ingé / management
    "Diplôme d'ingénieur": "formation_ingenieur",
    "formation d'école spécialisée": "formation_ingenieur",  # approximation
    # Diplômes visés (écoles spécialisées labellisées)
    "Bachelor": "diplome_vise_niveau_bac_plus_trois_grade_licence",
    "Diplôme visé bac+5": "diplome_vise_niveau_bac_plus_cinq_grade_master",
}

# Mapping domaine projet → libellé discipline InserSup (caps exact)
DOMAINE_TO_DISCIPLINE = {
    "cyber": "INFORMATIQUE",
    "data_ia": "INFORMATIQUE",
}

# Libellés "agrégats" (fallback quand pas de discipline match)
TYPE_DIPLOME_AGGREGATE_LABELS = {
    "master_LMD": "Tout Master LMD",
    "licence_pro": "Toute licence professionnelle",
    "licence_generale": "Toute licence générale",
    "formation_ingenieur": "Tout diplôme d'ingénieurs",
    "but": None,  # InserSup n'a pas d'agrégat "Tout BUT"
}

# Colonnes clés (CSV officielles)
COL_UAI = "Code UAI de l'établissement"
COL_TYPE = "type_diplome"
COL_LIBELLE = "Libellé du diplôme"
COL_GENRE = "Genre"
COL_NAT = "Nationalité"
COL_REGIME = "Régime d'inscription"
# Tier 0 fix (spot-check Matteo 2026-04-18) : forcer obtention_diplome=ensemble
# — évite le bug de non-déterminisme où le pipeline prenait parfois "diplômé"
# parfois "ensemble" selon l'ordre de retour de l'API. "ensemble" est la vue
# publique de référence MESR et inclut les non-diplômés pertinents pour un
# outil d'orientation (le lycéen veut savoir le taux d'emploi réel, pas celui
# des admis jusqu'au bout).
COL_OBTENTION = "Obtention du diplôme"
COL_PROMO = "Promotion"
COL_SORTANTS = "Nombre de sortants"
# Tier 0 fix (spot-check Matteo 2026-04-18) : la colonne agrégée
# "12-Taux d'emploi - 12 mois après le diplôme" est null dans le dataset
# 2025_S2. Il faut calculer taux_emploi_12m comme somme des 3 composantes :
# salarié_France + non_salarié + étranger. Idem pour 18m.
COL_TAUX_EMPLOI_12M = "12-Taux d'emploi - 12 mois après le diplôme"
COL_TAUX_EMPLOI_SAL_FR_12M = "12-Taux d'emploi salarié en France - 12 mois après le diplôme"
COL_TAUX_EMPLOI_NON_SAL_12M = "12-Taux de sortants en emploi non salarié - 12 mois après le diplôme"
COL_TAUX_EMPLOI_ETRANGER_12M = "12-Taux de sortants en emploi à l'étranger - 12 mois après le diplôme"
COL_TAUX_EMPLOI_STABLE_12M = "12-Taux de sortants en emploi stable - 12 mois après le diplôme"
COL_SALAIRE_MEDIAN_12M = "12-Salaire mensuel net médian en équivalent temps plein - 12 mois après le diplôme"
COL_TAUX_EMPLOI_18M = "18-Taux d'emploi - 18 mois après le diplôme"
COL_TAUX_EMPLOI_SAL_FR_18M = "18-Taux d'emploi salarié en France - 18 mois après le diplôme"
COL_TAUX_EMPLOI_NON_SAL_18M = "18-Taux de sortants en emploi non salarié - 18 mois après le diplôme"
COL_TAUX_EMPLOI_ETRANGER_18M = "18-Taux de sortants en emploi à l'étranger - 18 mois après le diplôme"
COL_SALAIRE_MEDIAN_30M = "30-Salaire mensuel net médian en équivalent temps plein - 30 mois après le diplôme"


def _sum_emploi_components(row: dict, month: int) -> float | None:
    """Tier 0 fix (spot-check 2026-04-18) : compute taux d'emploi total
    as sum of salarié_France + non_salarié + étranger components.

    The aggregate column `tx_sortants_en_emploi_N` is null in the 2025_S2
    dataset, so we must sum the 3 sub-components. Returns None when all
    three are null ('nd' / empty).
    """
    if month == 12:
        cols = (COL_TAUX_EMPLOI_SAL_FR_12M, COL_TAUX_EMPLOI_NON_SAL_12M,
                COL_TAUX_EMPLOI_ETRANGER_12M)
    elif month == 18:
        cols = (COL_TAUX_EMPLOI_SAL_FR_18M, COL_TAUX_EMPLOI_NON_SAL_18M,
                COL_TAUX_EMPLOI_ETRANGER_18M)
    else:
        raise ValueError(f"Unsupported month {month}, expected 12 or 18")
    components = [_safe_float(row.get(c)) for c in cols]
    # Fallback : si la colonne agrégée est remplie (rare mais possible), on la prend
    agg_col = COL_TAUX_EMPLOI_12M if month == 12 else COL_TAUX_EMPLOI_18M
    agg = _safe_float(row.get(agg_col))
    if agg is not None:
        return agg
    # Sinon somme des composantes non-null ; None si toutes null
    non_null = [c for c in components if c is not None]
    if not non_null:
        return None
    return sum(non_null)


def _safe_float(val) -> float | None:
    """Return float(val) or None. InserSup codes vides ('') and 'nd' (non dispo)."""
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.lower() in ("nd", "nan"):
        return None
    try:
        # Some values use comma as decimal separator
        s = s.replace(",", ".")
        return float(s)
    except ValueError:
        return None


def _safe_int(val) -> int | None:
    f = _safe_float(val)
    if f is None:
        return None
    return int(f)


def _snapshot_from_row(row: dict) -> dict:
    """Extract the metrics subset from a single aggregated row.

    Tier 0 fix : taux d'emploi total = somme des 3 composantes (sal_fr +
    non_sal + étranger). Le champ agrégé `12-Taux d'emploi` est null dans
    le dataset 2025_S2.
    """
    return {
        "taux_emploi_12m": _sum_emploi_components(row, 12),
        "taux_emploi_stable_12m": _safe_float(row.get(COL_TAUX_EMPLOI_STABLE_12M)),
        "salaire_median_12m_mensuel_net": _safe_int(row.get(COL_SALAIRE_MEDIAN_12M)),
        "taux_emploi_18m": _sum_emploi_components(row, 18),
        "salaire_median_30m_mensuel_net": _safe_int(row.get(COL_SALAIRE_MEDIAN_30M)),
        "nombre_sortants": _safe_int(row.get(COL_SORTANTS)),
        "cohorte": (row.get(COL_PROMO) or "").strip() or None,
    }


def _has_any_metric(snap: dict) -> bool:
    """True if at least one core metric is non-null (skip rows with all 'nd')."""
    return any(
        snap.get(k) is not None
        for k in (
            "taux_emploi_12m",
            "taux_emploi_18m",
            "salaire_median_12m_mensuel_net",
            "salaire_median_30m_mensuel_net",
        )
    )


def load_insersup_aggregated(
    csv_path: str | Path,
) -> dict[tuple[str, str, str], list[dict]]:
    """Parse InserSup, keep only Genre=ensemble × Nat=ensemble × Régime=ensemble
    rows, and index by (cod_uai, type_diplome, libelle).

    Returns a dict: `{(uai, type_diplome, libelle): [snap_per_promo, ...]}`.
    Multiple promos per key — we keep all so callers can pick freshest.
    """
    idx: dict[tuple[str, str, str], list[dict]] = {}
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            # Tier 0 fix : filtre déterministe sur les 4 dimensions, dont
            # obtention_diplome="ensemble" (vue publique MESR par défaut).
            # Avant ce fix, le pipeline prenait parfois "diplômé" parfois
            # "ensemble" selon l'ordre de retour → incohérence des chiffres.
            if (row.get(COL_GENRE) != "ensemble"
                    or row.get(COL_NAT) != "ensemble"
                    or row.get(COL_REGIME) != "ensemble"
                    or row.get(COL_OBTENTION) != "ensemble"):
                continue
            uai = (row.get(COL_UAI) or "").strip()
            if not uai:
                continue
            type_dip = (row.get(COL_TYPE) or "").strip()
            lib = (row.get(COL_LIBELLE) or "").strip()
            snap = _snapshot_from_row(row)
            if not _has_any_metric(snap):
                continue
            idx.setdefault((uai, type_dip, lib), []).append(snap)
    return idx


def _cohorte_sort_key(cohorte: str | None) -> tuple:
    """Sort key for cohortes — higher values = more recent.
    Single-year promos (e.g. '2024') beat bi-annual aggregates ('2023,2024')
    at same peak year.
    """
    c = cohorte or "0"
    if "," in c:
        try:
            last = int(c.split(",")[-1])
        except ValueError:
            return (0, 0)
        return (last, 0)
    try:
        return (int(c), 1)
    except ValueError:
        return (0, 0)


_METRIC_KEYS = (
    "taux_emploi_12m",
    "taux_emploi_stable_12m",
    "salaire_median_12m_mensuel_net",
    "taux_emploi_18m",
    "salaire_median_30m_mensuel_net",
)


def _pick_freshest(snapshots: list[dict]) -> dict | None:
    """Merge snapshots across cohortes : for each metric, take the FRESHEST
    non-null value. The resulting snapshot uses the cohorte of the most
    recent snap as reference, and exposes `cohortes_used` for transparency.

    Tier 0 fix (2026-04-18) : InserSup publishes metrics progressively
    (2024 cohorte has taux_emploi_12m but not salaire_12m yet, while 2022
    has everything). Picking ONLY the freshest cohorte = losing salary data
    on recent promos. Merging avoids that blind spot.
    """
    if not snapshots:
        return None
    # Sort by freshness descending
    sorted_snaps = sorted(snapshots, key=lambda s: _cohorte_sort_key(s.get("cohorte")),
                          reverse=True)

    # Base = most recent snap (for cohorte field + nombre_sortants)
    merged = dict(sorted_snaps[0])
    # cohortes_used tracks which cohorte provided each metric
    cohortes_used: dict[str, str] = {}
    for key in _METRIC_KEYS:
        if merged.get(key) is not None:
            cohortes_used[key] = merged.get("cohorte") or "?"
            continue
        # Try older snaps for a non-null value
        for snap in sorted_snaps[1:]:
            val = snap.get(key)
            if val is not None:
                merged[key] = val
                cohortes_used[key] = snap.get("cohorte") or "?"
                break
    merged["cohortes_used"] = cohortes_used
    return merged


def _match_fiche_to_insersup(
    fiche: dict,
    idx: dict[tuple[str, str, str], list[dict]],
) -> tuple[dict | None, str | None]:
    """Return (snapshot, granularite) for a fiche, or (None, None) if no match.

    `granularite` indicates what the attached number covers:
      - "discipline"            : INFORMATIQUE (for cyber/data_ia)
      - "type_diplome_agrege"   : "Tout Master LMD" etc.
      - None                    : no match
    """
    uai = (fiche.get("cod_uai") or "").strip()
    if not uai:
        return None, None
    # Infer target InserSup type_diplome
    # Parcoursup type_diplome is inferred from 'type_diplome' field (ONISEP side)
    # or 'niveau' Parcoursup ("bac+2", "bac+3", "bac+5").
    ps_type = (fiche.get("type_diplome") or "").strip()
    target_is = PARCOURSUP_TO_INSERSUP_TYPE.get(ps_type)
    if not target_is:
        # Fallback from niveau
        niveau = fiche.get("niveau")
        if niveau == "bac+5":
            target_is = "master_LMD"
        elif niveau == "bac+3":
            target_is = "licence_generale"
        elif niveau == "bac+2":
            target_is = None  # BUT has no aggregate, and BTS is not in InserSup
    if not target_is:
        return None, None

    # Try DISCIPLINE match first (best granularity)
    domaine = fiche.get("domaine")
    discipline_label = DOMAINE_TO_DISCIPLINE.get(domaine) if domaine else None
    if discipline_label:
        snaps = idx.get((uai, target_is, discipline_label))
        if snaps:
            return _pick_freshest(snaps), "discipline"

    # Fall back to TYPE_DIPLOME aggregate ("Tout Master LMD" etc.)
    agg_label = TYPE_DIPLOME_AGGREGATE_LABELS.get(target_is)
    if agg_label:
        snaps = idx.get((uai, target_is, agg_label))
        if snaps:
            return _pick_freshest(snaps), "type_diplome_agrege"

    return None, None


def _build_disclaimer(fiche: dict, granularite: str) -> str:
    """Human-readable disclaimer on what the insertion numbers cover."""
    etab = fiche.get("etablissement", "l'établissement")
    domaine = fiche.get("domaine")
    if granularite == "discipline":
        discipline = DOMAINE_TO_DISCIPLINE.get(domaine, "la discipline")
        return (f"Chiffres d'insertion calculés sur tous les diplômés "
                f"{discipline} de {etab} (discipline agrégée, pas spécifique "
                f"à cette formation).")
    # type_diplome_agrege
    ps_type = fiche.get("type_diplome", "diplôme")
    return (f"Chiffres d'insertion calculés sur TOUS les {ps_type}s de "
            f"{etab} confondus (agrégat établissement, pas spécifique à "
            f"cette formation ni à sa discipline).")


def attach_insertion(
    fiches: list[dict],
    csv_path: str | Path,
) -> list[dict]:
    """Attach insersup snapshots to fiches via UAI matching.

    Adds `insertion` dict to each matched fiche with granularite + disclaimer.
    Graceful no-op if CSV is missing.
    """
    p = Path(csv_path)
    if not p.exists():
        return fiches

    idx = load_insersup_aggregated(p)

    for fiche in fiches:
        snapshot, granularite = _match_fiche_to_insersup(fiche, idx)
        if snapshot is None:
            continue
        fiche["insertion"] = {
            **snapshot,
            "granularite": granularite,
            "disclaimer": _build_disclaimer(fiche, granularite),
            "source": "InserSup DEPP",
            "source_url": "https://www.data.gouv.fr/datasets/insertion-professionnelle-des-diplomes-des-etablissements-denseignement-superieur-dispositif-insersup",
        }

    return fiches


# ---------- Sprint 12 D5 — exposition au RAG ----------

INSERSUP_SOURCE_URL = (
    "https://www.data.gouv.fr/datasets/insertion-professionnelle-"
    "des-diplomes-des-etablissements-denseignement-superieur-dispositif-insersup"
)


def attach_to_insertion_pro(
    fiches: list[dict],
    csv_path: str | Path,
) -> tuple[list[dict], dict]:
    """Sprint 12 D5 — variante de `attach_insertion` qui écrit dans
    `insertion_pro` (compatible dispatch RAG `_format_insertion_pro`).

    Schema écrit (avec `source='insersup'` explicite pour dispatch dans
    `src.rag.embeddings._format_insertion_pro`) :

        fiche['insertion_pro'] = {
            'source': 'insersup',
            'cohorte': '2021',
            'taux_emploi_12m': 78.0,           # %
            'taux_emploi_stable_12m': 65.7,    # % (CDI/CDD>6m)
            'taux_emploi_18m': 81.8,           # %
            'salaire_median_12m': 1850,        # € net mensuel ETP
            'salaire_median_30m': 2070,        # € net mensuel ETP
            'nombre_sortants': 247,
            'granularite': 'discipline' | 'type_diplome_agrege',
            'disclaimer': '...',
            'source_url': '...',
        }

    Politique d'overwrite : InserSup > Céreq pour les fiches niveau
    master/LP/DUT (plus granulaire, source officielle MESR par
    établissement). Tracé dans audit_stats.

    Returns:
        (fiches_enrichies, audit_stats) où audit_stats contient :
        - matched : nb fiches enrichies
        - unmatched_no_uai : nb fiches sans cod_uai (pas matchables)
        - unmatched_no_match : nb fiches avec cod_uai mais pas trouvé
        - overwritten_cereq : nb fiches avec Céreq préexistant remplacé
        - overwritten_cfa : nb fiches avec CFA préexistant remplacé
    """
    p = Path(csv_path)
    audit = {
        "matched": 0,
        "unmatched_no_uai": 0,
        "unmatched_no_match": 0,
        "overwritten_cereq": 0,
        "overwritten_cfa": 0,
    }
    if not p.exists():
        return fiches, audit

    idx = load_insersup_aggregated(p)

    for fiche in fiches:
        snapshot, granularite = _match_fiche_to_insersup(fiche, idx)
        if snapshot is None:
            if not fiche.get("cod_uai"):
                audit["unmatched_no_uai"] += 1
            else:
                audit["unmatched_no_match"] += 1
            continue

        # Trace overwrite si insertion_pro préexistant (pour audit honnête)
        existing = fiche.get("insertion_pro")
        if isinstance(existing, dict):
            existing_source = (existing.get("source") or "").lower()
            if existing_source == "cereq":
                audit["overwritten_cereq"] += 1
            elif existing_source == "inserjeunes_cfa":
                audit["overwritten_cfa"] += 1

        ip = {
            "source": "insersup",
            "cohorte": snapshot.get("cohorte"),
            "taux_emploi_12m": snapshot.get("taux_emploi_12m"),
            "taux_emploi_stable_12m": snapshot.get("taux_emploi_stable_12m"),
            "salaire_median_12m": snapshot.get("salaire_median_12m_mensuel_net"),
            "taux_emploi_18m": snapshot.get("taux_emploi_18m"),
            "salaire_median_30m": snapshot.get("salaire_median_30m_mensuel_net"),
            "nombre_sortants": snapshot.get("nombre_sortants"),
            "granularite": granularite,
            "disclaimer": _build_disclaimer(fiche, granularite),
            "source_url": INSERSUP_SOURCE_URL,
        }
        # Skip None values pour éviter pollution embedding avec "null"
        fiche["insertion_pro"] = {k: v for k, v in ip.items() if v is not None}
        audit["matched"] += 1

    return fiches, audit
