# Spot-check Gate 3 v5 — 2026-05-13

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

**Top-5 domain match** : ✓ 5/5 fiches du domain attendu
**Citations [source SX]** : 4
**Latence** : 31.72s

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
D’ici 2030, l’Occitanie devrait offrir des opportunités variées, avec des besoins marqués dans plusieurs secteurs clés. Voici les métiers les plus porteurs selon les projections régionales :

• **Santé** : Les **infirmiers et sages-femmes** concentreront **27 588 postes à pourvoir** (créations nettes + départs), avec une tension moyenne sur le marché [source S4]. Un secteur stable, idéal si tu cherches un métier à impact social et une insertion solide.

• **Industrie et technique** : Les **ingénieurs et cadres techniques de l’industrie** verront **17 233 postes** ouverts, dont **10 235 créations nettes** — un signe de dynamisme pour les profils qualifiés [source S5]. À explorer si les innovations technologiques ou la production t’attirent.

• **Métiers manuels spécialisés** : Les **ouvriers qualifiés en enlèvement de métal** (usinage, mécanique) afficheront **1 585 postes**, malgré un léger déclin net (-37 postes). Les départs en retraite (**1 622**) laisseront des places, surtout pour des profils formés [source S2].

*Attention* : Certains métiers comme **marins/pêcheurs** (275 postes [source S3]) restent très localisés (littoral) et en tension forte, mais avec peu de créations nettes.

**Qu’est-ce qui correspond le mieux à tes envies** : un métier **de terrain** (santé, industrie), **technique** (ingénierie), ou plutôt **artisanal** (mécanique, usinage) ?
```

---

### Q2 — Combien coûte le logement étudiant CROUS à Lyon ?

**Domain attendu** : `crous` (CROUS corpus — résidences U et restos par zone)

**Top-5 domain match** : ✓ 5/5 fiches du domain attendu
**Citations [source SX]** : 2
**Latence** : 7.09s

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
D’après tes critères, tu cherches à anticiper le budget pour un logement **CROUS à Lyon**. Voici ce que je peux te partager :

- **Coût du logement** : information non disponible dans mes sources.
  Le [CROUS Lyon](https://www.crous-lyon.fr/) propose **9 résidences universitaires** réparties notamment sur Saint-Étienne, Villeurbanne (Tech-la Doua) et Porte des Alpes [source S1].

- **Restauration** : 36 lieux (cafétérias, restaurants) sont accessibles, ce qui peut réduire tes dépenses alimentaires [source S1].

Pour affiner, je te conseille de consulter directement les tarifs sur le [site du CROUS Lyon](https://www.crous-lyon.fr/) ou de contacter leur service logement. Les prix varient selon la taille du studio et la résidence.

As-tu déjà identifié une zone précise (ex : Villeurbanne) pour tes recherches ?
```

---

### Q3 — Quels sont les blocs de compétences du RNCP 38450 ?

**Domain attendu** : `competences_certif` (France Compétences blocs RNCP)

**Top-5 domain match** : ✓ 5/5 fiches du domain attendu
**Citations [source SX]** : 2
**Latence** : 4.53s

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

Les fiches RNCP disponibles concernent d’autres certifications bac+5, comme :
- **Expert en numérisation industrielle** (RNCP38477) : métiers visés en études/développement informatique, management industriel [source S4]
- **Technologies de l’information** (RNCP38961) : métiers en expertise systèmes d’information, direction des SI [source S5]

Pour le RNCP 38450, je te conseille de vérifier directement sur [France Compétences](https://www.francecompetences.fr) ou de contacter le CIO le plus proche.

Quel domaine ou métier te intéresse dans cette certification ? Je peux t’aider à explorer des alternatives si besoin.
```

---

### Q4 — Quel salaire après un Master Droit en région PACA ?

**Domain attendu** : `insertion_pro` (InserSup spécifique discipline × région)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 2
**Latence** : 6.43s

**Top-5 sources retrievées** :
```
  S1: [insee_salaire] insee_salaan:cs:48 [score=0.015]
  S2: [insee_salaire] insee_salaan:cs:31 [score=0.015]
  S3: [metier] juriste en propriété intellectuelle [score=0.015]
  S4: [metier] juriste en droit social [score=0.013]
  S5: [metier] avocat / avocate [score=0.012]
```

**Réponse du pipeline** :

```
Je vois que tu cherches à anticiper les salaires après un master en droit en région PACA. Mes sources ne contiennent **aucune donnée spécifique** sur les salaires des diplômés de master droit dans cette région.

En revanche, voici deux repères nationaux sur des métiers accessibles après un master droit (sans garantie de localisation PACA) :
- **Juriste en propriété intellectuelle** : métier centré sur la protection des innovations et créations (brevets, droits d’auteur) [source S3].
- **Avocat·e** : salaire variable selon la spécialisation et la structure (cabinet, indépendant·e, salarié·e). Pour une comparaison large, les **professions libérales salariées** (PCS 31, incluant certains juristes) ont un salaire net médian de **2 250 €/mois** en France [source S2].

**Attention** : ces chiffres ne reflètent pas forcément la réalité régionale, et les écarts peuvent être importants selon le secteur (public/privé) ou la taille des structures.

As-tu une spécialisation en tête (droit social, affaires, public…) ? Cela pourrait affiner les pistes, même si je n’ai pas de données PACA dans mes sources.
```

---

### Q5 — Que fait un actuaire au quotidien ?

**Domain attendu** : `metier_detail` (ROME 4.0 fiches métiers — compétences détaillées)

**Top-5 domain match** : ✓ 2/5 fiches du domain attendu
**Citations [source SX]** : 4
**Latence** : 5.76s

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
D’après tes sources, le métier d’**[actuaire](https://www.onisep.fr/http/redirection/metier/slug/MET.861)** (ou chargé·e d’études actuarielles) repose sur trois piliers quotidiens :

• **Modélisation des risques** : utiliser statistiques et algorithmes pour évaluer les risques financiers (assurances, épargne) et proposer des tarifs adaptés. L’objectif ? Permettre à la direction de prendre des décisions éclairées, en anticipant l’imprévisible [source S2][source S4].

• **Veille et innovation** : intégrer de nouveaux produits d’assurance ou d’épargne, tout en réalisant une veille concurrentielle et marché pour ajuster les offres [source S1].

• **Optimisation des performances** : développer des outils de prévision (besoins clients, rentabilité) et mettre en place des mesures pour maximiser les résultats financiers de l’entreprise [source S1].

C’est un métier à la croisée des **mathématiques appliquées**, de la **stratégie commerciale** et de la **gestion des données** — idéal si tu aimes allier analyse technique et impact business.

Est-ce que c’est plutôt l’aspect *calculs/algorithmes* ou *conseil stratégique* qui t’attire dans ce quotidien ?
```

---

### Q6 — Quelles aides financières pour les étudiants boursiers ?

**Domain attendu** : `financement_etudes` (Financement curated dispositifs)

**Top-5 domain match** : ✓ 5/5 fiches du domain attendu
**Citations [source SX]** : 3
**Latence** : 6.68s

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
Si tu es étudiant·e boursier·e, plusieurs dispositifs peuvent compléter ta bourse pour alléger tes frais. Voici les principales aides **spécifiques ou cumulables** avec le statut boursier :

- **Bourse sur critères sociaux CROUS** : entre **1080 € et 5965 €/an** (2024-2025) selon ton échelon, pour les études supérieures (BTS, licence, master, etc.) [source S3]. *À demander via le Dossier Social Étudiant (DSE) chaque année.*

- **Aide à la première installation (CROUS)** : si tu déménages pour tes études, le Crous peut avancer ton dépôt de garantie (montant variable) ou proposer des prêts sans intérêt [source S5]. *À solliciter en parallèle de ta demande de logement Crous.*

- **APL/ALS** : ces aides de la CAF réduisent ton loyer (montant calculé selon tes ressources et la zone géographique). **Cumulable avec la bourse Crous** [source S2]. *Simule ton éligibilité sur [caf.fr](https://www.caf.fr) dès que tu as un bail.*

Tu peux aussi explorer les aides à la mobilité (Erasmus+, régions) si ton projet implique un déplacement. As-tu déjà vérifié ton échelon de bourse actuel pour estimer les montants complémentaires possibles ?
```

---

### Q7 — Quelles formations en Guadeloupe ?

**Domain attendu** : `territoire_drom` (DROM-COM territoires)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 5
**Latence** : 11.8s

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
Tu cherches des formations accessibles en Guadeloupe après le bac. Voici les options **publiques** disponibles dans mes sources, toutes basées à **Pointe-à-Pitre** ou **Saint-Claude** :

- **Sciences et environnement** :
  La **[Licence Sciences de la vie et de la terre](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=11749&typeBac=0&originePc=0)** à l’[Université des Antilles](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=11749&typeBac=0&originePc=0) propose **100 places** avec un taux d’accès de **100 %** en 2025 [source S1]. Idéal si tu vises la biologie, l’écologie ou les géosciences.
  *Alternative* : **[Licence Mathématiques](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=36146&typeBac=0&originePc=0)** (15 places) pour les maths appliquées ou l’enseignement [source S5].

- **Économie, gestion et enseignement** :
  Le **[BUT Gestion des entreprises](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=11768&typeBac=0&originePc=0)** à l’[IUT de Guadeloupe](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=11768&typeBac=0&originePc=0) (Saint-Claude) offre **70 places** (taux d’accès : **63 %**) [source S3].
  En licence, le **[portail Économie et gestion](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=39484&typeBac=0&originePc=0)** (250 places, **100 %** d’accès) couvre environnement, finance ou préparation aux métiers de l’enseignement [source S4].

- **Sport et santé** :
  La **[Licence STAPS - APAS](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=36152&typeBac=0&originePc=0)** (Activités Physiques Adaptées et Santé) compte **50 places** (taux d’accès : **50 %**) [source S2]. Pour les métiers du sport-santé ou de la réadaptation.

*À noter* : Aucune donnée disponible d...
```

---

### Q8 — Marché de l'emploi cadres en Bretagne ?

**Domain attendu** : `apec_region` (APEC régions)

**Top-5 domain match** : ✓ 1/5 fiches du domain attendu
**Citations [source SX]** : 2
**Latence** : 5.15s

**Top-5 sources retrievées** :
```
  S1: [apec_region] apec_region:bretagne, Bretagne [score=0.738]
```

**Réponse du pipeline** :

```
D’après les dernières données, le marché des cadres en Bretagne montre une dynamique plus favorable que la moyenne nationale en 2025.

• **Recrutements 2025** : 9 990 postes (+5 % vs 2024), contre une baisse de 3 % au niveau national. Une progression de 2 % est attendue en 2026 (10 200 postes), ce qui permettrait de retrouver le niveau record de 2023 (10 290) [source S1].
• **Créations nettes** : 2 910 postes en 2025 (contre 3 230 en 2024), avec une concentration des besoins dans les fonctions tertiaires (21 %), commercial-marketing (16 %), études-R&D (15 %), informatique (14 %) et production [source S1].

Ces tendances reflètent-elles les secteurs ou métiers qui t’intéressent particulièrement ?
```

---

### Q9 — Salaire moyen d'un cadre supérieur (PCS 37) ?

**Domain attendu** : `insee_salaire` (INSEE salaires PCS)

**Top-5 domain match** : ✓ 5/5 fiches du domain attendu
**Citations [source SX]** : 2
**Latence** : 15.29s

**Top-5 sources retrievées** :
```
  S1: [insee_salaire] insee_salaan:cs:37 [score=1.120]
  S2: [insee_salaire] insee_salaan:cs:33 [score=1.103]
  S3: [insee_salaire] insee_salaan:cs:38 [score=1.101]
  S4: [insee_salaire] insee_salaan:cs:34 [score=1.082]
  S5: [insee_salaire] insee_salaan:cs:48 [score=1.072]
```

**Réponse du pipeline** :

```
Le salaire net médian d’un **cadre administratif ou commercial d’entreprise (PCS 37)** s’élève à **3 750 € par mois**, soit **45 000 € par an** [source S1].

Cette catégorie compte **1,96 million de professionnels** en France, avec une répartition équilibrée entre hommes et femmes (50 %). Les salaires sont plus élevés en **Île-de-France**, région qui concentre près de la moitié des effectifs [source S1].

Est-ce que ce niveau de rémunération correspond à tes attentes dans le secteur visé ?
```

---

### Q10 — Insertion à 3 ans après un Bac pro Industrie ?

**Domain attendu** : `formation_insertion` (Inserjeunes lycée pro)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 0
**Latence** : 14.59s

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
Je préfère ne pas répondre sur ce point de manière détaillée, car ma réponse contiendrait des imprécisions factuelles importantes qui pourraient t'induire en erreur.

Détails :
• Formation citée non présente dans notre base de données vérifiée : *BUT Sciences fondamentales et applications (Grand Est)*.

Pour avoir une information fiable sur ton orientation, je te conseille :
- **ONISEP** : catalogue officiel des formations françaises — https://www.onisep.fr
- **Parcoursup** : procédures et taux d'accès officiels — https://www.parcoursup.fr
- **SCUIO** : service d'orientation de ton université (si étudiant·e)
- **CIO** / **Psy-EN** : conseiller·ères d'orientation en lycée

Tu peux aussi me reposer la question autrement (par exemple avec un profil plus précis ou sur un sujet plus ciblé) et je ferai de mon mieux pour répondre dans la limite de ce que nos données vérifient.
```

---

### Q11 — Quelles sont les spécialités possibles en BAC PRO agriculture ?

**Domain attendu** : `voie_pre_bac` (Voie pré-bac catalogue)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 2
**Latence** : 5.38s

**Top-5 sources retrievées** :
```
  S1: [(formation)] Sciences et techniques de l'agronomie pour la formation — MINISTERE DE L'AGRICULTURE ET DE LA SOUVERAINETE ALIMENTAIRE [score=0.871]
  S2: [(formation)] bac pro conduite de productions horticoles (arbres, arbustes, fruits, fleurs, légumes) — arbres, arbustes, fruits, fleurs, légumes [score=0.833]
  S3: [(formation)] Education et travail des jeunes équidés — MINISTERE DE L'AGRICULTURE ET DE LA SOUVERAINETE ALIMENTAIRE [score=0.826]
  S4: [(formation)] Services aux personnes et animation dans les territoires — MINISTERE DE L'AGRICULTURE ET DE LA SOUVERAINETE ALIMENTAIRE [score=0.829]
  S5: [(formation)] Conduite de productions en agriculture biologique et commercialisation — MINISTERE DE L'AGRICULTURE ET DE LA SOUVERAINETE ALIMENTAIRE [score=0.829]
```

**Réponse du pipeline** :

```
D’après les sources disponibles, voici les spécialités en **bac pro agriculture** que je peux identifier :

- **[Bac pro conduite de productions horticoles](https://www.onisep.fr/http/redirection/formation/slug/FOR.7687)** (arbres, arbustes, fruits, fleurs, légumes) — une formation en **3 ans** [source S2].
- **Conduite de productions en agriculture biologique et commercialisation** (certificat de spécialisation, niveau bac) [source S5].

Les autres formations listées (comme l’éducation des jeunes équidés ou les services aux personnes) relèvent de domaines connexes mais ne sont pas strictement des **bac pro agriculture**.

Pour explorer l’ensemble des options, je te conseille de consulter directement le [site de l’ONISEP](https://www.onisep.fr) ou de contacter un conseiller d’orientation.

Quelle branche de l’agriculture intéresse le plus ton projet ?
```

---

### Q12 — Taux de réussite L1 pour un bac S avec mention bien ?

**Domain attendu** : `parcours_bacheliers` (MESR parcours bacheliers en licence)

**Top-5 domain match** : ✓ 5/5 fiches du domain attendu
**Citations [source SX]** : 1
**Latence** : 4.85s

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
D’après les données disponibles, voici les taux de passage en L2 après une **L1** pour les bacheliers S avec mention **Bien** :

- En **Lettres, langues et sciences humaines** :
  **73,9 %** passent en L2 en 1 an, et **80,4 %** en 1 ou 2 ans [source S4].
  *9,1 % redoublent la L1, 2 % se réorientent en DUT.*

Si tu envisages une licence scientifique ou en STAPS, je n’ai pas de données précises pour la mention **Bien** dans mes sources (seulement **Très bien** ou **Assez bien**). Pour affiner, tu peux consulter les rapports du MESR ou les enquêtes d’insertion des universités visées.

Quel domaine te questionne le plus : les sciences, les lettres, ou un autre ?
```

---

### Q13 — Quelle insertion après un doctorat en chimie ?

**Domain attendu** : `insertion_pro` (Doctorat IP MESR)

**Top-5 domain match** : ⚠ 0/5 fiches du domain attendu
**Citations [source SX]** : 0
**Latence** : 6.13s

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
Je comprends que tu cherches des éléments concrets sur les débouchés après un doctorat en chimie. Malheureusement, **mes sources ne contiennent aucune donnée sur l'insertion professionnelle** (taux d'emploi, CDI, salaires, etc.) pour les masters ou doctorats en chimie listés — ni pour d'autres formations [sources S1 à S5].

Les fiches disponibles concernent uniquement des **masters** (bac+5) en chimie dans 5 universités publiques (Poitiers, Sorbonne, Polytechnique, Lille, Créteil), mais sans chiffre sur leur insertion ou celle des docteurs [sources S1-S5].

Pour explorer cette question, je te conseille :
- Le **[répertoire des métiers ONISEP](https://www.onisep.fr/)** (fiches "chercheur en chimie", "ingénieur R&D", etc.)
- Les **enquêtes insertion** des écoles doctorales (ex : [ED 388 "Chimie Physique et Chimie Analytique"](https://www.ed388.upmc.fr/) pour Paris)
- Un RDV avec le **SCUIO** de ton université ou un **conseiller CIO** spécialisé post-doctorat.

Quelle dimension de l'insertion t'intéresse le plus : secteur public/privé, mobilité géographique, ou types de postes (recherche, industrie, enseignement) ?
```

---

## Décision Gate 3 (manuel)

Après lecture des 13 réponses ci-dessus, indiquer :
- ✓ GO promotion (toutes questions passent les 4 critères)
- ⚠ GO conditionnel (1-3 questions à expliquer mais corpus utilisable)
- ❌ NO-GO (≥4 questions avec hallu, info non disponible non-justifiée, ou top-K mal retrouvé)
