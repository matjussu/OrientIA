from rapidfuzz import fuzz
from src.collect.normalize import normalize_name, normalize_city
from src.collect.niveau import infer_niveau


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
) -> list[dict]:
    onisep_sigs = [(f, _signature(f)) for f in onisep]
    merged = []
    for ps in parcoursup:
        ps_sig = _signature(ps)
        best_score = 0
        best_onisep = None
        for onisep_fiche, on_sig in onisep_sigs:
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

        # Stage 3: manual table (if provided)
        # Looks up each fiche against an external cross-reference table.
        # An entry with empty labels is "explicitly unlabeled" — useful for
        # benchmark contrast (private schools without SecNumEdu/CTI labels).
        if manual_table is not None:
            f_etab_norm = normalize_name(f.get("etablissement", ""))
            if f_etab_norm:
                for entry in manual_table:
                    ref = entry.get("etab_normalized", "")
                    if not ref:
                        continue
                    # Match if manual ref is substring of fiche etab (most specific) or vice versa
                    if ref in f_etab_norm or f_etab_norm in ref:
                        for label in entry.get("labels", []):
                            if label not in existing_labels:
                                existing_labels.append(label)
                        break  # first match wins

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
