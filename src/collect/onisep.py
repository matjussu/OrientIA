import json
from pathlib import Path
import requests


AUTH_URL = "https://api.opendata.onisep.fr/api/1.0/login"
FORMATIONS_DATASET = "5fa591127f501"
SEARCH_URL = f"https://api.opendata.onisep.fr/api/1.0/dataset/{FORMATIONS_DATASET}/search"


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


def collect_onisep_fiches(email: str, password: str, app_id: str) -> list[dict]:
    # Attempt authenticated fetch first; fall back to public endpoint if
    # Application-ID is not yet registered in the ONISEP developer portal.
    token = authenticate(email, password)
    fiches = []
    for domain, query in [
        ("cyber", "cybersécurité"),
        ("data_ia", "intelligence artificielle"),
        ("data_ia", "data science"),
    ]:
        try:
            results = fetch_formations(token, app_id, query)
        except Exception:
            # Application-ID not registered: fall back to public endpoint
            results = _fetch_formations_public(query)
        for r in results:
            fiches.append({
                "source": "onisep",
                "domaine": domain,
                "nom": r.get("libelle_formation_principal") or r.get("nom") or "",
                "etablissement": r.get("nom_etab") or r.get("etablissement") or "",
                "ville": r.get("lib_com") or r.get("ville") or "",
                "rncp": r.get("code_rncp") or None,
                "url_onisep": r.get("url_onisep") or r.get("url") or None,
                "type_diplome": r.get("type_formation_court") or None,
                "statut": r.get("statut") or None,
            })
    return fiches
