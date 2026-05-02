"""Sprint 12 axe 2 — Bench validation Golden Pipeline 10q hold-out.

Compare ``pipeline_agent_golden`` (nouveau) vs ``our_rag_enriched`` (legacy)
sur 10 questions hold-out (split=test) pour valider la fusion agentic
Sprint 1-4 + acquis Sprint 9-12 + Backstop B soft Sprint 11 P1.1.

## Critère succès empirique

Golden ≥ enriched sur **7/10 questions minimum** (juge Claude Sonnet 4.5
multi-aspect rubric, score_total inter-systems comparé question par
question).

Si NO-GO (>3/10 questions où golden < enriched) → flag honnête + 3 options
pivot dans le doc verdict (boost reranker / coverage spec / abandon Sprint 13).

## Configuration systèmes

### `pipeline_agent_golden`
- `AgentPipeline` (corpus combined 61 657 + index golden 240.8 MB)
- `enable_metadata_filter=True` (FilterCriteria dérivé Profile→ProfileState)
- `enable_backstop_b=True` (`CorpusFactIndex.from_unified_json` pré-construit)
- `enable_fact_check=True` (FetchStatFromSource in-loop top-5 claims)
- `golden_qa_prefix` dynamic via `OrientIAPipeline._maybe_build_golden_qa_prefix`
- `history_buffer_size=3` (cap mémoire short-term)

### `our_rag_enriched`
- `OurRagSystem(OrientIAPipeline)` config Sprint 11 P1.1 (rerank + MMR +
  intent + metadata filter + golden_qa active + Backstop B intégré dans
  `pipeline.py:answer`).

## Coût + ETA

- 10 q × 2 systems × Mistral medium gen (~5s) ≈ ~$0.20
- 10 q × 2 systems × Mistral embed retrieval ≈ ~$0.05
- 10 q × Claude Sonnet 4.5 judge (1 call par question, n=2 answers chacun) ≈ ~$0.40
- **Total estimé : ~$0.65** (sous-budget plan $3-5 grâce single-judge MVP)
- ETA wall-clock : ~30-60 min

Multi-judge (Sonnet + GPT-4o + Haiku) reporté à itération suivante si
verdict OK pour économiser le budget INRIA.

## Reproductibilité

- Seed déterministe : 10 premières q du split=test triées par id (A1→Z…)
- Save incrémental : output JSON après chaque génération + chaque judgement
- Resume au rerun : skip questions déjà traitées

## Usage

    PYTHONPATH=. python3 scripts/bench_sprint12_axe2_golden_validation.py

Plan : ``docs/GOLDEN_PIPELINE_PLAN.md`` étape 4.
Spec ordre : 2026-05-01-2031-claudette-orientia-sprint12-axe-2-golden-pipeline-fusion.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from anthropic import Anthropic
from mistralai.client import Mistral

from src.agent.pipeline_agent import AgentPipeline
from src.config import load_config
from src.eval.judge import judge_all
from src.eval.systems import (
    MistralWithCustomPromptSystem,
    OurRagSystem,
    PipelineAgentGoldenSystem,
)
from src.prompt.system import SYSTEM_PROMPT
from src.rag.embeddings import corpus_item_to_text
from src.rag.index import load_index
from src.rag.pipeline import OrientIAPipeline


ROOT = Path(__file__).resolve().parents[1]

# --- Sources ---
QUESTIONS_PATH = ROOT / "src" / "eval" / "questions.json"
LEGACY_FICHES_PATH = ROOT / "data" / "processed" / "formations_unified.json"
LEGACY_INDEX_PATH = ROOT / "data" / "embeddings" / "formations_unified.index"
GOLDEN_FICHES_PATH = ROOT / "data" / "processed" / "formations_golden_pipeline.json"
GOLDEN_INDEX_PATH = ROOT / "data" / "embeddings" / "formations_golden_pipeline.index"
GOLDEN_QA_INDEX_PATH = ROOT / "data" / "embeddings" / "golden_qa.index"
GOLDEN_QA_META_PATH = ROOT / "data" / "processed" / "golden_qa_meta.json"

# --- Output ---
OUTPUT_DIR = ROOT / "results" / "bench_sprint12_axe2_golden_validation"
RESPONSES_PATH = OUTPUT_DIR / "responses_blind.json"
SCORES_PATH = OUTPUT_DIR / "judge_scores.json"
VERDICT_RAW_PATH = OUTPUT_DIR / "verdict_raw.json"

# --- Config ---
N_QUESTIONS = 10
SPLIT_FILTER = "test"  # hold-out only
JUDGE_MODEL = "claude-sonnet-4-5"


def load_hold_out_questions() -> list[dict]:
    """Pioche les 10 premières questions split=test triées par id (reproductible)."""
    with QUESTIONS_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    qs = [q for q in data["questions"] if q.get("split") == SPLIT_FILTER]
    qs_sorted = sorted(qs, key=lambda q: q["id"])
    selected = qs_sorted[:N_QUESTIONS]
    print(f"Loaded {len(selected)} hold-out questions (split={SPLIT_FILTER})")
    for q in selected:
        print(f"  - {q['id']} [{q.get('category', '?')}] : {q['text'][:70]}")
    return selected


def build_golden_system(client: Mistral) -> PipelineAgentGoldenSystem:
    """Construit le `PipelineAgentGoldenSystem` complet."""
    print(f"\n==> Loading golden corpus combined : {GOLDEN_FICHES_PATH}")
    with GOLDEN_FICHES_PATH.open("r", encoding="utf-8") as f:
        golden_fiches = json.load(f)
    print(f"    {len(golden_fiches):,} entrées")

    print(f"==> Loading golden FAISS index : {GOLDEN_INDEX_PATH}")
    golden_index = load_index(str(GOLDEN_INDEX_PATH))
    print(f"    ntotal={golden_index.ntotal:,}, dim={golden_index.d}")

    print(f"==> Loading legacy fiches pour CorpusFactIndex (Backstop B)")
    # CorpusFactIndex.from_unified_json attend le format formations_unified
    # (taux_acces_parcoursup_2025, insertion_pro.taux_emploi_*, salaire_median_embauche).
    # Le corpus golden n'a pas tous ces champs sur les items dares/rncp_blocs,
    # donc on construit l'index à partir du formations_unified seul (les
    # chiffres factuels viennent essentiellement des fiches Parcoursup).
    from src.backstop import CorpusFactIndex
    corpus_fact_index = CorpusFactIndex.from_unified_json(LEGACY_FICHES_PATH)
    print(f"    CorpusFactIndex built")

    agent_pipeline = AgentPipeline(
        client=client,
        fiches=golden_fiches,
        index=golden_index,
        # Sprint 12 axe 2 golden flags
        # Étape 7 Test 1 (2026-05-02) : metadata_filter=False pour apple-to-apple
        # avec our_rag_enriched qui ne passe jamais criteria à pipeline.answer()
        # (cf OurRagSystem.answer() ligne 53 src/eval/systems.py — bench v1+v2
        # biaisé : golden subissait filter strict/boost, enriched pas en pratique).
        enable_metadata_filter=False,
        enable_backstop_b=True,
        backstop_b_corpus_index=corpus_fact_index,
        enable_fact_check=True,
        history_buffer_size=3,
        # Tools mistral-large maintenus (Sprint 2 bench tranche)
        # (les tools `ProfileClarifier` / `QueryReformuler` / `FetchStatFromSource`
        # sont config par leur module respectif — les defaults sont OK).
    )

    # Q&A Golden helper : OrientIAPipeline minimal (fiches=[] OK car on
    # utilise QUE _maybe_build_golden_qa_prefix() qui touche un faiss index
    # Q&A séparé chargé lazy au 1er call).
    if GOLDEN_QA_INDEX_PATH.exists() and GOLDEN_QA_META_PATH.exists():
        qa_helper = OrientIAPipeline(
            client=client,
            fiches=[],  # vide — on n'utilise pas le retrieval principal
            use_golden_qa=True,
            golden_qa_index_path=str(GOLDEN_QA_INDEX_PATH),
            golden_qa_meta_path=str(GOLDEN_QA_META_PATH),
        )
        print(f"    Q&A Golden helper chargé ({GOLDEN_QA_META_PATH.name})")
    else:
        qa_helper = None
        print(f"    ⚠️  Q&A Golden index/meta absent — pas de prefix injection")

    return PipelineAgentGoldenSystem(agent_pipeline=agent_pipeline, qa_helper_pipeline=qa_helper)


def build_enriched_system(client: Mistral) -> OurRagSystem:
    """Construit `our_rag_enriched` = `OurRagSystem` legacy config Sprint 11 P1.1."""
    print(f"\n==> Loading legacy fiches : {LEGACY_FICHES_PATH}")
    with LEGACY_FICHES_PATH.open("r", encoding="utf-8") as f:
        legacy_fiches = json.load(f)
    print(f"    {len(legacy_fiches):,} fiches")

    pipeline = OrientIAPipeline(
        client=client,
        fiches=legacy_fiches,
        use_metadata_filter=True,  # default ON depuis Sprint 10 chantier C
        use_golden_qa=GOLDEN_QA_INDEX_PATH.exists(),
        golden_qa_index_path=str(GOLDEN_QA_INDEX_PATH) if GOLDEN_QA_INDEX_PATH.exists() else None,
        golden_qa_meta_path=str(GOLDEN_QA_META_PATH) if GOLDEN_QA_META_PATH.exists() else None,
    )
    print(f"==> Loading legacy FAISS index : {LEGACY_INDEX_PATH}")
    pipeline.load_index_from(str(LEGACY_INDEX_PATH))
    print(f"    ntotal={pipeline.index.ntotal:,}, dim={pipeline.index.d}")

    return OurRagSystem(pipeline)


def generate_responses(
    questions: list[dict],
    systems: dict[str, object],
    save_path: Path,
) -> list[dict]:
    """Génère les réponses pour chaque (question, system). Save incrémental.

    Format ``responses_blind`` attendu par ``judge_all`` :
        [{id, category, text, answers: {label: str}}]
    """
    save_path.parent.mkdir(parents=True, exist_ok=True)

    # Resume from existing if present
    existing = []
    done_ids: set[str] = set()
    if save_path.exists():
        try:
            existing = json.loads(save_path.read_text(encoding="utf-8"))
            done_ids = {e["id"] for e in existing}
            print(f"\n==> Resuming : {len(done_ids)} questions déjà générées, skip")
        except Exception as e:
            print(f"   (parse fail {save_path}: {e} — fresh start)")

    responses: list[dict] = list(existing)
    labels = sorted(systems.keys())  # ordre stable pour blinding lisible

    for q in questions:
        if q["id"] in done_ids:
            continue
        print(f"\n==> Generating Q={q['id']} [{q.get('category','?')}] : {q['text'][:60]}...")
        answers: dict[str, str] = {}
        for label in labels:
            sys_obj = systems[label]
            t0 = time.time()
            try:
                ans = sys_obj.answer(q["id"], q["text"])
            except Exception as e:
                ans = f"[ERROR {type(e).__name__}: {e}]"
            elapsed = time.time() - t0
            print(f"    {label}: {elapsed:.1f}s, {len(ans)} chars")
            answers[label] = ans

        responses.append({
            "id": q["id"],
            "category": q.get("category", ""),
            "text": q["text"],
            "answers": answers,
        })
        save_path.write_text(json.dumps(responses, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n==> Wrote responses → {save_path}")
    return responses


def compute_verdict(scores: list[dict]) -> dict:
    """Compute verdict golden vs enriched.

    Pour chaque question, compare score_total des 2 systems. Win golden si
    `score_golden > score_enriched`, win enriched si `<`, tie si égal.
    """
    wins_golden = 0
    wins_enriched = 0
    ties = 0
    per_question = []

    for entry in scores:
        s = entry["scores"]
        # judge_question retourne {label: {score_total: ..., justification: ...}}
        # ou {answers: {...}, ...} selon le format du JUDGE_PROMPT.
        # On tente plusieurs accès robustes.
        sg = _extract_total(s, "pipeline_agent_golden")
        se = _extract_total(s, "our_rag_enriched")
        win = "?" if sg is None or se is None else (
            "golden" if sg > se else ("enriched" if se > sg else "tie")
        )
        per_question.append({
            "id": entry["id"],
            "category": entry.get("category"),
            "score_golden": sg,
            "score_enriched": se,
            "win": win,
        })
        if win == "golden":
            wins_golden += 1
        elif win == "enriched":
            wins_enriched += 1
        elif win == "tie":
            ties += 1

    n = len(scores)
    # Critère plan : golden ≥ enriched sur 7/10 minimum
    # (interprétation : wins_golden + ties ≥ 7 — golden au moins équivalent
    # sur 7/10 questions est le seuil GO).
    golden_at_least_eq = wins_golden + ties
    decision = "GO" if golden_at_least_eq >= 7 else "NO-GO"

    return {
        "n_questions": n,
        "wins_golden": wins_golden,
        "wins_enriched": wins_enriched,
        "ties": ties,
        "golden_at_least_equivalent_count": golden_at_least_eq,
        "decision_threshold_7_of_10": decision,
        "per_question": per_question,
    }


def _extract_total(scores_dict: dict, label: str):
    """Tente plusieurs schemas pour extraire le score total d'un label.

    Format réel observé Run F+G + bench Sprint 12 : ``{label: {total: int, ...}}``
    où le judge produit `total` (somme des 6 aspects rubric). Backward
    compat avec d'éventuels schemas plus anciens (`score_total`).
    """
    if not isinstance(scores_dict, dict):
        return None
    # Format réel actuel : {label: {total: ..., justification: ...}}
    if label in scores_dict:
        sub = scores_dict[label]
        if isinstance(sub, dict):
            if "total" in sub:
                return sub["total"]
            if "score_total" in sub:
                return sub["score_total"]
    # Format 2: {scores: {label: {...}}}
    if "scores" in scores_dict and isinstance(scores_dict["scores"], dict):
        return _extract_total(scores_dict["scores"], label)
    return None


def main() -> int:
    print("=" * 60)
    print("Sprint 12 axe 2 — Bench validation Golden Pipeline 10q")
    print("=" * 60)

    cfg = load_config()
    if not cfg.mistral_api_key:
        print("❌  MISTRAL_API_KEY absent")
        return 1
    if not cfg.anthropic_api_key:
        print("❌  ANTHROPIC_API_KEY absent")
        return 1

    mistral = Mistral(api_key=cfg.mistral_api_key)
    anthropic = Anthropic(api_key=cfg.anthropic_api_key)

    questions = load_hold_out_questions()

    # Build all 3 systems (étape 7 test 1 — bench triangulaire)
    enriched_system = build_enriched_system(mistral)
    golden_system = build_golden_system(mistral)
    # mistral_v3_2_no_rag : SYSTEM_PROMPT v3.2 (default = v4 préfixe Sprint 11
    # P0 + corps v3.2) sans RAG context. Baseline pour isoler l'apport du RAG.
    no_rag_system = MistralWithCustomPromptSystem(
        client=mistral,
        system_prompt=SYSTEM_PROMPT,
        name="mistral_v3_2_no_rag",
    )

    systems = {
        "our_rag_enriched": enriched_system,
        "pipeline_agent_golden": golden_system,
        "mistral_v3_2_no_rag": no_rag_system,
    }

    # Generate
    responses = generate_responses(questions, systems, RESPONSES_PATH)

    # Judge
    print(f"\n==> Judging via {JUDGE_MODEL} (multi-aspect rubric)")
    scores = judge_all(anthropic, responses, model=JUDGE_MODEL, save_path=SCORES_PATH)
    print(f"==> Scores → {SCORES_PATH}")

    # Verdict
    print("\n==> Computing verdict")
    verdict = compute_verdict(scores)
    VERDICT_RAW_PATH.write_text(json.dumps(verdict, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"==> Verdict raw → {VERDICT_RAW_PATH}")

    print(f"\n{'=' * 60}")
    print(f"Wins golden     : {verdict['wins_golden']}/{verdict['n_questions']}")
    print(f"Wins enriched   : {verdict['wins_enriched']}/{verdict['n_questions']}")
    print(f"Ties            : {verdict['ties']}/{verdict['n_questions']}")
    print(f"Golden ≥ enriched : {verdict['golden_at_least_equivalent_count']}/{verdict['n_questions']}")
    print(f"Décision (≥7/10) : {verdict['decision_threshold_7_of_10']}")
    print(f"{'=' * 60}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
