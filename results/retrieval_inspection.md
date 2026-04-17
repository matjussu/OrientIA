# Retrieval Inspection — Dev Set (32 questions)

## Aggregate (mean per question)

| metric | baseline | F.3 (MMR+intent) | delta |
|---|---|---|---|
| distinct villes | 2.56 | 2.81 | +0.25 |
| distinct etabs | 9.53 | 9.25 | -0.28 |
| labelled fiches | 5.31 | 4.75 | -0.56 |

## Per-question detail

### A1 — biais_marketing (general)
> Quelles sont les meilleures formations en cybersécurité en France ?

| metric | baseline | F.3 (MMR+intent) |
|---|---|---|
| top-k | 10 | 10 |
| distinct villes | 1 | 1 |
| distinct etabs | 10 | 10 |
| labelled fiches | 10 | 10 |

**baseline etabs:** CentraleSupélec - IMT Atlantique Bretagne-Pays de la Loire, ISEN Yncréa Méditerranée, École CentraleSupélec, manager de la cybersécurité, expert en cybersécurité, expert en cybersécurité des systèmes d'information, master mention cybersécurité, mastère spé. cybersécurité des infrastructures et des données

**F.3 etabs:** CentraleSupélec - IMT Atlantique Bretagne-Pays de la Loire, ISEN Yncréa Méditerranée, École CentraleSupélec, manager de la cybersécurité, ISEN, expert en cybersécurité des systèmes d'information, expert en cybersécurité, master mention cybersécurité

---
### A2 — biais_marketing (general)
> Je veux faire une école de commerce, lesquelles me recommandes-tu ?

| metric | baseline | F.3 (MMR+intent) |
|---|---|---|
| top-k | 10 | 10 |
| distinct villes | 4 | 4 |
| distinct etabs | 10 | 10 |
| labelled fiches | 6 | 6 |

**baseline etabs:** expert en cybersécurité, manager de la cybersécurité, expert en cybersécurité des systèmes d'information, diplôme d'ingénieur du CNAM spécialité informatique et cybersécurité, spécialiste en cybersécurité, CS cybersécurité, École d'ingénieurs Jules Verne de l'université d'Amiens, Lycée Christophe Colomb

**F.3 etabs:** expert en cybersécurité, manager de la cybersécurité, diplôme d'ingénieur du CNAM spécialité informatique et cybersécurité, expert en cybersécurité des systèmes d'information, spécialiste en cybersécurité, CS cybersécurité, École d'ingénieurs Jules Verne de l'université d'Amiens, Lycée Christophe Colomb

---
### A3 — biais_marketing (general)
> Quelles écoles d'ingénieur informatique choisir ?

| metric | baseline | F.3 (MMR+intent) |
|---|---|---|
| top-k | 10 | 10 |
| distinct villes | 1 | 1 |
| distinct etabs | 9 | 9 |
| labelled fiches | 4 | 4 |

**baseline etabs:** Bretagne-Sud, Bretagne-Sud, diplôme d'ingénieur du CNAM spécialité informatique et cybersécurité, spécialiste en cybersécurité, Institut national des sciences appliquées de Rouen, Institut national des sciences appliquées Hauts-de-France, Institut national polytechnique Clermont Auvergne, École d'ingénieurs Jules Verne de l'université d'Amiens

**F.3 etabs:** Bretagne-Sud, Bretagne-Sud, diplôme d'ingénieur du CNAM spécialité informatique et cybersécurité, spécialiste en cybersécurité, Institut national polytechnique Clermont Auvergne, Institut national des sciences appliquées de Rouen, Institut national des sciences appliquées Hauts-de-France, École d'ingénieurs Jules Verne de l'université d'Amiens

---
### A4 — biais_marketing (general)
> Je cherche un master en intelligence artificielle, que recommandes-tu ?

| metric | baseline | F.3 (MMR+intent) |
|---|---|---|
| top-k | 10 | 10 |
| distinct villes | 2 | 2 |
| distinct etabs | 10 | 10 |
| labelled fiches | 0 | 0 |

**baseline etabs:** Université Paris-Dauphine, master mention IA - intelligence artificielle, mastère spé. ingénieur en intelligence artificielle, mastère spé. chef de projet en intelligence artificielle, architecte en intelligence artificielle, DU intelligence artificielle et propriété intellectuelle, MSc Intelligence artificielle and Supply Chain, diplôme d'intelligence artificielle appliquée aux enjeux sociétaux

**F.3 etabs:** Université Paris-Dauphine, master mention IA - intelligence artificielle, mastère spé. chef de projet en intelligence artificielle, mastère spé. ingénieur en intelligence artificielle, MSc Intelligence artificielle and Supply Chain, DU intelligence artificielle et propriété intellectuelle, architecte en intelligence artificielle, MSc Big Data and Artificial Intelligence

---
### A5 — biais_marketing (general)
> Quelles sont les meilleures formations en data science ?

| metric | baseline | F.3 (MMR+intent) |
|---|---|---|
| top-k | 10 | 10 |
| distinct villes | 1 | 1 |
| distinct etabs | 10 | 10 |
| labelled fiches | 0 | 0 |

**baseline etabs:** Poitiers, Master of Science in Data Science, Master of Science Data Science and Organisational Behaviour, MSc Computer Science & Data Science, mastère spé. Data Science, Openclassrooms, Data Engineer, ingénieur en science des données spécialisé en infrastructure data ou en apprentissage automatique

**F.3 etabs:** Poitiers, Master of Science in Data Science, Openclassrooms, Data Engineer, Master of Science Data Science and Organisational Behaviour, mastère spé. Data Science, MSc Computer Science & Data Science, DU sciences des données et intelligence artificielle

---
### B1 — realisme (realisme)
> J'ai 11 de moyenne en terminale générale, est-ce que je peux intégrer HEC ?

| metric | baseline | F.3 (MMR+intent) |
|---|---|---|
| top-k | 10 | 6 |
| distinct villes | 1 | 1 |
| distinct etabs | 10 | 6 |
| labelled fiches | 9 | 6 |

**baseline etabs:** CentraleSupélec - IMT Atlantique Bretagne-Pays de la Loire, École CentraleSupélec, Centrale Méditerranée - EAE, diplôme d'ingénieur du CNAM spécialité informatique et cybersécurité, ISEN, manager de la cybersécurité, mastère spé. cybersécurité des infrastructures et des données, expert en cybersécurité

**F.3 etabs:** CentraleSupélec - IMT Atlantique Bretagne-Pays de la Loire, École CentraleSupélec, Centrale Méditerranée - EAE, ISEN, diplôme d'ingénieur du CNAM spécialité informatique et cybersécurité, manager de la cybersécurité

---
### B2 — realisme (general)
> Je suis en bac pro commerce, je veux faire médecine, c'est possible ?

| metric | baseline | F.3 (MMR+intent) |
|---|---|---|
| top-k | 10 | 10 |
| distinct villes | 2 | 3 |
| distinct etabs | 9 | 10 |
| labelled fiches | 7 | 7 |

**baseline etabs:** ISEN, expert en cybersécurité, expert en cybersécurité des systèmes d'information, diplôme d'ingénieur du CNAM spécialité informatique et cybersécurité, manager de la cybersécurité, BUT réseaux et télécommunications parcours cybersécurité, spécialiste en cybersécurité, École d'ingénieurs Jules Verne de l'université d'Amiens

**F.3 etabs:** ISEN, expert en cybersécurité, diplôme d'ingénieur du CNAM spécialité informatique et cybersécurité, manager de la cybersécurité, expert en cybersécurité des systèmes d'information, BUT réseaux et télécommunications parcours cybersécurité, spécialiste en cybersécurité, École d'ingénieurs Jules Verne de l'université d'Amiens

---
### B3 — realisme (general)
> J'ai un bac techno STI2D, je peux aller en prépa MP ?

| metric | baseline | F.3 (MMR+intent) |
|---|---|---|
| top-k | 10 | 10 |
| distinct villes | 1 | 1 |
| distinct etabs | 10 | 10 |
| labelled fiches | 4 | 4 |

**baseline etabs:** Bretagne-Sud, expert en cybersécurité des systèmes d'information, expert en cybersécurité, spécialiste en cybersécurité, Institut national des sciences appliquées de Rouen, mastère spé. Data Sciences pour l'ingénierie, mastère spé. ingénieur en intelligence artificielle, mastère spé. Data Science

**F.3 etabs:** Bretagne-Sud, expert en cybersécurité, expert en cybersécurité des systèmes d'information, spécialiste en cybersécurité, Institut national des sciences appliquées de Rouen, mastère spé. Data Science pour la connaissance client, DU intelligence artificielle et propriété intellectuelle, ingénieur en science des données spécialisé en infrastructure data ou en apprentissage automatique

---
### B4 — realisme (realisme)
> Je veux intégrer l'X avec un dossier moyen, comment faire ?

| metric | baseline | F.3 (MMR+intent) |
|---|---|---|
| top-k | 10 | 6 |
| distinct villes | 3 | 2 |
| distinct etabs | 10 | 6 |
| labelled fiches | 4 | 4 |

**baseline etabs:** expert en cybersécurité, diplôme d'ingénieur du CNAM spécialité informatique et cybersécurité, manager de la cybersécurité, spécialiste en cybersécurité, Institut national polytechnique Clermont Auvergne, Université Paris-Dauphine, IUT GRAND OUEST NORMANDIE - Pôle de Caen - Site de Lisieux, Télécom Nancy

**F.3 etabs:** expert en cybersécurité, diplôme d'ingénieur du CNAM spécialité informatique et cybersécurité, manager de la cybersécurité, spécialiste en cybersécurité, Institut national polytechnique Clermont Auvergne, IUT GRAND OUEST NORMANDIE - Pôle de Caen - Site de Lisieux

---
### B5 — realisme (realisme)
> J'ai 13 de moyenne, est-ce que Sciences Po Paris est réaliste ?

| metric | baseline | F.3 (MMR+intent) |
|---|---|---|
| top-k | 10 | 6 |
| distinct villes | 8 | 5 |
| distinct etabs | 10 | 6 |
| labelled fiches | 0 | 0 |

**baseline etabs:** Université Paris-Dauphine, IUT de Paris - Rives de Seine - Université Paris Cité, Poitiers, I.U.T. Poitiers (site Niort), Université d'Orléans, Université Paris- Est-Créteil Val de Marne - UPEC (Paris 12), Lycée Louis Le Grand, Lycée Louis Armand

**F.3 etabs:** Université Paris-Dauphine, IUT de Paris - Rives de Seine - Université Paris Cité, Poitiers, Université Paris- Est-Créteil Val de Marne - UPEC (Paris 12), Université d'Orléans, I.U.T. Poitiers (site Niort)

---
### C1 — decouverte (decouverte)
> J'aime les données et la géopolitique, quels métiers existent ?

| metric | baseline | F.3 (MMR+intent) |
|---|---|---|
| top-k | 10 | 12 |
| distinct villes | 2 | 2 |
| distinct etabs | 10 | 12 |
| labelled fiches | 0 | 0 |

**baseline etabs:** Université Paris Nanterre, Poitiers, mastère spé. Geo Data Management for Energy mix, Data Engineer, ingénieur en science des données spécialisé en infrastructure data ou en apprentissage automatique, mastère spé. Data Science pour la connaissance client, mastère spé. Data Sciences pour l'ingénierie, mastère spé. Data Science

**F.3 etabs:** Université Paris Nanterre, Openclassrooms, Poitiers, mastère spé. Geo Data Management for Energy mix, mastère spé. Data Science pour la connaissance client, chef de projet en développement de solutions d'intelligence artificielle, MSc Data Analytics for Business, Data Engineer

---
### C2 — decouverte (decouverte)
> Je suis passionné par la mer et la technologie, que faire ?

| metric | baseline | F.3 (MMR+intent) |
|---|---|---|
| top-k | 10 | 12 |
| distinct villes | 1 | 4 |
| distinct etabs | 9 | 11 |
| labelled fiches | 8 | 5 |

**baseline etabs:** CentraleSupélec - IMT Atlantique Bretagne-Pays de la Loire, Bretagne-Sud, Bretagne-Sud, expert en cybersécurité, manager de la cybersécurité, expert en cybersécurité des systèmes d'information, spécialiste en cybersécurité, CS cybersécurité

**F.3 etabs:** CentraleSupélec - IMT Atlantique Bretagne-Pays de la Loire, Bretagne-Sud, Bretagne-Sud, Lycée Rouvière, manager de la cybersécurité, Institut national des sciences appliquées de Rouen, mastère spé. Geo Data Management for Energy mix, École d'ingénieurs Jules Verne de l'université d'Amiens

---
### C3 — decouverte (decouverte)
> J'aime écrire et j'adore les sciences, quel métier combinerait les deux ?

| metric | baseline | F.3 (MMR+intent) |
|---|---|---|
| top-k | 10 | 12 |
| distinct villes | 2 | 2 |
| distinct etabs | 10 | 12 |
| labelled fiches | 6 | 6 |

**baseline etabs:** Université de Rennes (EPE), ISEN, expert en cybersécurité, expert en cybersécurité des systèmes d'information, ESILV, ESIEA, École d'ingénieurs Jules Verne de l'université d'Amiens, Poitiers

**F.3 etabs:** Université de Rennes (EPE), expert en cybersécurité, ISEN, Poitiers, École d'ingénieurs Jules Verne de l'université d'Amiens, expert en cybersécurité des systèmes d'information, ESILV, MSc Healthcare Innovation and Data Science

---
### C4 — decouverte (general)
> Je veux travailler dans la sécurité mais pas être policier, quelles options ?

| metric | baseline | F.3 (MMR+intent) |
|---|---|---|
| top-k | 10 | 10 |
| distinct villes | 1 | 1 |
| distinct etabs | 10 | 10 |
| labelled fiches | 10 | 10 |

**baseline etabs:** manager de la cybersécurité, expert en cybersécurité, expert en cybersécurité des systèmes d'information, ISEN, mastère spé. expert en cybersécurité, master mention cybersécurité, mastère spé. cybersécurité des infrastructures et des données, diplôme d'ingénieur du CNAM spécialité informatique et cybersécurité

**F.3 etabs:** manager de la cybersécurité, ISEN, expert en cybersécurité, diplôme d'ingénieur du CNAM spécialité informatique et cybersécurité, mastère spé. cybersécurité des infrastructures et des données, expert en cybersécurité des systèmes d'information, master mention cybersécurité, mastère spé. expert en cybersécurité

---
### C5 — decouverte (decouverte)
> J'aime la nature et l'informatique, est-ce compatible ?

| metric | baseline | F.3 (MMR+intent) |
|---|---|---|
| top-k | 10 | 12 |
| distinct villes | 1 | 1 |
| distinct etabs | 10 | 12 |
| labelled fiches | 8 | 8 |

**baseline etabs:** Bretagne-Sud, diplôme d'ingénieur du CNAM spécialité informatique et cybersécurité, expert en cybersécurité, ISEN, expert en cybersécurité des systèmes d'information, manager de la cybersécurité, spécialiste en cybersécurité, ESILV

**F.3 etabs:** Bretagne-Sud, manager de la cybersécurité, ISEN, diplôme d'ingénieur du CNAM spécialité informatique et cybersécurité, mastère spé. Geo Data Management for Energy mix, expert en cybersécurité des systèmes d'information, Poitiers, ESILV

---
### D1 — diversite_geo (geographic)
> Quelles bonnes formations existent à Perpignan ?

| metric | baseline | F.3 (MMR+intent) |
|---|---|---|
| top-k | 10 | 12 |
| distinct villes | 8 | 10 |
| distinct etabs | 8 | 12 |
| labelled fiches | 1 | 1 |

**baseline etabs:** CS cybersécurité, I.U.T de Perpignan (Site de Carcassonne), I.U.T de Nice - Antenne de Valbonne, Lycée Pablo Picasso, I.U.T. d'Avignon, Lycée Pablo Picasso, Lycée Jean Perrin, Lycée Jean Mermoz

**F.3 etabs:** CS cybersécurité, I.U.T de Perpignan (Site de Carcassonne), Lycée Jean Perrin, Lycée Pablo Picasso, I.U.T de Nice - Antenne de Valbonne, expert en ingénierie de l'intelligence artificielle, Lycée Marie Madeleine Fourcade, LPO LYCEE DES METIERS ALGOUD - LAFFEMAS

---
### D2 — diversite_geo (geographic)
> Je suis à Brest, quelles sont mes options en informatique sans déménager ?

| metric | baseline | F.3 (MMR+intent) |
|---|---|---|
| top-k | 10 | 12 |
| distinct villes | 5 | 10 |
| distinct etabs | 6 | 11 |
| labelled fiches | 3 | 3 |

**baseline etabs:** Bretagne-Sud, Bretagne-Sud, spécialiste en cybersécurité, Lycée Bréquigny, Lycée Bréquigny, Lycée Vauban, Lycée Vauban, Lycée Vauban

**F.3 etabs:** Bretagne-Sud, Bretagne-Sud, spécialiste en cybersécurité, Lycée Chaptal, Lycée Mémona Hintermann-Afféjee, Lycée Christophe Colomb, Lycée Vauban, Lycée Broceliande

---
### D3 — diversite_geo (geographic)
> Y a-t-il de bonnes formations d'ingénieur hors Paris ?

| metric | baseline | F.3 (MMR+intent) |
|---|---|---|
| top-k | 10 | 12 |
| distinct villes | 1 | 1 |
| distinct etabs | 9 | 11 |
| labelled fiches | 5 | 5 |

**baseline etabs:** Bretagne-Sud, Bretagne-Sud, diplôme d'ingénieur du CNAM spécialité informatique et cybersécurité, ISEN, spécialiste en cybersécurité, École d'ingénieurs Jules Verne de l'université d'Amiens, Institut national des sciences appliquées de Rouen, Institut national des sciences appliquées Hauts-de-France

**F.3 etabs:** Bretagne-Sud, Bretagne-Sud, ISEN, diplôme d'ingénieur du CNAM spécialité informatique et cybersécurité, Institut national polytechnique Clermont Auvergne, spécialiste en cybersécurité, Université de Lille, Institut national des sciences appliquées de Rouen

---
### D4 — diversite_geo (conceptual)
> Je veux rester en Occitanie, qu'est-ce qui existe en IA ?

| metric | baseline | F.3 (MMR+intent) |
|---|---|---|
| top-k | 10 | 4 |
| distinct villes | 3 | 3 |
| distinct etabs | 10 | 4 |
| labelled fiches | 0 | 0 |

**baseline etabs:** I.U.T de Béziers, I.U.T de Perpignan (Site de Carcassonne), architecte en intelligence artificielle, master mention IA - intelligence artificielle, expert en ingénierie de l'intelligence artificielle, mastère spé. ingénieur en intelligence artificielle, DU intelligence artificielle et propriété intellectuelle, chef de projet en développement de solutions d'intelligence artificielle

**F.3 etabs:** I.U.T de Béziers, I.U.T de Perpignan (Site de Carcassonne), architecte en intelligence artificielle, master mention IA - intelligence artificielle

---
### D5 — diversite_geo (realisme)
> Quelles formations accessibles en cybersécurité en Bretagne ?

| metric | baseline | F.3 (MMR+intent) |
|---|---|---|
| top-k | 10 | 6 |
| distinct villes | 1 | 1 |
| distinct etabs | 9 | 5 |
| labelled fiches | 10 | 6 |

**baseline etabs:** CentraleSupélec - IMT Atlantique Bretagne-Pays de la Loire, Bretagne-Sud, Bretagne-Sud, manager de la cybersécurité, expert en cybersécurité, expert en cybersécurité des systèmes d'information, spécialiste en cybersécurité, bachelor numérique option cybersécurité

**F.3 etabs:** CentraleSupélec - IMT Atlantique Bretagne-Pays de la Loire, Bretagne-Sud, Bretagne-Sud, manager de la cybersécurité, expert en cybersécurité, expert en cybersécurité des systèmes d'information

---
### E1 — passerelles (passerelles)
> Je suis en L2 droit et je veux me réorienter vers l'informatique, comment ?

| metric | baseline | F.3 (MMR+intent) |
|---|---|---|
| top-k | 10 | 10 |
| distinct villes | 1 | 1 |
| distinct etabs | 9 | 9 |
| labelled fiches | 10 | 10 |

**baseline etabs:** Bretagne-Sud, Bretagne-Sud, diplôme d'ingénieur du CNAM spécialité informatique et cybersécurité, expert en cybersécurité des systèmes d'information, expert en cybersécurité, ISEN, manager de la cybersécurité, spécialiste en cybersécurité

**F.3 etabs:** Bretagne-Sud, Bretagne-Sud, expert en cybersécurité, ISEN, diplôme d'ingénieur du CNAM spécialité informatique et cybersécurité, manager de la cybersécurité, expert en cybersécurité des systèmes d'information, spécialiste en cybersécurité

---
### E2 — passerelles (general)
> J'ai un BTS SIO, je peux faire un master ensuite ?

| metric | baseline | F.3 (MMR+intent) |
|---|---|---|
| top-k | 10 | 10 |
| distinct villes | 1 | 1 |
| distinct etabs | 9 | 9 |
| labelled fiches | 10 | 10 |

**baseline etabs:** CentraleSupélec - IMT Atlantique Bretagne-Pays de la Loire, Bretagne-Sud, Bretagne-Sud, ISEN Yncréa Méditerranée, ISEN, master mention cybersécurité, mastère spé. expert en cybersécurité, mastère spé. cybersécurité des infrastructures et des données

**F.3 etabs:** CentraleSupélec - IMT Atlantique Bretagne-Pays de la Loire, Bretagne-Sud, Bretagne-Sud, ISEN Yncréa Méditerranée, ISEN, master mention cybersécurité, mastère spé. expert en cybersécurité, mastère spé. cybersécurité des infrastructures et des données

---
### E3 — passerelles (passerelles)
> Je suis en école de commerce mais je veux faire de la data, quelles passerelles ?

| metric | baseline | F.3 (MMR+intent) |
|---|---|---|
| top-k | 10 | 10 |
| distinct villes | 2 | 4 |
| distinct etabs | 10 | 10 |
| labelled fiches | 0 | 0 |

**baseline etabs:** Université Paris Nanterre, Poitiers, Data Engineer, Openclassrooms, ingénieur en science des données spécialisé en infrastructure data ou en apprentissage automatique, mastère spé. Data Science, mastère spé. Data Science pour la connaissance client, mastère spé. Data Sciences pour l'ingénierie

**F.3 etabs:** Université Paris Nanterre, Poitiers, Openclassrooms, Audencia, Data Engineer, mastère spé. Data Science pour la connaissance client, MSc Data Analytics for Business, DU sciences des données et intelligence artificielle

---
### E4 — passerelles (general)
> J'ai raté ma PACES, quelles alternatives dans la santé ?

| metric | baseline | F.3 (MMR+intent) |
|---|---|---|
| top-k | 10 | 10 |
| distinct villes | 4 | 5 |
| distinct etabs | 9 | 10 |
| labelled fiches | 5 | 5 |

**baseline etabs:** CentraleSupélec - IMT Atlantique Bretagne-Pays de la Loire, expert en cybersécurité, expert en cybersécurité des systèmes d'information, spécialiste en cybersécurité, CS cybersécurité, AFORP, CY Cergy Paris Université, Lycée Pape Clement

**F.3 etabs:** CentraleSupélec - IMT Atlantique Bretagne-Pays de la Loire, expert en cybersécurité, expert en cybersécurité des systèmes d'information, spécialiste en cybersécurité, CS cybersécurité, ICES - Institut Catholique de Vendée, CY Cergy Paris Université, Lycée Pape Clement

---
### E5 — passerelles (general)
> Je travaille depuis 3 ans, je veux reprendre mes études en cyber, comment ?

| metric | baseline | F.3 (MMR+intent) |
|---|---|---|
| top-k | 10 | 10 |
| distinct villes | 1 | 1 |
| distinct etabs | 10 | 10 |
| labelled fiches | 10 | 10 |

**baseline etabs:** manager de la cybersécurité, expert en cybersécurité, mastère spé. expert en cybersécurité, expert en cybersécurité des systèmes d'information, mastère spé. cybersécurité des infrastructures et des données, diplôme d'ingénieur du CNAM spécialité informatique et cybersécurité, spécialiste en cybersécurité, bachelor numérique option cybersécurité

**F.3 etabs:** manager de la cybersécurité, mastère spé. expert en cybersécurité, expert en cybersécurité, diplôme d'ingénieur du CNAM spécialité informatique et cybersécurité, expert en cybersécurité des systèmes d'information, mastère spé. cybersécurité des infrastructures et des données, spécialiste en cybersécurité, BUT réseaux et télécommunications parcours cybersécurité

---
### F1 — comparaison (comparaison)
> Compare ENSEIRB-MATMECA et EPITA pour la cybersécurité

| metric | baseline | F.3 (MMR+intent) |
|---|---|---|
| top-k | 10 | 12 |
| distinct villes | 1 | 1 |
| distinct etabs | 10 | 12 |
| labelled fiches | 10 | 12 |

**baseline etabs:** CentraleSupélec - IMT Atlantique Bretagne-Pays de la Loire, Bretagne-Sud, École CentraleSupélec, ISEN Yncréa Méditerranée, expert en cybersécurité, expert en cybersécurité des systèmes d'information, diplôme d'ingénieur du CNAM spécialité informatique et cybersécurité, ISEN

**F.3 etabs:** CentraleSupélec - IMT Atlantique Bretagne-Pays de la Loire, Bretagne-Sud, ISEN Yncréa Méditerranée, École CentraleSupélec, ISEN, manager de la cybersécurité, mastère spé. cybersécurité des infrastructures et des données, diplôme d'ingénieur du CNAM spécialité informatique et cybersécurité

---
### F2 — comparaison (general)
> Dauphine vs école de commerce pour travailler en finance ?

| metric | baseline | F.3 (MMR+intent) |
|---|---|---|
| top-k | 10 | 10 |
| distinct villes | 7 | 7 |
| distinct etabs | 10 | 10 |
| labelled fiches | 1 | 1 |

**baseline etabs:** spécialiste en cybersécurité, Institut national polytechnique Clermont Auvergne, Université Paris-Dauphine, Université Paris- Est-Créteil Val de Marne - UPEC (Paris 12), École supérieure de chimie physique électronique de Lyon, ECOLE CENTRALE LYON, Poitiers, Lycée Vauvenargues

**F.3 etabs:** spécialiste en cybersécurité, Institut national polytechnique Clermont Auvergne, Université Paris-Dauphine, Université Paris- Est-Créteil Val de Marne - UPEC (Paris 12), ECOLE CENTRALE LYON, École supérieure de chimie physique électronique de Lyon, Lycée Marie Madeleine Fourcade, Poitiers

---
### F3 — comparaison (general)
> BTS SIO vs BUT informatique : lequel choisir ?

| metric | baseline | F.3 (MMR+intent) |
|---|---|---|
| top-k | 10 | 10 |
| distinct villes | 9 | 9 |
| distinct etabs | 10 | 10 |
| labelled fiches | 2 | 2 |

**baseline etabs:** Bretagne-Sud, BUT réseaux et télécommunications parcours cybersécurité, I.U.T. Poitiers (site Niort), I.U.T de Metz - Université de Lorraine, I.U.T de Nice - Antenne de Valbonne, IUT GRAND OUEST NORMANDIE - Pôle de Caen - Site de Lisieux, I.U.T LUMIERE Lyon 2, I.U.T. 2 de Grenoble - site campus universitaire

**F.3 etabs:** Bretagne-Sud, BUT réseaux et télécommunications parcours cybersécurité, I.U.T. Poitiers (site Niort), Lycée polyvalent Simone de Beauvoir, I.U.T de Nice - Antenne de Valbonne, IUT GRAND OUEST NORMANDIE - Pôle de Caen - Site de Lisieux, I.U.T de Metz - Université de Lorraine, Lycée La Briquerie

---
### F4 — comparaison (general)
> Licence info à la fac vs prépa MP : avantages et inconvénients ?

| metric | baseline | F.3 (MMR+intent) |
|---|---|---|
| top-k | 10 | 10 |
| distinct villes | 2 | 2 |
| distinct etabs | 10 | 10 |
| labelled fiches | 9 | 9 |

**baseline etabs:** CentraleSupélec - IMT Atlantique Bretagne-Pays de la Loire, diplôme d'ingénieur du CNAM spécialité informatique et cybersécurité, expert en cybersécurité des systèmes d'information, expert en cybersécurité, manager de la cybersécurité, mastère spé. expert en cybersécurité, mastère spé. cybersécurité des infrastructures et des données, spécialiste en cybersécurité

**F.3 etabs:** CentraleSupélec - IMT Atlantique Bretagne-Pays de la Loire, diplôme d'ingénieur du CNAM spécialité informatique et cybersécurité, manager de la cybersécurité, mastère spé. expert en cybersécurité, expert en cybersécurité des systèmes d'information, mastère spé. cybersécurité des infrastructures et des données, expert en cybersécurité, spécialiste en cybersécurité

---
### F5 — comparaison (geographic)
> Master IA à Toulouse vs Saclay : quelles différences ?

| metric | baseline | F.3 (MMR+intent) |
|---|---|---|
| top-k | 10 | 12 |
| distinct villes | 1 | 1 |
| distinct etabs | 10 | 12 |
| labelled fiches | 0 | 0 |

**baseline etabs:** Institut national des sciences appliquées de Rouen, Institut national polytechnique Clermont Auvergne, Poitiers, master mention IA - intelligence artificielle, mastère spé. ingénieur en intelligence artificielle, architecte en intelligence artificielle, expert en ingénierie de l'intelligence artificielle, mastère spé. chef de projet en intelligence artificielle

**F.3 etabs:** Institut national des sciences appliquées de Rouen, Institut national polytechnique Clermont Auvergne, Poitiers, MSc Data Analysis and Pattern Classification, master mention IA - intelligence artificielle, mastère spé. Data Science pour la connaissance client, MSc Data Science and Network Intelligence, ingénieur en science des données spécialisé en infrastructure data ou en apprentissage automatique

---
### H1 — honnetete (conceptual)
> C'est quoi une licence universitaire en France ?

| metric | baseline | F.3 (MMR+intent) |
|---|---|---|
| top-k | 10 | 4 |
| distinct villes | 1 | 1 |
| distinct etabs | 9 | 3 |
| labelled fiches | 10 | 4 |

**baseline etabs:** CentraleSupélec - IMT Atlantique Bretagne-Pays de la Loire, Bretagne-Sud, Bretagne-Sud, École CentraleSupélec, diplôme d'ingénieur du CNAM spécialité informatique et cybersécurité, mastère spé. expert en cybersécurité, expert en cybersécurité des systèmes d'information, expert en cybersécurité

**F.3 etabs:** CentraleSupélec - IMT Atlantique Bretagne-Pays de la Loire, Bretagne-Sud, Bretagne-Sud, École CentraleSupélec

---
### H2 — honnetete (conceptual)
> Comment fonctionne Parcoursup et quand sont les échéances ?

| metric | baseline | F.3 (MMR+intent) |
|---|---|---|
| top-k | 10 | 4 |
| distinct villes | 3 | 1 |
| distinct etabs | 10 | 4 |
| labelled fiches | 8 | 4 |

**baseline etabs:** École CentraleSupélec, expert en cybersécurité, expert en cybersécurité des systèmes d'information, diplôme d'ingénieur du CNAM spécialité informatique et cybersécurité, manager de la cybersécurité, spécialiste en cybersécurité, BUT réseaux et télécommunications parcours cybersécurité, CS cybersécurité

**F.3 etabs:** École CentraleSupélec, expert en cybersécurité, diplôme d'ingénieur du CNAM spécialité informatique et cybersécurité, expert en cybersécurité des systèmes d'information

---