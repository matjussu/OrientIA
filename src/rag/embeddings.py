from mistralai.client import Mistral


EMBED_MODEL = "mistral-embed"


def fiche_to_text(fiche: dict) -> str:
    parts = [
        f"Formation : {fiche.get('nom', '')}",
        f"Établissement : {fiche.get('etablissement', '')}",
        f"Ville : {fiche.get('ville', '')}",
    ]
    if fiche.get("type_diplome"):
        parts.append(f"Diplôme : {fiche['type_diplome']}")
    if fiche.get("niveau"):
        parts.append(f"Niveau : {fiche['niveau']}")
    if fiche.get("statut"):
        parts.append(f"Statut : {fiche['statut']}")
    labels = fiche.get("labels") or []
    if labels:
        parts.append(f"Labels : {', '.join(labels)}")
    if fiche.get("taux_acces_parcoursup_2025") is not None:
        parts.append(f"Taux d'accès Parcoursup 2025 : {fiche['taux_acces_parcoursup_2025']}%")
    if fiche.get("nombre_places") is not None:
        parts.append(f"Places : {fiche['nombre_places']}")
    if fiche.get("domaine"):
        parts.append(f"Domaine : {fiche['domaine']}")
    if fiche.get("departement"):
        parts.append(f"Département : {fiche['departement']}")
    # Include the formation detail (description) — a rich text signal
    # for retrieval specificity (distinguishes similar BTS by parcours).
    detail = (fiche.get("detail") or "").strip()
    if detail:
        parts.append(f"Détail : {detail[:200]}")
    # NOTE: debouches (ROME) and profil_admis are intentionally NOT included
    # here. The ROME debouches are shared across all fiches of the same
    # domain (embedding pollution). The profil_admis mentions/bac-types are
    # structured numeric data better served in the generator context where
    # the LLM can reason about them, not in the retrieval embedding.
    return " | ".join(parts)


def embed_texts(client: Mistral, texts: list[str]) -> list[list[float]]:
    response = client.embeddings.create(model=EMBED_MODEL, inputs=texts)
    return [d.embedding for d in response.data]


def embed_texts_batched(client: Mistral, texts: list[str], batch_size: int = 64) -> list[list[float]]:
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        all_embeddings.extend(embed_texts(client, batch))
    return all_embeddings
