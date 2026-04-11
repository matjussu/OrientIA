from mistralai.client import Mistral
from src.prompt.system import SYSTEM_PROMPT, build_user_prompt


def selectivite_qualitative(taux: float | None) -> str:
    """Translate a Parcoursup access rate to a qualitative label.

    Thresholds picked to match Parcoursup's own "sélective" terminology.
    """
    if taux is None:
        return "non renseignée"
    if taux < 20.0:
        return "Très sélective"
    if taux < 50.0:
        return "Sélective"
    return "Accessible"


def _fiche_header(i: int, f: dict) -> str:
    nom = (f.get("nom") or "").strip()
    etab = (f.get("etablissement") or "").strip()
    ville = (f.get("ville") or "").strip()
    dept = (f.get("departement") or "").strip()
    niveau = (f.get("niveau") or "").strip()
    statut = (f.get("statut") or "Inconnu").strip()

    loc = ville
    if dept:
        loc = f"{ville} ({dept})" if ville else dept
    head_bits = [f"{nom}"]
    if etab:
        head_bits.append(f"— {etab}")
    if loc:
        head_bits.append(f", {loc}")
    head = " ".join(head_bits)
    meta_bits = [b for b in (niveau, statut) if b]
    if meta_bits:
        head = f"{head} | {' | '.join(meta_bits)}"
    return f"FICHE {i}: {head}"


def _labels_line(f: dict) -> str | None:
    labels = [l for l in (f.get("labels") or []) if l]
    if not labels:
        return None
    return f"  Labels officiels: {', '.join(labels)}"


def _selectivite_line(f: dict) -> str | None:
    taux = f.get("taux_acces_parcoursup_2025")
    places = f.get("nombre_places")
    if taux is None and places is None:
        return None
    qual = selectivite_qualitative(taux)
    if taux is not None:
        body = f"Parcoursup 2025: {taux:g}% ({qual})"
    else:
        body = f"Parcoursup 2025: non renseignée"
    if places is not None:
        body = f"{body} | Places: {places}"
    return f"  Sélectivité {body}"


def _debouches_line(f: dict) -> str | None:
    debouches = f.get("debouches") or []
    if not debouches:
        return None
    top = debouches[:3]
    parts = [
        f"{d.get('libelle', '')} ({d.get('code_rome', '')})"
        for d in top
        if d.get("libelle")
    ]
    if not parts:
        return None
    return f"  Débouchés métiers: {', '.join(parts)}"


def _profil_line(f: dict) -> str | None:
    profil = f.get("profil_admis") or {}
    mentions = profil.get("mentions_pct") or {}
    bac_types = profil.get("bac_type_pct") or {}
    boursiers = profil.get("boursiers_pct")

    bits = []
    m_bits = []
    if mentions.get("tb") is not None:
        m_bits.append(f"TB {mentions['tb']:.0f}%")
    if mentions.get("b") is not None:
        m_bits.append(f"B {mentions['b']:.0f}%")
    if mentions.get("ab") is not None:
        m_bits.append(f"AB {mentions['ab']:.0f}%")
    if m_bits:
        bits.append(", ".join(m_bits))
    if bac_types.get("general") is not None:
        bits.append(f"Bac général {bac_types['general']:.0f}%")
    if boursiers is not None:
        bits.append(f"Boursiers {boursiers:.0f}%")
    if not bits:
        return None
    return f"  Profil admis: {' | '.join(bits)}"


def _detail_line(f: dict) -> str | None:
    detail = (f.get("detail") or "").strip()
    if not detail:
        return None
    return f"  Détail: {detail[:500]}"


def _source_line(f: dict) -> str | None:
    url = (f.get("url_onisep") or "").strip()
    if not url:
        return None
    return f"  Source: {url}"


def format_context(results: list[dict]) -> str:
    """Format retrieved fiches as a dense signal-first context block.

    Layout (≤ 8 lines per fiche, lines missing data are omitted):
        FICHE i: Nom — Etab, Ville (Dept) | Niveau | Statut
          Labels officiels: ...
          Sélectivité Parcoursup 2025: X% (qualif) | Places: N
          Débouchés métiers: m1 (ROME), m2, m3
          Profil admis: TB %, Bac général %, Boursiers %
          Détail: [500 chars]
          Source: url
    """
    blocks = []
    for i, r in enumerate(results, 1):
        f = r["fiche"]
        lines: list[str] = [_fiche_header(i, f)]
        for line in (
            _labels_line(f),
            _selectivite_line(f),
            _debouches_line(f),
            _profil_line(f),
            _detail_line(f),
            _source_line(f),
        ):
            if line is not None:
                lines.append(line)
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
