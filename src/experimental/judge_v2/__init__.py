"""judge_v2/ — méthodologie fact-check reweight Phase G (publication).

`judge_v2` applique une re-pondération post-judge basée sur le fact-check
Haiku/Claude (cf src/eval/fact_check_claude.py). `run_judge_v2` est le CLI
qui consomme un blind_scores.json existant et produit blind_scores_v2.json.

Reste accessible pour reproductibilité des résultats Phase G mais ne fait
pas partie du pipeline produit (niveau 2).
"""
