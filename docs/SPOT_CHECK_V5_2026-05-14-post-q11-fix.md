# Spot-check Gate 3 v5 — 2026-05-13

> Phase C.5 (BLOQUANT pour promotion v5). 13 questions ciblées sur
> les domaines précédemment dormants. Évaluation manuelle requise.

## Résumé exécutif

- **Questions testées** : 13
- **Questions avec domain attendu présent dans top-5** : 9/13
- **Erreurs runtime** : 0
- **Corpus** : `data/processed/formations_v5.json`
- **Index** : `data/embeddings/formations_v5.index`

## Critère pass (manuel)

Pour chaque question, vérifier :
1. La réponse n'est pas "info non disponible" (sauf si vraiment data absente)
2. Les chiffres cités sont accompagnés de `[source SX]` (R3)
3. Le top-K retrieve contient au moins 1 fiche du domain attendu
4. Pas d'invention de fiche / établissement / chiffre absent du corpus (R1, R2)

## Détails par question

### Q1 — Quels métiers vont recruter en Occitanie en 2030 ?

**Domain attendu** : `metier_prospective` (DARES Métiers 2030 — projections recrutement par région)

**Top-5 domain match** : ✓ 5/5 fiches du domain attendu
**Citations [source SX]** : 3
**Latence** : 78.37s

**Top-5 sources retrievées** :
```
  S1: [metier_prospective] dares_region:occitanie, Occitanie [score=0.797]
  S2: [metier_prospective] Ouvriers qualifiés travaillant par enlèvement de métal, Occitanie [score=0.784]
  S3: [metier_prospective] Marins, pêcheurs, aquaculteurs, Occitanie [score=0.770]
  S4: [metier_prospective] Infirmiers, sages-femmes, Occitanie [score=0.771]
  S5: [metier_prospective] Ingénieurs et cadres techniques de l'industrie, Occitanie [score=0.782]
```

**Réponse du pipeline** :

```
En Occitanie, plusieurs métiers devraient offrir des opportunités de recrutement d’ici 2030, avec des besoins variables selon les secteurs.

- **Santé** : Les [infirmiers et sages-femmes](https://candidat.onisep.fr) seront très recherchés, avec **27 588 postes à pourvoir** (créations nettes + départs) [source S4]. Un métier en tension moyenne mais avec une forte demande structurelle.
- **Industrie** : Les **ingénieurs et cadres techniques de l’industrie** auront **17 233 postes à pourvoir**, dont **10 235 créations nettes** [source S5], reflétant une dynamique industrielle régionale.
- **Métiers manuels** : Les **ouvriers qualifiés en enlèvement de métal** (usinage, mécanique) afficheront **1 585 postes**, malgré un léger déclin net (-37 postes), en raison des départs en retraite [source S2].

*Ces projections concernent les remplacements et créations de postes. Quel secteur t’intéresse le plus pour creuser les formations associées ?*
```

---

### Q2 — Combien coûte le logement étudiant CROUS à Lyon ?

**Domain attendu** : `crous` (CROUS corpus — résidences U et restos par zone)

**Top-5 domain match** : ✓ 5/5 fiches du domain attendu
**Citations [source SX]** : 1
**Latence** : 22.7s

**Top-5 sources retrievées** :
```
  S1: [crous] crous_region:lyon [score=1.055]
  S2: [crous] crous_region:bordeaux [score=0.999]
  S3: [crous] crous_region:corte [score=0.974]
  S4: [crous] crous:france [score=1.024]
  S5: [crous] crous_region:amiens [score=1.012]
```

**Réponse du pipeline** :

```
D’après mes sources, **les frais annuels pour un logement étudiant CROUS à Lyon ne sont pas précisés** [source S1].

En revanche, voici ce que je peux te dire sur l’offre CROUS lyonnaise :
- **9 résidences universitaires** réparties dans la région (Lyon, Saint-Étienne, Villeurbanne).
- **36 restaurants/cafétérias** pour les repas étudiants.

Pour connaître les tarifs exacts des logements, je te conseille de consulter directement le site du [CROUS Lyon](https://www.crous-lyon.fr) ou de contacter leur service logement.

Tu cherches un studio, une colocation ou une chambre en cité U ?
```

---

### Q3 — Quels sont les blocs de compétences du RNCP 38450 ?

**Domain attendu** : `competences_certif` (France Compétences blocs RNCP)

**Top-5 domain match** : ✓ 5/5 fiches du domain attendu
**Citations [source SX]** : 2
**Latence** : 8.46s

**Top-5 sources retrievées** :
```
  S1: [competences_certif] rncp_blocs:RNCP38997 [score=1.321]
  S2: [competences_certif] rncp_blocs:RNCP38345 [score=1.313]
  S3: [competences_certif] rncp_blocs:RNCP38156 [score=1.314]
  S4: [competences_certif] rncp_blocs:RNCP38477 [score=1.313]
  S5: [competences_certif] rncp_blocs:RNCP38961 [score=1.312]
```

**Réponse du pipeline** :

```
Je n’ai pas d’information sur le **RNCP 38450** dans mes sources.

Les blocs de compétences RNCP que je peux documenter concernent d’autres certifications bac+5, comme :
- **Réseaux et télécommunication** (RNCP38997) [source S1]
- **Expert en numérisation industrielle** (RNCP38477) [source S4]

Pour le RNCP 38450, je te conseille de consulter directement le [répertoire national des certifications professionnelles](https://www.francecompetences.fr/) ou de contacter un conseiller en évolution professionnelle (CEP).

Quel domaine te intéresse plus précisément dans cette certification ?
```

---

### Q4 — Quel salaire après un Master Droit en région PACA ?

**Domain attendu** : `insertion_pro` (InserSup spécifique discipline × région)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 3
**Latence** : 18.13s

**Top-5 sources retrievées** :
```
  S1: [insee_salaire] insee_salaan:cs:48 [score=0.015]
  S2: [insee_salaire] insee_salaan:cs:31 [score=0.015]
  S3: [metier] juriste en propriété intellectuelle [score=0.014]
  S4: [metier] juriste en droit social [score=0.013]
  S5: [metier] avocat / avocate [score=0.012]
```

**Réponse du pipeline** :

```
Je n’ai pas de données sur les salaires **spécifiques aux diplômés d’un Master Droit en région PACA** dans mes sources.

En revanche, voici des repères nationaux pour des métiers accessibles après un Master Droit :
- **[Juriste en propriété intellectuelle](https://www.onisep.fr/http/redirection/metier/slug/MET.33)** : métier centré sur les brevets, contrats industriels et droits d’auteur [source S3].
- **[Avocat·e](https://www.onisep.fr/http/redirection/metier/slug/MET.33)** : défense et conseil juridique, avec des salaires variables selon la spécialisation [source S5].
- **Professions libérales salariées** (ex : collaborateur juridique) : salaire net médian annuel de **27 000 €** (2 250 €/mois) [source S2].

Pour des chiffres régionaux précis, je te conseille de consulter les enquêtes d’insertion des universités PACA (ex : Aix-Marseille) ou l’[Observatoire des métiers du droit](https://www.defenseurdesdroits.fr/).

Quel domaine du droit t’intéresse le plus ?
```

---

### Q5 — Que fait un actuaire au quotidien ?

**Domain attendu** : `metier_detail` (ROME 4.0 fiches métiers — compétences détaillées)

**Top-5 domain match** : ✓ 2/5 fiches du domain attendu
**Citations [source SX]** : 4
**Latence** : 9.31s

**Top-5 sources retrievées** :
```
  S1: [metier_detail] Actuaire [score=0.023]
  S2: [metier] actuaire [score=0.021]
  S3: [metier_detail] Conseiller / Conseillère en assurances [score=0.021]
  S4: [metier] actuaire [score=0.021]
  S5: [metier] gestionnaire actif/passif [score=0.020]
```

**Réponse du pipeline** :

```
Un·e **actuaire** analyse les risques financiers pour aider les entreprises (assurances, banques) à prendre des décisions éclairées. Voici ses missions clés :

- **Modéliser et tarifier** : utiliser des statistiques et algorithmes pour définir les prix des contrats d’assurance ou d’épargne, et intégrer de nouveaux produits [source S1].
- **Veille stratégique** : surveiller les marchés et la concurrence pour anticiper les évolutions, tout en optimisant les performances de l’entreprise [source S1].
- **Conseiller la direction** : fournir des outils de prévision (ex : risques de sinistres, opportunités financières) pour guider les choix stratégiques [source S2].

Son expertise combine **mathématiques appliquées**, **droit des assurances** et **analyse économique** [source S4].

Tu envisages ce métier pour son côté technique, son impact business, ou autre ? 😊
```

---

### Q6 — Quelles aides financières pour les étudiants boursiers ?

**Domain attendu** : `financement_etudes` (Financement curated dispositifs)

**Top-5 domain match** : ✓ 5/5 fiches du domain attendu
**Citations [source SX]** : 3
**Latence** : 7.13s

**Top-5 sources retrievées** :
```
  S1: [financement_etudes] financement_voie:initial [score=0.765]
  S2: [financement_etudes] Aides au logement (APL, ALF, ALS) — étudiants [score=0.726]
  S3: [financement_etudes] Bourse sur critères sociaux CROUS — enseignement supérieur [score=0.734]
  S4: [financement_etudes] Bourse de lycée (collégiens et lycéens) [score=0.726]
  S5: [financement_etudes] Aide à la première installation (CROUS) [score=0.720]
```

**Réponse du pipeline** :

```
Pour financer tes études en tant qu’étudiant·e boursier·ère, voici les principales aides disponibles selon mes sources :

- **Bourse sur critères sociaux CROUS** : destinée aux étudiant·es post-bac (BTS, BUT, Licence, Master, etc.), avec des montants annuels variant entre **1080 € et 5965 €** (2024-2025) selon les revenus du foyer [source S3].
- **Aides au logement (APL/ALF/ALS)** : gérées par la CAF, elles couvrent une partie du loyer (montant variable selon ta situation et la zone géographique) [source S2].
- **Aide à la première installation** : proposée par le CROUS pour les étudiant·es éligibles aux logements CROUS, incluant des dispositifs comme Visale ou Loca-Pass pour le dépôt de garantie [source S5].

Tu peux cumuler plusieurs aides. Laquelle te semble la plus adaptée à ta situation actuelle ?

---
⚠️ **Points à vérifier dans ma réponse** :
- Mention manquante : interdit de redoublement PASS (arrêté 2019) — La réponse parle de PASS mais ne précise pas que le redoublement est interdit (arrêté du 4 novembre 2019). C'est une information obligatoire pour un lycéen en autonomie.

Ces points sont des patterns que nous surveillons. Vérifie directement sur [ONISEP](https://www.onisep.fr) ou [Parcoursup](https://www.parcoursup.fr) avant toute décision.
```

---

### Q7 — Quelles formations en Guadeloupe ?

**Domain attendu** : `territoire_drom` (DROM-COM territoires)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 9
**Latence** : 57.2s

**Top-5 sources retrievées** :
```
  S1: [(formation)] Licence - Portail Sciences de la vie et de la terre - Biologie des organismes et Ecologie  / Biologie générale et sciences de la terre et de l’univers / Géo-sciences, géo-risques, géo-environnements — Université des Antilles - Pôle Guadeloupe, Guadeloupe [score=1.080]
  S2: [(formation)] Licence - Portail Sciences et Techniques des Activités Physiques et Sportives - Activités physiques adaptées et santé (APAS) — Université des Antilles - Pôle Guadeloupe, Guadeloupe [score=1.069]
  S3: [(formation)] BUT - Gestion des entreprises et des administrations — I.U.T de la Guadeloupe - Campus de St-Claude, Guadeloupe [score=1.059]
  S4: [(formation)] Licence - Portail Economie et gestion - Eco de l'environnement et aménagement du territoire/Expertise éco,financière et managériale/Préparation aux métiers de l'enseignement - Guadeloupe — Université des Antilles - Pôle Guadeloupe, Guadeloupe [score=1.077]
  S5: [(formation)] Licence - Portail Mathématiques - Mathématiques appliquées aux sciences / Mathématiques pour l'enseignement  - Guadeloupe — Université des Antilles - Pôle Guadeloupe, Guadeloupe [score=1.071]
```

**Réponse du pipeline** :

```
En Guadeloupe, voici les formations post-bac disponibles dans mes sources, toutes **publiques** et accessibles via Parcoursup :

- **Sciences et santé** :
  - [Licence Sciences de la vie et de la terre](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=11749&typeBac=0&originePc=0) (biologie, écologie, géosciences) à l’**Université des Antilles** (Pointe-à-Pitre) : **100 places** [source S1], **100 % d’accès** en 2025 [source S1].
  - [Licence STAPS - APAS](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=36152&typeBac=0&originePc=0) (sport-santé) : **50 places** [source S2], **50 % d’accès** [source S2].

- **Économie et gestion** :
  - [BUT GEA](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=11768&typeBac=0&originePc=0) (gestion d’entreprise) à l’**IUT de Saint-Claude** : **70 places** [source S3], **63 % d’accès** [source S3].
  - [Licence Économie-Gestion](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=39484&typeBac=0&originePc=0) (3 parcours dont environnement/enseignement) : **250 places** [source S4], **100 % d’accès** [source S4].

- **Mathématiques** :
  - [Licence Maths](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=36146&typeBac=0&originePc=0) (appliquées ou enseignement) : **15 places** [source S5].

*Quelle voie correspond le mieux à ton projet ou tes centres d’intérêt ?*
```

---

### Q8 — Marché de l'emploi cadres en Bretagne ?

**Domain attendu** : `apec_region` (APEC régions)

**Top-5 domain match** : ✓ 1/5 fiches du domain attendu
**Citations [source SX]** : 2
**Latence** : 6.41s

**Top-5 sources retrievées** :
```
  S1: [apec_region] apec_region:bretagne, Bretagne [score=0.738]
```

**Réponse du pipeline** :

```
Le marché de l’emploi cadre en Bretagne montre une dynamique positive en 2025, à contre-courant des tendances nationales.

- **Recrutements 2025** : 9 990 postes (+5 % vs 2024), avec une prévision 2026 à 10 200 (+2 %), ce qui permettrait de retrouver le niveau record de 2023 (10 290) [source S1].
- **Créations nettes 2025** : 2 910 postes (contre 3 230 en 2024), avec des besoins forts dans les fonctions *Exploitation tertiaire* (21 %), *Commercial-marketing* (16 %), *Études-R&D* (15 %), *Informatique* (14 %) et *Production* [source S1].

Ces chiffres reflètent-ils un secteur ou une fonction qui t’intéresse en particulier ?
```

---

### Q9 — Salaire moyen d'un cadre supérieur (PCS 37) ?

**Domain attendu** : `insee_salaire` (INSEE salaires PCS)

**Top-5 domain match** : ✓ 5/5 fiches du domain attendu
**Citations [source SX]** : 1
**Latence** : 102.29s

**Top-5 sources retrievées** :
```
  S1: [insee_salaire] insee_salaan:cs:37 [score=1.121]
  S2: [insee_salaire] insee_salaan:cs:33 [score=1.104]
  S3: [insee_salaire] insee_salaan:cs:38 [score=1.102]
  S4: [insee_salaire] insee_salaan:cs:34 [score=1.083]
  S5: [insee_salaire] insee_salaan:cs:48 [score=1.073]
```

**Réponse du pipeline** :

```
Le salaire net médian d’un **cadre administratif ou commercial d’entreprise (PCS 37)** s’élève à **3 750 € par mois**, soit **45 000 € par an** [source S1].

- Ce métier compte **1,96 million de professionnels** en France, avec une répartition équilibrée (50 % de femmes).
- Les salaires sont plus élevés en **Île-de-France**, région qui concentre près de la moitié des effectifs.

Ces données reflètent la situation en 2023. Souhaites-tu des précisions sur les secteurs ou régions spécifiques ?
```

---

### Q10 — Insertion à 3 ans après un Bac pro Industrie ?

**Domain attendu** : `formation_insertion` (Inserjeunes lycée pro)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 1
**Latence** : 9.13s

**Top-5 sources retrievées** :
```
  S1: [insertion_pro] doctorat:sciences-agronomiques-et-ecologiques:2016:hommes:36-mois-apres-le-diplome [score=0.688]
  S2: [insertion_pro] insersup:bachelor-universitaire-de-technologie:sciences-fondamentales-et-applications:grand-est, Grand Est [score=0.687]
  S3: [insertion_pro] insersup:diplome-vise-niveau-bac-3-grade-licence:droit-sciences-politiques:ile-de-france, Île-de-France [score=0.688]
  S4: [insertion_pro] insersup:licence-professionnelle:sciences-fondamentales-et-applications:bretagne, Bretagne [score=0.682]
  S5: [insertion_pro] insersup:bachelor-universitaire-de-technologie:sciences-de-la-vie-de-la-terre-et-de-l-univers:provence-alpes-cote-d-azur, Provence-Alpes-Côte d'Azur [score=0.682]
```

**Réponse du pipeline** :

```
Je n’ai pas de données dans mes sources sur l’insertion **3 ans après un bac pro Industrie** (ou équivalent).

Mes informations couvrent uniquement :
- L’insertion **6 à 12 mois après** des diplômes **bac+3** (licences pro, BUT) en sciences fondamentales/appliquées **[sources S2, S4, S5]**.
- L’insertion **36 mois après un doctorat** (bac+8) en sciences agronomiques **[source S1]**.

Pour des chiffres précis sur les bac pro, je te conseille de consulter :
1. Les **enquêtes CEREQ** (ex : [Génération](https://www.cereq.fr/)).
2. Le **site de l’ONISEP** ou ton **CIO** local.

Quel aspect de l’insertion te préoccupe le plus : secteur d’activité, stabilité de l’emploi, ou poursuite d’études ?
```

---

### Q11 — Quelles sont les spécialités possibles en BAC PRO agriculture ?

**Domain attendu** : `voie_pre_bac` (Voie pré-bac catalogue)

**Top-5 domain match** : ✓ 2/5 fiches du domain attendu
**Citations [source SX]** : 1
**Latence** : 21.11s

**Top-5 sources retrievées** :
```
  S1: [voie_pre_bac] voie_pre_bac:bac-pro:agriculture [score=1.116]
  S2: [voie_pre_bac] voie_pre_bac:cap:agriculture [score=1.054]
  S3: [(formation)] Sciences et techniques de l'agronomie pour la formation — MINISTERE DE L'AGRICULTURE ET DE LA SOUVERAINETE ALIMENTAIRE [score=0.871]
  S4: [(formation)] bac pro conduite de productions horticoles (arbres, arbustes, fruits, fleurs, légumes) — arbres, arbustes, fruits, fleurs, légumes [score=0.833]
  S5: [(formation)] Education et travail des jeunes équidés — MINISTERE DE L'AGRICULTURE ET DE LA SOUVERAINETE ALIMENTAIRE [score=0.826]
```

**Réponse du pipeline** :

```
Voici les spécialités en **BAC PRO agriculture** référencées dans mes sources :

- **Bac pro aménagements paysagers (voir onisep.fr)** : pour travailler dans la création et l’entretien d’espaces verts.
- **Bac pro conduite d'activités d'élevage et d'hébergement dans le secteur canin-félin (CAEHSCF) (voir onisep.fr)** : axé sur les animaux de compagnie.
- **Bac pro conduite de productions aquacoles (voir onisep.fr)** : pour l’élevage de poissons et crustacés.
- **[Bac pro conduite de productions horticoles](https://www.onisep.fr/http/redirection/formation/slug/FOR.7687)** (arbres, arbustes, fruits, fleurs, légumes) [source S4].

D’autres spécialités existent, mais celles-ci sont les seules documentées ici. Laquelle t’intéresse le plus ?
```

---

### Q12 — Taux de réussite L1 pour un bac S avec mention bien ?

**Domain attendu** : `parcours_bacheliers` (MESR parcours bacheliers en licence)

**Top-5 domain match** : ✓ 5/5 fiches du domain attendu
**Citations [source SX]** : 0
**Latence** : 4.13s

**Top-5 sources retrievées** :
```
  S1: [parcours_bacheliers] parcours:lettres_langues_et_sciences_humaines|bac_s|très_bien [score=0.999]
  S2: [parcours_bacheliers] parcours:sciences_et_sciences_de_l'ingénieur|bac_s|assez_bien [score=0.996]
  S3: [parcours_bacheliers] parcours:staps|bac_s|très_bien [score=0.992]
  S4: [parcours_bacheliers] parcours:lettres_langues_et_sciences_humaines|bac_s|bien [score=0.997]
  S5: [parcours_bacheliers] parcours:sciences_et_sciences_de_l'ingénieur|bac_s|très_bien [score=0.996]
```

**Réponse du pipeline** :

```
Je préfère ne pas répondre sur ce point de manière détaillée, car ma réponse contiendrait des imprécisions factuelles importantes qui pourraient t'induire en erreur.

Détails :
• Le 'bac S' a été supprimé en 2021 (réforme Blanquer). Utiliser 'bac général avec spécialités Maths/PC/SVT'.

Pour avoir une information fiable sur ton orientation, je te conseille :
- **ONISEP** : catalogue officiel des formations françaises — https://www.onisep.fr
- **Parcoursup** : procédures et taux d'accès officiels — https://www.parcoursup.fr
- **SCUIO** : service d'orientation de ton université (si étudiant·e)
- **CIO** / **Psy-EN** : conseiller·ères d'orientation en lycée

Tu peux aussi me reposer la question autrement (par exemple avec un profil plus précis ou sur un sujet plus ciblé) et je ferai de mon mieux pour répondre dans la limite de ce que nos données vérifient.
```

---

### Q13 — Quelle insertion après un doctorat en chimie ?

**Domain attendu** : `insertion_pro` (Doctorat IP MESR)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 3
**Latence** : 7.72s

**Top-5 sources retrievées** :
```
  S1: [metier] chercheur / chercheuse en chimie [score=0.016]
  S2: [metier] géochimiste [score=0.016]
  S3: [metier] chercheur/euse en chimie [score=0.016]
  S4: [metier] ingénieur/e chimiste [score=0.016]
  S5: [metier] aide-chimiste [score=0.015]
```

**Réponse du pipeline** :

```
Les métiers accessibles après un doctorat en chimie incluent principalement des postes en recherche ou en expertise scientifique. Voici quelques pistes :

- **[Chercheur / chercheuse en chimie](https://www.onisep.fr/http/redirection/metier/slug/MET.590)** : travail en laboratoire, développement de projets de recherche fondamentale ou appliquée (santé, matériaux, environnement). Le métier s’exerce dans des organismes publics (CNRS, INSERM) ou privés (pharmacie, cosmétique) [source S1].
- **Géochimiste** : spécialisation dans l’étude des composants terrestres ou aquatiques pour répondre à des enjeux climatiques ou de gestion des ressources naturelles [source S2].
- **Ingénieur·e chimiste** : conception et optimisation de procédés industriels (pétrochimie, agroalimentaire, environnement), souvent en R&D ou production [source S4].

*Aucune donnée sur les salaires ou taux d’insertion n’est disponible dans mes sources.* Ces métiers exigent une forte mobilité (post-docs à l’étranger) et une veille scientifique constante.

Quelle branche de la chimie t’intéresse le plus pour affiner les options ?
```

---

## Décision Gate 3 (manuel)

Après lecture des 13 réponses ci-dessus, indiquer :
- ✓ GO promotion (toutes questions passent les 4 critères)
- ⚠ GO conditionnel (1-3 questions à expliquer mais corpus utilisable)
- ❌ NO-GO (≥4 questions avec hallu, info non disponible non-justifiée, ou top-K mal retrouvé)
