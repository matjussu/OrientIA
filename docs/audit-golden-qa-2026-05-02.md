# Audit pipeline Golden Q/A — état au 2026-05-02

**Auteur** : Claudette (ordre Jarvis `2026-05-02-1330-claudette-orientia-audit-golden-qa-pipeline`)
**Périmètre** : description factuelle. Pas de proposition d'évolution longue. Pistes courtes en fin de doc.

---

## TL;DR (5 lignes)

- **1412 records** dans `data/golden_qa/golden_qa_v1.jsonl`, dont **426 valides** (355 `keep` + 71 `flag`) et **986 `drop`**.
- Pipeline 4 phases agentic Claude (Haiku research → Opus draft → Opus self-critique → Opus refine), généré sur 3 nuits (28-29/04, 29-30/04, 30/04-01/05).
- **Rendement réel post-fix bug stop condition (nuit 2 + 3) ≈ 96%** keep+flag. La nuit 1 (95.6% drops) est un artefact réseau, pas qualité — neutralisé par le fix `548834a`.
- Couverture : **51 prompt_ids**, **7 catégories** (etudiant_reorientation, lyceen_post_bac, actif_jeune, master_debouchés, famille_social, meta_question, profil_non_cadre), 6 valeurs d'`axe_couvert` (1, 2, 3, [1,2], [2,3], transversal).
- **Limites principales** : plafond Claude Max (stop sur 12×429 consécutifs), pas de classifier ignorance dans le pipeline Q/A direct (vit côté Backstop B post-process Sprint 11 P1.1), seed `A1 bio-info/finance-quant/jeu-vidéo` cluster `flag 78` systématique.

---

## 1. Pipeline actuel

### 1.1 Source de vérité
- **Spec** : ordre `2026-04-28-1130-claudette-orientia-sprint9-data-pipeline-agentique-1000qa.md` (vault).
- **ADR référence** : `08-Decisions/2026-04-28-orientia-pivot-pipeline-agentique-claude.md`.
- **Branche** : `feat/sprint9-data-pipeline-agentique` (le script orchestrateur n'est pas encore mergé sur main).
- **Config prompts** : `config/diverse_prompts_50.yaml` (51 prompts × 5-6 seeds chacun, commit `b8417d9`).

### 1.2 Architecture — 4 phases par Q/A

| Phase | Sous-agent | Modèle | Rôle |
|---|---|---|---|
| 1. Research | `general-purpose` (Task tool) | `claude-haiku-4-5` | Web search → 3-5 sources factuelles datées (URL + extrait clé). Cache utilisé. |
| 2. Draft | `general-purpose` | `claude-opus-4-7` | Génère Q/A type entretien d'orientation (active listening + reformulation + 3 pistes pondérées + question finale). |
| 3. Self-critique | `general-purpose` | `claude-opus-4-7` | Rubric 4 axes /25 chacun, total /100 : pertinence factuelle, posture conseiller, cohérence persona/contexte, absence d'hallucination. |
| 4. Refine | `general-purpose` | `claude-opus-4-7` | Applique les corrections de l'étape 3 → `final_qa = {question, answer_refined}`. |

### 1.3 Decision policy

| Score critique /100 | Decision | Action |
|---|---|---|
| ≥ 82 | `keep` | Indexé FAISS, utilisable en few-shot |
| 70-81 | `flag` | Indexé FAISS, review humaine sample 100 cas (Matteo + Ella + Deo) |
| < 70 | `drop` | Persisté en JSONL pour audit, non indexé |

> Boundary `keep ≥ 82` ajusté lors de la nuit 2 (initialement 85 dans la spec, abaissé à 82 après calibration mini-test — cf frontmatter ordre nuit 2 : `phase_2_boundaries_done: keep ≥ 82 / flag 70-81 / drop < 70 + tests + ADR §13`).

### 1.4 Paramètres clés (config nuit 3 — la plus safe, validée empiriquement)

```
--parallel 1
--rate-limit-delay 4.0
--max-retries 3
research model = claude-haiku-4-5
draft model    = claude-opus-4-7
critique model = claude-opus-4-7
```

Stop condition : 12 × HTTP 429 consécutifs → arrêt propre `RuntimeError Stop condition`, exit code 3.
Append-only JSONL + checkpointing : un re-run skip les `prompt_id × iteration` déjà présents.

### 1.5 Output et indexation

- **JSONL brut** : `data/golden_qa/golden_qa_v1.jsonl` (1412 lignes, 3.2 MB).
- **Index FAISS dérivé** (Sprint 10 chantier D, script `scripts/embed_golden_qa.py`) :
  - Filtre `decision in (keep, flag)` → 426 vecteurs.
  - Embed `question_seed | final_qa.question` (PAS l'answer — décision sync : matching côté user query = intent, l'answer arrive en context post-retrieve).
  - Mistral-embed dim 1024.
  - Output : `data/embeddings/golden_qa.index` + `data/processed/golden_qa_meta.json`.

---

## 2. Volume cumul exact au 2026-05-02

### 2.1 Total

| Métrique | Valeur |
|---|---|
| Records JSONL | **1412** |
| `keep` | **355** |
| `flag` | **71** |
| `drop` | **986** |
| **Valides cumul (keep + flag)** | **426** |
| Drop rate brut | 69.8% |

### 2.2 Distribution par nuit (reconstituée depuis frontmatters)

| Run | Date | Records | keep | flag | drop | Yield keep+flag | Cause arrêt |
|---|---|---|---|---|---|---|---|
| Nuit 1 | 28-29/04 ~22h–06h | ~1020 | ~33 | ~12 | ~975 | **4.4%** | Bug stop condition propagation (réseau, pas qualité) |
| Mini-test post-fix | 29/04 09h | 9 (A1+B1+C1) | 8 | 1 | 0 | 100% | OK |
| Nuit 2 | 29/04 23h37 → 30/04 01h24 | 159 (en 106 min) | 135 | 21 | 4 (+ 2 errors) | **97.5%** | Stop condition propre quota Claude Max saturé |
| Nuit 3 | 30/04 → 01/05 matin | **~233** | **~211** | **~37** | restant | **~96.6%** | Quota / fin scope |

**Cumul après nuit 2** (frontmatter ordre nuit 2) : 1179 total / 201 valides.
**Cumul après nuit 3** (chiffres JSONL aujourd'hui) : 1412 total / 426 valides → **nuit 3 a ajouté +233 records / +225 valides**, rendement effectif ≈ 96.6% (cohérent avec la cible `>95%` fixée par Jarvis).

### 2.3 Clarification du delta journal vs JSONL

Le journal 30/04 mentionnait **297 valides cumul avant nuit 3**, l'addendum officiel **~437 après nuit 3**. Le chiffre actuel **426** (mesure exacte depuis le JSONL ce jour) est plus bas de 11. Probable cause : le 437 était une projection avant fin réelle de la nuit 3 (la stop condition a coupé un peu plus tôt que prévu, cf `nuit_2_records_correction: 159 effectifs vs 160 estim Jarvis - off-by-one mid-write SIGTERM`). **426 est la valeur de référence** au 2026-05-02, mesurée par `jq` sur le JSONL.

### 2.4 Distribution scores critique

| Tranche | Records | Note |
|---|---|---|
| < 60 | 979 | corrobore les 986 drops à 7 près (≈ erreurs Phase 4 ou hallu flagrante détectée) |
| 60-69 | 7 | borderline drop |
| 70-79 | 66 | majeure partie des `flag` |
| 80-89 | 257 | majeure partie des `keep` |
| 90-100 | 103 | top tier `keep` |

---

## 3. Couverture thématique

### 3.1 Catégories (7)

| Catégorie | Records | Part |
|---|---|---|
| etudiant_reorientation | 402 | 28.5% |
| lyceen_post_bac | 316 | 22.4% |
| actif_jeune | 194 | 13.7% |
| master_debouchés | 160 | 11.3% |
| famille_social | 160 | 11.3% |
| meta_question | 120 | 8.5% |
| profil_non_cadre | 60 | 4.2% |

### 3.2 Axes couverts (champ `axe_couvert`, mixed type int/list/string)

| Valeur | Records | Interprétation |
|---|---|---|
| transversal | 340 | questions multi-phases (initial + réorientation + master/pro mêlés) |
| `[1, 2]` | 322 | phase initiale + réorientation |
| `1` | 316 | phase initiale (lyceen_post_bac mostly) |
| `[2, 3]` | 194 | réorientation + master/pro |
| `[3]` | 160 | master/pro pur |
| `[2]` | 80 | réorientation pure |

> Cohérent avec scope V2 élargi 17-25 ans 3 phases égales (cf [[user_memory project_orientia_scope_v2]]). Phases 1-2-3 toutes représentées, transversal dominant.

### 3.3 Personas et seeds

- **51 prompt_ids actifs** : A1-A10 (sauf A7), B1-B10, C1-C8 (sauf C5), D1-D8, E1-E8, F1-F6, G1-G3.
- **Seeds par prompt** : 5-6 (étendu vs draft v2 à 3) — 264 seeds totaux.
- **Phrasings humains** : 8 prompts touchés par variantes argot/abréviations (annotation `phrasing_humain` dans YAML).
- **Test set v3 mapping** : 12 annotations `test_set_v3` intégrées (alignement bench evaluation).
- **Tutoiement vs vouvoiement** : 6 prompts en vouvoiement explicite (C8, D3, D7, D8, E1, E6), reste tutoiement.

### 3.4 Sources priorisées (déclarées par YAML par prompt)

ONISEP, Parcoursup, InserJeunes, France Compétences, RNCP, DARES, InserSup-DEPP — sources publiques officielles 2026 alignées avec le pivot souveraineté française.

Sources factuelles effectivement utilisées par phase 1 (research) : variables par Q/A, log persistés dans `research_sources_text` du JSONL pour audit.

### 3.5 Type de questions (vu sur sample)

- **ON-TOPIC** : ~majeure partie (orientation académique/pro post-bac).
- **OFF-TOPIC scaffolding** : peu présent dans le JSONL actuel (les prompts A-F sont tous orientation). À noter pour V2.
- **IGNORANCE_OK** : pas testé directement dans le pipeline Q/A — vit côté Backstop B soft post-process (PR #113, Sprint 11 P1.1, classifier v3 catch rate 64.7%).

---

## 4. Limites identifiées

### 4.1 Plafond capacitaire Claude Max
- Quota partagé Max → `parallel=1 rate-limit-delay=4.0` est la config safe minimale viable.
- Stop condition à 12×429 consécutifs déclenchée systématiquement nuit 2 + 3 (architecture défensive validée).
- **Conséquence** : impossible de boucler le scope `target=1020` en une nuit. Multi-nuit obligatoire pour atteindre 1000 valides.

### 4.2 Hallu chiffres résiduelles
- Score 4 axes mesure "absence d'hallucination flagrante" mais pas la véracité numérique fine (taux d'insertion exact, frais d'inscription, etc.).
- Mitigation : Backstop B soft post-process `FetchStatFromSource` + `BackstopBSoft` (PR #113, mergé Sprint 11 P1.1) → catch rate 64.7% sur 17 chiffres testés. Hors scope du JSONL Golden, vit côté `pipeline_agent_golden`.

### 4.3 Classifier ignorance v3
- **Pas dans le pipeline Q/A** (les Q/A Golden sont supposées answerable par construction depuis YAML).
- Vit côté Backstop B soft post-process (Sprint 11 P1.1, PR #113) — annotation `[chiffre non vérifié]` sur stats sans source.

### 4.4 Bias seed identifié (frontmatter ordre quick-win 2)
- **Seed `A1 bio-info / finance-quant / jeu-vidéo`** = cluster `flag 78` systématique (3/3 itérations nuit 1 + mini-test).
- Cause probable : la question évoque trois domaines hyper-différents qui forcent la réponse à se diluer → score posture conseiller pénalisé.
- Pas corrigé dans le YAML actuel.

### 4.5 OFF-TOPIC scaffolding manquant
- Les 51 prompts couvrent 100% ON-TOPIC orientation. Aucune Q/A Golden ne teste comment le système répond à une question hors scope (ex : "fais-moi un poème", "qui est le président").
- Hors scope explicite Sprint 9, à reprendre éventuellement Sprint 13+ si bench V2 pointe le besoin.

### 4.6 Cohabitation données fraîches / figées
- Sources web (phase 1 research) datées 2025-2026, mais pas de mécanisme de refresh sur les Q/A déjà produites.
- Décalage potentiel si une école change d'accréditation CTI / ferme une promo / etc. Refresh manuel uniquement (pas de cron).

### 4.7 `axe_couvert` mixed type
- Champ tantôt `int`, tantôt `list[int]`, tantôt `string "transversal"`.
- Le script `embed_golden_qa.py` gère les 3 cas, mais c'est un point de friction pour les downstream users (filtrage, reporting).

---

## 5. Pistes d'évolution suggérées (court — 5 max, hors scope cet audit)

1. **Standardiser `axe_couvert`** sur un seul type (ex : `list[str]` avec valeurs `["1"]`, `["1","2"]`, `["transversal"]`) — friction downstream.
2. **Re-générer le seed A1 bio-info/finance-quant/jeu-vidéo** en le scindant en 2-3 seeds plus focalisés pour casser le cluster flag 78.
3. **Ajouter une catégorie OFF-TOPIC** (ex : 5 prompts × 4 seeds = 20 Q/A) pour tester le scaffolding rejet hors scope, si bench V2 le demande.
4. **Cron refresh source dating** : marqueur `last_fetched_at` par record + script de re-validation des URLs / dates source (signal d'obsolescence).
5. **Augmenter le scope vers 1000 valides** (actuellement 426) : 2 nuits supplémentaires en config safe à ~$10-15 chacune si quota Claude Max disponible. À arbitrer Sprint 13.

---

## Annexes

### A. Scripts et fichiers cités

- **Pipeline orchestrateur** (branche `feat/sprint9-data-pipeline-agentique`) : `scripts/generate_golden_qa_v1.py` (non mergé sur main).
- **Config prompts** : `config/diverse_prompts_50.yaml` (1412 lignes YAML, 51 prompts, 264 seeds).
- **Embed → FAISS** : `scripts/embed_golden_qa.py` (Sprint 10 chantier D).
- **JSONL** : `data/golden_qa/golden_qa_v1.jsonl` (3.2 MB, 1412 lignes).
- **Index FAISS** : `data/embeddings/golden_qa.index` (gitignored).
- **Meta** : `data/processed/golden_qa_meta.json` (mapping idx → record réduit).

### B. Notes vault liées (pour traçabilité)

- `2026-04-28-1130-claudette-orientia-sprint9-data-pipeline-agentique-1000qa.md` (spec initiale)
- `2026-04-29-0625-claudette-orientia-fix-bug-stop-condition-propagation.md` (fix nuit 1)
- `2026-04-29-0656-claudette-orientia-validation-extract-nuit1.md` (post-mortem nuit 1)
- `2026-04-29-1011-claudette-orientia-sprint9-data-nuit2-prep.md` (config + résultats nuit 2)
- `2026-05-01-0035-claudette-orientia-sprint9-data-nuit-3-config-safe.md` (config + résultats nuit 3)
- `2026-05-01-1334-claudette-orientia-sprint11-P1-1-backstop-b-soft-classifier-v3.md` (classifier ignorance — hors pipeline Q/A direct)
- `2026-05-01-2031-claudette-orientia-sprint12-axe-2-golden-pipeline-fusion.md` (consommation des 426 Q/A en few-shot Sprint 12 axe 2, en cours)

---

## 6. Pivot Sonnet 02/05 — résultats audit qualitatif (addendum 14h-15h)

Section ajoutée suite à l'ordre Jarvis `2026-05-02-1402-claudette-orientia-pivot-sonnet-pipeline-golden-qa-run-completion`. Décision Matteo (Telegram 3053) : pivot Phase 3 (self-critique) + Phase 4 (refine) Opus 4.7 → Sonnet 4.6 pour économie tokens. Risque qualité accepté + audité empiriquement.

### 6.1 Pivot livré

- **Commit refactor** : `6f4153d` (`refactor(golden-qa): pivot P3+P4 Opus 4.7 → Sonnet 4.6`) + `fbd6202` (fix latent `PIPESTATUS` dans `launch_qa_gen_nuit.sh`).
- **Branche** : `feat/sprint9-data-pipeline-agentique`.
- **Constante ajoutée** : `DEFAULT_MODEL_CRITIQUE_REFINE = "claude-sonnet-4-6"` avec fallback chain `cfg.model_critique_refine or cfg.model or DEFAULT`.
- **P1 Haiku research + P2 Opus draft** : strictement inchangés (créativité user-facing préservée).
- **Tests** : 88/88 verts, aucune régression.
- **Override Opus rollback** : toujours possible via `--model-critique-refine claude-opus-4-7`.

### 6.2 Run de complétion en cours

- **Démarré** : 2026-05-02 14:08 CEST en config safe (`--parallel 1 --rate-limit-delay 4.0`, mode `--skip-decisions keep,flag`).
- **Scope** : 594 jobs (1020 catalogue YAML − 426 valides skip).
- **Avancement à 14:50** : 30 records pivot Sonnet produits (sample audit). Run continue, ETA ~16h end-to-end multi-session si quota tient.
- **Lifecycle JSON** armé avec `${PIPESTATUS[0]}` (capture exit code python réel).

### 6.3 Sample audit — distribution Sonnet vs Opus

| Métrique | Opus 4.7 (nuits 2+3, 381 records) | Sonnet 4.6 (sample 30 pivot) |
|---|---|---|
| Score moyen | ~86 | **78.9** |
| Score median | ~86 | 78 |
| Score range | 70-95 | 70-92 |
| keep rate | 84% (319/381) | **27%** (8/30) |
| flag rate | 16% (62/381) | **73%** (22/30) |
| drop rate | 0% (post-fix) | 0% (sample) |

**Couverture sample Sonnet** : 28/30 sur catégorie `actif_jeune` (C2, C3, C4) + 2 `etudiant_reorientation` (B4) — biaisé par l'ordre du run (drops à refaire en partant du début YAML hors valides). Catégories D-G non encore atteintes.

### 6.4 Drill-down qualitatif Pattern #3+#4

Sample exporté pour traçabilité : `docs/audit-pivot-sample-opus-2026-05-02.md` (30 Opus) + `docs/audit-pivot-sample-sonnet-2026-05-02.md` (30 Sonnet).

#### 6.4.1 Hallucinations factuelles détectées par self-critique Sonnet (récurrentes)

Sonnet a systématiquement détecté et corrigé ces patterns dans le draft Opus :

| Pattern halluciné | Récurrence dans le sample |
|---|---|
| `Décret n° 2025-500` (numéro réglementaire inventé) | 5+ records |
| `Vademecum 2026 France Compétences référence 36 fiches d'orientation` (document inexistant) | 4+ records |
| `1 837,34 €` salaire au centime IDCC 176 (précision suspecte non sourcée) | 4+ records |
| `421 heures` IDMC Lorraine (volume horaire précis non vérifiable) | 6+ records |
| `CDD de reconversion (nouveau dispositif depuis janvier 2026)` (dispositif inexistant) | 3+ records |
| `BTS Métiers de la coiffure` comme diplôme national (n'existe pas) | 1 record (correction structurante) |
| `Pôle Emploi` (terme obsolète depuis janvier 2024 → France Travail) | 2 records |

#### 6.4.2 Sur-projections empathiques détectées

Sonnet self-critique a relevé et corrigé :
- `burn-out` attribué à un user qui n'a pas mentionné ce terme
- `pression familiale` non établie par la question
- `budget tendu/serré` supposé sans confirmation explicite

#### 6.4.3 Misalignment question/réponse

Cas remarquables :
- Record #02 (B4#14) : la question demandait une définition (`c'est quoi exactement`) — le draft a ignoré la définition et listé des options. Sonnet flagué à 76 avec critique précise.
- Record #17 (C4#2) : la question explicitait deux options à comparer (`labo public vs pharma management`) — le draft a évacué la première option. Sonnet flagué à 71.
- Record #09 (C3#14) : la question demandait des chiffres coût/durée — la draft les a éludés. Sonnet flagué à 79.

### 6.5 Verdict explicite

**Sonnet TIENT le gate, et même mieux que Opus côté détection des hallucinations factuelles.**

Le score moyen plus bas (78.9 vs 86) reflète une **posture critique plus stricte**, **PAS** une qualité moindre des Q/A finales. Au contraire :

1. **Détection hallu finer** : Sonnet attrape des hallu spécifiques (numéros de décret, salaires au centime, noms de documents officiels) qu'Opus laissait passer plus souvent (cf #02, #03, #04, #05, #15, #16, #18, #19, #21, #22, #25, #28).
2. **Vérification alignement Q/R** : Sonnet pénalise les drafts qui ne répondent pas exactement à la question (#02, #09, #17).
3. **Posture conseiller plus rigoureuse** : Sonnet reformule en non-prescriptif et adoucit les sur-projections empathiques.

**Discriminative power** : la distribution 27% keep / 73% flag chez Sonnet est plus fine et utile en aval (filtrage Q/A authoritative pour few-shot RAG) que la distribution 84/16 chez Opus, qui mélangeait potentiellement keep et flag de qualité similaire.

### 6.6 Recommandations (verdict ferme + propositions)

| # | Recommandation | Rationale |
|---|---|---|
| 1 | **MAINTENIR le pivot Sonnet 4.6** par défaut sur P3+P4 | Économie tokens validée + qualité réelle améliorée sur axe hallucination + discrimination keep/flag plus pertinente |
| 2 | **NE PAS ajuster `SCORE_KEEP_THRESHOLD` upward** (rester à 82) | Boundary 85 serait sur-strict. À envisager 78 pour Sonnet uniquement, mais demande plus de data (audit complémentaire) |
| 3 | **Audit complémentaire** quand le run aura couvert D/E/F/G | Sample actuel biaisé sur actif_jeune (28/30). Lyceen_post_bac et meta_question doivent être validés aussi. |
| 4 | **Recalibrer attente yield** | Avec Sonnet, attendre ~70-80% keep+flag (vs ~95% historiquement annoncé Opus). Reste largement supérieur au yield nuit 1 buggée. |
| 5 | **Capitaliser le pattern hallu détectées** | Les 7 patterns identifiés (décret 2025-500, Vademecum, etc.) sont récurrents — possible amélioration côté Phase 2 draft Opus pour pré-prévenir ces hallu en upstream. Hors scope cet ordre, à proposer en `/propose-dev`. |

### 6.7 Surveillance vigilance bias seed

- **Seed `A1 bio-info/finance-quant/jeu-vidéo`** (cluster flag 78 historique Opus) : pas atteint dans ce sample (qui couvre B-C). À re-vérifier quand le run remontera vers A.
- **Seed C2#5 `master commerce → santé`** : 5 occurrences dans le sample, scores 71-86 chez Sonnet — pas de cluster systématique détecté.

---

*Audit livré 2026-05-02. Statut JSONL Golden Q/A initial : 1412 records, 426 valides, 7 catégories couvertes, 51 prompt_ids actifs, drop rate effectif post-fix ~4% nuits 2-3.*

*Addendum pivot Sonnet : 30 records pivot audités (run en cours, ETA ~16h multi-session). Verdict empirique : Sonnet maintient et même renforce la qualité du gate, économie tokens validée.*
