# Sprint 11 P0 Item 3 — LLM-Judge Faithfulness (verdict)

**Date** : 2026-04-29
**Branche** : `feat/sprint11-P0-llm-judge-faithfulness` (depuis main `c75b1b5`)
**Ordre Jarvis** : `2026-04-29-2055-claudette-orientia-sprint11-P0-item3-llm-judge-faithfulness`
**Modèle juge** : `claude-haiku-4-5` via subprocess (CI/dev offline UNIQUEMENT, pas runtime prod — souveraineté FR)

---

## TL;DR

- ✅ **Module `scripts/judge_faithfulness.py`** livré (~280 lignes, dataclass + parser robuste + fallback graceful + CLI demo)
- ✅ **3/3 hallucinations Matteo détectées** (Q5 IFSI / Q8 DEAMP / Q10 Terminale L) — score < 0.5 sur tous
- ✅ **2/2 cas clean synthétiques validés** — score ≥ 0.8
- ✅ **24 tests offline + 5 tests réels passent** (Haiku subprocess, 120s wall-clock, $0.005)
- ✅ **Bench A/B vs regex naïf** : judge recall 100% (équivalent regex sur ground truth) MAIS apport qualitatif décisif (justifications + flags individuels vs regex saturé 73-97%)
- ✅ **Intégré dans `scripts/test_serving_e2e.py`** — remplace l'ancien `measure_pollution()` regex
- ✅ **`measure_pollution()` conservée dans le module** pour le bench script (référence)

**Décision Item 3** : remplacement validé. Le judge devient la métrique faithfulness officielle CI/audit OrientIA.

---

## 1. Architecture du module

`scripts/judge_faithfulness.py` — 3 surfaces publiques :

```python
@dataclass
class FaithfulnessVerdict:
    score: float                # 0..1, 1.0 = fidèle, 0.0 = très infidèle, 0.5 = doute
    flagged_entities: list[str]
    justification: str
    raw_verdict: str            # "FIDELE" | "INFIDELE" | "UNKNOWN"
    parse_errors: list[str]
    latency_ms: int
    error: Optional[str]
    model: str
    prompt_chars: int

def judge_faithfulness(question, answer, fiches, *, model, timeout_s, max_fiches)
    -> FaithfulnessVerdict
```

Internals :
- `_call_judge()` — subprocess `claude --print --model <model>` avec stdin=prompt, timeout, returncode handling
- `_parse_judge_output()` — regex extraction VERDICT/ELEMENTS/JUSTIFICATION + fallback JSON parser → regex string extraction
- `_score_from_parsed()` — calibration empirique :
  - FIDELE + 0 elements → 1.0
  - FIDELE + N>0 elements → 0.7
  - INFIDELE + 0 → 0.4 (douteux)
  - INFIDELE + 1 → 0.35
  - INFIDELE + 2 → 0.20
  - INFIDELE + 3+ → 0.0
  - UNKNOWN → 0.5

Choix calibration : la spec exige ground truth `score < 0.5` (donc INFIDELE + 1+ flagué = 0.35 < 0.5 ✅) et clean cases `score ≥ 0.8` (donc FIDELE + 0 = 1.0 ≥ 0.8 ✅).

---

## 2. Variantes de prompt itérées (3 testées sur ground truth)

Spec exige *"prompt itéré 2-3 variantes — pas écrit en 30 sec ça marche"*. 3 variantes essayées (script spike one-shot supprimé après itération, contenu capturé ci-dessous) :

### v1 — Prompt minimal direct
- 36 lignes, structuré (TÂCHE / À flagger / NE PAS flagger / FORMAT STRICT)
- Pas de connaissance officielle externe injectée

### v2 — Prompt avec connaissance officielle injectée (RETENU ✅)
- 48 lignes, ajoute section *"Cas particulier — connaissance officielle française"* avec faits durcis :
  - Réforme bac 2021 / DEAMP 2016 / IFSI Parcoursup 2019 / PASS L1
- Permet au juge de sortir du seul "answer ⊂ fiches" et de catcher les contradictions historiques

### v3 — Prompt lourd à exemples
- 60 lignes, exemples FIDELE/INFIDELE inline
- Plus brittle (exemples corpus-spécifiques), prompt plus long → coûteux

### Résultats empiriques (4 cas : Q5 / Q8 / Q10 hallu + Q4 borderline)

| Variante | Q5 IFSI | Q8 DEAMP | Q10 Term L | Q4 borderline | Score qualitatif |
|---|---|---|---|---|---|
| **v1** | INFIDELE 6 elem (0.0) ✅ | INFIDELE 9 (0.0) ✅ | INFIDELE 9 (0.0) ✅ | INFIDELE 11 (0.0) | basique |
| **v2 ★** | INFIDELE 5 (0.0) ✅ | INFIDELE 7 (0.0) ✅ + cite "DEAMP fusionné DEAES 2016" | INFIDELE 6 (0.0) ✅ | INFIDELE 7 (0.0) | **explicite officiel** |
| **v3** | INFIDELE 7 (0.0) ✅ | INFIDELE 7 (0.0) ✅ | INFIDELE 6 (0.0) ✅ | INFIDELE 1 (0.35) | conservateur |

**v2 retenu** car :
1. Recall 3/3 ground truth (équivalent v1 et v3)
2. Justifications explicites citant la connaissance officielle ("DEAMP fusionné en 2016") = audit trail Matteo gold
3. Compromis flagging Q4 (7 vs 11 v1 / 1 v3) — pas de sur-réaction ni de manque
4. Prompt plus court que v3 → moins coûteux + moins brittle

---

## 3. Tests pytest (24 offline + 5 réels)

`tests/test_judge_faithfulness.py` — 29 tests :

**Ground truth OBLIGATOIRE (3 réels, ~30s chacun)** :
- `test_ground_truth_q5_ifsi_hallu_detected` : score < 0.5 ✅
- `test_ground_truth_q8_deamp_hallu_detected` : score < 0.5 ✅
- `test_ground_truth_q10_terminale_l_hallu_detected` : score < 0.5 ✅

**Cas clean synthétiques (2 réels, ~30s chacun)** :
- `test_clean_short_answer_directly_sourced` : "PASS Lille = Licence 1 an" + fiche identique → score ≥ 0.8 ✅
- `test_clean_explicit_advice_only` : 100% conseil pas d'affirmation → score ≥ 0.8 ✅

**Edge cases mocked (offline)** — fallback graceful, pas de subprocess :
- Answer vide → FIDELE 1.0 sans appel
- Whitespace only → FIDELE 1.0
- Subprocess timeout → score 0.5 + error="timeout"
- returncode != 0 → score 0.5 + error stderr
- claude CLI not found → score 0.5 + error explicite
- VERDICT pattern not matched → UNKNOWN + parse_errors documentés
- ELEMENTS JSON malformé (quotes mal échappées) → fallback regex extract strings ✅
- JUSTIFICATION manquante → empty string + parse_errors notés, verdict utilisable
- VERDICT: OUI/NON acceptés en alias FIDELE/INFIDELE
- Fiches vides ([]) → "(aucune fiche)" placeholder, judge call tente quand même
- Numeric claims entre quotes → parser extrait correctement

**Unit tests (offline)** — `_score_from_parsed`, `fiche_to_text`, `build_fiches_text` (dedupe par id, max_fiches respecté), `FaithfulnessVerdict.to_dict()` roundtrip.

**Skip env var** : `OFFLINE_JUDGE_TESTS=1 pytest tests/test_judge_faithfulness.py` skip les 5 réels (utile pour itération rapide locale).

---

## 4. Bench A/B vs regex naïf — 10 questions chantier E

Cf rapport complet : `docs/sprint11-P0-item3-bench-judge-vs-regex-2026-04-29.md`

### Résumé tableau

| Métrique | Recall ground truth (n=3) | Faux positifs FIDELE (n=0) | Latence médiane | Coût |
|---|---|---|---|---|
| **LLM-Judge** | 3/3 (100%) | 0 (n/a — aucun FIDELE certifié) | 33s | $0.001/eval |
| **Regex naïf** | 3/3 (100%) | 0 (idem) | <13ms | gratuit |

### Mais — analyse qualitative décisive

Sur les 10 questions chantier E, le regex naïf flag à `pollution_rate ∈ [73%, 97%]` — **saturé**, métrique morte. La nuance ground truth se perd dans le bruit.

Le judge LLM apporte 3 valeurs qualitatives critiques :
1. **Justification interprétable** : Matteo lit "DEAMP supprimé en 2016, fusionné DEAES" et confirme en 5 secondes au lieu de pondérer un % opaque
2. **Granularité élément-level** : la liste `flagged_entities` cite des affirmations textuelles précises (vs juste un compteur)
3. **Connaissance officielle française intégrée** : catch les contradictions historiques (réforme bac 2021, IFSI Parcoursup 2019) que le regex ne peut PAS détecter par construction

### Regex pollution — pourquoi mort sur ce corpus

Le regex extrait des entités majuscules / acronymes / chiffres / dates et flag celles absentes des fiches. Mais les réponses Mistral utilisent BEAUCOUP de "(connaissance générale)" non marqué (URLs Parcoursup hardcodées, prix de prépas approximatifs, etc.) — tout ça est légitime selon la doctrine prompt v3.2 mais flagué par le regex. Résultat : pollution_rate > 70% sur tous les cas.

---

## 5. Limitations méthodologiques honnêtes

1. **Sample ground truth = 3 hallu seulement** (audit qualitatif Matteo n=10, 3 critiques flaggés). Le recall calculé sur n=3 = signal faible. Étendre l'audit Matteo (Sprint 11 P1+ ?) avant conclusions définitives.
2. **Aucun cas FIDELE certifié dans les 10 questions** (toutes ont au moins une affirmation borderline non sourcée). Les "clean tests" sont donc synthétiques (PASS Lille = 1 an), pas issus de production réelle.
3. **Calibration score 0.5 = arbitraire** mais respectueuse de la spec. Si Matteo veut un seuil plus strict (ex: 0.3 = flagué), la formule `_score_from_parsed` est centralisée dans le module.
4. **Souveraineté française non respectée** par claude-haiku-4-5 — décision Matteo 2026-04-29 18:54 UTC : OK uniquement parce que CI/dev offline (aucune donnée user transférée). Si glissement futur vers runtime prod : refacto vers Mistral ou modèle souverain (Sprint 12+).
5. **Variance non mesurée** : même prompt + même input peut donner verdict différent (LLM stochastique). Pour audit rigoureux, ajouter triple-run + IC95 (Sprint 11 P1 ?). Pour CI/sanity-check : single-run suffit.
6. **Latence subprocess 28-40s/eval** = bottleneck pour tests CI. Pour 1 000 questions bench (Sprint 12 ?) → ~10h sequential, parallelisation nécessaire.

---

## 6. Coût et performance empirique

| Item | Coût | Latence | Notes |
|---|---|---|---|
| 1 eval judge | ~$0.001 | 28-40s wall-clock | subprocess CLI bootup ~5-10s |
| Bench A/B (10 q) | $0.01 | 5 min | sequentiel |
| Tests pytest réels (5) | $0.005 | 2 min | sequentiel |
| Spike 3 variantes × 4 cas | $0.012 | 8 min | itération prompt |
| **Total dev session** | **~$0.03** | **15 min** | bien sous le budget $0.10 |

---

## 7. Décision finale & next steps

### Item 3 décision

**REMPLACÉ** : `scripts/test_serving_e2e.py` n'utilise plus `measure_pollution()` (regex naïf). À la place : `judge_faithfulness()` per question.

`measure_pollution()` est conservée dans le module pour le bench script (référence) mais marquée comme legacy dans le commentaire d'intégration.

### Sprint 11 P0 plan global (état)

| Item | Status | PR |
|---|---|---|
| Item 1 — refonte SYSTEM_PROMPT v4 (Strict Grounding + Glossaire + Progressive Disclosure) | ✅ MERGED | #108 |
| Item 2 — buffer mémoire short-term + REPL CLI + Directive 4 format adaptatif | ✅ MERGED | #109 |
| **Item 3 — LLM-Judge Faithfulness** | ✅ **READY-FOR-REVIEW** | **#110 (this PR)** |
| Item 4 — full re-run 10 questions chantier E avec prompt v4 + judge | À planifier post-merge #110 (coût ~$1, ETA 15 min) |

### Suggestions Item 4 (hors scope cet ordre)

Une fois #110 mergée :
1. Re-run `scripts/test_serving_e2e.py` complet (Mistral + judge sur 10 questions, $1, 15 min)
2. Comparer faithfulness scores pré-Sprint11 (chantier E baseline) vs post-Sprint11 (prompt v4 + judge)
3. Mesurer si la refonte prompt Item 1 a effectivement réduit les hallu sur les 7 questions non encore auditées
4. Étendre l'audit qualitatif Matteo (n=3 → n=10) pour calibrer le seuil judge plus précisément

---

*Doc généré par Claudette pour PR #110 — `feat/sprint11-P0-llm-judge-faithfulness`. Audit Jarvis indépendant attendu avant merge.*
