"""OrientIA CLI — Sprint 10 chantier E.

CLI propre + output structuré + mesures empiriques pour audit serving
end-to-end post-bac. Repointe vers le corpus unifié 55k post-merge B+D
(formations.json/index → formations_unified.json/index).

Args :
  --with-golden-qa            Activer Q&A Golden Few-Shot retrieval (défaut True)
  --with-sop                  Activer SOP routing (défaut False — pas encore indexées)
  --use-metadata-filter       Activer filter métadonnées (défaut True)
  --output-json <path>        Logger output structuré JSON (mesures + sources)
  --question "..."            Question utilisateur (sinon arg positionnel)

Sortie standard : Q&A Golden top-1 (si activé) + 10 fiches top-k filtered + réponse
Mistral + sources + 3 mesures empiriques (latences breakdown / filter stats).

Output JSON optionnel (`--output-json`) : log complet structuré pour audit.

Spec ordre Jarvis : 2026-04-29-1146-claudette-orientia-sprint10-finalisation-rag-complet (chantier E).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from mistralai.client import Mistral

from src.config import load_config
from src.rag.metadata_filter import FilterCriteria
from src.rag.pipeline import OrientIAPipeline


# Sprint 10 chantier E — repointage vers corpus unifié post-merge B
FICHES_PATH = "data/processed/formations_unified.json"
INDEX_PATH = "data/embeddings/formations_unified.index"

# Sprint 10 chantier D — Q&A Golden artifacts (chantier D mergé sur main)
GOLDEN_QA_INDEX_PATH = "data/embeddings/golden_qa.index"
GOLDEN_QA_META_PATH = "data/processed/golden_qa_meta.json"


def _format_fiche_summary(item: dict) -> str:
    """Render compact d'une fiche pour stdout."""
    f = item.get("fiche") or {}
    score = item.get("score", 0.0)
    nom = f.get("nom") or f.get("title") or "(sans nom)"
    etab = f.get("etablissement") or ""
    ville = f.get("ville") or ""
    niveau = f.get("niveau") or "?"
    statut = f.get("statut") or ""
    region = f.get("region_canonical") or f.get("region") or ""
    parts = [nom[:65]]
    if etab:
        parts.append(f"@ {etab[:50]}")
    if ville:
        parts.append(ville)
    meta_bits = [b for b in (niveau, statut, region) if b]
    meta_str = " | ".join(meta_bits) if meta_bits else ""
    return f"  [score={score:.3f}] {' '.join(parts)} | {meta_str}"


def parse_cli() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="OrientIA CLI — test serving end-to-end")
    p.add_argument("question", nargs="?", default=None,
                   help="Question utilisateur (ou utilise --question)")
    p.add_argument("--question", dest="question_flag", default=None)
    p.add_argument("--with-golden-qa", action="store_true", default=True,
                   help="Activer Q&A Golden Few-Shot retrieval (défaut True)")
    p.add_argument("--no-golden-qa", action="store_false", dest="with_golden_qa",
                   help="Désactiver Q&A Golden")
    p.add_argument("--with-sop", action="store_true", default=False,
                   help="Activer SOP routing (défaut False — pas encore indexées)")
    p.add_argument("--use-metadata-filter", action="store_true", default=True,
                   help="Activer filter métadonnées (défaut True)")
    p.add_argument("--no-metadata-filter", action="store_false", dest="use_metadata_filter",
                   help="Désactiver filter métadonnées")
    p.add_argument("--criteria-region", type=str, default=None,
                   help="Critère region (ex 'occitanie')")
    p.add_argument("--criteria-secteur", type=str, default=None,
                   help="Critère secteur (ex 'informatique')")
    p.add_argument("--output-json", type=Path, default=None,
                   help="Si fourni, logger output structuré JSON")
    p.add_argument("--top-k-sources", type=int, default=10,
                   help="Nombre de fiches passées au generator (défaut 10)")
    p.add_argument("--interactive", "-i", action="store_true",
                   help="Mode REPL interactif avec history session in-memory "
                        "(Sprint 11 P0 Item 2). Sortie via /quit ou Ctrl+D.")
    return p.parse_args()


def build_criteria(args: argparse.Namespace) -> FilterCriteria | None:
    """Construit FilterCriteria depuis args CLI. Retourne None si tout vide."""
    secteurs = [args.criteria_secteur] if args.criteria_secteur else None
    criteria = FilterCriteria(region=args.criteria_region, secteur=secteurs)
    return criteria if not criteria.is_empty() else None


def run_interactive_repl(pipeline: OrientIAPipeline, args: argparse.Namespace,
                         criteria: FilterCriteria | None) -> int:
    """Sprint 11 P0 Item 2 — REPL interactif avec history session in-memory.

    Capture history user/assistant alternés, ré-injecte au call suivant pour
    permettre suivi de tiroirs ("Oui Plan A" → développe). Pas de persistance
    disque v1 (out of scope, à voir Sprint 11+ avec session storage).

    Sortie via /quit, /exit, /q ou Ctrl+D / Ctrl+C.
    Commandes :
        /reset    — vide history (recommence stateless)
        /history  — affiche history courante
    """
    print(f"\n{'=' * 70}")
    print("OrientIA REPL interactif — buffer mémoire short-term")
    print("Tape ta question, /quit pour sortir, /reset pour vider history.")
    print('=' * 70)

    history: list[dict] = []
    turn = 1

    while True:
        try:
            print()
            user_input = input(f"[Tour {turn}] » ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 À bientôt !")
            break

        if not user_input:
            continue
        if user_input in ("/quit", "/exit", "/q"):
            print("👋 À bientôt !")
            break
        if user_input == "/reset":
            history = []
            turn = 1
            print("🔄 History vidée, retour stateless.")
            continue
        if user_input == "/history":
            print(f"📜 History courante ({len(history)} messages) :")
            for i, msg in enumerate(history, 1):
                preview = msg["content"][:80].replace("\n", " ")
                print(f"  {i}. [{msg['role']}] {preview}{'...' if len(msg['content']) > 80 else ''}")
            continue

        t_start = time.time()
        answer, top = pipeline.answer(
            user_input,
            top_k_sources=args.top_k_sources,
            criteria=criteria,
            history=history if history else None,  # None plutôt que [] pour passer le path v1 si vide
        )
        elapsed_ms = (time.time() - t_start) * 1000

        print(f"\n--- RÉPONSE (t={elapsed_ms:.0f}ms, {len(top)} sources) ---")
        print(answer)

        # Append à history pour le tour suivant
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": answer})
        turn += 1

    return 0


def main() -> int:
    args = parse_cli()
    question = args.question or args.question_flag
    if not question and not args.interactive:
        question = "Quelles sont les meilleures formations en cybersécurité en France ?"

    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key)

    print(f"==> Loading corpus from {FICHES_PATH} ...", flush=True)
    fiches = json.loads(Path(FICHES_PATH).read_text(encoding="utf-8"))
    print(f"    {len(fiches)} fiches loaded")

    pipeline_kwargs = {
        "use_metadata_filter": args.use_metadata_filter,
        "use_golden_qa": args.with_golden_qa,
    }
    if args.with_golden_qa:
        pipeline_kwargs["golden_qa_index_path"] = GOLDEN_QA_INDEX_PATH
        pipeline_kwargs["golden_qa_meta_path"] = GOLDEN_QA_META_PATH

    pipeline = OrientIAPipeline(client, fiches, **pipeline_kwargs)

    if Path(INDEX_PATH).exists():
        print(f"==> Loading cached index from {INDEX_PATH} ...", flush=True)
        pipeline.load_index_from(INDEX_PATH)
    else:
        print(f"⚠️  Index absent : {INDEX_PATH}")
        print(f"    Run : PYTHONPATH=. python3 scripts/embed_unified.py")
        return 1

    criteria = build_criteria(args)

    # Sprint 11 P0 Item 2 — dispatch REPL si --interactive
    if args.interactive:
        return run_interactive_repl(pipeline, args, criteria)

    print(f"\n{'=' * 70}")
    print(f"QUESTION: {question}")
    if criteria is not None:
        print(f"CRITERIA: {criteria}")
    print(f"FLAGS: with_golden_qa={args.with_golden_qa}, use_metadata_filter={args.use_metadata_filter}")
    print('=' * 70)

    # Chantier E-3 : timestamping empirique latence
    t_start = time.time()
    answer, top = pipeline.answer(
        question, top_k_sources=args.top_k_sources, criteria=criteria,
    )
    t_total_ms = (time.time() - t_start) * 1000

    # Mesures collectées par le pipeline
    last_filter_stats = pipeline.last_filter_stats or {}
    last_golden_qa = pipeline.last_golden_qa or {}

    print(f"\n--- RÉPONSE ---\n{answer}")

    print(f"\n--- SOURCES TOP-{len(top)} ---")
    for item in top:
        print(_format_fiche_summary(item))

    print(f"\n--- MESURES EMPIRIQUES (chantier E) ---")
    print(f"  t_total_ms : {t_total_ms:.0f} ms")
    print(f"  filter_stats : {last_filter_stats}")
    if last_golden_qa.get("active"):
        print(f"  golden_qa : matched={last_golden_qa.get('matched')} "
              f"prompt_id={last_golden_qa.get('prompt_id')} "
              f"score_total={last_golden_qa.get('score_total')} "
              f"retrieve_score={last_golden_qa.get('retrieve_score'):.3f}"
              if last_golden_qa.get('retrieve_score') is not None
              else f"  golden_qa : matched={last_golden_qa.get('matched')}")
    else:
        print(f"  golden_qa : inactive")

    # Chantier E-2 — output structuré JSON optionnel
    if args.output_json:
        output = {
            "question": question,
            "criteria": {
                "region": args.criteria_region,
                "secteur": args.criteria_secteur,
            },
            "flags": {
                "with_golden_qa": args.with_golden_qa,
                "with_sop": args.with_sop,
                "use_metadata_filter": args.use_metadata_filter,
                "top_k_sources": args.top_k_sources,
            },
            "answer": answer,
            "sources": [
                {
                    "score": item.get("score"),
                    "fiche_id": (item.get("fiche") or {}).get("id"),
                    "nom": (item.get("fiche") or {}).get("nom") or (item.get("fiche") or {}).get("title"),
                    "etablissement": (item.get("fiche") or {}).get("etablissement"),
                    "ville": (item.get("fiche") or {}).get("ville"),
                    "region": (item.get("fiche") or {}).get("region_canonical") or (item.get("fiche") or {}).get("region"),
                    "niveau": (item.get("fiche") or {}).get("niveau_int") or (item.get("fiche") or {}).get("niveau"),
                    "secteur": (item.get("fiche") or {}).get("secteur_canonical") or (item.get("fiche") or {}).get("secteur"),
                    "url": (item.get("fiche") or {}).get("lien_form_psup") or (item.get("fiche") or {}).get("url_onisep") or (item.get("fiche") or {}).get("url"),
                }
                for item in top
            ],
            "measures": {
                "t_total_ms": round(t_total_ms),
                "filter_stats": last_filter_stats,
                "golden_qa": last_golden_qa,
            },
        }
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(
            json.dumps(output, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\n==> Output JSON sauvé : {args.output_json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
