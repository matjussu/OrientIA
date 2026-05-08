# Audit schéma corpora annexes — 2026-05-07

> Phase A.4 du plan corpus v5 (ADR-057). Vérifie la conformité des
> corpora annexes au schéma minimal attendu par le merger v3 et la
> FactCard de Phase A.1.

## Résumé

- **Corpora audités** : 22
- **Corpora présents (chargés)** : 22
- **Corpora absents** : 0
- **Records totaux** : 61350
- **Records conformes** : 59592 (97.1%)
- **Records non-conformes** : 1758
- **Corpora avec issues** : 2

## Tableau récapitulatif

| Corpus | Type | n records | Conforme | % | Domain attendu | Tier 1 dom. |
|---|:-:|---:|---:|---:|---|:-:|
| MonMaster formations | primary | 8953 | 8953 | 100.0 ✓ | (libre) | ✓ |
| LBA formations | primary | 6646 | 6646 | 100.0 ✓ | (libre) | ✓ |
| Inserjeunes CFA | primary | 11314 | 11314 | 100.0 ✓ | (libre) | ✓ |
| RNCP certifications | primary | 6590 | 6590 | 100.0 ✓ | (libre) | ✓ |
| ONISEP formations extended | primary | 4775 | 4775 | 100.0 ✓ | (libre) | ✓ |
| Parcoursup extended | primary | 9212 | 9212 | 100.0 ✓ | (libre) | ✓ |
| DARES Métiers 2030 | annexe | 1160 | 1160 | 100.0 ✓ | metier_prospective (100.0%) | ✓ |
| APEC régions | annexe | 13 | 13 | 100.0 ✓ | apec_region (100.0%) | — |
| CROUS corpus | annexe | 39 | 39 | 100.0 ✓ | crous (100.0%) | ✓ |
| INSEE salaires PCS | annexe | 59 | 59 | 100.0 ✓ | insee_salaire (100.0%) | ✓ |
| France Compétences blocs | annexe | 4891 | 4891 | 100.0 ✓ | competences_certif (100.0%) | ✓ |
| Inserjeunes lycée pro corpus | annexe | 2693 | 2693 | 100.0 ✓ | formation_insertion (100.0%) | ✓ |
| InserSup corpus | annexe | 368 | 368 | 100.0 ✓ | insertion_pro (100.0%) | ✓ |
| Métiers IDEO ONISEP | annexe | 1075 | 1075 | 100.0 ✓ | metier (100.0%) | ✓ |
| ONISEP métiers | annexe | 1518 | 0 | 0.0 ✗ | metier (0.0%) | ✓ |
| Parcours bacheliers | annexe | 151 | 151 | 100.0 ✓ | parcours_bacheliers (100.0%) | ✓ |
| Doctorat IP | annexe | 240 | 0 | 0.0 ✗ | insertion_pro (0.0%) | ✓ |
| DROM-COM territoires | annexe | 16 | 16 | 100.0 ✓ | territoire_drom (100.0%) | ✓ |
| Voie pré-bac | annexe | 20 | 20 | 100.0 ✓ | voie_pre_bac (100.0%) | ✓ |
| Financement | annexe | 28 | 28 | 100.0 ✓ | financement_etudes (100.0%) | ✓ |
| Corrections factuelles | annexe | 5 | 5 | 100.0 ✓ | (libre) | ✓ |
| ROME 4.0 métiers | annexe | 1584 | 1584 | 100.0 ✓ | metier_detail (100.0%) | ✓ |

Légende :
- Type `primary` : corpus formations principales (MonMaster, LBA, Inserjeunes CFA, RNCP, ONISEP/Parcoursup extended). Schema réduit attendu (juste `source` + nom inférable). Le merger v3 ajoutera `id`/`domain`/`text` au Stage 2 (MERGE_FUZZY) + Stage 5 (NORMALIZE).
- Type `annexe` : corpus annexe avec domain natif. Schema complet attendu (`id`, `domain`, `source`, `text` non-vides + tier inférable).
- `✓` : 100% conforme
- `⚠` : ≥80% conforme
- `✗` : <80% conforme
- Tier 1 dom. `✓` : 100% des records classés tier_1
- Tier 1 dom. `△` : tier_1 partiellement présent
- Tier 1 dom. `—` : aucun tier_1 inféré (fixer la source pour Phase B)

## Détails par corpus

### MonMaster formations

- Path : `data/processed/monmaster_formations.json`
- Records : 8953
- Conformes : 8953 (100.0%)
- Non conformes : 0

**Distribution `domain`** :
- `__none__` : 8953

**Distribution `source`** :
- `monmaster` : 8953

**Distribution tier (inféré ADR-055)** :
- `tier_1` : 8953

### LBA formations

- Path : `data/processed/lba_formations.json`
- Records : 6646
- Conformes : 6646 (100.0%)
- Non conformes : 0

**Distribution `domain`** :
- `__none__` : 6646

**Distribution `source`** :
- `labonnealternance` : 6646

**Distribution tier (inféré ADR-055)** :
- `tier_1` : 6646

### Inserjeunes CFA

- Path : `data/processed/inserjeunes_cfa.json`
- Records : 11314
- Conformes : 11314 (100.0%)
- Non conformes : 0

**Distribution `domain`** :
- `__none__` : 11314

**Distribution `source`** :
- `inserjeunes_cfa` : 11314

**Distribution tier (inféré ADR-055)** :
- `tier_1` : 11314

### RNCP certifications

- Path : `data/processed/rncp_certifications.json`
- Records : 6590
- Conformes : 6590 (100.0%)
- Non conformes : 0

**Distribution `domain`** :
- `__none__` : 6590

**Distribution `source`** :
- `rncp` : 6590

**Distribution tier (inféré ADR-055)** :
- `tier_1` : 6590

### ONISEP formations extended

- Path : `data/processed/onisep_formations_extended.json`
- Records : 4775
- Conformes : 4775 (100.0%)
- Non conformes : 0

**Distribution `domain`** :
- `__none__` : 4775

**Distribution `source`** :
- `onisep` : 4775

**Distribution tier (inféré ADR-055)** :
- `tier_1` : 4775

### Parcoursup extended

- Path : `data/processed/parcoursup_extended.json`
- Records : 9212
- Conformes : 9212 (100.0%)
- Non conformes : 0

**Distribution `domain`** :
- `__none__` : 9212

**Distribution `source`** :
- `parcoursup` : 9212

**Distribution tier (inféré ADR-055)** :
- `tier_1` : 9212

### DARES Métiers 2030

- Path : `data/processed/dares_corpus.json`
- Records : 1160
- Conformes : 1160 (100.0%)
- Non conformes : 0

**Distribution `domain`** :
- `metier_prospective` : 1160

**Distribution `source`** :
- `dares_metiers_2030` : 1160

**Distribution tier (inféré ADR-055)** :
- `tier_1` : 1160

### APEC régions

- Path : `data/processed/apec_regions_corpus.json`
- Records : 13
- Conformes : 13 (100.0%)
- Non conformes : 0

**Distribution `domain`** :
- `apec_region` : 13

**Distribution `source`** :
- `apec_observatoire_emploi_cadre_2026` : 13

**Distribution tier (inféré ADR-055)** :
- `tier_2` : 13

### CROUS corpus

- Path : `data/processed/crous_corpus.json`
- Records : 39
- Conformes : 39 (100.0%)
- Non conformes : 0

**Distribution `domain`** :
- `crous` : 39

**Distribution `source`** :
- `crous_combine_logements_restos` : 39

**Distribution tier (inféré ADR-055)** :
- `tier_1` : 39

### INSEE salaires PCS

- Path : `data/processed/insee_salaan_corpus.json`
- Records : 59
- Conformes : 59 (100.0%)
- Non conformes : 0

**Distribution `domain`** :
- `insee_salaire` : 59

**Distribution `source`** :
- `insee_salaan_2023` : 59

**Distribution tier (inféré ADR-055)** :
- `tier_1` : 59

### France Compétences blocs

- Path : `data/processed/france_comp_blocs_corpus.json`
- Records : 4891
- Conformes : 4891 (100.0%)
- Non conformes : 0

**Distribution `domain`** :
- `competences_certif` : 4891

**Distribution `source`** :
- `rncp_blocs` : 4891

**Distribution tier (inféré ADR-055)** :
- `tier_1` : 4891

### Inserjeunes lycée pro corpus

- Path : `data/processed/inserjeunes_lycee_pro_corpus.json`
- Records : 2693
- Conformes : 2693 (100.0%)
- Non conformes : 0

**Distribution `domain`** :
- `formation_insertion` : 2693

**Distribution `source`** :
- `inserjeunes_lycee_pro` : 2693

**Distribution tier (inféré ADR-055)** :
- `tier_1` : 2693

### InserSup corpus

- Path : `data/processed/insersup_corpus.json`
- Records : 368
- Conformes : 368 (100.0%)
- Non conformes : 0

**Distribution `domain`** :
- `insertion_pro` : 368

**Distribution `source`** :
- `insersup_mesr` : 368

**Distribution tier (inféré ADR-055)** :
- `tier_1` : 368

### Métiers IDEO ONISEP

- Path : `data/processed/metiers_corpus.json`
- Records : 1075
- Conformes : 1075 (100.0%)
- Non conformes : 0

**Distribution `domain`** :
- `metier` : 1075

**Distribution `source`** :
- `onisep_ideo_fiches` : 1075

**Distribution tier (inféré ADR-055)** :
- `tier_1` : 1075

### ONISEP métiers

- Path : `data/processed/onisep_metiers.json`
- Records : 1518
- Conformes : 0 (0.0%)
- Non conformes : 1518

**Distribution `domain`** :
- `__none__` : 1518

**Distribution `source`** :
- `onisep_metiers` : 1518

**Distribution tier (inféré ADR-055)** :
- `tier_1` : 1518

**Issues** :
- champ 'id' absent ou vide : 1518 fois
- champ 'domain' absent ou vide : 1518 fois
- champ 'text' absent ou vide : 1518 fois

**Exemples records non-conformes (premiers 3)** :
- record #0 (id=None) : champ 'id' absent ou vide, champ 'domain' absent ou vide, champ 'text' absent ou vide
- record #1 (id=None) : champ 'id' absent ou vide, champ 'domain' absent ou vide, champ 'text' absent ou vide
- record #2 (id=None) : champ 'id' absent ou vide, champ 'domain' absent ou vide, champ 'text' absent ou vide

### Parcours bacheliers

- Path : `data/processed/parcours_bacheliers_corpus.json`
- Records : 151
- Conformes : 151 (100.0%)
- Non conformes : 0

**Distribution `domain`** :
- `parcours_bacheliers` : 151

**Distribution `source`** :
- `mesri_parcours_bacheliers_licence` : 151

**Distribution tier (inféré ADR-055)** :
- `tier_1` : 151

### Doctorat IP

- Path : `data/processed/ip_doc_doctorat.json`
- Records : 240
- Conformes : 0 (0.0%)
- Non conformes : 240

**Distribution `domain`** :
- `__none__` : 240

**Distribution `source`** :
- `ip_doc_doctorat` : 240

**Distribution tier (inféré ADR-055)** :
- `tier_1` : 240

**Issues** :
- champ 'id' absent ou vide : 240 fois
- champ 'domain' absent ou vide : 240 fois
- champ 'text' absent ou vide : 240 fois

**Exemples records non-conformes (premiers 3)** :
- record #0 (id=None) : champ 'id' absent ou vide, champ 'domain' absent ou vide, champ 'text' absent ou vide
- record #1 (id=None) : champ 'id' absent ou vide, champ 'domain' absent ou vide, champ 'text' absent ou vide
- record #2 (id=None) : champ 'id' absent ou vide, champ 'domain' absent ou vide, champ 'text' absent ou vide

### DROM-COM territoires

- Path : `data/processed/domtom_corpus.json`
- Records : 16
- Conformes : 16 (100.0%)
- Non conformes : 0

**Distribution `domain`** :
- `territoire_drom` : 16

**Distribution `source`** :
- `domtom_curated` : 16

**Distribution tier (inféré ADR-055)** :
- `tier_1` : 16

### Voie pré-bac

- Path : `data/processed/voie_pre_bac_corpus.json`
- Records : 20
- Conformes : 20 (100.0%)
- Non conformes : 0

**Distribution `domain`** :
- `voie_pre_bac` : 20

**Distribution `source`** :
- `onisep_formations_extended` : 20

**Distribution tier (inféré ADR-055)** :
- `tier_1` : 20

### Financement

- Path : `data/processed/financement_corpus.json`
- Records : 28
- Conformes : 28 (100.0%)
- Non conformes : 0

**Distribution `domain`** :
- `financement_etudes` : 28

**Distribution `source`** :
- `financement_dispositifs_curated` : 28

**Distribution tier (inféré ADR-055)** :
- `tier_1` : 28

### Corrections factuelles

- Path : `data/processed/corrections_factuelles_corpus.json`
- Records : 5
- Conformes : 5 (100.0%)
- Non conformes : 0

**Distribution `domain`** :
- `correction_factuelle` : 5

**Distribution `source`** :
- `corrections_factuelles_curated` : 5

**Distribution tier (inféré ADR-055)** :
- `tier_1` : 5

### ROME 4.0 métiers

- Path : `data/processed/rome_metier_corpus.json`
- Records : 1584
- Conformes : 1584 (100.0%)
- Non conformes : 0

**Distribution `domain`** :
- `metier_detail` : 1584

**Distribution `source`** :
- `rome_api_v4` : 1584

**Distribution tier (inféré ADR-055)** :
- `tier_1` : 1584

## Recommandations pour Phase B (merger v3)

### Corpora avec issues à corriger
- **ONISEP métiers** : 1518 non-conformes — issue principale : champ 'id' absent ou vide (1518 fois)
- **Doctorat IP** : 240 non-conformes — issue principale : champ 'id' absent ou vide (240 fois)

## Critères de pass pour Phase B

1. ≥95% des records de chaque corpus annexe ont les 5 champs obligatoires (`id`, `domain`, `source`, `text`, tier inférable)
2. 100% des sources listées dans SOURCE_TO_TIER (cf `src/rag/fact_card.py`)
3. Aucun corpus présent dans `CORPORA_TO_AUDIT` mais absent du filesystem (sauf opt-out explicite)

Si un de ces critères échoue, il faut corriger le `build_*.py` correspondant
OU étendre `SOURCE_TO_TIER` (ADR-055) avant de lancer le merger v3.
