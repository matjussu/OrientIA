"""ONISEP Idéo-Fiches Métiers — index éditorialisé des métiers (data.gouv.fr).

Source : `datagouv_onisep_ideo_fiches_metiers.xml` (1 075 fiches, 13 MB).
Licence : Licence Ouverte Etalab 2.0.

Distinct du dataset `onisep_metiers.py` (API JSON, 1 518 métiers, mapping
ROME simple). Ce dataset apporte :

- Fiches éditorialisées riches : `accroche_metier` (~270 chars, hook) +
  `format_court` (~1 500 chars, description + durée études + débouchés HTML)
- Pyramide niveaux d'accès du CAP au bac+9 (204 CAP, 321 bac+5, …)
- 968 fiches avec formations minimales requises (id + libellé diplôme)
- 1 060 fiches avec centres d'intérêt taxonomiques (« je veux travailler
  de mes mains », « j'aime les sciences », …)
- 722 fiches avec synonymes de titre métier
- Statuts professionnels (salarié / artisan / libéral / fonctionnaire…)
- Sources web externes par métier

Enrichit `formations.json` avec des libellés métiers humains + contextes
d'accès réalistes — complémentaire au dataset API métiers (ADR-040 Axe 1).

Sortie : `data/processed/ideo_fiches_metiers.json`
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


RAW_PATH = Path("data/raw/data-gouv/datagouv_onisep_ideo_fiches_metiers.xml")
PROCESSED_PATH = Path("data/processed/ideo_fiches_metiers.json")


_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _strip_html(text: str | None) -> str:
    if not text:
        return ""
    return _WS_RE.sub(" ", _HTML_TAG_RE.sub(" ", text)).strip()


def _text_or_empty(elem: ET.Element | None, tag: str) -> str:
    """Helper : `<parent><tag>value</tag></parent>` → 'value' ou ''."""
    if elem is None:
        return ""
    found = elem.find(tag)
    if found is None or found.text is None:
        return ""
    return found.text.strip()


def _extract_synonymes(metier: ET.Element) -> list[str]:
    """Extrait les `<synonyme><nom_metier>X</nom_metier></synonyme>`."""
    container = metier.find("synonymes")
    if container is None:
        return []
    names: list[str] = []
    for syn in container.findall("synonyme"):
        name = _text_or_empty(syn, "nom_metier")
        if name:
            names.append(name)
    return names


def _extract_romes(metier: ET.Element) -> list[str]:
    container = metier.find("romesV3")
    if container is None:
        return []
    codes: list[str] = []
    for rome in container.findall("romeV3"):
        if rome.text and rome.text.strip():
            codes.append(rome.text.strip())
    return codes


def _extract_id_libelle_list(
    metier: ET.Element, container_tag: str, item_tag: str
) -> list[dict[str, str]]:
    """Pattern récurrent : `<container><item><id/><libelle/></item>…`."""
    container = metier.find(container_tag)
    if container is None:
        return []
    items: list[dict[str, str]] = []
    for item in container.findall(item_tag):
        libelle = _text_or_empty(item, "libelle")
        id_ = _text_or_empty(item, "id")
        # Certains éléments ONISEP portent id/libelle en attributs (ex. secteurs).
        if not libelle:
            libelle = (item.attrib.get("libelle") or "").strip()
        if not id_:
            id_ = (item.attrib.get("id") or "").strip()
        if libelle or id_:
            items.append({"id": id_, "libelle": libelle})
    return items


def _extract_niveau_acces(metier: ET.Element) -> dict[str, str] | None:
    node = metier.find("niveau_acces_min")
    if node is None:
        return None
    libelle = _text_or_empty(node, "libelle")
    id_ = _text_or_empty(node, "id")
    if not libelle and not id_:
        return None
    return {"id": id_, "libelle": libelle}


def _extract_sources(metier: ET.Element) -> list[dict[str, str]]:
    container = metier.find("sources_numeriques")
    if container is None:
        return []
    sources: list[dict[str, str]] = []
    for src in container.findall("source"):
        url = _text_or_empty(src, "valeur")
        commentaire = _text_or_empty(src, "commentaire")
        if url:
            sources.append({"url": url, "commentaire": commentaire})
    return sources


def normalize_metier(metier: ET.Element) -> dict[str, Any]:
    """Convertit un `<metier>` XML ONISEP en dict normalisé."""
    identifiant = _text_or_empty(metier, "identifiant")
    nom = _text_or_empty(metier, "nom_metier")
    libelle_f = _text_or_empty(metier, "libelle_feminin")
    libelle_m = _text_or_empty(metier, "libelle_masculin")

    accroche = _strip_html(metier.findtext("accroche_metier"))
    format_court = _strip_html(metier.findtext("format_court"))
    nature_travail = _strip_html(metier.findtext("nature_travail"))
    acces_metier = _strip_html(metier.findtext("acces_metier"))
    condition_travail = _strip_html(metier.findtext("condition_travail"))
    vie_professionnelle = _strip_html(metier.findtext("vie_professionnelle"))
    competences = _strip_html(metier.findtext("competences"))

    return {
        "identifiant": identifiant,
        "nom_metier": nom,
        "libelle_feminin": libelle_f,
        "libelle_masculin": libelle_m,
        "synonymes": _extract_synonymes(metier),
        "codes_rome_v3": _extract_romes(metier),
        "niveau_acces_min": _extract_niveau_acces(metier),
        "formations_min_requise": _extract_id_libelle_list(
            metier, "formations_min_requise", "formation_min_requise"
        ),
        "statuts": _extract_id_libelle_list(metier, "statuts", "statut"),
        "centres_interet": _extract_id_libelle_list(
            metier, "centres_interet", "centre_interet"
        ),
        "secteurs_activite": _extract_id_libelle_list(
            metier, "secteurs_activite", "secteur_activite"
        ),
        "metiers_associes": _extract_id_libelle_list(
            metier, "metiers_associes", "metier_associe"
        ),
        "accroche": accroche,
        "format_court": format_court,
        "nature_travail": nature_travail,
        "acces_metier_description": acces_metier,
        "condition_travail": condition_travail,
        "vie_professionnelle": vie_professionnelle,
        "competences": competences,
        "sources_numeriques": _extract_sources(metier),
    }


def load_metiers(path: Path | None = None) -> list[ET.Element]:
    target = path or RAW_PATH
    tree = ET.parse(target)
    return tree.getroot().findall("metier")


def normalize_all_metiers(metiers: list[ET.Element]) -> list[dict[str, Any]]:
    return [normalize_metier(m) for m in metiers]


def build_rome_to_metiers_index(
    records: list[dict[str, Any]],
) -> dict[str, list[str]]:
    """Mapping inverse code ROME → [nom_metier, …] pour humanisation côté RAG."""
    index: dict[str, list[str]] = {}
    for r in records:
        nom = r.get("nom_metier") or ""
        for code in r.get("codes_rome_v3") or []:
            if not code:
                continue
            index.setdefault(code, []).append(nom)
    return index


def save_processed(records: list[dict[str, Any]], path: Path | None = None) -> Path:
    target = path or PROCESSED_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target


def main() -> None:  # pragma: no cover
    print(f"[IDEO-FICHES] loading {RAW_PATH}")
    metiers = load_metiers()
    records = normalize_all_metiers(metiers)
    out = save_processed(records)
    rome_index = build_rome_to_metiers_index(records)
    print(f"[IDEO-FICHES] {len(records)} fiches → {out}")
    print(f"[IDEO-FICHES] {len(rome_index)} codes ROME distincts indexés")


if __name__ == "__main__":  # pragma: no cover
    main()
