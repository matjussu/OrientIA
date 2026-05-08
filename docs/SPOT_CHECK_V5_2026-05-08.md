# Spot-check Gate 3 v5 — 2026-05-08

> Phase C.5 (BLOQUANT pour promotion v5). 13 questions ciblées sur
> les domaines précédemment dormants. Évaluation manuelle requise.

## Résumé exécutif

- **Questions testées** : 13
- **Questions avec domain attendu présent dans top-5** : 12/13
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

**Top-5 domain match** : ✓ 3/5 fiches du domain attendu
**Citations [source SX]** : 3
**Latence** : 10.74s

**Top-5 sources retrievées** :
```
  S1: [metier_prospective] Dirigeants d'entreprises, Occitanie [score=1.800]
  S2: [metier_prospective] Enseignants, Occitanie [score=1.800]
  S3: [metier_prospective] Formateurs, Occitanie [score=1.800]
  S4: [(formation)] Licence - Langues, littératures et civilisations étrangères et régionales - Parcours Catalan — Université de Perpignan Via Domitia, Occitanie [score=1.052]
  S5: [(formation)] MANAGEMENT SECTORIEL — Management de l’Adaptation Climatique des Organisations en Méditerranée — Université de Montpellier, Occitanie [score=0.972]
```

**Réponse du pipeline** :

```
Tu t’interroges sur les métiers porteurs en Occitanie d’ici 2030, et c’est une excellente question pour anticiper ton orientation. Voici trois secteurs qui devraient offrir des opportunités, selon les projections régionales :

• **Enseignement** : 33 961 postes à pourvoir entre 2019 et 2030 en Occitanie, avec un besoin important lié aux départs en retraite (29 600 postes) [source S2]. Un secteur stable, accessible après un master MEEF ou équivalent.

• **Formation professionnelle** : 6 345 postes attendus sur la même période, dont 4 430 liés aux départs en fin de carrière [source S3]. Le niveau de tension est qualifié de *moyen*, ce qui laisse des marges pour les nouveaux entrants.

• **Dirigeants d’entreprise** : 7 567 postes à pourvoir, avec une création nette de 2 944 emplois [source S1]. Un domaine plus compétitif, mais dynamique en Occitanie (présence proche de la moyenne nationale).

Ces chiffres reflètent des tendances structurelles (retraites, créations d’emplois), pas des promesses individuelles. Pour toi, la question clé serait : *dans lequel de ces univers te vois-tu évoluer au quotidien, au-delà des débouchés* ?
```

---

### Q2 — Combien coûte le logement étudiant CROUS à Lyon ?

**Domain attendu** : `crous` (CROUS corpus — résidences U et restos par zone)

**Top-5 domain match** : ✓ 3/5 fiches du domain attendu
**Citations [source SX]** : 3
**Latence** : 4.02s

**Top-5 sources retrievées** :
```
  S1: [crous] crous_region:lyon [score=2.120]
  S2: [crous] crous_region:strasbourg [score=2.120]
  S3: [crous] crous_region:bordeaux [score=2.120]
  S4: [(formation)] Double diplôme  Sciences Po Lyon (Grade Master) - Licence  (Université Jean Monnet) — Sciences Po Lyon - Institut d'Etudes Politiques - campus de Saint-Etienne, Auvergne-Rhône-Alpes [score=1.156]
  S5: [(formation)] BUT - Génie civil - Construction durable — IUT Lyon1 Site de Villeurbanne Doua, Auvergne-Rhône-Alpes [score=1.054]
```

**Réponse du pipeline** :

```
Tu te renseignes sur les coûts de logement étudiant à Lyon via le CROUS, ce qui est essentiel pour anticiper ton budget.

Malheureusement, **les frais de logement CROUS ne sont pas indiqués dans mes sources** pour Lyon [source S1]. En revanche, voici ce que je peux te préciser :
- **36 restaurants universitaires** sont disponibles (dont 21 cafétérias et 12 restaurants traditionnels) [source S1].
- **9 résidences CROUS** sont répertoriées dans la région lyonnaise (Saint-Étienne, Villeurbanne, Porte des Alpes) [source S1].

Pour obtenir les tarifs exacts des loyers, je te conseille de consulter directement le [site du CROUS Lyon](https://www.crous-lyon.fr) ou de contacter leur service logement.

As-tu déjà identifié un quartier en particulier pour tes recherches ?
```

---

### Q3 — Quels sont les blocs de compétences du RNCP 38450 ?

**Domain attendu** : `competences_certif` (France Compétences blocs RNCP)

**Top-5 domain match** : ✓ 3/5 fiches du domain attendu
**Citations [source SX]** : 1
**Latence** : 3.31s

**Top-5 sources retrievées** :
```
  S1: [competences_certif] rncp_blocs:RNCP40440 [score=2.380]
  S2: [competences_certif] rncp_blocs:RNCP37636 [score=2.380]
  S3: [competences_certif] rncp_blocs:RNCP41171 [score=2.380]
  S4: [(formation)] Manager des ressources humaines — TALIS COMPETENCES & CERTIFICATIONS [score=0.886]
  S5: [(formation)] Chef de projet géomatique — ATLAS SOUTENIR LES COMPETENCES [score=0.885]
```

**Réponse du pipeline** :

```
Je n’ai pas de formation associée au **RNCP 38450** dans mes sources actuelles, donc je ne peux pas te détailler ses blocs de compétences.

Si tu cherches des infos sur des certifications RNCP en santé (comme l’ostéopathie [source S1/S2]) ou en informatique/ingénierie (ex : ISTY [source S3]), je peux t’éclairer. Sinon, je te conseille de vérifier directement sur [France Compétences](https://www.francecompetences.fr/) ou de contacter le certificateur du RNCP 38450.

Quel domaine ou métier te intéresse derrière cette recherche ?
```

---

### Q4 — Quel salaire après un Master Droit en région PACA ?

**Domain attendu** : `insertion_pro` (InserSup spécifique discipline × région)

**Top-5 domain match** : ✓ 2/5 fiches du domain attendu
**Citations [source SX]** : 1
**Latence** : 5.91s

**Top-5 sources retrievées** :
```
  S1: [voie_pre_bac] voie_pre_bac:bac-pro:droit [score=1.727]
  S2: [insertion_pro] insersup:diplome-vise-niveau-bac-5-grade-master:droit-sciences-politiques:provence-alpes-cote-d-azur, Provence-Alpes-Côte d'Azur [score=1.719]
  S3: [insertion_pro] insersup:diplome-vise-niveau-bac-5-grade-master:lettres-sciences-du-langage-arts:provence-alpes-cote-d-azur, Provence-Alpes-Côte d'Azur [score=1.719]
  S4: [(formation)] MANAGER D'AFFAIRES (MANITUDE) — SARL COACHING PACA [score=1.012]
  S5: [(formation)] DROIT PRIVE — Droit privé général — Université de Pau et des Pays de l'Adour, Nouvelle-Aquitaine [score=1.016]
```

**Réponse du pipeline** :

```
Tu te demandes quel salaire attendre après un master en droit en région PACA. Voici ce que mes sources indiquent pour cette zone géographique :

- **Master Droit, sciences politiques (Aix-Marseille Université)** : le taux d’emploi salarié atteint **63 % à 12 mois** après le diplôme, mais **aucune donnée sur le salaire médian** n’est disponible dans mes sources [source S2].
- Les autres masters droit en PACA (comme ceux des IEP ou écoles privées) ne sont pas couverts par les données salariales dans mes fiches.

Pour affiner ta recherche, tu pourrais contacter directement le **Service Orientation-Insertion d’Aix-Marseille Université** ou consulter les enquêtes locales de l’**OREF PACA**. Qu’est-ce qui compte le plus pour toi : la stabilité de l’emploi, le secteur d’activité, ou le niveau de rémunération ?
```

---

### Q5 — Que fait un actuaire au quotidien ?

**Domain attendu** : `metier_detail` (ROME 4.0 fiches métiers — compétences détaillées)

**Top-5 domain match** : ✓ 3/5 fiches du domain attendu
**Citations [source SX]** : 1
**Latence** : 4.53s

**Top-5 sources retrievées** :
```
  S1: [metier_detail] Actuaire [score=2.120]
  S2: [metier_detail] Professeur / Professeure d'enseignement général pour déficients sensoriels [score=2.054]
  S3: [metier_detail] Standardiste [score=2.048]
  S4: [(formation)] ACTUARIAT — Actuariat et Ingénierie Mathématique pour l'Assurance et la Finance — Université de Rouen Normandie, Normandie [score=0.981]
  S5: [(formation)] MONNAIE, BANQUE, FINANCE, ASSURANCE — Métiers de la banque de détail -  En Alternance (apprentissage et contrat pro) — Université de Lille, Hauts-de-France [score=0.941]
```

**Réponse du pipeline** :

```
Tu t’intéresses au métier d’actuaire et veux savoir en quoi consiste son quotidien. Voici les missions clés, tirées directement des compétences référencées :

- **Développement commercial et stratégie** :
  L’actuaire définit la tarification des produits d’assurance ou d’épargne, intègre de nouveaux produits sur le marché, et réalise une veille concurrentielle pour ajuster les offres. Il met aussi en place des outils de prévision des besoins clients, optimisant ainsi les performances de l’entreprise `[source S1]`.

- **Analyse et modélisation** :
  Bien que non détaillé ici, son rôle inclut souvent la création de modèles mathématiques pour évaluer les risques (santé, accidents, marchés financiers) — une dimension centrale du métier, même si les chiffres précis d’insertion ou de salaire ne sont pas disponibles dans mes sources.

Ce métier allie donc technique (maths, stats) et business (stratégie, marché). Est-ce que c’est plutôt l’aspect *calcul de risques* ou l’aspect *création de produits* qui t’attire ?
```

---

### Q6 — Quelles aides financières pour les étudiants boursiers ?

**Domain attendu** : `financement_etudes` (Financement curated dispositifs)

**Top-5 domain match** : ✓ 2/5 fiches du domain attendu
**Citations [source SX]** : 4
**Latence** : 6.39s

**Top-5 sources retrievées** :
```
  S1: [competences_certif] rncp_blocs:RNCP38500 [score=1.857]
  S2: [financement_etudes] Prime à la naissance / PreParE pour étudiants parents [score=1.800]
  S3: [financement_etudes] Bourse sur critères sociaux CROUS — enseignement supérieur [score=1.800]
  S4: [(formation)] Licence - Langues étrangères appliquées - Parcours LEA Anglais-Français pour étudiants étrangers — Université Savoie Mont Blanc - Chambéry, Auvergne-Rhône-Alpes [score=1.220]
  S5: [(formation)] Licence - Portail Mathématiques - Mathématiques et Applications - HORS parcours Sciences actuarielles et financières — Le Mans Université, Pays-de-la-Loire [score=1.175]
```

**Réponse du pipeline** :

```
Je comprends que tu cherches à sécuriser ton projet d’études en identifiant les aides financières accessibles. Voici les dispositifs pertinents dans mes sources, spécifiquement pour les étudiants boursiers ou en situation particulière :

• **Bourse sur critères sociaux (CROUS)** : Destinée aux étudiants en formation initiale (BTS, licence, master, écoles reconnues), avec des montants annuels variant entre **1080 € et 5965 €** selon l’échelon (2024-2025). Les revenus du foyer fiscal déterminent l’éligibilité `[source S3]`.
  → *Compatibilité* : Cumule possible avec d’autres aides comme les APL ou les allocations familiales.

• **Prestations CAF pour étudiants parents** : Si tu es parent d’un jeune enfant pendant tes études, tu peux bénéficier de la **Prime à la naissance (PreParE)** et des allocations liées (PAJE, APL). Ces aides restent versées même en formation initiale, sous conditions de ressources `[source S2]`.
  → *À vérifier* : La bourse CROUS et les aides CAF sont cumulables, mais les montants exacts dépendent de ta situation familiale.

Aucune information dans mes sources ne précise des aides *spécifiques* aux formations sélectives (comme la licence LEA à Chambéry `[source S4]`) ou aux filières scientifiques `[source S5]`. Les dispositifs cités s’appliquent à tous les boursiers, quel que soit le domaine d’études.

**Question pour toi** : Est-ce que ta priorité aujourd’hui est plutôt de couvrir les frais de vie quotidienne (logement, transport), ou de financer des frais liés à la formation elle-même (matériel, déplacements stages) ?
```

---

### Q7 — Quelles formations en Guadeloupe ?

**Domain attendu** : `territoire_drom` (DROM-COM territoires)

**Top-5 domain match** : ✓ 3/5 fiches du domain attendu
**Citations [source SX]** : 0
**Latence** : 6.72s

**Top-5 sources retrievées** :
```
  S1: [territoire_drom] Université des Antilles — formations dans les DROM [score=2.200]
  S2: [territoire_drom] Guadeloupe [score=2.186]
  S3: [territoire_drom] Martinique [score=2.093]
  S4: [(formation)] Licence - Humanités - Parcours Histoire et sciences sociales (option préparation IEP) - Saint-Claude - Guadeloupe — Université des Antilles - Pôle Guadeloupe (Saint-Claude), Guadeloupe [score=1.220]
  S5: [(formation)] BTS - Services - Management en hôtellerie restauration — Lycée des métiers de l'Hôtellerie et du Tourisme Archipel Guadeloupe, Guadeloupe [score=1.147]
```

**Réponse du pipeline** :

```
Je préfère ne pas répondre sur ce point de manière détaillée, car ma réponse contiendrait des imprécisions factuelles importantes qui pourraient t'induire en erreur.

Détails :
• Formation citée non présente dans notre base de données vérifiée : *Licence Humanités (Histoire et sciences sociales, option prépa IEP)*.

Pour avoir une information fiable sur ton orientation, je te conseille :
- **ONISEP** : catalogue officiel des formations françaises — https://www.onisep.fr
- **Parcoursup** : procédures et taux d'accès officiels — https://www.parcoursup.fr
- **SCUIO** : service d'orientation de ton université (si étudiant·e)
- **CIO** / **Psy-EN** : conseiller·ères d'orientation en lycée

Tu peux aussi me reposer la question autrement (par exemple avec un profil plus précis ou sur un sujet plus ciblé) et je ferai de mon mieux pour répondre dans la limite de ce que nos données vérifient.
```

---

### Q8 — Marché de l'emploi cadres en Bretagne ?

**Domain attendu** : `apec_region` (APEC régions)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 3
**Latence** : 6.32s

**Top-5 sources retrievées** :
```
  S1: [metier_prospective] Cadres de la fonction publique, Bretagne [score=1.800]
  S2: [metier_prospective] Techniciens et cadres de l'agriculture, Bretagne [score=1.800]
  S3: [metier_prospective] Cadres de la banque et des assurances, Bretagne [score=1.800]
  S4: [(formation)] Licence - Portail Droit - Droit/histoire de l'art et archéologie parcours Droit - Marché de l'art — Université de Brest - Site de Quimper, Bretagne [score=1.220]
  S5: [(formation)] MANAGEMENT SECTORIEL — Direction des établissements sanitaires et médico-sociaux — Institut catholique de Rennes, Bretagne [score=0.945]
```

**Réponse du pipeline** :

```
Tu t’intéresses aux perspectives d’emploi pour les cadres en Bretagne. Voici quelques éléments clés tirés des projections régionales à horizon 2030, en ciblant des secteurs porteurs ou en tension.

- **Fonction publique** : Le secteur compte **23 563 cadres** en 2019, avec **7 117 postes à pourvoir** d’ici 2030, principalement liés aux départs en retraite (7 254). Cependant, les **jeunes débutants attendus** sont en retrait (-5 913), ce qui pourrait rendre l’accès plus compétitif [source S1].
- **Agriculture** : Un secteur dynamique en Bretagne, avec **2 535 postes de techniciens/cadres à pourvoir** d’ici 2030, dont **720 créations nettes** (rare). La tension est **très forte** en 2019, et le métier y est **2 fois plus représenté** qu’au niveau national [source S2].
- **Banque/Assurances** : Moins porteur, avec **2 467 postes** à pourvoir mais une **destruction nette de 291 emplois**. Le métier reste **sous-représenté** en Bretagne (×0,66 vs France), malgré une tension forte [source S3].

Ces données suggèrent des opportunités variables selon les filières. As-tu une préférence pour l’un de ces secteurs, ou souhaites-tu explorer des formations spécifiques pour t’y préparer ?
```

---

### Q9 — Salaire moyen d'un cadre supérieur (PCS 37) ?

**Domain attendu** : `insee_salaire` (INSEE salaires PCS)

**Top-5 domain match** : ✓ 3/5 fiches du domain attendu
**Citations [source SX]** : 1
**Latence** : 15.77s

**Top-5 sources retrievées** :
```
  S1: [insee_salaire] insee_salaan:cs:37 [score=2.200]
  S2: [insee_salaire] insee_salaan:cs:34 [score=2.200]
  S3: [insee_salaire] insee_salaan:cs:33 [score=2.200]
  S4: [(formation)] Licence - Gestion - Parcours Commerce Affaires Développement des Relations Economiques  (CADRE) — UHA Business School, Grand-Est [score=0.986]
  S5: [(formation)] Licence professionnelle - Métiers des réseaux informatiques et télécommunications Parcours réseaux et cybersécurité — CY Cergy Paris Université, Île-de-France [score=0.986]
```

**Réponse du pipeline** :

```
Tu t’intéresses au salaire moyen des cadres administratifs et commerciaux (PCS 37) — voici les données INSEE les plus récentes pour te donner un repère concret.

- **Salaire net médian annuel** : 45 000 € (soit **3 750 €/mois**), avec une répartition équilibrée entre hommes et femmes (50/50) [source S1].
- **Top 3 régions** pour les effectifs : Île-de-France (48 % des postes), Auvergne-Rhône-Alpes, puis PACA. Une localisation francilienne peut influencer significativement ce salaire à la hausse.

Ces chiffres couvrent l’ensemble du spectre (jeunes cadres comme seniors), sans distinction par ancienneté ou secteur précis. Pour affiner, as-tu une idée du domaine qui t’attire (grande entreprise, PME, international…) ?
```

---

### Q10 — Insertion à 3 ans après un Bac pro Industrie ?

**Domain attendu** : `formation_insertion` (Inserjeunes lycée pro)

**Top-5 domain match** : ✓ 2/5 fiches du domain attendu
**Citations [source SX]** : 4
**Latence** : 5.02s

**Top-5 sources retrievées** :
```
  S1: [voie_pre_bac] voie_pre_bac_synthese:bac-pro [score=1.800]
  S2: [formation_insertion] inserjeunes_formation:bac-pro:microtechniques [score=1.800]
  S3: [formation_insertion] inserjeunes_formation:bac-pro:logistique [score=1.800]
  S4: [(formation)] Formation d'ingénieur Bac + 5 - (en 6 ans) - Bac général — INSA Lyon, Auvergne-Rhône-Alpes [score=1.137]
  S5: [(formation)] Formation d'ingénieur Bac + 5 - bac  général et STI2D — ISA BTP, Nouvelle Aquitaine [score=1.142]
```

**Réponse du pipeline** :

```
Tu te demandes comment se passe l’insertion professionnelle **3 ans après un Bac Pro dans l’industrie**. Voici ce que montrent les données disponibles :

- **Pas de chiffre précis à 3 ans** pour les Bac Pro industriels dans mes sources. En revanche, pour des spécialités proches :
  - **Microtechniques** : 38,5 % en emploi à 12 mois, 46,5 % à 24 mois [source S2].
  - **Logistique** (secteur connexe) : 51,1 % à 12 mois, 56,6 % à 24 mois [source S3].
  → Ces taux suggèrent une insertion progressive, avec une partie des diplômés poursuivant des études (ex. 66,7 % en poursuite pour les microtechniques [source S2]).

- **Domaine industriel** : 22 spécialités de Bac Pro référencées (ex. usinage, maintenance), mais **aucune donnée d’insertion à 3 ans** dans mes sources [source S1].

Tu envisages plutôt une entrée directe dans la vie active ou une poursuite d’études pour te spécialiser ? Cela peut influencer le choix de la filière.
```

---

### Q11 — Quelles sont les spécialités possibles en BAC PRO agriculture ?

**Domain attendu** : `voie_pre_bac` (Voie pré-bac catalogue)

**Top-5 domain match** : ✓ 3/5 fiches du domain attendu
**Citations [source SX]** : 2
**Latence** : 4.32s

**Top-5 sources retrievées** :
```
  S1: [voie_pre_bac] voie_pre_bac:bac-pro:agriculture [score=1.807]
  S2: [voie_pre_bac] voie_pre_bac:bac-pro:tourisme-hotellerie [score=1.790]
  S3: [voie_pre_bac] voie_pre_bac_synthese:bac-pro [score=1.800]
  S4: [(formation)] BTS - Agricole - Technico-commercial - Spécialité biens et services pour l'agriculture — LEAP AGRICULTURE ET TERRITOIRE IS4A, Grand-Est [score=0.909]
  S5: [(formation)] Ingénieur diplômé de l’Institut supérieur d’agriculture Rhône-Alpes — MINISTERE DE L'AGRICULTURE ET DE LA SOUVERAINETE ALIMENTAIRE [score=0.939]
```

**Réponse du pipeline** :

```
Tu t’intéresses aux spécialités du **BAC PRO en agriculture**, un domaine qui offre des parcours variés pour travailler dans l’élevage, les cultures ou l’aménagement des espaces.

Voici les 9 spécialités référencées dans ce secteur **[source S3]** :
- **Aménagements paysagers** (création et entretien d’espaces verts)
- **Conduite d’activités d’élevage et d’hébergement dans le secteur canin-félin** (CAEHSCF)
- **Conduite de productions aquacoles** (élevage de poissons, crustacés…)
- *6 autres spécialités non détaillées dans mes sources* (liste complète sur [ONISEP](https://www.onisep.fr/)).

Ces formations, de niveau 4 (équivalent bac), se préparent en 3 ans après la 3ᵉ **[source S3]**.

Est-ce qu’une de ces spécialités te parle plus que les autres, ou cherches-tu des précisions sur les débouchés concrets ?
```

---

### Q12 — Taux de réussite L1 pour un bac S avec mention bien ?

**Domain attendu** : `parcours_bacheliers` (MESR parcours bacheliers en licence)

**Top-5 domain match** : ✓ 3/5 fiches du domain attendu
**Citations [source SX]** : 2
**Latence** : 3.94s

**Top-5 sources retrievées** :
```
  S1: [parcours_bacheliers] parcours:staps|bac_professionnel|très_bien [score=2.040]
  S2: [parcours_bacheliers] parcours:santé|bac_technologique_hors_stmg|assez_bien [score=2.040]
  S3: [parcours_bacheliers] parcours:santé|bac_s|bien [score=2.040]
  S4: [(formation)] BTS - Production - Assistance technique d'ingénieur — Lycée professionnel Amiral Lacaze, Réunion [score=1.207]
  S5: [(formation)] Licence - Langues, littératures et civilisations étrangères et régionales - Parcours  Anglais — Université de Rennes 2, Bretagne [score=1.114]
```

**Réponse du pipeline** :

```
Tu veux savoir comment se passent les études en licence pour un·e bachelier·e S avec mention Bien, notamment en termes de réussite en première année.

Pour la **licence en Santé** (accès via Parcoursup), les données montrent que :
- **100 % des étudiant·es** de ce profil passent en L2 en 1 an [source S3].
- Sur un suivi plus long (cohorte 2012), **75 % obtiennent leur licence en 3 ans** (ou 4 ans max) [source S3].

Ces chiffres concernent uniquement la licence Santé, mais ils donnent un aperçu de la réussite dans une filière exigeante.

Est-ce que cette filière t’intéresse particulièrement, ou cherches-tu des infos sur d’autres domaines ?
```

---

### Q13 — Quelle insertion après un doctorat en chimie ?

**Domain attendu** : `insertion_pro` (Doctorat IP MESR)

**Top-5 domain match** : ✓ 3/5 fiches du domain attendu
**Citations [source SX]** : 4
**Latence** : 6.82s

**Top-5 sources retrievées** :
```
  S1: [insertion_pro] doctorat:chimie-et-sciences-des-materiaux:2016:hommes:12-mois-apres-le-diplome [score=1.800]
  S2: [insertion_pro] doctorat:chimie-et-sciences-des-materiaux:2016:hommes:36-mois-apres-le-diplome [score=1.800]
  S3: [insertion_pro] doctorat:chimie-et-sciences-des-materiaux:2014:hommes:12-mois-apres-le-diplome [score=1.800]
  S4: [(formation)] CHIMIE — Chimie Analytique et Qualité — Université de Poitiers, Nouvelle-Aquitaine [score=1.018]
  S5: [(formation)] CHIMIE — Integrated research for advanced chemistry and materials — Université de Lille, Hauts-de-France [score=1.011]
```

**Réponse du pipeline** :

```
Je comprends que tu veux y voir plus clair sur les débouchés après un doctorat en chimie, surtout dans un domaine où l’investissement est long. Voici ce que montrent les données pour les docteurs en **chimie et sciences des matériaux** (cohorte masculine, source MESR) :

• **À 12 mois** : 83 % des diplômés sont en emploi, dont 99 % en poste cadre et 46 % en CDI [source S1]. Le salaire net médian atteint **2200 €/mois** [source S1], avec près de la moitié (49 %) dans le secteur académique (recherche publique, enseignement supérieur).
• **À 36 mois** : l’insertion progresse à **93 %**, dont 66 % en emploi stable (CDI, titulaire) [source S2]. Le salaire médian passe à **2500 €/mois** [source S2], et la répartition se diversifie : 34 % en R&D privée (industrie, pharma), 38 % dans l’académique.

**À noter** : Ces chiffres concernent une population majoritairement masculine (sources disponibles). Les secteurs à l’étranger représentent **34 à 38 %** des emplois [sources S1/S2], ce qui peut ouvrir des opportunités si la mobilité t’intéresse.

Ces perspectives te semblent-elles alignées avec tes attentes, ou souhaites-tu explorer des voies plus appliquées (type masters pro en chimie analytique ou matériaux) pour comparer ?
```

---

## Décision Gate 3 (manuel)

Après lecture des 13 réponses ci-dessus, indiquer :
- ✓ GO promotion (toutes questions passent les 4 critères)
- ⚠ GO conditionnel (1-3 questions à expliquer mais corpus utilisable)
- ❌ NO-GO (≥4 questions avec hallu, info non disponible non-justifiée, ou top-K mal retrouvé)
