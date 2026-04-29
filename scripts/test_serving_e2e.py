"""Test serving end-to-end OrientIA — Sprint 10 chantier E.

Lance 10 questions post-bac diverses via OrientIAPipeline + capture pour
chacune :
- Réponse Mistral
- Q&A Golden top-1 retrieved (si actif)
- 10 fiches RAG retournées
- Mesures empiriques : latence breakdown, filter stats

Calcule ensuite :
- Pollution rate : entités de la Q&A Golden citées dans la réponse Mistral
  mais ABSENTES des 10 fiches RAG (= pollution potentielle Comment→Quoi)
- Filter saturation : % questions hit_max + distribution n_after_filter
- Latence breakdown : t_total_ms p50/p90/max

Output : `docs/sprint10-E-test-serving-2026-04-29.md` avec stats + 10
réponses lisibles pour audit qualitatif Matteo+Jarvis.

Usage : `PYTHONPATH=. python3 scripts/test_serving_e2e.py`

Coût Mistral API estimé : 10 questions × ~$0.05-0.10 = ~$0.50-1.00.
ETA : ~5-10 min wall-clock (chaque .answer() prend 5-30s avec Mistral medium).

Spec ordre Jarvis : 2026-04-29-1146-claudette-orientia-sprint10-finalisation-rag-complet (chantier E).
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from mistralai.client import Mistral

from src.config import load_config
from src.rag.metadata_filter import FilterCriteria
from src.rag.pipeline import OrientIAPipeline


ROOT = Path(__file__).resolve().parents[1]
FICHES_PATH = ROOT / "data" / "processed" / "formations_unified.json"
INDEX_PATH = ROOT / "data" / "embeddings" / "formations_unified.index"
GOLDEN_QA_INDEX_PATH = ROOT / "data" / "embeddings" / "golden_qa.index"
GOLDEN_QA_META_PATH = ROOT / "data" / "processed" / "golden_qa_meta.json"
OUTPUT_DOC = ROOT / "docs" / "sprint10-E-test-serving-2026-04-29.md"
OUTPUT_RAW_JSONL = ROOT / "docs" / "sprint10-E-raw-results-2026-04-29.jsonl"


# 10 questions post-bac diverses (couverture intentionnelle large)
TEST_QUESTIONS = [
    "Je suis en terminale spé maths-physique mais je sature des maths abstraites, alternatives concrètes à la prépa MPSI ?",
    "Je suis en L1 droit et je perds toute motivation, comment me réorienter ?",
    "Je suis en prépa MPSI, je suis en burn-out, est-ce que je peux abandonner sans gâcher mon avenir ?",
    "Je suis boursière échelon 7, comment trouver un logement étudiant abordable ?",
    "J'ai raté ma PASS, est-ce que je peux quand même faire kiné ou infirmière ?",
    "Quelles formations en cybersécurité à Toulouse niveau bachelor ?",
    "Master de droit des affaires, quels débouchés concrets en France ?",
    "Je travaille dans le tertiaire depuis 5 ans, je veux me reconvertir paramédical après un burn-out, par où commencer ?",
    "Mon fils veut faire un apprentissage en plomberie mais nous voulions qu'il fasse une école d'ingénieur, comment réagir ?",
    "Je suis en terminale L et tout le monde me dit que ça ne mène à rien, est-ce vrai ?",
]


# Pattern entités potentiellement polluées (extraits de Q&A Golden mais absents
# du context fiches RAG = signal pollution Comment→Quoi)
ENTITY_PATTERNS = [
    # Noms d'écoles capitalisés (2+ mots)
    re.compile(r"\b[A-ZÉÈÀ][a-zéèàâîôûç]+(?:\s+[A-ZÉÈÀ][a-zéèàâîôûç]+){1,3}\b"),
    # Acronymes (2-6 lettres majuscules consécutives)
    re.compile(r"\b[A-Z]{2,6}\b"),
    # Pourcentages
    re.compile(r"\d+\s*%"),
    # Montants euros
    re.compile(r"\d+[\s.,]?\d*\s*€"),
    # Dates précises (mois français + année)
    re.compile(r"\b(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4}", re.IGNORECASE),
]


def extract_entities(text: str) -> set[str]:
    """Extrait les entités potentiellement chiffrées/nommées du texte."""
    entities = set()
    for pattern in ENTITY_PATTERNS:
        for match in pattern.findall(text):
            if isinstance(match, tuple):
                match = match[0] if match else ""
            ent = match.strip()
            if ent and len(ent) >= 2:
                entities.add(ent)
    return entities


def measure_pollution(answer: str, sources: list[dict], golden_qa_record: dict | None) -> dict:
    """Mesure la pollution Q&A Golden → réponse Mistral.

    Pour chaque entité présente dans la réponse Mistral :
    - Si elle apparaît AUSSI dans le content des fiches RAG → OK (sourcée)
    - Sinon → pollution flag (vient potentiellement de la Q&A Golden ou hallu)

    Returns dict avec stats + liste des entités polluées.
    """
    answer_entities = extract_entities(answer)

    # Aggregate des contents fiches RAG
    fiches_content = ""
    for src in sources:
        f = src.get("fiche") or {}
        for key in ("nom", "title", "etablissement", "ville", "departement", "region", "detail"):
            v = f.get(key)
            if v and isinstance(v, str):
                fiches_content += " " + v

    polluted: list[str] = []
    for ent in answer_entities:
        # Skip false positives évidents (mots français courants en majuscules de phrase)
        if ent.lower() in ("oui", "non", "si", "voici", "exemple", "tu", "te", "je", "on", "il", "elle", "ils", "ce", "cette", "comme", "alors", "ainsi", "mais"):
            continue
        # Skip stop-acronyms français
        if ent in ("ET", "OU", "DE", "LA", "LE", "EN", "AU", "DU"):
            continue
        if ent not in fiches_content:
            polluted.append(ent)

    return {
        "answer_entities_count": len(answer_entities),
        "polluted_entities": sorted(set(polluted)),
        "polluted_count": len(set(polluted)),
        "pollution_rate": len(set(polluted)) / max(len(answer_entities), 1),
    }


def run_one_question(pipeline: OrientIAPipeline, question: str, criteria: FilterCriteria | None = None) -> dict:
    """Lance 1 .answer() complet et collecte les mesures."""
    t_start = time.time()
    try:
        answer, top = pipeline.answer(question, top_k_sources=10, criteria=criteria)
        t_total_ms = (time.time() - t_start) * 1000

        sources = [
            {
                "score": item.get("score"),
                "fiche": item.get("fiche"),
            }
            for item in top
        ]

        last_filter_stats = pipeline.last_filter_stats or {}
        last_golden_qa = pipeline.last_golden_qa or {}

        # Récupérer le record Q&A Golden complet pour mesure pollution
        golden_qa_record = None
        if last_golden_qa.get("matched") and pipeline._golden_qa_meta:
            for m in pipeline._golden_qa_meta:
                if (m.get("prompt_id") == last_golden_qa.get("prompt_id")
                        and m.get("iteration") == last_golden_qa.get("iteration")):
                    golden_qa_record = m
                    break

        pollution = measure_pollution(answer, top, golden_qa_record)

        return {
            "question": question,
            "answer": answer,
            "sources": sources,
            "t_total_ms": round(t_total_ms),
            "filter_stats": last_filter_stats,
            "golden_qa": last_golden_qa,
            "golden_qa_record_question": (golden_qa_record or {}).get("question_seed"),
            "pollution": pollution,
            "error": None,
        }
    except Exception as e:
        return {
            "question": question,
            "answer": None,
            "sources": [],
            "t_total_ms": round((time.time() - t_start) * 1000),
            "error": f"{type(e).__name__}: {e}",
        }


def render_md_report(results: list[dict]) -> str:
    """Render le rapport MD pour audit Matteo+Jarvis."""
    n = len(results)
    valid_results = [r for r in results if r.get("error") is None]

    # Stats agrégées
    latencies = [r["t_total_ms"] for r in valid_results]
    pollutions = [r.get("pollution", {}).get("pollution_rate", 0) for r in valid_results]
    filter_hits_max = sum(1 for r in valid_results if r.get("filter_stats", {}).get("hit_max"))
    filter_n_after = [r.get("filter_stats", {}).get("n_after_filter", 0) for r in valid_results]
    golden_qa_matched = sum(1 for r in valid_results if r.get("golden_qa", {}).get("matched"))
    expansions_count = [r.get("filter_stats", {}).get("expansions", 0) for r in valid_results]

    parts = [
        "# Sprint 10 chantier E — Test serving end-to-end (mesures empiriques)",
        "",
        "**Date** : 2026-04-29",
        f"**Questions testées** : {n}",
        f"**Réponses valides** : {len(valid_results)}/{n}",
        "**Pipeline** : OrientIAPipeline avec `use_metadata_filter=True` (chantier C activation, post-merge #106) + `use_golden_qa=True` (chantier D, post-merge #104)",
        "**Corpus** : `formations_unified.json` (55 606 entries, post-merge #105)",
        "**Modèles** : Mistral medium (generate) + Mistral-embed dim 1024 (retrieve)",
        "",
        "---",
        "",
        "## Stats agrégées (mesures empiriques)",
        "",
    ]

    # Latence
    if latencies:
        latencies_sorted = sorted(latencies)
        p50 = latencies_sorted[len(latencies_sorted) // 2]
        p90 = latencies_sorted[int(len(latencies_sorted) * 0.9)]
        parts += [
            "### Alerte 2 — Latence end-to-end",
            "",
            f"- p50 (médiane) : **{p50} ms**",
            f"- p90 : **{p90} ms**",
            f"- max : **{max(latencies)} ms**",
            f"- min : {min(latencies)} ms",
            f"- moyenne : {sum(latencies) // len(latencies)} ms",
            "",
            "Note : t_total_ms = AnalystAgent (si actif) + Q&A Golden retrieve (si actif) + FAISS retrieve + reranker + filter + Mistral generate. Pas de breakdown granulaire dans cette première mesure (à raffiner Sprint 11 si latence problématique).",
            "",
        ]

    # Pollution
    parts += [
        "### Alerte 4 — Pollution Q&A Golden → Mistral (mesure empirique)",
        "",
        f"- Pollution rate moyenne : **{sum(pollutions) / len(pollutions) * 100:.1f}%** des entités citées en réponse",
        f"- Pollution rate médiane : {sorted(pollutions)[len(pollutions) // 2] * 100:.1f}%",
        f"- Pollution rate max : {max(pollutions) * 100:.1f}%",
        "",
        "Méthode : pour chaque réponse Mistral, extraction des entités (noms propres, acronymes, montants, pourcentages, dates précises) → comparaison avec le content des 10 fiches RAG. Entités présentes dans Mistral mais ABSENTES des fiches = pollution potentielle (probablement Q&A Golden ou hallu).",
        "",
        "**Décision data-driven** :",
        "- Si <5% pollution → pattern IGNORE actuel suffit, pas de post-filter Sprint 11",
        "- Si 5-15% → ajouter post-filter regex Sprint 11",
        "- Si >15% → urgent + investigation prompt design",
        "",
    ]

    # Filter saturation
    parts += [
        "### Alerte 1 — Filter saturation (mesure empirique)",
        "",
        f"- Questions hit_max (cap MAX_K_MULTIPLIER atteint) : **{filter_hits_max}/{len(valid_results)}**",
    ]
    if filter_n_after:
        parts.append(f"- n_after_filter médiane : {sorted(filter_n_after)[len(filter_n_after) // 2]}")
        parts.append(f"- n_after_filter moyenne : {sum(filter_n_after) // len(filter_n_after)}")
    parts.append(f"- expansions cumul : {sum(expansions_count)} (sur {len(valid_results)} questions)")
    parts.append("")
    parts.append("**Décision data-driven** :")
    parts.append("- Si >30% questions hit_max → migration FAISS → Qdrant urgente Sprint 11")
    parts.append("- Si 5-30% → fallback graceful filter Sprint 11")
    parts.append("- Si <5% → architecture FAISS post-filter actuelle suffit")
    parts.append("")

    # Q&A Golden coverage
    parts += [
        "### Q&A Golden retrieval coverage",
        "",
        f"- Questions avec match Q&A Golden : **{golden_qa_matched}/{len(valid_results)}**",
        f"- Coverage : {golden_qa_matched / len(valid_results) * 100:.0f}%",
        "",
        "Note : 45 Q&A Golden actuelles couvrent uniquement `lyceen_post_bac` (nuit 1). Coverage complète attendue post-nuit 2 (drops-only autres catégories).",
        "",
        "---",
        "",
        "## 10 réponses Mistral pour audit qualitatif",
        "",
    ]

    # Détail des 10 réponses
    for i, r in enumerate(results, 1):
        parts.append(f"### Q{i} — {r['question'][:90]}{'...' if len(r['question']) > 90 else ''}")
        parts.append("")
        if r.get("error"):
            parts.append(f"❌ ERREUR : {r['error']}")
            parts.append("")
            continue

        # Mesures
        parts.append(f"**Mesures** : t_total={r['t_total_ms']}ms | "
                     f"filter n_after={r.get('filter_stats', {}).get('n_after_filter', '?')} "
                     f"expansions={r.get('filter_stats', {}).get('expansions', '?')} "
                     f"hit_max={r.get('filter_stats', {}).get('hit_max', False)} | "
                     f"pollution_rate={r.get('pollution', {}).get('pollution_rate', 0) * 100:.0f}%")
        parts.append("")

        # Q&A Golden matched
        gq = r.get("golden_qa", {})
        if gq.get("matched"):
            parts.append(f"**Q&A Golden top-1** : `{gq.get('prompt_id')}` iter {gq.get('iteration')} (score {gq.get('score_total')}, retrieve sim {gq.get('retrieve_score', 0):.2f})")
            qg_q = r.get("golden_qa_record_question", "")
            if qg_q:
                parts.append(f"  - Seed : « {qg_q[:120]} »")
            parts.append("")

        # Réponse Mistral
        parts.append("**Réponse Mistral** :")
        parts.append("")
        parts.append("> " + r["answer"].replace("\n", "\n> "))
        parts.append("")

        # Sources top 3
        parts.append(f"**Sources top-3 sur {len(r.get('sources', []))} retournées** :")
        for j, src in enumerate(r.get("sources", [])[:3], 1):
            f = src.get("fiche") or {}
            nom = f.get("nom") or f.get("title") or "(sans nom)"
            etab = f.get("etablissement") or ""
            ville = f.get("ville") or ""
            niveau = f.get("niveau") or ""
            parts.append(f"  {j}. **{nom[:80]}** — {etab[:50]} {ville} (niveau {niveau}) [score={src.get('score', 0):.3f}]")
        parts.append("")

        # Pollution flag si présente
        pollution = r.get("pollution", {})
        polluted = pollution.get("polluted_entities", [])
        if polluted:
            parts.append(f"⚠️  **Entités polluées détectées** ({len(polluted)}) : {', '.join(polluted[:8])}{' ...' if len(polluted) > 8 else ''}")
            parts.append("")

        parts.append("---")
        parts.append("")

    parts.append("")
    parts.append("*Doc généré par `scripts/test_serving_e2e.py` sous l'ordre `2026-04-29-1146-claudette-orientia-sprint10-finalisation-rag-complet` (chantier E mesures empiriques).*")

    return "\n".join(parts)


def main() -> int:
    cfg = load_config()
    client = Mistral(api_key=cfg.mistral_api_key)

    print(f"==> Loading corpus from {FICHES_PATH}")
    fiches = json.loads(FICHES_PATH.read_text(encoding="utf-8"))
    print(f"    {len(fiches)} fiches chargées")

    pipeline_kwargs = {
        "use_metadata_filter": True,
        "use_golden_qa": True,
        "golden_qa_index_path": str(GOLDEN_QA_INDEX_PATH),
        "golden_qa_meta_path": str(GOLDEN_QA_META_PATH),
    }
    pipeline = OrientIAPipeline(client, fiches, **pipeline_kwargs)
    pipeline.load_index_from(str(INDEX_PATH))
    print(f"    Index loaded {INDEX_PATH.name}")

    print(f"\n==> Running {len(TEST_QUESTIONS)} test questions...")
    print(f"    Estimated cost ~$0.50-1.00 Mistral API, ETA ~5-10 min")
    print()

    results = []
    for i, question in enumerate(TEST_QUESTIONS, 1):
        print(f"[{i}/{len(TEST_QUESTIONS)}] {question[:80]}...", flush=True)
        result = run_one_question(pipeline, question)
        if result.get("error"):
            print(f"    ❌ {result['error']}")
        else:
            print(f"    ✅ t={result['t_total_ms']}ms | "
                  f"filter n_after={result.get('filter_stats', {}).get('n_after_filter', '?')} | "
                  f"pollution={result.get('pollution', {}).get('pollution_rate', 0) * 100:.0f}%")
        results.append(result)

    # Sauvegarder raw results JSONL
    OUTPUT_RAW_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_RAW_JSONL.open("w", encoding="utf-8") as f:
        for r in results:
            # Trim sources fiches pour size raisonnable du JSONL
            r_trimmed = dict(r)
            r_trimmed["sources"] = [
                {"score": s.get("score"), "fiche_nom": (s.get("fiche") or {}).get("nom") or (s.get("fiche") or {}).get("title"),
                 "fiche_id": (s.get("fiche") or {}).get("id")}
                for s in r.get("sources", [])
            ]
            f.write(json.dumps(r_trimmed, ensure_ascii=False) + "\n")
    print(f"\n==> Raw results : {OUTPUT_RAW_JSONL}")

    # Render rapport MD
    OUTPUT_DOC.parent.mkdir(parents=True, exist_ok=True)
    report = render_md_report(results)
    OUTPUT_DOC.write_text(report, encoding="utf-8")
    print(f"==> Rapport MD : {OUTPUT_DOC} ({len(report.splitlines())} lignes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
