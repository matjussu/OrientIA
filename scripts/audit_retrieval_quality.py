"""Audit qualité retrieval — répond à 'la data sert-elle vraiment la question ?'.

Utilise phase_a_with_sources.json (top_sources retrievées par question) pour
mesurer 3 dimensions :

1. **Recall topical** : la question récupère-t-elle des fiches du bon thème ?
   Heuristique : la question a des mots-clés thématiques (cyber, droit, etc.)
   → au moins X% des top_sources doivent matcher ces mots-clés.

2. **Couverture chiffres** : les fiches contiennent-elles les champs
   stat-rich (taux_acces, salaire, places, insertion_pro) que la réponse
   tente de citer ?

3. **Spécificité** : les fiches sont-elles précises (école nommée + ville)
   ou génériques (titres RNCP nationaux sans école) ?

Output : tableau par question + verdict global "data ok / off-topic /
trop générique / sans stats".
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# Mots-clés thématiques attendus par question (basé sur le contenu de
# tests/mini_bench/questions_20.json)
EXPECTED_KEYWORDS = {
    "A1": {"cyber", "cybersécur", "sécurité"},
    "A3": {"informatique", "info", "ingénieur"},
    "H4": {"ects", "crédit", "licence", "master"},
    "H8": {"secnumedu", "anssi", "cyber"},
    "H9": {"cti", "ingénieur"},
    "H1": {"licence", "université"},
    "C1": {"data", "donnée", "géopolit", "international"},
    "C5": {"environnement", "écolog", "informatique"},
    "D5": {"cyber", "bretagne", "rennes", "brest", "vannes", "lorient"},
    "E5": {"cyber", "alternance", "reconversion", "continue"},
    "F1": {"enseirb", "epita", "cyber", "ingénieur"},
    "F3": {"bts sio", "but informatique", "but réseau"},
    "F6": {"insa", "informatique", "lyon", "toulouse"},
    "B1": {"hec", "commerce", "école"},
    "B5": {"sciences po", "iep", "politique"},
    "X1": {"cyber", "brest", "secnumedu"},
    "X2": {"cyber", "master", "anssi"},
    "Z1": {"droit", "fiscal", "avocat", "barreau", "juridique"},
}

STAT_FIELDS = {
    "taux_acces_parcoursup_2025",
    "nombre_places",
    "duree",
    "frais_annuels",
    "taux_admission",
    "n_candidats_pp",
    "n_acceptes_total",
}


def fiche_text_blob(summary: str) -> str:
    return summary.lower()


def has_keyword(blob: str, keywords: set[str]) -> bool:
    return any(kw in blob for kw in keywords)


def has_stat_field(summary: str) -> bool:
    return any(f in summary for f in STAT_FIELDS) or "insertion." in summary


def is_specific(summary: str) -> bool:
    return ("etablissement=" in summary) and ("ville=" in summary)


def audit_question(qid: str, top_sources: list[dict]) -> dict:
    keywords = EXPECTED_KEYWORDS.get(qid, set())
    n_sources = len(top_sources)
    if n_sources == 0:
        return {
            "qid": qid,
            "n_sources": 0,
            "topical_match_pct": None,
            "stat_rich_pct": None,
            "specific_pct": None,
            "verdict_retrieval": "no_retrieval",
        }

    blobs = [fiche_text_blob(s.get("summary", "")) for s in top_sources]
    n_topical = sum(1 for b in blobs if has_keyword(b, keywords)) if keywords else None
    n_stat = sum(1 for b in blobs if has_stat_field(b))
    n_specific = sum(1 for b in blobs if is_specific(b))

    topical_pct = round(100 * n_topical / n_sources, 1) if n_topical is not None else None
    stat_pct = round(100 * n_stat / n_sources, 1)
    specific_pct = round(100 * n_specific / n_sources, 1)

    if topical_pct is None:
        verdict = "no_keyword_baseline"
    elif topical_pct < 30:
        verdict = "off_topic"
    elif specific_pct < 30:
        verdict = "too_generic"
    elif stat_pct < 30:
        verdict = "no_stats_in_sources"
    else:
        verdict = "ok"

    return {
        "qid": qid,
        "n_sources": n_sources,
        "expected_keywords": sorted(keywords),
        "topical_match_pct": topical_pct,
        "stat_rich_pct": stat_pct,
        "specific_pct": specific_pct,
        "verdict_retrieval": verdict,
        "examples_top3": [s.get("summary", "")[:250] for s in top_sources[:3]],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bench", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    bench = json.loads(args.bench.read_text(encoding="utf-8"))
    audit_records = []
    verdict_counts: Counter = Counter()

    for rec in bench["unimodal_results"]:
        qid = rec["id"]
        sources = rec.get("top_sources") or []
        a = audit_question(qid, sources)
        a["question"] = rec["question"]
        a["category"] = rec.get("category")
        verdict_counts[a["verdict_retrieval"]] += 1
        audit_records.append(a)

    out_payload = {
        "metadata": {
            "source_bench": str(args.bench),
            "n_processed": len(audit_records),
            "verdict_counts": dict(verdict_counts),
        },
        "audit_records": audit_records,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{'qid':<6} {'n_src':>5} {'topic%':>7} {'stat%':>7} {'spec%':>7} {'verdict':<22} | expected_keywords")
    print("-" * 100)
    for a in audit_records:
        kws = ",".join(a["expected_keywords"])[:35]
        topical = a["topical_match_pct"] if a["topical_match_pct"] is not None else "—"
        print(f"{a['qid']:<6} {a['n_sources']:>5} {str(topical):>7} {a['stat_rich_pct']:>7} "
              f"{a['specific_pct']:>7} {a['verdict_retrieval']:<22} | {kws}")
    print(f"\nVerdict counts: {dict(verdict_counts)}")
    print(f"\n[saved] {args.out}")


if __name__ == "__main__":
    main()
