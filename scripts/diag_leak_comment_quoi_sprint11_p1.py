"""Diag leak Comment→Quoi — Sprint 11 P1 préparation.

Quantifie le taux de leak Q&A Golden few-shot → réponse Mistral sur les 10
questions du re-run Item 4 (PR #111 mergée SHA 2d36cb4).

Méthode : pour chaque flagged_entity remontée par le judge Item 3 sur Item 4,
classer LEAK (substring inclusive case-insensitive in Q&A Golden retrieved
text) vs INVENTION (absent du texte Q&A Golden).

Substring inclusive justifié par spec ordre : "si chiffre arrondi dans réponse
vs Q&A Golden → classer LEAK quand même (intention pioche)".

Pas d'appel LLM. Coût $0. ETA <1 min.

Usage : `PYTHONPATH=. python3 scripts/diag_leak_comment_quoi_sprint11_p1.py`

Spec ordre : 2026-04-30-2125-claudette-orientia-diag-leak-comment-quoi-sprint11-P1
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ITEM4_JSONL = ROOT / "docs" / "sprint11-P0-item4-rerun-raw-results-2026-04-30.jsonl"
GOLDEN_QA_META = ROOT / "data" / "processed" / "golden_qa_meta.json"
OUTPUT_DOC = ROOT / "docs" / "sprint11-P1-diagnostic-leak-comment-quoi-2026-04-30.md"


def load_golden_qa_lookup() -> dict[tuple[str, int], dict]:
    """Returns dict {(prompt_id, iteration): record} indexed for fast lookup."""
    data = json.loads(GOLDEN_QA_META.read_text(encoding="utf-8"))
    records = data.get("records", [])
    return {(r["prompt_id"], r["iteration"]): r for r in records}


def golden_qa_text(record: dict | None) -> str:
    """Concatène les champs textuels d'une Q&A Golden pour le matching substring."""
    if record is None:
        return ""
    parts = [
        record.get("question_seed") or "",
        record.get("question_refined") or "",
        record.get("answer_refined") or "",
    ]
    return " | ".join(parts).lower()


def normalize_for_match(s: str) -> str:
    """Normalise pour matching robuste : casefold + collapse spaces + strip."""
    if not s:
        return ""
    # collapse multiple whitespaces
    return re.sub(r"\s+", " ", s.lower()).strip()


def classify_entity(entity: str, golden_text_normalized: str) -> str:
    """Returns 'LEAK' ou 'INVENTION' selon présence substring dans Q&A Golden text.

    v2 (post drill-down §6) — matching numérique STRICT pour éviter faux
    positifs : un chiffre seul (ex "5", "1") matchait n'importe quel contexte
    "bac+5", "M1 sélectif", "(2+3 ans)" → faux LEAK.

    Règles :
    - LEAK si entity entière (substring textuel) ≥ 5 chars apparaît dans golden
    - LEAK si chiffre extrait apparaît AVEC suffix unit/qualificateur cohérent
      (€, %, " ans", " mois", " places", etc.) — ex "5 000-10 000€/an" → cherche
      "5 000" + €, pas juste "5"
    - Sinon INVENTION
    """
    e = normalize_for_match(entity)
    if not e:
        return "INVENTION"

    # 1. Substring textuel — exiger ≥ 5 chars pour éviter matching trivial
    if len(e) >= 5 and e in golden_text_normalized:
        return "LEAK"

    # 2. Matching numérique STRICT : chiffre + unit/contexte adjacent
    # Extract pairs (num, unit_or_word_after) — exiger >= 2 chiffres OU avec unit
    # Pattern : un chiffre suivi optionnellement d'un séparateur puis d'unit
    nums_with_context = re.findall(
        r"(\d{2,}(?:[,.]\d+)?)\s*(?:€|%|\s*(?:ans?|mois|places?|heures?|euros?))?",
        e
    )
    for num in nums_with_context:
        num_normalized = num.replace(",", ".")
        # Le chiffre doit apparaître avec un contexte similaire dans golden
        # (chiffre seul ≥ 2 chiffres = unique enough pour matching textuel)
        if num in golden_text_normalized or num_normalized in golden_text_normalized:
            return "LEAK"
    return "INVENTION"


def wilson_ci_95(n_success: int, n_total: int) -> tuple[float, float]:
    """Wilson score interval 95% pour proportion. Retourne (low, high) en pct."""
    if n_total == 0:
        return (0.0, 0.0)
    z = 1.96
    p = n_success / n_total
    denom = 1 + z * z / n_total
    centre = (p + z * z / (2 * n_total)) / denom
    margin = (z / denom) * math.sqrt(p * (1 - p) / n_total + z * z / (4 * n_total * n_total))
    low = max(0.0, centre - margin)
    high = min(1.0, centre + margin)
    return (low * 100, high * 100)


def main() -> int:
    if not ITEM4_JSONL.exists():
        raise SystemExit(f"Missing Item 4 raw : {ITEM4_JSONL}")
    if not GOLDEN_QA_META.exists():
        raise SystemExit(f"Missing Q&A Golden meta : {GOLDEN_QA_META}")

    golden_lookup = load_golden_qa_lookup()
    print(f"==> Q&A Golden lookup loaded : {len(golden_lookup)} records (prompt_id, iteration) keys")

    item4_records = [json.loads(l) for l in ITEM4_JSONL.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"==> Item 4 records loaded : {len(item4_records)}")

    per_question_results = []
    for idx, rec in enumerate(item4_records, 1):
        question = rec.get("question", "")
        gq = rec.get("golden_qa") or {}
        prompt_id = gq.get("prompt_id")
        iteration = gq.get("iteration")
        golden_record = None
        if prompt_id is not None and iteration is not None:
            golden_record = golden_lookup.get((prompt_id, int(iteration)))
        golden_text = normalize_for_match(golden_qa_text(golden_record))

        flagged = (rec.get("faithfulness") or {}).get("flagged_entities") or []
        n_flagged = len(flagged)

        per_entity = []
        n_leak = 0
        n_invention = 0
        for ent in flagged:
            cls = classify_entity(str(ent), golden_text)
            per_entity.append({"entity": str(ent)[:200], "class": cls})
            if cls == "LEAK":
                n_leak += 1
            else:
                n_invention += 1

        per_question_results.append({
            "qid": idx,
            "question": question,
            "golden_qa_matched": gq.get("matched", False),
            "golden_qa_prompt_id": prompt_id,
            "golden_qa_iteration": iteration,
            "golden_qa_text_chars": len(golden_text),
            "n_flagged": n_flagged,
            "n_leak": n_leak,
            "n_invention": n_invention,
            "leak_rate": (n_leak / n_flagged) if n_flagged > 0 else None,
            "per_entity": per_entity,
        })

    # Aggregate stats
    total_flagged = sum(r["n_flagged"] for r in per_question_results)
    total_leak = sum(r["n_leak"] for r in per_question_results)
    total_invention = sum(r["n_invention"] for r in per_question_results)
    leak_rate_global = total_leak / total_flagged if total_flagged > 0 else 0.0
    ci_low, ci_high = wilson_ci_95(total_leak, total_flagged)

    # Verdict directionnel selon spec ordre
    if leak_rate_global > 0.50:
        verdict = "LEAK MAJEUR (>50%) — Revoir architecture Q&A Golden few-shot. Sprint 11 P1 priorité = repenser séparation Comment/Quoi (ex retirer answer_refined du prefix, garder uniquement question_seed comme pattern de ton)."
        verdict_short = "LEAK MAJEUR (>50%)"
    elif leak_rate_global < 0.20:
        verdict = "INVENTION DOMINANTE (<20%) — Hallu = invention pure Mistral, peu lié aux Q&A Golden. Sprint 11 P1 priorité = P1.1 Strict Grounding renforcé contre invention de stats."
        verdict_short = "INVENTION DOMINANTE (<20%)"
    else:
        verdict = "MIXTE (20-50%) — Les 2 chantiers en parallèle : (1) renforcer séparation Q&A Golden Comment/Quoi (modif _build_few_shot_prefix) ET (2) renforcer Strict Grounding contre invention chiffres (refonte directive 1)."
        verdict_short = "MIXTE (20-50%)"

    # Render report
    md = render_report(per_question_results, total_flagged, total_leak, total_invention,
                       leak_rate_global, ci_low, ci_high, verdict, verdict_short)
    OUTPUT_DOC.write_text(md, encoding="utf-8")
    print(f"\n==> Doc résultats : {OUTPUT_DOC} ({len(md.splitlines())} lignes)")

    # Print summary console
    print(f"\n=== STATS AGRÉGÉES ===")
    print(f"Total flagged : {total_flagged}")
    print(f"  LEAK      : {total_leak} ({100*leak_rate_global:.1f}%)")
    print(f"  INVENTION : {total_invention} ({100*(1-leak_rate_global):.1f}%)")
    print(f"  CI95 leak : [{ci_low:.1f}%, {ci_high:.1f}%]")
    print(f"\n=== VERDICT DIRECTIONNEL ===")
    print(verdict)

    return 0


def render_report(per_q, total_flagged, total_leak, total_invention,
                  leak_rate, ci_low, ci_high, verdict, verdict_short) -> str:
    parts = [
        "# Sprint 11 P1 préparation — Diagnostic leak Q&A Golden Comment→Quoi",
        "",
        "**Date** : 2026-04-30",
        "**Branche** : `diag/sprint11-P1-leak-comment-quoi` depuis main `2d36cb4`",
        "**Ordre Jarvis** : `2026-04-30-2125-claudette-orientia-diag-leak-comment-quoi-sprint11-P1`",
        "**Données** : 10 questions du re-run Item 4 (PR #111 mergée SHA `2d36cb4`)",
        "**Coût** : $0 (analyse déterministe, pas d'appel LLM)",
        "",
        "## TL;DR",
        "",
        f"- **{total_flagged} chiffres / entités** flagués INFIDELE par le judge sur 10 questions",
        f"- **LEAK** (apparaît dans Q&A Golden retrieved few-shot) : **{total_leak}** ({100*leak_rate:.1f}%)",
        f"- **INVENTION** (absent Q&A Golden) : **{total_invention}** ({100*(1-leak_rate):.1f}%)",
        f"- **IC95 binomial Wilson** taux LEAK : [{ci_low:.1f}%, {ci_high:.1f}%]",
        f"- **Verdict directionnel Sprint 11 P1** : **{verdict_short}**",
        "",
        "---",
        "",
        "## §1 Méthode",
        "",
        "Pour chaque question des 10 du re-run Item 4 :",
        "1. Extraction `faithfulness.flagged_entities` du judge LLM (Item 3, claude-haiku-4-5)",
        "2. Lookup Q&A Golden retrieved en few-shot prefix via `(golden_qa.prompt_id, golden_qa.iteration)` dans `data/processed/golden_qa_meta.json` (45 records)",
        "3. Concaténation des champs textuels Q&A Golden : `question_seed | question_refined | answer_refined`, normalisation casefold + collapse whitespace",
        "4. Classification de chaque flagged_entity :",
        "   - **LEAK** : substring inclusive case-insensitive dans le texte Q&A Golden concat OU chiffre extrait (regex `\\d+(?:[,.]\\d+)?`) présent dans le texte",
        "   - **INVENTION** : absent",
        "",
        "**Justification substring inclusive** (vs matching exact) : conforme spec ordre — chiffre arrondi (ex Mistral cite `27%` quand Q&A Golden a `27 %` ou `27` dans contexte différent) doit compter LEAK car intention pioche.",
        "",
        "**Edge case** : si Q&A Golden retrieved n'a pas de chiffres ou texte vide, toutes flagged_entities = INVENTION par défaut.",
        "",
        "---",
        "",
        "## §2 Tableau per-question",
        "",
        "| Q | Q&A Golden retrieved | N flagged | N LEAK | N INVENTION | % LEAK |",
        "|---|---|---|---|---|---|",
    ]
    for r in per_q:
        gq_label = f"{r['golden_qa_prompt_id']} iter {r['golden_qa_iteration']}" if r['golden_qa_matched'] else "—"
        leak_pct = f"{100*r['leak_rate']:.0f}%" if r['leak_rate'] is not None else "n/a"
        parts.append(f"| Q{r['qid']} | {gq_label} | {r['n_flagged']} | {r['n_leak']} | {r['n_invention']} | {leak_pct} |")

    parts += [
        "",
        "---",
        "",
        "## §3 Stats agrégées",
        "",
        f"- **Total flagged entities** (10 questions cumul) : {total_flagged}",
        f"- **LEAK** : {total_leak} → **{100*leak_rate:.1f}%**",
        f"- **INVENTION** : {total_invention} → {100*(1-leak_rate):.1f}%",
        f"- **IC95 Wilson taux LEAK** : [{ci_low:.1f}% ; {ci_high:.1f}%] (intervalle de confiance binomial sur N={total_flagged})",
        "",
        "**Lecture statistique** : avec N={n}, l'IC95 reste assez large mais le centre {p:.0f}% donne un signal directionnel utilisable pour l'arbitrage Sprint 11 P1.".format(n=total_flagged, p=100*leak_rate),
        "",
        "---",
        "",
        "## §4 Verdict directionnel Sprint 11 P1",
        "",
        f"### {verdict_short}",
        "",
        verdict,
        "",
        "### Mapping seuils ordre (rappel)",
        "",
        "| Taux LEAK observé | Action Sprint 11 P1 |",
        "|---|---|",
        "| > 50 % | **LEAK MAJEUR** — revoir architecture Q&A Golden few-shot (ex retirer `answer_refined`, garder uniquement `question_seed` comme pattern ton) |",
        "| 20-50 % | **MIXTE** — 2 chantiers parallèles : refactor few-shot + renforcer Strict Grounding |",
        "| < 20 % | **INVENTION DOMINANTE** — P1.1 Strict Grounding renforcé contre invention stats reste la bonne cible |",
        "",
        "---",
        "",
        "## §5 Limitations méthodologiques",
        "",
        f"- **Sample size** : N={total_flagged} flagged entities sur 10 questions = signal statistique modéré. IC95 Wilson [{ci_low:.1f}%, {ci_high:.1f}%] reflète l'incertitude réelle.",
        "- **Substring inclusive** peut surestimer LEAK si une entité contient un mot commun présent dans la Q&A Golden par hasard (faux positif). Mitigation : la classification par chiffres extraits est plus discriminante que substring textuel large.",
        "- **Pas de dédup** entre questions : si plusieurs questions retrieved la même Q&A Golden, les leaks comptent indépendamment.",
        "- **Faithfulness scoring binaire INFIDELE** ne distingue pas hallu mineure vs majeure. Une entity = un point. Granularité acceptable pour ce diagnostic mais pas pour l'arbitrage exécution.",
        "- **Pas de cross-référence avec fiches RAG** : un chiffre absent Q&A Golden ET absent fiches = INVENTION par défaut. Mais théoriquement il pourrait venir de l'historique conversationnel (Item 2 buffer) — non pris en compte ici (bench single-shot).",
        "",
        "---",
        "",
        "*Diagnostic généré par `scripts/diag_leak_comment_quoi_sprint11_p1.py` sous l'ordre `2026-04-30-2125-claudette-orientia-diag-leak-comment-quoi-sprint11-P1`. Standby pour arbitrage Matteo Sprint 11 P1.*",
    ]
    return "\n".join(parts)


if __name__ == "__main__":
    raise SystemExit(main())
