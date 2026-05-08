"""Construit `doctorat_corpus.json` depuis le RAW IP-DOC MESR.

Phase B finalisation du plan corpus v5 (gap identifié post-Phase A.4).
Source RAW : `data/processed/ip_doc_doctorat.json` (240 stats agrégées
d'insertion doctorat par discipline × année × situation × genre).

## Granularité

Chaque record source = `(discipline_principale × discipline_agregee ×
annee_cohorte × situation × genre)`. Les chiffres exposés :
- taux_insertion (à 12 ou 24 mois selon situation)
- part_cadre, part_temps_plein, part_stable
- part_secteur_academique vs RD privée vs étranger
- salaires Q1 / médian / Q3 (mensuel net)
- nb_repondants (taille échantillon)

## Domain et identifiant

`domain = "insertion_pro"` (cohabite avec InserSup qui a aussi
`domain=insertion_pro`). Le `text` raconte clairement la spécificité
"Insertion doctorat" pour ne pas confondre côté retrieval.

`id` = `doctorat:<slug_discipline>:<annee>:<genre>` pour stabilité.

## Schéma de sortie

```json
{
  "id": "doctorat:chimie-sciences-materiaux:2014:hommes",
  "domain": "insertion_pro",
  "source": "ip_doc_doctorat",
  "discipline_agregee": "Sciences et leurs interactions",
  "discipline_principale": "Chimie et sciences des matériaux",
  "niveau": "bac+8",
  "annee_cohorte": "2014",
  "situation": "12 mois après le diplôme",
  "genre": "hommes",
  "nb_repondants": 452,
  "taux_insertion": 0.81,
  "part_cadre": 0.94,
  "part_temps_plein": 0.97,
  "part_stable": 0.46,
  "salaire_net_median_mensuel": 2125,
  "text": "Insertion doctorat (MESR IP-DOC) — Chimie ... | n=452 | taux 81% ...",
  "provenance": {
    "tier": "tier_1",
    "source_label": "MESR — insertion doctorat",
    "source_url": "https://data.enseignementsup-recherche.gouv.fr/..."
  }
}
```

Sortie : `data/processed/doctorat_corpus.json` (~240 records).
"""
from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any


RAW_PATH = Path("data/processed/ip_doc_doctorat.json")
CORPUS_PATH = Path("data/processed/doctorat_corpus.json")

_TEXT_MAX_CHARS = 1500
_PROVENANCE_BASE = {
    "tier": "tier_1",
    "source_label": "MESR — insertion doctorat",
    "source_url": (
        "https://data.enseignementsup-recherche.gouv.fr/explore/dataset/"
        "fr-esr-insertion-professionnelle-des-doctorants-et-docteurs-en-france/"
    ),
}


def _slug(text: str | None) -> str:
    if not text:
        return "unknown"
    s = "".join(
        c for c in unicodedata.normalize("NFKD", str(text))
        if not unicodedata.combining(c)
    ).lower()
    out = []
    prev_dash = False
    for c in s:
        if c.isalnum():
            out.append(c)
            prev_dash = False
        else:
            if not prev_dash:
                out.append("-")
                prev_dash = True
    return "".join(out).strip("-")[:50]


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
        if f != f or f == float("inf") or f == float("-inf"):
            return None
        return f
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _format_pct(val: float | None) -> str:
    """0.81 → 81%."""
    if val is None:
        return "n/d"
    return f"{int(round(val * 100))}%"


def _build_text(record: dict[str, Any]) -> str:
    """Texte retrievable narratif."""
    parts: list[str] = []

    disc_agr = _safe_str(record.get("discipline_agregee"))
    disc_pr = _safe_str(record.get("discipline_principale"))
    annee = _safe_str(record.get("annee"))
    situation = _safe_str(record.get("situation"))
    genre = _safe_str(record.get("genre"))

    header = f"Insertion doctorat (MESR IP-DOC)"
    if disc_pr:
        header += f" — {disc_pr}"
    if disc_agr and disc_agr != disc_pr:
        header += f" ({disc_agr})"
    parts.append(header)

    if annee or situation:
        bits = []
        if annee:
            bits.append(f"cohorte {annee}")
        if situation:
            bits.append(situation)
        parts.append(", ".join(bits))

    if genre and genre.lower() not in ("ensemble", ""):
        parts.append(f"sous-population : {genre}")

    nb = _safe_int(record.get("nb_repondants"))
    if nb is not None:
        parts.append(f"n={nb} répondants")

    chiffres_bits = []
    taux = _safe_float(record.get("taux_insertion"))
    if taux is not None:
        chiffres_bits.append(f"taux d'insertion {_format_pct(taux)}")
    cadre = _safe_float(record.get("part_cadre"))
    if cadre is not None:
        chiffres_bits.append(f"part cadre {_format_pct(cadre)}")
    stable = _safe_float(record.get("part_stable"))
    if stable is not None:
        chiffres_bits.append(f"part emploi stable {_format_pct(stable)}")
    temps_plein = _safe_float(record.get("part_temps_plein"))
    if temps_plein is not None:
        chiffres_bits.append(f"part temps plein {_format_pct(temps_plein)}")
    sal_med = _safe_int(record.get("salaire_net_median_mensuel"))
    if sal_med is not None:
        chiffres_bits.append(f"salaire net médian {sal_med}€/mois")
    if chiffres_bits:
        parts.append(" | ".join(chiffres_bits))

    # Répartition secteur
    sec_bits = []
    acad = _safe_float(record.get("part_secteur_academique"))
    if acad is not None:
        sec_bits.append(f"académique {_format_pct(acad)}")
    rd_priv = _safe_float(record.get("part_rd_privee"))
    if rd_priv is not None:
        sec_bits.append(f"R&D privée {_format_pct(rd_priv)}")
    pub_hors = _safe_float(record.get("part_public_hors_academique"))
    if pub_hors is not None:
        sec_bits.append(f"public hors académique {_format_pct(pub_hors)}")
    etr = _safe_float(record.get("part_emploi_etranger"))
    if etr is not None:
        sec_bits.append(f"étranger {_format_pct(etr)}")
    if sec_bits:
        parts.append("Secteurs d'emploi : " + ", ".join(sec_bits))

    text = " | ".join(parts)
    if len(text) > _TEXT_MAX_CHARS:
        text = text[:_TEXT_MAX_CHARS].rsplit(" ", 1)[0] + "…"
    return text


def normalize_to_corpus(record: dict[str, Any]) -> dict[str, Any] | None:
    """Convertit une fiche RAW IP-DOC en record corpus retrievable.

    Retourne None pour les records malformés (sans discipline_principale).
    """
    if not isinstance(record, dict):
        return None
    disc_pr = _safe_str(record.get("discipline_principale"))
    if not disc_pr:
        return None

    annee = _safe_str(record.get("annee")) or "unknown"
    genre = _safe_str(record.get("genre")) or "ensemble"
    situation = _safe_str(record.get("situation")) or "unknown"
    # Inclure situation (12m vs 24m vs autre) pour éviter collisions ID
    fiche_id = f"doctorat:{_slug(disc_pr)}:{annee}:{_slug(genre)}:{_slug(situation)}"

    out: dict[str, Any] = {
        "id": fiche_id,
        "domain": "insertion_pro",
        "source": "ip_doc_doctorat",
        "discipline_agregee": _safe_str(record.get("discipline_agregee")) or None,
        "discipline_principale": disc_pr,
        "domaine_orientia": _safe_str(record.get("domaine_orientia")) or None,
        "niveau": _safe_str(record.get("niveau_orientia")) or "bac+8",
        "annee_cohorte": annee,
        "situation": _safe_str(record.get("situation")) or None,
        "genre": genre,
        "nb_repondants": _safe_int(record.get("nb_repondants")),
        "taux_insertion": _safe_float(record.get("taux_insertion")),
        "part_cadre": _safe_float(record.get("part_cadre")),
        "part_temps_plein": _safe_float(record.get("part_temps_plein")),
        "part_stable": _safe_float(record.get("part_stable")),
        "part_secteur_academique": _safe_float(record.get("part_secteur_academique")),
        "part_public_hors_academique": _safe_float(record.get("part_public_hors_academique")),
        "part_rd_privee": _safe_float(record.get("part_rd_privee")),
        "part_prive_hors_rd": _safe_float(record.get("part_prive_hors_rd")),
        "part_emploi_etranger": _safe_float(record.get("part_emploi_etranger")),
        "salaire_net_q1_mensuel": _safe_int(record.get("salaire_net_q1_mensuel")),
        "salaire_net_median_mensuel": _safe_int(record.get("salaire_net_median_mensuel")),
        "salaire_net_q3_mensuel": _safe_int(record.get("salaire_net_q3_mensuel")),
        "salaire_brut_median_annuel": _safe_int(record.get("salaire_brut_median_annuel")),
        "provenance": dict(_PROVENANCE_BASE),
    }
    out["text"] = _build_text(record)
    return out


def build_corpus(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map normalize, dédup par id, tri stable."""
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
    print(f"[DOCTORAT-CORPUS] {len(raw)} → {len(corpus)} records → {CORPUS_PATH}")
    avg = sum(len(c["text"]) for c in corpus) // max(1, len(corpus))
    n_with_taux = sum(1 for c in corpus if c.get("taux_insertion") is not None)
    print(f"[DOCTORAT-CORPUS] longueur text moyenne : {avg} chars")
    print(f"[DOCTORAT-CORPUS] avec taux_insertion : {n_with_taux}/{len(corpus)}")


if __name__ == "__main__":  # pragma: no cover
    main()
