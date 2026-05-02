# Sprint 12 axe 2 — Golden Pipeline v2 (filter soft) verdict

> **Statut** : VERDICT EMPIRIQUE FINAL — **NO-GO empirique 5/10** mais **bruit judge dominant** (signal réel mais marginal).
> **Date** : 2026-05-01
> **Branche** : `feat/sprint12-axe-2-golden-pipeline` (étape 6 même PR #117)
> **Spec ordre** : 2026-05-01-2247-claudette-orientia-sprint12-axe-2-golden-pipeline-v2-filter-soft
> **V1 référence** : `docs/sprint12-axe-2-golden-pipeline-2026-05-01.md` (NO-GO 6/10)

---

## TL;DR

- **Verdict empirique v2** : NO-GO 5/10 (golden ≥ enriched). Wins golden 4/10, enriched 5/10, ties 1/10.
- **Effet réel mais marginal** : `diversite_geo` golden +3 (5→8) — fix a un signal mais **insuffisant pour atteindre la cible ≥12**.
- **Bruit judge dominant** : variance contrôle enriched (système identique) = stdev 2.60 par question, range [-4,+5]. Cumul ±10-15 = bruit. Single-judge 10q **incapable de distinguer un changement réel <13 points cumul d'un bruit**.
- **Reco Sprint 13** : pivoter vers **Option 2 (ProfileState plus permissif)** OU **Option C (abandon partiel)**. Pas d'acharnement sur boost ×1.3.

---

## Changement v1 → v2

**Avant (v1, étape 4)** : `apply_metadata_filter` strict bloquant, drop des fiches non-matching le profil.

**Après (v2, étape 6)** : `apply_metadata_boost` soft, multiplie le score des matches par `metadata_boost_factor=1.3`, **aucun drop**.

### Implémentation `apply_metadata_boost` (`src/rag/metadata_filter.py`)

```python
def apply_metadata_boost(retrieved, criteria, boost_factor=1.3):
    """Boost score ×factor des matches, aucun drop. Re-trie par score desc."""
    if criteria.is_empty() or boost_factor == 1.0:
        return list(retrieved)
    boosted = []
    for item in retrieved:
        if _matches(item.get("fiche") or {}, criteria):
            new_item = dict(item)
            new_item["score"] = float(new_item.get("score", 0)) * boost_factor
            new_item["_boosted"] = True
            boosted.append(new_item)
        else:
            boosted.append(item)
    boosted.sort(key=lambda it: it.get("score", 0), reverse=True)
    return boosted
```

Wiring `_retrieve_for_subquery` : remplace `apply_metadata_filter` par `apply_metadata_boost` quand `enable_metadata_filter=True`. Plus de sur-retrieve ×2 (pas de drop à absorber).

### Tests

- `TestRetrieveWithMetadataBoost` (renommé de `TestRetrieveWithMetadataFilter`) : 5 tests adaptés
- `TestBoostPreservesDiversite` (NEW garde-fou) : 4 tests vérifiant aucun drop, scores préservés non-matches, re-tri correct
- Suite globale : **2 300 passed**, 0 régression

---

## Méthodologie bench v2

- **Reproductible** : 10 mêmes questions hold-out v1 (split=test)
- **Systems** : `pipeline_agent_golden` v2 (boost soft) vs `our_rag_enriched` (legacy strict, identique v1)
- **Judge** : Claude Sonnet 4.5 multi-aspect rubric (single-judge MVP, identique v1)
- **Backup v1** : `results/bench_sprint12_axe2_golden_validation/*_v1_filter_strict.json`
- **Incident technique** : A7 a généré 0 char au 1er run (transient Mistral, idem B10 v1). A7 droppé puis regenerate. Re-run isolé OK 2520 chars.

---

## Comparaison v1 vs v2 — par aspect (cumul 10q)

| Aspect | v1 G | v2 G | Δ G | v1 E | v2 E | Δ E |
|---|---|---|---|---|---|---|
| neutralite | 26 | 25 | -1 | 22 | 25 | **+3** |
| realisme | 25 | 23 | -2 | 24 | 25 | +1 |
| sourcage | 22 | 24 | **+2** | 20 | 21 | +1 |
| **diversite_geo** | **5** | **8** | **+3** ⭐ | **16** | **16** | 0 |
| agentivite | 28 | 25 | -3 | 26 | 29 | **+3** |
| decouverte | 19 | 18 | -1 | 16 | 17 | +1 |
| **TOTAL** | **125** | **123** | **-2** | **124** | **133** | **+9** |

**Lecture clé** :
- Sur l'aspect cible `diversite_geo`, le boost soft livre +3 (5→8). Réel mais loin de la cible ≥12. Le boost ×1.3 nudge insuffisamment les fiches non-matching dans le top-K.
- Le cumul golden a baissé de 2 points (125→123) — dans la zone de bruit (cf §Variance).
- Le cumul enriched a monté de 9 points (124→133) — système identique, donc **pur bruit judge**.

---

## Variance & bruit du judge — découverte critique

Sur le système enriched (identique entre v1 et v2 — pas de change technique côté retrieval/génération/prompt), le judge Claude Sonnet 4.5 produit des scores qui varient :

| Statistique | Valeur |
|---|---|
| Moyenne delta enriched | +0.90 |
| Écart-type enriched | **2.60** |
| Range enriched | [-4, +5] |

**Variance golden (vraie change v1→v2)** :

| Statistique | Valeur |
|---|---|
| Moyenne delta golden | -0.10 |
| Écart-type golden | **3.00** |
| Range golden | [-7, +4] |

**Conclusion méthodologique** : variance enriched (2.60) ≈ variance golden (3.00). L'écart cumul v1/v2 (-2 sur golden, +9 sur enriched) est dans le bruit du judge non-déterministe. **Single-judge 10q est incapable de distinguer un changement <13 points cumul d'un bruit aléatoire.**

---

## Per-question breakdown (10q)

| QID | v1 G | v1 E | v2 G | v2 E | Win v1 | Win v2 |
|---|---|---|---|---|---|---|
| A6 | 15 | 7 | 17 | 11 | 🟢 | 🟢 |
| A9 | 13 | 9 | 13 | 5 | 🟢 | 🟢 |
| A12 | 13 | 12 | 12 | 11 | 🟢 | 🟢 |
| A10 | 13 | **14** | **16** | 14 | 🔴 | 🟢 (**flip enriched→golden**) |
| A11 | **16** | 12 | 9 | **17** | 🟢 | 🔴 (**flip golden→enriched**) |
| A7 | 13 | 12 | 12 | 12 | 🟢 | 🟡 (tie, post fix crash) |
| A8 | 8 | **16** | 12 | **16** | 🔴 | 🔴 (golden +4 mais loss) |
| B10 | 13 | **16** | 13 | **17** | 🔴 | 🔴 |
| B11 | 11 | 11 | 11 | **14** | 🟡 | 🔴 |
| B12 | 10 | **15** | 9 | **16** | 🔴 | 🔴 |

Wins golden : 5 → 4 (-1). Wins enriched : 4 → 5 (+1). Tie : 1 → 1.

**Flips notables** :
- A10 enriched→golden (golden +3 sur cette question, vraisemblable signal réel)
- A11 golden→enriched (golden -7 sur cette question — possiblement bruit, possiblement boost qui a perturbé)

---

## Sample 3 questions verbatim Pattern #4

### Cas 1 — A8 "écoles design en France" (cible v1 catastrophique G=8 E=16)

V1 strict : G=8 E=16 (-8 dramatique, golden monopolisait IDF, diversite_geo 0)
V2 boost : G=12 E=16 (-4, golden gagne en sourcage et agentivite mais loss persistante)

Verdict A8 : amélioration mesurable +4 mais loss reste forte. Le boost a aidé sans suffire.

### Cas 2 — A11 "audit, quelles écoles" (régression v2)

V1 strict : G=16 E=12 (+4, win golden franc)
V2 boost : G=9 E=17 (-8, flip dramatique)

Lecture : sur cette question, le boost a pu pousser des fiches profil-cohérentes mais pas les meilleures écoles d'audit dans le top-K. OU pur bruit judge sur cette question (variance ±5 plausible). Sans multi-judge, impossible de trancher.

### Cas 3 — A6 "développeur web full-stack" (consistance win golden)

V1 strict : G=15 E=7 (+8)
V2 boost : G=17 E=11 (+6, win confirmé)

Lecture : sur les questions où le profil est très cohérent avec la query (info/dev), le boost soft maintient ou améliore. Pas de régression.

---

## Décision finale v2 — NO-GO empirique mais avec nuance

### Verdict honnête

- **NO-GO strict** : golden ≥ enriched 5/10 (cible ≥7). Pire que v1 (6/10).
- **MAIS** : différence cumul v1/v2 dans le bruit du judge.
- `diversite_geo` a réellement bougé (+3) mais marginal.

### NE PAS merger PR #117 sur cette base

Le boost ×1.3 ne livre pas un GO clair. Pas d'acharnement sur la même direction.

### 2 options Sprint 13 (par recommandation)

#### Option 2 (recommandée) — ProfileState plus permissif

Modifier `derive_filter_criteria_from_profile_state` :
- Ne dériver `region` que si la query mentionne explicitement un nom de région ou ville française (matching texte query).
- Ne dériver `secteur` que si `sector_interest` a au moins 1 entrée NON ambiguë dérivée explicitement de la query (pas du profil libre).

Effort 0.5j. Hypothèse : éliminer le filter biais sur les questions nationales (A8, B12) tout en préservant le profil-aware sur les questions explicitement régionales.

**Méthodologie révisée requise** : avant tout bench Option 2, **multi-judge OBLIGATOIRE** (Claude Sonnet + GPT-4o + Haiku, comme Run F+G). Single-judge 10q a un bruit qui rend tout verdict <13 points cumul indistinguable.

#### Option C — Abandon partiel

Conclure que le golden mode `enable_metadata_filter` (strict ou soft) n'apporte pas de gain mesurable. Garder `our_rag_enriched` canonical.

Préserver les acquis golden mode utilisables :
- Backstop B soft (`src/backstop/`) — déjà sur main, exploitable directement
- FetchStat in-loop — déjà dans `pipeline_agent.py`, peut être backporté à `OrientIAPipeline`
- A1+A2 contracts/bridge (`src/axe2/`) — utilisables pour Phase 2 agentic Sonnet 4.5 future
- Corpus combined (`formations_golden_pipeline.json`) — toujours utilisable comme corpus alternatif si rebench

PR #117 close sans merge (ou converti en draft).

---

## Recommandation Claudette finale

**Option C** — abandon partiel.

**Pourquoi** : le bench v2 montre que l'ajustement boost soft n'a pas livré de delta mesurable au-dessus du bruit. La méthodologie single-judge 10q ne permet pas de discriminer signal réel < 13 points cumul. Investir Sprint 13 dans Option 2 nécessiterait d'abord upgrader la méthodologie (multi-judge + n>30) — coût estimé +$10-15. Le ROI vs garder enriched canonical n'est pas évident.

Préserver A1+A2 contracts/bridge cherry-picks pour utilisation future Phase 2 agentic. Le travail Sprint 12 axe 2 reste réutilisable même en option C.

**Décision finale appartient à Matteo via Jarvis.**

---

## Apprentissages

- **#15 (NEW)** Single-judge bench avec n=10 a un bruit dominant (stdev ~2.6 par question). Pour distinguer un signal réel d'un bruit, la méthodologie doit être : (a) multi-judge (≥2-3 juges) avec inter-judge κ documenté, OU (b) n≥30 questions, OU (c) acceptance d'un delta cumul ≥3×stdev pour conclure GO/NO-GO. Run F+G a fait (a)+(b) — d'où sa robustesse. Bench MVP 10q single-judge ne convient que pour smoke-test rapide, pas pour verdict définitif.
- **#16 (NEW)** Boost ×1.3 sur metadata filter améliore marginalement `diversite_geo` (+3) mais ne suffit pas à compenser un over-filter conceptuel sur les questions nationales. La cause racine n'est pas la *force* du filter mais sa *présence* dès qu'un profil libre est inféré. La fix doit être en amont : ne pas inférer region/secteur de manière agressive depuis profil libre.

---

## Coûts cumul Sprint 12 axe 2 finaux

- Étape 2 embedding : ~$1.2
- Étape 4 bench v1 : ~$0.65
- Étape 6 bench v2 (incl. re-run A7) : ~$0.70
- **Total : ~$2.55** (vs estimé $8-12 plan)

---

## Artefacts livrables (additions étape 6)

- `src/rag/metadata_filter.py` : `apply_metadata_boost()` (NEW)
- `src/agent/pipeline_agent.py` : flag `metadata_boost_factor=1.3` (NEW)
- `tests/test_pipeline_agent_golden.py` : `TestRetrieveWithMetadataBoost` (renommé) + `TestBoostPreservesDiversite` (NEW)
- `results/bench_sprint12_axe2_golden_validation/*_v1_filter_strict.json` (archive v1)
- `results/bench_sprint12_axe2_golden_validation/{responses_blind,judge_scores,verdict_raw}.json` (v2 actifs)
- `docs/sprint12-axe-2-golden-pipeline-v2-filter-soft-2026-05-01.md` (ce verdict)

---

*Plan de fond : `docs/GOLDEN_PIPELINE_PLAN.md`. V1 verdict : `docs/sprint12-axe-2-golden-pipeline-2026-05-01.md`.*
