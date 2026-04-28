# Sprint 9-data — Pipeline agentique 1000 Q&A (Ordre 2/2)

**Date** : 2026-04-28 (J-27 deadline INRIA 2026-05-25)
**Scope** : Ordre 2/2 du Sprint 9 — génération dataset golden Q&A "réponses
parfaites de conseiller" via pipeline agentique 4 phases (research → draft →
critique → refine) en subprocess `claude --print` (Claude Opus 4.7,
Claude Max plan, 0$ marginal).
**Coût** : 0$ marginal (subscription Matteo, décision D5 ADR pivot)
**Branche** : `feat/sprint9-data-pipeline-agentique`
**Commits** : `b8417d9` (Phase 1 YAML) + `b6be153` (Phase 2 script + tests + tmux)
**ADR référence** : `08-Decisions/2026-04-28-orientia-pivot-pipeline-agentique-claude.md`

---

## ⚠️ Lecture du verdict

Sprint 9-data Ordre 2/2 livré sous l'ordre Jarvis
`2026-04-28-1130-claudette-orientia-sprint9-data-pipeline-agentique-1000qa`.
Audits cross-check Jarvis :
- ✅ YAML 51 prompts × 5-6 seeds (audit 11:43, clean)
- ✅ Script + tests + tmux launcher (audit 11:47, clean, 4 obs mineures non-bloquantes)
- 🟡 Dry-run 1 prompt × 5 itérations (en cours / à compléter post-run)
- 🟡 Lancement nuit 22h après go/no-go Matteo (en attente)

---

## 1. Contexte

### Pivot stratégique 2026-04-28 (rappel ADR)

OrientIA bascule de Q&A documentaire RAG vers conseiller IA conversationnel.
Sprint 9 décomposé en 2 ordres :
- **Ordre 1/2 — Sprint 9-archi** : couche Coordinator + 3 sub-agents
  (PR #100, audit Jarvis 13/13 positif, en attente go merge Matteo)
- **Ordre 2/2 — Sprint 9-data** ← cet ordre — génération offline 1000 Q&A
  via pipeline agentique Claude Opus 4.7

### Décision Matteo Option A (Telegram msg 2795)

Pipeline 4 phases conservé (qualité top), étalement 8-10 nuits accepté pour
atteindre 1020 Q&A. Sprint 10 reporté ~12-13/05.

---

## 2. Architecture livrée

### Pipeline 4 phases offline pure

```
[YAML config 51 prompts × 5-6 seeds = 264 seeds]
        │
        ▼
ThreadPoolExecutor (--parallel N adaptable plan Matteo)
        │
        │ Pour chaque (prompt_id, iteration_idx) :
        │
        ▼
┌─────────────────────────────────────────────────┐
│ Phase 1 — RESEARCH                              │
│   subprocess claude --print --model opus-4.7    │
│   --allowedTools WebSearch,WebFetch             │
│   → 3-5 sources factuelles datées 2025-2026     │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│ Phase 2 — DRAFT (persona conseiller)            │
│   active listening + reformulation              │
│   3 pistes pondérées non-prescriptives          │
│   question finale d'exploration                 │
│   → JSON {question, answer}                     │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│ Phase 3 — SELF-CRITIQUE (4 axes /100)           │
│   factualité / posture / cohérence / hallu      │
│   pénalités lourdes -10 explicites              │
│   → JSON {score_total, scores_par_axe, ...}     │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│ Phase 4 — REFINE                                │
│   intègre corrections suggérées                 │
│   préserve question + structure conseiller      │
│   → JSON {question, answer_refined}             │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
   ThreadSafeJsonlAppender (append-only resumable)
   → data/golden_qa/golden_qa_v1.jsonl
```

### Decision policy keep / flag / drop

- Score Claude self-critique **≥ 85** → `keep` (validé)
- Score **70-85** → `flag` (review humaine sample 100 cas mardi 29/04 par
  Matteo + Ella + Deo Munduku)
- Score **< 70** → `drop` (rejeté)

### Rate limiting défensif intégré (remarque opérationnelle Jarvis)

Plan Claude Max configurable :
- Max 20x : `--parallel 5`, ~4-8h/nuit, 1020 Q&A en 1-2 nuits
- Max 5x : `--parallel 2`, ~16-20h/nuit, 1020 Q&A en 8-10 nuits ← **cas
  retenu Option A Matteo**
- Pro : `--parallel 1`, infaisable nuit, fallback 500 cas

Détection 429 : 4 patterns regex (`rate.limit` / `429` / `quota exceeded`
/ `too many requests`) sur stderr + stdout. Backoff exponentiel 2^attempt
+ rate-limit-delay. Stop condition >10 consecutive 429 → abort propre.

---

## 3. Fichiers livrés

| Fichier | Rôle | LoC |
|---|---|---|
| `config/diverse_prompts_50.yaml` | 51 prompts × 5-6 seeds (264 seeds totaux) | 1412 |
| `scripts/generate_golden_qa_v1.py` | Orchestrateur 4 phases + checkpointing + signal handling | ~440 |
| `scripts/launch_qa_gen_nuit.sh` | Bash launcher tmux session-name `qa-gen` | ~115 |
| `tests/test_generate_golden_qa.py` | 56 tests : YAML / decision / 429 / retry / parsing / appender / orchestration / CLI | ~390 |
| `docs/SPRINT9_DATA_VERDICT.md` | Verdict ADR (ce document) | (TBD) |

### Audit cross-check Jarvis (résumés)

**Audit YAML** (11:43 UTC) :
- ✅ Parsing yaml.safe_load OK
- ✅ 51 prompts, IDs uniques, distribution conforme draft v2
- ✅ 9 champs requis présents sur 51/51
- ✅ Seeds 5-6 strict (mean 5.18, total 264)
- ✅ Tone 6 vouvoiements aux IDs exacts (C8 / D3 / D7 / D8 / E1 / E6)
- ✅ 12 annotations `# test_set_v3 Q*` + 46 `# phrasing_humain`
- ✅ Distribution axes : 9+8+2+7+8+17 = 51

**Audit script + tests + bash launcher** (11:47 UTC) :
- ✅ Architecture claire (docstring + ASCII diagram + sections)
- ✅ Type hints, datatypes propres (GenerateConfig + RetryStats thread-safe)
- ✅ Subprocess wrapper robuste (timeout / FileNotFound / returncode)
- ✅ 4 patterns rate limit detection
- ✅ Backoff exponentiel + stop condition >10 consecutive 429
- ✅ Signal SIGINT/SIGTERM clean
- ✅ Mode dry-run-no-subprocess avec détection schema markers
- ✅ Phase 2 prompt très bien construit (active listening + reformulation
  + 3 pistes pondérées + INTERDIT prescriptif + question finale + estimation)
- ✅ Phase 3 critique avec pénalités lourdes -10 explicites
- ✅ parse_json_safe avec 3 niveaux fallback
- ✅ Exit code 2 si error_rate > 30% (signal surveillance Jarvis)
- ✅ Bash launcher `set -euo pipefail` + sanity checks pré-launch + kill confirm

**Track record audits Jarvis : 14/14 positifs cumulés** (13 + Sprint 9-data Phase 1+2).

---

## 4. Tests

### Couverture suite Sprint 9-data (56 tests)

- TestYAMLConfig (6) : 51 prompts + fields requis + range 5-6 seeds + mapping test set v3
- TestDecisionPolicy (6) : boundaries 85 / 70 / 100 / 0 stricts
- TestRateLimitDetection (12 paramétrés) : 429 / rate-limit / quota / Too Many sur stderr+stdout, no false positives
- TestRetryStats (3) : reset consecutive / return count / thread-safety 10 threads × 100 increments
- TestParseJsonSafe (6) : JSON propre + markdown fence + bare fence + préambule + invalid + empty
- TestThreadSafeJsonlAppender (5) : append + existing_keys + skip invalid + concurrent 10 threads × 50 writes
- TestCallClaudeSubprocess (5) : stdout / timeout / FileNotFoundError + flags --allowedTools / --model
- TestCallClaudeWithRetry (5) : success / 429 retry / max retries fail / stop condition >10 / dry-run no-subprocess
- TestGenerateQaOrchestration (3) : record fields + seed iteration modulo + error handling graceful
- TestBuildJobs (4) : --filter-prompt-id / --max-iterations / --target / unknown id ValueError

**56/56 tests verts en 3.6s, suite globale 1628 passed (+56 vs main 1572), 0 régression.**

---

## 5. Dry-run results — A1 × 5 itérations (2026-04-28 ~13h45 UTC)

### Configuration

```bash
python scripts/generate_golden_qa_v1.py \
  --config config/diverse_prompts_50.yaml \
  --output data/golden_qa/dryrun_test.jsonl \
  --filter-prompt-id A1 \
  --max-iterations 5 \
  --parallel 2 \
  --model claude-opus-4-7 \
  --rate-limit-delay 1.0 \
  --max-retries 3 \
  --timeout-s 300
```

### Résultats

| Métrique | Valeur |
|---|---|
| Q&A produits | **5/5 (100%)** |
| Décisions | **3 keep + 2 flag + 0 drop** (60% keep, 40% flag, 0% drop) |
| Score moyen | **84.2** (range 78-89) |
| Latence par Q&A | 154.8 → 183.4s (mean ~168s) |
| Total elapsed | **8.2 min** |
| Sub-agent calls | 20 success / 0 errors |
| **429 / rate limit** | **0** |
| Format `--model claude-opus-4-7` | ✅ accepté direct (pas de fallback nécessaire) |
| Format `--allowedTools WebSearch,WebFetch` | ✅ accepté direct |
| Critère acceptance ≥3 Q&A score ≥85 | ✅ **3 keep ≥85** (validé) |

### Décomposition scores 4 axes (sur /25)

| Axe | Mean | Min | Max | Lecture |
|---|---:|---:|---:|---|
| **Posture conseiller** | 23.4 | 23 | 24 | ⭐ Active listening + reformulation systématique, 3 pistes pondérées non-prescriptives, tutoiement adaptatif respecté |
| **Cohérence persona** | 22.6 | 22 | 23 | ⭐ Vocabulaire/registre adapté au lycéen 17 ans (cible A1) |
| **Factualité** | 20.4 | 18 | 22 | 🟡 Quelques chiffres marqués "estimation connaissance générale" non sourcés (à creuser via prompts) |
| **Hallucination** | 17.8 | 15 | 20 | 🟡 Point faible — critique catch les hallu (ex Q&A#5 score 78 "ESNA Toulouse n'existe pas", Q&A#3 score 82 "dates précises 28 avril 2026 non sourcées") |

→ **Le filtre `score≥85` protège bien le dataset final** : les Q&A qui échappent à la détection hallucination passent en `flag` (review humaine mardi) au lieu de `keep` automatique.

### Sample qualité — Q&A #2 (score 86 keep, le plus représentatif)

**Question générée** : "Je suis en terminale spé maths-physique, j'ai des bons résultats mais je sature des maths super abstraites style démonstrations à rallonge. La prépa MPSI me fait flipper. Tu vois des alternatives concrètes ?"

**Answer refined** :
> Si je te comprends bien, tu as un vrai profil scientifique solide, mais
> ce qui t'attire c'est l'application concrète plutôt que la démonstration
> pour la démonstration — et la MPSI te semble pousser le curseur trop loin
> côté abstraction. C'est une lucidité plutôt saine, beaucoup de profils
> comme le tien s'épanouissent davantage ailleurs qu'en prépa classique.
>
> Voici trois pistes que tu pourrais explorer, à pondérer selon ce qui
> résonne le plus avec toi :
>
> **Piste 1 — BUT (Bachelor Universitaire de Technologie), 3 ans en IUT.**
> Plusieurs spécialités sont très alignées avec ton profil maths-physique
> [...]

✅ Active listening + reformulation en ouverture
✅ 3 pistes pondérées non-prescriptives (pas de "tu devrais")
✅ Tone tutoiement bienveillant respecté
✅ Question finale d'exploration en clôture
✅ Estimation/source markers présents pour chiffres approximatifs

### Throughput projection lancement nuit

- Mesure dry-run : 20 calls / 8.2 min = **~2.4 calls/min en parallel 2**
- Pour 1020 Q&A × 4 phases = 4080 calls :
  - **Parallel 2 (Max 5x)** : ~28h → étalement 4 nuits (cohérent Option A 8-10 nuits)
  - **Parallel 5 (Max 20x)** : ~11h → 1-2 nuits
- Estimation 1 nuit (22h-7h = 9h) :
  - ~600 Q&A en parallel 2
  - ~1500 Q&A en parallel 5

### Décision GO / NO-GO nuit 22h

🟡 **GO côté Claudette** (livrable technique validé) — _en attente décision Matteo via Jarvis post-relai._

Cibles à confirmer côté Matteo :
- Plan Claude Max (5x / 20x / Pro) → ajuste `--parallel`
- Inspection détaillée Q&A #1, #3, #4, #5 si nécessaire (résumés ci-dessus)
- Ajustement éventuel prompts Phase 2 / Phase 3 si signal qualité insuffisant
  (ex : forcer "(estimation)" plus systématique sur chiffres pour réduire l'axe
  hallucination de 17.8 → 22+)

---

## 6. Décisions techniques notables

### D-data-1 : subprocess `claude --print` vs API SDK Anthropic

**Décision** : subprocess `claude --print` utilise quota Claude Max plan
de Matteo, 0$ marginal.

**Rationale** :
- Décision Matteo Telegram msg 2758 (28/04 09:05 UTC) : "utiliser Claude
  Code avec mon abonnement et non l'API ça va devenir beaucoup trop chère
  sinon"
- Cohérent avec D5 ADR (stack 3 LLMs à 3 positions optimales : Claude Opus
  pour génération offline, Mistral Medium pour inférence produit, sample
  humain pour validation)
- Quota Max plan : 1020 Q&A × 4 phases = ~4080 sub-agent calls + research
  WebSearch. Étalement 8-10 nuits accepté Option A.

### D-data-2 : 4 phases agentic vs 1-shot generation

**Décision** : Pipeline 4 phases (research → draft → critique → refine)
plutôt que 1-shot generation.

**Rationale** :
- Le research Phase 1 ancre les Q&A sur des sources officielles 2025-2026,
  réduisant l'hallucination factuelle
- Le draft Phase 2 produit la posture conseiller avec persona prompt fort
- Le self-critique Phase 3 catch les dérives prescriptives / tone
  mismatch / hallucination résiduelle
- Le refine Phase 4 applique les corrections, élève le score moyen
- Match l'architecture Sprint 9-archi (Coordinator + EmpathicAgent +
  AnalystAgent + SynthesizerAgent) — données et inférence en cohérence

### D-data-3 : Pattern strangler fig préservé

**Décision** : Le pipeline Sprint 9-data NE TOUCHE PAS au pipeline factuel
existant (`src/agent/pipeline_agent.py`, `src/rag/*`). Génération 100%
offline.

**Rationale** : zéro risque de casser le bench Mode Baseline +7,4pp Sprint 7.
Les 1020 Q&A produits seront indexés FAISS en Sprint 10 (D6 ADR : few-shot
dynamique retrieval top-3) sans altérer le retrieval.

### D-data-4 : ThreadPoolExecutor + ThreadSafeJsonlAppender

**Décision** : Reproduire le pattern existant `src/agent/parallel.py:parallel_apply`
Sprint 4-5 plutôt qu'inventer une abstraction.

**Rationale** : pattern éprouvé en prod sur AgentPipeline, no surprise.
Confiance > nouveauté en pré-deadline INRIA.

### D-data-5 : Stop condition >10 consecutive 429

**Décision** : abort propre du run si 10 calls subprocess successifs
hit 429.

**Rationale** : fallback gracieux pour préserver le quota nuit. Si la
limite est atteinte 10× de suite, on est probablement à fond du quota et
on doit attendre le reset. Stop > continue + spam 429.

---

## 7. Risques connus + atténuations

| Risque | Détection | Atténuation |
|---|---|---|
| Format `--model claude-opus-4-7` rejected par CLI | Dry-run | Fallback `opus` (alias short), puis drop le flag (default session) |
| WebFetch dans `--allowedTools` reject | Dry-run | Fallback `WebSearch` seul |
| Quota Claude Max épuisé en milieu de nuit | Stop condition >10 × 429 | Abort propre, reprise resume au reset quota (checkpointing JSONL) |
| Score moyen <85 en dry-run (qualité insuffisante) | Inspection Matteo 17h | Calibration prompts (Phase 2 / Phase 3) puis re-dry-run |
| `parse_json_safe` rate >5% (LLM ne respecte pas le JSON strict) | Logs dry-run | Ajouter des markers explicites dans prompts ("Réponds UNIQUEMENT en JSON, ne préface pas") |
| Persona drift sur certains prompts (G1 brut, B6 Sarah-style) | Sample humain mardi | Itération phrasings / few-shots Sprint 10 si signal |
| Latency >5 min par Q&A (timeout 300s) | Dry-run elapsed_s | Augmenter `--timeout-s` ou réduire `--parallel` |

---

## 8. Surveillance nuit Jarvis (28-29/04)

Pendant la génération nuit (22h → 7h), Jarvis prend le rôle valideur :

- **Check 01h** : qualité 30-50 premiers Q&A produits (sample 5-10 random)
- **Check 04h** : qualité + rythme + stats keep/flag/drop + retry stats
- **Stop conditions** :
  - Drop rate >30% sur 50 cas (calibration prompt nécessaire)
  - Rate limit Claude Max successive (>10 × 429 stop déjà côté script)
  - Divergence stylistique majeure (signal 0 keep sur 30 cas)
- **Report matin 7h** : stats + sample qualité + reco pour sample humain Matteo

---

## 9. Sample humain mardi 29/04

Validation finale par 3 reviewers humains :
- **Matteo** (toutes catégories)
- **Ella** (étudiante, regard cible 17-25)
- **Deo Munduku** (conseiller pro orientation, si dispo)

100 cas review sur les ~1020 produits :
- Sample stratifié par catégorie (au prorata : 18 lyceen / 20 reorientation /
  14 actif / 16 master / 16 famille / 12 meta / 6 non-cadre = 100)
- Inspection : qualité conseiller, factualité, hallu, posture, tone
- Décision finale dataset Sprint 10 : keep / drop / re-generate

---

## 10. Reproductibilité

```bash
cd ~/projets/OrientIA && source .venv/bin/activate

# Tests Sprint 9-data
pytest tests/test_generate_golden_qa.py -v

# Sanity check imports / parsing YAML
python -c "import yaml; data = yaml.safe_load(open('config/diverse_prompts_50.yaml')); print(f'{len(data[\"prompts\"])} prompts loaded')"

# Dry-run (1 prompt × 5 itérations)
python scripts/generate_golden_qa_v1.py \
  --config config/diverse_prompts_50.yaml \
  --output data/golden_qa/dryrun_test.jsonl \
  --filter-prompt-id A1 --max-iterations 5 --parallel 2 \
  --model claude-opus-4-7 --rate-limit-delay 1.0 --max-retries 3

# Lancement nuit (Max 5x → parallel 2, target 1020)
bash scripts/launch_qa_gen_nuit.sh 2 1020
# Reattach surveillance
tmux attach -t qa-gen
# Graceful shutdown
tmux send-keys -t qa-gen C-c
```

---

## 11. Sprint 9-data status final

✅ Phase 1 — Audit codebase + lecture draft v2 + annexe (test set v3 mapping + phrasings humains)
✅ Phase 2 — Conversion 51 prompts → YAML strict (1412 lignes, 264 seeds)
✅ Phase 3 — Audit cross-check Jarvis YAML (clean)
✅ Phase 4 — Implem `generate_golden_qa_v1.py` (4 phases + rate limit + checkpointing + signal)
✅ Phase 5 — Tests `test_generate_golden_qa.py` (56 verts, 1628 globale, 0 régression)
✅ Phase 6 — Bash launcher `launch_qa_gen_nuit.sh` (tmux session-name qa-gen detachable)
✅ Phase 7 — Audit cross-check Jarvis script (clean, 4 obs mineures non-bloquantes)
🟡 Phase 8 — Dry-run A1 × 5 itérations (en cours, results pending)
🟡 Phase 9 — Go/no-go Matteo 17h (en attente)
🟡 Phase 10 — Lancement nuit 22h tmux + surveillance Jarvis (en attente)
🟡 Phase 11 — Sample humain 100 cas matin 29/04 (à venir)
🟡 Phase 12 — PR ouverte (à venir, NE PAS MERGER avant sample humain validé)

**Cumul Sprint 9-data Phase 1+2** :
- 4 nouveaux fichiers (1 YAML + 1 script Python + 1 bash launcher + 1 test)
- 2725 insertions, 0 deletion
- 56 tests verts, 1628/1629 suite globale (+ 1 skipped pré-existant), 0 régression
- 0 fichier protégé touché
- 0$ coût API cumulé (Phase 1+2 = 0 subprocess réel, dry-run = ~20 calls)
- Branche `feat/sprint9-data-pipeline-agentique`
- Audit Jarvis 2/2 positifs (YAML + script)

### Verdict synthèse défendable INRIA (à compléter post-nuit)

> _Section à enrichir mardi 29/04 après lancement nuit + sample humain._

L'argumentaire INRIA D5 ADR :

> "Premier conseiller IA d'orientation 17-25 ans avec dataset 1000 Q&A
> généré par pipeline agentique 4 phases sur Claude Opus 4.7 1M ctx avec
> recherche web live ONISEP/Parcoursup/APEC/France Compétences, validé
> par sample humain expert, déployé en inférence sur stack souverain
> Mistral France."

Sprint 9-data livre la première moitié (génération offline 1020 Q&A).
Sprint 10 livrera l'indexation FAISS + few-shot dynamique. Sprint 11
livrera l'eval HEART + sample humain élargi.

---

*Doc préparée par Claudette le 2026-04-28 sous l'ordre
`2026-04-28-1130-claudette-orientia-sprint9-data-pipeline-agentique-1000qa`.
ADR pivot référence : `2026-04-28-orientia-pivot-pipeline-agentique-claude.md` (vault Obsidian).
Source draft v2 : `docs/sprint9-data-50-prompts-draft.md` (commit `ab0ab3d`).*
