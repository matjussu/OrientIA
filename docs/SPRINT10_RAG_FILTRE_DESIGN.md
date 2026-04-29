# Sprint 10 — RAG filtré métadonnées (chantier C, design ADR)

**Statut** : ✅ **v1 LIVRÉ** (8.1→8.5 done, dual-audit Jarvis GO sans réserve)
**Auteur** : Claudette
**Date** : 2026-04-29 (livraison v1 même jour que kickoff)
**Ordre Jarvis** : `2026-04-29-0700c-claudette-orientia-sprint10-rag-filtre-metadonnees`
**Branche** : `feat/sprint10-rag-filtre-metadonnees` (basée sur main post-PR #100 commit `00dadd8`)
**PR** : #102 (3 commits cumul : kickoff design + skeleton, mastère=Bac+6 fix, plug pipeline §8.3-§8.4)
**Dépendances amont** : PR #100 (AnalystAgent mergé) ✅
**Dépendances aval** : chantier B (textualisation ONISEP/RNCP avec frontmatter) → PR #103 livré v1.1 (102 ONISEP + 6590 RNCP ACTIVE)

---

## Changelog v1 livré 2026-04-29

| Étape | Statut | Commit | Tests |
|---|---|---|---|
| §8.1 Module `metadata_filter.py` skeleton | ✅ | `4fe1f32` | 81 verts |
| §8.2 `extract_filter_from_profile` + lookups | ✅ | `4fe1f32` | (idem) |
| Fix Master/Mastère=Bac+6 (correction Matteo) | ✅ | `3ab41fc` | 86 verts cumul (5 nouveaux) |
| §8.3 Plug `apply_metadata_filter` dans pipeline | ✅ | `a64eb84` | 11 nouveaux verts |
| §8.4 Auto-expansion `k×3 → ×10` | ✅ | `a64eb84` | (idem, dans tests intégration) |
| §8.5 Documentation README + ADR | ✅ | (ce commit) | — |

**Verdict tests cumul** : 11 (pipeline integration) + 86 (filter unit) = 97 nouveaux cas, suite globale 1706 verts, 0 régression.

**Audit Jarvis cumul** :
1. Kickoff design + skeleton (§8.1+§8.2) → GO sans réserve, 6 points review tranchés techniquement
2. Fix mastère=6 sur les 2 chantiers (B + C) cohérent → GO sans réserve
3. Plug pipeline §8.3+§8.4 (commit local a64eb84) → GO sans réserve avant push

---

## 1. Motivation

### 1.1 Point 2 grille Matteo (ce matin)
> "Donner à l'IA des méthodes de réflexion, pas juste des données métiers."

Le Sprint 9-archi a installé l'EmpathicAgent + AnalystAgent qui extraient en background le profil utilisateur (région, niveau, contraintes type alternance, intérêts). Mais ce profil est aujourd'hui **inutilisé côté retrieval** : on continue de faire un FAISS top-k brut sur la question, sans filtrer les formations sur les critères dur-codés du user.

Conséquence : l'utilisateur en Occitanie cherchant "alternance niveau Bac+2" se fait remonter des Masters parisiens en formation initiale parce qu'ils sont sémantiquement proches de sa requête.

### 1.2 Précision retrieval mesurable

Le Run F+G (Phase F.2 ablation) a mesuré que l'absence de filtres métadonnées coûte ~3-5 points de score factuelle sur les questions à contraintes (région, niveau, alternance). Le filtre cible 80% de gain de précision sur cette classe de questions sans coût supplémentaire FAISS (filtrage post-retrieve en mémoire).

### 1.3 Réutilisation AnalystAgent (PR #100)

L'AnalystAgent expose déjà un `profile_delta` JSON tour-à-tour avec :
- `region: str | null` (libellé canonique français)
- `niveau_scolaire: str | null` (libre-forme structurée, ex `"terminale_spe_maths_physique"`, `"l1_droit_redoublement"`)
- `contraintes: list[str]` (format `"clé:valeur"`, ex `"alternance:true"`, `"budget:moderate"`)
- `interets_detectes: list[str]` (vocabulaire snake_case)

→ Pas besoin d'un NLU dédié pour extraire les critères : on consomme ce que l'AnalystAgent produit déjà.

---

## 2. Schéma des 5 critères filtre v1

| Critère | Type | Source `profile_delta` | Sémantique filtre |
|---|---|---|---|
| `region` | `str \| None` | `profile.region` | Match formation.region OR formation.scope == "national" (national passe toujours) |
| `niveau_min` | `int \| None` | dérivé de `profile.niveau_scolaire` | Bac+N min accessible (ex L1 → niveau_min=2 pour passerelles) |
| `niveau_max` | `int \| None` | dérivé de `profile.niveau_scolaire` | Bac+N max raisonnable (ex L1 → niveau_max=5) |
| `alternance` | `bool \| None` | `contraintes` parsing (`alternance:true`) | True = formation alternance possible ; None = peu importe |
| `budget_max` | `int \| None` (€/an) | `contraintes` parsing (`budget:low\|moderate\|high`) | Borne sup acceptable. Mapping : low<2000, moderate<5000, high=∞ |
| `secteur` | `list[str] \| None` | `interets_detectes` lookup taxonomie | Liste de secteurs candidats (informatique, sante, droit, etc.). Match sur `formation.secteur` |

**Note v1** : critères tous **optionnels**. None = pas de filtre sur cet axe (équivalent SQL `WHERE 1=1`).

**Note v2** : ajouter `mobilite` (rayon km autour région), `prerequis_diplome` (filière requise), `langue` (anglais/français/bilingue).

---

## 3. Mapping AnalystAgent profile → filter criteria

```python
# src/rag/metadata_filter.py — extract_filter_from_profile()

def extract_filter_from_profile(profile_delta: dict) -> FilterCriteria:
    contraintes_dict = parse_contraintes(profile_delta.get("contraintes", []))
    niveau = profile_delta.get("niveau_scolaire")
    return FilterCriteria(
        region=normalize_region(profile_delta.get("region")),
        niveau_min=infer_niveau_min(niveau),
        niveau_max=infer_niveau_max(niveau),
        alternance=contraintes_dict.get("alternance"),  # "true"/"false"/None → bool|None
        budget_max=BUDGET_BRACKETS.get(contraintes_dict.get("budget")),
        secteur=infer_secteurs(profile_delta.get("interets_detectes", [])),
    )
```

### 3.1 Parsing contraintes "clé:valeur"

```python
def parse_contraintes(items: list[str]) -> dict[str, str]:
    out = {}
    for item in items:
        if ":" not in item:
            continue
        key, val = item.split(":", 1)
        out[key.strip().lower()] = val.strip().lower()
    return out
```

### 3.2 Infer niveau_min / niveau_max

Mapping libre-forme `niveau_scolaire` → range Bac+N :

| Pattern niveau_scolaire | niveau_min | niveau_max | Rationale |
|---|---|---|---|
| `terminale*` | 1 | 5 | Tout ouvert post-bac |
| `seconde\|premiere*` | 1 | 3 | Cible BTS/BUT/L courte |
| `l1_*\|bac+1*` | 2 | 5 | Passerelles + poursuite |
| `l2_*\|bac+2*` | 2 | 5 | Idem + L3 / écoles ingé en 3 ans |
| `l3_*\|bac+3*` | 3 | 5 | Master / écoles ingé spec |
| `m1_*\|bac+4*` | 4 | 5 | Fin de cycle |
| `actif_*\|professionnel_*` | 2 | 5 | Reconversion : courtes pro privilégiées |
| (None / non-reconnu) | None | None | Pas de filtre |

### 3.3 Mapping budget brackets

```python
BUDGET_BRACKETS = {
    "low": 2000,        # public ou modeste
    "moderate": 5000,   # privé associatif
    "high": None,       # pas de borne
}
```

### 3.4 Mapping intérêts → secteurs

Lookup table `INTERESTS_TO_SECTORS` (à enrichir au fil du run F+G) :
```python
INTERESTS_TO_SECTORS = {
    "informatique": ["informatique", "numerique"],
    "code": ["informatique", "numerique"],
    "cybersecurite": ["informatique", "securite"],
    "ingenierie": ["ingenierie", "industriel"],
    "biologie": ["sante", "vivant"],
    "droit": ["droit", "juridique"],
    "psychologie": ["psychologie", "sante"],
    # ... (extensible)
}
```

Secteur = liste retournée par lookup OR liste vide si rien matché → traduire en None (no filter).

---

## 4. Point d'injection dans le pipeline

### 4.1 Options évaluées

| Option | Description | Latence | Recall | Implémentation | Verdict |
|---|---|---|---|---|---|
| **A — Pré-FAISS** | Filtre `fiches` list + rebuild index | Très lente (re-embed) | Optimal | Lourd | ❌ Non viable production |
| **B — Post-FAISS** | FAISS top-k → filter → expand si trop peu | Rapide | Bon avec k_expanded=k×3 | Léger | ✅ **v1 recommandé** |
| **C — Sub-index FAISS** | IndexIDMap + IDSelector pré-search | Rapide | Optimal | Migration FAISS requise | 🟡 v2 si v1 insuffisant |

### 4.2 Architecture v1 (Option B)

```
question → AnalystAgent.update_profile() → profile_delta
                                              ↓
                                    extract_filter_from_profile()
                                              ↓
                                       criteria (FilterCriteria)
                                              ↓
question → retrieve_top_k(k=k_expanded=30×3=90) → reranked
                                              ↓
                                  apply_metadata_filter(reranked, criteria)
                                              ↓
                                  filtered (≥ top_k_sources items)
                                              ↓
                                  if len(filtered) < top_k_sources:
                                      retry retrieve_top_k(k=k_expanded×2)
                                              ↓
                                       MMR / top_k_sources
                                              ↓
                                            generate()
```

### 4.3 Auto-expansion stratégie

```python
# pseudocode dans pipeline.answer()
INITIAL_K_MULTIPLIER = 3  # k_expanded = k × 3 par défaut
MAX_K_MULTIPLIER = 10     # cap absolu

k_eff = k * INITIAL_K_MULTIPLIER
attempts = 0
while attempts < 3:
    retrieved = retrieve_top_k(client, index, fiches, question, k=k_eff)
    filtered = apply_metadata_filter(retrieved, criteria)
    if len(filtered) >= top_k_sources:
        break
    k_eff = min(k_eff * 2, k * MAX_K_MULTIPLIER)
    attempts += 1
# Fallback : si toujours pas assez, on prend ce qu'on a + 1 log warn
```

**Cap MAX_K_MULTIPLIER=10** : protège contre les criteria pathologiques (ex `region:guyane + alternance:true + niveau_min:5` = 0 fiches dans le corpus 443). Au-delà, on accepte la dégradation et on log pour analyse.

### 4.4 Interaction MMR / reranker

- Le filtre s'applique **après reranker** mais **avant MMR** : on filtre sur la pertinence boostée par les scores domain-aware (ADR-049), puis MMR sélectionne la diversité parmi le pool filtré.
- Si `use_mmr=False` : filter directement le slice `[:top_k_sources]`.

### 4.5 Backward compat

Le filtre est **opt-in** via flag `OrientIAPipeline(use_metadata_filter=False)` (défaut **False** v1 jusqu'à validation Run F+H).
Quand False → comportement actuel inchangé (pas de filter, pas de k_expanded).

---

## 5. API publique

### 5.1 Module `src/rag/metadata_filter.py`

```python
from dataclasses import dataclass
from typing import Iterable

@dataclass
class FilterCriteria:
    region: str | None = None
    niveau_min: int | None = None
    niveau_max: int | None = None
    alternance: bool | None = None
    budget_max: int | None = None  # €/an
    secteur: list[str] | None = None  # liste OR

    def is_empty(self) -> bool:
        """True si tous critères None (équivaut pas de filter)."""
        return all(getattr(self, f.name) is None for f in dataclasses.fields(self))


def extract_filter_from_profile(profile_delta: dict) -> FilterCriteria: ...

def apply_metadata_filter(
    fiches_with_score: list[dict],
    criteria: FilterCriteria,
) -> list[dict]:
    """Filtre les résultats retrievés sur les critères. Préserve l'ordre.

    Args:
        fiches_with_score: list[dict] avec clés "fiche" (le dict formation)
            et "score" (float). Format compatible `retrieve_top_k`.
        criteria: FilterCriteria.

    Returns:
        Sous-liste filtrée. Conserve l'ordre du retrieved.
    """
    if criteria.is_empty():
        return fiches_with_score
    return [item for item in fiches_with_score if _matches(item["fiche"], criteria)]


def _matches(fiche: dict, c: FilterCriteria) -> bool:
    # Mongo-style $eq, $in, $gte, $lte, $exists
    ...
```

### 5.2 Mongo-style operators internes

Pas exposés en API publique v1, mais utilisés en interne pour la composition :

```python
# $eq : exact match (ou national passe-toujours pour region)
def _match_region(fiche_region: str | None, criteria_region: str | None) -> bool:
    if criteria_region is None:
        return True
    if fiche_region is None or fiche_region == "national":
        return True
    return fiche_region.lower() == criteria_region.lower()

# $gte / $lte : range
def _match_niveau(fiche_niveau: int | None, niveau_min: int | None, niveau_max: int | None) -> bool:
    if fiche_niveau is None:
        return True  # absence de niveau = on prend (defensive)
    if niveau_min is not None and fiche_niveau < niveau_min:
        return False
    if niveau_max is not None and fiche_niveau > niveau_max:
        return False
    return True

# $eq bool optional : None = peu importe
def _match_alternance(fiche_alt: bool | None, c_alt: bool | None) -> bool:
    if c_alt is None:
        return True
    if fiche_alt is None:
        return False  # contrainte explicite, fiche sans info → exclue
    return fiche_alt == c_alt

# $lte budget
def _match_budget(fiche_budget: int | None, c_budget_max: int | None) -> bool:
    if c_budget_max is None:
        return True
    if fiche_budget is None:
        return True  # absence = on prend (defensive)
    return fiche_budget <= c_budget_max

# $in secteur
def _match_secteur(fiche_secteur: str | None, c_secteurs: list[str] | None) -> bool:
    if not c_secteurs:
        return True
    if fiche_secteur is None:
        return False  # contrainte explicite, fiche sans secteur → exclue
    return fiche_secteur.lower() in [s.lower() for s in c_secteurs]
```

**Asymétrie** sur `_match_alternance` et `_match_secteur` (fiche sans info → exclue) vs `_match_region`, `_match_niveau`, `_match_budget` (fiche sans info → incluse, defensive). Justification : alternance et secteur sont des critères dur ; région et niveau/budget sont souples (one-size-fits-all formations nationales / sans coût affiché).

À valider Matteo : cette asymétrie est-elle correcte ou faut-il un mode `strict_mode=True/False` ?

---

## 6. Format frontmatter formations attendu (consommé par filter)

Chantier B (textualisation ONISEP/RNCP) produira :

```yaml
---
id: onisep_F-A-1234
title: BUT Informatique — IUT Toulouse III
region: occitanie
niveau: 3                  # 0 = avant bac, 1 = Bac+1, ..., 5 = Bac+5
alternance: true           # bool
budget: 0                  # €/an (0 = formation publique gratuite)
secteur: informatique      # canonique
duree_mois: 36
selectivite: moderate      # low/moderate/high (non utilisé v1)
source: parcoursup_2026
---
Le BUT Informatique se prépare en 3 ans à l'IUT Toulouse III...
```

Le filter consomme ces frontmatter via `fiche` dict avec keys `region`, `niveau`, `alternance`, `budget`, `secteur` (top-level, pas nested).

**Important** : pour les fiches actuelles `data/processed/formations.json` (443 fiches Parcoursup + ONISEP) qui n'ont pas encore ces frontmatter (chantier B pas livré), le filter en l'état traite chaque champ absent comme None → defensive pass-through (cf §5.2 asymétrie).

→ Tests v1 utilisent un **mock fiches list inline avec frontmatter** ; intégration pipeline réelle attend chantier B.

---

## 7. Tests unitaires v1 (attendus)

`tests/test_metadata_filter.py` :

1. **Parsing contraintes**
   - `parse_contraintes(["alternance:true", "budget:moderate"])` → `{"alternance": "true", "budget": "moderate"}`
   - Edge case : item sans `:` → ignoré silencieusement
   - Edge case : item avec multiple `:` → split sur premier seulement (`"region:auvergne-rhone-alpes"` OK)

2. **Infer niveau range**
   - `"terminale_spe_maths_physique"` → (1, 5)
   - `"l1_droit"` → (2, 5)
   - `"actif_marketing"` → (2, 5)
   - None → (None, None)

3. **FilterCriteria.is_empty()**
   - all None → True
   - 1 critère set → False

4. **apply_metadata_filter — single criterion**
   - Region match : ["occitanie", "ile-de-france", "national"] avec criteria.region=`occitanie` → 2 (occitanie + national)
   - Niveau range : fiches niveau [1, 3, 5, 7] avec niveau_min=2, niveau_max=5 → [3, 5]
   - Alternance True : fiches [True, False, None] avec criteria.alternance=True → [True]
   - Budget cap : fiches [0, 3000, 8000] avec budget_max=5000 → [0, 3000]
   - Secteur in : fiches ["info", "droit", "sante"] avec secteur=["informatique"] → ? (lookup à valider)

5. **apply_metadata_filter — composite (AND logique)**
   - Région Occitanie + alternance True + niveau Bac+2 → matches uniquement les BUT/écoles correspondantes

6. **Edge cases**
   - is_empty() criteria → return list intacte (pas de copy)
   - Liste vide → liste vide
   - Aucun match → liste vide (pas crash)
   - fiche avec 0 frontmatter → defensive pass-through ou exclusion selon asymétrie §5.2

7. **extract_filter_from_profile end-to-end**
   - Profile typique L1 droit Occitanie : `{"region": "occitanie", "niveau_scolaire": "l1_droit_redoublement", "contraintes": ["alternance:false"], "interets_detectes": ["droit", "psychologie"]}` → criteria attendue connue

---

## 8. Plan d'implémentation par étape

| Étape | Livrable | Tests | Branchement |
|---|---|---|---|
| **8.1** Module `src/rag/metadata_filter.py` (FilterCriteria + parse_contraintes + infer_niveau + apply_metadata_filter) | code prêt | unit tests 1-6 (~25 cas) | aucun (skeleton standalone) |
| **8.2** `extract_filter_from_profile()` + lookup tables (BUDGET_BRACKETS, INTERESTS_TO_SECTORS) | code prêt | unit test 7 + lookup table tests | aucun |
| **8.3** Plug `apply_metadata_filter` dans `OrientIAPipeline.answer()` derrière flag `use_metadata_filter=False` | pipeline modifiée backward-compat | tests pipeline existants verts + 3 nouveaux tests `use_metadata_filter=True` avec mock criteria | nécessite chantier B fini OU mock fiches inline |
| **8.4** Auto-expansion k logic | pipeline robuste | test path "criteria restrictif → expand → fallback warn" | dépend 8.3 |
| **8.5** Documentation utilisateur (README mise à jour) | DOCS.md / README.md | aucun | dépend 8.4 |

**Ce premier commit kickoff** = §8.1 + §8.2 (skeleton + tests) **uniquement**. Pas de plug pipeline tant que B pas livré.

---

## 9. Risques identifiés

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Asymétrie pass-through fiche-sans-info trop permissive (faux positifs) | Moyen | Modéré (recall haut, précision baisse) | Mode `strict_mode=True` opt-in (v2) |
| Mapping `INTERESTS_TO_SECTORS` incomplet → secteur=None alors qu'il aurait fallu filtrer | Élevé v1 | Modéré | Logs des interets non-mappés → enrichissement table au fil des sessions réelles |
| Niveau_scolaire libre-forme AnalystAgent non couvert par patterns infer_niveau | Moyen | Faible (fallback None) | Catalog des patterns vus en logs, ajouter au fil de l'eau |
| k_expanded × 3 trop petit pour criteria multi-restrictifs | Faible (corpus 443 fiches) | Moyen (réponse appauvrie) | MAX_K_MULTIPLIER=10 + warn log |
| Frontmatter chantier B retardé → impossible de tester intégration | Moyen | Faible (mock dispo) | Tests pipeline avec mock fiches inline tant que B en cours |
| Régression run F+G measurements (use_metadata_filter=True doit améliorer score, pas baisser) | Faible (filter post-rerank) | Élevé (effet de bord retrieval) | Mesure A/B avec/sans filter sur 32 dev set avant promote |

---

## 10. Validation Matteo / arbitrage Jarvis (clos 2026-04-29)

Les 6 points du design ont été tous arbitrés techniquement par Jarvis lors de l'audit kickoff (cf message 0700c GO sans réserve). Pas de blocage Matteo.

| Point | Verdict | Notes |
|---|---|---|
| 1. Option B (post-FAISS) vs Option C (IndexIDMap) | ✅ Option B | v1 minimal viable, à réviser si corpus >10k fiches |
| 2. Asymétrie defensive vs strict_mode unifié | ✅ Asymétrie acceptée | Sémantique métier correcte. À surveiller F+G post-chantier B (faux négatifs réels). Strict_mode opt-in v2 si recall pose pb |
| 3. Schéma 5 critères v1 vs ajouter mobilite/prerequis_diplome | ✅ 5 critères suffisant | Mobilité redondant avec region (national pass-through). Prerequis_diplome plus complexe, repousser v2 |
| 4. k_expanded × 3 avec MAX × 10 | ✅ Ratios acceptés | Mesure empirique requise F+G : si >30% questions hit MAX → réviser |
| 5. Flag opt-in `use_metadata_filter=False` | ✅ Accepté | Cohérent backward compat + A/B test |
| 6. Maintien `INTERESTS_TO_SECTORS` | ✅ Manuel v1 | Enrichissement v2 via embeddings clustering sur intérêts non-mappés observés en logs |

### Reco mesure F+G post-livraison (Jarvis audit kickoff)

Run F+G doit mesurer A/B avec/sans `use_metadata_filter` :
- Recall sur 32 dev set (gates : >10pp baisse → réviser asymétrie ou schéma)
- Distribution fiches avec frontmatter incomplet → faux négatifs réels asymétrie alternance/secteur
- `k_expanded` effectif moyen via `pipeline.last_filter_stats` (combien d'expansions × 3 / × 6 / × 10 hit en pratique)

Gates : >10pp recall ou >30% questions hit MAX_K_MULTIPLIER → réviser asymétrie ou schéma critères.

---

## 11. Liens

- Ordre Jarvis : `2026-04-29-0700c-claudette-orientia-sprint10-rag-filtre-metadonnees`
- AnalystAgent référence : `src/agents/hierarchical/analyst_agent.py` (PR #100)
- Pipeline existant : `src/rag/pipeline.py`, `src/rag/retriever.py`
- Chantier B amont (frontmatter formations) : ordre `2026-04-29-0700b-claudette-orientia-sprint10-textualisation-onisep-rncp`
- ADR-049 (domain-aware reranker) : `docs/DECISION_LOG.md`

---

*Doc préparée par Claudette le 2026-04-29 sous l'ordre 0700c. v1 livré le 2026-04-29 : §8.1 → §8.5 done, dual-audit Jarvis GO sans réserve, 1706 tests cumul verts. Activation production via `OrientIAPipeline(..., use_metadata_filter=True)` derrière feature flag config (v1.1 future).*
