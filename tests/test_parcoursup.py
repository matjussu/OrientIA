import pandas as pd
from src.collect.parcoursup import (
    load_parcoursup,
    filter_domain,
    extract_fiche,
    DOMAIN_KEYWORDS,
)


def test_domain_keywords_defined():
    assert "cyber" in DOMAIN_KEYWORDS
    assert "data_ia" in DOMAIN_KEYWORDS
    assert any("cybersécurité" in kw.lower() or "cyber" in kw.lower()
               for kw in DOMAIN_KEYWORDS["cyber"])
    assert any("data" in kw.lower() or "intelligence artificielle" in kw.lower()
               for kw in DOMAIN_KEYWORDS["data_ia"])


def test_filter_domain_keeps_cyber_entries():
    df = pd.DataFrame({
        "formation": [
            "Master Cybersécurité",
            "Licence Histoire",
            "BUT Informatique parcours cyber",
            "BTS Comptabilité",
        ]
    })
    filtered = filter_domain(df, "cyber", name_column="formation")
    assert len(filtered) == 2
    assert "Histoire" not in filtered["formation"].values


# === Vague A — extract_fiche enriched fields ===

def _vague_a_row() -> pd.Series:
    """Minimal row with all Vague A new columns populated."""
    return pd.Series({
        "lib_for_voe_ins": "Master Cybersécurité",
        "g_ea_lib_vx": "Université de Rennes",
        "cod_uai": "0351842X",
        "ville_etab": "Rennes",
        "region_etab_aff": "Bretagne",
        "dep_lib": "Ille-et-Vilaine",
        "taux_acces_ens": 18.0,
        "capa_fin": 24,
        "contrat_etab": "Public",
        "detail_forma": "Description formation",
        "pct_tb": 45.0, "pct_b": 30.0, "pct_ab": 20.0, "pct_sansmention": 5.0,
        "pct_bg": 80.0, "pct_bt": 15.0, "pct_bp": 5.0,
        "part_acces_gen": 80.0, "part_acces_tec": 15.0, "part_acces_pro": 5.0,
        "pct_bours": 20.0,
        # Vague A new columns
        "cod_aff_form": "42156",
        "lien_form_psup": "https://www.parcoursup.fr/formation/42156",
        "voe_tot": 1250,
        "nb_voe_pp": 800,
        "nb_cla_pp": 600,
        "acc_internat": 5,
        "pct_f": 24.0,
        "pct_neobac": 85.0,
        "pct_aca_orig_idf": 12.0,
    })


def test_extract_fiche_vague_a_includes_cod_aff_form():
    fiche = extract_fiche(_vague_a_row())
    assert fiche["cod_aff_form"] == "42156"
    assert "parcoursup.fr" in fiche["lien_form_psup"]


def test_extract_fiche_includes_cod_uai_for_insersup_join():
    """cod_uai is the official MEN establishment id — required to join
    with InserSup (insertion pro) and other ESR open-data datasets.
    Missing it silently means 0 InserSup matches."""
    fiche = extract_fiche(_vague_a_row())
    assert fiche["cod_uai"] == "0351842X"


def test_extract_fiche_vague_a_admission_block_structured():
    fiche = extract_fiche(_vague_a_row())
    adm = fiche["admission"]
    assert adm["session"] == 2025
    assert adm["taux_acces"] == 18.0
    assert adm["places"] == 24
    assert adm["volumes"]["voeux_totaux"] == 1250
    assert adm["volumes"]["voeux_phase_principale"] == 800
    assert adm["volumes"]["classes_phase_principale"] == 600
    assert adm["internat_disponible"] is True


def test_extract_fiche_vague_a_internat_zero_means_false():
    row = _vague_a_row()
    row["acc_internat"] = 0
    fiche = extract_fiche(row)
    assert fiche["admission"]["internat_disponible"] is False


def test_extract_fiche_vague_a_internat_missing_means_none():
    row = _vague_a_row()
    row["acc_internat"] = None
    fiche = extract_fiche(row)
    assert fiche["admission"]["internat_disponible"] is None


def test_extract_fiche_vague_a_profil_admis_extended_demographics():
    fiche = extract_fiche(_vague_a_row())
    profil = fiche["profil_admis"]
    assert profil["femmes_pct"] == 24.0
    assert profil["neobacheliers_pct"] == 85.0
    assert profil["origine_academique_idf_pct"] == 12.0


def test_extract_fiche_vague_a_legacy_fields_still_present():
    """Backward-compat check: legacy flat fields (taux_acces_parcoursup_2025,
    nombre_places) remain populated so the existing FAISS index and 231
    legacy tests don't break."""
    fiche = extract_fiche(_vague_a_row())
    assert fiche["taux_acces_parcoursup_2025"] == 18.0
    assert fiche["nombre_places"] == 24
