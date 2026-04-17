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
    # Vague B.3 — detail window expanded 200 → 800 chars.
    # The diagnostic of Vague B.1 showed Parcoursup-rich fiches losing to
    # ONISEP-only fiches at retrieval because ONISEP names are narrative
    # while Parcoursup fiches had little semantic body beyond the name.
    # The extended detail carries specialisation, parcours, stages info —
    # all semantic signals that improve ranking on "formations cyber",
    # "data science", "réseaux" type queries without polluting with numbers.
    detail = (fiche.get("detail") or "").strip()
    if detail:
        parts.append(f"Détail : {detail[:800]}")
    # Vague B.3 — ROME job titles injected (libellés only, not codes).
    # The rationale from the old NOTE ("ROME pollutes since shared across
    # domain") is only partially true: within a domain, specific ROME
    # appellations (RSSI vs Data Scientist vs Architecte sécurité) DO
    # carry discriminating semantic signal that helps match queries
    # like "je veux être RSSI" or "devenir data scientist" to the right
    # formations. We inject libellés only (no codes, no percentages) to
    # keep the embedding narrative-dense without polluting it with
    # structured data that belongs in the generator context.
    debouches = fiche.get("debouches") or []
    if debouches:
        libelles = [d.get("libelle", "").strip()
                    for d in debouches if d.get("libelle")]
        if libelles:
            parts.append(f"Métiers possibles : {', '.join(libelles)}")
    # NOTE: profil_admis (mentions %, bac-types %, femmes %, etc.) is
    # intentionally NOT included here — structured numeric data belongs
    # in the generator context where the LLM can reason on numbers, not
    # in retrieval embeddings where numbers pollute similarity.
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
