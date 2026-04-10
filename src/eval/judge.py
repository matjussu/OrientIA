import json
import re
from anthropic import Anthropic


JUDGE_PROMPT = """Tu es un évaluateur expert en orientation scolaire française.

On te donne une question d'un étudiant et TROIS réponses anonymisées (A, B, C) produites par trois systèmes IA différents.

RÈGLE D'OR : les labels A, B, C sont anonymisés et randomisés par question. Tu NE DOIS PAS deviner ni essayer d'identifier quel système a produit quelle réponse. Évalue uniquement le contenu, pas ton intuition sur l'origine.

Évalue chaque réponse indépendamment sur les 6 critères suivants, chacun noté de 0 à 3.

CRITÈRES :

1. NEUTRALITÉ institutionnelle
   0 : ne mentionne que des écoles privées
   1 : mélange sans distinction
   2 : mentionne des formations publiques
   3 : priorise les labels officiels (SecNumEdu, CTI, CGE, Grade Master)

2. RÉALISME
   0 : "Tout est possible !" sans nuance
   1 : mentionne la sélectivité vaguement
   2 : cite des données de sélectivité
   3 : donne taux d'accès précis + alternatives réalistes

3. SOURÇAGE
   0 : aucune source
   1 : sources vagues ("on dit que...")
   2 : mentionne des institutions
   3 : cite des données vérifiables avec la source précise (ONISEP, Parcoursup, ANSSI, etc.)

4. DIVERSITÉ géographique
   0 : que Paris
   1 : principalement Paris + 1-2 villes
   2 : plusieurs régions
   3 : couverture territoriale adaptée au profil

5. AGENTIVITÉ
   0 : réponse fermée et directive
   1 : peu de choix
   2 : propose des options
   3 : options + question ouverte + encourage la réflexion

6. DÉCOUVERTE
   0 : ne mentionne que des métiers évidents
   1 : 1-2 suggestions classiques
   2 : propose des pistes originales
   3 : fait découvrir des métiers/formations méconnus et pertinents

IMPORTANT :
- Évalue uniquement la réponse fournie, pas tes propres connaissances.
- Sois objectif et cohérent entre les évaluations.
- Présente les scores du plus élevé au plus bas dans chaque rubrique pour réduire le rubric order bias.

Réponds UNIQUEMENT au format JSON valide, sans texte autour, exactement cette structure :

{
  "A": {"neutralite": X, "realisme": X, "sourcage": X, "diversite_geo": X, "agentivite": X, "decouverte": X, "total": X, "justification": "phrase courte"},
  "B": {"neutralite": X, "realisme": X, "sourcage": X, "diversite_geo": X, "agentivite": X, "decouverte": X, "total": X, "justification": "phrase courte"},
  "C": {"neutralite": X, "realisme": X, "sourcage": X, "diversite_geo": X, "agentivite": X, "decouverte": X, "total": X, "justification": "phrase courte"}
}

Où X est un entier entre 0 et 3 pour les critères, et total = somme des 6 critères (max 18).
"""


_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json(text: str) -> dict:
    match = _JSON_OBJECT_RE.search(text)
    if not match:
        raise ValueError(f"No JSON found in judge response: {text[:200]}")
    return json.loads(match.group(0))


def judge_question(
    client: Anthropic,
    question: str,
    answers: dict[str, str],
    model: str = "claude-sonnet-4-5",
) -> dict:
    user_content = f"""Question de l'étudiant : {question}

RÉPONSE A :
{answers['A']}

RÉPONSE B :
{answers['B']}

RÉPONSE C :
{answers['C']}
"""
    response = client.messages.create(
        model=model,
        max_tokens=2000,
        system=JUDGE_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )
    text = response.content[0].text
    return _extract_json(text)


def judge_all(
    client: Anthropic,
    responses_blind: list[dict],
    model: str = "claude-sonnet-4-5",
) -> list[dict]:
    all_scores = []
    for entry in responses_blind:
        scores = judge_question(client, entry["text"], entry["answers"], model=model)
        all_scores.append({
            "id": entry["id"],
            "category": entry["category"],
            "scores": scores,
        })
    return all_scores
