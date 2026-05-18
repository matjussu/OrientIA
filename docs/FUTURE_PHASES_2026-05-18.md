# OrientIA — Phases futures à partir du 2026-05-18

Document de référence des chantiers identifiés pendant la session 2026-05-13
+ 2026-05-14, à attaquer dans les sessions suivantes. Mis à jour après le
merge des PRs #135 + #137 + #138 (3 fixes structurels).

---

## État de base au 2026-05-18

### PRs mergées dans cette série (cross-validées Claudette + ingénieur Langfuse)

| PR | Contenu | Métrique mesurée |
|---|---|---|
| #135 | E (broken link post-process) + H (regex citation multi-format) | 33/33 tests verts, 0 régression visuelle |
| #137 | C+ (`fiche_to_text` annexes) + GQ (rebuild golden_qa multi-cat) | 4/13 → 8/13 top-5 match, 60.7 % → 24.6 % bruit `(formation)` |
| #138 | Phase 1.4 (Q11 voie_pre_bac domain_hint) + script diag Q01 | 8/13 → 9/13 top-5 match |

### Diagnostic découvert (Phase 1.3, faux signal observability)

L'anomalie Q01 "40 s avec 0 small calls" (rapportée par l'ingénieur observability)
est un **cold-start warmup** générique du premier `.answer()` de la session :
~14 s d'init invisibles à Langfuse (lazy load FAISS golden_qa + connection pool
Mistral). Pas spécifique à Q01.

### Métriques agrégées avant/après cette série

| Métrique | 2026-05-11 baseline | 2026-05-18 post-merges |
|---|---:|---:|
| Top-5 domain match | 4/13 | **9/13** |
| % top-5 = `(formation)` (bruit) | 60.7 % | **~22 %** |
| Refusals "info non disponible" | 6/13 | **2/13** |
| Tests passants | 169 | 220+ (115 intent + 33 post_process + 23 embeddings) |
| Bugs visuels (broken links) | 3 | **0** |

**Mais** : faithfulness Ragas reste à **0.49 bimodale** (26 % grounded ≥ 0.7,
54 % extrapolent < 0.5). Le retrieve a été fixé, la génération reste fragile.

---

## Phase 2 — Faithfulness 0.49 → 0.65+ (LE BLOQUEUR PRODUIT N°1)

### Pourquoi c'est la priorité

Un outil d'orientation où 1 réponse sur 2 contient des claims non supportés
n'est pas déployable. C'est le bloqueur principal entre l'état actuel ("démo
qui retrouve les bonnes infos") et l'état cible ("outil utilisable par lycéens
en autonomie"). C+ a fixé la première moitié du problème (le LLM reçoit les
bonnes infos), Phase 2 fixe la seconde (le LLM utilise correctement ces infos).

### Mécanisme (3 sous-tâches)

| # | Tâche | Effort | Coût | Confiance |
|---|---|---:|---:|---:|
| 2.1 | **Re-Ragas avec context_precision + answer_relevancy** (reference-free) sur 50q équilibré par catégorie. Le `context_recall` actuel = 0.021 est un artefact protocole (golden_qa généré contre sources web, pas contre corpus FAISS). | 1 h ingé | ~$3 | 95 % calibration valide |
| 2.2 | **Audit empirique** : sur les 13 réponses post-fix, marquer chaque claim "supporté par [source SX] | non supporté". Identifier le pattern d'extrapolation (quel type de question / quel passage / quel type de claim). | 2-3 h Claudette | $0 | 100 % info utile |
| 2.3 | **Fix calibré** (2 options à choisir post-audit) : (A) règle Validator déterministe nouvelle (détecte claims non supportés → flag WARNING → retry forced grounding) ou (B) modif additive prompt `SPRINT11_P0` règle 5 "Tout chiffre/nom d'école/URL doit être suivi de [source SX]". Mesure pre/post obligatoire. | 2-3 h | $0 | 60-70 % gain |

### Métrique de succès

- Faithfulness 0.49 → **0.65+** (cible minimum)
- Sur les 13 questions du spot-check, ≤ 1 réponse contient des claims non sourcés
- Aucune régression sur les métriques existantes (9/13 top-5 match, refusals 2/13)

### Risques

- Le system prompt `SPRINT11_P0` est load-bearing — toute modif peut faire
  régresser d'autres patterns historiques (Run F). **Mitigation** : mesure
  A/B mini-bench avant push, rollback si régression nette.
- Le Validator règle nouvelle peut sur-flagger et bloquer des réponses
  correctes (faux positifs). **Mitigation** : tuning sur 5-10 questions
  adverses avant activation production.

### Total estimé

5-6 h Claudette + 1 h ingé + ~$3 budget. ~1 jour calendaire.

---

## Chantier F — Anti-hybridation prospective (mode étiqueté validé)

### Quoi

Détecter les questions prospectives (`en 2030`, `d'ici 2035`, `projections`,
`tendances futures`) dans l'intent classifier → injecter une contrainte de
prompt + nouvelle règle Validator L1 `prospective_claim_without_dares_source`
qui force le hedging si aucune source `metier_prospective` (DARES) n'est dans
le top-K.

### Pourquoi

Régression observée le 2026-05-13 sur Q1 ("métiers Occitanie 2030") : le LLM
substituait des formations actuelles à des projections métiers. Maintenant
que C+ ramène les fiches DARES correctement, le mode étiqueté est défensif
contre les futures questions sans match DARES.

### Coût

2-3 h. $0. Confiance 70 %.

### Métrique

Sur 5-10 questions prospectives sans match DARES, 100 % en mode hedging
("je n'ai pas de projections officielles pour [année]") ou refus propre,
0 substitution silencieuse formations→métiers.

---

## Chantier D — FilterCriteria niveau auto

### Quoi

Extraire le niveau de la question (`bac pro`, `BTS`, `BUT`, `licence`,
`master`, `doctorat`, `bac+N`) dans l'intent classifier → injecter dans
`FilterCriteria.niveau` du pipeline (mécanique existante avec auto-expansion
k si trop restrictif).

### Pourquoi

Q10 "Bac pro Industrie" renvoie aujourd'hui des fiches doctorat biologie
2014 du retrieve. La sémantique d'embedding ne discrimine pas correctement
les niveaux quand le sujet partage du vocabulaire (insertion / spécialité).

### Coût

3-4 h. $0. Confiance 75 %.

### Métrique

Q10 cesse de retourner des fiches doctorat. Plus largement, mesurer le
taux de contamination niveau sur 10 questions niveau-explicites
(bac pro / BTS / master / doctorat).

---

## Chantier B — Lookup déterministe par code

### Quoi

Détecteur regex dans `intent.py` : `(RNCP|ROME|FOR\.|MET\.|RNE)\s*\d+` →
si match → court-circuit FAISS → lookup direct dans dict indexé par code.
Si absent du corpus → refus propre + redirection (france-competences.fr,
onisep.fr) — pas de best-match hallucinogène.

### Pourquoi

Q3 "RNCP 38450" retourne aujourd'hui RNCP 35298/35307/etc. (voisins
sémantiques). Pattern reproductible sur tous codes structurés. Élimine
mécaniquement une catégorie de hallucinations.

### Coût

4-6 h. $0. Confiance 80 %.

### Métrique

Toutes les questions à code explicite renvoient soit la fiche exacte
(top-1 confirmed match), soit un refus propre + redirection. Zéro
best-match silencieux.

---

## Cold-start warmup pipeline

### Quoi

Méthode `pipeline.warmup()` appelée à l'instanciation, qui force le lazy
load des artefacts (FAISS golden_qa + meta, BM25 index si activé,
connection pool Mistral) + dummy retrieve. Éliminer les ~14 s du Run 1
de chaque session.

### Pourquoi

Phase 1.3 a démontré que Q01 latency 40 s n'est pas un bug spécifique
mais le cold-start du premier `.answer()`. Pas critique côté API serveur
(1 cold par instance) mais pénalise l'UX en CLI / 1 user = 1 session.

### Coût

1 h. $0. Confiance 95 %.

### Métrique

Premier `.answer()` après instanciation pipeline < 8 s (vs 26-40 s
actuellement).

---

## Couverture corpus — Q4, Q7, Q10, Q13 (chantiers data séparés)

Ces 4 questions restent à 0/5 top-5 match malgré C+. Ce sont des trous de
**couverture corpus**, pas de problèmes pipeline. Chantiers plus longs
qui nécessitent l'extension du data ingestion.

| Q | Domain visé | Trou |
|---|---|---|
| Q4 Master Droit PACA | `insertion_pro` | InserSup n'a pas de fiche spécifique discipline×région (608 fiches insertion_pro, mais pas droit×PACA) |
| Q7 Guadeloupe | `territoire_drom` | 16 fiches LADOM/mobilité ≠ "formations en Guadeloupe" (ce sont des aides, pas un catalogue territorial) |
| Q10 Bac pro Industrie | `formation_insertion` | 2693 fiches Inserjeunes mais aucune discrimine "Industrie" comme spécialité |
| Q13 doctorat chimie | `insertion_pro` | 608 fiches dominées par doctorat biologie 2014, pas doctorat chimie |

### Effort estimé

1-2 jours par sous-corpus à enrichir (download + parsing + merge + re-embed).
Cumulé : 1 semaine pour passer 9/13 → 12-13/13.

### Priorité

**Plus basse que Phase 2** parce que le bloqueur produit principal est la
qualité de réponse, pas la couverture. Un utilisateur préfère 9 réponses
fidèles + 4 refus propres à 13 réponses dont 7 contiennent des claims faux.

---

## Hiérarchisation finale (ordre recommandé)

| Ordre | Chantier | Effort | Confiance | Impact produit |
|---|---|---:|---:|---|
| **1** | **Phase 2 — Faithfulness** | 5-6 h + $3 | 60-70 % | **🔴 Bloqueur produit n°1** |
| 2 | Chantier F — Anti-hybridation prospective | 2-3 h | 70 % | Élimine 1 mode hallu critique |
| 3 | Cold-start warmup | 1 h | 95 % | UX (premier-run)
| 4 | Chantier D — FilterCriteria niveau | 3-4 h | 75 % | Précision retrieve |
| 5 | Chantier B — Lookup déterministe code | 4-6 h | 80 % | Zéro hallu sur codes |
| 6 | Couverture corpus Q4/Q7/Q10/Q13 | 1 semaine | 90 % | +3-4 questions au top-5 |

**Test utilisateur final** : après Phase 2 + Chantier F minimum, re-test sur
5 profils (Léo / Sarah / Catherine / Dominique / nouveau) pour mesurer
"voudrait l'utiliser" et "trouve la réponse fiable". Métrique de succès :
4/5 répondent oui aux 2.

---

## Notes opérationnelles

### Branches de référence à conserver (filets, post-merge)

- `feature/alpha-restricted-llm` — α prompt non mergé (filet ADR-030)

### Backups conservés localement (gitignored)

- `data/embeddings/formations_v5.index.bak-20260513-pre-chantier-c-plus` (avant C+)
- `data/embeddings/golden_qa.index.bak-20260513` (avant GQ rebuild)
- `data/processed/golden_qa_meta.json.bak-20260513` (avant GQ rebuild)

### Dette technique identifiée à suivre

1. **`docs/SPOT_CHECK_V5_2026-05-13.md`** ambigu post-merges : représente le
   pre-fix C+. À renommer en `docs/SPOT_CHECK_V5_2026-05-13-pre-chantier-c-plus.md`
   pour cohérence.
2. **`data/golden_qa_v1.jsonl` ↔ `data/embeddings/golden_qa.index` désync**
   à automatiser. Ajouter un check pre-commit ou cron qui flag si JSONL
   modifié sans rebuild.
3. **`scripts/diag_q01_latency.py`** : à factoriser dans `src/observability/`
   ou `src/diagnostics/` pour réutilisation systématique.

---

*Document rédigé le 2026-05-18 après merge des PRs #135 + #137 + #138.
Source de vérité opérationnelle pour les futures sessions. Mis à jour
par sessions selon avancement.*
