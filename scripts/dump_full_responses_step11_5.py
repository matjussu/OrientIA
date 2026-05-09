"""Step 11.5 — Audit qualitatif PRE-Phase-D : dump des réponses complètes.

Sélectionne 10 questions critiques (couverture axes : superlatif, paraphrase,
géo, comparaison, réalisme, cross-domain), lance le pipeline COMPLET en mode
router_ON, capture pour chaque question :

- RouteDecision sérialisée (sub_indexes, criteria, refusal_reason, etc.)
- Sources top-N (NON-tronquées : nom, etab, ville, region, domain, score)
- Réponse FULL (pas d'excerpt 300 chars)
- Validation : honesty, flagged, intent, latency

Output : 1 fichier Markdown par question + un INDEX.md global.
Coût : 10 × pipeline complet ≈ $0.10 + ~3 min wall-clock.

Sélection des 10 questions :
- L01 (golden_60 v3) — superlative live
- L02 (golden_60 v3) — cyber Bretagne live (test BTS Rennes / BUT Brest)
- P01 (golden_60 v3) — paraphrase CROUS sans mot-clé
- A3 (mini_bench) — ingé info, refusait à tort avant fix _match_secteur
- B1 (mini_bench) — HEC 11/20, test posture franche
- D5 (mini_bench) — cyber Bretagne géo (généralisation L02)
- F1 (mini_bench) — comparaison ENSEIRB vs EPITA (cas difficile)
- B5 (mini_bench) — Sciences Po 13/20, réalisme + posture
- X1 (mini_bench) — grippe → cross-domain (ScopeClassifier court-circuit)
- A1 (mini_bench) — meilleures formations cyber (superlatif généralisation)

Usage :
    cd ~/projets/OrientIA && source .venv/bin/activate
    python scripts/dump_full_responses_step11_5.py
    python scripts/dump_full_responses_step11_5.py --question-ids L01,L02

Cf docs/SESSION_HANDOFF + plan step 11.5 (ad-hoc avant Phase D).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mistralai.client import Mistral

from src.config import load_config
from src.rag.factory import make_production_pipeline
from src.validator import Validator


# 10 questions sélectionnées par axes critiques. Couvre :
# - superlatif live (L01, A1)
# - cyber Bretagne live (L02, D5)
# - paraphrase sans mot-clé (P01)
# - cas qui refusait à tort avant fix _match_secteur (A3)
# - posture franche (B1, B5)
# - comparaison difficile (F1)
# - cross-domain (X1)
SELECTED_IDS_GOLDEN = ["L01", "L02", "P01"]  # golden_60.json v3
SELECTED_IDS_MINI = ["A3", "B1", "D5", "F1", "B5", "X1", "A1"]  # questions_20.json


def _load_questions() -> list[dict]:
    """Charge les 10 questions depuis golden_60 + questions_20."""
    golden_path = PROJECT_ROOT / "data" / "golden_eval" / "golden_60.json"
    mini_path = PROJECT_ROOT / "tests" / "mini_bench" / "questions_20.json"

    golden = json.loads(golden_path.read_text(encoding="utf-8"))
    mini = json.loads(mini_path.read_text(encoding="utf-8"))

    out: list[dict] = []
    g_by_id = {q["id"]: q for q in golden["questions"]}
    for qid in SELECTED_IDS_GOLDEN:
        q = g_by_id.get(qid)
        if not q:
            print(f"⚠ ID golden non trouvé : {qid}", file=sys.stderr)
            continue
        out.append({
            "id": qid,
            "source": "golden_60.json",
            "category": q["category"],
            "question": q["question"],
            "expected_routing": q.get("expected_routing"),
            "expected_refusal": q.get("expected_refusal", False),
            "expected_keywords": q.get("expected_keywords_in_answer", []),
        })

    mini_by_id = {q["id"]: q for q in mini["questions_unimodal"]}
    for qid in SELECTED_IDS_MINI:
        q = mini_by_id.get(qid)
        if not q:
            print(f"⚠ ID mini_bench non trouvé : {qid}", file=sys.stderr)
            continue
        out.append({
            "id": qid,
            "source": "questions_20.json",
            "category": q.get("category"),
            "question": q["text"],
            "intent_target": q.get("intent_target"),
            "scope_target": q.get("scope_target"),
        })
    return out


def _format_route_decision(rd) -> str:
    """Formate une RouteDecision en bloc Markdown lisible."""
    if rd is None:
        return "_RouteDecision : None (pas de router branché)_\n"
    lines = []
    lines.append(f"- **sub_indexes** : `{list(rd.sub_indexes)}`")
    if rd.criteria is not None:
        lines.append(f"- **criteria.region** : `{rd.criteria.region}`")
        lines.append(f"- **criteria.niveau_min/max** : `{rd.criteria.niveau_min}` / `{rd.criteria.niveau_max}`")
        lines.append(f"- **criteria.secteur** : `{rd.criteria.secteur}`")
        lines.append(f"- **criteria.domain** : `{rd.criteria.domain}`")
    else:
        lines.append("- **criteria** : `None`")
    lines.append(f"- **domain_lock** : `{rd.domain_lock}`")
    lines.append(f"- **refusal_reason** : `{rd.refusal_reason}`")
    lines.append(f"- **hardlock_region_strict** : `{rd.hardlock_region_strict}`")
    lines.append(f"- **hardlock_domain_strict** : `{rd.hardlock_domain_strict}`")
    lines.append(f"- **top_k_override** : `{rd.top_k_override}`")
    lines.append(f"- **confidence** : `{rd.confidence}`")
    lines.append(f"- **is_fallback** : `{rd.is_fallback}`")
    return "\n".join(lines)


def _format_sources(sources: list[dict], max_n: int = 12) -> str:
    """Formate les top-N sources en table Markdown."""
    if not sources:
        return "_(aucune source — court-circuit ou path bypass)_"
    lines = ["| # | nom | etab | ville | region | domain | score |",
             "|---:|---|---|---|---|---|---:|"]
    for i, src in enumerate(sources[:max_n], start=1):
        f = src.get("fiche", {}) or {}
        nom = (f.get("nom") or f.get("libelle_metier") or f.get("intitule") or "")[:60].replace("|", "\\|")
        etab = (f.get("etablissement") or "")[:35].replace("|", "\\|")
        ville = (f.get("ville") or "")[:25].replace("|", "\\|")
        region = (f.get("region") or "")[:25].replace("|", "\\|")
        domain = f.get("domain") or "—"
        score = src.get("score")
        score_str = f"{score:.3f}" if isinstance(score, (int, float)) else "—"
        lines.append(f"| {i} | {nom} | {etab} | {ville} | {region} | {domain} | {score_str} |")
    return "\n".join(lines)


def run_question(pipeline, validator, q: dict) -> dict:
    qid = q["id"]
    text = q["question"]
    t0 = time.time()
    try:
        response, top_sources = pipeline.answer(text)
    except Exception as e:
        return {
            "id": qid,
            "question": text,
            "error": f"pipeline.answer() exception: {e}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    latency = time.time() - t0

    rd = getattr(pipeline, "last_router_result", None)
    fs = getattr(pipeline, "last_filter_stats", None)
    sr = getattr(pipeline, "last_scope_result", None)

    # Validation honesty/flagged sur la réponse
    val_dict: dict = {}
    if response:
        try:
            val = validator.validate(response)
            val_dict = {
                "honesty_score": float(getattr(val, "honesty_score", 0.0) or 0.0),
                "flagged": bool(getattr(val, "flagged", False)),
                "n_failed_claims": len(getattr(val, "failed_claims", []) or []),
            }
        except Exception as e:
            val_dict = {"validator_error": str(e)}

    return {
        "id": qid,
        "source": q.get("source"),
        "category": q.get("category"),
        "question": text,
        "expected_routing": q.get("expected_routing"),
        "expected_refusal": q.get("expected_refusal"),
        "expected_keywords": q.get("expected_keywords"),
        "intent_target": q.get("intent_target"),
        "scope_target": q.get("scope_target"),
        "route_decision_obj": rd,
        "filter_stats": fs,
        "scope_label": sr.label if sr else None,
        "scope_reason": sr.reason if sr else None,
        "response_full": response,
        "n_sources_top": len(top_sources),
        "top_sources": top_sources,
        "latency_total_s": round(latency, 2),
        "validation": val_dict,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def write_question_md(record: dict, out_dir: Path) -> None:
    """Écrit un fichier .md par question (lisible humain)."""
    qid = record["id"]
    out_path = out_dir / f"{qid}.md"
    lines: list[str] = []
    lines.append(f"# {qid} — {record['question']}")
    lines.append(f"\n_Source: {record.get('source', '?')} · Category: {record.get('category', '?')} · Run: {record['timestamp']}_\n")

    if "error" in record:
        lines.append(f"## ❌ ERROR\n\n```\n{record['error']}\n```")
        out_path.write_text("\n".join(lines), encoding="utf-8")
        return

    # Attentes (depuis le golden / mini_bench)
    if record.get("expected_routing") or record.get("expected_refusal") or record.get("expected_keywords"):
        lines.append("## Attentes")
        if record.get("expected_routing"):
            lines.append(f"- expected_routing : `{record['expected_routing']}`")
        if record.get("expected_refusal") is not None:
            lines.append(f"- expected_refusal : `{record['expected_refusal']}`")
        if record.get("expected_keywords"):
            lines.append(f"- expected_keywords_in_answer : `{record['expected_keywords']}`")
        if record.get("scope_target"):
            lines.append(f"- scope_target (mini_bench) : `{record['scope_target']}`")
        lines.append("")

    # Routing décidé par RouterLLM
    lines.append("## Routing (RouteDecision)")
    lines.append(_format_route_decision(record.get("route_decision_obj")))
    lines.append("")

    # Filter stats
    fs = record.get("filter_stats") or {}
    if fs:
        lines.append("## Filter stats")
        for k, v in fs.items():
            lines.append(f"- {k} : `{v}`")
        lines.append("")

    # Scope (court-circuit éventuel ScopeClassifier)
    if record.get("scope_label") and record["scope_label"] != "in_scope":
        lines.append("## ⚠ ScopeClassifier court-circuit")
        lines.append(f"- label : `{record['scope_label']}`")
        lines.append(f"- reason : `{record['scope_reason']}`")
        lines.append("")

    # Sources top-N
    lines.append(f"## Sources retrieved (top {min(12, record['n_sources_top'])} sur {record['n_sources_top']})")
    lines.append(_format_sources(record.get("top_sources") or []))
    lines.append("")

    # Réponse FULL (non tronquée)
    lines.append("## Réponse complète du pipeline\n")
    lines.append("```")
    lines.append(record["response_full"] or "_(réponse vide)_")
    lines.append("```")
    lines.append("")

    # Validation
    val = record.get("validation") or {}
    lines.append("## Validator")
    lines.append(f"- honesty_score : `{val.get('honesty_score', '—')}`")
    lines.append(f"- flagged : `{val.get('flagged', '—')}`")
    lines.append(f"- n_failed_claims : `{val.get('n_failed_claims', '—')}`")
    lines.append(f"- latency_total_s : `{record['latency_total_s']}`")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def write_index_md(records: list[dict], out_dir: Path) -> None:
    """Écrit un INDEX.md global avec table de résumé."""
    lines: list[str] = []
    lines.append("# Step 11.5 — Audit qualitatif PRE-Phase-D")
    lines.append(f"\n_Run: {datetime.now(timezone.utc).isoformat()}_")
    lines.append(f"_{len(records)} questions sélectionnées sur axes critiques_\n")
    lines.append("Lecture humaine recommandée : ouvrir chaque `.md` dans l'ordre du tableau.\n")

    lines.append("| ID | Source | Catégorie | refusal_reason | honesty | latency | Question (court) |")
    lines.append("|---|---|---|---|---:|---:|---|")
    for r in records:
        if "error" in r:
            lines.append(f"| {r['id']} | {r.get('source', '?')} | — | ERROR | — | — | {r['question'][:70]} |")
            continue
        rd = r.get("route_decision_obj")
        ref = (rd.refusal_reason if rd and rd.refusal_reason else "—")
        val = r.get("validation") or {}
        honesty = val.get("honesty_score", "—")
        q_short = r["question"][:70].replace("|", "\\|")
        lines.append(
            f"| [{r['id']}]({r['id']}.md) | {r.get('source', '?')[:20]} | "
            f"{r.get('category', '?')} | {ref} | {honesty} | "
            f"{r['latency_total_s']}s | {q_short}... |"
        )

    (out_dir / "INDEX.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\n📄 INDEX écrit : {out_dir / 'INDEX.md'}")


# ────────────────────────── CLI ──────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--question-ids", type=str, default=None,
        help="Comma-separated IDs (override sélection par défaut).",
    )
    parser.add_argument(
        "--out-dir", type=Path,
        default=PROJECT_ROOT / "results" / "full_responses_audit_phaseD",
    )
    parser.add_argument("--corpus-path", type=Path,
                        default=PROJECT_ROOT / "data" / "processed" / "formations_v7.json")
    parser.add_argument("--index-path", type=Path,
                        default=PROJECT_ROOT / "data" / "embeddings" / "formations.index")
    args = parser.parse_args()

    cfg = load_config()
    if not cfg.mistral_api_key:
        print("ERREUR : MISTRAL_API_KEY absent", file=sys.stderr)
        return 1
    args.out_dir.mkdir(parents=True, exist_ok=True)

    questions = _load_questions()
    if args.question_ids:
        wanted = {x.strip() for x in args.question_ids.split(",") if x.strip()}
        questions = [q for q in questions if q["id"] in wanted]
    print(f"Questions sélectionnées : {len(questions)}")

    fiches = json.loads(args.corpus_path.read_text(encoding="utf-8"))
    print(f"Corpus : {len(fiches)} fiches")

    client = Mistral(api_key=cfg.mistral_api_key, timeout_ms=120000)
    pipeline = make_production_pipeline(
        client, fiches,
        enable_router_llm=True,
        enable_validator=True,
        enable_layer3=False,
        enable_golden_qa=True,
        enable_post_process=True,
        enable_strict_v4=True,
    )
    pipeline.load_index_from(str(args.index_path))
    validator = Validator(fiches=fiches, layer3=None)

    print(f"\n=== Audit qualitatif {len(questions)} questions (router_ON) ===\n")
    records: list[dict] = []
    for i, q in enumerate(questions, start=1):
        print(f"[{i}/{len(questions)}] {q['id']}: {q['question'][:60]}...")
        rec = run_question(pipeline, validator, q)
        records.append(rec)
        if "error" not in rec:
            rd = rec.get("route_decision_obj")
            ref = rd.refusal_reason if rd and rd.refusal_reason else "—"
            print(
                f"   → lat={rec['latency_total_s']}s, "
                f"refusal={ref}, honesty={rec['validation'].get('honesty_score')}"
            )
        write_question_md(rec, args.out_dir)

    write_index_md(records, args.out_dir)
    print(f"\n✅ Done — ouvre {args.out_dir / 'INDEX.md'} pour démarrer la lecture")
    return 0


if __name__ == "__main__":
    sys.exit(main())
