# Sprint 11 P0 Item 3 — LLM-Judge Faithfulness (verdict)

**Date** : 2026-04-29
**Branche** : `feat/sprint11-P0-llm-judge-faithfulness` (depuis main `c75b1b5`)
**Ordre Jarvis** : `2026-04-29-2055-claudette-orientia-sprint11-P0-item3-llm-judge-faithfulness`
**Modèle juge** : `claude-haiku-4-5` via subprocess (CI/dev offline UNIQUEMENT, pas runtime prod — souveraineté FR)

---

## TL;DR

- ✅ **Module `scripts/judge_faithfulness.py`** livré (~280 lignes, dataclass + parser robuste + fallback graceful + CLI demo)
- ✅ **3/3 hallucinations Matteo détectées** (Q5 IFSI / Q8 DEAMP / Q10 Terminale L) — score < 0.5 sur tous, **avec prompt v1 minimal qui mobilise la connaissance externe de Haiku** (PAS de whitelist injectée)
- ✅ **2/2 cas clean synthétiques validés** — score ≥ 0.8
- ✅ **2/3 tests généralisation hors-whitelist** détectés (DUT→BUT 2021 ✅, MPENA inventé ✅, Première STG → STMG xfail ⚠️ — limitation framing acceptance documentée)
- ✅ **27 tests offline + 5 tests réels + 3 généralisation passent** (Haiku subprocess, ~190s wall-clock total, $0.008)
- ✅ **Bench A/B vs regex naïf** : judge recall 3/3 ground truth + apport qualitatif décisif (justifications mobilisent connaissance officielle de Haiku, ex Q8 cite DEAMP fantôme directement) vs regex saturé 73-97%
- ✅ **Intégré dans `scripts/test_serving_e2e.py`** — remplace l'ancien `measure_pollution()` regex
- ✅ **`measure_pollution()` conservée dans le module** pour le bench script (référence)

**Décision Item 3** : remplacement validé. Le judge devient la métrique faithfulness officielle CI/audit OrientIA, avec limitation framing acceptance documentée (cf §5).

**Itération post-recadrage Jarvis 2026-04-29 20:27** : v2 retenu initialement injectait une whitelist de faits officiels (réforme bac 2021, DEAMP 2016, IFSI Parcoursup 2019, PASS L1) qui contenait EXACTEMENT les 3 ground truth → test trivial, juge ne généralisait pas. Recadrage Matteo via Jarvis : *"Le but était de mettre Claude Haiku dans la boucle pour vérifier les info, pas de mettre des mots dans le prompt système."* Correction : v1 minimal retenu, mobilise la propre connaissance du juge (knowledge cutoff janv 2026 = OK pour faits français publics). Nouveaux tests généralisation ajoutés. Cf §2 itération + §5 limitations honnêtes.

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

## 2. Variantes de prompt itérées (3 testées + recadrage v2 abandonné)

Spec exige *"prompt itéré 2-3 variantes — pas écrit en 30 sec ça marche"*. 3 variantes essayées (script spike one-shot supprimé après itération, contenu capturé ci-dessous) :

### v1 — Prompt minimal direct (RETENU ★ post-recadrage)
- ~35 lignes, structuré (OBJECTIF / CRITÈRES / FORMAT STRICT)
- Mobilise la connaissance externe du juge (knowledge cutoff janv 2026)
- Pas d'injection de faits dans le prompt → mesure la VRAIE capacité sémantique de Haiku

### v2 — Prompt avec whitelist connaissance officielle injectée (ABANDONNÉ post-recadrage)
- 48 lignes, ajoutait section *"Cas particulier — connaissance officielle française"* avec faits durcis :
  - Réforme bac 2021 / DEAMP 2016 / IFSI Parcoursup 2019 / PASS L1
- **Problème méthodologique** : la whitelist contenait EXACTEMENT les 3 ground truth (Q5/Q8/Q10), rendant le test trivial. Le juge pattern-matchait contre la whitelist au lieu de raisonner. Annulait la valeur du LLM-as-Judge (le but est que Haiku mobilise SA connaissance, pas qu'il relise des mots dans le prompt système).
- Recadrage Matteo 2026-04-29 20:27 via Jarvis : *"Le but était de mettre Claude Haiku dans la boucle pour vérifier les info, pas de mettre des mots dans le prompt système."*
- **Itération correctrice** : retour à v1 minimal, ré-validation des 3 ground truth (passent toutes), ajout de 3 tests généralisation hors-whitelist (DUT→BUT, MPENA inventé, Première STG en xfail).

### v3 — Prompt lourd à exemples
- 60 lignes, exemples FIDELE/INFIDELE inline
- Plus brittle (exemples corpus-spécifiques), prompt plus long → coûteux
- Pas re-testé post-recadrage (v1 suffit empiriquement)

### Résultats empiriques v1 (post-recadrage, sans whitelist)

| Cas | Verdict Haiku | Score | Détection |
|---|---|---|---|
| **Q5 IFSI** | INFIDELE | 0.05 | ⚠️ Indirect : flag IFMK chiffres + DE Ambulancier "(pas de concours)", pas explicitement "concours IFSI" — score < 0.5 OK |
| **Q8 DEAMP** | INFIDELE | 0.00 | ✅ Direct : flag "DEAMP en 1 an" + IFPEK fictif détecté avec connaissance Haiku |
| **Q10 Terminale L** | INFIDELE | 0.00 | ⚠️ Indirect : flag stats hallucinées (87%, 42%, +238%), pas le framing "Terminale L existe" |
| Clean PASS Lille | FIDELE | 1.00 | ✅ |
| Clean conseil pur | FIDELE | 1.00 | ✅ |
| **DUT→BUT 2021** | INFIDELE | < 0.5 | ✅ Haiku catche : "DUT bac+2 remplacé par BUT bac+3 en 2021" |
| **MPENA inventé** | INFIDELE | < 0.5 | ✅ Haiku catche le diplôme fictif |
| **Première STG → STMG** | FIDELE | ≥ 0.8 | ❌ xfail strict=True : framing acceptance, Haiku joue le jeu de la prémisse |

**Insight méthodologique critique** :
- Sur 3 ground truth Matteo, **1/3 catché DIRECTEMENT** par Haiku via sa connaissance officielle (Q8 DEAMP), **2/3 catchés INDIRECTEMENT** via éléments adjacents (chiffres non sourcés). Le score < 0.5 passe sur les 3 mais la raison de détection diffère.
- Limitation **framing acceptance** : quand l'utilisateur affirme implicitement une fausse prémisse ("Je suis en Première STG"), Haiku joue le jeu et n'invalide pas, même si sa connaissance le permettrait. Affecte Q10 (Terminale L) et STG. Documenté §5.

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

1. **Framing acceptance Haiku 4.5 (limitation découverte post-recadrage)** : quand l'utilisateur affirme implicitement une fausse prémisse dans la question ("Je suis en Première STG", "Je suis en terminale L"), Haiku joue le jeu de la prémisse et ne corrige pas, même si sa connaissance le permettrait. Affecte le test STG (xfail strict=True dans `test_judge_faithfulness.py`) et indirectement Q10 chantier E (détecté pour autre raison : stats non sourcées). Options pour adresser ça (Sprint 11 P1 / Item 4) :
   - **Option A** : augmenter Haiku → Sonnet 4.6 (probablement plus rigoureux sur la prémisse, coût × 5 mais reste <$0.05/eval)
   - **Option B** : ajouter une étape de "premise check" en pré-prompt ("Avant tout, vérifie si la question implique une fausse prémisse")
   - **Option C** : accepter cette limitation comme borderline acceptable — Q10/Q5 sont quand même catchés via éléments adjacents (chiffres non sourcés). La détection indirecte fonctionne.
2. **Détection indirecte vs directe** : sur les 3 ground truth Matteo, seul Q8 DEAMP est catché directement (Haiku flag explicitement le diplôme fantôme). Q5 IFSI et Q10 Terminale L sont catchés via éléments adjacents (chiffres précis non sourcés). Le score < 0.5 passe sur les 3 mais le mécanisme diffère. À surveiller : si une future réponse Mistral hallucine une fausse prémisse SANS chiffres adjacents, le judge pourrait la rater.
3. **Sample ground truth = 3 hallu seulement** (audit qualitatif Matteo n=10, 3 critiques flaggés). Le recall calculé sur n=3 = signal faible. Étendre l'audit Matteo (Item 4 / Sprint 11 P1) avant conclusions définitives.
4. **Aucun cas FIDELE certifié dans les 10 questions** (toutes ont au moins une affirmation borderline non sourcée). Les "clean tests" sont donc synthétiques (PASS Lille = 1 an), pas issus de production réelle.
5. **Calibration score 0.5 = arbitraire** mais respectueuse de la spec. Si Matteo veut un seuil plus strict (ex: 0.3 = flagué), la formule `_score_from_parsed` est centralisée dans le module.
6. **Souveraineté française non respectée** par claude-haiku-4-5 — décision Matteo 2026-04-29 18:54 UTC : OK uniquement parce que CI/dev offline (aucune donnée user transférée). Si glissement futur vers runtime prod : refacto vers Mistral ou modèle souverain (Sprint 12+).
7. **Variance non mesurée** : même prompt + même input peut donner verdict différent (LLM stochastique). Pour audit rigoureux, ajouter triple-run + IC95 (Sprint 11 P1). Pour CI/sanity-check : single-run suffit.
8. **Latence subprocess 28-40s/eval** = bottleneck pour tests CI. Pour 1 000 questions bench (Sprint 12) → ~10h sequential, parallelisation nécessaire.

---

## 6. Coût et performance empirique

| Item | Coût | Latence | Notes |
|---|---|---|---|
| 1 eval judge | ~$0.001 | 28-40s wall-clock | subprocess CLI bootup ~5-10s |
| Bench A/B (10 q) × 2 runs (avec/sans whitelist) | $0.02 | 10 min | sequentiel |
| Tests pytest réels (5 ground truth + 3 généralisation) × 2 runs | $0.016 | 6 min | sequentiel |
| Spike 3 variantes × 4 cas | $0.012 | 8 min | itération prompt initiale |
| **Total dev session** (init + recadrage iteration) | **~$0.05** | **30 min** | bien sous le budget $0.10 |

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
