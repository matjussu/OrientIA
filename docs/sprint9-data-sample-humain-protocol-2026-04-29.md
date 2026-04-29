# Sample humain — Protocole d'évaluation Q&A OrientIA (workflow 2 phases)

> **Statut au 29/04 07:10 CEST** : Phase 1 active (Matteo review direct sur les 45 Q&A keep+flag de la nuit 1). Phase 2 lancera après la nuit 2 drops-only ce soir, avec couverture des 6 catégories non couvertes par la nuit 1.

> Doc miroir du protocole tenu dans le vault Obsidian Jarvis (`01-Projets/Actifs/OrientIA-Sample-Humain-2026-04-29.md`). Maintenu sur GitHub pour accès Matteo en mobilité.

---

## ⚠️ Constat structurel important — Couverture nuit 1

La nuit 1 (28-29/04) a été partiellement échouée à cause d'un bug stop condition propagation (fixé ce matin commit `548834a`). Sur les 1020 jobs prévus, seuls **45 Q&A keep+flag** sont utilisables. Et toutes proviennent de **3 prompts dans 1 seule catégorie** :

| Catégorie YAML | Couverture nuit 1 |
|---|---|
| `lyceen_post_bac` (A1 + A2 + A3) | ✅ 45 / 600 jobs prévus = 7.5% |
| `etudiant_reorientation` (B*) | ❌ 0 / 600 |
| `actif_jeune` (C*) | ❌ 0 / 420 |
| `master_debouches` (D*) | ❌ 0 / 480 |
| `famille_social` (E*) | ❌ 0 / 480 |
| `meta_question` (F*) | ❌ 0 / 360 |
| `profil_non_cadre` (G*) | ❌ 0 / 180 |

**Conséquence** : on ne peut pas valider la couverture cross-catégorie avec ce sample. Mais on peut :
1. Calibrer les frontières keep/flag/drop dans 1 catégorie
2. Identifier les patterns d'hallucination (axe le plus faible : 19.7/25)
3. Ajuster les prompts v3 avant la nuit 2 si nécessaire

La nuit 2 drops-only ce soir (parallel=2, post-fix bug) couvrira les 6 catégories non couvertes → input pour Phase 2.

---

## 🎯 Workflow 2 phases

### Phase 1 — Review direct Matteo (aujourd'hui matinée)

**Pourquoi seulement Matteo en phase 1** :
- Couverture monotypique 1/7 → κ Fleiss à 3 évaluateurs peu informatif sur 1 catégorie
- Matteo le mieux placé pour caler les prompts (vision projet + connaissance YAML 51 prompts)
- Disponibilité Ella + Deo pas garantie immédiate
- Calibrage rapide → ajustement avant nuit 2 ce soir 23h

**Output Phase 1** :
- Verdict par Q&A (keep / correctible / drop) — divergence éventuelle vs scoring auto
- Patterns récurrents identifiés (force / faiblesse / cas limites)
- **Ajustements prompts v3 → v3.1** si nécessaire avant nuit 2

### Phase 2 — Sample humain 3 évaluateurs (post-nuit 2)

**Quand** : matinée 30/04 ou journée selon livraison nuit 2 propre

**Pourquoi 3 évaluateurs** : κ Fleiss inter-rater agreement informatif sur les 6 catégories nouvellement couvertes + redondance pour réduire biais individuel.

**Sample target** : 100-150 Q&A stratifiées par catégorie.

---

## 📐 Grille critères HEART adaptée orientation

> Échelle 1-5 systématique (1 = très mauvais, 3 = acceptable, 5 = excellent). Ne pas hésiter à donner des 1 ou 5 — la dispersion est un signal utile.

### H — Happiness (ton & empathie)
Le ton est-il chaleureux, accueillant, sans jugement ? Le jeune se sent-il accueilli ou interrogé ?
- 1 : froid / corporate / professoral
- 3 : neutre / poli / sans chaleur particulière
- 5 : chaleureux / empathique / humain — donne envie de continuer

### E — Engagement (relance conversationnelle)
La réponse pose-t-elle une question retour ? Invite-t-elle à approfondir ? Donne-t-elle envie de répondre ?
- 1 : réponse plate / monologue / pas de relance
- 3 : 1 question retour générique
- 5 : question retour ciblée + invitation contextuelle naturelle

### A — Adoption (lisibilité 17-25 mobile)
Un jeune lit-il ça en entier sur son téléphone ? Format ? Verbosité ?
- 1 : pavé indigeste / 500+ mots / jargon non expliqué
- 3 : un peu long mais lisible / quelques bullets
- 5 : 250-350 mots / aéré / vocabulaire accessible

### R — Retention (positionnement conseiller longue durée)
La réponse fait-elle ressortir le côté "conseiller qui te suit" plutôt que "ChatGPT one-shot anonyme" ?
- 1 : aucun signal compagnon / pourrait sortir de n'importe quel chatbot
- 3 : reprend 1-2 éléments du profil mais reste générique
- 5 : reprend explicitement le contexte persona + propose suivi concret

### T — Task success (factualité & pertinence)
Les chiffres sont-ils sourcés ? Les liens existent-ils ? La réponse répond-elle à la question posée ?
- 1 : hallucination flagrante (chiffres inventés, lien mort, hors-sujet)
- 3 : factuellement OK mais sources floues ou pertinence partielle
- 5 : 0 chiffre non sourcé, sources réelles vérifiables, pertinence directe

---

## 🔍 Recommandations Claudette intégrées (5 reco extract MD nuit 1)

1. **Focus axe `hallucination`** (19.7/25 = axe le plus faible) — vérifier chaque chiffre cité, chaque URL référencée, chaque nom propre formation/école. Les 9 flags ont tous hallucination en axe minimum (range 15-19/25).
2. **Comparer keep score 85 vs 89** — y a-t-il une vraie différence qualitative entre la borne basse keep et le haut du panier ?
3. **Comparer flag 70 vs 84** — la frontière 84/85 est-elle bien calibrée ? Faut-il décaler boundary keep à 87 ou 90 ?
4. **Couvrir au moins 1 cas par seed_idx unique** dans A1, A2, A3 — vérifier pas de bias seed (toujours mêmes patterns selon seed).
5. **Cross-check les 9 flags en priorité** — décider si keep (remontée frontière) / drop (mauvaise qualité réelle) / re-run (bug isolé non-stop-condition).

---

## 📊 Phase 1 — Review direct Matteo

**Source des 45 Q&A** : [`docs/sprint9-data-nuit1-samples-2026-04-29.md`](https://github.com/matjussu/OrientIA/blob/feat/sprint9-data-pipeline-agentique/docs/sprint9-data-nuit1-samples-2026-04-29.md) (200 KB, format v3 lisible : Question → Réponse → Sources → Critique scores → Corrections → Décision).

**Workflow proposé** :
1. Matteo ouvre le doc et review en lecture continue
2. Pour chaque Q&A "intéressante" (keep haut score, flag ambigu, ou pattern surprenant) → note rapide dans la grille ci-dessous
3. Ne pas noter les 45 systématiquement — focus sur cas instructifs (pattern flag, score borderline, hallucination détectée à l'œil)
4. À la fin → synthèse rapide avec Jarvis pour ajustement prompts v3 → v3.1

### Grille de notes rapides Matteo

| # | prompt_id | iter | score auto | verdict humain | pattern observé / hallucination détectée |
|---|---|---|---|---|---|
| _ | _ | _ | _ | keep / correctible / drop | _ |

(Ajouter lignes au fil de la review)

### Synthèse Phase 1 (à remplir après review Matteo)

- **Patterns récurrents identifiés** :
  - Forces : _
  - Faiblesses : _
  - Cas limites : _

- **Ajustements prompts v3 → v3.1 proposés** :
  - [ ] _
  - [ ] _

- **Décision frontières keep/flag/drop** :
  - Garder 85 / 70 / 0 ? Ou décaler ?

- **Décision nuit 2** :
  - Lancer telle quelle avec v3 ? Ou attendre v3.1 ?

---

## 📊 Phase 2 — Sample humain 3 évaluateurs (post-nuit 2)

### Calcul taille échantillon

Si nuit 2 livre ~150-200 Q&A propres sur 6 catégories :
- Sample stratifié 15-20 Q&A par catégorie = 90-120 Q&A
- 3 évaluateurs × 6 catégories × ~17 Q&A = 306 évaluations
- Temps estimé par évaluateur : ~5 min × 17 Q&A × 6 catégories = ~8h30 réparti sur 2-3 jours

### Inter-rater agreement (κ Fleiss)

> **κ Fleiss** = mesure de la concordance entre N évaluateurs (N≥2) sur des décisions catégorielles (ici verdict keep/correctible/drop par Q&A).
>
> **Formule** : κ = (P̄ − P̄ₑ) / (1 − P̄ₑ) où P̄ est l'accord observé moyen et P̄ₑ l'accord attendu par chance.
>
> **Interprétation Landis & Koch** :
> - κ < 0.20 : accord faible (signaux fragiles)
> - 0.20-0.40 : accord léger
> - 0.40-0.60 : accord modéré
> - 0.60-0.80 : accord substantiel ✅ **seuil minimum recherche**
> - 0.80-1.00 : accord quasi-parfait

**Procédure** :
- Calculer κ Fleiss après que les 3 évaluateurs ont rempli leurs grilles (script Python rapide ou Excel)
- Si κ ≥ 0.60 → conclusions valides, peuvent être citées dans dossier INRIA
- Si κ < 0.60 → identifier sur quels Q&A les divergences se concentrent + renforcer le brief évaluateurs / clarifier la grille HEART

### Grille d'évaluation Q&A (template phase 2 — à dupliquer × N)

```
### Q&A #N — [prompt_id::seed_idx::category]

**Question** :
> <question complète>

**Réponse** :
> <réponse complète>

**Sources citées** :
- <source 1>

#### 🟢 Évaluation Matteo
| Critère | Note | Commentaire |
|---|---|---|
| H — Happiness | _ | _ |
| E — Engagement | _ | _ |
| A — Adoption | _ | _ |
| R — Retention | _ | _ |
| T — Task success | _ | _ |
| **Verdict** | | keep / correctible / drop |

#### 🟡 Évaluation Ella
| Critère | Note | Commentaire |
|---|---|---|
| ... même grille |

#### 🟠 Évaluation Deo
| Critère | Note | Commentaire |
|---|---|---|
| ... même grille |
```

---

## 📈 Note méthodologique — Test Mistral inférence Sprint 10

> Important : **les 1000 Q&A Golden sont générées par Claude Opus 4.7** (offline, pour qualité). **Le serving final cible est Mistral** (pivot D5 ADR souveraineté FR). Si Mistral en inférence dégrade au passage, le travail Sprint 9 perd en valeur.
>
> **Ajout au backlog Sprint 10** : test empirique Mistral inférence sur un échantillon de 20-30 questions sample du test_set_v3, comparer qualité vs Claude. Si gap >10pp sur axes HEART → réviser stratégie (fine-tuning Mistral spécialisé orientation ? prompt engineering pour Mistral ? ou cap inférence Claude API ?).

---

## 🔗 Liens

- Source 45 Q&A nuit 1 : [`docs/sprint9-data-nuit1-samples-2026-04-29.md`](https://github.com/matjussu/OrientIA/blob/feat/sprint9-data-pipeline-agentique/docs/sprint9-data-nuit1-samples-2026-04-29.md)
- ADR pivot OrientIA : `08-Decisions/2026-04-28-orientia-pivot-pipeline-agentique-claude.md` (vault Obsidian)
- Repo : `~/projets/OrientIA/`

---

*Doc miroir GitHub du protocole sample humain 2 phases. Source de vérité = vault Obsidian côté Jarvis. Mis à jour côté GitHub pour accès Matteo en mobilité.*
