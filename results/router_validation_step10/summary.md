# Step 10 — Validation live A/B router_llm

_Run: 2026-05-09T11:24:03.389054+00:00_
_Mode: router-only (cheap)_
_Questions: 15_

## A/B latency
| Mode | n_ok | p50 (s) | p95 (s) | mean (s) |
|---|---:|---:|---:|---:|
| router=ON | 15 | 0.56 | 0.90 | 0.61 |
| router=OFF | 0 | — | — | — |

## Routing correctness (mode router=ON)
- Confidence moyenne : **0.95** sur 15 questions (gate plan ≥ 0.7)
- Routing match (sub_index attendu présent) : **6/6** (100 %)
- Refusal handled correctly : **13/15** (87 %)

## Sub-index choisi par question (mode router=ON)
| ID | category | question | sub_indexes | conf | refusal | match |
|---|---|---|---|---:|---|:-:|
| G02 | lyceen_parcoursup | Combien de places en BUT Informatique à Lyon ?... | formations | 0.95 | — | — |
| G21 | metier | Que fait un actuaire au quotidien ?... | metiers,statistiques | 0.9 | — | — |
| G23 | metier | Quels métiers vont recruter en Occitanie en 2030 ?... | metiers | 0.95 | — | — |
| G29 | metier | Quel salaire moyen pour un cadre supérieur PCS 37 ?... | statistiques | 0.95 | — | — |
| G36 | geographique | Quelles formations en Guadeloupe ?... | formations | 0.95 | — | — |
| G45 | geographique | École de commerce à Lyon ?... | formations | 0.95 | — | — |
| G46 | vie_etudiante | Combien coûte le logement étudiant CROUS à Lyon ?... | aides_territoires | 0.95 | — | — |
| A07 | adversarial | Mention TB obligatoire pour entrer en CPGE Henri-IV à T... | formations | 0.95 | — | — |
| X01 | cross_domain | Comment soigner une grippe ?... | formations,metiers,statistiques,aides_territoires | 1.0 | cross_domain | — |
| L01 | live | Quelle est la meilleure école de commerce en France ?... | formations | 0.95 | superlative_no_data | ✓ |
| L02 | live | Quelles écoles d'ingénieur en cybersécurité existent en... | formations | 0.95 | — | ✓ |
| P01 | paraphrase | Combien ça coûte de vivre dans une chambre étudiante à ... | aides_territoires | 0.95 | — | ✓ |
| P02 | paraphrase | Quels jobs pour quelqu'un qui aime les chiffres ?... | metiers,statistiques | 0.95 | — | ✓ |
| A09 | adversarial | Top 3 des prépas scientifiques en France ?... | formations | 0.95 | superlative_no_data | ✓ |
| A10 | adversarial | Combien gagnent les meilleurs avocats à Paris ?... | statistiques | 0.95 | — | ✓ |

## Verdict gate step 10

- Confidence ≥ 0.70 : ✓ (0.95)
- Latency p95 ≤ 1.0s : ✓ (0.90s)
- Routing match ≥ 85 % : ✓ (6/6)
- Refusal handled ≥ 85 % : ✓ (13/15)

**GATE STEP 10 PASS ✅**