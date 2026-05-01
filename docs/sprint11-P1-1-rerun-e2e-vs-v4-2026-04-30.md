# Sprint 11 P1.1 Phase 2 Sous-étape 3 — Verdict v5 vs v4 baseline

**Date** : 2026-04-30
**Branche** : `feat/sprint11-P1-1-strict-grounding-stats`
**Ordre Jarvis** : `2026-04-30-2150-claudette-orientia-sprint11-P1-1-strict-grounding-stats-phase1` Phase 2

## Setup bench

- Prompt v5 : Directive 1 scaffolding 2 étapes + 4 few-shots ❌→✅ + OBLIGATION majuscules + scope élargi + balises XML brouillon/reponse_finale + clause révoquée connaissance générale
- Prompt v4 baseline : Sous-étape 1 raw JSONL temp=0.1 (= prompt v4 actuel main pré-Phase 2)
- Température fixée : 0.1 (optimale Sous-étape 1)
- Questions : 11 (10 baseline Item 4 + 1 q piège)
- 4 métriques : Faithfulness (judge Item 3) + Empathie (judge nouveau) + Format compliance (regex) + Ignorance class piège

## Tableau comparatif per-question (v4 baseline → v5)

| Q | Faith v4 | Faith v5 | Δ | Empat v4 | Empat v5 | Δ | Format v4 | Format v5 | Δ |
|---|---|---|---|---|---|---|---|---|---|
| Q1 | 0.00 | 0.00 | ⚫ +0.00 | 4.0 | 4.0 | ⚫ +0.0 | 100% | 80% | 🔴 -20 |
| Q2 | 0.00 | 0.20 | 🟢 +0.20 | 3.0 | 4.0 | 🟢 +1.0 | 80% | 20% | 🔴 -60 |
| Q3 | 0.50 | 0.00 | 🔴 -0.50 | 4.0 | 4.0 | ⚫ +0.0 | 80% | 80% | ⚫ +0 |
| Q4 | 0.20 | 1.00 | 🟢 +0.80 | 4.0 | 5.0 | 🟢 +1.0 | 80% | 20% | 🔴 -60 |
| Q5 | 0.70 | 0.35 | 🔴 -0.35 | 3.0 | 3.0 | ⚫ +0.0 | 80% | 80% | ⚫ +0 |
| Q6 | 0.00 | 0.00 | ⚫ +0.00 | 4.0 | 4.0 | ⚫ +0.0 | 80% | 80% | ⚫ +0 |
| Q8 | 0.05 | 0.35 | 🟢 +0.30 | 4.0 | 4.0 | ⚫ +0.0 | 80% | 20% | 🔴 -60 |
| Q9 | 0.35 | 0.00 | 🔴 -0.35 | 4.0 | 4.0 | ⚫ +0.0 | 80% | 80% | ⚫ +0 |
| Q10 | 0.00 | 0.00 | ⚫ +0.00 | 4.0 | 5.0 | 🟢 +1.0 | 80% | 80% | ⚫ +0 |
| PIÈGE | 1.00 | 1.00 | ⚫ +0.00 | 4.0 | 4.0 | ⚫ +0.0 | 20% | 20% | ⚫ +0 |

## Stats agrégées (10 questions baseline, hors piège)

| Métrique | v4 baseline | v5 | Δ | Critère succès |
|---|---|---|---|---|
| **Faithfulness mean** | 0.200 | **0.211** | +0.011 | < 0.30 (ordre original) ET ≥ 0.30 (correction Jarvis) |
| **FIDELE/10 (score ≥ 0.5)** | 2/10 | **1/10** | -1 | ≥ 5/10 |
| **Empathie mean** | 3.78 | **4.11** | +0.33 | ≥ 3.0 |
| **Format compliance %** | 82.2% | **60.0%** | -22.2pp | > 80% |
| **Ignorance piège** | PARTIAL_FUZZY | **PARTIAL_FUZZY** | — | IGNORANCE_OK attendu |

## Verdict critères succès v3 enrichi

- Faithfulness mean v5 = **0.211**
  - Critère ordre original (« < 0.30 ») : ✅ OK
  - Critère correction Jarvis (« ≥ 0.30 ») : ❌ KO
- FIDELE/10 = **1/10** (critère ≥ 5/10) : ❌ KO
- Empathie mean = **4.11** (critère ≥ 3.0) : ✅ OK
- Format compliance = **60.0%** (critère > 80%) : ❌ KO
- Ignorance piège = **PARTIAL_FUZZY** (critère IGNORANCE_OK) : ❌ KO

### INSUFFISANT — 1/5 critères atteints

v5 atteint seulement 1/5 critères. Le scaffolding + few-shots ne suffit pas à corriger l'invention chiffres systémique Mistral medium. Escalation Sous-étape 4 backstop B obligatoire OU pivoter vers option C (citation [fiche_id]) ou modèle plus capable.

## Limitations méthodologiques

- **Single-run** v5 (pas de triple-run + IC95). Variance attendue (cf Sous-étape 1 temp=0.2 outlier).
- **Sample 10 q + 1 piège** — verdict directionnel uniquement. Étendre n>30 pour conclusions statistiquement significatives.
- **Judge Empathie sans gold standard** — calibration empirique sur 22 calls (11 v4 + 11 v5). Si variance score inter-versions <0.5, signal probable bruité.
- **Balises XML respect non mesuré rigoureusement** — le pipeline strip les balises avant retour answer, donc présence balises invisible dans answer post-strip. Vérifier via inspection log Mistral raw si besoin.
- **Q piège n=1** — signal binaire ignorance class. Étendre dans Sprint 12+.

## Coût empirique réel

- Mistral v5 : 11 q × ~$0.05 = ~$0.55
- Judge faithfulness : 11 calls × ~$0.001 = ~$0.011
- Judge empathie : 11 calls × ~$0.001 = ~$0.011
- **Total Sous-étape 3** : ~$0.57 (cumul Phase 2 ~$1.10 sur budget $1)

*Verdict auto-généré par `scripts/bench_v5_vs_v4_sprint11_p1_1.py`. PR #112 conditionnel selon critères ci-dessus.*

---

## §6 Captures qualitatives 5 sample réponses v5 (audit Matteo manuel)

Sélection diverse : 1 succès (Q4), 1 régression (Q3), 1 mixte (Q5), 1 framing inchangé (Q10), 1 piège ignorance (Q11).

### Q4 — Boursière logement (FIDELE 1.00, succès off-topic) — format 20 %

> **TL;DR**
> Ta question sur le logement étudiant abordable **n'est pas couverte par les fiches d'orientation que j'ai en contexte** (spécialisées formations). En revanche, voici 3 ressources officielles et gratuites pour t'aider rapidement [...]

→ **IGNORANCE_OK comportement parfait** : Mistral admet explicitement que les fiches ne couvrent pas le sujet. Format 20 % parce que format Plans A/B/C abandonné au profit d'orientation vers ressources externes. **C'est exactement le comportement attendu sur question off-topic corpus**.

### Q3 — Prépa MPSI burn-out (INFIDELE 0.00, régression vs v4 0.50) — format 80 %

> ### Plan A — Explorer les alternatives scientifiques
> Consulte la [fiche ONISEP sur les réorientations après une prépa scientifique](https://www.onisep.fr/http/redirection/formation/slug/FOR.10115) [...]

→ **Régression** : v4 baseline temp=0.1 avait faith 0.50, v5 chute à 0.00. URL ONISEP `FOR.10115` inventée + recommendations spécifiques inventées. Le scaffolding 2 étapes n'a PAS empêché l'invention de fact factual avec source falsifiée.

### Q5 — PASS hallu IFSI (INFIDELE 0.35, vs v4 0.70 régression) — format 80 %

> **TL;DR**
> 1. Les fiches que j'ai en contexte **ne couvrent ni les formations en kinésithérapie ni celles en soins infirmiers (IFSI)**, ni les passerelles après un échec en PASS.
> [...]
> ### Plan A — Réaliste : Contacter les sources officielles
> - **Pour infirmière** : Les **IFSI** recrutent **sur dossier via Parcoursup (plus de concours depuis 2019)** [...]

→ **Mix scaffolding partiellement honoré** : Mistral commence par admettre l'insuffisance des fiches (✓), puis cite quand même "FNEK", "L.AS Sciences pour la Santé Sorbonne code 28675" (✗). Hallu Q5 IFSI Item 4 toujours absente (✓ — Mistral dit "plus de concours depuis 2019" correctement). Régression score vs v4 0.70 explicable par citations FNEK/L.AS Sorbonne inventées.

### Q10 — Terminale L framing (INFIDELE 0.00, identique v4) — format 80 %

> **TL;DR**
> Ton bac avec des spécialités littéraires (ex : HLP, Langues) n'est pas une impasse !
> [...]
> 📍 Licence LEA (2 langues hors anglais) — Sorbonne Université (Paris)
> Pour toi : Si tu aimes les langues et un domaine appliqué (économie, droit, tourisme), c'est un bon compromis. **Sélectivité modérée (42 % d'admis en 2025), mais attention : 87 % de femmes et salaire médian à 1 790€/mois après le master (source : InserSup DEPP, Sorbonne)** [...]

→ **MÊMES hallu chiffrées Item 4 reproduits exactement** : 42 %, 87 % femmes, 1 790€/mois, source InserSup DEPP. Scaffolding totalement ignoré sur cette question. **Slight progress framing acceptance** : Mistral ne dit plus "tu es en terminale L", mais reformule "Ton bac avec des spécialités littéraires (ex : HLP, Langues)" — gain marginal sur la fausse prémisse implicite.

### Q11 — Piège IFSI Lille admis 2026 + directeur (FIDELE 1.00, IGNORANCE PARFAITE) — format 20 %

> **TL;DR**
> 1. **Je n'ai pas d'information sur l'IFSI de Lille (admis 2026, directeur) dans les sources officielles fournies.**
> 2. Les données sur les IFSI ne sont pas couvertes par les fiches disponibles ici.
> 3. Pour des réponses précises, consulte le site de l'IFSI de Lille ou un conseiller d'orientation (CIO/ONISEP).

→ **IGNORANCE PARFAITE — succès majeur du scaffolding sur ce cas**. Mistral admet explicitement, suggère alternative officielle, ne reformule pas en faisant des Plans inventés.

⚠️ **Bug classifier transparent** : `classify_piege_response()` a retourné PARTIAL_FUZZY (donc compté KO sur critère ignorance). Le regex pattern `je n'ai pas (cette|ces|l')\s*information` ne matche PAS "Je n'ai pas **d'**information" (cas réel ici). **Si on corrige le pattern → IGNORANCE_OK = critère ignorance OK passé**. Note honnête pour Sprint 11 P2 capitalisation `feedback_pr_patterns.md` : regex ignorance à étendre.

---

## §7 Reco honnête Claudette (cf process Matteo arbitrage manuel)

### Diagnostic v5

**v5 atteint 1/5 critères stricts**. Mais lecture nuancée des sample révèle un pattern important :

- ✅ **v5 fonctionne sur questions OFF-TOPIC corpus** (Q4 boursière, Q11 piège) : Mistral admet ignorance, ne fait plus d'invention. Scaffolding 2 étapes effectif sur ces cas.
- ❌ **v5 échoue sur questions ON-TOPIC partielles** (Q3, Q10) : Mistral continue à inventer chiffres/écoles, comme si le scaffolding était shadow-banned par sa fluidité conversationnelle. Q10 reproduit EXACTEMENT les hallu Item 4 (42 %, 87 % femmes, 1 790€).
- ⚠️ **v5 dégrade le format compliance** (-22pp) probablement à cause des balises XML brouillon qui détournent Mistral du pattern Plans A/B/C habituel.

### Reco escalation Sous-étape 4 backstop B : OUI mais avec investigation préalable

**Ne pas merge v5 tel quel** : régression mesurable sur FIDELE/10 (1 vs 2 v4) et format compliance (60 % vs 82 %).

**Hypothèses correctives à tester AVANT escalation B** (effort marginal, mesurable) :
- **v5b** : retirer les balises XML brouillon (instruction prompt mais sans `<brouillon>`/`<reponse_finale>`). Garder scaffolding 2 étapes + few-shots + OBLIGATION majuscules + scope élargi. Hypothèse : les balises XML perturbent le format Plans A/B/C de Mistral medium. Test rapide : 1 nouveau bench v5b vs v5 vs v4 sur 11 q (~$0.51, 15-20 min).
- Si v5b améliore format SANS perdre IGNORANCE benefit → ship v5b en remplacement v4
- Si v5b ne change rien → escalation B confirmée nécessaire

**Reco si Matteo veut aller direct B** : OK mais on perd l'opportunité d'isoler la cause format dégradé (probablement les balises XML).

### Pattern méta capturé pour Sprint 11 P2

**Mistral medium a un plafond capacitaire** sur les contraintes complexes en system prompt. v5 prompt prefix est passé de 887 à ~1010 lignes (+14 % lignes prompt). Hypothèse : "lost in the middle" sur prompt long (cf cross-check Q3 audit externe Jarvis). À documenter pour Sprint 11 P1.3 ou Sprint 12+ ablation prefix vs body.

### Capitalisation immédiate

- **Bug regex classifier ignorance** (`classify_piege_response`) : le pattern manque "d'information" (cas réel observé). À étendre dans `feedback_pr_patterns.md` post-merge ou à corriger directement dans le script si un re-bench est lancé.
- **Pattern OFF-TOPIC vs ON-TOPIC scaffolding** : le scaffolding n'est pas binaire (marche / marche pas). Il dépend de la disponibilité des fiches. À noter dans `feedback_discipline_velocite.md` ou nouveau `feedback_prompt_engineering.md`.

---

## §8 Données tronquées / erreurs

- **Q7 timeout Mistral** (read operation timed out après ~120s) — pas de data v5 Q7. Le bench A/B Sous-étape 1 avait Q7 valide avec faith 0.0 INFIDELE temp=0.1. Aggregation sur 9 q valides (vs 10 prévu).
- **Q11 PIEGE IGNORANCE_OK comportement réel mais classifier KO** (cf §6 Q11 + §7 capitalisation).

---

*Doc verdict + sample qualitatif + reco honnête. Standby arbitrage Matteo via Jarvis sur escalation B (option principale) vs v5b investigation (option intermédiaire) vs autre.*