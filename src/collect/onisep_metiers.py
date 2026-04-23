"""ONISEP Ideo-Métiers — index national des métiers (D12 Axe 1 ADR-040).

Source : https://api.opendata.onisep.fr/downloads/5fa5949243f97/5fa5949243f97.json
Licence : Licence Ouverte Etalab 2.0 (redistribution autorisée).
Volume : ~1 518 métiers (distinct du dataset formations `5fa591127f501`).

**Particularité** : ce dataset est un **index métier grand-public** — il ne
contient PAS les journées types ni les salaires (ces infos sont dans les
fiches HTML ONISEP, scraping bloqué par Cloudflare). Sa valeur pour OrientIA
est le **mapping métier → codes ROME** pour enrichir les fiches formation
avec des libellés métiers humains (vs codes ROME bruts).

Scope ADR-040 D12 : complète la dimension "métiers" du scope élargi 17-25
ans, sans l'ambition des salaires (couverts par INSEE D14 + Céreq D11).

Accès public sans auth — activation immédiate, pas de signup Matteo requis.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import requests


DATA_URL = (
    "https://api.opendata.onisep.fr/downloads/5fa5949243f97/5fa5949243f97.json"
)
RAW_DIR = Path("data/raw/onisep_metiers")
PROCESSED_PATH = Path("data/processed/onisep_metiers.json")


def download_metiers(
    target_path: Optional[Path] = None,
    url: str = DATA_URL,
    session: Optional[requests.Session] = None,
    timeout: int = 60,
) -> Path:
    """Télécharge le JSON brut ONISEP métiers sur disque.

    Idempotent léger : si le fichier existe, comparer juste la taille HEAD.
    """
    sess = session or requests.Session()
    target = target_path or (RAW_DIR / "ideo_metiers.json")
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists():
        try:
            head = sess.head(url, timeout=30, allow_redirects=True)
            remote_size = int(head.headers.get("Content-Length", 0))
            if target.stat().st_size == remote_size and remote_size > 0:
                return target
        except Exception:
            pass  # fallback : re-download

    resp = sess.get(url, timeout=timeout, stream=True)
    resp.raise_for_status()
    with open(target, "wb") as f:
        for chunk in resp.iter_content(chunk_size=65536):
            if chunk:
                f.write(chunk)
    return target


def load_raw(path: Optional[Path] = None) -> list[dict[str, Any]]:
    """Lit le JSON téléchargé. Lève FileNotFoundError si absent."""
    target = path or (RAW_DIR / "ideo_metiers.json")
    return json.loads(target.read_text(encoding="utf-8"))


# --- Normalisation ---


def _parse_codes_rome(raw: str) -> list[str]:
    """ONISEP concatène les codes ROME avec ' | ' — split propre."""
    if not raw:
        return []
    return [c.strip() for c in raw.split("|") if c.strip()]


def _parse_libelles_rome(raw: str) -> list[str]:
    """Libellés ROME alignés sur codes (mêmes indices, séparateur identique)."""
    if not raw:
        return []
    return [lib.strip() for lib in raw.split("|") if lib.strip()]


def _parse_domaine(domaine_raw: str) -> dict[str, Optional[str]]:
    """Champ `domainesous-domaine` ONISEP = "Domaine > Sous-domaine" ou similaire.

    Normalise en dict {domaine, sous_domaine}.
    """
    if not domaine_raw:
        return {"domaine": None, "sous_domaine": None}
    parts = [p.strip() for p in domaine_raw.split(">")]
    if len(parts) >= 2:
        return {"domaine": parts[0], "sous_domaine": parts[1]}
    return {"domaine": parts[0], "sous_domaine": None}


def normalize_metier(record: dict[str, Any]) -> dict[str, Any]:
    """Transforme un record ONISEP métier en schéma OrientIA."""
    codes_rome = _parse_codes_rome(record.get("code_rome", ""))
    libelles_rome = _parse_libelles_rome(record.get("libelle_rome", ""))
    # Zip codes + libelles si nombres alignés, sinon juste les codes
    rome_pairs = []
    if codes_rome and len(codes_rome) == len(libelles_rome):
        rome_pairs = [{"code": c, "libelle": l} for c, l in zip(codes_rome, libelles_rome)]
    else:
        rome_pairs = [{"code": c, "libelle": None} for c in codes_rome]

    domaine_info = _parse_domaine(record.get("domainesous-domaine", ""))

    return {
        "source": "onisep_metiers",
        "type": "metier",
        "libelle": (record.get("libelle_metier") or "").strip(),
        "codes_rome": rome_pairs,
        "rome_link": record.get("lien_rome"),
        "url_onisep": record.get("lien_site_onisepfr"),
        "gfe": record.get("gfe"),  # Groupement Filière Emploi
        "domaine": domaine_info["domaine"],
        "sous_domaine": domaine_info["sous_domaine"],
        "publication": record.get("nom_publication"),
        "collection": record.get("collection"),
        "annee": record.get("annee"),
        "isbn": record.get("gencod"),
        "date_creation": record.get("date_creation"),
        "date_de_modification": record.get("date_de_modification"),
    }


def normalize_all(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_metier(r) for r in records]


def build_rome_to_metiers_index(
    metiers: list[dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    """Index inverse code ROME → liste des métiers ONISEP correspondants.

    Utilisé côté pipeline RAG pour enrichir les fiches formation : chaque
    fiche a des débouchés ROME ; on peut lister les libellés métier humains
    via cet index.
    """
    index: dict[str, list[dict[str, Any]]] = {}
    for m in metiers:
        for rome in m.get("codes_rome") or []:
            code = rome.get("code")
            if not code:
                continue
            index.setdefault(code, []).append(
                {"libelle": m["libelle"], "url_onisep": m.get("url_onisep")}
            )
    return index


def save_processed(
    normalized: list[dict[str, Any]], path: Path = PROCESSED_PATH
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return path


def collect_onisep_metiers(
    raw_path: Optional[Path] = None,
    download_if_missing: bool = True,
    save: bool = True,
) -> list[dict[str, Any]]:
    """Pipeline end-to-end : download (si absent) → parse → normalize → save."""
    target = raw_path or (RAW_DIR / "ideo_metiers.json")
    if not target.exists() and download_if_missing:
        download_metiers(target)
    if not target.exists():
        raise FileNotFoundError(
            f"ONISEP métiers JSON absent : {target}. "
            "Run `python -m src.collect.onisep_metiers` pour download."
        )
    raw = load_raw(target)
    normalized = normalize_all(raw)
    if save:
        path = save_processed(normalized)
        print(f"  [onisep_metiers] {len(normalized)} métiers normalisés → {path}")
    return normalized


if __name__ == "__main__":
    metiers = collect_onisep_metiers()
    print(f"  [onisep_metiers] total métiers : {len(metiers)}")
    # Quick stats
    from collections import Counter
    gfe_counts = Counter(m.get("gfe") for m in metiers if m.get("gfe"))
    print(f"  [onisep_metiers] top 5 GFE : {gfe_counts.most_common(5)}")
    index = build_rome_to_metiers_index(metiers)
    print(f"  [onisep_metiers] index ROME → métiers : {len(index)} codes ROME uniques")
