# Sprint 11 P1.1 — Analyse 3 options Strict Grounding renforcé (Phase 1)

**Date** : 2026-04-30
**Branche** : `feat/sprint11-P1-1-strict-grounding-stats` depuis main `2d36cb4`
**Ordre Jarvis** : `2026-04-30-2150-claudette-orientia-sprint11-P1-1-strict-grounding-stats-phase1`
**Phase** : 1 (analyse + reco) — Phase 2 (exécution) conditionnelle post-arbitrage Matteo

---

## §1 Rappel cible

Re-run E2E Item 4 (PR #111, SHA `2d36cb4`) a révélé via judge faithfulness Item 3 que **10/10 questions sortent INFIDELE** malgré la Directive 1 v4 actuelle. 39 entités flagged total.

**Distribution observée des hallucinations** (analyse sample 15 sur 39 flagged) :

| Type | Exemples Item 4 | Volume estimé |
|---|---|---|
| Stats chiffrées invention | "sélectivité 27 % (73 % mentions TB)", "100 % d'insertion (source : ONISEP)", "Salaire médian 1 790€" | ~60 % |
| Écoles / formations inventées | "EPF Montpellier", "Master Paris-Panthéon-Assas", "L.AS Sciences pour la Santé code 28675" | ~20 % |
| Procédures factuelles fausses | "Parcoursup acceptent étudiants prépa cours d'année", "Certaines licences rentrées janvier/février" | ~10 % |
| Attribution erronée | "AFEV propose coloc' à loyers modérés" (AFEV = tutorat pas logement) | ~5 % |
| Faits divers chiffrés | "Bac+5 accessible alternance après Bac S/STI2D" | ~5 % |

**⚠️ Challenge implicite du nom d'ordre "P1.1 stats"** : ~40 % des hallu Item 4 ne sont PAS des stats chiffrées (écoles inventées, procédures fausses, attribution erronée). Une option focalisée uniquement sur les chiffres en raterait la moitié.

**Directive 1 v4 actuelle** (`src/prompt/system.py` lignes 30-50) — wording exact :
- "Tu dois formuler ta réponse en utilisant **EXCLUSIVEMENT** les informations présentes dans les `<fiches_rag>`"
- "**STRICTEMENT INTERDIT** : Inventer des diplômes / formations / écoles + Inventer modalités d'admission + Inventer filières + Citer chiffres précis (taux, places, salaires, frais, dates) absents des fiches + Utiliser connaissances pré-entraînement"
- Fallback prescrit : "Je n'ai pas l'information [précise sur X] dans les sources" + suggérer alternative (CIO, ONISEP, conseiller)

**Constat empirique** : la directive v4 prescrit déjà strictement (interdit explicit + fallback prescrit), mais Mistral l'ignore en pratique sur 10/10 questions. Reformulation "plus stricte" sans changer d'angle d'attaque risque de produire le même résultat.

---

## §2 Option A — Reformulation Directive 1 prompt v5 (scaffolding + few-shots)

### Proposition wording v5

Passer d'une **directive d'interdiction** (échec empirique sur prompt v4) à une **directive de scaffolding actif + few-shot examples** illustrant les transformations attendues.

**Wording proposé** (cohérent structure Sprint 11 P0 prefix, ~40 lignes prompt) :

```
DIRECTIVE 1 — STRICT GROUNDING (anti-hallucination factuelle, v5 scaffolding)

Pour chaque affirmation factuelle de ta réponse (chiffre, nom propre,
date, procédure d'admission, attribution institutionnelle), applique
SYSTÉMATIQUEMENT ce check en 2 étapes :

Étape 1 — Vérification source :
  - Cette information est-elle textuellement présente dans une fiche du
    contexte <fiches_rag> ?
  - Si OUI → tu peux la citer telle quelle.
  - Si NON → passer à l'étape 2.

Étape 2 — Reformulation qualitative :
  - Remplace l'affirmation chiffrée/nominative précise par une formulation
    qualitative qui ne nécessite pas de source spécifique.
  - Si même la formulation qualitative est trompeuse → écris explicitement :
    « Cette information n'est pas disponible dans les sources que j'ai en
    contexte ; vérifie sur ONISEP / Parcoursup officiel / CIO. »

EXEMPLES (suis ce pattern strictement) :

❌ "L'IFSI de Lille a une sélectivité de 30 % en 2025"
✅ "L'IFSI de Lille est une formation publique en 3 ans (cf fiche).
   La sélectivité varie selon les années — vérifie sur Parcoursup."

❌ "Le Master Droit International Assas accepte sur dossier C1 anglais"
✅ "Les masters de droit international en France évaluent généralement
   le niveau d'anglais au dossier — pour la procédure exacte d'un master
   précis, contacte la fac concernée."

❌ "Salaire médian sortie LEA : 1 790€ net (source : DEPP 2024)"
✅ "Les salaires de sortie en LEA dépendent fortement du master
   complémentaire — InserSup donne des chiffres consultables si tu
   veux un point précis."

❌ "L.AS Sciences pour la Santé Sorbonne code Parcoursup 28675"
✅ "La L.AS Sciences pour la Santé existe à Sorbonne — cherche le code
   Parcoursup officiel sur le site dossierappel.parcoursup.fr"
```

### Effort estimé

| Item | ETA |
|---|---|
| Édition `src/prompt/system.py` Directive 1 v5 | 30 min |
| Tests `tests/test_prompt_system_sprint11_p0.py` mise à jour | 30 min |
| Re-run E2E `scripts/test_serving_e2e.py` (10 q + judge) | 15 min wall-clock + ~$0.51 |
| Doc verdict comparatif vs v4 baseline | 30 min |
| **Total Phase 2 si A** | **~2 h, ~$0.51** |

### Risque empirique

- **Hypothèse principale** : scaffolding actif (check 2 étapes) + few-shots concrets > directive d'interdiction passive. Hypothèse plausible (track record Item 1 prompt v4 a corrigé Q5+Q8 via Glossaire DIRECTIVE 2 = scaffolding similaire), mais **non garantie**.
- **Risque** : Mistral medium peut continuer à ignorer même un scaffolding actif si ses poids pré-entraînés priorisent la "fluidité conversationnelle" (citer chiffres précis pour paraître crédible). Capacité du modèle à suivre des contraintes complexes en system prompt = limite connue Mistral medium vs plus gros modèles.
- **Mesure de succès** : faithfulness mean Item 4-bis < 0.30 (vs 0.10 v4) ET au moins 5/10 questions FIDELE (vs 0/10 v4). Si A n'atteint pas ce seuil → escalader vers B en complément.

### Backward compat

- Modification additive du prompt prefix Sprint 11 P0. Pas de breaking change interface pipeline.
- A/B test possible vs prompt v4 via flag config (à coder en option si Matteo veut comparer empiriquement avant de remplacer).
- Tests pytest existants (`test_prompt_system_sprint11_p0.py`) à mettre à jour pour valider que les nouvelles structures (étape 1/2, few-shots) sont présentes.

---

## §3 Option B — Validation programmatique post-génération

### Architecture

Nouveau module `src/rag/anti_hallu_post_filter.py` :

```python
@dataclass
class PostFilterResult:
    answer_filtered: str
    flagged_numbers: list[str]      # chiffres flaggés non sourcés
    fallback_applied: bool
    debug: dict

def post_filter_answer(
    answer: str,
    fiches: list[dict],
    *,
    aggressive: bool = False,
) -> PostFilterResult:
    """Détecte les chiffres précis dans la réponse Mistral non sourcés
    dans les fiches RAG retrieved. Remplace par formulation qualitative
    si aggressive=True, sinon flag-only mode warning."""
```

Logique :
1. Extract chiffres de la réponse via regex `\d+(?:[,.]\d+)?\s*(?:€|%|\s*ans?|\s*mois|\s*places?|\s*heures?)`
2. Pour chaque chiffre extrait, lookup substring case-insensitive dans `fiches[i].nom + .detail + autres champs textuels`
3. Si chiffre absent fiches → flag (mode warning) ou remplace par formulation qualitative (mode aggressive)
4. Retourne `PostFilterResult` avec answer transformée + métriques

### Effort estimé

| Item | ETA |
|---|---|
| Module `anti_hallu_post_filter.py` (~200 l) + tests (~150 l) | 3 h |
| Intégration `OrientIAPipeline.answer()` (opt-in via flag) | 30 min |
| Bench faux positifs (codes Parcoursup, téléphones INSEE, dates) | 1 h |
| Re-run E2E `scripts/test_serving_e2e.py` 10 q | 15 min + $0.51 |
| Doc verdict | 30 min |
| **Total Phase 2 si B** | **~5-6 h, ~$0.51** |

### Risques identifiés (mitigation requise)

| Risque | Volume | Mitigation |
|---|---|---|
| Faux positifs codes Parcoursup `g_ta_cod=28675` | Élevé (URLs Parcoursup partout) | Whitelist regex pré-filtrage : `g_ta_cod=\d+`, `code_uai=\w+` |
| Faux positifs numéros téléphone INSEE 08 92 25 70 70 | Modéré | Whitelist pattern téléphone FR |
| Faux positifs dates précises (calendrier Parcoursup) | Faible | Whitelist months FR + années 2025-2027 |
| Faux positifs prix CROUS officiels (350€ studio) | Modéré | Whitelist `range monthly housing` si fiches CROUS retrieved |
| Vraies stats légitimes formulées différemment dans fiches | Modéré | Substring inclusive case-insensitive (cf bug v1 diag leak — éviter matching numérique 1-chiffre) |

**Pattern à éviter** (capitalisé hier dans `feedback_pr_patterns.md`) : matching numérique sur 1 chiffre = trop large. Exiger ≥ 2 chiffres OU contexte adjacent.

### Limitation scope

⚠️ **Option B isolée NE COUVRE PAS** :
- Écoles inventées non-chiffrées ("EPF Montpellier", "Master Paris-Panthéon-Assas")
- Procédures factuelles fausses ("Parcoursup mid-year")
- Attributions erronées ("AFEV agence logement")

→ Option B traite UNIQUEMENT les chiffres précis. Couvre ~60 % des hallu Item 4 selon distribution §1. Les ~40 % autres restent non traités → Mistral peut continuer à inventer des écoles et procédures.

### Backward compat

- Opt-in via flag init `OrientIAPipeline(post_filter=AntiHalluPostFilter())`. Default None = comportement original.
- Tests E2E pipeline existants (1998+) doivent rester verts. Le post-filter ajoute une étape post-`answer()` sans toucher au flow gen Mistral.
- Latence impact : ~50-100 ms supplémentaire per question (regex + lookup substring + remplacement éventuel).

---

## §4 Option C — Forcer citation source `[fiche_id]` (variante hybride proposée)

### Architecture proposée (variante hybride non-prévue dans verdict #111 §7.1)

L'option C originale (`Mistral doit ajouter [fiche_id] après chaque chiffre cité, validation au build`) souffre d'un problème UX majeur : `[fiche_id_42]` pollue la réponse user-facing.

**Variante proposée** : citation au BUILD-TIME pour métriques, MASKED user-side pour UX.

Pipeline :
1. Prompt v5-bis demande à Mistral d'ajouter `<src id="fiche_X"/>` après chaque chiffre précis (XML léger, pas markdown user)
2. Validation pre-render : parse `<src/>` tags, vérifier `fiche_X` ∈ ids fiches retrieved → log metric (% chiffres sourcés, % chiffres non sourcés)
3. Render user-side : strip `<src/>` tags via regex avant envoi
4. Audit trail : metric stockée pour bench / dashboard / paper INRIA

### Effort estimé

| Item | ETA |
|---|---|
| Modif prompt v5-bis avec instruction `<src/>` + few-shots | 1 h |
| Module `src/rag/source_validator.py` (parse + metric + strip) | 2 h |
| Tests parser robuste (XML mal formé, ids inventés, citations multiples) | 2 h |
| Intégration pipeline + render | 1 h |
| Re-run E2E + bench format markdown préservé | 30 min + $0.51 |
| Doc verdict + dashboard métrique sourcing | 1 h |
| **Total Phase 2 si C** | **~7-8 h, ~$0.51** |

### Risques

- **Mistral peut casser le format `<src/>`** (tag mal placé, id inventé, escape XML). Parser doit être tolérant + log incidents.
- **Latence ↑** : génération avec contraintes XML peut ralentir Mistral (estim. +5-10 % latence).
- **Audit trail INRIA = atout méthodologique fort** : citation explicite démontre la grounding scientifiquement (avantage paper publication / soumission INRIA Mai).

### Backward compat

- Opt-in via flag `enable_source_citation=True` dans pipeline. Default False = pas de citation.
- A/B test possible vs prompt v4 baseline.
- Tests existants doivent rester verts (citation strip avant envoi).

---

## §5 Tableau comparatif

| Dimension | Option A (prompt v5) | Option B (post-filter) | Option C (citation hybride) |
|---|---|---|---|
| **Effort dev** | ~2 h | ~5-6 h | ~7-8 h |
| **Coût Phase 2** | ~$0.51 | ~$0.51 | ~$0.51 |
| **Latence runtime impact** | 0 (prompt seul) | +50-100 ms (regex+lookup) | +5-10 % génération XML |
| **Couverture hallu Item 4** | ~95 % (chiffres + écoles + procédures via scaffolding) | ~60 % (chiffres seulement) | ~95 % (citation systématique) |
| **Risque échec empirique** | Modéré (Mistral peut ignorer scaffolding) | Faible (déterministe) | Élevé (Mistral peut casser XML) |
| **Backward compat** | Strict (modif prompt additive) | Opt-in flag | Opt-in flag |
| **ROI MVP démo INRIA (12 mai)** | ⭐⭐⭐ Rapide, large couverture | ⭐⭐ Lent, étroit | ⭐ Long, mais audit trail INRIA paper or |
| **ROI paper publication INRIA** | ⭐⭐ Anecdotique | ⭐⭐⭐ Mesure programmatique | ⭐⭐⭐⭐ Citation explicite défendable |
| **Complexité maintenance** | Faible (prompt) | Modérée (whitelists faux positifs à gérer) | Élevée (parser + render) |

---

## §6 Reco terrain Claudette + plan d'attaque Phase 2

### Reco principale : Option A (scaffolding + few-shots), avec scope élargi

**Convergence avec biais Jarvis (A)** confirmée empiriquement par mon analyse, MAIS avec 2 nuances :

1. **Scope élargi** : la directive v5 doit couvrir **tous les types factuels** (chiffres + écoles + procédures + attributions), pas uniquement les stats. ~40 % des hallu Item 4 ne sont pas chiffrées.

2. **Approche scaffolding ≠ "INTERDIT plus fort"** : Mistral ignore déjà l'interdit v4. Reformulation passive risque de reproduire l'échec. La proposition §2 utilise un check 2-étapes actif + few-shots concrets — pattern qui a fonctionné dans Item 1 (Glossaire DIRECTIVE 2 a corrigé Q5+Q8 par exemple-driven, pas par interdit).

### Plan d'attaque Phase 2 (si Matteo go A)

1. **Branche existante** `feat/sprint11-P1-1-strict-grounding-stats` (déjà créée Phase 1, doc-only commit)
2. **Édition `src/prompt/system.py`** : remplacer Directive 1 v4 par v5 scaffolding (wording §2)
3. **Tests `tests/test_prompt_system_sprint11_p0.py`** : ajouter 3-5 tests validant la présence des étapes 1/2 + few-shots clés
4. **Re-run E2E `scripts/test_serving_e2e.py`** sur 10 questions chantier E avec prompt v5 + judge Item 3
5. **Verdict comparatif `docs/sprint11-P1-1-rerun-e2e-vs-v4-2026-04-30.md`** : tableau v4 vs v5 par question + analyse hallu corrigées vs persistantes + verdict empirique
6. **Critère succès** : faithfulness mean v5 < 0.30 (v4=0.10) ET ≥ 5/10 questions FIDELE — si non atteint → escalation vers B en Phase 3 conditionnelle
7. **PR #112 ready-for-review** + ping order-done-phase-2

### Reco secondaire : escalation conditionnelle Phase 3 vers B

Si Phase 2 (option A) ne suffit pas (judge persiste à flag chiffres précis) → ajouter Option B en complément (post-filter sur chiffres uniquement, après prompt v5). Architecture défensive en couches :
- Couche 1 : prompt v5 scaffolding (option A) — réduit la fréquence des inventions
- Couche 2 : post-filter B sur chiffres résiduels — catch ce qui passe la couche 1

Total cumul effort si Phase 3 nécessaire : 2h (A) + 5-6h (B) = **~7-8 h** étalés sur 1-2 jours.

### Option C écartée (avec rationale honnête)

- Effort 7-8h pour une couverture similaire à A
- Risque élevé Mistral casse le format XML
- ROI INRIA paper réel mais **pas pour MVP démo 12 mai** (deadline trop courte)
- À reconsidérer Sprint 12+ si publication paper INRIA Mai-Juin se confirme et qu'on veut démontrer scientifiquement la grounding

---

## §7 Challenge explicite biais Jarvis (cohérent avec ma capitalisation hier "ne pas rubber-stamp")

### Convergence

Je suis d'accord avec la reco Jarvis **A en première intention**. Track record Item 1 (prompt v4 corrige Q5+Q8) prouve qu'une reformulation prompt PEUT corriger des hallu spécifiques. Plausible que A v5 corrige les chiffres aussi.

### Nuance 1 — Scope P1.1 trop étroit

Le nom d'ordre "Strict Grounding stats" suggère focus chiffres. Mais analyse Item 4 §1 montre 40 % hallu non-chiffrées. Si Phase 2 implémente A "scope chiffres only" → on passe à côté.

→ **Recommendation** : redéfinir scope Phase 2 = "Strict Grounding tout factuel non sourcé" (chiffres + écoles + procédures + attributions). Modif additive dans le wording proposé §2 le couvre déjà — pas de surcout.

### Nuance 2 — Risque empirique non négligeable

Mistral medium ignore déjà directive v4 INTERDIT formel. Hypothèse "scaffolding + few-shots = mieux" plausible mais non garantie. **Si bench Phase 2 montre faithfulness ≥ v4** (pas d'amélioration ou régression) → flag explicite limit Mistral medium + escaler B (post-filter déterministe couvre les chiffres au moins) OU envisager modèle plus capable (Mistral Large, Sonnet 4.6) — mais ça touche au pillar souveraineté FR.

### Nuance 3 — Scope démo vs paper

A est optimal pour MVP démo 12 mai (ETA <2h, large couverture). C est optimal pour paper INRIA (audit trail méthodologique).

Si Matteo priorise paper INRIA Mai-Juin → C variante hybride mérite considération malgré effort 7-8 h. À arbitrer selon ses priorités.

### Synthèse challenge

| Si Matteo priorise | Reco honnête |
|---|---|
| MVP démo 12 mai + lancement RidKod | **Option A** (scope élargi) — convergence avec biais Jarvis |
| Paper INRIA Mai-Juin | **Option C variante hybride** — mérite plus d'effort (citation explicite défendable scientifiquement) |
| Couverture maximale en pipeline | **Option A + B en cascade** (Phase 2 + Phase 3 conditionnelle) |
| Ressources limitées + verdict directionnel rapide | **Option A seule** (cf scope élargi §2) |

---

*Doc analyse Phase 1 livrée ~30 min après order. Phase 2 conditionnelle attend arbitrage Matteo via Jarvis. Standby.*
