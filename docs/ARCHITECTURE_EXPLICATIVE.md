# OrientIA — Architecture explicative

> Document d'onboarding pour quelqu'un qui découvre le projet. Couvre **les données utilisées**, **le format RAG**, **le pipeline complet**, et **ce qui se passe étape par étape quand un lycéen pose une question**.
>
> Daté du 2026-05-07 — pipeline v4.1. Source de vérité produit : ce document. Source de vérité décisions : `docs/DECISION_LOG.md`. Source de vérité opérationnelle : `docs/SESSION_HANDOFF.md`.

---

## 1. Vue d'ensemble en 1 minute

OrientIA est un **assistant d'orientation post-bac** pour lycéens et étudiants français. On lui pose une question en français — *"Je suis en terminale, j'hésite entre prépa et BUT info à Lyon"* — et il répond avec **3 pistes pondérées, des chiffres sourcés, et une question pour faire avancer la réflexion**.

C'est un système **RAG** (Retrieval-Augmented Generation) construit sur Mistral :

- **Mistral Embed** transforme la question en vecteur numérique (1024 dimensions)
- **FAISS** retrouve les ~30 fiches les plus proches dans une base de **48 914 formations**
- **Mistral Medium** génère la réponse en s'appuyant **uniquement** sur les chiffres extraits de ces fiches
- Plusieurs garde-fous (règles, validation corpus, post-process) empêchent les hallucinations

Soumission INRIA AI Grand Challenge en cours. Stack 100% souveraine (Mistral + données publiques françaises).

---

## 2. Les données — d'où viennent les chiffres

### 2.1 Le corpus principal `formations.json` — 48 914 fiches

C'est la base que voit le système quand il répond. Chaque fiche décrit **une formation post-bac** avec ses chiffres officiels. Distribution par source :

| Source | Nombre de fiches | Type |
|---|---|---|
| `inserjeunes_cfa` | 11 314 | Apprentissage / CFA — taux d'emploi 6/12/18/24 mois |
| `parcoursup` | 10 536 | Formations post-bac — taux d'accès, places, profil admis |
| `monmaster` | 8 953 | Masters universitaires (Bac+5) |
| `labonnealternance` | 6 646 | Offres d'alternance |
| `rncp` | 6 590 | Titres et certifications RNCP |
| `onisep` | 4 875 | Diplômes nationaux (BTS, BUT, Licence pro, etc.) |

Les données proviennent **toutes d'opens data publics français** (Parcoursup, ONISEP, France Travail, Cereq, INSEE, DARES, APEC, CROUS). Aucune source privée. Argument INRIA : **souveraineté française** + **données fraîches** (refresh prévu mensuel).

### 2.2 Format d'une fiche

Chaque fiche est un dict JSON. Les champs varient selon la source, mais structure typique :

```json
{
  "source": "parcoursup",
  "nom": "Bachelor Cybersécurité",
  "etablissement": "Lycée Emmanuel d'Alzon",
  "ville": "Nîmes",
  "region": "Occitanie",
  "departement": "30",
  "niveau": "bac+3",
  "statut": "Privé",
  "type_diplome": "formation d'école spécialisée",
  "labels": ["SecNumEdu"],
  "admission": {
    "taux_acces": 52.0,
    "places": 25,
    "volumes": {"voeux_totaux": 412}
  },
  "insertion_pro": {
    "source": "cereq",
    "taux_emploi_3ans": 0.86,
    "taux_emploi_6ans": 0.91,
    "taux_cdi": 0.83,
    "salaire_median_embauche": 1740,
    "cohorte": "2020"
  },
  "debouches": ["RSSI", "Administrateur sécurité", "Ingénieur sécurité"],
  "url_parcoursup": "https://dossierappel.parcoursup.fr/.../?g_ta_cod=39320...",
  "url_onisep": "https://www.onisep.fr/.../FOR.10945",
  "trends": {
    "taux_acces": {"direction": "down", "delta_pp": 8}
  }
}
```

**Deux familles de fiches** dans le corpus :

1. **Parcoursup riches** (~21,5%, 10 536 fiches) : ont les chiffres sélectivité (taux d'accès, places, profil admis). C'est le sous-corpus "or" pour les questions chiffrées.
2. **Multi-corpus / MonMaster / RNCP** (~78,5%) : ont l'identité de la formation et souvent l'insertion pro, mais pas les stats Parcoursup.

### 2.3 Les corpora annexes (multi-domaines)

À côté de `formations.json`, le système charge **8 corpora plus petits** ciblant chacun un domaine non-formation :

| Corpus | Fichier | Couvre |
|---|---|---|
| **DARES Métiers 2030** | `dares_corpus.json` | Projections recrutement par métier en 2030 |
| **APEC** | `apec_regions_corpus.json` | Marché travail cadres par région |
| **CROUS** | `crous_corpus.json` | Logements et restos U |
| **INSEE Salaires** | `insee_salaan_corpus.json` | Grilles salariales par PCS |
| **France Comp blocs** | (intégré formations) | Blocs de compétences certifiés RNCP |
| **Financement** | `financement_corpus.json` | Bourses, CPF, aides |
| **DROM** | `domtom_corpus.json` | Outre-mer (Guadeloupe, Réunion, etc.) |
| **Inserjeunes lycée pro** | (intégré formations) | Insertion bac pro / CAP |

Ces corpora sont **agrégés dans `formations.json`** via un champ `domain` (par exemple `domain: "metier_prospective"` pour DARES). Le **reranker** sait quoi booster selon le type de question (cf. §3.2).

### 2.4 Le corpus Golden QA — 45 paires question/réponse expertes

Fichier `data/processed/golden_qa_meta.json` (45 entrées). Ce sont **45 questions/réponses idéales** rédigées manuellement par des conseillers d'orientation experts. Servent de **few-shot** pour montrer au LLM le ton, la structure, l'empathie attendus.

**Important** : ces Q&A sont une **référence de style uniquement**. Le LLM ne doit **JAMAIS** reprendre les chiffres ou écoles citées dans l'exemple Golden — seules les fiches du corpus RAG factuel font autorité (cf. §3.5).

### 2.5 Index FAISS — où vit le RAG

- **`data/embeddings/formations.index`** (192 MB) — l'index FAISS principal sur les 48 914 fiches. Type : `IndexFlatL2` (recherche exacte par distance euclidienne, pas d'approximation).
- **`data/embeddings/golden_qa.index`** (181 KB) — l'index FAISS Golden QA, beaucoup plus petit.
- Tous les vecteurs sont en **1024 dimensions** (Mistral Embed).

### 2.6 Comment une fiche devient un vecteur (`fiche_to_text`)

Avant l'embedding, chaque fiche est sérialisée en **texte narratif** par `src/rag/embeddings.py:fiche_to_text()`. Exemple :

```
Bachelor Cybersécurité — Lycée Emmanuel d'Alzon, Nîmes (30) | bac+3 | Privé
Labels officiels: SecNumEdu
Sélectivité Parcoursup 2025: 52% (Sélective) | Places: 25 | Vœux formulés: 412
Insertion pro (source Céreq, cohorte 2020) : taux emploi 3 ans : 86% — taux emploi 6 ans : 91% — taux CDI : 83% — salaire médian embauche : 1740€
Débouchés: RSSI, Administrateur sécurité, Ingénieur sécurité
```

Ce texte est ensuite envoyé à Mistral Embed qui retourne un vecteur 1024d, stocké dans FAISS. **Important** : le format narratif est crucial — c'est lui qui rend les chiffres "retrievables". Une fiche dont l'`insertion_pro` n'est pas formaté en texte sera muette pour le retrieval.

---

## 3. Le pipeline — ce qui se passe quand un user pose une question

Quand un lycéen tape une question, elle traverse **10 étapes**. Chaque étape peut court-circuiter les suivantes (urgent → réponse en 0s, factual pointu → réponse déterministe sans LLM). Détaillons.

```
                    [Question utilisateur]
                              │
                              ▼
   ┌──────────────────────────────────────────────┐
   │ ÉTAPE 1 — ScopeClassifier (gate amont)       │
   │  → urgent / out_of_scope / in_scope          │
   └──────────────────────────────────────────────┘
        │           │              │
   URGENT      OUT_OF_SCOPE      IN_SCOPE
   (3114...)   (réoriente)         │
   ~0s         ~1s                 ▼
                    ┌──────────────────────────────────┐
                    │ ÉTAPE 2 — Intent classifier      │
                    │  → 8 classes (regex)             │
                    └──────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────────────────────┐
                    │ ÉTAPE 3 — SELECT bypass          │
                    │  Si factual_pointed + entité OK  │
                    │  → réponse déterministe (zéro LLM)│
                    └──────────────────────────────────┘
                              │ (sinon)
                              ▼
                    ┌──────────────────────────────────┐
                    │ ÉTAPE 4 — Retrieval FAISS        │
                    │  embedding + top-30 + rerank +MMR│
                    └──────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────────────────────┐
                    │ ÉTAPE 5 — Golden QA few-shot     │
                    │  retrieve top-1 sur 45 exemples  │
                    └──────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────────────────────┐
                    │ ÉTAPE 6 — Generation v4.1 strict │
                    │  Mistral Medium + FactCard JSON  │
                    │  R1-R6 max 250 mots              │
                    └──────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────────────────────┐
                    │ ÉTAPE 7 — Validator + retry      │
                    │  rules + corpus_check + presence │
                    │  retry-with-hint cap 1, t.o. 30s │
                    └──────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────────────────────┐
                    │ ÉTAPE 8 — UX Policy              │
                    │  Block / Warn / Modify           │
                    └──────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────────────────────┐
                    │ ÉTAPE 9 — Phase projet minimal   │
                    │  redirect CIO si HEC/PASS/kiné   │
                    └──────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────────────────────┐
                    │ ÉTAPE 10 — Post-process          │
                    │  URLs hallu + slugs + tableaux   │
                    └──────────────────────────────────┘
                              │
                              ▼
                       [Réponse finale]
                       (~7-12s, ~184 mots)
```

### Étape 1 — ScopeClassifier (amont, ~0,5-1s)

**Rôle** : décider AVANT toute coûteuse opération si la question est légitime. Trois catégories :

- **`urgent`** — détresse psychologique, idéations suicidaires, violences subies. Court-circuit immédiat avec **les vrais numéros d'écoute** : 3114 (suicide), 3919 (violences femmes), 119 (enfance), 30 18 (SOS Amitié).
- **`out_of_scope`** — recettes, météo, blagues, devoirs. Réorientation polie vers l'orientation post-bac.
- **`in_scope`** — toute question d'orientation. Continue dans le pipeline.

**Mécanique** (`src/rag/scope_classifier.py`) :

1. **Pré-filter regex** sur ~13 patterns explicites d'urgence (`suicide`, `me tuer`, `violences conjugales`...). Si match → URGENT en 0s sans appeler le LLM. **Sécurité** : on ne veut pas qu'un LLM rate un signal d'urgence.
2. **Sinon** → **Mistral Small** (`mistral-small-latest`, ~$0.0005/q, timeout 5s) avec un prompt de classification + 10 few-shots couvrant les formulations indirectes (*"j'en peux plus"*, *"à quoi bon"*, *"je suis nul·le"*).
3. **Mode dégradé** : si Mistral down/timeout → default `in_scope` (mieux laisser le pipeline gérer honnêtement qu'un faux refus).

### Étape 2 — Intent classifier (regex pure, <10ms)

**Rôle** : catégoriser la question pour adapter la stratégie de retrieval. **Aucun LLM**, 100% regex déterministes. 8 classes :

| Intent | Déclencheurs | top-k | mmr_lambda |
|---|---|---|---|
| `factual_pointed` | "quel est le taux d'accès de X", "combien de places à Y" | 5 | 0.9 |
| `comparaison` | "compare X et Y", "EPITA ou EPITECH" | 12 | 0.6 |
| `realisme` | "11 de moyenne", "est-ce que je peux intégrer" | 6 | 0.85 |
| `geographic` | mention d'une ville/région française | 12 | 0.4 |
| `passerelles` | "réorientation", "passerelles", "après ma L2" | 10 | 0.6 |
| `decouverte` | "quels métiers", "je m'intéresse à" | 12 | 0.3 |
| `conceptual` | "c'est quoi", "comment fonctionne" | 4 | 0.9 |
| `general` | fallback catch-all | 10 | 0.7 |

**Pourquoi mmr_lambda varie** : `decouverte` (λ=0,3) veut **diversité** (montrer plein de pistes différentes), `realisme` (λ=0,85) veut **pertinence pure** (aller chercher la bonne réponse, pas explorer).

**En parallèle** : `classify_domain_hint()` détecte si la question relève d'un corpus annexe (`metier`, `crous`, `apec_region`, `dares`, etc.) — utilisé en Étape 4 par le reranker.

### Étape 3 — SELECT bypass (factual pointu, déterministe, <100ms)

**Rôle** : sur les questions très précises ("Quel est le taux d'accès de l'EFREI à Paris ?"), on **n'utilise pas le LLM du tout**. On fait un lookup déterministe dans `formations.json`.

**Mécanique** (`src/lookup/structured_select.py`) :

1. Détecter le **field demandé** (`taux_acces`, `salaire`, `places`, `frais`...).
2. Extraire l'**entité** (formation + ville + niveau) avec regex + parsing.
3. **Fuzzy match** avec rapidfuzz (≥85 de similarité).
4. **Garde anti-stale** : si la donnée a >18 mois, refus.
5. **Garde INVALID_VALUES** : refus si valeur 0, null, N/A.
6. Si tout OK → **retourne la réponse formatée** sans appeler le LLM.

Argument démo INRIA : *"les chiffres viennent toujours d'un lookup, jamais d'une génération. Zéro hallu chiffres par construction."*

### Étape 4 — Retrieval (embedding + FAISS + rerank + MMR, ~0,3-0,5s)

**Rôle** : trouver les ~30 fiches les plus pertinentes, puis rerank/diversifier pour garder ~5-12 selon l'intent.

**Mécanique** (`src/rag/pipeline.py:_retrieve_and_filter`) :

1. **Embed la question** via Mistral Embed (1024d).
2. **FAISS IndexFlatL2** retourne les `k=30` fiches les plus proches (distance L2 minimale).
3. **Rerank** (`src/rag/reranker.py`) — multiplie le score par des boosts :
   - Labels officiels : SecNumEdu ×1,5, CTI ×1,3, Grade Master ×1,3
   - Public/privé : Public ×1,1
   - Niveau : Bac+5 ×1,15, Bac+3 ×1,05
   - Établissement nommé (vs ONISEP générique) : ×1,1
   - Parcoursup riche (a `cod_aff_form` + `profil_admis`) : ×1,2
   - **Domain-aware** (ADR-049) : si la question matche un `domain_hint`, les fiches du bon corpus sont boostées (APEC ×1,5, CROUS ×1,4, INSEE ×1,5...).
4. **MMR diversification** (Maximal Marginal Relevance) — sélectionne les top-k finaux en équilibrant pertinence et diversité (évite 12 fiches quasi-identiques). Le `mmr_lambda` vient de l'Étape 2.
5. **Filter métadonnées** (optionnel) — si l'appelant fournit des `criteria` (région, niveau, alternance...), filtrer + auto-expansion `k` si trop restrictif.

À la sortie : `top_k_sources` fiches reranked et diversifiées.

### Étape 5 — Golden QA few-shot (~0,3s)

**Rôle** : retrouver une question/réponse d'expert similaire à la question utilisateur, et l'injecter comme **exemple de style** dans le prompt LLM.

**Mécanique** (`src/rag/pipeline.py:_retrieve_golden_qa`) :

1. **Embed la question** (Mistral Embed).
2. **FAISS Golden QA index** → top-1 sur les 45 paires expertes.
3. Le prompt système ajoute un préfixe :
   ```
   === EXEMPLE EXPERT (RÉFÉRENCE TON/STRUCTURE/EMPATHIE UNIQUEMENT) ===
   Question : « ... »
   Réponse de référence : ...

   ⚠️ IMPORTANT — SÉPARATION STRICTE COMMENT vs QUOI :
   - IGNORE les écoles, chiffres, dates cités dans cet exemple.
   - SEULES les fiches du contexte RAG ci-dessous sont sources autorisées.
   ```

**Pourquoi cette séparation est critique** : si on laissait le LLM reprendre les chiffres de l'exemple Golden, il citerait des données d'un autre cas qui n'ont rien à voir avec la question utilisateur. Le préfixe **bloque cette confusion par construction**.

### Étape 6 — Generation v4.1 strict (Mistral Medium, ~5-15s)

C'est le cœur. **Approche v4.1 STRICT** : on ne donne plus la prose libre des fiches au LLM — on lui donne un **tableau JSON typé** avec champs explicites.

**Mécanique** (`src/rag/generator.py` + `src/prompt/system_v4_strict.py`) :

1. **`format_sources_for_llm(top_5_sources)`** — extrait chaque fiche en `FactCard` :
   ```json
   [
     {
       "id": "S1",
       "formation": "Bachelor Cybersécurité",
       "etablissement": "Lycée Emmanuel d'Alzon",
       "ville": "Nîmes",
       "niveau": "bac+3",
       "statut": "Privé",
       "chiffres": {
         "taux_acces_parcoursup_2025": 52.0,
         "nombre_places": 25,
         "duree": "3 ans",
         "taux_emploi_3ans": 0.86,
         "taux_cdi": 0.83,
         "salaire_median_embauche": 1740,
         "frais_annuels": null
       },
       "selectivite_code": "formation sélective",
       "debouches": ["RSSI", "Administrateur sécurité"],
       "url": "https://dossierappel.parcoursup.fr/..."
     },
     ...
   ]
   ```
   **Crucial** : les `null` sont explicites. Le LLM voit "frais_annuels: null" → il sait qu'il n'a pas l'info → il écrit *"information non disponible"*.

2. **System prompt SYSTEM_PROMPT_V4_STRICT** avec 6 règles non-négociables (R1-R6) :

   - **R1 — Chiffres** : tu peux citer **UNIQUEMENT** les valeurs du bloc `chiffres`. Si null → *"information non disponible"*. Pas d'estimation.
   - **R2 — Identité** : tu cites **UNIQUEMENT** les formations dont l'identité (formation+etablissement+ville) figure dans `<sources>`.
   - **R3 — Citations** : chaque chiffre doit être suivi de `[source SX]` (ex : `52% [source S1]`).
   - **R4 — Style** : libre depuis Golden QA, MAIS jamais de chiffres ou écoles tirés de l'exemple Golden.
   - **R5 — Posture** : empathique sans excès, direct sur le réalisme, pas de discrimination, termine par une question ouverte.
   - **R6 — Longueur** : **strictement max 250 mots**. Structure : intro courte + 2-3 puces + question finale. Pas d'intro "voici 3 pistes", pas de fermeture "n'hésite pas".

3. **Appel LLM** : `client.chat.complete(model="mistral-medium-latest", temperature=0.3, max_tokens=400)`.

**Mesure réelle (mini-bench v4.1 sur 23 questions)** : latence moyenne 7,26s, longueur moyenne 184 mots, 0 réponse flagged, score honnêteté 1,0.

### Étape 7 — Validator + retry-with-hint (~0,5s sans retry, +5-15s avec)

**Rôle** : vérifier la réponse, et si elle a des claims problématiques, **demander au LLM de réessayer avec un hint correctif**.

**Trois couches de validation** (`src/validator/`) :

1. **`rules.py`** — anti-discrimination, no-chiffres-conv, anti-stéréotypes (sexisme = ligne rouge, cf `feedback_sexisme_ligne_rouge.md`).
2. **`corpus_check.py`** — chaque chiffre cité dans la réponse doit avoir un similar dans le corpus (similarité ≥ 0,30). Sinon → flag.
3. **`presence.py`** — info obligatoire manquante (ex : question CRFPA mais pas de mention CAPA).

**Couche optionnelle** :

4. **`layer3.py`** — un LLM Mistral Small revérifie la réponse. **OFF par défaut** (+$0.001/q, +2-4s). Activable via `enable_layer3=True`.

**Retry-with-hint** :

- Si `failed_claims` non vide ET budget timeout OK → **tour 2** avec hint réinjecté.
- Cap dur **`MAX_RETRIES_WITH_HINT = 1`** (pas 2 — éviter régression sur claims validés au tour 1).
- Timeout wall-clock **30s**, marge réserve 5s.
- Métrique **`retry_stability`** = ratio claims tour 1 préservés au tour 2. Seuils 0,7 (warn) / 0,5 (audit).

À la sortie : la meilleure réponse (moins de failed_claims gagne).

### Étape 8 — UX Policy (Block / Warn / Modify, déterministe)

**Rôle** : décider quoi faire de la réponse selon la validation (`src/validator/policy.py`).

- **Block** : si la réponse est dangereuse (rare) → remplacée par un message générique sécurisé.
- **Warn** : si flag mineur → ajouter un bandeau d'avertissement à la fin (ex : *"⚠️ Le 'taux d'accès' Parcoursup correspond au rang du dernier appelé, pas au taux d'admission"*).
- **Modify** : ajustements automatiques.

### Étape 9 — Phase projet minimal (déterministe)

**Rôle** : sur certaines questions à enjeu fort (HEC, PASS, médecine, kiné, prépa), **ajouter un bloc** qui rend la réflexion à l'utilisateur (`src/validator/phase_projet.py`) :

```
💭 Avant de décider cette voie :
1. Qu'est-ce qui te motive précisément dans ce choix ?
2. Que sais-tu du métier au quotidien (stages, rencontres, shadowing) ?
3. As-tu rencontré quelqu'un qui fait ce métier ?

👤 Parle-en au CIO le plus proche ou au Psy-EN de ton lycée. Ils sont
formés pour t'aider à structurer ton projet — pas juste à choisir une formation.
```

### Étape 10 — Post-process déterministe (~10ms)

**Rôle** : nettoyer la réponse finale (`src/rag/post_process.py`).

- **`strip_invented_urls`** — retire les URLs github.com hallucinées par le LLM.
- **`fix_broken_markdown_tables`** — répare les tableaux markdown mal formés.
- **`validate_onisep_slugs`** — détecte les slugs ONISEP inventés (FOR.XXXX faux) et les retire.

À la sortie : la réponse définitive envoyée au lycéen.

---

## 4. Walk-through concret — 3 exemples

### Exemple A — Question d'urgence

**User** : *"J'en peux plus, je veux en finir avec tout ça"*

| Étape | Que se passe-t-il ? |
|---|---|
| 1. ScopeClassifier | Regex `\b(en finir\|finir avec) (?:la vie\|tout)\b` matche → URGENT en 0,01s |
| 2-10 | **Court-circuit** — réponse pré-écrite immédiate |

**Réponse retournée (instantanée)** :
```
Je perçois dans ton message une **détresse importante**. Avant tout,
ta sécurité et ton bien-être passent avant les questions d'orientation.

Numéros d'écoute gratuits, anonymes, 24h/24 :
- 3114 — Numéro national de prévention du suicide
- 3919 — Violences faites aux femmes
- 119 — Enfance en danger / maltraitance
- 30 18 — SOS Amitié, écoute généraliste
- 15 — SAMU si urgence vitale immédiate

Tu peux aussi en parler à une personne de confiance...
```

**Latency : ~0s. Coût : 0$.** Le système ne tente jamais de "répondre" — ce n'est pas son rôle.

### Exemple B — Question factuelle pointue

**User** : *"Quel est le taux d'accès de l'EFREI à Paris ?"*

| Étape | Que se passe-t-il ? |
|---|---|
| 1. ScopeClassifier | LLM Mistral Small → `in_scope`, ~0,8s |
| 2. Intent | Regex `\bquel.*taux.*acces` → `factual_pointed` |
| 3. SELECT bypass | `try_select_or_none()` : field=`taux_acces`, entity="EFREI Paris", fuzzy=92 → **MATCH** |
| 4-10 | **Court-circuit** — réponse déterministe sans LLM |

**Réponse retournée** :
```
D'après Parcoursup 2025, le taux d'accès de l'EFREI (Cycle ingénieur post-bac,
Villejuif) est de 67%. La formation propose 580 places, classée "non sélective".

Sources : https://dossierappel.parcoursup.fr/.../?g_ta_cod=14127
```

**Latency : ~1s (juste le ScopeClassifier). Coût : ~$0.0005. Zéro LLM de génération = zéro hallu chiffres par construction.**

### Exemple C — Question complexe in_scope

**User** : *"Je suis en terminale, j'hésite entre prépa MPSI et BUT info à Lyon. J'ai 14 de moyenne en maths."*

| Étape | Que se passe-t-il ? |
|---|---|
| 1. ScopeClassifier | LLM → `in_scope` (~0,8s) |
| 2. Intent | Regex matches : `prépa` + `BUT` + `Lyon` + `14 de moyenne` → priorité `comparaison` (top-k=12, λ=0,6) |
| 3. SELECT | Pas factual_pointed → skip |
| 4. Retrieval | Embed question → FAISS top-30 → rerank (boost CTI, Public, Bac+3, etab nommé) → MMR top-12 |
| 5. Golden QA | Top-1 match : exemple "hésitation prépa vs BUT" → préfixe injecté |
| 6. Generation | FactCard de 12 fiches → JSON `<sources>` → SYSTEM_PROMPT_V4_STRICT → Mistral Medium ~7s |
| 7. Validator | Tour 1 : 0 failed_claims → pas de retry |
| 8. Policy | OK → pas de modification |
| 9. Phase projet | Question MPSI → append bloc "💭 Avant de décider..." |
| 10. Post-process | Vérif URLs OK, slugs ONISEP OK |

**Réponse retournée (~8s, ~200 mots)** :
```
Avec 14 en maths et une hésitation prépa/BUT, voici 2 pistes solides à Lyon :

- **CPGE MPSI au Lycée du Parc** [source S1] : prépa scientifique généraliste,
  taux d'accès Parcoursup 24% en 2025 (très sélective). Ton profil maths est
  cohérent. Voie longue (2 ans + écoles d'ingé), exigeante.

- **BUT Informatique IUT Lyon 1 (Villeurbanne)** [source S3] : 86 places, taux
  d'accès 38% en 2025. Insertion rapide à Bac+3, taux d'emploi 91% à 3 ans
  [source S3]. Plus pratique, alternance possible en B3.

Question pour toi : tu te vois plutôt sur 2 ans très théoriques avant écoles,
ou directement orienté pro à Bac+3 ?

💭 Avant de décider cette voie :
1. Qu'est-ce qui te motive précisément dans ce choix ?
2. Que sais-tu du métier au quotidien (stages, rencontres, shadowing) ?
3. As-tu rencontré quelqu'un qui fait ce métier ?

👤 Parle-en au CIO le plus proche ou au Psy-EN de ton lycée.
```

**Latency : ~8s. Coût : ~$0.003. Citations explicites partout. 0 chiffre inventé.**

---

## 5. Coût et latency par étape (mini-bench v4.1 mesuré)

| Étape | Latency | Coût LLM |
|---|---|---|
| 1. ScopeClassifier | 0,5-1s | ~$0.0005 |
| 2. Intent classifier | <10ms | 0 (regex) |
| 3. SELECT bypass | <100ms | 0 (déterministe) |
| 4. Retrieval (embed + FAISS) | ~0,3s | ~$0.0001 |
| 5. Golden QA retrieval | ~0,3s | ~$0.0001 |
| 6. Generation v4.1 (Mistral Medium) | **5-15s** | **~$0.001-0.003** |
| 7. Validator (sans retry) | <500ms | 0 (déterministe) |
| 7. Validator (avec retry tour 2) | +5-15s | +$0.001-0.003 |
| 8-10. Policy/Phase/Post-process | <100ms | 0 (déterministe) |
| **TOTAL moyen** | **~7-12s** | **~$0.002-0.005** |

---

## 6. Ce qui est ACTIVÉ par défaut (v4.1, depuis le 2026-05-06)

```python
# Configuration appelée par make_production_pipeline()
enable_scope_classifier = True   # Étape 1 — gate amont
use_intent              = True   # Étape 2 — regex 8 classes
use_mmr                 = True   # Étape 4 — diversification
use_metadata_filter     = True   # Étape 4 — filter si criteria
enable_golden_qa        = True   # Étape 5 — few-shot top-1
enable_strict_v4        = True   # Étape 6 — FactCard JSON + R1-R6
enable_validator        = True   # Étape 7 — c1+c2 (rules + corpus + presence)
enable_layer3           = False  # OFF — opt-in (+$0.001/q, +2-4s)
enable_post_process     = True   # Étape 10 — URLs/slugs/tableaux
model                   = "mistral-medium-latest"
```

**Bench v4.1 sur 23 questions** (`results/mini_bench/phase_b4_v4_1.json`) :
- `flagged = 0` (zéro réponse rejetée)
- `avg_honesty_score = 1.0`
- `avg_latency = 7,26s`
- `avg_words = 184`

---

## 7. Fichiers clés à connaître

| Fichier | Rôle |
|---|---|
| `src/rag/factory.py` | **Point d'entrée** — `make_production_pipeline()` instancie tout |
| `src/rag/pipeline.py` | Classe `OrientIAPipeline` — méthode `.answer(question)` |
| `src/rag/scope_classifier.py` | Gate amont (urgent/out_of_scope/in_scope) |
| `src/rag/intent.py` | Intent classifier regex + domain hint |
| `src/lookup/structured_select.py` | SELECT bypass déterministe |
| `src/rag/retriever.py` | FAISS top-k retrieve |
| `src/rag/reranker.py` | Reranker avec boosts (SecNumEdu, CTI, domain-aware...) |
| `src/rag/mmr.py` | MMR diversification |
| `src/rag/embeddings.py` | `fiche_to_text()` + Mistral Embed |
| `src/rag/fact_card.py` | Extraction structurée JSON `<sources>` |
| `src/rag/generator.py` | Appel Mistral Medium |
| `src/prompt/system_v4_strict.py` | **SYSTEM_PROMPT_V4_STRICT** (R1-R6) |
| `src/validator/rules.py` | Rules anti-discrimination + format |
| `src/validator/corpus_check.py` | Vérification claims vs corpus (sim ≥ 0,30) |
| `src/validator/presence.py` | Info obligatoire manquante |
| `src/validator/layer3.py` | Layer 3 LLM (OFF par défaut) |
| `src/validator/policy.py` | Block/Warn/Modify |
| `src/validator/phase_projet.py` | Append bloc CIO/Psy-EN |
| `src/rag/post_process.py` | Post-process déterministe |
| `data/processed/formations.json` | **48 914 fiches** corpus principal |
| `data/embeddings/formations.index` | **FAISS index** 1024d × 48 914 vecteurs |
| `data/processed/golden_qa_meta.json` | **45 Q&A expertes** few-shot |
| `data/embeddings/golden_qa.index` | FAISS Golden QA |

---

## 8. Pour démarrer une session — commandes

```bash
cd ~/projets/OrientIA
source .venv/bin/activate

# Vérifier que l'env est OK
python3 -c "from src.config import load_config; c = load_config(); print(f'Mistral:{bool(c.mistral_api_key)}')"

# Lancer les tests (231 attendus verts)
pytest tests/

# Inspecter une question manuellement (FREE — pas d'appel LLM)
python -m src.eval.inspect_retrieval \
    --questions data/eval_questions.json \
    --out results/retrieval_inspection.md

# Mini-bench reproductible (~$0.10 sur 23 questions)
python scripts/mini_bench.py --phase phase_b4_v4_1
```

**Code minimal pour répondre à une question** :

```python
import json
from pathlib import Path
from mistralai.client import Mistral
from src.rag.factory import make_production_pipeline

client = Mistral(api_key="...")
fiches = json.loads(Path("data/processed/formations.json").read_text())

pipeline = make_production_pipeline(client, fiches)
pipeline.load_index_from("data/embeddings/formations.index")

text, sources = pipeline.answer("Je suis en terminale, j'hésite entre prépa et BUT info")
print(text)
```

---

## 9. Limites connues — ce qu'il faut savoir avant démo

1. **Couverture domaine** — formations bien couvertes : informatique, cybersécurité, ingénierie. Moins bien : santé, droit, architecture, vétérinaire. Le système répond honnêtement *"je n'ai pas de source pertinente"* sur ces domaines (cf R2).

2. **R6 max 250 mots** — appliqué via prompt + `max_tokens=400`. En moyenne 184 mots, mais peut dépasser 300 sur questions complexes (pas un truncate dur côté pipeline).

3. **Pas de multi-tour** — le système est stateless. Chaque question est traitée indépendamment. Phase 4 multi-tour conversationnel à venir (cf `docs/HANDOFF_2026-05-06_pipeline_v4-1_phase4_plan.md`).

4. **Layer3 OFF par défaut** — la couche LLM Mistral Small est désactivée pour économiser coût/latency. Activable si on veut un audit factuel poussé (au prix de +$0.001/q et +2-4s).

5. **Données figées au snapshot** — refresh mensuel cron des opens data prévu, pas encore en place.

6. **Bench n=23** sur le mini-bench v4.1. Run F+G équivalent (n=100, multi-systèmes, multi-judges) à refaire avec v4.1 pour soumission INRIA.

---

## 10. Pour aller plus loin

- **Vision stratégique** → `docs/STRATEGIE_VISION_2026-04-16.md`
- **Décisions architecture** → `docs/DECISION_LOG.md` (15+ ADR)
- **Plan Phase 4 multi-tour** → `docs/HANDOFF_2026-05-06_pipeline_v4-1_phase4_plan.md`
- **État opérationnel** → `docs/SESSION_HANDOFF.md`
- **Méthodologie benchmark** → `docs/METHODOLOGY.md`

---

*Doc créé le 2026-05-07 pour onboarding. Référence pipeline v4.1 (commit 5f2b201).*
