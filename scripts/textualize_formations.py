"""Textualisation ONISEP/RNCP → markdown avec frontmatter — Sprint 10 chantier B.

Lit `data/raw/onisep_formations.json` (102 fiches data_ia + cyber) ET
`data/raw/rncp/export-fiches-csv-2026-04-23.zip` (filtré ACTIVE), génère
pour chacune un .md avec frontmatter consommable par chantier C (RAG filtré
métadonnées) + paragraphe naturel 200-500 mots.

Usage :
  python3 scripts/textualize_formations.py                    # both (default)
  python3 scripts/textualize_formations.py --source onisep    # ONISEP only
  python3 scripts/textualize_formations.py --source rncp      # RNCP only

Output : `data/textualized/onisep-<slug>.md` (tiret) + `data/textualized/rncp-<numero>.md`.

Spec ordre Jarvis : 2026-04-29-0700b-claudette-orientia-sprint10-textualisation-onisep-rncp.

Anti-hallucination : tous les chiffres du paragraphe sortent du source.
Aucun chiffre inventé (vérifié par tests).
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
INPUT_JSON = ROOT / "data" / "raw" / "onisep_formations.json"
INPUT_RNCP_ZIP = ROOT / "data" / "raw" / "rncp" / "export-fiches-csv-2026-04-23.zip"
RNCP_STANDARD_CSV_NAME = "export_fiches_CSV_Standard_2026_04_22.csv"
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


# Inférence niveau Bac+N depuis type_diplome (utilisé en fallback quand
# `niveau` source est None — fix réserve audit Jarvis + correction Matteo :
# 18/21 mastères ONISEP avaient niveau:null parce que la source JSON ne
# les renseigne pas).
#
# CORRECTION Matteo via Jarvis 2026-04-29 : Mastère Spécialisé (MS) ≠ Master.
# - Master = diplôme national Bac+5 (M1+M2), universités, État
# - Mastère Spécialisé (MS) = label privé Conférence des Grandes Écoles,
#   post-Master, **Bac+6**, formation pro 1 an écoles commerce/ingé
#
# Patterns ordonnés (plus spécifique d'abord). Mastère AVANT Master pour
# priorité (sinon `master` regex matche "mastere" via préfixe).
TYPE_DIPLOME_TO_NIVEAU: list[tuple[re.Pattern[str], int]] = [
    # Bac+6 — Mastère Spécialisé (CGE), distinct du Master national
    (re.compile(r"mastère|mastere", re.IGNORECASE), 6),
    (re.compile(r"\bms\b", re.IGNORECASE), 6),  # acronyme MS = Mastère Spé
    (re.compile(r"bac\+?6", re.IGNORECASE), 6),
    # Bac+5 — Master national, ingénieur, MSc, MBA, certif spé
    (re.compile(r"\bmaster\s+of\s+science\b", re.IGNORECASE), 5),
    (re.compile(r"\bm(aster|sc)\b", re.IGNORECASE), 5),
    (re.compile(r"diplôme d['']ingénieur|ingenieur|ingénieur", re.IGNORECASE), 5),
    (re.compile(r"\bmba\b", re.IGNORECASE), 5),
    (re.compile(r"certificat de spécialisation|certificat de specialisation", re.IGNORECASE), 5),
    # Bac+3 — Bachelor, Licence, BUT
    (re.compile(r"\bbachelor\b|\blicence\b", re.IGNORECASE), 3),
    (re.compile(r"\bbut\b", re.IGNORECASE), 3),
    # Bac+2 — BTS, DUT
    (re.compile(r"\bbts\b|\bdut\b", re.IGNORECASE), 2),
    # Bac (niveau 0 sur Bac+N) — bac pro, bac général
    (re.compile(r"baccalauréat|baccalaureat|\bbac pro", re.IGNORECASE), 0),
]


# Mapping Nomenclature Europe (niveau certif) → Bac+N pour RNCP.
# Cf https://www.francecompetences.fr/recherche-de-certification/
# NIV3 = CAP/BEP (avant bac), NIV4 = Bac, NIV5 = Bac+2, NIV6 = Bac+3,
# NIV7 = Bac+5, NIV8 = Doctorat. Notre échelle s'arrête à Bac+5 (5),
# donc NIV8 mappé à 5 (lossy mais cohérent avec les patterns AnalystAgent
# côté metadata_filter chantier C).
NIVEAU_EUROPE_TO_BAC_PLUS_N: dict[str, int] = {
    "NIV3": 0,
    "NIV4": 0,
    "NIV5": 2,
    "NIV6": 3,
    "NIV7": 5,
    "NIV8": 5,
}


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


def infer_niveau_from_type(type_diplome: str | None, fiche_name: str | None = None) -> int | None:
    """Fallback : infère le niveau Bac+N depuis `type_diplome` (et optionellement
    `fiche_name`) quand le champ niveau source est manquant.

    Returns None si aucun pattern ne matche.
    """
    candidates: list[str] = []
    if type_diplome:
        candidates.append(type_diplome)
    if fiche_name:
        candidates.append(fiche_name)
    for text in candidates:
        for pattern, niveau in TYPE_DIPLOME_TO_NIVEAU:
            if pattern.search(text):
                return niveau
    return None


def parse_niveau_with_fallback(
    niveau_raw: str | None,
    type_diplome: str | None = None,
    fiche_name: str | None = None,
) -> int | None:
    """Essaie parse_niveau d'abord ; si None, fallback infer_niveau_from_type."""
    direct = parse_niveau(niveau_raw)
    if direct is not None:
        return direct
    return infer_niveau_from_type(type_diplome, fiche_name)


def parse_niveau_europe(niveau_europe: str | None) -> int | None:
    """RNCP `'NIV7'` → 5 (Bac+5), `'NIV5'` → 2, etc. None / unknown → None."""
    if not niveau_europe:
        return None
    return NIVEAU_EUROPE_TO_BAC_PLUS_N.get(niveau_europe.strip().upper())


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

    v1.1 fix réserve audit Jarvis : si niveau source est None, fallback
    infer_niveau_from_type(type_diplome, fiche_name) — récupère 20/21
    fiches niveau:null cas mastère / cert spé / MSc / bac pro.
    """
    nom = raw.get("nom") or "formation sans nom"
    type_dip = raw.get("type_diplome") or ""
    duree_raw = raw.get("duree") or ""
    duree_mois = parse_duree_mois(duree_raw)
    niveau = parse_niveau_with_fallback(
        raw.get("niveau"),
        type_diplome=type_dip,
        fiche_name=nom,
    )
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


# ───────────────────── RNCP → TextualizedFiche ──────────────────────


def textualize_rncp_fiche(raw: dict[str, str]) -> TextualizedFiche:
    """Mappe une row RNCP Standard CSV vers TextualizedFiche.

    Champs CSV utilisés : Numero_Fiche / Intitule / Abrege_Intitule /
    Nomenclature_Europe_Niveau / Nomenclature_Europe_Intitule /
    Accessible_Nouvelle_Caledonie / Accessible_Polynesie_Francaise / Actif /
    Type_Enregistrement.

    Limitations v1.1 :
    - region : null (pas dans Standard CSV — disponible dans Partenaires.csv,
      à exploiter v1.2 avec join coûteux 31 MB)
    - alternance : null (pas dans Standard, possiblement dans Voix d'Accès)
    - budget : null (pas dans RNCP — c'est par établissement, hors source)
    - secteur : null v1.1 (lookup nomenclature NSF requis, defer v1.2)
    - duree_mois : null v1.1 (pas dans Standard ; à dériver de Voix d'Accès)
    """
    numero = (raw.get("Numero_Fiche") or "").strip()
    intitule = (raw.get("Intitule") or "formation RNCP sans intitulé").strip()
    abrege = (raw.get("Abrege_Intitule") or "").strip()
    niveau_eu = raw.get("Nomenclature_Europe_Niveau") or ""
    niveau = parse_niveau_europe(niveau_eu)
    type_enreg = (raw.get("Type_Enregistrement") or "").strip()
    accessible_nc = (raw.get("Accessible_Nouvelle_Caledonie") or "").strip().lower() == "oui"
    accessible_pf = (raw.get("Accessible_Polynesie_Francaise") or "").strip().lower() == "oui"

    # numero == "RNCP181" ; on extrait "181" pour le frontmatter rncp
    rncp_short = re.sub(r"^RNCP", "", numero, flags=re.IGNORECASE) or numero

    fid = f"rncp-{rncp_short}" if rncp_short else f"rncp-{_slugify(intitule)}"

    paragraph = _build_paragraph_rncp(
        intitule=intitule,
        abrege=abrege,
        niveau_eu_label=raw.get("Nomenclature_Europe_Intitule") or "",
        rncp_short=rncp_short,
        type_enreg=type_enreg,
        accessible_nc=accessible_nc,
        accessible_pf=accessible_pf,
    )

    return TextualizedFiche(
        id=fid,
        source="rncp",
        title=intitule,
        region=None,  # absent Standard CSV
        niveau=niveau,
        alternance=None,  # absent Standard CSV
        budget=None,  # absent RNCP (par établissement)
        secteur=None,  # NSF lookup requis (v1.2)
        duree_mois=None,  # absent Standard CSV (Voix d'Accès)
        rncp=rncp_short,
        url=f"https://www.francecompetences.fr/recherche/rncp/{rncp_short}/" if rncp_short else None,
        paragraph=paragraph,
    )


def _build_paragraph_rncp(
    *,
    intitule: str,
    abrege: str,
    niveau_eu_label: str,
    rncp_short: str,
    type_enreg: str,
    accessible_nc: bool,
    accessible_pf: bool,
) -> str:
    """Génère paragraph naturel sobre depuis row RNCP Standard.

    Anti-hallu : aucun chiffre invented. Source numbers possibles :
    - rncp_short (code numérique)
    - niveau (depuis NIV3-NIV8 mappé)
    - "Niveau N" depuis label europe (texte natif source)
    """
    parts: list[str] = []

    # Phrase 1 — identification certif
    if abrege:
        parts.append(f"Le {abrege} « {intitule} » est une certification professionnelle référencée au Répertoire National des Certifications Professionnelles (RNCP).")
    else:
        parts.append(f"« {intitule} » est une certification professionnelle référencée au RNCP.")

    # Phrase 2 — niveau européen (cité tel quel depuis source)
    if niveau_eu_label:
        parts.append(f"Elle correspond au {niveau_eu_label} du cadre européen des certifications.")

    # Phrase 3 — type d'enregistrement (qualité de reconnaissance)
    if type_enreg:
        parts.append(f"Type d'enregistrement : {type_enreg}.")

    # Phrase 4 — code RNCP (cité tel quel)
    if rncp_short:
        parts.append(
            f"Cette certification est inscrite sous le numéro RNCP {rncp_short}, "
            f"ce qui atteste de sa reconnaissance officielle par l'État français."
        )

    # Phrase 5 — accessibilité DROM-COM (utile pour métadonnées région)
    drom_clauses = []
    if accessible_nc:
        drom_clauses.append("Nouvelle-Calédonie")
    if accessible_pf:
        drom_clauses.append("Polynésie française")
    if drom_clauses:
        parts.append(
            f"Cette certification est accessible en {' et '.join(drom_clauses)} "
            f"selon France Compétences."
        )

    # Phrase 6 — invitation France Compétences pour info à jour
    parts.append(
        "Pour les informations à jour sur les voies d'accès, les blocs de "
        "compétences, les certificateurs et les passerelles, consulter la "
        "fiche officielle France Compétences (lien en frontmatter)."
    )

    return " ".join(parts)


# ───────────────────── Loaders ──────────────────────


def load_onisep(path: Path = INPUT_JSON) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_rncp_active(zip_path: Path = INPUT_RNCP_ZIP) -> list[dict[str, str]]:
    """Lit le RNCP Standard CSV depuis le zip et filtre `Actif='ACTIVE'`.

    Évite l'extraction physique du CSV (lecture in-memory via zipfile).
    Retourne la liste des dicts row pour les fiches actives uniquement.
    """
    if not zip_path.exists():
        raise FileNotFoundError(f"RNCP zip absent : {zip_path}")
    rows = []
    with zipfile.ZipFile(zip_path) as z:
        with z.open(RNCP_STANDARD_CSV_NAME) as f:
            text = f.read().decode("utf-8")
    reader = csv.DictReader(text.splitlines(), delimiter=";")
    for row in reader:
        if (row.get("Actif") or "").strip().upper() == "ACTIVE":
            rows.append(row)
    return rows


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
    parser = argparse.ArgumentParser(description="Textualisation ONISEP/RNCP → markdown frontmatter.")
    parser.add_argument(
        "--source",
        choices=["onisep", "rncp", "both"],
        default="both",
        help="Sources à textualiser (défaut: both)",
    )
    args = parser.parse_args()

    all_textualized: list[TextualizedFiche] = []

    if args.source in ("onisep", "both"):
        if not INPUT_JSON.exists():
            print(f"⚠️  ONISEP input manquant : {INPUT_JSON}")
            return 1
        raw_onisep = load_onisep()
        print(f"==> {len(raw_onisep)} fiches ONISEP chargées")
        textualized_onisep = [textualize_onisep_fiche(r) for r in raw_onisep]
        all_textualized.extend(textualized_onisep)

    if args.source in ("rncp", "both"):
        if not INPUT_RNCP_ZIP.exists():
            print(f"⚠️  RNCP zip manquant : {INPUT_RNCP_ZIP}")
            return 1
        raw_rncp = load_rncp_active()
        print(f"==> {len(raw_rncp)} fiches RNCP ACTIVE chargées (filter Actif=ACTIVE)")
        textualized_rncp = [textualize_rncp_fiche(r) for r in raw_rncp]
        all_textualized.extend(textualized_rncp)

    all_textualized = dedupe_ids(all_textualized)
    written = write_textualized(all_textualized)
    print(f"==> {written} fichiers .md écrits dans {OUTPUT_DIR}")

    # Stats sanity par source
    onisep_count = sum(1 for f in all_textualized if f.source == "onisep")
    rncp_count = sum(1 for f in all_textualized if f.source == "rncp")
    with_rncp_field = sum(1 for f in all_textualized if f.rncp)
    with_niveau = sum(1 for f in all_textualized if f.niveau is not None)
    with_secteur = sum(1 for f in all_textualized if f.secteur)
    print(f"    - ONISEP : {onisep_count} | RNCP : {rncp_count}")
    print(f"    - avec rncp field : {with_rncp_field}")
    print(f"    - avec niveau parsé : {with_niveau} ({100*with_niveau/max(len(all_textualized),1):.1f}%)")
    print(f"    - avec secteur mappé : {with_secteur} ({100*with_secteur/max(len(all_textualized),1):.1f}%)")
    print(f"    - total IDs uniques : {len(set(f.id for f in all_textualized))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
