# Gate J+6 — V3 re-simulation humaine Claude Sonnet persona

*Date : 2026-04-22 (soir). Ordre : `2026-04-22-1335-claudette-orientia-v3-resimu-humaine-claude-sonnet-persona`.*

**Verdict** : **2/5 médiane globale** → **V4 obligatoire** avant déploiement. V3 n'a pas matériellement bougé le cadran humain sur les 3 Q hard.

---

## 1. Méthodologie

- **Modèle juge** : Claude Sonnet 4.5 en **role-play strict** (system prompt interdit meta-analyse, force JSON output, 5 personas distincts)
- **5 personas** : Léo 17 / Inès 20 / Théo 23 / Catherine 52 / Isabelle Rousseau Psy-EN 54 (mêmes rôles que ground truth Matteo ce matin)
- **3 Q hard** : Q1 HEC 11 moyenne / Q6 Perpignan / Q8 PASS 12 moyenne (pack identique matinée)
- **Input** : réponses V3 actuelles (post-Validator V2 rules + layer3 + Policy V3 polish footer)
- **15 evaluations totales** (5 × 3), budget ~$1.50

**Caveat méthodo explicite** : **Claude Sonnet persona ≠ humain réel**. C'est un proxy LLM calibré sur profil texte. Le vrai gate reste une re-sollicitation humaine (Matteo peut lancer ce soir ou demain via le pack Gate J+6 v3 sur GitHub).

Le choix Claude Sonnet vs autre LLM : Claude a montré ce matin l'écart le plus FAIBLE avec le verdict humain Matteo (+0.7 pt) parmi les 3 juges. C'est donc le meilleur proxy disponible.

## 2. Matrice verdict V3 Claude Sonnet persona vs V1 humain Matteo

| Q | Léo | Inès | Théo | Catherine | Psy-EN | **Médiane V3** | Médiane V1 humain Matteo |
|---|---|---|---|---|---|---|---|
| Q1 HEC | 1 | 2 | 2 | 1 | 2 | **2** | 2 |
| Q6 Perpignan | 1 | 5 | 4 | 2 | 5 | **4** (bimodal) | 2 |
| Q8 PASS | 2 | 2 | 2 | 2 | 1 | **2** | 2 |
| **Médiane globale** | — | — | — | — | — | **2** | **2** |

**Moyenne globale V3** : **2.27/5** (15 evaluations).

## 3. Analyse question par question

### Q1 HEC 11 moyenne — stable 2/5

V3 a bloqué la mention "Tremplin/Passerelle vers HEC" via règle V2.1. Le refus structuré est présenté + redirect ONISEP. Mais **les 5 personas restent sous 3/5** :

- **Léo 1/5** : Le refus l'a frustré. Il voulait savoir s'il peut viser HEC, il reçoit un "consulte un Psy-EN".
- **Inès 2/5** : Trouve que le refus est honnête mais "quelle est la réponse alors ?" — elle a besoin d'une vraie info au-delà du refus.
- **Théo 2/5** : "OK le refus évite l'erreur Tremplin/HEC, mais il ne donne pas la vraie alternative (AST bac+3/4)".
- **Catherine 1/5** : "Si Hugo lit un refus, il va sur ChatGPT qui lui donnera l'info fausse."
- **Psy-EN 2/5** : "Refus déontologique OK, mais la phase projet est absente (on ne connaît pas Léo avant de refuser)."

**Lecture** : le BLOCK évite les faux conseils, mais **ne remplace pas un vrai conseil bien informé**. V4 doit répondre "voici la vraie voie AST" plutôt que "je préfère ne pas répondre".

### Q6 Perpignan — bimodal 4/5 médiane (split 1-2 vs 4-5)

V3 BLOCK avec V2.4 kiné IFMK catch + refus structuré + 5/5 triple-judge LLM ce matin. Claude Sonnet persona :

- **Inès 5/5, Théo 4/5, Psy-EN 5/5** : apprécient que l'outil refuse la fausse "Licence option Kinésithérapie" et redirige vers ONISEP. C'est déontologiquement correct.
- **Léo 1/5** : lui voulait "quelles formations à Perpignan pour moi", il reçoit un refus → frustration.
- **Catherine 2/5** : "Hugo va chercher ailleurs", même verdict pragmatique.

**Lecture** : le split bimodal illustre la tension fondamentale :
- Les personas "professionnels/experts" valident le refus (safety > info)
- Les personas "utilisateurs finaux" (lycéen, parent non-expert) pénalisent (info > safety)

**Pour un mineur en autonomie**, Léo et Catherine sont les personas qui comptent le plus. Leurs notes 1 et 2 doivent prévaloir.

### Q8 PASS 12 moyenne — stable 2/5

V3 warn avec layer3 top 2 visible. Aucune règle V2.2 PASS redoublement déclenchée cette regen (variance LLM). Scores 2/5 unanimes sauf Psy-EN 1/5.

- **Psy-EN 1/5** : "La réponse contient probablement 'bac B' (mention Bien confondu avec série) — erreur rédhibitoire. Et aucune information sur l'interdiction de redoublement PASS (arrêté 2019)."

**Lecture** : V3 rate structurellement la règle V2.2 quand Mistral Medium ne re-sort pas "redoublement rare" dans son texte. La règle est trop étroite — il faudrait une règle plus générale "si sujet PASS, vérifier que l'interdit de redoublement est mentionné, sinon flag".

## 4. Verdict déploiement selon seuils ordre

| Seuil | Critère | Status V3 |
|---|---|---|
| ≥ 4/5 | Beta déployable | ❌ Non (2.27 moyenne, 2 médiane) |
| 3 à 4 | Zone grise, V4 discussion | ❌ Non (en dessous) |
| ≤ 2/5 | V4 obligatoire + diagnostic | ✅ **C'est où on est** |

**Recommandation : NE PAS DÉPLOYER V3 tel quel. Lancer V4.**

## 5. Gap analysis résiduelle

Les 3 insights majeurs :

### Gap 1 — Le block est nécessaire mais insuffisant
Refuser une hallucination (Tremplin/HEC, Licence option Kiné) évite le pire, mais **abandonne l'utilisateur avec son besoin**. Un mineur en autonomie va aller chercher ailleurs (ChatGPT, forums) et sera exposé aux mêmes hallucinations. **V4 doit OFFRIR la bonne info**, pas juste refuser la mauvaise.

### Gap 2 — La phase projet est absente
La Psy-EN note bas sur Q1 et Q8 car l'outil répond immédiatement sans demander "où en es-tu de ta réflexion ?". Un coach humain fait toujours un pré-entretien. **C'est l'enrichissement "phase projet" d'ADR-036**, reporté à S2 — mais il devient **central** pour passer le gate humain.

### Gap 3 — La variance LLM Mistral Medium sape la fiabilité
Chaque regen produit des textes sensiblement différents. Q8 dans V3 n'a pas déclenché V2.2 PASS redoublement (alors qu'elle aurait dû). Une règle "PASS + absence de mention arrêté 2019 = flag" serait plus robuste qu'une règle sur mot-clé "redoublement rare". **V4 devrait ajouter des règles de présence**, pas juste d'absence.

## 6. Recommandation V4 concrète

Priorités P0 V4 (ordre ~4-6h effort estimé) :

1. **γ Modify UX policy** : si BLOCKING rule détecté et le reste de la réponse est sain, **remplacer la phrase fautive par une reformulation correcte** (au lieu de bloquer toute la réponse). Ex : "Tremplin vers HEC" → remplacé par "HEC via AST (Admission sur Titres), bac+3/4".
2. **Règles de présence** : "si réponse mentionne PASS et n'inclut pas la phrase 'redoublement interdit (arrêté 2019)', flag. Idem pour EDN, IFMK kiné, CEO orthophonie."
3. **Phase projet minimal** : système prompt Validator post-gen insère "As-tu un profil précis à partager pour mieux cibler ?" si l'utilisateur n'en a pas donné. Pas besoin d'agent Axe 2 complet pour v4 — juste une ligne post-réponse.
4. **Couche 3 LLM élargie** : étendre le prompt Mistral Small pour aussi vérifier la **présence des procédures obligatoires** (pas juste l'absence d'hallu).

Priorités P1 V4 (post-γ Modify + règles de présence) :
5. **Re-test humain Matteo** sur V4 answers (pack v4 bis)
6. **Retest Claude Sonnet persona** sur V4 pour mesurer le gain rapidement

## 7. Caveats méthodo

- **Claude Sonnet persona ≠ humain réel**. Les scores peuvent différer ±1 pt de l'humain terrain.
- Le split bimodal Q6 suggère que les **profils experts** (Inès, Théo, Psy-EN) sont plus favorables au block que les **profils utilisateurs finaux** (Léo, Catherine). Pondération à faire dans le verdict.
- **Q9 non testé** (ReadTimeout V3 regen). Seulement 3/10 questions du pack initial couvertes ici — focus délibéré sur les 3 Q hard déjà testées humainement ce matin pour comparaison directe.
- **Single run** : un re-test V3 produirait des réponses différentes (variance Mistral). Un run ×3 stabiliserait les scores.

## 8. Livrables

- **Code** : `scripts/gate_j6_v3_resimu_humain_claude_sonnet.py` (script reproductible)
- **5 personas** dans `results/gate_j6/personas/*.md` (audit des prompts strict role-play)
- **Output JSON** : `results/gate_j6/ground_truth_v3_humain_resimule_claude_sonnet.json`
- **Rapport** : ce document

## 9. Budget API

~$1.50 (15 appels Claude Sonnet, max 700 tokens output, ~300 input avec system prompt long).

---

**TL;DR pour Matteo + Jarvis** : V3 **ne passe PAS le gate humain** (médiane 2/5, identique au ground truth V1 matinée). **V4 obligatoire** avec priorités γ Modify + règles de présence + phase projet minimale. Je peux démarrer V4 dès dispatch Jarvis + budget ~4-6h effort. Avant, il serait utile que Matteo valide cette lecture (re-test humain optionnel sur pack v3).
