"""Axe 2 typed contracts — Pydantic v2 models pour le flow agentic Phase 1.

Couche ADDITIVE qui coexiste avec les dataclasses Sprint 9 hierarchical
(`UserSessionProfile`, `EmpathicResponse`) sans les remplacer. Adapters
bidirectionnels assurent la compat lors de la jonction Sprint 9 →
Axe 2 (cf `analyze_for_routing()` A2).

## Design choices documentés S0

- **Pydantic v2** (dispo `pydantic==2.12.5` transitive via mistralai/fastapi)
    - Validation runtime stricte vs dataclass annotations cosmétiques
    - JSON schema export natif (utile pour orchestrateur Sonnet 4.5
        tool definitions + Anthropic SDK)
    - `model_config = ConfigDict(extra="forbid")` strict — les
        contracts agentiques ne tolèrent pas de champs surprises
    - Sérialisation cohérente avec Anthropic / OpenAI SDKs

- **Enums Python** (vs Literal) — réutilise les VALID_*_GROUPS/_LEVELS/
    _TYPES de `src/agent/tools/profile_clarifier.py` Sprint 1 legacy
    (anti-réinvention 332 lignes existantes), mais expose les valeurs
    via `enum.StrEnum` pour intégration Pydantic propre.

- **Champs bornés** : `Field(..., ge=0.0, le=1.0)` pour confidence,
    relevance scores. Validation runtime catch les outputs LLM
    dégradés en amont.

## Modèles publics

- `ProfileState` : profil typé enum-routable produit par A2
    `AnalystAgent.analyze_for_routing()`. Distinct de Sprint 9
    `UserSessionProfile` libre-forme.
- `SubQuestion` : sous-question décomposée (Phase 2 A3 input, mais
    contract défini Phase 1 pour stabilité interface).
- `ToolCallResult` : résultat d'invocation tool A4 (search_formations,
    get_debouches, get_admission_calendar).
- `AgentInput` / `AgentOutput` : I/O orchestrateur Sonnet 4.5 Phase 1.
"""
from __future__ import annotations

import enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---------- Enums ----------
# Values empruntées à src/agent/tools/profile_clarifier.py Sprint 1
# (anti-réinvention) mais exposées via StrEnum pour Pydantic v2.


class AgeGroup(str, enum.Enum):
    LYCEEN_2NDE = "lyceen_2nde"
    LYCEEN_TERMINALE = "lyceen_terminale"
    BACHELIER_GENERAL = "bachelier_general"
    BACHELIER_TECHNO = "bachelier_techno"
    BACHELIER_PRO = "bachelier_pro"
    ETUDIANT_L1_L3 = "etudiant_l1_l3"
    ETUDIANT_MASTER = "etudiant_master"
    ADULTE_25_45 = "adulte_25_45"
    PROFESSIONNEL_ACTIF = "professionnel_actif"
    PARENT_LYCEEN = "parent_lyceen"
    PROFESSIONNEL_EDUCATION = "professionnel_education"
    OTHER_OR_UNKNOWN = "other_or_unknown"


class EducationLevel(str, enum.Enum):
    INFRA_BAC = "infra_bac"
    TERMINALE = "terminale"
    BAC_OBTENU = "bac_obtenu"
    BAC_PLUS_1 = "bac+1"
    BAC_PLUS_2 = "bac+2"
    BAC_PLUS_3 = "bac+3"
    BAC_PLUS_4 = "bac+4"
    BAC_PLUS_5 = "bac+5"
    BAC_PLUS_8_DOCTORAT = "bac+8_doctorat"
    PROFESSIONNEL_ACTIF = "professionnel_actif"
    UNKNOWN = "unknown"


class IntentType(str, enum.Enum):
    ORIENTATION_INITIALE = "orientation_initiale"
    REORIENTATION_ETUDE = "reorientation_etude"
    RECONVERSION_PRO = "reconversion_pro"
    COMPARAISON_OPTIONS = "comparaison_options"
    DECOUVERTE_FILIERES = "decouverte_filieres"
    INFO_METIER_SPECIFIQUE = "info_metier_specifique"
    DEMARCHE_ADMINISTRATIVE = "demarche_administrative"
    CONCEPTUEL_DEFINITION = "conceptuel_definition"
    CONSEIL_STRATEGIQUE = "conseil_strategique"
    OTHER = "other"


# ---------- Models publics ----------


class ProfileState(BaseModel):
    """Profil utilisateur typé enum-routable — Axe 2 Phase 1.

    Produit par `AnalystAgent.analyze_for_routing(session)` (A2). Sert
    d'input à l'orchestrateur Sonnet 4.5 pour décider quels tools
    appeler avec quels arguments.

    Distinct de Sprint 9 `UserSessionProfile` libre-forme (préservé en
    parallèle pour EmpathicAgent persona conseiller). Mapping rules
    libre-forme → enum implémenté en A2.
    """

    model_config = ConfigDict(
        extra="forbid",
        use_enum_values=False,  # garde les enum Python pour comparaison
    )

    age_group: AgeGroup = Field(
        ...,
        description="Catégorie d'âge / situation (enum). 'other_or_unknown' si "
                    "ambigu. Source : mapping `UserSessionProfile.niveau_scolaire` + "
                    "`age_estime` selon règles A2.",
    )
    education_level: EducationLevel = Field(
        ...,
        description="Niveau d'études actuel ou dernier obtenu (enum). 'unknown' "
                    "si non déterminable.",
    )
    intent_type: IntentType = Field(
        ...,
        description="Nature de la demande (enum). Une seule catégorie même si "
                    "intents secondaires.",
    )
    sector_interest: list[str] = Field(
        default_factory=list,
        description="Liste des secteurs/domaines mentionnés (libre-forme courte, "
                    "ex 'informatique', 'santé', 'numérique'). Vide si aucun.",
    )
    region: str | None = Field(
        default=None,
        description="Région française canonique (ex 'Île-de-France', 'Bretagne', "
                    "'La Réunion'). Null si non mentionnée.",
    )
    urgent_concern: bool = Field(
        default=False,
        description="True si la query exprime stress/peur/urgence.",
    )
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Niveau de confiance auto-rapporté du LLM (0-1).",
    )


class SubQuestion(BaseModel):
    """Sous-question décomposée à partir de la query user.

    Produit par A3 SubQuestionDecomposer (Phase 2). Le contract est
    défini Phase 1 pour stabilité interface lors du jointage.

    Pattern d'usage :
        sq = SubQuestion(
            id="sq_1",
            text="Quelles formations cyber post-bac à Toulouse ?",
            requires_tools=["search_formations"],
            depends_on=[],
        )
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(
        ...,
        min_length=1,
        description="Identifiant local stable, ex 'sq_1', 'sq_2_a'.",
    )
    text: str = Field(
        ...,
        min_length=1,
        description="Texte de la sous-question, formulée pour matcher un tool.",
    )
    requires_tools: list[str] = Field(
        default_factory=list,
        description="Noms des tools nécessaires pour répondre (vide = pure "
                    "synthèse depuis context).",
    )
    depends_on: list[str] = Field(
        default_factory=list,
        description="IDs de sous-questions à résoudre AVANT (e.g. 'sq_1' avant 'sq_2_a').",
    )


class ToolCallResult(BaseModel):
    """Résultat d'invocation d'un tool A4.

    Pattern uniforme pour search_formations / get_debouches /
    get_admission_calendar : chaque tool retourne un payload + métadonnées.
    L'orchestrateur Sonnet 4.5 lit `success` + `payload` pour décider
    next-step.
    """

    model_config = ConfigDict(extra="forbid")

    tool_name: str = Field(
        ...,
        min_length=1,
        description="Nom du tool invoqué (ex 'search_formations').",
    )
    success: bool = Field(
        ...,
        description="True si l'invocation a abouti à un payload exploitable.",
    )
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Données retournées par le tool (forme libre selon tool, "
                    "validée par tool-spécifique en aval).",
    )
    error: str | None = Field(
        default=None,
        description="Message d'erreur si success=False. Null sinon.",
    )
    elapsed_ms: int | None = Field(
        default=None,
        ge=0,
        description="Latence wall-clock du call en ms (telemetry, optionnel).",
    )


class AgentInput(BaseModel):
    """Input orchestrateur Sonnet 4.5 — Phase 1 minimal.

    Construit par le wrapper agent depuis :
    - La query user actuelle
    - Le `ProfileState` produit par `AnalystAgent.analyze_for_routing()`
    - L'historique conversationnel des N derniers tours (Sprint 9 Session)
    """

    model_config = ConfigDict(extra="forbid")

    user_query: str = Field(
        ...,
        min_length=1,
        description="Message user du tour courant.",
    )
    profile: ProfileState = Field(
        ...,
        description="Profil typé enum (A2 output).",
    )
    history: list[dict[str, str]] = Field(
        default_factory=list,
        description="N derniers tours `[{role, content}, ...]` (forme Sprint 9 "
                    "Session). Vide si premier tour.",
    )
    max_tool_calls: int = Field(
        default=4,
        ge=1,
        le=10,
        description="Garde-fou orchestrateur (anti-loop). Phase 1 minimal = 4.",
    )


class AgentOutput(BaseModel):
    """Output orchestrateur Sonnet 4.5 — Phase 1 minimal.

    Sert d'input au générateur final Mistral medium qui produit le texte
    user-facing à partir de `tool_results` + `final_answer_hint`.

    `final_answer_hint` est optionnel : si Sonnet a déjà rédigé une
    ébauche de réponse, Mistral l'utilise comme guide ; sinon Mistral
    rédige from scratch en s'appuyant sur les tool_results.
    """

    model_config = ConfigDict(extra="forbid")

    tool_calls_made: list[ToolCallResult] = Field(
        default_factory=list,
        description="Trace des invocations de tools dans l'ordre chronologique.",
    )
    final_answer_hint: str | None = Field(
        default=None,
        description="Ébauche de réponse Sonnet (optionnel, guide Mistral générateur).",
    )
    stopped_reason: str = Field(
        ...,
        description="Pourquoi l'orchestration s'est arrêtée. Ex 'max_calls_reached', "
                    "'sonnet_decided_done', 'error_critical'.",
    )
    elapsed_orchestration_ms: int | None = Field(
        default=None,
        ge=0,
        description="Latence wall-clock totale orchestration en ms (telemetry).",
    )
