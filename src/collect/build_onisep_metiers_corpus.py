"""Construit `onisep_metiers_corpus.json` depuis le RAW ONISEP métiers.

Phase B finalisation du plan corpus v5 (gap identifié post-Phase A.4).
Source RAW : `data/processed/onisep_metiers.json` (1 518 fiches métiers
éditoriales ONISEP avec codes ROME, url, GFE, domaine, collection).

## Distinction avec les autres corpora métiers

- `metiers_corpus.json` (1 075 fiches) : IDEO ONISEP — fiches enrichies
  format_court / accroche / centres_interet. domain="metier".
- `rome_metier_corpus.json` (1 584 fiches) : France Travail ROME 4.0 —
  compétences détaillées par enjeu + savoirs. domain="metier_detail".
- `onisep_metiers_corpus.json` (ce module, 1 518 fiches) : catalogue ONISEP
  éditorial avec mapping codes ROME multiples + url ONISEP slug + GFE
  pédagogique. domain="metier" (cohabite avec IDEO mais granularité
  catalogue).

Les 3 sources sont **complémentaires** : IDEO décrit le métier au lycéen,
ROME 4.0 liste les compétences, ONISEP métiers fournit le catalogue
classifié (GFE + domaine + collection éditoriale).

## Schéma de sortie

```json
{
  "id": "onisep_metier:MET.782",
  "domain": "metier",
  "source": "onisep_metiers",
  "libelle": "accompagnant éducatif et social / accompagnante éducative et sociale",
  "codes_rome": ["K1301", "K1302"],
  "rome_libelles": ["Accompagnement médicosocial", "Assistance auprès d'adultes"],
  "url": "https://www.onisep.fr/http/redirection/metier/slug/MET.782",
  "gfe": "GFE R : santé, social, soins personnels",
  "domaine": "santé, social, sport/travail social",
  "publication": "Travail social",
  "collection": "Parcours",
  "annee": 2024,
  "text": "Métier ONISEP : ... | Codes ROME : K1301 (...), K1302 (...) | GFE : ... | Domaine : ...",
  "provenance": {
    "tier": "tier_1",
    "source_label": "ONISEP — métiers",
    "source_url": "https://www.onisep.fr/...",
    "last_updated": "2026-03-05"
  }
}
```

Sortie : `data/processed/onisep_metiers_corpus.json` (~1 518 fiches).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


RAW_PATH = Path("data/processed/onisep_metiers.json")
CORPUS_PATH = Path("data/processed/onisep_metiers_corpus.json")

_TEXT_MAX_CHARS = 1500
_PROVENANCE_BASE = {
    "tier": "tier_1",
    "source_label": "ONISEP — métiers",
}


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _extract_slug_from_url(url: str | None) -> str | None:
    """Extrait `MET.782` de `https://www.onisep.fr/.../slug/MET.782`."""
    if not url:
        return None
    m = re.search(r"slug/(MET\.\d+)", url)
    if m:
        return m.group(1)
    return None


def _extract_codes_rome(record: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Extrait (codes, libellés) depuis le bloc codes_rome."""
    raw = record.get("codes_rome") or []
    codes: list[str] = []
    libelles: list[str] = []
    for item in raw:
        if isinstance(item, dict):
            code = _safe_str(item.get("code"))
            libelle = _safe_str(item.get("libelle"))
            if code:
                codes.append(code)
                libelles.append(libelle or code)
    return codes, libelles


def _build_text(record: dict[str, Any], codes: list[str], rome_libelles: list[str]) -> str:
    """Texte retrievable narratif (cap _TEXT_MAX_CHARS)."""
    parts: list[str] = []
    libelle = _safe_str(record.get("libelle"))
    if libelle:
        parts.append(f"Métier ONISEP : {libelle}")

    if codes:
        rome_chunks = [
            f"{code} ({lib})" if lib else code
            for code, lib in zip(codes, rome_libelles)
        ]
        parts.append("Codes ROME : " + ", ".join(rome_chunks))

    gfe = _safe_str(record.get("gfe"))
    if gfe:
        parts.append(f"GFE : {gfe}")

    domaine = _safe_str(record.get("domaine"))
    if domaine:
        parts.append(f"Domaine : {domaine}")

    sous_domaine = _safe_str(record.get("sous_domaine"))
    if sous_domaine:
        parts.append(f"Sous-domaine : {sous_domaine}")

    publication = _safe_str(record.get("publication"))
    collection = _safe_str(record.get("collection"))
    annee = record.get("annee")
    if publication or collection or annee:
        bits = []
        if publication:
            bits.append(f"publication : {publication}")
        if collection:
            bits.append(f"collection : {collection}")
        if annee:
            bits.append(f"année : {annee}")
        parts.append("Édition ONISEP — " + ", ".join(bits))

    text = " | ".join(parts)
    if len(text) > _TEXT_MAX_CHARS:
        text = text[:_TEXT_MAX_CHARS].rsplit(" ", 1)[0] + "…"
    return text


def normalize_to_corpus(record: dict[str, Any]) -> dict[str, Any] | None:
    """Convertit une fiche RAW ONISEP métiers en record corpus retrievable.

    Retourne None pour les fiches malformées (libellé vide).
    """
    if not isinstance(record, dict):
        return None
    libelle = _safe_str(record.get("libelle"))
    if not libelle:
        return None

    url_onisep = _safe_str(record.get("url_onisep")) or None
    slug = _extract_slug_from_url(url_onisep)
    fiche_id = f"onisep_metier:{slug}" if slug else (
        f"onisep_metier:{libelle.lower().replace(' ', '_')[:60]}"
    )

    codes, rome_libelles = _extract_codes_rome(record)

    out: dict[str, Any] = {
        "id": fiche_id,
        "domain": "metier",
        "source": "onisep_metiers",
        "libelle": libelle,
        "codes_rome": codes,
        "rome_libelles": rome_libelles,
        "url": url_onisep,
        "gfe": _safe_str(record.get("gfe")) or None,
        "domaine": _safe_str(record.get("domaine")) or None,
        "sous_domaine": _safe_str(record.get("sous_domaine")) or None,
        "publication": _safe_str(record.get("publication")) or None,
        "collection": _safe_str(record.get("collection")) or None,
        "annee": record.get("annee"),
        "provenance": dict(_PROVENANCE_BASE),
    }
    # last_updated depuis date_de_modification si dispo
    last_mod = _safe_str(record.get("date_de_modification"))
    if last_mod:
        # Format DD/MM/YYYY → YYYY-MM-DD
        m = re.match(r"(\d{2})/(\d{2})/(\d{4})", last_mod)
        if m:
            out["provenance"]["last_updated"] = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    if url_onisep:
        out["provenance"]["source_url"] = url_onisep

    out["text"] = _build_text(record, codes, rome_libelles)
    return out


def build_corpus(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map normalize sur tous les records, dédup par id, tri stable."""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for r in records:
        rec = normalize_to_corpus(r)
        if rec is None:
            continue
        if rec["id"] in seen:
            continue
        seen.add(rec["id"])
        out.append(rec)
    out.sort(key=lambda r: r["id"])
    return out


def main() -> None:  # pragma: no cover
    raw = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    corpus = build_corpus(raw)
    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CORPUS_PATH.write_text(
        json.dumps(corpus, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[ONISEP-METIERS-CORPUS] {len(raw)} → {len(corpus)} records → {CORPUS_PATH}")
    avg = sum(len(c["text"]) for c in corpus) // max(1, len(corpus))
    n_with_rome = sum(1 for c in corpus if c["codes_rome"])
    print(f"[ONISEP-METIERS-CORPUS] longueur text moyenne : {avg} chars")
    print(f"[ONISEP-METIERS-CORPUS] avec codes ROME : {n_with_rome}/{len(corpus)}")


if __name__ == "__main__":  # pragma: no cover
    main()
