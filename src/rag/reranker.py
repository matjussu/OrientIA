from dataclasses import dataclass


@dataclass(frozen=True)
class RerankConfig:
    # Label boosts — historiquement décrits comme la "primary INRIA-thesis
    # innovation". Vague 0.5 (2026-05-08) — neutralisés à 1.0 par défaut.
    # Audit Phase 0 v5 a mesuré la couverture effective :
    #   SecNumEdu : 21 fiches sur 47 193 = 0.04%
    #   CTI : 7 fiches = 0.01%
    #   Grade Master : 1 fiche = 0.002%
    # Total signal mort à 0.06% — les boosts ×1.5/×1.3 étaient appliqués sur
    # un signal quasi-inexistant. Neutralisation honnête en attendant une
    # ré-extraction depuis ANSSI/CTI/CGE/FESIC référentiels (Vague 1+ ou
    # post-démo). Réactivable simplement en passant la valeur > 1.0 au
    # constructeur quand la data sera enrichie.
    # public_boost reste à 1.1 car couverture statut="Public" mesurée à
    # 41.5% (audit Phase 0 v5) — signal significatif.
    secnumedu_boost: float = 1.0
    cti_boost: float = 1.0
    grade_master_boost: float = 1.0
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
    # Vague 0.5 (2026-05-08) — ROME 4.0 metier_detail boost. Sans ce boost
    # dédié, les fiches `metier` (ONISEP IDEO, 2150 fiches) écrasaient
    # systématiquement les fiches `metier_detail` (ROME 4.0, 1584 fiches)
    # au top-K même pour les questions conceptuelles métier (cas spot-check
    # Q5 "Que fait un actuaire au quotidien ?" : top-5 sans aucune fiche
    # ROME 4.0 actuaire). Boost 1.4 priorise légèrement ROME 4.0 (compétences
    # structurées + code ROME) sur ONISEP IDEO (description conversationnelle)
    # pour rééquilibrer le retrieval. Quand domain_hint=metier, les 2 corpus
    # sont boostés (cf rerank() ci-dessous).
    domain_boost_metier_detail: float = 1.4
    domain_boost_parcours_bacheliers: float = 1.3
    # Phase B (ordre 2026-04-25-1442) — 3 nouveaux corpora aggrégés
    domain_boost_crous: float = 1.4
    domain_boost_insee_salaire: float = 1.5
    domain_boost_insertion_pro: float = 1.4
    # Phase C DARES Métiers 2030 — tuned 1.5 → 1.0 le 2026-04-26.
    # Bench dédié ordre 1100 a révélé régression -30.5pp verified /
    # +24.2pp halluc avec ×1.5 (9/10 queries activantes voyaient top-10 =
    # 100% DARES). Iteration ×1.1 améliore mais 6/10 queries toujours
    # only-DARES top-K. ×1.0 = pas de boost, pure L2 ranking. Domain
    # hint reste classifié (utilisé pour auditing/observability) mais
    # n'écrase plus le top-K. Cohabitation formation + DARES naturelle.
    domain_boost_metier_prospective: float = 1.0
    # France Comp blocs RNCP — compétences certifiées (cohérent données
    # chiffrées externes APEC/INSEE/DARES = 1.5).
    domain_boost_competences_certif: float = 1.5
    # Sprint 7 Action 5 — boosts pour les nouveaux corpora Sprint 6.
    # Cohabitation avec multi-corpus existant : niveaux similaires aux
    # autres domaines factuels (1.4-1.5). Pas de pénalité hors-domain.
    # Anti-hallu défensif (axes 4 + 2) bénéficie du nouveau verdict
    # `verified_by_official_source` (Sprint 7 Action 1) — le boost
    # accentue le retrieval, l'Action 1 valorise la mesure.
    domain_boost_formation_insertion: float = 1.4  # Inserjeunes lycée pro (axe 3b star)
    domain_boost_financement_etudes: float = 1.5  # Financement curated (axe 4 muet → unmute)
    domain_boost_territoire_drom: float = 1.5  # DROM territorial (axe 2 non-mesuré)
    domain_boost_voie_pre_bac: float = 1.4  # BAC PRO + CAP catalogue (axe 3a rare)

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
            "domain_boost_metier_detail": self.domain_boost_metier_detail,
            "domain_boost_parcours_bacheliers": self.domain_boost_parcours_bacheliers,
            "domain_boost_crous": self.domain_boost_crous,
            "domain_boost_insee_salaire": self.domain_boost_insee_salaire,
            "domain_boost_insertion_pro": self.domain_boost_insertion_pro,
            "domain_boost_metier_prospective": self.domain_boost_metier_prospective,
            "domain_boost_competences_certif": self.domain_boost_competences_certif,
            # Sprint 7 Action 5
            "domain_boost_formation_insertion": self.domain_boost_formation_insertion,
            "domain_boost_financement_etudes": self.domain_boost_financement_etudes,
            "domain_boost_territoire_drom": self.domain_boost_territoire_drom,
            "domain_boost_voie_pre_bac": self.domain_boost_voie_pre_bac,
        }


# Mapping domain hint → attribut de config (utilisé en Stage E ADR-049).
_DOMAIN_BOOST_FIELDS = {
    "apec_region": "domain_boost_apec_region",
    "metier": "domain_boost_metier",
    "metier_detail": "domain_boost_metier_detail",
    "parcours_bacheliers": "domain_boost_parcours_bacheliers",
    "crous": "domain_boost_crous",
    "insee_salaire": "domain_boost_insee_salaire",
    "insertion_pro": "domain_boost_insertion_pro",
    "metier_prospective": "domain_boost_metier_prospective",
    "competences_certif": "domain_boost_competences_certif",
    # Sprint 7 Action 5 — Sprint 6 axes
    "formation_insertion": "domain_boost_formation_insertion",
    "financement_etudes": "domain_boost_financement_etudes",
    "territoire_drom": "domain_boost_territoire_drom",
    "voie_pre_bac": "domain_boost_voie_pre_bac",
}

# Vague 0.5 — Mapping cross-domain : un domain_hint peut booster plusieurs
# domains de fiche pour rééquilibrer la couverture top-K. Cas concret :
# `domain_hint="metier"` (classifié sur "Que fait un actuaire ?") doit booster
# à la fois les fiches `metier` (ONISEP IDEO, descriptions naturelles) ET
# `metier_detail` (ROME 4.0, compétences structurées) avec une légère priorité
# pour ROME 4.0 (1.4 vs 1.3) sur les questions conceptuelles métier.
# Si une entrée n'est pas dans ce dict, comportement par défaut : boost
# uniquement le domain qui matche strictement le hint (cf rerank()).
_DOMAIN_HINT_CROSS_BOOSTS: dict[str, list[str]] = {
    "metier": ["metier", "metier_detail"],
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
    # Vague 0.5 — calcul des domain qui doivent recevoir un boost pour ce hint.
    # Cas standard : un seul domain (= hint). Cas étendu via _DOMAIN_HINT_CROSS_BOOSTS :
    # plusieurs domains peuvent être boostés (ex hint="metier" → metier + metier_detail).
    boosted_domains: dict[str, float] = {}
    if domain_hint:
        targets = _DOMAIN_HINT_CROSS_BOOSTS.get(domain_hint, [domain_hint])
        for target_domain in targets:
            attr = _DOMAIN_BOOST_FIELDS.get(target_domain)
            if attr:
                boost = getattr(config, attr)
                if boost != 1.0:
                    boosted_domains[target_domain] = boost

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

        # Stage E (ADR-049 + Vague 0.5): domain-aware boost — applied to fiches
        # whose `domain` est dans la liste des domains boostables pour ce hint
        # (1 par défaut, ou plusieurs via _DOMAIN_HINT_CROSS_BOOSTS).
        # No-op pour fiches d'autres domains (pas de pénalité).
        fiche_domain = fiche.get("domain")
        if fiche_domain in boosted_domains:
            score *= boosted_domains[fiche_domain]

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
