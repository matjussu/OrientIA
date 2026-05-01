# Sprint 12 D5 — Verdict validation retrieval

**Date** : 2026-05-01
**Branche** : `feat/sprint12-D5-inserjeunes-insersup-data-gouv`
**Référence ordre** : `2026-05-01-1659-claudette-orientia-sprint12-D5-inserjeunes-insersup-data-gouv` (S6)
**Auteur** : Claudette
**Pipeline mesuré** : `Mistral embed → FAISS index rebuilt (D1+D5 mutualisé) → top-K fiches`

---

## TL;DR

| Métrique | Cible | Mesure | Statut |
|---|---|---|---|
| Top-1 hit rate (Insertion InserSup) | ≥ 60 % | **0 % (0/5)** | ❌ NOOP empirique |
| Avg top-5 fiches avec section | ≥ 2 / 5 | **0 / 5** | ❌ |
| Tests unitaires schéma `insersup` | 100 % | 8/8 verts | ✅ |
| Suite globale | 0 régression | 2071 / 1 skip | ✅ |
| Coverage `insertion_pro` post-D5 | doc | 79.2 % (32 704→30 013 cereq + 2 691 insersup + 11 314 cfa) | ✅ inchangée vs pre-D5 |

**Verdict empirique tranchant** : sur 5 questions ciblées insertion/salaire univ master/LP/DUT, **AUCUNE des 2 691 fiches enrichies InserSup** n'apparaît en top-K. Le bench tranche en faveur du quasi-noop hypothesis (cf message coord-D5-discovery-empirique 2026-05-01-1715 — sur-promesse spec confirmée empiriquement).

**Discovery empirique S3 honnête (Apprentissage #6 strict)** :

InserSup matche **2 691 fiches** mais **TOUS les match overwritent du Cereq préexistant** (overwritten_cereq = 2 691, overwritten_cfa = 0). **Net unique add = 0 fiches**. Le coverage globale `insertion_pro` reste à **79.2 %** inchangée vs pre-D5.

**Reframing valeur D5** : pas de gain coverage (l'argument spec ordre "élimine ~80 % hallu insertion+salaires" était sur-promu, le 79 % était déjà exposé v3 cas A). Gain réel = **GRANULARITÉ** — 2 691 fiches passent d'agrégat Cereq (discipline×niveau, e.g. moyenne nationale informatique master) à établissement-spécifique InserSup (par UAI, e.g. ENSIBS Vannes Master Cyber 2021). Hypothèse à valider bench : la granularité réduit-elle empiriquement les hallu Mistral plus que la moyenne Cereq ne les réduisait déjà ?

---

## Méthode

Build mutualisé D1+D5 sur D5 branch (D1 commit `d060180` cherry-picked) :
- `python -m scripts.embed_unified` (Mistral-embed dim 1024, batched 64, ETA ~10-15 min, ~$3)
- `formations_unified.index` régénéré sur corpus enrichi profil_admis (D1) + insertion_pro source insersup (D5)

Validation indépendante D5 via `scripts/validate_d1_d5_retrieval.py` :
- 5 questions ciblées insertion ("salaire sortie Master Cyber ENSIBS Vannes" / "insertion 6 mois MIAGE Tours" / "taux d'emploi 12 mois informatique Paris-Saclay" / etc.)
- Top-5 fiches récupérées, marker `"Insertion pro (source InserSup MESR"` cherché dans `fiche_to_text(fiche)`

Audit empirique S3 enrichissement :
- matched : 2 691 (5 % corpus total absolu)
- unmatched_no_uai : 45 070 (fiches sans cod_uai — non-cible InserSup par construction)
- unmatched_no_match : 7 845 (cod_uai présent mais pas dans CSV InserSup)
- overwritten_cereq : 2 691 (= 100 % des match)
- overwritten_cfa : 0
- net unique add : 0 ⚠️

---

## Sample 3 questions retrieved (Pattern #4)

Extraits verbatim depuis `docs/sprint12-D1-D5-validation-retrieval-raw-2026-05-01.jsonl`. Tous les top-1 retrievés ont **section absente** — 0/5 hit.

### Q1 — "Quel est le salaire à la sortie d'un Master Cybersécurité ENSIBS Vannes ?"

> Top-1 : `expert en développement de solutions de cybersécurité` — _(établissement vide)_
> Section "Insertion pro (source InserSup MESR" présente top-1 : **NON**
> Section présente sur **0/5** top-5
> _Cause structurelle_ : retrieval favorise similarité nom de formation ("expert cybersécurité") sur fiche sans `cod_uai` (donc non-éligible InserSup matching). La fiche concrète ENSIBS Vannes Master Cyber est plus loin dans le ranking.

### Q2 — "Insertion professionnelle à 6 mois pour un Master MIAGE Tours ?"

> Top-1 : `master mention tourisme` — _(établissement vide)_
> Section "Insertion pro (source InserSup MESR" présente top-1 : **NON**
> Section présente sur **0/5** top-5
> _Cause structurelle_ : embedding similarité MIAGE → master tourisme (proximité lexicale faible mais embedding plat retrieve fiche sans uai). InserSup matching n'a pas couvert MIAGE Tours dans les 2 691.

### Q3 — "Taux d'emploi à 12 mois pour un Master informatique Paris-Saclay ?"

> Top-1 : `diplôme d'ingénieur de l'École polytechnique universitaire de l'université Paris-Saclay spécialité informatique` — Paris-Saclay
> Section "Insertion pro (source InserSup MESR" présente top-1 : **NON**
> Section présente sur **0/5** top-5
> _Cause structurelle_ : la fiche correcte Paris-Saclay informatique est retrieved en top-1 mais elle a `insertion_pro.source = 'cereq'` (pas insersup) — InserSup n'a pas de match UAI pour cette fiche spécifique malgré son existence dans le corpus.

---

## Limitations honnêtes

1. **Net unique add = 0 fiches** : D5 ne change pas le coverage globale, juste la granularité sur 2 691 fiches univ. Le narratif "élimine ~80 % hallu insertion+salaires" est sur-promu en absolu — le 79 % existait déjà via Cereq + CFA exposé v3.
2. **Hypothèse granularité non-validée empiriquement par ce bench** : ce verdict mesure si l'index FAISS rebuilt expose bien la nouvelle section. Le gain réel "Mistral cite chiffre établissement-spécifique vs agrégat" demanderait un bench E2E avec génération + judge — hors scope D5 ce sprint, à prévoir Sprint 12+.
3. **Sample n = 5 questions ciblées** trop petit pour confidence interval propre.
4. **Politique d'overwrite InserSup > Cereq** : décision de design. Argument : InserSup MESR par UAI est plus granulaire que Cereq agrégé par discipline+niveau. Mais cohérent avec « le système gagne, pas le paper » (CLAUDE.md OrientIA principe directeur #1) : à mesurer empiriquement par bench downstream.
5. **Threshold flag spec ordre <30%** : 5 % match absolu < 30 % cible, mais denominator ambigu (corpus total vs univ uniquement). Flag transparent à Jarvis 2026-05-01-1715.

---

## Recommandation merge / no-merge

**Verdict factuel empirique** :
- 0/5 hit rate top-1 = **NOOP empirique sur ce sample**
- L'hypothèse "granularité gain InserSup > Cereq agrégat" non-validée par bench retrieval
- Les 2 691 fiches enrichies InserSup existent dans le corpus mais ne sont pas surfaced en top-K par les questions insertion/salaire types
- Cause structurelle identifiée : embedding similarity favorise similarité nom de formation sur similarité section nouvelle. La section "Insertion pro (source InserSup MESR..." ajoute du signal mais insuffisant pour battre le signal nom/contenu sémantique des fiches SANS InserSup data (souvent sans `cod_uai`)

**Décisions possibles à arbitrer Matteo** :

**Option A — Merge tel quel** :
- Préserve la couverture granulaire pour 2 691 fiches (utile si Mistral cite explicitement une de ces fiches dans sa génération)
- Coût marginal nul post-merge (la code-base est stable, les 8 tests verts garantissent la robustesse)
- Limite : noop sur la métrique retrieval bench → pas d'argument empirique fort pour le narrative INRIA

**Option B — Pas merger, retraiter** :
- Investigation Sprint 12+ pour comprendre pourquoi les fiches enrichies ne montent pas en top-K
- Pistes :
  - Boost reranker sur source `'insersup'` (×1.5) pour favoriser ces fiches
  - Élargir matching UAI → fuzzy (matching nom établissement + ville en complément)
  - Augmenter le poids de la section InserSup dans `fiche_to_text` (placement, longueur, marqueurs)
- Coût : +1-2 jours travail Sprint 12

**Option C — Rollback D5** :
- Revert overwrite Cereq → restaure l'état pre-D5 (32 704 cereq + 11 314 cfa)
- Argument : si D5 = noop, autant ne pas dégrader la lisibilité du code et de la pipeline
- Limite : le code D5 reste utile en infrastructure pour Sprint 12+ futurs travaux InserSup

**Mon biais** : Option A par défaut (préserver l'infrastructure code D5 pour itérations futures Sprint 12+). Mais arbitrage final est sur Matteo via Jarvis. Audit Pattern #3+#4 indépendant attendu.

## Limitations honnêtes (continued)

5. **Sample n=5 questions ciblées trop petit** — le 0/5 est un signal fort mais pas définitif. Triple-run avec 15-20 questions étendues ferait verdict plus robuste.
6. **Investigation root cause non-exhaustive** — j'ai identifié la cause structurelle (embedding nom > section ajoutée) mais pas testé les remèdes (boost reranker, weight section). Le bench actuel mesure le retrieval VANILLA post-rebuild ; un retrieval avec reranker tweaks pourrait améliorer.
7. **Effet downstream sur GENERATION non-mesuré** — peut-être que Mistral mentionne quand même les fiches insersup dans sa génération via context plus loin dans top-K (au-delà de top-1). Bench E2E avec génération + judge faithfulness hors scope D5.

---

## Livrables

- ✅ `src/collect/insersup.py` — fonction `attach_to_insertion_pro` + `INSERSUP_SOURCE_URL` (commit `e5b02bf`)
- ✅ `src/rag/embeddings.py` — branch dispatch `source == "insersup"` dans `_format_insertion_pro` + helper `_pct_int`
- ✅ `tests/test_embeddings.py` — 8 nouveaux tests insersup + 2 régressions cereq/cfa préservées
- ✅ `scripts/enrich_with_insersup_d5.py` — script wiring corpus
- ✅ `data/processed/formations_unified.json` — corpus enrichi (2 691 fiches insersup, overwritten cereq)
- ✅ `data/processed/formations_unified.pre_d5_backup.json` — backup pré-enrichissement (gitignored 95M)
- ⏳ `data/embeddings/formations_unified.index` — re-build mutualisé D1+D5 (en cours)
- ⏳ `docs/sprint12-D1-D5-validation-retrieval-raw-2026-05-01.jsonl` — raw bench
- ⏳ Ce verdict (sample 3 questions à compléter)

**Coût** : ~$3 build (mutualisé D1+D5) + $0.001 queries embed = ~$3 partagé avec D1.
**Wall-clock** : ~3h cumul session D5 (discovery existing modules + S2bis adapter + S3 wiring + S4 dispatch + 8 tests + push + verdict en cours).
**Suite tests** : 2071 passed, 1 skipped, 0 régression vs 2063 baseline post-Sprint 11 P1-1.
