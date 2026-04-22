"""Phase projet minimal (V4) — déontologie Psy-EN reportée ADR-036.

Implementation light : détecte si la question porte sur un sujet à enjeu
fort (HEC, ESSEC, ESCP, médecine, PASS, kiné, orthophoniste, véto,
Sciences Po, polytechnique, dentaire). Si oui, appende une ligne invitant
l'utilisateur à réfléchir au projet (3 Q max) + redirect CIO/Psy-EN.

Cohérent avec ADR-036 sans implémentation complète phase projet (reportée
à S2 Axe 2 agentic ProfileClarifier).
"""
from __future__ import annotations

import re


# Topics à enjeu fort (sélectivité + décision lourde + pressure sociale)
HIGH_STAKES_TRIGGERS = [
    r"\bHEC\b",
    r"\bESSEC\b",
    r"\bESCP\b",
    r"\b(?:médecine|médecin|médical)\b",
    r"\bPASS\b",
    r"\bL\.?AS\b",
    r"\bkin[eé]",
    r"\borthophon",
    r"\bvét[eé]rinaire\b",
    r"\bSciences?\s+Po\b",
    r"\bPolytechnique\b",
    r"\bdentaire\b|\bchirurgien-dentiste\b",
]

PHASE_PROJET_FOOTER = """
💭 **Avant de décider cette voie** :
1. Qu'est-ce qui te motive précisément dans ce choix ?
2. Que sais-tu du métier au quotidien (stages, rencontres, shadowing) ?
3. As-tu rencontré quelqu'un qui fait ce métier ?

👤 Parle-en au **CIO** le plus proche ou au **Psy-EN** de ton lycée. Ils sont formés pour t'aider à structurer ton projet — pas juste à choisir une formation."""


def detect_high_stakes_topic(question: str) -> str | None:
    """Retourne le premier topic à enjeu fort détecté, ou None."""
    for pat in HIGH_STAKES_TRIGGERS:
        m = re.search(pat, question, re.IGNORECASE | re.UNICODE)
        if m:
            return m.group(0)
    return None


def already_has_project_prompts(answer: str) -> bool:
    """True si la réponse contient déjà un prompt de phase projet
    (évite duplicate si le generator l'a déjà inclus)."""
    if "qu'est-ce qui te motive" in answer.lower():
        return True
    if "avant de décider" in answer.lower():
        return True
    if re.search(r"as-tu\s+rencontré\s+quelqu'un\s+qui\s+fait", answer, re.IGNORECASE):
        return True
    return False


def append_phase_projet(answer: str, question: str) -> tuple[str, bool]:
    """Appende le footer phase projet si la question déclenche + pas déjà présent.
    Retourne (answer_augmenté, was_appended)."""
    topic = detect_high_stakes_topic(question)
    if topic is None:
        return answer, False
    if already_has_project_prompts(answer):
        return answer, False
    return answer.rstrip() + "\n" + PHASE_PROJET_FOOTER, True
