"""Audit qualité automatique des corpus OrientIA normalisés (D+S+1 extension).

Vérifie toutes les sources ingérées dans `data/processed/` et produit un
rapport markdown dans `docs/AUDIT_DATA_QUALITY_<date>.md`.

Usage :
    python scripts/audit_data_quality.py [--out path/to/rapport.md]

Vérifications :
1. JSON valid parsing (chaque fichier ingéré se charge sans erreur)
2. Métriques globales (n par source, par phase, par niveau, par domaine)
3. Anomalies :
   - Fiches sans champ critique (`source`, `phase`, `nom`/`intitule`/`libelle`)
   - Doublons potentiels (signature nom+etablissement+ville identique)
   - Encoding suspect (valeurs "nan", "null", "undefined", "None")
   - Valeurs numériques hors bornes (taux_admission hors [0,1], etc.)
4. Distribution vs ADR-039 répartition 33/33/34 par phase
5. Verdict GO/NO-GO pour re-index FAISS (D6)
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import date as _date
from pathlib import Path
from typing import Any


PROCESSED_DIR = Path("data/processed")

# Fichiers OrientIA canoniques attendus. Chacun est une liste de dicts.
EXPECTED_SOURCES = {
    "monmaster_formations.json": {"type": "fiches", "phase_default": "master"},
    "rncp_certifications.json": {"type": "fiches", "phase_default": None},  # inféré niveau_eu
    "onisep_metiers.json": {"type": "metiers", "phase_default": None},
    "onisep_formations_extended.json": {"type": "fiches", "phase_default": None},
    "lba_formations.json": {"type": "fiches", "phase_default": "reorientation"},  # D10 alternance  # D2 ext
    "cereq_insertion_stats.json": {"type": "stats", "phase_default": None},
    "insee_salaires_pcs_age.json": {"type": "stats", "phase_default": None},
    "parcoursup_extended.json": {"type": "fiches", "phase_default": None},
    "formations.json": {"type": "fiches", "phase_default": None},  # corpus legacy
}

# Fichiers de stats/index (pas des fiches) — à auditer séparément
STATS_TYPES = {"metiers", "stats"}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _signature(fiche: dict[str, Any]) -> str:
    """Signature pour détection de doublons.

    Inclut l'identifiant unique source quand dispo pour éviter les faux
    doublons :
    - MonMaster : `ifc` (identifiant formation-établissement unique), nested
      dans `id_mon_master.ifc`
    - RNCP : `numero_fiche` distingue les certifs (pas juste l'intitulé)
    - Parcoursup : `cod_aff_form` distingue formation × établissement
    - LBA : `id_lba`
    """
    # Identifiants top-level prioritaires
    for id_key in ("cod_aff_form", "numero_fiche", "id_lba"):
        id_val = fiche.get(id_key)
        if id_val:
            return f"id:{id_key}={id_val}"
    # Identifiants nested MonMaster (id_mon_master.ifc)
    id_mm = fiche.get("id_mon_master") or {}
    if isinstance(id_mm, dict):
        ifc = id_mm.get("ifc") or id_mm.get("inmp")
        if ifc:
            return f"id:mm_ifc={ifc}"
    # Fallback : nom + etablissement + ville
    nom = (fiche.get("nom") or fiche.get("intitule") or fiche.get("libelle") or "").strip().lower()
    etab = (fiche.get("etablissement") or "").strip().lower()
    ville = (fiche.get("ville") or "").strip().lower()
    return f"{nom}|{etab}|{ville}"


def _suspicious_string(val: Any) -> bool:
    """Retourne True si une valeur a l'air d'une valeur sentinelle mal parsée."""
    if not isinstance(val, str):
        return False
    stripped = val.strip().lower()
    return stripped in {"nan", "null", "undefined", "none", "n/a", "#n/a"}


def audit_fiches(path: Path, info: dict[str, Any]) -> dict[str, Any]:
    """Audit une source de type `fiches`."""
    try:
        data = _load_json(path)
    except Exception as exc:
        return {"file": path.name, "error": f"Parse JSON fail: {exc}"}

    if not isinstance(data, list):
        return {"file": path.name, "error": f"Expected list, got {type(data).__name__}"}

    total = len(data)
    missing_critical = defaultdict(int)
    suspicious_values = defaultdict(int)
    phase_counts: Counter[str] = Counter()
    niveau_counts: Counter[str] = Counter()
    domaine_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    signatures: Counter[str] = Counter()

    critical_fields_any = ["nom", "intitule", "libelle"]  # au moins un doit être rempli

    for f in data:
        if not isinstance(f, dict):
            missing_critical["non_dict_entry"] += 1
            continue
        # Champ nom/libellé obligatoire
        if not any(str(f.get(k) or "").strip() for k in critical_fields_any):
            missing_critical["nom/intitule/libelle"] += 1
        # phase (ADR-039 obligatoire)
        if not f.get("phase"):
            missing_critical["phase"] += 1
        # source
        if not f.get("source"):
            missing_critical["source"] += 1

        # Scan valeurs suspectes (tous champs string)
        for k, v in f.items():
            if _suspicious_string(v):
                suspicious_values[k] += 1

        # Distribution par phase / niveau / domaine / source
        if f.get("phase"):
            phase_counts[f["phase"]] += 1
        if f.get("niveau"):
            niveau_counts[f["niveau"]] += 1
        if f.get("domaine"):
            domaine_counts[f["domaine"]] += 1
        if f.get("source"):
            source_counts[f["source"]] += 1

        # Signature pour dedup
        signatures[_signature(f)] += 1

    # Doublons = signatures apparaissant plus d'une fois
    duplicates = {sig: count for sig, count in signatures.items() if count > 1 and sig != "||"}

    # Valeurs hors bornes (taux_admission in [0,1] typique MonMaster)
    out_of_bounds_taux_admission = sum(
        1 for f in data
        if isinstance(f, dict) and isinstance(f.get("taux_admission"), (int, float))
        and not (0.0 <= f["taux_admission"] <= 1.0)
    )

    return {
        "file": path.name,
        "total": total,
        "missing_critical": dict(missing_critical),
        "suspicious_values": dict(suspicious_values),
        "phase_counts": dict(phase_counts),
        "niveau_counts": dict(niveau_counts),
        "domaine_counts_top5": dict(domaine_counts.most_common(5)),
        "source_counts": dict(source_counts),
        "duplicates_count": len(duplicates),
        "duplicates_top5": [{"sig": s, "count": c} for s, c in
                            sorted(duplicates.items(), key=lambda x: -x[1])[:5]],
        "out_of_bounds_taux_admission": out_of_bounds_taux_admission,
    }


def audit_stats(path: Path, info: dict[str, Any]) -> dict[str, Any]:
    """Audit léger pour métiers / stats (pas le même schéma que fiches)."""
    try:
        data = _load_json(path)
    except Exception as exc:
        return {"file": path.name, "error": f"Parse JSON fail: {exc}"}
    if not isinstance(data, list):
        return {"file": path.name, "error": "Expected list"}
    total = len(data)
    return {
        "file": path.name,
        "total": total,
        "type": info["type"],
        "sample_keys": list(data[0].keys())[:10] if data else [],
    }


def run_audit() -> dict[str, Any]:
    """Exécute l'audit complet sur tous les fichiers attendus."""
    reports = []
    for fname, info in EXPECTED_SOURCES.items():
        path = PROCESSED_DIR / fname
        if not path.exists():
            reports.append({"file": fname, "status": "absent"})
            continue
        if info["type"] in STATS_TYPES:
            report = audit_stats(path, info)
        else:
            report = audit_fiches(path, info)
        report["status"] = "ok" if "error" not in report else "error"
        reports.append(report)
    return {"date": _date.today().isoformat(), "reports": reports}


def format_markdown_report(audit: dict[str, Any]) -> str:
    """Formate le résultat d'audit en markdown lisible."""
    lines = [
        f"# Audit qualité data OrientIA — {audit['date']}",
        "",
        "Généré automatiquement par `scripts/audit_data_quality.py`. ",
        "Vérifie tous les corpus normalisés dans `data/processed/`.",
        "",
        "## Résumé global",
        "",
    ]
    total_fiches = 0
    for r in audit["reports"]:
        if r.get("status") == "absent":
            lines.append(f"- ❌ **{r['file']}** : absent (ingestion pas faite localement)")
        elif r.get("status") == "error":
            lines.append(f"- 🔴 **{r['file']}** : ERREUR — {r.get('error')}")
        else:
            total = r.get("total", 0)
            if r.get("type") in STATS_TYPES:
                lines.append(f"- ℹ️  **{r['file']}** ({r.get('type')}) : {total:,} entrées")
            else:
                total_fiches += total
                miss = sum(r.get("missing_critical", {}).values())
                dup = r.get("duplicates_count", 0)
                oob = r.get("out_of_bounds_taux_admission", 0)
                flags = []
                if miss:
                    flags.append(f"{miss} manques critiques")
                if dup:
                    flags.append(f"{dup} doublons")
                if oob:
                    flags.append(f"{oob} taux hors bornes")
                flag_str = f" ⚠️ {', '.join(flags)}" if flags else " ✅"
                lines.append(f"- **{r['file']}** : {total:,} fiches{flag_str}")
    lines += [
        "",
        f"**Total fiches auditées** : {total_fiches:,}",
        "",
        "---",
        "",
        "## Détail par source",
        "",
    ]
    for r in audit["reports"]:
        if r.get("status") == "absent":
            continue
        lines += [f"### `{r['file']}`", ""]
        if r.get("status") == "error":
            lines += [f"🔴 **ERREUR** : {r['error']}", ""]
            continue
        if r.get("type") in STATS_TYPES:
            lines += [
                f"- Type : `{r.get('type')}`",
                f"- Entrées : {r.get('total', 0):,}",
                f"- Sample keys : `{r.get('sample_keys', [])}`",
                "",
            ]
            continue
        lines += [
            f"- Total : {r.get('total', 0):,}",
            f"- Distribution par phase : `{r.get('phase_counts')}`",
            f"- Distribution par niveau : `{r.get('niveau_counts')}`",
            f"- Top 5 domaines : `{r.get('domaine_counts_top5')}`",
            f"- Sources : `{r.get('source_counts')}`",
            f"- Manques critiques : `{r.get('missing_critical')}`",
            f"- Valeurs suspectes par champ : `{r.get('suspicious_values')}`",
            f"- Doublons (signatures identiques) : {r.get('duplicates_count', 0)}",
            f"- `taux_admission` hors bornes [0,1] : {r.get('out_of_bounds_taux_admission', 0)}",
        ]
        dup5 = r.get("duplicates_top5", [])
        if dup5:
            lines.append(f"- Top 5 doublons : `{dup5}`")
        lines.append("")

    # Phase distribution vs ADR-039 cible 33/33/34
    total_phase: Counter[str] = Counter()
    for r in audit["reports"]:
        for phase, count in r.get("phase_counts", {}).items():
            total_phase[phase] += count
    lines += [
        "---",
        "",
        "## Répartition phase cumulée (vs ADR-039 cible 33/33/34)",
        "",
    ]
    total_p = sum(total_phase.values())
    if total_p == 0:
        lines.append("Aucune fiche avec phase détectée.")
    else:
        for phase, count in sorted(total_phase.items(), key=lambda x: -x[1]):
            pct = 100.0 * count / total_p
            cible = "33%" if phase in ("initial", "master", "reorientation") else "N/A"
            lines.append(f"- `{phase}` : {count:,} ({pct:.1f}%) — cible {cible}")
        lines.append("")
        lines.append(
            "Si un phase dépasse 40% ou tombe sous 25% → signal de déséquilibre, "
            "action S+2 (up-sample ou down-sample)."
        )

    # Verdict GO/NO-GO D6 re-index FAISS
    critical_issues = 0
    for r in audit["reports"]:
        if r.get("status") == "error":
            critical_issues += 1
        miss = sum(r.get("missing_critical", {}).values())
        if miss > 10:
            critical_issues += 1
    lines += [
        "",
        "---",
        "",
        "## Verdict re-index FAISS (D6)",
        "",
    ]
    if critical_issues == 0:
        lines += [
            "✅ **GO** : aucune anomalie bloquante détectée. Safe to proceed avec ",
            "re-index FAISS sur corpus élargi.",
            "",
            "Action post-validation Matteo budget $5-10 :",
            "```bash",
            "python -m src.rag.embeddings  # re-build FAISS index",
            "```",
        ]
    else:
        lines += [
            f"🔴 **NO-GO** : {critical_issues} anomalie(s) critique(s) détectée(s). ",
            "Corriger avant de lancer le re-index (évite de re-embed des fiches corrompues).",
        ]

    lines += [
        "",
        "---",
        "",
        "*Rapport généré par `scripts/audit_data_quality.py`. Re-exécuter après ",
        "chaque nouvelle ingestion pour détecter les régressions.*",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        type=str,
        default=f"docs/AUDIT_DATA_QUALITY_{_date.today().isoformat()}.md",
    )
    args = parser.parse_args()
    audit = run_audit()
    report = format_markdown_report(audit)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(f"Audit sauvé → {out_path}")
    # Also print summary to stdout
    total = sum(r.get("total", 0) for r in audit["reports"] if r.get("status") == "ok")
    print(f"Total entrées auditées : {total:,}")


if __name__ == "__main__":
    main()
