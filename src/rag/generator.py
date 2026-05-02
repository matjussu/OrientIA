import re

from mistralai.client import Mistral
from src.prompt.system import SYSTEM_PROMPT, build_user_prompt
from src.rag.intent import classify_intent, intent_to_format_guidance
from src.rag.user_level import classify_user_level, level_to_guidance


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
    # Sprint 12 axe 2 (2026-05-02) — cast str() avant .strip() pour gérer
    # les corpus hétérogènes (combined formations_unified + dares + rncp_blocs)
    # où certains items ont des champs numériques (niveau RNCP int, etc.).
    # Les fiches formations_unified canon ont des str ; le cast est no-op.
    nom = str(f.get("nom") or "").strip()
    etab = str(f.get("etablissement") or "").strip()
    ville = str(f.get("ville") or "").strip()
    dept = str(f.get("departement") or "").strip()
    niveau = str(f.get("niveau") or "").strip()
    statut = str(f.get("statut") or "Inconnu").strip()

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


_TREND_TAUX_MIN_PP = 5      # Task B : ±5pp minimum pour trend actionable
_TREND_VOEUX_MIN_PCT = 15   # Task B : ±15% minimum de vœux
_TREND_PLACES_MIN = 10      # Task B : ±10 places minimum


def _trend_suffix(trends: dict) -> str | None:
    """Compact trend string for the selectivity line. Emits only
    SIGNIFICANT directions (task B, 2026-04-19) — seuils minimaux
    pour éviter les trends décoratives que les 5 testeurs v2 ont
    jugées bruit ou anxiogènes.

    Seuils : taux ≥5pp, vœux ≥15%, places ≥10. En-deçà → omis.

    Exemple output :
      'Tendance 2023→2025 : taux ↓23pp (plus sélective), vœux ↑38% (attrait +)'
    """
    if not trends:
        return None
    bits: list[str] = []
    # Taux d'accès direction — significance threshold 5pp
    taux = trends.get("taux_acces") or {}
    if taux.get("direction") in ("up", "down"):
        delta = abs(taux.get("delta_pp") or 0)
        if delta >= _TREND_TAUX_MIN_PP:
            arrow = "↓" if taux["direction"] == "down" else "↑"
            label = "plus sélective" if taux["direction"] == "down" else "plus accessible"
            bits.append(f"taux {arrow}{delta:g}pp ({label})")
    # Places direction — significance threshold 10 places
    places = trends.get("places") or {}
    if places.get("direction") in ("up", "down"):
        delta = abs(places.get("delta") or 0)
        if delta >= _TREND_PLACES_MIN:
            arrow = "↑" if places["direction"] == "up" else "↓"
            bits.append(f"places {arrow}{delta}")
    # Vœux direction (popularité) — significance threshold 15%
    voeux = trends.get("voeux") or {}
    if voeux.get("direction") in ("up", "down"):
        start = voeux.get("start_value") or 1
        delta = voeux.get("delta") or 0
        pct = round(delta / start * 100)
        if abs(pct) >= _TREND_VOEUX_MIN_PCT:
            arrow = "↑" if voeux["direction"] == "up" else "↓"
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
    """Tier 0 extended (2026-04-19 task B) : masque les codes ROME
    du texte exposé au LLM. Le libellé suffit pour la génération ;
    le code ROME reste disponible dans le dict fiche pour le retrieval
    interne mais n'apparaît plus en clair dans le contexte LLM
    (même rationale que cod_aff_form / RNCP / FOR.xxx du Tier 0)."""
    debouches = f.get("debouches") or []
    if not debouches:
        return None
    top = debouches[:3]
    parts = [
        d.get("libelle", "").strip()
        for d in top
        if d.get("libelle")
    ]
    parts = [p for p in parts if p]
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
    # V2 data cleanup (ADR-036) : préfixer "mention" explicitement pour
    # éviter que Mistral Medium confonde "B 42%" avec "série bac B 42%"
    # (cf bug détecté dans Q8 Gate J+6, ground truth humain 2026-04-22).
    m_bits = []
    if mentions.get("tb") is not None:
        m_bits.append(f"mention TB {mentions['tb']:.0f}%")
    if mentions.get("b") is not None:
        m_bits.append(f"mention B {mentions['b']:.0f}%")
    if mentions.get("ab") is not None:
        m_bits.append(f"mention AB {mentions['ab']:.0f}%")
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
    """Vague D — insertion pro InserSup DEPP (taux emploi, salaire médian)
    with explicit disclaimer on the aggregation level. This line is optional
    and only emitted when a matched insertion snapshot is attached.

    Format kept compact to fit budget (replaces the previously-free line 7
    which was the source line — we fold source + insertion into the line).
    """
    ins = f.get("insertion")
    if not ins:
        return None
    bits = []
    taux = ins.get("taux_emploi_12m")
    if taux is not None:
        # InserSup stores taux as decimal fraction (0.88) or percent (88) —
        # detect heuristically: if value > 1.5, it's already percent.
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
    gran_short = "discipline" if gran == "discipline" else "agrégat établissement"
    return (f"  Insertion (InserSup DEPP, cohorte {cohorte}, {gran_short}): "
            + " | ".join(bits))


def _source_line(f: dict) -> str | None:
    """Tier 0 fix (2026-04-18 user feedback) : produce an LLM-facing line
    that nudges toward clickable markdown links and away from raw admin
    codes in the output.

    The system prompt tells the LLM explicitly NOT to cite cod_aff_form /
    RNCP / FOR.xxx in cleartext — instead use the URLs from this line as
    markdown links `[fiche officielle Parcoursup](URL)`. The codes remain
    available in the context for the LLM's internal reasoning (knowing
    which fiche is which), but the user-visible output stays clean.
    """
    psup = (f.get("lien_form_psup") or "").strip()
    onisep = (f.get("url_onisep") or "").strip()

    parts: list[str] = []
    if psup:
        parts.append(f"Parcoursup officiel = {psup}")
    if onisep and onisep != psup:
        parts.append(f"ONISEP officiel = {onisep}")

    if not parts:
        return None
    return (f"  Sources à citer en liens markdown cliquables "
            f"(pas d'ID brut dans la réponse) : {' | '.join(parts)}")


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
    inject_user_level: bool = True,
    system_prompt_override: str | None = None,
    golden_qa_prefix: str | None = None,
    history: list[dict] | None = None,
) -> str:
    """Generate an answer via Mistral.

    `inject_user_level` (Tier 2.2, 2026-04-18) adds a "Profil détecté"
    guidance prefix derived from rule-based classification of the
    question. Disable only for A/B comparisons of the feature itself
    in benchmark harnesses — production should keep it on.

    `system_prompt_override` (Sprint 7, 2026-04-27) optional override
    of the system prompt. Default `None` = utilise `SYSTEM_PROMPT` v3.2
    (non-régression Sprint 5/6 stricte). Pour activer v3.3 strict
    (Sprint 7 Action 3), passer `SYSTEM_PROMPT_V33_STRICT` depuis
    `src.prompt.system_strict`.

    `golden_qa_prefix` (Sprint 10 chantier D, 2026-04-29) optional
    Q&A Golden Dynamic Few-Shot prefix avec **séparation stricte
    Comment/Quoi** (cf `OrientIAPipeline._build_few_shot_prefix`).
    Quand fourni, append au system prompt — la Q&A devient référence
    comportementale, les fiches du retrieved restent seules sources
    factuelles autorisées. Default `None` = backward compat strict.

    `history` (Sprint 11 P0 Item 2, 2026-04-29) optional buffer de la
    conversation précédente pour permettre le suivi de tiroir
    ("Oui Plan A" → développe ce qui a été dit). Format Mistral compliant :
    `[{"role": "user"|"assistant", "content": str}, ...]`. Injecté
    entre system prompt et user current. Default `None`/empty = no-op
    (backward compat strict pour Run F+G + serving stateless).
    """
    context = format_context(retrieved)
    guidance_parts: list[str] = []
    if inject_user_level:
        level = classify_user_level(question)
        guidance_parts.append(level_to_guidance(level).tone_instruction)
        intent = classify_intent(question)
        guidance_parts.append(intent_to_format_guidance(intent))
    user_guidance = "\n\n".join(guidance_parts)
    user_prompt = build_user_prompt(context, question, user_guidance=user_guidance)
    sys_prompt = system_prompt_override if system_prompt_override is not None else SYSTEM_PROMPT
    if golden_qa_prefix:
        # Append au system prompt avec séparateur clair. Mistral honore
        # plus strictement les system instructions que les user-side
        # injections — le few-shot avec instruction "IGNORE écoles/chiffres
        # exemple" doit être system pour maximiser le respect.
        sys_prompt = sys_prompt + "\n\n" + golden_qa_prefix

    # Sprint 11 P0 Item 2 — buffer mémoire short-term
    # Construction messages array : system → history (user/assistant alternés) → user current
    messages: list[dict] = [{"role": "system", "content": sys_prompt}]
    if history:
        for msg in history:
            role = msg.get("role")
            content = msg.get("content")
            if role in ("user", "assistant") and isinstance(content, str) and content:
                messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_prompt})

    response = client.chat.complete(
        model=model,
        temperature=temperature,
        messages=messages,
    )
    content = response.choices[0].message.content
    # Sprint 11 P1.1 v5 — strip brouillon XML balises si détectées.
    # Format attendu : <brouillon>...</brouillon>\n<reponse_finale>...</reponse_finale>
    # Tolérant : si Mistral n'utilise pas les balises (Q simple, fallback,
    # consigne ignorée), retourne le content brut.
    m = _RE_REPONSE_FINALE.search(content)
    if m:
        return m.group(1).strip()
    return content


_RE_REPONSE_FINALE = re.compile(
    r"<reponse_finale>\s*(.*?)\s*</reponse_finale>",
    re.DOTALL | re.IGNORECASE,
)
