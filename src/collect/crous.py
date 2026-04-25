"""CROUS — logements étudiants + restaurants universitaires (data.gouv.fr).

Sources :
- Logements : GeoJSON national (820 résidences), licence Etalab 2.0.
  `datagouv_crous_logements_france.geojson`
- Restaurants : 26 XML régionaux (999 lieux cumulés), licence Etalab 2.0.
  `crous_restos_xml/resto_<region>.xml`

Enrichit la dimension logement/restauration du scope 17-25 ans (ADR-040 Axe 1).
Permet de répondre à "où se loger à <ville>" ou "resto U près de <université>"
avec des données officielles géolocalisées.

Sorties normalisées :
- data/processed/crous_logements.json
- data/processed/crous_restaurants.json
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable


RAW_DIR = Path("data/raw/data-gouv")
LOGEMENTS_GEOJSON = RAW_DIR / "datagouv_crous_logements_france.geojson"
RESTOS_DIR = RAW_DIR / "crous_restos_xml"

PROCESSED_LOGEMENTS = Path("data/processed/crous_logements.json")
PROCESSED_RESTOS = Path("data/processed/crous_restaurants.json")


_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _strip_html(text: str | None) -> str:
    if not text:
        return ""
    return _WS_RE.sub(" ", _HTML_TAG_RE.sub(" ", text)).strip()


def _parse_house_services(raw: str | None) -> list[str]:
    """house_services est un JSON-in-string ({'house_service': [...]})."""
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    if isinstance(data, dict):
        for key in ("house_service", "services"):
            vals = data.get(key)
            if isinstance(vals, list):
                return [str(v).strip() for v in vals if v]
    if isinstance(data, list):
        return [str(v).strip() for v in data if v]
    return []


def normalize_logement(feature: dict[str, Any]) -> dict[str, Any]:
    props = feature.get("properties") or {}
    geom = feature.get("geometry") or {}
    coords = geom.get("coordinates") or []
    lon = coords[0] if len(coords) >= 1 else None
    lat = coords[1] if len(coords) >= 2 else None

    return {
        "id": props.get("id"),
        "nom": (props.get("title") or "").strip(),
        "adresse": (props.get("address") or props.get("short_desc") or "").strip(),
        "zone": (props.get("zone") or "").strip(),
        "region": (props.get("regions") or "").strip(),
        "telephone": (props.get("phone") or "").strip(),
        "email": (props.get("mail") or "").strip(),
        "url_residence": (props.get("interneturl") or "").strip(),
        "url_reservation": (props.get("bookingurl") or "").strip(),
        "url_rdv": (props.get("appointmenturl") or "").strip(),
        "services": _parse_house_services(props.get("house_services")),
        "description": _strip_html(props.get("infos")),
        "latitude": float(lat) if lat is not None else None,
        "longitude": float(lon) if lon is not None else None,
    }


def load_logements(path: Path | None = None) -> list[dict[str, Any]]:
    target = path or LOGEMENTS_GEOJSON
    payload = json.loads(target.read_text(encoding="utf-8"))
    return payload.get("features", [])


def normalize_all_logements(features: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_logement(f) for f in features]


def save_logements(records: list[dict[str, Any]], path: Path | None = None) -> Path:
    target = path or PROCESSED_LOGEMENTS
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target


_OPENING_DAYS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
_OPENING_SLOTS = ("matin", "midi", "soir")


def _parse_opening_pattern(pattern: str | None) -> dict[str, str]:
    """`110,110,110,110,110,000,000` → {lundi: 'matin+midi', …, samedi: 'ferme'}.

    Triplet = (matin, midi, soir). 1=ouvert, 0=fermé. Mapping jour → label.
    """
    if not pattern:
        return {}
    parts = [p.strip() for p in pattern.split(",")]
    result: dict[str, str] = {}
    for day, triplet in zip(_OPENING_DAYS, parts):
        if len(triplet) != 3 or set(triplet) - {"0", "1"}:
            continue
        labels = [svc for flag, svc in zip(triplet, _OPENING_SLOTS) if flag == "1"]
        result[day] = "+".join(labels) if labels else "ferme"
    return result


def normalize_resto(resto_elem: ET.Element) -> dict[str, Any]:
    a = resto_elem.attrib
    infos_el = resto_elem.find("infos")
    contact_el = resto_elem.find("contact")
    lat = a.get("lat")
    lon = a.get("lon")

    return {
        "id": (a.get("id") or "").strip(),
        "nom": (a.get("title") or "").strip(),
        "type": (a.get("type") or "").strip(),
        "zone": (a.get("zone") or "").strip(),
        "zone_secondaire": (a.get("zone2") or "").strip(),
        "description_courte": (a.get("short_desc") or "").strip(),
        "horaires_hebdo": _parse_opening_pattern(a.get("opening")),
        "ferme_actuellement": a.get("closing") == "1",
        "infos": _strip_html(infos_el.text if infos_el is not None else ""),
        "contact": _strip_html(contact_el.text if contact_el is not None else ""),
        "latitude": float(lat) if lat else None,
        "longitude": float(lon) if lon else None,
    }


def _region_from_filename(xml_path: Path) -> str:
    """`resto_aix.marseille.xml` → 'aix-marseille' ; `resto_paris.xml` → 'paris'."""
    return xml_path.stem.removeprefix("resto_").replace(".", "-")


def iter_restos(restos_dir: Path | None = None) -> Iterable[tuple[str, ET.Element]]:
    target = restos_dir or RESTOS_DIR
    for xml_path in sorted(target.iterdir()):
        if xml_path.suffix.lower() != ".xml":
            continue
        region = _region_from_filename(xml_path)
        tree = ET.parse(xml_path)
        for resto in tree.getroot().findall("resto"):
            yield region, resto


def normalize_all_restos(restos_dir: Path | None = None) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for region, elem in iter_restos(restos_dir):
        record = normalize_resto(elem)
        record["region_source"] = region
        records.append(record)
    return records


def save_restos(records: list[dict[str, Any]], path: Path | None = None) -> Path:
    target = path or PROCESSED_RESTOS
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target


def main() -> None:  # pragma: no cover
    print(f"[CROUS] logements ← {LOGEMENTS_GEOJSON}")
    logs = normalize_all_logements(load_logements())
    out_logs = save_logements(logs)
    print(f"[CROUS] {len(logs)} logements → {out_logs}")

    print(f"[CROUS] restos ← {RESTOS_DIR}")
    restos = normalize_all_restos()
    out_restos = save_restos(restos)
    print(f"[CROUS] {len(restos)} restos → {out_restos}")


if __name__ == "__main__":  # pragma: no cover
    main()
