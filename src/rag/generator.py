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
        if f.get("departement"):
            lines.append(f"  Département: {f['departement']}")
        if f.get("detail"):
            lines.append(f"  Détail: {f['detail'][:250]}")
        # Profil des admis (from Parcoursup) — realism signal
        profil = f.get("profil_admis") or {}
        mentions = profil.get("mentions_pct") or {}
        if any(v for v in mentions.values() if v is not None):
            mparts = []
            if mentions.get("tb") is not None:
                mparts.append(f"TB {mentions['tb']:.0f}%")
            if mentions.get("b") is not None:
                mparts.append(f"B {mentions['b']:.0f}%")
            if mentions.get("ab") is not None:
                mparts.append(f"AB {mentions['ab']:.0f}%")
            if mparts:
                lines.append(f"  Mentions admis: {', '.join(mparts)}")
        bac_types = profil.get("bac_type_pct") or {}
        if any(v for v in bac_types.values() if v is not None):
            bparts = []
            if bac_types.get("general") is not None:
                bparts.append(f"général {bac_types['general']:.0f}%")
            if bac_types.get("techno") is not None:
                bparts.append(f"techno {bac_types['techno']:.0f}%")
            if bac_types.get("pro") is not None:
                bparts.append(f"pro {bac_types['pro']:.0f}%")
            if bparts:
                lines.append(f"  Répartition bac admis: {', '.join(bparts)}")
        if profil.get("boursiers_pct") is not None:
            lines.append(f"  Boursiers admis: {profil['boursiers_pct']:.0f}%")
        if f.get("url_onisep"):
            lines.append(f"  Source ONISEP: {f['url_onisep']}")
        debouches = f.get("debouches") or []
        if debouches:
            metiers = ", ".join(f"{d['libelle']} ({d['code_rome']})" for d in debouches[:5])
            lines.append(f"  Débouchés métiers ROME 4.0: {metiers}")
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
