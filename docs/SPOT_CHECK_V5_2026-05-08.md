# Spot-check Gate 3 v5 — 2026-05-08

> Phase C.5 (BLOQUANT pour promotion v5). 13 questions ciblées sur
> les domaines précédemment dormants. Évaluation manuelle requise.

## Résumé exécutif

- **Questions testées** : 13
- **Questions avec domain attendu présent dans top-5** : 8/13
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

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 4
**Latence** : 14.41s

**Top-5 sources retrievées** :
```
  S1: [formation_insertion] inserjeunes_formation_region:mc3:employe-traiteur:occitanie, OCCITANIE [score=1.726]
  S2: [formation_insertion] inserjeunes_formation_region:mc3:sommellerie:occitanie, OCCITANIE [score=1.726]
  S3: [formation_insertion] inserjeunes_region_diplome:occitanie:mc3, OCCITANIE [score=1.726]
  S4: [(formation)] Licence - Sociologie — Université de Perpignan Via Domitia, Occitanie [score=1.052]
  S5: [(formation)] METIERS DU LIVRE ET DE L'EDITION — None — Institut catholique de Toulouse, Occitanie [score=0.963]
```

**Réponse du pipeline** :

```
Tu t’interroges sur les métiers porteurs en Occitanie pour 2030. Mes données couvrent surtout les formations courtes (MC3) et quelques licences, avec des indicateurs récents — mais pas de projections à 6 ans.

Voici ce qui ressort des **formations avec insertion mesurée** aujourd’hui :
• **Employé·e traiteur** (MC3) : 75 % en emploi à 24 mois en Occitanie [source S1]. Un secteur en tension (restauration collective, traiteurs artisanaux), où les compétences pratiques sont recherchées.
• **Cuisinier·ère en desserts de restaurant** (MC3) : spécialité la plus représentée en Occitanie (44 cohortes suivies), avec un taux d’emploi régional à **69,4 % à 12 mois** [source S3]. La pâtisserie-restauration recrute activement.

Pour les **métiers du livre/édition** (master à Toulouse), aucune donnée d’insertion n’est disponible dans mes sources [source S5]. La sociologie (licence à Perpignan) affiche **100 % d’accès via Parcoursup** en 2025, mais sans visibilité sur les débouchés concrets [source S4].

**Question pour toi** : Préfères-tu te former sur un métier en tension *immédiate* (hôtellerie-restauration, services à la personne) ou miser sur un secteur plus niche (édition, social) malgré l’incertitude ?
```

---

### Q2 — Combien coûte le logement étudiant CROUS à Lyon ?

**Domain attendu** : `crous` (CROUS corpus — résidences U et restos par zone)

**Top-5 domain match** : ✓ 3/5 fiches du domain attendu
**Citations [source SX]** : 2
**Latence** : 6.04s

**Top-5 sources retrievées** :
```
  S1: [crous] crous_region:lyon [score=1.770]
  S2: [crous] crous_region:strasbourg [score=1.770]
  S3: [crous] crous_region:bordeaux [score=1.770]
  S4: [(formation)] Double diplôme  Sciences Po Lyon (Grade Master) - Licence  (Université Jean Monnet) — Sciences Po Lyon - Institut d'Etudes Politiques - campus de Saint-Etienne, Auvergne-Rhône-Alpes [score=1.156]
  S5: [(formation)] BUT - Génie civil - Construction durable — IUT Lyon1 Site de Villeurbanne Doua, Auvergne-Rhône-Alpes [score=1.054]
```

**Réponse du pipeline** :

```
Tu te renseignes sur les coûts de logement étudiant à Lyon via le CROUS, ce qui est essentiel pour anticiper ton budget.

Pour Lyon, mes sources ne précisent **pas les tarifs exacts** des logements CROUS (résidences universitaires ou studios). En revanche, voici ce que je peux te confirmer :
- **9 résidences universitaires** sont répertoriées dans la région lyonnaise [source S1].
- Le CROUS propose aussi des **36 points de restauration** (cafétérias, restaurants U) sur Lyon et Villeurbanne, ce qui peut réduire tes dépenses alimentaires [source S1].

**Pour obtenir les prix actualisés** (loyers, APL, critères d’éligibilité), je te conseille de consulter directement :
→ [Site du CROUS Lyon](https://www.crous-lyon.fr) (onglet *Logement*)
→ Ou le [portail national des résidences CROUS](https://trouverunlogement.lescrous.fr).

As-tu déjà identifié un quartier lyonnais en particulier pour tes recherches ?
```

---

### Q3 — Quels sont les blocs de compétences du RNCP 38450 ?

**Domain attendu** : `competences_certif` (France Compétences blocs RNCP)

**Top-5 domain match** : ✓ 3/5 fiches du domain attendu
**Citations [source SX]** : 0
**Latence** : 4.27s

**Top-5 sources retrievées** :
```
  S1: [competences_certif] rncp_blocs:RNCP40440 [score=1.949]
  S2: [competences_certif] rncp_blocs:RNCP37636 [score=1.949]
  S3: [competences_certif] rncp_blocs:RNCP41171 [score=1.949]
  S4: [(formation)] Manager des ressources humaines — TALIS COMPETENCES & CERTIFICATIONS [score=0.886]
  S5: [(formation)] Chef de projet géomatique — ATLAS SOUTENIR LES COMPETENCES [score=0.885]
```

**Réponse du pipeline** :

```
Je n’ai pas de formation associée au RNCP 38450 dans mes sources.

Si tu cherches des informations précises sur ce RNCP (blocs de compétences, métiers visés, etc.), je te conseille de consulter directement la fiche sur [France Compétences](https://www.francecompetences.fr/) ou de contacter l’organisme certificateur.

Quel est ton projet derrière cette recherche ? Peut-être puis-je t’orienter vers des alternatives proches dans mes données.
```

---

### Q4 — Quel salaire après un Master Droit en région PACA ?

**Domain attendu** : `insertion_pro` (InserSup spécifique discipline × région)

**Top-5 domain match** : ✓ 2/5 fiches du domain attendu
**Citations [source SX]** : 2
**Latence** : 5.58s

**Top-5 sources retrievées** :
```
  S1: [voie_pre_bac] voie_pre_bac:bac-pro:droit [score=1.727]
  S2: [insertion_pro] insersup:diplome-vise-niveau-bac-5-grade-master:droit-sciences-politiques:provence-alpes-cote-d-azur, Provence-Alpes-Côte d'Azur [score=1.719]
  S3: [insertion_pro] insersup:diplome-vise-niveau-bac-5-grade-master:lettres-sciences-du-langage-arts:provence-alpes-cote-d-azur, Provence-Alpes-Côte d'Azur [score=1.719]
  S4: [(formation)] DROIT PRIVE — Droit privé général — Université de Pau et des Pays de l'Adour, Nouvelle-Aquitaine [score=1.016]
  S5: [(formation)] DROIT INTERNATIONAL ET DROIT EUROPEEN — Droit de la mer et des activités maritimes (DMAM) — Université Côte d'Azur, Provence-Alpes-Côte d'Azur [score=1.002]
```

**Réponse du pipeline** :

```
Tu veux savoir à quoi t’attendre financièrement après un master en droit en région PACA. Voici ce que mes sources indiquent pour cette zone géographique :

- **Master en Droit, sciences politiques** (Aix-Marseille Université) : le taux d’emploi salarié atteint **63 % à 12 mois** après le diplôme, mais **aucune donnée sur le salaire médian** n’est disponible dans mes sources [source S2].
- Pour les spécialisations comme le **Droit international et européen (Droit de la mer, Université Côte d’Azur)**, aucune information salariale ou d’insertion n’est référencée [source S5].

Les chiffres d’insertion existent donc, mais les salaires précis restent **non communiqués** dans les données officielles que je consulte. Cela peut varier fortement selon le secteur (cabinet, entreprise, fonction publique) et la spécialisation.

Est-ce que la stabilité de l’emploi (taux CDI) ou le type de métier (juriste d’entreprise, avocat, etc.) t’intéresse autant que le salaire ?
```

---

### Q5 — Que fait un actuaire au quotidien ?

**Domain attendu** : `metier_detail` (ROME 4.0 fiches métiers — compétences détaillées)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 4
**Latence** : 6.71s

**Top-5 sources retrievées** :
```
  S1: [metier] actuaire [score=1.966]
  S2: [metier] gestionnaire de patrimoine [score=1.921]
  S3: [metier] actuaire [score=1.919]
  S4: [(formation)] ACTUARIAT — None — Université Gustave Eiffel, Île-de-France [score=0.977]
  S5: [(formation)] MONNAIE, BANQUE, FINANCE, ASSURANCE — Responsable de clientèle Professionnels et Agriculteurs — Université de Caen Normandie, Normandie [score=0.942]
```

**Réponse du pipeline** :

```
Tu t’intéresses au métier d’actuaire et veux savoir en quoi consiste son quotidien. C’est un métier où les mathématiques et la gestion des risques se rencontrent, souvent méconnu mais central dans les secteurs de l’assurance et de la finance.

- **Analyser et modéliser les risques** : L’actuaire utilise des **statistiques, algorithmes et outils de modélisation** pour évaluer les risques (accidents, maladies, catastrophes naturelles, etc.) et aider les entreprises à prendre des décisions éclairées — par exemple, fixer le prix d’une assurance ou ajuster les conditions d’un contrat `[source S1]`. Son travail repose sur une **double compétence** : maîtrise des **mathématiques appliquées** (probabilités, data science) et compréhension fine des **enjeux économiques ou sociaux** (réglementations, comportements des clients) `[source S3]`.

- **Conseiller les dirigeants** : Ses analyses servent à concevoir ou modifier des **contrats d’assurance**, mais aussi à anticiper des scénarios financiers complexes (retraites, investissements). Il/elle travaille souvent en équipe avec des juristes, des commerciaux ou des data scientists, et doit savoir traduire des données techniques en recommandations claires pour les décideurs `[source S1]`.

- **Secteurs et synonymes** : Le métier s’exerce principalement dans les **assurances** (code ROME C1105) ou la **banque/finance**, mais aussi dans des cabinets de conseil. Autres appellations possibles : *chargé·e d’études actuarielles*, *ingénieur·e en assurances* `[source S3]`.

Est-ce que c’est plutôt l’aspect **technique** (modélisation, data) ou l’aspect **stratégique** (conseil, prise de décision) qui t
```

---

### Q6 — Quelles aides financières pour les étudiants boursiers ?

**Domain attendu** : `financement_etudes` (Financement curated dispositifs)

**Top-5 domain match** : ✓ 1/5 fiches du domain attendu
**Citations [source SX]** : 1
**Latence** : 3.92s

**Top-5 sources retrievées** :
```
  S1: [financement_etudes] Aides au logement (APL, ALF, ALS) — étudiants [score=1.708]
  S2: [metier] ingénieur financier / ingénieure financière [score=1.706]
  S3: [metier] spécialiste des affaires réglementaires en chimie [score=1.707]
  S4: [(formation)] Licence - Parcours d'Accès Spécifique Santé (PASS) — Aix-Marseille Université - Site de Marseille Timone, Provence-Alpes-Côte d'Azur [score=1.018]
  S5: [(formation)] BTS - Agricole - Agronomie et cultures durables — Campus Natur'Alim - Lycée Chartres-La Saussaye, Centre [score=0.968]
```

**Réponse du pipeline** :

```
Je comprends que tu cherches des pistes concrètes pour financer tes études en tant qu’étudiant·e boursier·e. Voici ce que mes sources couvrent :

• **Aides au logement (APL/ALF/ALS)** : Accessibles aux étudiant·es locataires (résidence universitaire, parc privé, foyer), avec un montant variable selon tes ressources, ton loyer et ta zone géographique. Un simulateur est disponible pour estimer ton éligibilité `[source S1]`.

C’est la seule aide financière explicitement mentionnée dans mes données. Pour les bourses sur critères sociaux (CROUS), les aides d’urgence ou les dispositifs régionaux, **information non disponible dans mes sources**.

As-tu déjà exploré les aides de ta région ou de ton établissement ? Certaines universités proposent des fonds spécifiques.
```

---

### Q7 — Quelles formations en Guadeloupe ?

**Domain attendu** : `territoire_drom` (DROM-COM territoires)

**Top-5 domain match** : ✓ 3/5 fiches du domain attendu
**Citations [source SX]** : 2
**Latence** : 8.52s

**Top-5 sources retrievées** :
```
  S1: [territoire_drom] Guadeloupe [score=2.186]
  S2: [territoire_drom] Martinique [score=2.093]
  S3: [territoire_drom] Guyane [score=2.079]
  S4: [(formation)] Licence - Portail Physique, chimie - Physique chimie et applications, Sciences pour l'ingénieur — Université des Antilles - Pôle Guadeloupe, Guadeloupe [score=1.154]
  S5: [(formation)] BUT - Carrières sociales Parcours éducation spécialisée — I.U.T de la Guadeloupe - Campus de St-Claude, Guadeloupe [score=1.049]
```

**Réponse du pipeline** :

```
Tu explores les formations post-bac en Guadeloupe, un territoire où les opportunités locales peuvent correspondre à des projets variés. Voici deux options identifiées dans mes sources :

• **Licence – Portail Physique, Chimie et Sciences pour l’ingénieur** à l’**Université des Antilles (Pointe-à-Pitre)** : formation non sélective avec **40 places** en 2025 et un taux d’accès de **100 %** pour les candidat·es [source S4]. Idéal si tu vises une poursuite en master ou école d’ingénieur, avec une approche théorique et appliquée.

• **BUT Carrières sociales (parcours Éducation spécialisée)** à l’**IUT de Guadeloupe (Saint-Claude)** : cursus sélectif (**12 places**, **31 % d’accès en 2025**) [source S5], orienté vers les métiers du social et de l’accompagnement. Alternance possible dès la 2ᵉ année.

Ces deux formations sont **publiques** (frais réduits), mais leurs débouchés et publics cibles diffèrent fortement. Quel domaine te parle le plus : les sciences "dures" ou l’humain et le travail social ?

---
⚠️ **Points à vérifier dans ma réponse** :
- Mention manquante : 'taux d'accès' = rang du dernier appelé — La réponse cite un 'taux d'accès Parcoursup' sans préciser que c'est le rang du dernier candidat appelé (pas le taux d'admission). Nuance critique pour un lycéen.

Ces points sont des patterns que nous surveillons. Vérifie directement sur [ONISEP](https://www.onisep.fr) ou [Parcoursup](https://www.parcoursup.fr) avant toute décision.
```

---

### Q8 — Marché de l'emploi cadres en Bretagne ?

**Domain attendu** : `apec_region` (APEC régions)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 2
**Latence** : 4.74s

**Top-5 sources retrievées** :
```
  S1: [insertion_pro] insersup:diplome-grade-ou-vise-management-niveau-bac-5:sciences-economiques-gestion:bretagne, Bretagne [score=1.710]
  S2: [formation_insertion] inserjeunes_formation_region:bac-pro:accompagnement-soins-et-services-a-la-personne-option-a-a-do:bretagne, BRETAGNE [score=1.701]
  S3: [formation_insertion] inserjeunes_formation_region:bac-pro:accompagnement-soins-et-services-a-la-personne-option-b-en-s:bretagne, BRETAGNE [score=1.701]
  S4: [(formation)] Licence - Langues, littératures et civilisations étrangères et régionales - Parcours Breton - confirmé — Université de Rennes 2, Bretagne [score=1.022]
  S5: [(formation)] ECONOMIE DU TRAVAIL ET DES RESSOURCES HUMAINES — Territoire, Emploi et Ressources Humaines (TERH) — Université Rennes 2, Bretagne [score=0.951]
```

**Réponse du pipeline** :

```
Tu t’intéresses à l’insertion des profils cadres en Bretagne, notamment après des études en management ou économie. Voici ce que montrent les données disponibles dans mes sources pour des diplômés **bac+5** dans ces domaines :

- **Management (éco/gestion)** : 6 mois après le diplôme, **51 %** des sortants sont en emploi salarié, un taux qui atteint **64 % à 12 mois** [source S1]. Ces chiffres concernent spécifiquement les diplômés des écoles **Brest Business School** et **Rennes School of Business**.
- **Économie des ressources humaines** : aucune donnée d’insertion n’est disponible pour le master **TERH (Territoire, Emploi et Ressources Humaines)** à Rennes 2 dans mes sources [source S5].

Pour les **bac pro** du secteur social (ex : accompagnement soins et services), les taux d’emploi à 12 mois oscillent entre **46,9 % et 49,1 %** [sources S2/S3], mais ces profils ne correspondent pas à des postes cadres.

Ces éléments te donnent-ils une idée plus précise, ou souhaites-tu explorer d’autres filières en Bretagne ?
```

---

### Q9 — Salaire moyen d'un cadre supérieur (PCS 37) ?

**Domain attendu** : `insee_salaire` (INSEE salaires PCS)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 0
**Latence** : 1.35s

**Top-5 sources retrievées** :
```
```

**Réponse du pipeline** :

```
Je n'ai pas l'information sur salaire médian à l'embauche dans mes sources vérifiées.

Plusieurs formations matchent ta demande. Précise davantage (ville, établissement, niveau) pour que je puisse te donner le chiffre exact.
```

---

### Q10 — Insertion à 3 ans après un Bac pro Industrie ?

**Domain attendu** : `formation_insertion` (Inserjeunes lycée pro)

**Top-5 domain match** : ✓ 2/5 fiches du domain attendu
**Citations [source SX]** : 3
**Latence** : 9.04s

**Top-5 sources retrievées** :
```
  S1: [voie_pre_bac] voie_pre_bac:bac-pro:ingenierie-industrielle [score=1.727]
  S2: [formation_insertion] inserjeunes_formation:bac-pro:accompagnement-soins-et-services-a-la-personne [score=1.713]
  S3: [formation_insertion] inserjeunes_formation:bac-pro:accompagnement-soins-et-services-a-la-personne-option-a-a-do [score=1.713]
  S4: [(formation)] Formation d'ingénieur Bac + 5 - bac  général et STI2D — ISA BTP, Nouvelle Aquitaine [score=1.142]
  S5: [(formation)] Formation d'ingénieur Bac + 5 - (en 6 ans) - Bac général — INSA Lyon, Auvergne-Rhône-Alpes [score=1.137]
```

**Réponse du pipeline** :

```
Je comprends que tu cherches des données concrètes sur l’insertion après un Bac Pro dans l’industrie. Voici ce que je peux te partager à partir de mes sources :

- **Données générales Bac Pro Industrie** : Aucune statistique d’insertion à 3 ans n’est disponible dans mes sources pour les spécialités industrielles (ex. aéronautique, agroéquipement, carrosserie) `[source S1]`.
- **Comparaison avec un Bac Pro du secteur social** : Pour te donner un ordre d’idée, le Bac Pro *Accompagnement, soins et services à la personne* affiche un taux d’emploi de **44,1 % à 12 mois** et **49,2 % à 24 mois** `[source S3]`. Les données industrielles ne sont malheureusement pas aussi détaillées.

Si l’industrie t’intéresse vraiment, as-tu envisagé des formations post-bac comme un **BUT** ou une **école d’ingénieurs** (ex. ISA BTP à Anglet, accessible après un Bac STI2D) pour booster ton insertion ? `[source S4]`

Qu’est-ce qui t’attire le plus dans l’industrie : le technique, la gestion de projets, ou autre chose ?
```

---

### Q11 — Quelles sont les spécialités possibles en BAC PRO agriculture ?

**Domain attendu** : `voie_pre_bac` (Voie pré-bac catalogue)

**Top-5 domain match** : ✓ 1/5 fiches du domain attendu
**Citations [source SX]** : 3
**Latence** : 4.51s

**Top-5 sources retrievées** :
```
  S1: [voie_pre_bac] voie_pre_bac:bac-pro:agriculture [score=1.807]
  S2: [metier] halieute [score=1.779]
  S3: [metier] ingénieur / ingénieure en expérimentation et production végétales [score=1.777]
  S4: [(formation)] Ingénieur diplômé de l’Institut supérieur d’agriculture Rhône-Alpes — MINISTERE DE L'AGRICULTURE ET DE LA SOUVERAINETE ALIMENTAIRE [score=0.939]
  S5: [(formation)] diplôme d'État de paysagiste [score=0.853]
```

**Réponse du pipeline** :

```
Tu t’intéresses aux spécialités du **BAC PRO agriculture**, un diplôme qui ouvre sur des métiers concrets liés aux productions végétales, animales ou à l’aménagement des espaces. Voici les options identifiées dans mes sources :

• **BAC PRO aménagements paysagers** : pour travailler sur la création et l’entretien d’espaces verts, parcs ou jardins [source S1].
• **BAC PRO conduite d’activités d’élevage canin-félin (CAEHSCF)** : axé sur la gestion d’élevages ou de structures d’hébergement pour animaux de compagnie [source S1].
• **BAC PRO conduite de productions aquacoles** : spécialisé dans l’élevage de poissons, crustacés ou coquillages en milieu contrôlé [source S1].

D’autres spécialités existent (comme les productions végétales ou viticoles), mais elles ne figurent pas dans mes données actuelles. **Qu’est-ce qui t’attire le plus dans ces domaines : le contact avec les animaux, le travail de la terre, ou la gestion technique de projets ?**
```

---

### Q12 — Taux de réussite L1 pour un bac S avec mention bien ?

**Domain attendu** : `parcours_bacheliers` (MESR parcours bacheliers en licence)

**Top-5 domain match** : ✓ 3/5 fiches du domain attendu
**Citations [source SX]** : 0
**Latence** : 6.47s

**Top-5 sources retrievées** :
```
  S1: [parcours_bacheliers] parcours:staps|bac_professionnel|très_bien [score=1.715]
  S2: [parcours_bacheliers] parcours:santé|bac_technologique_hors_stmg|assez_bien [score=1.715]
  S3: [parcours_bacheliers] parcours:santé|bac_s|bien [score=1.715]
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

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 4
**Latence** : 6.63s

**Top-5 sources retrievées** :
```
  S1: [metier] responsable de laboratoire de contrôle en chimie [score=1.750]
  S2: [metier] parfumeur / parfumeuse [score=1.750]
  S3: [metier] responsable de fabrication en chimie [score=1.750]
  S4: [(formation)] CHIMIE — Chimie Analytique et Qualité — Université de Poitiers, Nouvelle-Aquitaine [score=1.018]
  S5: [(formation)] CHIMIE — Integrated research for advanced chemistry and materials — Université de Lille, Hauts-de-France [score=1.011]
```

**Réponse du pipeline** :

```
Tu t’interroges sur les débouchés après un doctorat en chimie, et c’est normal de vouloir clarifier les pistes avant de s’engager dans 3 ans de thèse. Mes sources ne fournissent pas de données chiffrées sur l’insertion post-doctorat (taux d’emploi, salaires, etc.) [toutes sources]. En revanche, voici les métiers et parcours compatibles avec ce niveau d’études dans le domaine :

• **Responsable de laboratoire de contrôle en chimie** : un poste qui implique la supervision des analyses, la gestion d’équipes et la validation des procédés. Ce métier s’inscrit dans le GFE *transformation des matériaux* et relève du code ROME *H1501* (direction de laboratoire) [source S1].
• **Responsable de fabrication en chimie** : orienté vers la production industrielle, ce rôle combine expertise technique et management (code ROME *H1206*). Les docteurs sont souvent recherchés pour leur capacité à innover dans les procédés [source S3].

Pour des masters en chimie (bac+5) qui pourraient précéder ou compléter une thèse, deux options publiques existent :
- **Master *Chimie Analytique et Qualité*** à l’**Université de Poitiers** [source S4].
- **Master *Integrated research for advanced chemistry and materials*** à l’**Université de Lille** [source S5].

Aucune donnée n’est disponible sur les salaires ou taux d’insertion spécifiques à ces parcours dans mes sources.

Qu’est-ce qui t’attire le plus : la recherche appliquée en laboratoire, la production industrielle, ou un autre aspect de la chimie ?
```

---

## Décision Gate 3 (manuel)

Après lecture des 13 réponses ci-dessus, indiquer :
- ✓ GO promotion (toutes questions passent les 4 critères)
- ⚠ GO conditionnel (1-3 questions à expliquer mais corpus utilisable)
- ❌ NO-GO (≥4 questions avec hallu, info non disponible non-justifiée, ou top-K mal retrouvé)
