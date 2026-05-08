# Spot-check Gate 3 v5 — 2026-05-08

> Phase C.5 (BLOQUANT pour promotion v5). 13 questions ciblées sur
> les domaines précédemment dormants. Évaluation manuelle requise.

## Résumé exécutif

- **Questions testées** : 13
- **Questions avec domain attendu présent dans top-5** : 11/13
- **Erreurs runtime** : 0
- **Corpus** : `data/processed/formations_v6.json`
- **Index** : `data/embeddings/formations_v6.index`

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
**Latence** : 10.01s

**Top-5 sources retrievées** :
```
  S1: [metier_prospective] Dirigeants d'entreprises, Occitanie [score=1.800]
  S2: [(formation)] Formation d'ingénieur Bac + 5 - Bac général — Polytech Montpellier, Occitanie [score=1.144]
  S3: [metier_prospective] Enseignants, Occitanie [score=1.800]
  S4: [metier_prospective] Formateurs, Occitanie [score=1.800]
  S5: [(formation)] Licence - Langues, littératures et civilisations étrangères et régionales - Parcours Bi-disciplinaire Occitan - Catalan — Université Toulouse 2 Jean Jaurès, Occitanie [score=1.059]
```

**Réponse du pipeline** :

```
Tu te demandes quels métiers auront des opportunités en Occitanie d’ici 2030. Voici trois secteurs porteurs selon les projections régionales, avec des besoins identifiés en recrutement :

• **Enseignement** : 33 961 postes à pourvoir entre 2019 et 2030, principalement liés aux départs en retraite (29 600). Un secteur stable, avec une présence légèrement supérieure à la moyenne nationale [source S3].
*Exemples de voies* : Master MEEF (pour les concours de l’Éducation nationale), formations en pédagogie.

• **Formation professionnelle** : 6 345 postes attendus, avec une tension moyenne sur le marché. Les créations nettes (+1 914) et les départs (4 430) offrent des débouchés, notamment pour les formateurs spécialisés [source S4].

• **Dirigeants d’entreprise** : 7 567 postes à pourvoir, dont 2 944 créations nettes. Les jeunes débutants pourraient rencontrer plus de concurrence (-1 380 postes "réservés"), mais le secteur reste dynamique [source S1].

Ces métiers demandent souvent un niveau bac+3 à bac+5. Pour toi, la question est : *préfères-tu un métier centré sur la transmission (enseignement/formation), ou plutôt sur la gestion et la stratégie (dirigeant) ?*
```

---

### Q2 — Combien coûte le logement étudiant CROUS à Lyon ?

**Domain attendu** : `crous` (CROUS corpus — résidences U et restos par zone)

**Top-5 domain match** : ✓ 3/5 fiches du domain attendu
**Citations [source SX]** : 3
**Latence** : 3.76s

**Top-5 sources retrievées** :
```
  S1: [crous] crous_region:lyon [score=2.120]
  S2: [crous] crous_region:strasbourg [score=2.120]
  S3: [crous] crous_region:bordeaux [score=2.120]
  S4: [(formation)] Double diplôme  Sciences Po Lyon (Grade Master) - Licence  (Université Jean Monnet) — Sciences Po Lyon - Institut d'Etudes Politiques - campus de Saint-Etienne, Auvergne-Rhône-Alpes [score=1.156]
  S5: [(formation)] BUT - Génie civil - Construction durable — IUT Lyon1 Site de Villeurbanne Doua, Auvergne-Rhône-Alpes [score=1.059]
```

**Réponse du pipeline** :

```
Tu cherches des infos sur les coûts de logement étudiant CROUS à Lyon pour anticiper ton budget.

D’après mes sources, **les frais exacts de logement CROUS ne sont pas disponibles** [source S1]. En revanche, voici ce que je peux te dire sur l’offre :
- **9 résidences universitaires** sont répertoriées dans la région lyonnaise (Lyon, Villeurbanne, Saint-Étienne) [source S1].
- **36 lieux de restauration** (cafétérias, restaurants U) sont accessibles, ce qui peut réduire tes dépenses alimentaires [source S1].

Pour obtenir les tarifs précis des loyers, je te conseille de consulter directement le site du **CROUS Lyon** ou de contacter leur service logement.

As-tu déjà exploré d’autres options comme les colocations ou les résidences privées en parallèle ?
```

---

### Q3 — Quels sont les blocs de compétences du RNCP 38450 ?

**Domain attendu** : `competences_certif` (France Compétences blocs RNCP)

**Top-5 domain match** : ✓ 3/5 fiches du domain attendu
**Citations [source SX]** : 0
**Latence** : 4.92s

**Top-5 sources retrievées** :
```
  S1: [competences_certif] rncp_blocs:RNCP40440 [score=2.380]
  S2: [competences_certif] rncp_blocs:RNCP37636 [score=2.380]
  S3: [competences_certif] rncp_blocs:RNCP38780 [score=2.380]
  S4: [(formation)] Formation d'ingénieur Bac + 5 - Bac STL (Spécialité SPCL) — CPI Rennes (ENS Chimie Rennes), Bretagne [score=1.110]
  S5: [(formation)] Licence professionnelle - Métiers des réseaux informatiques et télécommunications Parcours réseaux et cybersécurité — CY Cergy Paris Université, Île-de-France [score=1.026]
```

**Réponse du pipeline** :

```
Je n’ai pas de formation associée au RNCP 38450 dans mes sources, ni d’information sur ses blocs de compétences.

Si ce numéro correspond à une certification en ostéopathie, sache que pour les RNCP **RNCP40440**, **RNCP37636** et **RNCP38780** (ostéopathe bac+5), les blocs de compétences ne sont **pas accessibles séparément** en raison de la réglementation du métier `[source S1, S2, S3]`.

Pour le RNCP 38450, je te conseille de vérifier directement sur [France Compétences](https://www.francecompetences.fr/) ou de contacter l’organisme certificateur.

Quelle est la formation ou le métier qui t’intéresse derrière ce RNCP ? Je peux peut-être t’orienter vers des alternatives documentées.
```

---

### Q4 — Quel salaire après un Master Droit en région PACA ?

**Domain attendu** : `insertion_pro` (InserSup spécifique discipline × région)

**Top-5 domain match** : ✓ 3/5 fiches du domain attendu
**Citations [source SX]** : 2
**Latence** : 5.5s

**Top-5 sources retrievées** :
```
  S1: [insertion_pro] insersup:master-lmd:droit-sciences-politiques:grand-est, Grand Est [score=1.800]
  S2: [insertion_pro] insersup:master-lmd:droit-sciences-politiques:pays-de-la-loire, Pays de la Loire [score=1.800]
  S3: [insertion_pro] insersup:master-lmd:droit-sciences-politiques:normandie, Normandie [score=1.800]
  S4: [(formation)] Double diplôme  Sciences Po Lyon (Grade Master) - Licence  (Université Jean Monnet) — Sciences Po Lyon - Institut d'Etudes Politiques - campus de Saint-Etienne, Auvergne-Rhône-Alpes [score=1.154]
  S5: [(formation)] Licence - Portail Droit — Université Côte d'Azur, Provence-Alpes-Côte d'Azur [score=1.095]
```

**Réponse du pipeline** :

```
Tu te demandes quel salaire attendre après un **Master Droit en région PACA**, mais mes sources ne couvrent pas cette région pour ce diplôme.

Voici ce que je peux te partager sur d’autres territoires pour te donner un ordre d’idée (même si les réalités locales varient) :
- En **Grand Est**, 52 % des diplômés d’un Master Droit sont en emploi salarié à 6 mois [source S1].
- En **Normandie**, ce taux monte à 66 % à 6 mois et 81 % à 12 mois [source S3].

**Aucune donnée salariale ou spécifique à la PACA** n’est disponible dans mes sources. Pour des chiffres précis, je te conseille de consulter :
- Les enquêtes **Observatoire Régional des Métiers PACA** (ex : [ORM](https://www.orm-paca.org))
- Les rapports **InserSup MESR** filtrés par académie (Nice/Aix-Marseille).

Qu’est-ce qui motive ta question sur le salaire : un projet d’installation en PACA, ou une comparaison avec d’autres régions ?
```

---

### Q5 — Que fait un actuaire au quotidien ?

**Domain attendu** : `metier_detail` (ROME 4.0 fiches métiers — compétences détaillées)

**Top-5 domain match** : ✓ 3/5 fiches du domain attendu
**Citations [source SX]** : 2
**Latence** : 5.01s

**Top-5 sources retrievées** :
```
  S1: [metier_detail] Actuaire [score=2.120]
  S2: [metier_detail] Professeur / Professeure d'enseignement général pour déficients sensoriels [score=2.060]
  S3: [metier_detail] Standardiste [score=2.054]
  S4: [(formation)] Double licence - Mathématiques / Economie - DOUBLE licence Économie - Mathématiques parcours Sciences actuarielles et financières — Le Mans Université, Pays de la Loire [score=1.028]
  S5: [(formation)] Licence professionnelle - Assurance, banque, finance : chargé de clientèle - Parcours chargé de clientèle banque- assurance — Université de Cergy-Pontoise - CY SUP, Île-de-France [score=1.013]
```

**Réponse du pipeline** :

```
Tu t’intéresses au métier d’actuaire, qui allie mathématiques, analyse de risques et stratégie financière. Voici ce qui rythme son quotidien, d’après les compétences clés identifiées :

- **Développer des outils de prévision et optimiser les performances** : il conçoit des modèles statistiques pour anticiper les besoins (ex : tarification d’assurances) et propose des mesures pour améliorer la rentabilité des produits. L’objectif est de concilier attractivité commerciale et maîtrise des risques `[source S1]`.
- **Veille marché et innovation produit** : il analyse la concurrence, intègre de nouveaux produits d’assurance ou d’épargne, et ajuste les offres en fonction des évolutions réglementaires ou des attentes clients `[source S1]`.
- **Collaboration transverse** : bien que centré sur les données, le métier implique des échanges réguliers avec les équipes commerciales, juridiques ou marketing pour traduire les analyses en décisions opérationnelles.

Les détails sur les conditions d’exercice (salaire, débouchés, formations associées) ne sont pas disponibles dans mes sources. Si c’est un aspect qui t’importe, comment envisages-tu de creuser ces questions ?
```

---

### Q6 — Quelles aides financières pour les étudiants boursiers ?

**Domain attendu** : `financement_etudes` (Financement curated dispositifs)

**Top-5 domain match** : ✓ 1/5 fiches du domain attendu
**Citations [source SX]** : 3
**Latence** : 5.17s

**Top-5 sources retrievées** :
```
  S1: [competences_certif] rncp_blocs:RNCP38500 [score=1.920]
  S2: [financement_etudes] Bourse sur critères sociaux CROUS — enseignement supérieur [score=1.800]
  S3: [competences_certif] rncp_blocs:RNCP40662 [score=1.831]
  S4: [(formation)] Double licence - Mathématiques / Economie - DOUBLE licence Économie - Mathématiques parcours Sciences actuarielles et financières — Le Mans Université, Pays de la Loire [score=1.220]
  S5: [(formation)] Licence - Langues étrangères appliquées - Parcours LEA Anglais-Français pour étudiants étrangers — Université Savoie Mont Blanc - Chambéry, Auvergne-Rhône-Alpes [score=1.220]
```

**Réponse du pipeline** :

```
Tu te demandes quelles aides financières existent pour les étudiants boursiers, et c’est une question essentielle pour aborder sereinement tes études.

• **Bourse sur critères sociaux CROUS** : elle s’adresse aux étudiants en formation initiale (BTS, BUT, licence, master, écoles d’ingénieurs/commerce reconnues) avec des revenus familiaux sous plafond. Les montants annuels varient entre **1080 € et 5965 €** pour 2024-2025 [source S2].

• **Pas d’autres dispositifs** mentionnés dans mes sources pour des aides spécifiques aux boursiers (logement, mobilité, etc.). Les formations comme la double licence Maths-Économie au Mans ou le parcours LEA à Chambéry sont éligibles à cette bourse, mais sans précisions sur des compléments locaux [source S4][source S5].

Quelle est ta priorité : couvrir les frais de vie au quotidien, ou financer un projet spécifique (mobilité internationale, matériel, etc.) ?
```

---

### Q7 — Quelles formations en Guadeloupe ?

**Domain attendu** : `territoire_drom` (DROM-COM territoires)

**Top-5 domain match** : ✓ 3/5 fiches du domain attendu
**Citations [source SX]** : 0
**Latence** : 6.74s

**Top-5 sources retrievées** :
```
  S1: [territoire_drom] Université des Antilles — formations dans les DROM [score=2.200]
  S2: [territoire_drom] Guadeloupe [score=2.186]
  S3: [territoire_drom] Martinique [score=2.093]
  S4: [(formation)] Licence - Humanités - Parcours Histoire et sciences sociales (option préparation IEP) - Saint-Claude - Guadeloupe — Université des Antilles - Pôle Guadeloupe (Saint-Claude), Guadeloupe [score=1.220]
  S5: [(formation)] Diplôme de Comptabilité et de Gestion — Lycée Baimbridge, Guadeloupe [score=1.139]
```

**Réponse du pipeline** :

```
Je préfère ne pas répondre sur ce point de manière détaillée, car ma réponse contiendrait des imprécisions factuelles importantes qui pourraient t'induire en erreur.

Détails :
• Formation citée non présente dans notre base de données vérifiée : *Licence Humanités (Histoire et sciences sociales, option préparation IEP)*.

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
**Latence** : 8.04s

**Top-5 sources retrievées** :
```
  S1: [metier_prospective] Cadres de la fonction publique, Bretagne [score=1.800]
  S2: [metier_prospective] Techniciens et cadres de l'agriculture, Bretagne [score=1.800]
  S3: [metier_prospective] Cadres de la banque et des assurances, Bretagne [score=1.800]
  S4: [(formation)] Licence - Portail Economie et management — Université de Brest, Bretagne [score=1.021]
  S5: [(formation)] LANGUES, LITTERATURES ET CIVILISATIONS ETRANGERES ET REGIONALES — Breton et Celtique — Université Rennes 2, Bretagne [score=0.949]
```

**Réponse du pipeline** :

```
Tu t’intéresses aux perspectives d’emploi pour les cadres en Bretagne. Voici quelques éléments clés selon les secteurs projetés jusqu’en 2030 :

- **Fonction publique** : 7 117 postes à pourvoir en Bretagne d’ici 2030, principalement liés aux départs en retraite (7 254). Le secteur reste stable, avec une présence proche de la moyenne nationale `[source S1]`.
- **Agriculture** : 2 535 postes attendus, dont 720 créations nettes (secteur en tension forte). La Bretagne surreprésente ce métier (×2 vs France), avec un besoin marqué en jeunes qualifiés `[source S2]`.
- **Banque/Assurances** : 2 467 postes à pourvoir, mais avec un solde négatif pour les jeunes débutants (-1 374). Le secteur est sous-représenté en région (×0.66 vs France) et en forte tension `[source S3]`.

Ces données suggèrent des opportunités variables selon le domaine. Quel secteur te parle le plus pour affiner l’analyse ?
```

---

### Q9 — Salaire moyen d'un cadre supérieur (PCS 37) ?

**Domain attendu** : `insee_salaire` (INSEE salaires PCS)

**Top-5 domain match** : ✓ 3/5 fiches du domain attendu
**Citations [source SX]** : 2
**Latence** : 4.26s

**Top-5 sources retrievées** :
```
  S1: [insee_salaire] insee_salaan:cs:37 [score=2.200]
  S2: [insee_salaire] insee_salaan:cs:34 [score=2.200]
  S3: [insee_salaire] insee_salaan:cs:33 [score=2.200]
  S4: [(formation)] Formation d'ingénieur Bac + 5 - Bac général — Polytech Paris-Saclay, Île-de-France [score=1.079]
  S5: [(formation)] Formation d'ingénieur Bac + 5 - bac général — CPBx (Bordeaux Sciences Agro.), Nouvelle-Aquitaine [score=1.073]
```

**Réponse du pipeline** :

```
Un cadre supérieur (PCS 37) perçoit en France un salaire net médian annuel de **45 000 €**, soit **3 750 € par mois** [source S1].

Cette catégorie compte **1 960 800 professionnels**, avec une répartition équilibrée entre hommes et femmes (50 % chacun). L’Île-de-France concentre près de la moitié des effectifs [source S1].

Ces données reflètent une moyenne nationale — les écarts peuvent être importants selon le secteur, la taille de l’entreprise ou la région. Est-ce que ce niveau de rémunération correspond à tes attentes ou à un projet précis ?
```

---

### Q10 — Insertion à 3 ans après un Bac pro Industrie ?

**Domain attendu** : `formation_insertion` (Inserjeunes lycée pro)

**Top-5 domain match** : ✓ 2/5 fiches du domain attendu
**Citations [source SX]** : 4
**Latence** : 4.87s

**Top-5 sources retrievées** :
```
  S1: [voie_pre_bac] voie_pre_bac_synthese:bac-pro [score=1.800]
  S2: [formation_insertion] inserjeunes_formation:bts:concepteur-en-art-industrie-ceramique [score=1.800]
  S3: [formation_insertion] inserjeunes_formation:bac-pro:logistique [score=1.800]
  S4: [(formation)] Formation d'ingénieur Bac + 5 - (en 6 ans) - Bac général — INSA Lyon, Auvergne-Rhône-Alpes [score=1.142]
  S5: [(formation)] Formation d'ingénieur Bac + 5 - bac  général et STI2D — ISA BTP, Nouvelle-Aquitaine [score=1.146]
```

**Réponse du pipeline** :

```
Ton intérêt pour l’insertion après un Bac Pro dans l’industrie est tout à fait pertinent, mais les données précises à 3 ans manquent souvent pour ces filières. Voici ce que je peux te partager :

- **Bac Pro Logistique** : 51,1 % des diplômés trouvent un emploi **12 mois après** le diplôme, et 56,6 % à **24 mois** [source S3]. Aucune donnée à 3 ans n’est disponible dans mes sources.
- **Catalogue global Bac Pro** : 87 spécialités existent, dont 22 en ingénierie industrielle, mais **aucune statistique d’insertion à 3 ans** n’est fournie [source S1].

Si tu cherches une voie avec des débouchés plus documentés, certaines écoles d’ingénieurs post-bac (comme l’**INSA Lyon** ou l’**ISA BTP**) offrent des taux d’accès en formation très variables (7 % [source S4] à 25 % [source S5]), mais sans données sur leur insertion à 3 ans non plus.

Qu’est-ce qui compte le plus pour toi : un diplôme avec des stats d’insertion solides (même à court terme) ou une formation qui te motive vraiment, même si les chiffres manquent ?

---
⚠️ **Points à vérifier dans ma réponse** :
- Mention manquante : 'taux d'accès' = rang du dernier appelé — La réponse cite un 'taux d'accès Parcoursup' sans préciser que c'est le rang du dernier candidat appelé (pas le taux d'admission). Nuance critique pour un lycéen.

Ces points sont des patterns que nous surveillons. Vérifie directement sur [ONISEP](https://www.onisep.fr) ou [Parcoursup](https://www.parcoursup.fr) avant toute décision.
```

---

### Q11 — Quelles sont les spécialités possibles en BAC PRO agriculture ?

**Domain attendu** : `voie_pre_bac` (Voie pré-bac catalogue)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 0
**Latence** : 3.53s

**Top-5 sources retrievées** :
```
  S1: [competences_certif] rncp_blocs:RNCP39195 [score=1.897]
  S2: [competences_certif] rncp_blocs:RNCP39906 [score=1.886]
  S3: [competences_certif] rncp_blocs:RNCP40825 [score=1.881]
  S4: [(formation)] BUT - Génie biologique Parcours agronomie — I.U.T Clermont Auvergne - site d'Aurillac, Auvergne-Rhône-Alpes [score=1.101]
  S5: [(formation)] Formation d'ingénieur Bac + 5 - Bacs technologiques — ESA - Ecole Supérieure des Agricultures (Paris-St Quentin), Île-de-France [score=1.085]
```

**Réponse du pipeline** :

```
Je n’ai pas de formation pertinente dans mes sources pour détailler les spécialités du **bac pro agriculture**. Mes données couvrent plutôt des cursus post-bac (BUT, écoles d’ingénieurs) en agronomie ou agriculture [source S4, S5].

Pour explorer les spécialités de bac pro (ex : productions végétales, élevage, agroéquipement), je te conseille de consulter :
- **ONISEP** (fiches métiers et diplômes)
- **Les sites des lycées agricoles** de ta région
- **Ton CIO** (Centre d’Information et d’Orientation) pour un accompagnement personnalisé.

Qu’est-ce qui t’attire dans l’agriculture : le travail du sol, l’élevage, les nouvelles technologies, ou autre ? Cela pourrait t’aider à affiner tes recherches.
```

---

### Q12 — Taux de réussite L1 pour un bac S avec mention bien ?

**Domain attendu** : `parcours_bacheliers` (MESR parcours bacheliers en licence)

**Top-5 domain match** : ✓ 3/5 fiches du domain attendu
**Citations [source SX]** : 2
**Latence** : 4.24s

**Top-5 sources retrievées** :
```
  S1: [parcours_bacheliers] parcours:staps|bac_professionnel|très_bien [score=2.040]
  S2: [parcours_bacheliers] parcours:santé|bac_technologique_hors_stmg|assez_bien [score=2.040]
  S3: [parcours_bacheliers] parcours:santé|bac_s|bien [score=2.040]
  S4: [(formation)] BTS - Production - Assistance technique d'ingénieur — Lycée professionnel Amiral Lacaze, La Réunion [score=1.207]
  S5: [(formation)] Licence - Langues, littératures et civilisations étrangères et régionales - Parcours  Anglais — Université de Rennes 2, Bretagne [score=1.121]
```

**Réponse du pipeline** :

```
Tu veux savoir comment se passent les études en licence pour un·e bachelier·e S avec mention Bien, notamment en termes de réussite en première année.

Pour la **licence en Santé** (uniquement cette formation dans mes sources) :
- **100 % des néobacheliers S mention Bien** passent en L2 en 1 an [source S3].
- Sur un suivi plus long (cohorte 2012), **75 % obtiennent leur licence en 3 ans** (ou 4 ans pour certains) [source S3].

Ces données concernent uniquement la licence Santé, mais elles montrent une bonne adaptation des profils S mention Bien à ce type de cursus.

Est-ce que cette filière t’intéresse, ou cherches-tu des infos sur d’autres domaines en particulier ?
```

---

### Q13 — Quelle insertion après un doctorat en chimie ?

**Domain attendu** : `insertion_pro` (Doctorat IP MESR)

**Top-5 domain match** : ✓ 3/5 fiches du domain attendu
**Citations [source SX]** : 3
**Latence** : 5.71s

**Top-5 sources retrievées** :
```
  S1: [insertion_pro] doctorat:chimie-et-sciences-des-materiaux:2016:hommes:12-mois-apres-le-diplome [score=1.800]
  S2: [insertion_pro] doctorat:chimie-et-sciences-des-materiaux:2014:hommes:36-mois-apres-le-diplome [score=1.800]
  S3: [insertion_pro] doctorat:chimie-et-sciences-des-materiaux:2016:hommes:36-mois-apres-le-diplome [score=1.800]
  S4: [(formation)] Licence - Portail Chimie - Physique Sciences pour l'Ingénieur - Chimie — Université Clermont Auvergne, Auvergne-Rhône-Alpes [score=1.180]
  S5: [(formation)] Licence - Double diplôme - Licence Chimie -  Chimie - Cursus intégré franco-allemand avec l'Université de Bielefeld — Université Paris Cité, Île-de-France [score=1.083]
```

**Réponse du pipeline** :

```
Je comprends que tu te demandes concrètement à quoi mène un doctorat en chimie, surtout après plusieurs années d’études. Voici ce que montrent les données pour les docteurs en **chimie et sciences des matériaux** (hommes, cohortes récentes) :

• **À 12 mois** : 83 % en emploi, dont 99 % en poste cadre et 46 % en CDI. Salaire médian net de **2200 €/mois** [source S1]. Près de la moitié (49 %) reste dans le secteur académique (recherche publique, enseignement supérieur), l’autre moitié se partage entre R&D privée (31 %) et opportunités à l’étranger (37 %).

• **À 36 mois** : l’insertion se consolide à **92-93 %**, avec une stabilité accrue (64-66 % en CDI) et des salaires médians entre **2394 € et 2500 €/mois** [source S2][source S3]. La R&D privée gagne du terrain (34 %), tandis que l’académique représente encore 38-43 % des débouchés.

Les secteurs porteurs (académique, industrie, international) offrent des perspectives variées, mais la mobilité géographique et la flexibilité sur le type de contrat en début de carrière sont souvent nécessaires.

Est-ce que ces chiffres te rassurent, ou bien est-ce que tu te demandes surtout comment *choisir entre académique et privé* après la thèse ?
```

---

## Décision Gate 3 (manuel)

Après lecture des 13 réponses ci-dessus, indiquer :
- ✓ GO promotion (toutes questions passent les 4 critères)
- ⚠ GO conditionnel (1-3 questions à expliquer mais corpus utilisable)
- ❌ NO-GO (≥4 questions avec hallu, info non disponible non-justifiée, ou top-K mal retrouvé)
