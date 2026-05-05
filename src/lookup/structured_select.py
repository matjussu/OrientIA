"""SELECT structuré déterministe — Chantier 2 (2026-05-03).

Pour les questions factuelles pointues sur UNE formation nommée, on bypasse
le RAG et on fait un lookup direct sur `formations.json`. Argument démo INRIA :
« les chiffres viennent toujours d'un lookup, jamais d'une génération.
Zéro hallu chiffres par construction. »

## Pipeline

1. `extract_entity_simple(question)` → `Entity(formation_name, ville, niveau)`
   via regex patterns (zero coût LLM, déterministe).
2. `lookup_formation(entity, fiches)` → fuzzy match `rapidfuzz` ≥ FUZZY_THRESHOLD.
   Sous le seuil → None → fallback RAG.
3. `extract_field(fiche, field_key)` → SELECT avec INVALID_VALUES guard.
   Si valeur invalide (None, 0, "-", "N/A") → None → fallback unifié.
4. `format_select_response(fiche, field, value)` → templater déterministe
   « Le taux d'accès Parcoursup 2025 de [formation] est [X]%. Source: [URL]. »

## Garde-fous expert

- **Seuil de confiance ≥85** : aucun SELECT à confiance basse (sinon
  hallu déterministe « le taux de la formation X est Y » alors que X
  n'est pas la vraie formation visée).
- **INVALID_VALUES guard** : champ présent mais valeur 0/N/A/None →
  fallback unifié (sinon « taux EFREI Bordeaux est 0% » bug visible démo).
- **Multi-match ambigu** : si scores ≥85 sur multiple fiches avec ex-aequo
  proches → demander précision à l'utilisateur (« Plusieurs formations
  matchent : EFREI Paris ou EFREI Bordeaux ? »).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from rapidfuzz import fuzz, process

from src.rag.fallback_response import format_unknown_response


def _strip_accents(s: str) -> str:
    """Normalisation accents pour matching robuste."""
    return "".join(
        c for c in unicodedata.normalize("NFKD", s)
        if not unicodedata.combining(c)
    )


# Seuil de confiance fuzzy match. Sous ce score, on refuse le SELECT
# pour ne pas créer une hallu déterministe (« taux de Bachelor cyber
# est X » alors que le match était sur le mauvais Bachelor cyber).
FUZZY_THRESHOLD = 85

# Si plusieurs fiches matchent ≥ FUZZY_THRESHOLD avec un écart < ce
# nombre de points, on considère le match ambigu → demande précision.
AMBIGUITY_DELTA = 5

# Critique expert #4b (2026-05-03) — mots discriminateurs métier qui DOIVENT
# matcher dans la fiche cible si présents dans la query, sinon match suspect.
# Ex : « prépa commerciales Henri IV » ne doit PAS matcher la prépa A/L
# (lettres) d'Henri IV juste parce que « prépa » + « Henri IV » overlap —
# « commerciales » est un discriminateur qui doit aussi être dans la fiche.
# Liste conservatrice (pas exhaustive) — couvre les cas critiques observés
# en prépa CPGE, séries L/ES/S, options de master, spécialités d'ingénieur.
_DISCRIMINATORS = frozenset({
    # Voies CPGE
    "commercial", "commerciale", "commerciales", "ec", "ecg", "ect", "ecs", "ece",
    "scientifique", "scientifiques", "mp", "pc", "psi", "mpsi", "pcsi", "bcpst", "tpc",
    "litteraire", "litteraires", "littéraire", "littéraires", "al", "a/l", "bl", "b/l",
    "khagne", "hypokhagne",
    # Spécialités ingé / domaines majeurs
    "informatique", "info", "cybersecurite", "cybersécurité", "cyber", "data",
    "mecanique", "mécanique", "civil", "electronique", "électronique", "biotech",
    "biologique", "chimie", "chimique", "energie", "énergie", "telecoms", "télécoms",
    "reseau", "réseau", "reseaux", "réseaux", "aero", "aéro", "aerospatial", "aérospatial",
    # Options de droit
    "international", "internationale", "internationales", "europeen", "européen",
    "europeenne", "européenne", "affaires", "penal", "pénal", "fiscal", "civil",
    "social", "notarial", "constitutionnel", "administratif",
    # Spécialités santé / paramédical
    "kine", "kiné", "kinesitherapie", "kinésithérapie", "infirmier", "infirmiere",
    "infirmière", "psychologue", "orthophonie", "orthophoniste", "podologue",
})


def _query_discriminators_match_fiche(query_tokens: list[str], fiche_text: str) -> bool:
    """Garde anti-faux-positifs : si la query contient un mot discriminateur
    métier (commercial, MP, kiné, international, etc.), ce mot DOIT être
    présent dans le texte de la fiche.

    Match accepté si :
      - exact match d'un mot fiche, OU
      - préfixe match (discriminator est préfixe d'un mot fiche, ou inverse)
        ex : « cyber » matche « cybersécurité » via préfixe.

    Sinon le fuzzy match est trompeur (mauvais sous-domaine matché par
    overlap accidentel — ex « prépa commerciales » → « prépa A/L »).
    """
    query_discriminators = {t.lower() for t in query_tokens if t.lower() in _DISCRIMINATORS}
    if not query_discriminators:
        return True
    fiche_words = set(re.findall(r"\w+", fiche_text.lower()))

    def _matches(disc: str) -> bool:
        if disc in fiche_words:
            return True
        # Préfixe / inclusion (cyber ↔ cybersécurité, kiné ↔ kinésithérapie)
        for w in fiche_words:
            if len(disc) >= 3 and (w.startswith(disc) or disc.startswith(w)):
                return True
        return False

    return all(_matches(d) for d in query_discriminators)

# Valeurs considérées comme invalides — déclenchent le fallback unifié.
# Le set est conservatif : 0 et -1 sont marqueurs Parcoursup pour
# « capacité fermée » ou « non renseigné », pas une vraie valeur.
INVALID_VALUES: frozenset = frozenset({None, "", "N/A", "n/a", "-", "non renseigné", "non renseignee", 0, -1, 0.0})


@dataclass(frozen=True)
class Entity:
    """Entité extraite d'une question factual_pointed.

    Au moins UNE des trois (formation_name, ville, niveau) doit être
    non-None pour avoir une chance de matcher. La combinaison améliore
    le fuzzy score (e.g. "EFREI Bordeaux" > juste "EFREI").
    """

    formation_name: str | None = None
    ville: str | None = None
    niveau: str | None = None

    def is_empty(self) -> bool:
        return not (self.formation_name or self.ville or self.niveau)

    def to_query_string(self) -> str:
        """Concatène les composantes pour le fuzzy match (lowercase, trim)."""
        parts = [p for p in (self.formation_name, self.ville, self.niveau) if p]
        return " ".join(p.strip().lower() for p in parts)


@dataclass(frozen=True)
class SelectResult:
    """Résultat d'un SELECT — soit un fait formaté, soit un fallback."""

    text: str
    via_select: bool       # True = SELECT déterministe, False = fallback unifié
    matched_fiche_id: str | None = None
    fuzzy_score: float | None = None
    field_key: str | None = None  # ex: "taux_acces_parcoursup_2025"
    reason: str | None = None     # 'select_no_entity' | 'select_no_match' | 'select_invalid_value' | 'select_ambiguous'


# ──────────────────────── Field key detection ────────────────────────

# Mapping pattern question → field key dans la fiche
SELECT_FIELD_PATTERNS: list[tuple[re.Pattern[str], str, str]] = [
    # (pattern, field_key, label_humain)
    (
        re.compile(r"\btaux\s+d['e]\s*acces", re.IGNORECASE),
        "taux_acces_parcoursup_2025",
        "taux d'accès Parcoursup 2025",
    ),
    (
        re.compile(r"\b(?:nombre\s+de\s+)?places?\s+(?:disponibles?\s+)?(?:à|en|dans|de|d['e]\s*)", re.IGNORECASE),
        "nombre_places",
        "nombre de places",
    ),
    (
        re.compile(r"\bcombien\s+de\s+places?", re.IGNORECASE),
        "nombre_places",
        "nombre de places",
    ),
    (
        re.compile(r"\bselectivit", re.IGNORECASE),
        "taux_acces_parcoursup_2025",
        "sélectivité (taux d'accès Parcoursup 2025)",
    ),
    (
        re.compile(r"\bsalaire\s+(?:median|moyen|annuel|net|brut|de\s+(?:sortie|debut|embauche))", re.IGNORECASE),
        "insertion_pro.salaire_median_embauche",
        "salaire médian à l'embauche",
    ),
    # Critique expert #4a (2026-05-03) — « Quel salaire après LEA ? » sans
    # qualificatif (médian/moyen). Pattern complémentaire moins strict.
    (
        re.compile(r"\b(?:quel\s+)?salaire\s+(?:apres|post|en\s+sortie\s+de|au\s+sortir)", re.IGNORECASE),
        "insertion_pro.salaire_median_embauche",
        "salaire à la sortie",
    ),
    (
        re.compile(r"\bcombien\s+gagne", re.IGNORECASE),
        "insertion_pro.salaire_median_embauche",
        "rémunération",
    ),
    (
        re.compile(r"\btaux\s+d['e]\s*emploi\s+(?:a|au\s+bout\s+de\s+)?\s*(?:3\s+ans?|3ans?)", re.IGNORECASE),
        "insertion_pro.taux_emploi_3ans",
        "taux d'emploi à 3 ans",
    ),
    (
        re.compile(r"\btaux\s+d['e]\s*emploi\s+(?:a|au\s+bout\s+de\s+)?\s*(?:6\s+ans?|6ans?)", re.IGNORECASE),
        "insertion_pro.taux_emploi_6ans",
        "taux d'emploi à 6 ans",
    ),
    (
        re.compile(r"\btaux\s+(?:de\s+)?cdi", re.IGNORECASE),
        "insertion_pro.taux_cdi",
        "taux de CDI à l'embauche",
    ),
    # Critique expert #4a (2026-05-03) — frais / coût / scolarité.
    # Champ rarement présent dans formations.json (~0.7% sample) → SELECT
    # tombera en fallback unifié pour la majorité, c'est ce qu'on veut :
    # mieux qu'une hallu RAG (« 8000 €/an » inventé pour une fac publique).
    (
        re.compile(r"\bcombien\s+(?:ca\s+|cela\s+)?co[uû]te", re.IGNORECASE),
        "frais_annuels",
        "frais de scolarité",
    ),
    (
        re.compile(r"\b(?:co[uû]t|frais|tarif)\s+(?:de\s+(?:la\s+|l['e]\s*))?(?:formation|scolarit|inscription|annuel)", re.IGNORECASE),
        "frais_annuels",
        "frais de scolarité",
    ),
    (
        re.compile(r"\b(?:quel|quels)\s+(?:sont\s+(?:les\s+)?)?frais", re.IGNORECASE),
        "frais_annuels",
        "frais de scolarité",
    ),
    # Durée de formation (champ `duree` présent dans ~2% des fiches).
    # Matche « durée du BUT », « durée de la formation », « combien d'années dure ».
    (
        re.compile(r"\bdur[ée]e\s+(?:de\s+(?:la\s+|l['e]\s*)|du\s+|des\s+|d['e]\s*)?(?:formation|cursus|etudes?|but|bts|licence|master|bachelor|prepa|prépa)", re.IGNORECASE),
        "duree",
        "durée de la formation",
    ),
    (
        re.compile(r"\bcombien\s+(?:de\s+|d['e]\s*)?(?:temps|annees?|ans)\s+dure", re.IGNORECASE),
        "duree",
        "durée de la formation",
    ),
    (
        re.compile(r"\bcombien\s+(?:de\s+|d['e]\s*)annees?\b", re.IGNORECASE),
        "duree",
        "durée de la formation",
    ),
]


def detect_field_key(question: str) -> tuple[str, str] | None:
    """Détecte quel champ est demandé.

    Strip accents avant matching pour robustesse (sélectivité → selectivite,
    accès → acces, etc. — les regex sont écrites sans accents).

    Returns:
        Tuple (field_key, label_humain) ou None si aucun pattern ne match.
    """
    norm = _strip_accents(question)
    for pattern, field_key, label in SELECT_FIELD_PATTERNS:
        if pattern.search(norm):
            return field_key, label
    return None


# ──────────────────────── Entity extraction (regex-based, no LLM) ────────────────────────

# Mots-outils à filtrer pour ne pas polluer le fuzzy match.
# Inclut les mots-clés de field detection (taux, places, salaire, etc.) pour
# éviter qu'ils polluent le score de match contre les noms de formations.
_STOPWORDS = frozenset({
    # articles, prépositions, pronoms basiques
    "le", "la", "les", "un", "une", "des", "du", "de", "d", "à", "a",
    "en", "et", "ou", "est", "sont", "que", "qui", "quoi", "comment",
    "pour", "par", "sur", "dans", "avec", "sans", "quel", "quelle",
    "quels", "quelles", "combien", "année", "annees", "ans", "ce", "cette",
    "ces", "ma", "mon", "mes", "ta", "ton", "tes", "sa", "son", "ses",
    "il", "elle", "on", "nous", "vous", "ils", "elles", "je", "tu",
    "moi", "toi", "lui", "leur", "leurs", "y", "se", "ne", "pas", "plus",
    "moins", "très", "tres", "trop", "bien", "mieux", "mal", "fort",
    "ai", "ai-je", "as-tu", "a-t-il", "avons", "avez", "ont",
    "suis", "es", "est-ce", "sommes", "êtes", "etes",
    "veux", "voulez", "voudrais", "souhaite", "souhaitez",
    "savoir", "connaitre", "connaître", "voir", "trouver",
    "formation", "formations", "ecole", "ecoles", "université", "universite",
    "fac", "diplome", "cursus",
    # mots-clés de field detection (à filtrer pour ne pas polluer fuzzy)
    "taux", "accès", "acces", "selectivite", "sélectivité", "selectivité",
    "places", "place", "candidats", "voeux", "vœux", "inscrits",
    "salaire", "salaires", "rémunération", "remuneration", "gagne",
    "frais", "coût", "cout", "tarif", "cotisation",
    "emploi", "insertion", "cdi", "réussite", "reussite", "admission",
    "median", "médian", "moyen", "moyenne", "annuel", "annuelle", "net",
    "brut",
})

# Liste des villes courantes (réutilise la liste intent.py)
from src.rag.intent import _FRENCH_CITIES


def extract_entity_simple(question: str) -> Entity:
    """Extraction d'entité regex-based (zero LLM, déterministe).

    Stratégie :
    1. Tokenize la question, filtre stopwords + mots courts.
    2. Détecte une ville française (closed set _FRENCH_CITIES).
    3. Détecte un niveau (BTS, BUT, Licence, Master, Bachelor, etc.).
    4. Le reste = candidate formation_name (joined).

    Returns:
        Entity. is_empty() == True si rien d'utile détecté.
    """
    if not question or not question.strip():
        return Entity()

    # Tokens (préserve majuscules pour acronymes types EFREI, EPITA)
    # Apostrophe NON incluse dans le pattern : "d'accès" → ["d", "accès"]
    # pour permettre le filtrage stopwords mot par mot. Tirets conservés
    # pour noms composés ("Saint-Étienne").
    raw_tokens = re.findall(r"[a-zA-Zéèêàùôîçâïü0-9][a-zA-Zéèêàùôîçâïü0-9\-]*", question)

    ville = None
    niveau = None
    name_tokens: list[str] = []
    for tok in raw_tokens:
        low = tok.lower()
        if low in _STOPWORDS:
            continue
        if low in _FRENCH_CITIES:
            ville = ville or tok  # garde le premier match
            continue
        # Niveau patterns
        if re.match(r"^(bts|but|dut|licence|master|bachelor|prépa|prepa|cap|deust|deaes|deamp|pass|las)$", low):
            niveau = niveau or tok.upper()
            continue
        if re.match(r"^bac\+?\d$", low):
            niveau = niveau or tok
            continue
        # Sinon = candidate formation name
        if len(tok) > 1:
            name_tokens.append(tok)

    formation_name = " ".join(name_tokens).strip() if name_tokens else None
    return Entity(formation_name=formation_name, ville=ville, niveau=niveau)


# ──────────────────────── Lookup formations ────────────────────────


def _fiche_searchable_text(fiche: dict) -> str:
    """Construit la string concatenée à matcher pour le fuzzy."""
    parts = []
    for key in ("nom", "etablissement", "ville", "niveau"):
        v = fiche.get(key)
        if v:
            parts.append(str(v))
    return " ".join(parts).lower()


def lookup_formation(entity: Entity, fiches: list[dict]) -> tuple[dict | None, float, bool]:
    """Fuzzy match entity → fiche.

    Critique expert #4b (2026-05-03) : ajout d'une garde discriminateurs
    métier — si la query contient un mot discriminateur (commercial, MP,
    kiné, international, etc.) qui n'est PAS dans le top match, on rejette
    le match (mieux qu'un mauvais SELECT confiant).

    Returns:
        (best_fiche, score, ambiguous_flag)
        - best_fiche: la fiche matchée (ou None si score < FUZZY_THRESHOLD
          OU discriminateur query absent)
        - score: float 0-100
        - ambiguous_flag: True si plusieurs fiches matchent ≥ FUZZY_THRESHOLD
          avec un écart < AMBIGUITY_DELTA (besoin de précision)
    """
    if entity.is_empty() or not fiches:
        return None, 0.0, False

    query = entity.to_query_string()
    if not query:
        return None, 0.0, False

    # Tokens query (sans stopwords) pour la garde discriminateur
    query_tokens = [t for t in re.findall(r"\w+", query) if t.lower() not in _STOPWORDS]

    # rapidfuzz.process.extract pour les top matches
    candidates = [(i, _fiche_searchable_text(f)) for i, f in enumerate(fiches)]

    # Score chaque candidate avec WRatio (robuste aux variations)
    results = process.extract(
        query,
        {i: text for i, text in candidates},
        scorer=fuzz.WRatio,
        limit=5,
    )
    # results = [(text, score, key), ...] format rapidfuzz
    if not results:
        return None, 0.0, False

    top_text, top_score, top_idx = results[0]
    if top_score < FUZZY_THRESHOLD:
        return None, top_score, False

    # GARDE DISCRIMINATEUR (critique expert #4b) : si la query contient un mot
    # discriminateur métier qui n'est PAS dans la fiche top → rejeter, mieux
    # qu'un faux positif (ex « prépa commerciales » → « prépa A/L »).
    if not _query_discriminators_match_fiche(query_tokens, top_text):
        # Tenter de trouver un match parmi les top-5 qui satisfait le discriminateur
        for text, score, idx in results[1:]:
            if score < FUZZY_THRESHOLD:
                break
            if _query_discriminators_match_fiche(query_tokens, text):
                return fiches[idx], score, False
        # Aucun candidat ne matche le discriminateur → reject (None, conservatif)
        return None, top_score, False

    # Détection ambiguité : 2e match aussi ≥ FUZZY_THRESHOLD avec score proche
    ambiguous = False
    if len(results) > 1:
        _, second_score, _ = results[1]
        if second_score >= FUZZY_THRESHOLD and (top_score - second_score) < AMBIGUITY_DELTA:
            ambiguous = True

    return fiches[top_idx], top_score, ambiguous


# ──────────────────────── Field extraction with INVALID_VALUES guard ────────────────────────


def is_valid_field_value(value: Any) -> bool:
    """Garde de validité — INVALID_VALUES expansion + handling NaN.

    Évite catastrophe démo : « Le taux d'accès EFREI Bordeaux est 0% »
    quand le champ est présent mais vide dans les fiches mergées.
    """
    if value in INVALID_VALUES:
        return False
    # NaN check pour les float
    if isinstance(value, float):
        import math
        if math.isnan(value) or math.isinf(value):
            return False
    # String "0", "0.0" considérée invalide (cas edge Parcoursup)
    if isinstance(value, str):
        s = value.strip().lower()
        if s in ("0", "0.0", "0%", ""):
            return False
    return True


def extract_field(fiche: dict, field_key: str) -> Any | None:
    """Extrait field_key d'une fiche, support du dotted path (e.g. 'insertion_pro.taux_emploi_3ans').

    Returns:
        La valeur si valide, sinon None (déclenche le fallback unifié).
    """
    if not fiche or not field_key:
        return None

    # Support dotted path : insertion_pro.taux_emploi_3ans
    keys = field_key.split(".")
    current: Any = fiche
    for k in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(k)
        if current is None:
            return None

    if not is_valid_field_value(current):
        return None

    return current


# ──────────────────────── Response templater ────────────────────────


def _format_value(value: Any, field_key: str) -> str:
    """Formate la valeur selon son type (taux %, salaire €, places nombre)."""
    if "taux" in field_key or "selectivit" in field_key:
        # Taux Parcoursup : float déjà en %, ou ratio 0-1
        try:
            f = float(value)
            if 0.0 <= f <= 1.0:
                return f"{int(round(f * 100))} %"
            return f"{int(round(f))} %"
        except (ValueError, TypeError):
            return str(value)
    if "salaire" in field_key:
        try:
            return f"{int(round(float(value)))} €"
        except (ValueError, TypeError):
            return str(value)
    if field_key in ("nombre_places",):
        try:
            return f"{int(value)} places"
        except (ValueError, TypeError):
            return str(value)
    return str(value)


def format_select_response(
    fiche: dict,
    field_key: str,
    field_label: str,
    value: Any,
) -> str:
    """Templater déterministe pour la réponse SELECT.

    Format : « Le [label] de [formation] (à [ville]) est [value formatée]. Source: [URL]. »
    """
    nom = (fiche.get("nom") or "").strip()
    etab = (fiche.get("etablissement") or "").strip()
    ville = (fiche.get("ville") or "").strip()

    # Identifier la formation pour l'utilisateur (lisible)
    formation_id = nom
    if etab and etab != nom:
        formation_id = f"{nom} ({etab})" if nom else etab
    if ville:
        formation_id = f"{formation_id} à {ville}"

    formatted_value = _format_value(value, field_key)

    # URL source : préférence à lien_form_psup, fallback URL ONISEP
    url = (
        fiche.get("lien_form_psup")
        or fiche.get("url_onisep")
        or fiche.get("url")
        or ""
    )
    source_suffix = ""
    if url:
        source_suffix = f" Source : [fiche officielle Parcoursup]({url})."
    elif fiche.get("source"):
        source_suffix = f" (Source : {fiche.get('source')})."

    return (
        f"Le {field_label} de **{formation_id}** est **{formatted_value}**.{source_suffix}"
    )


# ──────────────────────── End-to-end orchestrator ────────────────────────


def try_select_or_none(
    question: str,
    fiches: list[dict],
) -> SelectResult | None:
    """Tentative de SELECT déterministe end-to-end.

    Returns:
        SelectResult avec via_select=True si le SELECT a réussi.
        SelectResult avec via_select=False (fallback) si :
          - pas d'entité reconnue (`reason='select_no_entity'`)
          - pas de field key détecté → return None (le router gère)
          - fuzzy < FUZZY_THRESHOLD (`reason='select_no_match'`)
          - multi-match ambigu (`reason='select_ambiguous'`)
          - field absent/invalide dans la fiche matchée (`reason='select_invalid_value'`)
        None si le pattern ne matche pas du tout (le router fallback RAG).
    """
    # 1. Field key detection
    field_info = detect_field_key(question)
    if field_info is None:
        return None  # pas une question SELECT — laisser le router décider
    field_key, field_label = field_info

    # 2. Entity extraction
    entity = extract_entity_simple(question)
    if entity.is_empty():
        return SelectResult(
            text=format_unknown_response(missing_field=field_label),
            via_select=False,
            field_key=field_key,
            reason="select_no_entity",
        )

    # 3. Fuzzy lookup
    fiche, score, ambiguous = lookup_formation(entity, fiches)
    if fiche is None:
        return SelectResult(
            text=format_unknown_response(
                missing_field=f"{field_label} pour la formation que tu décris",
                near_match=(
                    f"Je n'ai pas trouvé de formation correspondant suffisamment "
                    f"précisément à « {entity.to_query_string()} » dans mes sources "
                    f"(meilleur score : {score:.0f}/100, seuil requis : {FUZZY_THRESHOLD})."
                ),
            ),
            via_select=False,
            field_key=field_key,
            fuzzy_score=score,
            reason="select_no_match",
        )

    if ambiguous:
        return SelectResult(
            text=format_unknown_response(
                missing_field=field_label,
                near_match=(
                    f"Plusieurs formations matchent ta demande. Précise davantage "
                    f"(ville, établissement, niveau) pour que je puisse te donner "
                    f"le chiffre exact."
                ),
                suggestion=None,  # pas de redirection externe — précision interne demandée
            ),
            via_select=False,
            matched_fiche_id=str(fiche.get("id") or fiche.get("nom") or ""),
            fuzzy_score=score,
            field_key=field_key,
            reason="select_ambiguous",
        )

    # 4. Field extraction avec INVALID_VALUES guard
    value = extract_field(fiche, field_key)
    if value is None:
        return SelectResult(
            text=format_unknown_response(
                missing_field=f"{field_label} pour cette formation",
                near_match=(
                    f"J'ai trouvé la fiche **{fiche.get('nom') or '?'}** "
                    f"mais le champ « {field_label} » n'est pas renseigné "
                    f"dans la source."
                ),
            ),
            via_select=False,
            matched_fiche_id=str(fiche.get("id") or fiche.get("nom") or ""),
            fuzzy_score=score,
            field_key=field_key,
            reason="select_invalid_value",
        )

    # 5. SUCCESS — réponse déterministe
    return SelectResult(
        text=format_select_response(fiche, field_key, field_label, value),
        via_select=True,
        matched_fiche_id=str(fiche.get("id") or fiche.get("nom") or ""),
        fuzzy_score=score,
        field_key=field_key,
        reason=None,
    )
