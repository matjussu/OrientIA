"""Compare 2 spot-check V5 reports (pre/post Chantier C+ fix `fiche_to_text`).

Pré-fix : `docs/SPOT_CHECK_V5_2026-05-13.md` (regen 2026-05-13 matin sur HEAD
sans patch). Post-fix : `docs/SPOT_CHECK_V5_<date>.md` (à régénérer après
re-embed avec patch).

Métriques calculées par fichier puis comparées :

1. **n_domain_match_top5** : nb questions avec ≥1 fiche du domain attendu
   (métrique binaire historique).
2. **pct_top5_sources_formation** : % de fiches top-5 qui sont `(formation)`
   sur l'ensemble des questions (métrique engineer 2026-05-13, plus solide).
   Cible attendue : 60.7% pre → ~30% post (les annexes prennent leur place).
3. **n_citations_total** : total des `[source SX]` (single + combiné +
   virgule) — proxy de l'engagement du LLM avec les sources retrievées.
4. **n_refusals** : nb réponses "info non disponible / je n'ai pas / je
   préfère ne pas".
5. **mean_latency_s** : latence moyenne.

Usage :
    python scripts/diff_spot_check_v5_pre_post_chantier_c_plus.py \\
        --pre docs/SPOT_CHECK_V5_2026-05-13.md \\
        --post docs/SPOT_CHECK_V5_2026-05-14.md
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path


def parse_spot_check_md(path: Path) -> dict:
    """Parse un rapport spot_check_v5 markdown vers dict de métriques."""
    text = path.read_text(encoding="utf-8")

    # Block par question : "### QN — question"
    questions = []
    blocks = re.split(r"^### Q\d+ — ", text, flags=re.MULTILINE)[1:]

    pct_top5_formation_per_q: list[float] = []
    n_domain_match_per_q: list[int] = []
    n_citations_per_q: list[int] = []
    refusal_flags: list[bool] = []
    latencies: list[float] = []

    refusal_markers = (
        "n'ai pas de données",
        "n'ai pas de formation",
        "n'ai pas d'information",
        "informations non disponibles",
        "information non disponible",
        "je préfère ne pas répondre",
        "mes sources ne fournissent",
        "ne sont pas disponibles dans mes sources",
        "données non disponibles",
    )

    for block in blocks:
        # Top-5 domain match : "X/5 fiches du domain attendu"
        m_dm = re.search(r"(\d+)/5 fiches du domain attendu", block)
        n_dm = int(m_dm.group(1)) if m_dm else 0
        n_domain_match_per_q.append(n_dm)

        # Sources top-5 : extraire les S1..S5 [domain]
        top5_lines = re.findall(r"S\d+: \[([^\]]+)\]", block)
        if top5_lines:
            n_formation = sum(1 for d in top5_lines if d == "(formation)")
            pct_top5_formation_per_q.append(100.0 * n_formation / len(top5_lines))

        # Citations [source SX] (support combiné/virgule)
        n_cit = 0
        for tag in re.findall(r"\[source\s+([^\]]+)\]", block):
            n_cit += len(re.findall(r"S\d+", tag))
        n_citations_per_q.append(n_cit)

        # Refus détection
        block_lc = block.lower()
        refusal_flags.append(any(m in block_lc for m in refusal_markers))

        # Latence : "Latence : X.XXs"
        m_lat = re.search(r"Latence\*?\*?\s*:\s*([\d.]+)\s*s", block)
        if m_lat:
            latencies.append(float(m_lat.group(1)))

    n_total = len(blocks)
    return {
        "n_questions": n_total,
        "n_domain_match_at_least_1": sum(1 for n in n_domain_match_per_q if n >= 1),
        "domain_match_per_q": n_domain_match_per_q,
        "pct_top5_formation_overall": (
            sum(pct_top5_formation_per_q) / len(pct_top5_formation_per_q)
            if pct_top5_formation_per_q else 0
        ),
        "pct_top5_formation_per_q": pct_top5_formation_per_q,
        "n_citations_total": sum(n_citations_per_q),
        "n_citations_per_q": n_citations_per_q,
        "n_refusals": sum(refusal_flags),
        "refusal_per_q": refusal_flags,
        "mean_latency_s": sum(latencies) / len(latencies) if latencies else 0,
        "latencies": latencies,
    }


def fmt_diff(pre: float, post: float, unit: str = "", inverse_is_good: bool = False) -> str:
    diff = post - pre
    sign = "+" if diff > 0 else ""
    arrow = ""
    if inverse_is_good:
        if diff < 0: arrow = " ✅ (mieux)"
        elif diff > 0: arrow = " ❌ (pire)"
    else:
        if diff > 0: arrow = " ✅ (mieux)"
        elif diff < 0: arrow = " ❌ (pire)"
    return f"{pre:.2f}{unit} → {post:.2f}{unit} ({sign}{diff:.2f}{unit}){arrow}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pre", required=True, help="Pre-fix spot-check .md")
    parser.add_argument("--post", required=True, help="Post-fix spot-check .md")
    args = parser.parse_args()

    pre = parse_spot_check_md(Path(args.pre))
    post = parse_spot_check_md(Path(args.post))

    print(f"\n=== Diff spot-check V5 — Chantier C+ ===")
    print(f"Pre  : {args.pre}")
    print(f"Post : {args.post}")
    print(f"N questions : {pre['n_questions']} → {post['n_questions']}")
    print()
    print(f"Top-5 domain match  : {pre['n_domain_match_at_least_1']}/13 → {post['n_domain_match_at_least_1']}/13")
    print(f"  per Q (pre)       : {pre['domain_match_per_q']}")
    print(f"  per Q (post)      : {post['domain_match_per_q']}")
    print()
    print(f"%% top-5 = (formation) : {fmt_diff(pre['pct_top5_formation_overall'], post['pct_top5_formation_overall'], '%', inverse_is_good=True)}")
    print(f"  (cible : ~60.7%% → ~30%% — annexes prennent leur place)")
    print()
    print(f"Citations total      : {fmt_diff(pre['n_citations_total'], post['n_citations_total'])}")
    print(f"Refusals (sur 13)    : {fmt_diff(pre['n_refusals'], post['n_refusals'], inverse_is_good=True)}")
    print(f"Latence moyenne (s)  : {fmt_diff(pre['mean_latency_s'], post['mean_latency_s'], 's', inverse_is_good=True)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
