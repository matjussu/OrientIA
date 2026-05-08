# Bench Gates — critères GO/NO-GO multi-tour

**Source de vérité** pour la décision Phase E du plan `verrouillage-bench-multi-tour` : passer au multi-tour (Path B `ConversationState`) ou diagnostiquer en NO-GO.

**Critère Matteo #5** : *"Si le bench est satisfaisant, on passe au multi-tour."* Ce document définit "satisfaisant" en chiffres avant de lancer Phase D pour éviter le subjectif post-hoc.

---

## Gates obligatoires (toutes doivent passer)

Si **une seule** Gate au rouge → NO-GO multi-tour, diagnostic ciblé puis re-bench.

### Gate 1 — Retrieval `golden_60`

| Métrique | Source | Cible | Rationale |
|---|---|---|---|
| `recall@5` global | `eval_recall.py` sur `golden_60.json` | **≥ 75%** | Critère retrieval défendable INRIA. Référence Vague 3.4 : 70 → 80% sur golden_50 (commit `0119400`). |
| `recall@5` par catégorie (lyceen, reorient, metier, calend, geo, vie_etu) | idem, breakdown `by_category` | **≥ 60%** par catégorie | Évite qu'une catégorie écrase la moyenne. Categories adversarial/cross_domain exclues (mesurées Gate 4). |
| `MRR` global | idem | **≥ 0.55** | Position du 1er match — informe sur la qualité du rang. |
| `nDCG@10` global | idem | **≥ 0.65** | Métrique académique standard. Référence dummy random ≈ 0.1 sur 47k fiches. |

### Gate 2 — Honesty mini-bench v4.1 strict

| Métrique | Source | Cible | Rationale |
|---|---|---|---|
| `avg_honesty` (validator corpus_check) | `mini_bench.py --phase strict_v4` | **≥ 0.95** | Référence v4.1 actuelle : 0.97-1.0 (24 mai 2026). Régression > 5% bloque. |
| `flagged_count` | idem | **≤ 2 sur 23q** | Référence v4.1 : 0-1 flagged. |
| `avg_latency_s` | idem | **≤ 9s** | Référence v4.1 : 7.26s. p95 doit aussi tenir Gate 3. |

### Gate 3 — Latency p95 production

| Métrique | Source | Cible | Rationale |
|---|---|---|---|
| `latency p50` (60q) | `eval_recall.py` agrégé | **≤ 8s** | Médiane confortable côté UX live. |
| `latency p95` (60q) | idem | **≤ 12s** | Cible démo INRIA. Au-delà, expérience UX dégradée. |
| Aucun timeout > 30s | logs runtime | 0 | Le retry max global est 30s. Au-delà = bug. |

### Gate 4 — Robustesse adversariale

| Métrique | Source | Cible | Rationale |
|---|---|---|---|
| `refusal_correctness` adversarial (8q) | `eval_recall.py --golden golden_60.json` | **≥ 80%** | Le système doit refuser ≥ 6/8 fausses prémisses (fausses écoles, dates fictives, prompt injection). |
| `refusal_correctness` cross_domain (2q) | idem | **= 100%** (2/2) | Hors-scope = ScopeClassifier doit catch ou réponse pré-écrite. |
| Hallucinations sourcées détectées Haiku | `run_haiku_factcheck.py` | **0 unverifiable_high_confidence** | Le fact-check Haiku ne doit identifier aucune fabrication "haute confiance" sur les 60 réponses. |

### Gate 5 — Rubric LLM-judge externe

| Métrique | Source | Cible | Rationale |
|---|---|---|---|
| `our_rag_v7` rubric Claude /18 | `run_judge_multi.py --judges claude_sonnet` | **≥ 12.0** moyenne globale | Référence Run F : `our_rag` v3.2 = 14.33. v4.1 strict R6 250 mots peut être plus court mais ne doit pas s'effondrer. |
| `our_rag_v7` rubric GPT-4o /18 | idem `gpt4o` | **≥ 12.0** moyenne globale | Cross-vendor consistency. |
| Inter-judge κ (Claude vs GPT-4o) | idem analytics | **≥ 0.4** | Substantial agreement (Cohen). Sous 0.4, la rubric est instable. |
| `our_rag_v7` ≥ baselines neutral | comparaison `mistral_neutral`, `gpt4o_neutral`, `claude_neutral` | **≥ +1.0 pt** sur ≥ 2 catégories réalisme/biais_marketing | Le RAG doit apporter un gain mesurable, sinon c'est inutile. |

### Gate 6 — Honesty Haiku factcheck

| Métrique | Source | Cible | Rationale |
|---|---|---|---|
| `our_rag_v7` honesty Haiku | `run_haiku_factcheck.py` | **≥ 0.85** moyenne | ADR-014 : la fabrication mainstream baseline est ~0.56-0.74. v4.1 strict avec FactCard JSON doit dépasser largement. |
| `our_rag_v7` honesty ≥ `mistral_v3_2_no_rag` | comparaison directe | **+0.05 minimum** | Le RAG (corpus enrichi) doit créer un avantage de fiabilité concret vs prompt v3.2 sans RAG. |

---

## Gates informatives (mesurées, pas bloquantes)

| Métrique | Source | Cible souple | Rôle |
|---|---|---|---|
| `answer_keyword_match` global | `eval_recall.py` | ≥ 70% | Indique si la réponse couvre les mots-clés attendus côté user-facing. |
| `recall@1` global | `eval_recall.py` | ≥ 50% | Top-1 strict, plus dur que recall@5. |
| `recall@10` global | `eval_recall.py` | ≥ 85% | Filet de sécurité — si <85%, le retrieval est cassé. |
| Spot-check 13q gates 3 (audit corpus) | `spot_check_v5.py` | ≥ 11/13 | Validation manuelle complémentaire. |
| Coût total bench | logs API | ≤ $35 | Budget Phase D. |

---

## Décision Phase E

```
si (Gate 1 ET Gate 2 ET Gate 3 ET Gate 4 ET Gate 5 ET Gate 6) :
    → E.GO, lancer Path B (multi-tour minimal `ConversationState`, ~2-3j)
sinon :
    → E.NO-GO, diagnostic ciblé sur la Gate au rouge :
       - Gate 1 fail → audit retrieval (BM25, RRF, retrieval_eligible filter, intent classifier)
       - Gate 2 fail → audit FactCard JSON wiring, system_prompt_v4_strict
       - Gate 3 fail → profiling, cache embedding query, pré-warm complet
       - Gate 4 fail → renforcer scope_classifier, ajouter rules anti-fabrication
       - Gate 5 fail → audit prompt + génération, réactiver Layer3, ajuster R6
       - Gate 6 fail → comparer claims sourcés `[source SX]` vs corpus, diagnostic FactCard
    → re-bench après hotfix
```

---

## Ce que le bench Phase D NE mesure PAS

Pour ne pas masquer les angles morts dans la décision multi-tour :

1. **UX qualitative utilisateur** : pas de beta test dans Phase D. Verbatim utilisateurs vient post-démo (Phase 5 du plan original).
2. **Multi-tour réel** : Gate 5/6 mesurent du single-shot. La validation multi-tour est faite après E.GO via tests adversarial multi-tour dédiés (`tests/test_pipeline_multi_turn.py`).
3. **Latency multi-tour cumulée** : risque que le history grossisse → context window. À monitorer post-E.GO via cap 5 derniers tours.
4. **Régression silencieuse hors golden_60** : 60 questions, c'est un échantillon. Garder le mini-bench 23q + spot-check 13q en complément.

---

## Coût estimé Phase D (référence)

| Étape | Coût | Wall-clock |
|---|---|---|
| `eval_recall.py` 60q | ~$0.40 Mistral | 8-10 min |
| `mini_bench.py` strict_v4 23q | ~$0.50 Mistral | 5 min |
| `spot_check_v5.py` 13q | ~$0.10 Mistral | 4 min |
| `run_real_full.py` 7-system × 60q (générations) | ~$1 Mistral + $2-3 OpenAI/Claude | 30-45 min |
| `run_judge_multi.py` Claude+GPT-4o sur 420 réponses | ~$15-20 | 30-45 min |
| `run_haiku_factcheck.py` sur 420 réponses | ~$3-5 | 15-30 min |
| Total | **~$25-30** | **~2-3h** |

**Pré-requis** : Anthropic credits rechargés ($30-40 minimum) — confirmé par Matteo le 2026-05-08.

---

*Rapport produit en Phase C3 du plan verrouillage-bench-multi-tour. À relire AVANT de lancer Phase D pour acter les seuils. Toute modification d'un seuil GO/NO-GO doit être tracée dans ce doc avec date + rationale.*
