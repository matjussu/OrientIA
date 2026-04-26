# Verdict bench persona complet — baseline pré-agentique (2026-04-26)

**Date** : 2026-04-26 après-midi (ordre Jarvis 2026-04-26-1210)
**Scope** : baseline scientifique unified pré-bascule axe B agentique
**Index** : `formations_multi_corpus_phaseD.index` (54 297 vecteurs =
phaseB 49 295 + DARES 111 + blocs 4 891) — **état "main actuel post
DARES + blocs + tune ×1.0"**
**Bench** : 48 queries × 3 runs (triple-run IC95) sur 4 sous-suites
**Eval qualitatif** : Claude Sonnet 4.5 sur 18 personas v4 evals (TOOL
hors stack prod Mistral souverain, distinction épistémique préservée)
**Coût** : ~$0.40 (Mistral $0.30 triple-run + Anthropic $0.10 eval)

---

## Résumé exécutif (1 page)

**Baseline officielle pré-agentique** :
- **39.4 % verified, 17.9 % halluc** (global unified, n=3 IC95 ±3.66pp / ±3.90pp)
- **48 queries × 3 runs**, 4 sous-suites couvrant tout le spectre OrientIA

Cette baseline servira de **point d'ancrage scientifique** pour mesurer
les gains réels de la bascule axe B agentique (kick-off samedi 02/05).
Sans cette mesure pre-agentique, les claim post-agentique ne
pourraient pas être chiffrés honnêtement vs un baseline propre.

**Insights majeurs** :

1. **Le bench shipping personas v4 sous-estimait la régression DARES**
   — sur les 18 queries formation-centric (sous-suite 1), DARES n'est
   pas activé. Sur les 10 queries DARES dédiées (sous-suite 2), halluc
   monte à **30.9 %** (vs 13.4 % sur sous-suite 1). Le tune ×1.0 a
   atténué la régression mais le contenu DARES reste toxique pour la
   génération LLM même sans boost.
2. **Les blocs RNCP cohabitent mieux que DARES** : halluc 17.4 % sur
   sous-suite blocs (boost ×1.5 dominant 9/10 top-K) vs 30.9 % DARES.
   Le contenu pédagogique des blocs (« assurer la maintenance
   frigorifique ») est moins fabricable que les chiffres aggregés
   DARES (« 488 700 postes 2019-2030 »).
3. **User-naturel surprise** : best verified rate (48.7 %, mais variance
   ±16 pp). Les 10 queries user-naturel restent toutes sur formation
   domain en top-K (10/10 formation, 1 émergence metier_prospective,
   1 competences_certif). Pas de cohabitation multi-corpus naturelle —
   le L2 brut privilégie les fiches Parcoursup riches.
4. **Hallucinations régulières détectées** par eval qualitatif Claude :
   6/18 personas v4 — incluant **1 erreur réglementaire critique**
   (titre RNCP psychologue niveau 6 alors que titre protégé bac+5
   niveau 7).

---

## 1. Méthodologie

### 1.1 Architecture index

`formations_multi_corpus_phaseD.index` (NEW pour ce bench) — 54 297
vecteurs combinés via reuse $0 (cf `scripts/build_index_phaseD.py`) :

- 49 295 vecteurs phaseB (formations + 1 705 multi-corpus existants)
- 111 vecteurs DARES Métiers 2030 (PR #70, boost reranker ×1.0 post tune PR #73)
- 4 891 vecteurs blocs RNCP (PR #71, boost reranker ×1.5)

Pas d'embed neuf — extraction depuis indexes Phase C existants.

### 1.2 4 sous-suites unified

| Sous-suite | n queries | Calibration | Boost activé attendu |
|---|---:|---|---|
| 1. PERSONAS v4 | 18 | formation-centric (déjà bench v5++/v5+++) | rare |
| 2. DARES dédiées | 10 | calibrées prospective FAP/2030/postes pourvoir | metier_prospective ×1.0 |
| 3. Blocs dédiées | 10 | calibrées contenu pédagogique/blocs/VAE | competences_certif ×1.5 |
| 4. User-naturel | 10 | sans trigger pattern, multi-domain croisé | None (pure L2) |

### 1.3 Triple-run IC95

3 runs séquentiels avec offset 30s + 60s pour décorréler API rate limits
Mistral. Aggregate via t-distribution df=2 (t=4.303 pour 95% CI sur n=3).

### 1.4 Eval qualitatif Claude-sonnet

Claude Sonnet 4.5 utilisé sur run1 uniquement (18 personas v4 evals)
comme **outil méthodo distinct de la stack RAG prod Mistral**. POV
persona simulé : description + question + réponse RAG → verdict + flag
hallu + suggestion. Pattern judge multi-LLM (cf `src/eval/judge.py`).

---

## 2. Résultats chiffrés

### 2.1 Global unified

| Métrique | run1 | run2 | run3 | Mean ± IC95 |
|---|---:|---:|---:|---|
| n_stats fact-check | 470 | 472 | 479 | 473.7 ± 13.45 |
| pct_verified | 38.5 | 41.1 | 38.6 | **39.4 ± 3.66pp** |
| pct_hallucinated | 19.6 | 17.6 | 16.5 | **17.9 ± 3.90pp** |
| avg_gen | 12.91s | 12.27s | 11.87s | 12.35 ± 1.30s |

### 2.2 Per sous-suite

#### Sous-suite 1 : PERSONAS v4 (18 queries)

| Métrique | run1 | run2 | run3 | Mean ± IC95 |
|---|---:|---:|---:|---|
| pct_verified | 46.7 | 44.7 | 42.8 | **44.7 ± 4.84pp** |
| pct_hallucinated | 17.5 | 9.2 | 13.5 | **13.4 ± 10.31pp** |
| avg_gen | 13.64s | 12.93s | 13.05s | 13.21 ± 0.94s |

✅ Best halluc rate (13.4 %, mais variance large ±10 pp).
Cohérent avec triple-run blocs nuit (bench shipping v5+++ blocs : -5.4 pp halluc IC95).

#### Sous-suite 2 : DARES dédiées (10 queries)

| Métrique | run1 | run2 | run3 | Mean ± IC95 |
|---|---:|---:|---:|---|
| pct_verified | 23.5 | 23.4 | 22.7 | **23.2 ± 1.08pp** ⚠️ |
| pct_hallucinated | 43.5 | 27.7 | 21.6 | **30.9 ± 28.08pp** ⚠️ |
| avg_gen | 12.19s | 12.0s | 10.76s | 11.65 ± 1.93s |

⚠️ **Halluc 30.9 % = pire sous-suite**. Confirme la régression
structurelle DARES post tune ×1.0. IC95 énorme (±28 pp) reflète la
variabilité du LLM face au contenu DARES dense en chiffres
recombinables.

#### Sous-suite 3 : Blocs RNCP dédiées (10 queries)

| Métrique | run1 | run2 | run3 | Mean ± IC95 |
|---|---:|---:|---:|---|
| pct_verified | 20.5 | 30.0 | 18.5 | **23.0 ± 15.26pp** |
| pct_hallucinated | 25.0 | 12.5 | 14.8 | **17.4 ± 16.53pp** |
| avg_gen | 11.63s | 9.45s | 9.82s | 10.30 ± 2.90s |

Halluc moyen (17.4 %), variance large (±16 pp). Boost ×1.5 dominant
(9/10 top-K avec competences_certif). Verified bas (23 %) car les blocs
ont peu de stats numériques vérifiables — le fact-checker extrait
moins.

#### Sous-suite 4 : User-naturel multi-domain (10 queries)

| Métrique | run1 | run2 | run3 | Mean ± IC95 |
|---|---:|---:|---:|---|
| pct_verified | 41.1 | 52.1 | 52.8 | **48.7 ± 16.30pp** |
| pct_hallucinated | 5.4 | 26.4 | 19.4 | **17.1 ± 26.56pp** |
| avg_gen | 13.58s | 14.16s | 12.92s | 13.55 ± 1.54s |

✅ Best verified (48.7 %, mais variance ±16 pp). Halluc moyen (17.1 %).
**0 émergence multi-corpus naturelle** : 10/10 queries restent sur
formation domain, 1 émergence metier_prospective, 1 émergence
competences_certif. Le L2 brut privilégie Parcoursup riche.

### 2.3 Domain coverage top-K (run1, illustratif)

| Sous-suite | formation | metier_prospective | competences_certif | autres |
|---|---:|---:|---:|---|
| personas_v4 (18q) | 18/18 | 0 | 2 | metier 1, parcours_bach 1 |
| dares_dedie (10q) | 5/10 | **8/10** | 0 | apec_region 2 |
| blocs_dedie (10q) | 3/10 | 0 | **9/10** | — |
| user_naturel (10q) | 10/10 | 1 | 1 | metier 1 |

⚠️ **Cohabitation user-naturelle quasi-nulle** — les pivots DARES /
blocs ne remontent dans top-K user-naturel que via patterns spécifiques.
En conditions naturelles, formation domine. C'est un signal pour
l'agentique : retrieval pure-L2 ne suffit pas pour exploiter les
corpora ajoutés.

---

## 3. Eval qualitatif persona (Claude Sonnet 4.5, n=18)

### 3.1 Distribution verdicts

| Verdict | Count | % |
|---|---:|---:|
| utile_partielle | 8 | 44 % |
| hallu_detecte | 6 | **33 %** ⚠️ |
| claire | 3 | 17 % |
| error parse | 1 | 6 % |
| **Actionnable** | 16 | 89 % |
| **Compréhensible** | 17 | 94 % |

✅ 89 % actionnable et 94 % compréhensible — l'output reste utilisable
même si imparfait.
⚠️ 33 % hallu détectées sur les seules personas v4 — supérieur au
17.9 % halluc fact-checker global, signe que le LLM-as-evaluator catch
des erreurs que le StatFactChecker rate (erreurs réglementaires,
formations inventées, liens fictifs).

### 3.2 Hallucinations détectées (extrait)

| Persona | Query | Type halluc |
|---|---|---|
| lila | q1 (débouchés licence lettres) | Stats insertion 44-74 % CDI inventées (annotées "non vérifié") |
| lila | q2 (fac vs école com) | Stats insertion 44 %/70-80 % CDI/2200 € inventées |
| emma | q3 (M1 info Lille data) | **Formations inventées** : DU IA Sciences-U Lille, MSc Big Data avec liens fictifs |
| valerie | q2 (STAPS débouchés) | Stats taux 55-68 %, vœux -34 %, salaire 2200 € inventés |
| valerie | q3 (kiné Terminale S) | Stat 5-10 % IFMK non sourcée |
| psy_en | q1 (insertion master psycho) | **Erreur réglementaire critique** : Titre RNCP Psychologue niveau 6 mentionné, alors que titre protégé exigeant master bac+5 niveau 7 obligatoire |

### 3.3 Suggestions récurrentes (Claude POV personas)

1. **Retirer stats non vérifiées** ou remplacer par fourchettes
   officiellement sourcées (5/18 evals)
2. **Vérifier existence des établissements/formations cités** (3/18)
3. **Ajouter dates concrètes** de candidature, délais (3/18)
4. **Ajouter contacts concrets** (CFA, missions locales) pour
   actionnabilité (2/18)
5. **Sources salary surveys APEC** ou enquêtes écoles pour
   crédibiliser fourchettes (2/18)

### 3.4 Caveat épistémique sur l'eval

Claude Sonnet 4.5 utilisé comme **TOOL méthodo séparé** de la stack
prod RAG (100 % Mistral souverain). Ses verdicts représentent un
**second avis LLM-judge** distinct du fact-checker StatFactChecker
Mistral aval. Cohérent avec le pattern judge multi-LLM (Claude + GPT-4o
+ Haiku) du Run F+G. Pour le dossier INRIA, présenter Claude eval
comme "outil d'analyse externe", pas comme composant prod.

---

## 4. Caveats méthodologiques

### 4.1 Sample size + variance

n=3 runs sur 48 queries = sample relativement petit. IC95 reflète la
variance LLM run-to-run (générations différentes pour la même query).
Les sous-suites de 10 queries ont des IC95 larges (±10-28 pp) — les
deltas sub-IC95 ne sont pas statistiquement significatifs.

Pour un baseline solide post-INRIA, refaire en n=5 ou n=10 runs
réduirait l'IC95 (loi √n). Coût : x3-7 le triple-run actuel.

### 4.2 Stress GAPs DATA_INVENTORY (sous-suite 4)

Les 10 user-naturel touchent les GAPs critiques :
- DROM-COM (q11), Bac pro (q12, q16), Reconversion (q13, q14),
  Financement (q15)

Sans bench A/B vs un index "phaseB only" (sans DARES sans blocs),
impossible de mesurer si l'ajout des 2 corpora aide *vraiment* sur
les user-naturel. À faire en complément si bande passante : 30 min,
$0.05 single-run phaseB seul.

### 4.3 Eval qualitatif n=18 only

Le persona qualitative eval s'arrête aux 18 personas v4 (3 par
persona × 6). N'évalue pas user-naturel ni blocs/DARES dédiés.
Extension future : eval similaire sur user-naturel pour mesurer la
qualité hors triggers.

### 4.4 Caveat L2-pure user-naturel

Sous-suite 4 mesure la **robustesse retrievability par L2 pure** —
révèle que les corpora ne remontent pas naturellement quand
sémantiquement pertinents. Cohérent avec le floor architectural
identifié sur DARES (cf `docs/VERDICT_BENCH_DARES_DEDIE.md` §4.4).
**Reflète la qualité que verra un user lambda** sans formulation
calibrée. Motive le pivot agentique J-23.

---

## 5. Décision baseline et bascule axe B

### 5.1 Baseline officielle figée

**À partir de maintenant, la baseline "main actuel post DARES + blocs +
tune ×1.0" est figée à : 39.4 % verified / 17.9 % halluc (IC95 ±3.66 /
±3.90, n=3 runs × 48 queries unified).**

Tout claim post-agentique qui mesurera "+X pp verified" ou "-Y pp halluc"
devra référer à cette baseline. Pas de re-bench main sans en
retriple-runner officiellement.

### 5.2 Validation bascule axe B

✅ **GO bascule axe B agentique** (consensus Claudette + Jarvis +
Matteo via order 1210).

Ce baseline livre :
1. Point d'ancrage scientifique INRIA — referenceable dans le dossier
2. 4 sous-suites distinctes pour analyser les gains agentique
   par cas d'usage (formation / prospective / compétences /
   user-naturel)
3. Eval qualitatif persona = signal d'amélioration produit (où ça
   coince actuellement → où l'agentique peut aider)

### 5.3 Roadmap agentique (informationnel)

L'agentique J-23 (focal samedi 02/05) cible spécifiquement :
- **Floor L2-only-DARES** (4/10 DARES dédiées) : agent peut décider
  de NE PAS utiliser DARES sur queries où il bruite
- **Cohabitation user-naturelle** (10/10 formation seul) : agent peut
  fusionner sources de domain différents quand pertinent
- **Hallucination réglementaire** (psy_en_q1 titre RNCP) : agent peut
  vérifier l'autorité d'une formation citée avant de la mentionner

---

## 6. Reproductibilité

```bash
cd ~/projets/OrientIA && source .venv/bin/activate

# 1. Build Phase D index ($0, ~5s)
python scripts/build_index_phaseD.py

# 2. Triple-run bench unified (~12 min × 3 = ~36 min en parallèle, $0.30)
python scripts/run_bench_persona_complet.py
python scripts/run_bench_persona_complet.py --out-suffix _run2
python scripts/run_bench_persona_complet.py --out-suffix _run3

# 3. Eval qualitatif Claude Sonnet ($0.10, ~3 min)
python scripts/persona_qualitative_eval.py
```

---

## 7. Annexe : Déclaration épistémique INRIA

Cette baseline a été établie selon les **garde-fous épistémiques**
capitalisés de la session 24-26 avril :

1. ✅ **Bench inclut des queries activantes pour chaque pivot** (DARES
   dédiées + blocs dédiées) — pas de shipping aveugle.
2. ✅ **Triple-run IC95** sur le baseline complet — pas de single-run
   isolé qui sous-estime la variance.
3. ✅ **Caveat upper-bound** documenté pour les sous-suites calibrées
   sur patterns regex.
4. ✅ **Floor architectural reconnu** comme limite produite, pas
   défaut caché — motive les axes V2 (agentique).
5. ✅ **Distinction épistémique** : Claude Sonnet eval = TOOL méthodo
   distinct de la stack prod Mistral souveraine. Pas de pollution
   stack.

Cette baseline est **honnête épistémiquement** : elle révèle les
limites courantes (33 % hallu détectées par persona eval, 30.9 %
halluc DARES dédiées, 0 cohabitation user-naturelle multi-corpus)
en même temps qu'elle fournit des chiffres globaux acceptables
(39.4 % verified / 17.9 % halluc).

C'est ce qu'on espère démontrer en INRIA : un système qui sait dire
ce qu'il sait, et ce qu'il ne sait pas encore.
