"""Construit `rome_metier_corpus.json` retrievable depuis les fiches ROME 4.0.

Phase A.2 du plan corpus v5 (ADR-057). Source RAW :
`data/raw/rome_api/fiches_metiers/*.json` — 1 584 fiches téléchargées le
2026-04-23 via `scripts/ingest_rome_fiches.py` (status "done").

Distinction avec `build_metiers_corpus.py` :

- `build_metiers_corpus.py` traite les fiches IDEO ONISEP (1 075 entrées
  éditorialisées, axée découverte / orientation : accroche, format_court,
  niveau d'accès, secteurs, centres d'intérêt). `domain="metier"`.
- `build_rome_corpus.py` (ce module) traite les fiches France Travail
  ROME 4.0 (1 584 entrées API officielles, axée compétences techniques :
  groupes de compétences mobilisées par enjeu + savoirs par catégorie).
  `domain="metier_detail"`.

Les 2 sources sont **complémentaires** : ONISEP raconte le métier au
lycéen, ROME 4.0 décrit ce qu'on y fait techniquement.

## Schéma de sortie

```json
{
  "id": "rome_metier:A1101",
  "domain": "metier_detail",
  "source": "rome_api_v4",
  "code_rome": "A1101",
  "libelle_metier": "Conducteur / Conductrice d'engins agricoles",
  "obsolete": false,
  "competences_par_enjeu": [
    {"enjeu": "Aménagement", "competences": ["Contrôler ...", ...]}
  ],
  "savoirs_par_categorie": [
    {"categorie": "Domaines d'expertise", "savoirs": ["Agronomie", ...]}
  ],
  "text": "Métier ROME A1101 : ... | Compétences ... | Savoirs ...",
  "url": "https://candidat.francetravail.fr/metierscope/fiche-metier/A1101",
  "provenance": {
    "tier": "tier_1",
    "source_label": "France Travail ROME 4.0",
    "source_url": "https://francetravail.io/data/api/rome-4-0",
    "last_updated": "2026-04-23"
  }
}
```

Sortie : `data/processed/rome_metier_corpus.json`
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROME_RAW_DIR = Path("data/raw/rome_api/fiches_metiers")
ROME_CORPUS_PATH = Path("data/processed/rome_metier_corpus.json")
ROME_PROGRESS_PATH = Path("data/raw/rome_api/fiches_metiers_progress.json")

# Cap aligné sur build_metiers_corpus.py — limite tokens Mistral pratique.
_TEXT_MAX_CHARS = 2500
# Limites de troncature pour ne pas saturer le narratif text.
_MAX_COMPETENCES_PAR_ENJEU = 6   # 6 compétences par enjeu max dans le text
_MAX_ENJEUX = 4                  # 4 enjeux max dans le text
_MAX_SAVOIRS_PAR_CATEGORIE = 5   # 5 savoirs par catégorie max
_MAX_CATEGORIES = 3              # 3 catégories de savoirs max

_PROVENANCE_BASE = {
    "tier": "tier_1",
    "source_label": "France Travail ROME 4.0",
    "source_url": "https://francetravail.io/data/api/rome-4-0",
}


def _safe_str(value: Any) -> str:
    """Strip et retourne string non-vide ou ''."""
    if value is None:
        return ""
    return str(value).strip()


def _extract_competences(groupes: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Transforme `groupesCompetencesMobilisees` en liste structurée propre.

    Format input ROME 4.0 :
        [
          {"enjeu": {"code": "15", "libelle": "Aménagement"},
           "competences": [{"type": "...", "code": "...", "libelle": "..."}]}
        ]

    Format output :
        [{"enjeu": "Aménagement", "competences": ["lib1", "lib2", ...]}]
    """
    if not isinstance(groupes, list):
        return []
    out: list[dict[str, Any]] = []
    for g in groupes:
        if not isinstance(g, dict):
            continue
        enjeu = (g.get("enjeu") or {}).get("libelle") if isinstance(g.get("enjeu"), dict) else None
        enjeu_lib = _safe_str(enjeu)
        if not enjeu_lib:
            continue
        comp_libs = []
        for c in g.get("competences") or []:
            if isinstance(c, dict):
                lib = _safe_str(c.get("libelle"))
                if lib:
                    comp_libs.append(lib)
        if comp_libs:
            out.append({"enjeu": enjeu_lib, "competences": comp_libs})
    return out


def _extract_savoirs(groupes: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Transforme `groupesSavoirs` en liste structurée propre.

    Format input ROME 4.0 :
        [
          {"categorieSavoirs": {"code": "2", "libelle": "Domaines d'expertise"},
           "savoirs": [{"type": "SAVOIR", "code": "...", "libelle": "..."}]}
        ]

    Format output :
        [{"categorie": "Domaines d'expertise", "savoirs": ["Agronomie", ...]}]
    """
    if not isinstance(groupes, list):
        return []
    out: list[dict[str, Any]] = []
    for g in groupes:
        if not isinstance(g, dict):
            continue
        cat = (g.get("categorieSavoirs") or {}).get("libelle") if isinstance(g.get("categorieSavoirs"), dict) else None
        cat_lib = _safe_str(cat)
        if not cat_lib:
            continue
        savoir_libs = []
        for s in g.get("savoirs") or []:
            if isinstance(s, dict):
                lib = _safe_str(s.get("libelle"))
                if lib:
                    savoir_libs.append(lib)
        if savoir_libs:
            out.append({"categorie": cat_lib, "savoirs": savoir_libs})
    return out


def build_text(fiche: dict[str, Any]) -> str:
    """Construit le texte retrievable narratif depuis une fiche ROME 4.0 normalisée.

    Composition (segments séparés par ` | `, capé à `_TEXT_MAX_CHARS`) :
    - Métier ROME <code> : <libelle>
    - Compétences par enjeu : <enjeu>: c1, c2, c3 ; <enjeu>: c4, c5
    - Savoirs : <catégorie>: s1, s2 ; <catégorie>: s3, s4
    """
    parts: list[str] = []

    code = _safe_str(fiche.get("code_rome"))
    libelle = _safe_str(fiche.get("libelle_metier"))
    if code and libelle:
        parts.append(f"Métier ROME {code} : {libelle}")
    elif libelle:
        parts.append(f"Métier : {libelle}")

    competences_par_enjeu = fiche.get("competences_par_enjeu") or []
    if competences_par_enjeu:
        chunks = []
        for grp in competences_par_enjeu[:_MAX_ENJEUX]:
            enjeu = grp.get("enjeu", "")
            comps = grp.get("competences", [])[:_MAX_COMPETENCES_PAR_ENJEU]
            if enjeu and comps:
                chunks.append(f"{enjeu} ({', '.join(comps)})")
        if chunks:
            parts.append("Compétences par enjeu : " + " ; ".join(chunks))

    savoirs_par_cat = fiche.get("savoirs_par_categorie") or []
    if savoirs_par_cat:
        chunks = []
        for grp in savoirs_par_cat[:_MAX_CATEGORIES]:
            cat = grp.get("categorie", "")
            savoirs = grp.get("savoirs", [])[:_MAX_SAVOIRS_PAR_CATEGORIE]
            if cat and savoirs:
                chunks.append(f"{cat} ({', '.join(savoirs)})")
        if chunks:
            parts.append("Savoirs : " + " ; ".join(chunks))

    text = " | ".join(parts)
    if len(text) > _TEXT_MAX_CHARS:
        # Coupe au dernier espace pour éviter de couper un mot
        text = text[:_TEXT_MAX_CHARS].rsplit(" ", 1)[0] + "…"
    return text


def normalize_to_corpus(
    fiche: dict[str, Any],
    last_updated: str | None = None,
) -> dict[str, Any] | None:
    """Convertit une fiche ROME 4.0 RAW en record corpus retrievable.

    Returns None pour les fiches `obsolete=True` ou sans libellé métier
    (filtrage qualité — règle "zéro tolérance erreurs" feedback_data_integrity).

    Args:
        fiche: dict RAW depuis l'API ROME 4.0 (un fichier de
            `data/raw/rome_api/fiches_metiers/`).
        last_updated: date YYYY-MM-DD du download (depuis progress.json).
            Si None, omis du provenance.

    Returns:
        Record corpus avec schema décrit en module docstring, ou None.
    """
    if not isinstance(fiche, dict):
        return None
    if fiche.get("obsolete") is True:
        return None

    metier = fiche.get("metier") or {}
    if not isinstance(metier, dict):
        return None

    code = _safe_str(fiche.get("code")) or _safe_str(metier.get("code"))
    libelle = _safe_str(metier.get("libelle"))
    if not code or not libelle:
        return None

    competences = _extract_competences(fiche.get("groupesCompetencesMobilisees"))
    savoirs = _extract_savoirs(fiche.get("groupesSavoirs"))

    record = {
        "id": f"rome_metier:{code}",
        "domain": "metier_detail",
        "source": "rome_api_v4",
        "code_rome": code,
        "libelle_metier": libelle,
        "obsolete": False,
        "competences_par_enjeu": competences,
        "savoirs_par_categorie": savoirs,
        "url": f"https://candidat.francetravail.fr/metierscope/fiche-metier/{code}",
        "provenance": dict(_PROVENANCE_BASE),
    }
    if last_updated:
        record["provenance"]["last_updated"] = last_updated
    # Le `text` doit être construit APRÈS le record car il s'appuie sur les
    # champs structurés (competences_par_enjeu, savoirs_par_categorie).
    record["text"] = build_text(record)
    return record


def load_rome_fiches(directory: Path | None = None) -> list[dict[str, Any]]:
    """Charge toutes les fiches RAW depuis `data/raw/rome_api/fiches_metiers/`.

    Sort sur le nom de fichier pour idempotence garantie (ordre déterministe).
    """
    target = directory or ROME_RAW_DIR
    if not target.exists():
        return []
    out = []
    for path in sorted(target.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                out.append(data)
        except (json.JSONDecodeError, OSError):
            continue
    return out


def load_progress_date(progress_path: Path | None = None) -> str | None:
    """Récupère la date 'last_updated' depuis le progress.json (mtime fallback).

    Le fichier progress.json contient `{"status": "done", "ok": N, ...}`
    sans timestamp explicite. On utilise le mtime du fichier comme fallback.
    """
    target = progress_path or ROME_PROGRESS_PATH
    if not target.exists():
        return None
    try:
        from datetime import datetime, timezone
        mtime = target.stat().st_mtime
        return datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%d")
    except OSError:
        return None


def build_corpus(
    fiches_raw: list[dict[str, Any]],
    last_updated: str | None = None,
) -> list[dict[str, Any]]:
    """Map normalize sur tous les RAW. Skip obsoletes / malformés.

    Idempotent : tri final par `id` (== code ROME) garantit ordre stable.
    """
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for f in fiches_raw:
        record = normalize_to_corpus(f, last_updated=last_updated)
        if record is None:
            continue
        if record["id"] in seen:
            continue
        seen.add(record["id"])
        out.append(record)
    out.sort(key=lambda r: r["id"])
    return out


def save_corpus(records: list[dict[str, Any]], path: Path | None = None) -> Path:
    """Écrit le corpus en JSON UTF-8 indenté pour idempotence."""
    target = path or ROME_CORPUS_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target


def main() -> None:  # pragma: no cover
    print(f"[ROME-CORPUS] loading raw from {ROME_RAW_DIR}")
    raw = load_rome_fiches()
    last_updated = load_progress_date()
    print(f"[ROME-CORPUS] {len(raw)} fiches RAW chargées (last_updated={last_updated})")
    corpus = build_corpus(raw, last_updated=last_updated)
    out = save_corpus(corpus)
    avg_text_len = sum(len(c["text"]) for c in corpus) // max(1, len(corpus))
    n_with_competences = sum(1 for c in corpus if c["competences_par_enjeu"])
    n_with_savoirs = sum(1 for c in corpus if c["savoirs_par_categorie"])
    print(f"[ROME-CORPUS] {len(corpus)} records → {out}")
    print(f"[ROME-CORPUS] longueur texte moyenne : {avg_text_len} chars")
    print(f"[ROME-CORPUS] avec compétences      : {n_with_competences}/{len(corpus)}")
    print(f"[ROME-CORPUS] avec savoirs          : {n_with_savoirs}/{len(corpus)}")


if __name__ == "__main__":  # pragma: no cover
    main()
