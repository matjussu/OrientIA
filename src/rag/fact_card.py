"""FactCard — extraction structurée des fiches pour le contrat strict v4.0.

Étape 2 refonte WHAT/HOW (2026-05-06). L'idée : au lieu de passer la prose
libre des fiches au LLM (qui mélange chiffres et description), on extrait
les champs typés en JSON tabulaire explicite. Le LLM voit alors clairement
"ce que je peux citer" vs "ce que je n'ai pas".

## 2 modes de fiches

Le corpus formations.json contient ~48k fiches de 2 natures :

1. **Parcoursup riches** (~21.5%, 10 536 fiches) : ont `taux_acces_parcoursup_2025`,
   `nombre_places`, `admission` (nested avec historique 2023-2025), `profil_admis`,
   `selectivite_code`, `debouches`. C'est le sous-corpus "or" pour les chiffres.

2. **Multi-corpus / MonMaster / RNCP** (~78.5%, ~38k fiches) : ont `nom`,
   `etablissement`, `niveau`, parfois `insertion_pro` (90% du corpus total a
   ce champ), souvent un `text` libre ou `detail` mais pas les stats Parcoursup.

`fiche_to_fact_card()` gère les 2 cas : extrait ce qui est disponible,
laisse `None` ailleurs. Le LLM décide de citer ou de dire "info non disponible".

## Format JSON pour le prompt LLM

`format_sources_for_llm(top_sources)` produit un tableau JSON sérialisé :

    [
      {
        "id": "S1",
        "formation": "Bachelor Cybersécurité ...",
        "etablissement": "Lycée Emmanuel d'Alzon",
        "ville": "Nîmes",
        "region": "Occitanie",
        "niveau": "bac+3",
        "statut": "Privé",
        "type_diplome": "formation d'école spécialisée",
        "chiffres": {
          "taux_acces_parcoursup_2025": 52.0,
          "nombre_places": 25,
          "duree": "3 ans",
          "taux_emploi_3ans": 0.86,
          "taux_cdi": 0.83,
          "salaire_median_embauche": 1740,
          "frais_annuels": null
        },
        "selectivite_code": "formation sélective",
        "debouches": ["RSSI", "Administrateur sécurité", "Ingénieur sécurité"],
        "url": "https://dossierappel.parcoursup.fr/.../?g_ta_cod=39320..."
      },
      ...
    ]

Le LLM lit ce JSON, sait quels chiffres citer, voit explicitement les `null`
qui doivent déclencher "info non disponible".
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class FactChiffres:
    """Sous-bloc 'chiffres' de la FactCard. Tous les champs sont None par
    défaut — le contrat strict v4 dit au LLM 'si null → info non disponible'."""
    taux_acces_parcoursup_2025: float | None = None
    nombre_places: int | None = None
    duree: str | None = None
    frais_annuels: float | None = None
    taux_emploi_3ans: float | None = None
    taux_emploi_6ans: float | None = None
    taux_cdi: float | None = None
    salaire_median_embauche: int | None = None
    pct_acceptes_debut_pp: float | None = None
    propositions_totales: int | None = None


@dataclass
class FactCard:
    """Structure une fiche corpus pour le LLM en mode strict v4.

    L'identité (formation/etab/ville/niveau) est obligatoire si présente — le
    LLM ne peut citer que les formations dont l'identité figure ici.
    Les chiffres sont scopés dans `chiffres` pour clarté visuelle dans le JSON.
    """
    id: str  # "S1", "S2", ... pour citations [source SX]
    formation: str
    etablissement: str | None = None
    ville: str | None = None
    region: str | None = None
    niveau: str | None = None
    statut: str | None = None  # "Public" | "Privé"
    type_diplome: str | None = None
    selectivite_code: str | None = None  # "formation sélective" | "formation non sélective"
    chiffres: FactChiffres = field(default_factory=FactChiffres)
    debouches: list[str] = field(default_factory=list)  # libellés métiers (depuis ROME)
    url: str | None = None  # url_parcoursup ou url_onisep prioritairement
    annee_donnees: int | None = None  # session Parcoursup ex 2025
    text_libre: str | None = None  # detail / text pour fiches non-Parcoursup
    domain: str | None = None  # "formation" | "metier" | "apec_region" | etc.

    def to_dict(self) -> dict[str, Any]:
        """Sérialise pour injection dans le user prompt LLM."""
        d = asdict(self)
        # Retire les champs None pour ne pas polluer le prompt avec du bruit
        # MAIS conserve `chiffres` même si tous null (le LLM doit voir
        # explicitement quels chiffres sont absents → "info non disponible").
        d_clean = {k: v for k, v in d.items() if k == "chiffres" or v not in (None, "", [])}
        return d_clean


def _safe_int(value: Any) -> int | None:
    """Convertit en int ou None (pas d'exception)."""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> float | None:
    """Convertit en float ou None (pas d'exception)."""
    if value is None or value == "":
        return None
    try:
        f = float(value)
        # NaN/inf check
        if f != f or f == float("inf") or f == float("-inf"):
            return None
        return f
    except (TypeError, ValueError):
        return None


def _safe_str(value: Any) -> str | None:
    """Convertit en str non-vide ou None."""
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.lower() in ("none", "null", "n/a", "nan", "non renseigné", "non renseignee"):
        return None
    return s


def _extract_debouches_libelles(debouches: Any) -> list[str]:
    """Extrait les libellés métiers depuis le champ debouches (list de dicts ROME)."""
    if not isinstance(debouches, list):
        return []
    out = []
    for d in debouches:
        if isinstance(d, dict):
            lib = _safe_str(d.get("libelle"))
            if lib:
                out.append(lib)
    return out


def _pick_url(fiche: dict) -> str | None:
    """Sélectionne l'URL la plus authoritative.

    Priorité : Parcoursup (lien direct fiche officielle) > ONISEP > url générique.
    """
    for key in ("lien_form_psup", "url_onisep", "url"):
        url = _safe_str(fiche.get(key))
        if url and url.startswith(("http://", "https://")):
            return url
    return None


def _pick_annee(fiche: dict) -> int | None:
    """Récupère l'année des données. Priorité : admission.session > annee > collected_at year."""
    admission = fiche.get("admission")
    if isinstance(admission, dict):
        annee = _safe_int(admission.get("session"))
        if annee:
            return annee
    annee = _safe_int(fiche.get("annee"))
    if annee:
        return annee
    # collected_at peut être un dict source -> date "YYYY-MM-DD"
    ca = fiche.get("collected_at")
    if isinstance(ca, dict):
        for v in ca.values():
            if isinstance(v, str) and len(v) >= 4 and v[:4].isdigit():
                year = _safe_int(v[:4])
                if year:
                    return year
    return None


def _pick_text_libre(fiche: dict, max_chars: int = 400) -> str | None:
    """Pour les fiches sans chiffres Parcoursup, récupère un texte court."""
    for key in ("text", "detail"):
        t = _safe_str(fiche.get(key))
        if t:
            return t[:max_chars]
    return None


def fiche_to_fact_card(fiche: dict, fact_id: str) -> FactCard:
    """Mappe une fiche corpus (dict JSON) vers une FactCard structurée.

    Args:
        fiche: dict (depuis formations.json). Tolérant aux champs absents.
        fact_id: identifiant court "S1", "S2", ... pour citations LLM.

    Returns:
        FactCard. Garantie : `formation` non vide. Tous les autres champs
        peuvent être None — le contrat v4 dit au LLM "si None, info non
        disponible".
    """
    nom = _safe_str(fiche.get("nom")) or "(formation sans nom)"

    # CHIFFRES PARCOURSUP (sous-corpus 21.5%)
    chiffres = FactChiffres(
        taux_acces_parcoursup_2025=_safe_float(fiche.get("taux_acces_parcoursup_2025")),
        nombre_places=_safe_int(fiche.get("nombre_places")),
        duree=_safe_str(fiche.get("duree")),
        frais_annuels=_safe_float(fiche.get("frais_annuels")),
        propositions_totales=_safe_int(fiche.get("propositions_totales")),
        pct_acceptes_debut_pp=_safe_float(fiche.get("pct_acceptes_debut_pp")),
    )
    # CHIFFRES INSERTION PRO (90% du corpus, sous insertion_pro nested)
    ip = fiche.get("insertion_pro")
    if isinstance(ip, dict):
        chiffres.taux_emploi_3ans = _safe_float(ip.get("taux_emploi_3ans"))
        chiffres.taux_emploi_6ans = _safe_float(ip.get("taux_emploi_6ans"))
        chiffres.taux_cdi = _safe_float(ip.get("taux_cdi"))
        chiffres.salaire_median_embauche = _safe_int(ip.get("salaire_median_embauche"))

    return FactCard(
        id=fact_id,
        formation=nom,
        etablissement=_safe_str(fiche.get("etablissement")),
        ville=_safe_str(fiche.get("ville")),
        region=_safe_str(fiche.get("region")),
        niveau=_safe_str(fiche.get("niveau")),
        statut=_safe_str(fiche.get("statut")),
        type_diplome=_safe_str(fiche.get("type_diplome")),
        selectivite_code=_safe_str(fiche.get("selectivite_code")),
        chiffres=chiffres,
        debouches=_extract_debouches_libelles(fiche.get("debouches")),
        url=_pick_url(fiche),
        annee_donnees=_pick_annee(fiche),
        text_libre=_pick_text_libre(fiche),
        domain=_safe_str(fiche.get("domain")) or _safe_str(fiche.get("domaine")),
    )


def format_sources_for_llm(
    top_sources: list[dict],
    max_sources: int = 10,
    max_debouches_per_card: int = 5,
) -> str:
    """Sérialise les top_sources retrievées en JSON tabulaire pour le user prompt v4.

    Args:
        top_sources: liste retournée par retrieve_top_k + rerank. Chaque item
            est soit `{score, fiche}`, soit la fiche elle-même.
        max_sources: cap pour éviter prompt trop long (top-10 par défaut).
        max_debouches_per_card: cap par carte pour éviter explosion.

    Returns:
        String JSON formaté (indent=2) prêt à injecter dans le user message.
    """
    cards = []
    for i, s in enumerate(top_sources[:max_sources], 1):
        fiche = s.get("fiche") if isinstance(s, dict) and "fiche" in s else s
        if not isinstance(fiche, dict):
            continue
        card = fiche_to_fact_card(fiche, fact_id=f"S{i}")
        # Tronque debouches pour cap
        if card.debouches and len(card.debouches) > max_debouches_per_card:
            card.debouches = card.debouches[:max_debouches_per_card]
        cards.append(card.to_dict())
    return json.dumps(cards, ensure_ascii=False, indent=2)


def has_any_chiffres(card: FactCard) -> bool:
    """Vrai si la FactCard contient AU MOINS un chiffre exploitable."""
    c = card.chiffres
    return any(
        v is not None for v in (
            c.taux_acces_parcoursup_2025,
            c.nombre_places,
            c.duree,
            c.frais_annuels,
            c.taux_emploi_3ans,
            c.taux_emploi_6ans,
            c.taux_cdi,
            c.salaire_median_embauche,
        )
    )
