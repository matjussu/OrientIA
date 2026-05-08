"""Spot-check manuel Phase C.5 — Gate 3 du triple-gate corpus v5.

Phase C.5 du plan corpus v5 (BLOQUANT pour promotion).
Lance le pipeline v4.1 avec le corpus v5 sur 13 questions ciblées sur les
domaines précédemment dormants (corpora annexes). Le but : vérifier que
chaque question retrouve bien sa fiche annexe et que la réponse n'est pas
"info non disponible" alors que la donnée existe.

## Critère pass

- Aucune réponse "info non disponible" sur une donnée présente dans le corpus
- Aucune hallu chiffres détectée (R1 contrat strict v4)
- Citations [source SX] présentes quand chiffres cités (R3)

## Output

Rapport markdown `docs/SPOT_CHECK_V5_<date>.md` avec, pour chaque question :
- La question
- Le domain attendu
- La réponse du pipeline
- Les top sources retrievées (id, domain, libelle)
- Évaluation manuelle requise (le script ne décide pas le pass/fail)

Usage :
    python scripts/spot_check_v5.py
    # Override paths
    ORIENTIA_CORPUS_PATH=data/processed/formations_v5.json \\
    ORIENTIA_INDEX_PATH=data/embeddings/formations_v5.index \\
    python scripts/spot_check_v5.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from mistralai.client import Mistral

from src.config import load_config
from src.rag.factory import make_production_pipeline


# ─────────────── 13 questions Gate 3 ───────────────


SPOT_CHECK_QUESTIONS: list[tuple[str, str, str]] = [
    # (question, domain attendu majoritaire dans top-K, raison/explication)
    ("Quels métiers vont recruter en Occitanie en 2030 ?",
     "metier_prospective",
     "DARES Métiers 2030 — projections recrutement par région"),
    ("Combien coûte le logement étudiant CROUS à Lyon ?",
     "crous",
     "CROUS corpus — résidences U et restos par zone"),
    ("Quels sont les blocs de compétences du RNCP 38450 ?",
     "competences_certif",
     "France Compétences blocs RNCP"),
    ("Quel salaire après un Master Droit en région PACA ?",
     "insertion_pro",
     "InserSup spécifique discipline × région"),
    ("Que fait un actuaire au quotidien ?",
     "metier_detail",
     "ROME 4.0 fiches métiers — compétences détaillées"),
    ("Quelles aides financières pour les étudiants boursiers ?",
     "financement_etudes",
     "Financement curated dispositifs"),
    ("Quelles formations en Guadeloupe ?",
     "territoire_drom",
     "DROM-COM territoires"),
    ("Marché de l'emploi cadres en Bretagne ?",
     "apec_region",
     "APEC régions"),
    ("Salaire moyen d'un cadre supérieur (PCS 37) ?",
     "insee_salaire",
     "INSEE salaires PCS"),
    ("Insertion à 3 ans après un Bac pro Industrie ?",
     "formation_insertion",
     "Inserjeunes lycée pro"),
    ("Quelles sont les spécialités possibles en BAC PRO agriculture ?",
     "voie_pre_bac",
     "Voie pré-bac catalogue"),
    ("Taux de réussite L1 pour un bac S avec mention bien ?",
     "parcours_bacheliers",
     "MESR parcours bacheliers en licence"),
    ("Quelle insertion après un doctorat en chimie ?",
     "insertion_pro",
     "Doctorat IP MESR"),
]


def _load_pipeline(corpus_path: Path, index_path: Path) -> tuple:
    """Charge le pipeline OrientIA avec corpus v5 + index v5."""
    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=120000)
    fiches = json.loads(corpus_path.read_text(encoding="utf-8"))
    print(f"Loaded {len(fiches)} fiches from {corpus_path}")
    pipeline = make_production_pipeline(client, fiches)
    pipeline.load_index_from(str(index_path))
    print(f"Loaded FAISS index from {index_path}")
    return pipeline, client


def _format_top_source(source: dict, idx: int) -> str:
    """Formate un top source pour le rapport."""
    fiche = source.get("fiche") if isinstance(source, dict) and "fiche" in source else source
    if not isinstance(fiche, dict):
        return f"  S{idx}: (non-dict)"
    domain = fiche.get("domain") or "(formation)"
    nom = (
        fiche.get("nom") or fiche.get("libelle_metier") or fiche.get("libelle")
        or fiche.get("fap_libelle") or fiche.get("subject")
        or fiche.get("id") or "(?)"
    )
    etab = fiche.get("etablissement", "")
    region = fiche.get("region", "")
    score = source.get("score") if isinstance(source, dict) else None
    score_str = f" [score={score:.3f}]" if score is not None else ""
    extra = f" — {etab}" if etab else ""
    extra += f", {region}" if region else ""
    return f"  S{idx}: [{domain}] {nom}{extra}{score_str}"


def run_spot_check(corpus_path: Path, index_path: Path, max_top_k: int = 5) -> dict:
    """Exécute le spot-check sur les 13 questions, retourne dict de résultats."""
    pipeline, client = _load_pipeline(corpus_path, index_path)
    results = []

    for i, (question, expected_domain, raison) in enumerate(SPOT_CHECK_QUESTIONS, 1):
        print(f"\n[{i}/{len(SPOT_CHECK_QUESTIONS)}] {question}")
        t0 = time.time()
        try:
            answer, top = pipeline.answer(question, top_k_sources=max_top_k)
        except Exception as e:
            results.append({
                "question": question,
                "expected_domain": expected_domain,
                "raison": raison,
                "error": str(e),
                "answer": None,
                "top_sources": [],
                "latency_s": time.time() - t0,
            })
            print(f"  ERROR: {e}")
            continue

        latency = time.time() - t0
        # Compter combien des top-K matchent le domain attendu
        domains_in_top = [
            (s.get("fiche") if isinstance(s, dict) and "fiche" in s else s).get("domain")
            for s in top[:max_top_k]
        ]
        n_expected = sum(1 for d in domains_in_top if d == expected_domain)

        # Compter les citations [source SX] dans la réponse
        import re
        n_citations = len(re.findall(r"\[source S\d+\]", answer))

        results.append({
            "question": question,
            "expected_domain": expected_domain,
            "raison": raison,
            "answer": answer,
            "top_domains": domains_in_top,
            "n_expected_domain_in_top_k": n_expected,
            "n_citations": n_citations,
            "latency_s": round(latency, 2),
            "top_sources_summary": [
                _format_top_source(s, j + 1)
                for j, s in enumerate(top[:max_top_k])
            ],
        })
        print(f"  → {n_expected}/{max_top_k} top-K avec domain attendu '{expected_domain}'")
        print(f"  → {n_citations} citations [source SX]")
        print(f"  → latency: {latency:.2f}s")

    return {
        "corpus_path": str(corpus_path),
        "index_path": str(index_path),
        "n_questions": len(SPOT_CHECK_QUESTIONS),
        "results": results,
    }


def build_report(spot_check_data: dict, date_str: str) -> str:
    """Construit le rapport markdown du spot-check."""
    results = spot_check_data["results"]
    n_total = len(results)
    n_with_expected_in_top = sum(
        1 for r in results
        if r.get("n_expected_domain_in_top_k", 0) >= 1
    )
    n_errors = sum(1 for r in results if r.get("error"))

    lines = [
        f"# Spot-check Gate 3 v5 — {date_str}",
        "",
        "> Phase C.5 (BLOQUANT pour promotion v5). 13 questions ciblées sur",
        "> les domaines précédemment dormants. Évaluation manuelle requise.",
        "",
        "## Résumé exécutif",
        "",
        f"- **Questions testées** : {n_total}",
        f"- **Questions avec domain attendu présent dans top-5** : {n_with_expected_in_top}/{n_total}",
        f"- **Erreurs runtime** : {n_errors}",
        f"- **Corpus** : `{spot_check_data['corpus_path']}`",
        f"- **Index** : `{spot_check_data['index_path']}`",
        "",
        "## Critère pass (manuel)",
        "",
        "Pour chaque question, vérifier :",
        "1. La réponse n'est pas \"info non disponible\" (sauf si vraiment data absente)",
        "2. Les chiffres cités sont accompagnés de `[source SX]` (R3)",
        "3. Le top-K retrieve contient au moins 1 fiche du domain attendu",
        "4. Pas d'invention de fiche / établissement / chiffre absent du corpus (R1, R2)",
        "",
        "## Détails par question",
        "",
    ]

    for i, r in enumerate(results, 1):
        lines.append(f"### Q{i} — {r['question']}")
        lines.append("")
        lines.append(f"**Domain attendu** : `{r['expected_domain']}` ({r['raison']})")
        lines.append("")

        if r.get("error"):
            lines.append(f"❌ **Erreur runtime** : `{r['error']}`")
            lines.append("")
            continue

        n_exp = r.get("n_expected_domain_in_top_k", 0)
        verdict = "✓" if n_exp >= 1 else "⚠"
        lines.append(f"**Top-5 domain match** : {verdict} {n_exp}/5 fiches du domain attendu")
        lines.append(f"**Citations [source SX]** : {r.get('n_citations', 0)}")
        lines.append(f"**Latence** : {r.get('latency_s', 0)}s")
        lines.append("")
        lines.append("**Top-5 sources retrievées** :")
        lines.append("```")
        for src_str in r.get("top_sources_summary", []):
            lines.append(src_str)
        lines.append("```")
        lines.append("")
        lines.append("**Réponse du pipeline** :")
        lines.append("")
        lines.append("```")
        answer = r.get("answer", "(vide)")
        lines.append(answer[:2000] + ("..." if len(answer) > 2000 else ""))
        lines.append("```")
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.extend([
        "## Décision Gate 3 (manuel)",
        "",
        "Après lecture des 13 réponses ci-dessus, indiquer :",
        "- ✓ GO promotion (toutes questions passent les 4 critères)",
        "- ⚠ GO conditionnel (1-3 questions à expliquer mais corpus utilisable)",
        "- ❌ NO-GO (≥4 questions avec hallu, info non disponible non-justifiée, ou top-K mal retrouvé)",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--corpus", default=os.environ.get("ORIENTIA_CORPUS_PATH",
                                            "data/processed/formations_v5.json"),
    )
    parser.add_argument(
        "--index", default=os.environ.get("ORIENTIA_INDEX_PATH",
                                            "data/embeddings/formations_v5.index"),
    )
    parser.add_argument("--output", default=None)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    corpus_path = Path(args.corpus)
    index_path = Path(args.index)
    if not corpus_path.exists():
        print(f"❌ Corpus absent : {corpus_path}", file=sys.stderr)
        return 1
    if not index_path.exists():
        print(f"❌ Index absent : {index_path}", file=sys.stderr)
        return 1

    spot_check_data = run_spot_check(corpus_path, index_path, max_top_k=args.top_k)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    report = build_report(spot_check_data, date_str)
    output_path = Path(args.output) if args.output else (
        PROJECT_ROOT / f"docs/SPOT_CHECK_V5_{date_str}.md"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")

    n_with_expected = sum(
        1 for r in spot_check_data["results"]
        if r.get("n_expected_domain_in_top_k", 0) >= 1
    )
    n_total = spot_check_data["n_questions"]
    print(f"\n→ {n_with_expected}/{n_total} questions ont leur domain attendu dans top-5")
    print(f"Rapport : {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
