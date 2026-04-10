import json
import re
from pathlib import Path
import requests


AUTH_URL = "https://api.opendata.onisep.fr/api/1.0/login"
FORMATIONS_DATASET = "5fa591127f501"
SEARCH_URL = f"https://api.opendata.onisep.fr/api/1.0/dataset/{FORMATIONS_DATASET}/search"


# ---------------------------------------------------------------------------
# School-name extractor
# ---------------------------------------------------------------------------

# Patterns ordered from most specific to most general.
# The extractor returns the FIRST match. No match → None.
_SCHOOL_PATTERNS = [
    # Parens at end: "(EPITA)", "(ISEN Lille)"
    (r"\(([^)]{2,60})\)\s*$", 1),
    # "de l'X": "de l'ENSIBS", "de l'école polytechnique"
    (r"\bde\s+l['']([A-ZÉÈÊÀÂÇ][A-Za-zéèêàâçÉÈÊÀÂÇ\s\-']{2,60}?)(?:\s+(?:spécialité|mention|parcours|voie|option)\b|$|,)", 1),
    # "de X" where X starts with uppercase: "de Télécom Nancy", "de Polytech Grenoble"
    (r"\bde\s+([A-ZÉÈÊ][A-Za-zéèêàâç\s\-']{2,60}?)(?:\s+de\s+l['']|\s+(?:spécialité|mention|parcours|voie|option)\b|$|,)", 1),
]


def extract_school_from_formation_name(name: str) -> str | None:
    """Best-effort extraction of the school name from an ONISEP formation title.

    Returns None when no school can be confidently extracted (e.g., generic
    diploma titles like 'expert en cybersécurité des systèmes d'information').
    """
    if not name:
        return None
    for pattern, group in _SCHOOL_PATTERNS:
        m = re.search(pattern, name)
        if m:
            return m.group(group).strip()
    return None


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def authenticate(email: str, password: str) -> str:
    resp = requests.post(AUTH_URL, data={"email": email, "password": password}, timeout=30)
    resp.raise_for_status()
    return resp.json()["token"]


def fetch_formations(token: str, app_id: str, query: str, size: int = 500) -> list[dict]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Application-ID": app_id,
    }
    params = {"q": query, "size": size}
    resp = requests.get(SEARCH_URL, headers=headers, params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data.get("results", [])


def save_raw(data: list[dict], path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _fetch_formations_public(query: str, size: int = 500) -> list[dict]:
    """Fetch formations without authentication (public endpoint, no Application-ID required)."""
    params = {"q": query, "size": size}
    resp = requests.get(SEARCH_URL, params=params, timeout=60)
    resp.raise_for_status()
    return resp.json().get("results", [])


# ---------------------------------------------------------------------------
# Niveau mapping
# ---------------------------------------------------------------------------

def _map_onisep_niveau(niveau_sortie: str | None) -> str | None:
    """Map ONISEP's 'bac + N' format to our 'bac+N' internal format."""
    if not niveau_sortie:
        return None
    # ONISEP uses "bac + 2", "bac + 3", "bac + 5", "bac + 8"
    normalized = niveau_sortie.replace(" ", "").lower()
    if normalized in ("bac+2", "bac+3", "bac+5", "bac+8"):
        return normalized
    return None


# ---------------------------------------------------------------------------
# Main collector
# ---------------------------------------------------------------------------

def collect_onisep_fiches(email: str, password: str, app_id: str) -> list[dict]:
    """Fetch and normalize ONISEP formations for OrientIA's two domains.

    ONISEP returns formation-type records (not per-school instances), so
    etablissement is extracted heuristically from the formation name.
    Fiches where extraction fails still carry the formation name, RNCP,
    and level — they can still contribute to the benchmark as generic
    diploma references.
    """
    token = authenticate(email, password)
    fiches = []
    seen_signatures = set()

    for domain, query in [
        ("cyber", "cybersécurité"),
        ("data_ia", "intelligence artificielle"),
        ("data_ia", "data science"),
    ]:
        results = fetch_formations(token, app_id, query, size=500)
        for r in results:
            nom = r.get("libelle_formation_principal", "").strip()
            if not nom:
                continue
            etab = extract_school_from_formation_name(nom) or ""
            sig = (nom, etab)
            if sig in seen_signatures:
                continue
            seen_signatures.add(sig)

            fiches.append({
                "source": "onisep",
                "domaine": domain,
                "nom": nom,
                "etablissement": etab,
                "ville": "",  # ONISEP formations-dataset has no city field
                "rncp": r.get("code_rncp") or None,
                "url_onisep": r.get("url_et_id_onisep") or None,
                "type_diplome": r.get("libelle_type_formation") or None,
                "duree": r.get("duree") or None,
                "tutelle": r.get("tutelle") or None,
                "niveau": _map_onisep_niveau(r.get("niveau_de_sortie_indicatif")),
                "statut": None,  # to be inferred from tutelle or establishment later
            })
    return fiches
