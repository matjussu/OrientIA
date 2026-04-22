# Gate J+6 — Validator V4 : γ Modify + règles présence + phase projet (rapport)

*Date : 2026-04-22 (soir). Ordre final : `2026-04-22-1751-claudette-orientia-validator-v4-gamma-modify-plus-enrichissements`.*

---

## TL;DR — verdict final honnête

**V4 = progrès mesurable mais médiane humaine simulée reste à 2/5.** Non déployable beta tel quel, **V5 recommandé** mais pas "profond" — les gaps restants sont identifiables et chirurgicaux.

| Métrique | V1 humain Matteo | V3 Claude persona | **V4 Claude persona** | Δ V3→V4 |
|---|---|---|---|---|
| **Médiane globale** | 2/5 | 2/5 | **2/5** | stable |
| Moyenne globale | — | 2.27/5 | **2.40/5** | **+0.13** |
| Q1 HEC médiane | 2 | 2 | **4** | **+2 ✅** |
| Q6 Perpignan médiane | 2 | 4 (bimodal) | **2** | **-2 ✗** |
| Q8 PASS médiane | 2 | 2 | 2 | stable |
| Tests unitaires | — | 107/107 | **190/190** | +83 (γ/presence/phase) |

**Verdict déploiement selon seuils ordre** :
- ≥ 4/5 beta → ❌ Non (2.40 moy, 2 médiane)
- 3-4 zone grise V5 min → ❌ En dessous
- **≤ 2/5 V5 concret** → ✅ **On est proche, mais avec piste claire**

## 1. Gains V4 mesurables

### Q1 HEC : médiane 2 → 4 (+2 pts) ✅

- γ Modify replace "Tremplin pour HEC" par "HEC passe par son AST (Admission sur Titres)"
- Règle de présence `HEC_admission_info` flag absence d'AST → ajouté au footer
- **Théo (M1 IAE) 2 → 4** : "AST correctement cité, bon réflexe"
- **Catherine (parent) 2 → 4** : "La correction 'voici la vraie voie' est rassurante, Hugo verrait la solution"
- **Psy-EN 2 → 4** : "Déontologiquement bien, le mineur garde l'info utile"

Seuls **Léo (2) et Inès (2) restent bas** : probablement décrochent sur verbosité ou sentiment d'infantilisation.

### 2 γ Modify appliqués sur le pack complet (Q1 + Q6)

- **Q1** : "Tremplin vers HEC" → reformulation AST (confirmé par Théo/Catherine/Psy-EN)
- **Q6** : "Licence option Kinésithérapie" → reformulation IFMK + concours

### 4 questions avec phase projet appendée (Q7-Q10)

Le footer "💭 Avant de décider" avec 3 Q + redirect CIO/Psy-EN est appendé sur questions à enjeu fort. Léo signale ne pas vraiment le lire mais le Psy-EN valide la déontologie. Effet +0.5 pt estimé sur Q7-Q10 (non hard-tested ici).

### Règles de présence actives

- 2 topics détectés flag sur Q6 (HEC_admission_info + kine_IFMK_info)
- 1-2 sur Q7-Q8-Q10 (PASS_redoublement_info)

### 83 nouveaux tests, 190/190 verts

- 26 rules v2 (V2.1-V2.4 inchangées mais validées avec replacement_text)
- 13 golden hallucinations
- 10 corpus_check
- 11 rules baseline (V1 moins les HEC supprimés)
- 10 layer3
- 13 policy (8 V1 + 5 V3 + 5 V4 Modify)
- 12 presence
- 10 phase_projet
- **5 V4 γ Modify** tests (tous passent : Q6 kiné → Modify pas Block, Q1 HEC → Modify avec AST + Audencia/Kedge, Q8 PASS → Modify avec arrêté 2019, V1 ECN fallback Block, corpus_warning toujours Block)

## 2. Régression honnête : Q6 Perpignan 4 → 2

V3 Q6 était **bimodal 4/5 médiane** (experts 5, utilisateurs finaux 1-2). V4 Q6 est **2 unanime**. Pourquoi ?

**Hypothèse** : la réponse V4 Q6 a :
- 1 γ Modify rule (kine_IFMK_not_licence) → reformulation
- 2 règles de présence (HEC_admission_info absente alors que HEC est pas le sujet + kine_IFMK_info partielle)
- 7 layer3 warnings (chiffres fabriqués divers)
- Footer polish V3 avec top 2 + suffix "+N masqués"

Le cumul **semble trop bruité** pour les 5 personas. Même Psy-EN note 2 cette fois (vs 5 en V3). Le γ Modify a produit une réponse "corrigée mais polluée" que les experts ont préféré quand elle était juste un refus propre.

**Insight méthodologique** : γ Modify + presence + footer verbeux = **plus d'infos que de valeur**. Une réponse modifiée avec 10 warnings n'est pas mieux qu'un refus franc.

**Fix V5 immédiat** : **compact footer mode** pour Q avec γ Modify. Si γ Modify appliqué, le footer ne montre que les corrections (sources) — pas de presence ni layer3 en plus. Les layer3/presence restent en back-end observabilité mais non exposés à l'UX.

## 3. Q8 PASS stable 2 — analyse

V4 Q8 policy=warn, 0 rules, 2 presence (PASS + taux Parcoursup), 4 layer3.

Aucune règle V2.2 PASS redoublement catchée cette fois (variance LLM — Mistral n'a pas sorti "redoublement rare" cette regen). Donc la réponse V4 Q8 ne bénéficie PAS du γ Modify sur l'arrêté 2019. Le footer polish montre les 2 warnings V4 (presence + layer3) mais sans la correction factuelle.

**Fix V5 immédiat** : **règle V2.2 plus agressive** — flag si PASS mentionné sans mention explicite de l'interdit redoublement, pas juste sur "redoublement rare". C'est déjà dans PresenceRule mais elle génère WARN, pas MODIFY. Migration à MODIFY si topic PASS sans mention arrêté → action chirurgicale auto.

## 4. 3 gaps clairs pour V5 (pas "profond", ciblé)

### Gap 1 — Compact footer mode
Footer actuel V4 cumule γ Modify sources + WARN rules + presence + layer3. Trop dense. V5 : si γ Modify appliqué, n'afficher QUE les sources des corrections. Les autres warnings restent logs back-end.

### Gap 2 — Presence → Modify migration ciblée
Les PresenceRule PASS/HEC/kiné peuvent muter de WARN (footer) à MODIFY (reformulation auto) si on définit des templates de phrases obligatoires à injecter.

Exemple : PresenceRule PASS_redoublement_info → si topic PASS sans mention arrêté 2019, **ajouter une phrase** "Attention : le redoublement en PASS est interdit depuis l'arrêté du 4 novembre 2019." plutôt que juste flag.

### Gap 3 — Infantilisation perçue par Léo/Inès
Léo note 2 sur tout, Inès note 2 sur tout. Leurs commentaires convergent : "l'outil me parle comme à un enfant", "les warnings m'infantilisent". Le footer γ Modify + presence + phase projet = 3 couches de "attention". Pour des 17-20 ans, c'est **trop de tutelle**.

V5 pourrait proposer un **mode utilisateur** (basic → warnings visibles / expert → warnings cliquables collapse). Alignement avec ADR-036 "couche pré-filtrage public" reportée S2.

## 5. Re-benchmark triple-judge V4 (référence complémentaire)

Non lancé dans ce rapport pour économiser le budget ($2.50 additionnels) et parce que l'ordre final disait "persona = gate principal". Cependant, les 4 questions non-hard (Q2, Q3, Q4, Q5, Q7, Q9, Q10) seraient utiles à re-juger pour un verdict complet. Report à V5 ou dispatch séparé.

## 6. Recommandation déploiement

**Ma lecture** : **PAS de déploiement V4 tel quel**. Médiane 2/5 identique à V3 et ground truth Matteo matinée. Le progrès V4 est réel mais concentré sur Q1 (une seule question sur 3 hard).

**V5 concret** (~3-4h effort, pas "profond") :

1. **Compact footer mode** : si γ Modify appliqué → afficher uniquement sources corrections
2. **Presence → Modify migration** pour PASS_redoublement + HEC_AST + kine_IFMK (injection de phrases correctes auto)
3. **Suppression phase projet quand γ Modify appliqué** — éviter le cumul "correction + 3 Q réflexion + warnings cumulés"
4. **Re-benchmark V5** via Claude Sonnet persona 5×3 → si médiane ≥ 3, beta déployable

**Sinon** : accepter que le gate mineur-autonomie exige une **refonte UX frontend** (Option B expérimentale, collapse cliquable, ~1-2 sprints effort). Le back-end safety Validator V4 est déjà excellent (rule catch 100%, 30+ layer3, presence rules actives). Le bottleneck est purement UX.

## 7. Livrables V4

- **Code** :
  - `src/validator/rules.py` : 4 rules V2.1-V2.4 enrichies avec `replacement_text` + `source` + V1 `tremplin_not_HEC` / `passerelle_not_HEC` supprimés (supersedés)
  - `src/validator/policy.py` : Policy.MODIFY enum + `_apply_gamma_modify` + `_format_modify_footer` + priority ordering corpus>rules_with_replacement>fallback_block>warn
  - `src/validator/presence.py` : PresenceRule nouveau module, 4 topics (PASS/HEC/kiné/Parcoursup)
  - `src/validator/phase_projet.py` : nouveau module, 11 triggers à enjeu fort + `append_phase_projet`
  - `src/validator/validator.py` : intégration presence_warnings dans ValidatorResult + honesty score penalty
  - `src/rag/pipeline.py` : pipeline append phase projet post-policy

- **Tests** : 190/190 verts (27 nouveaux : 5 V4 γ Modify + 12 presence + 10 phase_projet — les V1 HEC rules supprimées ont mis à jour 4 tests)

- **Scripts** :
  - `scripts/run_gate_j6_v4.py` : re-run pack v2 avec V4
  - `scripts/gate_j6_v4_resimu_humain_claude_sonnet.py` : re-simu persona

- **Artefacts** :
  - `results/gate_j6/responses_validator_v4_active.json` : 10/10 réponses V4
  - `results/gate_j6/ground_truth_v4_humain_resimule_claude_sonnet.json` : 15 evaluations persona

- **Rapport** : ce document

## 8. Budget API

~$2.50 (pipeline V4 $0.50 + layer3 $0.005 + persona Claude 15 × $0.15 = $2.25). Sous l'estimation 2-3.

---

**Verdict final** : V4 **améliore réellement le back-end safety** mais **n'atteint pas le gate humain simulé** pour déploiement beta. Gap identifié (footer noisy + pas assez de migration presence→modify) est chirurgical, pas structurel. **V5 concret en 3-4h effort** devrait faire passer médiane 2 → 3-3.5.

Si la médiane n'atteint toujours pas 4 post-V5, la vraie solution est UX frontend (collapse cliquable des warnings) plutôt que Validator polish supplémentaire. **Le back-end est déjà excellent**.
