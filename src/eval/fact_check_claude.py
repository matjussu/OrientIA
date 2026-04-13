"""Claude-powered fact-check — the Phase E.3 upgrade over the regex
version in fact_check.py.

Why:
- The regex version penalized real schools cited outside the retrieved
  fiches (e.g. "INSA Lyon" from mistral_raw → unverifiable even though
  INSA Lyon exists). That was a structural asymmetry in our favor.
- The regex version could verify a percentage that happened to appear in
  any fiche, even if the claim was "47% at Rennes" while the 47% came
  from a Paris fiche. No entity/number consistency check.
- Regex was blind to semantic consistency (a fabricated narrative with
  locally-plausible tokens could still score high).

Claude Haiku 4.5 (10× cheaper than Sonnet) handles all four statuses:
  * verified_fiche   — claim aligns with a retrieved fiche
  * verified_general — claim is true in Claude's world knowledge
                       (a real school/label/institution that isn't in
                       the fiches)
  * unverifiable     — plausible but not checkable
  * contradicted     — Claude knows the claim is wrong (fake report,
                       fake school, wrong number for a named entity)

The final score is (verified_fiche + verified_general) / total, matching
the regex version's contract. Empty-claim answers return 1.0 (neutral).

Cost per run (96 answers @ ~4K input + ~1.5K output Haiku tokens each):
roughly $1.25 with Haiku 4.5 pricing at the time of writing.
"""
from __future__ import annotations

import json
import re
from enum import Enum
from typing import Any


class ClaimStatus(str, Enum):
    VERIFIED_FICHE = "verified_fiche"
    VERIFIED_GENERAL = "verified_general"
    UNVERIFIABLE = "unverifiable"
    CONTRADICTED = "contradicted"


_KNOWN_STATUSES = {s.value: s for s in ClaimStatus}


FACT_CHECK_SYSTEM_PROMPT = """Tu es un vérificateur de faits rigoureux, \
spécialisé dans le système éducatif français (Parcoursup, ONISEP, écoles \
d'ingénieurs, universités, labels officiels SecNumEdu / CTI / CGE / Grade \
Master).

Pour chaque réponse d'un assistant d'orientation que tu reçois, tu dois
identifier TOUTES les affirmations factuelles puis les classer dans l'un
des quatre statuts suivants :

- **verified_fiche** : l'affirmation correspond à une information présente
  dans les fiches fournies (nom d'établissement, taux d'accès, label, code,
  URL). Les écarts numériques de moins de 3 points sont acceptables.
- **verified_general** : l'affirmation n'est pas dans les fiches mais elle
  est correcte selon tes connaissances générales (ex : une école connue
  comme « INSA Lyon » qui existe réellement, un label officiel valide,
  un code ROME authentique, une donnée cohérente avec la réalité).
- **unverifiable** : tu ne peux ni confirmer ni infirmer. Plausible mais
  non vérifiable.
- **contradicted** : tu sais que l'affirmation est fausse (rapport qui
  n'existe pas, école qui n'existe pas, taux incohérent avec l'établissement
  cité, label inventé).

Catégories d'affirmations à vérifier :
- Noms d'établissements, écoles, universités, lycées
- Taux d'accès, pourcentages de mentions, parts de bacs
- Labels officiels (SecNumEdu, CTI, CGE, Grade Master)
- Identifiants ONISEP (FOR.xxxx) et Parcoursup
- Codes ROME (format : 1-2 lettres + 4 chiffres)
- Noms de rapports, études, enquêtes — attention : les modèles hallucinent \
souvent des « rapports ANSSI 2023 » ou « études OCDE XX » qui n'existent pas.
- Salaires, nombres de places, dates de campagne

Sois FERME sur les rapports / études / enquêtes : si tu n'as aucune trace
d'un rapport cité, marque-le contradicted (pas unverifiable). Les
hallucinations de sources sont le biais principal que nous cherchons à
mesurer.

Réponds UNIQUEMENT en JSON valide, sans texte autour, strictement cette
structure :
{
  "claims": [
    {"text": "…", "type": "school|percentage|label|report|rome|onisep_id|other", \
"status": "verified_fiche|verified_general|unverifiable|contradicted", \
"reason": "une phrase courte"}
  ]
}

Si la réponse ne contient AUCUNE affirmation factuelle (réponse purement
qualitative ou conceptuelle), renvoie {"claims": []}.
"""


_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _fiche_of(container: dict) -> dict:
    return container.get("fiche", container)


def _summarise_fiches(retrieved: list[dict]) -> str:
    if not retrieved:
        return "(aucune fiche fournie pour cette réponse — baseline sans RAG)"
    bits = []
    for i, r in enumerate(retrieved, 1):
        f = _fiche_of(r)
        line = (
            f"{i}. {f.get('nom', '?')} — {f.get('etablissement', '?')}"
            f", {f.get('ville', '?')}"
        )
        if f.get("taux_acces_parcoursup_2025") is not None:
            line += f" | taux {f['taux_acces_parcoursup_2025']}%"
        labels = f.get("labels") or []
        if labels:
            line += f" | labels {', '.join(labels)}"
        if f.get("url_onisep"):
            line += f" | {f['url_onisep']}"
        bits.append(line)
    return "\n".join(bits)


def build_fact_check_prompt(answer: str, retrieved: list[dict]) -> str:
    """Assemble the user-side prompt for the fact-check turn."""
    return (
        f"Réponse à analyser :\n---\n{answer}\n---\n\n"
        f"Fiches RAG disponibles (source de vérité primaire) :\n"
        f"{_summarise_fiches(retrieved)}\n\n"
        f"Identifie toutes les affirmations factuelles et classe-les. "
        f"Réponds en JSON comme décrit dans tes instructions."
    )


def parse_fact_check_response(text: str) -> list[dict]:
    """Extract the claims list from Claude's response, robust to Markdown
    wrapping and unknown status values.
    """
    match = _JSON_OBJECT_RE.search(text)
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    raw_claims = data.get("claims") or []
    parsed: list[dict] = []
    for c in raw_claims:
        status_raw = c.get("status", "unverifiable")
        status = _KNOWN_STATUSES.get(status_raw, ClaimStatus.UNVERIFIABLE)
        parsed.append(
            {
                "text": c.get("text", ""),
                "type": c.get("type", "other"),
                "status": status,
                "reason": c.get("reason", ""),
            }
        )
    return parsed


def claude_fact_check(
    client: Any,
    answer: str,
    retrieved: list[dict],
    *,
    model: str = "claude-haiku-4-5-20251001",
    max_tokens: int = 4000,
) -> list[dict]:
    """Call Claude Haiku to produce the parsed claims list for one answer."""
    user_prompt = build_fact_check_prompt(answer, retrieved)
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=FACT_CHECK_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = response.content[0].text
    return parse_fact_check_response(text)


def claude_fact_check_score(
    client: Any,
    answer: str,
    retrieved: list[dict],
    *,
    model: str = "claude-haiku-4-5-20251001",
) -> float:
    """Return (verified_fiche + verified_general) / total_claims in [0, 1].

    Empty-claim answers return 1.0 (neutral) — qualitative responses
    aren't penalized for not citing anything. This matches the regex
    version's contract so judge_v2 can swap in the Claude-based scorer
    without other changes.
    """
    claims = claude_fact_check(client, answer, retrieved, model=model)
    if not claims:
        return 1.0
    verified = sum(
        1
        for c in claims
        if c["status"] in (ClaimStatus.VERIFIED_FICHE, ClaimStatus.VERIFIED_GENERAL)
    )
    return verified / len(claims)
