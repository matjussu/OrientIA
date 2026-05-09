"""Phase projet minimal (V4) — déontologie Psy-EN reportée ADR-036.

Implementation light : détecte si la question porte sur un sujet à enjeu
fort (HEC, ESSEC, ESCP, médecine, PASS, kiné, orthophoniste, véto,
Sciences Po, polytechnique, dentaire). Si oui, appende une ligne invitant
l'utilisateur à réfléchir au projet + redirect CIO/Psy-EN.

Cohérent avec ADR-036 sans implémentation complète phase projet (reportée
à S2 Axe 2 agentic ProfileClarifier).

Step 11.7 chantier 4 (2026-05-09) : skip contextuel + 1 question au lieu
de 3. Le user a observé sur le dump step 11.5 que le footer s'injectait
sur des questions inadéquates (B1 "11/20 pour HEC ?" et B5 "Sciences Po
13/20 réaliste ?" reçoivent "Que sais-tu du métier au quotidien
(stages, rencontres, shadowing) ?" — ridicule pour Sciences Po qui
n'est pas un métier, ou pour une question de réalisme/sélectivité).

Politique v2 :
- Skip si la question est sur le réalisme/sélectivité ("puis-je", "11/20",
  "réaliste", "moyenne", "places", "taux d'accès", "compar")
- Réduire à 1 question contextuelle au topic + 1 ligne CIO
- Variants par topic : médecine/PASS → stages observation, HEC/ESSEC →
  projet pro commerce, Sciences Po/Polytechnique → enjeu public/scientifique
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

# Step 11.7 chantier 4 — questions où phase_projet n'apporte rien
# (la personne demande de la sélectivité/réalisme, pas une réflexion
# de projet motivationnelle).
SKIP_PATTERNS = [
    # Réalisme / faisabilité avec moyenne
    r"\b(?:puis-je|peux-je|est-ce que je peux|est-ce que c'est possible)\b",
    r"\bréalist(?:e|ique)\b",
    r"\b(?:avec|j'ai)\s+\d{1,2}\s*(?:de|/)\s*(?:moyenne|/?20)",
    r"\b\d{1,2}\s*/\s*20\b",
    # Sélectivité / chiffres
    r"\b(?:sélectivité|selectivite|taux d'accès|taux d'admission)\b",
    r"\b(?:places? disponibles?|nombre de places?|combien de places?)\b",
    # Comparaison
    r"\b(?:compar(?:e|er|aison)|vs|versus|ou\s+plut[oô]t)\b",
    # Recherche d'information factuelle
    r"\b(?:quel(?:le)?s?\s+(?:sont|formations|écoles|cursus))\b",
]


# Step 11.7 chantier 4 — Footers contextuels par topic (1 question + CIO)
# au lieu du PHASE_PROJET_FOOTER unique avec 3 questions.

_TOPIC_TO_QUESTION: dict[str, str] = {
    # Métiers santé : focus sur observation terrain
    "médecine": "As-tu pu observer ces métiers en stage ou en consultation ?",
    "médecin": "As-tu pu observer ces métiers en stage ou en consultation ?",
    "médical": "As-tu pu observer ces métiers en stage ou en consultation ?",
    "PASS": "As-tu pu observer le métier de médecin en stage ou en consultation ?",
    "LAS": "As-tu pu observer le métier de médecin en stage ou en consultation ?",
    "L.AS": "As-tu pu observer le métier de médecin en stage ou en consultation ?",
    "kin": "As-tu pu observer le métier de kinésithérapeute en stage ?",
    "orthophon": "As-tu pu observer le métier d'orthophoniste en consultation ?",
    "vét": "As-tu pu observer le métier de vétérinaire en cabinet ou refuge ?",
    "dentaire": "As-tu pu observer le métier de dentiste en cabinet ?",
    # Écoles de commerce : focus sur projet pro
    "HEC": "Quel projet pro motive ton intérêt pour le commerce/management ?",
    "ESSEC": "Quel projet pro motive ton intérêt pour le commerce/management ?",
    "ESCP": "Quel projet pro motive ton intérêt pour le commerce/management ?",
    # Sciences Po / Polytechnique : focus enjeux publics/scientifiques
    "Sciences Po": "Y a-t-il un domaine ou un enjeu public spécifique qui t'attire ?",
    "Polytechnique": "Quel domaine scientifique ou technique te passionne particulièrement ?",
}


def _question_for_topic(topic: str) -> str:
    """Retourne la question contextuelle au topic (insensible à la casse)."""
    topic_lower = topic.lower()
    # Match partiel : "Sciences Po" matche "sciences po" et "Sciences  Po"
    for key, q in _TOPIC_TO_QUESTION.items():
        if key.lower() in topic_lower:
            return q
    # Fallback générique
    return "Qu'est-ce qui te motive précisément dans ce choix ?"


def _build_phase_projet_footer(topic: str) -> str:
    """Step 11.7 chantier 4 — footer contextuel (1 question + CIO court)."""
    question = _question_for_topic(topic)
    return (
        "\n\n"
        f"💭 **Avant de te lancer** : {question}\n\n"
        "👤 Pour structurer ton projet en profondeur, parle-en au **CIO** "
        "ou au **Psy-EN** de ton lycée."
    )


# Footer historique (gardé pour compat tests si référencé)
PHASE_PROJET_FOOTER = (
    "\n\n"
    "💭 **Avant de décider cette voie** :\n"
    "1. Qu'est-ce qui te motive précisément dans ce choix ?\n"
    "2. Que sais-tu du métier au quotidien (stages, rencontres, shadowing) ?\n"
    "3. As-tu rencontré quelqu'un qui fait ce métier ?\n"
    "\n"
    "👤 Parle-en au **CIO** le plus proche ou au **Psy-EN** de ton lycée. "
    "Ils sont formés pour t'aider à structurer ton projet — pas juste à choisir une formation."
)


def detect_high_stakes_topic(question: str) -> str | None:
    """Retourne le premier topic à enjeu fort détecté, ou None."""
    for pat in HIGH_STAKES_TRIGGERS:
        m = re.search(pat, question, re.IGNORECASE | re.UNICODE)
        if m:
            return m.group(0)
    return None


def is_factual_or_realism_question(question: str) -> bool:
    """Step 11.7 chantier 4 — True si la question est sur réalisme/
    sélectivité/comparaison/recherche d'info factuelle. Dans ces cas,
    le footer phase_projet "Qu'est-ce qui te motive ?" est inadéquat
    (la personne ne cherche PAS de la motivation, elle cherche un fait
    chiffré ou un avis sur ses chances)."""
    for pat in SKIP_PATTERNS:
        if re.search(pat, question, re.IGNORECASE | re.UNICODE):
            return True
    return False


def already_has_project_prompts(answer: str) -> bool:
    """True si la réponse contient déjà un prompt de phase projet
    (évite duplicate si le generator l'a déjà inclus)."""
    if "qu'est-ce qui te motive" in answer.lower():
        return True
    if "avant de décider" in answer.lower():
        return True
    if "avant de te lancer" in answer.lower():
        return True
    if re.search(r"as-tu\s+rencontré\s+quelqu'un\s+qui\s+fait", answer, re.IGNORECASE):
        return True
    if re.search(r"as-tu\s+pu\s+observer", answer, re.IGNORECASE):
        return True
    return False


def append_phase_projet(answer: str, question: str) -> tuple[str, bool]:
    """Appende un footer phase projet contextuel si la question déclenche.

    Step 11.7 chantier 4 — politique v2 :
    1. Détecte un topic à enjeu fort (HEC, médecine, etc.)
    2. Si la question est factuelle/réalisme/comparaison → SKIP
       (le footer "Qu'est-ce qui te motive ?" est inadéquat sur
       "11/20 pour HEC ?" — la personne cherche un avis sur ses
       chances, pas de la motivation)
    3. Si déjà présent dans answer → SKIP
    4. Sinon → appende footer contextuel (1 question topic-aware + CIO)

    Retourne (answer_augmenté, was_appended).
    """
    topic = detect_high_stakes_topic(question)
    if topic is None:
        return answer, False
    if is_factual_or_realism_question(question):
        return answer, False
    if already_has_project_prompts(answer):
        return answer, False
    footer = _build_phase_projet_footer(topic)
    return answer.rstrip() + footer, True
