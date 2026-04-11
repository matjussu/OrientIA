from pathlib import Path
import pandas as pd
from src.collect.niveau import infer_niveau


DOMAIN_KEYWORDS = {
    "cyber": [
        "cyber",
        "cybersécurité", "cyber sécurité", "cyber-sécurité", "cybersecurity",
        "sécurité informatique", "sécurité des systèmes", "sécurité numérique",
        r"\bSSI\b", r"\bSecNumEdu\b",
    ],
    "data_ia": [
        "intelligence artificielle", "data science", "données", "data",
        "machine learning", "apprentissage automatique", "big data",
        r"\bIA\b", "science des données", "data analyst", "data engineer",
    ],
}

# Resolved column names from the real Parcoursup 2025 export
# (inspected by controller on 2026-04-10; Parcoursup open data has no RNCP column)
FORMATION_COLUMN = "lib_for_voe_ins"
ETABLISSEMENT_COLUMN = "g_ea_lib_vx"
VILLE_COLUMN = "ville_etab"
TAUX_ACCES_COLUMN = "taux_acces_ens"
PLACES_COLUMN = "capa_fin"
CONTRAT_COLUMN = "contrat_etab"
REGION_COLUMN = "region_etab_aff"
DEPARTEMENT_COLUMN = "dep_lib"
DETAIL_COLUMN = "detail_forma"

# Mention-level breakdown of admitted candidates (useful for realism scoring)
PCT_TB_COLUMN = "pct_tb"               # % admis avec mention Très Bien
PCT_B_COLUMN = "pct_b"                 # % admis avec mention Bien
PCT_AB_COLUMN = "pct_ab"               # % admis avec mention Assez Bien
PCT_SANSMENTION_COLUMN = "pct_sansmention"

# Bac-type breakdown of admitted candidates (profile signal)
PCT_BG_COLUMN = "pct_bg"               # % admis bac général
PCT_BT_COLUMN = "pct_bt"               # % admis bac techno
PCT_BP_COLUMN = "pct_bp"               # % admis bac pro

# Access share by bac type (realism: can someone from bac techno get in?)
PART_ACCES_GEN_COLUMN = "part_acces_gen"
PART_ACCES_TEC_COLUMN = "part_acces_tec"
PART_ACCES_PRO_COLUMN = "part_acces_pro"

PCT_BOURS_COLUMN = "pct_bours"         # % boursiers (social mix)


def load_parcoursup(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(Path(path), sep=";", encoding="utf-8", low_memory=False)


def filter_domain(df: pd.DataFrame, domain: str, name_column: str) -> pd.DataFrame:
    if domain not in DOMAIN_KEYWORDS:
        raise ValueError(f"Unknown domain: {domain}")
    pattern = "|".join(DOMAIN_KEYWORDS[domain])
    mask = df[name_column].fillna("").str.contains(pattern, case=False, regex=True)
    return df[mask].copy()


def _safe_float(val) -> float | None:
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_int(val) -> int | None:
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _infer_statut(contrat: str) -> str:
    if not isinstance(contrat, str):
        return "Inconnu"
    c = contrat.lower()
    if c.startswith("public"):
        return "Public"
    if "privé" in c or "prive" in c:
        return "Privé"
    return "Inconnu"


def extract_fiche(row: pd.Series) -> dict:
    nom = str(row.get(FORMATION_COLUMN, "")).strip()
    return {
        "source": "parcoursup",
        "nom": nom,
        "etablissement": str(row.get(ETABLISSEMENT_COLUMN, "")).strip(),
        "ville": str(row.get(VILLE_COLUMN, "")).strip(),
        "region": str(row.get(REGION_COLUMN, "")).strip() or None,
        "departement": str(row.get(DEPARTEMENT_COLUMN, "")).strip() or None,
        "rncp": None,
        "taux_acces_parcoursup_2025": _safe_float(row.get(TAUX_ACCES_COLUMN)),
        "nombre_places": _safe_int(row.get(PLACES_COLUMN)),
        "statut": _infer_statut(row.get(CONTRAT_COLUMN, "")),
        "niveau": infer_niveau(nom),
        # Enriched fields for realism & discovery scoring
        "detail": str(row.get(DETAIL_COLUMN, "")).strip() or None,
        "profil_admis": {
            "mentions_pct": {
                "tb": _safe_float(row.get(PCT_TB_COLUMN)),
                "b": _safe_float(row.get(PCT_B_COLUMN)),
                "ab": _safe_float(row.get(PCT_AB_COLUMN)),
                "sans": _safe_float(row.get(PCT_SANSMENTION_COLUMN)),
            },
            "bac_type_pct": {
                "general": _safe_float(row.get(PCT_BG_COLUMN)),
                "techno": _safe_float(row.get(PCT_BT_COLUMN)),
                "pro": _safe_float(row.get(PCT_BP_COLUMN)),
            },
            "acces_pct": {
                "general": _safe_float(row.get(PART_ACCES_GEN_COLUMN)),
                "techno": _safe_float(row.get(PART_ACCES_TEC_COLUMN)),
                "pro": _safe_float(row.get(PART_ACCES_PRO_COLUMN)),
            },
            "boursiers_pct": _safe_float(row.get(PCT_BOURS_COLUMN)),
        },
    }


def collect_parcoursup_fiches(path: str | Path) -> list[dict]:
    df = load_parcoursup(path)
    all_fiches = []
    for domain in ("cyber", "data_ia"):
        filtered = filter_domain(df, domain, FORMATION_COLUMN)
        for _, row in filtered.iterrows():
            fiche = extract_fiche(row)
            fiche["domaine"] = domain
            all_fiches.append(fiche)
    return all_fiches
