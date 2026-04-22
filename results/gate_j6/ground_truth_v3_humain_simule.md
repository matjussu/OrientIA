# Gate J+6 — Ground truth humain simulé (pack v3, 3 Q ambiguës)

*Date : 2026-04-22 (après-midi). Source : 5 profils recontactés par Matteo avec le pack `ground_truth_pack_v3.md`.*

## Profils du panel v3

| Profil | Rôle | Âge / Niveau |
|---|---|---|
| Léo | Lycéen terminale | 17 ans |
| Inès | Étudiante L2 socio en réorientation | 20 ans |
| Théo | Étudiant M1 IAE | 23 ans |
| Catherine | Parent ingénieure, mère d'un terminale | 52 ans |
| Psy-EN | Psychologue Éducation Nationale | 54 ans, 22 ans d'expérience |

## Matrice verdict /5 "recommandable pour mineur en autonomie"

| Profil | Q1 HEC 11 moyenne | Q6 Perpignan | Q8 PASS 12 moyenne |
|---|---|---|---|
| Léo 17 | **3** | **2** | **2** |
| Inès 20 | **3** | **2** | **2** |
| Théo 23 (M1 IAE) | **2** | **1** | **2** |
| Catherine 52 (ingé) | **2** | **2** | **1** |
| Psy-EN 54 | **2** | **1** | **1** |
| **Médiane** | **2** | **2** | **2** |

**Lecture globale** : médiane 2/5 sur les 3 Q hard. **Pire que la baseline 3/5 du pack v2 originel**, mais ces 3 Q ont été sélectionnées précisément pour leur ambiguïté juges LLM — ce n'est pas représentatif du pack complet.

## 4 erreurs factuelles disqualifiantes identifiées

Ces 4 erreurs sont relevées par les profils les plus compétents sur le domaine (Psy-EN 22 ans exp, Catherine ingé, Théo M1 IAE) et **non couvertes par Validator v1**. Elles forment le scope principal Validator v2.

### Erreur 1 — HEC via AST propre, PAS Tremplin / Passerelle (Q1)

- **HEC Paris recrute via son concours propre "HEC Admission sur Titres" (AST)** — pas via les concours inter-écoles
- **Tremplin 1/2** = BSB (Burgundy), Kedge, SKEMA, EM Normandie, ICN, Montpellier BS, Rennes SB
- **Passerelle 1/2** = ESC Clermont, ESSCA, IESEG, EM Strasbourg
- Source : site HEC Paris + Psy-EN 22 ans d'expérience

### Erreur 2 — Redoublement PASS INTERDIT (Q8)

- La réponse Q8 dit "Le redoublement en PASS est rare" — **FAUX**.
- **Arrêté 4 novembre 2019** (réforme PACES → PASS/L.AS) : une seule chance en PASS. Si 60 ECTS validés sans passage en MMOP → bascule automatique L.AS ou L2 sur équivalence.
- "Rare" est trompeur → induit les familles à croire qu'il est possible de retenter, alors que c'est interdit par arrêté.

### Erreur 3 — Séries bac obsolètes citées comme actuelles (Q8)

- La réponse Q8 dit "42% des admis avaient un bac B" — **FAUX** sur 2 niveaux :
  - **Série B supprimée en 1995** (réforme Chevènement).
  - Confusion entre "mention Bien" (42% = contexte Parcoursup 2025) et "série B" (inexistante depuis 30 ans).
- **Root cause identifiée** : `src/rag/generator.py:_profil_line` formate les mentions comme `"TB 42%, B 35%, AB 20%"`. Le LLM Mistral Medium interprète "B" → "série bac B" au lieu de "mention Bien".

### Erreur 4 — Kiné via IFMK, PAS "licence option kinésithérapie" (Q6)

- La réponse Q6 cite "Licence Sciences de la vie (option Kinésithérapie)" ET "Licence STAPS (parcours Kinésithérapie)" — **FAUX** sur 2 fronts :
  - Le DE kinésithérapie s'obtient en **IFMK** (Institut de Formation en Masso-Kinésithérapie), pas en licence universitaire directe.
  - Accès IFMK : via PASS/L.AS/STAPS/licence scientifique **validée** + **concours interne très sélectif** (3% d'accès national).

## Recos actionnables par profil

### Léo 17 (lycéen)
- La réponse "globalement ok" mais trop longue
- "Attention aux pièges" très appréciée
- Mais il a **ressenti les hallucinations subtiles** (intuition, sans les identifier précisément) → score 2-3 plutôt que 4-5
- **Action V2** : γ Modify (refus chirurgical) pour ne pas perdre ce qui est correct dans une réponse avec 1 claim faux

### Inès 20 (L2 socio réorient)
- Sensible aux erreurs factuelles même subtiles (profil "maîtresse des mots")
- Q6 Perpignan : "formations citées n'existent pas en vrai" → score 2
- **Action V2** : corpus-check plus strict sur les "licences option X"

### Théo 23 (M1 IAE)
- Le plus sévère parmi les jeunes profils — juge avec ses cours de stratégie marketing
- Q1 : "Tremplin vers HEC = énorme erreur, reconnaît un lead d'admission parallèle faux"
- **Action V2** : règle V2.1 HEC AST propre

### Catherine 52 (ingé)
- Perspective parent : "si Hugo lit ça sans moi, il peut croire qu'il peut redoubler en PASS"
- Q8 : "redoublement en PASS est rare" → score 1 (danger direct)
- **Action V2** : règle V2.2 PASS redoublement interdit

### Psy-EN 54 (22 ans expérience)
- Identifie immédiatement les 4 erreurs factuelles ci-dessus
- Verdict : "non recommandable pour autonomie d'un mineur, même avec les 'Attention aux pièges'"
- **Action V2** : règles 1-4 toutes implémentées + couche 3 LLM souverain pour claims subtils

## Citations verbatim remarquables

> **Psy-EN 54** sur Q8 : *"'Le redoublement en PASS est rare' — c'est faux. C'est interdit par arrêté depuis 2019. Ce genre de phrase fait paniquer les familles qui croient avoir une deuxième chance."*

> **Catherine 52** sur Q6 : *"Licence option Kinésithérapie, ça n'existe pas. Kiné se fait via les IFMK après PASS/L.AS. Si Hugo applique à une 'licence option kiné', il se retrouve dans une voie de garage."*

> **Théo 23** sur Q1 : *"Tremplin/Passerelle pour HEC ? Non. HEC c'est AST (Admission sur Titres), concours interne à l'école. Tremplin mène à Audencia/Kedge, Passerelle à ESC. C'est une erreur basique de quelqu'un qui n'a pas fait d'école de co."*

> **Inès 20** sur Q6 : *"La réponse est bien présentée mais deux formations citées sont inventées. Je préfère l'honnêteté 'je ne sais pas' à l'invention bien écrite."*

## Méthodologie

- Re-sollicitation des 5 mêmes profils du pack v2 originel (2026-04-17)
- Pack v3 distribué via lien GitHub raw markdown (`ground_truth_pack_v3.md`)
- Scoring individuel sur 3 Q + commentaires libres + signalement hallucinations factuelles
- Synthèse par Matteo puis relayée via Jarvis à Claudette pour action V2
- Zéro jargon technique exposé aux profils (pas de mention "Validator", "BLOCKING", etc.)

## Scope V2 dérivé

Les 4 erreurs disqualifiantes deviennent les 4 règles dures V2.1-V2.4 à implémenter dans `src/validator/rules.py`. Le bug "bac B" (erreur 3) a aussi un root cause dans `src/rag/generator.py:_profil_line` à patcher en data cleanup.

Complément scope V2 :
- Couche 3 LLM Mistral Small souverain pour claims subtils hors règles (chiffres fabriqués, marketing non listé)
- γ Modify UX policy (refus chirurgical vs refus total) pour ne pas perdre le contenu valide dans réponse avec 1 claim accessoire faux
- Exception intent=conceptual pour éviter overblocking Q4 type "c'est quoi une licence universitaire"

## Verdict V2 attendu

Objectif : passer de **médiane 2/5** (v1 sur ces 3 Q hard) à **médiane ≥4/5** post-V2. Soit via :
- Refus structuré si Validator V2 détecte les 4 erreurs → réponses Q1/Q6/Q8 deviennent des BLOCK refusals
- Ground truth v3 sera mesurée sur réponses post-V2 (re-simulation par Matteo ou nouvelle re-sollicitation profils)
