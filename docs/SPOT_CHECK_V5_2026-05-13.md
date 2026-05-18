# Spot-check Gate 3 v5 — 2026-05-13

> Phase C.5 (BLOQUANT pour promotion v5). 13 questions ciblées sur
> les domaines précédemment dormants. Évaluation manuelle requise.

## Résumé exécutif

- **Questions testées** : 13
- **Questions avec domain attendu présent dans top-5** : 4/13
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
**Citations [source SX]** : 3
**Latence** : 12.03s

**Top-5 sources retrievées** :
```
  S1: [(formation)] Licence - Langues, littératures et civilisations étrangères et régionales - Parcours Occitan — Université Paul Valery - Montpellier 3, Occitanie [score=1.083]
  S2: [(formation)] MANAGEMENT SECTORIEL — Management de l’Adaptation Climatique des Organisations en Méditerranée — Université de Montpellier, Occitanie [score=0.972]
  S3: [(formation)] METIERS DE L'ENTREPRENEURIAT (LP) — CHAMBRE DE METIERS ET DE L'ARTISANAT DE REGION OCCITANIE [score=0.823]
  S4: [(formation)] METIERS DU LIVRE ET DE L'EDITION — None — Université de Montpellier Paul-Valéry, Occitanie [score=0.970]
  S5: [(formation)] METIERS DE L'ENSEIGNEMENT, DE L'EDUCATION ET DE LA FORMATION (MEEF), 1ER DEGRE — Premier degré - Langues Régionales occitan et catalan (catalan sur le site de Perpignan, occitan sur les sites de Carcassonne et Mende) — Université de Montpellier, Occitanie [score=0.975]
```

**Réponse du pipeline** :

```
Je comprends que tu cherches à anticiper les secteurs porteurs en Occitanie pour construire un projet solide. Voici les pistes qui émergent dans mes sources, même si les données sur les métiers *futurs* (2030) sont limitées :

• **Enseignement et transmission des langues régionales** :
  Le [master MEEF 1er degré - Langues Régionales (occitan/catalan)](https://www.monmaster.gouv.fr/) à Carcassonne ou Mende [source S5] forme aux métiers de professeur des écoles bilingue (occitan ou catalan). Un secteur soutenu par les politiques éducatives locales, avec des besoins spécifiques en zones rurales.

• **Adaptation climatique et transition écologique** :
  Le [master Management de l’Adaptation Climatique des Organisations en Méditerranée](https://www.monmaster.gouv.fr/) à Montpellier [source S2] prépare aux métiers émergents de *responsable RSE*, *chargé·e de mission transition écologique* ou *consultant·e en adaptation climatique* — des postes en croissance avec les obligations légales des entreprises.

• **Métiers du livre et de l’édition** :
  Le [master Métiers du Livre et de l’Édition](https://www.monmaster.gouv.fr/) à Montpellier [source S4] ouvre aux métiers de *chargé·e d’édition*, *libraire spécialisé·e* ou *médiateur·trice culturelle*, avec un ancrage fort dans l’écosystème occitan (maisons d’édition locales, festivals).

**Attention** : mes sources ne donnent pas de chiffres d’insertion ou de projections 2030. Pour affiner, je te conseille de croiser avec les [études de la Région Occitanie](https://www.laregion.fr/) ou les rapports Pôle Emploi sur les métiers en tension.

Quelle dimension te parle le plus : *transmettre* (enseignement), *agir* (climat) ou *créer* (édition/culture) ?
```

---

### Q2 — Combien coûte le logement étudiant CROUS à Lyon ?

**Domain attendu** : `crous` (CROUS corpus — résidences U et restos par zone)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 0
**Latence** : 4.12s

**Top-5 sources retrievées** :
```
  S1: [(formation)] Sciences Po / Instituts d'études politiques - Sciences Humaines et Sociales - Grade Master - Cursus général — Sciences Po Lyon - Institut d'Etudes Politiques - campus de Lyon, Auvergne-Rhône-Alpes [score=1.163]
  S2: [(formation)] Licence professionnelle - Métiers de l'Immobilier - Gestion et administration de biens — Université Jean Moulin Lyon 3, Auvergne-Rhône-Alpes [score=1.095]
  S3: [(formation)] Double diplôme  Sciences Po Lyon (Grade Master) - Licence  (Université Jean Monnet) — Sciences Po Lyon - Institut d'Etudes Politiques - campus de Saint-Etienne, Auvergne-Rhône-Alpes [score=1.156]
  S4: [(formation)] Licence - Langues, littératures et civilisations étrangères et régionales - Parcours Chinois - Grands débutants (cursus 4 ans) — Université Jean Moulin Lyon 3, Auvergne-Rhône-Alpes [score=1.055]
  S5: [(formation)] BUT - Management de la Logistique et des Transports — I.U.T LUMIERE Lyon 2, Auvergne-Rhône-Alpes [score=1.058]
```

**Réponse du pipeline** :

```
Je n'ai pas de formation ni d'information sur les logements CROUS à Lyon dans mes sources.

Pour obtenir ces données, je te conseille de consulter directement :
- Le site du [CROUS Lyon](https://www.crous-lyon.fr/)
- La plateforme **Trouver un logement étudiant** sur [messervices.etudiant.gouv.fr](https://messervices.etudiant.gouv.fr/)
- Ou de contacter le CIO de ton lycée pour un accompagnement personnalisé.

Tu cherches un studio, une coloc, ou un logement en résidence universitaire en particulier ?
```

---

### Q3 — Quels sont les blocs de compétences du RNCP 38450 ?

**Domain attendu** : `competences_certif` (France Compétences blocs RNCP)

**Top-5 domain match** : ✓ 5/5 fiches du domain attendu
**Citations [source SX]** : 2
**Latence** : 3.84s

**Top-5 sources retrievées** :
```
  S1: [competences_certif] rncp_blocs:RNCP35298 [score=1.041]
  S2: [competences_certif] rncp_blocs:RNCP35307 [score=1.041]
  S3: [competences_certif] rncp_blocs:RNCP35329 [score=1.041]
  S4: [competences_certif] rncp_blocs:RNCP35575 [score=1.041]
  S5: [competences_certif] rncp_blocs:RNCP35583 [score=1.041]
```

**Réponse du pipeline** :

```
Je n'ai pas d'information sur le **RNCP 38450** dans mes sources actuelles. Les certifications disponibles concernent d'autres codes (ex: RNCP35298 pour *Responsable de chantier de dépollution pyrotechnique* [source S1], RNCP35583 pour *Technicien informatique systèmes et réseaux* [source S5]).

Pour obtenir les blocs de compétences précis du RNCP 38450, je te conseille de consulter directement la [fiche officielle sur France Compétences](https://www.francecompetences.fr/) ou de contacter un conseiller en évolution professionnelle (CEP). Quel métier ou domaine te intéresse derrière cette certification ?
```

---

### Q4 — Quel salaire après un Master Droit en région PACA ?

**Domain attendu** : `insertion_pro` (InserSup spécifique discipline × région)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 0
**Latence** : 5.46s

**Top-5 sources retrievées** :
```
  S1: [(formation)] DROIT — Droit public et carrières publiques — Aix-Marseille Université, Provence-Alpes-Côte d'Azur [score=1.024]
  S2: [(formation)] DROIT INTERNATIONAL ET DROIT EUROPEEN — Droit et pratique du commerce international (DPCI) — Université Côte d'Azur, Provence-Alpes-Côte d'Azur [score=1.001]
  S3: [(formation)] DROIT — Métiers du droit — Avignon Université, Provence-Alpes-Côte d'Azur [score=1.017]
  S4: [(formation)] DROIT PRIVE — Droit privé — Université Côte d'Azur, Provence-Alpes-Côte d'Azur [score=1.013]
  S5: [(formation)] ECONOMIE DU DROIT — None — Aix-Marseille Université, Provence-Alpes-Côte d'Azur [score=1.008]
```

**Réponse du pipeline** :

```
D’après tes critères, tu cherches à connaître les salaires après un **master en droit en région PACA**. Voici ce que je peux te partager à partir des données disponibles :

- **Aucune information salariale** (médiane à l’embauche ou autre) n’est disponible dans mes sources pour les masters en droit en PACA. Les fiches des formations comme le **[DROIT — Droit public et carrières publiques à Aix-Marseille Université](information non disponible dans mes sources)** ou le **[DROIT INTERNATIONAL — Droit et pratique du commerce international à Université Côte d'Azur](information non disponible dans mes sources)** ne précisent pas ces données.

- Les masters en droit de la région (ex : **DROIT PRIVE** à Nice ou **Métiers du droit** à Avignon) sont tous publics, donc avec des frais d’inscription modérés, mais leurs débouchés salariaux ne sont pas renseignés ici.

Pour affiner ta recherche, as-tu une spécialisation précise en tête (droit public, privé, international) ou préfères-tu explorer d’autres critères comme les taux d’insertion ?
```

---

### Q5 — Que fait un actuaire au quotidien ?

**Domain attendu** : `metier_detail` (ROME 4.0 fiches métiers — compétences détaillées)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 4
**Latence** : 14.51s

**Top-5 sources retrievées** :
```
  S1: [metier] actuaire [score=0.021]
  S2: [metier] gestionnaire de patrimoine [score=0.021]
  S3: [metier] actuaire [score=0.021]
  S4: [metier] ingénieur financier / ingénieure financière [score=0.020]
  S5: [metier] responsable des produits structurés actions [score=0.020]
```

**Réponse du pipeline** :

```
Tu t’intéresses au métier d’[actuaire](https://www.onisep.fr/http/redirection/metier/slug/MET.861) et veux savoir en quoi consiste son quotidien. Voici les missions clés, tirées des fiches ONISEP :

- **Concevoir et ajuster des contrats d’assurance** : l’actuaire utilise des modèles statistiques pour évaluer les risques (santé, accidents, catastrophes naturelles) et proposer des tarifs adaptés aux assureurs. Son travail permet de garantir l’équilibre financier des contrats [source S1][source S3].
- **Analyser des données pour anticiper les tendances** : à partir de bases de données (sinistres, comportements clients), il/elle identifie des patterns et simule des scénarios futurs (ex : impact d’une épidémie sur les remboursements). Ces analyses aident les dirigeants à prendre des décisions stratégiques [source S1].
- **Collaborer avec d’autres services** : l’actuaire travaille souvent avec les équipes commerciales (pour expliquer les tarifs), juridiques (pour respecter les réglementations) ou informatiques (pour optimiser les outils de modélisation).

Ce métier allie **mathématiques poussées**, **sens du conseil** et **compréhension des enjeux business** — idéal si tu aimes les chiffres *et* leur traduction concrète.

Est-ce que c’est plutôt l’aspect **technique** (modélisation, algorithmes) ou **stratégique** (négociation avec les assureurs) qui t’attire dans ce rôle ? [source S3]
```

---

### Q6 — Quelles aides financières pour les étudiants boursiers ?

**Domain attendu** : `financement_etudes` (Financement curated dispositifs)

**Top-5 domain match** : ✓ 5/5 fiches du domain attendu
**Citations [source SX]** : 3
**Latence** : 5.98s

**Top-5 sources retrievées** :
```
  S1: [financement_etudes] Aides au logement (APL, ALF, ALS) — étudiants [score=0.708]
  S2: [financement_etudes] Aide à la première installation (CROUS) [score=0.700]
  S3: [financement_etudes] Aide à la mobilité internationale (CROUS / Erasmus+) [score=0.685]
  S4: [financement_etudes] Aide à la mobilité Master [score=0.680]
  S5: [financement_etudes] Bourse sur critères sociaux CROUS — enseignement supérieur [score=0.680]
```

**Réponse du pipeline** :

```
Je comprends que tu cherches à sécuriser ton budget pour tes études. Voici les dispositifs **spécifiques aux étudiants boursiers** que je peux te confirmer :

• **Bourse sur critères sociaux CROUS** : accessible aux étudiants post-bac (BTS, BUT, Licence, Master, etc.) avec des montants annuels variant entre **1080 € et 5965 €** (2024-2025), selon les revenus du foyer [source S5]. C’est l’aide de base à demander en priorité.

• **Aide à la mobilité Master** : si tu es boursier·e et que tu changes de région pour ton Master, un forfait de **1000 €** est prévu (2024-2025) [source S4]. Utile pour couvrir une partie des frais de déménagement ou de double loyer.

• **Aides au logement (APL/ALS/ALF)** : même si tu es boursier·e, tu peux cumuler avec ces aides pour réduire ton loyer (montant variable selon ta situation) [source S1].

*Question pour toi* : As-tu déjà fait une simulation sur [mesdroitssociaux.gouv.fr](https://www.mesdroitssociaux.gouv.fr) pour voir à quelles aides tu pourrais prétendre en combinant ces dispositifs ?
```

---

### Q7 — Quelles formations en Guadeloupe ?

**Domain attendu** : `territoire_drom` (DROM-COM territoires)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 5
**Latence** : 7.89s

**Top-5 sources retrievées** :
```
  S1: [(formation)] Licence - Portail Sciences de la vie et de la terre - Biologie des organismes et Ecologie  / Biologie générale et sciences de la terre et de l’univers / Géo-sciences, géo-risques, géo-environnements — Université des Antilles - Pôle Guadeloupe, Guadeloupe [score=1.080]
  S2: [(formation)] Licence - Portail Sciences et Techniques des Activités Physiques et Sportives - Activités physiques adaptées et santé (APAS) — Université des Antilles - Pôle Guadeloupe, Guadeloupe [score=1.069]
  S3: [(formation)] Licence - Portail Economie et gestion - Eco de l'environnement et aménagement du territoire/Expertise éco,financière et managériale/Préparation aux métiers de l'enseignement - Guadeloupe — Université des Antilles - Pôle Guadeloupe, Guadeloupe [score=1.077]
  S4: [(formation)] Licence - Portail Mathématiques - Mathématiques appliquées aux sciences / Mathématiques pour l'enseignement  - Guadeloupe — Université des Antilles - Pôle Guadeloupe, Guadeloupe [score=1.071]
  S5: [(formation)] Licence - Portail Sciences pour la santé -  Biochimie - Sciences de l'aliment (BSA) / Sciences de la santé (BSS)  - Guadeloupe — Université des Antilles - Pôle Guadeloupe, Guadeloupe [score=1.069]
```

**Réponse du pipeline** :

```
Tu cherches des formations accessibles en Guadeloupe après le bac. Voici les options disponibles dans mes sources, toutes proposées par **[l’Université des Antilles - Pôle Guadeloupe](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=11749&typeBac=0&originePc=0)** à Pointe-à-Pitre :

• **Sciences fondamentales et santé** :
  - [Licence Portail Sciences de la vie et de la terre](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=11749&typeBac=0&originePc=0) (3 parcours : biologie, géosciences, etc.) avec **100 places** [source S1].
  - [Licence Portail Sciences pour la santé](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=11742&typeBac=0&originePc=0) (biochimie, sciences de l’aliment, santé) avec **150 places** [source S5].
  - [Licence Portail Mathématiques](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=36146&typeBac=0&originePc=0) (maths appliquées ou enseignement) avec **15 places** [source S4].

• **Économie, gestion et sport** :
  - [Licence Portail Économie et gestion](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=39484&typeBac=0&originePc=0) (3 parcours dont environnement/aménagement) avec **250 places** [source S3].
  - [Licence STAPS - APAS](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=36152&typeBac=0&originePc=0) (sport adapté et santé) avec **50 places** [source S2].

Toutes ces licences sont **non sélectives** à l’entrée (taux d’accès à 100 % pour la plupart [sources S1/S3/S4/S5]), mais les effectifs varient fortement. Frais d’inscription et débouchés non précisés dans mes sources.

Quel domaine t’attire le plus parmi ces propositions ? Ou souhaites-tu des précisions sur un parcours en particulier ?
```

---

### Q8 — Marché de l'emploi cadres en Bretagne ?

**Domain attendu** : `apec_region` (APEC régions)

**Top-5 domain match** : ✓ 1/5 fiches du domain attendu
**Citations [source SX]** : 4
**Latence** : 16.23s

**Top-5 sources retrievées** :
```
  S1: [apec_region] apec_region:bretagne, Bretagne [score=0.681]
```

**Réponse du pipeline** :

```
D’après les dernières données, le marché des cadres en Bretagne montre une dynamique positive malgré un contexte national plus morose.

- **Recrutements 2025** : 9 990 postes (+5 % vs 2024), à contre-courant de la tendance nationale (-3 %) [source S1].
- **Prévisions 2026** : 10 200 recrutements (+2 %), ce qui permettrait de retrouver le niveau record de 2023 (10 290 postes) [source S1].
- **Créations nettes** : 2 910 postes en 2025 (contre 3 230 en 2024) [source S1].
- **Secteurs porteurs** : exploitation tertiaire (21 %), commercial-marketing (16 %), études-R&D (15 %), informatique (14 %), production [source S1].

Ces chiffres suggèrent une région attractive pour les profils cadres, notamment dans les services et le numérique. Quels secteurs ou métiers t’intéressent plus particulièrement pour affiner l’analyse ?
```

---

### Q9 — Salaire moyen d'un cadre supérieur (PCS 37) ?

**Domain attendu** : `insee_salaire` (INSEE salaires PCS)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 0
**Latence** : 28.25s

**Top-5 sources retrievées** :
```
```

**Réponse du pipeline** :

```
Je n'ai pas de formation ni de données salariales pertinentes dans mes sources pour répondre à ta question sur le salaire moyen d'un cadre supérieur (PCS 37).

Pour des chiffres officiels, je te conseille de consulter :
- Les **études INSEE** (tableaux "Revenus et patrimoine des ménages")
- Les **rapports APEC** sur les rémunérations cadres
- Le **site de la Dares** (Ministère du Travail)

Tu cherches ces infos pour un projet précis ou par curiosité ? 😊
```

---

### Q10 — Insertion à 3 ans après un Bac pro Industrie ?

**Domain attendu** : `formation_insertion` (Inserjeunes lycée pro)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 0
**Latence** : 14.19s

**Top-5 sources retrievées** :
```
  S1: [insertion_pro] doctorat:biologie-medecine-et-sante:2014:femmes-et-hommes:12-mois-apres-le-diplome [score=0.663]
  S2: [insertion_pro] doctorat:biologie-medecine-et-sante:2014:femmes-et-hommes:36-mois-apres-le-diplome [score=0.663]
  S3: [insertion_pro] doctorat:biologie-medecine-et-sante:2014:femmes:12-mois-apres-le-diplome [score=0.663]
  S4: [insertion_pro] doctorat:biologie-medecine-et-sante:2014:femmes:36-mois-apres-le-diplome [score=0.663]
  S5: [insertion_pro] doctorat:biologie-medecine-et-sante:2014:hommes:12-mois-apres-le-diplome [score=0.663]
```

**Réponse du pipeline** :

```
Je n’ai pas de données dans mes sources sur l’insertion après un **Bac pro Industrie** (ni à 3 ans, ni à d’autres horizons). Mes chiffres concernent uniquement des docteurs en **biologie, médecine et santé** (Bac+8), avec des profils très différents du tien.

Pour explorer les débouchés après un Bac pro Industrie, je te conseille :
- Le site de l’**[ONISEP](https://www.onisep.fr/)** (fiches métiers et parcours par secteur)
- Les enquêtes **insertion** de ta région (ex : Observatoires régionaux de l’emploi)
- Un **RDV avec un·e conseiller·ère du CIO** ou de ta mission locale pour des données locales précises

Quel type d’industrie ou de métier te fait envie ? Ça peut aider à affiner les pistes.
```

---

### Q11 — Quelles sont les spécialités possibles en BAC PRO agriculture ?

**Domain attendu** : `voie_pre_bac` (Voie pré-bac catalogue)

**Top-5 domain match** : ✓ 1/5 fiches du domain attendu
**Citations [source SX]** : 0
**Latence** : 16.7s

**Top-5 sources retrievées** :
```
  S1: [voie_pre_bac] voie_pre_bac:bac-pro:agriculture [score=0.807]
  S2: [(formation)] conseiller en gestion d’entreprise agri-agro [score=0.805]
  S3: [(formation)] bac pro forêt [score=0.780]
  S4: [(formation)] bac pro cultures marines [score=0.774]
  S5: [(formation)] bac pro aménagements paysagers [score=0.780]
```

**Réponse du pipeline** :

```
D’après tes centres d’intérêt pour l’agriculture, voici les spécialités de **BAC PRO** référencées dans mes sources, toutes accessibles en 3 ans [source S3/S4/S5] :

• **[BAC pro aménagements paysagers](https://www.onisep.fr/http/redirection/formation/slug/FOR.7681)** : pour travailler sur la création et l’entretien d’espaces verts, parcs ou jardins.
• **[BAC pro forêt](https://www.onisep.fr/http/redirection/formation/slug/FOR.7418)** : axé sur la gestion des espaces boisés, l’exploitation forestière et la préservation des écosystèmes.
• **[BAC pro cultures marines](https://www.onisep.fr/http/redirection/formation/slug/FOR.1083)** : spécialisé dans l’élevage et la production d’organismes aquatiques (poissons, crustacés, algues).
• **BAC pro conduite d’activités d’élevage canin-félin** ou **aquacole** : deux autres options mentionnées, mais sans lien direct dans mes sources.

Ces formations te permettent une insertion directe ou une poursuite en BTS. Laquelle de ces thématiques (végétal, animal, forêt, mer) te parle le plus ?
```

---

### Q12 — Taux de réussite L1 pour un bac S avec mention bien ?

**Domain attendu** : `parcours_bacheliers` (MESR parcours bacheliers en licence)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 0
**Latence** : 5.37s

**Top-5 sources retrievées** :
```
  S1: [(formation)] BTS - Production - Assistance technique d'ingénieur — Lycée professionnel Amiral Lacaze, Réunion [score=1.207]
  S2: [(formation)] Licence - Langues, littératures et civilisations étrangères et régionales - Parcours  Anglais — Université de Rennes 2, Bretagne [score=1.114]
  S3: [(formation)] Licence - Histoire — Université de La Réunion - Saint Denis, Réunion [score=1.120]
  S4: [(formation)] Licence - Information et communication — Université de La Réunion - Saint Denis, Réunion [score=1.114]
  S5: [(formation)] BUT - Hygiène Sécurité Environnement — I.U.T de la Réunion, Réunion [score=1.105]
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
**Citations [source SX]** : 0
**Latence** : 9.46s

**Top-5 sources retrievées** :
```
  S1: [(formation)] CHIMIE — Chimie Analytique et Qualité — Université de Poitiers, Nouvelle-Aquitaine [score=0.022]
  S2: [(formation)] CHIMIE — None — Sorbonne Université, Île-de-France [score=0.021]
  S3: [(formation)] CHIMIE — M1 - Chemistry and Interfaces — Institut polytechnique de Paris, Île-de-France [score=0.021]
  S4: [(formation)] CHIMIE — Integrated research for advanced chemistry and materials — Université de Lille, Hauts-de-France [score=0.020]
  S5: [(formation)] CHIMIE — Physico-Chimie moléculaire et applications — Université Paris-Est Créteil, Île-de-France [score=0.020]
```

**Réponse du pipeline** :

```
Je comprends que tu te demandes concrètement à quoi mène un doctorat en chimie après plusieurs années d’études. Malheureusement, **mes sources ne fournissent aucune donnée sur l’insertion professionnelle après un doctorat** (taux d’emploi, CDI, salaires, etc.) pour les masters en chimie listés [source S1 à S5].

Ce que je peux te dire en revanche :
- Les masters proposés couvrent des spécialités variées (chimie analytique, interfaces, matériaux, etc.), souvent en **statut public** (ex : [CHIMIE — Chimie Analytique et Qualité à l’Université de Poitiers](information non disponible dans mes sources), [CHIMIE — Integrated research for advanced chemistry and materials à l’Université de Lille](information non disponible dans mes sources)). Ces parcours peuvent préparer à une thèse, mais **je n’ai pas d’informations sur leur suite en doctorat**.
- Pour explorer les débouchés *post-doctorat*, je te conseille de consulter directement :
  • Les **enquêtes insertion** des écoles doctorales (ex : [ED 388 "Chimie Physique et Chimie Analytique"](https://www.ed388.upmc.fr/) pour l’Île-de-France).
  • Les fiches métiers **ONISEP** (ex : [Chercheur·e en chimie](https://www.onisep.fr/), [Ingénieur·e R&D](https://www.onisep.fr/)) pour des données sectorielles.

**Question pour toi** : As-tu une idée du domaine qui t’attire le plus (recherche académique, industrie, start-up) ? Cela pourrait affiner les pistes.
```

---

## Décision Gate 3 (manuel)

Après lecture des 13 réponses ci-dessus, indiquer :
- ✓ GO promotion (toutes questions passent les 4 critères)
- ⚠ GO conditionnel (1-3 questions à expliquer mais corpus utilisable)
- ❌ NO-GO (≥4 questions avec hallu, info non disponible non-justifiée, ou top-K mal retrouvé)
