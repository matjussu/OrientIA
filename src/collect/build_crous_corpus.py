"""Construit `crous_corpus.json` retrievable aggregé depuis `crous_logements`
+ `crous_restaurants` (sources PR #54).

Stratégie aggregation (~50 cells) :
- 1 cell par CROUS régional (n=26 régions restos) : aggrege restos + logements
  de la région, fournit nb logements / nb restos / types restos / sample
  établissements
- 1 cell par grande ville étudiante (top 10-15 villes par nb logements) :
  zoom sur les villes principales (Paris 18, Montpellier, Nantes, etc.)
- 1 cell France entière (vue d'ensemble)

Total cible : ~30-40 cells (vs 1 819 raw → 50× réduction de bruit top-K).

Pattern dual-output (cohérent PR #57 parcours) :
- `data/processed/crous_logements.json` (raw, déjà existant 820 records)
- `data/processed/crous_restaurants.json` (raw, déjà existant 999 records)
- `data/processed/crous_corpus.json` (aggregé retrievable, nouveau)
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


LOGEMENTS_PATH = Path("data/processed/crous_logements.json")
RESTOS_PATH = Path("data/processed/crous_restaurants.json")
CORPUS_PATH = Path("data/processed/crous_corpus.json")

# Slug map pour les CROUS régionaux (clé = region_source des restos XML)
_CROUS_REGION_LABELS = {
    "aix-marseille": "CROUS Aix-Marseille",
    "amiens": "CROUS Amiens",
    "antilles-guyane": "CROUS Antilles-Guyane",
    "bfc": "CROUS Bourgogne-Franche-Comté",
    "bordeaux": "CROUS Bordeaux",
    "clermont-ferrand": "CROUS Clermont-Ferrand",
    "corte": "CROUS Corte",
    "creteil": "CROUS Créteil",
    "grenoble": "CROUS Grenoble",
    "lille": "CROUS Lille",
    "limoges": "CROUS Limoges",
    "lyon": "CROUS Lyon",
    "montpellier": "CROUS Montpellier",
    "nancy-metz": "CROUS Nancy-Metz",
    "nantes": "CROUS Nantes",
    "nice": "CROUS Nice",
    "normandie": "CROUS Normandie",
    "orleans-tours": "CROUS Orléans-Tours",
    "paris": "CROUS Paris",
    "poitiers": "CROUS Poitiers",
    "reims": "CROUS Reims",
    "rennes": "CROUS Rennes",
    "reunion": "CROUS Réunion",
    "strasbourg": "CROUS Strasbourg",
    "toulouse": "CROUS Toulouse",
    "versailles": "CROUS Versailles",
}


def _slug(text: str) -> str:
    """Normalise une chaîne en slug ASCII pour les ids."""
    import re
    s = (text or "").lower()
    s = s.replace("é", "e").replace("è", "e").replace("ê", "e")
    s = s.replace("à", "a").replace("â", "a")
    s = s.replace("ô", "o").replace("ö", "o")
    s = s.replace("ç", "c").replace("ï", "i")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def _aggregate_by_region(
    logements: list[dict],
    restos: list[dict],
) -> list[dict]:
    """1 cell par CROUS régional. Aggrege logements + restos de la région."""
    # Regroupe restos par region_source (clé interne CROUS)
    restos_by_region: dict[str, list[dict]] = defaultdict(list)
    for r in restos:
        regsrc = r.get("region_source") or ""
        if regsrc:
            restos_by_region[regsrc].append(r)

    # Regroupe logements par region administrative (Île-de-France etc.)
    # On va mapper region admin → CROUS regional via une heuristique simple
    # (les CROUS et les regions admin françaises ne matchent pas 1-1 ;
    # pour simplifier on matche par ville présente).
    out: list[dict] = []
    for regsrc, region_restos in restos_by_region.items():
        label = _CROUS_REGION_LABELS.get(regsrc, f"CROUS {regsrc}")
        # Ville-clé typique du CROUS (ex: "paris" → "Paris")
        slug_id = f"crous_region:{regsrc}"

        # Statistiques restos
        n_restos = len(region_restos)
        types_restos = Counter(r.get("type", "") for r in region_restos)
        zones_restos = Counter(r.get("zone", "") for r in region_restos)

        # Logements de la région (matching par ville incluse dans zones_restos
        # principales)
        zones_keys = {z.lower() for z in zones_restos.keys() if z}
        region_logements = [
            l for l in logements
            if (l.get("zone") or "").lower() in zones_keys
        ]
        n_logements = len(region_logements)
        services_logements: Counter[str] = Counter()
        for l in region_logements:
            for s in l.get("services") or []:
                services_logements[s] += 1
        sample_residences = [
            (l.get("nom"), l.get("zone")) for l in region_logements[:5]
        ]
        sample_restos_named = [
            (r.get("nom"), r.get("zone"), r.get("type"))
            for r in region_restos[:5]
        ]

        # Texte retrievable
        parts = [f"Vie étudiante CROUS {label} (logement + restauration universitaire)"]
        parts.append(f"Restaurants universitaires : {n_restos} lieux totaux")
        if types_restos:
            top_types = ", ".join(
                f"{t} ({n})" for t, n in types_restos.most_common(5) if t
            )
            parts.append(f"Types principaux : {top_types}")
        if zones_restos:
            top_zones = ", ".join(z for z, _ in zones_restos.most_common(3) if z)
            parts.append(f"Zones principales : {top_zones}")
        if n_logements:
            parts.append(f"Résidences universitaires : {n_logements} logements répertoriés dans la région")
            if services_logements:
                top_services = ", ".join(
                    s for s, _ in services_logements.most_common(5) if s
                )
                parts.append(f"Services principaux : {top_services}")
        if sample_residences:
            samples = "; ".join(
                f"{nom} ({zone})" for nom, zone in sample_residences if nom
            )
            parts.append(f"Exemples résidences : {samples}")
        if sample_restos_named:
            samples = "; ".join(
                f"{nom} ({zone}, {typ})"
                for nom, zone, typ in sample_restos_named if nom
            )
            parts.append(f"Exemples restaurants : {samples}")

        record = {
            "id": slug_id,
            "domain": "crous",
            "source": "crous_combine_logements_restos",
            "region_crous": label,
            "region_slug": regsrc,
            "n_logements": n_logements,
            "n_restos": n_restos,
            "types_restos": dict(types_restos),
            "zones_principales": [z for z, _ in zones_restos.most_common(5)],
            "services_logements_principaux": [
                s for s, _ in services_logements.most_common(5)
            ],
            "text": " | ".join(parts),
        }
        out.append(record)
    return out


def _aggregate_by_grande_ville(logements: list[dict], top_n: int = 12) -> list[dict]:
    """1 cell par grande ville étudiante (top par nb logements)."""
    by_zone: dict[str, list[dict]] = defaultdict(list)
    for l in logements:
        zone = (l.get("zone") or "").strip()
        if zone:
            by_zone[zone].append(l)
    # Top N par nb logements
    sorted_zones = sorted(by_zone.items(), key=lambda kv: -len(kv[1]))[:top_n]
    out: list[dict] = []
    for zone, zone_logements in sorted_zones:
        if len(zone_logements) < 3:
            continue  # skip toutes petites zones (peu de signal RAG)
        n = len(zone_logements)
        services_count: Counter[str] = Counter()
        for l in zone_logements:
            for s in l.get("services") or []:
                services_count[s] += 1
        regions_count = Counter(l.get("region", "") for l in zone_logements)
        region_dom = regions_count.most_common(1)[0][0] if regions_count else ""

        parts = [f"Logements étudiants CROUS à {zone}"]
        parts.append(f"Région : {region_dom}")
        parts.append(f"Nombre de résidences : {n}")
        if services_count:
            top_services = ", ".join(
                s for s, _ in services_count.most_common(7) if s
            )
            parts.append(f"Services principaux : {top_services}")
        sample_names = "; ".join(
            l.get("nom", "") for l in zone_logements[:5] if l.get("nom")
        )
        parts.append(f"Exemples résidences : {sample_names}")

        out.append({
            "id": f"crous_ville:{_slug(zone)}",
            "domain": "crous",
            "source": "crous_combine_logements_restos",
            "ville": zone,
            "region": region_dom,
            "n_residences": n,
            "services_principaux": [s for s, _ in services_count.most_common(7)],
            "text": " | ".join(parts),
        })
    return out


def _aggregate_france(logements: list[dict], restos: list[dict]) -> dict:
    """Vue d'ensemble France : 1 cell."""
    n_log = len(logements)
    n_res = len(restos)
    types = Counter(r.get("type", "") for r in restos)
    regions = Counter(l.get("region", "") for l in logements)
    services: Counter[str] = Counter()
    for l in logements:
        for s in l.get("services") or []:
            services[s] += 1

    parts = [
        "Vie étudiante CROUS — vue d'ensemble France",
        f"Total résidences universitaires : {n_log} logements répertoriés",
        f"Total restaurants/cafétérias universitaires : {n_res} lieux",
        f"Types restaurants principaux : "
        + ", ".join(f"{t} ({n})" for t, n in types.most_common(5) if t),
        f"Top régions logement : "
        + ", ".join(f"{r} ({n})" for r, n in regions.most_common(5) if r),
        f"Services logements principaux : "
        + ", ".join(s for s, _ in services.most_common(7) if s),
    ]
    return {
        "id": "crous:france",
        "domain": "crous",
        "source": "crous_combine_logements_restos",
        "n_logements_total": n_log,
        "n_restos_total": n_res,
        "regions_principales": [r for r, _ in regions.most_common(5)],
        "text": " | ".join(parts),
    }


def build_corpus(
    logements: list[dict] | None = None,
    restos: list[dict] | None = None,
) -> list[dict]:
    if logements is None:
        logements = json.loads(LOGEMENTS_PATH.read_text(encoding="utf-8"))
    if restos is None:
        restos = json.loads(RESTOS_PATH.read_text(encoding="utf-8"))
    out: list[dict] = []
    out.append(_aggregate_france(logements, restos))
    out.extend(_aggregate_by_region(logements, restos))
    out.extend(_aggregate_by_grande_ville(logements))
    return out


def save_corpus(records: list[dict], path: Path | None = None) -> Path:
    target = path or CORPUS_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target


def main() -> None:  # pragma: no cover
    print(f"[CROUS-CORPUS] loading raw…")
    corpus = build_corpus()
    out = save_corpus(corpus)
    avg_text = sum(len(c["text"]) for c in corpus) // max(1, len(corpus))
    print(f"[CROUS-CORPUS] {len(corpus)} cells → {out}")
    print(f"[CROUS-CORPUS] longueur texte moyenne : {avg_text} chars")


if __name__ == "__main__":  # pragma: no cover
    main()
