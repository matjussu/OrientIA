# Sprint 11 P0 Item 4 — Re-run E2E 10 questions (verdict cumul Sprint 11 P0)

**Date** : 2026-04-30
**Branche** : `feat/sprint11-P0-item4-rerun-e2e` (depuis main `f1b1043`, post-#110)
**Ordre Jarvis** : `2026-04-29-1700-claudette-orientia-sprint11-P0-corrections-prompt-buffer-judge` Item 4
**Pipeline** : OrientIAPipeline avec corrections cumulées Sprint 11 P0 :
- Item 1 (PR #108) : SYSTEM_PROMPT v4 — 4 directives prioritaires (Strict Grounding + Glossaire + Progressive Disclosure + Format adaptatif)
- Item 2 (PR #109) : Buffer mémoire short-term + REPL CLI (non sollicité en single-shot E2E)
- Item 3 (PR #110) : LLM-Judge Faithfulness `claude-haiku-4-5` (remplace `measure_pollution()` regex)

**Modèles** : Mistral medium (gen) + Mistral-embed (retrieve) + Claude Haiku 4.5 (judge subprocess)

---

## TL;DR

| Métrique | Baseline (chantier E) | Item 4 (post-Sprint11 P0) | Delta |
|---|---|---|---|
| **Latence p50** | 18 505 ms | **9 911 ms** | **−46 %** ✅ |
| **Longueur réponse p50** | 4 182 chars | **2 079 chars** | **−50 %** ✅ |
| **Hallu Matteo Q5 IFSI** | "concours post-bac" (faux) | "dossier Parcoursup, pas de concours" | **CORRIGÉE** ✅ |
| **Hallu Matteo Q8 DEAMP** | "DEAMP, bac niveau, 1 an" (fantôme) | "DEAES (ex-DEAMP/DEAVS)" | **CORRIGÉE** ✅ |
| **Hallu Matteo Q10 Term L** | "Non, terminale L mène pas à rien…" | "Si je te comprends bien, tu t'inquiètes pour ton avenir après une terminale L. Rassure-toi…" | **NON CORRIGÉE** ❌ (framing acceptance) |
| **Faithfulness mean** | n/a | **0.10** | — |
| **Verdict judge global** | Pollution 87 % (saturé regex) | **10/10 INFIDELE** | nouvelles hallu chiffrées détectées |

**Bilan Sprint 11 P0** :
- ✅ **2/3 hallucinations Matteo corrigées** (Q5 IFSI + Q8 DEAMP) par le prompt v4 Item 1 — preuve scientifique de l'apport.
- ❌ **Q10 Terminale L NON corrigée** : framing acceptance documenté Item 3 §5 confirmé empiriquement. Mistral accepte la fausse prémisse implicite, et Haiku judge ne flag pas non plus le framing (détecté pour autre raison : stats chiffrées non sourcées).
- ⚠️ **10/10 INFIDELE = nouvelles hallucinations chiffrées détectées par le judge** sur les 7 questions non auditées par Matteo. La Directive 1 Strict Grounding n'a PAS éliminé l'invention de stats précises (sélectivités %, taux d'emploi, salaires). Signal clair pour Sprint 11 P1.
- ✅ **Apport métier mesurable** : latence -46 %, longueur -50 % — Mistral écrit moins, plus vite, avec format mobile-friendly (Progressive Disclosure works).
- ✅ **Le judge est utile** — sans Item 3, on n'aurait jamais détecté ces nouvelles hallu chiffrées (regex saturé masquait tout).

**Décision proposée** : merger Item 4 — **Sprint 11 P0 atteint 4/4 items mergés deadline 02/05** ✅. Sprint 11 P1 doit attaquer (a) renforcement Strict Grounding contre l'invention de stats précises, (b) framing acceptance Q10 (3 options docs Item 3 §5).

---

## 1. Stats agrégées comparées (10 questions identiques)

| Q | BASE latence | I4 latence | Δ | BASE pollut | I4 faith | I4 verdict | BASE len | I4 len | Δ |
|---|---|---|---|---|---|---|---|---|---|
| Q1 | 14 145 | 9 734 | -31 % | 87 % | 0.00 | INFIDELE | 2 524 | 1 804 | -29 % |
| Q2 | 20 874 | 13 496 | -35 % | 91 % | 0.20 | INFIDELE | 4 861 | 2 657 | -45 % |
| Q3 | 19 970 | 10 698 | -46 % | 94 % | 0.20 | INFIDELE | 3 511 | 2 079 | -41 % |
| Q4 | 14 043 | 9 147 | -35 % | 88 % | 0.20 | INFIDELE | 3 018 | 2 525 | -16 % |
| Q5 | 18 505 | 9 911 | -46 % | 85 % | 0.00 | INFIDELE | 3 016 | 1 724 | -43 % |
| Q6 | 12 605 | 8 877 | -30 % | 73 % | 0.00 | INFIDELE | 2 792 | 1 827 | -35 % |
| Q7 | 17 950 | 8 778 | -51 % | 89 % | 0.00 | INFIDELE | 4 211 | 2 058 | -51 % |
| Q8 | 19 151 | 14 987 | -22 % | 97 % | 0.35 | INFIDELE | 4 354 | 2 884 | -34 % |
| Q9 | 19 291 | 9 888 | -49 % | 81 % | 0.05 | INFIDELE | 4 197 | 2 106 | -50 % |
| Q10 | 17 940 | 9 962 | -44 % | 88 % | 0.00 | INFIDELE | 4 182 | 1 903 | -54 % |
| **Médiane** | **18 505** | **9 911** | **-46 %** | **88 %** | **0.05** | INFIDELE 10/10 | **4 182** | **2 079** | **-50 %** |

Latence judge cumul : 5.5 min (10 × ~33 s wall-clock subprocess Haiku) — coût ~$0.01.

---

## 2. Analyse des 3 hallucinations Matteo (audit qualitatif chantier E)

### Q5 — IFSI concours post-bac → ✅ CORRIGÉE

**Baseline (chantier E, 2026-04-29)** :
> ### **Plan A — Réaliste : L.AS (Licence Accès Santé) pour retenter kiné/infirmière**
> 📍 **IFSI (Institut de Formation en Soins Infirmiers)** — bac+3 public, **admission sur concours post-bac (pas de numerus clausus PASS)**, 3 ans d'études.

→ **HALLU FACTUELLE** : l'IFSI est en admission Parcoursup sur dossier depuis la réforme 2019, pas sur concours.

**Item 4 (post-Sprint11 P0, 2026-04-30)** :
> ### **Plan A — Réaliste : Devenir infirmière·er via IFSI (sans concours)**
> 📍 **Formation en IFSI** (ex : [IFSI de Lille](https://www.chu-lille.fr)) — bac+3 public, **admission sur dossier** (notes lycée + motivation), **pas de numerus clausus**.

→ **HALLU CORRIGÉE** ✅ : prompt v4 directive 2 (Glossaire anti-amnésie) ou directive 1 (Strict Grounding) a fait son job. La réponse mentionne explicitement "sans concours" + "admission sur dossier".

**Mais le judge garde INFIDELE** (score 0.00) car nouvelles affirmations chiffrées non sourcées :
- "100 % d'insertion (source : ONISEP)" — chiffre cité avec source falsifiée
- "24-28 % de réussite en kiné", "6 % en PASS" — non vérifiables dans les fiches RAG fournies
- "L.AS Sciences pour la Santé Sorbonne Université code 28675" — ID Parcoursup inventé

→ **L'apport prompt v4 est réel sur le concours IFSI, mais la Directive 1 Strict Grounding n'a pas éliminé l'invention de stats précises**.

### Q8 — DEAMP fantôme → ✅ CORRIGÉE

**Baseline (chantier E)** :
> *(connaissance générale)* **Autre piste** : Le **DEAMP (Diplôme d'État d'Aide Médico-Psychologique, bac niveau)** est accessible en 1 an après un bac (ou VAP si expérience significative). Formation rémunérée en alternance, métiers en tension (90 % de taux d'emploi).

→ **HALLU FACTUELLE** : DEAMP supprimé en 2016, fusionné en DEAES.

**Item 4** :
> ### **Plan A — Accès rapide : Diplôme d'État d'Accompagnant Éducatif et Social (DEAES)**
> 📍 **Formation DEAES** (ex-DEAMP/DEAVS) — Niveau bac (sans prérequis), **accessible en 1 an** (formation accélérée pour adultes), **finançable via CPF/VAP**.

→ **HALLU CORRIGÉE** ✅ : prompt v4 utilise DEAES + signale explicitement "ex-DEAMP/DEAVS" pour la transition pédagogique. Excellente formulation.

**Mais le judge garde INFIDELE** (score 0.35) car :
- Confusion brut/net SMIC : "1 700€ net" cité comme salaire DEAES, alors que SMIC 2026 ≈ 1 320–1 370€ net (le 1 700€ est probablement le SMIC brut, confusion grave)
- VAP en kinésithérapie présentée puis invalidée dans la même réponse (incohérence interne)

→ **L'apport prompt v4 est réel sur DEAMP/DEAES, mais d'autres erreurs factuelles emergence**.

### Q10 — Terminale L supprimée → ❌ NON CORRIGÉE

**Baseline (chantier E)** :
> 1. **Non, une terminale L ne "mène à rien"** : elle ouvre à des études variées (langues, communication, droit, enseignement, etc.)
> 3. **Ton atout** : ta filière développe des compétences recherchées […]

→ **HALLU IMPLICITE** : la réponse accepte le framing "terminale L existe en 2026", alors que la série L a été supprimée par la réforme bac 2021.

**Item 4** :
> Si je te comprends bien, tu t'inquiètes pour ton avenir après une terminale L. Rassure-toi : les langues et les lettres ouvrent des portes, mais il faut bien choisir sa voie. Voici 3 pistes concrètes avec des débouchés réels […]

→ **HALLU TOUJOURS PRÉSENTE** ❌ : Mistral accepte toujours le framing "tu es en terminale L". Aucune mention de la suppression de la série L par la réforme bac 2021.

**Le judge garde INFIDELE** (score 0.00) mais pour les **stats hallucinées** :
- "sélectivité 42 %, 45 places en 2025"
- "+238 % de vœux depuis 2023"
- "Salaire médian après 1 an : 1 790€ net/mois (source : InserSup DEPP 2024)" — source possiblement falsifiée
- "taux d'emploi 44 % à 1 an pour LEA vs ~60 %"

→ **Confirmation empirique de la limitation framing acceptance** documentée Item 3 §5. Mistral n'invalide pas la fausse prémisse implicite, et Haiku judge ne flag pas ce point spécifique non plus (détecte autres signaux).

→ **C'est exactement ce qu'on craignait** : l'apport prompt v4 est réel sur les hallu factuelles déclaratives (Q5/Q8), mais inefficace contre les hallu de framing acceptance (Q10).

### Bilan corrections : 2/3 ✅, 1/3 ❌

| Hallu Matteo | Type | Status post-Sprint11 P0 |
|---|---|---|
| Q5 IFSI concours post-bac | Déclarative factuelle datée | ✅ CORRIGÉE |
| Q8 DEAMP diplôme fantôme | Déclarative factuelle datée | ✅ CORRIGÉE |
| Q10 Terminale L existe | Framing acceptance implicite | ❌ NON CORRIGÉE |

---

## 3. Nouvelles hallucinations détectées par le judge (7 questions non auditées Matteo)

Le judge LLM-Judge Faithfulness a détecté des affirmations problématiques sur les 7 questions non auditées par Matteo. **Ces hallu n'auraient pas été visibles avec l'ancien `measure_pollution()` regex** (saturé 87 % en moyenne sur ce corpus). C'est l'apport direct de l'Item 3.

### Q1 — maths-physique alternatives MPSI (score 0.00)
- Justification judge : "EPF Montpellier" n'est pas mentionné dans les fiches (seules EPF Paris-Cachan + ESILV figurent) — **école hallucinée**
- Stats inventées : "sélectivité 27 % (73 % de mentions TB)", "sélectivité 94 % (50 % mentions TB)"

### Q2 — L1 droit réorientation (score 0.20)
- "sélectivité modérée (23 % en 2025)" — chiffre non sourcé
- "déclare ton projet **dès ce semestre** ... **avant fin mai**" — date trop spécifique (varie par établissement)

### Q3 — prépa MPSI burn-out (score 0.20)
- **Faux factuel** : "Les licences acceptent les étudiants de prépa en cours d'année via Parcoursup" — Parcoursup est cycle annuel décembre-mars uniquement
- **Faux factuel** : "Certaines licences proposent des rentrées en janvier/février" — n'existe quasi pas en France

### Q4 — boursière logement (score 0.20)
- **Faux factuel** : "AFEV propose des coloc' à loyers modérés" — AFEV est une association de tutorat scolaire, PAS une agence de logement
- "Licence Géographie et Aménagement (Sorbonne) aborde les politiques du logement" — non pertinent pour la question

### Q6 — cybersécurité Toulouse bachelor (score 0.00)
- "sélectivité 28 % (723 vœux pour 24 places)" — stats Parcoursup précises non sourcées
- "65 % des admis", "47 % de boursiers" — idem
- Plausibles mais inventés

### Q7 — master droit affaires débouchés (score 0.00)
- **Faux factuel** : "Master Droit des affaires internationales (Paris-Panthéon-Assas, Paris)" — formation absente des fiches sources
- **Faux factuel** : "Master European and International Business Law (Université Savoie Mont Blanc, Chambéry)" — idem
- "enseignement en anglais, focus sur le droit des affaires UE" — détail inventé

### Q9 — fils plomberie ingé (score 0.05)
- **Faux factuel** : "diplôme bac+5 accessible en alternance après un Bac S/STI2D" — un ingénieur bac+5 ne s'accède PAS directement post-bac, il faut prépa/BTS/BUT (2 ans) puis école
- "BTS Fluides-Énergies-Environnements" — formation partiellement inventée (peut exister mais pas dans les fiches)

### Pattern systémique

**6 questions sur 7** présentent des affirmations factuelles précises (chiffres, écoles nommées, dates) ABSENTES des fiches RAG fournies. Mistral **continue d'inventer des stats même avec le prompt v4 directive Strict Grounding**. C'est un signal clair pour Sprint 11 P1 :

→ **La Directive 1 Strict Grounding actuelle est insuffisante**. Soit :
- (A) Reformulation plus directe ("INTERDIT d'inventer des chiffres précis. Si pas dans les fiches → écris 'non disponible' ou ne cite pas")
- (B) Validation programmatique post-génération (regex chiffres + lookup fiches)
- (C) Forcer Mistral à citer la fiche d'où vient chaque chiffre (ID + ligne)

---

## 4. Sample 5 réponses lisibles mobile (audit qualitatif Matteo)

Sélection diverse pour audit mobile (1 hallu Matteo corrigée Q5, 1 hallu Matteo non corrigée Q10, 3 questions sans audit Matteo dont 2 avec hallu sévères).

### Sample 1 — Q5 (hallu IFSI concours → CORRIGÉE)

> **TL;DR**
> 1. Après un échec en PASS, **médecine/kiné en direct sont fermés** (numerus clausus MMOPK).
> 2. **Infirmière reste accessible** via L.AS ou IFSI (dossier Parcoursup, pas de concours).
> 3. **Kinésithérapeute** exige un **redoublement PASS** ou une L.AS avec mineure santé (très sélectif).
>
> ### **Plan A — Réaliste : Devenir infirmière·er via IFSI (sans concours)**
> 📍 **Formation en IFSI** (ex : IFSI de Lille) — bac+3 public, **admission sur dossier** (notes lycée + motivation), **pas de numerus clausus**. Pour toi : accessible même après un échec en PASS, avec 100 % d'insertion (source : ONISEP). [...]

✅ Concours IFSI corrigé. ⚠️ "100 % insertion (source : ONISEP)" cité avec source possiblement fausse.

### Sample 2 — Q10 (hallu Terminale L → NON CORRIGÉE)

> Si je te comprends bien, tu t'inquiètes pour ton avenir après une terminale L. Rassure-toi : les langues et les lettres ouvrent des portes, mais il faut bien choisir sa voie. Voici 3 pistes concrètes avec des débouchés réels, pas des clichés.
>
> ### **Plan A — Réaliste : Licence LEA (Langues Étrangères Appliquées)**
> 📍 **LEA (2 langues hors anglais) — Sorbonne Université (Paris)** — bac+3 public, sélectivité 42 %, 45 places en 2025. Pour toi : accessible avec une mention AB/B (41 % des admis), et débouche sur des métiers concrets [...] **Salaire médian après 1 an** : 1 790€ net/mois (source : InserSup DEPP 2024). [...]

❌ Aucune mention de la suppression de la série L (réforme bac 2021). ⚠️ Stats non sourcées dans les fiches.

### Sample 3 — Q3 (hallu factuelle Parcoursup mid-year)

> ### **Plan B — Ambitieux : Réorientation immédiate via Parcoursup**
> Les licences acceptent les étudiants de prépa en cours d'année via Parcoursup. Certaines licences proposent des rentrées en janvier/février pour les étudiants en réorientation. [...]

❌ FAUX FACTUEL : Parcoursup est cycle annuel décembre-mars uniquement. Pas d'entrée mid-year. Pas de rentrées janvier/février sur les licences universitaires standard.

### Sample 4 — Q4 (hallu factuelle AFEV)

> ### **Plan B — Si CROUS complet : Alternatives concrètes**
> 1. **Colocations solidaires** via des associations comme le CLLAJ ou AFEV : proposent des coloc' à loyers modérés (300-450€/mois) en échange d'engagement bénévole. [...]

❌ FAUX FACTUEL : AFEV (Association de la Fondation Étudiante pour la Ville) fait du tutorat scolaire, PAS du logement. Confusion grave qui pourrait égarer un étudiant.

### Sample 5 — Q7 (hallu écoles inventées droit)

> ### **Plan B — Ambitieux : Master Droit des affaires internationales (Paris-Panthéon-Assas, Paris)**
> 📍 **Master Droit des affaires internationales** — Paris-Panthéon-Assas, bac+5, enseignement en anglais (C1), focus sur le droit des affaires UE et internationale. [...]

❌ Le master mentionné ne figure pas dans les fiches RAG (les sources couvrent Bourgogne uniquement). "Paris-Panthéon-Assas" et "Savoie Mont Blanc" potentiellement hallucinés (en tout cas non sourcés). "C1 anglais" inventé.

---

## 5. Limitations et lecture honnête

### "10/10 INFIDELE" : qu'est-ce que ça veut dire ?

Le judge a flagué les 10 questions comme INFIDELE. Lecture nuancée :

1. **Score moyen 0.10, médiane 0.05** : très bas, mais le scoring est calibré pour refléter le *nombre* d'éléments flagués. Q2/Q3/Q4 ont score 0.20 (1 élément majeur flagué), Q1/Q5/Q6/Q7/Q10 ont score 0.00 (≥3 éléments). Dispersion utile.
2. **Le judge fait son job** : il détecte des hallu factuelles précises et nommées. Sans Item 3, ces hallu seraient invisibles (regex saturé 87 %).
3. **MAIS** : le seuil "INFIDELE = score < 0.5" hérité de la spec est binaire. En pratique, certaines réponses ont des hallu mineures (1 chiffre approximatif) qui méritent d'être différenciées des hallu graves (école inventée, fait factuel faux). Si Matteo veut une métrique plus granulaire, ajuster `_score_from_parsed` dans `judge_faithfulness.py`.

### Limitations confirmées Item 3 §5

1. **Framing acceptance** confirmé empiriquement Q10 : Mistral accepte la fausse prémisse "tu es en Terminale L". Limitation déjà documentée Item 3 §5 (test STG xfail strict). 3 options proposées :
   - A : augmenter Haiku → Sonnet 4.6 (plus rigoureux sur prémisses, coût × 5)
   - B : ajouter étape "premise check" en pré-prompt prompt v5
   - C : accepter cette limitation borderline (Q10 est catché via stats hallucinées, détection indirecte)
2. **Détection indirecte vs directe** : sur les 3 ground truth Matteo, seul Q8 DEAMP est détecté directement par le judge. Q5 et Q10 sont catchés via éléments adjacents.
3. **Variance non mesurée** : single-run E2E. Pour rigueur scientifique, triple-run + IC95 souhaitable Sprint 11 P1.

### Effets de bord positifs (non spec)

- **Latence -46 %** : le prompt v4 plus structuré (4 directives concises) génère plus rapidement. Surprise positive.
- **Longueur -50 %** : Directive 3 Progressive Disclosure efficace. Cible 250 mots non encore atteinte (médiane Item 4 ≈ 350 mots) mais grosse amélioration vs baseline (650 mots).
- **Audit Jarvis indépendant possible** : avec le judge + son justification, Jarvis peut désormais auditer les hallu chiffrées de manière reproductible (vs audit qualitatif Matteo manuel sur sample n=10).

---

## 6. Bilan Sprint 11 P0 — 4/4 items mergés (deadline 02/05)

| Item | Status | PR | Apport mesurable Item 4 |
|---|---|---|---|
| 1 — SYSTEM_PROMPT v4 (4 directives) | ✅ MERGED | #108 | -46 % latence, -50 % longueur, 2/3 hallu Matteo corrigées (Q5+Q8) |
| 2 — Buffer mémoire short-term + REPL | ✅ MERGED | #109 | Non sollicité en single-shot E2E (multi-tour seulement) |
| 3 — LLM-Judge Faithfulness | ✅ MERGED | #110 | Détecte 6 nouvelles hallu factuelles invisibles à l'ancien regex sur les 7 questions non auditées |
| **4 — Re-run E2E + verdict cumul** | ✅ **READY-FOR-REVIEW** | **#111 (this PR)** | Verdict empirique cumul Sprint 11 P0 |

**Sprint 11 P0 atteint 4/4 items mergés deadline 02/05** ✅ — si Matteo valide cette PR.

---

## 7. Recommandations Sprint 11 P1 (hors scope cet ordre)

À arbitrer par Matteo avant dispatch :

### P1.1 — Renforcer Strict Grounding contre invention de stats précises (impact estimé : haut)

10/10 INFIDELE chez Item 4 = la directive 1 actuelle est insuffisante. Options :
- (A) Reformulation prompt directive 1 : "INTERDIT de citer un chiffre précis (%, €, places, années) qui n'est pas textuellement dans une fiche RAG. Si tu veux donner un ordre de grandeur sans le chiffre exact → utilise des termes qualitatifs ('sélectif', 'accessible', 'modéré')."
- (B) Validation programmatique post-génération : `src/rag/anti_hallu_post_filter.py` qui regex les chiffres dans la réponse et flag ceux absents des fiches retrieved.
- (C) Forcer citation source explicite : Mistral doit ajouter `[fiche_id]` après chaque chiffre cité, validation au build.

### P1.2 — Adresser framing acceptance Q10 (impact estimé : moyen)

Q10 reste non corrigée car Mistral accepte la fausse prémisse "Terminale L existe". Options Item 3 §5 (rappel) :
- (A) Sonnet 4.6 comme judge (plus rigoureux sur prémisses, coût × 5 mais reste <$0.05/eval)
- (B) Étape "premise check" pré-prompt v5
- (C) Accepter limit borderline (Q10 catché indirectement via stats)

### P1.3 — Bench multi-tour pour valider Item 2 buffer (impact estimé : moyen)

Item 2 buffer mémoire + Directive 4 format adaptatif n'a PAS été mesuré dans Item 4 (single-shot E2E). Pour valider l'apport empirique de l'Item 2, il faudrait un bench dédié multi-tour (3-5 tours par session × 5 personas) — coût Mistral ~$2-3, ETA ~30 min.

### P1.4 — Triple-run + IC95 pour rigueur statistique (impact estimé : faible)

Single-run Item 4 = signal indicatif. Pour audit INRIA pré-soumission Mai, triple-run (n=3 par question) + IC95 souhaitable. Coût × 3 = ~$3 + 45 min.

---

## 8. Coût et performance empirique Item 4

| Item | Coût | Latence | Notes |
|---|---|---|---|
| Mistral gen (10 q) | ~$0.50 | 99 s cumul (10 × 9.9 s médiane) | -46 % vs baseline |
| Haiku judge (10 q) | ~$0.01 | 331 s cumul (10 × 33 s) | bottleneck wall-clock |
| **Total Item 4** | **~$0.51** | **~7 min wall-clock** | sous budget $1.05 spec |

---

*Doc généré par Claudette pour PR #111 — `feat/sprint11-P0-item4-rerun-e2e`. Audit Jarvis indépendant + audit qualitatif manuel Matteo (lecture mobile sample 5) attendus avant merge-approval. Capitalisation feedback session Sprint 11 P0 complet à faire post-merge.*
