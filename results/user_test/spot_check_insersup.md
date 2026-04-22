# Spot-check manuel InserSup — 5 échantillons

*À vérifier par Matteo avant de lancer le bench formel. Pour chaque fiche, ouvrir le site ESR et comparer nos chiffres aux chiffres officiels. Si tout colle → gate passé.*

## Procédure par fiche

1. Ouvrir : https://data.enseignementsup-recherche.gouv.fr/explore/dataset/fr-esr-insersup/table/
2. Filtrer par Code UAI = valeur ci-dessous
3. Filtrer Genre = ensemble, Nationalité = ensemble, Régime d'inscription = ensemble
4. Filtrer Promotion = cohorte indiquée
5. Comparer Taux d'emploi 12 mois et Salaire médian 12 mois avec nos chiffres

Si écart > 2 points (taux) ou > 50€ (salaire) : **STOP, investiguer avant de merger quoi que ce soit**.

---

## Échantillon 1

- **Nom formation (OrientIA)** : `C.M.I - Cursus Master en Ingénierie - Mathématiques - Cursus Master en Ingénierie (CMI) :  Ingénierie Statistique des Do`
- **Établissement** : `Université d'Orléans`
- **Code UAI** (à utiliser sur InserSup) : **`0450855K`**
- **cod_aff_form** Parcoursup : `23357`
- **Granularité** : `discipline` — au niveau discipline INFORMATIQUE
- **Cohorte** : 2022
- **Type diplôme InserSup** à filtrer : `master_LMD`
- **Libellé diplôme** : `INFORMATIQUE`

### Chiffres affichés par OrientIA

| Métrique | Notre valeur |
|---|---|
| Taux d'emploi 12m | nd |
| Salaire médian 12m | 2380 € net/mois |
| Nombre de sortants (base statistique) | 32 |

### À vérifier sur InserSup officiel

| Métrique | Ta valeur trouvée | Écart OK ? |
|---|---|---|
| Taux d'emploi 12m |  |  |
| Salaire médian 12m |  |  |
| Nombre de sortants |  |  |

**Validé ?** ☐ oui / ☐ non — si non, noter pourquoi :

---

## Échantillon 2

- **Nom formation (OrientIA)** : `Licence - Portail Physique - Licence - physique/chimie/sciences de l'ingénieur (PCSI) - option Kinésithérapie`
- **Établissement** : `Université de Montpellier`
- **Code UAI** (à utiliser sur InserSup) : **`0342490X`**
- **cod_aff_form** Parcoursup : `32431`
- **Granularité** : `type_diplome_agrege` — agrégé tout l'établissement, type_diplome Parcoursup = inconnu
- **Cohorte** : 2022
- **Type diplôme InserSup** à filtrer : `master_LMD`
- **Libellé diplôme** : `Tout Master LMD / Toute licence générale`

### Chiffres affichés par OrientIA

| Métrique | Notre valeur |
|---|---|
| Taux d'emploi 12m | nd |
| Salaire médian 12m | 2220 € net/mois |
| Nombre de sortants (base statistique) | 2342 |

### À vérifier sur InserSup officiel

| Métrique | Ta valeur trouvée | Écart OK ? |
|---|---|---|
| Taux d'emploi 12m |  |  |
| Salaire médian 12m |  |  |
| Nombre de sortants |  |  |

**Validé ?** ☐ oui / ☐ non — si non, noter pourquoi :

---

## Échantillon 3

- **Nom formation (OrientIA)** : `Licence - Economie et gestion - Parcours Cursus master en ingénierie (CMI) : Data science for social Sciences`
- **Établissement** : `Université Paris Nanterre`
- **Code UAI** (à utiliser sur InserSup) : **`0921204J`**
- **cod_aff_form** Parcoursup : `27089`
- **Granularité** : `type_diplome_agrege` — agrégé tout l'établissement, type_diplome Parcoursup = inconnu
- **Cohorte** : 2022
- **Type diplôme InserSup** à filtrer : `master_LMD`
- **Libellé diplôme** : `Tout Master LMD / Toute licence générale`

### Chiffres affichés par OrientIA

| Métrique | Notre valeur |
|---|---|
| Taux d'emploi 12m | nd |
| Salaire médian 12m | 2310 € net/mois |
| Nombre de sortants (base statistique) | 1704 |

### À vérifier sur InserSup officiel

| Métrique | Ta valeur trouvée | Écart OK ? |
|---|---|---|
| Taux d'emploi 12m |  |  |
| Salaire médian 12m |  |  |
| Nombre de sortants |  |  |

**Validé ?** ☐ oui / ☐ non — si non, noter pourquoi :

---

## Échantillon 4

- **Nom formation (OrientIA)** : `Licence - Parcours d'Accès Spécifique Santé (PASS)`
- **Établissement** : `Université de Lille`
- **Code UAI** (à utiliser sur InserSup) : **`0597239Y`**
- **cod_aff_form** Parcoursup : `29181`
- **Granularité** : `type_diplome_agrege` — agrégé tout l'établissement, type_diplome Parcoursup = inconnu
- **Cohorte** : 2022
- **Type diplôme InserSup** à filtrer : `licence_generale`
- **Libellé diplôme** : `Tout Master LMD / Toute licence générale`

### Chiffres affichés par OrientIA

| Métrique | Notre valeur |
|---|---|
| Taux d'emploi 12m | nd |
| Salaire médian 12m | 1730 € net/mois |
| Nombre de sortants (base statistique) | 1612 |

### À vérifier sur InserSup officiel

| Métrique | Ta valeur trouvée | Écart OK ? |
|---|---|---|
| Taux d'emploi 12m |  |  |
| Salaire médian 12m |  |  |
| Nombre de sortants |  |  |

**Validé ?** ☐ oui / ☐ non — si non, noter pourquoi :

---

## Échantillon 5

- **Nom formation (OrientIA)** : `Licence - Parcours d'Accès Spécifique Santé (PASS)`
- **Établissement** : `Université Grenoble Alpes`
- **Code UAI** (à utiliser sur InserSup) : **`0383546Y`**
- **cod_aff_form** Parcoursup : `30760`
- **Granularité** : `type_diplome_agrege` — agrégé tout l'établissement, type_diplome Parcoursup = inconnu
- **Cohorte** : 2022
- **Type diplôme InserSup** à filtrer : `licence_generale`
- **Libellé diplôme** : `Tout Master LMD / Toute licence générale`

### Chiffres affichés par OrientIA

| Métrique | Notre valeur |
|---|---|
| Taux d'emploi 12m | nd |
| Salaire médian 12m | 1730 € net/mois |
| Nombre de sortants (base statistique) | 909 |

### À vérifier sur InserSup officiel

| Métrique | Ta valeur trouvée | Écart OK ? |
|---|---|---|
| Taux d'emploi 12m |  |  |
| Salaire médian 12m |  |  |
| Nombre de sortants |  |  |

**Validé ?** ☐ oui / ☐ non — si non, noter pourquoi :

---

## Règle de décision finale

- **5 échantillons validés** → gate passé, on peut continuer (bench formel, Vagues E/F, etc.)
- **1-2 échantillons avec écart** → erreur de mapping / parsing, **investiguer avant tout merge**
- **3+ échantillons avec écart** → bug structurel, **rollback InserSup de main**

Sources :
- https://data.enseignementsup-recherche.gouv.fr/explore/dataset/fr-esr-insersup/table/
- https://www.data.gouv.fr/datasets/insertion-professionnelle-des-diplomes-des-etablissements-denseignement-superieur-dispositif-insersup
