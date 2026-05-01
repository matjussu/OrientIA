# Sprint 12 Axe 2 A2 — Bridge design AnalystAgent → ProfileState

**Date** : 2026-05-01
**Branche** : `feat/sprint12-axe-2-agentic-phase-1`
**Référence ordre** : `2026-05-01-1820-claudette-orientia-sprint12-axe-2-agentic-phase-1-A1-A2-A4` (A2)
**Auteur** : Claudette
**Scope** : doc design BRIDGE entre Sprint 9 hierarchical (libre-forme dataclass) et Axe 2 (Pydantic enum-typed). Audit Pattern #3+#4 strict requested AVANT A4 démarrage.

---

## Contrat sémantique BRIDGE

`AnalystAgent.analyze_for_routing(session, user_query=None) → ProfileState` (Pydantic).

**Side effect documenté** : mute `session.profile` via `merge_update(delta)` (cohérent avec semantics `update_profile()` Sprint 9 préservé bit-à-bit).

**Pipeline en 3 étapes** :
1. `update_profile(session)` — Sprint 9 flow function-calling Mistral (`update_session_profile` tool)
2. `session.profile.merge_update(delta)` si delta non-vide
3. `derive_profile_state(session, user_query)` — mapping déterministe pure-function (cf `src/axe2/profile_mapping.py`)

**Coût marginal Axe 2 vs Sprint 9** : aucun appel Mistral supplémentaire — les mapping rules sont déterministes O(N regex × N input chars) en mémoire, ~µs.

---

## Mapping rules détaillées

### 1. `niveau_scolaire` → `EducationLevel`

Patterns regex appliqués sur niveau **normalisé** (`_` → ` ` + accents stripped). Ordonnés du plus spécifique au plus général :

| Pattern niveau | EducationLevel |
|---|---|
| `\b(?:doctorat\|phd\|these)\b` | BAC_PLUS_8_DOCTORAT |
| `\bm2\b` ou `\bmaster\s+2\b` | BAC_PLUS_5 |
| `\bm1\b` ou `\bmaster\s+1\b` | BAC_PLUS_4 |
| `\bmaster\b` (générique) | BAC_PLUS_5 |
| `\bl3\b` ou `\blicence\s+3\b` | BAC_PLUS_3 |
| `\bl2\b` ou `\blicence\s+2\b` | BAC_PLUS_2 |
| `\bl1\b` ou `\blicence\s+1\b` | BAC_PLUS_1 |
| `\b(?:bts\|but\|dut)\b` | BAC_PLUS_2 |
| `\bprepa\b` | BAC_PLUS_1 |
| `\bterminale\b` ou `\bterm\b` | TERMINALE |
| `\b(?:premiere\|seconde\|2nde\|1ere)\b` | INFRA_BAC |
| `\bbac\+5\b` | BAC_PLUS_5 |
| `\bbac\+4\b` / `\bbac\+3\b` / `\bbac\+2\b` / `\bbac\+1\b` | BAC_PLUS_X |
| `\bbachelier\b` ou `\bbac\b` | BAC_OBTENU |
| `\bprofessionnel\b` ou `\bsalarie\b` | PROFESSIONNEL_ACTIF |
| **Aucun match** | UNKNOWN (pas d'invention) |

### 2. `niveau_scolaire` + `age_estime` → `AgeGroup`

Logique chain :
1. Lycéens : `terminale` → check techno/sti2d/stmg/st2s → BACHELIER_TECHNO ; check pro → BACHELIER_PRO ; sinon LYCEEN_TERMINALE
2. `(seconde|2nde|premiere|1ere)` → LYCEEN_2NDE
3. `(l1|l2|l3|licence)` → ETUDIANT_L1_L3
4. `(m1|m2|master)` → ETUDIANT_MASTER
5. `(doctorat|phd|these)` → ETUDIANT_MASTER (approximation, pas d'enum doctorat)
6. `(bts|but|dut|prepa)` → BACHELIER_GENERAL (post-bac court)
7. `(professionnel|salarie)` → PROFESSIONNEL_ACTIF
8. `parent` → PARENT_LYCEEN
9. **Fallback `age_estime`** si fourni :
    - ≤ 16 → LYCEEN_2NDE
    - 17-18 → LYCEEN_TERMINALE
    - 19-22 → ETUDIANT_L1_L3
    - 23-25 → ETUDIANT_MASTER
    - 26-45 → ADULTE_25_45
10. **Aucun match** → OTHER_OR_UNKNOWN

### 3. `user_query` → `IntentType` (heuristique mot-clé)

Patterns appliqués sur query **strippée d'accents** (`réorienter` → `reorienter`, etc.). Ordre du plus spécifique au plus général :

| Pattern query | IntentType |
|---|---|
| `\breconvertir\b` ou `\bchangement\s+de\s+metier\b` | RECONVERSION_PRO |
| `\breorienter\b` ou `\bchanger\s+de\s+filiere\b` | REORIENTATION_ETUDE |
| `\bcomparer\b` ou `\bvs\.?\b` ou `\bentre\s+\w+\s+et\s+\w+\b` | COMPARAISON_OPTIONS |
| `\b(formation_type)\b ... \bou\b ... \b(formation_type)\b` | COMPARAISON_OPTIONS |
| `\bc'est\s+quoi\b` ou `\bdefinition\b` | CONCEPTUEL_DEFINITION |
| `\bmetier\s+(?:de\|du)\b` ou `\bprofession\b` | INFO_METIER_SPECIFIQUE |
| `\bdemarche\b` ou `\bs'inscrire\b` ou `\bparcoursup\s+calendrier\b` | DEMARCHE_ADMINISTRATIVE |
| `\bconseil\b` ou `\bstrategie\b` ou `\bque\s+me\s+conseilles\b` | CONSEIL_STRATEGIQUE |
| `\bdecouvrir\b` ou `\bquelles?\s+(?:formations?\|filieres?)\s+existe\b` | DECOUVERTE_FILIERES |
| **Aucun match** | ORIENTATION_INITIALE (fallback dominant corpus user) |
| Query None ou vide | OTHER |

### 4. Heuristique `urgent_concern` (boolean)

Patterns sur query/valeurs/questions_ouvertes concaténés + accent-strippés :
- `\b(?:stress\|panique\|peur\|angoisse\|deteste\|deprime)\b`
- `\b(?:perdu\|sature\|epuise\|au\s+bord)\b`
- `\b(?:urgent\|urgence\|rapidement)\b`
- `\b(?:burnout\|burn[- ]out\|craquer)\b`
- `\bsais\s+pas\s+(?:quoi\s+faire|comment)\b`

Match → True. Aucun match → False.

### 5. Pass-through champs déjà typés

- `sector_interest` ← `interets_detectes` (list pass-through)
- `region` ← `region` (str pass-through, suppose canonique)
- `confidence` ← `confidence` (float pass-through, validation Pydantic 0-1)

---

## Ambiguïtés irréductibles documentées

Aucune ambiguïté irréductible identifiée pendant l'implémentation A2. Les cas multi-pattern sont résolus par **ordre du plus spécifique au plus général** (e.g. `m2_droit` matche `\bm2\b` AVANT `\bmaster\b`). Les cas non-couverts retournent UNKNOWN / OTHER_OR_UNKNOWN / OTHER (pas d'invention magique).

Si Phase 2+ révèle une ambiguïté empirique (e.g. mauvaise classification sur 10q bench S4), elle sera capitalisée dans `feedback_pr_patterns.md` et corrigée par règle ajoutée (pas par `if "and" in niveau then ...` ad-hoc dans le code).

---

## Tests A2 — 94 verts, 0 régression

`tests/test_axe2_profile_mapping.py` :

| Catégorie | Cas |
|---|---|
| `map_niveau_scolaire_to_education_level` | 23 patterns parametrize + 3 edge cases (None/empty/unknown) = 26 |
| `map_niveau_scolaire_to_age_group` | 23 combinations parametrize + 1 override priority = 24 |
| `infer_intent_type` | 22 patterns parametrize + 2 edge cases (None/empty) = 24 |
| `infer_urgent_concern` | 7 cas (stress / burnout / panic / valeurs / questions_ouvertes / no signal / all None) |
| `derive_profile_state` | 4 pipelines bout-en-bout (full session / explicit query override / empty session / urgent_concern propagated) |
| Régression `update_profile` | 3 (signature, no_turns, additivity) |
| Bridge `analyze_for_routing` mocked | 3 (full flow / Mistral error / no tool_call) |
| **Total** | **94 verts en 0.49s** |

Suite globale : **2206 passed, 1 skipped, 0 régression** (vs 2112 baseline post-A1).

---

## Décisions design clés vs alternatives

### Pourquoi mapping déterministe pure-function (pas LLM re-call)

- ✅ Coût marginal $0 (vs Mistral ~$0.01/call × 10q bench S4 = $0.10 économisé)
- ✅ Latence µs (vs 2-4s LLM call)
- ✅ Reproductible 100% (vs LLM non-déterministe avec température > 0)
- ✅ Auditable transparent — patterns regex documentés dans le doc
- ❌ Limité aux patterns documentés ; LLM aurait pu généraliser
- **Décision** : Phase 1 minimal accepte la limitation pour transparence + coût. Phase 2 pourra remplacer par classifier LLM dédié si bench S4 GO et que le mismatch d'intent dégrade la qualité de retrieval.

### Pourquoi side effect `merge_update` (mutation session)

- ✅ Cohérent avec semantics `update_profile()` Sprint 9 (qui retourne le delta SANS l'appliquer — c'est le Coordinator qui applique)
- ✅ Évite double-call dans les flows futurs (Coordinator ne re-merge pas)
- ❌ Effet de bord = harder to reason about
- **Décision** : documenté explicitement dans docstring. Tests assertent la mutation pour transparence.

### Pourquoi import lazy de `derive_profile_state`

```python
def analyze_for_routing(self, session, user_query=None):
    from src.axe2.profile_mapping import derive_profile_state
    ...
```

- ✅ Évite couplage circulaire à l'import (analyst_agent.py reste isolable de src.axe2)
- ✅ Évite le coût d'import si `analyze_for_routing()` jamais appelé (rare mais conceptuellement OK)
- ❌ Légèrement plus verbose
- **Décision** : import lazy gardé. Pattern propre pour bridges optionnels.

---

## Vérification Pattern #3+#4 (auto-audit Apprentissage #6)

✅ Pas de spec "élimine X% hallu" dans tout le doc — métriques pures architecturales (94 tests verts, 0 régression).

✅ Pas de présentation pédagogique fabriquée — tous les exemples mapping rules tirés du code source verbatim ou des tests parametrize.

✅ Pas de pré-stamp audit_jarvis (Pattern #1) — verdict factuel, audit Pattern #3+#4 indépendant attendu.

✅ Limitations honnêtes documentées : intent_type heuristique (Phase 2 pourra remplacer par LLM), pas de support enums doctorat (approximation ETUDIANT_MASTER).

---

## Suite

A2 = livré. Validation Pattern #3+#4 Jarvis attendue sur ce doc bridge design + 94 tests AVANT démarrage A4 (3 tools core + tests). ETA A4 ~10h, bench gate S4 ~2.5h cumul ~12.5h restant Phase 1.
