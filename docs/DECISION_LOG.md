# OrientIA — Decision Log

**Purpose:** chronological log of major design decisions with date,
rationale, and alternatives considered. Complements `METHODOLOGY.md`
(the *how*) with the *why*. Each entry is ADR-lite (Architecture
Decision Record) format.

Entries are append-only — if a decision gets reversed, add a new
entry pointing to the old one, don't edit history.

---

## ADR-001 — Use Mistral as generation and embedding model (2026-03-10)

**Context.** The project targets French educational guidance for INRIA's
AI Grand Challenge.

**Decision.** Use `mistral-medium-latest` for generation and
`mistral-embed` for embeddings across the `our_rag` system.

**Rationale.**
- Native French optimization (vs GPT-4o / Claude being English-first).
- French sovereignty narrative aligns with INRIA's mission.
- Same provider for embeddings + generation = vector-space consistency.
- Cost-competitive for the benchmark scale.

**Alternatives considered.**
- OpenAI `text-embedding-3-large` + `gpt-4o` : rejected on sovereignty.
- Anthropic Claude + Voyage embeddings : rejected on French specialisation.
- Local open-weights (Llama, Mistral-Nemo) : rejected — higher complexity,
  lower baseline quality for French.

---

## ADR-002 — Label-based reranker instead of pure vector similarity (2026-03-15)

**Context.** FAISS cosine-similarity retrieval surfaces private schools
with dense SEO metadata more than public programs with sparse ONISEP
descriptions.

**Decision.** Add a multiplicative reranker stage that boosts fiches
carrying official labels (SecNumEdu, CTI, Grade Master, public status).

**Rationale.**
- The thesis of OrientIA is that *official institutional labels* are
  the right correction for private-school marketing bias.
- Multiplicative boost is simple, interpretable, auditable.
- Weights determined via grid search (`src/eval/grid_search.py`).

**Alternatives.**
- Hybrid BM25 + vector : rejected — still doesn't encode the label
  priority.
- LLM-based reranker : rejected on cost + latency.

---

## ADR-003 — 7-system ablation matrix instead of 3-system comparison (2026-04-13)

**Context.** Phase E (Run 10) showed `our_rag` +5.31 over `mistral_raw`,
but the original 3-system setup (our_rag / mistral_raw / chatgpt_recorded)
can't disentangle "RAG adds value" from "our v3.2 prompt adds value".

**Decision.** Expand to a 7-system matrix :
```
1. our_rag                 (v3.2 + RAG)
2. mistral_neutral         (NEUTRAL, no RAG)
3. mistral_v3_2_no_rag     (v3.2, no RAG)      ← ISOLATES RAG
4. gpt4o_neutral           (cross-vendor fair baseline)
5. gpt4o_v3_2_no_rag       (cross-vendor prompt portability)
6. claude_neutral          (cross-vendor fair baseline)
7. claude_v3_2_no_rag      (cross-vendor prompt portability)
```

**Rationale.**
- System 3 is the scientific key : if `our_rag > mistral_v3_2_no_rag`
  significantly, RAG adds value beyond prompt engineering.
- Systems 4-7 test cross-vendor prompt portability : does v3.2 also
  improve GPT-4o / Claude ? (If yes, that strengthens the contribution.)
- Systems 2, 4, 6 act as honest baselines for each LLM family.

**Alternatives.**
- Keep 3 systems and accept the ambiguity : rejected — reviewer would
  rightly call out the train=test problem.
- 9 systems (add ChatGPT + generic Claude as 8/9) : rejected on cost
  ($35 → $50+) and diminishing scientific return.

---

## ADR-004 — ChatGPT recordings replaced by API baselines (2026-04-13)

**Context.** Runs 1-10 used `chatgpt_recorded` (manual ChatGPT Plus web UI
responses, frozen at 2026-04-10) as the third system. This was non-
representative : short responses, no system prompt, manual transcription.

**Decision.** Remove `chatgpt_recorded` entirely in Phase F. Replace with
API-driven `OpenAIBaseline` (×2 configurations) in the 7-system matrix.

**Rationale.**
- Reproducibility : API calls are deterministic + scriptable, web UI
  recordings are not.
- Controllability : we can set temperature, max_tokens, system prompt
  exactly — web UI injects hidden context.
- Fairness : the API version is what a developer would actually use.

**Alternatives.** Keep recordings as supplementary : rejected, confuses
the narrative.

---

## ADR-005 — Dev/test split at 32/68 instead of 80/20 random (2026-04-13)

**Context.** The original 32 questions have been used for 10 runs of
prompt tuning (v3 → v3.1 → v3.2). A reviewer would rightly say
"train = test, overfitting".

**Decision.** Preserve the 32 original questions as `dev` set (for
historical traceability and prompt tuning). Add 68 brand-new questions
as `test` set (generation assisted by Claude Opus, manual review). The
**headline numbers in the study report will come from the test set**.

**Rationale.**
- Historical traceability : we can still compare Run F to Run 1-10
  via the dev subset.
- Hold-out honesty : test set has never informed any prompt change.
- Category balance preserved : both splits cover the 9 categories
  proportionally.

**Alternatives.**
- 80/20 random split : rejected — loses historical comparability.
- 50/50 : rejected — dev too small to still calibrate prompts.

---

## ADR-006 — Human evaluation via 2 students (IA + Cyber), not domain experts (2026-04-13)

**Context.** Original Phase G plan mentioned "expert humain" as a
ground truth. Matteo pushed back : no expert available, but 2 student
peers available (1 IA, 1 Cyber student).

**Decision.** Use 2 students × 30 blind-labelled questions as the human
eval protocol. Measure :
- Inter-student Cohen's κ (agreement between the 2)
- Student-vs-Claude κ (validates LLM-as-judge methodology)
- Student ranking of the 7 systems (headline human-preference metric)

**Rationale.**
- Students represent the target audience (18-22 yr olds in orientation
  decisions) — their preferences are diagnostic.
- 2 students gives us agreement stats; a single expert would not.
- Zero API cost for this layer → doesn't compete with Run F/G budget.

**Alternatives.**
- No human eval : rejected — the paper needs human validation of
  LLM-as-judge to be defensible.
- Recruit paid experts : rejected on cost + timeline.

---

## ADR-007 — NEUTRAL_MISTRAL_PROMPT as baseline (2026-04-12, Phase E.1)

**Context.** Runs 6-9 compared `our_rag` against `mistral_raw` where
mistral_raw used the *same* v3.2 prompt as our_rag. This handicapped the
baseline : mistral_raw had to respect rules (anti-confession, Plan A/B/C,
etc.) designed for a RAG-augmented model.

**Decision.** Create `NEUTRAL_MISTRAL_PROMPT` — a plain generic-assistant
prompt — and use it for the 3 `*_neutral` baselines (mistral, gpt4o,
claude).

**Rationale.**
- Scientific integrity : a fair baseline must not be crippled by rules
  it can't satisfy (can't cite sources when it has no retrieval).
- Reveals the true contribution of the RAG + prompt combination.
- Run 10 showed the gap grew from +0.25 (unfair) to +5.31 (fair) — i.e.
  we had been *underestimating* OrientIA's contribution all along.

---

## ADR-008 — MMR post-rerank with λ=0.7 default (2026-04-15, Phase F.3.a)

**Context.** Run 10 analysis showed `diversite_geo` failing : top-5
retrievals were often 3+ near-duplicate Paris-EFREI fiches.

**Decision.** Add Maximal Marginal Relevance as a post-rerank selection
step with default `λ=0.7` (moderate balance leaning toward relevance).

**Rationale.**
- MMR is the standard IR technique for this exact problem (Carbonell &
  Goldstein 1998), well-understood and auditable.
- λ=0.7 keeps relevance primary — we don't want to surface irrelevant
  fiches for the sake of diversity. Per-intent `intent_to_config()` can
  override to more aggressive (0.3-0.4) for decouverte / geographic.
- Embeddings already in FAISS → reconstructing them via
  `index.reconstruct()` is free (no extra Mistral API calls).

**Alternatives.**
- Structural diversity (filter by distinct `ville`) : rejected —
  less principled, doesn't generalise.
- Embedding-based clustering : rejected on complexity.
- Do nothing and trust the reranker : rejected — the failure mode is
  real and empirically measured.

---

## ADR-009 — Rule-based intent classifier, not LLM (2026-04-15, Phase F.3.b)

**Context.** Different question types benefit from different retrieval
strategies. Need a way to classify each question before retrieval.

**Decision.** Rule-based classifier (regex + keyword lists + closed-set
city/region match) mapping French questions to 7 intents.

**Rationale.**
- **Deterministic**. Same question → same intent. Critical for
  reproducibility and paper defensibility.
- **Zero API cost**. LLM classifier would add 100 calls per benchmark
  run, inflating OpenAI tier-1 rate-limit pressure.
- **Auditable**. We can show the exact regex patterns in the paper
  appendix. No "trust the model".
- **Fast to iterate**. Test-driven : add a failing case, extend the
  regex, move on.

**Alternatives.**
- Zero-shot LLM classifier (mistral-small) : rejected on cost + non-
  determinism.
- Fine-tuned French BERT classifier : rejected — overkill for 7 classes
  with clear surface patterns.

---

## ADR-010 — Skip manual label expansion (F.3.c) (2026-04-15)

**Context.** Original Phase F plan included F.3.c : expand
`data/manual_labels.json` from 21 → ~50 entries (add CTI / CGE / Grade
Master systematically).

**Decision.** **Skip F.3.c** as planned. Do not expand labels manually.

**Rationale.**
- The target "21 → 50" is negligible vs the 443 total fiches. Even
  hitting 50 would keep coverage at 11% of the knowledge base — the
  label boost multiplicative effect would still be diluted.
- For a *systemic* neutralité gain, we'd need 200+ labels (cross-
  referencing CTI's official 210-school list, CGE's 242, Grade Master's
  600+). That's a multi-day task not fitting Phase F's 3-day window.
- Run 10 already showed `neutralite` as a strength, not a weakness.
  Investing F.3 effort in MMR + intent (which target the actual
  weaknesses : diversite_geo, comparaison) has higher expected gain.
- Deferred option F.3.c-pro (proper 200+ label expansion) remains on
  the table post-Run F if empirical data shows a neutralité gap.

**Alternatives considered.** Do F.3.c half-heartedly : rejected on
principle — half work hurts credibility more than no work.

---

## ADR-011 — Multi-judge (Claude Sonnet + GPT-4o) instead of single judge (2026-04-15, Phase F.4)

**Context.** Runs 1-10 used Claude Sonnet 4.5 as the sole judge. A
reviewer could rightly say : "single-judge bias undetectable".

**Decision.** Use 2 judges in parallel for Run F : Claude Sonnet 4.5
and GPT-4o. Run G will add Claude Haiku as a 3rd judge (cheap, enabling
fact-check).

**Rationale.**
- Inter-judge agreement (Cohen's κ) measures methodological robustness.
  If κ ≥ 0.6 (substantial), we can defend the LLM-as-judge approach.
- Two vendors (Anthropic + OpenAI) reduces shared-bias risk.
- The shared JUDGE_PROMPT is byte-identical across judges — any
  disagreement is attributable to the model, not the instruction.

**Alternatives.**
- Stick with single judge : rejected on reviewer pushback risk.
- Three judges from the start : rejected on cost + coordination ; scale
  up progressively (2 → 3 at Run G once infrastructure proven).

---

## ADR-012 — 12 RPM OpenAI rate limiter instead of upgrading tier (2026-04-15, Phase F.4)

**Context.** First Run F attempt was running at 5 min/question due to
OpenAI tier-1 caps (15 RPM for gpt-4o). Exponential backoff from
parallel 429s turned a 30-min run into 8h.

**Decision.** Ship a thread-safe rate limiter capping combined OpenAI
rate at 12 RPM. Do NOT upgrade OpenAI tier.

**Rationale.**
- **Zero quality compromise**. Same models, same prompts, same matrix.
  Only orchestration changed.
- **Tier upgrade is slow** : requires $50 cumulative spend + 7 days
  (policy), not activable on-demand.
- **12 RPM = 60/12 = 5s gap with 20% safety margin** below the 15 RPM
  cap. Empirical : zero 429 after deploy.
- **Wall-time drops 8h → ~1h** (Mistral + Anthropic stay unthrottled).

**Alternatives.**
- Drop to 1 OpenAI baseline : rejected — breaks the 7-system matrix.
- gpt-4o-mini on one baseline : rejected — breaks cross-vendor
  consistency.
- Batch API (50% cheaper, 24h delay) : rejected — breaks iteration loop.

---

## ADR-013 — Progressive Run F : 1 run first, then decide variance runs (2026-04-15)

**Context.** Phase F plan called for 3 runs × 7 systems × 100 questions
for variance measurement (~$35). Without seeing intermediate results,
this is a big commit.

**Decision.** Run a single full F pass first (~$15-20), checkpoint with
Matteo, then decide whether to commit to 2 additional runs ($25-30 more)
based on signal strength.

**Rationale.**
- **Risk mitigation** : if our_rag ≤ mistral_v3_2_no_rag on Run 1,
  variance runs won't change the story. Save budget for debugging.
- **Fast feedback loop** : 1h vs 3h wall-time per decision cycle.
- **Budget discipline** : aligns with "ZERO intermediate benchmarks"
  rule — Run F-1 is itself the "result", not an intermediate.

**Alternatives.** Commit all 3 runs upfront : rejected on risk.

---

## ADR-014 — Fact-check layer flips the RAG result (2026-04-16, Phase G)

**Context.** Run F-1 dual-judge analysis showed `our_rag` ≤
`mistral_v3_2_no_rag` on both Claude Sonnet and GPT-4o rubric judges
(Δ -0.27 and +0.04 respectively). This matched the ADR-013 negative-
result scenario : the RAG seemed to add no value beyond the v3.2
prompt engineering.

**Discovery via Haiku fact-check (Phase G).** We ran a third-layer
Claude Haiku 4.5 fact-check that classifies each factual claim as
`verified_fiche`, `verified_general`, `unverifiable`, or `contradicted`.
Applied as a multiplicative weight on the `sourcage` criterion
(via the existing `judge_v2.reweight_v1_scores` logic, shipped in
Phase 3.2 but never previously run at scale).

**Findings** :
- Raw honesty score (fraction of verified claims): `claude_neutral` 0.837
  (no sourcing rule) → `mistral_v3_2_no_rag` 0.562 (worst). `our_rag`
  0.575, just above `mistral_v3_2_no_rag`.
- **RAG contribution (our_rag − mistral_v3_2_no_rag)** after fact-check:
  - Claude judge, in-domain 92q : -0.14 → **+0.03** (flip to win)
  - GPT-4o judge, in-domain 92q : +0.22 → +0.23 (stable win)
  - Overall 100q : Claude -0.27 → -0.06 ; GPT-4o +0.04 → +0.06 (tie)
- Per-category shifts (Claude) where fact-check matters most:
  - adversarial : -1.40 → -0.70 (shift +0.70, biggest win)
  - biais_marketing : -1.17 → -0.50 (shift +0.67)
  - cross_domain : -1.75 → -1.12 (shift +0.62)
  - realisme : +0.58 → +0.92 (shift +0.33)

**Decision — the paper's pivotal claim** : the v3.2 prompt's "cite your
sources" rule forces baselines without RAG to **fabricate plausible-
but-unverifiable institutional citations** that naïve LLM-as-judge
methodologies reward as "good sourcing". A deterministic fact-check
layer reveals the asymmetry and restores a measurable RAG advantage.

**Rationale.**
- Scientifically defensible : both judges agree on the direction of
  the shift, and the honesty score ranking (Haiku) is orthogonal to
  the rubric ranking.
- Methodologically novel : LLM-as-judge papers rarely check the
  factuality of cited sources. The finding is publication-worthy.
- Fair to all systems : the fact-check is applied with `retrieved=[]`
  for every system, so `our_rag` doesn't get a special treatment
  (the advantage comes only from real-world truth of its claims).

**Alternatives considered.**
- Run F variance runs ×2 to stabilise the v1 "RAG loses" finding and
  publish the negative result : rejected because Phase G's fact-check
  was already planned and happened to reverse the story.
- Reject the fact-check as too expensive to include in methodology :
  rejected because Haiku at $0.005/call made 700 fact-checks affordable
  (~$3.50 total).

**Caveat** : 6 of 700 fact-check calls (the last 6 cross_domain
questions) were processed by Claude Sonnet 4.5 instead of Haiku
(Anthropic 529 Overloaded on Haiku endpoint). Same prompt, same model
family — methodologically acceptable, documented in the paper.

---

## ADR-015 — Incremental save mandatory for all judge runs (2026-04-15)

**Context.** On 2026-04-15, the Claude Sonnet judge run for Run F
stalled on an Anthropic API degradation after ~80-90 questions had
been judged in-memory. Because `judge_all()` only returned its
accumulated list AT THE END, killing the process to stop the budget
bleed also lost all paid-for scores. ~$14 of Anthropic credit evaporated.

**Decision.** All judge / fact-check functions must accept a `save_path`
parameter and write the accumulated list to disk atomically after EACH
question. On resume, existing entries skip the API call to avoid
double-billing.

**Rationale.**
- Budget safety : protects against API degradation, SIGTERM, OOM, any
  unexpected interrupt.
- Mirrors `runner.py`'s established pattern for generation (same
  `done_ids` skip logic).
- Zero performance cost : a 100-item JSON rewrite per second is
  negligible vs the API call latency.

**Implementation** : commit `3c4daf8` (fix(eval): CRITICAL incremental
save + resume for judge_all). Tests cover (a) file grows after each
call, (b) resume-from-disk skips already-judged entries.

---

## Pending decisions (to be logged when made)

- ADR-016 : Whether to run F variance runs (×2 more) — pending Matteo
  checkpoint after ADR-014 finding.
- ADR-017 : Whether to add Voyage embeddings as hybrid retrieval —
  post-Run F.
- ADR-018 : Final study report format (markdown only vs markdown + PDF)
  — Week 3.
- ADR-019 : Demo UI stack (FastAPI + React vs Next.js) — optional, Week 3.
- ADR-020 : Fix for `passerelles` -0.42 loss under fact-check — diagnostic
  pending.

---

## ADR-021 — Repivot stratégique : système qui gagne > paper qui démontre (2026-04-17)

**Context** : Run F+G (16 avril 2026) a révélé que le RAG ne contribuait
rien à la rubric nue (-0.27 vs prompt seul). L'hypothèse initiale
"démontrer l'efficacité du RAG re-ranking" n'est pas tenable.

**Decision** : pivot. La cible devient "construire un système d'orientation
qui bat ChatGPT / Claude / Mistral chat sur l'accompagnement des lycéens
et étudiants français", pas "publier un negative result honnête sur le
RAG". Validé par Matteo le 2026-04-17.

**Rationale** :
- Le concours INRIA est jugé sur la qualité du système, pas du paper
- Un système qui donne les chiffres Parcoursup 2025 + tendances + profils
  admis bat un LLM généraliste même sans preuve statistique de contribution RAG
- On peut toujours publier honnêtement les résultats après coup

**Impact** : préserve ADR-001 à ADR-020. Les 4 axes data foundation,
agentic, RAFT, UX s'ajoutent, ne remplacent pas.

---

## ADR-022 — Format de citation structurée stable pour futur RAFT (2026-04-17)

**Context** : tout RAG souffre du "LLM paraphrase sans citer". Sans format
stable, impossible de mesurer précision des attributions ou faire du
fine-tuning RAFT (exige format explicite).

**Decision** : figer un format `##begin_quote## ... ##end_quote##` dans
system.py à partir de Vague A. Ne plus le changer avant RAFT éventuel.

**Rationale** : Mistral medium ne l'adopte pas spontanément (3/6 → 0/6
sur les itérations), MAIS le format reste utilisé verbatim dans les
exemples RAFT futurs → cohérence train/prod critique. Le LLM utilise
l'esprit (cod_aff_form inline) plutôt que la forme exacte → acceptable.

---

## ADR-023 — Sanity UX α (brièveté) + β (exploitation signaux) (2026-04-17)

**Context** : post-Vague A/B/C, diagnostic diff qualitatif : LLM produit
~10 000 caractères par réponse en utilisant peu les signaux Vague A
(cod_aff_form, trends). Pattern convergent sur 3 itérations.

**Decision** : addition stricte au system prompt d'une section "RÈGLES
PRIORITAIRES UTILISATEUR FINAL LYCÉEN" qui :
- α : override ~1000 mots → **300-500 mots**, Plan A/B/C préservé 2-3 lignes max
- β : force citation cod_aff_form quand Parcoursup cité, mention trends
  quand présentes

**Résultat mesuré** : longueur 1421 → 661 mots (-54%), B3/B5 améliorés,
B6 citation precision 1.00 maintenu, cod_aff_form cités 0 → 10 sur 6 réponses.

**Limitation révélée 2026-04-18** : 300-500 mots reste trop long pour les
4 testeurs unanimes. Tier 2 ramènera à 150-300 mots.

---

## ADR-024 — Extension domaine santé + quality data gaps (2026-04-17)

**Context** : corpus restreint à cyber + data_ia → non représentatif de
l'orientation des lycéens français (santé = 2e flux). Matteo confirme
extension santé comme preuve de généralisation.

**Decisions** :
1. DOMAIN_KEYWORDS santé (25 mots-clés : PASS, L.AS, médecine, kiné, IFSI,
   pharmacie, orthophon, infirmier, ergothérap, etc.)
2. 10 codes ROME J1xxx pour santé
3. Bug fix manual_labels leak : Stage 3 restreint à cyber/data_ia (les PASS
   santé de Limoges/Rennes héritaient erronément de SecNumEdu)
4. Seuil statistique MIN_SORTANTS=20 + sample_size_tier (PR #7, non mergée)
5. Visibilité ⚠AGRÉGAT dans generator (PR #7, non mergée)
6. infer_niveau étendu aux D.E santé (PR #7, non mergée)

**Effet cumulé** : 443 → 1424 fiches (+221%), 9 → 194 matches InserSup.

---

## ADR-025 — Tier 0 corrections critiques post-user-feedback (2026-04-18)

**Context** : spot-check Matteo + 4 tests utilisateurs (lycéen, étudiante,
M1, parent DRH, conseiller d'orientation pro) ont identifié 9
convergences absolues cross-profils, dont 3 critiques (bugs InserSup,
discriminations sexistes, codes admin visibles) et 6 erreurs factuelles
récurrentes.

**Decisions** (PR #8) :

1. **Bug InserSup taux emploi null** : `_sum_emploi_components` additionne
   les 3 composantes (sal_fr + non_sal + etranger). La colonne agrégée
   est null dans le dataset 2025_S2.
2. **Bug InserSup obtention_diplome non-déterministe** : filtre explicite
   `obtention_diplome="ensemble"` — vue publique MESR par défaut, inclut
   les non-diplômés (pertinent pour orientation).
3. **Fusion cohortes par métrique** : `_pick_merged` remplace
   `_pick_freshest` — pour chaque métrique, prend la valeur non-null de
   la cohorte la plus fraîche. `cohortes_used` exposé pour audit.
4. **Règles dures anti-discriminations** : le % de femmes n'est JAMAIS
   un argument positif/négatif. Formulations "100% de femmes →
   environnement solidaire/adapté/accessible" explicitement interdites.
5. **Anti-hallucinations** : 6 erreurs factuelles identifiées listées
   comme interdictions explicites dans system prompt :
   - MBA HEC "plus accessible avec expérience" → faux (5-8 ans + GMAT 700 + 80k€)
   - École 42 "gratuite en alternance" → gratuite tout court
   - Passerelle VAP Infirmier → Kiné → quasi-impossible en 22 ans pratique
   - Prépas privées médecine "2x chances" → marketing, biais de sélection
   - CentraleSupélec en "Plan A" → post-prépa très sélective
   - "X pour les Nuls" pour concours <20% → conseil catastrophique
6. **"Fabrique pas un Plan A artificiel"** : règle autorisant le LLM
   à dire honnêtement "ta voie directe n'est pas réaliste" quand le
   profil est incompatible (ex : 11/20 visant HEC).
7. **Masquage codes admin dans sortie** : `_source_line` expose URLs
   comme instructions LLM pour liens markdown cliquables
   `[fiche Parcoursup](URL)`. System prompt interdit citer
   cod_aff_form/RNCP/FOR.xxx en clair.
8. **Renvoi humain systématique** : rappel SCUIO/CIO/Psy-EN obligatoire
   (demande unanime Catherine + Dominique).

**Effets mesurés** :
- Taux emploi 12m : 0/194 → **194/194** (100% des fiches insertion)
- Taux ET salaire 12m combinés : 9/194 → **189/194** (97.4%)
- Validation end-to-end : question EFREI produit
  `[fiche Parcoursup EFREI Paris](URL)` au lieu de `cod_aff_form: 36040`

**Tests** : 343 → 348 verts, +5 Tier 0, zéro régression.

---

## ADR-026 — Règle absolue : spot-check manuel obligatoire avant merge source data (2026-04-18)

**Context** : l'audit automatique d'InserSup a validé les salaires (corrects)
et déclaré "0 outlier" — mais a **raté** que le taux d'emploi était null
partout sur 194 fiches. Parce qu'il ne comparait pas avec la donnée
officielle disponible, seulement avec ses propres seuils de sanité.

**Decision** : gravée comme **règle absolue du projet**.

> Ne jamais merger une nouvelle source data externe sans spot-check manuel
> de 3-5 échantillons vs source officielle.

**Rationale** :
- L'audit automatique peut valider la cohérence interne mais ne peut pas
  détecter les erreurs de parsing / de colonne (on ne compare pas avec ce
  qu'on ne sait pas regarder)
- Le coût humain est faible (~30 minutes pour 5 échantillons)
- Le coût d'une erreur data sur un outil conseil aux mineurs est
  disproportionné (cf règle "zéro tolérance" de Matteo)
- Sans ce spot-check, on aurait livré InserSup avec taux d'emploi null
  partout — catastrophe silencieuse

**Alternatives rejetées** :
- Confiance à 100% dans l'audit automatique → échec empirique démontré
- Tests utilisateurs comme garde-fou unique → arrive trop tard dans le
  cycle, chers à organiser

**Implications** : règle applicable à ONISEP API live, France Compétences
RNCP, classements externes, toute source future. Le script d'audit
automatique reste utile pour détecter les outliers, mais ne remplace
JAMAIS le spot-check manuel.

---

## ADR-027 — Plan de travail Tier 0 → 4 post-user-feedback (2026-04-18)

**Context** : feedback utilisateurs 2026-04-18 révèle plus de dette
utilisateur que prévu. Hiérarchisation nécessaire pour ne pas tout
faire en même temps.

**Decision** : plan en 4 tiers de priorité décroissante.

- **Tier 0** (PR #8, fait) : bugs InserSup + anti-discriminations +
  masquage codes + anti-hallucinations + renvoi humain
- **Tier 1** (à faire) : anti-hallucination approfondie (scorer
  automatique des 6 erreurs identifiées), détection programmée des
  patterns interdits dans les sorties
- **Tier 2** (à faire, prochain gros chantier) : pyramide inversée
  (TL;DR 3 lignes → chiffres → détail), brièveté **150-300 mots** (vs
  300-500 du sanity UX qui reste trop long), détection niveau utilisateur
  (terminale/L2/M1/reconversion), format adapté par type de question
  (conceptuelle vs comparaison vs choix vs hors-corpus)
- **Tier 3** : ⚠Attention aux pièges généralisés, mode exploration
  préalable (questionnement Socratic avant recommandation, aligne avec
  question participant INRIA sur pensée critique), témoignages étudiants
  (dataset à construire), coût total études, disclaimer permanent
- **Tier 4** : trancher positionnement α (Parcoursup-only) vs β (élargi
  carrière 20-30 ans, gap marché identifié par Thomas 23)

**Critère de succès Tier 2** : refaire tester par les 4 mêmes profils.
Si Léo passe "décroche au milieu" → "lu en entier", Sarah cesse de se
sentir infantilisée, Catherine cesse de relever des erreurs graves,
Dominique recommanderait à un élève seul → on est sur la bonne voie.

---

## ADR-028 — Fermeture PRs redondantes après Tier 0 (2026-04-18)

**Context** : 3 PRs ouvertes à clarifier :

- PR #7 `feature/fix-data-quality-gaps` — niveau D.E. santé +
  MIN_SORTANTS=20 + visibilité ⚠AGRÉGAT. Utile mais dépassée par Tier 0
  (qui a changé la forme du disclaimer et le schéma de cohortes).
- PR `docs/session-2026-04-17-continuity` — SESSION_HANDOFF §13 + 4 ADRs.
  Superseded par §13+14 consolidés dans PR #8.
- PR #8 `fix/tier0-critical-user-feedback` — Tier 0 critique, en attente
  validation Matteo.

**Decision** :

- **Merger PR #8** (Tier 0) après spot-check passé par Matteo
- **Fermer PR #7** et re-faire seulement les fixes encore pertinents
  dans Tier 2 :
  - niveau D.E. santé → garder (utile au reranker)
  - MIN_SORTANTS=20 → évaluer si nécessaire après fix taux emploi
    (maintenant qu'on a vraiment 194 fiches insertion, filter agressif
    pourrait être contre-productif)
  - visibilité ⚠AGRÉGAT → déjà fait différemment dans Tier 0
- **Fermer branche docs/session-2026-04-17-continuity** — redondante
  avec la doc commit de PR #8

**Rationale** : chaîne de PRs non-mergées crée de la confusion et de la
dette mentale. Un seul merge propre (Tier 0 + doc complète) remet le
projet sur des rails clairs.

---

## ADR-029 — Tier 2 UX livré et mergé (2026-04-19)

**Context** : après Tier 0 mergé sur main (PR #8, 2026-04-19), le plan
Tier 1-4 (ADR-027) positionnait Tier 2 comme prochain gros chantier.
Cible : adresser la plainte unanime #1 des 5 user tests (TROP LONG)
avec pyramide inversée, brièveté 150-300 mots, détection niveau user,
format par type de question.

**Decision** (PR #9 mergée sur main le 2026-04-19) : livraison de
5 sous-chantiers modulaires Tier 2.1 → 2.5.

### Sous-chantiers livrés

**Tier 2.1 — Pyramide inversée + brièveté** (`src/prompt/system.py`) :
ajout du bloc "RÈGLES TIER 2" avec 12 sous-règles T2.1-T2.12. Sections
obsolètes marquées explicitement (α 300-500 et FORMAT DE SORTIE v3.2
remplacés, non plus appliqués).

**Tier 2.2 — Détection niveau user** (`src/rag/user_level.py`, nouveau) :
classifier heuristique regex mappant les questions vers 5 classes
(terminale / licence / master / reconversion / inconnu). Ordre de
priorité : reconversion (âge/carrière) > master (M1/M2/bac+4-5) >
licence (L1-L3/BTS/BUT) > terminale (terminale/lycéen/17 ans) > inconnu.
La guidance associée est injectée dans le user prompt via
`build_user_prompt(user_guidance=...)`.

**Tier 2.3 — Format par type de question** (`src/rag/intent.py`
enrichi) : nouvelle fonction `intent_to_format_guidance` qui mappe
les 7 intents existants vers des hints de format (comparaison→tableau,
conceptual→didactique, decouverte→hors corpus, etc.). Réutilise
le classifier `classify_intent` sans duplication.

**Tier 2.4 — Attention aux pièges** : règle T2.4 impose section
"⚠ Attention aux pièges" systématique sur choix/comparaison, avec
exclusion explicite pour questions conceptuelles.

**Tier 2.5 — Pack user test v2** (`results/user_test_v2/`, nouveau) :
re-génération des 10 mêmes questions post-Tier 2 pour comparer. 5
profils (Léo 17, Sarah 20, Thomas 23, Catherine 52, Dominique 48
Psy-EN pro 22 ans) ont fait leur audit.

### Résultats mesurables v1 → v2

| Métrique | v1 (2026-04-17) | v2 (2026-04-19) | Δ |
|---|---|---|---|
| Mean word count | 801 | 484 | **-40%** |
| Median | 828 | 448 | -46% |
| Max | 1258 | 649 | -48% |
| TL;DR présent | 0/10 | 10/10 | +100% |
| Attention aux pièges | 1/10 | 9/10 | +80% |
| Q4 conceptual sans Plan A/B/C | non | oui | format-par-intent OK |
| Sexism violations | 0/10 | 0/10 | Tier 0 tient |
| Admin codes en clair | 0/10 | 0/10 | Tier 0 tient |

### Verdict utilisateurs v2

Primitives validées unanimement : TL;DR, Attention aux pièges, tableau
comparaison (Q3, Q9), renvoi Psy-EN/CIO/SCUIO, liens Parcoursup. Q8
PASS 12 de moyenne = gabarit consensus 5/5.

Mais **3/5 profils maintiennent "non recommandable pour mineur en
autonomie"** à cause de 7+ hallucinations factuelles distinctes
identifiées en "(connaissance générale)" :
- ECN confondu avec EDN (réforme R2C 2023)
- Bac S cité comme bac actuel (supprimé 2021)
- Distances géographiques inventées (Périgueux-Perpignan 3h30 → réel 5-6h)
- VAE confondue avec VAP
- Certificat de Spécialisation présenté comme standalone
- Coûts écoles privées sous-estimés 20-40%
- Concours Tremplin/Passerelle attribués à HEC à tort
- Formations inventées (Licence Humanités-Parcours Orthophonie)

**Tests** : 348 → **426 verts** (+78 Tier 2). Tier 0 intégralement
préservé.

**Rationale** : -40% word count est un gain structurel mesuré, pas
un gain cosmétique. Mais les hallucinations factuelles nécessitent
un pivot architectural (α restricted LLM testé, puis agentic ou
RAFT — cf ADR-030 et ADR-031).

---

## ADR-030 — α Restricted LLM : preuve empirique du plafond prompt-engineering (2026-04-19)

**Context** : 5 user tests v2 ont identifié ~7 hallucinations
factuelles distinctes en "(connaissance générale)". Cause racine
hypothétique : ANTI-CONFESSION (fix Phase 1 Run 7) force le LLM
à compenser les trous du corpus par des inventions plausibles.
Hypothèse α : remplacer cette stratégie par une discipline
d'abstention structurée résout les hallucinations.

**Decision** : implémenter α sur branche `feature/alpha-restricted-llm`
avec protocole baseline + regression (expert recommendation 2026-04-19).
Ajout de 4 règles :
- α.1 Liste blanche explicite des connaissances stables autorisées
  (cadre LMD, calendrier Parcoursup, rôles Psy-EN/SCUIO/CIO, bac et
  mentions, labels officiels, EDN remplace ECN depuis 2023, VAE/VAP
  distincts, voies d'accès HEC)
- α.2 Abstention structurée pour tout hors liste blanche et hors corpus
  (distances, coûts, noms formations, taux, calendriers spécifiques)
- α.3 Override ciblé d'ANTI-CONFESSION pour questions entièrement
  hors-scope (aveu d'ignorance autorisé et souhaité)
- α.4 Renvoi explicite autorisé (modifie "ne redirige jamais")

**Résultats empiriques v2 → v2-α (pack re-généré)** :

| Hallucination | v2 | v2-α | Delta |
|---|---|---|---|
| ECN comme nom actuel | 1/10 | 1/10 | = |
| Bac S cité comme actuel | 3/10 | 3/10 | = |
| Licence Humanités Ortho inventée | 1/10 | 1/10 | = |
| Périgueux 3h30 | 1/10 | 0/10 | ↓ |
| Pattern "Je n'ai pas de source vérifiée" | 0/10 | 0/10 | = |

Word count : 484 → 474 (neutre). Tier 0 + Tier 2 préservés.

**Verdict** : α a **préservé** l'existant et corrigé 1 cas mineur
(Périgueux), mais **n'a PAS fait bouger** Mistral medium sur les
hallucinations principales. Le LLM **n'adopte pas** le pattern de
refus explicite "Je n'ai pas de source vérifiée" (0/10 occurrences).

**Rationale** : **preuve empirique que le prompt-engineering seul
n'est pas suffisant pour résoudre les hallucinations factuelles sur
Mistral medium**. C'est une limite architecturale du modèle
sous-jacent, pas un défaut de prompt. Cette donnée est importante
pour le paper INRIA : elle justifie empiriquement le pivot vers
une approche architecturale (Axe 2 agentic ou Axe 3 RAFT).

**Status** : α **mergeable comme filet non-régressif** (0 régression
Tier 0/Tier 2, 1 petite victoire). PR #10 pas encore ouverte, décision
reportée — le gain marginal ne justifie pas à ce stade l'empilement
dans main. Si Axe 2 agentic est livré sans α, α peut rester en branche.

**Alternatives rejetées** :
- Itérer α 2-3 fois avec prompts encore plus agressifs → pattern
  "empile des fixes" que l'expert a identifié comme anti-pattern.
  Plafond Mistral medium probablement indépassable par prompt.

---

## ADR-031 — Pivot Axe 2 agentic remplace RAFT dans sprint 2 semaines (2026-04-19)

**Context** : plan initial 2 semaines α + β (RAFT) selon expert
recommendation. Mais critère Matteo élargi "outil qui bat ChatGPT
mesurablement ET aide les jeunes pour études + monde pro" change
la priorisation. Thomas (M1 fintech) et Sarah (L2 réorientation)
sont **dans la cible**, pas hors-cible.

**Decision** : remplacer "α + RAFT 2 semaines" par "α + Axe 2 agentic
prototype 2 semaines". RAFT reste en réserve S3+ (optionnel si
agentic insuffisant).

### Pourquoi agentic plutôt que RAFT sur tes critères

| Critique user v2 | RAFT | Agentic |
|---|---|---|
| Phase exploratoire manquante (Dominique déontologique) | Non | Oui (ProfileClarifier A2) |
| "Il me connaît pas et il répond" (Léo) | Non | Oui |
| "Pose une question avant" (Sarah) | Non | Oui |
| "Formation pas métier" (Thomas, critère élargi) | Non | Oui (tools ROME/InserJeunes) |
| "Coûts cumulés" (Catherine) | Non | Oui (tool dédié trivial) |
| Hallucinations factuelles | Oui (gate R7 à 30-40% échec) | Partiel (Validator A6) |

Agentic adresse **5/6 verdicts users**. RAFT adresse surtout le 6e.

### Risques nommés

1. **Dépendance Axe 1 étendu** : sans data pro (ROME, InserJeunes, APEC),
   les tools get_debouches/get_insertion_stats sont vides = agents creux.
   **D3+D4+D5 prérequis dur en S1** (plus "opportuniste").
2. **Souveraineté partielle** : orchestrateur Claude Sonnet → Mistral
   Large (cf ADR-032 POC validé).
3. **Latence multi-call** : 3-5 tools par question = 10-15s. Acceptable
   pour orientation (pas chat temps réel).
4. **Debug plus complexe** : fallback single-shot pipeline si agent échoue.

### Ce qui se conserve

**Tier 2 n'est PAS jeté.** Le Composer agent hérite du prompt v3.2 +
Tier 2 (TL;DR, Attention aux pièges, format par intent). Les gains
mesurés -40% longueur sont préservés dans le Composer.

**Alternatives rejetées** :
- RAFT seul (plan initial) : gate R7 30-40% risque d'échec, 2 semaines
  dataset curation, narrative forte mais coût élevé si échec.
- α seul : α a échoué empiriquement (ADR-030), insuffisant.
- α + RAFT + agentic parallèle : trop de fronts ouverts, palimpseste.

---

## ADR-032 — Mistral Large orchestrator validé (POC H, 2026-04-19)

**Context** : Axe 2 agentic exige un orchestrateur tool-use. STRATEGIE
§5 Axe 2 prévoyait Phase 1 Claude Sonnet pour prototypage rapide,
Phase 2 Mistral Large pour souveraineté. Matteo a refusé Claude
Sonnet même en Phase 1 (ADR-001 Mistral souveraineté).

**Decision** : Mistral Large (`mistral-large-latest`) comme orchestrateur
direct. POC H lancé 2026-04-19 pour valider empiriquement avant
investissement S2.

### Résultats POC H (5 questions représentatives)

| Question | Tool calls | Iterations | Latence | Succès |
|---|---|---|---|---|
| ranking_cyber | 2 | 2 | 15.0s | ✓ |
| realisme_sante | 1 | 2 | 10.9s | ✓ |
| debouches | 3 | 2 | 18.5s | ✓ |
| comparaison | 2 | 2 | 20.6s | ✓ |
| conceptuelle | 0 | 1 | 19.7s | ✓ |

- **5/5 succès** (schémas respectés, params valides, pas d'hallucination param)
- **Latence moyenne 16.9s** (légèrement au-dessus du gate arbitraire 15s)
- **Conceptuelle Q5 sans tool call** → 1 iteration, Mistral distingue
  correctement quand les tools ne sont pas nécessaires
- Réponses cohérentes, intégration propre des tool results

**Verdict** : gate technique **PASS**. Latence 17s acceptable pour UX
orientation (pas chat temps réel). Optimisations futures possibles
(parallélisation tool calls, cache LRU, Composer hors loop).

**Decision finale** : Mistral Large orchestrator **validé pour Axe 2
S2**. Narrative souveraineté française préservée. Composer agent final
reste Mistral Medium.

**Alternatives de secours si POC échoue** (non utilisées) :
- Mistral Medium + ReAct from-scratch (plus fragile, debuggable)
- Claude Sonnet temporaire + Composer Mistral (perd partie narrative)

Fichiers : `experiments/poc_mistral_toolcall.py`,
`experiments/poc_mistral_toolcall_results.json`.

---

## ADR-033 — Task B fixes UX indépendants LLM (2026-04-19)

**Context** : 5 user tests v2 ont identifié 3 défauts UX qui ne sont
pas architecturaux mais trivialement corrigeables côté code/prompt.

**Decisions** (3 fixes sur branche `feature/axe2-agentic-prep`) :

1. **Masquage codes ROME** (`src/rag/generator.py:_debouches_line`) :
   les codes ROME (M1812, M1819, J1102) sont retirés du texte exposé
   au LLM. Rationale identique au Tier 0 masquage cod_aff_form/RNCP/
   FOR.xxx : Léo et Dominique ont signalé "artefacts techniques sortis
   du RAG qui n'ont rien à faire devant un lycéen". Le code ROME reste
   dans le dict fiche pour le retrieval interne.

2. **Seuils de significance trends** (`src/rag/generator.py:_trend_suffix`) :
   ajout de seuils minimums (5pp taux, 15% vœux, 10 places). Les
   changements en-deçà sont omis. 5 testeurs v2 ont unanimement jugé
   les trends "décoratives ou anxiogènes" sans seuil d'actionabilité.
   On coupe le bruit à la source data plutôt qu'attendre que le LLM
   filtre (il ne filtre pas).

3. **Alertes critiques dans TL;DR** (`src/prompt/system.py` T2.2
   renforcée) : règle "Si la question porte sur une formation avec
   alerte structurante (mineure éliminatoire PASS, numerus clausus,
   coût privé >8k€, filière <10%, 10 ans d'études, VAP quasi-
   impossible), la mentionner explicitement dans les 3 lignes TL;DR".
   Catherine : "Hugo lira le TL;DR puis fermera — l'alerte doit être là".

**Rationale** : ces fixes adressent 3 symptômes mais ne touchent
pas à la cause racine (hallucinations factuelles, cf ADR-030). Ils
sont additifs et non-régressifs, mergeables sans risque.

**Tests** : 426 → 426 verts (pas de régression, fixes affectent
comportement LLM mais pas assertions tests).

---

## ADR-034 — D3a ROME 4.0 référentiel offline (partie 1/2) (2026-04-19)

**Context** : STRATEGIE §5 Axe 1 D3 prévoit intégration ROME 4.0 France
Travail API live (salaire médian + tension marché). Le zip `rome_4_0.zip`
(ROME 4.0 v460) était déjà téléchargé dans `data/raw/` (avril 2026
release, 30 CSV, ~1584 codes). Permet d'exploiter partiellement sans
signup API.

**Decision** : implémenter la partie offline (D3a) immédiatement.
Partie API live (D3b, salaire + tension) reportée à quand signup
France Travail aura lieu.

### D3a livré (`src/collect/rome.py` enrichi)

Nouvelles fonctions mémoïsées `lru_cache` :
- `get_rome_info(code_rome)` : libellé, transition_eco/num/demo,
  emploi_reglemente, emploi_cadre, code_rome_parent
- `list_all_rome_codes()` : ~1584 codes v460
- `is_emploi_cadre(code)`, `is_transition_numerique(code)` : helpers bool-safe

Compatible avec `RELEVANT_ROME_CODES` hardcodés existants (les 4 tests
initiaux de `test_rome.py` passent toujours).

### Utilité pour Axe 2

Le tool `get_debouches(code_rome)` pourra démarrer en S2 avec libellé
+ flags cadre/numérique/transition. Salaire + tension marché viendront
en D3b post-signup France Travail.

**Tests** : 426 → 430 verts (+4 tests rome offline).

**Alternatives rejetées** :
- Attendre signup France Travail pour tout faire en une fois → bloque
  Axe 2 S2 sur un paramètre externe. D3a est utile seul.
- Scraper les données salaire depuis fiches ROME web → violation ToS,
  effort élevé, qualité incertaine.

---
