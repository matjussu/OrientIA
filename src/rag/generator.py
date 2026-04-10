from mistralai.client import Mistral
from src.prompt.system import SYSTEM_PROMPT, build_user_prompt


def format_context(results: list[dict]) -> str:
    blocks = []
    for i, r in enumerate(results, 1):
        f = r["fiche"]
        lines = [f"FICHE {i}:"]
        lines.append(f"  Nom: {f.get('nom','')}")
        lines.append(f"  Établissement: {f.get('etablissement','')}")
        lines.append(f"  Ville: {f.get('ville','')}")
        lines.append(f"  Statut: {f.get('statut','Inconnu')}")
        if f.get("niveau"):
            lines.append(f"  Niveau: {f['niveau']}")
        labels = f.get("labels") or []
        lines.append(f"  Labels: {', '.join(labels) if labels else 'aucun'}")
        if f.get("taux_acces_parcoursup_2025") is not None:
            lines.append(f"  Taux d'accès Parcoursup 2025: {f['taux_acces_parcoursup_2025']}%")
        if f.get("nombre_places") is not None:
            lines.append(f"  Places: {f['nombre_places']}")
        if f.get("url_onisep"):
            lines.append(f"  Source ONISEP: {f['url_onisep']}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def generate(
    client: Mistral,
    retrieved: list[dict],
    question: str,
    model: str = "mistral-medium-latest",
    temperature: float = 0.3,
) -> str:
    context = format_context(retrieved)
    user_prompt = build_user_prompt(context, question)
    response = client.chat.complete(
        model=model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content
