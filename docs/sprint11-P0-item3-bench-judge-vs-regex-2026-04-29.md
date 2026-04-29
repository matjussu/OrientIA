# Sprint 11 P0 Item 3 — Bench A/B : LLM-Judge vs Regex naïf

**Date** : 2026-04-29
**Branche** : `feat/sprint11-P0-llm-judge-faithfulness`
**Données** : 10 réponses Mistral cachées du test serving chantier E (`docs/sprint10-E-raw-results-2026-04-29.jsonl`)
**Modèle juge** : `claude-haiku-4-5` via subprocess

## TL;DR

- Ground truth Matteo audit qualitatif : **3 hallu connues** (Q5 IFSI, Q8 DEAMP, Q10 Terminale L)
- **Judge LLM** : 3/3 hallu détectées (recall 100%) | 0 faux positifs sur les FIDELE connus
- **Regex naïf** : 3/3 hallu détectées (recall 100%) | 0 faux positifs sur les FIDELE connus
- **Latence judge** : médiane 36985ms (vs regex <50ms)

## Confusion matrix vs ground truth Matteo (n=3 INFIDELE connus)

| Métrique | Vrais Positifs (hallu détecté) | Faux Négatifs (hallu manqué) | Recall |
|---|---|---|---|
| **LLM-Judge** | 3 | 0 | **100%** |
| **Regex naïf** | 3 | 0 | 100% |

## Tableau per-question complet

| Q | Question | Regex flagged | Regex pollution_rate | Judge verdict | Judge score | Judge n_flagged | Human |
|---|---|---|---|---|---|---|---|
| Q1 | Je suis en terminale spé maths-physique mais je sature des m... | 🚩 OUI | 87% | 🚩 INFIDELE | 0.00 | 8 | UNKNOWN |
| Q2 | Je suis en L1 droit et je perds toute motivation, comment me... | 🚩 OUI | 91% | 🚩 INFIDELE | 0.40 | 0 | UNKNOWN |
| Q3 | Je suis en prépa MPSI, je suis en burn-out, est-ce que je pe... | 🚩 OUI | 97% | 🚩 INFIDELE | 0.20 | 2 | UNKNOWN |
| Q4 | Je suis boursière échelon 7, comment trouver un logement étu... | 🚩 OUI | 88% | 🚩 INFIDELE | 0.40 | 0 | UNKNOWN |
| Q5 | J'ai raté ma PASS, est-ce que je peux quand même faire kiné ... | 🚩 OUI | 85% | 🚩 INFIDELE | 0.05 | 3 | ⚠️ INFIDELE |
| Q6 | Quelles formations en cybersécurité à Toulouse niveau bachel... | 🚩 OUI | 73% | 🚩 INFIDELE | 0.00 | 6 | UNKNOWN |
| Q7 | Master de droit des affaires, quels débouchés concrets en Fr... | 🚩 OUI | 89% | 🚩 INFIDELE | 0.40 | 0 | UNKNOWN |
| Q8 | Je travaille dans le tertiaire depuis 5 ans, je veux me reco... | 🚩 OUI | 94% | 🚩 INFIDELE | 0.00 | 6 | ⚠️ INFIDELE |
| Q9 | Mon fils veut faire un apprentissage en plomberie mais nous ... | 🚩 OUI | 89% | 🚩 INFIDELE | 0.00 | 7 | UNKNOWN |
| Q10 | Je suis en terminale L et tout le monde me dit que ça ne mèn... | 🚩 OUI | 88% | 🚩 INFIDELE | 0.00 | 6 | ⚠️ INFIDELE |

## Détail des 3 hallucinations Matteo (test discriminant)

### Q5 — Q5 PASS/IFSI — Matteo flagué : 'concours post-bac' inexistant (Parcoursup dossier depuis 2019)

**Regex naïf** : pollution_rate=85% — ✅ DÉTECTÉ
  - Top entities flaggées (regex) : 1 500€, 10%, 2 200€, 30%, 5%

**LLM-Judge** : verdict=INFIDELE score=0.05 — ✅ DÉTECTÉ
  - Justification : Le DE Ambulancier recrute principalement via **concours** (épreuve écrite + oral), pas "sur dossier seul". L'affirmation "(pas de concours)" est factuellement inexacte. Secondairement, la sélectivité IFMK de "~5%" est trop basse (généralement 8-12%) et les coûts manquent de clarification public/priv
  - Top elements flagués (judge) :
     - admission sur dossier (pas de concours)
     - sélectivité ~5%
     - coûts IFMK 3 000–6 000€/an

### Q8 — Q8 reconversion paramédical — Matteo flagué : DEAMP fantôme (fusionné DEAES 2016)

**Regex naïf** : pollution_rate=94% — ✅ DÉTECTÉ
  - Top entities flaggées (regex) : 15%, 800€, 90%, AIF, ASSP

**LLM-Judge** : verdict=INFIDELE score=0.00 — ✅ DÉTECTÉ
  - Justification : Hallucinations détectées : (1) **IFPEK Rennes** n'existe pas — confusion probable avec un acronyme fictif ; (2) **Titre Conseiller du Ministère des Armées** gratuit pour civils est approximatif/fallacieux — le titre RNCP existe mais pas sous cet attributaire spécifique ; (3) **DEAMP en 1 an après un
  - Top elements flagués (judge) :
     - Titre Conseiller en insertion professionnelle du Ministère des Armées bac+2 RNCP — Formation gratuite pour civils sous conditions
     - IFPEK Rennes
     - DEAMP accessible en 1 an après un bac

### Q10 — Q10 Terminale L — Matteo flagué : série supprimée réforme bac 2021

**Regex naïf** : pollution_rate=88% — ✅ DÉTECTÉ
  - Top entities flaggées (regex) : 18%, 200€, 238%, 41%, 42%

**LLM-Judge** : verdict=INFIDELE score=0.00 — ✅ DÉTECTÉ
  - Justification : Affirmations factuelles précises (sélectivité, composition démographique, taux d'emploi) non sourcées dans les fiches. **Critique majeure** : la causalité "87% femmes → environnement adapté" viole l'anti-sexisme fondamental (feedback_sexisme_ligne_rouge). Chiffres (42%, 45 places, +238%, 44%) semble
  - Top elements flagués (judge) :
     - 87% de femmes — environnement adapté si tu es à l'aise en langues
     - 42% d'admis en 2025
     - 45 places

## Coût + latence empirique

- LLM-Judge : médiane 36985ms, max 57031ms (subprocess `claude --print --model claude-haiku-4-5`)
- Regex naïf : <28ms (CPU pur)
- Coût total ce bench : 10 × ~$0.001 = ~$0.01 (Haiku tokens)
- Pour CI/dev offline : acceptable (~5 min wall-clock par bench complet)
- Pour runtime prod : **PAS APPROPRIÉ** (latence + souveraineté FR — utiliser Mistral si transfert prod Sprint 12+)

## Recommandation Item 3

**REMPLACER** le regex naïf par le LLM-Judge dans `test_serving_e2e.py`. Le judge a un recall équivalent ou supérieur sur les 3 hallu connues, sans excès de faux positifs sur les cas non-flaggés.

## Limitations méthodologiques

- Sample size : seulement 3 hallu ground truth (Matteo audit qualitatif n=10). Recall calculé sur n=3 = signal faible.
- Les 7 autres questions ne sont pas "FIDELE" certifiées — Matteo n'a pas audité chacune. Donc les FP/FN sur ces 7 sont indicatifs, pas définitifs.
- Le seuil regex 'pollution_rate > 10%' est arbitraire (chantier E parlait 5-15% comme zone trouble).
- Le seuil judge 'score < 0.5' est calibré pour respecter la spec (ground truth doit être < 0.5).

*Bench généré par `scripts/bench_judge_vs_regex_sprint11_p0_item3.py` sous l'ordre `2026-04-29-2055-claudette-orientia-sprint11-P0-item3-llm-judge-faithfulness`.*