"""Prepare a clean user-test pack — just questions and answers, no context.

Extracts the 6 cyber/data + 4 santé responses from the existing diff
files and produces a single reader-friendly markdown file. Goal: give
2-3 lycéens real answers to read and provide feedback on.

Output: results/user_test/answers_to_show.md
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from datetime import datetime


OUT_PATH = Path("results/user_test/answers_to_show.md")
FEEDBACK_PATH = Path("results/user_test/feedback_template.md")


def _load_json(path: str) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> None:
    cyber_responses = _load_json("results/vague_a_diff/responses.json")
    sante_responses = _load_json("results/sante_diff/responses.json")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = [
        "# OrientIA — Réponses test utilisateur",
        "",
        f"*Généré le {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        "",
        "Ce document contient 10 questions d'orientation + les réponses générées "
        "par OrientIA. À montrer à des lycéens ou étudiants pour recueillir leur "
        "feedback sincère (voir `feedback_template.md` à côté).",
        "",
        "**Consignes pour la personne testée :**",
        "1. Lis chaque réponse comme si tu posais vraiment la question",
        "2. Note ce qui est **clair** vs **confus**",
        "3. Note les chiffres qui **t'aident** vs ceux qui **t'effraient** ou qui te semblent **suspects**",
        "4. Dis si tu **ferais confiance** à ces conseils pour décider",
        "",
        "---",
        "",
    ]

    def _render(r: dict, label: str, number: int) -> list[str]:
        return [
            f"## Question {number} — {label}",
            "",
            f"> **{r['question']}**",
            "",
            "### Réponse OrientIA",
            "",
            r.get("answer", r.get("response", "(réponse manquante)")),
            "",
            "---",
            "",
        ]

    counter = 1
    for r in cyber_responses:
        lines.extend(_render(r, f"[{r['category']}]", counter))
        counter += 1
    for r in sante_responses:
        lines.extend(_render(r, f"[{r['category']}]", counter))
        counter += 1

    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({counter - 1} questions)")

    # Feedback template
    fb: list[str] = [
        "# Feedback test utilisateur — OrientIA",
        "",
        "*Remplir une fiche par personne testée. Grille simple à noter sur chaque réponse.*",
        "",
        "## Profil de la personne testée",
        "",
        "- Prénom / âge :",
        "- Statut (terminale, bac+N, en réorientation) :",
        "- Spécialités / bac :",
        "- Idée actuelle d'orientation :",
        "",
        "## Évaluation par question",
        "",
        "Pour chaque question dans `answers_to_show.md` :",
        "",
        "| Q# | Clair (1-5) | Utile (1-5) | Confiance (1-5) | Ce qui marche | Ce qui bloque / confus | Aurait-tu lu en entier ? |",
        "|----|-------------|-------------|-----------------|---------------|-----------------------|-------------------------|",
        "| Q1 |             |             |                 |               |                        |                         |",
        "| Q2 |             |             |                 |               |                        |                         |",
        "| Q3 |             |             |                 |               |                        |                         |",
        "| Q4 |             |             |                 |               |                        |                         |",
        "| Q5 |             |             |                 |               |                        |                         |",
        "| Q6 |             |             |                 |               |                        |                         |",
        "| Q7 |             |             |                 |               |                        |                         |",
        "| Q8 |             |             |                 |               |                        |                         |",
        "| Q9 |             |             |                 |               |                        |                         |",
        "| Q10|             |             |                 |               |                        |                         |",
        "",
        "## Questions ouvertes (après toutes les questions)",
        "",
        "1. **Les chiffres** (taux, vœux, salaires) t'ont-ils aidé ou noyé ? Lesquels t'ont le plus parlé ?",
        "",
        "2. **La longueur** des réponses : trop long, trop court, juste bien ?",
        "",
        "3. **Confiance** : si un conseiller d'orientation t'avait donné cette réponse, aurais-tu suivi les conseils ? Pourquoi ?",
        "",
        "4. **Vs ChatGPT** : Si tu avais posé cette question à ChatGPT, qu'est-ce qui serait mieux/moins bien ici ?",
        "",
        "5. **Ce qui manque** : quelle info aurais-tu voulu qu'on ajoute ?",
        "",
        "6. **Mention trends** : quand tu as vu \"devenue plus sélective\" ou \"+28% de vœux depuis 2023\", est-ce que ça t'a aidé ou c'est du bruit ?",
        "",
        "7. **Tu utiliserais ce truc** : dans quelles circonstances tu ouvrirais un outil comme ça plutôt que d'autres moyens (parents, prof, CIO, ChatGPT, L'Étudiant) ?",
        "",
        "## Observations libres",
        "",
        "(Tout ce qui t'a frappé, surpris, agacé, plu — brut de décoffrage)",
        "",
    ]
    FEEDBACK_PATH.write_text("\n".join(fb), encoding="utf-8")
    print(f"Wrote {FEEDBACK_PATH}")


if __name__ == "__main__":
    main()
