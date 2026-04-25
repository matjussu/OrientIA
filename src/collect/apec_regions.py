"""Construit `apec_regions_corpus.json` retrievable depuis le markdown
APEC régional 2026 (`docs/APEC_REGIONAL_SUMMARY.md`).

Source : synthèse APEC observatoire de l'emploi cadre, prévisions 2026,
12 régions métropolitaines hors IDF — pré-traitée par l'Agent Jarvis le
2026-04-24 (PRs #53 IDF + chantier APEC régional). Données stats verbatim
des panels APEC 2026 publiés en avril 2026.

## Stratégie multi-corpus (cohérente PR #56 metiers + PR #57 parcours)

Chaque région = 1 record retrievable. Plus :
- 1 record national overview (« France hexagonale 2026 »)
- 1 record observations cross-régions (synthèse comparative)

Total cible : ~13 records retrievables en plus du corpus formations.

Le markdown source (`docs/APEC_REGIONAL_SUMMARY.md`) est input read-only.
Le parser ne le modifie pas. La sortie `data/processed/apec_regions_corpus.json`
est commitée.

ADR-04X RAG multi-corpus à formaliser à la PR convergence multi_corpus.py.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


SUMMARY_MD_PATH = Path("docs/APEC_REGIONAL_SUMMARY.md")
CORPUS_PATH = Path("data/processed/apec_regions_corpus.json")


# ---------- Helpers parsing markdown ----------


_BULLET_RE = re.compile(
    r"^\s*-\s+\*\*([^*]+)\*\*(?:\s*\([^)]*\))?\s*:\s*(.+)$",
    re.MULTILINE,
)
_REGION_HEADER_RE = re.compile(r"^###\s+\d+\.\d+\s+(.+)$", re.MULTILINE)


def _strip_emphasis(text: str) -> str:
    """`**foo**` → `foo`, simple cleanup pour les valeurs."""
    return re.sub(r"\*\*([^*]+)\*\*", r"\1", text).strip()


def _bullets_to_dict(section: str) -> dict[str, str]:
    """Extrait `- **Label** : valeur` en dict {label: valeur} (HTML strip light)."""
    result: dict[str, str] = {}
    for match in _BULLET_RE.finditer(section):
        label = match.group(1).strip()
        value = _strip_emphasis(match.group(2))
        # Normaliser les clés (lowercase, _ pour espaces, accents conservés
        # car déjà human-readable)
        key = (
            label.lower()
            .replace(" ", "_")
            .replace("'", "_")
            .replace("(", "")
            .replace(")", "")
        )
        result[key] = value
    return result


def _split_regions(markdown: str) -> list[tuple[str, str]]:
    """Sépare le markdown en (nom_region, bloc_texte) par `### 2.X Nom`."""
    headers = list(_REGION_HEADER_RE.finditer(markdown))
    out: list[tuple[str, str]] = []
    for i, header in enumerate(headers):
        name = header.group(1).strip()
        start = header.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(markdown)
        block = markdown[start:end].strip()
        # Stop at next major section (`## 3. ...`)
        major_break = re.search(r"^---\s*$", block, re.MULTILINE)
        if major_break:
            block = block[: major_break.start()].strip()
        out.append((name, block))
    return out


def _extract_section_block(markdown: str, header_pattern: str) -> str:
    """Extrait le bloc texte sous un `## X. Title` ou `## TitleSimple`."""
    match = re.search(header_pattern, markdown, re.MULTILINE)
    if not match:
        return ""
    start = match.end()
    next_h2 = re.search(r"^##\s+", markdown[start:], re.MULTILINE)
    end = start + next_h2.start() if next_h2 else len(markdown)
    return markdown[start:end].strip()


# ---------- Builders ----------


_REGION_FIELDS = (
    "recrutements_2025",
    "prévision_2026",
    "créations_nettes_2025",
    "répartition_géographique",
    "top_5_fonctions_2025",
    "répartition_secteurs_2026",
    "contexte_régional",
)


def build_region_text(name: str, bullets: dict[str, str]) -> str:
    """Compose le texte retrievable pour une région."""
    parts = [f"Marché du travail cadres en {name} (panel APEC 2026)"]
    for key in _REGION_FIELDS:
        if key in bullets:
            label = key.replace("_", " ").capitalize()
            parts.append(f"{label} : {bullets[key]}")
    # Verbatim délégué APEC (citation contextuelle riche pour RAG)
    for key in bullets:
        if key.startswith("verbatim"):
            parts.append(f"Citation déléguée APEC : {bullets[key]}")
            break
    return " | ".join(parts)


def normalize_region(name: str, block: str) -> dict[str, Any]:
    """Convertit (nom_région, bloc markdown) en record corpus retrievable."""
    bullets = _bullets_to_dict(block)
    slug = (
        name.lower()
        .replace(" ", "-")
        .replace("'", "")
        .replace("&", "et")
        .replace(".", "")
    )
    slug = re.sub(r"[^a-z0-9-éèêëàâäîïôöùûüç]", "", slug)
    return {
        "id": f"apec_region:{slug}",
        "domain": "apec_region",
        "source": "apec_observatoire_emploi_cadre_2026",
        "region": name,
        "bullets": bullets,
        "text": build_region_text(name, bullets),
    }


def build_overview_record(markdown: str) -> dict[str, Any]:
    """Record agrégé pour la vue d'ensemble France hexagonale 2026."""
    block = _extract_section_block(
        markdown, r"^##\s+1\.\s+Vue d['\u2019]ensemble.*$"
    )
    bullets = _bullets_to_dict(block) if block else {}
    parts = ["Marché du travail cadres en France hexagonale 2026 (vue d'ensemble APEC)"]
    for label, value in bullets.items():
        readable = label.replace("_", " ").capitalize()
        parts.append(f"{readable} : {value}")
    return {
        "id": "apec_region:france-hexagonale",
        "domain": "apec_region",
        "source": "apec_observatoire_emploi_cadre_2026",
        "region": "France hexagonale",
        "bullets": bullets,
        "text": " | ".join(parts) if bullets else parts[0],
    }


def build_observations_record(markdown: str) -> dict[str, Any] | None:
    """Record agrégé pour la section observations cross-régions."""
    block = _extract_section_block(markdown, r"^##\s+4\.\s+Observations.*$")
    if not block:
        return None
    # Remplacer le markdown par texte plat (`1.`, `**`, etc. nettoyés)
    text = re.sub(r"^\d+\.\s+\*\*([^*]+)\*\*\s*:\s*", r"\1 : ", block, flags=re.MULTILINE)
    text = _strip_emphasis(text)
    text = re.sub(r"\s+", " ", text).strip()
    return {
        "id": "apec_region:observations-cross-regions",
        "domain": "apec_region",
        "source": "apec_observatoire_emploi_cadre_2026",
        "region": "Observations cross-régions",
        "bullets": {},
        "text": "Observations cross-régions APEC 2026 : " + text[:3000],
    }


def build_corpus(markdown: str) -> list[dict[str, Any]]:
    """Pipeline complet : markdown → liste records retrievables."""
    records: list[dict[str, Any]] = []
    overview = build_overview_record(markdown)
    if overview:
        records.append(overview)
    for name, block in _split_regions(markdown):
        records.append(normalize_region(name, block))
    obs = build_observations_record(markdown)
    if obs:
        records.append(obs)
    return records


def load_summary(path: Path | None = None) -> str:
    target = path or SUMMARY_MD_PATH
    return target.read_text(encoding="utf-8")


def save_corpus(records: list[dict[str, Any]], path: Path | None = None) -> Path:
    target = path or CORPUS_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target


def main() -> None:  # pragma: no cover
    print(f"[APEC-REGIONS] loading {SUMMARY_MD_PATH}")
    md = load_summary()
    corpus = build_corpus(md)
    out = save_corpus(corpus)
    avg_len = sum(len(c["text"]) for c in corpus) // max(1, len(corpus))
    print(f"[APEC-REGIONS] {len(corpus)} records → {out}")
    print(f"[APEC-REGIONS] longueur texte moyenne : {avg_len} chars")


if __name__ == "__main__":  # pragma: no cover
    main()
