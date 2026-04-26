"""France Compétences blocs RNCP — corpus retrievable aggregé compétences certifiées.

Source : ZIP CSV France Compétences "export-fiches-csv-YYYY-MM-DD.zip"
(data.gouv.fr Etalab 2.0). Le ZIP contient le CSV
`export_fiches_CSV_Blocs_De_Compétences_*.csv` qui n'était pas exploité
par le collecteur RNCP existant (`src/collect/rncp.py` joint Standard +
VoixdAccès + Rome + Nsf + Certificateurs uniquement).

## Dimension unique apportée à OrientIA

Jusqu'ici, OrientIA connaît les **fiches RNCP** (intitulé, niveau, ROME,
NSF) mais pas le **contenu pédagogique** des certifications : ce qu'on
y apprend, les compétences validées en sortie, les savoir-faire opposables.

Les blocs de compétences répondent directement à la question d'orientation
classique : "qu'est-ce que je vais apprendre concrètement avec ce
diplôme ?" — question non couverte par Parcoursup ni ONISEP fiches métiers.

## Stratégie aggregation (~4 891 cells)

- 1 cell par fiche RNCP **active** ayant au moins 1 bloc (intersection
  6 590 active × 10 181 fiches-avec-blocs = 4 891 cells)
- Texte : intitulé + niveau + ROMEs visés + tous les blocs concaténés
  + voies d'accès (alternance / VAE / formation continue)
- Aggregation per-fiche au lieu de per-bloc (52 592 raw rows → 4 891 cells
  = 10.7× réduction de dilution top-K, pattern cohérent v5++ Phase B)

## Aucun appel API externe

Les blocs sont déjà dans le ZIP existant `data/raw/rncp/export-fiches-csv-*.zip`
(téléchargé pour `src/collect/rncp.py`). Pas besoin de re-fetch France
Compétences API. ~30s build, $0 download.

Pattern dual-output (cohérent PR #57 parcours / PR #67 Phase B / PR #70 DARES) :
- Pas de RAW_PATH dédié (raw blocs reste dans le ZIP, exploitation directe)
- `data/processed/france_comp_blocs_corpus.json` (aggregé retrievable)
"""
from __future__ import annotations

import csv
import io
import json
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional


RNCP_ZIP_DIR = Path("data/raw/rncp")
BLOCS_CSV_PREFIX = "export_fiches_CSV_Blocs_De_Compétences_"
RNCP_CERTIFS_PATH = Path("data/processed/rncp_certifications.json")
CORPUS_PATH = Path("data/processed/france_comp_blocs_corpus.json")


def _find_latest_zip(rncp_dir: Path = RNCP_ZIP_DIR) -> Optional[Path]:
    """Cherche le ZIP CSV France Comp le plus récent (par date suffix)."""
    if not rncp_dir.exists():
        return None
    candidates = sorted(rncp_dir.glob("export-fiches-csv-*.zip"))
    return candidates[-1] if candidates else None


def _find_blocs_csv_name(zip_path: Path) -> Optional[str]:
    """Le nom du CSV blocs varie par date, on matche par prefix."""
    with zipfile.ZipFile(zip_path) as z:
        for n in z.namelist():
            if n.startswith(BLOCS_CSV_PREFIX):
                return n
    return None


def load_blocs(zip_path: Optional[Path] = None) -> list[dict[str, str]]:
    """Lit le CSV Blocs_De_Compétences depuis le ZIP RNCP local.

    Returns rows avec keys 'Numero_Fiche', 'Bloc_Competences_Code',
    'Bloc_Competences_Libelle'.
    """
    target = zip_path or _find_latest_zip()
    if target is None or not target.exists():
        raise FileNotFoundError(
            f"Aucun ZIP RNCP trouvé dans {RNCP_ZIP_DIR}. "
            "Run `python -m src.collect.rncp` d'abord pour télécharger."
        )
    csv_name = _find_blocs_csv_name(target)
    if csv_name is None:
        raise FileNotFoundError(
            f"CSV {BLOCS_CSV_PREFIX}*.csv absent du ZIP {target.name}"
        )
    with zipfile.ZipFile(target) as z:
        with z.open(csv_name) as f:
            text = io.TextIOWrapper(f, encoding="utf-8", errors="replace")
            return list(csv.DictReader(text, delimiter=";"))


def _index_blocs_by_fiche(
    blocs: list[dict[str, str]],
) -> dict[str, list[dict[str, str]]]:
    """Groupe les rows blocs par numéro de fiche RNCP."""
    by_fiche: dict[str, list[dict[str, str]]] = defaultdict(list)
    for b in blocs:
        numero = (b.get("Numero_Fiche") or "").strip()
        if numero:
            by_fiche[numero].append(b)
    return dict(by_fiche)


def _format_blocs_text(blocs: list[dict[str, str]]) -> str:
    """Formate la liste des blocs en string concise.

    Trie par code (BC01, BC02, ...) pour lisibilité humaine et
    déterminisme entre runs (utile pour l'embedding stable).
    """
    sorted_blocs = sorted(
        blocs,
        key=lambda b: (b.get("Bloc_Competences_Code") or "").strip(),
    )
    items = []
    for b in sorted_blocs:
        libelle = (b.get("Bloc_Competences_Libelle") or "").strip()
        if libelle:
            items.append(libelle)
    if not items:
        return ""
    return " | ".join(f"Bloc {i+1} : {lib}" for i, lib in enumerate(items))


def aggregate_by_fiche(
    certifs: list[dict[str, Any]],
    blocs_by_fiche: dict[str, list[dict[str, str]]],
) -> list[dict[str, Any]]:
    """1 cell par fiche RNCP active ayant au moins 1 bloc.

    Texte format :
    "Compétences certifiées (RNCP <numero>) — <intitule> (<niveau>)
     | Métiers visés : <ROMEs>
     | Voies d'accès : <voies>
     | Bloc 1 : <libelle>
     | Bloc 2 : <libelle>
     | Source : France Compétences (RNCP)"
    """
    out: list[dict[str, Any]] = []
    for f in certifs:
        if not f.get("actif"):
            continue
        numero = f.get("numero_fiche")
        if not numero:
            continue
        blocs = blocs_by_fiche.get(numero, [])
        if not blocs:
            continue

        intitule = (f.get("intitule") or "").strip()
        niveau = f.get("niveau") or ""
        niveau_intitule = f.get("niveau_intitule") or ""
        codes_rome = f.get("codes_rome") or []
        codes_nsf = f.get("codes_nsf") or []
        voies = f.get("voies_acces") or []

        parts = [
            f"Compétences certifiées ({numero}) — {intitule}"
            + (f" ({niveau})" if niveau else "")
        ]
        if niveau_intitule and niveau and niveau_intitule.lower() not in niveau.lower():
            parts.append(f"Niveau européen : {niveau_intitule}")
        if codes_rome:
            rome_str = ", ".join(
                f"{r.get('code', '')} {r.get('libelle', '')}".strip()
                for r in codes_rome[:3]
                if r.get("code")
            )
            if rome_str:
                parts.append(f"Métiers visés (ROME) : {rome_str}")
        if codes_nsf:
            nsf_str = ", ".join(
                (n.get("libelle") or n.get("code") or "").strip()
                for n in codes_nsf[:2]
                if (n.get("code") or n.get("libelle"))
            )
            if nsf_str:
                parts.append(f"Spécialité NSF : {nsf_str}")
        if voies:
            parts.append(f"Voies d'accès : {', '.join(voies)}")

        blocs_text = _format_blocs_text(blocs)
        if blocs_text:
            parts.append(blocs_text)
        parts.append("Source : France Compétences (RNCP, blocs de compétences)")

        out.append({
            "id": f"rncp_blocs:{numero}",
            "domain": "competences_certif",
            "source": "rncp_blocs",
            "numero_fiche": numero,
            "intitule": intitule,
            "niveau": niveau,
            "niveau_eu": f.get("niveau_eu"),
            "phase": f.get("phase"),
            "codes_rome": [
                r.get("code") for r in codes_rome if r.get("code")
            ],
            "codes_nsf": [
                n.get("code") for n in codes_nsf if n.get("code")
            ],
            "n_blocs": len(blocs),
            "voies_acces": voies,
            "text": " | ".join(parts),
        })
    return out


def build_corpus(
    certifs: Optional[list[dict[str, Any]]] = None,
    blocs: Optional[list[dict[str, str]]] = None,
) -> list[dict[str, Any]]:
    """Construit le corpus aggregé blocs RNCP.

    Inputs :
    - certifs : `data/processed/rncp_certifications.json` (active fiches)
    - blocs : raw rows du CSV Blocs_De_Compétences

    Si non fournis, charge depuis les chemins par défaut.
    """
    if certifs is None:
        certifs = json.loads(RNCP_CERTIFS_PATH.read_text(encoding="utf-8"))
    if blocs is None:
        blocs = load_blocs()
    blocs_by_fiche = _index_blocs_by_fiche(blocs)
    return aggregate_by_fiche(certifs, blocs_by_fiche)


def save_corpus(
    records: list[dict[str, Any]], path: Optional[Path] = None
) -> Path:
    target = path or CORPUS_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target


def main() -> None:  # pragma: no cover
    print(f"[FRANCE-COMP-BLOCS] loading certifications + blocs…")
    corpus = build_corpus()
    save_corpus(corpus)
    avg_text = sum(len(c["text"]) for c in corpus) // max(1, len(corpus))
    avg_blocs = sum(c["n_blocs"] for c in corpus) / max(1, len(corpus))
    print(
        f"[FRANCE-COMP-BLOCS] {len(corpus)} cells aggregées "
        f"(active fiches × blocs) → {CORPUS_PATH}"
    )
    print(f"[FRANCE-COMP-BLOCS] longueur texte moyenne : {avg_text} chars")
    print(f"[FRANCE-COMP-BLOCS] blocs moyens par fiche : {avg_blocs:.1f}")


if __name__ == "__main__":  # pragma: no cover
    main()
