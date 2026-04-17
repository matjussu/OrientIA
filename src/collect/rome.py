from pathlib import Path
import pandas as pd


# ROME 4.0 codes relevant to OrientIA's two domains.
# Verified against France Travail ROME 4.0 open data (2026-04 release,
# 1584 codes total). These are the codes that will show up as "débouchés"
# for formations in each domain.
RELEVANT_ROME_CODES = {
    # Cybersécurité — 9 direct codes
    "M1812": "Responsable de la Sécurité des Systèmes d'Information (RSSI)",
    "M1817": "Administrateur / Administratrice sécurité informatique",
    "M1819": "Ingénieur / Ingénieure sécurité informatique",
    "M1844": "Analyste en cybersécurité",
    "M1846": "Ingénieur / Ingénieure Cybersécurité Datacenter",
    "M1856": "Expert / Experte en cybersécurité",
    "M1863": "Evaluateur / Evaluatrice sécurité des systèmes et produits informatiques",
    "M1882": "Architecte sécurité informatique",
    "M1884": "Ingénieur / Ingénieure systèmes, réseaux et sécurité informatique",
    # Data / IA — 6 direct codes
    "M1405": "Data scientist",
    "M1419": "Data analyst",
    "M1423": "Chief Data Officer",
    "M1811": "Data engineer",
    "M1868": "Architecte base de données",
    "M1894": "Gestionnaire de base de données",
    # Santé — 10 codes J1xxx couvrant les principaux métiers paramédicaux
    # et médicaux (source : Pôle Emploi / France Travail ROME 4.0, 2026).
    # Intentionally broad so a "santé" fiche Parcoursup (qu'elle soit PASS,
    # IFSI, ou formation paramédicale spécifique) surface une gamme réaliste
    # de métiers accessibles après la formation.
    "J1102": "Médecin généraliste / Médecin spécialiste",
    "J1103": "Médecin de prévention et santé publique",
    "J1104": "Sage-femme",
    "J1201": "Professions paramédicales (aide-soignant, auxiliaire de puériculture)",
    "J1304": "Pharmacien / Préparateur en pharmacie",
    "J1401": "Audioprothésiste / Opticien / Orthoptiste / Podologue",
    "J1501": "Infirmier / Infirmière diplômé(e) d'État",
    "J1502": "Cadre de santé / Directeur de soins",
    "J1505": "Kinésithérapeute / Ergothérapeute",
    "J1506": "Orthophoniste",
}


_DOMAIN_CODES = {
    "cyber": ["M1812", "M1817", "M1819", "M1844", "M1846", "M1856", "M1863", "M1882", "M1884"],
    "data_ia": ["M1405", "M1419", "M1423", "M1811", "M1868", "M1894"],
    "sante": ["J1102", "J1103", "J1104", "J1201", "J1304", "J1401",
              "J1501", "J1502", "J1505", "J1506"],
}


def load_rome_job_titles(path: str | Path) -> dict[str, str]:
    """Load the ROME 4.0 canonical code→libellé mapping.

    Expects the unix_referentiel_code_rome_v460_utf8.csv file from the
    official France Travail ROME 4.0 open data ZIP. CSV uses comma
    separator and the canonical column name is `libelle_rome`.
    """
    df = pd.read_csv(path, sep=",", encoding="utf-8")
    return dict(zip(df["code_rome"], df["libelle_rome"]))


def get_debouches_for_domain(domain: str) -> list[dict]:
    """Return the list of ROME codes and canonical labels for a domain.

    Uses the hard-coded RELEVANT_ROME_CODES mapping (verified against ROME 4.0)
    rather than filtering the full CSV at runtime. This keeps the debouches
    stable and reproducible across benchmark runs.
    """
    codes = _DOMAIN_CODES[domain]
    return [{"code_rome": c, "libelle": RELEVANT_ROME_CODES[c]} for c in codes]
