"""Audit du schéma des corpora annexes — pré-flight Phase B.1 du plan corpus v5.

Phase A.4 du plan ADR-057. Vérifie que chaque corpus annexe collecté dans
`data/processed/` est conforme au schéma minimal attendu par le merger v3
(Stage 10 APPEND_ANNEXES) et la FactCard de Phase A.1.

## Schéma minimal attendu (5 champs obligatoires par record)

- `id` : string non-vide, identifiant unique stable de la fiche
- `domain` : string non-vide ∈ {12 domain_hint connus} (cf src/rag/intent.py)
- `source` : string non-vide, listée dans SOURCE_TO_TIER (ADR-055)
- `text` : string non-vide, retrievable narratif (consommé par fiche_to_text)
- tier inférable depuis `source` ou `provenance` block (tier 1/2/3)

## Périmètre audité

22 corpora annexes (`*_corpus.json` + `inserjeunes_cfa.json` + le ROME 4.0
nouveau de Phase A.2) + 1 audit du nouveau corpus ROME si présent.

## Output

Rapport markdown `docs/CORPORA_SCHEMA_AUDIT_<date>.md` avec :
- Tableau résumé conformité (corpus | n_records | n_conforme | %)
- Section détail par corpus non-conforme avec liste des issues
- Recommandations pour Phase B (corpus à fixer avant intégration)

Usage :
    python scripts/audit_corpora_schema_compliance.py
    python scripts/audit_corpora_schema_compliance.py --output docs/AUDIT_X.md
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Permet à l'audit de tourner depuis n'importe où (script standalone).
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.rag.fact_card import SOURCE_TO_TIER, _infer_provenance, _pick_formation_name  # noqa: E402


# ─────────────── Configuration des corpora à auditer ───────────────


# Tuple : (label_humain, path_relatif_au_root, domain_attendu_majoritaire_ou_None,
#         is_primary_formations)
#
# `is_primary_formations=True` désigne les 6 corpora "principaux" de
# formations classiques (MonMaster, LBA, Inserjeunes CFA, RNCP, ONISEP
# extended, Parcoursup extended). Ces corpora n'ont pas vocation à être
# directement intégrés via le champ `domain` — c'est le merger v3 (Stages
# 2 MERGE_FUZZY + 5 NORMALIZE) qui leur ajoute `id`/`domain`/`text` au
# moment de l'agrégation. L'audit les vérifie donc sur un schema réduit :
# présence d'un nom inférable + tier de provenance correctement déduit.
#
# `is_primary_formations=False` désigne les corpora annexes (DARES, APEC,
# CROUS, etc.) qui doivent être conformes au schema minimal complet
# (`id`, `domain`, `source`, `text` non-vides).
CORPORA_TO_AUDIT: list[tuple[str, str, str | None, bool]] = [
    # Formations principales (multi-source aggregées) — schema réduit
    ("MonMaster formations", "data/processed/monmaster_formations.json", None, True),
    ("LBA formations", "data/processed/lba_formations.json", None, True),
    ("Inserjeunes CFA", "data/processed/inserjeunes_cfa.json", None, True),
    ("RNCP certifications", "data/processed/rncp_certifications.json", None, True),
    ("ONISEP formations extended", "data/processed/onisep_formations_extended.json", None, True),
    ("Parcoursup extended", "data/processed/parcoursup_extended.json", None, True),
    # Corpora annexes (avec domain natif) — schema complet
    ("DARES Métiers 2030", "data/processed/dares_corpus.json", "metier_prospective", False),
    ("APEC régions", "data/processed/apec_regions_corpus.json", "apec_region", False),
    ("CROUS corpus", "data/processed/crous_corpus.json", "crous", False),
    ("INSEE salaires PCS", "data/processed/insee_salaan_corpus.json", "insee_salaire", False),
    ("France Compétences blocs", "data/processed/france_comp_blocs_corpus.json", "competences_certif", False),
    ("Inserjeunes lycée pro corpus", "data/processed/inserjeunes_lycee_pro_corpus.json", "formation_insertion", False),
    ("InserSup corpus", "data/processed/insersup_corpus.json", "insertion_pro", False),
    ("Métiers IDEO ONISEP", "data/processed/metiers_corpus.json", "metier", False),
    ("ONISEP métiers", "data/processed/onisep_metiers.json", "metier", False),
    ("Parcours bacheliers", "data/processed/parcours_bacheliers_corpus.json", "parcours_bacheliers", False),
    ("Doctorat IP", "data/processed/ip_doc_doctorat.json", "insertion_pro", False),
    ("DROM-COM territoires", "data/processed/domtom_corpus.json", "territoire_drom", False),
    ("Voie pré-bac", "data/processed/voie_pre_bac_corpus.json", "voie_pre_bac", False),
    ("Financement", "data/processed/financement_corpus.json", "financement_etudes", False),
    ("Corrections factuelles", "data/processed/corrections_factuelles_corpus.json", None, False),
    # ROME 4.0 (Phase A.2 livrée — fichier généré)
    ("ROME 4.0 métiers", "data/processed/rome_metier_corpus.json", "metier_detail", False),
]


# ─────────────── Audit logic ───────────────


REQUIRED_FIELDS_ANNEX = ("id", "domain", "source", "text")
REQUIRED_FIELDS_PRIMARY = ("source",)  # corpora principaux : juste source (les autres champs sont ajoutés par le merger v3)


def _check_record(record: Any, is_primary: bool = False) -> list[str]:
    """Retourne la liste des issues détectées sur un record, [] si conforme.

    Pour les corpora annexes (`is_primary=False`), vérifie le schema complet :
    `id`, `domain`, `source`, `text` non-vides + tier inférable.

    Pour les corpora principaux formations (`is_primary=True`), vérifie le
    schema réduit : tier inférable + nom inférable via `_pick_formation_name`.
    Le merger v3 ajoutera `id`/`domain`/`text` au moment de l'agrégation.
    """
    issues: list[str] = []
    if not isinstance(record, dict):
        return [f"record n'est pas un dict (type={type(record).__name__})"]

    required = REQUIRED_FIELDS_PRIMARY if is_primary else REQUIRED_FIELDS_ANNEX
    for f in required:
        val = record.get(f)
        if val is None or (isinstance(val, str) and not val.strip()):
            issues.append(f"champ '{f}' absent ou vide")

    # source → tier inférable
    src = record.get("source")
    if isinstance(src, str) and src.strip():
        if src.lower() not in SOURCE_TO_TIER:
            # Vérifier si tier 3 par préfixe site_etablissement_
            if not src.lower().startswith("site_etablissement_"):
                # Vérifier provenance explicite
                provenance = record.get("provenance")
                if not (isinstance(provenance, dict) and provenance.get("tier") in ("tier_1", "tier_2", "tier_3")):
                    issues.append(f"source '{src}' non listée dans SOURCE_TO_TIER (ADR-055)")

    # Pour primary : vérifier qu'un nom inférable existe (cascade _pick_formation_name)
    if is_primary:
        nom = _pick_formation_name(record)
        if not nom or nom == "(formation sans nom)":
            issues.append("nom inférable absent (cascade _pick_formation_name retourne fallback)")

    return issues


def audit_corpus(
    label: str,
    path: Path,
    expected_domain: str | None = None,
    is_primary: bool = False,
) -> dict[str, Any]:
    """Audite un corpus, retourne un dict de stats."""
    result = {
        "label": label,
        "path": str(path.relative_to(PROJECT_ROOT)) if path.is_absolute() else str(path),
        "exists": path.exists(),
        "is_primary": is_primary,
        "n_records": 0,
        "n_conforme": 0,
        "n_non_conforme": 0,
        "issues_summary": Counter(),
        "domain_distribution": Counter(),
        "source_distribution": Counter(),
        "tier_distribution": Counter(),
        "expected_domain": expected_domain,
        "expected_domain_match_pct": None,
        "sample_issue_records": [],
        "load_error": None,
    }
    if not path.exists():
        result["load_error"] = "fichier absent"
        return result

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        result["load_error"] = f"erreur lecture : {e}"
        return result

    # Détection du format : list ou dict
    records: list[Any]
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict):
        # Tente les clés courantes
        for key in ("records", "data", "items", "entries"):
            if key in data and isinstance(data[key], list):
                records = data[key]
                break
        else:
            result["load_error"] = "dict sans clé 'records/data/items/entries'"
            return result
    else:
        result["load_error"] = f"format non supporté (type={type(data).__name__})"
        return result

    result["n_records"] = len(records)
    n_expected_match = 0

    for i, rec in enumerate(records):
        issues = _check_record(rec, is_primary=is_primary)
        if not isinstance(rec, dict):
            result["n_non_conforme"] += 1
            for iss in issues:
                result["issues_summary"][iss] += 1
            continue

        # Distributions
        result["domain_distribution"][rec.get("domain") or "__none__"] += 1
        result["source_distribution"][rec.get("source") or "__none__"] += 1

        # Tier via _infer_provenance (cohérence Phase A.1)
        prov = _infer_provenance(rec)
        tier = prov.tier if prov else "__none__"
        result["tier_distribution"][tier] += 1

        # Match expected_domain
        if expected_domain is not None and rec.get("domain") == expected_domain:
            n_expected_match += 1

        if issues:
            result["n_non_conforme"] += 1
            for iss in issues:
                result["issues_summary"][iss] += 1
            if len(result["sample_issue_records"]) < 3:
                result["sample_issue_records"].append({
                    "index": i,
                    "id": rec.get("id"),
                    "issues": issues,
                })
        else:
            result["n_conforme"] += 1

    if expected_domain is not None and result["n_records"] > 0:
        result["expected_domain_match_pct"] = round(
            n_expected_match / result["n_records"] * 100, 1
        )

    return result


# ─────────────── Rapport markdown ───────────────


def _format_summary_table(audits: list[dict[str, Any]]) -> str:
    """Tableau résumé : | corpus | type | n records | conforme | % | tier 1 dom. |."""
    lines = [
        "| Corpus | Type | n records | Conforme | % | Domain attendu | Tier 1 dom. |",
        "|---|:-:|---:|---:|---:|---|:-:|",
    ]
    for a in audits:
        type_tag = "primary" if a.get("is_primary") else "annexe"
        if a["load_error"]:
            lines.append(
                f"| {a['label']} | {type_tag} | — | — | — | — | ⚠️ {a['load_error']} |"
            )
            continue
        n = a["n_records"]
        nc = a["n_conforme"]
        pct = round(nc / n * 100, 1) if n else 0.0
        symbol = "✓" if pct == 100.0 else ("⚠" if pct >= 80.0 else "✗")
        expect = a["expected_domain"] or "(libre)"
        if a["expected_domain_match_pct"] is not None:
            expect = f"{expect} ({a['expected_domain_match_pct']}%)"
        tier1_count = a["tier_distribution"].get("tier_1", 0)
        tier1_dom = "✓" if tier1_count > 0 and tier1_count == n else (
            "△" if tier1_count > 0 else "—"
        )
        lines.append(
            f"| {a['label']} | {type_tag} | {n} | {nc} | {pct} {symbol} | {expect} | {tier1_dom} |"
        )
    return "\n".join(lines)


def _format_corpus_detail(audit: dict[str, Any]) -> str:
    """Section détail pour un corpus avec issues."""
    a = audit
    lines = [f"### {a['label']}", ""]
    if a["load_error"]:
        lines.append(f"⚠️ **Non chargé** : {a['load_error']}")
        lines.append("")
        return "\n".join(lines)

    lines.append(f"- Path : `{a['path']}`")
    lines.append(f"- Records : {a['n_records']}")
    lines.append(f"- Conformes : {a['n_conforme']} ({round(a['n_conforme']/a['n_records']*100, 1) if a['n_records'] else 0}%)")
    lines.append(f"- Non conformes : {a['n_non_conforme']}")
    lines.append("")

    # Distribution domain
    if a["domain_distribution"]:
        lines.append("**Distribution `domain`** :")
        for d, c in a["domain_distribution"].most_common(5):
            lines.append(f"- `{d}` : {c}")
        lines.append("")

    # Distribution source
    if a["source_distribution"]:
        lines.append("**Distribution `source`** :")
        for s, c in a["source_distribution"].most_common(5):
            lines.append(f"- `{s}` : {c}")
        lines.append("")

    # Distribution tier
    if a["tier_distribution"]:
        lines.append("**Distribution tier (inféré ADR-055)** :")
        for t, c in sorted(a["tier_distribution"].items()):
            lines.append(f"- `{t}` : {c}")
        lines.append("")

    # Issues
    if a["issues_summary"]:
        lines.append("**Issues** :")
        for iss, c in a["issues_summary"].most_common():
            lines.append(f"- {iss} : {c} fois")
        lines.append("")

    if a["sample_issue_records"]:
        lines.append("**Exemples records non-conformes (premiers 3)** :")
        for sample in a["sample_issue_records"]:
            lines.append(f"- record #{sample['index']} (id={sample['id']!r}) : {', '.join(sample['issues'])}")
        lines.append("")

    return "\n".join(lines)


def build_report(audits: list[dict[str, Any]], date_str: str) -> str:
    """Construit le rapport markdown complet."""
    n_total = sum(a["n_records"] for a in audits if not a["load_error"])
    n_conforme_total = sum(a["n_conforme"] for a in audits if not a["load_error"])
    n_corpora_present = sum(1 for a in audits if not a["load_error"])
    n_corpora_audited = len(audits)

    # Liste des corpora avec issues
    non_conformes = [a for a in audits if (a["n_non_conforme"] or 0) > 0]
    absents = [a for a in audits if a["load_error"]]

    pct_global = round(n_conforme_total / n_total * 100, 1) if n_total else 0.0

    lines = [
        f"# Audit schéma corpora annexes — {date_str}",
        "",
        "> Phase A.4 du plan corpus v5 (ADR-057). Vérifie la conformité des",
        "> corpora annexes au schéma minimal attendu par le merger v3 et la",
        "> FactCard de Phase A.1.",
        "",
        "## Résumé",
        "",
        f"- **Corpora audités** : {n_corpora_audited}",
        f"- **Corpora présents (chargés)** : {n_corpora_present}",
        f"- **Corpora absents** : {len(absents)}",
        f"- **Records totaux** : {n_total}",
        f"- **Records conformes** : {n_conforme_total} ({pct_global}%)",
        f"- **Records non-conformes** : {n_total - n_conforme_total}",
        f"- **Corpora avec issues** : {len(non_conformes)}",
        "",
        "## Tableau récapitulatif",
        "",
        _format_summary_table(audits),
        "",
        "Légende :",
        "- Type `primary` : corpus formations principales (MonMaster, LBA, Inserjeunes CFA, RNCP, ONISEP/Parcoursup extended). Schema réduit attendu (juste `source` + nom inférable). Le merger v3 ajoutera `id`/`domain`/`text` au Stage 2 (MERGE_FUZZY) + Stage 5 (NORMALIZE).",
        "- Type `annexe` : corpus annexe avec domain natif. Schema complet attendu (`id`, `domain`, `source`, `text` non-vides + tier inférable).",
        "- `✓` : 100% conforme",
        "- `⚠` : ≥80% conforme",
        "- `✗` : <80% conforme",
        "- Tier 1 dom. `✓` : 100% des records classés tier_1",
        "- Tier 1 dom. `△` : tier_1 partiellement présent",
        "- Tier 1 dom. `—` : aucun tier_1 inféré (fixer la source pour Phase B)",
        "",
        "## Détails par corpus",
        "",
    ]
    for a in audits:
        lines.append(_format_corpus_detail(a))

    # Recommandations
    lines.extend([
        "## Recommandations pour Phase B (merger v3)",
        "",
    ])
    if absents:
        lines.append("### Corpora absents à générer avant Phase B")
        for a in absents:
            lines.append(f"- **{a['label']}** (`{a['path']}`) : {a['load_error']}")
        lines.append("")

    if non_conformes:
        lines.append("### Corpora avec issues à corriger")
        for a in non_conformes:
            top_issue = a["issues_summary"].most_common(1)[0] if a["issues_summary"] else None
            issue_str = f"{top_issue[0]} ({top_issue[1]} fois)" if top_issue else "?"
            lines.append(f"- **{a['label']}** : {a['n_non_conforme']} non-conformes — issue principale : {issue_str}")
        lines.append("")

    if not absents and not non_conformes:
        lines.append("✓ Tous les corpora audités sont conformes — Phase B peut démarrer.")
        lines.append("")

    lines.append("## Critères de pass pour Phase B")
    lines.extend([
        "",
        "1. ≥95% des records de chaque corpus annexe ont les 5 champs obligatoires (`id`, `domain`, `source`, `text`, tier inférable)",
        "2. 100% des sources listées dans SOURCE_TO_TIER (cf `src/rag/fact_card.py`)",
        "3. Aucun corpus présent dans `CORPORA_TO_AUDIT` mais absent du filesystem (sauf opt-out explicite)",
        "",
        "Si un de ces critères échoue, il faut corriger le `build_*.py` correspondant",
        "OU étendre `SOURCE_TO_TIER` (ADR-055) avant de lancer le merger v3.",
        "",
    ])

    return "\n".join(lines)


# ─────────────── Main CLI ───────────────


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Path de sortie du rapport (défaut : docs/CORPORA_SCHEMA_AUDIT_<date>.md)",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Silencieux — n'affiche que le path du rapport en sortie",
    )
    args = parser.parse_args()

    audits = []
    for label, rel_path, expected_domain, is_primary in CORPORA_TO_AUDIT:
        path = PROJECT_ROOT / rel_path
        result = audit_corpus(label, path, expected_domain, is_primary=is_primary)
        audits.append(result)
        if not args.quiet:
            symbol = "✓" if not result["load_error"] and result["n_non_conforme"] == 0 else "⚠"
            n = result["n_records"]
            issue_count = result["n_non_conforme"]
            error_str = f" — {result['load_error']}" if result["load_error"] else ""
            print(f"  {symbol} {label}: {n} records, {issue_count} issues{error_str}")

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    output_path = Path(args.output) if args.output else (
        PROJECT_ROOT / f"docs/CORPORA_SCHEMA_AUDIT_{date_str}.md"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report = build_report(audits, date_str)
    output_path.write_text(report, encoding="utf-8")

    if not args.quiet:
        print()
        print(f"Rapport écrit : {output_path}")

    # Code retour : 0 si tout conforme, 1 sinon (utile en CI)
    n_non_conforme_total = sum(
        a["n_non_conforme"] or 0 for a in audits if not a["load_error"]
    )
    n_absents = sum(1 for a in audits if a["load_error"])
    return 0 if (n_non_conforme_total == 0 and n_absents == 0) else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
