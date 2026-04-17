---
title: OrientIA — Schéma data v2 (Vague A, strategie data foundation)
date: 2026-04-17
status: LIVING — évolue au fil des vagues d'enrichissement data
audience: Claudette (implémentation), Matteo (revue), Jarvis (mémoire projet)
---

# Schéma data v2 — Référence technique

Document vivant qui fige la structure d'une fiche enrichie + les conventions
de provenance + le format de citation. À jour à chaque vague d'enrichissement
data (A → M) de la stratégie V2.

Ce document n'est PAS un ADR (pas append-only). Il est **modifiable** à
condition qu'un ADR accompagne tout changement de format qui casserait un
RAFT déjà entraîné.

## 1. Principes directeurs

1. **Séparation embedding vs generator.** L'embedding text (pour retrieval)
   contient le qualitatif discriminant. Le generator context (pour réponse)
   contient tous les chiffres structurés. Les chiffres ne polluent pas
   l'embedding, les descriptions ne noient pas le generator.

2. **Matching hiérarchisé.** Clés en ordre de confiance : RNCP > cod_aff_form
   Parcoursup > slug ONISEP > fuzzy nom+ville+établissement. Le fuzzy est
   toujours fallback, jamais primaire.

3. **Provenance par champ.** Chaque champ enrichi porte l'origine de ses
   données pour traçabilité et résolution de conflits. Exposé dans les
   citations LLM (pas masqué).

4. **Fraîcheur first-class.** Chaque source versionnée par date de collecte.
   Permet au generator d'ancrer les réponses dans le temps au lieu d'un
   "selon mes informations" flottant.

5. **Complétude visible.** Une fiche sait ce qui lui manque. Le generator
   peut dire "je n'ai pas l'info sur [X]" au lieu d'halluciner.

6. **North Star lycéen.** Les champs prioritaires sont ceux qui parlent
   concrètement à un lycéen / parent. Les champs techniques (RIASEC, blocs
   RNCP détaillés) restent en backend pour qualité retrieval, pas en sortie.

## 2. Schéma JSON d'une fiche enrichie

Après Vague A, une fiche ressemble à :

```jsonc
{
  // === IDENTITÉ ===
  "source": "parcoursup" | "onisep" | "merged",
  "nom": "Bachelor Cybersécurité des systèmes industriels et urbains",
  "detail": "...",                          // description longue, non tronquée
  "domaine": "cyber" | "data_ia" | "sante" | ...,
  "type_diplome": "formation d'école spécialisée",
  "niveau": "bac+3",
  "duree": "3 ans",

  // === CLÉS DE JONCTION ===
  "rncp": "37989",                          // prioritaire, clé France Compétences
  "cod_aff_form": "12345",                  // clé unique Parcoursup (NOUVEAU Vague A)
  "url_onisep": "https://.../FOR.9891",     // slug ONISEP (FOR.xxxxx extractible)
  "lien_form_psup": "https://...",          // URL officielle Parcoursup (NOUVEAU)

  // === ÉTABLISSEMENT ===
  "etablissement": "Lycée Emmanuel d'Alzon",
  "statut": "Public" | "Privé" | "Consulaire" | "Inconnu",
  "tutelle": "non renseigné",
  "ville": "Nîmes",
  "departement": "Gard",
  "region": "Occitanie",

  // === LABELS QUALITÉ ===
  "labels": ["SecNumEdu", "CTI", ...],

  // === ADMISSION (Parcoursup 2025) ===
  "admission": {
    "taux_acces": 52.0,                     // % global (anciennement taux_acces_parcoursup_2025)
    "places": 25,
    "volumes": {
      "voeux_totaux": 1250,                 // voe_tot (NOUVEAU)
      "voeux_phase_principale": 800,        // nb_voe_pp (NOUVEAU)
      "classes_phase_principale": 600       // nb_cla_pp (NOUVEAU)
    },
    "session": 2025,                        // année du snapshot
    "internat_disponible": false            // acc_internat > 0 (NOUVEAU)
  },

  // === PROFIL DES ADMIS ===
  "profil_admis": {
    "mentions_pct": {                       // % des admis par mention
      "tb": 15.0, "b": 35.0, "ab": 25.0, "sans": 25.0
    },
    "bac_type_pct": {                       // % des admis par type de bac
      "general": 73.0, "techno": 27.0, "pro": 0.0
    },
    "acces_pct": {                          // part d'accès par type bac (part_acces_*)
      "general": 73.0, "techno": 27.0, "pro": 0.0
    },
    "boursiers_pct": 18.0,                  // % boursiers parmi admis
    "femmes_pct": 24.0,                     // pct_f (NOUVEAU)
    "neobacheliers_pct": 85.0,              // pct_neobac (NOUVEAU)
    "origine_academique_idf_pct": 12.0      // pct_aca_orig_idf (NOUVEAU)
  },

  // === DÉBOUCHÉS MÉTIERS (ROME 4.0) ===
  "debouches": [
    {
      "code_rome": "M1812",
      "libelle": "Responsable de la Sécurité des Systèmes d'Information (RSSI)"
    }
    // ... (enrichi dans Vague D avec compétences, RIASEC, mobilités)
  ],

  // === MÉTADONNÉES MATCH + PROVENANCE ===
  "match_method": "rncp" | "fuzzy_89.7" | "parcoursup_only" | "onisep_only",
  "merge_confidence": {                     // NOUVEAU Vague A
    "parcoursup": 1.0,
    "onisep": 0.95,                         // null si non-matchée
    "labels": 1.0
  },
  "provenance": {                           // NOUVEAU Vague A
    "admission": "parcoursup_2025",
    "profil_admis": "parcoursup_2025",
    "debouches": "rome_4_0",
    "type_diplome": "onisep"
  },
  "collected_at": {                         // NOUVEAU Vague A
    "parcoursup": "2026-04-17",
    "onisep": "2026-04-10",
    "rome": "2026-04-10"
  }
}
```

## 3. Niveaux de contexte pour le generator

**Niveau 1 — Résumé (~100 tokens)** : utilisé dans le contexte initial avec
le top-K complet du retrieval.

```
FICHE i: <nom> — <etab>, <ville> (<dept>) | <niveau> | <statut>
  Labels officiels: ...
  Sélectivité Parcoursup 2025: X% (qualif) | Places: N
```

**Niveau 2 — Fiche détaillée (~400 tokens)** : utilisé pour les top-3
fiches les plus pertinentes uniquement.

```
FICHE i: <header niveau 1>
  Labels officiels: ...
  Sélectivité Parcoursup 2025: X% | Places: N | Vœux formulés: V | Internat: oui/non
  Profil admis: TB X%, B Y%, AB Z% | Bac général X%, techno Y%, pro Z% | Boursiers W% | Femmes V%
  Débouchés métiers: libelle1 (ROME1), libelle2 (ROME2), libelle3 (ROME3)
  Détail: <description non tronquée>
  Source officielle: <lien_form_psup ou url_onisep>
  Fraîcheur: Parcoursup 2025, ONISEP 2026-04
```

**Niveau 3 — Détails externes** : compétences RNCP, RIASEC, passerelles —
appelés par tools dans Axe 2 (pas dans Vague A).

## 4. Format de citation pour le LLM (figé pour RAFT)

Le generator est instruit à citer toute donnée chiffrée avec ce format
stable. Sera réutilisé tel quel dans les exemples RAFT (Axe 3).

**Citation de fait sourcé :**

```
##begin_quote##
<claim factuel en français>
(Source: <nom_source> <date/année>, <id_type>: <id_valeur>)
##end_quote##
```

Exemples :

```
##begin_quote##
Le Bachelor Cybersécurité d'ESEA Pau admet 35% de candidats avec mention Bien.
(Source: Parcoursup 2025, cod_aff_form: 42156)
##end_quote##
```

```
##begin_quote##
Le Master MIAGE Tours affiche un taux d'insertion à 6 mois de 89%.
(Source: InserSup DEPP 2024, RNCP: 35909)
##end_quote##
```

**Refus (info absente) :**

```
##no_oracle##
Je n'ai pas de donnée source fiable pour répondre à <aspect spécifique>.
##end_no_oracle##
```

Exemples :

```
##no_oracle##
Je n'ai pas de donnée source fiable pour le salaire médian post-diplôme
de cette formation spécifique.
##end_no_oracle##
```

**Règles d'usage** :

- Le LLM cite avec ce format **pour tout chiffre** (%, taux, montants).
- Pour les descriptions qualitatives (contenu pédagogique, atmosphère), pas
  de citation obligatoire — c'est le contexte entier qui fait foi.
- Refus à invoquer quand le contexte ne contient pas la donnée, **pas** quand
  le LLM n'est pas sûr à 100%. L'hésitation se joue dans le ton, pas dans
  un refus.

## 5. Colonnes Parcoursup — étendues en Vague A

Cols déjà parsées (base actuelle) :
- `lib_for_voe_ins` → nom
- `g_ea_lib_vx` → etablissement
- `ville_etab` → ville
- `region_etab_aff`, `dep_lib` → region, departement
- `taux_acces_ens` → admission.taux_acces
- `capa_fin` → admission.places
- `contrat_etab` → statut
- `detail_forma` → detail
- `pct_tb/b/ab/sansmention` → profil_admis.mentions_pct
- `pct_bg/bt/bp` → profil_admis.bac_type_pct
- `part_acces_gen/tec/pro` → profil_admis.acces_pct
- `pct_bours` → profil_admis.boursiers_pct

Cols **AJOUTÉES en Vague A** :
- `cod_aff_form` → id Parcoursup unique
- `lien_form_psup` → URL officielle fiche
- `voe_tot` → admission.volumes.voeux_totaux
- `nb_voe_pp` → admission.volumes.voeux_phase_principale
- `nb_cla_pp` → admission.volumes.classes_phase_principale
- `acc_internat` → admission.internat_disponible (bool : > 0)
- `pct_f` → profil_admis.femmes_pct
- `pct_neobac` → profil_admis.neobacheliers_pct
- `pct_aca_orig_idf` → profil_admis.origine_academique_idf_pct

Cols à ajouter en **Vague B** (ROME profond + matching RNCP) :
- Historique Parcoursup 2023/2024 (trend)
- Extraction RNCP du texte `detail` via regex

## 6. Backward compatibility

La fiche enrichie garde les champs legacy à leur emplacement original :
`taux_acces_parcoursup_2025`, `nombre_places`, etc. Les nouveaux champs
structurés (`admission.*`) sont **ajoutés à côté**. Le generator lit en
priorité les champs structurés et fallback sur les legacy. Ça permet de :

- Ne pas casser les 231 tests pytest existants.
- Garder la cohérence avec l'index FAISS courant (pas de re-embed Vague A).
- Permettre un re-refactor propre en Vague B quand on pourra re-embed.

## 7. Hors scope Vague A

Explicitement pour plus tard :
- Re-embed FAISS avec nouveau `fiche_to_text` → Vague B
- Matching RNCP-first (couches 1-5) → Vague B
- Historique Parcoursup 2023/2024 → Vague C
- ROME profond (compétences, savoirs, RIASEC, mobilités) → Vague D
- APIs externes (ONISEP live, France Compétences, InserSup, France Travail) → Vagues E-H
- Extension domaine santé → après Vague B (pipeline stable)
- Classements externes + anti-biais → Vague K
