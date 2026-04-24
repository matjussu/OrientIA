# Audit qualité data OrientIA — 2026-04-24

Généré automatiquement par `scripts/audit_data_quality.py`. 
Vérifie tous les corpus normalisés dans `data/processed/`.

## Résumé global

- **monmaster_formations.json** : 8,953 fiches ✅
- **rncp_certifications.json** : 6,590 fiches ✅
- ℹ️  **onisep_metiers.json** (metiers) : 1,518 entrées
- **onisep_formations_extended.json** : 4,775 fiches ✅
- **lba_formations.json** : 6,646 fiches ✅
- ℹ️  **cereq_insertion_stats.json** (stats) : 43 entrées
- ❌ **insee_salaires_pcs_age.json** : absent (ingestion pas faite localement)
- **parcoursup_extended.json** : 9,212 fiches ✅
- **formations.json** : 37,600 fiches ⚠️ 1567 doublons

**Total fiches auditées** : 73,776

---

## Détail par source

### `monmaster_formations.json`

- Total : 8,953
- Distribution par phase : `{'master': 8953}`
- Distribution par niveau : `{'bac+5': 8953}`
- Top 5 domaines : `{}`
- Sources : `{'monmaster': 8953}`
- Manques critiques : `{}`
- Valeurs suspectes par champ : `{}`
- Doublons (signatures identiques) : 0
- `taux_admission` hors bornes [0,1] : 0

### `rncp_certifications.json`

- Total : 6,590
- Distribution par phase : `{'initial': 4810, 'master': 1780}`
- Distribution par niveau : `{'bac': 776, 'cap-bep': 627, 'bac+2': 680, 'bac+3': 1275, 'bac+5': 1779, 'bac+8': 1}`
- Top 5 domaines : `{}`
- Sources : `{'rncp': 6590}`
- Manques critiques : `{}`
- Valeurs suspectes par champ : `{}`
- Doublons (signatures identiques) : 0
- `taux_admission` hors bornes [0,1] : 0

### `onisep_metiers.json`

- Type : `metiers`
- Entrées : 1,518
- Sample keys : `['source', 'type', 'libelle', 'codes_rome', 'rome_link', 'url_onisep', 'gfe', 'domaine', 'sous_domaine', 'publication']`

### `onisep_formations_extended.json`

- Total : 4,775
- Distribution par phase : `{'initial': 2984, 'master': 1791}`
- Distribution par niveau : `{'bac+3': 1033, 'bac+5': 1789, 'bac+2': 653, 'bac+8': 2}`
- Top 5 domaines : `{'eco_gestion': 1181, 'lettres_arts': 746, 'ingenierie_industrielle': 599, 'sciences_fondamentales': 548, 'sport': 408}`
- Sources : `{'onisep': 4775}`
- Manques critiques : `{}`
- Valeurs suspectes par champ : `{}`
- Doublons (signatures identiques) : 0
- `taux_admission` hors bornes [0,1] : 0

### `lba_formations.json`

- Total : 6,646
- Distribution par phase : `{'reorientation': 6646}`
- Distribution par niveau : `{'cap-bep': 263, 'bac': 1279, 'bac+5': 1806, 'bac+3': 1300, 'bac+2': 1998}`
- Top 5 domaines : `{'eco_gestion': 2330, 'lettres_arts': 787, 'sport': 746, 'sante': 689, 'sciences_fondamentales': 640}`
- Sources : `{'labonnealternance': 6646}`
- Manques critiques : `{}`
- Valeurs suspectes par champ : `{}`
- Doublons (signatures identiques) : 0
- `taux_admission` hors bornes [0,1] : 0

### `cereq_insertion_stats.json`

- Type : `stats`
- Entrées : 43
- Sample keys : `['source', 'cohorte', 'code', 'libelle_menu', 'libelle_complet', 'niveau', 'domaine', 'horizon_3ans', 'horizon_6ans']`

### `parcoursup_extended.json`

- Total : 9,212
- Distribution par phase : `{'initial': 8473, 'master': 739}`
- Distribution par niveau : `{'bac+2': 2623, 'bac+3': 4264, 'bac+5': 739}`
- Top 5 domaines : `{'eco_gestion': 2464, 'ingenierie_industrielle': 1085, 'sante': 981, 'sciences_fondamentales': 918, 'langues': 888}`
- Sources : `{'parcoursup': 9212}`
- Manques critiques : `{}`
- Valeurs suspectes par champ : `{}`
- Doublons (signatures identiques) : 0
- `taux_admission` hors bornes [0,1] : 0

### `formations.json`

- Total : 37,600
- Distribution par phase : `{'initial': 17619, 'master': 13335, 'reorientation': 6646}`
- Distribution par niveau : `{'bac+3': 8279, 'bac+2': 6339, 'bac+5': 15138, 'bac+8': 3, 'bac': 2055, 'cap-bep': 890}`
- Top 5 domaines : `{'eco_gestion': 7968, 'sciences_humaines': 4341, 'ingenierie_industrielle': 4263, 'sciences_fondamentales': 4053, 'sante': 3011}`
- Sources : `{'parcoursup': 10536, 'onisep': 4875, 'monmaster': 8953, 'rncp': 6590, 'labonnealternance': 6646}`
- Manques critiques : `{}`
- Valeurs suspectes par champ : `{}`
- Doublons (signatures identiques) : 1567
- `taux_admission` hors bornes [0,1] : 0
- Top 5 doublons : `[{'sig': "programme grande ecole|ministere de l'enseignement superieur et de la recherche|", 'count': 4}, {'sig': "boulanger|ministere de l'education nationale et de la jeunesse|", 'count': 4}, {'sig': "diplôme supérieur en marketing, commerce et gestion|ministere de l'enseignement superieur et de la recherche|", 'count': 4}, {'sig': "maçon|ministere de l'education nationale et de la jeunesse|", 'count': 3}, {'sig': "couvreur|ministere de l'education nationale et de la jeunesse|", 'count': 3}]`

---

## Répartition phase cumulée (vs ADR-039 cible 33/33/34)

- `initial` : 33,886 (45.9%) — cible 33%
- `master` : 26,598 (36.1%) — cible 33%
- `reorientation` : 13,292 (18.0%) — cible 33%

Si un phase dépasse 40% ou tombe sous 25% → signal de déséquilibre, action S+2 (up-sample ou down-sample).

---

## Verdict re-index FAISS (D6)

✅ **GO** : aucune anomalie bloquante détectée. Safe to proceed avec 
re-index FAISS sur corpus élargi.

Action post-validation Matteo budget $5-10 :
```bash
python -m src.rag.embeddings  # re-build FAISS index
```

---

*Rapport généré par `scripts/audit_data_quality.py`. Re-exécuter après 
chaque nouvelle ingestion pour détecter les régressions.*
