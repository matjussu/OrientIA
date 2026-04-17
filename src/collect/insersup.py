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


# === Statistical representativeness thresholds (quality-gaps fix) ===
#
# InserSup cohortes with very few graduates produce noisy statistics that
# must not be cited as if they had the same weight as a 500-graduate
# aggregate. A lycéen reads "85%" the same whether it's on 30 or 500
# people, but margin of error is completely different.
#
# Policy:
#   ≥ 100 sortants : "large"  — no warning, standard citation
#   30-99 sortants : "medium" — cite with sample size visible
#   20-29 sortants : "small"  — cite with explicit prudence
#   < 20 sortants  : skip     — too few to be statistically meaningful
MIN_SORTANTS_TO_ATTACH = 20
SAMPLE_TIER_LARGE = 100
SAMPLE_TIER_MEDIUM = 30


def _sample_size_tier(n: int | None) -> str:
    """Classify a cohorte size into a robustness tier."""
    if n is None:
        return "unknown"
    if n >= SAMPLE_TIER_LARGE:
        return "large"
    if n >= SAMPLE_TIER_MEDIUM:
        return "medium"
    return "small"


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
COL_PROMO = "Promotion"
COL_SORTANTS = "Nombre de sortants"
COL_TAUX_EMPLOI_12M = "12-Taux d'emploi - 12 mois après le diplôme"
COL_TAUX_EMPLOI_STABLE_12M = "12-Taux de sortants en emploi stable - 12 mois après le diplôme"
COL_SALAIRE_MEDIAN_12M = "12-Salaire mensuel net médian en équivalent temps plein - 12 mois après le diplôme"
COL_TAUX_EMPLOI_18M = "18-Taux d'emploi - 18 mois après le diplôme"
COL_SALAIRE_MEDIAN_30M = "30-Salaire mensuel net médian en équivalent temps plein - 30 mois après le diplôme"


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
    """Extract the metrics subset from a single aggregated row."""
    return {
        "taux_emploi_12m": _safe_float(row.get(COL_TAUX_EMPLOI_12M)),
        "taux_emploi_stable_12m": _safe_float(row.get(COL_TAUX_EMPLOI_STABLE_12M)),
        "salaire_median_12m_mensuel_net": _safe_int(row.get(COL_SALAIRE_MEDIAN_12M)),
        "taux_emploi_18m": _safe_float(row.get(COL_TAUX_EMPLOI_18M)),
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
            if (row.get(COL_GENRE) != "ensemble"
                    or row.get(COL_NAT) != "ensemble"
                    or row.get(COL_REGIME) != "ensemble"):
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


def _pick_freshest(snapshots: list[dict]) -> dict | None:
    """Pick the snapshot with the most recent promo year. Prefers single-year
    promos (e.g. '2024') over bi-annual aggregates ('2023,2024'). Returns None
    if empty list.

    Sort key: (peak_year, is_single_year). With reverse=True, both higher
    peak_year and is_single_year=1 win → single-year '2024' beats bi-annual
    '2023,2024' at the same peak year.
    """
    if not snapshots:
        return None
    def sort_key(s):
        c = s.get("cohorte") or "0"
        if "," in c:
            # Bi-annual '2023,2024' — peak year is the latest
            try:
                last = int(c.split(",")[-1])
            except ValueError:
                return (0, 0)
            return (last, 0)  # bi-annual tied-loser at same peak year
        try:
            return (int(c), 1)  # single-year wins ties
        except ValueError:
            return (0, 0)
    return sorted(snapshots, key=sort_key, reverse=True)[0]


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


def _build_disclaimer(
    fiche: dict,
    granularite: str,
    sample_tier: str = "unknown",
    n_sortants: int | None = None,
) -> str:
    """Human-readable disclaimer on what the insertion numbers cover.

    Includes sample size warning for medium/small cohortes so the lycéen
    understands the statistical robustness (or lack thereof).
    """
    etab = fiche.get("etablissement", "l'établissement")
    domaine = fiche.get("domaine")
    if granularite == "discipline":
        discipline = DOMAINE_TO_DISCIPLINE.get(domaine, "la discipline")
        base = (f"Chiffres d'insertion calculés sur tous les diplômés "
                f"{discipline} de {etab} (discipline agrégée, pas spécifique "
                f"à cette formation).")
    else:
        # type_diplome_agrege
        ps_type = fiche.get("type_diplome", "diplôme")
        base = (f"Chiffres d'insertion calculés sur TOUS les {ps_type}s de "
                f"{etab} confondus (agrégat établissement, pas spécifique à "
                f"cette formation ni à sa discipline).")

    # Append sample size caveat
    if sample_tier == "small" and n_sortants is not None:
        base += (f" Attention : échantillon limité ({n_sortants} diplômés) — "
                 f"ces chiffres ont une marge d'erreur plus large que pour "
                 f"les grandes promos.")
    elif sample_tier == "medium" and n_sortants is not None:
        base += f" Échantillon modéré ({n_sortants} diplômés)."
    return base


def attach_insertion(
    fiches: list[dict],
    csv_path: str | Path,
) -> list[dict]:
    """Attach insersup snapshots to fiches via UAI matching.

    Adds `insertion` dict to each matched fiche with granularite + disclaimer +
    sample_size_tier. Fiches with cohortes < MIN_SORTANTS_TO_ATTACH are
    skipped entirely (statistically insufficient to cite honestly).
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
        # Statistical representativeness filter — skip small cohortes rather
        # than cite misleading numbers.
        n_sortants = snapshot.get("nombre_sortants")
        if n_sortants is not None and n_sortants < MIN_SORTANTS_TO_ATTACH:
            continue
        sample_tier = _sample_size_tier(n_sortants)
        fiche["insertion"] = {
            **snapshot,
            "granularite": granularite,
            "sample_size_tier": sample_tier,
            "disclaimer": _build_disclaimer(fiche, granularite, sample_tier, n_sortants),
            "source": "InserSup DEPP",
            "source_url": "https://www.data.gouv.fr/datasets/insertion-professionnelle-des-diplomes-des-etablissements-denseignement-superieur-dispositif-insersup",
        }

    return fiches
