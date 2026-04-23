# Audit qualité data OrientIA — 2026-04-23

Généré automatiquement par `scripts/audit_data_quality.py`. 
Vérifie tous les corpus normalisés dans `data/processed/`.

## Résumé global

- **monmaster_formations.json** : 16,257 fiches ⚠️ 7304 doublons, 6 taux hors bornes
- **rncp_certifications.json** : 6,590 fiches ✅
- ℹ️  **onisep_metiers.json** (metiers) : 1,518 entrées
- ❌ **cereq_insertion_stats.json** : absent (ingestion pas faite localement)
- ❌ **insee_salaires_pcs_age.json** : absent (ingestion pas faite localement)
- **parcoursup_extended.json** : 9,212 fiches ✅
- **formations.json** : 1,424 fiches ⚠️ 1424 manques critiques

**Total fiches auditées** : 33,483

---

## Détail par source

### `monmaster_formations.json`

- Total : 16,257
- Distribution par phase : `{'master': 16257}`
- Distribution par niveau : `{'bac+5': 16257}`
- Top 5 domaines : `{}`
- Sources : `{'monmaster': 16257}`
- Manques critiques : `{}`
- Valeurs suspectes par champ : `{}`
- Doublons (signatures identiques) : 7304
- `taux_admission` hors bornes [0,1] : 6
- Top 5 doublons : `[{'sig': 'id:mm_ifc=0900820SRD2N', 'count': 2}, {'sig': 'id:mm_ifc=0900894XC6IF', 'count': 2}, {'sig': 'id:mm_ifc=0900916WE8BZ', 'count': 2}, {'sig': 'id:mm_ifc=0900916WQ3HF', 'count': 2}, {'sig': 'id:mm_ifc=0900924E87IM', 'count': 2}]`

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
- Distribution par phase : `{}`
- Distribution par niveau : `{'bac+3': 407, 'bac+2': 385, 'bac+5': 72}`
- Top 5 domaines : `{'sante': 981, 'cyber': 352, 'data_ia': 91}`
- Sources : `{'parcoursup': 1324, 'onisep': 100}`
- Manques critiques : `{'phase': 1424}`
- Valeurs suspectes par champ : `{}`
- Doublons (signatures identiques) : 0
- `taux_admission` hors bornes [0,1] : 0

---

## Répartition phase cumulée (vs ADR-039 cible 33/33/34)

- `master` : 18,776 (58.6%) — cible 33%
- `initial` : 13,283 (41.4%) — cible 33%

Si un phase dépasse 40% ou tombe sous 25% → signal de déséquilibre, action S+2 (up-sample ou down-sample).

---

## Verdict re-index FAISS (D6)

🔴 **NO-GO** : 1 anomalie(s) critique(s) détectée(s). 
Corriger avant de lancer le re-index (évite de re-embed des fiches corrompues).

---

*Rapport généré par `scripts/audit_data_quality.py`. Re-exécuter après 
chaque nouvelle ingestion pour détecter les régressions.*
