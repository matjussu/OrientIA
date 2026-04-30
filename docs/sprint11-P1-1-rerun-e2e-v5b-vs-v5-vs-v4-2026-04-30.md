# Sprint 11 P1.1 Sous-étape 4 — Verdict v5b vs v5 vs v4 baseline

**Date** : 2026-05-01
**Branche** : `feat/sprint11-P1-1-strict-grounding-stats` (PR #112)
**Ordre Jarvis** : `2026-05-01-0000-claudette-orientia-sprint11-P1-1-substep-4-v5b-investigation`

## §1 Setup et changements v5b vs v5

**v5b = v5 - balises XML brouillon** :
- ✅ GARDÉ : scaffolding 2 étapes (vérification source / reformulation qualitative)
- ✅ GARDÉ : 4 few-shots concrets ❌→✅ (IFSI / Master Droit / Salaire LEA / L.AS Sorbonne)
- ✅ GARDÉ : clause OBLIGATION en MAJUSCULES
- ✅ GARDÉ : scope élargi tous types factuels
- ❌ RETIRÉ : section "STRUCTURE DE RÉPONSE OBLIGATOIRE — BALISES XML" (instruction `<brouillon>`/`<reponse_finale>`)
- Température fixée : **0.1** (idem v5)

**Hypothèse Matteo** : balises XML ont surchargé instruction-following Mistral medium → format Plans A/B/C sacrifié pour respecter split XML. Ablation préalable obligatoire avant escalation backstop B.

**Fixes méthodologiques Sous-étape 4.1 appliqués** :
- Regex classifier `classify_piege_response()` v2 étendu (matche "d'information", "ne sont pas couvertes par les fiches")
- Format compliance recalculé sur 8 q ON-TOPIC seulement (exclut Q4 boursière logement + Q11 piège ignorance, OFF-TOPIC corpus)
- Re-classification ignorance v4 + v5 raw avec pattern v2 pour comparaison équitable

## §2 Tableau comparatif tri-version per-question

| Q | Type | Faith v4 | Faith v5 | Faith v5b | Format v4 | Format v5 | Format v5b |
|---|---|---|---|---|---|---|---|
| Q1 | ON-TOPIC | 0.00 | 0.00 | 0.00 | 100% | 80% | 80% |
| Q2 | ON-TOPIC | 0.00 | 0.20 | 0.20 | 80% | 20% | 80% |
| Q3 | ON-TOPIC | 0.50 | 0.00 | 0.40 | 80% | 80% | 80% |
| Q4 | OFF-TOPIC | 0.20 | 1.00 | 0.05 | 80% | 20% | 80% |
| Q5 | ON-TOPIC | 0.70 | 0.35 | 0.70 | 80% | 80% | 80% |
| Q6 | ON-TOPIC | 0.00 | 0.00 | 0.00 | 80% | 80% | 80% |
| Q7 | ON-TOPIC | 0.40 | — | 0.20 | 80% | — | 80% |
| Q8 | ON-TOPIC | 0.05 | 0.35 | 0.35 | 80% | 20% | 20% |
| Q9 | ON-TOPIC | 0.35 | 0.00 | 0.20 | 80% | 80% | 80% |
| Q10 | ON-TOPIC | 0.00 | 0.00 | 0.20 | 80% | 80% | 80% |
| Q11 | PIEGE | 1.00 | 1.00 | 1.00 | 20% | 20% | 20% |

## §3 Stats agrégées tri-version (avec fixes Sous-étape 4.1)

| Métrique | v4 baseline | v5 (avec XML) | v5b (sans XML) | Critère succès |
|---|---|---|---|---|
| **Faithfulness mean** (10 q) | 0.220 | 0.211 | **0.230** | ≥ 0.30 |
| **FIDELE/10** (score ≥ 0.5) | 2/10 | 1/10 | **1/10** | ≥ 5/10 |
| **Empathie mean** (10 q) | 3.80 | 4.11 | **4.10** | ≥ 3.0 |
| **Format compliance ANCIEN** (10 q) | 82.0% | 60.0% | **74.0%** | > 80% |
| **Format compliance NOUVEAU** (8 q ON-TOPIC) | 82.2% | 65.0% | **73.3%** | > 80% |
| **Ignorance Q11 piège** (post-fix v2) | PARTIAL_FUZZY | IGNORANCE_OK | **PARTIAL_FUZZY** | IGNORANCE_OK |

**Note transparence formule format** : ancienne formule (10 q baseline hors Q11) incluait Q4 boursière logement (off-topic, fallback ressources externes correct) qui ne suit pas le pattern Plans A/B/C par nature. Nouvelle formule (8 q ON-TOPIC) exclut Q4 + Q11 pour mesurer le pattern Plans A/B/C uniquement où il s'applique.

## §4 Verdict critères succès v3 enrichi (avec NOUVELLE formule format)

- Faithfulness mean v5b = **0.230** (≥ 0.30) : ❌ KO
- FIDELE/10 = **1/10** (≥ 5/10) : ❌ KO
- Empathie mean = **4.10** (≥ 3.0) : ✅ OK
- Format compliance NOUVEAU 8 q = **73.3%** (> 80%) : ❌ KO
- Ignorance Q11 piège = **PARTIAL_FUZZY** (IGNORANCE_OK) : ❌ KO

### Score : 1/5 critères atteints

## §5 Reco honnête Claudette

**INSUFFISANT** (1/5 critères). v5b ne restaure pas significativement vs v5. Hypothèse Matteo (balises XML coupables format) **INFIRMÉE** : la cause format dégradé est ailleurs (probablement scaffolding 2 étapes ou OBLIGATION majuscules ou prompt trop long).

Recommandation : escalation backstop B obligatoire OU pivot modèle plus capable (Sonnet 4.6, souveraineté FR impactée). v5/v5b à abandonner si on retient B ou pivot.

## §6 Captures qualitatives 3 sample (audit Matteo manuel)

### Q4 OFF-TOPIC succès attendu — v5b faith=0.05 (INFIDELE) | format=80%

> **TL;DR**
> 1. Les fiches fournies ne couvrent pas les dispositifs de logement étudiant (CROUS, résidences sociales, etc.).
> 2. En revanche, certaines formations en **aménagement/immobilier** (ex : Licence Géographie à la Sorbonne) incluent des modules sur l’accès au logement — utile pour comprendre les leviers.
> 3. Je te redirige vers les ressources **officielles et gratuites** pour trouver un logement adapté à ton échelon 7.
> 
> ---
> 
> ### **Plan A — Urgent : Logement social étudiant (CROUS/ALS)**
> - **Dossier Social Étudiant (DSE)** : à remplir **dès maintenant** sur [messervices.etudiant.gouv.fr](https://messervices.etudiant.gouv.fr) pour bénéficier des **résidences CROUS** (loyers de 200€ à 400€/mois selon ville) et de l’**Aide au Logement (ALS)**.
> - *Pour toi* : Priorité absolue avec l’échelon

### Q10 ON-TOPIC régression persistante (framing Terminale L) — v5b faith=0.20 (INFIDELE) | format=80%

> **TL;DR**
> Si tu aimes les langues et la culture, la série L n’est pas un problème : elle te prépare bien à des études comme **LEA (Langues Étrangères Appliquées)**. Mais attention, **le bac L n’existe plus depuis 2021** – aujourd’hui, ce sont les **spécialités** (HLP, Langues, SES, etc.) qui comptent pour ton orientation. Voici 3 pistes concrètes pour toi, avec des formations qui recrutent *vraiment* après le bac.
> 
> ---
> 
> ### **Plan A — Réaliste : Licence LEA (Langues Étrangères Appliquées)**
> 📍 **LEA (2 langues hors anglais) — Sorbonne Université (Paris)**
> Formation **publique en 3 ans**, sélective (42% d’admis en 2025), idéale si tu aimes les langues *et* leur application (commerce, traduction, tourisme).
> *Pour toi :* Avec un bon dossier (mention AB ou mieux), c’est accessible – et Paris of

### Q11 PIEGE ignorance — v5b faith=1.00 (FIDELE) | format=20%

> **TL;DR**
> 1. Les fiches fournies ne concernent **pas l'IFSI de Lille** (institut de formation en soins infirmiers).
> 2. Je n’ai **aucune donnée** sur le nombre d’admis 2026 ou le nom du directeur dans mes sources.
> 3. Pour des infos officielles, consulte **l’IFSI de Lille directement** ou le site de l’**ARS Hauts-de-France**.
> 
> ---
> **Où trouver ces informations ?**
> - **Site de l’IFSI de Lille** : [recherche Google "IFSI Lille contact"](https://www.google.com) → onglet "Admission" ou "Équipe".
> - **Parcoursup** : si la formation y est référencée, les stats 2026 y seront publiées **à partir de juin 2026** (après la phase d’admission).
> - **ARS Hauts-de-France** : liste officielle des IFSI agréés + coordonnées des directeurs ([site ARS](https://www.hauts-de-france.ars.sante.fr)).
> 
> **Attention** : 

---

*Verdict v5b vs v5 vs v4 généré par `scripts/bench_v5b_vs_v5_vs_v4_sprint11_p1_1.py`. Standby arbitrage Matteo via Jarvis sur ship v5b / escalation B / pivot.*

---

## §7 Nuances clés (gains/pertes qualitatifs non capturés par stats agrégées)

### 7.1 Q10 framing acceptance CORRIGÉ par v5b — première occurrence Sprint 11

Verdict auto §4 dit "INSUFFISANT 1/5". MAIS la lecture qualitative Q10 v5b révèle un gain majeur **non capturé par les métriques agrégées** :

> v5b Q10 réponse : *« Si tu aimes les langues et la culture, la série L n'est pas un problème : elle te prépare bien à des études comme LEA. Mais attention, **le bac L n'existe plus depuis 2021** — aujourd'hui, ce sont les spécialités (HLP, Langues, SES, etc.) qui comptent pour ton orientation. »*

→ **Première fois Mistral invalide la fausse prémisse implicite Q10** sur l'ensemble des bench Sprint 11 (Item 4 v4, Sous-étape 1 v4 températures multiples, Sous-étape 3 v5, Sous-étape 4 v5b). Tous les autres runs acceptaient le framing « tu es en terminale L ».

Hypothèse : le scaffolding 2 étapes (vérification source obligatoire) déclenche un check actif sur les noms d'éléments (« terminale L »), et la connaissance officielle Mistral medium se mobilise mieux SANS la distraction des balises XML. Limite framing acceptance Item 3 §5 + §6 verdict #111 : **partiellement franchie** par v5b.

→ **Gain qualitatif majeur à préserver** quelle que soit la voie suivante.

### 7.2 Q4 v5b — perte de l'IGNORANCE_OK benefit OFF-TOPIC

v5 Q4 admettait clairement « pas couvert par les fiches » + redirection ressources externes (faith FIDELE 1.00, format 20% car pas de Plans A/B/C par nature OFF-TOPIC).

v5b Q4 a INVENTÉ « Licence Géographie à la Sorbonne inclut modules sur l'accès au logement » + plein de chiffres CROUS (200-400€) avec format Plans A/B/C complets. **Faith INFIDELE 0.05**, format 80%.

Hypothèse : sans les balises XML brouillon, Mistral est revenu à son comportement par défaut « toujours produire des Plans » même en OFF-TOPIC. **Trade-off entre format compliance et IGNORANCE_OK comportement.**

### 7.3 Q11 piège — bug classifier RÉCIDIVE (Apprentissage #4 confirmé)

v5b Q11 a écrit un aveu d'ignorance PARFAIT :
> *« Les fiches fournies ne concernent **pas l'IFSI de Lille** [...] Je n'ai **aucune donnée** sur le nombre d'admis 2026 ou le nom du directeur dans mes sources. »*

→ Comportement attendu IGNORANCE_OK. MAIS classifier v2 retourne PARTIAL_FUZZY car le pattern v2 cherche « informations » et ne match pas « **aucune donnée** » ni « ne concernent pas l'IFSI ».

**Apprentissage #4 RÉCIDIVE empiriquement** : tester regex classifier avec exemples réels variés AVANT déployer. Le pattern v2 est encore insuffisant. Pattern v3 nécessaire pour matcher « aucune donnée », « ne concernent pas », autres formulations naturelles.

→ Si on étend classifier v3 → v5b passerait à **2/5 critères** (Empathie + Ignorance OK).

→ Capitalisation à venir : étendre `feedback_pr_patterns.md` Apprentissage #4 avec « le pattern v2 lui-même peut être insuffisant — itérer jusqu'à coverage saturée empiriquement ».

### 7.4 Format compliance amélioré v5b vs v5 (mais pas atteint baseline v4)

| Format ON-TOPIC 8 q | v4 baseline | v5 (avec XML) | v5b (sans XML) |
|---|---|---|---|
| % | **82.2 %** | 65.0 % | **73.3 %** |

v5b restaure **+8.3 pp vs v5** mais reste **-8.9 pp sous v4 baseline**. **Hypothèse balises XML coupables format = PARTIELLEMENT confirmée** (~50 % du gap restauré). Le scaffolding 2 étapes + OBLIGATION + few-shots eux-mêmes contribuent au reste de la perte format (probablement « lost in the middle » sur prompt long, +14 % lignes vs v4).

---

## §8 Reco honnête Claudette affinée

### Diagnostic synthétique tri-version

| Aspect | Voie gagnante | Notes |
|---|---|---|
| Faithfulness mean | v5b ~ v4 ≥ v5 | Tous insuffisants (<0.30) |
| FIDELE/10 | v4 (2) > v5 = v5b (1) | Régression v5/v5b vs v4 |
| Empathie | v5 ≈ v5b > v4 | Tous OK |
| Format compliance | v4 > v5b > v5 | Hypothèse XML partielle confirmée |
| **Q10 framing** | **v5b uniquement** | **Gain qualitatif majeur, première fois** |
| Q11 ignorance (vrai comportement) | v5 = v5b > v4 | Mais bug classifier masque pour v5b |
| Q4 IGNORANCE_OK OFF-TOPIC | v5 > v5b | v5b sacrifie pour format |

### Reco principale

**Escalation Sous-étape 5 backstop B confirmée nécessaire** — aucune des 3 voies (v4, v5, v5b) n'atteint ≥ 4/5 critères. Le post-filter chiffres déterministe en cascade reste l'unique chemin pour atteindre les critères stricts.

### Reco secondaire — préservation gains v5b

**Si Matteo retient backstop B**, je recommande de le construire **sur la base de v5b (et non v5 ni v4)** car v5b apporte 2 gains qualitatifs uniques :
1. **Q10 framing acceptance corrigé** — première fois Sprint 11
2. **Format compliance partiellement restauré** vs v5 (+8 pp ON-TOPIC)

Coût marginal : v5b déjà committé sur main via PR #112 (sera mergé OU pas selon arbitrage Matteo). Phase B = scope additif.

### Reco tertiaire — extension classifier v3

**Si Matteo retient v5b ship en l'état (sans backstop B immédiat)**, je recommande d'étendre le classifier ignorance en v3 (matche « aucune donnée », « ne concernent pas ») pour valider proprement le critère ignorance Q11 — passerait v5b de 1/5 à 2/5 critères. ETA marginal ~10 min.

### Hypothèse Matteo balises XML — verdict empirique

**PARTIELLEMENT confirmée** : v5b restaure +8.3 pp format vs v5 (~50 % du gap récupéré). Le reste de la perte format est probablement dû au **prompt long « lost in the middle »** (cf cross-check Q3 audit externe Jarvis) ou au scaffolding 2 étapes lui-même qui détourne Mistral du pattern Plans A/B/C même sans balises XML.

Hypothèse à valider Sprint 11 P1.3 : ablation prefix vs body sur prompt v5 minimal (sans scaffolding) pour isoler l'effet « lost in the middle » purement.

---

*§7 + §8 nuances + reco affinée appendées 2026-05-01 post-bench v5b. Standby arbitrage Matteo via Jarvis sur escalation B (recommandation principale) construite sur base v5b (préserve Q10 framing fix + format restauré partiel).*