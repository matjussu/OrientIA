# OrientIA — Assistant d'orientation INRIA AI Grand Challenge

Système RAG spécialisé pour l'orientation académique et professionnelle française. Soumission au concours INRIA AI Grand Challenge. Stack Python 3.12, Mistral (gen + embed), FAISS, Anthropic + OpenAI (judges), FastAPI.

**Statut au 2026-04-16** : Run F+G (100q × 7 systèmes × 3 juges) terminé. Pivot stratégique en cours vers la V2 (système agentic + corpus enrichi + RAFT + UX). Voir `docs/STRATEGIE_VISION_2026-04-16.md`.

---

## À lire en premier (par ordre de priorité)

1. **🔴 `docs/GOLDEN_PIPELINE_PLAN.md`** (NEW 2026-05-01) — **Plan séquencé pipeline canonical** = fusion agentic Sprint 1-4 + acquis Sprint 9-12 + Backstop B soft Sprint 11 P1.1. Direction active Sprint 12 axe 2 post-pivot stratégique 2026-05-01. Lecture obligatoire avant toute modif `src/agent/`, `src/rag/pipeline.py`, `src/eval/systems.py`.
2. **`docs/STRATEGIE_VISION_2026-04-16.md`** — vision V2 + 4 axes d'attaque + roadmap. Source de vérité stratégique.
3. **`docs/SESSION_HANDOFF.md`** — état projet à un instant T (mis à jour à chaque sprint). Source de vérité opérationnelle.
4. **`docs/DECISION_LOG.md`** — 15+ ADR (Architecture Decision Records) avec rationale. Le *pourquoi* de chaque choix.
5. **`docs/METHODOLOGY.md`** — protocole reproductible benchmark (rubric, blinding, dev/test split).
6. **`README.md`** — pitch projet (focus narrative INRIA, à actualiser avec V2).
7. **`results/run_F_robust/ANALYSIS_TRIPLE_LAYER.md`** — résultats définitifs Run F+G.

---

## Stack

- **Python** 3.12 (.venv local)
- **LLMs** : Mistral medium (génération) + mistral-embed (1024 dims), Claude Sonnet 4.5 + GPT-4o + Haiku 4.5 (judges)
- **Vector store** : FAISS IndexFlatL2 (CPU)
- **Backend** : FastAPI (Railway prêt mais non-actif Phase F)
- **Tests** : pytest 9.0.3 (231 verts au 2026-04-16)
- **Deps** : voir `requirements.lock` (reproductible) ou `requirements.txt` + `pyproject.toml`

---

## Commandes essentielles

```bash
# Setup
cd ~/projets/OrientIA
source .venv/bin/activate

# Tests
pytest tests/                              # full suite (231 attendu)
pytest tests/test_reranker.py -v           # un module
pytest -k "intent" -v                      # par mot-clé

# Vérifier configs API
python3 -c "from src.config import load_config; c = load_config(); print(f'Mistral:{bool(c.mistral_api_key)}, Anthropic:{bool(c.anthropic_api_key)}, OpenAI:{bool(c.openai_api_key)}')"

# Benchmark (CHER — uniquement avec validation Matteo)
python -m src.eval.run_real_full --out-dir results/run_X         # generation 7 systems × 100q
python -m src.eval.run_judge_multi --responses results/run_X/responses_blind.json --out-dir results/run_X
python -m src.eval.run_haiku_factcheck --responses ... --out ... # fact-check Haiku

# Inspection retrieval (FREE)
python -m src.eval.inspect_retrieval --questions data/eval_questions.json --out results/retrieval_inspection.md

# Index FAISS
python -m src.collect.merge      # rebuild data/processed/formations.json
python -m src.rag.embeddings     # rebuild data/embeddings/formations.index (~$5-10 mistral)
```

---

## Architecture

```
OrientIA/
├── src/
│   ├── collect/           # Ingestion Parcoursup, ONISEP, ROME, SecNumEdu, fuzzy merge
│   ├── rag/               # embeddings, FAISS index, retriever, reranker, MMR, intent classifier
│   ├── prompt/            # system.py = SYSTEM_PROMPT v3.2 (Phase E.2, figé)
│   ├── eval/              # judge, fact_check, runner, systems (7-matrix), rate_limit
│   ├── api/               # FastAPI (non-actif Phase F, prêt pour V2)
│   └── config.py          # load_config() depuis .env
├── data/
│   ├── raw/               # CSV/JSON sources (Parcoursup, ONISEP)
│   ├── processed/
│   │   └── formations.json    # 443 fiches (343 Parcoursup + 102 ONISEP fusionnées)
│   ├── embeddings/
│   │   └── formations.index   # FAISS 1.7 MB, 443 × 1024, gitignored
│   └── manual_labels.json     # 25 entrées AUTHORITATIVE (curé manuel)
├── docs/                  # STRATEGIE_VISION, SESSION_HANDOFF, DECISION_LOG, METHODOLOGY
├── results/               # run1_*/ ... run10_*/ + run_F_robust/ + futurs runs V2
├── tests/                 # pytest (231 verts)
└── experiments/           # notebooks exploration (non utilisés en Phase F)
```

---

## Conventions projet

### Décisions et ADR

- **Toute décision structurelle** (architecture, stack, méthodo) crée un ADR dans `docs/DECISION_LOG.md`.
- ADR append-only — ne jamais éditer une ADR passée. Si on revient sur une décision : nouvelle ADR qui pointe l'ancienne.
- Format ADR-lite : Context / Decision / Rationale / Alternatives.
- Numérotation continue (ADR-001 → ADR-015 actuels, prochains ADR-021+).

### Workflow benchmark (CRITIQUE)

1. **Zero intermediate benchmarks** : le code RAG / prompt évolue *localement* (validation par tests pytest + inspection retrieval gratuite). Aucun appel judge entre deux jalons mesurés.
2. **Dev/test split strict** : 32 dev (tuning autorisé) + 68 test hold-out (jamais utilisé pour ajuster). Headlines de papers/reports = test set.
3. **Multi-judge obligatoire** : Claude Sonnet + GPT-4o + Haiku fact-check. Inter-judge κ documenté.
4. **Blinding seed-déterministe** : `seed.txt` figé par run, mapping A-G → system stocké dans `label_mapping.json`.
5. **Incremental save mandatory** (ADR-015) : tout `judge_all` ou `fact_check_all` doit accepter `save_path` et écrire après chaque question. Resume skip les déjà-faits.
6. **Validation Matteo avant tout run > $5**. Estimation budget en début de run.

### Tests

- TDD encouragé pour nouvelles features RAG (cf F.3.a MMR, F.3.b intent classifier)
- 231 tests verts au 2026-04-16 — ne jamais merger qui les casse
- `tests/` reflète la structure de `src/`

### Git

- Branches `feature/*`, `fix/*`, `refactor/*`, `dev/*`
- Conventional commits (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`)
- Push sur main interdit (deny dans settings) — passer par `gh pr merge` après validation Matteo via Jarvis (cf pattern merge-approval CLAUDE.md parent)

---

## Fichiers protégés (load-bearing — ne pas toucher sans ADR)

| Fichier | Pourquoi |
|---|---|
| `src/prompt/system.py` (v3.2) | Résultat de 5 itérations Phase 1→C→E. +3.71 pts vs fair baseline (Claude). Modifs additives uniquement. |
| `src/eval/judge.py` (v1 rubric) | Préservé pour comparaison longitudinale Run 1 → Run F+. |
| `src/eval/runner.py` | Retry + resume + incremental save + Cloudflare 520 handling. Load-bearing pour multi-hour runs. |
| `src/rag/embeddings.py:fiche_to_text` | NE PAS inclure ROME (fait régresser, cf Run 5 ablation). À refondre proprement en Axe 1 V2. |
| `src/rag/reranker.py` (RerankConfig defaults) | Stables depuis Run 3 ablation. Boosts SecNumEdu 1.5 / CTI 1.3 / etc. |
| `data/manual_labels.json` (25 entrées) | Curé manuellement, AUTHORITATIVE. Blocklist EPITA, Epitech, Guardia, IONIS, École 42. |
| `src/eval/rate_limit.py` (12 RPM) | Calibré pour OpenAI tier-1 + 25% safety margin. Ne pas raise sans tier 2. |

---

## Variantes systèmes (7-system matrix actuelle)

| # | name | prompt | RAG | rôle |
|---|---|---|---|---|
| 1 | `our_rag` | v3.2 | yes + MMR + intent | full stack (thèse) |
| 2 | `mistral_neutral` | NEUTRAL | no | fair baseline Mistral |
| 3 | `mistral_v3_2_no_rag` | v3.2 | no | **isole le RAG** (compétiteur clé) |
| 4 | `gpt4o_neutral` | NEUTRAL | no | baseline GPT-4o |
| 5 | `gpt4o_v3_2_no_rag` | v3.2 | no | cross-vendor prompt |
| 6 | `claude_neutral` | NEUTRAL | no | baseline Claude |
| 7 | `claude_v3_2_no_rag` | v3.2 | no | cross-vendor prompt |

V2 ajoutera `our_rag_v2_data`, `our_rag_v3_agentic`, `our_rag_v4_raft`, `chatgpt_natural`, `claude_natural`, `mistral_natural` (cf STRATEGIE §6 B2).

---

## Budget API et surveillance

- **Mistral** : paid tier actif. Embeddings + chat.complete. `_call_with_retry` gère rate limits + timeouts + 5xx + Cloudflare 520.
- **Anthropic** : recharger au coup par coup. Run F+G a consommé ~$24 Claude Sonnet + ~$3 Haiku.
- **OpenAI** : tier-1 (15 RPM gpt-4o). Rate limiter `src/eval/rate_limit.py` à 12 RPM. Run F+G a consommé ~$5.
- **Total Run F+G** : ~$42 sur plan $70-90.
- **Règle** : tout run estimé > $5 demande validation Matteo (via Jarvis) avant lancement.

Voir SESSION_HANDOFF §8 pour détail budget par item.

---

## Principes directeurs (extraits STRATEGIE §10)

1. **Le système gagne, pas le paper** — toute décision se mesure à "rend-elle le produit objectivement meilleur pour un lycéen ?"
2. **Le RAG est un moyen, pas une thèse** — si une feature donne plus sans RAG, on l'implémente sans RAG.
3. **Le benchmark est un garde-fou** — mesure les progrès, pas l'objectif. Si un gain ne se voit pas dans les chiffres, soit il n'existe pas, soit le benchmark est inadéquat.
4. **Rigueur méthodologique non-négociable** — ADR continu, dev/test split, blinding, multi-judge.
5. **Souveraineté française** — Mistral + opens data publics + RAFT spécialisé. Argument INRIA fort.
6. **Données fraîches > figées** — refresh mensuel cron des opens data = avantage structurel sur LLMs natifs (cutoff janvier 2026).
7. **Étudiants réels = vérité** — tests utilisateurs > LLM-judges.
8. **Pas d'over-engineering** — 80% du gain en 20% des features. Mesurer avant de complexifier.

---

## Confidentialité

**Repo PRIVATE** : https://github.com/matjussu/OrientIA

- Ne pas partager externalement
- Pas de screenshots méthodologie internes sans go-ahead Matteo
- Pas de push vers public mirror
- Bascule public envisagée post-soumission INRIA (décision Q6 STRATEGIE §11)

---

## Reprendre une session sur OrientIA

```bash
cd ~/projets/OrientIA && source .venv/bin/activate
git log --oneline -15                       # ce qui a bougé récemment
pytest tests/ 2>&1 | tail -5                # 231 attendu
cat docs/SESSION_HANDOFF.md                 # état opérationnel
cat docs/STRATEGIE_VISION_2026-04-16.md     # vision V2 (si pas encore lu)
```

Vérifier si un sprint V2 est en cours (SESSION_HANDOFF §6) et reprendre où Claudette / Matteo s'est arrêté.
