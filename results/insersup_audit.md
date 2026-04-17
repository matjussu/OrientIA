# InserSup integration audit

**Source** : `data/raw/insersup.csv` + `data/processed/formations.json`
**InserSup index size** : 4413 triples (uai, type_diplome, libelle)

## Coverage

| Metric                          | Count | % of total |
|---------------------------------|-------|------------|
| Total fiches                    | 443 | 100% |
| With cod_uai                    | 343 | 77.4% |
| Without cod_uai (ONISEP-only)   | 100 | 22.6% |
| Matched at **discipline** level | 1 | 0.2% |
| Matched at aggregate level      | 8 | 1.8% |
| Unmatched (UAI present)         | 334 | 75.4% |

UAI absent from InserSup entirely : 242 distinct establishments.

## Discipline-level matched samples (spot-check these !)

| Établissement | Formation | Niveau | Taux emploi 12m | Salaire médian 12m | Cohorte | N sortants |
|---|---|---|---|---|---|---|
| Université d'Orléans | C.M.I - Cursus Master en Ingénierie - Mathématiques - Cursus | bac+5 | nd | 2380€ | 2022 | 32 |

## Aggregate-level matched samples (less specific — spot-check too)

| Établissement | Formation | Niveau | Taux emploi 12m | Salaire médian 12m | Cohorte | N sortants |
|---|---|---|---|---|---|---|
| ECAM LaSalle | Formation Bac + 3 - Bachelor Cybersécurité des systèmes indu | bac+3 | nd | 2640€ | 2022 | 268 |
| EFREI Paris | Formation Bac + 3 - Bachelor Cybersécurité et Ethical Hackin | bac+3 | nd | 2830€ | 2022 | 464 |
| CY Cergy Paris Université | Licence professionnelle - Métiers des réseaux informatiques  | bac+3 | nd | 1750€ | 2022 | 183 |
| Université Paris- Est-Créteil Val de Marne - UPEC (Paris 12) | Licence - Double diplôme - Licence Economie et gestion - Dou | bac+3 | nd | 1820€ | 2022 | 473 |
| Université d'Orléans | Double licence - Economie / Informatique - Intelligence Arti | bac+3 | nd | 1700€ | 2022 | 261 |
| Université de Rennes (EPE) | Licence - Double diplôme - Licence Sciences de la vie - Biol | bac+3 | nd | 1700€ | 2022 | 185 |
| Université Paris Nanterre | Licence - Economie et gestion - Parcours Cursus master en in | bac+5 | nd | 2310€ | 2022 | 1704 |
| Avignon Université | Licence - Administration économique et sociale - Parcours Do | bac+3 | nd | 1640€ | 2022 | 112 |

## Outliers detected

✅ No outliers detected (all taux in [0,1], all salaires in [500€, 8000€]).

## Manual verification checklist

Before this audit is accepted, **manually verify 3-5 of the **discipline-level** samples above**:

1. Open the ESR / establishment website for each sample
2. Check that the taux d'emploi 12m and salaire médian we extracted match what is published officially
3. If any sample is off by more than a few percentage points → STOP, investigate before merging

Source officielle à vérifier :
- https://data.enseignementsup-recherche.gouv.fr/explore/dataset/fr-esr-insersup/table/
- https://www.data.gouv.fr/datasets/insertion-professionnelle-des-diplomes-des-etablissements-denseignement-superieur-dispositif-insersup