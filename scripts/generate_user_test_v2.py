"""Generate user test v2 answers using the Tier 2 updated pipeline.

Re-generates the 10 user-test questions (same as v1 2026-04-17) with
the post-Tier 2 system: pyramide inversée + brièveté 150-300 mots +
détection niveau user + format guidance par intent.

Output : results/user_test_v2/answers_to_show.md + responses.json.
Ready for re-test by the same 4 profiles (ADR-027 success criteria).

Cost estimate : ~$0.10-0.30 Mistral medium (10 questions, ~300 mots
each at 200 tokens/answer + 1500 tokens context × 10).
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from mistralai.client import Mistral

from src.config import load_config
from src.rag.pipeline import OrientIAPipeline


FICHE_PATH = Path("data/processed/formations.json")
INDEX_PATH = "data/embeddings/formations.index"
OUT_DIR = Path("results/user_test_v2")
OUT_PATH = OUT_DIR / "answers_to_show.md"
RESPONSES_JSON = OUT_DIR / "responses.json"


QUESTIONS: list[tuple[str, str]] = [
    # cyber / data (6)
    ("realisme", "J'ai 11 de moyenne en terminale générale, est-ce que je peux intégrer HEC ?"),
    ("biais_marketing", "Quelles sont les meilleures formations en cybersécurité en France ?"),
    ("comparaison", "Compare ENSEIRB-MATMECA et EPITA pour la cybersécurité"),
    ("honnetete", "C'est quoi une licence universitaire en France ?"),
    ("passerelles", "Je suis en L2 droit et je veux me réorienter vers l'informatique, comment ?"),
    ("diversite_geo", "Quelles bonnes formations existent à Perpignan ?"),
    # santé (4)
    ("decouverte_sante", "Je veux devenir médecin, comment faire ?"),
    ("realisme_sante", "J'ai 12 de moyenne générale en terminale, est-ce que j'ai mes chances en PASS ?"),
    ("comparaison_sante", "Compare devenir infirmier et kinésithérapeute : études, salaires, débouchés."),
    ("passerelles_sante", "Je suis en L2 psychologie et je veux me réorienter vers l'orthophonie, comment ?"),
]


def main() -> None:
    config = load_config()
    if not config.mistral_api_key:
        raise RuntimeError("MISTRAL_API_KEY missing — check .env")

    client = Mistral(api_key=config.mistral_api_key, timeout_ms=120000)
    fiches = json.loads(FICHE_PATH.read_text(encoding="utf-8"))
    print(f"Loaded {len(fiches)} fiches")

    pipeline = OrientIAPipeline(
        client=client,
        fiches=fiches,
        use_mmr=True,
        use_intent=True,
    )
    pipeline.load_index_from(INDEX_PATH)
    print(f"Loaded FAISS index from {INDEX_PATH}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    lines: list[str] = [
        "# OrientIA — Réponses test utilisateur v2 (post-Tier 2)",
        "",
        f"*Généré le {datetime.now().strftime('%Y-%m-%d %H:%M')} — SYSTEM_PROMPT v3.2 + sanity UX α/β + Tier 0 + Tier 2.1-2.3*",
        "",
        "Ce document contient les 10 mêmes questions que le pack v1 (2026-04-17) "
        "re-générées avec le système post-Tier 2 : pyramide inversée + brièveté "
        "150-300 mots + détection niveau user + format adapté par type de question.",
        "",
        "**Objectif** : re-test par les 4 mêmes profils (Léo 17, Sarah 20, "
        "Thomas 23, Catherine 52, Dominique 48) sur les 10 mêmes questions. "
        "Critères de succès (ADR-027) :",
        "- Léo 17 passe de « décroche à la moitié » à « lu en entier »",
        "- Sarah 20 cesse de se sentir infantilisée par le template A/B/C",
        "- Catherine 52 cesse de relever des erreurs factuelles graves",
        "- Dominique 48 recommanderait l'outil à un élève seul",
        "",
        "---",
        "",
    ]

    answers_data: list[dict] = []
    for i, (category, question) in enumerate(QUESTIONS, 1):
        print(f"Q{i}/{len(QUESTIONS)} [{category}]: {question[:80]}...")
        answer, _retrieved = pipeline.answer(question, k=30, top_k_sources=10)
        word_count = len(answer.split())
        print(f"  → {word_count} mots")

        lines.extend([
            f"## Question {i} — [{category}]",
            "",
            f"> **{question}**",
            "",
            f"*Word count : {word_count} mots*",
            "",
            "### Réponse OrientIA v2",
            "",
            answer,
            "",
            "---",
            "",
        ])

        answers_data.append({
            "question_num": i,
            "category": category,
            "question": question,
            "answer": answer,
            "word_count": word_count,
        })

    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    RESPONSES_JSON.write_text(
        json.dumps(answers_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    mean_wc = sum(a["word_count"] for a in answers_data) / len(answers_data)
    wcs = sorted(a["word_count"] for a in answers_data)
    print("\n=== Statistiques ===")
    print(f"Mean word count : {mean_wc:.0f}")
    print(f"Min / median / max : {wcs[0]} / {wcs[len(wcs)//2]} / {wcs[-1]}")
    print(f"Within 150-300 target : {sum(1 for w in wcs if 150 <= w <= 300)}/{len(wcs)}")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
