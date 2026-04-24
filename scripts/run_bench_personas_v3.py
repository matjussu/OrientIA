"""Bench OrientIA — 6 personas × 3 queries = 18 queries (2026-04-24).

Objectif : baseline post D6 re-index sur corpus v2 48 914 fiches +
rééquilibrage phase ADR-039 (CFA integration).

Personas :
1. Lila (17 ans, Terminale L, indécise) — scope initial
2. Théo (19 ans, L2 Droit échec) — scope réorientation
3. Emma (22 ans, M1 Info) — scope master-pro
4. Mohamed (17 ans, CAP cuisine) — voie pro/apprentissage
5. Valérie (parent) — perspective externe
6. Psy-EN (pro accompagnateur) — persona ground truth

Usage :
    python scripts/run_bench_personas.py                    # tous les personas
    python scripts/run_bench_personas.py --persona lila     # un seul
    python scripts/run_bench_personas.py --max 2            # 2 premiers personas

Output : `results/bench_personas_v3_2026-04-24/` avec :
- `query_<N>_<persona>_<qN>.json` par query (prompt + réponse + sources)
- `_SYNTHESIS.md` tableau notation + observations (généré à la fin)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mistralai.client import Mistral  # noqa: E402
from src.config import load_config  # noqa: E402
from src.rag.pipeline import OrientIAPipeline  # noqa: E402


FICHES_PATH = REPO_ROOT / "data" / "processed" / "formations.json"
INDEX_PATH = REPO_ROOT / "data" / "embeddings" / "formations.index"
OUT_DIR = REPO_ROOT / "results" / "bench_personas_v3_2026-04-24"


PERSONAS: list[dict[str, Any]] = [
    {
        "id": "lila",
        "description": "Lila, 17 ans, Terminale L indécise (scope initial)",
        "scope": "initial",
        "queries": [
            {"id": "q1", "type": "factuelle", "text":
                "Quels sont les principaux débouchés après une licence de lettres modernes ?"},
            {"id": "q2", "type": "orientation_ambigue", "text":
                "J'hésite entre une fac de sciences humaines et une école de communication à Paris, pourquoi choisir l'une plutôt que l'autre ?"},
            {"id": "q3", "type": "contextuelle_riche", "text":
                "Je suis en Terminale L, j'ai 14 de moyenne, j'aime écrire et j'aime l'histoire mais je ne veux pas être prof. Je cherche un parcours post-bac qui me laisse plusieurs options métiers ouvertes."},
        ],
    },
    {
        "id": "theo",
        "description": "Théo, 19 ans, L2 Droit en échec (scope réorientation)",
        "scope": "reorientation",
        "queries": [
            {"id": "q1", "type": "factuelle", "text":
                "Quelles passerelles existent après une L1/L2 de droit pour aller vers un BTS ou une école de commerce ?"},
            {"id": "q2", "type": "orientation_ambigue", "text":
                "Je n'aime pas du tout le droit, je ne veux pas redoubler. Qu'est-ce qui est le plus réaliste cette année pour me réorienter ?"},
            {"id": "q3", "type": "contextuelle_riche", "text":
                "J'ai validé ma L1 de droit mais je galère en L2, je pense à me réorienter vers l'audiovisuel ou le commerce, si possible en alternance. J'habite à Bordeaux, quelles options concrètes ?"},
        ],
    },
    {
        "id": "emma",
        "description": "Emma, 22 ans, M1 Info (scope master-pro)",
        "scope": "master_pro",
        "queries": [
            {"id": "q1", "type": "factuelle", "text":
                "Quel est le salaire moyen d'un développeur débutant post M2 informatique en France ?"},
            {"id": "q2", "type": "orientation_ambigue", "text":
                "Je finis mon M1 info, je dois choisir entre un M2 classique recherche ou un master en alternance. Qu'est-ce qui me donnera le meilleur CV pour entrer en CDI direct ?"},
            {"id": "q3", "type": "contextuelle_riche", "text":
                "Je suis en M1 info à l'université de Lille, j'aime la data et le ML, je ne sais pas si je dois viser grosse boîte tech type Doctolib ou Criteo, ou plutôt une startup early-stage. Je veux un poste CDI dès la sortie, pas un CDD recherche."},
        ],
    },
    {
        "id": "mohamed",
        "description": "Mohamed, 17 ans, CAP cuisine (voie pro/apprentissage)",
        "scope": "voie_pro",
        "queries": [
            {"id": "q1", "type": "factuelle", "text":
                "Quels sont les principaux débouchés métier après un Bac pro cuisine par apprentissage ?"},
            {"id": "q2", "type": "orientation_ambigue", "text":
                "J'ai fini mon CAP cuisine, je ne suis plus sûr de vouloir rester en restauration. Qu'est-ce que je peux faire d'autre avec ce CAP ?"},
            {"id": "q3", "type": "contextuelle_riche", "text":
                "Je suis en CAP cuisine à Marseille, je veux continuer en Bac pro alternance mais j'hésite entre cuisine et boulangerie-pâtisserie. Salaires, perspectives, contraintes de rythme ?"},
        ],
    },
    {
        "id": "valerie",
        "description": "Valérie, parent de lycéen (perspective externe)",
        "scope": "parent",
        "queries": [
            {"id": "q1", "type": "factuelle", "text":
                "Quel est le coût moyen d'une année d'école de commerce privée par rapport à une licence publique ?"},
            {"id": "q2", "type": "orientation_ambigue", "text":
                "Mon fils veut faire STAPS mais je m'inquiète des débouchés. Est-ce un choix raisonnable aujourd'hui ?"},
            {"id": "q3", "type": "contextuelle_riche", "text":
                "Mon fils est en Terminale S, moyenne 13, il adore le sport. Il hésite entre STAPS et kiné. On n'a pas les moyens d'une école privée chère. Quelles voies publiques les plus sûres ?"},
        ],
    },
    {
        "id": "psy_en",
        "description": "Psy-EN (psychologue Éducation nationale)",
        "scope": "pro",
        "queries": [
            {"id": "q1", "type": "factuelle", "text":
                "Quels sont les indicateurs d'insertion professionnelle à 3 ans pour un master en psychologie clinique en France ?"},
            {"id": "q2", "type": "orientation_ambigue", "text":
                "Une élève en 1ère S redouble avec 7 de moyenne en maths mais excellente en philo, comment la guider vers un post-bac réaliste ?"},
            {"id": "q3", "type": "contextuelle_riche", "text":
                "J'accompagne un élève de 2nde issu d'un milieu modeste, qui rêve de devenir ingénieur aéro mais ses résultats sont moyens (10-11 en maths). Quelles stratégies long-terme sur la suite du lycée ?"},
        ],
    },
]


def _run_one_query(
    pipeline: OrientIAPipeline,
    persona: dict,
    query: dict,
    idx: int,
) -> dict:
    """Execute 1 query + collecte résultats pour notation."""
    t0 = time.time()
    answer, sources = pipeline.answer(query["text"])
    elapsed = time.time() - t0

    return {
        "idx_global": idx,
        "persona_id": persona["id"],
        "persona_description": persona["description"],
        "scope": persona["scope"],
        "query_id": query["id"],
        "query_type": query["type"],
        "query_text": query["text"],
        "elapsed_s": round(elapsed, 2),
        "answer": answer,
        "n_sources": len(sources),
        "sources_top10": [
            {
                "score": round(float(s.get("score", 0)), 4),
                "nom": s["fiche"].get("nom", "")[:100],
                "etablissement": s["fiche"].get("etablissement", ""),
                "ville": s["fiche"].get("ville", ""),
                "niveau": s["fiche"].get("niveau"),
                "phase": s["fiche"].get("phase"),
                "source": s["fiche"].get("source"),
                "domaine": s["fiche"].get("domaine"),
                "labels": s["fiche"].get("labels") or [],
            }
            for s in sources[:10]
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Bench personas OrientIA 2026-04-24")
    parser.add_argument("--persona", type=str, default=None, help="ID persona spécifique (ex lila)")
    parser.add_argument("--max", type=int, default=None, help="Limite N premiers personas")
    args = parser.parse_args()

    if not FICHES_PATH.exists():
        print(f"❌ formations.json absent — lance le pipeline v2 d'abord.")
        return 1
    if not INDEX_PATH.exists():
        print(f"❌ FAISS index absent — build D6 d'abord.")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Loading config + Mistral client…")
    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key)

    print(f"Loading {FICHES_PATH}…")
    fiches = json.loads(FICHES_PATH.read_text(encoding="utf-8"))
    print(f"  {len(fiches):,} fiches")

    print(f"Loading cached FAISS index {INDEX_PATH}…")
    pipeline = OrientIAPipeline(client, fiches)
    pipeline.load_index_from(str(INDEX_PATH))

    # Sélection personas
    personas_to_run = PERSONAS
    if args.persona:
        personas_to_run = [p for p in PERSONAS if p["id"] == args.persona]
        if not personas_to_run:
            print(f"❌ persona {args.persona!r} non trouvé.")
            return 1
    if args.max is not None:
        personas_to_run = personas_to_run[: args.max]

    print(f"\nRunning bench : {len(personas_to_run)} persona(s) × 3 queries = "
          f"{len(personas_to_run) * 3} queries")
    print("=" * 60)

    idx = 0
    all_results: list[dict] = []
    for persona in personas_to_run:
        print(f"\n▶ Persona {persona['id']} ({persona['description']})")
        for query in persona["queries"]:
            idx += 1
            print(f"  [{idx:2d}/{len(personas_to_run) * 3}] {query['id']} ({query['type']}) — \"{query['text'][:80]}…\"")
            try:
                result = _run_one_query(pipeline, persona, query, idx)
            except Exception as e:  # noqa: BLE001
                print(f"      ❌ erreur : {type(e).__name__}: {e}")
                result = {
                    "idx_global": idx,
                    "persona_id": persona["id"],
                    "query_id": query["id"],
                    "query_text": query["text"],
                    "error": f"{type(e).__name__}: {e}",
                }
            out_path = OUT_DIR / f"query_{idx:02d}_{persona['id']}_{query['id']}.json"
            out_path.write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            all_results.append(result)
            if "error" not in result:
                print(f"      ✓ {result['elapsed_s']}s, {result['n_sources']} sources")

    # Dump global
    all_path = OUT_DIR / "_ALL_QUERIES.json"
    all_path.write_text(
        json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n✅ Bench fini. {len(all_results)} queries → {OUT_DIR}")
    print(f"   Résumé global → {all_path}")
    print(f"\n📝 Prochaine étape : notation manuelle Claudette (5 critères × 18 queries)")
    print(f"   + synthèse Markdown → {OUT_DIR}/_SYNTHESIS.md")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
