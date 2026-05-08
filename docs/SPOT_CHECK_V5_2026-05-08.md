# Spot-check Gate 3 v5 — 2026-05-08

> Phase C.5 (BLOQUANT pour promotion v5). 13 questions ciblées sur
> les domaines précédemment dormants. Évaluation manuelle requise.

## Résumé exécutif

- **Questions testées** : 13
- **Questions avec domain attendu présent dans top-5** : 11/13
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
**Citations [source SX]** : 4
**Latence** : 13.38s

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

• **Enseignement** : 33 961 postes à pourvoir d’ici 2030 en Occitanie, principalement liés aux départs en retraite (29 600). Un besoin structurel, même si les jeunes débutants pourraient être moins nombreux que les postes disponibles (-16 800) [source S2].

• **Formation professionnelle** : 6 345 postes attendus, avec une tension moyenne sur le marché. Les créations nettes (+1 914) et les départs (4 430) laissent une marge pour les nouveaux entrants, malgré un solde négatif pour les jeunes (-3 760) [source S3].

• **Direction d’entreprise** : 7 567 postes à pourvoir, dont 2 944 créations nettes. Les besoins en renouvellement (4 622 départs) contrastent avec une prévision de -1 380 jeunes débutants — un écart qui pourrait jouer en faveur des profils qualifiés [source S1].

Ces chiffres reflètent des dynamiques régionales, mais rien ne remplace une veille sur les formations qui y préparent (comme la licence Catalan à Perpignan [source S4], si les langues t’intéressent).

**Question pour toi** : parmi ces secteurs, lequel correspond le plus à tes aspirations *et* à tes points forts actuels ?
```

---

### Q2 — Combien coûte le logement étudiant CROUS à Lyon ?

**Domain attendu** : `crous` (CROUS corpus — résidences U et restos par zone)

**Top-5 domain match** : ✓ 3/5 fiches du domain attendu
**Citations [source SX]** : 2
**Latence** : 3.08s

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
Tu te demandes quel budget prévoir pour un logement CROUS à Lyon. Voici ce que je peux te dire :

- **Information sur les prix** : les données précises sur les tarifs des logements CROUS ne sont pas disponibles dans mes sources [source S1].
- **Offre de logements** : 9 résidences universitaires sont répertoriées dans la région lyonnaise [source S1].

Pour avancer, as-tu déjà consulté le site du CROUS Lyon ou envisagé de contacter directement leurs services pour obtenir les grilles tarifaires actualisées ?
```

---

### Q3 — Quels sont les blocs de compétences du RNCP 38450 ?

**Domain attendu** : `competences_certif` (France Compétences blocs RNCP)

**Top-5 domain match** : ✓ 3/5 fiches du domain attendu
**Citations [source SX]** : 1
**Latence** : 4.16s

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

En revanche, si tu cherches des informations sur des certifications RNCP en santé (comme l’ostéopathie [source S1/S2]) ou en informatique/ingénierie (ex : ISTY [source S3]), je peux t’éclairer sur ces parcours.

As-tu une idée du domaine ou du métier visé par ce RNCP ? Cela m’aiderait à t’orienter vers des alternatives documentées.
```

---

### Q4 — Quel salaire après un Master Droit en région PACA ?

**Domain attendu** : `insertion_pro` (InserSup spécifique discipline × région)

**Top-5 domain match** : ✓ 2/5 fiches du domain attendu
**Citations [source SX]** : 2
**Latence** : 4.7s

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
Tu te demandes quel salaire attendre après un **Master Droit en région PACA**. Voici ce que je peux te partager à partir des données disponibles :

- **Insertion à 6 mois** : Pour un **diplôme visé bac+5 en Droit/Sciences politiques** (Aix-Marseille Université), le taux d’emploi salarié est de **55 %** à 6 mois et **63 %** à 12 mois [source S2]. *En revanche, le salaire médian n’est pas précisé dans mes sources.*

- **Comparaison avec d’autres filières** : En PACA, un master en **Lettres/Arts** affiche un taux d’emploi de **44 %** à 6 mois [source S3], ce qui suggère que le droit offre une insertion légèrement plus favorable, mais sans garantie de rémunération élevée.

Aucune source ne mentionne de salaire exact pour ce master en PACA. Souhaites-tu explorer d’autres critères (débouchés, spécialisations) pour affiner ton choix ?
```

---

### Q5 — Que fait un actuaire au quotidien ?

**Domain attendu** : `metier_detail` (ROME 4.0 fiches métiers — compétences détaillées)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 2
**Latence** : 5.02s

**Top-5 sources retrievées** :
```
  S1: [metier] gestionnaire actif/passif [score=2.040]
  S2: [metier] ergothérapeute [score=2.040]
  S3: [metier] souscripteur/trice [score=2.040]
  S4: [(formation)] ACTUARIAT — Actuariat et Ingénierie Mathématique pour l'Assurance et la Finance — Université de Rouen Normandie, Normandie [score=0.981]
  S5: [(formation)] MONNAIE, BANQUE, FINANCE, ASSURANCE — Métiers de la banque de détail -  En Alternance (apprentissage et contrat pro) — Université de Lille, Hauts-de-France [score=0.940]
```

**Réponse du pipeline** :

```
Tu t’intéresses au métier d’actuaire, qui allie mathématiques, analyse des risques et stratégie financière. Voici ce qui caractérise son quotidien, d’après les métiers proches dans mes sources :

- **Analyse et modélisation des risques** : Comme le **gestionnaire actif/passif** (ALM), l’actuaire évalue les risques financiers pour des assureurs ou banques, en s’appuyant sur des données statistiques et des outils mathématiques. Son objectif ? Optimiser la performance tout en limitant les pertes [source S1].
- **Tarification et souscription** : À l’instar du **souscripteur/trice**, il participe à la définition des primes d’assurance ou des conditions de couverture, en analysant la probabilité de survenance des risques (santé, accidents, catastrophes naturelles) [source S3].
- **Conseil stratégique** : Ses rapports aident les directions à prendre des décisions éclairées, par exemple sur le lancement de nouveaux produits financiers ou la gestion des fonds de pension.

Ces missions s’inscrivent souvent dans des secteurs comme l’assurance, la réassurance, ou la finance — des environnements où la précision et la rigueur sont essentielles.

Est-ce que c’est plutôt l’aspect *technique* (modélisation, calculs) ou *stratégique* (conseil, prise de décision) qui t’attire dans ce métier ?
```

---

### Q6 — Quelles aides financières pour les étudiants boursiers ?

**Domain attendu** : `financement_etudes` (Financement curated dispositifs)

**Top-5 domain match** : ✓ 2/5 fiches du domain attendu
**Citations [source SX]** : 2
**Latence** : 5.01s

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
Je comprends que tu cherches des pistes concrètes pour financer tes études en tant qu’étudiant·e boursier·e. Voici les dispositifs identifiés dans mes sources :

• **Bourse sur critères sociaux CROUS** : accessible aux étudiant·es en formation initiale (BTS, BUT, licence, master, écoles d’ingénieurs/commerce). Les montants annuels varient entre **1080 € et 5965 €** (2024-2025) selon l’échelon `[source S3]`. Elle couvre aussi les formations en alternance sous conditions.

• **Prestations CAF pour étudiant·es parents** : si tu as un enfant, la **Prime à la Naissance (PreParE)** et les allocations (PAJE, APL) restent versées pendant les études, en complément d’une éventuelle bourse CROUS `[source S2]`. Les montants exacts dépendent de ta situation familiale (à vérifier sur [caf.fr](https://www.caf.fr)).

Aucune information n’est disponible dans mes sources sur les aides spécifiques aux formations en alternance ou les dispositifs régionaux.

Quelle est ta situation actuelle (niveau d’études, famille à charge, région) ? Cela pourrait aider à affiner les pistes.
```

---

### Q7 — Quelles formations en Guadeloupe ?

**Domain attendu** : `territoire_drom` (DROM-COM territoires)

**Top-5 domain match** : ✓ 3/5 fiches du domain attendu
**Citations [source SX]** : 4
**Latence** : 4.81s

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
Tu cherches des formations accessibles en Guadeloupe après le bac. Voici deux options concrètes, avec leurs spécificités locales :

• **Licence Humanités (parcours Histoire et sciences sociales, option prépa IEP)** à l’**Université des Antilles (Saint-Claude)** : formation non sélective (100 % d’accès en 2025 [source S4]), avec 100 places disponibles. 35 % des admis étaient en début de liste principale [source S4]. Idéal si tu vises les concours IEP ou une poursuite en master sciences sociales.

• **BTS Management en hôtellerie-restauration** au **Lycée Archipel Guadeloupe (Le Gosier)** : formation sélective (61 % d’accès en 2025 [source S5]), avec 36 places. 30 % des admis étaient en début de liste principale [source S5]. Secteur porteur localement, avec des débouchés dans le tourisme (1er employeur de l’île).

Pour affiner, est-ce que tu privilégies un parcours long (licence → master) ou une insertion professionnelle rapide (BTS) ? Et as-tu une préférence entre les sciences humaines et les métiers du service ?
```

---

### Q8 — Marché de l'emploi cadres en Bretagne ?

**Domain attendu** : `apec_region` (APEC régions)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 3
**Latence** : 8.19s

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
Tu t’intéresses aux perspectives d’emploi pour les cadres en Bretagne. Voici les tendances clés selon les projections DARES 2030 pour trois familles professionnelles :

• **Fonction publique** : 7 117 postes à pourvoir d’ici 2030 en Bretagne, mais avec un solde négatif pour les jeunes débutants (-5 913 postes), reflétant des départs en fin de carrière massifs (7 254) [source S1].
• **Agriculture** : Secteur dynamique avec 2 535 postes à pourvoir, dont 720 créations nettes, mais une tension très forte sur les recrutements (métier sur-représenté en Bretagne ×2 vs France) [source S2].
• **Banque/Assurances** : 2 467 postes attendus, mais un solde négatif pour les jeunes (-1 374) et une sous-représentation régionale (×0,66 vs France) [source S3].

Ces chiffres montrent des opportunités variables selon les secteurs, avec une forte concurrence pour les débutant·es dans la fonction publique et la finance.

Quels métiers cadres t’attirent particulièrement ? Cela pourrait affiner les pistes à explorer.
```

---

### Q9 — Salaire moyen d'un cadre supérieur (PCS 37) ?

**Domain attendu** : `insee_salaire` (INSEE salaires PCS)

**Top-5 domain match** : ✓ 3/5 fiches du domain attendu
**Citations [source SX]** : 2
**Latence** : 4.3s

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
Le salaire moyen d’un cadre administratif ou commercial (PCS 37) en France te concerne peut-être pour évaluer un projet professionnel ou une formation visée.

- **Salaire net médian annuel** : 45 000 €, soit **3 750 €/mois** [source S1].
- **Répartition genre** : 50 % de femmes dans cette catégorie [source S1].

Ces chiffres couvrent l’ensemble des cadres du secteur privé (hors fonction publique). Si tu envisages une formation spécifique, vérifie si ses débouchés correspondent bien à cette PCS.

Qu’est-ce qui t’attire dans ce type de poste — le relationnel client, la stratégie commerciale, ou autre chose ?
```

---

### Q10 — Insertion à 3 ans après un Bac pro Industrie ?

**Domain attendu** : `formation_insertion` (Inserjeunes lycée pro)

**Top-5 domain match** : ✓ 2/5 fiches du domain attendu
**Citations [source SX]** : 2
**Latence** : 5.82s

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
Ton questionnement sur l’insertion après un Bac Pro dans l’industrie est crucial, surtout pour évaluer la poursuite d’études ou l’entrée dans la vie active. Voici ce que montrent les données disponibles :

- **Logistique** : 51,1 % des diplômés trouvent un emploi **12 mois après le diplôme**, et 56,6 % à **24 mois** [source S3]. Une partie significative (41,3 %) choisit de poursuivre ses études, souvent vers des BTS ou licences pro.
- **Microtechniques** : L’insertion est plus lente avec **38,5 % en emploi à 12 mois** et **46,5 % à 24 mois** [source S2]. En revanche, **66,7 % continuent leurs études**, un taux élevé qui reflète peut-être des débouchés perçus comme limités sans spécialisation supplémentaire.

**Aucune source ne fournit de données à 3 ans** pour ces Bac Pro — les mesures s’arrêtent à 24 mois. Les chiffres suggèrent aussi que l’industrie logistique offre une insertion plus rapide que les microtechniques, mais avec des écarts régionaux possibles.

Qu’est-ce qui pèse le plus pour toi : la sécurité d’un emploi rapide, ou la possibilité de te spécialiser davantage après le Bac Pro ?
```

---

### Q11 — Quelles sont les spécialités possibles en BAC PRO agriculture ?

**Domain attendu** : `voie_pre_bac` (Voie pré-bac catalogue)

**Top-5 domain match** : ✓ 3/5 fiches du domain attendu
**Citations [source SX]** : 2
**Latence** : 5.24s

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
Tu t’intéresses aux spécialités du **BAC PRO agriculture** — un domaine qui couvre des métiers variés, du travail avec les animaux à l’aménagement des espaces verts.

Voici les **9 spécialités référencées** dans mes sources :
- **Aménagements paysagers** (création et entretien d’espaces verts)
- **Conduite d’activités d’élevage canin-félin** (soins, gestion de structures)
- **Conduite de productions aquacoles** (élevage de poissons, crustacés)
*(liste complète sur ONISEP via les liens fournis [source S1])*

Ces formations, d’une durée de **3 ans après la 3ᵉ**, mènent à un diplôme de **niveau 4** (équivalent bac) [source S3].

Qu’est-ce qui t’attire le plus dans ces options : le contact avec les animaux, le travail manuel en extérieur, ou la dimension technique (machinisme, gestion) ?
```

---

### Q12 — Taux de réussite L1 pour un bac S avec mention bien ?

**Domain attendu** : `parcours_bacheliers` (MESR parcours bacheliers en licence)

**Top-5 domain match** : ✓ 3/5 fiches du domain attendu
**Citations [source SX]** : 0
**Latence** : 3.56s

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

**Top-5 domain match** : ✓ 3/5 fiches du domain attendu
**Citations [source SX]** : 6
**Latence** : 5.26s

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
Je comprends que tu veux y voir plus clair sur les débouchés après un doctorat en chimie, surtout dans un domaine où l’investissement est long. Voici ce que montrent les données pour les docteurs en **chimie et sciences des matériaux** (hommes, cohortes récentes) :

• **À 12 mois** : 83 % en emploi [source S1], dont 99 % en poste cadre et 46 % en CDI. Salaire médian net de **2200 €/mois** [source S1]. Près de la moitié (49 %) travaille dans le secteur académique (universités, CNRS…), 31 % en R&D privée.
• **À 36 mois** : l’insertion progresse à 93 % [source S2], avec 66 % en emploi stable et un salaire médian de **2500 €/mois** [source S2]. La R&D privée (34 %) dépasse presque le secteur académique (38 %).

**Point notable** : L’international est une voie fréquente (37 % à 12 mois [source S1], 34 % à 36 mois [source S2]), notamment dans les laboratoires ou entreprises à l’étranger.

Ces chiffres concernent spécifiquement les hommes — si tu veux des données plus larges (mixte ou femmes), je te conseille de consulter directement les rapports MESR. Pour toi, est-ce que la perspective académique (recherche/enseignement) ou privée (R&D industrielle) t’attire le plus aujourd’hui ?
```

---

## Décision Gate 3 (manuel)

Après lecture des 13 réponses ci-dessus, indiquer :
- ✓ GO promotion (toutes questions passent les 4 critères)
- ⚠ GO conditionnel (1-3 questions à expliquer mais corpus utilisable)
- ❌ NO-GO (≥4 questions avec hallu, info non disponible non-justifiée, ou top-K mal retrouvé)
