"""Backstop B soft — annotation des chiffres non-sourcés.

Pipeline : `LLM v5b → soft_annotator → réponse annotée`. Le module ne
remplace AUCUN contenu (option B soft validée Matteo 2026-05-01) — il
ajoute des balises HTML autour des taux/salaires non vérifiables et
ajoute un disclaimer global systématique en pied.

## Spec ordre 2026-05-01-1334 Sous-étape 1

- Cibler EXCLUSIVEMENT :
    - Taux : `\\d+(?:[.,]\\d+)?\\s*%` (sélectivité, admission, emploi, etc.)
    - Prix/salaires : `\\d+(?:[.,]\\d+)?\\s*(?:€|k€|euros?)` (frais, salaires)
- Ne PAS flagger les durées : `5 ans`, `3h`, `2 mois`, `6 semaines`, etc.
- Contexte adjacent obligatoire dans fenêtre ±50 caractères :
    sélectivité, salaire, taux, frais, admission, emploi, réussite,
    insertion (mot-clé statistique/financier requis)
- Cross-ref corpus avec tolérance ±0.5pp pour pourcentages, ±5% pour
    montants. Si chiffre + contexte trouvés dans le corpus → pas
    d'annotation. Si absents OU divergents au-delà tolérance → annoter.
- Disclaimer global SYSTÉMATIQUE (pas conditionnel) en pied de chaque
    réponse.

## Format sortie HTML

```html
<span class="stat-unverified" data-tooltip="Information statistique
générée. Privilégiez toujours la consultation de la source officielle
citée en bas de page.">42%</span>
```

## API publique

- `CorpusFactIndex.from_unified_json(path)` — charge l'index depuis
    `data/processed/formations_unified.json`
- `annotate_response(answer, corpus_index)` — pipeline complet
- `DISCLAIMER` — chaîne disclaimer ajoutée systématiquement
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


# ---------- Constantes ----------

DISCLAIMER = (
    "\n\n---\n\n_Les données chiffrées (coûts, taux d'admission) peuvent "
    "évoluer d'une année sur l'autre. Pense à les confirmer sur les sites "
    "des écoles._"
)

TOOLTIP_TEXT = (
    "Information statistique générée. Privilégiez toujours la consultation "
    "de la source officielle citée en bas de page."
)

# Mots-clés contexte stat/financier (filtre #1 — ne flagger que ces domaines).
CONTEXT_KEYWORDS_STAT_FIN = {
    "sélectivité", "selectivite",
    "salaire", "salaires",
    "taux",
    "frais",
    "admission", "admis", "admises", "admise",
    "emploi", "emplois",
    "réussite", "reussite",
    "insertion",
    # Élargissements naturels conservés conservatives :
    "acceptation", "places",
    "coût", "cout",
}

# Tolérances cross-ref corpus.
TOLERANCE_PCT_POINTS = 0.5     # 38.5 % matche 38 % ± 0.5 pp
TOLERANCE_AMOUNT_RATIO = 0.05  # 5 % d'écart relatif sur montants

# Régex chiffres ciblés.
RE_PCT = re.compile(r"\b(\d+(?:[.,]\d+)?)\s*%", re.IGNORECASE)
RE_AMOUNT = re.compile(
    r"\b(\d+(?:[.,]\d+)?)\s*(€|k€|euros?)",
    re.IGNORECASE,
)

# Régex durées explicites — exclues même si suivies de % ou €. Elles
# n'apparaissent pas dans la regex chiffre mais on les énumère ici pour
# documentation et test.
DURATION_PATTERNS = [
    r"\d+\s*(?:ans?|mois|semaines?|heures?|h\b|j\b|jours?|min\b)",
]

# Fenêtre contextuelle ±50 caractères autour du match.
CONTEXT_WINDOW_CHARS = 50


# ---------- Helpers ----------

def _normalize(text: str) -> str:
    """Lowercase + strip diacritics — pour matching contexte keyword."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    no_diac = "".join(c for c in nfkd if not unicodedata.combining(c))
    return no_diac.lower()


def _parse_value(num_str: str) -> float:
    """`'38,5'` → `38.5`. Tolère virgule décimale française."""
    return float(num_str.replace(",", "."))


def _has_context_keyword(window_text: str) -> bool:
    """True si le texte contient au moins un mot-clé stat/financier."""
    norm = _normalize(window_text)
    norm_keywords = {_normalize(k) for k in CONTEXT_KEYWORDS_STAT_FIN}
    return any(kw in norm for kw in norm_keywords)


def _extract_context_window(answer: str, start: int, end: int) -> str:
    """Renvoie ±CONTEXT_WINDOW_CHARS autour de [start:end] dans `answer`."""
    lo = max(0, start - CONTEXT_WINDOW_CHARS)
    hi = min(len(answer), end + CONTEXT_WINDOW_CHARS)
    return answer[lo:hi]


# ---------- Index corpus ----------

@dataclass(frozen=True)
class CorpusFact:
    """Un fait numérique du corpus — value + tag + context entities."""
    value: float
    fact_type: str  # "pct" | "amount"
    entity_keywords: frozenset[str]


class CorpusFactIndex:
    """Index plat des faits numériques du corpus formations_unified.

    Pas d'optimisation indexée fancy : 55k formations × 4 fields ≈ 200k
    entrées maximum, scan O(N) par lookup reste ~1ms. Pré-mature optim
    évitée jusqu'à preuve d'un goulot.
    """

    def __init__(self, facts: list[CorpusFact]):
        self._facts = facts

    @classmethod
    def from_unified_json(cls, path: Path | str) -> "CorpusFactIndex":
        """Charge l'index depuis `data/processed/formations_unified.json`.

        Extrait per-formation :
        - taux_acces_parcoursup_2025 → fact_type "pct"
        - insertion_pro.taux_emploi_3ans → "pct" (× 100 si stocké en
            décimal 0-1)
        - insertion_pro.taux_emploi_6ans → "pct"
        - insertion_pro.taux_cdi → "pct"
        - insertion_pro.salaire_median_embauche → "amount" (€)

        Le `entity_keywords` agrège nom + établissement + ville +
        domaine pour permettre matching contextuel large.
        """
        path = Path(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        facts: list[CorpusFact] = []
        for entry in data:
            kws = cls._extract_entity_keywords(entry)
            if not kws:
                continue

            # Taux d'accès Parcoursup (pct)
            taux = entry.get("taux_acces_parcoursup_2025")
            if isinstance(taux, (int, float)):
                facts.append(CorpusFact(float(taux), "pct", kws))

            # Insertion pro — convertit décimal 0-1 → pourcentage si
            # nécessaire.
            insertion = entry.get("insertion_pro") or {}
            for key in ("taux_emploi_3ans", "taux_emploi_6ans", "taux_cdi"):
                v = insertion.get(key)
                if isinstance(v, (int, float)):
                    pct = float(v) * 100 if 0 <= v <= 1 else float(v)
                    facts.append(CorpusFact(pct, "pct", kws))

            # Salaire (montant €)
            salaire = insertion.get("salaire_median_embauche")
            if isinstance(salaire, (int, float)) and salaire > 0:
                facts.append(CorpusFact(float(salaire), "amount", kws))

        return cls(facts)

    @staticmethod
    def _extract_entity_keywords(entry: dict) -> frozenset[str]:
        """Token bag depuis nom + établissement + ville + domaine. Filtre
        stopwords courts (≤2 caractères) pour éviter les matches
        triviaux ('a', 'la')."""
        fields = ("nom", "etablissement", "ville", "domaine")
        tokens: set[str] = set()
        for f in fields:
            val = entry.get(f) or ""
            if not isinstance(val, str):
                continue
            norm = _normalize(val)
            for tok in re.split(r"[^a-z0-9]+", norm):
                if len(tok) >= 3:
                    tokens.add(tok)
        return frozenset(tokens)

    def is_supported(
        self,
        value: float,
        fact_type: str,
        context_window: str,
    ) -> bool:
        """True si (value, fact_type) match au moins un fact corpus
        avec ≥ 1 entity keyword présent dans la fenêtre contextuelle.

        Tolérance : ±TOLERANCE_PCT_POINTS pour pct, ±TOLERANCE_AMOUNT_RATIO
        pour amount.
        """
        if fact_type == "pct":
            tol = TOLERANCE_PCT_POINTS
        elif fact_type == "amount":
            tol = max(value * TOLERANCE_AMOUNT_RATIO, 1.0)
        else:
            return False

        norm_window = _normalize(context_window)
        for fact in self._facts:
            if fact.fact_type != fact_type:
                continue
            if abs(fact.value - value) > tol:
                continue
            # Value match — vérifier contexte entité
            if any(kw in norm_window for kw in fact.entity_keywords):
                return True
        return False

    def __len__(self) -> int:
        return len(self._facts)


# ---------- Annotation pipeline ----------

@dataclass(frozen=True)
class _CandidateMatch:
    start: int
    end: int
    raw: str
    value: float
    fact_type: str  # "pct" | "amount"


def _find_candidates(answer: str) -> list[_CandidateMatch]:
    """Repère tous les chiffres pct/amount dans la réponse.

    Filtre #1 : durée explicite (e.g. '5 ans', '6 semaines') jamais
    matchée par RE_PCT/RE_AMOUNT, donc rien à exclure ici. Mais on
    documente le test négatif.
    """
    candidates: list[_CandidateMatch] = []

    for m in RE_PCT.finditer(answer):
        candidates.append(_CandidateMatch(
            start=m.start(),
            end=m.end(),
            raw=m.group(0),
            value=_parse_value(m.group(1)),
            fact_type="pct",
        ))

    for m in RE_AMOUNT.finditer(answer):
        unit = m.group(2).lower()
        # Convertir k€ en € pour la cross-ref unifiée.
        value = _parse_value(m.group(1))
        if unit.startswith("k"):
            value *= 1000
        candidates.append(_CandidateMatch(
            start=m.start(),
            end=m.end(),
            raw=m.group(0),
            value=value,
            fact_type="amount",
        ))

    candidates.sort(key=lambda c: c.start)
    return candidates


def _wrap_match(raw: str) -> str:
    return (
        f'<span class="stat-unverified" data-tooltip="{TOOLTIP_TEXT}">'
        f'{raw}</span>'
    )


def annotate_response(
    answer: str,
    corpus_index: CorpusFactIndex,
) -> str:
    """Annote les chiffres non-sourcés + ajoute le disclaimer.

    Pipeline :
    1. Trouver candidats (taux % ou montants €/k€/euros)
    2. Pour chaque candidat : vérifier mot-clé contexte stat/financier
        dans ±50 chars. Si absent → pas annoté (filtre #1).
    3. Si contexte présent : check corpus avec tolérance. Si match → pas
        annoté. Si absent / divergent → wrap dans `<span class="...">`.
    4. Append `DISCLAIMER` à la fin de la réponse (systématique).

    Returns : la réponse augmentée des balises et du disclaimer.
    """
    if not answer:
        return DISCLAIMER.lstrip("\n")  # cas dégénéré : disclaimer seul

    candidates = _find_candidates(answer)
    if not candidates:
        return answer + DISCLAIMER

    # Construire la sortie en parcourant les candidats du DERNIER au
    # PREMIER pour ne pas invalider les offsets pendant les insertions.
    out = answer
    for cand in reversed(candidates):
        window = _extract_context_window(answer, cand.start, cand.end)
        if not _has_context_keyword(window):
            # Filtre #1 — pas de mot-clé stat/financier dans ±50 chars.
            continue
        if corpus_index.is_supported(cand.value, cand.fact_type, window):
            # Filtre #2 — chiffre + contexte trouvés dans corpus → pas
            # d'annotation.
            continue
        # Sinon — annoter.
        out = out[:cand.start] + _wrap_match(cand.raw) + out[cand.end:]

    return out + DISCLAIMER
