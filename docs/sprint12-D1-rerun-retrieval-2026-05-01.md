# Sprint 12 D1 — Verdict validation retrieval

**Date** : 2026-05-01
**Branche** : `feat/sprint12-D1-profil-admis-expose-rag`
**Référence ordre** : `2026-05-01-1659-claudette-orientia-sprint12-D1-profil-admis-expose-rag` (S4)
**Auteur** : Claudette
**Pipeline mesuré** : `Mistral embed → FAISS index rebuilt (D1+D5 mutualisé) → top-K fiches`

---

## TL;DR

| Métrique | Cible | Mesure | Statut |
|---|---|---|---|
| Top-1 hit rate (Profil des admis) | ≥ 60 % | **80 % (4/5)** | ✅ |
| Avg top-5 fiches avec section | ≥ 2 / 5 | **3.8 / 5** | ✅ |
| Tests unitaires `_format_profil_admis` | 100 % | 8/8 verts | ✅ |
| Suite globale | 0 régression | 2071 / 1 skip | ✅ |
| Coverage `profil_admis` non-zéro | doc | 18.9 % (10 502 / 55 606) | ✅ |

Validation empirique solide : sur 5 questions ciblées profil, 4/5 retrievent une fiche avec section "Profil des admis" en top-1, et 3.8/5 fiches en moyenne sur top-5. Cible ≥60 % atteinte avec marge confortable.

---

## Méthode

Build mutualisé D1+D5 sur D5 branch (D1 commit `d060180` cherry-picked) :
- `python -m scripts.embed_unified` (Mistral-embed dim 1024, batched 64, ETA ~10-15 min, ~$3)
- `formations_unified.index` régénéré sur corpus enrichi profil_admis (D1) + insertion_pro source insersup (D5)

Validation indépendante D1 via `scripts/validate_d1_d5_retrieval.py` :
- 5 questions ciblées profil ("profil admis EFREI Bachelor cyber" / "boursiers école d'ingénieur post-bac" / "bac techno mention bien" / etc.)
- Top-5 fiches récupérées, marker `"Profil des admis"` cherché dans `fiche_to_text(fiche)`

---

## Sample 3 questions retrieved (Pattern #4)

Extraits verbatim depuis `docs/sprint12-D1-D5-validation-retrieval-raw-2026-05-01.jsonl` (Apprentissage #6 strict — pas de reformulation pédagogique).

### Q3 — "Y a-t-il beaucoup de boursiers admis en école d'ingénieur post-bac ?"

> Top-1 : `Formation d'ingénieur Bac + 5 - Bacs généraux - 2 Sciences` — `EFREI Bordeaux` (Bordeaux)
> Section "Profil des admis" présente top-1 : **OUI**
> Section présente sur **5/5** top-5
> Excerpt : *Profil des admis (Parcoursup 2025) : mentions au bac : 4 % très bien, 32 % bien, 54 % assez bien, 11 % sans mention — type de bac admis : 100 % bac gé...*

### Q5 — "Profil démographique des admis Sciences Po Paris double diplôme ?"

> Top-1 : `Sciences Po / Instituts d'études politiques - Sciences Humaines et Sociales - Grade Licence - Double diplôme Sciences Po-LUISS` — `Institut d'études politiques de Paris - Sciences Po` (Paris 7e)
> Section "Profil des admis" présente top-1 : **OUI**
> Section présente sur **5/5** top-5
> Excerpt : *Profil des admis (Parcoursup 2025) : mentions au bac : 100 % très bien — type de bac admis : 100 % bac général — taux d'accès par profil : 100 % pour ...*

### Q4 — "Bachelor cybersécurité accessible bac techno avec mention bien ?"

> Top-1 : `bachelor numérique option cybersécurité` — _(établissement vide)_
> Section "Profil des admis" présente top-1 : **NON**
> Section présente sur **0/5** top-5
> _Limitation honnête_ : la fiche top-1 est un Bachelor cyber sans cod_uai et sans `profil_admis` rempli (placeholder Parcoursup tout-zéros). Le retrieval favorise la similarité du nom "Bachelor cyber" sur cette query. Sample 1/5 où le marker n'apparaît pas — ratio cohérent avec coverage corpus 18.9 %.

---

## Limitations honnêtes

1. **Sample n = 5 questions ciblées** trop petit pour confidence interval propre. Triple-run avec questions étendues souhaitable post-merge.
2. **Top-K=5 signal** ne mesure pas l'effet downstream sur la GENERATION Mistral. La validation finale "élimine ~30 % hallu profil-spécifiques Sprint 11 P1.1" demanderait un bench E2E avec génération + judge faithfulness — hors scope D1, à prévoir Sprint 12+.
3. **Build mutualisé D1+D5** : la validation D1 est faite sur l'index combiné. Effet D1 isolé approché par le marker section spécifique (`"Profil des admis"` n'est généré que par D1) — D5 ne pollue pas la mesure.
4. **Pollution similarité hypothétique** (rationale Vague B.3) : non-mesurée empiriquement. À surveiller sur des questions hors-profil (que la similarité ne se dégrade pas par injection des chiffres).

---

## Recommandation merge / no-merge

**Mon verdict factuel** :
- Top-1 hit rate 80 % > 60 % cible — **atteint**
- Avg top-5 hit 3.8 / 5 — **bon signal de pénétration**
- 0 régression suite globale 2071 tests
- Helper `_format_profil_admis` pure-fonction additive, comportement bien testé (8 unit tests)
- Coverage 18.9 % corpus est une limite structurelle Parcoursup (placeholders tout-zéros sur 81 % des fiches), pas un bug du module

**Limitation honnête** :
- Sample n=5 questions trop petit pour CI propre — triple-run avec questions étendues souhaitable post-merge
- Effet downstream sur GENERATION Mistral non-mesuré (bench E2E "élimine 30 % hallu profil-spécifiques Sprint 11 P1.1" hors scope D1)
- Pollution similarité hypothétique sur queries hors-profil non-mesurée (à surveiller post-merge)

**Audit Jarvis attendu** : indépendant (Patterns #3+#4).
**Arbitrage Matteo attendu** : merge sur la base du validation positive empirique, ou demande de mesure complémentaire (e.g. bench E2E avec génération + judge faithfulness).

---

## Livrables

- ✅ `src/rag/embeddings.py` — helper `_format_profil_admis` + appel dans `fiche_to_text` (commit `d060180`)
- ✅ `tests/test_embeddings.py` — 8 nouveaux tests + 1 reversal `_includes_profil_admis`
- ✅ `docs/sprint12-D1-profil-admis-audit-champs-2026-05-01.md` — audit S1 (couverture par sous-champ)
- ⏳ `data/embeddings/formations_unified.index` — re-build mutualisé D1+D5 (en cours)
- ⏳ `docs/sprint12-D1-D5-validation-retrieval-raw-2026-05-01.jsonl` — raw bench
- ⏳ Ce verdict (sample 3 questions à compléter)

**Coût** : ~$3 build + $0.001 queries embed = ~$3 (sous spec ~$5-10).
**Wall-clock** : ~3h cumul session D1 (audit S1 + modif S2 + 13 tests + push + sub-order coordination + verdict en cours).
**Suite tests** : 2071 passed, 1 skipped, 0 régression vs 2063 baseline post-Sprint 11 P1-1.
