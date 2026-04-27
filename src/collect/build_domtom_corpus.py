"""DROM-COM territorial — corpus retrievable curé démographie/économie/orientation.

Source : `data/raw/domtom/territoires_2026.json` (JSON curé manuellement
depuis sources officielles publiques INSEE Antilles-Guyane, INSEE Océan
Indien, INSEE Mayotte, France Travail statistiques territoriales).

Licence : sources publiques (Etalab, statistique publique).

## Dimension unique apportée à OrientIA

L'axe 3b (PR #82 inserjeunes_lycee_pro) couvre déjà 4/5 DROM côté
**insertion bac pro/CAP/BTS** (Guadeloupe, Martinique, Guyane, La Réunion ;
Mayotte non-couvert car effectifs trop faibles). Cet axe complète avec
les **dimensions territoriales structurelles** non couvertes par
inserjeunes :

- Démographie (population, structure par âge, jeunes 15-24 ans)
- Économie (PIB/hab, salaires médians, taux de chômage spécifiquement
  élevé chez les jeunes)
- Secteurs dominants par territoire (tourisme, BTP, services publics,
  agro, spatial Guyane, énergies La Réunion)
- Spécificités orientation : insularité, mobilité contrainte, dispositifs
  spécifiques DROM (LADOM, SMA, prépa concours antennes locales)

**Critique pour l'orientation** : un·e jeune en DROM a des contraintes
structurelles différentes (insularité, marché de l'emploi local
contraint, coût mobilité métropole). Le RAG sans cette info répond
"comme en métropole" — irrelevant pour 800k jeunes DROM.

Couvre les **5 DROM** : Guadeloupe, Martinique, Guyane, La Réunion,
**Mayotte** (gap noted dans 3b — couvert ici structurellement même si
effectifs lycée pro trop faibles pour insertion stats).

## Stratégie aggregation (~6 cells)

- 1 cell par **territoire** (5 cells, granularity: "territoire") —
  vue détaillée par DROM avec démo + éco + spécificités orientation
- 1 cell **synthèse cross-DROM** (1 cell, granularity: "synthese_cross")
  — vue comparative + dispositifs spécifiques (LADOM, SMA, etc.)

Total : 6 cells, ~900 chars/cell. Domain `territoire_drom` (nouveau,
pour intent classifier ciblage queries DROM-COM).

## Anti-hallucination défensive

Mêmes principes que axe 4 financement :
- Chiffres approximatifs sourcés à une année (ex "2022" ou "2023")
- URL INSEE/France Travail systématique pour vérification
- Marqueur "approx" sur les valeurs numériques pour rappeler l'incertitude
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


RAW_PATH = Path("data/raw/domtom/territoires_2026.json")
RAW_DISPOSITIFS_ETENDUS_PATH = Path("data/raw/domtom/dispositifs_etendus_2026.json")  # Sprint 8 W2
CORPUS_PATH = Path("data/processed/domtom_corpus.json")


def _slug(text: str) -> str:
    import re
    s = (text or "").lower()
    repl = {"é": "e", "è": "e", "ê": "e", "ë": "e", "à": "a", "â": "a",
            "ô": "o", "ö": "o", "ç": "c", "ï": "i", "î": "i", "ù": "u",
            "û": "u", "ÿ": "y"}
    for k, v in repl.items():
        s = s.replace(k, v)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:60]


def load_raw(path: Path | None = None) -> dict[str, Any]:
    target = path or RAW_PATH
    return json.loads(target.read_text(encoding="utf-8"))


def _format_indicator(label: str, value: Any) -> str | None:
    """Formate un dict d'indicateur (avec clé approx + annee + comparaison)."""
    if isinstance(value, (int, float)):
        return f"{label} : {value}"
    if isinstance(value, dict):
        approx = value.get("approx")
        annee = value.get("annee", "")
        comp = value.get("comparaison_france_metro")
        if approx is None:
            return None
        parts = [f"{label} : ~{approx}"]
        if annee:
            parts.append(f"({annee})")
        if comp is not None:
            parts.append(f"; France métro ~{comp}")
        return " ".join(parts)
    return None


def aggregate_by_territoire(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """1 cell par DROM — vue territoriale détaillée."""
    out: list[dict[str, Any]] = []
    for t in raw.get("territoires", []):
        nom = t["nom"]
        zone = t.get("zone", "")
        code = t.get("code_insee", "")

        parts = [
            f"DROM — {nom} (département {code}, {zone})",
            f"Population approximative 2024 : {t['population_approximative_2024']:,} habitants".replace(",", " "),
        ]
        densite = t.get("densite_hab_km2")
        if densite:
            parts.append(f"Densité : ~{densite} hab/km²")

        # Indicateurs jeunes
        part_jeunes = t.get("part_jeunes_15_24_pct")
        if part_jeunes:
            parts.append(f"Part des 15-24 ans dans la population : ~{part_jeunes}%")

        # Chômage
        chomage_glob = _format_indicator("Taux de chômage global (%)", t.get("taux_chomage_global_pct"))
        if chomage_glob:
            parts.append(chomage_glob)
        chomage_jeunes = _format_indicator("Taux de chômage 15-24 ans (%)", t.get("taux_chomage_jeunes_15_24_pct"))
        if chomage_jeunes:
            parts.append(chomage_jeunes)

        # PIB et salaires
        pib = _format_indicator("PIB par habitant (€)", t.get("pib_par_habitant_eur"))
        if pib:
            parts.append(pib)
        salaire = _format_indicator("Salaire médian net mensuel (€)", t.get("salaire_median_net_mensuel_eur"))
        if salaire:
            parts.append(salaire)

        # Secteurs
        secteurs = t.get("secteurs_dominants", [])
        if secteurs:
            parts.append(f"Secteurs dominants : {', '.join(secteurs)}")

        # Spécificités orientation
        spec = t.get("specificites_orientation", [])
        if spec:
            parts.append("Spécificités orientation : " + " ; ".join(spec))

        # Sources
        sources = t.get("sources_officielles", [])
        if sources:
            parts.append(f"Sources officielles : {', '.join(sources)}")

        out.append({
            "id": f"domtom_territoire:{t['id']}",
            "domain": "territoire_drom",
            "source": "domtom_curated",
            "granularity": "territoire",
            "territoire_id": t["id"],
            "code_insee": code,
            "nom": nom,
            "zone": zone,
            "population_approximative": t["population_approximative_2024"],
            "text": " | ".join(parts),
        })
    return out


def aggregate_synthese_cross(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """1 cell synthèse cross-DROM — vue comparative + dispositifs spécifiques."""
    s = raw.get("synthese_cross_drom")
    if not s:
        return []

    parts = [
        f"DROM — {s.get('nom', 'synthèse comparative')}",
    ]

    # Indicateurs communs
    ind = s.get("indicateurs_communs", {})
    for label, val in ind.items():
        if val:
            parts.append(f"{label.replace('_', ' ').capitalize()} : {val}")

    # Dispositifs spécifiques
    disp = s.get("dispositifs_specifiques_drom", [])
    if disp:
        parts.append("Dispositifs spécifiques DROM : " + " ; ".join(disp))

    # Sources
    sources = s.get("sources_officielles_synthese", [])
    if sources:
        parts.append(f"Sources officielles : {', '.join(sources)}")

    return [{
        "id": f"domtom_synthese:{s.get('id', 'cross-drom')}",
        "domain": "territoire_drom",
        "source": "domtom_curated",
        "granularity": "synthese_cross",
        "nom": s.get("nom", ""),
        "text": " | ".join(parts),
    }]


def aggregate_dispositifs_etendus(path: Path | None = None) -> list[dict[str, Any]]:
    """Sprint 8 W2 — agrège les dispositifs étendus DROM (10 cells supplémentaires).

    Source : `data/raw/domtom/dispositifs_etendus_2026.json`. Pattern flat
    (1 cell par dispositif, structure simple subject/content/source).
    """
    target = path or RAW_DISPOSITIFS_ETENDUS_PATH
    if not target.exists():
        return []
    raw = json.loads(target.read_text(encoding="utf-8"))
    out: list[dict[str, Any]] = []
    for d in raw.get("dispositifs_etendus", []):
        subject = d.get("subject", "")
        content = d.get("content", "")
        public = d.get("public_cible", "")
        source = d.get("source_officielle", "")

        parts = [
            f"DROM-COM (extension Sprint 8 W2) — {subject}",
            content,
        ]
        if public:
            parts.append(f"Public cible : {public}")
        if source:
            parts.append(f"Source officielle (vérification année en cours) : {source}")

        out.append({
            "id": f"domtom_dispositif:{d['id']}",
            "domain": "territoire_drom",
            "source": "domtom_curated",
            "granularity": "dispositif_etendu",
            "subject": subject,
            "source_officielle": source,
            "text": " | ".join(p for p in parts if p),
        })
    return out


def build_corpus(raw: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    if raw is None:
        raw = load_raw()
    out: list[dict[str, Any]] = []
    out.extend(aggregate_by_territoire(raw))
    out.extend(aggregate_synthese_cross(raw))
    out.extend(aggregate_dispositifs_etendus())  # Sprint 8 W2
    return out


def save_corpus(records: list[dict[str, Any]], path: Path | None = None) -> Path:
    target = path or CORPUS_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target


def main() -> None:  # pragma: no cover
    print(f"[DOMTOM] loading {RAW_PATH}")
    raw = load_raw()
    n_terr = len(raw.get("territoires", []))
    print(f"[DOMTOM] {n_terr} territoires raw, version {raw.get('version', 'n/a')}")

    corpus = build_corpus(raw)
    save_corpus(corpus)
    avg_text = sum(len(c["text"]) for c in corpus) // max(1, len(corpus))
    granularities: dict[str, int] = defaultdict(int)
    for c in corpus:
        granularities[c["granularity"]] += 1
    print(f"[DOMTOM] {len(corpus)} cells aggregées → {CORPUS_PATH}")
    print(f"[DOMTOM] décomposition : {dict(granularities)}")
    print(f"[DOMTOM] longueur texte moyenne : {avg_text} chars")


if __name__ == "__main__":  # pragma: no cover
    main()
