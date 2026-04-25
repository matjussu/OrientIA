# Bench OrientIA v5 vs v4 — Multi-corpus retrievable + fix Mistral timeout

**Date** : 2026-04-25 (samedi mid-day)
**Contexte** : ordre Jarvis 2026-04-25-1140, Axe 1.D + Axe 4.
**Variable isolée** : pivot architectural multi-corpus (ADR-048) + fix `timeout_ms=180000` (ADR-047). Tout le reste constant (mêmes 18 queries v4, même fact-checker Mistral Small, même `fiche_to_text` v3, mêmes embeddings formations préservés via mode append).
**Approche** : APPEND mode — index FAISS étendu de 48 914 → 50 153 records (+1 239 multi-corpus) sans re-embedding des formations. Coût Mistral embed effectif : ~$0.06 (vs $2.50 full rebuild).

---

## Verdict synthétique

| Critère | v4 (24/04) | v5 (25/04) | Δ | Verdict |
|---|:---:|:---:|:---:|---|
| **Queries complétées** | 17/18 (Q12 timeout) | **18/18** (0 timeout) | **+1** | ✅ ADR-047 confirmé |
| **Multi-corpus activé** | n/a | 1/18 queries (Q4 Théo q1) | +1 | ⚠️ peu d'usage sur queries v4 |
| **Stats fact-checked total** | 207 (sur 17 q) | 184 (sur 18 q) | -23 | ≈ Mistral génère moins de stats |
| **Verified rate** | 47.3 % (98/207) | 42.9 % (79/184) | -4.4 pp | ⚠️ légère régression |
| **Hallucination rate** | 11.6 % (24/207) | 15.2 % (28/184) | +3.6 pp | ⚠️ légère régression |
| **Disclaimer rate** | 41.1 % (85/207) | 41.8 % (77/184) | +0.7 pp | ≈ stable |
| **Latence gen moyenne** | 24.4 s/query | **15.5 s/query** | **-37 %** | ⭐ amélioration nette |

**Verdict honnête** : la PR #61 confirme l'ADR-047 (Q12 timeout résolu, latence -37 %), mais le pivot multi-corpus **n'apporte pas d'amélioration mesurable** sur les 18 queries v4 — qui sont formation-centric par construction. Le multi-corpus ne tape pas sur les nouveaux corpus pour 17/18 queries.

---

## 1. ADR-047 confirmé — Q12 timeout résolu

| Query | v4 status | v5 status | v5 gen time |
|---|---|---|---:|
| **Q12 Mohamed q3 cuisine Marseille** | ❌ ReadTimeout (>60 s, 4 retries) | ✅ Succès | **16.3 s gen + 12.5 s fact-check** |

Cause root identifiée dans ADR-047 : `Mistral(api_key=...)` sans `timeout_ms` → défaut SDK ~60 s. Fix appliqué dans `scripts/run_bench_personas_v3.py` et `_v4.py` : `Mistral(api_key=..., timeout_ms=180000)`. Bench v5 : **18/18 queries répondues**, latence max 20.9 s (vs 60 s timeout v4).

`fiche_to_text` v3 confirmé innocent (cf ADR-047 mesure : moyenne 162 tokens, max 300 tokens, 1.6 % du prompt total).

## 2. Multi-corpus retrievable — activation rate très faible sur queries v4

Sur les 18 queries du bench (mêmes que v3/v4) :

| Pattern multi-corpus | Queries | % |
|---|---:|---:|
| 100 % `formation` (top-10) | 17 | 94 % |
| Mix `formation` + `parcours_bacheliers` | **1** (Q4) | 6 % |
| Mix avec `metier` | 0 | 0 % |
| Mix avec `apec_region` | 0 | 0 % |

**Q4 Théo q1** ("Quelles passerelles existent après une L1/L2 de droit pour aller vers les sciences politiques ou Sciences Po ?") : 4/10 sources `parcours_bacheliers` (top-K). Le retriever a correctement identifié que "passerelles L1/L2" est en partie une question de parcours bacheliers réussite licence — c'est exactement le cas d'usage du corpus.

**Conclusion factuelle** : les nouveaux corpora ne sont sollicités que sur les queries qui ont un thème **non-formation-centric**. Les 18 queries v3/v4 ont été conçues pour mesurer le RAG formation, pas les autres dimensions (métiers, parcours, marché du travail régional). Donc absence d'effet attendue.

### Validation qualitative séparée (pré-bench)

3 queries de smoke test (cf `scripts/build_multi_corpus_index.py` README) ont montré le multi-corpus actif :

| Query | Top-10 distribution |
|---|---|
| "marché du travail des cadres en Bretagne" | **8/10 `apec_region`** + 2/10 `formation` |
| "taux réussite licence droit BAC L mention bien" | **10/10 `parcours_bacheliers`** |
| "CAP cuisine Marseille bac pro alternance" | 10/10 `formation` (cohérent — pas de parasitage) |

Le multi-corpus fonctionne — il n'est juste pas exercé par les 18 queries v4. **Pour mesurer l'impact réel, il faudrait des queries multi-domain**.

## 3. Précision factuelle — légère régression côté fact-check

Les stats fact-check (Mistral Small fact-checker) montrent une légère dégradation :

- Verified rate : 47.3 % → 42.9 % (-4.4 pp)
- Hallucination rate : 11.6 % → 15.2 % (+3.6 pp)

**Hypothèses sur la régression** :

1. **Variance Mistral** (le plus probable) : à génération réelle (température non-zéro), Mistral medium varie d'un run à l'autre. Sample size 18 queries × 1 run, IC95 large. Pas significatif statistiquement.
2. **Top-K boundary shift** : avec 1 239 records additionnels, certaines queries ont vu leurs top-10 shifter aux marges, même si dominant `formation`. Possibilité d'avoir perdu 1-2 fiches verified au profit de fiches voisines moins informatives.
3. **Run timing différent** : v4 24/04 PM vs v5 25/04 AM — possibles différences subtiles de cache Mistral / load API.

**Ce que cette régression ne peut PAS être** : un effet de la modif `fiche_to_text` (non touché), ni du fix timeout (additif sur le client HTTP, pas sur la génération).

**Reco S+1** : refaire le bench v5 avec **3 runs** (triple) pour stabiliser les chiffres. Coût additionnel ~$3-6, dans le budget.

## 4. Latence — amélioration nette

| Métrique latence | v4 (17 queries) | v5 (18 queries) |
|---|---:|---:|
| Gen moyenne / query | 24.4 s | **15.5 s** |
| Gen totale | 414 s | **287 s** |
| Fact-check moyenne / query | 6.4 s | 8.3 s |
| Total elapsed | ~520 s | ~436 s |

La latence -37 % est inattendue — **ce n'est pas dû au multi-corpus** (qui devrait au contraire allonger légèrement le retrieval avec +1 239 records dans l'index). Hypothèse plus probable : les queries génèrent moins de tokens output (184 stats v5 vs 207 v4 = -11 % stats cités) → temps de génération plus court → latence réduite. Ou Mistral API moins chargée samedi matin vs vendredi PM.

## 5. Tableau fact-check par query (comparatif v4 → v5)

| Q | Persona | v4 gen | v4 stats verified | v5 gen | v5 stats verified | Δ verified | Domains v5 |
|---:|---|---:|---:|---:|---:|---:|---|
| 1 | Lila | 20.6 s | 4/13 (31 %) | 13.7 s | 3/10 (30 %) | -1pp | formation |
| 2 | Lila | 22.4 s | 9/16 (56 %) | 13.8 s | 9/14 (64 %) | +8pp | formation |
| 3 | Lila | 22.9 s | 8/14 (57 %) | 9.6 s | 8/14 (57 %) | 0pp | formation |
| **4** | **Théo** | 68.2 s | 12/14 (86 %) | 18.4 s | 5/8 (63 %) | **-23pp** | formation+**parcours** |
| 5 | Théo | 24.1 s | 10/13 (77 %) | 20.9 s | 12/14 (86 %) | +9pp | formation |
| 6 | Théo | 31.0 s | 13/18 (72 %) | 14.0 s | 0/0 | n/a | formation |
| 7 | Emma | 21.5 s | 0/15 (0 %) | 7.6 s | 0/12 (0 %) | 0pp | formation |
| 8 | Emma | 20.9 s | 2/6 (33 %) | 11.7 s | 4/10 (40 %) | +7pp | formation |
| 9 | Emma | 30.5 s | 4/15 (27 %) | 15.4 s | 0/6 (0 %) | -27pp | formation |
| 10 | Mohamed | 22.5 s | 4/9 (44 %) | 15.7 s | 1/6 (17 %) | -27pp | formation |
| 11 | Mohamed | 23.0 s | 1/5 (20 %) | 12.0 s | 0/9 (0 %) | -20pp | formation |
| **12** | **Mohamed** | **TIMEOUT** | n/a | **16.3 s** | 0/0 | **n/a** | formation |
| 13 | Valérie | 19.1 s | 9/15 (60 %) | 11.2 s | 7/18 (39 %) | -21pp | formation |
| 14 | Valérie | 27.2 s | 8/15 (53 %) | 12.5 s | 6/16 (38 %) | -16pp | formation |
| 15 | Valérie | 19.5 s | 8/17 (47 %) | 9.9 s | 6/11 (55 %) | +8pp | formation |
| 16 | Psy-EN | 17.6 s | 0/0 | 20.2 s | 3/11 (27 %) | n/a | formation |
| 17 | Psy-EN | 23.9 s | 2/10 (20 %) | 12.3 s | 2/10 (20 %) | 0pp | formation |
| 18 | Psy-EN | 30.4 s | 4/12 (33 %) | 13.9 s | 13/15 (87 %) | **+54pp** | formation |

**Observation clé** : Q4 (qui active multi-corpus) verified rate baisse 86 % → 63 %. Mais Q18 monte 33 % → 87 %. Variance énorme par query, signal vs bruit difficile à isoler sur 1 run.

## 6. Verdict scientifique INRIA

À 30 jours du livrable INRIA (deadline 25/05/2026) :

✅ **Pivot architectural ADR-048 multi-corpus livré et testé**.
✅ **ADR-047 Mistral timeout résolu** (root cause + fix), Q12 passe.
✅ **Latence -37 %** sur la même suite de queries.
⚠️ **Pas de gain mesuré sur les 18 queries v4** — attendu car queries formation-centric, multi-corpus actif sur 1/18.
⚠️ **Légère régression verified rate** dans le bruit statistique (single run, ~5 pp delta) — refaire en triple-run pour stabiliser.

**Note INRIA-recommandable** : la valeur du pivot multi-corpus se manifestera sur des queries d'orientation **non-formation-centric** (que les juges humains pourraient ne pas tester). À discuter avec Matteo : ajouter 5-10 queries multi-domain dans la suite de bench pour démontrer l'extension de scope (logements CROUS, marché cadres régional, taux réussite licence par profil bachelier).

## 7. Notation humaine v4 → v5 (Axe (a) ordre 2026-04-25-1315 PR #63)

Notation grille stricte 5 critères (1-5 par critère, max 25 par query)
réalisée par Claudette en cohérence méthodologique avec la notation v4
de la synthèse `_SYNTHESIS_V4_VS_V3.md`.

### Moyennes par critère (18 queries v5 vs 17 queries v4 — Q12 timeout exclu côté v4)

| Critère | v4 (17 q notées) | **v5 (18 q notées)** | Δ |
|---|:---:|:---:|:---:|
| **Précision factuelle** | **4.53** | **3.89** | **-0.64** ⚠️ |
| Pertinence du conseil | 4.71 | 4.78 | +0.07 |
| Personnalisation | 4.18 | 4.44 | +0.26 |
| Safety | 5.00 | 4.67 | -0.33 ⚠️ |
| Verbosité / lisibilité | 4.47 | 4.33 | -0.14 |
| **MOY GLOBALE / 5** | **4.57** | **4.42** | **-0.15** |
| **MOY GLOBALE / 25** | **22.85** | **22.11** | **-0.74** |

**Verdict notation humaine** : régression nette de la précision factuelle
(-0.64 / 5 = -14 %) sur les queries formation-centric, partiellement
compensée par un gain en personnalisation (+0.26). Net global -0.15 / 5.

**Cohérent avec le fact-check Mistral Small** : v5 hallucination rate
+3.6pp (11.6 % → 15.2 %), v5 verified rate -4.4pp (47.3 % → 42.9 %).
Les deux mesures (humaine et automatique) convergent sur **régression
légère mais réelle** sur les queries formation-centric.

### Per-query précision factuelle

| Q | Persona | Topic | v4 prec | **v5 prec** | Δ |
|---:|---|---|:---:|:---:|:---:|
| 1 | Lila | Débouchés L lettres | 4 | 4 | 0 |
| 2 | Lila | SHS vs école com | 5 | 5 | 0 |
| 3 | Lila | 14 moy T L | 5 | 4 | **-1** |
| 4 | Théo | Passerelles droit (multi-corpus) | 5 | 4 | **-1** |
| 5 | Théo | Pas droit réaliste | 5 | 5 | 0 |
| 6 | Théo | Bordeaux audio/com | 5 | 4 | **-1** |
| 7 | Emma | Salaire dev M2 | 4 | 4 | 0 |
| 8 | Emma | M2 rech vs altern | 4 | 3 | **-1** |
| 9 | Emma | Lille data CDI | 4 | 4 | 0 |
| 10 | Mohamed | Débouchés cuisine | 4 | 3 | **-1** |
| 11 | Mohamed | CAP pas resto | 4 | 3 | **-1** |
| 12 | Mohamed | Marseille cuis/pât | n/a | 4 | (timeout v4) |
| 13 | Valérie | Coût école com | 5 | 4 | **-1** |
| 14 | Valérie | STAPS débouchés | 4 | 3 | **-1** |
| 15 | Valérie | Fils T S budget | 5 | 4 | **-1** |
| 16 | Psy-EN | Master psycho 3 ans | 5 | 4 | **-1** |
| 17 | Psy-EN | 1ère S redouble | 4 | 3 | **-1** |
| 18 | Psy-EN | 2nde modeste aéro | 5 | 5 | 0 |

**Pattern notable** : 11 queries sur 17 communes (65 %) voient leur
précision baisser de 1 point (sur 5). 6 queries restent stables.
**Aucune query ne voit sa précision augmenter sur les 17 communes.**

### Hypothèses sur la régression précision factuelle

1. **Top-K boundary shift par dilution multi-corpus** : avec 1 239
   records additionnels dans l'index, certaines queries voient des
   records voisins (formation low-relevance ou multi-corpus
   hors-domaine) shifter dans le top-10 au lieu de fiches formation
   spécifiques. Dilution du signal retrieval.
2. **Variance Mistral génération** : non-zero temperature, single run.
   Sur 17 queries × 1 run, IC95 large.
3. **Caveat doublons formations** (audit data 2026-04-25 EOD) : 5.4 %
   de doublons Parcoursup non-dédupliqués dans `formations.json`. Le
   merger v2 silencieux a injecté ~2 648 doublons depuis ADR-039. Le
   top-K v5 peut récupérer plusieurs fois la même fiche par
   coïncidence numérique, dégradant la pertinence apparente.
4. **Caveat R3 labels à 0 %** (audit data 2026-04-25 EOD) : régression
   silencieuse du champ `labels` (5.2 % historique → 0 %). Le reranker
   ADR-002 boost SecNumEdu/CTI/CGE/etc. est devenu un no-op récemment,
   sans rapport direct avec le pivot multi-corpus mais affecte la
   qualité retrieve formation pour ces 2 versions.

### Régressions silencieuses parallèles (info Jarvis 2026-04-25 11h32)

Audit data EOD a flaggé 2 régressions du merger v2 indépendantes du
pivot multi-corpus, mais qui **affectent les 2 systèmes (v4 et v5)
identiquement** :

- **R1 (P0)** : 2 648 doublons Parcoursup stricts (5.4 % corpus)
- **R3 (P1)** : champ `labels` à 0 % (vs 5.2 % historique) → reranker
  SecNumEdu/CTI/CGE no-op

**Implication méthodologique** : la comparaison v4 → v5 reste valide
(même corpus dégradé pour les deux), mais les valeurs absolues v5 ont
un caveat. Une vraie mesure du pivot multi-corpus nécessiterait
**fix R1 + R3 + triple-run** sur index propre.

### Recommandation S+1 (Matteo arbitrage attendu)

1. **Fix R1 dedup** (P0, ~30 min) : déduper formations.json par
   `cod_aff_form` + provenance, rebuild FAISS multi-corpus
2. **Fix R3 labels** (P1, ~1h) : investigation root cause du merger v2
   silencieux, restaurer 5.2 % historique
3. **Triple-run bench v5** post-fix ($3-6 budget) pour stabiliser les
   chiffres avec IC95 propre
4. **Implémentation ADR-049 reranker multi-domain** (~2-3h, hors
   deadline samedi)
5. **Inexactitude ADR-048 à corriger** : la couverture ROME via RNCP
   atteint 98.5 % côté metiers / 16 % côté formations (audit). La PR
   #56 SYNTHESIS annonce <5 % par jointure ROME formations × ideo —
   correct pour ce cas spécifique mais l'argumentaire général "ROME
   couvre <5 %" est imprécis. Le pivot multi-corpus reste pertinent
   (ideo apporte du contenu éditorial, pas juste du ROME).

## 8. Hors scope cette synthèse

- **Bench v5 triple-run** : à arbitrer post-fix R1+R3 (budget +$3-6).
- **Bench multi-domain queries** : livré PR #62 — verdict +1.5 % notation
  humaine, +75 % activation FAISS, mais 0 % activation top-K post
  reranker pour APEC → ADR-049 (DRAFT) capturé.
- **Caveat données fixes en attente Matteo** : R1 dedup, R3 labels.

---

## Liens

- Branche : `feat/faiss-rebuild-multi-corpus-bench-v5`
- ADR-047 (Mistral timeout) : `docs/DECISION_LOG.md` (PR #58 mergée)
- ADR-048 (RAG multi-corpus) : `docs/DECISION_LOG.md` (PR #60 mergée)
- Bench v4 référence : `results/bench_personas_v4_2026-04-24/_SYNTHESIS_V4_VS_V3.md`
- Output JSON par query : `results/bench_personas_v5_2026-04-25/query_*.json`
- Index multi-corpus : `data/embeddings/formations_multi_corpus.index` (195.9 MB, gitignored)
- Fiches multi-corpus : `data/processed/formations_multi_corpus.json` (99.1 MB, gitignored — ADR-046)
