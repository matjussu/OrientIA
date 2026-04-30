# Sprint 10 chantier E — Test serving end-to-end (mesures empiriques)

**Date** : 2026-04-29
**Questions testées** : 10
**Réponses valides** : 10/10
**Pipeline** : OrientIAPipeline avec `use_metadata_filter=True` (chantier C activation, post-merge #106) + `use_golden_qa=True` (chantier D, post-merge #104)
**Corpus** : `formations_unified.json` (55 606 entries, post-merge #105)
**Modèles** : Mistral medium (generate) + Mistral-embed dim 1024 (retrieve)

---

## Stats agrégées (mesures empiriques)

### Alerte 2 — Latence end-to-end

- p50 (médiane) : **9911 ms**
- p90 : **14987 ms**
- max : **14987 ms**
- min : 8778 ms
- moyenne : 10547 ms

Note : t_total_ms = AnalystAgent (si actif) + Q&A Golden retrieve (si actif) + FAISS retrieve + reranker + filter + Mistral generate. Pas de breakdown granulaire dans cette première mesure (à raffiner Sprint 11 si latence problématique).

### Alerte 4 — Faithfulness LLM-Judge (Sprint 11 P0 Item 3)

- Score faithfulness moyen : **0.10** (1.0 = totalement fidèle, 0.0 = très infidèle)
- Score médian : 0.05
- Réponses flagées (score < 0.5) : **10/10**
- Latence judge médiane : 29940ms (subprocess `claude --print --model claude-haiku-4-5`)

Méthode : pour chaque réponse Mistral, appel `judge_faithfulness(question, answer, fiches)` (claude-haiku-4-5) qui produit VERDICT FIDELE/INFIDELE + liste d'éléments non sourcés + justification 1-2 phrases. Remplace l'ancien regex pollution naïf saturé sur ce corpus (cf bench A/B `docs/sprint11-P0-item3-bench-judge-vs-regex-2026-04-29.md`).

**Lecture du score** :
- ≥ 0.8 : fidèle (peu/pas d'affirmations non sourcées)
- 0.5 ≤ score < 0.8 : zone grise (juge fidèle mais notes ou inverse)
- < 0.5 : flagué (au moins 1 affirmation factuelle non sourcée)
- 0.5 strict : parse error / timeout — caller décide quoi en faire

### Alerte 1 — Filter saturation (mesure empirique)

- Questions hit_max (cap MAX_K_MULTIPLIER atteint) : **0/10**
- n_after_filter médiane : 30
- n_after_filter moyenne : 30
- expansions cumul : 0 (sur 10 questions)

**Décision data-driven** :
- Si >30% questions hit_max → migration FAISS → Qdrant urgente Sprint 11
- Si 5-30% → fallback graceful filter Sprint 11
- Si <5% → architecture FAISS post-filter actuelle suffit

### Q&A Golden retrieval coverage

- Questions avec match Q&A Golden : **10/10**
- Coverage : 100%

Note : 45 Q&A Golden actuelles couvrent uniquement `lyceen_post_bac` (nuit 1). Coverage complète attendue post-nuit 2 (drops-only autres catégories).

---

## 10 réponses Mistral pour audit qualitatif

### Q1 — Je suis en terminale spé maths-physique mais je sature des maths abstraites, alternatives ...

**Mesures** : t_total=9734ms | filter n_after=30 expansions=0 hit_max=False | faithfulness=0.00 (INFIDELE)

**Q&A Golden top-1** : `A1` iter 6 (score 88, retrieve sim 0.94)
  - Seed : « Je suis en terminale spé maths-physique mais je sature des maths abstraites, alternatives concrètes à la prépa MPSI ? »

**Réponse Mistral** :

> **TL;DR**
> Tu veux du concret en maths/physique sans l’abstraction pure de la prépa ? Voici 3 pistes **appliquées** avec des projets dès la 1ère année, hors prépa MPSI.
> 
> ---
> **Plan A — Licence double diplôme Maths-Physique à Versailles**
> 📍 [Licence Maths-Physique-Sciences de l’Ingénieur](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=41045&typeBac=0&originePc=0) (Université Paris-Saclay) — **bac+5 public**, sélectivité 27% (73% de mentions TB).
> *Pour toi : mix théorie/concret avec projets ingé, mais exigeant en notes (TB quasi obligatoire).*
> 
> **Plan B — École d’ingé post-bac accessible (EPF Montpellier)**
> 📍 [EPF Montpellier](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=47486&typeBac=0&originePc=0) — **bac+5 privé**, sélectivité 94% (accessible), 50% de mentions TB.
> *Pour toi : cursus intégré avec stages dès la 1ère année, idéal si tu veux éviter la fac. Budget à prévoir (privé).*
> 
> **Plan C — Licence Maths-Physique Approfondies (Strasbourg) + projets**
> 📍 [Licence MPA-Mag](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=8061&typeBac=0&originePc=0) (Univ. Strasbourg) — **bac+3 public**, sélectivité 42% (39% de mentions B acceptées).
> *Pour toi : moins sélective que Versailles, avec un magistère (recherche appliquée) possible en L3.*
> 
> ---
> **⚠ Attention aux pièges**
> - **EPF/ESILV** : Frais élevés (privé) — vérifie les bourses ou l’alternance en année 3.
> - **Licences sélectives** : Paris-Saclay et Strasbourg privilégient les mentions TB/B. Prépare un dossier solide (notes + projet motivé).
> 
> **Question pour toi** : Tu préfères un cadre **universitaire** (recherche/projets) ou **école d’ingé** (rythme soutenu, stages obligatoires) ? On affine ensemble !

**Sources top-3 sur 10 retournées** :
  1. **Licence - Double diplôme - Licence Mathématiques, Physique et Sciences pour l'In** — Université Paris-Saclay - Campus de Versailles Versailles (niveau bac+5) [score=1.219]
  2. **Licence - Mathématiques - Parcours Mathématiques et physique approfondies - Magi** — Université de Strasbourg Strasbourg (niveau bac+3) [score=1.107]
  3. **Licence - Double diplôme - Licence Mathématiques et informatique appliquées aux ** — Institut d'études politiques de Paris - Sciences P Paris  7e  Arrondissement (niveau bac+3) [score=1.091]

⚠️  **Affirmations flaguées par juge** (4) :
   - sélectivité 27% (73% de mentions TB)
   - EPF Montpellier
   - sélectivité 94% (50% de mentions TB)
   - sélectivité 42% (39% de mentions B acceptées)
   - **Justification juge** : Aucun chiffre de sélectivité ou de taux de mentions n'apparaît dans les 5 fiches sources fournies. De plus, "EPF Montpellier" n'est pas mentionné (seules EPF Paris-Cachan et ESILV figurent) — c'est une hallucination probable. Les fiches Parcoursup ne contiennent typiquement pas ces statistiques déta

---

### Q2 — Je suis en L1 droit et je perds toute motivation, comment me réorienter ?

**Mesures** : t_total=13496ms | filter n_after=30 expansions=0 hit_max=False | faithfulness=0.20 (INFIDELE)

**Q&A Golden top-1** : `A2` iter 0 (score 84, retrieve sim 0.67)
  - Seed : « Je hésite entre éco-gestion, droit et sciences-po, comment choisir ? »

**Réponse Mistral** :

> **TL;DR**
> 1. En L1 droit, une réorientation est tout à fait possible — tu n’es pas coincé.
> 2. **3 chemins concrets** : une licence bidisciplinaire (droit + langues), une licence pro pour un métier précis, ou une année de césure pour clarifier ton projet.
> 3. La clé : agir **dès ce semestre** pour ne pas perdre de temps.
> 
> ---
> 
> ### **Plan A — Réaliste : Double licence Droit/LEA (Anglais/Allemand)**
> 📍 **[Droit-LEA Anglais/Allemand](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=35429&typeBac=0&originePc=0)** — **Université Savoie Mont Blanc (Annecy)** · Bac+3 public, sélectivité modérée (23% en 2025).
> *Pour toi :* Idéal si tu aimes le droit mais veux l’allier à des langues pour des débouchés plus variés (juriste international, institutions européennes). **Admission sur dossier en L2** — contacte le secrétariat pédagogique **dès maintenant** pour un transfert.
> 
> ### **Plan B — Pro : Licence pro ou BUT pour un métier précis**
> Je n’ai pas d’information sur des licences pro **juridiques** dans les sources actuelles, mais c’est une piste solide pour te spécialiser (ex : métiers du notariat, gestion administrative). **À explorer** :
> - **Licences pro** en alternance (ex : "Métiers du droit et de la justice") via les **CFA** (Centres de Formation d’Apprentis) de ta région.
> - **BUT Carrières Juridiques** (ex : IUT de Villetaneuse) — bac+3 pro, accessible en admission parallèle.
> 
> *Pour toi :* Si tu veux **quitter le théorique** pour du concret, avec un diplôme pro en poche.
> 
> ### **Plan C — Pause : Année de césure ou réorientation hors droit**
> - **Césure** : 1 an pour faire un stage, un service civique (ex : dans le social, les institutions), ou travailler. **Calendrier** : déclare ton projet **avant fin mai** à ton université.
> - **Réorientation radicale** : Si le droit ne te plaît plus du tout, explore des **licences en sciences sociales** (socio, science politique) ou des **BUT** (ex : BUT GEA pour la gestion). **Pas de Parcoursup** à ce stade : candidatures directes en L2 via **eCandidat** (plateforme des universités).
> 
> ---
> **⚠ Attention** :
> - En double licence (Plan A), le rythme est **exigeant** (droit + langues) — vérifie que tu es prêt à t’investir.
> - Pour les licences pro/BUT (Plan B), **l’alternance est souvent obligatoire** : trouve une entreprise **avant la rentrée**.
> 
> ---
> **Question pour toi** :
> Qu’est-ce qui te motive le moins dans le droit aujourd’hui ? **Le côté théorique, les débouchés flous, ou l’environnement universitaire** ? Ça aidera à affiner le plan. *(Et n’oublie pas : un RDV avec le **SCUIO** de ta fac peut t’aider à peaufiner ton dossier de réorientation.)*

**Sources top-3 sur 10 retournées** :
  1. **Double licence - Droit / Langues étrangères appliquées - Droit - LEA parcours An** — Université Savoie Mont Blanc - Annecy-le-Vieux Annecy (niveau bac+3) [score=0.979]
  2. **DROIT (MASTER)** — UNIVERSITE DE BRETAGNE SUD  (niveau bac+5) [score=0.817]
  3. **DROIT (MASTER)** — UNIVERSITE DE BRETAGNE SUD  (niveau bac+5) [score=0.817]

⚠️  **Affirmations flaguées par juge** (2) :
   - sélectivité modérée (23% en 2025)
   - déclare ton projet **dès ce semestre** ... **avant fin mai**
   - **Justification juge** : Le chiffre de sélectivité "23% en 2025" est une affirmation factuelle précise qui ne figure dans aucune des 5 fiches données. La date "fin mai" pour déclarer une césure est trop spécifique et varie selon l'établissement — cette affirmation factuelle datée n'est pas sourcée. Seule la double licence D

---

### Q3 — Je suis en prépa MPSI, je suis en burn-out, est-ce que je peux abandonner sans gâcher mon ...

**Mesures** : t_total=10698ms | filter n_after=30 expansions=0 hit_max=False | faithfulness=0.20 (INFIDELE)

**Q&A Golden top-1** : `A1` iter 6 (score 88, retrieve sim 0.75)
  - Seed : « Je suis en terminale spé maths-physique mais je sature des maths abstraites, alternatives concrètes à la prépa MPSI ? »

**Réponse Mistral** :

> **TL;DR**
> Abandonner ta prépa MPSI en cours d’année ne ferme **aucune porte** — mais il faut rebondir sur une formation adaptée à ton profil scientifique. Les fiches disponibles ne couvrent pas les filières post-prépa (écoles d’ingé, licences scientifiques), mais voici des pistes **réalistes** pour éviter une année blanche.
> 
> ---
> 
> ### **Plan A — Réorientation immédiate en licence scientifique**
> Les licences de **maths, physique, ou informatique** (bac+3) acceptent les étudiants de prépa en cours d’année (via **Parcoursup** ou candidatures directes). Exemple : **Licence Informatique** (public, sélectivité modérée, débouchés solides en data/IA).
> *Pour toi* : Capitalise sur tes acquis en maths/physique sans recommencer à zéro.
> 
> ### **Plan B — BUT (Bachelor Universitaire de Technologie)**
> Les **BUT** (ex-DUT) en **informatique, mesures physiques, ou génie industriel** (bac+3) sont accessibles sur dossier, avec des projets concrets dès la 1ère année.
> *Pour toi* : Alternance possible en 2e/3e année pour financer tes études et gagner en expérience.
> 
> ### **Plan C — Pause constructive + rentrée décalée**
> Certaines écoles (ex : **École 42** en informatique) ou licences proposent des **rentrées en janvier/février**. Utilise les 3-6 prochains mois pour :
> - Te former en autodidacte (OpenClassrooms, projets GitHub).
> - Travailler en job étudiant (pour financer une reprise).
> *Pour toi* : Solution si tu as besoin d’un break immédiat.
> 
> ---
> **⚠ Attention** : Les fiches fournies ne détaillent pas ces filières (spécialisées en santé/social). Pour explorer **précisément** les licences/BUT près de chez toi, consulte :
> → [ONISEP officiel (recherche par ville)](https://www.onisep.fr/http/redirection/formation/slug/FOR.10115)
> → Le **SCUIO** (Service Commun Universitaire d’Information et d’Orientation) de ton académie.
> 
> **Question pour toi** :
> Préfères-tu une formation **100% scientifique** (Plan A), **appliquée/projet** (Plan B), ou as-tu besoin d’une **pause** avant de reprendre (Plan C) ? Je peux t’aider à affiner en fonction de ta région ou de tes matières préférées.

**Sources top-3 sur 10 retournées** :
  1. **Psychologie de l’éducation et de la formation (fiche nationale)** — UNIVERSITE AMIENS PICARDIE JULES VERNE  (niveau bac+5) [score=0.862]
  2. **Jouer et mettre en scène** — MINISTERE DE L'ENSEIGNEMENT SUPERIEUR ET DE LA REC  (niveau bac+5) [score=0.855]
  3. **METIERS DE L'ENTREPRENEURIAT (LP)** — SYNDICAT ENSEIGNEMENT AGRIC POUILLE  (niveau bac+3) [score=0.780]

⚠️  **Affirmations flaguées par juge** (2) :
   - Les licences acceptent les étudiants de prépa en cours d'année via Parcoursup
   - Certaines licences proposent des rentrées en janvier/février
   - **Justification juge** : Parcoursup fonctionne sur un cycle annuel unique (candidatures décembre-mars, entrée septembre obligatoire) ; il ne permet pas d'entrée mid-year. De plus, les licences universitaires n'offrent pas de rentrées janvier/février — seules certaines écoles spécialisées (École 42, quelques écoles privées) 

---

### Q4 — Je suis boursière échelon 7, comment trouver un logement étudiant abordable ?

**Mesures** : t_total=9147ms | filter n_after=30 expansions=0 hit_max=False | faithfulness=0.20 (INFIDELE)

**Q&A Golden top-1** : `A2` iter 18 (score 86, retrieve sim 0.67)
  - Seed : « Je hésite entre éco-gestion, droit et sciences-po, comment choisir ? »

**Réponse Mistral** :

> **TL;DR**
> Si je te comprends bien, tu cherches des solutions concrètes pour un logement étudiant **abordable** en tant que boursière échelon 7. Les fiches que j’ai en contexte ne couvrent pas directement les aides au logement, mais elles pointent vers des formations en **aménagement/immobilier** qui pourraient t’aider à identifier des acteurs locaux (CROUS, résidences sociales, associations étudiantes).
> 
> ---
> 
> ### **Plan A — Logements CROUS et résidences sociales**
> 📍 **CROUS de ton académie** : priorité absolue pour les boursiers échelons 5-7. Dossier Social Étudiant (DSE) à remplir **dès maintenant** sur [messervices.etudiant.gouv.fr](https://messervices.etudiant.gouv.fr). Logements entre **200€ et 450€/mois** selon la ville.
> *Pour toi : échéance critique (souvent mai-juin), vérifie les dates sur le site du CROUS de ta future ville d’études.*
> 
> ### **Plan B — Colocations solidaires et associations**
> 📍 **Associations comme le CLLAJ ou AFEV** : proposent des coloc’ à loyers modérés (ex : **300-500€/mois**) pour étudiants boursiers, avec accompagnement social.
> *Pour toi : idéal si tu vises Paris/Lyon/Bordeaux (listes d’attente longues → postule dès que possible).*
> 
> ### **Plan C — Formations en immobilier pour comprendre les aides**
> 📍 **Licence Géographie et Aménagement (Sorbonne)** — [fiche Parcoursup](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=9311&typeBac=0&originePc=0)
> *Pour toi : si tu envisages ce domaine, cette formation aborde les politiques du logement (utile pour décrypter les aides).*
> 
> ---
> **⚠ Attention aux pièges**
> - **Délais** : Les logements CROUS et associations ont des dates limites **strictes** (souvent avant l’été).
> - **Arnaques** : Méfie-toi des offres "trop belles" (loyer < 200€ à Paris = risque d’escroquerie). Passe par des plateformes **labellisées** (Lokaviz, Studapart).
> - **Villes tendues** : À Paris, Lyon ou Bordeaux, prévois un budget **minimum 500€/mois** même avec aides (même en coloc).
> 
> ---
> **Question pour toi** :
> As-tu déjà une ville cible pour tes études ? Je peux t’aider à trouver des contacts locaux (CROUS, associations) **spécifiques à cette ville** si tu me la précises. Sinon, préfères-tu qu’on explore d’abord les aides financières complémentaires (APL, FSL) ?
> 
> ---
> *Pour aller plus loin* :
> - **Site officiel** : [Logement étudiant - gouvernement.fr](https://www.service-public.fr/particuliers/vosdroits/F1986)
> - **Urgent** : Si tu es à la rue ou en risque, contacte le **115** (numéro d’urgence hébergement).

**Sources top-3 sur 10 retournées** :
  1. **Licence - Géographie et aménagement** — Sorbonne université Paris  6e  Arrondissement (niveau bac+3) [score=1.018]
  2. **BTS - Services - Management en hôtellerie restauration** — Lycée Des métiers Jean DROUANT Paris 17e  Arrondissement (niveau bac+2) [score=0.979]
  3. **URBANISME ET AMENAGEMENT — Habitat, Accès au Logement, Ingénierie Sociale.** — Université Le Havre Normandie LE HAVRE CEDEX (niveau bac+5) [score=0.941]

⚠️  **Affirmations flaguées par juge** (2) :
   - Associations comme le CLLAJ ou AFEV : proposent des coloc' à loyers modérés
   - Licence Géographie et Aménagement (Sorbonne) — cette formation aborde les politiques du logement
   - **Justification juge** : L'AFEV (Association de la Fondation Étudiante pour la Ville) est une association de tutorat scolaire et d'accompagnement éducatif, **non une agence de logement**. Mentionner AFEV parmi les solutions de colocation solidaire est factuellement faux. Le Plan C proposant des formations en aménagement com

---

### Q5 — J'ai raté ma PASS, est-ce que je peux quand même faire kiné ou infirmière ?

**Mesures** : t_total=9911ms | filter n_after=30 expansions=0 hit_max=False | faithfulness=0.00 (INFIDELE)

**Q&A Golden top-1** : `A3` iter 0 (score 86, retrieve sim 0.70)
  - Seed : « J'aime les lettres mais tout le monde dit que ça mène à rien, c'est vrai ? »

**Réponse Mistral** :

> **TL;DR**
> 1. Après un échec en PASS, **médecine/kiné en direct sont fermés** (numerus clausus MMOPK).
> 2. **Infirmière reste accessible** via L.AS ou IFSI (dossier Parcoursup, pas de concours).
> 3. **Kinésithérapeute** exige un **redoublement PASS** ou une L.AS avec mineure santé (très sélectif).
> 
> ---
> 
> ### **Plan A — Réaliste : Devenir infirmière·er via IFSI (sans concours)**
> 📍 **Formation en IFSI** (ex : [IFSI de Lille](https://www.chu-lille.fr)) — bac+3 public, **admission sur dossier** (notes lycée + motivation), **pas de numerus clausus**.
> *Pour toi : accessible même après un échec en PASS, avec 100% d’insertion (source : ONISEP).*
> 
> ### **Plan B — Ambitieux : Retenter kiné via L.AS (Licence Accès Santé)**
> 📍 **L.AS Sciences pour la Santé** (ex : [Sorbonne Université](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=28675)) — bac+3 public, **24-28% de réussite** en kiné (vs 6% en PASS).
> *Pour toi : si tu as au moins **12 de moyenne en PASS**, cette voie est plus réaliste qu’un redoublement.*
> 
> ### **Plan C — Alternative : Métiers paramédicaux (sans redoublement)**
> 📍 **DEAES (Accompagnant Éducatif et Social)** ou **BTS Diététique** — bac+2/3, **admission sur dossier**, débouchés en 6-12 mois.
> *Pour toi : si tu veux un métier du soin **rapidement**, sans repasser par la case santé.*
> 
> ---
> **⚠ Attention** : Les écoles privées "prépa kiné" ou "PASS bis" coûtent **5 000-10 000€/an** pour des taux de réussite non garantis (marketing agressif).
> 
> **Question pour toi** : Préfères-tu **rebondir vite** (infirmière/paramédical) ou **retenter ta chance** en kiné via L.AS (avec risque d’échec) ? 👤 Pour affiner, un RDV avec le SCUIO de ta fac ou un CIO est indispensable.

**Sources top-3 sur 10 retournées** :
  1. **Licence - Parcours d'Accès Spécifique Santé (PASS)** — Université de Lille Lille (niveau bac+3) [score=1.123]
  2. **Licence - Parcours d'Accès Spécifique Santé (PASS)** — Université de Lille Lille (niveau bac+3) [score=1.123]
  3. **Licence - Parcours d'Accès Spécifique Santé (PASS)** — Sorbonne université Paris  6e  Arrondissement (niveau bac+3) [score=1.112]

⚠️  **Affirmations flaguées par juge** (8) :
   - 100% d'insertion (source : ONISEP)
   - 24-28% de réussite en kiné
   - 6% en PASS
   - IFSI de Lille
   - L.AS Sciences pour la Santé Sorbonne Université code 28675
   - ... (3 autres)
   - **Justification juge** : Les 5 fiches sources fournies ne couvrent que des PASS. La réponse développe des formations entièrement absentes des sources (IFSI, L.AS distinct, DEAES, BTS) et cite des chiffres précis (100%, 24-28%, 6%) sans source vérifiable. La réponse dépasse largement le périmètre couvert par les fiches dispo

---

### Q6 — Quelles formations en cybersécurité à Toulouse niveau bachelor ?

**Mesures** : t_total=8877ms | filter n_after=30 expansions=0 hit_max=False | faithfulness=0.00 (INFIDELE)

**Q&A Golden top-1** : `A1` iter 3 (score 84, retrieve sim 0.77)
  - Seed : « Quelles sont les meilleures formations en cybersécurité en France ? »

**Réponse Mistral** :

> **TL;DR**
> Vous cherchez des formations en cybersécurité **niveau bachelor à Toulouse** ? Voici 3 options adaptées, avec des profils d’admission variés (bac général, techno ou pro).
> 
> ---
> 
> ### **Plan A — BTS Cybersécurité (Lycée Déodat de Séverac, Toulouse)**
> 📍 **BTS Cybersécurité, Informatique et Réseaux** ([Toulouse](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=4060&typeBac=0&originePc=0)) — bac+2 public, sélectivité **28%** (723 vœux pour 24 places).
> *Pour vous : accessible aux bacs techno/pro (65% des admis), avec 47% de boursiers. Poursuite possible en licence pro ou école d’ingé après.*
> 
> ### **Plan B — Bachelor Cybersécurité (EFREI Bordeaux)**
> 📍 **Bachelor Cybersécurité et Ethical Hacking** ([Bordeaux](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=36041&typeBac=0&originePc=0)) — bac+3 privé (labels **SecNumEdu/CTI**), sélectivité **77%** (36 places).
> *Pour vous : plus technique et labellisé, mais à 2h de Toulouse. Exige un bon dossier (71% de bacs généraux).*
> 
> ### **Plan C — BUT Réseaux & Télécoms (parcours cybersécurité)**
> 📍 **BUT Réseaux et Télécommunications** ([ONISEP](https://www.onisep.fr/http/redirection/formation/slug/FOR.8012)) — bac+3 public, label **SecNumEdu**.
> *Pour vous : alternative en 3 ans avec stages, à chercher dans d’autres villes (ex : Montauban à 1h de Toulouse).*
> 
> ---
> **Question pour vous :**
> Préférez-vous une formation **courte et professionnelle (BTS)**, **longue et labellisée (bachelor)**, ou **un compromis public en 3 ans (BUT)** ? Je peux préciser les modalités d’admission pour l’option qui vous intéresse.
> 
> *(Note : Aucune formation bac+3 en cybersécurité n’est listée à Toulouse même dans les sources officielles 2026. Les options B et C impliquent une mobilité géographique.)*

**Sources top-3 sur 10 retournées** :
  1. **Formation Bac + 3 - Bachelor Cybersécurité et Ethical Hacking** — EFREI Bordeaux Bordeaux (niveau bac+3) [score=2.006]
  2. **bachelor numérique option cybersécurité** —   (niveau bac+3) [score=1.176]
  3. **BUT réseaux et télécommunications parcours cybersécurité** —   (niveau bac+3) [score=1.172]

⚠️  **Affirmations flaguées par juge** (7) :
   - sélectivité 28% (723 vœux pour 24 places)
   - 65% des admis
   - 47% de boursiers
   - labels SecNumEdu/CTI
   - sélectivité 77% (36 places)
   - ... (2 autres)
   - **Justification juge** : Multiples affirmations factuelles précises (taux d'admission détaillés, pourcentages de composition, labels de certification) sont énoncées sans source dans les fiches fournies. Bien que plausibles (SecNumEdu/CTI sont des labels réels, ces chiffres ressemblent à des données Parcoursup), elles dépass

---

### Q7 — Master de droit des affaires, quels débouchés concrets en France ?

**Mesures** : t_total=8778ms | filter n_after=30 expansions=0 hit_max=False | faithfulness=0.00 (INFIDELE)

**Q&A Golden top-1** : `A2` iter 14 (score 86, retrieve sim 0.69)
  - Seed : « Pour un profil SES-HG, quel master pro paie mieux à 5 ans : droit ou éco ? »

**Réponse Mistral** :

> **TL;DR**
> Vous explorez les débouchés concrets d’un **master en droit des affaires** en France. Ces formations (bac+5 public) mènent principalement à des postes de **juriste d’affaires**, avec des spécialisations variées (international, banque, distribution). Voici 3 pistes pour cibler votre projet.
> 
> ---
> 
> ### **Plan A — Juriste d’affaires en entreprise**
> 📍 **Master Droit des affaires internationales** (Paris-Panthéon-Assas, Paris) — bac+5 public, spécialisation en contrats internationaux et compliance.
> *Pour vous : idéal si vous visez les grands groupes, cabinets d’avocats, ou institutions financières (banque/assurance).*
> 
> ### **Plan B — Spécialisation sectorielle (banque, distribution, patrimoine)**
> 📍 **Master Droit des affaires : Banque, patrimoine, assurance** (Université Bourgogne, Dijon) — bac+5 public, axé sur les enjeux juridiques des secteurs réglementés.
> *Pour vous : débouchés ciblés dans les banques, assurances, ou gestion de patrimoine, avec des postes comme juriste conformité ou conseiller en protection des données.*
> 
> ### **Plan C — Carrières internationales ou européennes**
> 📍 **Master European and International Business Law** (Université Savoie Mont Blanc, Chambéry) — bac+5 public, enseignement en anglais, focus sur le droit des affaires UE et commerce international.
> *Pour vous : pour travailler dans des entreprises multinationnelles, institutions européennes, ou cabinets avec une dimension transfrontalière.*
> 
> ---
> **⚠ Attention aux pièges**
> - **Sélectivité variable** : Certains masters (ex : Paris-Panthéon-Assas) sont très demandés — dossier solide requis (notes + stages).
> - **Anglais indispensable** pour les parcours internationaux (ex : Chambéry) — niveau C1 souvent exigé.
> - **Réseau professionnel crucial** : Les débouchés dépendent fortement des stages et du networking pendant le master.
> 
> **Question pour vous** : Préférez-vous un poste en **entreprise** (juriste interne), en **cabinet d’avocats**, ou dans le **secteur public/international** (institutions, ONG) ? Cela peut affiner le choix de spécialisation.

**Sources top-3 sur 10 retournées** :
  1. **DROIT DES AFFAIRES — Juriste d'affaires internationales** — Université Bourgogne Europe DIJON (niveau bac+5) [score=0.990]
  2. **DROIT DES AFFAIRES — Juriste d'affaires-commerce-distribution-consommation** — Université Bourgogne Europe DIJON (niveau bac+5) [score=0.984]
  3. **DROIT DES AFFAIRES — Juriste d'affaires européen** — Université Paris Cité MALAKOFF (niveau bac+5) [score=0.984]

⚠️  **Affirmations flaguées par juge** (4) :
   - Master Droit des affaires internationales (Paris-Panthéon-Assas, Paris)
   - Master European and International Business Law (Université Savoie Mont Blanc, Chambéry)
   - enseignement en anglais, focus sur le droit des affaires UE
   - niveau C1 souvent exigé
   - **Justification juge** : Le RAG hallucine deux formations absentes des sources fournies (Paris-Panthéon-Assas et Savoie Mont Blanc), puis invente des détails (anglais, C1) non mentionnés en fiche. Seul Plan B (Bourgogne) correspond aux sources réelles. L'université Paris-Panthéon-Assas n'apparaît pas dans les 5 fiches ; la 

---

### Q8 — Je travaille dans le tertiaire depuis 5 ans, je veux me reconvertir paramédical après un b...

**Mesures** : t_total=14987ms | filter n_after=30 expansions=0 hit_max=False | faithfulness=0.35 (INFIDELE)

**Q&A Golden top-1** : `A2` iter 0 (score 84, retrieve sim 0.71)
  - Seed : « Je hésite entre éco-gestion, droit et sciences-po, comment choisir ? »

**Réponse Mistral** :

> **TL;DR**
> Vous souhaitez une reconversion dans le paramédical après 5 ans dans le tertiaire : c’est un projet exigeant mais structurant. **Priorité absolue** : valider votre motivation via des immersions (stages, bénévolat) avant de choisir une formation. Voici 3 pistes **réalistes pour adultes**, avec des parcours adaptés à votre expérience.
> 
> ---
> 
> ### **Plan A — Accès rapide : Diplôme d’État d’Accompagnant Éducatif et Social (DEAES)**
> 📍 **Formation DEAES** (ex-DEAMP/DEAVS) — Niveau bac (sans prérequis), **accessible en 1 an** (formation accélérée pour adultes), **finançable via CPF/VAP**. Débouchés : EHPAD, handicap, inclusion scolaire.
> *Pour vous : Idéal pour tester le terrain paramédical sans engagement long, avec une reconnaissance officielle (diplôme d’État).*
> 
> ### **Plan B — Spécialisation : Conseiller en transition professionnelle (secteur social/paramédical)**
> 📍 **Certificat RNCP "Conseiller emploi et accompagnement"** — bac+2, **100% en ligne** (OpenClassrooms), éligible CPF. Débouchés : accompagnement de publics fragiles (insertion, santé).
> *Pour vous : Passerelle vers des métiers d’interface (ex : coordinateur en SSR), en capitalisant sur votre expérience tertiaire.*
> 
> ### **Plan C — Réorientation longue : Kinésithérapie (si motivation confirmée)**
> 📍 **Diplôme d’État de Masseur-Kinésithérapeute** — bac+5, **accès via VAP** (Validation des Acquis Professionnels) pour les >26 ans, ou **L.AS/PASS** si reprise d’études. Sélectif (concours).
> *Pour vous : Seulement si vous êtes prêt·e à un investissement long (5 ans) et à des stages hospitaliers. Pensez à valider via un **stage d’observation** avant.*
> 
> ---
> **⚠ Attention aux pièges**
> - **DEAES** : Salaire modeste (SMIC à 1 700€ net en début de carrière — source : conventions collectives 2026).
> - **Kinésithérapie** : La VAP est **très rare** en IFMK (instituts de formation) — privilégiez d’abord une année de mise à niveau (ex : DU de remédiation scientifique).
> - **Formations privées** : Méfiez-vous des écoles non reconnues par l’État (ex : "kiné en 3 ans") — vérifiez systématiquement le **RNCP** ou le diplôme d’État.
> 
> ---
> **Question pour vous** :
> Avez-vous déjà identifié un **domaine précis** du paramédical qui vous attire (rééducation, accompagnement du handicap, soins de base) ? Cela aidera à affiner entre DEAES (rapide) ou une spécialisation plus technique. *(Un bilan de compétences via votre OPCO peut aussi clarifier ce choix.)*
> 
> ---
> 👤 **Pour aller plus loin** :
> - **Immersion** : Contactez des **plateformes comme [Viavoi](https://www.viavoi.fr/)** pour des stages d’observation en EHPAD ou cabinets de kiné.
> - **Financement** : Votre **CPF** (Compte Personnel de Formation) peut couvrir jusqu’à 100% des certifications RNCP (ex : DEAES).
> - **Conseil humain** : Un **conseiller en Évolution Professionnelle (CEP)** de Pôle Emploi ou de votre OPCO peut monter un dossier VAP avec vous.

**Sources top-3 sur 10 retournées** :
  1. **MASSEUR-KINESITHERAPEUTE (DIPLOME D'ETAT)** — INSTITUT PARAMEDICAL DES METIERS DE LA REEDUCATION  (niveau bac+5) [score=0.939]
  2. **Carrières sociales : Villes et territoires durables** — MINISTERE DE L'ENSEIGNEMENT SUPERIEUR ET DE LA REC  (niveau bac+3) [score=0.858]
  3. **Carrières Sociales : Villes et territoires durables** — UNIVERSITE DE BORDEAUX  (niveau bac+3) [score=0.853]

⚠️  **Affirmations flaguées par juge** (1) :
   - Salaire modeste (SMIC à 1 700€ net en début de carrière)
   - **Justification juge** : 1. **Salaire DEAES erroné** : L'affirmation "SMIC à 1 700€ net" est factuellement fausse. Le SMIC 2026 est ~1 750€ **brut**, soit environ 1 320-1 370€ **net**. Confusion brut/net grave.
2. **VAP kinésithérapie trompeuse** : La réponse présente VAP comme option viable dans le Plan C ("accès via VAP")

---

### Q9 — Mon fils veut faire un apprentissage en plomberie mais nous voulions qu'il fasse une école...

**Mesures** : t_total=9888ms | filter n_after=30 expansions=0 hit_max=False | faithfulness=0.05 (INFIDELE)

**Q&A Golden top-1** : `A1` iter 19 (score 86, retrieve sim 0.71)
  - Seed : « Quelles écoles d'ingénieur post-bac valent le coup vs prépa ? »

**Réponse Mistral** :

> **TL;DR**
> Votre fils a deux voies complémentaires : un CAP/Bac Pro en plomberie (métier concret, insertion rapide) **ou** une école d’ingénieur en alternance (accès possible sans prépa, avec spécialités techniques). L’idéal ? Lui faire explorer les deux pour qu’il choisisse en conscience.
> 
> ---
> 
> ### **Plan A — Réaliste : CAP/Bac Pro Plomberie en alternance**
> 📍 **CAP Plombier chauffagiste** (France entière) — Niveau CAP, formation en 2 ans avec contrat d’apprentissage, diplôme d’État.
> *Pour lui : accès direct au métier, salaire dès la 1ère année, débouchés assurés (besoins forts en main-d’œuvre qualifiée).*
> 
> ### **Plan B — Ambitieux : École d’ingénieur en alternance**
> 📍 **Diplôme d’ingénieur ECAM Lyon** (Lyon) — bac+5, spécialité Génie Industriel ou Énergétique, accessible en alternance après un Bac S/STI2D.
> *Pour lui : si la théorie l’attire, il peut viser un BUT Génie Mécanique d’abord, puis intégrer une école d’ingé en alternance (ex : ECAM, INSA).*
> 
> ### **Plan C — Passerelle : Technicien supérieur avant ingé**
> 📍 **BTS Fluides-Énergies-Environnements** (existe dans toute la France) — bac+2, formation pro avec stages, puis poursuite en licence pro ou école d’ingé.
> *Pour lui : compromis entre pratique et théorie, avec porte de sortie à bac+2 si le projet évolue.*
> 
> ---
> **⚠ Attention aux pièges**
> - **Alternance ingé** : très sélective (dossier + entretien), souvent réservée aux bacs généraux/technos avec bonnes notes en sciences.
> - **CAP/Bac Pro** : certains parents craignent un "plafond de verre", mais les meilleurs artisans gagnent très bien leur vie (et montent leur entreprise).
> 
> ---
> **Question pour vous** :
> Avez-vous déjà discuté avec lui de ce qui l’attire le plus : **le concret immédiat** (CAP/plomberie) ou **la théorie avec un projet long terme** (ingénieur) ? Un stage d’observation dans les deux milieux pourrait l’aider à trancher.
> 
> ---
> 👤 *Pour aller plus loin, un entretien avec un conseiller en évolution professionnelle (CEP) ou le Psy-EN de son lycée peut éclairer son choix. Les chambres de métiers organisent aussi des portes ouvertes pour découvrir l’artisanat.*

**Sources top-3 sur 10 retournées** :
  1. **INGENIEUR DIPLOME DE L'ECOLE CATHOLIQUE D'ARTS ET METIERS DE LA FONDATION ECAM, ** — ASSOCIATION CENTRE DE FORMATION D APPRENTIS DE L I  (niveau bac+5) [score=0.933]
  2. **INGENIEUR DIPLOME DE L'INSTITUT NATIONAL DES SCIENCES APPLIQUEES DE LYON, SPECIA** — ASSOCIATION CENTRE DE FORMATION D APPRENTIS DE L I  (niveau bac+5) [score=0.932]
  3. **INGENIEUR DIPLOME DE L'ECOLE CATHOLIQUE D'ARTS ET METIERS DE LA FONDATION ECAM, ** — ASSOCIATION CENTRE DE FORMATION D APPRENTIS DE L I  (niveau bac+5) [score=0.931]

⚠️  **Affirmations flaguées par juge** (3) :
   - accessible en alternance après un Bac S/STI2D
   - BUT Génie Mécanique d'abord, puis intégrer une école d'ingé en alternance
   - BTS Fluides-Énergies-Environnements
   - **Justification juge** : L'affirmation clé "diplôme bac+5 accessible en alternance après un Bac S/STI2D" est factuellement fausse. Un ingénieur bac+5 ne s'accède pas directement post-bac : il faut d'abord passer par BTS/BUT (2 ans) ou prépa (2 ans), PUIS intégrer l'école en alternance. Les sources valident ECAM/INSA et leur

---

### Q10 — Je suis en terminale L et tout le monde me dit que ça ne mène à rien, est-ce vrai ?

**Mesures** : t_total=9962ms | filter n_after=30 expansions=0 hit_max=False | faithfulness=0.00 (INFIDELE)

**Q&A Golden top-1** : `A3` iter 0 (score 86, retrieve sim 0.81)
  - Seed : « J'aime les lettres mais tout le monde dit que ça mène à rien, c'est vrai ? »

**Réponse Mistral** :

> **TL;DR**
> Si je te comprends bien, tu t’inquiètes pour ton avenir après une terminale L. Rassure-toi : les langues et les lettres ouvrent des portes, mais il faut bien choisir sa voie. Voici 3 pistes concrètes avec des débouchés réels, pas des clichés.
> 
> ---
> 
> ### **Plan A — Réaliste : Licence LEA (Langues Étrangères Appliquées)**
> 📍 **LEA (2 langues hors anglais) — Sorbonne Université (Paris)** — bac+3 public, sélectivité 42%, 45 places en 2025.
> *Pour toi : accessible avec une mention AB/B (41% des admis), et débouche sur des métiers concrets (communication, commerce international, traduction).*
> **Salaire médian après 1 an** : 1 790€ net/mois (source : InserSup DEPP 2024).
> 
> ### **Plan B — Ambitieux : Double compétence langues + droit/éco**
> 📍 **Licence LEA — Université Lyon 2** — bac+3 public, moins sélective qu’à Paris.
> *Pour toi : combine langues avec une mineure en droit ou économie pour élargir tes options (ex : métiers de l’UE, diplomatie).*
> 
> ### **Plan C — Alternatif : Certifications pro en médiation/enseignement**
> 📍 **Certificat RNCP "Langues, enseignement, médiation"** — formations courtes (bac+3) axées métiers (prof de langues, médiation culturelle).
> *Pour toi : si tu veux un diplôme rapide et professionnel, sans passer par 5 ans d’études.*
> 
> ---
> **⚠ Attention aux pièges**
> - **LEA à Paris est très demandée** (+238% de vœux depuis 2023) : prépare un dossier solide (notes + projet motivé).
> - **Les licences générales (lettres pures) ont un taux d’emploi plus faible** (44% à 1 an pour LEA vs ~60% pour les filières pro). Pense à un master ou une spécialisation après.
> 
> ---
> **Question pour toi** : Est-ce que tu préfères un parcours **universitaire long** (LEA/master) pour garder des options ouvertes, ou une formation **pro courte** (certificat RNCP) pour entrer vite dans la vie active ? 👤 *Pour affiner, un RDV avec le Psy-EN de ton lycée peut t’aider à creuser tes envies.*

**Sources top-3 sur 10 retournées** :
  1. **Licence - Langues étrangères appliquées - Parcours LEA (Langues Etrangères Appli** — Sorbonne université Paris  6e  Arrondissement (niveau bac+3) [score=1.072]
  2. **LANGUES ETRANGERES APPLIQUEES (MASTER)** — UNIVERSITE LUMIERE LYON 2  (niveau bac+5) [score=0.888]
  3. **LANGUES ETRANGERES APPLIQUEES (LIC LMD)** — UNIVERSITE LUMIERE LYON 2  (niveau bac+3) [score=0.820]

⚠️  **Affirmations flaguées par juge** (6) :
   - sélectivité 42%, 45 places en 2025
   - 41% des admis avec mention AB/B
   - Salaire médian après 1 an : 1 790€
   - +238% de vœux depuis 2023
   - taux d'emploi 44% à 1 an pour LEA vs ~60%
   - ... (1 autres)
   - **Justification juge** : La réponse accumule 6+ affirmations factuelles très précises (sélectivité %, taux d'emploi %, augmentation de vœux, salaires) absentes des fiches sources ET non vérifiables. Le certificat RNCP nommé n'existe pas dans le corpus (fiches 4-5 sont "Études eur./int." et "Métiers de la forme"). Ces chiffr

---


*Doc généré par `scripts/test_serving_e2e.py` sous l'ordre `2026-04-29-1146-claudette-orientia-sprint10-finalisation-rag-complet` (chantier E mesures empiriques).*