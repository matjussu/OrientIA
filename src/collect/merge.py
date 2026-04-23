from datetime import date
from rapidfuzz import fuzz
from src.collect.normalize import normalize_name, normalize_city
from src.collect.niveau import infer_niveau
from src.collect.rome import get_debouches_for_domain


# Mapping codes NSF (Nomenclature Spécialités Formation) → domaine OrientIA.
# Utilisé pour inférer un `domaine` sur les fiches RNCP + MonMaster qui n'ont
# pas de classification domaine OrientIA native. Couvre les 17 secteurs
# NSF principaux (code première lettre = grand secteur).
_NSF_PREFIX_TO_DOMAIN = {
    "1": "sciences_fondamentales",   # 100-199
    "2": "ingenierie_industrielle",  # 200-249 informatique + 250-299 industrie
    "3": "services",                  # 300-499 services (commerce, santé, transport...)
    "4": "sciences_humaines",         # 410-429 lettres / 500-599 général
}

# Sous-mapping plus granulaire pour les NSF 3xx (services) : secteurs clés.
_NSF_CODE_TO_DOMAIN = {
    "326": "data_ia",                 # Informatique, TIT
    "344": "sante",                   # Technologies médicales
    "331": "sante",                   # Santé
    "332": "sante",                   # Travail social
    "133": "sciences_fondamentales",  # Maths / physique fondamentales
    "134": "sciences_fondamentales",  # Sciences vie / terre
    "230": "ingenierie_industrielle", # Spécialités pluritechnologiques
    "310": "eco_gestion",             # Commerce, gestion
    "313": "eco_gestion",             # Finance, banque, assurance
    "315": "eco_gestion",             # Ressources humaines
    "125": "sciences_humaines",       # Histoire, géographie
    "126": "sciences_humaines",       # Philosophie
    "131": "langues",                 # Français, littérature, langues
    "136": "langues",                 # Langues vivantes étrangères
    "223": "ingenierie_industrielle", # Métallurgie
    "227": "ingenierie_industrielle", # Énergie
    "343": "communication",           # Communication, information
    "335": "sciences_humaines",       # Animation, tourisme
    "324": "eco_gestion",             # Secrétariat
    "345": "eco_gestion",             # Application informatique gestion
    "100": "sciences_fondamentales",  # Formations générales
    "200": "ingenierie_industrielle",
    "300": "services",
    "400": "sciences_humaines",
    "500": "sciences_humaines",
}


def _infer_domaine_from_nsf(nsf_codes: list) -> str | None:
    """Infère un domaine OrientIA depuis les codes NSF d'une fiche."""
    if not nsf_codes:
        return None
    for nsf in nsf_codes:
        code = nsf.get("code") if isinstance(nsf, dict) else str(nsf)
        if not code:
            continue
        # Match exact code 3 digits
        if code in _NSF_CODE_TO_DOMAIN:
            return _NSF_CODE_TO_DOMAIN[code]
    # Fallback sur préfixe 1-chiffre
    for nsf in nsf_codes:
        code = nsf.get("code") if isinstance(nsf, dict) else str(nsf)
        if code and code[0] in _NSF_PREFIX_TO_DOMAIN:
            return _NSF_PREFIX_TO_DOMAIN[code[0]]
    return None


def _infer_domaine_from_rome(rome_codes: list) -> str | None:
    """Infère un domaine OrientIA depuis les codes ROME d'une fiche."""
    if not rome_codes:
        return None
    # M18* = informatique/data, J* = santé, K* = social, M1405+ = data scientist
    first = rome_codes[0]
    code = first.get("code") if isinstance(first, dict) else str(first)
    if not code:
        return None
    if code.startswith("M18") or code in {"M1405", "M1419", "M1423", "M1811", "M1868", "M1894"}:
        return "data_ia" if code in {"M1405", "M1419", "M1423", "M1811", "M1868", "M1894"} else "cyber"
    if code.startswith("J"):
        return "sante"
    if code.startswith("K"):
        return "social"
    if code.startswith("M1"):
        return "ingenierie_industrielle"
    if code.startswith("C"):
        return "eco_gestion"
    if code.startswith("D"):
        return "ingenierie_industrielle"
    if code.startswith("E"):
        return "ingenierie_industrielle"
    if code.startswith("H"):
        return "ingenierie_industrielle"
    if code.startswith("F"):
        return "ingenierie_industrielle"  # Construction, BTP
    if code.startswith("G"):
        return "services"  # Hôtellerie restauration
    if code.startswith("L"):
        return "communication"  # Arts, spectacle, communication
    return None


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
        #
        # DOMAIN FILTER (Vague santé fix) : the current manual table is all
        # cyber-focused (SecNumEdu, CTI, CGE, Grade Master). Applying its
        # labels to any fiche of a listed establishment wrongly labelled
        # PASS/Licence santé fiches at Université de Limoges etc. as
        # SecNumEdu. We now only apply the manual table to fiches in the
        # tech domains (cyber, data_ia) where those labels are relevant.
        if manual_table is not None and f.get("domaine") in ("cyber", "data_ia"):
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


# === Extension scope élargi 17-25 ans (ADR-039) : MonMaster + RNCP + Céreq ===


def monmaster_to_fiche(mm_record: dict) -> dict:
    """Convertit un record MonMaster normalisé en fiche compatible pipeline.

    MonMaster normalisé (via src/collect/monmaster.py) a déjà les bons champs
    `nom`, `etablissement`, `ville`, `niveau`. On ajoute juste `domaine`
    (inféré depuis discipline) et `match_method`.
    """
    fiche = dict(mm_record)
    # Assure la présence des champs pipeline
    fiche.setdefault("match_method", "monmaster_only")
    fiche.setdefault("labels", [])
    fiche.setdefault("statut", "Public")  # masters universitaires = public par défaut
    # Domaine inféré depuis discipline MESR (plus fin que "master" générique)
    if not fiche.get("domaine"):
        disc = (fiche.get("discipline") or "").lower()
        if "informatique" in disc or "science" in disc and "donnée" in disc:
            fiche["domaine"] = "data_ia"
        elif "sant" in disc or "biologie" in disc or "médecine" in disc:
            fiche["domaine"] = "sante"
        elif "droit" in disc or "politique" in disc:
            fiche["domaine"] = "droit"
        elif "économ" in disc or "gestion" in disc:
            fiche["domaine"] = "eco_gestion"
        elif "humaine" in disc or "social" in disc:
            fiche["domaine"] = "sciences_humaines"
        elif "langue" in disc:
            fiche["domaine"] = "langues"
        elif "lettre" in disc or "art" in disc:
            fiche["domaine"] = "lettres_arts"
        elif "sport" in disc or "staps" in disc:
            fiche["domaine"] = "sport"
        elif "fondament" in disc or "ingénier" in disc or "technolog" in disc:
            fiche["domaine"] = "sciences_fondamentales"
        else:
            fiche["domaine"] = "autre"
    return fiche


def rncp_to_fiche(certif: dict) -> dict:
    """Convertit une certification RNCP normalisée en fiche pipeline.

    RNCP (via src/collect/rncp.py) a `intitule` / `numero_fiche` / `niveau`
    mais pas `nom` / `etablissement` / `ville`. On mappe :
    - `nom` = `intitule`
    - `etablissement` = premier certificateur (ou vide)
    - `ville` = "" (certification nationale, pas de ville)
    - `domaine` = inféré depuis codes_nsf + codes_rome
    """
    certificateurs = certif.get("certificateurs") or []
    etab = ""
    if certificateurs:
        etab = (certificateurs[0].get("nom") or "").strip()

    domaine = _infer_domaine_from_nsf(certif.get("codes_nsf") or []) or \
              _infer_domaine_from_rome(certif.get("codes_rome") or []) or \
              "autre"

    fiche = {
        "source": "rncp",
        "phase": certif.get("phase", "initial"),
        "nom": certif.get("intitule", ""),
        "etablissement": etab,
        "ville": "",
        "rncp": certif.get("numero_fiche"),
        "niveau": certif.get("niveau"),
        "niveau_eu": certif.get("niveau_eu"),
        "type_diplome": certif.get("abrege_intitule"),
        "abrege_type": certif.get("abrege_type"),
        "domaine": domaine,
        "statut": "Certificat RNCP",  # catégorie distincte des formations classiques
        "voies_acces": certif.get("voies_acces") or [],
        "codes_rome": certif.get("codes_rome") or [],
        "codes_nsf": certif.get("codes_nsf") or [],
        "certificateurs": certificateurs,
        "actif": certif.get("actif", True),
        "date_effet": certif.get("date_effet"),
        "date_fin_enregistrement": certif.get("date_fin_enregistrement"),
        "match_method": "rncp_only",
        "labels": [],
    }
    return fiche


def attach_cereq_insertion(
    fiches: list[dict], cereq_entries: list[dict] | None
) -> list[dict]:
    """Enrichit chaque fiche avec les stats d'insertion Céreq correspondant
    à son `niveau` + `domaine`.

    Céreq agrège par niveau × domaine, pas par formation individuelle — donc
    l'enrichissement est indicatif (plusieurs fiches partagent les mêmes
    stats). Utile pour réponses RAG "x% d'insertion à 3 ans pour les masters
    en informatique" sans inventer.

    Sans aucun CSV Céreq parsé → no-op (scaffold-ready).
    """
    if not cereq_entries:
        return fiches
    # Index Céreq par (niveau, domaine)
    index: dict[tuple, dict] = {}
    for entry in cereq_entries:
        key = (entry.get("niveau"), (entry.get("domaine") or "").lower())
        if key not in index or index[key].get("cohorte", "") < entry.get("cohorte", ""):
            index[key] = entry

    for f in fiches:
        key = (f.get("niveau"), (f.get("domaine") or "").lower())
        stats = index.get(key)
        if stats:
            f["insertion_pro"] = {
                "taux_emploi_3ans": stats.get("taux_emploi_3ans"),
                "taux_emploi_6ans": stats.get("taux_emploi_6ans"),
                "taux_cdi": stats.get("taux_cdi"),
                "salaire_median_embauche": stats.get("salaire_median_embauche"),
                "source": "cereq",
                "cohorte": stats.get("cohorte"),
            }
    return fiches


def merge_all_extended(
    parcoursup: list[dict],
    onisep: list[dict],
    secnumedu: list[dict],
    monmaster: list[dict] | None = None,
    rncp: list[dict] | None = None,
    cereq: list[dict] | None = None,
    manual_labels: list[dict] | None = None,
    fuzzy_threshold: int = 85,
) -> list[dict]:
    """Pipeline étendu : intègre MonMaster + RNCP + Céreq en plus du pipeline
    legacy (Parcoursup + ONISEP + SecNumEdu).

    Backward-compat : si `monmaster`, `rncp` ou `cereq` sont None/vides, le
    comportement reste identique à `merge_all()` existant (pas de side-effect
    sur les tests de régression existants).

    Respect ADR-039 scope élargi : chaque fiche issue des nouvelles sources
    porte un `phase` explicite (master / initial / reorientation) pour
    faciliter la répartition 33/33/34.
    """
    # Étape 1 : pipeline legacy (Parcoursup + ONISEP + SecNumEdu + labels + debouches + metadata)
    legacy = merge_all(parcoursup, onisep, secnumedu, manual_labels, fuzzy_threshold)

    # Étape 2 : append MonMaster (si présent)
    mm_fiches = [monmaster_to_fiche(r) for r in (monmaster or [])]

    # Étape 3 : append RNCP (si présent)
    rncp_fiches = [rncp_to_fiche(c) for c in (rncp or [])]

    # Étape 4 : merge global
    all_fiches = legacy + mm_fiches + rncp_fiches

    # Étape 5 : attach_debouches ROME (pour les fiches qui n'ont pas encore
    # de débouchés — ex MonMaster ne les a pas nativement)
    all_fiches = attach_debouches(all_fiches)

    # Étape 6 : attach_metadata pour les nouveaux ajouts (MonMaster + RNCP
    # manquent provenance / collected_at / merge_confidence après étape 2-3)
    all_fiches = attach_metadata(all_fiches)

    # Étape 7 : enrichissement Céreq (late-stage, indicatif par niveau+domaine)
    all_fiches = attach_cereq_insertion(all_fiches, cereq)

    # Étape 8 : assurer phase par défaut si absente (rétrocompat Parcoursup)
    for f in all_fiches:
        if not f.get("phase"):
            # Parcoursup legacy = majoritairement phase (a) post-bac initial
            niveau = f.get("niveau") or ""
            f["phase"] = "master" if niveau in ("bac+5", "bac+8") else "initial"

    return all_fiches
