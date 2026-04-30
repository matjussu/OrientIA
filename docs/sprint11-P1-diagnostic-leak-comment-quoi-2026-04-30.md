# Sprint 11 P1 préparation — Diagnostic leak Q&A Golden Comment→Quoi

**Date** : 2026-04-30
**Branche** : `diag/sprint11-P1-leak-comment-quoi` depuis main `2d36cb4`
**Ordre Jarvis** : `2026-04-30-2125-claudette-orientia-diag-leak-comment-quoi-sprint11-P1`
**Données** : 10 questions du re-run Item 4 (PR #111 mergée SHA `2d36cb4`)
**Coût** : $0 (analyse déterministe, pas d'appel LLM)

## TL;DR

- **39 chiffres / entités** flagués INFIDELE par le judge sur 10 questions
- **LEAK** (apparaît dans Q&A Golden retrieved few-shot) : **3** (7.7%)
- **INVENTION** (absent Q&A Golden) : **36** (92.3%)
- **IC95 binomial Wilson** taux LEAK : [2.7%, 20.3%]
- **Verdict directionnel Sprint 11 P1** : **INVENTION DOMINANTE (<20%)**

---

## §1 Méthode

Pour chaque question des 10 du re-run Item 4 :
1. Extraction `faithfulness.flagged_entities` du judge LLM (Item 3, claude-haiku-4-5)
2. Lookup Q&A Golden retrieved en few-shot prefix via `(golden_qa.prompt_id, golden_qa.iteration)` dans `data/processed/golden_qa_meta.json` (45 records)
3. Concaténation des champs textuels Q&A Golden : `question_seed | question_refined | answer_refined`, normalisation casefold + collapse whitespace
4. Classification de chaque flagged_entity :
   - **LEAK** : substring inclusive case-insensitive dans le texte Q&A Golden concat OU chiffre extrait (regex `\d+(?:[,.]\d+)?`) présent dans le texte
   - **INVENTION** : absent

**Justification substring inclusive** (vs matching exact) : conforme spec ordre — chiffre arrondi (ex Mistral cite `27%` quand Q&A Golden a `27 %` ou `27` dans contexte différent) doit compter LEAK car intention pioche.

**Edge case** : si Q&A Golden retrieved n'a pas de chiffres ou texte vide, toutes flagged_entities = INVENTION par défaut.

---

## §2 Tableau per-question

| Q | Q&A Golden retrieved | N flagged | N LEAK | N INVENTION | % LEAK |
|---|---|---|---|---|---|
| Q1 | A1 iter 6 | 4 | 0 | 4 | 0% |
| Q2 | A2 iter 0 | 2 | 0 | 2 | 0% |
| Q3 | A1 iter 6 | 2 | 0 | 2 | 0% |
| Q4 | A2 iter 18 | 2 | 0 | 2 | 0% |
| Q5 | A3 iter 0 | 8 | 1 | 7 | 12% |
| Q6 | A1 iter 3 | 7 | 0 | 7 | 0% |
| Q7 | A2 iter 14 | 4 | 1 | 3 | 25% |
| Q8 | A2 iter 0 | 1 | 0 | 1 | 0% |
| Q9 | A1 iter 19 | 3 | 1 | 2 | 33% |
| Q10 | A3 iter 0 | 6 | 0 | 6 | 0% |

---

## §3 Stats agrégées

- **Total flagged entities** (10 questions cumul) : 39
- **LEAK** : 3 → **7.7%**
- **INVENTION** : 36 → 92.3%
- **IC95 Wilson taux LEAK** : [2.7% ; 20.3%] (intervalle de confiance binomial sur N=39)

**Lecture statistique** : avec N=39, l'IC95 reste assez large mais le centre 8% donne un signal directionnel utilisable pour l'arbitrage Sprint 11 P1.

---

## §4 Verdict directionnel Sprint 11 P1

### INVENTION DOMINANTE (<20%)

INVENTION DOMINANTE (<20%) — Hallu = invention pure Mistral, peu lié aux Q&A Golden. Sprint 11 P1 priorité = P1.1 Strict Grounding renforcé contre invention de stats.

### Mapping seuils ordre (rappel)

| Taux LEAK observé | Action Sprint 11 P1 |
|---|---|
| > 50 % | **LEAK MAJEUR** — revoir architecture Q&A Golden few-shot (ex retirer `answer_refined`, garder uniquement `question_seed` comme pattern ton) |
| 20-50 % | **MIXTE** — 2 chantiers parallèles : refactor few-shot + renforcer Strict Grounding |
| < 20 % | **INVENTION DOMINANTE** — P1.1 Strict Grounding renforcé contre invention stats reste la bonne cible |

---

## §5 Limitations méthodologiques

- **Sample size** : N=39 flagged entities sur 10 questions = signal statistique modéré. IC95 Wilson [2.7%, 20.3%] reflète l'incertitude réelle.
- **Substring inclusive** peut surestimer LEAK si une entité contient un mot commun présent dans la Q&A Golden par hasard (faux positif). Mitigation : la classification par chiffres extraits est plus discriminante que substring textuel large.
- **Pas de dédup** entre questions : si plusieurs questions retrieved la même Q&A Golden, les leaks comptent indépendamment.
- **Faithfulness scoring binaire INFIDELE** ne distingue pas hallu mineure vs majeure. Une entity = un point. Granularité acceptable pour ce diagnostic mais pas pour l'arbitrage exécution.
- **Pas de cross-référence avec fiches RAG** : un chiffre absent Q&A Golden ET absent fiches = INVENTION par défaut. Mais théoriquement il pourrait venir de l'historique conversationnel (Item 2 buffer) — non pris en compte ici (bench single-shot).

---

*Diagnostic généré par `scripts/diag_leak_comment_quoi_sprint11_p1.py` sous l'ordre `2026-04-30-2125-claudette-orientia-diag-leak-comment-quoi-sprint11-P1`. Standby pour arbitrage Matteo Sprint 11 P1.*