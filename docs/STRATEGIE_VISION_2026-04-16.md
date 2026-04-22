---
title: OrientIA — Vision stratégique et roadmap V2
date: 2026-04-16
status: REFERENCE — remplace AMELIORATIONS_2026-04-16.md comme nouveau document de référence
authors: Matteo (vision) + Jarvis (audit + structuration)
context: pivot stratégique post-Run F+G — repositionnement projet vers "système qui bat les IAs génératives" plutôt que "paper qui défend honnêtement un negative result"
---

# OrientIA — Vision stratégique et roadmap V2

## Table des matières

1. [Vision et pivot stratégique](#1-vision-et-pivot-stratégique)
2. [État actuel — où on en est vraiment](#2-état-actuel--où-on-en-est-vraiment)
3. [Diagnostic d'expert — pourquoi le RAG actuel n'aide pas](#3-diagnostic-dexpert--pourquoi-le-rag-actuel-naide-pas)
4. [Acquis à préserver](#4-acquis-à-préserver)
5. [Stratégie — les 4 axes d'attaque](#5-stratégie--les-4-axes-dattaque)
   - [Axe 1 — Data foundation](#axe-1--data-foundation-le-levier-1)
   - [Axe 2 — Architecture agentic multi-step](#axe-2--architecture-agentic-multi-step-le-levier-2)
   - [Axe 3 — Fine-tuning RAFT](#axe-3--fine-tuning-raft-spécialisation-souveraine)
   - [Axe 4 — Différenciateurs UX](#axe-4--différenciateurs-ux-le-wow-factor-jury)
6. [Refonte du benchmark V2](#6-refonte-du-benchmark-v2)
7. [Hiérarchisation et ordre d'attaque](#7-hiérarchisation-et-ordre-dattaque)
8. [Stratégie v1 minimale si deadline serrée](#8-stratégie-v1-minimale-si-deadline-serrée)
9. [Réponse à la critique tuteur INRIA](#9-réponse-à-la-critique-tuteur-inria)
10. [Principes directeurs](#10-principes-directeurs)
11. [Décisions à trancher maintenant](#11-décisions-à-trancher-maintenant)
12. [Annexes](#12-annexes)

---

## 1. Vision et pivot stratégique

### 1.1 La vision

**OrientIA est un assistant d'orientation conçu pour battre concrètement les IAs génératives généralistes (ChatGPT, Claude, Mistral chat) sur l'accompagnement des lycéens et étudiants français vers leurs études et leur futur professionnel.**

Pas un paper de recherche. Pas une démonstration méthodologique. Un produit qui marche.

### 1.2 Le pivot — d'où on vient, où on va

Le projet a longtemps été framé comme une **étude de la méthodologie RAG re-ranking** pour le concours INRIA. Cette framing avait du sens académiquement, mais a deux problèmes graves révélés par Run F+G :

1. **Empiriquement** : le RAG actuel ne contribue rien sur la rubric nue (-0.27 vs prompt seul). La thèse "RAG re-ranking améliore l'orientation" n'est pas démontrable telle quelle.
2. **Stratégiquement** : le concours INRIA est jugé sur la **qualité du système**, pas sur la rigueur du papier. Un système qui présente honnêtement un échec méthodologique perd face à un système qui produit des réponses concrètement meilleures.

**Le repivot** :

| Avant | Après |
|---|---|
| "Étude de méthodologie RAG re-ranking" | "Système d'orientation qui bat les IAs génératives" |
| Le benchmark = la finalité | Le benchmark = garde-fou de qualité |
| RAG single-shot tuné finement | Architecture agentic multi-axe |
| Corpus minimal mais scientifiquement isolé | Corpus enrichi exploitant tous les opens data publics |
| Mistral fine-tuning = "future work" | RAFT = piste sérieuse à attaquer |
| Pas d'UX (FastAPI optionnelle) | Différenciateurs UX comme partie intégrante du produit |

### 1.3 Le problème qu'OrientIA résout vraiment

Un lycéen de terminale, ses parents, un·e étudiant·e qui veut se réorienter, font face à :
- Un labyrinthe administratif (Parcoursup, calendriers, dossiers, candidatures parallèles)
- Une asymétrie d'information (les écoles privées font du marketing, les formations publiques labellisées sont mal référencées)
- Une fragmentation des sources (ONISEP, Parcoursup, France Travail, sites écoles, témoignages forums)
- Des chiffres qui changent chaque année (taux d'accès Parcoursup, places ouvertes, salaires post-diplôme)
- Un manque de personnalisation (les conseillers d'orientation sont surchargés, ChatGPT donne des réponses génériques)

Les IAs génératives généralistes échouent sur **trois dimensions critiques** :

1. **Données fraîches** : leur cutoff est janvier 2026 max → elles ne savent pas les chiffres Parcoursup 2025-2026
2. **Personnalisation profile** : pas de mémoire utilisateur, pas de modèle bac/notes/contraintes
3. **Actionabilité** : elles produisent du wall-of-text, pas un calendrier interactif, pas de calculator de score, pas de comparateur visuel

OrientIA peut écraser ChatGPT précisément sur ces 3 dimensions, **si** on construit le bon produit.

### 1.4 Hypothèse de travail

> *"Un assistant d'orientation qui combine (a) une base de connaissances française enrichie en continu, (b) une architecture agentic qui décompose les questions et croise les sources, (c) un modèle Mistral fine-tuné spécialisé orientation, et (d) une UI dédiée au métier (calendrier, calculator, comparateur), bat structurellement les IAs génératives généralistes sur l'accompagnement à l'orientation des étudiants français."*

C'est cette hypothèse que les 4 axes ci-dessous attaquent.

---

## 2. État actuel — où on en est vraiment

### 2.1 Ce qui marche

- **Pipeline RAG fonctionnel** : ingestion 443 fiches, FAISS indexé, retriever + reranker + MMR + intent classifier, generator Mistral medium. 30+ runs documentés. 231 tests verts.
- **Système prompt v3.2 efficace** : contribue +3.71 pts vs fair baseline (Claude). C'est un acquis mesurable, ne pas le casser.
- **Méthodologie d'évaluation rigoureuse** : 100q dev/test, 7-system ablation, dual-judge + fact-check, blinding, inter-judge κ 0.46-0.59. Ça reste utile pour mesurer les améliorations.
- **Décision-log + traçabilité** : 15 ADR, SESSION_HANDOFF, METHODOLOGY. Excellent pour onboarding et continuité.
- **Code modulaire** : retriever / reranker / generator / judge bien séparés. Refactorer vers agentic ne demande pas un rewrite from-scratch.

### 2.2 Ce qui ne marche pas (chiffres)

Run F+G triple-layer (100q × 7 systèmes × 3 juges, 2026-04-16) :

| Système | Claude v1 | Claude v2 (factcheck) | GPT-4o v1 | Honesty (Haiku) |
|---|---|---|---|---|
| `mistral_v3_2_no_rag` (prompt seul) | 15.43 | 14.39 | 16.12 | 0.562 (7e/7) |
| `our_rag` (prompt + RAG) | 15.16 | 14.33 | 16.16 | 0.575 (6e/7) |
| Δ RAG vs prompt-only | **-0.27** | **-0.06** | +0.04 | +0.013 |

- Le RAG contribue **0 à -0.27** sur la rubric nue
- Le shift fact-check (+0.21) est dans le bruit (single run, pas d'IC95%)
- Le honesty score d'`our_rag` est 6e/7 — la "mémoire ancrée" est marginale
- Sur cross_domain (8 questions hors scope cyber/data), le RAG perd -1.12 même après fact-check

### 2.3 Diagnostic data (chiffré)

Source : audit AMELIORATIONS §3.

| Dimension | Chiffres | Lecture |
|---|---|---|
| Champs Parcoursup CSV exploités | **17%** (20/118) | 98 colonnes droppées dont voe_tot_*, prop_tot_*, classements |
| Matching ONISEP réussi | **1.6%** (7/443 fuzzy) | 75.8% fiches sans duree, type_diplome, tutelle, url_onisep |
| Labels qualité remplis | **5.2%** (23/443) | SecNumEdu+CTI+CGE jamais branchés correctement |
| Débouchés ROME discriminants | **0%** | 9 codes hardcodés par domaine |
| `profil_admis` exposé au RAG | **Non** | Riche dans 100% des fiches mais jamais dans le contexte LLM |
| Taux insertion InserJeunes | **Absent** | Donnée DEPP disponible, jamais intégrée |

**Conclusion** : le corpus est creux à ~83%. Le RAG ne peut pas apporter ce qu'il n'a pas.

---

## 3. Diagnostic d'expert — pourquoi le RAG actuel n'aide pas

Au-delà du diagnostic data, voici les **4 causes racines** structurelles. Chacune attaquée par un axe de la stratégie.

### Cause #1 — Corpus affamé → Axe 1

Le LLM (Mistral medium) a "lu Internet" lors de son training jusqu'à fin 2025. Le RAG injecte un contexte qui contient moins d'informations que ce que le LLM sait déjà. Résultat : le RAG est au mieux redondant, au pire confondant (le contexte injecté contredit ou appauvrit la connaissance native).

**Implication** : tant que le corpus n'est pas plus riche que la mémoire native du LLM, le RAG ne peut pas créer de valeur.

### Cause #2 — Architecture single-shot → Axe 2

Le pipeline `question → 1 retrieve top-k → 1 generate` ne peut pas reproduire le raisonnement d'un conseiller d'orientation, qui est **multi-étapes** :

1. Clarifie le profil ("quel bac ? quelles notes ? quelle zone géographique ? quel budget ?")
2. Décompose la question ("quelles formations existent + quels débouchés métiers + quelle admissibilité + quelles passerelles")
3. Recherche **chaque axe séparément** dans des sources spécialisées
4. Croise les résultats et compose une réponse personnalisée
5. Anticipe les questions de suivi

Le RAG single-shot fait **1 seule requête**. Même un corpus parfaitement riche ne peut pas être exploité profondément avec un seul retrieve.

**Implication** : pour exploiter vraiment un RAG riche, il faut une architecture qui fait plusieurs requêtes spécialisées (= tools).

### Cause #3 — Pas de modèle utilisateur → Axe 2 (volet profil) + Axe 4 (UX)

Le système répond à une question abstraite. Il n'y a pas de profil étudiant, pas de mémoire de conversation, pas de continuité. Le system prompt v3.2 dit "termine par une question ouverte" mais on ne capture jamais les réponses suivantes.

Un vrai conseiller construit un dossier qui s'enrichit. ChatGPT non plus n'a pas ça (chaque conversation part de zéro). C'est précisément où OrientIA peut différencier en construisant un produit dédié au métier.

**Implication** : l'agentivité (Axe 2) doit avoir un volet profil utilisateur, et l'UX (Axe 4) doit le persister.

### Cause #4 — Données figées → Axe 1 D7 (cron refresh)

Parcoursup publie ses chiffres 2026-2027 en juin 2026. ONISEP met à jour en continu. France Travail publie InserJeunes annuellement. Notre corpus est figé depuis Run 6 (avril 2026). Mistral/ChatGPT/Claude ont des cutoffs autour de janvier 2026.

C'est précisément où un RAG live devrait écraser tout le monde : sur des questions "quel taux d'accès Parcoursup 2025 sur l'INSA Lyon en cyber ?", aucun chatbot généraliste n'a la réponse. **Mais notre système actuel ne l'a pas non plus.**

**Implication** : une mécanique de refresh automatique (cron mensuel sur APIs publiques) débloque un avantage structurel sur les modèles avec cutoff.

---

## 4. Acquis à préserver

Le repivot ne signifie pas tout balayer. Voici ce qui reste valide et qu'il faut **explicitement préserver** dans la V2.

### 4.1 Méthodologie d'évaluation
- 7-system ablation matrix → garder, étendre avec systèmes V2 et baselines naturels
- Dual-judge + fact-check → garder, c'est la rigueur qui prouve les progrès
- Dev/test split (32/68 hold-out) → garder, hold-out reste hold-out
- Inter-judge κ → garder, métrique standard
- Blinding seed-déterministe → garder, indispensable

### 4.2 Code modulaire
- `src/eval/` (judge, fact_check, runner, rate_limit, run_judge_multi) → garder, sera réutilisé pour bench V2
- `src/rag/` (embeddings, index, retriever, reranker, mmr, intent) → garder mais étendre — le retriever devient un *tool* parmi d'autres dans l'agent
- `src/prompt/system.py` v3.2 → conservé pour `our_rag_v2_data` (1ère étape), peut être adapté pour agent prompts en V3

### 4.3 Décisions documentées (ADR-001 à ADR-015)
- Chaque ADR reste valide jusqu'à preuve contraire
- Nouveaux ADR (021+) viennent étendre, pas remplacer
- ADR-001 (Mistral) → reste valide, Mistral reste le modèle générateur cible (souveraineté)
- ADR-005 (dev/test split) → renforcer encore avec V2 (test set jamais utilisé pour tuner)

### 4.4 Corpus de base
- Les 443 fiches restent. On les enrichit, on n'en supprime pas.
- `data/manual_labels.json` (25 entrées curées) → reste authoritative
- Index FAISS → re-build après enrichissement, mais pipeline de build inchangé

### 4.5 Documentation
- SESSION_HANDOFF.md → continue d'être source de vérité, mis à jour à chaque sprint
- DECISION_LOG.md → continue, append-only
- METHODOLOGY.md → met à jour avec nouvelles métriques V2
- AMELIORATIONS_2026-04-16.md → archivé (ce nouveau doc le remplace), garder pour historique

---

## 5. Stratégie — les 4 axes d'attaque

Pas de deadline imposée par cette stratégie (Matteo a confirmé que le temps n'est pas un blocage). Chaque axe vit indépendamment ; l'ordre §7 est recommandé pour ROI mais paralléliser est possible.

---

### Axe 1 — Data foundation (LE LEVIER #1)

#### Objectif
Passer d'un corpus 17% exploité à un corpus 80% exploité, avec données fraîches et discriminantes par formation/établissement/métier.

#### Mécanisme
Brancher les opens data français publics (gratuits) sur le corpus, exposer les champs riches déjà présents mais cachés, et installer un mécanisme de refresh continu.

#### Plan d'action détaillé

| # | Action | Détail technique | Effort | Coût |
|---|---|---|---|---|
| **D1** | Exposer `profil_admis` au RAG | Modifier `src/rag/embeddings.py:fiche_to_text` pour inclure mentions %, bac type % par formation. Re-générer les embeddings. | 4-6h | $0 |
| **D2** | ONISEP API live | Inscription gratuite `opendata.onisep.fr`. Nouveau module `src/collect/onisep_api.py`. Itérer par codes ROME ou mots-clés. Champs cibles : `duree`, `type_diplome`, `tutelle`, `url_onisep`, vidéos, témoignages. Cible : 22.6% → 80% champs ONISEP remplis. | 6-8h | $0 |
| **D3** | ROME 4.0 France Travail API | Inscription `francetravail.io` (clé gratuite). Nouveau module `src/collect/rome_api.py`. Pour chaque fiche : codes ROME spécifiques + description compétences + salaire médian + tension marché. Cible : différenciation réelle entre formations (Bachelor cyber vs Master cyber → débouchés différents). Endpoints :<br>- `https://francetravail.io/data/api/rome-4-0-metiers`<br>- `https://francetravail.io/data/api/rome-4-0-fiches-metiers`<br>- `https://api.gouv.fr/les-api/api-rome` | 10-12h | $0 |
| **D4** | Scraping labels qualité complets | Scraper SecNumEdu ANSSI, CTI, CGE. Matching fuzzy assoupli (threshold 80 vs 85 actuel). Cible : 5.2% → 60-80% labels.<br>- `https://cyber.gouv.fr/.../formation-secnumedu/`<br>- `https://www.cti-commission.fr/les-ecoles/annuaire`<br>- `https://www.cge.asso.fr/` | 4-6h | $0 |
| **D5** | InserJeunes / InserSup | Téléchargement dataset `data.gouv.fr/datasets/insertion-professionnelle-...`. Match par RNCP + établissement. Stocker `taux_insertion_6m`, `taux_insertion_12m`, `salaire_median_post_diplome`. Cible : réponses peuvent citer "85% d'insertion à 6 mois". | 4-6h | $0 |
| **D6** | Refonte schema FAISS + re-index | Mettre à jour `fiche_to_text` pour inclure tous nouveaux champs. Re-build embeddings (443 × 1024 dims Mistral). Validation : retrieval sur dev set montre amélioration sur questions ciblées. | 4-6h | $5-10 (mistral embed) |
| **D7** | Cron refresh mensuel | Nouveau module `src/collect/refresh_cron.py`. Refresh Parcoursup + ONISEP + InserJeunes mensuel. Détection de drift (nb fiches changé > 10%) → alerte. Garde le corpus frais contrairement aux LLMs avec cutoff. | 6-8h | $0 |

#### Exemple concret de gain

**Avant (corpus actuel)**, question "Bachelor cyber accessible à un bac techno avec mention bien ?" :
- Le RAG retourne 5 fiches cyber génériques (toutes avec les mêmes 9 codes ROME hardcodés)
- Le LLM ne sait rien sur le profil_admis (caché du contexte)
- Réponse : généralités sur le cyber, mention que c'est sélectif, pas de chiffre concret

**Après Axe 1**, même question :
- Le RAG retourne 5 fiches cyber avec leurs mentions % spécifiques (35% mention bien chez ESEA Pau, 18% à EFREI, etc.)
- Le LLM voit aussi le profil bac type (15% bac techno chez Pau, 5% chez EFREI, etc.)
- Le LLM voit aussi taux d'insertion 6m (Pau 88%, EFREI 92%) et débouchés ROME précis
- Réponse : "Pour bac techno mention bien : ESEA Pau réaliste (35% des admis ont mention bien, 15% issus de bac techno, 88% insertion 6m vers métiers ROME M1810/M1809)..."

#### Métriques de succès
- Couverture champs Parcoursup : 17% → **75%** minimum
- Match ONISEP : 1.6% → **75%** minimum
- Labels remplis : 5.2% → **60%** minimum
- Re-bench `our_rag_v2_data` vs `mistral_v3_2_no_rag` : Δ Claude rubric nue passe de **-0.27 → +1.0 minimum**
- Sur catégories réalisme + biais_marketing : gain attendu **+1.5 à +2** (questions concrètes nécessitent données concrètes)

#### Risques et mitigations

| Risque | Probabilité | Mitigation |
|---|---|---|
| API France Travail clé activation lente | Moyenne | Lancer demande clé J+0, parallèliser autres actions |
| Matching RNCP / établissement imparfait | Moyenne | Score de confiance par match + fallback exact-match strict |
| Données ONISEP incohérentes vs Parcoursup | Faible | Source-of-truth = Parcoursup pour overlap, ONISEP enrichit |
| Performance retrieval dégradée par fiches plus longues | Faible | Test dev set avant prod, MMR ajusté si nécessaire |

#### Fichiers à créer
- `src/collect/onisep_api.py`
- `src/collect/rome_api.py`
- `src/collect/labels_scraper.py` (SecNumEdu + CTI + CGE)
- `src/collect/inserjeunes.py`
- `src/collect/refresh_cron.py`
- `tests/test_onisep_api.py`, `tests/test_rome_api.py`, etc.

#### Fichiers à modifier
- `src/rag/embeddings.py:fiche_to_text` — exposer profil_admis + tous nouveaux champs
- `src/collect/merge.py` — pipeline d'enrichissement étendu
- `data/processed/formations.json` — nouveau schema (versionné v2)
- `data/embeddings/formations.index` — re-build (gitignored)

---

### Axe 2 — Architecture agentic multi-step (LE LEVIER #2)

#### Objectif
Refondre `our_rag` d'un pipeline single-shot en un agent orienté outils qui exploite vraiment le RAG enrichi par requêtes spécialisées multi-axes.

#### Mécanisme
Décomposer la réponse en plusieurs étapes : clarification profil → décomposition question → appels parallèles à des tools spécialisés → composition structurée. Imiter le raisonnement métier d'un conseiller d'orientation.

#### Architecture cible

```
┌────────────────────────────────────────────────────────┐
│ [question lycéen + (optionnel) profil session]         │
└──────────────────┬─────────────────────────────────────┘
                   ↓
┌──────────────────────────────────────────────────────────┐
│ Profile Clarifier Agent                                  │
│ - Extrait profil de la question (si déjà mentionné)      │
│ - OU demande clarifications nécessaires                  │
│ - Output : ProfileState{bac, notes, geo, budget,...}     │
└──────────────────┬───────────────────────────────────────┘
                   ↓
┌──────────────────────────────────────────────────────────┐
│ Decomposer Agent                                         │
│ - Split la question en sous-questions par axe            │
│ - Output : list[SubQuestion(axis, query, priority)]      │
└──────────────────┬───────────────────────────────────────┘
                   ↓ (en parallèle, tool-use)
   ┌───────────────┼───────────────┐───────────────┐
   ↓               ↓               ↓               ↓
[Tool: search_   [Tool: get_   [Tool: get_     [Tool: web_
 formations]      debouches]     calendar]       search]
[Tool: get_      [Tool: get_   [Tool: get_      ...
 insertion_       passerelles]   profil_admis_
 stats]                          stats]
   │               │               │               │
   └───────────────┼───────────────┘───────────────┘
                   ↓
┌──────────────────────────────────────────────────────────┐
│ Composer Agent                                           │
│ - Synthétise résultats tools en réponse structurée       │
│ - Plan A/B/C personnalisé selon profil                   │
│ - Tableau si comparaison demandée                        │
│ - Sources cliquables ONISEP/Parcoursup vérifiées         │
│ - Question de suivi pour enrichir profil                 │
└──────────────────┬───────────────────────────────────────┘
                   ↓
┌──────────────────────────────────────────────────────────┐
│ Validator Agent (optionnel)                              │
│ - Vérifie cohérence (pas de contradictions Plan A vs B)  │
│ - Détecte fabrications (sources citées existent)         │
│ - Re-prompt si problème détecté                          │
└──────────────────┬───────────────────────────────────────┘
                   ↓
            [Réponse finale]
```

#### Tools à implémenter

| Tool | Input | Output | Notes |
|---|---|---|---|
| `search_formations(filters)` | filtres : domain, niveau, ville, label, statut | list[Fiche] enrichie | Refacto du retriever existant |
| `get_debouches(rome_code)` | code ROME 4.0 | dict{description, salaires, tension, métiers} | Branche ROME API (Axe 1 D3) |
| `get_insertion_stats(rncp)` | code RNCP | dict{insertion_6m, insertion_12m, salaire} | Branche InserJeunes (Axe 1 D5) |
| `get_admission_calendar(parcoursup_code)` | code Parcoursup | dict{deadline_voeux, results, oraux} | Données Parcoursup live + statique |
| `get_passerelles(formation_id)` | id fiche | list[passerelle] | Branche ONISEP API (Axe 1 D2) |
| `get_profil_admis_stats(formation_id)` | id fiche | dict{mentions%, bac_types%, accès} | Champ profil_admis exposé (Axe 1 D1) |
| `web_search(query)` | requête texte | list[résultat web] | Brave Search API ou Mistral web search |
| `compare_formations(id1, id2)` | 2 ids | dict{critères côte-à-côte} | Compose autres tools |

#### Choix de l'orchestrateur

| Option | Avantages | Inconvénients | Recommandation |
|---|---|---|---|
| **Mistral Large function calling** | Souveraineté française, narrative INRIA fort, intégré à la stack | Tool-use moins mature que Claude/OpenAI, doc moins claire | Phase 2 si Phase 1 stable |
| **Claude Sonnet 4.5 tool-use** | Très mature, doc excellente, débuggable | Perd argument souveraineté | **Phase 1 (prototypage rapide)** |
| **OpenAI GPT-4o function calling** | Mature mais déjà testé comme baseline (15.16 vs 16.16, marginal) | Souveraineté zéro | Skip |
| **From-scratch (boucle while + dispatch)** | Contrôle total | Réinvente la roue, plus de bugs | Skip |

**Recommandation** : démarrer Claude Sonnet 4.5 en orchestrateur pour stabilité (1 semaine), puis basculer Mistral Large si tool-use stable et gain souveraineté significatif. Le générateur de réponse finale reste **Mistral** (cohérence souveraineté).

#### Plan d'action détaillé

| # | Action | Effort | Détail |
|---|---|---|---|
| **A1** | Définir interfaces tools (typed contracts) | 4-6h | Pydantic models pour input/output, schémas JSON pour LLM |
| **A2** | Implémenter ProfileClarifier agent | 6-8h | Système prompt dédié, état session-based |
| **A3** | Implémenter Decomposer agent | 6-8h | Étendre intent classifier rule-based existant + LLM fallback |
| **A4** | Implémenter 3 tools core (search_formations, get_debouches, get_calendar) | 8-12h | Wrap RAG existant + APIs Axe 1 |
| **A5** | Implémenter Composer agent | 6-8h | Système prompt v4 (issu de v3.2 mais adapté tool-use) |
| **A6** | Implémenter Validator agent (citation precision) | 4-6h | Vérifie programmatiquement que IDs cités existent |
| **A7** | Orchestration Claude Sonnet (Phase 1) | 6-8h | Tool-use loop, retry, error handling |
| **A8** | Tests d'intégration end-to-end | 6-8h | Pytest sur 10-15 questions représentatives |
| **A9** | Bench `our_rag_v3_agentic` vs baselines | 2h orchestration + run | Coût ~$20-30 (multi-call par question) |
| **A10** | (Optionnel Phase 2) Bascule Mistral Large | 6-8h | Si Phase 1 stable et économique |

**Total Axe 2** : 50-72h Claudette + Matteo arbitrage. Coût ~$30-50.

#### Exemple concret de gain

**Avant (single-shot)**, question complexe : *"Je suis en bac techno STI2D mention bien, j'aime l'informatique mais j'ai peur que ce soit trop dur. Qu'est-ce qui est réaliste pour moi en 5 ans ? Je suis en région Centre."* :

- 1 retrieve top-10 sur "informatique bac techno"
- 1 generate Mistral avec contexte
- Réponse : Plan A/B/C génériques, mention de la sélectivité, suggestion BUT informatique sans données spécifiques au profil

**Après agentic**, même question :

1. ProfileClarifier extrait : `bac=techno_STI2D, mention=bien, geo=Centre, durée=5ans, anxiété=true, intérêt=informatique`
2. Decomposer split en 4 sous-questions :
   - "Formations 5 ans en informatique accessibles bac techno mention bien région Centre"
   - "Débouchés métiers stables et accessibles depuis ces formations"
   - "Calendrier admission Parcoursup 2026-2027 pour ces formations"
   - "Passerelles si la première année se passe mal"
3. Tools en parallèle :
   - `search_formations(filters={domain:'informatique', niveau:'bac+5', region:'Centre', accepts_techno:true})` → 8 fiches matchées
   - `get_profil_admis_stats(...)` pour chaque → mentions % et bac_types %
   - `get_debouches(rome_code='M1810')` → métiers développeur/admin/cyber, tension marché Centre
   - `get_insertion_stats(...)` pour chaque → 85-92% insertion 6m
   - `get_admission_calendar(...)` → vœux Parcoursup janvier-mars 2026, oraux mai
   - `get_passerelles(...)` → BTS SIO en alternance si décrochage L1
4. Composer compose une réponse personnalisée :
   ```
   Pour ton profil (STI2D mention bien, région Centre, 5 ans visés) :

   Plan A — Réaliste : Master MIAGE Tours
   - 32% des admis sont issus de bac techno (l'un des meilleurs ratios)
   - 41% ont mention bien comme toi
   - 89% d'insertion à 6 mois (DEPP 2024)
   - Calendrier : voeux jusqu'au 14 mars 2026
   - Source : ONISEP FOR.18472, InserSup 2024

   Plan B — Ambitieux : Polytech Tours filière info
   - Concours commun Geipi-Polytech (places techno : 12% de l'effectif)
   - Notes à viser : 14+ en spé maths terminale
   - Calendrier : inscription concours novembre 2025
   - Source : Parcoursup formation #FR_RNE0410834W

   Plan C — Sécurité : BUT Informatique IUT Bourges en alternance
   - Accessible à bac techno (45% des admis)
   - Salaire alternance ~800€/mois
   - Permet de financer ton autonomie + sortir de la peur du décrochage
   - Source : ONISEP FOR.13821

   📅 Tes prochaines étapes :
   - 14 nov 2025 : inscription Geipi-Polytech (Plan B)
   - 15 jan - 14 mars 2026 : voeux Parcoursup (Plans A et C)
   - Mars-mai 2026 : oraux éventuels

   💡 Question pour toi : ce qui t'angoisse le plus, c'est le risque
   d'échec ou la difficulté de la matière elle-même ? La réponse change
   le bon plan : si c'est l'échec, Plan C (alternance + BUT) sécurise ;
   si c'est la matière, Plan A (MIAGE plus appliqué) convient mieux.

   🔀 Passerelles si Plan A se passe mal : LP Métiers de l'informatique
   à Tours en année +1, accessible avec dossier L1.
   ```

C'est cette différence de qualité qu'aucun ChatGPT généraliste ne peut produire — il n'a ni les données précises (taux Parcoursup 2025, bac type %), ni la mécanique d'agent multi-step, ni le profil utilisateur.

#### Métriques de succès
- Bench `our_rag_v3_agentic` vs `mistral_v3_2_no_rag` (avec corpus Axe 1) : **+1.5 minimum** sur Claude rubric nue
- Bench `our_rag_v3_agentic` vs `chatgpt_natural` : **+2 minimum** sur questions complexes (passerelles, comparaison, multi-critères)
- Métrique B3 actionabilité : `our_rag_v3` doit scorer **5/5** sur les composantes (Plan A/B/C, calendrier, sources cliquables, tableau, question retour)
- Test sur 10 questions très complexes (multi-axe) : amélioration qualitative validée par Matteo

#### Risques et mitigations

| Risque | Probabilité | Mitigation |
|---|---|---|
| Tool-use Mistral instable (si on bascule) | Moyenne | Phase 1 sur Claude, Phase 2 sur Mistral seulement si gain |
| Latence multi-call trop élevée (>10s par question) | Moyenne | Cache LRU sur tools déterministes, parallélisation max |
| Coût explosé (multi-call × 100q) | Moyenne | Cap budget run = $50, observabilité par tool |
| Hallucination malgré tools | Faible | Validator agent vérifie citations, re-prompt si problème |
| Refactor casse les 231 tests existants | Moyenne | Garder pipeline single-shot en parallèle (système `our_rag_v2_data` reste accessible) |

#### Fichiers à créer
- `src/rag/agents/profile_clarifier.py`
- `src/rag/agents/decomposer.py`
- `src/rag/agents/composer.py`
- `src/rag/agents/validator.py`
- `src/rag/agents/orchestrator.py`
- `src/rag/tools/__init__.py`
- `src/rag/tools/search_formations.py`
- `src/rag/tools/get_debouches.py`
- `src/rag/tools/get_insertion_stats.py`
- `src/rag/tools/get_admission_calendar.py`
- `src/rag/tools/get_passerelles.py`
- `src/rag/tools/get_profil_admis_stats.py`
- `src/rag/tools/web_search.py`
- `src/rag/tools/compare_formations.py`
- `src/prompt/agent_prompts.py` — system prompts par agent
- `tests/test_agents/`, `tests/test_tools/`

#### Fichiers à modifier
- `src/eval/systems.py` — ajouter `our_rag_v3_agentic`
- `src/api/` — endpoint pour orchestrateur agent (en plus du single-shot existant)

---

### Axe 3 — Fine-tuning RAFT (spécialisation souveraine)

#### Objectif
Fine-tuner Mistral-7B avec la recette RAFT (Zhang et al. 2024, arXiv 2403.10131) pour qu'il apprenne à exploiter le contexte RAG, citer correctement, et refuser quand l'info n'est pas dans le contexte. Argument souveraineté française fort pour le jury.

#### Pourquoi RAFT et pas FT pur

| Approche | Problème |
|---|---|
| Fine-tuning supervisé classique | Apprend le style mais pas les facts. Sans RAG runtime, hallucinations numériques (taux Parcoursup, places, URLs). |
| Fine-tuning par instructions | Améliore tone et structure mais ignore comment exploiter le contexte. |
| **RAFT** | Apprend à utiliser le contexte RAG, citer explicitement, et refuser si oracle absent. Conserve le RAG runtime. |

#### Mécanisme RAFT (recap)

Chaque exemple d'entraînement :
- Question Q
- Document oracle D* (la fiche pertinente pour répondre)
- k=4 distracteurs plausibles (autres fiches du corpus, sémantiquement proches)
- Réponse avec citations explicites au format :
  ```
  ##begin_quote## Master MIAGE Tours, 32% bac techno admis (Source: ONISEP FOR.18472) ##end_quote##

  ##Answer: Pour ton profil bac techno mention bien...
  ```
- P=80% des exemples avec oracle inclus, 20% sans (apprend le refus poli si oracle absent)

#### Préalable critique : générer 500-1000 paires d'entraînement

C'est le **vrai bottleneck** d'Axe 3. 3 options à combiner :

| Option | Volume | Coût | Qualité | Effort Matteo |
|---|---|---|---|---|
| **α — Génération Claude Opus + review Matteo** | 500-700 paires | ~$30 Opus | Haute | 1h/jour × 7j = 7h |
| **β — Génération synthétique pure Mistral Large + filtre auto** | 500-1000 paires | ~$15 | Moyenne (risque "modèle imite générateur") | 0h |
| **γ — Récup questions étudiants réels (Reddit/forums Parcoursup) + curation Matteo** | 200-300 paires | $0 | Authentique (la VRAIE distribution) | 5-8h sur 1 semaine |

**Recommandation** : Option α (700 synthetic-curated) **+** γ (200 réelles curées) en parallèle. Total ~5j calendaire dont ~14h attention Matteo répartis. C'est le coût du sérieux RAFT.

#### Training (Unsloth QLoRA)

```python
# Stack technique validée (extrait AMELIORATIONS §5.3)
from unsloth import FastLanguageModel

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="mistralai/Mistral-7B-Instruct-v0.3",
    max_seq_length=2048,
    load_in_4bit=True,                # QLoRA NF4
    bnb_4bit_use_double_quant=True,
)
# LoRA: r=32, alpha=64, dropout=0.05, target=qkvo+gate+up+down
# Training: batch=2, grad_accum=4, gradient_checkpointing=True
# LR=5e-5, warmup=50, 3 epochs, early-stop sur 100 ex held-out
# Mix 10% OASST FR pour éviter catastrophic forgetting français
# VRAM peak ~12 GB
```

#### Stack GPU (sans achat matériel)

| Plateforme | GPU | Coût | Faisabilité |
|---|---|---|---|
| Kaggle Notebooks | P100 / T4×2 16GB | Gratuit (30h/sem) | ✅ Excellent — démarrage |
| Google Colab Pro | T4 16GB | $11.99/mois | ✅ Stable pour ablations principales |
| RunPod Spot RTX 4090 | 24GB | $0.34/h (~$8.50 pour 25h) | ✅ Overflow / runs urgents |
| **Combo recommandé** | Kaggle + Colab Pro + RunPod | **~$22 total** | Fiabilité ~95% |

#### Plan d'action détaillé

| # | Action | Effort | Détail |
|---|---|---|---|
| **R1** | Génération dataset α (Opus + review) | 7j calendaire (~$30 Opus, 7h Matteo) | Script `src/finetune/raft_dataset_gen.py` qui appelle Opus avec template, output JSONL |
| **R2** | Génération dataset γ (forums réels) | 5-8j calendaire (5-8h Matteo) | Script `src/finetune/scrape_real_questions.py` (Reddit r/Parcoursup, forum onisep, etc.) + curation manuelle |
| **R3** | Validation dataset + decontamination test set | 4-6h | Vérifier zero overlap avec test set 68q. Hash check + manual review |
| **R4** | Setup Unsloth + Kaggle/Colab | 4-6h | Notebook reproducible, config versionnée |
| **R5** | Training baseline LoRA r=32 | 2-3h compute | Premier modèle, sanity check |
| **R6** | Ablations LoRA r∈{16, 32, 64} × epochs∈{2, 3, 5} | 6-9 runs × 2-3h | Grid search compact |
| **R7** | Évaluation FT vs base sur dev set (32q, free) | 1h | Si dev set hold-out compromise → STOP |
| **R8** | Intégration `our_rag_v4_raft` (FT model + RAG runtime) | 4-6h | Wrap modèle FT + même tools Axe 2 |
| **R9** | Bench complet `our_rag_v4_raft` vs `our_rag_v3_agentic` vs baselines | $20-30 | Validation gain |
| **R10** | (Si gain) Documentation complète + ADR | 4-6h | Pour reproduction jury |

**Total Axe 3** : 10-14j calendaire (dont 5-8j génération dataset), ~$50-60 (Opus + GPU + bench).

#### Métriques de succès
- Honesty score Haiku : `our_rag_v4_raft` passe de 0.575 → **0.75 minimum**
- Rubric Claude : `our_rag_v4_raft` > `our_rag_v3_agentic` de **+0.5 minimum**
- Citation precision (B3 sub-metric) : 90%+ des citations vérifiées valides

#### Risques et mitigations

| Risque | Probabilité | Mitigation |
|---|---|---|
| Modèle FT pire que base | 30-40% | Ablations multiples (r∈{16,32,64}, epochs∈{2,3,5}), abandon si tous pires |
| Catastrophic forgetting français | Moyenne | Mix 10% OASST FR pendant training |
| Decontamination test set ratée | Faible mais critique | Hash check automatique + manual review (R3) |
| Overfit sur petit dataset (<1000 paires) | Moyenne | Early stop sur 100 ex held-out + dropout 0.05 |
| Coût Opus pour génération dataset explose | Faible | Cap budget = $50, batch génération |
| GPU cloud instable (Kaggle timeout, RunPod interruption) | Haute | Checkpoints toutes les 30 min, multi-plateforme fallback |

#### Décision gate après R7
- Si modèle FT > base sur dev set + honesty score amélioré → continuer R8-R10
- Sinon → archiver dataset + notes + abandonner Axe 3 pour cette itération
- Future work : retenter avec 2x dataset + DPO post-RAFT

#### Fichiers à créer
- `src/finetune/raft_dataset_gen.py` (génération assistée Opus)
- `src/finetune/scrape_real_questions.py` (forums + Reddit)
- `src/finetune/dataset_validate.py` (decontamination + checks)
- `src/finetune/train_unsloth.py` (training script Kaggle/Colab)
- `src/finetune/eval_ft_model.py` (bench dev set)
- `notebooks/raft_training.ipynb` (Kaggle notebook)
- `data/finetune/raft_train.jsonl`, `raft_eval.jsonl`
- `models/lora_r32_e3/` (checkpoints LoRA, gitignored, hosted HuggingFace)

---

### Axe 4 — Différenciateurs UX (LE WOW FACTOR JURY)

#### Objectif
Produire des fonctionnalités que ChatGPT/Claude/Mistral chat ne peuvent **structurellement pas** faire, parce qu'elles requièrent un produit dédié au métier d'orientation.

#### Mécanisme
Identifier les actions concrètes qu'un lycéen·étudiant veut faire **après** avoir reçu une réponse texte, et les outiller dans l'UI directement.

#### Catalogue de différenciateurs

| # | Feature | Effort | Pourquoi ChatGPT ne peut pas |
|---|---|---|---|
| **U1** | Calendrier Parcoursup interactif (j-X avant chaque deadline 2026-2027) | 4-6h | Données live + UI dédiée |
| **U2** | Calculator score Parcoursup (notes lycée → estimation chances par formation) | 6-8h | Algorithme custom + corpus profil_admis |
| **U3** | Comparateur côte-à-côte drag-drop (2 formations) | 4-6h | UI custom |
| **U4** | Carte géographique France interactive (densité formations par région) | 6-8h | Visualisation + corpus enrichi |
| **U5** | Liens cliquables vérifiés vers fiches officielles ONISEP/écoles | 2-4h | Citation precision déterministe |
| **U6** | Mode "exploration" vs "décision urgente" (UX différente) | 4-6h | Distinction métier |
| **U7** | Export PDF du conseil donné (pour parents/CIO) | 4-6h | Génération document |
| **U8** | Profil étudiant persistant (LocalStorage ou compte) | 6-8h | État utilisateur |
| **U9** | Chat conversationnel avec contexte (vs single-question) | 6-8h | Mémoire session |
| **U10** | "Mes formations sauvegardées" + alerte deadline | 4-6h | Persistance + notifications |

#### Stack technique
- Frontend : Astro 5 + React + Tailwind (stack déjà connue côté Site ReadKode, donc Claudette est productive)
- Backend : FastAPI déjà en place (`src/api/`), à enrichir
- Storage utilisateur : LocalStorage v1, compte (Auth0 ou Supabase) v2 si nécessaire
- Déploiement : Vercel (frontend) + Railway (backend, déjà configuré)

#### Plan d'action détaillé (priorités selon ROI démo)

**Sprint UX-1 (priorités hautes, démo-ables)**
- U1 calendrier Parcoursup
- U3 comparateur côte-à-côte
- U5 liens cliquables vérifiés
- U7 export PDF

**Sprint UX-2 (engagement utilisateur)**
- U8 profil persistant
- U9 chat conversationnel
- U2 calculator score

**Sprint UX-3 (nice-to-have)**
- U4 carte géographique
- U6 modes UX différents
- U10 alertes deadline

**Total Axe 4** : 36-52h front-end (dépend du périmètre choisi). Coût $0.

#### Métriques de succès
- Démo live au jury INRIA fluide sans bug
- Captures d'écran intégrées dans STUDY_REPORT
- Test 5 utilisateurs qui font une recherche complète : durée < 10 min, satisfaction > 4/5
- "Wow factor" jury : à l'œil des évaluateurs, qualitatif mais critique

#### Fichiers à créer
- `frontend/` (nouveau dossier Astro)
- `frontend/src/components/Calendar.astro` (U1)
- `frontend/src/components/Comparator.tsx` (U3)
- `frontend/src/components/ScoreCalculator.tsx` (U2)
- `frontend/src/components/Map.tsx` (U4 — Leaflet ou MapLibre)
- `src/api/routes/calendar.py`, `compare.py`, `calculate.py` (backend)
- `src/api/routes/pdf_export.py` (U7 — ReportLab ou WeasyPrint)
- `src/api/routes/profile.py` (U8)

---

## 6. Refonte du benchmark V2

Le benchmark actuel est rigoureux mais évalue **uniquement la production de texte**. Le système V2 doit être évalué sur ses différenciateurs réels.

### Évolutions

| # | Action | Pourquoi | Effort | Coût |
|---|---|---|---|---|
| **B1** | Étendre questions (+30q, scope élargi) | Couverture Parcoursup 2026, ROME précis, passerelles intra-univ | 4-6h | $0 |
| **B2** | Baselines naturels Playwright (chatgpt_natural, claude_natural, mistral_natural) | Représente vraiment ce que l'utilisateur obtient des chatbots, pas pénalisé par notre prompt | 6-8h + run | $20-30 |
| **B3** | Métrique "actionabilité" déterministe | Compte automatique : Plan A/B/C ? calendrier ? sources cliquables ? tableau ? question retour ? | 4-6h | $0 |
| **B4** | Test utilisateur étendu (5-10 étudiants × 20q blind) | Validation humaine + κ inter-étudiants + ranking | 4h prep + 1 sem calendaire | $0 (volunteers) |
| **B5** | Métrique "fraîcheur" déterministe | Sous-ensemble 20q ciblant données 2025-2026, cible où ChatGPT cutoff perd | 4-6h | $0 |
| **B6** | Métrique "citation precision" déterministe | Pour chaque claim avec source citée : vérifier que ID existe dans corpus / URL répond 200 | 4-6h | $0 |

### Total refonte benchmark
12-18j travail Claudette (parallélisable), ~$30-40 budget tools Playwright + appels supplémentaires.

### Cible chiffrée pour V2 final

| Métrique | Cible `our_rag_v4_full` |
|---|---|
| Rubric Claude (rubric nue) | > `chatgpt_natural` de **+2 minimum** |
| Rubric Claude (factcheck) | > `chatgpt_natural` de **+3 minimum** |
| Honesty score Haiku | > 0.80 (vs 0.575 actuel) |
| Métrique B3 actionabilité | 5/5 sur 90% des questions |
| Métrique B5 fraîcheur | 80% des questions données 2025-2026 répondues correctement (vs 0-20% pour ChatGPT/Claude/Mistral) |
| Métrique B6 citation precision | 95% des sources citées vérifiables |
| Test utilisateur B4 | Préférence > 70% pour OrientIA vs ChatGPT |

---

## 7. Hiérarchisation et ordre d'attaque

### Tableau récapitulatif

| Axe | Effort | Coût $ | Risque | Gain attendu | Prio | Préséance |
|---|---|---|---|---|---|---|
| **Axe 1** Data foundation | 38-52h | $5-10 | Faible | +1.5 à +3 sur rubric | **P0** | Bloque les autres |
| **Axe 2** Agentic multi-step | 50-72h | $30-50 | Moyen | +1 à +2 + différenciation | **P0** | Dépend Axe 1 |
| **B1-B2** Bench étendu + baselines naturels | 10-14h | $20-30 | Faible | mesure honnête | **P0 transversal** | À faire en // |
| **B3-B4-B5-B6** Métriques V2 | 12-18h | $0 | Faible | démontre les diffs | **P1** | Après que Axes 1+2 ont bougé |
| **Axe 3** RAFT FT | 10-14j | ~$50 | Moyen-haut | +1 à +2 + souveraineté | **P1** | Lance dataset gen en // |
| **Axe 4** UX différenciateurs | 36-52h | $0 | Faible | wow factor jury | **P1** | À faire en // de Axes 2-3 |

### Sprints recommandés (semaines de 5j ouvrés)

**Sprint 1 (S1-S2) — Data foundation + benchmark étendu**
- Track Claudette : D1 → D2 → D4 → D5 → D6 (skip D3 si timing serré)
- Track Claudette // : B1 + B2 (Playwright baselines)
- Checkpoint : rerun `our_rag_v2_data` vs baselines naturels. Cible Δ Claude > +1.0.

**Sprint 2 (S3-S4) — Architecture agentic**
- Track Claudette : Axe 2 (A1-A9)
- Track Claudette // : B3 + B6 (métriques actionabilité + citation precision)
- Checkpoint : rerun `our_rag_v3_agentic` > `chatgpt_natural` de +1.5.

**Sprint 3 (S5-S6) — RAFT en parallèle de UX**
- Track A (Claudette + Matteo) : Axe 3 (R1-R10), génération dataset α en background pendant que R2 γ tourne
- Track B (Claudette) : Axe 4 (UX-1 priorités hautes : U1, U3, U5, U7)
- Track Claudette // : B5 (métrique fraîcheur)
- Checkpoint : RAFT survit aux ablations + UX features démo-ables.

**Sprint 4 (S7) — Test utilisateur + bench final**
- B4 (5-10 étudiants × 20q)
- Bench final : `our_rag_v4_full` vs naturels vs `our_rag_v3_agentic` vs `our_rag_v2_data`
- UX-2 features (U8, U9, U2) en // si temps

**Sprint 5 (S8) — Polish + reproducibility + STUDY_REPORT positif**
- Reproducibility package complet
- STUDY_REPORT.md narrative positive
- Demo UI live polish
- UX-3 si temps

**Total** : 8 semaines de sprint efficace.

---

## 8. Stratégie v1 minimale si deadline serrée

Si pour une raison X la deadline INRIA est verrouillée à ~17j (début mai 2026), voici la stratégie minimale.

### Semaine 1 (J+1 à J+7) — Data foundation condensée
- D1 + D2 + D4 + D6 (skip D3 ROME, D5 InserJeunes, D7 cron)
- B2 baseline naturels Playwright (essentiel pour montrer qu'on bat les vraies cibles)

### Semaine 2 (J+8 à J+14) — Agentic minimal
- 3 tools seulement : `search_formations` + `get_debouches` + `get_admission_calendar`
- Composer simple (pas de Validator)
- Bench rerun

### Semaine 3 (J+15 à J+17) — Polish + report + démo
- Reproducibility package
- STUDY_REPORT v1 (narrative "data + agentic battent les IAs natives sur l'orientation")
- Demo UI 2-3 features clés (U1 calendrier + U3 comparateur)

### Skip pour v1
- Axe 3 RAFT entier
- Axe 4 UX étendu (garde juste 2-3 features)
- Test utilisateur B4

### Plan v2 post-soumission
Le projet continue après. RAFT, UX étendue, test utilisateur, refresh mensuel = roadmap publique post-INRIA.

---

## 9. Réponse à la critique tuteur INRIA

Avec le repivot, la critique du tuteur prend tout son sens. AMELIORATIONS l'avait écartée un peu rapidement ; on l'embrace dans la stratégie.

### Critique 1 — "Fine-tunez les modèles"

**Position OrientIA V2** : tu as raison sur le besoin d'aller au-delà du RAG vanilla. La forme la plus défendable est **RAFT** (Berkeley 2024) plutôt que FT pur :
- Conserve le RAG runtime (les chiffres Parcoursup changent, on ne peut pas les "graver" dans les poids)
- Apprend explicitement à exploiter le contexte + citer + refuser
- Préserve la souveraineté française (Mistral-7B open weights)

→ C'est l'**Axe 3** de cette roadmap. Lancé en Sprint 3.

### Critique 2 — "Similarité euclidienne au lieu de LLM-as-judge"

**Position OrientIA V2** : la métrique précise (cosine sim sur embeddings) est sub-optimale (BLEU/ROUGE plafonnent à κ~0.3 avec humain), MAIS l'intuition sous-jacente — *les juges LLM sont des boîtes noires sujettes à l'auto-préférence* — est juste.

On ne remplace pas LLM-as-judge, on **ajoute des couches non-LLM** complémentaires :
- **Métrique B3 actionabilité** : compte programmatique des composantes structurelles (Plan A/B/C, calendrier, etc.)
- **Métrique B5 fraîcheur** : test déterministe sur questions 2025-2026
- **Métrique B6 citation precision** : vérifie programmatiquement que IDs/URLs cités existent
- **Test utilisateur B4** : 5-10 étudiants réels, pas un seul LLM

→ Ces 4 couches non-LLM répondent à la critique sans renoncer à la rigueur LLM-as-judge.

### Synthèse pour le tuteur

> *"Les deux critiques étaient justes et nous les implémentons dans la V2 :*
> *- Le fine-tuning : on adopte RAFT (Mistral-7B Unsloth, ~$22 GPU) avec dataset 700-900 paires curées, qui conserve le RAG en runtime et apprend l'exploitation du contexte + citations + refus*
> *- L'évaluation non-LLM : on ajoute 4 couches déterministes (actionabilité, fraîcheur, citation precision, test étudiants) en complément du triple-layer existant*
> *Le résultat est un système d'orientation qui bat structurellement ChatGPT/Claude/Mistral chat sur les axes où c'est mesurable (fraîcheur des données 2025-2026, actionabilité, citation precision, préférence utilisateur réelle)."*

---

## 10. Principes directeurs

À graver pour ne pas redériver vers les anti-patterns du passé.

### Principe 1 — Le système gagne, pas le paper
Toute décision se mesure à : *"Est-ce que ça rend le produit objectivement meilleur pour un lycéen qui s'oriente ?"* Si non, on ne le fait pas.

### Principe 2 — Le RAG est un moyen, pas une thèse
Si une feature donne plus de valeur sans RAG (ex: calculator score Parcoursup déterministe), on l'implémente sans RAG. Pas d'attachement religieux à l'architecture initiale.

### Principe 3 — Le benchmark est un garde-fou, pas un objectif
Le benchmark mesure les progrès. Si une amélioration ne se voit pas dans les chiffres, c'est qu'elle ne marche pas (ou que le benchmark est inadéquat — auquel cas on l'étend, voir B1-B6).

### Principe 4 — La rigueur méthodologique reste obligatoire
Repivot ≠ relâchement. ADR continue, dev/test split continue, blinding continue, multi-judge continue. C'est ce qui distingue OrientIA d'un démonstrateur tape-à-l'œil.

### Principe 5 — La souveraineté française a une valeur
Le narratif INRIA apprécie Mistral + opens data français + RAFT spécialisé. Ne pas y renoncer pour des gains marginaux. Mais ne pas s'y enfermer si Claude/OpenAI sont strictement nécessaires (ex: orchestration agent en Sprint 2 sur Claude pour stabilité).

### Principe 6 — Données fraîches > données figées
La fenêtre temporelle est notre avantage structurel sur les LLMs natifs. Cron de refresh mensuel (D7) n'est pas un nice-to-have, c'est un différenciateur central.

### Principe 7 — Les étudiants réels sont la vérité
Tests utilisateurs avec vrais étudiants (B4) > 100 questions LLM-judged. Si les chiffres benchmark disent "OrientIA gagne" mais 0 étudiant·e ne l'utiliserait, on a échoué.

### Principe 8 — Pas d'over-engineering
Si une feature simple (3-tools agentic, 2 baselines naturels) débloque 80% du gain, pas la peine d'aller à 7-tools agentic + 5 baselines avant d'avoir mesuré.

---

## 11. Décisions à trancher maintenant

Avant qu'on attaque concrètement, j'ai besoin que Matteo tranche sur ces points.

### Q1 — Deadline INRIA réelle
- (a) Verrouillée début mai (~J+17) → **stratégie v1 minimale §8**
- (b) Décalable de 6-8 semaines → **stratégie complète §7**
- (c) Hybride : v1 minimale soumission + v2 enrichie démo finale → **§7+§8 combinés**

### Q2 — Sprint en premier
- Recommandé : **Axe 1 data first** (gros ROI, débloque les autres)
- Alternative : tout démarrer en // (Claudette sur Axes 1+2, dataset RAFT en background, Matteo arbitre UX)

### Q3 — Orchestrateur agent (Axe 2)
- Phase 1 Claude Sonnet (recommandé pour stabilité)
- Direct Mistral Large (souveraineté immédiate, risque tool-use immature)
- Bascule prévue mi-Sprint 2 selon résultats

### Q4 — Génération dataset RAFT (Axe 3)
- Option α + γ (Opus + forums réels) — recommandé
- Option β pure synthétique (plus rapide, moins authentique)
- Combinaison personnalisée

### Q5 — Périmètre UX V1 (Axe 4)
- Sprint UX-1 only (4 features démo) — minimal
- Sprint UX-1 + UX-2 (engagement) — équilibré
- Tout (3 sprints) — maximaliste

### Q6 — Repo public ?
- Aujourd'hui PRIVATE (memory `feedback_orientia_framing.md`)
- Garder PRIVATE jusqu'à soumission INRIA confirmé ?
- Ou passer PUBLIC avant pour bonus narrative open-source jury ?

---

## 12. Annexes

### 12.1 Glossaire

- **Rubric** : grille d'évaluation 6 critères × 0-3 pts = /18 (criteres : sourcage, neutralité, réalisme, agentivité, structure, exhaustivité)
- **Fair baseline** : système identique aux concurrents sans avantage déloyal (NEUTRAL_MISTRAL_PROMPT pour notre cas)
- **Ablation** : comparaison de configurations qui isolent l'apport d'un composant (ex: RAG isolé vs prompt isolé)
- **Hold-out** : ensemble de questions jamais utilisé pour tuner le système, garde la valeur scientifique du test
- **Inter-judge κ (Cohen)** : mesure d'accord entre juges (0=hasard, 1=parfait, 0.4-0.6 substantial)
- **RAFT** : Retrieval-Augmented Fine-Tuning (Zhang et al. 2024)
- **MMR** : Maximal Marginal Relevance (Carbonell & Goldstein 1998)
- **LoRA / QLoRA** : Low-Rank Adaptation / Quantized — fine-tuning efficace en VRAM

### 12.2 Références

**Papers**
- RAFT : Zhang et al. 2024, arXiv 2403.10131
- MT-Bench / LLM-as-judge : Zheng et al. 2023, arXiv 2306.05685
- Self-preference bias : Panickssery et al. 2024
- FActScore (référence pour métriques non-LLM) : Min et al. 2023
- Fine-tuning vs RAG : Ovadia et al. 2024
- MMR : Carbonell & Goldstein 1998

**APIs data publiques (gratuites)**
- Parcoursup Open Data : `https://data.enseignementsup-recherche.gouv.fr/pages/parcoursupdata/`
- ONISEP API : `https://opendata.onisep.fr/3-api.htm`
- France Travail ROME 4.0 : `https://francetravail.io/data/api/rome-4-0-metiers`
- InserJeunes / InserSup : `https://www.data.gouv.fr/datasets/insertion-professionnelle-...`
- SecNumEdu ANSSI : `https://cyber.gouv.fr/.../formation-secnumedu/`
- CTI : `https://www.cti-commission.fr/les-ecoles/annuaire`
- CGE : `https://www.cge.asso.fr/`

**Outils FT**
- Unsloth : `https://unsloth.ai/blog/mistral-benchmark`
- Kaggle GPU : `https://www.kaggle.com/docs/efficient-gpu-usage`
- Colab pricing : `https://colab.research.google.com/signup`
- RunPod pricing : `https://www.runpod.io/gpu-pricing`

### 12.3 Structure de docs OrientIA après ce repivot

```
docs/
├── STRATEGIE_VISION_2026-04-16.md  ← CE DOCUMENT (référence)
├── SESSION_HANDOFF.md              ← état projet (mis à jour à chaque sprint)
├── DECISION_LOG.md                 ← ADR append-only (étendu avec ADR-021+)
├── METHODOLOGY.md                  ← protocole reproductible (mis à jour bench V2)
└── eval/
    └── ... (analyses Run F+G, futurs runs V2)
```

L'ancien AMELIORATIONS_2026-04-16.md a été supprimé : son contenu actionnable est intégré dans ce document.

### 12.4 Migration de la doc existante (à faire post-validation Matteo)

- INRIA_AI_ORIENTATION_PROJECT.md → à mettre à jour avec narrative V2 (Sprint 5)
- README.md → ajouter section "Vision V2" pointant vers ce doc
- SESSION_HANDOFF.md §6 (Active plan) → remplacer par référence à ce doc
- DECISION_LOG.md → ajouter ADR-021 "Repivot stratégique vers système qui gagne"

### 12.5 Ce que ce document **n'est pas**

- Un plan d'exécution code détaillé ligne-par-ligne (chaque axe sera décliné en plan technique au moment du sprint)
- Une garantie de résultat (les chiffres cibles sont des objectifs, pas des engagements ; les risques sont documentés)
- Un substitut au DECISION_LOG (les décisions futures continuent d'être tracées en ADR)

---

## Conclusion

OrientIA passe de "étude de méthodologie RAG re-ranking" à "système qui bat les IAs génératives sur l'orientation française". Les 4 causes structurelles du sous-performance actuel (corpus affamé, single-shot, anonyme, figé) sont attaquées par 4 axes techniques (data foundation, agentic, RAFT, UX), avec un benchmark V2 conçu pour exposer les différenciateurs réels.

L'effort total complet : ~8 semaines. La fallback v1 minimale : ~17 jours. Le tuteur INRIA avait raison sur les deux critiques (FT + non-LLM eval), elles sont embraced dans la stratégie.

**Le système gagne, le paper documente.** Pas l'inverse.

---

*Document de référence stratégique — créé le 2026-04-16 par Matteo (vision) et Jarvis (audit + structuration). Remplace l'ancien AMELIORATIONS_2026-04-16.md (supprimé).*
