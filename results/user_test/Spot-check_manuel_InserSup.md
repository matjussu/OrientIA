# Spot-check manuel InserSup — 5 échantillons — **COMPLÉTÉ**

*Vérification effectuée le 18 avril 2026 via l'API officielle OpenDataSoft (dataset `fr-esr-insersup`, version `2025_S2`). Chaque ligne a été interrogée en filtrant `etablissement`, `type_diplome`, `libelle_diplome`, `genre=ensemble`, `nationalite=ensemble`, `regime_inscription=ensemble`, `promo=2022`.*

## TL;DR du gate

**Verdict : ⚠️ GATE NON PASSÉ — investigation requise avant tout merge.**

Les salaires médians 12m matchent exactement sur les 5/5 échantillons, mais deux problèmes structurels ont été découverts :

1. **Incohérence sur `obtention_diplome`** : OrientIA tire parfois la ligne `obtention_diplome=diplômé` (échantillons 1 & 2) et parfois `obtention_diplome=ensemble` (échantillons 3, 4, 5). Ce n'est pas un choix documenté — c'est un bug de pipeline (probablement un tri non-déterministe ou un `first()` sur un résultat multi-lignes).
2. **Taux d'emploi 12m systématiquement à "nd"** alors que la donnée officielle existe. InserSup a éclaté le taux en `tx_sortants_en_emploi_sal_fr_12` + `tx_sortants_en_emploi_non_sal_12` + `tx_sortants_en_emploi_etranger_12` ; OrientIA lit probablement `tx_sortants_en_emploi_12` (qui est `null` dans le dataset actuel) au lieu d'additionner les trois composantes.

Selon la règle de décision du document : **3 échantillons sur 5 avec écart → bug structurel → rollback InserSup de main** (ou a minima, ne pas merger avant correction du pipeline).

---

## Procédure par fiche

1. Ouvrir : https://data.enseignementsup-recherche.gouv.fr/explore/dataset/fr-esr-insersup/table/
2. Filtrer par Code UAI = valeur ci-dessous
3. Filtrer Genre = ensemble, Nationalité = ensemble, Régime d'inscription = ensemble
4. Filtrer Promotion = cohorte indiquée
5. Comparer Taux d'emploi 12 mois et Salaire médian 12 mois avec nos chiffres

Si écart > 2 points (taux) ou > 50€ (salaire) : **STOP, investiguer avant de merger quoi que ce soit**.

> **Note de la vérif** : la procédure ne précise pas `obtention_diplome`, qui peut prendre les valeurs `diplômé` ou `ensemble`. C'est précisément là que se joue le bug. Pour les fiches ci-dessous, j'indique **les deux lignes officielles** pour chaque établissement et je marque laquelle OrientIA a tirée.

---

## Échantillon 1

- **Nom formation (OrientIA)** : `C.M.I - Cursus Master en Ingénierie - Mathématiques - Cursus Master en Ingénierie (CMI) : Ingénierie Statistique des Do`
- **Établissement** : `Université d'Orléans`
- **Code UAI** : `0450855K`
- **cod_aff_form** Parcoursup : `23357`
- **Granularité** : `discipline` — au niveau discipline INFORMATIQUE
- **Cohorte** : 2022
- **Type diplôme InserSup** : `master_LMD`
- **Libellé diplôme** : `INFORMATIQUE`

> ⚠️ Remarque : la "Granularité" est notée `discipline` dans le brief, mais le filtre réel est `libelle_diplome=INFORMATIQUE` qui correspond en fait à la granularité **`diplome`** (pas `discipline`). Dans le dataset, la `discipli_lib` associée est "Sciences fondamentales et applications" et le `sectdis_lib` est "Informatique". À clarifier dans la taxonomie OrientIA.

### Chiffres affichés par OrientIA

| Métrique | Notre valeur |
|---|---|
| Taux d'emploi 12m | nd |
| Salaire médian 12m | 2380 € net/mois |
| Nombre de sortants | 32 |

### Valeurs officielles InserSup (deux lignes disponibles)

| `obtention_diplome` | nb_sortants | sal_q2_12 | tx_sal_fr_12 | tx_non_sal_12 | **tx_emploi_12 total** |
|---|---|---|---|---|---|
| **`diplômé`** ✅ *(ligne tirée par OrientIA)* | **32** | **2380** | 87,5 % | 6,25 % | **93,75 %** |
| `ensemble` | 33 | 2380 | 84,85 % | 6,06 % | 90,91 % |

### Comparaison OrientIA vs officiel

| Métrique | OrientIA | Officiel (diplômé) | Écart | OK ? |
|---|---|---|---|---|
| Taux d'emploi 12m | nd | 93,75 % | **manquant** | ❌ |
| Salaire médian 12m | 2380 € | 2380 € | 0 € | ✅ |
| Nombre de sortants | 32 | 32 | 0 | ✅ |

**Validé ?** ☐ oui / ☒ non — **nb_sortants et salaire OK mais taux d'emploi 12m manquant côté OrientIA** (donnée officielle disponible à 93,75 %). Bug de lecture : OrientIA lit probablement `tx_sortants_en_emploi_12` (null) au lieu d'agréger `tx_sortants_en_emploi_sal_fr_12 + tx_sortants_en_emploi_non_sal_12 + tx_sortants_en_emploi_etranger_12`.

---

## Échantillon 2

- **Nom formation (OrientIA)** : `Licence - Portail Physique - Licence - physique/chimie/sciences de l'ingénieur (PCSI) - option Kinésithérapie`
- **Établissement** : `Université de Montpellier`
- **Code UAI** : `0342490X`
- **cod_aff_form** Parcoursup : `32431`
- **Granularité** : `type_diplome_agrege` — agrégé tout l'établissement
- **Cohorte** : 2022
- **Type diplôme InserSup** : `master_LMD`
- **Libellé diplôme** : `Tout Master LMD`

> ⚠️ Remarque méta : la "formation Parcoursup" ici est une **Licence de Physique**, mais OrientIA renvoie des stats **Master LMD agrégé** — étrange que cette formation ne soit pas reliée à la licence générale ? À vérifier côté mapping `cod_aff_form → type_diplome_agrege`. Ça peut venir d'un fallback si pas de stats licence disponibles.

### Chiffres affichés par OrientIA

| Métrique | Notre valeur |
|---|---|
| Taux d'emploi 12m | nd |
| Salaire médian 12m | 2220 € net/mois |
| Nombre de sortants | 2342 |

### Valeurs officielles InserSup

| `obtention_diplome` | nb_sortants | sal_q2_12 | tx_sal_fr_12 | tx_non_sal_12 | **tx_emploi_12 total** |
|---|---|---|---|---|---|
| **`diplômé`** ✅ *(ligne tirée par OrientIA)* | **2342** | **2220** | 72,37 % | 1,67 % | **74,04 %** |
| `ensemble` | 2478 | 2220 | 71,19 % | 1,94 % | 73,13 % |

### Comparaison OrientIA vs officiel

| Métrique | OrientIA | Officiel (diplômé) | Écart | OK ? |
|---|---|---|---|---|
| Taux d'emploi 12m | nd | 74,04 % | **manquant** | ❌ |
| Salaire médian 12m | 2220 € | 2220 € | 0 € | ✅ |
| Nombre de sortants | 2342 | 2342 | 0 | ✅ |

**Validé ?** ☐ oui / ☒ non — même problème que l'échantillon 1 : le taux d'emploi 12m est à "nd" alors que la donnée existe.

---

## Échantillon 3

- **Nom formation (OrientIA)** : `Licence - Economie et gestion - Parcours Cursus master en ingénierie (CMI) : Data science for social Sciences`
- **Établissement** : `Université Paris Nanterre`
- **Code UAI** : `0921204J`
- **cod_aff_form** Parcoursup : `27089`
- **Granularité** : `type_diplome_agrege` — agrégé tout l'établissement
- **Cohorte** : 2022
- **Type diplôme InserSup** : `master_LMD`
- **Libellé diplôme** : `Tout Master LMD`

### Chiffres affichés par OrientIA

| Métrique | Notre valeur |
|---|---|
| Taux d'emploi 12m | nd |
| Salaire médian 12m | 2310 € net/mois |
| Nombre de sortants | 1704 |

### Valeurs officielles InserSup

| `obtention_diplome` | nb_sortants | sal_q2_12 | tx_sal_fr_12 | tx_non_sal_12 | **tx_emploi_12 total** |
|---|---|---|---|---|---|
| `diplômé` | 1465 | 2320 | 66,83 % | 3,75 % | 70,58 % |
| **`ensemble`** ✅ *(ligne tirée par OrientIA)* | **1704** | **2310** | 64,44 % | 3,76 % | **68,20 %** |

### Comparaison OrientIA vs officiel

| Métrique | OrientIA | Officiel (ensemble) | Écart | OK ? |
|---|---|---|---|---|
| Taux d'emploi 12m | nd | 68,20 % | **manquant** | ❌ |
| Salaire médian 12m | 2310 € | 2310 € | 0 € | ✅ |
| Nombre de sortants | 1704 | 1704 | 0 | ✅ |

**Validé ?** ☐ oui / ☒ non — ⚠️ **INCOHÉRENCE MAJEURE** : cette fiche a été tirée depuis `obtention_diplome=ensemble` alors que les échantillons 1 et 2 (même structure, même type_diplome `master_LMD`, même libelle `Tout Master LMD`/`INFORMATIQUE`) ont été tirés depuis `obtention_diplome=diplômé`. Le pipeline OrientIA n'applique pas de règle déterministe sur ce filtre.

---

## Échantillon 4

- **Nom formation (OrientIA)** : `Licence - Parcours d'Accès Spécifique Santé (PASS)`
- **Établissement** : `Université de Lille`
- **Code UAI** : `0597239Y`
- **cod_aff_form** Parcoursup : `29181`
- **Granularité** : `type_diplome_agrege` — agrégé tout l'établissement
- **Cohorte** : 2022
- **Type diplôme InserSup** : `licence_generale`
- **Libellé diplôme** : `Toute licence générale`

### Chiffres affichés par OrientIA

| Métrique | Notre valeur |
|---|---|
| Taux d'emploi 12m | nd |
| Salaire médian 12m | 1730 € net/mois |
| Nombre de sortants | 1612 |

### Valeurs officielles InserSup

| `obtention_diplome` | nb_sortants | sal_q2_12 | tx_sal_fr_12 | tx_non_sal_12 | **tx_emploi_12 total** |
|---|---|---|---|---|---|
| `diplômé` | 976 | 1720 | 54,92 % | 2,77 % | 57,69 % |
| **`ensemble`** ✅ *(ligne tirée par OrientIA)* | **1612** | **1730** | 54,22 % | 3,85 % | **58,07 %** |

### Comparaison OrientIA vs officiel

| Métrique | OrientIA | Officiel (ensemble) | Écart | OK ? |
|---|---|---|---|---|
| Taux d'emploi 12m | nd | 58,07 % | **manquant** | ❌ |
| Salaire médian 12m | 1730 € | 1730 € | 0 € | ✅ |
| Nombre de sortants | 1612 | 1612 | 0 | ✅ |

**Validé ?** ☐ oui / ☒ non — même problème taux d'emploi. Ligne tirée depuis `ensemble`.

---

## Échantillon 5

- **Nom formation (OrientIA)** : `Licence - Parcours d'Accès Spécifique Santé (PASS)`
- **Établissement** : `Université Grenoble Alpes`
- **Code UAI** : `0383546Y`
- **cod_aff_form** Parcoursup : `30760`
- **Granularité** : `type_diplome_agrege`
- **Cohorte** : 2022
- **Type diplôme InserSup** : `licence_generale`
- **Libellé diplôme** : `Toute licence générale`

### Chiffres affichés par OrientIA

| Métrique | Notre valeur |
|---|---|
| Taux d'emploi 12m | nd |
| Salaire médian 12m | 1730 € net/mois |
| Nombre de sortants | 909 |

### Valeurs officielles InserSup

| `obtention_diplome` | nb_sortants | sal_q2_12 | tx_sal_fr_12 | tx_non_sal_12 | **tx_emploi_12 total** |
|---|---|---|---|---|---|
| `diplômé` | 708 | 1720 | 50,28 % | 2,68 % | 52,96 % |
| **`ensemble`** ✅ *(ligne tirée par OrientIA)* | **909** | **1730** | 50,17 % | 3,19 % | **53,36 %** |

### Comparaison OrientIA vs officiel

| Métrique | OrientIA | Officiel (ensemble) | Écart | OK ? |
|---|---|---|---|---|
| Taux d'emploi 12m | nd | 53,36 % | **manquant** | ❌ |
| Salaire médian 12m | 1730 € | 1730 € | 0 € | ✅ |
| Nombre de sortants | 909 | 909 | 0 | ✅ |

**Validé ?** ☐ oui / ☒ non — même problème taux d'emploi. Ligne tirée depuis `ensemble`.

---

## Synthèse croisée

| # | Étab | `obtention_diplome` tiré par OrientIA | Salaire OK | nb_sortants OK | Taux emploi 12m OK |
|---|---|---|---|---|---|
| 1 | Orléans (master INFORMATIQUE) | **`diplômé`** | ✅ | ✅ | ❌ (nd au lieu de 93,75 %) |
| 2 | Montpellier (Tout Master) | **`diplômé`** | ✅ | ✅ | ❌ (nd au lieu de 74,04 %) |
| 3 | Paris Nanterre (Tout Master) | **`ensemble`** | ✅ | ✅ | ❌ (nd au lieu de 68,20 %) |
| 4 | Lille (Toute licence) | **`ensemble`** | ✅ | ✅ | ❌ (nd au lieu de 58,07 %) |
| 5 | Grenoble Alpes (Toute licence) | **`ensemble`** | ✅ | ✅ | ❌ (nd au lieu de 53,36 %) |

### Bugs identifiés

**BUG #1 — Incohérence sur `obtention_diplome` (sérieux)**
Le pipeline OrientIA ne spécifie pas de filtre déterministe sur `obtention_diplome`. Selon l'établissement, il prend tantôt la ligne `diplômé`, tantôt `ensemble`. Ce n'est pas détectable à l'œil nu parce que les salaires médians sont souvent identiques entre les deux lignes (différence typique : 0 à 10€), mais les `nb_sortants` et les taux d'emploi diffèrent sensiblement (ex : Lille : 976 vs 1612, Grenoble : 708 vs 909).

*Hypothèse sur la cause racine* : le pipeline fait probablement un `query → first_row()` sur l'API InserSup sans filtre explicite sur `obtention_diplome`, et l'ordre de retour n'est pas garanti. Un `ORDER BY` côté OpenDataSoft, ou une bascule d'ordre selon `date_jeu`, pourrait expliquer le pattern.

*Fix recommandé* : **forcer explicitement `obtention_diplome=ensemble`** dans toutes les requêtes InserSup. C'est la vue publique de référence du MESR (celle affichée par défaut sur le portail data.gouv), et elle inclut les non-diplômés qui sont précisément le public cible d'un outil d'orientation (un lycéen veut savoir le taux d'emploi réel, pas uniquement celui des admis jusqu'au bout).

Alternative si tu veux rester sur `diplômé` : bien documenter le choix et basculer les 3 échantillons "ensemble" en "diplômé" pour cohérence.

**BUG #2 — Taux d'emploi 12m à "nd" systématique (sérieux)**
Dans le dataset 2025_S2 actuel, le champ agrégé `tx_sortants_en_emploi_12` est à `null` pour toutes les lignes. InserSup a éclaté le taux en 3 composantes :
- `tx_sortants_en_emploi_sal_fr_12` (salariés en France)
- `tx_sortants_en_emploi_non_sal_12` (non-salariés, auto-entrepreneurs, etc.)
- `tx_sortants_en_emploi_etranger_12` (salariés à l'étranger, souvent `null`/`nd`)

*Fix recommandé* : côté mapping OrientIA, calculer :
```
tx_emploi_12 = safe_float(tx_sortants_en_emploi_sal_fr_12)
             + safe_float(tx_sortants_en_emploi_non_sal_12)
             + safe_float(tx_sortants_en_emploi_etranger_12)
```
avec `safe_float(x) = float(x) if x not in (None, 'nd') else 0`. Gérer aussi le cas "toutes les composantes sont nd" → renvoyer `nd`.

*Attention* : si une composante est `nd` et les autres sont des nombres, l'arrondi peut légèrement sous-estimer le taux. À documenter dans l'UI (tooltip "hors emploi étranger" le cas échéant).

**BUG #3 (mineur) — Taxonomie "Granularité" trompeuse (échantillon 1)**
Le brief dit `Granularité: discipline — au niveau discipline INFORMATIQUE`. Mais dans InserSup, "INFORMATIQUE" en tant que `libelle_diplome` correspond à la granularité **`diplome`**, pas `discipline`. La `discipli_lib` officielle associée est "Sciences fondamentales et applications" (`sectdis_lib` = "Informatique"). Cela peut induire en erreur dans les logs/tickets. À clarifier dans la doc interne de la taxonomie OrientIA.

---

## Règle de décision finale — appliquée

- ~~5 échantillons validés → gate passé~~
- ~~1-2 échantillons avec écart → erreur de mapping / parsing~~
- **5 échantillons avec écart** (taux d'emploi 12m manquant sur les 5, et incohérence `obtention_diplome` sur 2/5) → **🔴 Bug structurel, rollback InserSup de main**

### Plan d'action proposé

1. **Rollback immédiat** du merge InserSup sur `main` (si déjà mergé). Sinon bloquer la PR.
2. **Fix BUG #2 en priorité** (taux d'emploi 12m) — il impacte les 5/5 échantillons et c'est la métrique la plus visible pour un lycéen. Ajouter un test unitaire qui valide le calcul sur un cas type où les 3 composantes sont présentes + cas où certaines sont `nd`.
3. **Fix BUG #1** (forcer `obtention_diplome=ensemble` par défaut, documenté). Ajouter un test d'intégration qui requête les 5 UAI de ce spot-check et vérifie qu'on tire toujours la même ligne.
4. **Re-run du bench formel** après les 2 fixes, avec le même set d'UAI + 5 UAI supplémentaires tirés au hasard pour gagner en puissance statistique.
5. **Clarifier la taxonomie** (BUG #3) dans le README OrientIA : distinguer clairement `granularité={etablissement, discipline, secteur, diplome}` et ne pas mélanger avec `libelle_diplome`.

---

## Sources & reproductibilité

- Dataset officiel : https://data.enseignementsup-recherche.gouv.fr/explore/dataset/fr-esr-insersup/table/
- Doc data.gouv : https://www.data.gouv.fr/datasets/insertion-professionnelle-des-diplomes-des-etablissements-denseignement-superieur-dispositif-insersup
- API utilisée (v2.1 OpenDataSoft) : `https://data.enseignementsup-recherche.gouv.fr/api/explore/v2.1/catalog/datasets/fr-esr-insersup/records`
- Version du jeu au moment de la vérif : `date_jeu = 2025_S2`
- Date de la vérif : 18 avril 2026

### Exemple de requête reproductible (échantillon 1)

```bash
curl -s 'https://data.enseignementsup-recherche.gouv.fr/api/explore/v2.1/catalog/datasets/fr-esr-insersup/records' \
  --data-urlencode 'where=etablissement="0450855K" AND type_diplome="master_LMD" AND libelle_diplome="INFORMATIQUE" AND genre="ensemble" AND nationalite="ensemble" AND regime_inscription="ensemble" AND promo="2022"' \
  --data-urlencode 'limit=10' -G | jq '.results[] | {obtention_diplome, nb_sortants, salaire_q2_12, tx_sortants_en_emploi_sal_fr_12, tx_sortants_en_emploi_non_sal_12}'
```