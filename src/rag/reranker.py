from dataclasses import dataclass


@dataclass(frozen=True)
class RerankConfig:
    # Label boosts — the primary INRIA-thesis innovation
    secnumedu_boost: float = 1.5
    cti_boost: float = 1.3
    grade_master_boost: float = 1.3
    public_boost: float = 1.1
    # Niveau boosts — secondary correction for BTS dominance in Parcoursup data
    # Intentionally kept below label boosts so they don't dominate.
    level_boost_bac5: float = 1.15
    level_boost_bac3: float = 1.05
    # Named-establishment boost — mild preference for fiches whose establishment
    # field is populated (vs ONISEP generic diploma types with empty etab).
    # Helps surface EFREI, ENSIBS, CentraleSupélec, etc. alongside the generic
    # ANSSI titles in questions like "meilleures formations en cybersécurité".
    etab_named_boost: float = 1.1
    # Vague B — Parcoursup-rich boost: a fiche with cod_aff_form + a populated
    # profil_admis (non-zero bac_type_pct) carries concrete chiffres (taux
    # d'accès, mentions %, bac-type split) that the Vague A generator context
    # exposes to the LLM. These fiches produce measurably more grounded
    # answers than ONISEP-only fiches which only describe the diploma type.
    # Kept moderate (1.2) so it amplifies without dominating label boosts.
    parcoursup_rich_boost: float = 1.2
    # ADR-049 — Domain-aware boosts (multi-corpus retrieval).
    # Appliqués UNIQUEMENT quand `domain_hint` (paramètre d'appel) matche
    # le `domain` de la fiche. Fiches non-matching gardent leur score 1.0
    # (pas de pénalité). Conséquence : le pivot ADR-048 multi-corpus est
    # exploité uniquement quand l'intent multi-domain le justifie.
    domain_boost_apec_region: float = 1.5
    domain_boost_metier: float = 1.3
    domain_boost_parcours_bacheliers: float = 1.3

    def as_dict(self) -> dict:
        return {
            "secnumedu_boost": self.secnumedu_boost,
            "cti_boost": self.cti_boost,
            "grade_master_boost": self.grade_master_boost,
            "public_boost": self.public_boost,
            "level_boost_bac5": self.level_boost_bac5,
            "level_boost_bac3": self.level_boost_bac3,
            "etab_named_boost": self.etab_named_boost,
            "parcoursup_rich_boost": self.parcoursup_rich_boost,
            "domain_boost_apec_region": self.domain_boost_apec_region,
            "domain_boost_metier": self.domain_boost_metier,
            "domain_boost_parcours_bacheliers": self.domain_boost_parcours_bacheliers,
        }


# Mapping domain hint → attribut de config (utilisé en Stage E ADR-049).
_DOMAIN_BOOST_FIELDS = {
    "apec_region": "domain_boost_apec_region",
    "metier": "domain_boost_metier",
    "parcours_bacheliers": "domain_boost_parcours_bacheliers",
}


def rerank(
    results: list[dict],
    config: RerankConfig,
    domain_hint: str | None = None,
) -> list[dict]:
    """Re-rank retrieval results applying staged boosts.

    Stages A-D : label / niveau / etab / parcoursup-rich (existant).
    Stage E (ADR-049) : domain-aware boost selon `domain_hint`. Le hint
    est calculé en amont par `intent.classify_domain_hint(question)`. Si
    None, aucun domain boost appliqué (= comportement formation-centric
    pre-ADR-049 préservé).

    Le domain boost est appliqué UNIQUEMENT aux fiches dont
    `fiche["domain"]` correspond au hint. Les fiches d'autres domains ne
    sont PAS pénalisées (score multiplié par 1.0 implicite).
    """
    domain_boost = 1.0
    if domain_hint and domain_hint in _DOMAIN_BOOST_FIELDS:
        domain_boost = getattr(config, _DOMAIN_BOOST_FIELDS[domain_hint])

    reranked = []
    for r in results:
        fiche = r["fiche"]
        score = r["base_score"]
        labels = fiche.get("labels") or []

        # Stage A: label boosts (primary)
        if "SecNumEdu" in labels:
            score *= config.secnumedu_boost
        if "CTI" in labels:
            score *= config.cti_boost
        if "Grade Master" in labels:
            score *= config.grade_master_boost
        if fiche.get("statut") == "Public":
            score *= config.public_boost

        # Stage B: niveau boosts (secondary)
        niveau = fiche.get("niveau")
        if niveau == "bac+5":
            score *= config.level_boost_bac5
        elif niveau == "bac+3":
            score *= config.level_boost_bac3
        # bac+2 and None get no boost (implicit 1.0 multiplier)

        # Stage C: named-establishment boost (mild)
        if (fiche.get("etablissement") or "").strip():
            score *= config.etab_named_boost

        # Stage D (Vague B): Parcoursup-rich boost — fiche carries cod_aff_form
        # AND a populated profil_admis.bac_type_pct (at least one value > 0).
        # These fiches arm the Vague A generator context with real numbers.
        if _is_parcoursup_rich(fiche):
            score *= config.parcoursup_rich_boost

        # Stage E (ADR-049): domain-aware boost — applied ONLY to fiches
        # whose `domain` matches the query's `domain_hint`. No-op for
        # fiches in other domains (multiplier 1.0 implicite). Le pivot
        # multi-corpus est ainsi activé sélectivement quand l'intent le
        # justifie, évitant la dilution top-K du formation-centric pur.
        if domain_boost != 1.0 and fiche.get("domain") == domain_hint:
            score *= domain_boost

        new = dict(r)
        new["score"] = score
        reranked.append(new)

    reranked.sort(key=lambda x: x["score"], reverse=True)
    return reranked


def _is_parcoursup_rich(fiche: dict) -> bool:
    """A fiche is Parcoursup-rich when it has a cod_aff_form AND a populated
    profil_admis (at least one bac-type percentage > 0).

    This is the signal that the fiche will produce a rich Vague A context
    (taux d'accès, mentions %, bac-type split, volumes de vœux, sources
    officielles citables). ONISEP-only fiches fail this check because they
    have no cod_aff_form.
    """
    cod = fiche.get("cod_aff_form")
    if not cod or not (isinstance(cod, str) and cod.strip()):
        return False
    profil = fiche.get("profil_admis") or {}
    bac_pct = profil.get("bac_type_pct") or {}
    # At least one bac-type percentage must be > 0 to avoid boosting
    # fiches that parsed cod_aff_form but have all-zero profil (Parcoursup
    # "capacity closed" or legacy rows).
    return any(
        (isinstance(v, (int, float)) and v > 0)
        for v in bac_pct.values()
    )
