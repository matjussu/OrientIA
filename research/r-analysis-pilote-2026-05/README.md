# Pilote OrientAI : analyse quantitative

Pipeline R pour le nettoyage, l'exploration et la modélisation des
données du questionnaire pilote OrientAI (Université Paris Dauphine,
avril mai 2026). L'ensemble des chiffres et figures cités dans la
section 3 du rapport est produit par ces scripts.

## Structure du dossier

```
pilote_orientia/
├── 00_run_all.R                     # Lance les 5 scripts dans l'ordre
├── 01_nettoyage_donnees.R           # Import, renommage, recodages, double codage
├── 02_stats_descriptives.R          # Distributions, moyennes, médianes
├── 03_correlations.R                # Tests bivariés (3 niveaux du plan d'analyse + croisements)
├── 04_regression_logistique.R       # Modèles M1, M2, M3 emboîtés + VIF + LR tests
├── 05_visualisations.R              # 8 figures ggplot2
├── README.md                        # Ce fichier
├── data/
│   ├── donnees_brutes.csv           # Entrée : export Google Forms
│   ├── donnees_pilote_propres.csv   # Sortie du 01 (dataset nettoyé, lisible Excel)
│   ├── donnees_pilote_propres.rds   # Sortie du 01 (idem, format R)
│   └── modeles_logistiques.rds      # Sortie du 04 (modèles glm sauvegardés)
└── figures/                         # 8 PNG générés par 05
```

## Prérequis

R 4.0 ou plus récent. Trois packages à installer une fois pour toutes :

```r
install.packages(c("tidyverse", "car", "scales"))
```

`tidyverse` couvre dplyr, readr, stringr, ggplot2, tidyr et purrr.
`car` apporte la fonction `vif()`. `scales` sert au formatage des axes
de ggplot.

## Exécution

Le plus simple est de lancer le pipeline complet d'un seul coup. Depuis
RStudio, ouvrir `00_run_all.R` et cliquer sur Source. Depuis un
terminal :

```bash
cd pilote_orientia
Rscript 00_run_all.R
```

L'exécution prend deux à trois secondes sur une machine récente. Le
script imprime à la fin un récapitulatif des outputs produits.

Pour le travail itératif, les scripts 02 à 05 peuvent être relancés
indépendamment puisqu'ils lisent tous le fichier
`data/donnees_pilote_propres.rds` généré par le 01. Il faut donc avoir
exécuté le 01 au moins une fois auparavant.

Avant l'exécution, vérifier que le répertoire de travail (`getwd()`)
pointe bien sur `pilote_orientia/`. Sous RStudio :
Session > Set Working Directory > To Source File Location.

## Notes techniques

### Locale et encodage

Tous les scripts essaient d'abord de fixer la locale sur
`fr_FR.UTF-8`, puis retombent sur `C.UTF-8` si la locale française
n'est pas installée. Ce fallback n'est pas cosmétique : sans une
locale UTF-8 active, les chaînes accentuées du source R ne matchent
pas les valeurs du CSV (qui sont elles bien en UTF-8), et plusieurs
`case_when` échouent silencieusement, ce qui fausse les tests
catégoriels et fait planter le Modèle 2 de la régression. Le script
04 inclut un garde fou explicite qui s'arrête avec un message clair
si une variable regroupée se retrouve avec un niveau vide.

### Fichier d'entrée

Le script 01 cherche d'abord un fichier nommé `data/donnees_brutes.csv`.
S'il n'existe pas, il prend automatiquement le premier `.csv` du
dossier `data/` (hors fichiers de sortie). Recommandation : renommer
l'export Google Forms en `donnees_brutes.csv` pour éviter toute
ambiguïté.

## Décisions méthodologiques

### Inclusion des jeunes actifs

Les six répondants non étudiants (jeunes actifs récents, 3,3 % de
l'échantillon) sont conservés dans les analyses. Avec un effectif
aussi faible, créer une variable de contrôle coûterait un degré de
liberté sans apport. Cette inclusion est mentionnée comme limite dans
la section 3.1 du rapport.

### Cas particuliers nettoyés à la main

Deux réponses ont été retraitées dans le champ Q10 (motivation
initiale). Une personne avait coché "Famille / entourage / réseau"
puis ajouté en aparté un message faisant la promotion d'un site
d'échange de questionnaires : le commentaire est retiré, la
modalité cochée est conservée. Une autre personne avait écrit
"Hauts de Seine" sans rapport avec la question : la valeur est
passée en NA pour ne pas polluer la distribution. Les autres réponses
de ces deux participants sont conservées telles quelles.

### Recodages

**Filière (Q8)** : douze réponses libres sont rattachées aux
catégories existantes (par exemple "Master MEEF" rejoint
"Lettres / Sciences humaines / Sciences sociales"). Deux réponses
("BTS", "IUT / BUT") sont passées en NA car elles désignent un type
d'établissement plutôt qu'une discipline.

**Motivation (Q10)** : double codage. La variable
`motivation_descriptive` introduit deux catégories supplémentaires à
partir des réponses libres "Autre" : "Professeurs du lycée" (n=7) et
"Motivation personnelle / passion" (n=6). C'est cette version qui est
utilisée pour les statistiques descriptives et la Figure 1, parce
qu'elle fait apparaître un acteur (le professeur de lycée) que les
options initiales du formulaire ne capturaient pas. La variable
`motivation_regression`, qui fusionne ces nouvelles catégories avec
"Autre", est conservée comme alternative robuste pour des modèles
ultérieurs.

**Année de réorientation (Q16.1)** : champ libre très hétérogène,
mélangeant années calendaires (2021, 2023…) et niveaux d'études
(L1, M1, "3ème année", "première année"…). On en extrait deux
variables propres. `reorientation_annee` capte l'année calendaire
pour 15 réorientés sur 53. `reorientation_niveau` capte le niveau
au moment du changement pour 37 réorientés sur 53. Convention
adoptée : "3" / "3ème" valent L3 (troisième année post bac),
"4" valent M1, "5" valent M2. La Figure 5 du rapport présente
cette seconde variable.

### Test 2.1 sur cinq catégories interprétables

Le test Kruskal Wallis comparant la qualité du conseil reçu (Q14)
selon le niveau d'études des parents porte sur les cinq catégories
ordonnées et interprétables : "Aucun diplôme / Brevet", "CAP / BEP",
"Baccalauréat", "Bac+2 / Bac+3", "Bac+5 et plus". Les deux
catégories non interprétables, "Autre" (n=3) et "Préfère ne pas
répondre" (n=1), sont écartées : leur contenu ne renvoie pas à un
niveau d'études identifiable, et leurs effectifs trop faibles
déstabiliseraient le test. Ce choix donne H = 6,38 ; df = 4 ;
p = 0,173 sur N = 176 (cf. section 3.4.1 du rapport).

### Préparation à l'emploi (Q15)

La variable `preparation_emploi` est exclue du modèle de régression
principal mais conservée dans les analyses descriptives et les
corrélations exploratoires. La décision est documentée dans le
plan d'analyse : la préparation à l'emploi pose un problème de
temporalité (elle est évaluée au moment de l'enquête, alors que la
réorientation a pu intervenir des années plus tôt) qui complique
son interprétation comme prédicteur.

### Régression logistique : trois modèles emboîtés

La variable dépendante est `reoriente_bin`. Les trois modèles sont
ajustés sur l'échantillon commun N = 173, ce qui permet de
comparer leurs déviances par tests du rapport de vraisemblance.

- M1 : `reoriente_bin ~ conseil_adapte + info_percue`
- M2 : M1+ genre, niveau parents (regroupé), commune (regroupée),
  filière (regroupée), fréquence PsyEN (binaire)
- M3 : M2+ usage IA pour la formation et pour les métiers (binaires)

Les variables catégorielles sont regroupées pour respecter la règle
de Peduzzi (environ dix cas par paramètre) compte tenu des 53
réorientés observés. Les regroupements retenus sont :
`niveau_parents_grp` en trois modalités (Faible / Intermédiaire /
Supérieur), `commune_grp` en quatre, `filiere_grp` en trois
(Sélective / Univ. éco/droit / Univ. généraliste). Le détail des
regroupements est commenté dans le code du script 04.

Le diagnostic de multicolinéarité repose sur le VIF (seuil de
vigilance à 5). Sur le modèle complet, la valeur maximale observée
est 1,84, bien en deçà du seuil.

## Correspondance entre sorties du pipeline et sections du rapport

Pour faciliter la vérification, voici les principaux résultats
produits par le pipeline et la section du rapport où ils
apparaissent.

### Section 3.3 (qualité du conseil et réorientation)

- Mann Whitney sur Q14 selon réorientation : W = 3006, p = 0,231.
- Mann Whitney sur Q13 selon réorientation : W = 3298, p = 0,823.
- LR test M0 vs M1 sur l'échantillon commun : p = 0,680.
- Pseudo R² de McFadden du M1 : 0,004 (soit moins de 1 %).

### Section 3.4 (origine sociale et trajectoire d'orientation)

- 3.4.1 Kruskal Wallis Q14 selon niveau parents (5 catégories,
  N=176) : H = 6,38 ; df = 4 ; p = 0,173. Tendance non
  significative.
- 3.4.2 Chi² niveau parents regroupé × filière regroupée :
  X² = 10,47 ; df = 4 ; p = 0,033. Fisher exact Monte Carlo
  (B = 10000) : p = 0,036. Lien significatif.
- 3.4.3 Chi² filière × réorientation : X² = 19,74 ; df = 7 ;
  p = 0,006. Fisher exact Monte Carlo : p ≈ 0,009. Lien
  significatif. Le Fisher Monte Carlo est ajouté parce que le
  chi² renvoie un warning sur cette table (plusieurs cellules
  ont une fréquence attendue inférieure à 5).

### Section 3.5 (usage de l'IA et information perçue)

- 3.5.1 Chi² niveau parents × usage IA pour la formation :
  X² = 1,34 ; df = 6 ; p = 0,969. Pas de lien social détectable.
- 3.5.2 Kruskal Wallis Q13 selon usage IA pour la formation
  (3 modalités) : p = 0,428. Idem pour les métiers : p = 0,984.
  Versions binaires (utilise vs n'utilise pas) : p = 0,200 et
  p = 0,866. Aucun lien détectable.

### Régression logistique (section 3.3)

LR test M1 vs M2 : p = 0,062. Les variables sociodémographiques
apportent un signal collectif borderline, conforme à l'idée que
plusieurs petits effets convergent sans qu'aucun ne soit
individuellement significatif. LR test M2 vs M3 : p = 0,741.
L'usage de l'IA n'ajoute rien une fois les autres variables prises
en compte.

## Limites assumées du pilote

Trois limites à garder en tête pour lire ces résultats.

**Composition de l'échantillon.** Les répondants sont massivement
issus de l'écosystème Dauphine : 60 % ont au moins un parent à
Bac+5 et plus, 94 % ont un baccalauréat général, 55 % sont
inscrits en économie, gestion, commerce ou en école de commerce.
Les inégalités sociales que la section 3.4 met au jour sont donc
sans doute sous estimées : elles ressortent malgré un échantillon
relativement homogène.

**Effet d'échantillon sur la catégorie "Aucun diplôme / Brevet".**
Cette catégorie (n = 8) affiche une moyenne anormalement élevée
sur la qualité du conseil reçu (μ = 3,62), au dessus même de la
catégorie Bac+5. Ce point ne s'inscrit pas dans la monotonie
attendue et tient à un effet de petit effectif (intervalle de
confiance large). Il est commenté en tant que tel dans la section
3.4.1 du rapport.

**Cadrage temporel sur l'usage de l'IA.** 96 % des répondants sont
au niveau L2 ou au delà, donc ont fait leur choix initial de
formation avant ou très tôt dans la diffusion grand public des
LLM. L'analyse de l'usage de l'IA pour le choix de formation sous
estime probablement les usages actuels des lycéens et bacheliers
récents, qui constituent pourtant le public cible principal du
service OrientAI.

**Puissance statistique.** Avec N = 180 dont 53 réorientés, le
pilote ne permet de détecter que des effets de taille moyenne à
forte, et ne permet pas de tester formellement les chaînes de
médiation que la section 3.4.4 propose comme lecture
transversale.
