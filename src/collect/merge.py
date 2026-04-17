from datetime import date
from rapidfuzz import fuzz
from src.collect.normalize import normalize_name, normalize_city
from src.collect.niveau import infer_niveau
from src.collect.rome import get_debouches_for_domain


def merge_by_rncp(parcoursup: list[dict], onisep: list[dict]) -> list[dict]:
    onisep_by_rncp = {f["rncp"]: f for f in onisep if f.get("rncp")}
    merged = []
    for ps in parcoursup:
        rncp = ps.get("rncp")
        if rncp and rncp in onisep_by_rncp:
            merged_fiche = {**onisep_by_rncp[rncp], **ps}
            merged_fiche["match_method"] = "rncp"
            merged.append(merged_fiche)
    return merged


def _signature(fiche: dict) -> str:
    return f"{normalize_name(fiche.get('nom',''))} {normalize_name(fiche.get('etablissement',''))} {normalize_city(fiche.get('ville',''))}"


def fuzzy_match_fiches(
    parcoursup: list[dict],
    onisep: list[dict],
    threshold: int = 85,
    min_tokens: int = 4,
    require_onisep_etab: bool = True,
) -> list[dict]:
    """Fuzzy match parcoursup fiches to onisep fiches with precision guards.

    Two anti-spurious-match filters were added after run 4 revealed 280+
    fuzzy_100.0 matches where the signatures were too short or generic:

    1. `min_tokens` : require the PARCOURSUP signature to have at least N
       tokens. Short signatures like "master ia" match many things at 100%
       and pollute the merge with noise.
    2. `require_onisep_etab` : only consider onisep candidates that have a
       populated etablissement field. Matching a parcoursup fiche against
       an onisep fiche with empty etab gives a spurious 100% match on the
       formation name alone, losing the geographic discrimination.
    """
    # Pre-filter onisep candidates by etab populated (if required)
    if require_onisep_etab:
        candidates = [(f, _signature(f)) for f in onisep if (f.get("etablissement") or "").strip()]
    else:
        candidates = [(f, _signature(f)) for f in onisep]

    merged = []
    for ps in parcoursup:
        ps_sig = _signature(ps)
        # Skip too-short signatures (high false-positive risk)
        if len(ps_sig.split()) < min_tokens:
            continue
        best_score = 0
        best_onisep = None
        for onisep_fiche, on_sig in candidates:
            score = fuzz.token_set_ratio(ps_sig, on_sig)
            if score > best_score:
                best_score = score
                best_onisep = onisep_fiche
        if best_onisep and best_score >= threshold:
            merged_fiche = {**best_onisep, **ps}
            merged_fiche["match_method"] = f"fuzzy_{best_score}"
            merged.append(merged_fiche)
    return merged


def attach_labels(
    fiches: list[dict],
    secnumedu: list[dict],
    manual_table: list[dict] | None = None,
) -> list[dict]:
    """Attach SecNumEdu (and other) labels from the reference list to merged fiches.

    Uses a three-stage matcher:
    1. Full-signature fuzzy match (name + etab + ville) at threshold 85 —
       catches cases where formation names align between sources.
    2. Establishment-only fuzzy match at threshold 85 — fallback for cases
       where formation names differ but establishment names overlap
       (e.g., Parcoursup "EFREI Bordeaux" vs SecNumEdu "EFREI").
    3. Manual table lookup — looks up each fiche's normalized establishment
       against a cross-reference table using substring containment.
       An entry with empty labels is "explicitly unlabeled" — useful for
       benchmark contrast (private schools without SecNumEdu/CTI labels).

    The Stage 2 fallback only fires on fiches in domains where the label list
    is relevant (currently: "cyber" for SecNumEdu). This prevents spurious
    attachments on unrelated domains.
    """
    sec_sigs = [(s, _signature(s)) for s in secnumedu]
    sec_etabs = [(s, normalize_name(s.get("etablissement", ""))) for s in secnumedu]

    for f in fiches:
        f_sig = _signature(f)
        existing_labels = list(f.get("labels", []))
        matched = False

        # Stage 1: full signature match
        for sec, sec_sig in sec_sigs:
            if fuzz.token_set_ratio(f_sig, sec_sig) >= 85:
                for label in sec.get("labels", []):
                    if label not in existing_labels:
                        existing_labels.append(label)
                matched = True
                break

        # Stage 2: establishment-only fallback (cyber domain only for SecNumEdu)
        if not matched and f.get("domaine") == "cyber":
            f_etab = normalize_name(f.get("etablissement", ""))
            if f_etab:
                for sec, sec_etab in sec_etabs:
                    if sec_etab and fuzz.token_set_ratio(f_etab, sec_etab) >= 85:
                        for label in sec.get("labels", []):
                            if label not in existing_labels:
                                existing_labels.append(label)
                        break

        # Stage 3: manual table (AUTHORITATIVE — overrides earlier stages).
        # When a fiche's establishment matches a manual entry, the manual
        # labels REPLACE any labels attached by Stages 1/2. This makes the
        # manual table a correction layer: entries with empty labels act as
        # a blocklist (e.g., EPITA/Guardia/Epitech are explicitly unlabeled
        # for benchmark contrast even if fuzzy matching would have labeled them).
        if manual_table is not None:
            f_etab_norm = normalize_name(f.get("etablissement", ""))
            if f_etab_norm:
                for entry in manual_table:
                    ref = entry.get("etab_normalized", "")
                    if not ref:
                        continue
                    if ref in f_etab_norm or f_etab_norm in ref:
                        existing_labels = list(entry.get("labels", []))
                        break

        f["labels"] = existing_labels
    return fiches


def merge_all(
    parcoursup: list[dict],
    onisep: list[dict],
    secnumedu: list[dict],
    manual_labels: list[dict] | None = None,
    fuzzy_threshold: int = 85,
) -> list[dict]:
    # Step 1: RNCP matching
    rncp_matched = merge_by_rncp(parcoursup, onisep)
    matched_rncps = {f.get("rncp") for f in rncp_matched if f.get("rncp")}

    # Step 2: Fuzzy matching on parcoursup orphans against onisep orphans
    ps_orphans = [p for p in parcoursup
                  if not p.get("rncp") or p.get("rncp") not in matched_rncps]
    onisep_orphans = [o for o in onisep
                      if not o.get("rncp") or o.get("rncp") not in matched_rncps]
    fuzzy_matched = fuzzy_match_fiches(ps_orphans, onisep_orphans, fuzzy_threshold)

    # Step 3: Parcoursup-only (kept even without ONISEP enrichment —
    # taux d'accès is the most critical field and we don't want to lose it)
    fuzzy_matched_sigs = {_signature(f) for f in fuzzy_matched}
    ps_only = []
    for p in ps_orphans:
        if _signature(p) not in fuzzy_matched_sigs:
            p_copy = dict(p)
            p_copy["match_method"] = "parcoursup_only"
            ps_only.append(p_copy)

    # Step 3b: ONISEP-only — ONISEP fiches not matched by either RNCP or fuzzy
    # are kept as standalone entries (they provide higher-ed coverage that
    # Parcoursup lacks: ingénieurs post-prépa, mastères spécialisés, etc.)
    matched_onisep_ids = set()
    for f in rncp_matched + fuzzy_matched:
        if f.get("source") == "onisep" or f.get("url_onisep"):
            # The merged fiche already has ONISEP fields; mark as matched
            # by using a signature on its onisep provenance
            matched_onisep_ids.add((f.get("rncp"), f.get("url_onisep")))
    onisep_only = []
    for o in onisep:
        # If this onisep fiche wasn't merged with a parcoursup fiche, keep it standalone
        key = (o.get("rncp"), o.get("url_onisep"))
        if key not in matched_onisep_ids:
            o_copy = dict(o)
            o_copy["match_method"] = "onisep_only"
            onisep_only.append(o_copy)

    all_merged = rncp_matched + fuzzy_matched + ps_only + onisep_only

    # Step 4: Attach SecNumEdu labels (now with optional manual table)
    all_merged = attach_labels(all_merged, secnumedu, manual_table=manual_labels)

    # Step 5: Infer statut from establishment name when missing
    for f in all_merged:
        if not f.get("statut"):
            est = normalize_name(f.get("etablissement", ""))
            if any(pub in est for pub in ["universite", "ecole normale", "institut national",
                                           "ecole nationale", "insa", "ens", "cnam",
                                           "imt", "telecom paris", "polytechnique"]):
                f["statut"] = "Public"
            else:
                f["statut"] = "Inconnu"
        f.setdefault("labels", [])
        if not f.get("niveau"):
            f["niveau"] = infer_niveau(f.get("nom", ""))

    return all_merged


# === Vague A — post-merge enrichment: debouches + provenance + fraîcheur ===


def attach_debouches(fiches: list[dict]) -> list[dict]:
    """Attach ROME 4.0 debouches to each fiche based on its `domaine`.

    Uses the canonical `get_debouches_for_domain()` mapping (src/collect/rome.py)
    which is verified against ROME 4.0 open data. Fiches without a known
    domaine keep their existing `debouches` (if any) or get an empty list.

    Before Vague A this step was done out-of-pipeline (one-off script).
    Now integrated so `run_merge.py` produces a fully-populated JSON from
    scratch, reproducibly.
    """
    for f in fiches:
        domaine = f.get("domaine")
        if not domaine:
            f.setdefault("debouches", [])
            continue
        # Don't clobber existing debouches if already populated (tests/fixtures)
        if f.get("debouches"):
            continue
        try:
            f["debouches"] = get_debouches_for_domain(domaine)
        except KeyError:
            # Unknown domain (e.g., future domain not yet in _DOMAIN_CODES) — keep empty
            f["debouches"] = []
    return fiches


def attach_metadata(
    fiches: list[dict],
    collection_date: str | None = None,
) -> list[dict]:
    """Attach Vague A provenance + collected_at metadata per fiche.

    - `provenance`: map of enriched-field → source name (for LLM citations
      and future conflict resolution when multiple sources disagree).
    - `collected_at`: map of source → ISO date (makes freshness first-class).
    - `merge_confidence`: confidence per source merge (1.0 for RNCP match,
      fuzzy score for fuzzy, null for unmatched).

    Called post-merge, post-attach_labels, post-attach_debouches.
    """
    today = collection_date or date.today().isoformat()

    for f in fiches:
        mm = f.get("match_method", "")
        # Infer which sources contributed this fiche
        sources_present = set()
        if f.get("cod_aff_form") or f.get("taux_acces_parcoursup_2025") is not None:
            sources_present.add("parcoursup")
        if f.get("url_onisep") or mm in ("rncp", "onisep_only") or mm.startswith("fuzzy"):
            sources_present.add("onisep")
        if f.get("debouches"):
            sources_present.add("rome")

        # Provenance per enriched field
        provenance = {}
        if f.get("admission") or f.get("taux_acces_parcoursup_2025") is not None:
            provenance["admission"] = "parcoursup_2025"
        if f.get("profil_admis"):
            provenance["profil_admis"] = "parcoursup_2025"
        if f.get("debouches"):
            provenance["debouches"] = "rome_4_0"
        if f.get("type_diplome") or f.get("duree"):
            provenance["type_diplome"] = "onisep"
        if f.get("labels"):
            # labels come from SecNumEdu scrape + manual_labels.json overlay
            provenance["labels"] = "secnumedu+manual"

        f["provenance"] = provenance

        # collected_at per source
        collected = {}
        if "parcoursup" in sources_present:
            collected["parcoursup"] = today
        if "onisep" in sources_present:
            collected["onisep"] = today
        if "rome" in sources_present:
            collected["rome"] = today
        f["collected_at"] = collected

        # merge_confidence per source
        confidence = {}
        if "parcoursup" in sources_present:
            confidence["parcoursup"] = 1.0
        if "onisep" in sources_present:
            if mm == "rncp":
                confidence["onisep"] = 1.0
            elif mm.startswith("fuzzy_"):
                try:
                    score = float(mm.split("_", 1)[1]) / 100.0
                    confidence["onisep"] = round(score, 2)
                except (ValueError, IndexError):
                    confidence["onisep"] = 0.85
            elif mm == "onisep_only":
                confidence["onisep"] = 1.0  # ONISEP-native, no merge loss
            elif mm == "parcoursup_only":
                confidence["onisep"] = None  # not matched
        if f.get("labels"):
            confidence["labels"] = 1.0
        f["merge_confidence"] = confidence

    return fiches
