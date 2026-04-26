# OrientIA — Inventaire Data complet (2026-04-26, post-merges PR #70-#73)

> Snapshot data state à 12h CEST le dimanche 26/04/2026, après livraison
> nuit + matin (PR #70 DARES, PR #71 France Comp blocs, PR #72 docs
> verdicts honnêtes, PR #73 fix DARES boost ×1.0). Successor de
> `DATA_INVENTORY_2026-04-25.md` (pré-DARES, pré-blocs RNCP). Doc socle
> du dossier livrable INRIA AI Grand Challenge **2026-05-25** (J-29).

---

## Executive summary (1 page)

OrientIA exploite actuellement **9 corpus retrievables** indexés FAISS
(Phase C blocs = 54 186 vecteurs avec blocs RNCP, Phase C DARES = 49 406
vecteurs avec DARES Métiers 2030). Couverture data 100% sources État
publiques (Etalab 2.0) — souveraineté française intégrale,
reproductibilité des pipelines.

**Découverte méthodologique majeure ce matin** : le bench dédié DARES
(ordre 1100) a révélé une régression structurelle du boost reranker
×1.5 — atténuée à ×1.0 (ordre 1122) avec 49 % de la régression résolue.
Floor architectural L2-only-DARES identifié sur 4/10 queries activantes :
limite du reranker rule-based, motivation pour le pivot agentique J-23
(focal samedi 02/05). Cf `docs/VERDICT_BENCH_DARES_DEDIE.md`.

**État retrievable courant (cells indexées) :**

| # | Corpus | Domain | Cells | Dimension unique apportée |
|---|---|---|---:|---|
| 1 | formations (base) | `formation` | 47 590 | catalogue formations Parcoursup + ONISEP fusionnés |
| 2 | metiers | `metier` | 1 075 | fiches métiers ONISEP éditorialisées |
| 3 | parcours_bacheliers | `parcours_bacheliers` | 151 | taux de réussite licence × bac × mention |
| 4 | apec_regions | `apec_region` | 13 | marché travail cadres × région |
| 5 | crous | `crous` | 39 | logements + restos universitaires |
| 6 | insee_salaan | `insee_salaire` | 59 | salaires nets PCS × région INSEE 2023 |
| 7 | insersup | `insertion_pro` | 368 | insertion master × discipline × région |
| 8 | dares | `metier_prospective` | 111 | projections recrutement 2030 par FAP |
| 9 | france_comp_blocs | `competences_certif` | 4 891 | compétences certifiées RNCP par bloc |
| **TOTAL** | — | 9 domains | **54 297** | — |

**Backlog data non-retrievable (gisement ~218k records bruts)** :
inserjeunes_lycee_pro 132k, insersup_insertion 48k brut, INSEE 10k brut,
inserjeunes_cfa 11k, etc. — sources processed mais non agrégées en
corpus retrievable. Voir §3.

**Tests** : 1 164 verts post-merge PR #73 (1 125 baseline + 39 nouveaux
DARES + blocs).

**Gap analysis (§4)** identifie 4 zones critiques sous-représentées :
DROM-COM, financement études (bourses, prêts), reconversion
adulte > 25 ans, données qualitatives (témoignages, cas concrets).

---

## 1. Inventaire 9 corpus retrievables

### 1.1 `formations` (base catalogue)

- **Source** : Parcoursup 2023-2025 + ONISEP API + RNCP CSV France Compétences + InserJeunes CFA + LBA + MonMaster (multi-sources fusionnées)
- **Records bruts** : 48 914 fiches multi-sources (avant dedupe)
- **Cells aggregées** : **47 590** post-dedupe (1 cell par fiche-formation, base catalogue)
- **Format aggregation** : 1 cell par formation, texte construit dynamiquement par `fiche_to_text(fiche)` v3 (cf `src/rag/embeddings.py`)
- **Dimension unique apportée** : seul corpus qui couvre l'**offre de formation française** au niveau granulaire (par établissement × diplôme × ville × niveau). Tous les autres corpus se réfèrent à des entités tierces (métiers, régions, etc.) sans le niveau de granularité formation.
- **Verdict bench latest** : v5++ shipping (PR #67) — 39.5 % verified / 18.0 % halluc baseline sur 18 queries personas v4
- **Caveats** :
  - Dédoublonnage Parcoursup × ONISEP via `cod_aff_form` puis fusion soft (ADR-046) — 1 324 doublons éliminés mais sub-1 % d'edge case avec text différent post-merge
  - ROME exclu de `fiche_to_text` v3 (régression Run 5 ablation, à refondre proprement Axe 1 V2)
  - Statut Public/Privé pas toujours renseigné — affecte le boost reranker `public_boost`

### 1.2 `metiers` (ONISEP Idéo-Fiches)

- **Source** : ONISEP Idéo-Fiches métiers (XML 13 MB → JSON 9.1 MB en intermédiaire)
- **Records bruts** : 1 075 fiches métiers éditorialisées
- **Cells aggregées** : **1 075** (1 cell par fiche métier, no aggregation supplémentaire)
- **Dimension unique** : seul corpus qui apporte la dimension **métier humain** (synonymes, accroche, conditions de travail, qualités, profils d'évolution). Complète l'offre formation par "qu'est-ce qu'on fait dans la vie après ?".
- **Couverture** : 100 % nom/identifiant/accroche, 924/1 075 codes ROME (85.9 %), 968 formations minimales liées
- **Source intégration** : PR #56 `feat/multi-corpus-metiers` (mergée 25/04)
- **Verdict bench** : pas de bench dédié, observé en domain top-K via classification regex `metier`
- **Caveats** :
  - Format éditorialisé ONISEP — qualité narrative haute mais peu de chiffres exploitables par fact-checker
  - 15 % des fiches sans code ROME (lien plus difficile vers offres emploi France Travail post-V2)

### 1.3 `parcours_bacheliers` (MESRI cohortes licence)

- **Source** : MESRI ESRI - Parcours et réussite des bacheliers en licence (cohortes 2012/2014)
- **Records bruts** : 5 508 records granulaires (Discipline × Bac × Mention × Âge × Sexe)
- **Cells aggregées** : **151** (1 cell par Discipline × Bac × Mention)
- **Format aggregation** : 36× réduction (5 508 → 151) — pivot lisible pour LLM
- **Dimension unique** : seul corpus qui apporte les **statistiques de réussite L1→L2 et licence en 3/4 ans** segmentées par profil bachelier (BAC L/S/ES/STMG/Pro × mention). Données critiques pour la question "ai-je une chance ?" (intent realisme).
- **Source intégration** : PR #57 `feat/parcours-bacheliers` (mergée 25/04)
- **Verdict bench** : domain hint `parcours_bacheliers` activé sur queries type "taux de réussite L1 droit BAC L mention" — confirmé top-K sur 1/18 queries personas v5++
- **Caveats** :
  - Cohortes 2012/2014 = données un peu datées (10-12 ans). Mise à jour MESRI parue 2024 (cohorte 2017) à intégrer en V2
  - Peu de granularité géographique (pas de découpage régional)

### 1.4 `apec_regions` (APEC observatoire cadres)

- **Source** : APEC Observatoire de l'emploi des cadres 2026 (PDF + chantier Jarvis 2026-04-24)
- **Records bruts** : 12 régions hors IDF + 1 national + observations cross-régions
- **Cells aggregées** : **13** (1 cell par région)
- **Dimension unique** : seul corpus qui apporte la **dynamique régionale du marché cadres** (volume recrutements, prévisions, secteurs porteurs). Critique pour "où chercher un emploi cadre" (intent geographic).
- **Source intégration** : PR #59 `feat/apec-regions-corpus` (mergée 25/04)
- **Verdict bench** : domain hint `apec_region` activé sur queries "marché du travail cadres en X" / "salaire médian cadre" — top-K confirmé 2/18 queries personas v5++
- **Caveats** :
  - Données 2026 publiées par APEC, pas de bench longitudinal historique
  - Couverture restreinte aux **cadres** (~16% pop active) — pas valable pour techniciens / employés

### 1.5 `crous` (logements + restos universitaires)

- **Source** : data.gouv.fr CROUS (XML public Etalab 2.0)
- **Records bruts** : 820 résidences universitaires + 999 restaurants/cafétérias = 1 819 entités
- **Cells aggregées** : **39** (1 cell par région ou type d'agrégation, ex "France entière", "Île-de-France logements", "Sud-Est restos")
- **Format aggregation** : 47× réduction (1 819 → 39)
- **Dimension unique** : seul corpus qui apporte la **vie étudiante quotidienne** (où loger, où manger, quoi attendre). Complète l'orientation académique avec la dimension pragmatique.
- **Source intégration** : PR #67 Phase B `feat/3-corpora-aggreges-rebase` (mergée 25/04 soir)
- **Verdict bench** : domain hint `crous` activé sur queries "logement étudiant", "vie étudiante" — pas de bench dédié pour l'instant
- **Caveats** :
  - Couverture France métropolitaine majoritaire, DROM-COM partiel
  - Données relativement statiques (mises à jour annuelles), pas de prix temps-réel

### 1.6 `insee_salaan` (salaires nets INSEE 2023)

- **Source** : INSEE Base SALAAN 2023 (Salaires Annuels)
- **Records bruts** : ~10 050 entrées (PCS × Région × Genre × Tranche d'âge)
- **Cells aggregées** : **59** (1 cell par PCS × Région ou aggregation)
- **Format aggregation** : 170× réduction (10 050 → 59)
- **Dimension unique** : seul corpus qui apporte les **salaires médians officiels par catégorie socio-professionnelle et région**. Données INSEE = autorité maximale pour citation académique INRIA.
- **Source intégration** : PR #67 Phase B (mergée 25/04 soir)
- **Verdict bench** : domain hint `insee_salaire` activé sur queries "salaire médian PCS X" — top-K confirmé 1/18 queries
- **Caveats** :
  - Données 2023 publiées 2026 (cycle INSEE = J+3 ans)
  - PCS21/22/23 = cadres, codes plus fins demandent la base SALAAN détaillée

### 1.7 `insersup` (insertion master MESR)

- **Source** : MESR base InserSup (sortants master, cohorte 2024 mesurée 2026)
- **Records bruts** : 48 230 enregistrements granulaires (Diplôme × Discipline × Région × Cohorte)
- **Cells aggregées** : **368** (1 cell par Discipline × Région pour Master + BUT)
- **Format aggregation** : 131× réduction (48 230 → 368)
- **Dimension unique** : seul corpus qui apporte le **taux d'insertion à 6/12/18/30 mois post-master** segmenté par discipline et région. Critique pour réorientation Phase (b) et Master Phase (c).
- **Source intégration** : PR #67 Phase B (mergée 25/04 soir)
- **Verdict bench** : domain hint `insertion_pro` activé sur queries "taux insertion à 18 mois après master" — top-K confirmé sur 1/18 queries
- **Caveats** :
  - **Sous-exploité** : 48 230 records bruts → seulement 368 cells (0.76 % granularité). Re-aggregation per-(diplôme × discipline × région × tranche-effectif) à investiguer en V2.
  - Couverture master/post-bac uniquement, pas Bac pro (cf inserjeunes_lycee_pro non encore retrievable)

### 1.8 `dares` (Métiers 2030 — projections recrutement)

- **Source** : DARES "Les métiers en 2030 quelles perspectives de recrutement en région" (XLSX 2 sheets, sheet "données")
- **Records bruts** : 1 049 records (FAP × Région × indicateurs)
- **Cells aggregées** : **111** (98 cells FAP × France + 13 cells Région × top FAP)
- **Format aggregation** : 9× réduction (1 049 → 111)
- **Dimension unique** : seul corpus **prospectif** d'OrientIA — projections 2019-2030 par famille professionnelle (FAP 98 codes) × région. Critique pour "quels métiers vont recruter quand je sortirai en 2028-2030".
- **Source intégration** : PR #70 `feat/dares-metiers-2030` (mergée 26/04 matin)
- **Verdict bench latest** :
  - Triple-run nuit (18 queries formation-centric) : v5+++ ≡ v5++ within IC95 — boost dormant (0/18 activations)
  - Bench dédié matin (10 queries prospectives activantes) avec ×1.5 : **régression -30.5 pp verified, +24.2 pp halluc** vs phaseB
  - Tune corrigé ×1.5 → ×1.0 (PR #73, mergé 26/04 matin) : 49 % régression résolue (delta verified -15.4 pp), halluc quasi-stable (+1.9 pp)
- **Caveats critiques** :
  - **Floor architectural L2-only-DARES** : 4/10 queries activantes voient top-K = 100 % cells DARES même sans boost (pure L2 distance). Limite du reranker rule-based.
  - **Fact-checker StatFactChecker hallucinable** : cells DARES denses en chiffres ("488 700 postes pourvus 2019-2030") incitent le LLM à recombiner créativement → halluc q01 q05 q10
  - Aggregation FAP × France perd la granularité par région — 98 cells nationales au lieu de 1 274 cells (98 FAP × 13 régions). Re-aggregation V2 listée roadmap (cf `docs/VERDICT_BENCH_DARES_DEDIE.md`).
  - XLSX 1 (43 sheets, 2 608 rows) **non exploité** — graphique support tables redondantes avec XLSX 2 ; valeur marginale.

### 1.9 `france_comp_blocs` (RNCP blocs de compétences)

- **Source** : France Compétences ZIP CSV `Blocs_De_Compétences` (déjà téléchargé pour rncp.py, inutilisé jusqu'au 26/04 matin)
- **Records bruts** : 52 592 rows blocs × 10 181 fiches RNCP avec blocs
- **Cells aggregées** : **4 891** (1 cell par fiche RNCP active ayant ≥1 bloc, intersection 6 590 active × 10 181 avec blocs)
- **Format aggregation** : 10.7× réduction (52 592 → 4 891)
- **Dimension unique** : seul corpus qui apporte le **contenu pédagogique** des certifications — ce qu'on apprend concrètement avec un BTS X, un BUT Y, un master Z. Complète le catalogue formation par "qu'est-ce que je vais valider en sortant ?".
- **Source intégration** : PR #71 `feat/france-comp-blocs-rncp` (mergée 26/04 matin)
- **Verdict bench latest** :
  - Single-run shipping nuit (18 queries formation-centric) : -6.8 pp halluc, +1.1 pp verified vs v5++ baseline
  - Triple-run IC95 matin : mean -5.4 pp halluc / +4.2 pp verified, IC95 ±9 pp (englobe zéro mais 3/3 runs cohérents directionnellement)
  - Effet émergent : 2/18 queries surfacent les blocs en top-K via L2 brute sans pattern regex matching (q3_lila projet ENS, q1_theo passerelles droit)
- **Caveats** :
  - Single-run -6.8 pp halluc lu comme **borne haute** vs triple-run -5.4 pp plus prudent
  - Bench blocs **dédié** maintenant prioritaire (suivi roadmap) — pattern ×1.5 boost transposable depuis DARES
  - Active fiches uniquement (6 590 sur 10 181 totales) — fiches inactives non retrievable, par choix protocolaire

---

## 2. Architecture FAISS multi-index

| Index | Vecteurs | Composition |
|---|---:|---|
| `formations.index` | 47 590 | base formations dedupe (legacy) |
| `formations_multi_corpus_phaseB.index` | 49 295 | base + 1 705 multi-corpus (PR #67 Phase B) |
| `formations_multi_corpus_phaseC_dares.index` | 49 406 | phaseB + 111 DARES (PR #70) |
| `formations_multi_corpus_phaseC_blocs.index` | 54 186 | phaseB + 4 891 blocs RNCP (PR #71) |

**Limitation actuelle** : pas d'index Phase D combiné (DARES + blocs en même temps). Roadmap §5.

---

## 3. Inventaire sources non-retrievables (gisement ~218k records bruts)

Sources processed sur disque, **non agrégées en corpus retrievable**.
Total identifié : **218 587 records bruts**.

| Source | Records | Status | Raison non-exploitation |
|---|---:|---|---|
| `inserjeunes_lycee_pro.json` | 132 124 | **Backlog actif** | Population Bac pro lycée — différent de l'audience InserSup (master). Aggregation per-(filière × région × tranche-effectif) à designer. ~30 % du gisement total. |
| `insersup_insertion.json` | 48 230 | Sous-exploité | 0.76 % granularité dans `insersup_corpus` (368 cells). Re-aggregation per-effectif en V2 envisagée. |
| `inserjeunes_cfa.json` | 11 314 | Indirect | Utilisé comme source `formations.json` (1 fiche par formation), mais données insertion CFA elles-mêmes pas aggregées séparément. |
| `insee_salaires_2023.json` | 10 050 | Sous-exploité | 0.59 % granularité dans `insee_salaan_corpus` (59 cells). Aggregation finer-grained PCS × tranche-âge × région envisageable. |
| `rncp_certifications.json` | 6 590 | Indirect | Source `france_comp_blocs_corpus`. Catalogue brut RNCP non retrievable directement (intentional — l'utilisateur cherche compétences, pas catalogue de codes). |
| `onisep_formations_extended.json` | 4 775 | Indirect | Source `formations.json`. |
| `onisep_metiers.json` | 1 518 | Indirect | Source `metiers_corpus.json` (1 075 actives). 443 fiches archivées non retrievable. |
| `ideo_fiches_metiers.json` | 1 075 | Indirect | Source `metiers_corpus.json`. Same. |
| `dares_metiers_2030.json` | 1 049 | Indirect | Source `dares_corpus.json`. Granularité (FAP × région) perdue dans aggregation 111 cells (cf §1.8 caveat). |
| `crous_logements + restos` | 1 819 | Indirect | Source `crous_corpus.json`. Granularité par établissement perdue. |
| **DARES XLSX 1** (43 sheets) | ~2 608 | Écarté | Tables support graphiques redondantes avec XLSX 2 exploitée. Valeur marginale, abandonné PR #70. |
| `cereq_insertion_stats.json` | 43 | Backlog | 43 entrées seulement, pas critique. À aggréger en V2 si pertinent. |

**Backlog identifié** :
- **inserjeunes_lycee_pro** (132k) — vrai gisement à exploiter pour audience Bac pro / CAP, complète InserSup côté niveau infra-bac
- **France Travail offres + ROMEO + LBA** — bloqué Matteo (habilitation 3 APIs en cours, état à reconfirmer)
- **MonMaster + LBA processed** — utilisés dans formations.json mais pas aggregés en corpus dédié (pertinent pour M2 alternance Phase c)
- **France Compétences API live** — RNCP blocs déjà exploité, mais pas l'API d'apprentissage (`api.apprentissage.beta.gouv.fr`) qui nécessite token (scope V2 noté `docs/TODO_MATTEO_APIS.md`)

**Sources écartées définitivement** :
- DARES XLSX 1 (43 sheets) — redondance
- Enquête Génération 2021 Céreq — embargo jusqu'à déc. 2027
- OCDE Education at a Glance — narrative INRIA seulement, pas data exploitable

---

## 4. Gap analysis structurée (5 axes)

### 4.1 Domaines

| Domaine | Couverture | Gap |
|---|---|---|
| Formations (offre académique) | ✅ 47 590 fiches Parcoursup + ONISEP | OK |
| Métiers (descriptions) | ✅ 1 075 fiches ONISEP | OK |
| Marché travail cadres | ✅ 13 régions APEC | OK pour cadres, gap technicien/employé |
| Insertion professionnelle | ✅ 368 cells master/BUT | **GAP Bac pro / CAP** (inserjeunes_lycee_pro 132k non retrievable) |
| Salaires | ✅ 59 cells PCS × région INSEE | OK |
| Compétences certifiées | ✅ 4 891 blocs RNCP | OK (post PR #71) |
| Prospective recrutement | ✅ 111 cells DARES | OK mais boost désactivé (cf VERDICT_BENCH_DARES_DEDIE.md) |
| Vie étudiante (CROUS) | ✅ 39 cells | OK |
| **Financement études** | ❌ | **GAP CRITIQUE** — pas de corpus bourses CROUS, prêts garantis État, frais de scolarité par établissement |
| **Orientation Phase (b) reconversion** | ⚠️ Partiel | inserjeunes pour bac+0-2, gap pour 25+ ans reconversion (CPF, VAE adulte) |
| **Bac pro / Apprentissage** | ⚠️ Partiel | inserjeunes_cfa indirect via formations.json, pas de corpus dédié. inserjeunes_lycee_pro 132k non retrievable. |

### 4.2 Régions

| Zone | Couverture | Gap |
|---|---|---|
| France métropolitaine 13 régions | ✅ Toutes | OK |
| Auvergne-Rhône-Alpes / Île-de-France / NAQ | ✅ Sur-représentées | OK |
| Bretagne / Pays de la Loire / Hauts-de-France | ✅ | OK |
| Corse | ⚠️ Partiel | Présente APEC + DARES, faible représentation crous + insersup |
| **DROM-COM** (Guadeloupe, Martinique, Guyane, Réunion, Mayotte) | ❌ | **GAP CRITIQUE** — quasi-absentes de tous les corpus, alors que population étudiante DROM significative |

### 4.3 Populations

| Population | Couverture | Gap |
|---|---|---|
| Lycéens Terminale (orientation initiale) | ✅ Parcoursup + Parcours bacheliers | OK |
| Bacheliers générale L/S/ES | ✅ Parcours bacheliers MESRI | OK |
| **Bacheliers technologiques (STMG, ST2S, etc.)** | ⚠️ | Présents dans MESRI mais sous-représentés dans bench |
| **Bacheliers professionnels** | ⚠️ | Inserjeunes lycée pro non retrievable |
| Étudiants L1-L3 réorientation | ✅ Parcours bacheliers + InserSup BUT | OK pour licence |
| Étudiants M1-M2 | ✅ InserSup master | OK |
| Cadres déjà en poste | ✅ APEC | OK |
| **Reconversion adulte 25-45** | ⚠️ | RNCP blocs partiel (VAE par bloc), pas de corpus CPF / formation continue |
| **NEET** (Not in Education, Employment, Training) | ❌ | **GAP** — pas de corpus dédié à cette audience pourtant ciblée par Mission Locale |

### 4.4 Périodes

| Période | Couverture | Gap |
|---|---|---|
| **Rétrospectif** (insertion passée) | ✅ Solide | InserSup, Cereq, INSEE 2023, MESRI cohorte 2014 — 5 corpora |
| **Courant** (état marché 2026) | ✅ APEC 2026, INSEE 2023 | OK |
| **Prospectif** (projections 2030+) | ✅ DARES uniquement | **Faible diversité** — 1 seul corpus prospectif (DARES). Pas de projections OECD ni France Stratégie ni autres. |

### 4.5 Types données

| Type | Couverture | Gap |
|---|---|---|
| Données chiffrées (stats officielles) | ✅ Solide | INSEE, MESRI, DARES, APEC |
| Données qualitatives (fiches descriptives) | ✅ ONISEP | OK |
| **Témoignages utilisateurs / cas concrets** | ❌ | **GAP** — pas de corpus témoignages réels d'étudiants. Pourrait améliorer la dimension empathique des réponses. |
| Réglementaires (statuts, décrets) | ⚠️ Indirect | RNCP via fiches France Comp, pas de corpus dédié décret/statut |
| Géolocalisé granulaire | ✅ Partiel | Régional OK, infra-régional limité (sauf formations.json par ville) |

---

## 5. Recommandations priorisées

Listée par ROI (impact / effort), Q = Quick Win, S = Structurelle moyen terme, L = Long terme.

### Priorité 1 — Q (J+1 → J+7)

**(a) Bench dédié `competences_certif`** — 6-12 queries calibrées blocs RNCP pour vérifier le pattern boost ×1.5 (transposable depuis DARES) ne reproduit pas régression similaire. Cf `docs/VERDICT_V5PLUSPLUSPLUS_BLOCS.md` suivi #1.

**(b) Fix sous-exploitation `insersup`** — re-aggregation per-(diplôme × discipline × région × effectif) pour passer de 368 cells (0.76 % granularité) à ~1 500-2 000 cells. Coût embed ~$0.10. Améliore retrieval insertion granulaire.

**(c) Hybrid retrieval forçant min N=3 formations top-K** — fix prioritaire DARES floor L2-only (cf VERDICT_BENCH_DARES_DEDIE.md roadmap (a)). Implementation simple post-rerank reservation.

### Priorité 2 — S (J+7 → J+21)

**(d) Corpus `inserjeunes_lycee_pro`** — 132k records → ~1 500 cells aggregées (per filière × région × niveau effectif). Comble le **GAP CRITIQUE Bac pro / CAP**. Coût embed ~$0.30, ETA ~3-5h dev (cohérent pattern existant DARES/blocs).

**(e) Corpus `financement_etudes`** — agrégation bourses CROUS (montants par échelon × académie) + prêts étudiants + frais scolarité moyens par type établissement. Comble **GAP CRITIQUE financement**. ETA ~5h, source data.gouv + CROUS API.

**(f) Re-aggregation DARES per-(FAP × région)** — passage 111 cells → ~1 080 cells (98 FAP × 13 régions). Réduit la "concentration sémantique" qui crée le floor L2-only-DARES sur 4/10 queries. Cf VERDICT_BENCH_DARES_DEDIE.md roadmap (b). Coût embed ~$0.10.

### Priorité 3 — S (J+21 → J+30 deadline INRIA)

**(g) Triple-run dédié `competences_certif`** — confirmer ou réviser la borne -6.8 pp halluc (single-run) en triple-run IC95. ~$0.10, 30 min.

**(h) Pivot DARES conditionnel** — activation du domain hint via score combiné (pattern + entités temporelles + scope prospectif explicite) plutôt que pattern regex seul. Désactive DARES sur queries où il bruite. ETA ~3h dev.

### Priorité 4 — L (post-INRIA / agentique J-23)

**(i) Multi-query expansion** — query rewriting LLM pour éclater queries multi-domain en sous-queries spécialisées. Améliore cohabitation par construction. Coût LLM par query +$0.001-0.005.

**(j) Pivot agentique** (focal samedi 02/05) — retrieval pipeline agentique adaptatif. Solution architecturale au floor L2-only-DARES et limites du reranker rule-based. Cf ADR-052 questioning anticipé par tune ×1.0.

**(k) Corpus DROM-COM dédié** — combler le gap géographique. Sources : observatoires DROM, INSEE Outre-Mer. ETA important.

**(l) Corpus témoignages / cas concrets** — populiation manuelle ou crawling forums étudiants modérés. Risk RGPD à valider Matteo.

---

## 6. Roadmap data avant deadline INRIA 2026-05-25 (J-29)

| Sprint | Items | ETA | Coût |
|---|---|---|---|
| S1 (27/04 → 03/05) | Priorité 1 (a)(b)(c) | 1-2 jours | ~$0.20 |
| S2 (04/05 → 10/05) | Priorité 2 (d)(e)(f) — corpus inserjeunes_lycee_pro + financement + re-agg DARES | 4-5 jours | ~$0.50 |
| S3 (11/05 → 17/05) | Priorité 3 (g)(h) — triple-run blocs + pivot DARES conditionnel | 2-3 jours | ~$0.20 |
| S4 (18/05 → 24/05) | Bench full + dossier livrable INRIA + corrections finales | 5 jours | ~$0.50 |

**Cumul budget data avant INRIA** : ~$1.40 sur $4 cible (35 % consommé après livraison).

---

## 7. Garde-fous épistémiques

Capitalisation des leçons méthodo des 24-25-26 avril :

- **Bench shipping doit inclure des queries activantes pour chaque pivot ajouté** (leçon DARES nuit aveugle sur formation-centric)
- **Single-run claim doit être confirmé en triple-run IC95** avant communication externe (leçon ADR -6.8 pp blocs nuit corrigé borne haute matin)
- **Caveat upper-bound sur queries calibrées sur patterns regex** (leçon bench dédié DARES — design A/B atténue le biais)
- **Floor architectural identifié = limite reconnue ≠ défaut produit** (leçon DARES L2-only-DARES, motivation pivot agentique)
- **Settings `git push origin main` deny prime sur instruction verbale** (leçon ordre 1100 → bascule pattern PR standard)

---

## 8. Annexes

### 8.1 Liens verdicts récents

- `docs/VERDICT_V5PLUSPLUSPLUS_DARES.md` — verdict triple-run DARES nuit + caveat 0/18 queries activantes
- `docs/VERDICT_V5PLUSPLUSPLUS_BLOCS.md` — verdict single-run + triple-run blocs RNCP
- `docs/VERDICT_BENCH_DARES_DEDIE.md` — verdict bench dédié DARES + analyse trio ×1.5/×1.1/×1.0 + roadmap

### 8.2 Scripts data

- `src/collect/build_dares_corpus.py` — DARES Métiers 2030 → corpus aggregé 111 cells
- `src/collect/build_france_comp_blocs_corpus.py` — RNCP blocs → corpus aggregé 4 891 cells
- `src/collect/build_phaseB_corpus.py` (à créer pour cohérence pattern) — actuellement build inline dans `scripts/build_index_phaseB.py`
- `scripts/build_index_phaseC_dares.py` / `phaseC_blocs.py` — append-rebuild FAISS reuse $0+$embed neuf
- `scripts/run_bench_dares_dedie.py` — bench A/B 10 queries dédiées prospective DARES

### 8.3 PRs livrées récentes

| PR | Date merge | Scope | SHA |
|---|---|---|---|
| #67 | 25/04 soir | Phase B 3 corpora aggrégés | e00f3b8 |
| #69 | 25/04 soir | Doc R3 revert triple-run | 5ef842e |
| #70 | 26/04 matin | DARES Phase C corpus | abb656a |
| #71 | 26/04 matin | France Comp blocs RNCP | 54bddd7 |
| #72 | 26/04 matin | Docs verdicts + triple-run | e39b2cb |
| #73 | 26/04 matin | Fix DARES boost ×1.0 | 28fd17d |

---

## 9. Headline chiffré (snapshot 26/04 12h)

- **9 corpus retrievables** indexés FAISS (54 297 cells totales)
- **218 587 records bruts** sur disque (gisement Phase D / V2)
- **1 164 tests pytest verts**, 0 régression
- **6 PRs mergées en 36h** (PR #67 → PR #73)
- **Coût Mistral cumul (24h dernières heures)** : ~$0.60 sur $4 budget (~15 %) — détail § ci-dessus
- **Verdicts honnêtes** : 3 documents (DARES nuit, blocs single+triple, DARES dédié) — pattern R3 revert reproduit
- **Deadline INRIA** : 2026-05-25 → **J-29**
- **Bascule axe B agentique J-23** : focal samedi 2026-05-02

---

*Doc rédigée par Claudette dimanche 2026-04-26 12h CEST sur ordre Jarvis 2026-04-26-1156. Successor de `DATA_INVENTORY_2026-04-25.md`. Refactor majeur post-DARES (PR #70) + post-blocs RNCP (PR #71) + post-tune ×1.0 (PR #73). Doc socle dossier livrable INRIA J-29.*
