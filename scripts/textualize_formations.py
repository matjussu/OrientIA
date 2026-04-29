"""Textualisation ONISEP/RNCP → markdown avec frontmatter — Sprint 10 chantier B.

Lit `data/raw/onisep_formations.json` (102 fiches data_ia + cyber), génère
pour chacune un .md avec frontmatter consommable par chantier C (RAG filtré
métadonnées) + paragraphe naturel 200-500 mots.

Usage : python3 scripts/textualize_formations.py
Output : data/textualized/onisep_<slug>.md (102 fichiers)

Spec ordre Jarvis : 2026-04-29-0700b-claudette-orientia-sprint10-textualisation-onisep-rncp.

Scope v1 : ONISEP uniquement. RNCP zip (`data/raw/rncp/export-fiches-csv-2026-04-23.zip`)
en v1.1 (commit séparé après audit Jarvis sur ONISEP).

Anti-hallucination : tous les chiffres du paragraphe sortent du JSON source.
Aucun chiffre inventé (vérifié par tests).
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INPUT_JSON = ROOT / "data" / "raw" / "onisep_formations.json"
OUTPUT_DIR = ROOT / "data" / "textualized"


# ───────────────────── Lookup tables ──────────────────────

# domaine ONISEP → secteurs canoniques (alignés avec INTERESTS_TO_SECTORS
# côté metadata_filter pour cohérence chantier B → C).
DOMAINE_TO_SECTEURS: dict[str, list[str]] = {
    "data_ia": ["informatique", "data_science"],
    "cyber": ["informatique", "securite"],
    # Extensible : "ingenierie", "sante", "droit", etc. au fur et à mesure
    # que d'autres domaines arrivent dans la source ONISEP.
}

# Patterns durée → durée_mois (int)
DUREE_PATTERNS: list[tuple[re.Pattern[str], int]] = [
    (re.compile(r"^(\d+)\s*(an|ans)$", re.IGNORECASE), 12),
    (re.compile(r"^(\d+)\s*(mois)$", re.IGNORECASE), 1),
    (re.compile(r"^(\d+)\s*(semestre|semestres)$", re.IGNORECASE), 6),
]


# ───────────────────── Datatypes ──────────────────────


@dataclass
class TextualizedFiche:
    """Frontmatter + paragraphe naturel pour une fiche formation."""

    id: str
    source: str  # "onisep" | "rncp"
    title: str
    region: str | None
    niveau: int | None  # 0..5 (Bac+N)
    alternance: bool | None
    budget: int | None  # €/an
    secteur: list[str] | None
    duree_mois: int | None
    rncp: str | None
    url: str | None
    paragraph: str

    def to_markdown(self) -> str:
        front = ["---"]
        front.append(f"id: {self.id}")
        front.append(f"source: {self.source}")
        front.append(f"title: {_yaml_escape(self.title)}")
        front.append(f"region: {self.region if self.region is not None else 'null'}")
        front.append(f"niveau: {self.niveau if self.niveau is not None else 'null'}")
        front.append(f"alternance: {_yaml_bool(self.alternance)}")
        front.append(f"budget: {self.budget if self.budget is not None else 'null'}")
        if self.secteur:
            front.append(f"secteur: [{', '.join(self.secteur)}]")
        else:
            front.append("secteur: null")
        front.append(
            f"duree_mois: {self.duree_mois if self.duree_mois is not None else 'null'}"
        )
        front.append(f"rncp: {self.rncp if self.rncp else 'null'}")
        front.append(f"url: {self.url if self.url else 'null'}")
        front.append("---")
        return "\n".join(front) + "\n\n" + self.paragraph + "\n"


# ───────────────────── Helpers ──────────────────────


def _yaml_escape(text: str | None) -> str:
    """Quote YAML string si elle contient des caractères spéciaux."""
    if text is None or text == "":
        return "null"
    if any(c in text for c in [':', '#', '"', "'", '\n', '[', ']', '{', '}', ',']):
        # Double-quote + escape internes
        return '"' + text.replace('"', '\\"') + '"'
    return text


def _yaml_bool(b: bool | None) -> str:
    if b is None:
        return "null"
    return "true" if b else "false"


def _slugify(text: str, max_len: int = 60) -> str:
    """ASCII slug compatible filename. Trim @ max_len. Fallback 'untitled' si vide."""
    if not text:
        return "untitled"
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_text = nfkd.encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text).strip("-").lower()
    return (s[:max_len].strip("-") or "untitled")


def parse_niveau(niveau_raw: str | None) -> int | None:
    """`'bac+5'` → 5, `'bac+3'` → 3, `'bac+2'` → 2, `'bac'` → 0, None → None."""
    if not niveau_raw:
        return None
    s = niveau_raw.strip().lower()
    if s == "bac":
        return 0
    m = re.match(r"^bac\+(\d+)$", s)
    if m:
        return int(m.group(1))
    return None


def parse_duree_mois(duree_raw: str | None) -> int | None:
    """'2 ans' → 24, '6 mois' → 6, '4 semestres' → 24, None → None."""
    if not duree_raw:
        return None
    s = duree_raw.strip().lower()
    for pattern, multiplier in DUREE_PATTERNS:
        m = pattern.search(s)
        if m:
            return int(m.group(1)) * multiplier
    return None


def domaine_to_secteurs(domaine: str | None) -> list[str] | None:
    if not domaine:
        return None
    return DOMAINE_TO_SECTEURS.get(domaine.strip().lower())


# ───────────────────── ONISEP → TextualizedFiche ──────────────────────


def textualize_onisep_fiche(raw: dict[str, Any]) -> TextualizedFiche:
    """Mappe une fiche brute ONISEP vers TextualizedFiche.

    Champs source : source / domaine / nom / etablissement / ville / rncp /
    url_onisep / type_diplome / duree / tutelle / niveau / statut.

    Frontmatter v1 : region/alternance/budget restent None (pas dans la
    source ONISEP — defensive pass-through côté metadata_filter chantier C).

    Anti-hallucination : aucun chiffre n'est inventé. Les seuls nombres dans
    le paragraphe sont `niveau` (bac+N), `duree_mois` (calculé depuis duree
    raw), et `rncp` (ID code).
    """
    nom = raw.get("nom") or "formation sans nom"
    type_dip = raw.get("type_diplome") or ""
    duree_raw = raw.get("duree") or ""
    duree_mois = parse_duree_mois(duree_raw)
    niveau = parse_niveau(raw.get("niveau"))
    rncp_id = raw.get("rncp") or None
    secteurs = domaine_to_secteurs(raw.get("domaine"))
    url = raw.get("url_onisep") or None
    etab = (raw.get("etablissement") or "").strip()
    ville = (raw.get("ville") or "").strip()
    tutelle = (raw.get("tutelle") or "").strip().lower()

    fid = f"onisep-{rncp_id}" if rncp_id else f"onisep-{_slugify(nom)}"

    paragraph = _build_paragraph_onisep(
        nom=nom,
        type_dip=type_dip,
        duree_raw=duree_raw,
        niveau_raw=raw.get("niveau"),
        rncp_id=rncp_id,
        etab=etab,
        ville=ville,
        tutelle=tutelle,
        secteurs=secteurs,
    )

    return TextualizedFiche(
        id=fid,
        source="onisep",
        title=nom,
        region=None,  # ONISEP source vide pour 102/102 fiches v1
        niveau=niveau,
        alternance=None,  # absent source ONISEP, defensive
        budget=None,  # absent source ONISEP, defensive
        secteur=secteurs,
        duree_mois=duree_mois,
        rncp=rncp_id,
        url=url,
        paragraph=paragraph,
    )


def _build_paragraph_onisep(
    *,
    nom: str,
    type_dip: str,
    duree_raw: str,
    niveau_raw: str | None,
    rncp_id: str | None,
    etab: str,
    ville: str,
    tutelle: str,
    secteurs: list[str] | None,
) -> str:
    """Génère un paragraphe naturel 200-500 chars depuis champs structurés.

    Anti-hallu : toutes les données factuelles citées sont issues de la
    fiche source. Vocabulaire descriptif neutre, pas de promesse débouchés
    ni qualificatif sélectivité.
    """
    parts: list[str] = []

    # Phrase 1 — identification formation
    if type_dip:
        parts.append(
            f"Le diplôme « {nom} » est un {type_dip} référencé par l'ONISEP."
        )
    else:
        parts.append(f"La formation « {nom} » est référencée par l'ONISEP.")

    # Phrase 2 — durée + niveau
    duree_clause = f"Sa durée annoncée est de {duree_raw}." if duree_raw else ""
    niveau_clause = (
        f"Elle prépare au niveau {niveau_raw}." if niveau_raw else ""
    )
    if duree_clause and niveau_clause:
        parts.append(f"{duree_clause} {niveau_clause}")
    elif duree_clause:
        parts.append(duree_clause)
    elif niveau_clause:
        parts.append(niveau_clause)

    # Phrase 3 — établissement + ville si présents (rare en v1, 0/102 source)
    if etab and ville:
        parts.append(f"Elle est dispensée par {etab}, basé à {ville}.")
    elif etab:
        parts.append(f"Elle est dispensée par {etab}.")
    elif ville:
        parts.append(f"L'établissement est localisé à {ville}.")

    # Phrase 4 — tutelle si non-vide et pas "non renseigné"
    if tutelle and tutelle not in ("non renseigné", "non-renseigne", "n/a"):
        parts.append(f"Elle est sous tutelle {tutelle}.")

    # Phrase 5 — RNCP si présent (valeur officielle reconnaissance État)
    if rncp_id:
        parts.append(
            f"Elle est inscrite au Répertoire National des Certifications "
            f"Professionnelles (RNCP) sous le numéro {rncp_id}, "
            f"ce qui atteste de sa reconnaissance officielle par l'État."
        )

    # Phrase 6 — domaines si secteurs mappés
    if secteurs:
        secteurs_label = " et ".join(secteurs)
        parts.append(f"Elle relève des domaines suivants : {secteurs_label}.")

    # Phrase 7 — invitation à consulter URL pour info à jour
    parts.append(
        "Pour les informations à jour sur les modalités d'admission, "
        "le programme et les frais de scolarité, consulter la fiche "
        "ONISEP officielle (lien en frontmatter)."
    )

    return " ".join(parts)


# ───────────────────── Main ──────────────────────


def load_onisep(path: Path = INPUT_JSON) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_textualized(fiches: list[TextualizedFiche], output_dir: Path = OUTPUT_DIR) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    for f in fiches:
        out_path = output_dir / f"{f.id}.md"
        out_path.write_text(f.to_markdown(), encoding="utf-8")
        written += 1
    return written


def dedupe_ids(fiches: list[TextualizedFiche]) -> list[TextualizedFiche]:
    """Suffixe `-2`, `-3`, ... sur les IDs en collision pour garantir
    l'unicité côté filesystem (overwrite évité) et côté retrieve (chaque
    candidate identifiable par son id stable même avec RNCP partagé)."""
    seen: dict[str, int] = {}
    out = []
    for f in fiches:
        if f.id not in seen:
            seen[f.id] = 1
            out.append(f)
        else:
            seen[f.id] += 1
            new_id = f"{f.id}-{seen[f.id]}"
            # On préserve le reste du dataclass, on ne fait que renommer l'id
            from dataclasses import replace
            out.append(replace(f, id=new_id))
    return out


def main() -> int:
    if not INPUT_JSON.exists():
        print(f"⚠️  Input manquant : {INPUT_JSON}")
        return 1

    raw_fiches = load_onisep()
    print(f"==> {len(raw_fiches)} fiches ONISEP chargées")

    textualized = [textualize_onisep_fiche(r) for r in raw_fiches]
    textualized = dedupe_ids(textualized)
    written = write_textualized(textualized)
    print(f"==> {written} fichiers .md écrits dans {OUTPUT_DIR}")

    # Stats sanity
    with_rncp = sum(1 for f in textualized if f.rncp)
    with_niveau = sum(1 for f in textualized if f.niveau is not None)
    with_secteur = sum(1 for f in textualized if f.secteur)
    print(f"    - avec RNCP : {with_rncp}")
    print(f"    - avec niveau parsé : {with_niveau}")
    print(f"    - avec secteur mappé : {with_secteur}")
    print(f"    - total IDs uniques : {len(set(f.id for f in textualized))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
