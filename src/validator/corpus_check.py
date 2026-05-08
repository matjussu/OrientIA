"""Corpus-check déterministe (Validator v1 couche 2).

Extrait les claims 'formation à établissement' de la réponse et vérifie
qu'un couple similaire existe dans le corpus (1424 fiches). Retourne des
CorpusWarning pour les claims sans correspondance raisonnable.

Stratégie :
- Extraction regex ciblée : patterns 'Licence/Master/BTS/BUT/MBA ... à/de l'/de Etablissement'
- Similarité composite `SequenceMatcher` : 70% nom + 30% établissement
- Seuil `similarity < 0.30` (conservateur) → claim flaggé comme probablement inventé

Pas d'appel LLM, pas de FAISS nécessaire (simple fuzzy sur texte brut).
Latence O(claims × fiches) négligeable pour ~5 claims × 1424 fiches.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass
class FormationClaim:
    raw: str
    formation_name: str | None
    etablissement: str | None


@dataclass
class CorpusWarning:
    claim: str
    reason: str
    closest_match: str | None = None
    similarity: float = 0.0


# Patterns extracteurs. Conservative : requiert à la fois type_diplôme +
# établissement (réduit faux positifs sur les mentions génériques).
_DIPLOMA_TYPE = (
    r"(?P<type>"
    r"Licence(?:\s+pro(?:fessionnelle)?)?|"
    r"Master(?:\s+MEEF)?|"
    r"BTS(?:A)?|"
    r"BUT|DUT|"
    r"Bachelor(?:\s+Universitaire\s+de\s+Technologie)?|"
    r"MBA|"
    r"Diplôme\s+d'ingénieur|"
    r"PASS|"
    r"L\.?AS|"
    r"Certificat\s+de\s+Spécialisation"
    r")"
)

# Séparateurs syntaxiques qui terminent le bloc etab (lookahead).
_ETAB_END_LOOKAHEAD = (
    r"(?=\s+(?:ou|et|pour|afin|qui|dans|où|offrant|propose|dispose|avec)\s+"
    r"|[.,;!?\n]"
    r"|$)"
)

_CLAIM_PATTERNS = [
    # Pattern 1 — "[Type] X à [Université|École|IUT|Fac|IFSI|...]"
    # Etab s'arrête à un séparateur syntaxique (ou/et/pour/...) ou ponctuation.
    re.compile(
        _DIPLOMA_TYPE
        + r"\s+(?P<name>[A-ZÀ-Ÿ][\wÀ-ÿ\s\-'/&,]{2,60}?)"
        + r"\s+(?:à\s+(?:l'|la\s+|le\s+)?|de\s+(?:l'|la\s+|le\s+))"
        + r"(?P<etab>(?:Université|IUT|École|Institut|Faculté|Fac|IFSI|ENS|INSA|"
        + r"Polytech|Télécom|Centrale|EPITA|EFREI|ESIEE|ESGI|Epitech|Supinfo|"
        + r"ENSIBS|ISEN|ISEP|[A-ZÀ-Ÿ])[\wÀ-ÿ\s\-'/&]{1,60}?)"
        + _ETAB_END_LOOKAHEAD,
        re.UNICODE,
    ),
    # Pattern 2 — Forme parenthétique : "[Type] X (Ville)" ou "[Type] X (Etablissement)".
    # Sprint refonte 2026-05-05 : forme massivement utilisée par le LLM,
    # historiquement skippée par le pattern 1 (cf forensic Q1
    # "Licence Maths-Physique Appliquées (Strasbourg) 42% admission" — 0 fiche
    # match, 0 warning car claim non extrait). La parenthèse peut contenir une
    # ville, un campus, ou un établissement court — on les normalise tous en
    # `etab` pour la similarité (matching sur ville+etablissement de la fiche
    # via check_formation_exists).
    re.compile(
        _DIPLOMA_TYPE
        + r"\s+(?P<name>[A-ZÀ-Ÿ][\wÀ-ÿ\s\-'/&,]{2,80}?)"
        + r"\s*\((?P<etab>[A-ZÀ-Ÿ][\wÀ-ÿ\s\-'/&,]{2,60}?)\)",
        re.UNICODE,
    ),
    # Pattern 3 — Forme avec tiret cadratin/em-dash : "[Type] X — [Etab]".
    # Style courant dans les TL;DR Plan A/B/C ("Plan A — Licence X — Toulouse").
    re.compile(
        _DIPLOMA_TYPE
        + r"\s+(?P<name>[A-ZÀ-Ÿ][\wÀ-ÿ\s\-'/&,]{2,80}?)"
        + r"\s*[—–-]\s+"
        + r"(?P<etab>(?:Université|IUT|École|Institut|Faculté|Fac|IFSI|ENS|INSA|"
        + r"Polytech|Télécom|Centrale|EPITA|EFREI|ESIEE|ESGI|Epitech|"
        + r"[A-ZÀ-Ÿ])[\wÀ-ÿ\s\-'/&]{1,60}?)"
        + _ETAB_END_LOOKAHEAD,
        re.UNICODE,
    ),
]


_ETAB_STOP_SEPARATORS = [
    " ou ", " et ", ", ", "; ", ". ", " pour ", " afin ",
    " dans ", " qui ", " où ", " offrant ", " propose ", " dispose ",
]


def _trim_etablissement(etab: str) -> str:
    """Coupe l'établissement au premier séparateur syntaxique pour éviter
    que le regex greedy n'embarque la suite de la phrase."""
    low = etab.lower()
    cut = len(etab)
    for sep in _ETAB_STOP_SEPARATORS:
        i = low.find(sep)
        if 0 < i < cut:
            cut = i
    return etab[:cut].strip().rstrip(".,;:")


def extract_claims(answer: str) -> list[FormationClaim]:
    """Extrait les claims 'formation à établissement' du texte."""
    claims: list[FormationClaim] = []
    for pattern in _CLAIM_PATTERNS:
        for m in pattern.finditer(answer):
            try:
                formation_name = (m.group("type") + " " + m.group("name")).strip()
                etablissement = _trim_etablissement(m.group("etab"))
            except IndexError:
                continue
            claims.append(
                FormationClaim(
                    raw=m.group(0),
                    formation_name=formation_name,
                    etablissement=etablissement,
                )
            )
    return claims


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def check_formation_exists(
    formation_name: str,
    etablissement: str | None,
    fiches: list[dict],
    threshold: float = 0.55,
) -> tuple[bool, str | None, float]:
    """Cherche la fiche la plus proche dans le corpus.

    Retourne (found, closest_match_label, best_similarity).
    `found` = True si best_similarity >= threshold.

    Score composite : 70% nom + 30% établissement (les noms de formations
    ont plus de signal que les noms d'écoles, souvent partagés).
    """
    best_sim = 0.0
    best_label: str | None = None
    fn = formation_name.lower().strip()
    et = (etablissement or "").lower().strip()

    # Pondération 0.85 nom / 0.15 etab — on veut que le nom domine la
    # décision (le nom d'une formation est plus discriminant que l'école
    # qui peut légitimement héberger plusieurs cursus).
    # Sprint refonte 2026-05-05 : approche en 2 phases pour éviter les
    # faux positifs type "Licence Maths-Physique (Strasbourg) → Licence
    # Physique — Tours" (composite 0.647) :
    #   Phase 1 : filtrer les candidats dont l'etab/ville matche le claim
    #     (sim_etab ≥ ETAB_FILTER_THRESHOLD).
    #   Phase 2 : best parmi candidats etab-compatibles. Si aucun
    #     candidat → fallback best général sans garde (signal de non-match).
    # L'`et` peut venir d'une parenthèse ("Licence X (Strasbourg)")
    # contenant une ville, ou d'une forme "à Université de X" contenant
    # un établissement. On compare à max(sim(et, etab), sim(et, ville))
    # pour couvrir les deux cas.
    # Compatibilité etab acceptée si :
    #   - similarité fuzzy ≥ 0.6 (variations orthographiques type
    #     "Saint-Étienne" / "Saint Etienne", "EFREI Paris" / "EFREI Paris-Cachan")
    #   OR
    #   - substring match (et ⊂ f_etab/f_ville ou inversement) — couvre les
    #     acronymes courts ("EFREI" ⊂ "EFREI Paris", "Sciences Po" ⊂
    #     "Institut d'études politiques de Paris - Sciences Po"). SequenceMatcher
    #     est artificiellement haut sur strings courts (Strasbourg vs Tours = 0.53).
    ETAB_FUZZY_THRESHOLD = 0.6

    def _etab_compatible(f_etab: str, f_ville: str) -> tuple[bool, float]:
        sim_etab = max(_similarity(et, f_etab), _similarity(et, f_ville) if f_ville else 0.0)
        if sim_etab >= ETAB_FUZZY_THRESHOLD:
            return True, sim_etab
        if f_etab and (et in f_etab or f_etab in et):
            return True, max(sim_etab, 0.7)
        if f_ville and (et in f_ville or f_ville in et):
            return True, max(sim_etab, 0.7)
        return False, sim_etab

    # Phase 1 : pré-filtrer par compatibilité etab (si claim spécifie etab)
    if et:
        candidats = []
        for f in fiches:
            f_etab = (f.get("etablissement") or "").lower().strip()
            f_ville = (f.get("ville") or "").lower().strip()
            ok, sim_etab = _etab_compatible(f_etab, f_ville)
            if ok:
                candidats.append((f, sim_etab))
        # Aucun candidat etab-compatible → claim suspect par construction.
        # On retourne quand même un best général pour le contexte du warning.
        if not candidats:
            for f in fiches:
                f_nom = (f.get("nom") or "").lower().strip()
                sim_nom = _similarity(fn, f_nom)
                composite = 0.85 * sim_nom  # sim_etab = 0
                if composite > best_sim:
                    best_sim = composite
                    best_label = f"{f.get('nom')} — {f.get('etablissement')}"
            return (False, best_label, best_sim)
    else:
        # Pas d'etab dans le claim : ancien comportement (tous candidats)
        candidats = [(f, 0.5) for f in fiches]

    # Phase 2 : best parmi candidats etab-compatibles
    for f, sim_etab in candidats:
        f_nom = (f.get("nom") or "").lower().strip()
        sim_nom = _similarity(fn, f_nom)
        composite = 0.85 * sim_nom + 0.15 * sim_etab
        if composite > best_sim:
            best_sim = composite
            best_label = f"{f.get('nom')} — {f.get('etablissement')}"

    return (best_sim >= threshold, best_label, best_sim)


def check_claims_in_corpus(
    answer: str,
    fiches: list[dict],
    threshold: float = 0.55,
) -> list[CorpusWarning]:
    """Retourne les claims non trouvés dans le corpus (< threshold).

    Threshold 0.55 avec poids 0.85/0.15 : un paraphrase réaliste d'une
    fiche du corpus dépasse 0.55 (nom proche + etab plausible) ; une
    formation inventée mais citée auprès d'un établissement existant reste
    sous 0.55 car la similarité du nom domine 85% du score.
    """
    warnings: list[CorpusWarning] = []
    for claim in extract_claims(answer):
        found, closest, sim = check_formation_exists(
            claim.formation_name or "",
            claim.etablissement,
            fiches,
            threshold,
        )
        if not found:
            warnings.append(
                CorpusWarning(
                    claim=claim.raw,
                    reason="formation_not_found_in_corpus",
                    closest_match=closest,
                    similarity=round(sim, 2),
                )
            )
    return warnings
