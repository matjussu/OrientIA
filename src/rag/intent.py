"""Rule-based intent classifier for student questions.

Maps a French orientation question to one of 7 intent classes. The
intent then drives a retrieval strategy (top_k_sources, mmr_lambda)
via intent_to_config().

Why rule-based: deterministic, zero API cost, auditable in the study
report. The 7 classes map cleanly to observable surface patterns
(comparison particles, geographic NER, grade mentions, etc.).

Order matters in classify_intent — checks are done from most specific
to least specific, with general as the catch-all fallback.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


INTENT_COMPARAISON = "comparaison"
INTENT_GEOGRAPHIC = "geographic"
INTENT_REALISME = "realisme"
INTENT_PASSERELLES = "passerelles"
INTENT_DECOUVERTE = "decouverte"
INTENT_CONCEPTUAL = "conceptual"
INTENT_GENERAL = "general"


# --- ADR-049 : domain hints orthogonaux (multi-corpus reranker) ---
# Hints additifs (parallèles aux INTENT_*) qui détectent quand une query
# devrait privilégier un corpus retrievable non-formation. None par défaut
# (= comportement formation-centric inchangé). Le reranker applique un
# boost UNIQUEMENT aux fiches dont `domain` matche le hint.
DOMAIN_HINT_METIER = "metier"
DOMAIN_HINT_PARCOURS = "parcours_bacheliers"
DOMAIN_HINT_APEC = "apec_region"
DOMAIN_HINT_CROUS = "crous"
DOMAIN_HINT_INSEE_SALAIRE = "insee_salaire"
DOMAIN_HINT_INSERTION_PRO = "insertion_pro"
DOMAIN_HINT_COMPETENCES_CERTIF = "competences_certif"  # France Comp blocs RNCP


@dataclass(frozen=True)
class IntentConfig:
    top_k_sources: int
    mmr_lambda: float


_CONFIGS: dict[str, IntentConfig] = {
    INTENT_GENERAL:     IntentConfig(top_k_sources=10, mmr_lambda=0.7),
    INTENT_COMPARAISON: IntentConfig(top_k_sources=12, mmr_lambda=0.6),
    INTENT_GEOGRAPHIC:  IntentConfig(top_k_sources=12, mmr_lambda=0.4),
    INTENT_REALISME:    IntentConfig(top_k_sources=6,  mmr_lambda=0.85),
    INTENT_PASSERELLES: IntentConfig(top_k_sources=10, mmr_lambda=0.6),
    INTENT_DECOUVERTE:  IntentConfig(top_k_sources=12, mmr_lambda=0.3),
    INTENT_CONCEPTUAL:  IntentConfig(top_k_sources=4,  mmr_lambda=0.9),
}


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s)
        if not unicodedata.combining(c)
    )


_FRENCH_CITIES = {
    "paris", "lyon", "marseille", "toulouse", "nice", "nantes", "strasbourg",
    "montpellier", "bordeaux", "lille", "rennes", "reims", "saint-etienne",
    "toulon", "grenoble", "dijon", "angers", "nimes", "villeurbanne",
    "aix-en-provence", "brest", "le mans", "amiens", "tours", "limoges",
    "clermont-ferrand", "besancon", "metz", "perpignan", "orleans",
    "mulhouse", "rouen", "caen", "nancy", "argenteuil", "boulogne-billancourt",
    "saint-denis", "vannes", "lorient", "quimper", "la rochelle", "pau",
    "valence", "annecy", "chambery", "poitiers", "avignon", "calais",
    "dunkerque", "le havre", "saint-nazaire",
}
_FRENCH_REGIONS = {
    "bretagne", "normandie", "alsace", "lorraine", "provence", "occitanie",
    "aquitaine", "auvergne", "bourgogne", "champagne", "franche-comte",
    "ile-de-france", "nord", "picardie", "pays de la loire", "rhone-alpes",
    "centre", "limousin", "poitou", "languedoc", "corse", "midi-pyrenees",
}


_PATTERNS_COMPARAISON_NORM = [
    re.compile(r"\bcompar(e[rz]?|aison)\b"),
    re.compile(r"\bdifferenc[a-z]*\s+entre\b"),
    re.compile(r"\bvaut[\s-]il\s+mieux\b"),
    re.compile(r"\bplutot que\b"),
    re.compile(r"\bmieux\s+(?:que|entre)\b"),
]
# Detected on the ORIGINAL question (case-sensitive) — catches the
# "EPITA ou EPITECH" / "INSA et CENTRALE" pattern where both sides
# are named institutions written as acronyms.
_PATTERNS_COMPARAISON_RAW = [
    re.compile(r"\b[A-Z][A-Z\-]{2,}\s+(?:ou|et)\s+[A-Z][A-Z\-]{2,}\b"),
]

_PATTERNS_REALISME = [
    re.compile(r"\b\d{1,2}[,.]?\d?\s+de\s+moyenne\b"),
    re.compile(r"\bavec\s+\d{1,2}\b"),
    re.compile(r"\btaux\s+(?:d['e]\s*)?(?:admission|acceptation|reussite)\b"),
    re.compile(r"\bselectivit[a-z]*\b"),
    re.compile(r"\baccessib[a-z]*\b"),
    re.compile(r"\b(?:est-ce que je peux|ai-je une chance|suis-je accept[a-z]+|puis-je integrer)\b"),
    re.compile(r"\bdossier\s+(?:moyen|faible|bon)\b"),
]

_PATTERNS_PASSERELLES = [
    re.compile(r"\breorient[a-z]*\b"),
    re.compile(r"\breconvers[a-z]*\b"),
    re.compile(r"\bpasserelle[sx]?\b"),
    re.compile(r"\bchanger\s+de\s+(?:filiere|voie|domaine|orientation)\b"),
    re.compile(r"\bapres\s+(?:mon|mes|\d)\s+(?:ans?|annee)"),
    re.compile(r"\btransition\s+(?:vers|professionnelle)\b"),
]

_PATTERNS_DECOUVERTE = [
    re.compile(r"\bquels metiers\b"),
    re.compile(r"\bdecouvr[a-z]*\b"),
    re.compile(r"\bmeconnu[sx]?\b"),
    re.compile(r"\boriginal[a-z]*\b"),
    re.compile(r"\bpiste[sx]?\b"),
    re.compile(r"\bj['e]\s*aime\b"),
    re.compile(r"\bje\s+(?:suis\s+)?(?:curieu[xs]|interess[a-z]+|passionn[a-z]+)\b"),
    re.compile(r"\bje\s+m['e]\s*interesse\s+(?:a|au|aux)\b"),
    re.compile(r"\bpropose[\-z]?[\-z]?moi\b"),
]

_PATTERNS_CONCEPTUAL = [
    re.compile(r"\bc['e]\s*est\s+quoi\b"),
    re.compile(r"\bqu['e]\s*est-ce\b"),
    re.compile(r"\bcomment\s+fonctionne\b"),
    re.compile(r"\bexpli(?:que[rz]?|cation)\b"),
    re.compile(r"\bdefini(?:tion|s|r)\b"),
]


# --- ADR-049 : patterns domain hint multi-corpus ---

# APEC : marché du travail cadres régional. Priorité 1 (le plus spécifique,
# évite que "marché du travail" matche aussi sur metier).
_PATTERNS_DOMAIN_APEC = [
    re.compile(r"\bmarche\s+(?:du\s+)?(?:travail|emploi)\b"),
    re.compile(r"\brecrutement[sx]?\s+(?:des\s+)?cadre[sx]?\b"),
    re.compile(r"\bcadre[sx]?\s+(?:en|a|au)\s+\d{4}\b"),
    re.compile(r"\bsalaire[sx]?\s+(?:median[a-z]*\s+)?cadre[sx]?\b"),
    re.compile(r"\bdynami(?:sme|que[sx]?)\s+(?:des\s+)?cadre[sx]?\b"),
    re.compile(r"\bperspective[sx]?\s+cadre[sx]?\b"),
    re.compile(r"\bobservatoire\s+(?:de\s+l['e]\s*emploi|des\s+cadre)"),
    re.compile(r"\bregion[a-z]*\s+(?:la\s+plus\s+)?dynami"),
]

# Parcours bacheliers : taux de réussite licence / passage L1→L2 /
# redoublement / réorientation DUT-BUT par profil bachelier.
_PATTERNS_DOMAIN_PARCOURS = [
    re.compile(r"\btaux\s+(?:de\s+)?(?:reussite|passage|obtention)\s+(?:en\s+)?(?:licence|l1|l2)"),
    re.compile(r"\bpassage\s+(?:en\s+)?l[12]\b"),
    re.compile(r"\bredoublement\s+(?:en\s+)?l1\b"),
    re.compile(r"\breorientation\s+(?:en\s+)?(?:dut|but)\b"),
    re.compile(r"\bobtention\s+(?:de\s+la\s+)?licence\s+en\s+\d\s+ans?\b"),
    re.compile(r"\b(?:bac|bachelier)\s+(?:l|s|es|stmg|techno|pro)[a-z]*\s+mention"),
    re.compile(r"\bcohorte[sx]?\s+(?:de\s+)?bacheliers?\b"),
    re.compile(r"\bstats?\s+(?:dis|des)?ent.*licence"),
]

# Métier : profession / "que fait un X" / "devenir X" / "rôle de".
# Évite que "marché du travail" + "cadres" matche aussi (priorité APEC).
_PATTERNS_DOMAIN_METIER = [
    re.compile(r"\bque\s+fait\s+un[e]?\b"),
    re.compile(r"\brole\s+(?:d['e]\s*un[e]?|du)\b"),
    re.compile(r"\bquel(?:le)?\s+(?:est\s+)?(?:le\s+)?metier\b"),
    re.compile(r"\bentre\s+(?:le[s]?\s+)?metier[sx]?\b"),
    re.compile(r"\b(?:devenir|etre)\s+(?:developpeu[rs]|ingenieur[s]?|actuair|infirmier|medecin|architect|psychologue|kine|avocat|comptable|enseignant|professeur|chercheur|consultant|journalist|designer|chef|technicien)"),
    re.compile(r"\bmetier[sx]?\s+(?:artistique[sx]?|manuel[sx]?|technique[sx]?|de\s+(?:bouche|terrain|service))"),
    re.compile(r"\b(?:profession|carriere)\s+(?:de|en|d['e]\s*)"),
    re.compile(r"\bjob\s+(?:de|d['e]\s*)"),
    re.compile(r"\bworking?\s+with\s+my\s+hands\b"),
    re.compile(r"\btravailler\s+(?:de\s+mes\s+|de\s+ses\s+)?mains\b"),
]


# Phase B (ordre 2026-04-25-1442) : 3 nouveaux domains aggregés
_PATTERNS_DOMAIN_CROUS = [
    re.compile(r"\bcrous\b"),
    re.compile(r"\blogement[sx]?\s+(?:etudiant|universitaire|crous)\b"),
    re.compile(r"\bresidence[sx]?\s+(?:universitaire|crous|etudiante[sx]?)\b"),
    re.compile(r"\b(?:resto[sx]?|restaurant[sx]?|cafeteri[as]+)\s+(?:u[r]?|universitaire[sx]?|crous)\b"),
    re.compile(r"\bvie\s+etudiante\b"),
    re.compile(r"\bse\s+loger\s+(?:a|en|pour)\s+(?:l[ae]?|mes?)\s*(?:fac|etude|universite)"),
    re.compile(r"\bou\s+(?:se\s+)?loger\s+(?:a|en|pendant)\s+(?:les\s+)?etude[sx]?\b"),
]

_PATTERNS_DOMAIN_INSEE_SALAIRE = [
    re.compile(r"\bsalaire[sx]?\s+(?:median[a-z]*|moyen[a-z]*|annuel[a-z]*|net[a-z]*|brut[a-z]*)\b"),
    re.compile(r"\bcombien\s+gagne[a-z]*\s+un[e]?\b"),
    re.compile(r"\bremuneration[sx]?\s+(?:median[a-z]*|moyenn[a-z]*)\b"),
    re.compile(r"\bsalaire[sx]?\s+(?:par|selon|tranche)\s+(?:age|tranche)\b"),
    re.compile(r"\bsalaire[sx]?\s+(?:cadre[sx]?|professions?\s+intermediaires?|employes?|ouvriers?)\b"),
    re.compile(r"\bgrille\s+(?:de\s+)?salaire[sx]?\b"),
    re.compile(r"\bpcs\s+(?:21|22|23|31|34|35|37|54)\b"),
    re.compile(r"\binsee\s+(?:salaan|salaires?)\b"),
]

_PATTERNS_DOMAIN_INSERTION_PRO = [
    re.compile(r"\btaux\s+(?:d['e]\s*)?(?:insertion|emploi)\s+(?:a|apres|au\s+bout)\s+(?:de\s+)?(?:6|12|18|24|30)\s+mois\b"),
    re.compile(r"\binsertion\s+professionnel[a-z]+\s+(?:apres|post)\s+(?:master|licence|diplom)"),
    re.compile(r"\b(?:debouches?|insertion)\s+(?:a|apres)\s+(?:bac\s*\+\s*[35]|master|licence)\b"),
    re.compile(r"\btrouve[a-z]*\s+(?:un\s+)?(?:emploi|travail)\s+(?:apres|post|au\s+bout\s+de)"),
    re.compile(r"\bcombien\s+(?:de\s+temps\s+)?(?:pour\s+)?trouver\s+(?:un\s+)?emploi\b"),
    re.compile(r"\bsortants?\s+(?:de\s+)?master\b"),
    re.compile(r"\binsersup\b"),
    re.compile(r"\benquete\s+insertion\b"),
]


# France Comp blocs RNCP — compétences certifiées par diplôme/titre.
# Détecte les questions sur le contenu pédagogique d'un diplôme : ce qu'on
# y apprend, les blocs validables, les savoir-faire certifiés. Couvre aussi
# les références explicites à RNCP (numéro de fiche) et VAE/validation
# partielle par bloc — usages opérationnels typiques des étudiants en
# reconversion ou phase (b)/(c) du scope élargi.
_PATTERNS_DOMAIN_COMPETENCES_CERTIF = [
    re.compile(r"\bbloc[sx]?\s+(?:de\s+)?competence[sx]?\b"),
    re.compile(r"\bcompetence[sx]?\s+(?:certifie[a-z]*|attestee[sx]?|valide[a-z]*)\b"),
    re.compile(r"\bcompetence[sx]?\s+(?:acquise[sx]?|developpee[sx]?)\s+(?:apres|en\s+sortant|grace\s+a)"),
    re.compile(r"\bque\s+(?:vais|va[a-z]*)?[\s-]?(?:je|on|tu)\s+apprendre\b"),
    re.compile(r"\bce\s+que\s+(?:je|on)\s+(?:vais|va)\s+apprendre\b"),
    re.compile(r"\bquel(?:s|les)?\s+(?:competences?|savoir[s\-]faire|skills?)\b"),
    re.compile(r"\bsavoir[\s\-]faire\s+(?:certifie[a-z]*|valide[a-z]*|acquis)\b"),
    re.compile(r"\b(?:objectif|programme)[sx]?\s+(?:pedagogique[sx]?|de\s+formation)\b"),
    re.compile(r"\bcontenu[sx]?\s+(?:du|de\s+(?:la|l['e]\s*))?(?:bts|but|licence|master|diplom|formation|certif)"),
    re.compile(r"\bque\s+(?:permet[a-z]*\s+(?:de\s+)?(?:faire|valider))\b"),
    re.compile(r"\brncp\s*\d+"),
    re.compile(r"\bvalidation\s+(?:partielle|par\s+bloc[sx]?)\b"),
    re.compile(r"\bvae\s+(?:par\s+bloc[sx]?|partielle)\b"),
]


def classify_domain_hint(question: str) -> str | None:
    """Retourne un hint de domain multi-corpus (ADR-049) ou None.

    Hint orthogonal au `INTENT_*` (les 2 cohabitent : un même question peut
    être COMPARAISON + DOMAIN_HINT_APEC). Le hint guide le reranker pour
    boost le bon corpus retrievable. None = formation-centric par défaut
    (comportement pre-ADR-049 préservé).

    Priorité de détection (du plus spécifique au plus générique) :
    1. APEC (marché du travail cadres) — termes très spécifiques
    2. INSEE salaire (médian / cadre / employé / PCS)
    3. Insertion pro (taux insertion à N mois)
    4. Compétences certifiées RNCP (blocs / contenu pédagogique)
    5. Parcours bacheliers (taux réussite licence × bac × mention)
    6. CROUS (logement étudiant / vie étudiante)
    7. Métier (profession / devenir / que fait un X)
    """
    if not question or not question.strip():
        return None

    norm = _strip_accents(question.lower())

    if any(p.search(norm) for p in _PATTERNS_DOMAIN_APEC):
        return DOMAIN_HINT_APEC
    if any(p.search(norm) for p in _PATTERNS_DOMAIN_INSEE_SALAIRE):
        return DOMAIN_HINT_INSEE_SALAIRE
    if any(p.search(norm) for p in _PATTERNS_DOMAIN_INSERTION_PRO):
        return DOMAIN_HINT_INSERTION_PRO
    if any(p.search(norm) for p in _PATTERNS_DOMAIN_COMPETENCES_CERTIF):
        return DOMAIN_HINT_COMPETENCES_CERTIF
    if any(p.search(norm) for p in _PATTERNS_DOMAIN_PARCOURS):
        return DOMAIN_HINT_PARCOURS
    if any(p.search(norm) for p in _PATTERNS_DOMAIN_CROUS):
        return DOMAIN_HINT_CROUS
    if any(p.search(norm) for p in _PATTERNS_DOMAIN_METIER):
        return DOMAIN_HINT_METIER
    return None


def _has_geographic_marker(question_norm: str) -> bool:
    """Detect a French city or region by token match. Uses a closed
    set rather than NER for speed and determinism."""
    tokens = re.findall(r"[a-z][a-z\-]+", question_norm)
    if any(t in _FRENCH_CITIES for t in tokens):
        return True
    for region in _FRENCH_REGIONS:
        if region in question_norm:
            return True
    return False


def classify_intent(question: str) -> str:
    """Return one of the INTENT_* constants for the given question."""
    if not question or not question.strip():
        return INTENT_GENERAL

    norm = _strip_accents(question.lower())

    # Specific patterns first — order matters where intents could
    # overlap (e.g. a comparison between two cities should still be
    # classified as comparaison, not geographic).
    if any(p.search(norm) for p in _PATTERNS_COMPARAISON_NORM):
        return INTENT_COMPARAISON
    if any(p.search(question) for p in _PATTERNS_COMPARAISON_RAW):
        return INTENT_COMPARAISON

    # Realisme: grade mentions and selectivity language are unambiguous.
    if any(p.search(norm) for p in _PATTERNS_REALISME):
        return INTENT_REALISME

    if any(p.search(norm) for p in _PATTERNS_PASSERELLES):
        return INTENT_PASSERELLES

    if any(p.search(norm) for p in _PATTERNS_CONCEPTUAL):
        return INTENT_CONCEPTUAL

    if any(p.search(norm) for p in _PATTERNS_DECOUVERTE):
        return INTENT_DECOUVERTE

    # Geographic last because a city mention inside a comparison or
    # realisme question shouldn't override the more specific intent.
    if _has_geographic_marker(norm):
        return INTENT_GEOGRAPHIC

    return INTENT_GENERAL


def intent_to_config(intent: str) -> IntentConfig:
    """Map an intent class to its retrieval strategy. Unknown intents
    fall back to INTENT_GENERAL so callers never crash on typos."""
    return _CONFIGS.get(intent, _CONFIGS[INTENT_GENERAL])


# --- Tier 2.3 : format guidance injected into the user prompt ---

_FORMAT_GUIDANCE: dict[str, str] = {
    INTENT_COMPARAISON: (
        "Type de question détecté : comparaison. Utilise obligatoirement "
        "un tableau côte-à-côte pour contraster les options, pas un "
        "Plan A/B/C. Termine par une synthèse de 2-3 lignes qui oriente "
        "selon le profil."
    ),
    INTENT_CONCEPTUAL: (
        "Type de question détecté : conceptuelle / définitionnelle. "
        "Réponds de façon didactique et concise (100-200 mots). Pas de "
        "Plan A/B/C, pas de fiches comme exemples — explique le concept, "
        "son fonctionnement, et les cas typiques."
    ),
    INTENT_DECOUVERTE: (
        "Type de question détecté : découverte / exploration. Les fiches "
        "couvrent cyber / data / santé — si la question sort de ces "
        "domaines, sors du corpus et propose en (connaissance générale) "
        "des métiers interdisciplinaires ou au-delà du périmètre actuel. "
        "Ne restreins pas la réponse aux seules fiches disponibles."
    ),
    INTENT_REALISME: (
        "Type de question détecté : réalisme / faisabilité. Sois direct "
        "et cash sur la faisabilité du projet. Appuie-toi sur les taux, "
        "les chiffres, les profils admis. Si l'objectif n'est pas réaliste, "
        "dis-le d'abord, puis propose des alternatives chiffrées."
    ),
    INTENT_GEOGRAPHIC: (
        "Type de question détecté : géographique. Privilégie la proximité "
        "demandée, mais cite au moins 3 villes distinctes si la question "
        "laisse du jeu. Mentionne les distances ou temps de transport "
        "quand pertinent."
    ),
    INTENT_PASSERELLES: (
        "Type de question détecté : passerelles / réorientation. Décris "
        "les chemins intermédiaires étape par étape (Étape 1 → Étape 2 → "
        "Étape 3). Inclus admissions parallèles, VAE/VAP, validation "
        "d'acquis, calendriers clés."
    ),
    INTENT_GENERAL: (
        "Type de question détecté : générale. Structure en Plan A/B/C "
        "condensé (1-2 lignes par plan). Termine par une section "
        "« Attention aux pièges » (1-3 puces)."
    ),
}


def intent_to_format_guidance(intent: str) -> str:
    """Map an intent class to a format hint injected into the user
    prompt. The rules themselves are in SYSTEM_PROMPT — this classifier
    only tells the LLM which rule applies. Unknown intents fall back
    to INTENT_GENERAL."""
    return _FORMAT_GUIDANCE.get(intent, _FORMAT_GUIDANCE[INTENT_GENERAL])
