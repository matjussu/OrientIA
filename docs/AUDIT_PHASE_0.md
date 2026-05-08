# OrientIA — Audit Data Phase 0

> **Daté du 2026-05-07.** Audit chiffré du corpus production avant grand ménage. Périmètre : `data/processed/formations.json` (48 914 fiches), tous les corpora annexes, tous les collectors, l'index FAISS, la dette de stockage.
>
> **Objectif** : poser les chiffres réels qui orientent la priorisation Phase 1 (ménage), Phase 2 (activation dormant) et Phase 3 (enrichissement ciblé).

---

## TL;DR — les 5 findings critiques

| # | Finding | Impact | Sévérité |
|---|---|---|---|
| 1 | **67% du corpus a des chiffres d'insertion qui sont 6 templates Cereq par niveau** (32 704 fiches partagent 6 tuples uniques) | Hallu data-borne masquée par `honesty=1.0`. La spécificité du système est mise en cause. | 🔴 Critique |
| 2 | **28% de doublons** (13 858 fiches sur (nom+etab+ville)) | FAISS retrieval effectif réduit, MMR insuffisant | 🔴 Critique |
| 3 | **Labels SecNumEdu/CTI : 23 fiches sur 48 914 (0,05%)** | Le reranker boost ×1,5 sur un signal quasi-absent | 🟠 Important |
| 4 | **Couverture URL : 10%** (4 882/48 914 fiches) | 90% des `[source SX]` non vérifiables par un user | 🟠 Important |
| 5 | **8 versions de `formations*.json` + 6 versions de `formations_multi_corpus_*`** | 3,16 GB de dette stockage, ambiguïté sur le corpus de référence | 🟡 Modéré |

**Décision induite** : Phase 1 doit traiter en priorité (1) (politique salaires agrégés), (2) (déduplication), avant tout enrichissement.

---

## 1. Audit corpus principal `formations.json`

### 1.1 Distribution par source

| Source | Fiches | % corpus | Vides | % vides |
|---|---|---|---|---|
| `inserjeunes_cfa` | 11 314 | 23,1% | 3 481 | **31%** |
| `parcoursup` | 10 536 | 21,5% | 0 | 0% |
| `monmaster` | 8 953 | 18,3% | 0 | 0% |
| `labonnealternance` | 6 646 | 13,6% | 0 | 0% |
| `rncp` | 6 590 | 13,5% | 1 452 | **22%** |
| `onisep` | 4 875 | 10,0% | 1 300 | **27%** |
| **Total** | **48 914** | **100%** | **6 233** | **12,7%** |

**Lecture** : trois sources (`inserjeunes_cfa`, `rncp`, `onisep`) ont des taux de vide significatifs (22-31%). 6 233 fiches participent au retrieval sans apporter de chiffre exploitable.

### 1.2 Densité chiffres exploitables par fiche

| Nb chiffres | Fiches | % | Lecture |
|---|---|---|---|
| 0 | 6 233 | 12,7% | Vides — à supprimer |
| 2 | 3 768 | 7,7% | Très faible |
| 3 | 26 442 | 54,1% | **Probablement** : Cereq agrégat × niveau (1 niveau + 1 sal + 1 t6) |
| 4 | 4 079 | 8,3% | Idem + 1 chiffre supplémentaire |
| 6 | 8 383 | 17,1% | Parcoursup riches (4 admission + 2 insertion) |
| 7-8 | 9 | 0,02% | Cas exceptionnels (Parcoursup + insertion + Cereq) |

**Médian = 3,5**, mais ce médian est biaisé par les 6 templates Cereq qui gonflent artificiellement la densité.

### 1.3 🔴 FINDING #1 — Les 6 templates Cereq par niveau

Sur les 32 704 fiches qui ont les 4 chiffres `(salaire_median_embauche, taux_emploi_3ans, taux_emploi_6ans, taux_cdi)` simultanément, on trouve **exactement 6 tuples uniques** :

| Tuple `(sal, t3, t6, cdi)` | Niveau associé | Fiches | % corpus |
|---|---|---|---|
| `(2080, 0.85, 0.91, 0.83)` | bac+5 | 15 138 | **30,9%** |
| `(1740, 0.86, 0.91, 0.83)` | bac+3 | 8 279 | 16,9% |
| `(1570, 0.80, 0.87, 0.76)` | bac+2 | 6 339 | 13,0% |
| `(1410, 0.73, 0.80, 0.66)` | bac | 2 055 | 4,2% |
| `(1330, 0.61, 0.69, 0.62)` | cap-bep | 890 | 1,8% |
| `(2790, 0.91, 0.95, 0.73)` | bac+8 | 3 | 0,0% |
| **Total fiches templées** | | **32 704** | **66,9%** |

**Diagnostic** : `Cereq.attach_cereq_insertion()` colle les **statistiques agrégées par niveau** à toutes les fiches du corpus, sans aucune spécificité par formation. Une fiche "BTS Cyber Marine Nationale" et une fiche "BTS Pâtisserie" ont **les mêmes 4 chiffres d'insertion**.

**Conséquence** :
- Le LLM cite ces chiffres en réponse → `honesty=1.0` (le chiffre **est** dans la fiche)
- Mais le chiffre n'est **pas spécifique à la formation** → c'est l'agrégat niveau bac+5 toutes filières
- Le system prompt R1 impose "uniquement valeurs présentes dans `chiffres`" mais ne distingue pas spécifique vs agrégat

**Cas concret bench Z1 (avocat fiscaliste)** :
- LLM cite "salaire médian embauche 2080€ pour Mastère Droit fiscal"
- 2080€ = template bac+5 généraliste, pas le salaire d'avocat fiscaliste (réalité 2500-4000€)
- Layer3 (OFF par défaut) avait flag cette erreur. ADR-053 l'avait classée "biais judge" — finding actuel suggère que c'est le data qui ment, pas le judge.

**Décision Phase 1 nécessaire** :
- **Option A — purge** : retirer ces 32 704 chiffres agrégés. Reste ~10 500 fiches Parcoursup riches + ~6 000 fiches avec chiffres spécifiques = ~16k fiches denses utiles.
- **Option B — tagger** : ajouter `provenance.source: "cereq_aggregat_niveau_bacX"` et faire que le LLM cite `[source S1, agrégat Cereq par niveau]` au lieu de `[source S1]`.
- **Option C — InserSup spécifique** : remplacer les agrégats par les chiffres InserSup réels (`insersup_insertion.json` 47MB déjà collecté mais non intégré, voir §3.3).

Recommandation : **A pour les questions par formation, B pour les questions par niveau, C dès qu'on a le chiffre spécifique**.

### 1.4 🔴 FINDING #2 — Doublons : 28% du corpus

**13 858 fiches** partagent leur clé `(nom + établissement + ville)` avec ≥1 autre fiche. Soit ~1 fiche sur 3 est une duplication (parfois une formation indexée 2× dans Parcoursup et ONISEP, parfois 3× via LBA).

**Conséquence retrieval** :
- FAISS top-30 → en pratique ~20-22 fiches uniques
- MMR (λ 0,4-0,9) ne déduplique pas brutalement les quasi-doublons
- Le top-k passé au LLM contient des fiches redondantes → moins de slots pour des angles différents

**Bonne nouvelle** : un fichier `formations_dedupe.json` (87 MB vs 94 MB) **existe déjà** depuis avril. Il faut soit (1) le promouvoir comme corpus de référence, soit (2) refaire la déduplication proprement avec la dernière logique de merge.

### 1.5 🟠 FINDING #3 — Labels boostés × 1,5 mais quasi-absents

Le reranker (`src/rag/reranker.py:RerankConfig`) configure :
```python
secnumedu_boost = 1.5
cti_boost = 1.3
grade_master_boost = 1.3
```

Réalité dans le corpus :
- Champ `labels` non-vide : **23 fiches sur 48 914 (0,05%)**

**Conséquence** : ces boosts ne se déclenchent pratiquement jamais. Le tuning du reranker est calibré sur des signaux fantômes.

**Cause probable** : les labels (SecNumEdu pour cybersécurité, CTI pour ingénieur, Grade Master, etc.) sont dans les fiches sources mais le merge ne les copie pas dans le champ `labels`. À vérifier dans `src/collect/secnumedu*.py` (qui scrape les labels) et `src/collect/run_merge*.py` (qui fait l'aggrégation).

**Décision Phase 1** : soit re-scraper et merger correctement les labels, soit retirer ces boosts du `RerankConfig` (ils n'ont aucun effet).

### 1.6 🟠 FINDING #4 — Couverture URL vérifiable

| Champ URL | Fiches avec | % |
|---|---|---|
| `url_parcoursup` ou `url_onisep` | 4 882 | 10,0% |

Les autres 90% (44 032 fiches) ont des `[source SX]` qui pointent vers une fiche du corpus mais aucune URL externe vérifiable. Pour un système qui plaide la traçabilité INRIA, c'est un gap structurel.

**Décision Phase 1** : audit fiche par fiche → chaque fiche doit avoir au minimum 1 URL canonique. Si la fiche source ne fournit pas d'URL → fallback à un slug ONISEP générique (`https://www.onisep.fr/recherche?q=<nom>`) avec marqueur "URL recherche, pas fiche directe".

### 1.7 Couverture géographique

| Métrique | Valeur |
|---|---|
| Fiches sans région | 18 175 (37,2%) |
| Régions distinctes après normalisation | 24 |
| Régions attendues (métropolitaine + DROM-COM) | 18 max |

**Casse de normalisation** : `Île-de-France` (2 420), `Ile-de-France` (2 039), `ILE-DE-FRANCE` (1 752) sont 3 régions distinctes dans la data — soit **6 211 fiches mal canonisées** sur cette région seule. Idem `Auvergne-Rhône-Alpes` (2 350) / `AUVERGNE-RHONE-ALPES` (1 397).

**Décision Phase 1** : passer un `normalize_region()` sur tout le corpus (utility déjà partielle dans `src/collect/normalize.py`).

### 1.8 Couverture niveau de diplôme

| Niveau | Fiches | % |
|---|---|---|
| `NULL` | 16 210 | 33,1% |
| `bac+5` | 15 138 | 30,9% |
| `bac+3` | 8 279 | 16,9% |
| `bac+2` | 6 339 | 13,0% |
| `bac` | 2 055 | 4,2% |
| `cap-bep` | 890 | 1,8% |
| `bac+8` | 3 | 0,0% |

**33% sans niveau** = 16 210 fiches non filtrables par niveau. Anomalie pour un système qui répond aux lycéens (qui pensent en niveaux).

### 1.9 Couverture par domaine professionnel

Heuristique mots-clés (premier match sur `nom + domaine + debouches`) :

| Domaine | Fiches | % |
|---|---|---|
| commerce / gestion / finance | 9 375 | 19,2% |
| santé / médical / social | 7 690 | 15,7% |
| ingénierie / industrie | 5 122 | 10,5% |
| informatique / cyber / numérique | 3 947 | 8,1% |
| droit / juridique | 2 085 | 4,3% |
| art / culture / design | 1 320 | 2,7% |
| sciences / recherche | 1 232 | 2,5% |
| communication / médias | 1 180 | 2,4% |
| agriculture / environnement | 1 046 | 2,1% |
| sport | 961 | 2,0% |
| tourisme / hôtellerie | 622 | 1,3% |
| btp / construction | 594 | 1,2% |
| enseignement / formation | 196 | 0,4% |
| transport / logistique | 107 | 0,2% |
| **[non classé]** | **13 437** | **27,5%** |

**Lacunes graves** :
- **Enseignement (0,4%)** — alors que c'est un secteur d'orientation massif (CRPE, agrégation, CAPES). Les questions "comment devenir prof" sont mal couvertes.
- **Transport / logistique (0,2%)** — quasi absent malgré être un secteur recruteur.
- **27,5% non classés** — le label `domaine` du corpus est probablement vide ou non normalisé pour 1/4 des fiches.

**Sur-représentation** : `commerce/gestion` (19%) reflète probablement l'avalanche d'écoles de commerce privées (LBA + RNCP). À pondérer côté reranker.

### 1.10 Statut public/privé

| Statut | Fiches | % |
|---|---|---|
| Public | 17 318 | 35,4% |
| `NULL` | 11 421 | 23,3% |
| CFA Apprentissage | 11 314 | 23,1% |
| Certificat RNCP | 6 590 | 13,5% |
| Privé | 2 177 | 4,5% |
| Inconnu | 94 | 0,2% |

**Anomalie** : seulement **2 177 fiches "Privé"** (4,5%). L'écosystème EPITA / EPITECH / IONIS / écoles de commerce privées représente bien plus que ça en réalité. Le statut "Privé" est sous-déclaré → bcp de fiches privées sont étiquetées `NULL` ou `CFA Apprentissage`.

---

## 2. Le sous-corpus or — Parcoursup riches (10 536 fiches)

C'est la **seule** partie du corpus qui mérite vraiment le label "production-grade" :

| Champ | Présence |
|---|---|
| `taux_acces` | 100,0% |
| `places` | 100,0% |
| `voeux_totaux` | 100,0% |
| `profil_admis` | 100,0% |
| `internat_disponible` | 2,1% |
| `≥3 chiffres admission` | 100,0% |

**Lecture** : 21,5% du corpus est dense, fiable, structuré. C'est sur ces fiches que repose vraiment l'argument "données officielles vérifiables".

**Décision implicite** : si on **purge les fiches non-Parcoursup sans chiffre spécifique**, on passe de 48 914 à ~16-20 000 fiches denses. Le corpus serait **plus petit mais beaucoup plus utile**.

---

## 3. Audit des collectors `src/collect/` (47 modules)

### 3.1 Collectors actifs (produisent un fichier référencé en prod)

| Collector | Output | Statut |
|---|---|---|
| `parcoursup.py` (lib via merge) | dans `formations.json` | ✅ Actif |
| `monmaster.py` | `monmaster_formations.json` | ✅ Actif |
| `onisep.py` (lib) | dans `formations.json` | ✅ Actif |
| `rncp.py` | `rncp_certifications.json` | ✅ Actif |
| `inserjeunes.py` | `inserjeunes_cfa.json` | ✅ Actif |
| `labonnealternance.py` (lib) | dans `formations.json` | ✅ Actif |
| `cereq.py` | `cereq_insertion_stats.json` | ✅ Actif (mais source du finding #1) |
| `apec_regions.py` | `apec_regions_corpus.json` | ✅ Actif |
| `crous.py` + `build_crous_corpus.py` | `crous_corpus.json`, logements, restos | ✅ Actif |
| `build_dares_corpus.py` | `dares_corpus.json` | ✅ Actif |
| `build_domtom_corpus.py` | `domtom_corpus.json` | ✅ Actif |
| `build_financement_corpus.py` | `financement_corpus.json` | ✅ Actif |
| `build_france_comp_blocs_corpus.py` | `france_comp_blocs_corpus.json` | ✅ Actif |
| `build_insee_salaan_corpus.py` | `insee_salaan_corpus.json` | ✅ Actif |
| `build_inserjeunes_lycee_pro_corpus.py` | `inserjeunes_lycee_pro_corpus.json` | ✅ Actif |
| `build_voie_pre_bac_corpus.py` | `voie_pre_bac_corpus.json` | ✅ Actif |
| `parcours_bacheliers.py` | `parcours_bacheliers_corpus.json` | ✅ Actif |
| `onisep_metiers.py` | `onisep_metiers.json` | ✅ Actif |
| `onisep_formations_extended.py` | `onisep_formations_extended.json` | ✅ Actif |
| `ip_doc_doctorat.py` | `ip_doc_doctorat.json` | ✅ Actif |
| `ideo_fiches.py` + `build_metiers_corpus.py` | `ideo_fiches_metiers.json`, `metiers_corpus.json` | ✅ Actif |
| `insee.py` | `insee_salaires_pcs_age.json`, `insee_taux_emploi_diplome.json` | ✅ Actif |
| `insee_emploi.py` | `insee_salaires_pcs_age.json` | ✅ Actif |
| `insee_salaan.py` | `insee_salaires_2023.json` | ✅ Actif |
| `insersup_api.py` | `insersup_insertion.json` | ✅ Actif (mais voir §3.3) |
| `build_insersup_corpus.py` | `insersup_corpus.json`, `insersup_insertion.json` | ✅ Actif |
| `build_corrections_factuelles_corpus.py` | `corrections_factuelles_corpus.json` | ✅ Actif |

### 3.2 Collectors potentiellement dormants

| Collector | Statut | Hypothèse |
|---|---|---|
| `dares_metiers_2030.py` | Produit `dares_metiers_2030.json` (1 MB) **non référencé** | Doublon avec `build_dares_corpus.py`, à archiver |
| `secnumedu_scrape.py` (`[MAIN]` mais aucune écriture détectée) | Code mort ou utilité interne ? | À investiguer (relié au finding #3 labels) |
| `ft_acces_emploi.py` | `[lib]` sans main | **Donnée France Travail dormant ⚠️** |
| `ft_base.py` | `[lib]` | Probablement utility, normal |
| `ft_marche_travail.py` | `[lib]` sans main | **Donnée France Travail dormant ⚠️** |
| `ft_offres_emploi.py` | `[lib]` sans main, mais `ft_offres_sample.json` existe | Partiellement actif |
| `ft_sortants_formation.py` | `[lib]` sans main | **Donnée France Travail dormant ⚠️** |
| `rome.py` | `[lib]` | Probablement importé par `build_metiers_corpus.py` |
| `rome_api.py` | `[lib]` | API ROME, importé |
| `romeo.py` | `[lib]` | API Romeo Pôle Emploi, à vérifier |

**Finding** : la suite **France Travail** (5 modules `ft_*`) est partiellement câblée. France Travail expose des API officielles riches (offres temps réel, statistiques marché du travail par bassin, accès à l'emploi par diplôme, sortants de formation insérés). C'est exactement le type de données spécifiques par formation qui manque dans le corpus actuel pour résoudre le finding #1.

**Décision Phase 2** : auditer chacun de ces 5 modules `ft_*`, ajouter un `__main__` block + un build_corpus dédié, intégrer.

### 3.3 Données collectées mais NON intégrées au corpus principal

Fichiers data/processed existants mais **non référencés** par `formations.json` ni le pipeline :

| Fichier | Taille | Hypothèse |
|---|---|---|
| `formations_golden_pipeline.json` | 97,7 MB | **Version enrichie (61 657 fiches, +DARES intégré, +RNCP blocs)**, jamais promue |
| `formations_multi_corpus_phaseB/C/D/E.json` | 92-101 MB chacune (×4) | Versions intermédiaires de l'aggregator multi-corpus, à archiver |
| `formations_unified.pre_d5_backup.json` | 93,7 MB | Backup d'avril, à archiver |
| `parcoursup_extended.json` | 14,1 MB | Vraie data Parcoursup étendue, **non intégrée** |
| `insee_salaires_2023.json` | 8,5 MB | Salaires INSEE 2023, possiblement non intégré |
| `inserjeunes_lycee_pro.json` | 90 MB | Insertion lycée pro, raw — corpus dérivé l'utilise mais raw est référencé orphelin |
| `apec_stats_2025.json` | 17 KB | Stats APEC 2025, non intégré |
| `dares_metiers_2030.json` | 1 MB | Doublon de `dares_corpus.json` |

**Finding** : `parcoursup_extended.json` (14 MB) et `insee_salaires_2023.json` (8,5 MB) contiennent probablement des chiffres spécifiques par formation/PCS qui résoudraient en partie le finding #1. À investiguer.

### 3.4 Coût stockage dette

| Dossier | Taille |
|---|---|
| `data/processed/` | **1,14 GB** |
| `data/embeddings/` | **2,02 GB** |
| **Total** | **3,16 GB** |

**Versions formations parallèles** :
- 8 fichiers `formations*.json` (4 actifs, 4 orphelins) = ~750 MB
- 6 fichiers `formations_multi_corpus_phaseB/C/D/E.index` = ~1,2 GB (TOUS orphelins)

**Action** : Phase 1 cleanup déplace les orphelins vers `data/archive/` → libère ~1,5 GB.

---

## 4. Audit `data/embeddings/` — index FAISS

| Index | Taille | Statut |
|---|---|---|
| `formations.index` | 192 MB | ✅ Actif (production) |
| `golden_qa.index` | 181 KB | ✅ Actif (Golden QA few-shot) |
| `formations_unified.index` | 218 MB | ✅ Actif (référencé) |
| `formations_multi_corpus.index` | 196 MB | ✅ Actif (référencé) |
| `formations_multi_corpus_dedupe.index` | 191 MB | ✅ Actif (référencé) |
| `formations_golden_pipeline.index` | 241 MB | ❌ Orphelin |
| `formations_multi_corpus_phaseB.index` | 193 MB | ❌ Orphelin |
| `formations_multi_corpus_phaseC_blocs.index` | 212 MB | ❌ Orphelin |
| `formations_multi_corpus_phaseC_dares.index` | 193 MB | ❌ Orphelin |
| `formations_multi_corpus_phaseD.index` | 212 MB | ❌ Orphelin |
| `formations_multi_corpus_phaseE.index` | 227 MB | ❌ Orphelin |
| `formations.index.pre_*` (×6) | ~390 MB | ❌ Orphelins (backups) |

**Total orphelins : ~1,86 GB** — soit 92% de `data/embeddings/`.

---

## 5. Synthèse des données par tier de qualité

Re-classification des sources selon **densité + spécificité + traçabilité** :

### Tier S — Excellente (officiel + spécifique + traçable)
- **Parcoursup** (10 536 fiches) : 100% des champs admission, URL Parcoursup, profil admis détaillé
- **MonMaster** (8 953 fiches) : Master + URL ONISEP

### Tier A — Bonne (officiel + spécifique partiel)
- **InserSup** (`insersup_insertion.json` 47 MB, non intégré) : insertion réelle Master ESR par formation
- **France Compétences blocs** (`france_comp_blocs_corpus.json` 8 MB) : compétences certifiées par diplôme RNCP
- **APEC régions** (22 KB) : marché cadre par région
- **DARES Métiers 2030** : projections recrutement par FAP
- **CROUS** (logements + restos)

### Tier B — Moyenne (officiel mais agrégé/macro)
- **Cereq** (32 704 fiches, finding #1) : agrégat 6 templates par niveau — **utilisable mais à tagger**
- **INSEE Salaires** (PCS, par âge) : agrégat statistique national, pas spécifique formation
- **INSEE Taux emploi par diplôme** : agrégat niveau

### Tier C — Faible (à challenger)
- **Inserjeunes CFA** (11 314 fiches dont 31% vides) : insertion apprentissage mais souvent NULL
- **RNCP générique** (6 590 fiches dont 22% vides) : titres RNCP sans contenu enrichi
- **ONISEP générique** (4 875 fiches dont 27% vides) : descriptions de diplômes types sans école

### Tier D — Dormante (non intégrée)
- **France Travail** : ft_acces_emploi, ft_marche_travail, ft_offres_emploi, ft_sortants_formation
- **ROME enrichi** : rome_api, romeo (API officielle, fiches métiers détaillées)
- **`parcoursup_extended.json`** (14 MB) : champs Parcoursup étendus non intégrés

---

## 6. Recommandations Phase 1 — Grand ménage (1-2 semaines)

Ordre par ROI décroissant.

### P0 — Politique salaires agrégés Cereq (FINDING #1)

**Décision à acter via ADR-054**.

Recommandation **Option C combinée** :
1. **Tag** chaque chiffre Cereq agrégé : ajouter dans la fiche un champ `insertion_pro_provenance: "cereq_aggregat_niveau_bacX"`.
2. **Adapter la FactCard** : exposer ce flag → le LLM cite *"salaire médian agrégat niveau bac+5 toutes filières : 2080€ [source S1, agrégat Cereq]"* au lieu de présenter comme spécifique.
3. **Activer InserSup** : `insersup_insertion.json` (47 MB déjà collecté) contient l'insertion réelle par master. Pour les fiches MonMaster qui matchent, **remplacer** l'agrégat Cereq par le chiffre InserSup spécifique avec `insertion_pro_provenance: "insersup"`.

Effort : 2 jours. Impact : restaure le narratif "100% spécifique sourcé" sur ~1/3 du corpus.

### P1 — Déduplication corpus

`formations_dedupe.json` existe (87 MB vs 94 MB). Soit promouvoir, soit refaire avec la dernière logique.

Effort : 4 heures. Impact : -28% taille index, retrieval plus efficace.

### P2 — Recalibrer reranker (FINDING #3)

Investiguer pourquoi `labels` n'est rempli que dans 23 fiches sur 48 914. Soit :
- **Réparer le scrape** SecNumEdu/CTI (si la donnée existe à la source)
- **Retirer les 4 boosts inutilisés** du `RerankConfig` (si la donnée n'existe pas)

Effort : 1 jour. Impact : reranker honnête, signaux mesurables.

### P3 — Normalisation régions

24 régions distinctes au lieu de 18 max. Casse de canonisation (Île-de-France vs Ile-de-France).

Effort : 2 heures. Impact : `domain_hint` géographique plus précis.

### P4 — Cleanup orphelins (data/processed + data/embeddings)

Déplacer les 4 orphelins `formations*` + 6 orphelins `embeddings/multi_corpus_*` + 6 backups `pre_*` dans `data/archive/`.

Effort : 30 min. Impact : ~1,5 GB libérés, plus aucune ambiguïté sur le corpus de référence.

### P5 — Décision sur `formations_golden_pipeline.json`

61 657 fiches (vs 48 914 prod), 8 sources (DARES + RNCP blocs intégrés au lieu de référencés à part). Soit le promouvoir comme nouveau corpus de référence, soit l'archiver.

Effort : 1 jour (test sur mini-bench). Impact : décide direction Phase 2.

---

## 7. Recommandations Phase 2 — Activer le dormant (1-2 semaines)

Par priorité d'impact :

### P6 — Intégrer InserSup spécifique
Lié au P0. Le fichier existe déjà. Branchement → enrichissement chiffres Master.

### P7 — Activer France Travail (5 modules dormants)
- **`ft_acces_emploi`** : taux d'accès à l'emploi par diplôme par bassin
- **`ft_marche_travail`** : statistiques marché par région/métier
- **`ft_sortants_formation`** : insertion réelle par formation publique
- **`ft_offres_emploi`** : offres temps réel par métier (pour le champ `realisme` du marché)

Effort : 1 semaine (audit + refactor + intégration). Impact : résout en partie finding #1 sur les chiffres spécifiques.

### P8 — Activer ROME enrichi
- Fiches métiers détaillées : compétences requises, conditions, salaires par tranche d'âge
- À intégrer dans `metiers_corpus.json` ou un nouveau `metiers_detailed_corpus.json`

Effort : 3 jours. Impact : couverture qualitative sur les métiers (utile pour questions "que fait un X").

### P9 — Investiguer `parcoursup_extended.json`
14 MB de data Parcoursup non intégrés. Possiblement champs (frais inscription, alternance dispo, hébergement, dates) qui manquent dans `formations.json`.

Effort : 2 jours.

---

## 8. Recommandations Phase 3 — Enrichissements ciblés (3-4 semaines)

Par ordre de priorité (toutes sources tier 1 officielles uniquement, cf décision narratif) :

### Axe 1 — Calendriers Parcoursup / MonMaster (1 semaine)
- Source : pages officielles Parcoursup et MonMaster
- Format : corpus dédié `calendriers_corpus.json` (dates clés annuelles)
- Couvre : *"Quand commence Parcoursup ?"*, *"Date limite vœux ?"*, *"Phase complémentaire ?"*

### Axe 2 — Aides financières étudiantes (1 semaine)
- Sources tier 1 : `aides.gouv.fr`, `1jeune1solution`, `mes-aides.gouv.fr`, CROUS
- Format : enrichir `financement_corpus.json` existant
- Couvre : bourses CROUS, aides logement, aides spécifiques DROM, contrat engagement jeune

### Axe 3 — Coûts formations privées (2 semaines)
- Sources : sites officiels écoles (HEC, EPITA, EMLV, etc.) — scraping ciblé top 100
- Format : champ `frais_annuels` dans la fiche existante
- Couvre la lacune actuelle (frais quasi-jamais renseignés)

### Axe 4 — Fiches métiers ROME enrichies (1 semaine)
- API ROME 4.0 + ONISEP métiers
- Couvre : compétences requises, conditions exercice, salaires PCS détaillés par âge

---

## 9. Métriques de succès Phase 1+2 (à mesurer après ménage)

| Métrique | Actuel | Cible Phase 1+2 |
|---|---|---|
| Doublons | 28% | 0% |
| Fiches vides | 12,7% | 0% |
| Chiffres "agrégat sans tag" | 67% | 0% (taggés ou remplacés) |
| Fiches avec URL vérifiable | 10% | ≥60% |
| Fiches sans région | 37% | ≤10% |
| Fiches sans niveau | 33% | ≤15% |
| Densité chiffres spécifiques médian | ~1,5 (déduit) | ≥3 |
| Couverture domaine "non classés" | 27,5% | ≤15% |
| Stockage data/ | 3,16 GB | ≤2 GB |
| Mini-bench v4.1 honesty | 1,0 | 1,0 préservé |
| Mini-bench v4.1 latency | 7,26 s | ≤7,26 s préservé |

---

## 10. Roadmap consolidée

```
Phase 0 (FAIT)          : Audit chiffré      ✓ ce document
                          ↓
Phase 1 (1-2 semaines) : ADR-054/055 + ménage
                          P0 salaires Cereq → ADR + tag + InserSup
                          P1 dédup
                          P2 recalibrer reranker
                          P3 normalisation régions
                          P4 cleanup orphelins
                          P5 décision golden_pipeline
                          → re-bench mini v4.1
                          ↓
Phase 2 (1-2 semaines) : Activer dormant
                          P6 InserSup intégration
                          P7 France Travail (5 modules)
                          P8 ROME enrichi
                          P9 parcoursup_extended
                          ↓
Phase 3 (3-4 semaines) : Enrichissement
                          Axe 1 calendriers
                          Axe 2 aides
                          Axe 3 coûts privés
                          Axe 4 fiches métiers
                          ↓
Phase 4 (1 semaine)   : Re-bench complet
                          Run F+G équivalent (100q × multi-systèmes × multi-judges)
                          Comparer avant/après
                          Déclarer corpus production-grade
```

**Effort total estimé : 6-9 semaines.**

---

## 11. Décisions stratégiques à acter avant Phase 1 (ADR à rédiger)

1. **ADR-054 — Politique chiffres agrégés Cereq** : Option A (purge) / B (tag) / C (mix tag + InserSup remplacement)
2. **ADR-055 — Liste blanche sources autorisées** : tier 1 officiel État / tier 2 semi-officiel / exclusions explicites
3. **ADR-056 — Pas d'avis subjectifs** : décision validée → pas de scraping forums/Glassdoor/Studyrama, redirection user vers ces ressources externes en fin de réponse
4. **ADR-057 — Corpus de référence unique** : choisir entre `formations.json` (48k actuel) vs `formations_golden_pipeline.json` (61k enrichi) vs nouveau corpus post-Phase 1

---

*Audit créé le 2026-05-07. Source des chiffres : scripts d'audit reproductibles disponibles dans la conversation. Toutes les métriques peuvent être re-vérifiées en relançant les scripts sur `data/processed/formations.json` (commit 5f2b201).*
