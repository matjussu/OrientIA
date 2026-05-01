"""Sprint 12 D1+D5 — validation retrieval ciblée profil + insertion.

Référence ordres :
- 2026-05-01-1659-claudette-orientia-sprint12-D1-profil-admis-expose-rag (S4)
- 2026-05-01-1659-claudette-orientia-sprint12-D5-inserjeunes-insersup-data-gouv (S6)

## Stratégie

Build mutualisé D1+D5 sur D5 branch (cherry-pick D1 commit local). 1
seul appel `python -m scripts.embed_unified` couvre les 2 changements
fiche_to_text (section Profil des admis Sprint 12 D1 + section
Insertion pro source InserSup Sprint 12 D5). Économie ~$5-10 vs 2
re-builds séparés.

Validation indépendante : 2 sets de questions ciblées séparées.
- Set A profil (D1) : 5 questions sur "qui est admis" / "profil
    bac type" / "mentions" / "boursiers"
- Set B insertion (D5) : 5 questions sur "salaire sortie" / "insertion
    6/12 mois" / "emploi" pour fiches univ master/LP/DUT

Pour chaque question :
1. Compute query embedding (Mistral)
2. FAISS top-5 nearest fiches
3. Vérifier que les fiches retrieved exposent la section attendue dans
    fiche_to_text() (D1 = Profil des admis ; D5 = Insertion InserSup)

Pattern #4 strict : sample 3 questions par set documenté avec :
- Question texte
- Top-3 fiches retrieved (nom + établissement + ville)
- Section présente dans fiche_to_text de la #1 fiche retrieved : oui/non
- Extrait verbatim de la section quand présent

## Output

- `docs/sprint12-D1-D5-validation-retrieval-2026-05-01.md` — verdict
    avec sample doublé (D1 et D5 indépendants)
- `docs/sprint12-D1-D5-validation-retrieval-raw-2026-05-01.jsonl` —
    raw top-K + section presence par question

Coût : 10 queries Mistral embed × $0.0001 ≈ $0.001 (négligeable).
"""
from __future__ import annotations

import json
from pathlib import Path

import faiss
import numpy as np
from mistralai.client import Mistral

from src.config import load_config
from src.rag.embeddings import embed_texts, fiche_to_text


ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "data" / "embeddings" / "formations_unified.index"
FICHES_PATH = ROOT / "data" / "processed" / "formations_unified.json"
OUT_DOC = ROOT / "docs" / "sprint12-D1-D5-validation-retrieval-2026-05-01.md"
OUT_RAW = ROOT / "docs" / "sprint12-D1-D5-validation-retrieval-raw-2026-05-01.jsonl"


# Set A — questions ciblées profil_admis (D1)
QUESTIONS_PROFIL = [
    "Quel est le profil des admis au Bachelor cybersécurité EFREI ?",
    "Pour le Master Cybersécurité ENSIBS Vannes, combien d'admis viennent de bac techno ?",
    "Y a-t-il beaucoup de boursiers admis en école d'ingénieur post-bac ?",
    "Bachelor cybersécurité accessible bac techno avec mention bien ?",
    "Profil démographique des admis Sciences Po Paris double diplôme ?",
]

# Set B — questions ciblées insertion_pro source InserSup (D5)
QUESTIONS_INSERTION = [
    "Quel est le salaire à la sortie d'un Master Cybersécurité ENSIBS Vannes ?",
    "Insertion professionnelle à 6 mois pour un Master MIAGE Tours ?",
    "Taux d'emploi à 12 mois pour un Master informatique Paris-Saclay ?",
    "Combien gagne-t-on après un Master de droit des affaires ?",
    "Quel est le taux d'emploi à 18 mois après un Master LMD informatique ?",
]


def _has_section(fiche: dict, section_marker: str) -> bool:
    """True si la section attendue apparaît dans fiche_to_text(fiche)."""
    return section_marker in fiche_to_text(fiche)


def _extract_section_excerpt(fiche: dict, section_marker: str, length: int = 200) -> str | None:
    """Extrait verbatim ~length chars de la section dans fiche_to_text."""
    text = fiche_to_text(fiche)
    idx = text.find(section_marker)
    if idx < 0:
        return None
    return text[idx:idx + length]


def main() -> int:
    print(f"[validate] loading index : {INDEX_PATH}")
    index = faiss.read_index(str(INDEX_PATH))
    print(f"[validate] FAISS index : ntotal={index.ntotal} dim={index.d}")

    print(f"[validate] loading fiches : {FICHES_PATH}")
    with FICHES_PATH.open(encoding="utf-8") as f:
        fiches = json.load(f)
    print(f"[validate] {len(fiches)} fiches chargées")

    if index.ntotal != len(fiches):
        print(f"⚠️  Mismatch index/fiches : {index.ntotal} vs {len(fiches)} — rebuild may be incomplete")

    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key)

    results: list[dict] = []

    for label, questions, section_marker in (
        ("D1_profil", QUESTIONS_PROFIL, "Profil des admis"),
        ("D5_insertion_insersup", QUESTIONS_INSERTION, "Insertion pro (source InserSup MESR"),
    ):
        print(f"\n[validate] === {label} ({len(questions)} questions, marker '{section_marker}') ===")

        embeddings = embed_texts(client, questions)
        query_arr = np.array(embeddings, dtype="float32")

        for q_idx, q_text in enumerate(questions):
            distances, indices = index.search(query_arr[q_idx:q_idx+1], k=5)
            top_5 = [fiches[i] for i in indices[0] if i >= 0]

            section_hits = sum(1 for f in top_5 if _has_section(f, section_marker))
            top_1 = top_5[0] if top_5 else {}
            top_1_has = _has_section(top_1, section_marker) if top_1 else False
            top_1_excerpt = _extract_section_excerpt(top_1, section_marker) if top_1 else None

            result = {
                "label": label,
                "question": q_text,
                "section_marker": section_marker,
                "n_top_5_with_section": section_hits,
                "top_1_nom": top_1.get("nom"),
                "top_1_etablissement": top_1.get("etablissement"),
                "top_1_ville": top_1.get("ville"),
                "top_1_has_section": top_1_has,
                "top_1_section_excerpt": top_1_excerpt,
                "top_5_summary": [
                    {
                        "nom": f.get("nom"),
                        "etablissement": f.get("etablissement"),
                        "ville": f.get("ville"),
                        "has_section": _has_section(f, section_marker),
                    }
                    for f in top_5
                ],
            }
            results.append(result)

            print(f"\n  Q : {q_text}")
            print(f"  Top-1 : {top_1.get('nom')} — {top_1.get('etablissement')} ({top_1.get('ville')})")
            print(f"  Section '{section_marker}' présente top-1 : {top_1_has}")
            print(f"  Section présente sur n/5 : {section_hits}/5")
            if top_1_excerpt:
                print(f"  Excerpt : {top_1_excerpt[:150]}...")

    # Save raw + summary
    with OUT_RAW.open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n[validate] raw saved : {OUT_RAW}")

    # Aggregate metrics par label
    print("\n========== SUMMARY ==========")
    for label in ("D1_profil", "D5_insertion_insersup"):
        sub = [r for r in results if r["label"] == label]
        n_q = len(sub)
        top_1_hit_rate = sum(1 for r in sub if r["top_1_has_section"]) / n_q
        avg_top_5 = sum(r["n_top_5_with_section"] for r in sub) / n_q
        print(f"{label} (n={n_q}) : top-1 hit rate = {top_1_hit_rate:.0%}, avg top-5 = {avg_top_5:.1f}/5")
    print("==============================")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
