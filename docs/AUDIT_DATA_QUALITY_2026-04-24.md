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
- **formations.json** : 1,424 fiches ✅

**Total fiches auditées** : 37,600

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

- Total : 1,424
- Distribution par phase : `{'initial': 1352, 'master': 72}`
- Distribution par niveau : `{'bac+3': 407, 'bac+2': 385, 'bac+5': 72}`
- Top 5 domaines : `{'sante': 981, 'cyber': 352, 'data_ia': 91}`
- Sources : `{'parcoursup': 1324, 'onisep': 100}`
- Manques critiques : `{}`
- Valeurs suspectes par champ : `{}`
- Doublons (signatures identiques) : 0
- `taux_admission` hors bornes [0,1] : 0

---

## Répartition phase cumulée (vs ADR-039 cible 33/33/34)

- `initial` : 17,619 (46.9%) — cible 33%
- `master` : 13,335 (35.5%) — cible 33%
- `reorientation` : 6,646 (17.7%) — cible 33%

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
