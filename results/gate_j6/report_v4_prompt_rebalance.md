# Gate J+6 — V4.1 system prompt rééquilibré + re-test Claude Sonnet persona

*Date : 2026-04-22 (soir tardif). Ordre : `2026-04-22-1834-claudette-orientia-system-prompt-rééquilibrage-plus-avis-global`.*

---

## TL;DR — hypothèse prompt réfutée, cause racine ailleurs

**Matteo a eu l'hypothèse juste** (system prompt demandait 3 pièges → noise) mais le **rééquilibrage seul ne bouge PAS le verdict** (médiane 2/5 unanime). La cause racine du plateau 2/5 est **plus profonde** : hallucinations Mistral Medium dans le contenu + bugs techniques γ Modify + phase projet non déclenchée.

| Métrique | V4 original | **V4.1 rebalance** | Δ |
|---|---|---|---|
| Médiane globale | 2/5 | **2/5** | stable |
| Moyenne globale | 2.40/5 | **2.00/5** | **−0.40 (légère régression)** |
| Q1 HEC médiane | 4 | **2** | **−2** |
| Q6 Perpignan médiane | 2 | 2 | stable |
| Q8 PASS médiane | 2 | 2 | stable |

## 1. Modifications T2.4 effectuées

`src/prompt/system.py` :
- T2.4 « ⚠ Attention aux pièges » : passé de "section systématique 3 puces" à "1 piège critique max, 2 si nécessaire, pas de section artificielle"
- Exemple dans prompt : "2 pièges" → "1 phrase Attention sur le coût" + note V4.1
- T2.9 générale : "+ Attention aux pièges" → "pièges uniquement si critiques"
- Tests Tier 0 + Tier 2 + validator : 177/177 verts → **zéro régression safety**

ADR-037 à créer (pas fait dans ce commit — à ajouter dans la PR).

## 2. Insights Psy-EN persona (le plus sévère) — commentaires verbatim

### Q1 HEC — bug γ Modify détecté

> **Psy-EN** : *"Texte illisible avec répétitions parasites ('HEC Paris passe par son propre concours AST...' collé 3 fois dans les fiches). Bug technique rédhibitoire pour un élève seul."*

**Bug identifié** : le γ Modify V4 utilise `str.replace(matched_text, replacement, 1)` par violation, mais si une même règle fire N fois sur un texte, N remplacements sont faits → 3 occurrences du même replacement à des endroits différents = pollution lisible. **Fix attendu v4.2** : dédupliquer sur `replacement_text` pour éviter les doublons.

### Q1 bis — Ines (L2 socio) complément

> *"IAE Toulouse présenté comme tremplin HEC : faux. Les AST HEC viennent massivement de Paris-Dauphine, Sciences Po, ENS, universités top 20 mondiales — pas d'IAE de province. Créer un faux espoir à un élève à 11 de moyenne."*

Le γ Modify corrige bien "Tremplin → HEC" mais le pipeline persiste à proposer IAE Toulouse comme rebond HEC → **nouvelle hallucination non couverte par les règles actuelles**.

### Q6 kiné — γ Modify pas appliqué ?

> **Psy-EN** : *"Licence Sciences de la vie - option Kinésithérapie n'existe PAS. L'accès kiné se fait via PASS/L.AS puis concours IFMK. Invention dangereuse."*

Malgré la règle V2.4 `kine_via_IFMK_not_licence` qui DEVRAIT γ Modify, la réponse contient toujours l'hallucination "Licence option Kinésithérapie". **Possibilité** : le regex V2.4 ne match pas exactement ce que Mistral a produit cette regen. Variance LLM + règle trop étroite.

### Q8 PASS — phase projet ABSENTE malgré trigger

> **Psy-EN** : *"Aucune phase projet : l'outil balance un Plan A/B/C sans demander 'Où en es-tu de ta réflexion ?'. Je commence TOUJOURS par cette question."*

Le trigger "PASS" est DANS la liste `HIGH_STAKES_TRIGGERS` du module `phase_projet.py`. Le footer devrait être appendé. **Bug possible** : `already_has_project_prompts` retourne `True` par erreur car la réponse contient une formulation proche de "Qu'est-ce qui te motive" en contexte non-projet. À déboguer.

### Q8 PASS — redoublement interdit NON mentionné

> *"PASS à 18% d'admission présenté comme 'ambitieux' sans préciser l'INTERDICTION de redoublement (arrêté 4 novembre 2019). Un lycéen doit savoir qu'il joue sa carte en une fois."*

La règle de présence `PASS_redoublement_info` est supposée flag ça. **Possible** : la règle flag correctement MAIS le flag arrive en `WARN footer` (top 2 polish) et Mistral medium n'ajoute pas spontanément la mention dans sa regeneration. → migration Presence → Modify (injection automatique) devient **P0 absolu v5**.

## 3. Root cause plus profond qu'un prompt verbeux

Contrairement à l'hypothèse initiale, le rééquilibrage "Attention aux pièges" **n'a PAS amélioré le score**. Les personas continuent de trouver les réponses 2/5 car :

1. **Hallucinations factuelles persistantes** dans le contenu même de la réponse (formations inventées, dates obsolètes, interdits non mentionnés)
2. **γ Modify produit des artefacts textuels** (répétitions du replacement) → bug technique
3. **Phase projet ne se déclenche pas en pratique** malgré triggers présents (bug à investiguer)
4. **Règles V2 ne catchent pas toutes les variations LLM** de l'hallucination (Mistral regen différemment à chaque run)

**Le prompt verbeux était un facteur UX aggravant, pas la cause première.** La vraie cause est **la qualité de génération** du modèle Mistral Medium + le manque de couverture règles/presence pour les variantes d'hallucinations.

## 4. Conclusion V4.1

- Rééquilibrage prompt = **utile** (réduit le bruit visuel, aligne avec feedback Léo "infantilisé"), mais **pas suffisant** pour le plateau 2/5
- Tests Tier 0 + validator : **177/177 verts, zéro régression safety**
- La **vraie cause racine** est le pipeline génération qui produit toujours le même type d'erreurs factuelles, quelles que soient les règles/presence en aval

**→ L'avis global Claudette (sections A-F ci-dessous) traite la vraie question : quelle piste back-end adresse le plateau ?**

## 5. Livrables

- `src/prompt/system.py` : T2.4 rééquilibré + T2.9 + exemple dans prompt
- `scripts/run_gate_j6_v4_rebalance.py` + `scripts/gate_j6_v4_rebalance_resimu.py`
- `results/gate_j6/responses_validator_v4_rebalance_active.json` (3 Q)
- `results/gate_j6/ground_truth_v4_rebalance_resimule.json` (15 evaluations)
- Ce rapport

## 6. Budget API

~$1.50 (3 Q pipeline + 15 persona calls).
