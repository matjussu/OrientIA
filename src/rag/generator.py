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
    # Prefer structured admission block (Vague A), fallback to legacy flat fields
    adm = f.get("admission") or {}
    taux = adm.get("taux_acces") if adm else f.get("taux_acces_parcoursup_2025")
    places = adm.get("places") if adm else f.get("nombre_places")
    volumes = adm.get("volumes") or {}
    voeux_totaux = volumes.get("voeux_totaux")
    internat = adm.get("internat_disponible")

    if taux is None and places is None and voeux_totaux is None:
        return None
    qual = selectivite_qualitative(taux)
    if taux is not None:
        body = f"Parcoursup 2025: {taux:g}% ({qual})"
    else:
        body = f"Parcoursup 2025: non renseignée"
    if places is not None:
        body = f"{body} | Places: {places}"
    if voeux_totaux is not None:
        body = f"{body} | Vœux formulés: {voeux_totaux}"
    if internat is True:
        body = f"{body} | Internat: oui"
    elif internat is False:
        body = f"{body} | Internat: non"
    # Vague C — trend summary: significant direction changes 2023→2025 folded
    # into the selectivity line to preserve the ≤8-lines-per-fiche budget.
    trend_suffix = _trend_suffix(f.get("trends") or {})
    if trend_suffix:
        body = f"{body} | {trend_suffix}"
    return f"  Sélectivité {body}"


def _trend_suffix(trends: dict) -> str | None:
    """Compact trend string for the selectivity line. Emits only meaningful
    directions (stable/None skipped). Example output:
      'Tendance 2023→2025 : taux ↓23pp (plus sélective), vœux ↑38% (attrait +)'
    """
    if not trends:
        return None
    bits: list[str] = []
    # Taux d'accès direction
    taux = trends.get("taux_acces") or {}
    if taux.get("direction") in ("up", "down"):
        arrow = "↓" if taux["direction"] == "down" else "↑"
        delta = abs(taux.get("delta_pp") or 0)
        label = "plus sélective" if taux["direction"] == "down" else "plus accessible"
        bits.append(f"taux {arrow}{delta:g}pp ({label})")
    # Places direction — only if significant
    places = trends.get("places") or {}
    if places.get("direction") in ("up", "down"):
        arrow = "↑" if places["direction"] == "up" else "↓"
        delta = abs(places.get("delta") or 0)
        bits.append(f"places {arrow}{delta}")
    # Vœux direction (popularité)
    voeux = trends.get("voeux") or {}
    if voeux.get("direction") in ("up", "down"):
        arrow = "↑" if voeux["direction"] == "up" else "↓"
        start = voeux.get("start_value") or 1
        delta = voeux.get("delta") or 0
        pct = round(delta / start * 100)
        label = "attrait +" if voeux["direction"] == "up" else "attrait -"
        bits.append(f"vœux {arrow}{pct:+d}% ({label})")
    if not bits:
        return None
    # Infer year range from whichever trend is present
    years_seen = set()
    for t in (taux, places, voeux):
        if t.get("start_year"):
            years_seen.add(t["start_year"])
            years_seen.add(t["end_year"])
    if years_seen:
        yr = f"{min(years_seen)}→{max(years_seen)}"
    else:
        yr = "historique"
    return f"Tendance {yr} : " + ", ".join(bits)


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
    femmes = profil.get("femmes_pct")
    neobac = profil.get("neobacheliers_pct")

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

    # Full bac-type split (Vague A: previously only "general" was exposed)
    bac_bits = []
    for key, label in (("general", "général"), ("techno", "techno"), ("pro", "pro")):
        val = bac_types.get(key)
        if val is not None:
            bac_bits.append(f"{label} {val:.0f}%")
    if bac_bits:
        bits.append(f"Bac {', '.join(bac_bits)}")

    if boursiers is not None:
        bits.append(f"Boursiers {boursiers:.0f}%")
    if femmes is not None:
        bits.append(f"Femmes {femmes:.0f}%")
    if neobac is not None:
        bits.append(f"Néobacheliers {neobac:.0f}%")

    if not bits:
        return None
    return f"  Profil admis: {' | '.join(bits)}"


def _detail_line(f: dict) -> str | None:
    detail = (f.get("detail") or "").strip()
    if not detail:
        return None
    return f"  Détail: {detail[:500]}"


def _insertion_line(f: dict) -> str | None:
    """Insertion pro InserSup DEPP with EXPLICIT warnings on aggregation +
    sample size. Visibility-first: "⚠ AGRÉGAT ÉTABLISSEMENT" or
    "N=NN DIPLÔMÉS" in capitals so the LLM (and indirectly the reader) sees
    them more than the mere disclaimer text.
    """
    ins = f.get("insertion")
    if not ins:
        return None
    bits = []
    taux = ins.get("taux_emploi_12m")
    if taux is not None:
        pct = taux if taux > 1.5 else taux * 100
        bits.append(f"emploi 12m: {pct:.0f}%")
    taux18 = ins.get("taux_emploi_18m")
    if taux is None and taux18 is not None:
        pct = taux18 if taux18 > 1.5 else taux18 * 100
        bits.append(f"emploi 18m: {pct:.0f}%")
    sal = ins.get("salaire_median_12m_mensuel_net")
    if sal is not None:
        bits.append(f"salaire médian 12m: {sal}€/mois net")
    sal30 = ins.get("salaire_median_30m_mensuel_net")
    if sal is None and sal30 is not None:
        bits.append(f"salaire médian 30m: {sal30}€/mois net")
    stable = ins.get("taux_emploi_stable_12m")
    if stable is not None:
        pct = stable if stable > 1.5 else stable * 100
        bits.append(f"emploi stable: {pct:.0f}%")
    if not bits:
        return None

    cohorte = ins.get("cohorte", "?")
    gran = ins.get("granularite", "?")
    sample_tier = ins.get("sample_size_tier", "unknown")
    n_sortants = ins.get("nombre_sortants")

    # Visibility markers — format "[SCOPE, SAMPLE]" prepended for LLM clarity
    scope_tag = "discipline" if gran == "discipline" else "⚠AGRÉGAT-ÉTAB"
    sample_tag = ""
    if sample_tier == "small" and n_sortants is not None:
        sample_tag = f", ⚠N={n_sortants}-marge-large"
    elif sample_tier == "medium" and n_sortants is not None:
        sample_tag = f", N={n_sortants}"
    # Large samples (≥100) are not tagged — trust the number

    return (f"  Insertion [InserSup DEPP {cohorte}, {scope_tag}{sample_tag}]: "
            + " | ".join(bits))


def _source_line(f: dict) -> str | None:
    """Unified source line: official URLs + stable identifiers (RNCP / cod_aff_form).

    Kept to a single line to preserve the ≤8-lines-per-fiche budget. The LLM uses
    these ids to cite in ##begin_quote## format (see src/prompt/system.py).
    Priority: Parcoursup URL > ONISEP URL (both shown when distinct).
    """
    psup = (f.get("lien_form_psup") or "").strip()
    onisep = (f.get("url_onisep") or "").strip()
    rncp = f.get("rncp")
    cod_aff = f.get("cod_aff_form")

    url_bits: list[str] = []
    if psup:
        url_bits.append(f"Parcoursup: {psup}")
    if onisep and onisep != psup:
        url_bits.append(f"ONISEP: {onisep}")

    id_bits: list[str] = []
    if isinstance(rncp, str) and rncp.strip():
        id_bits.append(f"RNCP {rncp.strip()}")
    if isinstance(cod_aff, str) and cod_aff.strip():
        id_bits.append(f"cod_aff_form {cod_aff.strip()}")

    if not url_bits and not id_bits:
        return None
    all_bits = url_bits + id_bits
    return f"  Source officielle: {' | '.join(all_bits)}"


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
            _insertion_line(f),
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
