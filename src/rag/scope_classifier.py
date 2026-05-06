"""ScopeClassifier — gating amont du pipeline OrientIA.

Décide AVANT le retrieval/generation si une question doit être traitée par
le pipeline RAG (`in_scope`) ou court-circuitée par une réponse pré-écrite
(`out_of_scope` ou `urgent`).

3 catégories :

- **in_scope** : toute question d'orientation académique ou professionnelle
  post-bac (formations, métiers, parcours, choix, réorientation, financement,
  insertion, comparaison écoles, etc.). Inclut les domaines mal couverts par
  le corpus actuel (santé, droit, archi, vétérinaire) — c'est le pipeline RAG
  qui décidera honnêtement de répondre ou de fallback.

- **out_of_scope** : question NON liée à l'orientation (devoirs scolaires,
  cuisine, blagues, météo, sport en tant que loisir, code/dev hors orientation,
  questions personnelles non liées). Réponse pré-écrite qui réoriente vers
  l'orientation post-bac.

- **urgent** : signal de mal-être grave, idéations suicidaires, violences
  subies, harcèlement intense, détresse psychologique aiguë. Réponse imposée
  qui (a) reconnaît la souffrance, (b) redirige vers les numéros d'urgence
  appropriés (3114 prévention suicide, 3919 violences femmes, 119 enfance
  maltraitance, 30 18 SOS Amitié). NE TENTE PAS de "répondre" — ce n'est pas
  notre rôle.

Stratégie :
1. Pré-filter regex pour les signaux clairs urgent (mots-clés forts) — gain
   latence + sécurité (pas de risque LLM rate l'urgence)
2. LLM Mistral Small `mistral-small-latest` pour les autres (out_of_scope vs
   in_scope) — déterministe-difficile à faire en regex (formulations indirectes
   "j'en peux plus de l'école", "à quoi bon faire des études")
3. Default conservateur : si LLM échoue ou ambigu, traiter comme `in_scope`
   (mieux pipeline qui dit honnêtement qu'il sait pas que refus accidentel)

Coût : ~$0.0005/q + 0.5-1s latency. Acceptable.
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

ScopeLabel = Literal["in_scope", "out_of_scope", "urgent"]


# ─────────────── Regex pré-filter URGENCE (signaux forts uniquement) ───────────────

# Patterns explicites d'urgence vie/mal-être grave. Conservatifs : ne couvrent
# que les signaux non-ambigus. Le LLM rattrape les formulations indirectes.
_URGENT_PATTERNS = [
    # Suicide / fin de vie
    re.compile(r"\bsuicid[a-z]*\b", re.IGNORECASE),
    re.compile(r"\bme tuer\b", re.IGNORECASE),
    re.compile(r"\bme suicider\b", re.IGNORECASE),
    re.compile(r"\b(en finir|finir avec) (?:la vie|tout)\b", re.IGNORECASE),
    re.compile(r"\bplus envie de vivre\b", re.IGNORECASE),
    re.compile(r"\bne plus exister\b", re.IGNORECASE),
    re.compile(r"\b(disparait|disparaitre|disparaître)\b.*\bpour de bon\b", re.IGNORECASE),
    # Violences subies
    re.compile(r"\b(je suis|j'ai été) (battu|frappé|violent|abus)", re.IGNORECASE),
    re.compile(r"\b(violences? conjugales?|violences? domestiques?)\b", re.IGNORECASE),
    re.compile(r"\b(viol|agression sexuelle)\b", re.IGNORECASE),
    re.compile(r"\b(harcèlement|harcelement) (sexuel|scolaire) (subi|grave)\b", re.IGNORECASE),
    # Détresse psy aiguë
    re.compile(r"\b(crise (de )?(panique|angoisse) (intense|grave))\b", re.IGNORECASE),
    re.compile(r"\bje (vais|veux) m['e]\s*(faire du mal|automutil)", re.IGNORECASE),
]


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s)
        if not unicodedata.combining(c)
    )


def detect_urgent_signals_regex(question: str) -> list[str]:
    """Retourne la liste des patterns matchés (vide si aucun)."""
    matched = []
    for pattern in _URGENT_PATTERNS:
        if pattern.search(question):
            matched.append(pattern.pattern)
    return matched


# ─────────────── Réponses pré-écrites ───────────────

OUT_OF_SCOPE_RESPONSE = (
    "Cette question sort du cadre d'OrientIA, qui est spécialisé dans "
    "l'**orientation académique et professionnelle post-bac** (formations, "
    "métiers, parcours, choix d'écoles, réorientation, financement des "
    "études, insertion pro).\n\n"
    "As-tu une question d'orientation à me poser ? Quelques exemples :\n"
    "- *« Je suis en terminale, j'hésite entre prépa et BUT info »*\n"
    "- *« Comment se réorienter après une L2 de droit ? »*\n"
    "- *« Quelles écoles d'ingénieur en cybersécurité existent en Bretagne ? »*\n\n"
    "Pour toute autre question, je te suggère de t'adresser à la ressource "
    "appropriée (enseignant, ami, autre outil)."
)


URGENT_RESPONSE = (
    "Je perçois dans ton message une **détresse importante**. Avant tout, "
    "ta sécurité et ton bien-être passent avant les questions d'orientation.\n\n"
    "**Numéros d'écoute gratuits, anonymes, 24h/24** :\n\n"
    "- **3114** — Numéro national de **prévention du suicide** "
    "(gratuit, confidentiel, professionnels formés)\n"
    "- **3919** — Violences faites aux femmes (gratuit, anonyme)\n"
    "- **119** — Enfance en danger / maltraitance (24h/24)\n"
    "- **30 18** — SOS Amitié, écoute généraliste (anxiété, isolement)\n"
    "- **15** — SAMU si urgence vitale immédiate\n\n"
    "Tu peux aussi en parler à une personne de confiance autour de toi : "
    "Psy-EN du lycée, infirmier·ère scolaire, médecin traitant, parent, ami·e.\n\n"
    "Je suis un outil d'orientation, pas un professionnel de santé mentale. "
    "Mais ces personnes et numéros sauront t'écouter et t'aider."
)


# ─────────────── LLM classifier (out_of_scope vs in_scope) ───────────────

_CLASSIFIER_SYSTEM_PROMPT = """Tu es un classifieur de scope pour OrientIA, un système d'orientation \
académique et professionnelle française post-bac.

Catégorise la question utilisateur en EXACTEMENT UNE des 3 catégories :

1. **in_scope** : toute question liée à l'orientation post-bac ou professionnelle.
   Inclut : formations supérieures (BTS, BUT, licence, master, écoles d'ingé/co/art, \
prépa, doctorat, alternance, formation continue), métiers (devenir X, que fait Y), \
choix entre options, réorientation, parcours après bac/L2/master, financement des \
études (bourses, CPF), insertion pro (taux, salaires), comparaison d'écoles, exigences \
d'admission, accessibilité d'une formation. **MÊME** si le domaine est mal couvert \
(santé, droit, archi, vétérinaire, hôtellerie, art, sport, etc.) → c'est in_scope.

2. **out_of_scope** : question SANS lien direct avec orientation post-bac/pro.
   Exemples : devoirs scolaires (résoudre un exercice), cuisine, météo, blagues, \
politique, sport en tant que loisir/spectateur, programmation pure (sauf si dans \
contexte orientation), questions personnelles non liées (relation amoureuse, voyage), \
salutations sans question.

3. **urgent** : signal de **mal-être grave, idéations suicidaires, violences subies, \
harcèlement intense, détresse psychologique aiguë**. Inclut les formulations \
indirectes : "j'en peux plus", "à quoi bon", "personne ne m'aime", "tout va mal", \
"je suis nul·le, je devrais arrêter", "je veux disparaître". Si DOUTE → urgent (mieux \
flag de trop que rater un signal).

Retourne UNIQUEMENT un JSON strict :

{
  "label": "in_scope" | "out_of_scope" | "urgent",
  "reason": "<courte phrase justifiant la décision>"
}

Pas de markdown, pas de préambule. JSON only.
"""


@dataclass(frozen=True)
class ScopeResult:
    label: ScopeLabel
    reason: str
    via: Literal["regex_urgent", "llm", "fallback_in_scope"]
    pre_written_response: str | None = None  # texte à retourner si != in_scope


def _extract_json(raw: str) -> dict | None:
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*?\}", raw)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None


class ScopeClassifier:
    """Gate amont du pipeline OrientIA.

    Usage :
        clf = ScopeClassifier(client=mistral_client)
        result = clf.classify(question)
        if result.label != "in_scope":
            return result.pre_written_response  # court-circuit
        # sinon → continue le pipeline RAG normal

    Args:
        client: Mistral client (pour LLM cheap classification). Si None, fallback
            uniquement sur regex urgent + default in_scope (mode dégradé).
        model: par défaut mistral-small-latest (~$0.0005/q).
        timeout_ms: 5s default.
    """

    def __init__(
        self,
        client=None,
        model: str = "mistral-small-latest",
        timeout_ms: int = 5000,
    ):
        self.client = client
        self.model = model
        self.timeout_ms = timeout_ms

    def classify(self, question: str) -> ScopeResult:
        """Classifie une question en {in_scope, out_of_scope, urgent}."""
        if not question or not question.strip():
            return ScopeResult(
                label="out_of_scope",
                reason="empty question",
                via="fallback_in_scope",
                pre_written_response=OUT_OF_SCOPE_RESPONSE,
            )

        # Étape 1 : pré-filter regex URGENT (signaux forts non-ambigus)
        urgent_matches = detect_urgent_signals_regex(question)
        if urgent_matches:
            return ScopeResult(
                label="urgent",
                reason=f"regex urgent matched: {urgent_matches[0]}",
                via="regex_urgent",
                pre_written_response=URGENT_RESPONSE,
            )

        # Étape 2 : LLM classifier (out_of_scope vs in_scope vs urgent indirect)
        if self.client is None:
            # Mode dégradé : sans LLM, default in_scope (laisse le pipeline gérer)
            return ScopeResult(
                label="in_scope",
                reason="no LLM client provided, default in_scope",
                via="fallback_in_scope",
                pre_written_response=None,
            )

        try:
            resp = self.client.chat.complete(
                model=self.model,
                max_tokens=200,
                messages=[
                    {"role": "system", "content": _CLASSIFIER_SYSTEM_PROMPT},
                    {"role": "user", "content": question},
                ],
                response_format={"type": "json_object"},
            )
            text = resp.choices[0].message.content or ""
        except Exception as e:
            # Mode dégradé : LLM down → default in_scope (graceful)
            return ScopeResult(
                label="in_scope",
                reason=f"LLM error, default in_scope: {type(e).__name__}",
                via="fallback_in_scope",
                pre_written_response=None,
            )

        parsed = _extract_json(text)
        if not parsed or "label" not in parsed:
            return ScopeResult(
                label="in_scope",
                reason="LLM JSON parse failed, default in_scope",
                via="fallback_in_scope",
                pre_written_response=None,
            )

        label = parsed.get("label", "in_scope")
        reason = parsed.get("reason", "")[:200]
        if label not in ("in_scope", "out_of_scope", "urgent"):
            label = "in_scope"  # safe default

        if label == "urgent":
            return ScopeResult(
                label="urgent",
                reason=reason,
                via="llm",
                pre_written_response=URGENT_RESPONSE,
            )
        if label == "out_of_scope":
            return ScopeResult(
                label="out_of_scope",
                reason=reason,
                via="llm",
                pre_written_response=OUT_OF_SCOPE_RESPONSE,
            )
        return ScopeResult(
            label="in_scope",
            reason=reason,
            via="llm",
            pre_written_response=None,
        )
