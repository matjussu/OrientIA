# Sprint 11 P1.1 Phase 2 Sous-étape 1 — A/B Températures

**Date** : 2026-04-30
**Branche** : `feat/sprint11-P1-1-strict-grounding-stats`
**Ordre Jarvis** : `2026-04-30-2150-claudette-orientia-sprint11-P1-1-strict-grounding-stats-phase1` (Phase 2 enrichie v3)

## Setup

- Températures testées : [0.0, 0.1, 0.2, 0.3]
- Questions : 10 baseline Item 4 + 1 q piège ignorance
- Q piège : *« Quel est le nombre exact d'admis 2026 et le nom du directeur de l'IFSI de Lille ? »*
  - IFSI Lille présent dans fiches retrieved (cf Q5 Item 4) MAIS détails ultra-précis (admis 2026 + nom directeur) absent → ignorance forcée
- Total réponses Mistral : 44 (4 temps × 11 q)
- 4 métriques par réponse :
  - Faithfulness LLM-judge (claude-haiku-4-5, Item 3 #110)
  - Empathie LLM-judge (claude-haiku-4-5, nouveau judge_empathie.py)
  - Format compliance programmatique (regex TL;DR + 3 Plans + Question fin)
  - Ignorance class (q piège seule) : IGNORANCE_OK / INVENTION_KO / PARTIAL_FUZZY

## Tableau croisé temp × métriques

| Temp | Faith mean | Faith FIDELE/10 | Empat mean | Format % | Ignorance piège |
|---|---|---|---|---|---|
| **0.0** | 0.150 | 1/10 | 4.10 | 80.0% | PARTIAL_FUZZY |
| **0.1** | 0.220 | 2/10 | 3.80 | 82.0% | PARTIAL_FUZZY |
| **0.2** | 0.035 | 0/10 | 4.10 | 76.0% | PARTIAL_FUZZY |
| **0.3** | 0.295 | 1/10 | 3.90 | 74.0% | PARTIAL_FUZZY |

## Choix température optimale

**TEMP OPTIMALE RETENUE : `0.1`**

Critère composite : faithfulness mean dominant + pénalités si empathie < 3.0, format < 80%, ignorance ≠ OK.

## Détail composite par température

- temp=0.0 → composite -0.150 (faith 0.15, empat 4.1, format 80%, piège PARTIAL_FUZZY)
- temp=0.1 → composite -0.080 (faith 0.22, empat 3.8, format 82%, piège PARTIAL_FUZZY)
- temp=0.2 → composite -0.565 (faith 0.04, empat 4.1, format 76%, piège PARTIAL_FUZZY)
- temp=0.3 → composite -0.305 (faith 0.30, empat 3.9, format 74%, piège PARTIAL_FUZZY)

## Limitations

- Variance non mesurée (single-run par temp). Si scores inter-temps écart < 0.1 → différence dans le bruit, choix optimal à arbitrer sur autre critère.
- Judge Empathie sans gold standard (calibration empirique sur ce sample). Si signal très bruité (variance >1.5 inter-temps) → flag.
- Q piège single. N=1 sur ignorance class = signal binaire (OK/KO/PARTIAL). À étendre si Sprint 12+.
- Coût : ~$0.51 cumul (Mistral + 2 judges Haiku)

*Doc auto-généré par `scripts/diag_ab_temperature_sprint11_p1_1.py`. Sous-étape 2 wording v5 utilisera `temperature=0.1` fixée.*