# TODO Matteo — Actions APIs & Data sources OrientIA

**Dernière MAJ** : 2026-04-23 17:15 CEST
**Objectif** : tout ce que Matteo doit faire côté APIs + downloads externes pour que Claudette puisse continuer les ingestions en autonomie.

---

## 📊 État actuel du corpus OrientIA

| Métrique | Valeur |
|---|---|
| Total fiches formations ingérées | **44 904** |
| Sources actives | Parcoursup extended + MonMaster + RNCP + ONISEP (métiers+formations ext) + LBA alternance |
| PRs mergées cette session | 7 (#30-36) |
| Phase répartition (ADR-039 cible 33/33/34) | Initial ~35% / Master ~50% / Reorientation 14.8% |
| APIs France Travail activées (8) | ROME 4.0 × 4 (utilisées) / Anotéa / Marché travail / Sortants formation / Accès emploi demandeurs |
| Scopes OAuth2 cochés dans app OrientIA | 5 (ROME 4.0 × 4 + nomenclatureRome) — **4-5 à ajouter** (cf §1 ci-dessous) |

---

## 🎯 Actions à faire (priorisées par impact OrientIA)

### §1 — 🔴 PRIORITÉ P0 — Cocher 4 scopes OAuth2 dans l'app OrientIA (France Travail)

**Durée** : 3-5 minutes devant l'interface dashboard FT.
**Débloque** : 3 ingestions live S+2 (Marché du travail + Sortants formation + Accès emploi + Offres d'emploi) pour **+8-12 jours de travail data**.

**Problème détecté ce soir** : les APIs sont **activées dans ton listing général** (8 APIs dans ton espace dev), MAIS les **scopes OAuth2** correspondants ne sont **pas cochés dans la config de ton app spécifique "OrientIA"**. Résultat : le token OAuth2 ne donne accès qu'aux 4 ROME 4.0 + nomenclature, pas aux autres.

**Procédure** :

1. Aller sur https://francetravail.io/dashboard (ou équivalent "Mon espace développeur")
2. Sélectionner ton app **OrientIA** (celle qui a `FT_CLIENT_ID` commençant par `PAR_orientiaassistantorie_...`)
3. Onglet / Section "**Habilitations**" ou "**Scopes**" ou "**APIs activées pour cette app**"
4. Tu verras une liste des APIs disponibles + checkboxes à cocher. Cocher **les 4 scopes suivants** :

   - [ ] **`api_marchedutravailv1`** — Marché du travail v1 (tension marché)
   - [ ] **`api_sortants-formation-acces-a-lemploiv1`** — Sortants de formation v1 (insertion post-formation)
   - [ ] **`api_acces-a-lemploi-des-demandeurs-demploiv1`** — Accès à l'emploi demandeurs v1 (taux retour emploi)
   - [ ] **`api_offresdemploi-v2`** — Offres d'emploi France Travail v2 (annonces temps réel)

   ⚠️ **Noms exacts à confirmer** : le dashboard FT expose les scopes dans un dropdown avec leur nom officiel. Si les noms ci-dessus ne matchent pas exactement ce que tu vois, choisir ceux qui correspondent au libellé humain (ex "Marché du travail v1", "Sortants de formation et accès à l'emploi v1", etc.).

5. **Sauvegarder/Soumettre**. Activation **immédiate** pour une app existante (pas de review 24-48h).
6. Ping Jarvis sur Telegram : "scopes cochés" → Claudette pourra lancer les 4 ingestions demain.

**Tests empiriques ce soir** : j'ai testé les 6 variants de nom possibles via OAuth2, tous retournent `HTTP 400 invalid_scope`. La liste ci-dessus est basée sur les conventions FT, mais **l'UI dashboard fait foi** pour le nom exact.

**Scaffold côté code** : les 5 modules (4 FT + ROMEO) sont déjà prêts dans ce commit, 20 tests mockés verts. Ingestion live lance-t-elle au premier `gh pr merge` de la PR associée + scopes activés.

---

### §2 — 🟡 PRIORITÉ P1 — Activer ROMEO (IA Compétences — scope ou portail séparé)

**Durée** : 5-10 minutes (procédure à vérifier).
**Débloque** : `ProfileClarifier` agent S+2 Axe 2 (matching texte libre utilisateur → codes ROME + compétences).
**Valeur** : **critique pour Sprint 2** — sans ROMEO on reste sur `DOMAIN_KEYWORDS` regex custom fragile vs matching sémantique officiel FT.

**Procédure (à confirmer)** :

**Option A** : ROMEO est un scope OAuth2 classique à cocher dans la même app OrientIA :
- [ ] `api_romeov2` (ou `api_romeo-v2`) — à vérifier via dropdown dashboard

**Option B** : ROMEO passe par un portail / URL dédié :
- URL candidate : https://francetravail.io/data/api/romeo-2
- Peut nécessiter un **2nd signup** distinct (ou juste coché dans même app).

→ Si Matteo ne trouve pas le scope dans le dropdown de §1, tester Option B. Sinon toutes les deux = OK.

---

### §3 — 🟢 PRIORITÉ P1-P2 — Downloads manuels data externes (3 sources)

Ces 3 sources ne sont **pas** accessibles via API live. Matteo doit télécharger les fichiers et les placer dans des dossiers locaux.

#### §3.A — 📋 Céreq Enquêtes Génération (~15 min)

**Utilité** : taux insertion + salaire médian + % CDI par niveau diplôme × secteur pour phase (c).

**Procédure** :

1. Aller sur https://www.cereq.fr/datavisualisation/insertion-professionnelle-des-jeunes/les-chiffres-cles-par-diplome
2. Télécharger les CSVs disponibles (boutons "Télécharger" / "Exporter" sur chaque dashboard — typiquement 1 CSV par niveau diplôme et par cohorte)
3. Copier les fichiers dans `~/projets/OrientIA/data/raw/cereq/` en les nommant :
   - `cereq_chiffres_cles_gen2017.csv`
   - `cereq_chiffres_cles_gen2020.csv` (si dispo)
   - `cereq_salaires_master_gen2017.csv` (etc.)
4. Ping Jarvis : "CSVs Céreq dispos" → Claudette lance `python -m src.collect.cereq` instant.

**Parser** : `src/collect/cereq.py` déjà prêt (scaffold PR #32 mergée), permissif sur delimiters FR/EN et noms colonnes variants.

#### §3.B — 📋 INSEE Base Tous Salariés 2023 (~10-15 min + bandwidth)

**Utilité** : salaires par PCS × âge pour phase (c) "combien gagne-t-on après X années dans ce métier".

**Procédure** :

1. Aller sur https://www.insee.fr/fr/statistiques/8730395 (Base Tous Salariés 2023)
2. Télécharger le fichier **"salariés" format CSV** (~100-500 MB).
   - Alternative format Parquet si plus pratique bandwidth.
3. Placer dans `~/projets/OrientIA/data/raw/insee/bts_2023_salaries.csv`
4. Ping Jarvis : "CSV INSEE dispo" → Claudette lance `python -m src.collect.insee_emploi` (agrégation pandas ~30s-2min).

**Output attendu** : `data/processed/insee_salaires_pcs_age.json` (stats agrégées par PCS × tranche âge).

**Alternative moins lourde** : si le CSV complet est trop gros, chercher un dataset pré-agrégé sur data.gouv.fr (mot-clé "salaires PCS 2020 tranche age") — peut être 5-20 MB au lieu de 500 MB, même usage final.

#### §3.C — 📋 APEC rapports Observatoire (~15-30 min)

**Utilité** : salaires cadres par ancienneté 1/3/5/10 ans pour phase (c) "trajectoire carrière".

**Procédure** :

1. Aller sur https://corporate.apec.fr/home/nos-etudes-et-analyses.html (ou équivalent "Observatoire")
2. Filtrer par "Rémunérations" / "Salaires cadres" / "Études salaires"
3. Télécharger les 5-10 **rapports PDF** les plus récents (idéalement les éditions 2024-2025) couvrant :
   - Salaires cadres IT / numérique (pour phase c tech)
   - Salaires cadres Finance / Gestion
   - Salaires cadres Santé / Sciences
   - "Les jeunes diplômés" (édition annuelle — critique pour 17-25)
4. Placer dans `~/projets/OrientIA/data/raw/apec/` avec noms lisibles :
   - `apec_salaires_it_2025.pdf`
   - `apec_jeunes_diplomes_2025.pdf`
   - ... etc.
5. Ping Jarvis : "PDFs APEC dispos" → Claudette lance le parser PDF (à développer S+2, effort estimé 3-5j).

⚠️ **Note effort Claudette** : le parsing APEC PDF est plus risqué (structure non-homogène potentielle), 3-5 jours d'implémentation vs 0.5-1j pour CSVs. OK pour S+2 mais pas critique si le temps manque INRIA.

---

### §4 — ⚪ OPTIONNEL — 2 signups additionnels si Matteo veut étendre encore

#### §4.A — ⚪ Open Formation (api.gouv.fr, P1-P2)

**Durée** : ~10 min signup + ~24-48h habilitation.
**Utilité** : catalogue formations FT + partenaires + RNCP (complément LBA + ONISEP).
**Mon avis** : **skippable** tant qu'on n'a pas mesuré le gap vs ONISEP extended. ADR-043 le classait P0 mais Matteo a choisi de ne pas l'inclure dans son ordre — OK, on peut rester comme ça.

**Si tu changes d'avis, procédure** :
1. https://api.gouv.fr/les-api/api-open-formation (ou portail FT pour la version open)
2. Signup avec email pro, demande d'habilitation
3. Token dans `.env` : `OPEN_FORMATION_API_KEY=...` (à définir post-procedure)

#### §4.B — ⚪ Reddit OAuth (décision S+2)

**Durée** : ~5 min.
**Utilité** : dataset RAFT S+3 (scraping r/Parcoursup + r/EtudesSuperieures).
**Reste en décision S+2** selon volume scraping autonome (forums ONISEP + Parcoursup public + StackExchange + HackerNews).

---

## ⏱️ Récapitulatif temps estimé Matteo

| Action | Durée | Priorité | Débloque |
|---|---|---|---|
| §1 Scopes dashboard FT (4 scopes) | 3-5 min | **🔴 P0** | 3-4 ingestions FT live |
| §2 ROMEO (scope ou portail) | 5-10 min | 🟡 P1 | ProfileClarifier agent S+2 |
| §3.A Céreq CSVs | 15 min | 🟢 P1 | Insertion 3 ans post-diplôme |
| §3.B INSEE BTS | 10-15 min + bandwidth | 🟢 P1 | Salaires par PCS × âge |
| §3.C APEC PDFs | 15-30 min | 🟢 P2 | Salaires cadres 1/3/5/10 ans |
| §4.A Open Formation (optionnel) | 10 min + 48h | ⚪ P2 | Catalogue FT + partenaires |
| §4.B Reddit (optionnel S+2) | 5 min | ⚪ P3 | Dataset RAFT γ |

**Total critique (P0 + P1)** : **~35-45 min** étalable sur plusieurs sessions.
**Total maximal avec optionnels** : ~1h + temps bandwidth downloads.

---

## 🔐 Checks sécurité systématiques

Après chaque copie de credentials dans `.env` :

```bash
cd ~/projets/OrientIA
# Vérif que .env est bien dans .gitignore
grep -c "^\.env$" .gitignore   # doit retourner 1

# Vérif que .env n'est pas tracké
git ls-files | grep "^\.env$"  # doit être vide

# Verif .env.example ne contient QUE des placeholders
grep -v "your_\|_here" .env.example | grep "^[A-Z].*="  # doit être vide
```

**Reco post-stabilisation projet** : revoke + regenerate tous les secrets (FT, ONISEP, LBA) car ils ont été exposés Telegram historique pendant cette session.

---

## 📁 État des modules code côté Claudette

| Source | Module | Statut | Tests |
|---|---|---|---|
| Parcoursup extended | `src/collect/parcoursup.py` | ✅ Ingesté 9 212 fiches | ✅ |
| MonMaster | `src/collect/monmaster.py` | ✅ Ingesté 16 257 fiches | ✅ |
| RNCP France Compétences | `src/collect/rncp.py` | ✅ Ingesté 6 590 certifs | ✅ |
| ONISEP formations extended | `src/collect/onisep_formations_extended.py` | ✅ Ingesté 4 775 fiches | ✅ |
| ONISEP métiers (D12) | `src/collect/onisep_metiers.py` | ✅ Ingesté 1 518 métiers | ✅ |
| ROME 4.0 (API live) | `src/collect/rome_api.py` | ✅ Ingesté 1 584 métiers + 1 584 fiches détaillées | ✅ |
| La Bonne Alternance | `src/collect/labonnealternance.py` + `scripts/ingest_lba.py` | ✅ Ingesté 6 646 formations | ✅ |
| Céreq | `src/collect/cereq.py` | ⏳ Parser prêt, attend CSVs (§3.A) | ✅ |
| INSEE BTS | `src/collect/insee_emploi.py` | ⏳ Scaffold prêt, attend CSV (§3.B) | ✅ |
| **Marché du travail v1** | `src/collect/ft_marche_travail.py` | ⏳ Scaffold prêt, attend scope (§1) | ✅ |
| **Sortants formation v1** | `src/collect/ft_sortants_formation.py` | ⏳ Scaffold prêt, attend scope (§1) | ✅ |
| **Accès emploi demandeurs v1** | `src/collect/ft_acces_emploi.py` | ⏳ Scaffold prêt, attend scope (§1) | ✅ |
| **Offres d'emploi v2** | `src/collect/ft_offres_emploi.py` | ⏳ Scaffold prêt, attend scope (§1) | ✅ |
| **ROMEO** | `src/collect/romeo.py` | ⏳ Scaffold prêt, attend scope ou portail (§2) | ✅ |
| APEC PDFs | (à développer S+2) | 🟠 Scaffold à venir S+2 | — |
| Scraping forums | `src/collect/scrape_forums_public.py` | 🟠 Scaffold à venir S+2 | — |

---

## 🎯 Prochaine étape post-§1 + §2

Une fois les scopes cochés (§1) :
- Claudette lance **4 ingestions live en parallèle** (Marché travail + Sortants formation + Accès emploi + Offres emploi) via sub-agents
- ETA cumul avec parallélisation : **4-6 jours**
- Gain RAG OrientIA : enrichissement par fiche avec tension marché + taux retour emploi + salaires + offres live par ROME × région

Une fois Céreq/INSEE/APEC téléchargés (§3) :
- Parsing + enrichissement fiches via `attach_cereq_insertion()` (Céreq) et nouvelles fonctions (INSEE/APEC)
- Phase (c) "débouchés professionnels détaillés" (ADR-040) enfin complet.

---

*Fichier généré / mis à jour par Claudette à la demande de Matteo (ordre Jarvis 2026-04-23-1710). Review recommandé à chaque fin de session pour garder le TODO à jour.*
