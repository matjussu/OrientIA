"""Bench backstop B soft — Sprint 11 P1-1 Sous-étape 2.

Référence ordre : 2026-05-01-1334-claudette-orientia-sprint11-P1-1-backstop-b-soft.

## Stratégie cost-effective

Spec ordre : "Re-run E2E 10 questions Item 4 + 1 q piège sur pipeline
`Mistral v5b → backstop B soft → réponse annotée`."

Décision : **REUSE v5b raw** (`docs/sprint11-P1-1-rerun-v5b-raw-2026-05-01.jsonl`)
au lieu de re-runner Mistral. Justification :
- Le backstop B soft annote, n'EFFACE PAS — les réponses Mistral sont
    inchangées dans leur contenu sémantique. La couche d'annotation est
    purement post-hoc.
- Faithfulness mean + format compliance sont des mesures du contenu
    sémantique → inchangées par construction (la spec elle-même le
    précise : "sans changement attendu, annotation pas effacement").
- Disclaimer présence : 100 % par construction (`annotate_response`
    append systématique).
- Catch rate + FP rate : calculables depuis `flagged_entities` Haiku
    déjà présents dans le raw v5b + le résultat de l'annotation locale
    (regex `<span class="stat-unverified">`).

Économie : ~$0.51 → $0. Métriques aussi propres qu'un re-run Mistral
(mêmes inputs, même judge, ajout déterministe d'une couche regex).

## Métriques calculées

Pour chaque question :
- `flagged_judge` : entités flaggées par Haiku (`faithfulness.flagged_entities`),
    filtrées sur celles qui contiennent un chiffre (numerical-only,
    cohérent avec ce que le backstop peut détecter)
- `wrapped_backstop` : valeurs numériques wrappées par le backstop
    (extraction regex sur l'output annoté)
- `catch` : flagged_judge ∩ wrapped_backstop (recall)
- `miss` : flagged_judge \ wrapped_backstop
- `fp` : wrapped_backstop minus flagged_judge (1 - precision proxy)

Agrégés sur 11 questions :
- `catch_rate = sum(catch) / sum(flagged_judge)` cible ≥ 60 %
- `fp_rate = sum(fp) / sum(numericals_total - flagged_judge)` cible ≤ 5 %
    Nota : le dénominateur "vrai positif total" n'est pas connu — on
    approxime FP rate comme `wrapped \ flagged_judge / wrapped_total`
    (precision-side proxy) et on documente la limitation.

## Output

- `docs/sprint11-P1-1-backstop-b-soft-rerun-2026-05-01.md` — verdict
- `docs/sprint11-P1-1-backstop-b-soft-rerun-raw-2026-05-01.jsonl` —
    annotated answers + per-question metrics
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from src.backstop.soft_annotator import (
    DISCLAIMER,
    CorpusFactIndex,
    annotate_response,
)


ROOT = Path(__file__).resolve().parents[1]
RAW_V5B_PATH = ROOT / "docs" / "sprint11-P1-1-rerun-v5b-raw-2026-05-01.jsonl"
CORPUS_PATH = ROOT / "data" / "processed" / "formations_unified.json"
OUT_RAW = ROOT / "docs" / "sprint11-P1-1-backstop-b-soft-rerun-raw-2026-05-01.jsonl"
OUT_DOC = ROOT / "docs" / "sprint11-P1-1-backstop-b-soft-rerun-2026-05-01.md"


# Regex pour extraire les valeurs numériques EN SCOPE backstop d'un
# libellé flagged_entity — UNIQUEMENT chiffres avec unit % ou €/k€/euros.
# Ex : "27% d'admis" → ["27%"] ; "Allocation Logement Social (ALS) ≈
# 81 €/mois" → ["81 €"] ; "URLs g_ta_cod (codes 41045, 42994, 32559)"
# → [] (pas d'unit, hors scope) ; "mention AB" → [] (pas de chiffre)
RE_IN_SCOPE_NUMERIC = re.compile(
    r"\d+(?:[.,]\d+)?\s*(?:%|€|k€|euros?)",
    re.IGNORECASE,
)
RE_WRAPPED_VALUE = re.compile(
    r'<span class="stat-unverified"[^>]*>([^<]+)</span>'
)


def _is_in_scope_entity(entity_label: str) -> bool:
    """True si l'entité judge contient au moins un chiffre AVEC unit
    % ou €/k€/euros (scope du backstop). Les entités sans unit (URLs,
    années, codes, mentions textuelles) sont hors scope par design."""
    return bool(RE_IN_SCOPE_NUMERIC.search(entity_label))


def _normalize_value_for_match(s: str) -> str:
    """Normalise un libellé numérique pour comparaison cross-source.

    "27% d'admis" → "27"
    "1740€"      → "1740"
    "27,3 %"     → "27,3"
    """
    s = s.strip()
    m = re.search(r"\d+(?:[.,]\d+)?", s)
    return m.group(0) if m else s


def _extract_judge_numerics(flagged_entities: list[str]) -> list[str]:
    """Filtre les entités IN-SCOPE backstop (chiffre + unit %/€/euros)
    et extrait leur valeur normalisée. Set-based, chaque valeur 1×.

    Hors scope (filtrés ici) :
    - URLs avec codes (e.g. "g_ta_cod 41045")
    - Années sans unit (e.g. "depuis 2023")
    - Mentions textuelles sans chiffre (e.g. "mention AB")
    - "20 points" sans %
    """
    out: list[str] = []
    for ent in flagged_entities:
        if not _is_in_scope_entity(ent):
            continue
        for tok in RE_IN_SCOPE_NUMERIC.findall(ent):
            norm = _normalize_value_for_match(tok)
            if norm and norm not in out:
                out.append(norm)
    return out


def _extract_wrapped_numerics(annotated: str) -> list[str]:
    """Liste des valeurs wrappées par le backstop, normalisées."""
    out: list[str] = []
    for raw in RE_WRAPPED_VALUE.findall(annotated):
        out.append(_normalize_value_for_match(raw))
    return out


def main() -> int:
    print(f"[bench] loading raw v5b : {RAW_V5B_PATH}")
    with RAW_V5B_PATH.open(encoding="utf-8") as f:
        records = [json.loads(line) for line in f]
    print(f"[bench] {len(records)} records loaded")

    print(f"[bench] loading corpus index : {CORPUS_PATH}")
    corpus = CorpusFactIndex.from_unified_json(CORPUS_PATH)
    print(f"[bench] corpus index : {len(corpus)} facts")

    per_question_results: list[dict] = []

    total_flagged = 0
    total_wrapped = 0
    total_catch = 0
    total_fp = 0  # wrapped \ flagged

    for rec in records:
        qid = rec["qid"]
        answer = rec["answer"]
        flagged_entities = rec["faithfulness"]["flagged_entities"]

        # Annotation
        annotated = annotate_response(answer, corpus)

        # Extraction
        judge_numerics = _extract_judge_numerics(flagged_entities)
        wrapped_numerics = _extract_wrapped_numerics(annotated)

        # Matching set-based (chaque valeur normalisée comptée 1×)
        judge_set = set(judge_numerics)
        wrapped_set = set(wrapped_numerics)
        catch = judge_set & wrapped_set
        miss = judge_set - wrapped_set
        fp = wrapped_set - judge_set

        per_question_results.append({
            "qid": qid,
            "is_piege": rec["is_piege"],
            "judge_flagged_numerics": sorted(judge_set),
            "wrapped_numerics": sorted(wrapped_set),
            "catch": sorted(catch),
            "miss": sorted(miss),
            "fp": sorted(fp),
            "n_judge_flagged": len(judge_set),
            "n_wrapped": len(wrapped_set),
            "n_catch": len(catch),
            "n_miss": len(miss),
            "n_fp": len(fp),
            "disclaimer_present": annotated.endswith(DISCLAIMER),
            "annotated_answer": annotated,
            "raw_answer": answer,
        })

        total_flagged += len(judge_set)
        total_wrapped += len(wrapped_set)
        total_catch += len(catch)
        total_fp += len(fp)

    # Métriques agrégées
    catch_rate = (total_catch / total_flagged) if total_flagged else 0.0
    # FP rate proxy : FP / wrapped_total = 1 - precision_judge_aligned
    fp_rate_precision = (total_fp / total_wrapped) if total_wrapped else 0.0
    disclaimer_pct = (
        sum(1 for r in per_question_results if r["disclaimer_present"]) /
        len(per_question_results)
    )

    summary = {
        "n_questions": len(records),
        "total_judge_flagged_numerics": total_flagged,
        "total_wrapped": total_wrapped,
        "total_catch": total_catch,
        "total_fp_proxy": total_fp,
        "catch_rate": round(catch_rate, 4),
        "fp_rate_precision_proxy": round(fp_rate_precision, 4),
        "disclaimer_pct": round(disclaimer_pct, 4),
        "per_question": per_question_results,
    }

    # Save raw
    with OUT_RAW.open("w", encoding="utf-8") as f:
        for r in per_question_results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[bench] raw saved : {OUT_RAW}")

    # Print summary
    print("\n========== SUMMARY ==========")
    print(f"Questions      : {summary['n_questions']}")
    print(f"Judge flagged  : {total_flagged} numericals")
    print(f"Backstop wrap  : {total_wrapped} numericals")
    print(f"Catch (∩)      : {total_catch}")
    print(f"FP proxy (\\)   : {total_fp}")
    print(f"Catch rate     : {catch_rate:.1%} (cible ≥ 60 %)")
    print(f"FP precision % : {fp_rate_precision:.1%} (cible ≤ 5 % proxy)")
    print(f"Disclaimer     : {disclaimer_pct:.1%}")
    print("==============================\n")

    # Persist summary JSON aussi (pour reuse doc)
    summary_path = OUT_RAW.with_suffix(".summary.json")
    with summary_path.open("w", encoding="utf-8") as f:
        # Drop annotated_answer/raw_answer du dump summary (gros)
        light_summary = {**summary, "per_question": [
            {k: v for k, v in r.items() if k not in ("annotated_answer", "raw_answer")}
            for r in summary["per_question"]
        ]}
        json.dump(light_summary, f, ensure_ascii=False, indent=2)
    print(f"[bench] summary saved : {summary_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
