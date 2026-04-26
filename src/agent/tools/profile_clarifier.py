"""ProfileClarifier — Sprint 1 axe B agentique.

Extraction structurée d'un profil utilisateur depuis une query libre.
Mistral function-calling avec `tool_choice="any"` (force le call) sur
l'unique tool `extract_user_profile`.

Le profil retourné guide le routing retrieval (Sprints 2-4) :
- `age_group` + `education_level` filtrent les corpora pertinents
- `sector_interest` pondère le ranking par domaine d'intérêt
- `region` active les corpora régionaux (APEC / DARES)
- `intent_type` route vers les patterns reranker existants
- `urgent_concern` flag pour adoucir le ton

Cf ADR-051 pour le rationale architectural.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from typing import Optional

from mistralai.client import Mistral

from src.agent.tool import Tool


# --- Profile dataclass (typed output) ---


VALID_AGE_GROUPS = {
    "lyceen_2nde",
    "lyceen_terminale",
    "bachelier_general",
    "bachelier_techno",
    "bachelier_pro",
    "etudiant_l1_l3",
    "etudiant_master",
    "adulte_25_45",
    "professionnel_actif",  # alias pratique : adulte avec emploi, pas
                            # de focus sur tranche d'âge précise
    "parent_lyceen",
    "professionnel_education",
    "other_or_unknown",
}

VALID_EDUCATION_LEVELS = {
    "infra_bac",  # 2nde, 1ère
    "terminale",
    "bac_obtenu",
    "bac+1",
    "bac+2",
    "bac+3",
    "bac+5",
    "bac+8_doctorat",
    "professionnel_actif",
    "unknown",
}

VALID_INTENT_TYPES = {
    "orientation_initiale",
    "reorientation_etude",
    "reconversion_pro",
    "comparaison_options",
    "decouverte_filieres",
    "info_metier_specifique",
    "demarche_administrative",
    "conceptuel_definition",
    "conseil_strategique",
    "other",
}


@dataclass
class Profile:
    """Profil utilisateur extrait par ProfileClarifier.

    Champs core (toujours présents) :
    - age_group : catégorie d'âge / situation
    - education_level : niveau d'études actuel
    - intent_type : nature de la demande

    Champs optionnels :
    - sector_interest : liste de secteurs / domaines mentionnés
    - region : région française mentionnée (libellé canonique)
    - urgent_concern : flag stress / urgence détecté
    - confidence : niveau de confiance auto-rapporté du LLM (0-1)
    - notes : annotations libres du LLM
    """

    age_group: str
    education_level: str
    intent_type: str
    sector_interest: list[str]
    region: Optional[str] = None
    urgent_concern: bool = False
    confidence: float = 0.5
    notes: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    def is_valid(self) -> bool:
        """Sanity check des enums core."""
        return (
            self.age_group in VALID_AGE_GROUPS
            and self.education_level in VALID_EDUCATION_LEVELS
            and self.intent_type in VALID_INTENT_TYPES
            and isinstance(self.sector_interest, list)
            and 0.0 <= self.confidence <= 1.0
        )


# --- Tool definition (Mistral function-calling JSON schema) ---


PROFILE_TOOL_PARAMS_SCHEMA = {
    "type": "object",
    "properties": {
        "age_group": {
            "type": "string",
            "enum": sorted(VALID_AGE_GROUPS),
            "description": (
                "Catégorie d'âge / situation de l'utilisateur. "
                "Choisis 'other_or_unknown' si la query ne donne pas "
                "assez d'indices."
            ),
        },
        "education_level": {
            "type": "string",
            "enum": sorted(VALID_EDUCATION_LEVELS),
            "description": (
                "Niveau d'études actuel ou dernier obtenu. "
                "'professionnel_actif' pour un adulte en poste sans "
                "info académique récente. 'unknown' si non déterminable."
            ),
        },
        "intent_type": {
            "type": "string",
            "enum": sorted(VALID_INTENT_TYPES),
            "description": (
                "Nature de la demande (cf doc OrientIA intent classifier). "
                "Une seule catégorie même si plusieurs intent secondaires."
            ),
        },
        "sector_interest": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Liste des secteurs / domaines mentionnés "
                "(ex: ['informatique', 'numérique'] pour 'BUT info data')"
                ". Vide si aucun secteur explicite."
            ),
        },
        "region": {
            "type": ["string", "null"],
            "description": (
                "Région française mentionnée (libellé officiel : "
                "'Île-de-France', 'Bretagne', 'La Réunion', etc.). "
                "null si non mentionnée."
            ),
        },
        "urgent_concern": {
            "type": "boolean",
            "description": (
                "True si la query exprime stress, peur, urgence "
                "(ex: 'j'ai peur', 'je galère', 'je ne sais pas quoi "
                "faire'). False sinon."
            ),
        },
        "confidence": {
            "type": "number",
            "description": (
                "Confiance auto-rapportée 0-1 sur l'extraction. "
                "0.3 si query très vague, 0.9 si query très explicite."
            ),
        },
        "notes": {
            "type": ["string", "null"],
            "description": (
                "Annotations libres : ambiguïtés détectées, indices "
                "implicites, contexte utile pour le routing aval. "
                "Max 200 caractères. Null si aucune note."
            ),
        },
    },
    "required": [
        "age_group", "education_level", "intent_type",
        "sector_interest", "urgent_concern", "confidence",
    ],
}


def _profile_clarifier_tool_func(**kwargs) -> dict:
    """Implémentation du Tool : valide les params et retourne le profil.

    Le LLM appelle ce tool avec les paramètres extraits. La fonction
    sert de validation finale (enum check, types) avant retour à
    l'agent loop. Utilisable hors agentique pour test.
    """
    try:
        profile = Profile(
            age_group=kwargs.get("age_group", "other_or_unknown"),
            education_level=kwargs.get("education_level", "unknown"),
            intent_type=kwargs.get("intent_type", "other"),
            sector_interest=kwargs.get("sector_interest", []) or [],
            region=kwargs.get("region"),
            urgent_concern=bool(kwargs.get("urgent_concern", False)),
            confidence=float(kwargs.get("confidence", 0.5)),
            notes=kwargs.get("notes"),
        )
    except (TypeError, ValueError) as e:
        return {"error": "profile_construction_failed", "message": str(e)}
    if not profile.is_valid():
        return {
            "error": "profile_validation_failed",
            "raw_input": {k: kwargs.get(k) for k in PROFILE_TOOL_PARAMS_SCHEMA["required"]},
        }
    return {"profile": profile.to_dict(), "valid": True}


PROFILE_CLARIFIER_TOOL = Tool(
    name="extract_user_profile",
    description=(
        "Extrait un profil structuré (age_group, education_level, "
        "intent_type, sector_interest, region, urgent_concern, "
        "confidence) depuis la query libre de l'utilisateur. À "
        "appeler en première étape pour comprendre QUI parle et QUE "
        "veut comprendre, avant de chercher des formations ou métiers."
    ),
    parameters=PROFILE_TOOL_PARAMS_SCHEMA,
    func=_profile_clarifier_tool_func,
)


# --- ProfileClarifier (interface haut niveau) ---


CLARIFIER_SYSTEM_PROMPT = (
    "Tu es ProfileClarifier d'OrientIA. Ta seule mission est d'extraire "
    "un profil structuré depuis la query libre de l'utilisateur en "
    "appelant l'outil `extract_user_profile`. Tu N'écris PAS de réponse "
    "narrative — tu invoques l'outil avec les paramètres extraits, "
    "c'est tout. Si la query est ambiguë, fais des best guesses et "
    "baisse `confidence` en conséquence."
)


@dataclass
class ProfileClarifier:
    """Wrapper haut niveau pour invoquer ProfileClarifier sur une query.

    Pattern :
        clarifier = ProfileClarifier(client)
        profile = clarifier.clarify("Je suis lycéen à La Réunion ...")
        # → Profile(age_group='lyceen_terminale', region='La Réunion', ...)

    En interne :
    - Force `tool_choice` sur `extract_user_profile` (single-call mode)
    - Parse les arguments retournés
    - Construit + valide la dataclass `Profile`
    - Retourne `Profile` ou raise `ValueError` si invalid
    """

    client: Mistral
    model: str = "mistral-large-latest"
    timeout_ms: int = 60_000

    def clarify(self, query: str) -> Profile:
        """Extrait le profil depuis `query`. Raise ValueError si parse fail."""
        messages = [
            {"role": "system", "content": CLARIFIER_SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ]
        response = self.client.chat.complete(
            model=self.model,
            messages=messages,
            tools=[PROFILE_CLARIFIER_TOOL.to_mistral_schema()],
            tool_choice="any",  # force le call
        )
        msg = response.choices[0].message
        if not msg.tool_calls:
            raise ValueError(
                f"ProfileClarifier: Mistral n'a pas appelé le tool "
                f"(content='{(msg.content or '')[:200]}')"
            )
        tc = msg.tool_calls[0]
        if tc.function.name != PROFILE_CLARIFIER_TOOL.name:
            raise ValueError(
                f"ProfileClarifier: tool inattendu '{tc.function.name}'"
            )
        try:
            args = json.loads(tc.function.arguments)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"ProfileClarifier: JSON parse failed "
                f"(args={tc.function.arguments[:200]!r}, err={e})"
            )
        result = PROFILE_CLARIFIER_TOOL.call(**args)
        if "error" in result:
            raise ValueError(
                f"ProfileClarifier: tool returned error: {result}"
            )
        return Profile(**result["profile"])
