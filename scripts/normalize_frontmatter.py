"""Normalize frontmatter cross-corpus → schema unifié 5 critères — Sprint 10 chantier B.

Charge :
- `data/processed/formations.json` (48 914 fiches Parcoursup/ONISEP/RNCP du Run F era)
- `data/textualized/*.md` (6 692 fiches textualisées chantier B v1.1, frontmatter YAML déjà
  partiellement normalisé)
- `data/processed/golden_qa_meta.json` (45 Q&A keep+flag indexées chantier D)

Produit `data/processed/formations_unified.json` (~55k entries) avec **schema unifié 5 critères**
consommable par le metadata_filter chantier C :

- `id` (composite : `<source>-<original_id>`)
- `source` (parcoursup/onisep/rncp/golden_qa)
- `region` (libellé canonique kebab-case lowercase, ex `ile-de-france`)
- `niveau` (int Bac+N, 0..6)
- `alternance` (bool|null)
- `budget` (`low`/`high`/null — semantic categorization, pas €/an précis)
- `secteur` (list[str] canonical sector tags)

Tous les champs originaux sont **préservés** pour backward compat avec `run_judge`,
`format_context`, etc. Les nouveaux champs sont **ajoutés** sans écraser.

Usage :
  PYTHONPATH=. python3 scripts/normalize_frontmatter.py

Spec ordre Jarvis : 2026-04-29-1146-claudette-orientia-sprint10-finalisation-rag-complet
(chantier B).
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
INPUT_FORMATIONS = ROOT / "data" / "processed" / "formations.json"
INPUT_TEXTUALIZED_DIR = ROOT / "data" / "textualized"
INPUT_GOLDEN_QA_META = ROOT / "data" / "processed" / "golden_qa_meta.json"
OUTPUT_UNIFIED = ROOT / "data" / "processed" / "formations_unified.json"


# ────────────────────── 18 régions canoniques FR ──────────────────────


REGIONS_CANONIQUES = [
    "auvergne-rhone-alpes",
    "bourgogne-franche-comte",
    "bretagne",
    "centre-val-de-loire",
    "corse",
    "grand-est",
    "guadeloupe",
    "guyane",
    "hauts-de-france",
    "ile-de-france",
    "la-reunion",
    "martinique",
    "mayotte",
    "normandie",
    "nouvelle-aquitaine",
    "occitanie",
    "pays-de-la-loire",
    "provence-alpes-cote-d-azur",
]


def slug_region(text: str) -> str:
    """Normalize libellé région → slug canonique kebab-case ASCII lowercase.

    "Île-de-France" → "ile-de-france"
    "AUVERGNE-RHONE-ALPES" → "auvergne-rhone-alpes"
    "Provence-Alpes-Côte d'Azur" → "provence-alpes-cote-d-azur"
    """
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_text = nfkd.encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text).strip("-").lower()
    # Variations communes
    s = s.replace("-d-", "-d-")  # placeholder, deja kebab-case OK
    return s


# Aliases pour mapper variations vers canoniques
REGION_ALIASES: dict[str, str] = {
    "ile-de-france": "ile-de-france",
    "auvergne-rhone-alpes": "auvergne-rhone-alpes",
    "auvergne-rhones-alpes": "auvergne-rhone-alpes",  # typo possible
    "occitanie": "occitanie",
    "hauts-de-france": "hauts-de-france",
    "provence-alpes-cote-d-azur": "provence-alpes-cote-d-azur",
    "paca": "provence-alpes-cote-d-azur",
    "nouvelle-aquitaine": "nouvelle-aquitaine",
    "grand-est": "grand-est",
    "pays-de-la-loire": "pays-de-la-loire",
    "bretagne": "bretagne",
    "normandie": "normandie",
    "bourgogne-franche-comte": "bourgogne-franche-comte",
    "centre-val-de-loire": "centre-val-de-loire",
    "centre": "centre-val-de-loire",  # alias historique
    "corse": "corse",
    "la-reunion": "la-reunion",
    "reunion": "la-reunion",
    "guadeloupe": "guadeloupe",
    "martinique": "martinique",
    "guyane": "guyane",
    "mayotte": "mayotte",
    "collectivites-d-outre-mer": None,  # pas de region canonique
    "nouvelle-caledonie": None,
    "polynesie-francaise": None,
}


# ────────────────────── Mapping département → région ──────────────────────


# Source : INSEE/officielle, 2026 18 régions FR (métro + DOM)
DEPT_TO_REGION: dict[str, str] = {
    # Auvergne-Rhône-Alpes (12 départements)
    "ain": "auvergne-rhone-alpes", "allier": "auvergne-rhone-alpes",
    "ardeche": "auvergne-rhone-alpes", "cantal": "auvergne-rhone-alpes",
    "drome": "auvergne-rhone-alpes", "isere": "auvergne-rhone-alpes",
    "loire": "auvergne-rhone-alpes", "haute-loire": "auvergne-rhone-alpes",
    "puy-de-dome": "auvergne-rhone-alpes", "rhone": "auvergne-rhone-alpes",
    "savoie": "auvergne-rhone-alpes", "haute-savoie": "auvergne-rhone-alpes",
    # Bourgogne-Franche-Comté (8 départements)
    "cote-d-or": "bourgogne-franche-comte", "doubs": "bourgogne-franche-comte",
    "jura": "bourgogne-franche-comte", "nievre": "bourgogne-franche-comte",
    "haute-saone": "bourgogne-franche-comte", "saone-et-loire": "bourgogne-franche-comte",
    "yonne": "bourgogne-franche-comte", "territoire-de-belfort": "bourgogne-franche-comte",
    # Bretagne (4 départements)
    "cotes-d-armor": "bretagne", "finistere": "bretagne",
    "ille-et-vilaine": "bretagne", "morbihan": "bretagne",
    # Centre-Val de Loire (6)
    "cher": "centre-val-de-loire", "eure-et-loir": "centre-val-de-loire",
    "indre": "centre-val-de-loire", "indre-et-loire": "centre-val-de-loire",
    "loir-et-cher": "centre-val-de-loire", "loiret": "centre-val-de-loire",
    # Corse (2)
    "corse-du-sud": "corse", "haute-corse": "corse",
    # Grand Est (10)
    "ardennes": "grand-est", "aube": "grand-est", "bas-rhin": "grand-est",
    "haut-rhin": "grand-est", "haute-marne": "grand-est",
    "marne": "grand-est", "meurthe-et-moselle": "grand-est",
    "meuse": "grand-est", "moselle": "grand-est", "vosges": "grand-est",
    # Hauts-de-France (5)
    "aisne": "hauts-de-france", "nord": "hauts-de-france",
    "oise": "hauts-de-france", "pas-de-calais": "hauts-de-france",
    "somme": "hauts-de-france",
    # Île-de-France (8)
    "paris": "ile-de-france", "seine-et-marne": "ile-de-france",
    "yvelines": "ile-de-france", "essonne": "ile-de-france",
    "hauts-de-seine": "ile-de-france", "seine-saint-denis": "ile-de-france",
    "val-de-marne": "ile-de-france", "val-d-oise": "ile-de-france",
    # Normandie (5)
    "calvados": "normandie", "eure": "normandie", "manche": "normandie",
    "orne": "normandie", "seine-maritime": "normandie",
    # Nouvelle-Aquitaine (12)
    "charente": "nouvelle-aquitaine", "charente-maritime": "nouvelle-aquitaine",
    "correze": "nouvelle-aquitaine", "creuse": "nouvelle-aquitaine",
    "dordogne": "nouvelle-aquitaine", "gironde": "nouvelle-aquitaine",
    "landes": "nouvelle-aquitaine", "lot-et-garonne": "nouvelle-aquitaine",
    "pyrenees-atlantiques": "nouvelle-aquitaine", "deux-sevres": "nouvelle-aquitaine",
    "vienne": "nouvelle-aquitaine", "haute-vienne": "nouvelle-aquitaine",
    # Occitanie (13)
    "ariege": "occitanie", "aude": "occitanie", "aveyron": "occitanie",
    "gard": "occitanie", "haute-garonne": "occitanie", "gers": "occitanie",
    "herault": "occitanie", "lot": "occitanie", "lozere": "occitanie",
    "hautes-pyrenees": "occitanie", "pyrenees-orientales": "occitanie",
    "tarn": "occitanie", "tarn-et-garonne": "occitanie",
    # Pays de la Loire (5)
    "loire-atlantique": "pays-de-la-loire", "maine-et-loire": "pays-de-la-loire",
    "mayenne": "pays-de-la-loire", "sarthe": "pays-de-la-loire",
    "vendee": "pays-de-la-loire",
    # PACA (6)
    "alpes-de-haute-provence": "provence-alpes-cote-d-azur",
    "hautes-alpes": "provence-alpes-cote-d-azur",
    "alpes-maritimes": "provence-alpes-cote-d-azur",
    "bouches-du-rhone": "provence-alpes-cote-d-azur",
    "var": "provence-alpes-cote-d-azur",
    "vaucluse": "provence-alpes-cote-d-azur",
    # DOM-TOM
    "guadeloupe": "guadeloupe",
    "guyane": "guyane",
    "martinique": "martinique",
    "la-reunion": "la-reunion",
    "reunion": "la-reunion",
    "mayotte": "mayotte",
}


# ────────────────────── 18 domaines → secteurs ──────────────────────


# Extension de INTERESTS_TO_SECTORS du chantier C (qui ne couvrait que cyber + data_ia
# dans son v1). Chantier B aligne les 18 domaines présents dans formations.json.
DOMAINE_TO_SECTEURS_EXTENDED: dict[str, list[str]] = {
    "apprentissage": ["industriel", "services"],  # générique + flag alternance
    "eco_gestion": ["commerce", "finance", "economie"],
    "sciences_humaines": ["psychologie", "sociologie", "humanites"],
    "ingenierie_industrielle": ["ingenierie", "industriel"],
    "sciences_fondamentales": ["sciences", "recherche"],
    "sante": ["sante", "medical"],
    "lettres_arts": ["lettres", "art", "humanites"],
    "droit": ["droit", "juridique"],
    "services": ["services", "commerce"],
    "langues": ["langues", "humanites"],
    "sport": ["sport", "education"],
    "tourisme_hotellerie": ["tourisme", "hotellerie", "services"],
    "data_ia": ["informatique", "data_science"],
    "cyber": ["informatique", "securite"],
    "communication": ["communication", "commerce"],
    "education": ["education", "enseignement"],
    "agriculture": ["agriculture", "vivant"],
    "autre": [],  # pas de secteur déterminable
}


# ────────────────────── Helpers normalisation ──────────────────────


def normalize_region(raw: str | None) -> str | None:
    """Normalize libellé région vers slug canonique. None si non mapped."""
    if not raw:
        return None
    s = slug_region(raw)
    return REGION_ALIASES.get(s)


def normalize_dept_name(raw: str | None) -> str | None:
    if not raw:
        return None
    return slug_region(raw)


def dept_to_region(dept_raw: str | None) -> str | None:
    """Lookup département → région canonique. None si dept inconnu."""
    if not dept_raw:
        return None
    slug = normalize_dept_name(dept_raw)
    return DEPT_TO_REGION.get(slug)


# Niveau parsing — réutilise la logique du textualizer (cohérence cross-chantier)
NIVEAU_RAW_PATTERN = re.compile(r"^bac\+?(\d+)$", re.IGNORECASE)


def parse_niveau(raw: str | int | None) -> int | None:
    """`'bac+5'` → 5, `'bac+3'` → 3, `0..6` int → int, None → None."""
    if raw is None or raw == "":
        return None
    if isinstance(raw, int):
        return raw if 0 <= raw <= 8 else None
    if not isinstance(raw, str):
        return None
    s = raw.strip().lower()
    if s == "bac":
        return 0
    if s in ("null", "none"):
        return None
    m = NIVEAU_RAW_PATTERN.match(s)
    if m:
        return int(m.group(1))
    # Fallback type_diplome patterns
    if "mastere" in s or "mastère" in s:
        return 6
    if "master" in s or "msc" in s:
        return 5
    if "ingenieur" in s or "ingénieur" in s:
        return 5
    if "bachelor" in s or "licence" in s or "but" in s:
        return 3
    if "bts" in s or "dut" in s:
        return 2
    return None


def infer_alternance(record: dict) -> bool | None:
    """Infère alternance depuis :
    1. Champ `alternance` direct (bool si présent)
    2. `domaine='apprentissage'` → True (cohérent statut CFA)
    3. Mots-clés `nom` ('apprentissage', 'alternance', 'cfa', 'contrat pro')
    4. Sinon None (defensive — chantier C metadata_filter en gère le pass-through)
    """
    direct = record.get("alternance")
    if isinstance(direct, bool):
        return direct
    domaine = (record.get("domaine") or "").strip().lower()
    if domaine == "apprentissage":
        return True
    statut = (record.get("statut") or "").strip().lower()
    if "cfa" in statut or "apprentissage" in statut:
        return True
    nom = (record.get("nom") or "").lower()
    if any(kw in nom for kw in ("alternance", "apprentissage", "contrat pro", "cfa ")):
        return True
    return None


def infer_budget(record: dict) -> str | None:
    """Infère budget depuis statut Public/CFA → low, Privé → high.
    Retourne `'low'`/`'high'`/None (catégorie sémantique, pas €/an précis)."""
    statut = (record.get("statut") or "").strip().lower()
    if not statut or statut == "inconnu":
        return None
    if "public" in statut or "cfa" in statut:
        return "low"
    if "prive" in statut or "privé" in statut:
        return "high"
    if "rncp" in statut:
        # Certificats RNCP : variable selon organisme — null defensive
        return None
    return None


def infer_secteur(record: dict) -> list[str] | None:
    """Mapping `domaine` → liste secteurs canoniques (extension 18 domaines)."""
    domaine = (record.get("domaine") or "").strip().lower()
    if not domaine:
        return None
    secteurs = DOMAINE_TO_SECTEURS_EXTENDED.get(domaine)
    if not secteurs:
        return None
    return list(secteurs)


# ────────────────────── Loaders + parseurs ──────────────────────


def load_formations() -> list[dict[str, Any]]:
    """Load les 48 914 fiches du corpus initial Run F."""
    return json.loads(INPUT_FORMATIONS.read_text(encoding="utf-8"))


def parse_textualized_md(path: Path) -> dict[str, Any] | None:
    """Parse un fichier .md textualized (frontmatter YAML simple + body).

    Retourne un dict avec :
    - les clés frontmatter (id/source/title/region/niveau/alternance/budget/
      secteur/duree_mois/rncp/url)
    - `body` (paragraphe naturel)

    Format attendu :
    ```
    ---
    id: onisep-37989
    source: onisep
    ...
    ---

    Le diplôme « ... » ...
    ```
    """
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if not m:
        return None
    front_text, body = m.group(1), m.group(2).strip()
    record: dict[str, Any] = {}
    for line in front_text.splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        # Strip quotes
        if val.startswith('"') and val.endswith('"'):
            val = val[1:-1].replace('\\"', '"')
        # null
        if val == "null":
            record[key] = None
        # int
        elif val.isdigit() or (val.startswith("-") and val[1:].isdigit()):
            record[key] = int(val)
        # bool
        elif val == "true":
            record[key] = True
        elif val == "false":
            record[key] = False
        # list [a, b]
        elif val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            if inner:
                record[key] = [s.strip() for s in inner.split(",") if s.strip()]
            else:
                record[key] = []
        else:
            record[key] = val
    record["body"] = body
    return record


def load_textualized() -> list[dict[str, Any]]:
    """Charge les 6 692 fiches .md du chantier B v1 mergé."""
    if not INPUT_TEXTUALIZED_DIR.exists():
        return []
    fiches = []
    for path in sorted(INPUT_TEXTUALIZED_DIR.glob("*.md")):
        rec = parse_textualized_md(path)
        if rec:
            fiches.append(rec)
    return fiches


def load_golden_qa() -> list[dict[str, Any]]:
    """Charge les 45 Q&A keep+flag depuis le meta du chantier D."""
    if not INPUT_GOLDEN_QA_META.exists():
        return []
    obj = json.loads(INPUT_GOLDEN_QA_META.read_text(encoding="utf-8"))
    return obj.get("records") or []


# ────────────────────── Normalize records ──────────────────────


def normalize_formation_record(record: dict[str, Any], idx: int) -> dict[str, Any]:
    """Normalize une fiche du corpus initial (formations.json).

    - id : composite source-{cod_aff_form|rncp|index} pour unicité
    - region : direct si présent + canonical, sinon dept→region lookup
    - niveau : parse "bac+N" → int 0..5
    - alternance : inférence multi-source
    - budget : inférence depuis statut
    - secteur : mapping étendu 18 domaines

    Préserve TOUS les champs originaux pour backward compat run_judge / format_context.
    """
    out = dict(record)  # shallow copy preservation
    source = record.get("source") or "unknown"

    # ID composite — préfère les identifiants stables existants
    original_id = (
        record.get("cod_aff_form")
        or record.get("rncp")
        or record.get("uai")
        or f"idx{idx}"
    )
    out["id"] = f"{source}-{original_id}"
    out["source"] = source

    # Région : direct → canonique, sinon dept→region lookup
    direct_region = normalize_region(record.get("region"))
    if direct_region:
        out["region_canonical"] = direct_region
    else:
        dept_region = dept_to_region(record.get("departement"))
        out["region_canonical"] = dept_region  # peut être None

    # Niveau : parse bac+N → int
    out["niveau_int"] = parse_niveau(record.get("niveau"))

    # Alternance : inférence multi-source
    out["alternance_inferred"] = infer_alternance(record)

    # Budget : inférence statut
    out["budget_category"] = infer_budget(record)

    # Secteur : mapping étendu
    out["secteur_canonical"] = infer_secteur(record)

    out["_normalized_v1"] = True
    return out


def normalize_textualized_record(record: dict[str, Any]) -> dict[str, Any]:
    """Normalize une fiche textualized .md (chantier B v1)."""
    out = dict(record)
    source = record.get("source") or "textualized"

    # ID déjà normalisé en v1 (ex `onisep-37989`)
    out["id"] = record.get("id") or f"{source}-untitled"
    out["source"] = source
    out["nom"] = record.get("title")

    # Région : déjà null v1 (ONISEP source vide). Defensive pass-through.
    out["region_canonical"] = normalize_region(record.get("region"))

    # Niveau : déjà int (parse_niveau du textualizer v1.1)
    niveau = record.get("niveau")
    if isinstance(niveau, int):
        out["niveau_int"] = niveau
    else:
        out["niveau_int"] = parse_niveau(niveau)

    # Alternance : déjà null v1 (pas dans source ONISEP). Pass-through.
    out["alternance_inferred"] = record.get("alternance")

    # Budget : déjà null v1.
    out["budget_category"] = record.get("budget")

    # Secteur : déjà mappé v1 (data_ia + cyber). Garder.
    out["secteur_canonical"] = record.get("secteur")

    # Détail = body (pour fiche_to_text utilisation)
    out["detail"] = record.get("body", "")

    out["_normalized_v1"] = True
    return out


def normalize_golden_qa_record(record: dict[str, Any]) -> dict[str, Any]:
    """Normalize une Q&A Golden (chantier D meta)."""
    out: dict[str, Any] = {}
    out["id"] = f"golden_qa-{record.get('prompt_id', '?')}-iter{record.get('iteration', 0)}"
    out["source"] = "golden_qa"
    out["nom"] = record.get("question_seed", "")
    # Body = answer_refined pour permettre fiche_to_text de matcher
    out["detail"] = record.get("answer_refined", "")
    out["category"] = record.get("category")
    out["score_total"] = record.get("score_total")
    out["decision"] = record.get("decision")

    # Frontmatter : Q&A Golden = catégorie lyceen_post_bac (toutes les 45 actuelles)
    # → niveau_int range 1-5 (lycéen → post-bac), pas 1 valeur précise. On laisse null
    # côté niveau_int et on fait porter l'info de catégorie par `category`.
    out["region_canonical"] = None
    out["niveau_int"] = None
    out["alternance_inferred"] = None
    out["budget_category"] = None
    out["secteur_canonical"] = None  # mixte par nature (Q&A pluri-secteurs)

    out["_normalized_v1"] = True
    return out


# ────────────────────── Main ──────────────────────


def main() -> int:
    print("==> Sprint 10 chantier B — normalize frontmatter cross-corpus")
    print()

    # Load 3 sources
    print(f"--- Loading sources ---")
    formations = load_formations()
    print(f"  formations.json : {len(formations)} fiches")
    textualized = load_textualized()
    print(f"  data/textualized/*.md : {len(textualized)} fiches")
    golden_qa = load_golden_qa()
    print(f"  data/processed/golden_qa_meta.json : {len(golden_qa)} records")
    print()

    # Normalize
    print(f"--- Normalize ---")
    unified: list[dict] = []
    for i, rec in enumerate(formations):
        unified.append(normalize_formation_record(rec, i))
    for rec in textualized:
        unified.append(normalize_textualized_record(rec))
    for rec in golden_qa:
        unified.append(normalize_golden_qa_record(rec))
    print(f"  total unified entries : {len(unified)}")
    print()

    # Stats coverage
    print(f"--- Coverage stats post-normalize ---")
    stats = {
        "region_canonical": sum(1 for r in unified if r.get("region_canonical")),
        "niveau_int": sum(1 for r in unified if r.get("niveau_int") is not None),
        "alternance_inferred": sum(1 for r in unified if r.get("alternance_inferred") is not None),
        "budget_category": sum(1 for r in unified if r.get("budget_category") is not None),
        "secteur_canonical": sum(1 for r in unified if r.get("secteur_canonical")),
    }
    for k, count in stats.items():
        pct = 100 * count / len(unified)
        print(f"  {k:25s} : {count:6d}/{len(unified)} ({pct:.1f}%)")
    print()

    # Save unified
    OUTPUT_UNIFIED.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_UNIFIED.write_text(
        json.dumps(unified, ensure_ascii=False),
        encoding="utf-8",
    )
    size_mb = OUTPUT_UNIFIED.stat().st_size / (1024 * 1024)
    print(f"==> Output saved : {OUTPUT_UNIFIED} ({size_mb:.1f} MB, {len(unified)} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
