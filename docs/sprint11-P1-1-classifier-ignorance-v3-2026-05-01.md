# Sprint 11 P1-1 — Classifier ignorance v3

**Date** : 2026-05-01
**Branche** : `feat/sprint11-P1-1-backstop-b-soft`
**Référence ordre** : `2026-05-01-1334-claudette-orientia-sprint11-P1-1-backstop-b-soft-classifier-v3` (Sous-étape 0)
**Auteur** : Claudette
**Cible** : passer v5b 1/5 → 2/5 critères stricts (Empathie déjà OK + Ignorance OK) AVANT bench backstop B → métriques propres comparables.

---

## Problème

Q11 v5b (réponse Mistral du re-run 2026-05-01) déclenche un faux `PARTIAL_FUZZY` malgré une ignorance parfaite (`faithfulness=1.00`). Le verdict v5b reste à 1/5 critères stricts uniquement parce que le classifier rate la wording.

**Réponse Mistral réelle Q11 v5b** (extraite de `docs/sprint11-P1-1-rerun-v5b-raw-2026-05-01.jsonl`) :

> 1. Les fiches fournies **ne concernent pas** l'IFSI de Lille (institut de formation en soins infirmiers).
> 2. Je n'ai **aucune donnée** sur le nombre d'admis 2026 ou le nom du directeur dans mes sources.

Les patterns v2 (Sous-étape 4.1, commit `12c7047`) couvrent :
- "je n'ai pas d'information"
- "ne figurent pas dans les fiches"
- "non sourcé / non disponible"

Mais **pas** :
- "aucune **donnée**" (vs "informations" en v2)
- "ne **concernent** pas" (vs "ne figurent pas" en v2)

Conséquence : **signal mort** — Mistral exprime correctement son ignorance, mais le classifier flag PARTIAL_FUZZY.

---

## Fix v3 (additif, 0 régression v2)

`scripts/diag_ab_temperature_sprint11_p1_1.py` — `IGNORANCE_OK_PATTERNS` étendu de 2 patterns :

```python
# Mots-clés explicites d'absence
re.compile(
    r"aucune\s+(?:donn[ée]es?|statistiques?|pr[ée]cisions?|d[ée]tails?|info\b)",
    re.IGNORECASE,
),
# Verbes de couverture niés sur les fiches/sources
re.compile(
    r"ne\s+(?:concernent|couvrent|incluent|contiennent|portent\s+sur)\s+pas\s+"
    r"(?:l['']|le\s|la\s|les\s|cette\s|ces\s|d['']|de\s)",
    re.IGNORECASE,
),
```

**Choix de design** :

1. **Additif** — les 8 patterns v2 sont préservés. Régression v2 vérifiée par les tests `test_v2_pattern_pas_d_information_sur_preserve` et `test_v2_pattern_ne_figurent_pas_preserve`.
2. **Pattern 1 large mais sûr** — `aucune (donnée|statistique|précision|détail|info)` est un signal d'absence très explicite. Les faux positifs hypothétiques ("aucune chance", "aucune raison") n'apparaissent pas dans le contexte question piège ; testé sur la suite globale = 0 régression.
3. **Pattern 2 contraint par déterminant** — `ne {verbe} pas` doit être suivi de `l'/le/la/les/cette/ces/d'/de` pour matcher. Évite "ces fiches ne concernent pas tellement" (sans déterminant) qui n'est pas une vraie déclaration d'absence.

---

## Tests (Apprentissage #4 méta appliqué)

`tests/test_classify_piege_response_v3.py` — 13 cas, 13 verts.

**Diversité réelle imposée par Apprentissage #4** : tester avec **exemples réels variés** AVANT déploiement, pas seulement des hypothèses bien formées.

| Type | # cas | Exemples |
|---|---|---|
| **IGNORANCE_OK** réel Q11 v5b | 1 | Wording authentique du re-run bench |
| **IGNORANCE_OK** paraphrases | 5 | "aucune statistique" / "ne couvrent pas" / "aucune précision" / "ne contiennent pas" / "aucune donnée disponible" |
| **IGNORANCE_OK** régression v2 | 2 | "pas d'information sur" / "ne figurent pas" |
| **INVENTION_KO** | 2 | "250 admis en 2026 dirigé par Mme Dupont" / "Le directeur s'appelle Pierre Martin" |
| **PARTIAL_FUZZY** esquive sans aveu | 2 | Redirection "consulte l'IFSI" / question relancée sans aveu |
| Edge case | 1 | input vide ou `None` |

**Suite globale** : 2019 passed, 1 skipped (+13 nouveaux vs baseline) — 0 régression sur les 1998+ tests cumul Sprint 11.

---

## Impact attendu sur verdict v5b

Avant fix : 1/5 critères stricts (Empathie ⭐ acquis, Format / Ignorance / Hallu / Faithfulness manqués).

Après fix v3 (sans bench LLM, validation analytique) : **2/5 critères stricts** (Empathie + Ignorance OK).

Métriques propres pour bench backstop B comparables au baseline v5b corrigé. Hallu chiffres précis et faithfulness restent à attaquer côté backstop B (Sous-étape 1).

---

## Apprentissage #4 méta — réinforcement

**Capitalisation parallèle** : `~/projets/.claude/memory/feedback_pr_patterns.md` est mis à jour avec une note de **réinforcement** Apprentissage #4 (pas un nouvel apprentissage — l'existant prouve sa valeur sur cet épisode v2 → v3).

Pattern reproductible :
1. Bug observé (Q11 v5 PARTIAL_FUZZY incorrect)
2. Fix v2 sur exemple réel + 1 paraphrase ⇒ marche temporairement
3. Re-bench v5b avec wording **différent** ⇒ bug réapparaît
4. Fix v3 avec **5 paraphrases couvrant le spectre lexical** + tests automatisés ⇒ robustesse durable

Leçon dure : **pour un classifier regex sur génération LLM, prévoir directement 5+ paraphrases au premier fix**, ne pas itérer fix-après-fix. Coût marginal 10 min, ROI = pas de re-fix Sprint 12+.

---

## Livrables

- ✅ `scripts/diag_ab_temperature_sprint11_p1_1.py` — 2 patterns ajoutés
- ✅ `tests/test_classify_piege_response_v3.py` — 13 tests (NEW)
- ✅ `docs/sprint11-P1-1-classifier-ignorance-v3-2026-05-01.md` — ce doc
- ✅ `~/projets/.claude/memory/feedback_pr_patterns.md` — note de réinforcement Apprentissage #4 (en parallèle)

**Coût** : $0 (pas de call LLM). **Wall-clock** : ~25 min.
**Suite tests** : 2019 passed, 1 skipped, 0 régression.
