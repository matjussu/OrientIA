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

_DOMAIN_QUERIES = [
    # cyber
    ("cyber", "cybersécurité"),
    # data / IA
    ("data_ia", "intelligence artificielle"),
    ("data_ia", "data science"),
    # santé — added in quality-gaps fix. Multi-query because ONISEP doesn't
    # expose a single "health" category; each query returns at most ~500 results.
    ("sante", "médecine"),
    ("sante", "pharmacie"),
    ("sante", "maïeutique"),
    ("sante", "infirmier"),
    ("sante", "kinésithérapie"),
    ("sante", "orthophonie"),
    ("sante", "ergothérapie"),
    ("sante", "podologie"),
    ("sante", "imagerie médicale"),
    ("sante", "audioprothèse"),
    ("sante", "orthoptie"),
    ("sante", "psychomotricité"),
]


def _normalize_record(r: dict, domain: str) -> dict | None:
    """Shared normalization between authenticated and public fetchers."""
    nom = r.get("libelle_formation_principal", "").strip()
    if not nom:
        return None
    etab = extract_school_from_formation_name(nom) or ""
    return {
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
    }


def collect_onisep_fiches(email: str, password: str, app_id: str) -> list[dict]:
    """Fetch and normalize ONISEP formations for OrientIA's three domains
    (cyber, data_ia, sante) via the authenticated endpoint.

    ONISEP returns formation-type records (not per-school instances), so
    etablissement is extracted heuristically from the formation name.
    Fiches where extraction fails still carry the formation name, RNCP,
    and level — they can still contribute to the benchmark as generic
    diploma references.
    """
    token = authenticate(email, password)
    fiches = []
    seen_signatures = set()

    for domain, query in _DOMAIN_QUERIES:
        results = fetch_formations(token, app_id, query, size=500)
        for r in results:
            norm = _normalize_record(r, domain)
            if norm is None:
                continue
            sig = (norm["nom"], norm["etablissement"])
            if sig in seen_signatures:
                continue
            seen_signatures.add(sig)
            fiches.append(norm)
    return fiches


def collect_onisep_fiches_public(delay_s: float = 3.0) -> list[dict]:
    """Fetch all three domains via the public endpoint (no authentication).

    Fallback path when credentials aren't available. The public endpoint
    has the same schema but is rate-limited (429 after ~5 fast queries).
    `delay_s` controls inter-query pacing — 3s works empirically.
    """
    import time
    fiches = []
    seen_signatures = set()
    for i, (domain, query) in enumerate(_DOMAIN_QUERIES):
        if i > 0:
            time.sleep(delay_s)
        try:
            results = _fetch_formations_public(query, size=500)
        except Exception as e:
            # One failed query shouldn't kill the whole collection
            print(f"[onisep] public fetch failed for {domain}/{query}: {e}")
            continue
        for r in results:
            norm = _normalize_record(r, domain)
            if norm is None:
                continue
            sig = (norm["nom"], norm["etablissement"])
            if sig in seen_signatures:
                continue
            seen_signatures.add(sig)
            fiches.append(norm)
        print(f"[onisep] {domain}/{query}: {len(results)} fetched, running total={len(fiches)}")
    return fiches
