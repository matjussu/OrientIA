import json
import re
from pathlib import Path
from anthropic import Anthropic


JUDGE_PROMPT = """Tu es un évaluateur expert en orientation scolaire française.

On te donne une question d'un étudiant et N réponses anonymisées (étiquetées A, B, C, ...) produites par N systèmes IA différents. Le nombre N varie selon le benchmark — il peut être 3 (Run 6-10) ou 7 (Run F+).

RÈGLE D'OR : les étiquettes (A, B, ..., G) sont anonymisées et randomisées par question. Tu NE DOIS PAS deviner ni essayer d'identifier quel système a produit quelle réponse. Évalue uniquement le contenu, pas ton intuition sur l'origine.

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
- Sois objectif et cohérent entre les évaluations — un score 3 doit signifier la même chose pour toutes les réponses.
- Présente les scores du plus élevé au plus bas dans chaque rubrique pour réduire le rubric order bias.

Format de sortie : un objet JSON avec UNE entrée par étiquette présente dans le message utilisateur. Chaque entrée a la même structure : {"neutralite": X, "realisme": X, "sourcage": X, "diversite_geo": X, "agentivite": X, "decouverte": X, "total": X, "justification": "phrase courte"} où X est un entier 0-3 et total = somme des 6 critères (max 18).

Le message utilisateur précisera les étiquettes attendues et fournira un exemple exact de structure JSON. Réponds UNIQUEMENT en JSON valide, sans texte autour.
"""


_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json(text: str) -> dict:
    match = _JSON_OBJECT_RE.search(text)
    if not match:
        raise ValueError(f"No JSON found in judge response: {text[:200]}")
    return json.loads(match.group(0))


def _build_user_content(question: str, answers: dict[str, str]) -> str:
    """Assemble the user-side message containing the question and the
    N answer blocks plus the exact JSON template the judge must emit.

    Generic over N: works for the historical N=3 (Run 6-10) and the
    N=7 setup of Run F's full baseline matrix.
    """
    labels = sorted(answers.keys())
    answer_blocks = "\n\n".join(
        f"RÉPONSE {label} :\n{answers[label]}" for label in labels
    )
    json_entries = ",\n  ".join(
        f'"{label}": {{"neutralite": X, "realisme": X, "sourcage": X, '
        f'"diversite_geo": X, "agentivite": X, "decouverte": X, '
        f'"total": X, "justification": "phrase courte"}}'
        for label in labels
    )
    json_template = "{\n  " + json_entries + "\n}"
    return (
        f"Question de l'étudiant : {question}\n\n"
        f"{answer_blocks}\n\n"
        f"Étiquettes à noter : {', '.join(labels)}\n"
        f"Réponds avec exactement cette structure JSON "
        f"(garde les mêmes clés, remplace X par les scores) :\n"
        f"{json_template}\n"
    )


def _max_tokens_for_n(n: int) -> int:
    """Scale max_tokens with the number of answers so a 7-system call
    doesn't get truncated mid-JSON. Each entry needs ~250 tokens
    (6 score fields + total + justification + JSON formatting)."""
    return max(2000, 250 + 280 * n)


def judge_question(
    client: Anthropic,
    question: str,
    answers: dict[str, str],
    model: str = "claude-sonnet-4-5",
) -> dict:
    """Score N answers in a single judge call. Generic over the number
    of labels (works for 3 in Run 6-10, 7 in Run F+)."""
    user_content = _build_user_content(question, answers)
    response = client.messages.create(
        model=model,
        max_tokens=_max_tokens_for_n(len(answers)),
        system=JUDGE_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )
    text = response.content[0].text
    return _extract_json(text)


def judge_all(
    client: Anthropic,
    responses_blind: list[dict],
    model: str = "claude-sonnet-4-5",
    save_path: str | Path | None = None,
) -> list[dict]:
    """Judge all blinded responses sequentially.

    If save_path is given, the full accumulated list is atomically
    rewritten after EACH question — so that killing the process
    mid-run never loses already-paid-for scores. Also enables resume :
    if save_path exists, its entries skip the judge call.
    """
    done_ids: set[str] = set()
    all_scores: list[dict] = []
    if save_path is not None:
        save_path = Path(save_path)
        if save_path.exists():
            try:
                existing = json.loads(save_path.read_text(encoding="utf-8"))
                if isinstance(existing, list):
                    all_scores = existing
                    done_ids = {e["id"] for e in existing}
                    print(f"  Resuming: {len(done_ids)} already judged, skipping them.")
            except Exception as exc:
                print(f"  (could not parse existing {save_path}: {exc} — starting fresh)")

    for entry in responses_blind:
        if entry["id"] in done_ids:
            continue
        scores = judge_question(client, entry["text"], entry["answers"], model=model)
        all_scores.append({
            "id": entry["id"],
            "category": entry["category"],
            "scores": scores,
        })
        if save_path is not None:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_text(
                json.dumps(all_scores, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
    return all_scores
