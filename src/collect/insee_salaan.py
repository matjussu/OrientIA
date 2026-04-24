"""INSEE SALAAN 2023 — Fichier Détail Salaires Annuels super-anonymisés.

Source : https://www.insee.fr/fr/statistiques/8793064 (ou similaire)
Format : CSV ~233 MB (zip 42 MB) — 1 ligne par salarié × poste.
Licence : statistique publique / Etalab.

**Différence avec SALCS (scaffold insee.py existant)** :
- SALCS = agrégats pré-calculés (xlsx, <15 MB) — déjà pivoté par PCS × âge
- SALAAN = détail individuel super-anonymisé (CSV, 233 MB) — on doit agréger

**Agrégation OrientIA** :

Stats pivotées par (CS × AGE_TR × SEXE × REGT) :
- Effectif pondéré (somme POND)
- Distribution TRNNETO (tranches salaire NET annuel, 24 modalités)
- Salaire NET médian estimé via point médian de la tranche cumulée
- Salaire NET moyen estimé via moyenne pondérée des points médians

**Usage OrientIA** : cross-link fiche × CS via codes ROME → domaine →
PCS-ESE. Permet de répondre "salaire NET médian ingénieur 27-31 ans IDF".

Mapping CS → domaine OrientIA : 29 catégories PCS-ESE Niveau 2.
"""
from __future__ import annotations

import csv
import io
import json
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Optional


RAW_ZIP = Path("data/raw/insee/FD_SALAAN_2023_csv.zip")
CSV_DATA_NAME = "FD_SALAAN_2023.csv"
CSV_VARMOD_NAME = "Varmod_SALAAN_2023.csv"
PROCESSED_PATH = Path("data/processed/insee_salaires_2023.json")


# --- Mapping CS (PCS-ESE Niveau 2) → domaine OrientIA + libellé ---

CS_LIBELLE: dict[str, str] = {
    "10": "Agriculteurs (salariés de leur exploitation)",
    "21": "Artisans (salariés de leur entreprise)",
    "22": "Commerçants et assimilés (salariés de leur entreprise)",
    "23": "Chefs d'entreprise de 10 salariés ou plus",
    "31": "Professions libérales (exercées sous statut de salarié)",
    "33": "Cadres de la fonction publique",
    "34": "Professeurs, professions scientifiques",
    "35": "Professions de l'information, des arts et des spectacles",
    "37": "Cadres administratifs et commerciaux d'entreprises",
    "38": "Ingénieurs et cadres techniques d'entreprises",
    "42": "Professeurs des écoles, instituteurs et professions assimilées",
    "43": "Professions intermédiaires de la santé et du travail social",
    "44": "Clergé, religieux",
    "45": "Professions intermédiaires administratives de la fonction publique",
    "46": "Professions intermédiaires administratives et commerciales d'entreprises",
    "47": "Techniciens (sauf techniciens tertiaires)",
    "48": "Contremaîtres, agents de maîtrise (maîtrise administrative exclue)",
    "52": "Employés civils et agents de service de la fonction publique",
    "53": "Agents de surveillance",
    "54": "Employés administratifs d'entreprise",
    "55": "Employés de commerce",
    "56": "Personnels des services directs aux particuliers",
    "62": "Ouvriers qualifiés de type industriel",
    "63": "Ouvriers qualifiés de type artisanal",
    "64": "Chauffeurs",
    "65": "Ouvriers qualifiés de la manutention, du magasinage et du transport",
    "67": "Ouvriers non qualifiés de type industriel",
    "68": "Ouvriers non qualifiés de type artisanal",
    "69": "Ouvriers agricoles et assimilés",
}

CS_TO_DOMAINE: dict[str, str] = {
    "10": "agriculture",
    "21": "artisanat",
    "22": "commerce",
    "23": "entreprise_direction",
    "31": "prof_lib",
    "33": "cadres_fonction_pub",
    "34": "cadres_enseign_sci",
    "35": "cadres_arts_media",
    "37": "cadres_admin_comm",
    "38": "cadres_ingenieurs",
    "42": "prof_inter_enseign",
    "43": "prof_inter_sante_social",
    "44": "cultes",
    "45": "prof_inter_admin_pub",
    "46": "prof_inter_admin_ent",
    "47": "prof_inter_technique",
    "48": "prof_inter_contremai",
    "52": "employes_fonction_pub",
    "53": "employes_police_militaire",
    "54": "employes_admin_ent",
    "55": "employes_commerce",
    "56": "employes_services_dir",
    "62": "ouvriers_qualifies_indus",
    "63": "ouvriers_qualifies_artisanat",
    "64": "chauffeurs",
    "65": "ouvriers_qualifies_manut_stock_trans",
    "67": "ouvriers_non_qualifies_indus",
    "68": "ouvriers_non_qualifies_artisanat",
    "69": "ouvriers_agricoles",
}


# --- Mapping TRNNETO (code → point médian de la tranche en €) ---
# Source : PDF descriptif page 3/8 (fichier Postes TRBRUTT) — les tranches sont
# identiques dans SALAAN pour TRNNETO (salaire NET annuel).

TRNNETO_MIDPOINT_EUR: dict[str, int] = {
    "00": 100,     # < 200€
    "01": 350,     # 200-499
    "02": 750,     # 500-999
    "03": 1250,    # 1000-1499
    "04": 1750,    # 1500-1999
    "05": 2500,    # 2000-2999
    "06": 3500,    # 3000-3999
    "07": 5000,    # 4000-5999
    "08": 7000,    # 6000-7999
    "09": 9000,    # 8000-9999
    "10": 11000,   # 10000-11999
    "11": 13000,   # 12000-13999
    "12": 15000,   # 14000-15999
    "13": 17000,   # 16000-17999
    "14": 19000,   # 18000-19999
    "15": 21000,   # 20000-21999
    "16": 23000,   # 22000-23999
    "17": 25000,   # 24000-25999
    "18": 27000,   # 26000-27999
    "19": 29000,   # 28000-29999
    "20": 32500,   # 30000-34999
    "21": 37500,   # 35000-39999
    "22": 45000,   # 40000-49999
    "23": 60000,   # 50000+ (estimation)
}


# --- Mapping REGT (région implantation) ---

REGT_LIBELLE: dict[str, str] = {
    "01": "Guadeloupe", "02": "Martinique", "03": "Guyane", "04": "La Réunion",
    "06": "Mayotte",
    "11": "Île-de-France", "24": "Centre-Val de Loire",
    "27": "Bourgogne-Franche-Comté", "28": "Normandie",
    "32": "Hauts-de-France", "44": "Grand Est", "52": "Pays de la Loire",
    "53": "Bretagne", "75": "Nouvelle-Aquitaine", "76": "Occitanie",
    "84": "Auvergne-Rhône-Alpes", "93": "Provence-Alpes-Côte d'Azur",
    "94": "Corse",
}


# --- Mapping AGE_TR (tranche d'âge quadriennale) ---

AGE_TR_LIBELLE: dict[str, str] = {
    "00": "[0;15[", "19": "[15;19[", "23": "[19;23[", "27": "[23;27[",
    "31": "[27;31[", "35": "[31;35[", "39": "[35;39[", "43": "[39;43[",
    "47": "[43;47[", "51": "[47;51[", "55": "[51;55[", "59": "[55;59[",
    "63": "[59;63[", "67": "[63;67[", "71": "[67;71[", "72": "[71;+[",
}


SEXE_LIBELLE: dict[str, str] = {"1": "Hommes", "2": "Femmes"}


# --- Agrégation streaming ---


def _median_from_distribution(
    distribution: dict[str, float],
) -> tuple[Optional[float], Optional[float]]:
    """Estime la médiane et la moyenne pondérée d'une distribution de
    tranches TRNNETO.

    Retourne (médiane_estim_eur, moyenne_estim_eur). Médiane = point médian
    de la tranche où on atteint 50% du poids cumulé. Moyenne = Σ (midpoint_i × weight_i) / Σ weights.

    None si distribution vide.
    """
    total = sum(distribution.values())
    if total == 0:
        return None, None
    # Moyenne pondérée
    weighted_sum = 0.0
    for tr_code, w in distribution.items():
        mid = TRNNETO_MIDPOINT_EUR.get(tr_code)
        if mid is not None:
            weighted_sum += mid * w
    moyenne = weighted_sum / total if total else None

    # Médiane : cumul croissant sur codes triés (00-23 = ordre naturel)
    codes_sorted = sorted(distribution.keys())
    cumul = 0.0
    mediane = None
    for c in codes_sorted:
        w = distribution[c]
        cumul += w
        if cumul >= total / 2:
            mediane = TRNNETO_MIDPOINT_EUR.get(c)
            break
    return mediane, moyenne


def aggregate_salaan(
    zip_path: Path = RAW_ZIP,
    csv_name: str = CSV_DATA_NAME,
    min_effectif: float = 100.0,
) -> list[dict[str, Any]]:
    """Stream CSV + agrège par (CS, AGE_TR, SEXE, REGT) → stats salaires.

    Args:
        zip_path: chemin du zip SALAAN
        csv_name: nom du CSV dans le zip
        min_effectif: seuil min effectif pondéré pour exporter (filtre
            les combinaisons rares qui bruitent les stats — INSEE masque
            typiquement < 100)

    Returns:
        Liste d'entrées (1 par combinaison CS × AGE_TR × SEXE × REGT
        passant le seuil) au schéma OrientIA :
        {source, millesime, cs_code, cs_libelle, domaine_orientia,
         age_tr, age_tr_libelle, sexe, sexe_libelle, region_code,
         region_libelle, effectif, salaire_net_median_annuel,
         salaire_net_moyen_annuel, salaire_net_median_mensuel,
         salaire_net_moyen_mensuel, distribution_tranches}
    """
    # distribution[(cs, age_tr, sexe, regt)] = Counter<tr_code → sum_pond>
    distributions: dict[tuple, Counter] = defaultdict(Counter)

    n_rows = 0
    with zipfile.ZipFile(zip_path) as z:
        with z.open(csv_name) as f:
            text = io.TextIOWrapper(f, encoding="latin-1")
            reader = csv.DictReader(text, delimiter=";")
            for row in reader:
                n_rows += 1
                cs = (row.get("CS") or "").strip()
                age_tr = (row.get("AGE_TR") or "").strip()
                sexe = (row.get("SEXE") or "").strip()
                regt = (row.get("REGT") or "").strip()
                tr = (row.get("TRNNETO") or "").strip()
                pond = row.get("POND") or "0"
                if not (cs and age_tr and sexe and tr):
                    continue
                try:
                    w = float(pond)
                except ValueError:
                    continue
                if w <= 0:
                    continue
                distributions[(cs, age_tr, sexe, regt)][tr] += w
                if n_rows % 500_000 == 0:
                    print(f"  [insee_salaan] rows processed: {n_rows:,}")

    print(f"  [insee_salaan] total rows: {n_rows:,}, combinaisons: {len(distributions):,}")

    entries: list[dict[str, Any]] = []
    for (cs, age_tr, sexe, regt), dist in distributions.items():
        effectif = sum(dist.values())
        if effectif < min_effectif:
            continue
        med, moy = _median_from_distribution(dist)
        entries.append({
            "source": "insee_salaan_2023",
            "millesime": "2023",
            "cs_code": cs,
            "cs_libelle": CS_LIBELLE.get(cs),
            "domaine_orientia": CS_TO_DOMAINE.get(cs),
            "age_tr": age_tr,
            "age_tr_libelle": AGE_TR_LIBELLE.get(age_tr),
            "sexe": sexe,
            "sexe_libelle": SEXE_LIBELLE.get(sexe),
            "region_code": regt,
            "region_libelle": REGT_LIBELLE.get(regt),
            "effectif_pondere": round(effectif, 1),
            "salaire_net_median_annuel": med,
            "salaire_net_moyen_annuel": round(moy, 0) if moy else None,
            "salaire_net_median_mensuel": round(med / 12, 0) if med else None,
            "salaire_net_moyen_mensuel": round(moy / 12, 0) if moy else None,
            "distribution_tranches": dict(dist),
        })
    return entries


def save_processed(
    entries: list[dict[str, Any]], path: Path = PROCESSED_PATH,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return path


def collect_insee_salaan(
    zip_path: Path = RAW_ZIP, save: bool = True, min_effectif: float = 100.0,
) -> list[dict[str, Any]]:
    """Pipeline complet : unzip + stream agrégation + save."""
    if not zip_path.exists():
        raise FileNotFoundError(
            f"ZIP INSEE SALAAN absent : {zip_path}. "
            "Upload requis (cf docs/TODO_MATTEO_APIS.md §6)."
        )
    print(f"  [insee_salaan] Agrégation de {zip_path} (streaming CSV)…")
    import time
    t0 = time.time()
    entries = aggregate_salaan(zip_path=zip_path, min_effectif=min_effectif)
    print(f"  [insee_salaan] {len(entries):,} stats agrégées en {time.time()-t0:.1f}s")

    if save:
        p = save_processed(entries)
        print(f"  [insee_salaan] saved → {p}")
    return entries


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-effectif", type=float, default=100.0)
    args = parser.parse_args()
    entries = collect_insee_salaan(min_effectif=args.min_effectif)
    print(f"  [insee_salaan] total : {len(entries):,} entrées")
