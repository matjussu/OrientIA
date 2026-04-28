# Draft v2 — 50 prompts diversifiés OrientIA Sprint 9-data

**Statut** : v2 consolidée avec retours Matteo intégrés (28/04 11:05 Telegram). Lecture mobile-friendly via GitHub.
**Date** : 28 avril 2026
**Référence ADR** : `08-Decisions/2026-04-28-orientia-pivot-pipeline-agentique-claude.md` (vault Obsidian)

---

## 🔄 Changelog v1 → v2

**Modifs structurelles intégrées suite review Matteo** :

✅ **3 nouveaux profils ajoutés** (catégorie G nouvelle) :
- **G1** — Décrocheur 16-18 ans (Missions Locales / E2C / SMV)
- **G2** — Neuroatypique DYS/TDAH (craint amphis / évaluations écrites longues)
- **G3** — Rural / Agricole (auto-censure "grandes écoles c'est pour Paris" + transport + logement)

✅ **2 fusions** (libère 2 slots) :
- **A1 + A7 → A1** "Scientifique cherche voies post-bac appliquées/hybrides"
- **B9 + C5 → B9** "Dilemme ROI continuer études vs marché direct"

✅ **Sources priority enrichies** :
- **Alternance/CFA** (A5, C3) : ajout `alternance.emploi.gouv.fr` + `1jeune1solution.gouv.fr`
- **Handicap** (A9, E3) : ajout `MonParcoursHandicap.gouv.fr` (vs ONISEP seul)
- **Fonction Publique** (D3) : ajout `Place de l'Emploi Public` + `Choisir le service public` (vs ENA/CNFPT seul)

✅ **Tone tutoiement/vouvoiement recadré** :
- **Tutoiement par défaut** jusqu'à 24/25 ans (ton bienveillant/coach)
- **Vouvoiement uniquement** pour requêtes statutaires/corporate : **C8** (expat retour), **D3** (Fonction Publique), **D7** (MBA), **D8** (VAE)
- Tous les autres profils 22-25 (C1, C2, C3, C4, C5→fusion, C6, C7) → tutoiement (proximité coach)

✅ **Questions seed → 5-6 par prompt** (au lieu de 3) + **intégration questions réelles user_test_v3** (cf annexe ci-dessous, 10 questions test set + variantes phrasings humains)

**Math final** : 50 - 2 (fusions) + 3 (G) = **51 prompts × 20 itérations ≈ 1020 cas Q&A**

---

## 📍 Contexte (rappel pour reprendre le fil)

Pivot stratégique majeur OrientIA tranché ce matin (brainstorming Telegram 06:09→09:21) : **Q&A documentaire RAG → conseiller IA conversationnel**. 9 décisions ADR (D1-D9) + Sprint 9 décomposé en 2 ordres (Ordre 1/2 archi LIVRÉ par Claudette PR #100 + Ordre 2/2 data = ce draft + génération nuit 28-29 via Task tool sub-agents Opus 4.7).

**Couverture** des 3 axes scope OrientIA 17-25 :

| Catégorie | # prompts | # cas | % couverture |
|-----------|-----------|-------|--------------|
| **A.** Lycéens post-bac | 9 (- A7 fusionné) | 180 | 17,6% |
| **B.** Étudiants en réorientation | 10 (B9 enrichi par fusion C5) | 200 | 19,6% |
| **C.** Actifs jeunes 22-25 | 7 (- C5 fusionné dans B9) | 140 | 13,7% |
| **D.** Master + débouchés pro | 8 | 160 | 15,7% |
| **E.** Cas familiaux/sociaux | 8 | 160 | 15,7% |
| **F.** Méta-questions conseil | 6 | 120 | 11,8% |
| **G.** Profils non-cadre classique | 3 (NOUVEAU) | 60 | 5,9% |
| **Total** | **51** | **1020** | **100%** |

---

## 📋 Format de chaque prompt

```yaml
ID: A1
Catégorie: Lycéen post-bac (Axe 1)
Persona: 17 ans, lycée public, profil scientifique solide
Context: Hésite voies post-bac scientifiques appliquées/hybrides
Constraints: [region:variable, budget:moderate, valeurs:concret_hybride]
Tone: tutoiement
Sources priority: ONISEP > Parcoursup > InserJeunes > France Compétences
Questions seed (5-6 par prompt, à étendre par Claudette en YAML):
  - "Je sature de maths abstraites, alternatives concrètes à la prépa MPSI ?"
  - "Quelles écoles d'ingénieur post-bac valent le coup vs prépa ?"
  - "Bio-info, finance quant, jeu vidéo : quelles voies post-bac précises ?"
  - "[Question test set v3 Q2] Quelles sont les meilleures formations en cybersécurité en France ?"
  - "[Variante phrasing humain] Bon en code mais CS classique me lasse, y'a quoi d'autre ?"
```

**📌 Note pour Claudette (conversion YAML)** : pour chaque prompt, étendre les 3 seeds actuelles à 5-6 en intégrant :
- 1-2 questions test set v3 si match (cf annexe)
- 1-2 variantes phrasing humain (argot, abréviations, syntaxe relaxée — inspiré Léo 17 / Sarah 20 / Thomas 23 / Catherine 52 / Dominique 48)
- Conserver les seeds originaux comme variantes formelles

---

## A. Lycéens post-bac (9 prompts) — Axe 1

### A1 — Scientifique cherche voies post-bac appliquées/hybrides ⚠️ FUSION A1+A7
**Persona** : 17 ans, terminale spé maths-physique ou maths/code, lycée public/privé, profil scientifique solide mais **pas attiré par prépa MPSI / CS pure**
**Context** : Cherche alternatives concrètes (BUT, écoles ingé post-bac, bachelors, formations hybrides bio-info / finance quant / jeu vidéo / robotique)
**Constraints** : `region:variable`, `budget:moderate`, `valeurs:concret_hybridation`, `style:non-mainstream`
**Tone** : tutoiement
**Sources priority** : ONISEP (alternatives prépa, formations hybrides), Parcoursup (BUT, écoles ingé post-bac), InserJeunes (insertion BUT vs prépa→école), France Compétences
**Questions seed** :
- "Je suis en terminale spé maths-physique mais je sature des maths abstraites, alternatives concrètes à la prépa MPSI ?"
- "Quelles écoles d'ingénieur post-bac valent le coup vs prépa ?"
- "Bio-info, finance quant, jeu vidéo : quelles voies post-bac précises ?"
- "[Test set v3 Q2] Quelles sont les meilleures formations en cybersécurité en France ?"
- "[Test set v3 Q3] Compare ENSEIRB-MATMECA et EPITA pour la cybersécurité"

### A2 — Terminale spé SES-HG, indécis multi-domaines
**Persona** : 17 ans, lycée public province, profil littéraire scientifique solide
**Context** : Hésite éco vs droit vs sciences-po vs IEP régional
**Constraints** : `region:hors_idf`, `budget:moderate`, `valeurs:utilité_sociale`, `style:pragmatique`
**Tone** : tutoiement
**Sources priority** : Parcoursup (formations éco/droit), CIDJ (témoignages), ONISEP (fiches métiers droit/éco), Sciences-Po (concours commun IEP)
**Questions seed** :
- "Je hésite entre éco-gestion, droit et sciences-po, comment choisir ?"
- "Sciences-Po Paris ou IEP région, quelle différence concrète ?"
- "Pour un profil SES-HG, quel master pro paie mieux à 5 ans : droit ou éco ?"
- "[Test set v3 Q1] J'ai 11 de moyenne en terminale générale, est-ce que je peux intégrer HEC ?"

### A3 — Terminale spé lettres, peur de débouchés
**Persona** : 17 ans, lycée privé sous contrat, passion écriture/littérature
**Context** : Aime les lettres mais panique sur le "ça mène à rien" parental/social
**Constraints** : `région:hors_idf`, `budget:bas`, `boursière:probable`, `valeurs:passion_créativité`
**Tone** : tutoiement, doux
**Sources priority** : ONISEP (débouchés lettres), CNED, France Travail (métiers de l'écrit), édition/presse (taux insertion)
**Questions seed** :
- "J'aime les lettres mais tout le monde dit que ça mène à rien, c'est vrai ?"
- "Quels métiers vraiment accessibles avec une licence de lettres modernes ?"
- "Master édition / journalisme / communication : lequel a le meilleur taux d'embauche ?"

### A4 — Terminale techno (STMG/STI2D), sous-estimation parents
**Persona** : 17 ans, lycée public, série techno valorisée par profs mais dévalorisée par parents
**Context** : Veut continuer études (BTS/BUT) mais parents poussent BAC général "pour se garder des options"
**Constraints** : `région:variable`, `budget:moderate`, `famille:doute_techno`, `mobilité:possible`
**Tone** : tutoiement, valorisant
**Sources priority** : ONISEP (filières techno→sup), Parcoursup (BTS/BUT), DARES (insertion BTS/BUT), témoignages BTS-BUT réussis
**Questions seed** :
- "Je suis en STMG, est-ce que c'est handicapant pour la fac ou les écoles de commerce ?"
- "BTS ou BUT pour un STI2D ? Quelle différence concrète ?"
- "Mes parents pensent que la techno c'est moins bien, comment leur répondre avec des chiffres ?"

### A5 — Terminale pro (bac pro), continuer ou marché ?
**Persona** : 17 ans, lycée pro, formation tertiaire ou industrielle
**Context** : Diplôme en poche, hésite continuer (BTS/CFA) vs entrer marché direct
**Constraints** : `région:variable`, `budget:bas`, `urgent:faim_indépendance`, `valeurs:travail_concret`
**Tone** : tutoiement, direct
**Sources priority** : France Travail (insertion bac pro), **`alternance.emploi.gouv.fr`** (ajout v2), **`1jeune1solution.gouv.fr`** (ajout v2), CFA (apprentissage post-bac pro), DARES (taux emploi 6 mois post-bac pro), OPCO (aides reconversion)
**Questions seed** :
- "Je sors d'un bac pro commerce, je continue en BTS ou je tente direct le marché ?"
- "Si je continue en alternance, comment trouver une entreprise ?"
- "Mon bac pro maintenance industrielle, quel BTS s'enchaîne vraiment ?"

### A6 — Terminale spé bio, aime soin pas médecine
**Persona** : 17 ans, lycée public, passion vivant et soin
**Context** : Aime aider mais ne veut pas faire médecine (PASS/LAS angoissant + écoles privées chères)
**Constraints** : `région:variable`, `budget:moderate`, `valeurs:soin_humain`, `peurs:concours_pass_las`
**Tone** : tutoiement, rassurant
**Sources priority** : ONISEP (paramédical), Parcoursup (IFSI infirmier, kiné, ostéo, sage-femme), CNED, témoignages réorientation post-PASS
**Questions seed** :
- "J'aime le soin mais PASS/LAS me terrorise, quelles alternatives santé ?"
- "Infirmier, kiné, ostéo : quelles différences concrètes au quotidien ?"
- "[Test set v3 Q7] Je veux devenir médecin, comment faire ?"
- "[Test set v3 Q8] J'ai 12 de moyenne générale en terminale, est-ce que j'ai mes chances en PASS ?"
- "[Test set v3 Q9] Compare devenir infirmier et kinésithérapeute : études, salaires, débouchés."

### A8 — Terminale boursière échelon élevé, mobilité limitée *(renumérotation : ex-A8)*
**Persona** : 17 ans, lycée public, boursière échelon 6-7
**Context** : Études supérieures uniquement viables si proche domicile (Bordeaux/Toulouse/Lyon/Lille selon perso) + bourses
**Constraints** : `région:hors_idf_proche_lycée`, `budget:très_bas`, `bourse:échelon_6_7`, `mobilité:max_50km`, `valeurs:emploi_rapide`
**Tone** : tutoiement, pragmatique
**Sources priority** : CROUS (bourses + logement), Parcoursup (filière + carte régionale), France Travail (insertion régionale), DARES (BUT/BTS taux insertion)
**Questions seed** :
- "Je suis boursière échelon 7, comment je peux faire des études sup en restant proche ?"
- "Quelles aides au logement étudiant existent au-delà de la bourse ?"
- "Pour mon profil, BUT près de chez moi vaut-il mieux que fac à Paris loin ?"

### A9 — Terminale handicap moteur, accessibilité écoles
**Persona** : 17 ans, lycée adapté, handicap moteur (fauteuil roulant)
**Context** : Études sup possibles mais besoin d'établissements accessibles + accompagnement
**Constraints** : `région:variable`, `budget:moderate`, `handicap:moteur`, `valeurs:accessibilité`, `mobilité:transports_adaptés`
**Tone** : tutoiement, attentionné
**Sources priority** : **`MonParcoursHandicap.gouv.fr`** (ajout v2 — plateforme État principale MDPH/études), ONISEP handicap, AGEFIPH (insertion pro), MDPH, témoignages associations étudiants handicapés
**Questions seed** :
- "Je suis en fauteuil, quelles études sup sont vraiment accessibles ?"
- "Quels aménagements obtenir pour les concours et examens ?"
- "Quelles aides financières spécifiques au handicap pour les études ?"

### A10 — Terminale international, envie partir Erasmus dès L1
**Persona** : 17 ans, lycée international, double profil (français + 1 autre langue)
**Context** : Veut commencer études en France mais avec mobilité Erasmus précoce ou Bachelor international
**Constraints** : `région:idf_ou_grande_ville`, `budget:moderate_high`, `valeurs:ouverture_internationale`, `langues:fr+en+autre`
**Tone** : tutoiement, ambitieux
**Sources priority** : Campus France, Erasmus+, ONISEP (programmes internationaux), Parcoursup (Bachelor + échanges), écoles spécifiques (ESCP, Sciences-Po, ESSEC en BBA)
**Questions seed** :
- "Je veux faire Erasmus dès la L1, c'est possible et où ?"
- "Bachelor international 3 ans (BBA, IBP) ou licence + Erasmus en L3 ?"
- "Mon double profil français-anglais comment le valoriser le mieux ?"

---

## B. Étudiants en réorientation (10 prompts) — Axe 1+2

### B1 — L1 droit ratée, sature, veut changer
**Persona** : 18-19 ans, L1 droit en cours d'échec
**Context** : Sature de la fac, peu de soutien, questionne son choix initial
**Constraints** : `région:variable`, `budget:moderate`, `urgence:semestre_validé_à_perdre`, `valeurs:concret`
**Tone** : tutoiement, encourageant
**Sources priority** : Parcoursup (Apb-réorientation), CIDJ (témoignages), ONISEP (passerelles L1→BTS/BUT), CNED (reprise études)
**Questions seed** :
- "Ma L1 droit ne se passe pas bien, je veux changer mais j'ai peur de perdre une année"
- "Quelles passerelles existent du droit vers d'autres formations sans repartir de zéro ?"
- "Un BUT après L1 droit ratée, c'est crédible ?"
- "[Test set v3 Q5] Je suis en L2 droit et je veux me réorienter vers l'informatique, comment ?"

### B2 — L1 PASS échec, pas refaire médecine
**Persona** : 18-19 ans, fin L1 PASS, échec ou écœurement
**Context** : PASS pas réussi, ne veut PAS refaire LAS, cherche reconversion santé non-médecin ou hors santé
**Constraints** : `région:variable`, `budget:moderate`, `émotion:échec_difficile`, `valeurs:soin_alternative`
**Tone** : tutoiement, compatissant
**Sources priority** : ONISEP (paramédical post-PASS), Parcoursup (passerelles PASS), témoignages réorientation post-PASS, France Travail (métiers de la santé hors médecin)
**Questions seed** :
- "J'ai raté PASS, je ne veux pas refaire LAS, quelles options ?"
- "Quelles formations valorisent vraiment ma L1 PASS pour les passerelles ?"
- "Comment se reconstruire psychologiquement après un échec PASS ?"
- "[Test set v3 Q10] Je suis en L2 psychologie et je veux me réorienter vers l'orthophonie, comment ?"

### B3 — L1 STAPS, blessure, plan B
**Persona** : 19 ans, L1 STAPS, blessure sportive empêche pratique intense
**Context** : Blessure ferme la voie carrière sportive directe, cherche pivot connexe (kiné, prof EPS, ergothérapie, sport management)
**Constraints** : `région:variable`, `budget:moderate`, `condition:blessure`, `valeurs:sport_indirect`
**Tone** : tutoiement, redirection positive
**Sources priority** : ONISEP (kiné, ergo, prof EPS), Parcoursup (passerelles STAPS), France Travail (sport management), MEEF (prof EPS)
**Questions seed** :
- "Ma blessure ferme la voie sportive, mais STAPS m'a appris des choses, comment réorienter ?"
- "Kinésithérapeute après L1 STAPS, comment ça marche ?"
- "Sport management : vrai débouché ou marché saturé ?"

### B4 — Classe prépa MPSI burn-out, sortie L2
**Persona** : 19 ans, fin de prépa MPSI, burn-out confirmé
**Context** : Concours moyen ou pas concours, équivalence L2 possible mais perdu
**Constraints** : `région:variable`, `budget:moderate`, `émotion:burnout_prépa`, `valeurs:rythme_humain`
**Tone** : tutoiement, déculpabilisant
**Sources priority** : Parcoursup (équivalences prépa), ONISEP (post-prépa hors écoles), témoignages reconversion prépa, fac sciences (équivalences L2/L3)
**Questions seed** :
- "Ma prépa MPSI m'a cramée, où aller maintenant ?"
- "L'équivalence L2 prépa vers fac sciences, ça vaut quoi sur le marché ?"
- "Une école d'ingé via concours décalés ou je passe à autre chose totalement ?"

### B5 — DUT/BUT 1ère année, mauvais choix branche
**Persona** : 18-19 ans, BUT 1ère année (ex: GEA), réalise qu'il s'est trompé de spé
**Context** : Veut basculer dans un autre BUT ou autre formation court (BTS), idéalement en gardant le crédit
**Constraints** : `région:variable`, `budget:moderate`, `valeurs:adapté_au_concret`, `urgence:réorientation_S2`
**Tone** : tutoiement, concret
**Sources priority** : Parcoursup (réorientation BUT/BTS), IUTs spécifiques, CIDJ (témoignages réorientation BUT), Apb-Replay
**Questions seed** :
- "Je suis en BUT GEA mais je m'ennuie, comment basculer en BUT info ?"
- "Réorientation BUT en cours d'année, c'est faisable ?"
- "BTS plutôt que BUT, sortie 2 ans, ça dépaysage ou pas ?"

### B6 — L2 langues, cherche reconversion concret
**Persona** : 20 ans, L2 LLCER (anglais), cherche reconversion vers un métier concret
**Context** : Bon en langues mais marché du travail limité prof/traduction, veut autre chose
**Constraints** : `région:variable`, `budget:moderate`, `valeurs:concret_marketable`, `valeurs:langues_atout`
**Tone** : tutoiement, ouvert
**Sources priority** : ONISEP (métiers langues+), France Travail (commerce international, marketing digital, RH internationales), masters spécialisés
**Questions seed** :
- "Ma L2 anglais, comment je la valorise dans un métier concret ?"
- "Master commerce international vs marketing digital vs RH : que choisir ?"
- "Quelles écoles privées valent le coup pour mon profil langues ?"

### B7 — L1 bio, aime science mais pas labo
**Persona** : 19 ans, L1 bio, déçu par la pratique exclusivement labo/microscope
**Context** : Aime concept biologique mais pas la routine labo, cherche bio appliqué (terrain, conseil, communication scientifique)
**Constraints** : `région:variable`, `budget:moderate`, `valeurs:terrain_diversité`, `style:multidisciplinaire`
**Tone** : tutoiement, exploratoire
**Sources priority** : ONISEP (bio terrain, écologie, conseil scientifique), Parcoursup (passerelles bio), France Travail (métiers environnement)
**Questions seed** :
- "Bio en labo me lasse, mais j'aime le vivant, alternatives ?"
- "Métiers de l'écologie de terrain : vrai débouché ou tendance ?"
- "Communication scientifique, médiation, journalisme scientifique : combien ça paie ?"

### B8 — Ingé école 1ère année dégoûté, recommencer ?
**Persona** : 19 ans, école d'ingé post-bac (5 ans), 1ère année finie, dégoûté
**Context** : Choix orienté famille, ne se reconnaît pas dans la culture/contenus, veut changer
**Constraints** : `région:variable`, `budget:moderate (école payante quitte)`, `émotion:déception_familiale_à_gérer`, `valeurs:authenticité`
**Tone** : tutoiement, déculpabilisant
**Sources priority** : Parcoursup (réorientation école→fac/BUT), témoignages reconversion ingé, CIDJ
**Questions seed** :
- "Je suis dans une école d'ingé que mes parents ont choisie, je veux partir, comment leur dire ?"
- "Quitter l'ingénieur après 1 an, équivalences vers la fac ou un BUT ?"
- "Y a-t-il vraiment un stigmate à quitter l'école d'ingé ?"

### B9 — Dilemme ROI continuer études vs marché direct ⚠️ FUSION B9+C5
**Persona** : 20-22 ans, fin de cursus court (BTS / BUT / LP en alternance, commerce/RH/finance/IT/comptabilité)
**Context** : Diplôme bac+2 ou bac+3 + 1 an d'expérience pro alternance, hésite continuer (LP ou master selon niveau) vs entrée marché direct (avec proposition d'embauche fréquente)
**Constraints** : `région:variable`, `budget:moderate`, `valeurs:gain_court_terme_vs_long_terme`, `marché:tendances_secteur`
**Tone** : tutoiement, pragmatique
**Sources priority** : APEC (gains carrière), DARES (LP/BTS/master ROI), France Travail (insertion BTS/BUT), témoignages anciens alternants, écoles cibles spécifiques
**Questions seed** :
- "J'ai mon BTS commerce, je continue en LP ou je tente le marché direct ?"
- "Ma boîte d'alternance veut m'embaucher, mais un master ferait-il vraiment la différence ?"
- "BTS+LP+1 an, gain salarial réel à 5 ans ?"
- "Master en alternance + emploi, c'est faisable concrètement ?"
- "Combien je perds réellement à pas faire le master, à 5 ans ?"

### B10 — Fin alternance L3 pro vers master *(prompt original B10 conservé)*
**Persona** : 21-22 ans, fin licence pro alternance (RH, marketing, comptabilité, IT, etc.) avec ambition master poussée
**Context** : Diplôme bac+3 + 1 an d'expérience pro, vise master en école ou alternance, dilemma ROI long terme
**Constraints** : `région:variable`, `budget:moderate_high (école master payante)`, `valeurs:retours_invest`, `marché:tendances_secteur`
**Tone** : tutoiement, pragmatique
**Sources priority** : APEC (fin LP→emploi), DARES (LP vs master ROI), écoles cibles spécifiques, France Travail
**Questions seed** :
- "Si je vise un master, lequel et quelle école pour mon profil LP ?"
- "Master spécialisé externe (HEC, ESSEC) après mon LP : ça vaut le coup ?"
- "Master en alternance vs initial pour un profil LP ?"

---

## C. Actifs jeunes 22-25 (7 prompts — C5 fusionné dans B9) — Axe 2+3

### C1 — 22 ans BAC+2 reconversion vers tech (dev) — TUTOIEMENT (recadré v2)
**Persona** : 22 ans, BTS ou DUT/BUT non-tech (commerce, gestion, etc.), 1-2 ans pro, veut basculer dev
**Context** : Auto-formé en code (HTML/CSS/JS), envisage formation pro courte (bootcamp) ou retour études
**Constraints** : `région:variable`, `budget:à_financer`, `urgence:reconversion_rapide`, `valeurs:carrière_tech`
**Tone** : tutoiement (recadré v2 : proximité coach pour profil 22 ans en reconversion)
**Sources priority** : France Travail (formations dev), Pôle Emploi (CPF), bootcamps (Le Wagon, 42, Holberton), OPCO (aides reconversion), DARES (insertion dev junior), **`1jeune1solution.gouv.fr`** (ajout v2)
**Questions seed** :
- "J'ai un BTS commerce, je veux devenir dev, bootcamp ou licence pro ?"
- "Le 42 vs Le Wagon vs licence pro info : quel choix pour mon profil ?"
- "Quelles aides financières pour reconversion vers le dev quand je travaille ?"

### C2 — 24 ans bac+5 commerce reconversion santé — TUTOIEMENT (recadré v2)
**Persona** : 24 ans, master école de commerce, 1-2 ans pro, lassée du commerce
**Context** : Veut basculer dans le sanitaire/social mais pas envie de refaire 5 ans d'études
**Constraints** : `région:idf_ou_grande_ville`, `budget:moderate (épargnée)`, `valeurs:utilité_humaine`, `pression:famille_questionne_changement`
**Tone** : tutoiement (recadré v2 : 24 ans en reconversion = proximité coach)
**Sources priority** : ONISEP (sanitaire-social bac+5 inclu reconversion), Parcoursup (IFSI/IFCS post-master), VAE pour santé, France Travail (cadre de santé)
**Questions seed** :
- "J'ai un master commerce mais je veux travailler dans la santé, par où commencer ?"
- "VAE pour devenir cadre de santé sans refaire 3 ans IFSI, c'est faisable ?"
- "Coordinateur santé / médico-social, ça correspond à mon profil bac+5 commerce ?"

### C3 — 23 ans CAP coiffure, reprendre études — TUTOIEMENT (recadré v2)
**Persona** : 23 ans, CAP coiffure + 5 ans pro, veut élargir compétences
**Context** : Bonne pratique mais veut entrepreneuriat (ouvrir salon) ou reconversion management
**Constraints** : `région:variable`, `budget:bas (à financer)`, `valeurs:autonomie_pro`, `urgence:projet_à_5_ans`
**Tone** : tutoiement (recadré v2)
**Sources priority** : OPCO (CAP→BP→BTS via VAE), Pôle Emploi (création entreprise), CMA (chambres des métiers), France Travail (BMA, BMS), **`alternance.emploi.gouv.fr`** (ajout v2)
**Questions seed** :
- "J'ai un CAP coiffure depuis 5 ans, comment ouvrir mon propre salon ?"
- "Quelles formations courtes pour devenir gérante de salon vs simple coiffeuse ?"
- "BP coiffure VAE vs BTS coiffure : quelle valeur ajoutée concrète ?"

### C4 — 25 ans master sciences ne trouve pas job, pivot — TUTOIEMENT (recadré v2)
**Persona** : 25 ans, master 2 sciences (bio, chimie, physique), 1 an galère
**Context** : Marché labo/recherche très saturé, doctorat impossible (pas de financement), veut pivot vers data ou industrie pharma management
**Constraints** : `région:variable`, `budget:bas (galère)`, `émotion:épuisement`, `valeurs:domaine_scientifique_si_possible`
**Tone** : tutoiement (recadré v2 : profil 25 ans en galère = proximité coach motivante)
**Sources priority** : APEC (master sciences→industrie), DARES (cadres industrie pharma/cosmétique), France Compétences (RNCP science→management), formations data conversion
**Questions seed** :
- "Mon master 2 bio ne trouve pas de boulot, comment pivoter sans repartir à zéro ?"
- "Data analyst pour profil sciences, quelles formations courtes ?"
- "Industrie pharma management vs labo public, quelles formations valorisent mon profil ?"

### C6 — 24 ans burn-out boîte, sabbatical reconversion — TUTOIEMENT (recadré v2)
**Persona** : 24 ans, 2-3 ans en cabinet conseil/finance, burn-out
**Context** : Pause récupération, cherche pivot vers domaine moins toxique mais pas perdre les acquis bac+5
**Constraints** : `région:variable`, `budget:épargne_à_dépenser`, `émotion:rare_décision_émotionnelle`, `valeurs:équilibre_vie`
**Tone** : tutoiement, doux (recadré v2 : proximité coach essentielle pour burn-out)
**Sources priority** : France Travail (gestion stress reconversion), PEC sabbatical, Pôle Emploi formations
**Questions seed** :
- "J'ai burn-out après 2 ans en cabinet, comment me reconvertir sans perdre mon CV ?"
- "Année sabbatique pour réorientation : conseils pratiques ?"
- "Métiers à fort sens et bon équilibre vie pro/perso pour profil bac+5 ?"

### C7 — 23 ans étudiant doctoral arrêté, pivot industrie — TUTOIEMENT (recadré v2)
**Persona** : 23 ans, doctorat 1ère ou 2e année arrêté (épuisement, financement coupé, ras-le-bol)
**Context** : Excellent niveau scientifique, mais doctorat ne va pas finir, marché industrie attractif
**Constraints** : `région:variable`, `budget:bas (post-bourse_thèse)`, `valeurs:application_concrète`
**Tone** : tutoiement, valorisant (recadré v2)
**Sources priority** : APEC (docteurs/chercheurs→industrie), DARES (parcours docteurs), forum L'Étudiant, ABG (Association Bernard Grégory)
**Questions seed** :
- "J'arrête mon doctorat, comment valoriser mes 2 ans de recherche en industrie ?"
- "Industrie pharma / cosmétique / agro : quelles entreprises recrutent les ex-doctorants ?"
- "Quelle est la différence salariale doctorat fini vs arrêté en début de carrière industrie ?"

### C8 — 25 ans expat retour France, équivalences — VOUVOIEMENT (statutaire)
**Persona** : 25 ans, BAC+5 obtenu à l'étranger (UK, US, Canada), retour France
**Context** : Diplôme étranger non automatiquement reconnu en France, démarches complexes
**Constraints** : `région:idf_ou_grande_ville`, `budget:moderate`, `valeurs:carrière_continuité`, `urgence:job_dans_3_mois`
**Tone** : **vouvoiement, structuré** (justifié v2 : démarches administratives statutaires)
**Sources priority** : Campus France, ENIC-NARIC (équivalences), APEC (recrutement profils internationaux), France Compétences (équivalences RNCP)
**Questions seed** :
- "J'ai un master UK, comment je le fais reconnaître en France pour le marché du travail ?"
- "Mon profil international, quelles entreprises FR le valorisent vraiment ?"
- "Équivalence ENIC-NARIC vs validation par employeur, lequel est plus rapide ?"

---

## D. Master + débouchés pro (8 prompts) — Axe 3

### D1 — L3 fin choix master spé/pro
**Persona** : 21-22 ans, fin L3 (lettres, sciences, éco, droit), choix master imminent
**Context** : Master recherche vs master pro vs école spécialisée, vs alternance, vs gap year
**Constraints** : `région:variable`, `budget:moderate`, `valeurs:long_terme_carrière`, `dispersion:trop_options`
**Tone** : tutoiement, méthodique
**Sources priority** : Parcoursup (Mon Master), APEC, DARES (master pro vs recherche insertion), école+alternance
**Questions seed** :
- "L3 droit, master pro ou recherche, lequel paie plus à 5 ans ?"
- "Master en école privée (HEC, ESSEC) ou en université, vrai écart ROI ?"
- "Master en alternance vs initial, comment choisir avec mon profil ?"

### D2 — Master 1 commerce, Bachelor + master spécialisé ?
**Persona** : 22 ans, fin M1 école de commerce généraliste, choix M2 spécialisation
**Context** : Spé finance vs marketing vs RH vs entrepreneuriat, ou alors mastère spé externe
**Constraints** : `région:idf_lyon`, `budget:élevé (école payante)`, `valeurs:carrière_top_tier`, `pression:promo_compétitive`
**Tone** : tutoiement, ambitieux
**Sources priority** : APEC (master commerce spé→carrière), LinkedIn (alumni écoles), DARES (gains spécialisation), Top 5 mastères spé France
**Questions seed** :
- "M1 commerce, je vise quelle spé pour le meilleur ROI à 5-10 ans ?"
- "Mastère spécialisé externe (HEC, ESSEC) après mon école : ça vaut le coup ?"
- "Finance vs entrepreneuriat à 5 ans : taux de succès et risques réels ?"

### D3 — RNCP Bac+5 reconversion vers fonction publique — VOUVOIEMENT (statutaire)
**Persona** : 27 ans, BAC+5 secteur privé, veut reconversion fonction publique
**Context** : Lassé du privé (pression, mobilité), cherche stabilité publique, hésite catégorie A vs B vs concours spécialisé
**Constraints** : `région:variable`, `budget:moderate`, `valeurs:stabilité_utilité_publique`, `marché:concours_2026_2027`
**Tone** : **vouvoiement, pragmatique** (justifié v2 : statutaire concours)
**Sources priority** : **`Place de l'Emploi Public`** (ajout v2 — référence catégories B + concours), **`Choisir le service public`** (ajout v2 — concrets concours), Fonction publique (catégorie A), CNFPT, ENA/ENS PSL Saclay, France Travail (intégration FP), DARES (FP vs privé carrière)
**Questions seed** :
- "Avec mon bac+5, quels concours fonction publique sont les plus pertinents ?"
- "Catégorie A vs B : différences concrètes (salaire, missions, mobilité) ?"
- "Préparation concours : prépa privée, CNED, ou auto-formation ?"

### D4 — Mastère spé ingé, vraie value ?
**Persona** : 24 ans, école d'ingé sortie diplômée, hésite mastère spé pour différenciation
**Context** : Mastère spécialisé (data science, finance, sustainability) après école d'ingé classique : vrai gain ou marketing ?
**Constraints** : `région:idf`, `budget:élevé (mastère payant 12-25k€)`, `valeurs:carrière_dual_compétence`
**Tone** : tutoiement, critique (24 ans, recadré v2)
**Sources priority** : APEC (gains mastère spé), CGE (Conférence Grandes Écoles), témoignages anciens, classements indépendants
**Questions seed** :
- "Mastère spé data science après école d'ingé, ROI réel sur 5 ans ?"
- "Quels sont les mastères spé qui valent vraiment leurs 15-25k€ ?"
- "Mastère spé en France vs MS étranger (UK, US) pour profil ingé ?"

### D5 — Doctorat/recherche vs industrie
**Persona** : 23 ans, fin master 2 sciences/sciences sociales, choix doctorat ou industrie direct
**Context** : Excellent dossier, tentation académique mais marché concours universitaires bouché
**Constraints** : `région:variable`, `budget:à_financer (bourse_thèse)`, `valeurs:passion_recherche_vs_pragmatisme`
**Tone** : tutoiement, analytique (23 ans, recadré v2)
**Sources priority** : ABG (Bernard Grégory), CNRS (recrutement chercheurs), APEC (carrière docteurs), DARES (recrutements universités 2026)
**Questions seed** :
- "Doctorat vs industrie direct, quel choix pour bon profil sciences ?"
- "Marché des concours universitaires en France 2026, vraiment bouché ?"
- "Doctorat industriel CIFRE, alternative concrète au doctorat académique ?"

### D6 — Master science-po vs école commerce
**Persona** : 22 ans, fin licence sciences-po IEP, choix master Sciences-Po Paris vs école commerce M2
**Context** : Profil ambition publique mais hésite vers business + cosmopolite
**Constraints** : `région:idf`, `budget:très_élevé`, `valeurs:influence_société_vs_business`, `pression:réseau_à_construire`
**Tone** : tutoiement, stratégique (22 ans, recadré v2)
**Sources priority** : APEC, Sciences-Po Paris (carrières alumni), HEC/ESSEC/ESCP carrières alumni, DARES (gain salarial à 10 ans)
**Questions seed** :
- "Sciences-Po Paris master ou HEC/ESSEC : carrière + salaire à 10 ans ?"
- "Si je vise haute fonction publique, Sciences-Po est-il indispensable ?"
- "École commerce + Sciences-Po (en MS), réaliste à mon stade ?"

### D7 — MBA jeune (25 ans), intérêt — VOUVOIEMENT (corporate)
**Persona** : 25 ans, 3 ans pro post-école commerce, veut booster carrière via MBA
**Context** : MBA accélèrent réseau et salaire mais coût (60-130k€) et opportunité (1-2 ans hors marché)
**Constraints** : `région:idf_lyon_us_uk`, `budget:très_élevé (prêt étudiant)`, `valeurs:carrière_internationale`
**Tone** : **vouvoiement, business** (justifié v2 : statutaire corporate haut niveau)
**Sources priority** : APEC (MBA carrière), classements MBA (FT, QS), témoignages alumni MBA français
**Questions seed** :
- "MBA à 25 ans, est-ce trop tôt pour un retour optimal ?"
- "INSEAD vs HEC vs Stanford à 25 ans : ROI estimé sur 10 ans ?"
- "Prêt étudiant 100k€ pour MBA, comment évaluer si ça vaut le coup pour mon profil ?"

### D8 — Validation acquis (VAE) bac+5 sans master — VOUVOIEMENT (statutaire)
**Persona** : 30 ans, 5 ans pro, veut Bac+5 via VAE sans refaire école
**Context** : Marché demande Bac+5 pour postes seniors, pratique l'expérience nécessite validation formelle
**Constraints** : `région:variable`, `budget:moderate (VAE coût modéré)`, `urgence:promotion_à_5_ans`, `valeurs:reconnaissance_diplôme`
**Tone** : **vouvoiement, structuré** (justifié v2 : 30 ans + statutaire VAE)
**Sources priority** : France VAE, France Compétences (RNCP), CNED, France Travail (VAE accompagnement)
**Questions seed** :
- "VAE master en RH, comment ça marche concrètement et combien de temps ?"
- "Coût + temps total VAE bac+5 pour profil expérimenté ?"
- "VAE est-elle vraiment reconnue par les recruteurs vs un master classique ?"

---

## E. Cas familiaux/sociaux (8 prompts) — Transversal

### E1 — Parent angoissé 1er enfant Parcoursup — VOUVOIEMENT (parent)
**Persona** : Parent ~45 ans, premier enfant en terminale, méconnaissance Parcoursup
**Context** : Veut accompagner son enfant sans le pousser, hésite informer/éduquer/rassurer
**Constraints** : `parent_côté`, `budget:variable`, `valeurs:réussite_enfant_sans_pression`, `méconnaissance:filières_actuelles`
**Tone** : vouvoiement, attentionné (justifié : profil parent 45 ans)
**Sources priority** : Parcoursup (parents), CIDJ (parents), ONISEP (parents)
**Questions seed** :
- "Mon enfant fait Parcoursup, comment l'accompagner sans le stresser ?"
- "Quels sont les pièges classiques de Parcoursup que les parents doivent connaître ?"
- "Filière X au lycée → quelles voies post-bac envisager pour mon enfant ?"

### E2 — Boursière échelon 7, mobilité limitée
**Persona** : 17 ans, lycée public, boursière échelon 7 maximum
**Context** : Très limitée géographiquement (proche domicile), budget zéro
**Constraints** : `région:proche_lycée`, `budget:très_bas`, `bourse:échelon_7`, `mobilité:transports_publics`
**Tone** : tutoiement, valorisant
**Sources priority** : CROUS (bourses + logement), Pôle Emploi (formations financées), associations (École Z, Frateli, etc.), France Travail (apprentissage payé), **`1jeune1solution.gouv.fr`** (ajout v2)
**Questions seed** :
- "Boursière échelon 7, comment financer mes études supérieures sans bouger ?"
- "Apprentissage rémunéré post-bac, quelles aides cumulables ?"
- "Cumul bourse échelon 7 + APL : combien je peux toucher au total ?"

### E3 — Handicap moteur école accessible
**Persona** : 18-22 ans, handicap moteur (visible/non-visible)
**Context** : Études sup envisageables mais besoin écoles accessibles + accompagnement humain
**Constraints** : `handicap:moteur`, `région:variable`, `valeurs:autonomie_dignité`, `mobilité:transports_adaptés`
**Tone** : tutoiement, attentionné (recadré v2 : 18-22 ans tutoiement coach)
**Sources priority** : **`MonParcoursHandicap.gouv.fr`** (ajout v2 — plateforme État principale), ONISEP handicap, AGEFIPH, MDPH, témoignages associations étudiants handicapés
**Questions seed** :
- "Quelles écoles d'ingénieur sont vraiment accessibles aux étudiants en fauteuil ?"
- "Comment obtenir un assistant pédagogique en master ?"
- "Stage en entreprise avec mon handicap, comment trouver des entreprises ouvertes ?"

### E4 — Mineur DOM-TOM, métropole
**Persona** : 17 ans, lycée Réunion / Antilles / Polynésie / Guyane / Mayotte
**Context** : Mobilité métropole pour études sup, choc culturel + financier potentiel
**Constraints** : `région:DOM-TOM_origine`, `budget:familial_modéré`, `mobilité:transition_vers_métropole`, `valeurs:retour_aux_sources_éventuel`
**Tone** : tutoiement, ouverture culturelle
**Sources priority** : Parcoursup (DOM-TOM aide mobilité), CROUS (logement métropole), France Travail (formations DOM-TOM), ONISEP (vie étudiante métropole)
**Questions seed** :
- "Je suis à La Réunion en terminale, comment préparer mon arrivée à Paris ?"
- "Quelles aides spécifiques aux étudiants ultramarins en métropole ?"
- "Si je veux revenir aux Antilles plus tard, comment construire mon parcours ?"

### E5 — Famille modeste, prudence financière
**Persona** : 18 ans, famille modeste province, prudence financière intuitive
**Context** : Conseille toujours BTS/BUT car "rapide et concret", famille craint chômage avec longs études
**Constraints** : `région:province`, `budget:bas_familial`, `valeurs:emploi_stable_rapide`, `pression:famille_pragmatique`
**Tone** : tutoiement, équilibré
**Sources priority** : DARES (insertion BTS/BUT), Parcoursup (parcours alternatives), témoignages anciens BTS/BUT vs licence générale
**Questions seed** :
- "Ma famille me pousse BTS pour 'la sécurité', mais j'aimerais autre chose, comment décider ?"
- "BTS/BUT garantissent vraiment plus de sécurité ?"
- "Si je fais une licence puis master, le risque de chômage est-il vraiment plus élevé ?"

### E6 — Étudiant migrant équivalences diplôme étranger — VOUVOIEMENT (statutaire)
**Persona** : 19-23 ans, diplôme étranger (sub-saharien, Maghreb, Asie, Europe Est), arrivée France
**Context** : Veut continuer études en France, équivalences complexes, démarches administratives lourdes
**Constraints** : `pays_origine:variable`, `région:idf_ou_grande_ville`, `budget:bas`, `urgence:visa_étudiant`
**Tone** : vouvoiement, structuré (justifié : démarches statutaires lourdes)
**Sources priority** : Campus France (équivalences pays origine), ENIC-NARIC, CROUS (aides étudiants étrangers), DAEU (diplôme accès études universitaires)
**Questions seed** :
- "J'ai un diplôme étranger, comment je le fais reconnaître pour entrer à la fac française ?"
- "Visa étudiant + études + travail à temps partiel, comment ça s'organise ?"
- "Quelles aides spécifiques aux étudiants étrangers (boursiers et non-boursiers) ?"

### E7 — Conflit parents (parent pousse droit, étudiant veut arts)
**Persona** : 17 ans, terminale, conflit fort avec parent qui pousse vers droit/médecine alors que passion arts
**Context** : Tension émotionnelle, peur de décevoir vs peur de regretter
**Constraints** : `région:variable`, `budget:moderate (parents financent)`, `valeurs:authenticité_vs_loyalité`, `émotion:angoisse_familiale`
**Tone** : tutoiement, soutenant
**Sources priority** : ONISEP (filières arts), Beaux-Arts (concours, écoles), DARES (insertion arts), témoignages reconversion arts→stable
**Questions seed** :
- "Mes parents me poussent vers le droit, mais je veux faire les Beaux-Arts, comment leur faire accepter ?"
- "Filières arts ont-elles vraiment des débouchés stables ?"
- "Si je fais arts, quelles voies hybrides existent pour rassurer mes parents ?"

### E8 — Étudiant sportif haut niveau, gestion études+sport
**Persona** : 18-22 ans, sportif niveau pro/semi-pro
**Context** : Peut-être sélectionné équipe nationale, gestion temps + concours universitaires
**Constraints** : `région:proche_centre_entraînement`, `budget:modéré (sponsoring partiel)`, `valeurs:double_carrière`, `mobilité:contraintes_compétitions`
**Tone** : tutoiement, motivant
**Sources priority** : INSEP (sport haut niveau études), Université Sportive Excellence, AS-AOSI, ONISEP (parcours sport-études)
**Questions seed** :
- "Je suis en équipe de France junior, comment concilier études et entraînements ?"
- "Aménagements universitaires sport haut niveau, comment les obtenir ?"
- "Si ma carrière sportive ne décolle pas, quelles voies de reconversion via mes études ?"

---

## F. Questions méta-conseil (6 prompts) — Transversal

### F1 — "J'aime telles matières mais je veux gagner X€/mois"
**Persona** : 17-25 ans, conscient du marché, raisonneur économique
**Context** : Recherche profit + alignement intérêt, parfois en conflit
**Constraints** : `région:variable`, `valeurs:rentabilité_vs_passion`, `style:franc_du_collier`
**Tone** : tutoiement, équilibré
**Sources priority** : APEC (salaires par métier), DARES (rémunérations sectorielles), France Travail (top métiers payés), LinkedIn Salary Insights
**Questions seed** :
- "J'aime les sciences humaines mais je veux 4000€/mois à 30 ans, c'est conciliable ?"
- "Pour un profil littéraire, quels métiers paient le plus à 5 ans d'expérience ?"
- "Est-ce que la passion compte plus que l'argent à 25 ans ? Et après ?"

### F2 — "Je veux du concret, pas de théorie"
**Persona** : 17-22 ans, allergie cours magistraux abstraits
**Context** : Préfère apprendre par la pratique, terrain, application
**Constraints** : `région:variable`, `valeurs:concret_terrain`, `style:hands_on`
**Tone** : tutoiement, direct
**Sources priority** : ONISEP (alternance, BUT, BTS), Parcoursup (formations terrain), France Travail (apprentissage), CFA, **`alternance.emploi.gouv.fr`** (ajout v2)
**Questions seed** :
- "Je déteste les cours magistraux et la théorie, quelles formations sont 100% terrain ?"
- "L'apprentissage est-il vraiment plus concret que les études classiques ?"
- "Quelles études supérieures intègrent vraiment la pratique dès la 1ère année ?"
- "[Test set v3 Q4] C'est quoi une licence universitaire en France ?"
- "[Test set v3 Q6] Quelles bonnes formations existent à Perpignan ?"

### F3 — "Quelle est la voie qui paie le plus en sortie d'école ?"
**Persona** : 18-22 ans, ambition financière forte, prêt à investir énergie
**Context** : Optimise pour le revenu de sortie, sans nécessairement passion intrinsèque
**Constraints** : `région:idf_principalement`, `budget:à_investir`, `valeurs:performance_financière`
**Tone** : tutoiement, business
**Sources priority** : APEC (top salaires sortie école), DARES (palmarès écoles par salaire), classements mondiaux écoles
**Questions seed** :
- "Quelles études paient le mieux à la sortie en France en 2026 ?"
- "École de commerce vs ingé vs droit pour les hauts salaires : que choisir ?"
- "Top 10 des métiers les mieux payés à 25 ans en France actuellement ?"

### F4 — "IA / data, hype ou vraie carrière ?"
**Persona** : 18-25 ans, conscient du hype IA/data, sceptique
**Context** : Veut savoir si vraie carrière long terme ou bulle marketing
**Constraints** : `région:idf_lyon_principalement`, `budget:formation_à_évaluer`, `valeurs:lucidité_marché`
**Tone** : tutoiement, analytique
**Sources priority** : APEC (data scientists insertion 2026), DARES (évolution emplois IA), articles tech (Stack Overflow, Hacker News), France Travail tendances métiers
**Questions seed** :
- "Data scientist en 2026, vraie carrière ou bulle marketing ?"
- "IA / ML : quelles formations sont solides et quelles sont des arnaques ?"
- "Saturation prévue du marché data à 5 ans en France, c'est probable ?"

### F5 — "École privée vs université publique, mon profil ?"
**Persona** : 17-22 ans, dilemma classique privé/public
**Context** : Privé coûte cher mais réseau + cadre, public moins cher mais grand-anonymat
**Constraints** : `région:variable`, `budget:variable`, `valeurs:rapport_coût_qualité`
**Tone** : tutoiement, comparatif
**Sources priority** : APEC (carrière privé vs public), DARES (taux insertion), classements indépendants (L'Étudiant, Le Monde), enquêtes alumni
**Questions seed** :
- "École privée coûte 60k€, université publique presque rien, ça vaut vraiment la peine ?"
- "Réseau alumni école privée vs grande université publique : différence concrète à 5 ans ?"
- "Pour un profil moyen-supérieur, le privé apporte-t-il un vrai gain ?"

### F6 — "Année de césure / gap year, bonne idée ?"
**Persona** : 18-22 ans, fatigué des études, envie de respirer
**Context** : Gap year peut booster ou retarder, dépend du projet
**Constraints** : `région:variable`, `budget:à_financer (job pays / aide)`, `valeurs:expérience_humaine`, `pression:famille_inquiète`
**Tone** : tutoiement, équilibré
**Sources priority** : Service Civique, Erasmus+ stages, WWOOF, Parcoursup (césure), témoignages gap years réussis vs ratés
**Questions seed** :
- "Gap year après le bac : freine ma carrière ou la booste vraiment ?"
- "Quelles options concrètes pour un gap year utile (Service Civique, voyage, stage) ?"
- "Comment expliquer un gap year aux recruteurs sans paraître flemmard ?"

---

## G. Profils non-cadre classique (3 prompts NOUVEAUX v2) — Transversal

### G1 — Décrocheur 16-18 ans (NOUVEAU v2)
**Persona** : 16-18 ans, sorti du système scolaire sans diplôme, perdu, souvent en rupture familiale ou sociale
**Context** : Pas de diplôme, parfois domicile instable. Cherche un cadre qui réintègre (Missions Locales, École de la 2e Chance, Service Militaire Volontaire) avec accompagnement humain fort
**Constraints** : `âge:16_18`, `diplôme:aucun`, `émotion:rupture_perte_repères`, `urgence:réintégration`, `mobilité:limitée_souvent`
**Tone** : tutoiement, soutien direct (pas paternaliste)
**Sources priority** : **Missions Locales** (réseau national), **`reseau-e2c.fr`** (École de la 2e Chance), **SMV** (Service Militaire Volontaire), **`1jeune1solution.gouv.fr`**, France Travail (Garantie Jeunes / Contrat d'Engagement Jeune)
**Questions seed** :
- "J'ai arrêté l'école à 16 ans, qu'est-ce que je peux faire maintenant ?"
- "Mission Locale, E2C, SMV : c'est quoi la différence concrètement ?"
- "Sans diplôme, comment je peux gagner ma vie en repartant ?"
- "[Phrasing brut] J'sais pas où aller, tout le monde dit que je suis foutu"
- "Le Service Militaire Volontaire, ça paie vraiment et ça donne quoi à la fin ?"

### G2 — Neuroatypique DYS / TDAH (NOUVEAU v2)
**Persona** : 17-25 ans, capacités intellectuelles solides MAIS DYS (dyslexie, dysorthographie, dyscalculie) ou TDAH
**Context** : Craint le système universitaire classique (amphis bondés bruyants, évaluations écrites longues, prise de notes rapide). Cherche écoles à fort accompagnement, contrôle continu, ou pédagogie alternative
**Constraints** : `neuroatypie:dys_ou_tdah`, `âge:17_25`, `valeurs:accompagnement_humain`, `craintes:amphis_bondés_évaluations_chronométrées`
**Tone** : tutoiement, déculpabilisant (les neuroatypiques entendent souvent qu'ils "ne s'appliquent pas")
**Sources priority** : **`MonParcoursHandicap.gouv.fr`** (RQTH étudiant + aménagements), MDPH (tiers temps + secrétariat), ONISEP (formations adaptées), **Fédération Française des DYS**, témoignages associations (HyperSupers TDAH France, Apedys), **écoles pédagogie active** (Steiner-Waldorf supérieur, Mons en Bareul, etc.)
**Questions seed** :
- "Je suis TDAH, comment survivre à la fac sans me cramer ?"
- "Dyslexique, quels aménagements je peux demander en école d'ingé ?"
- "Quelles formations sup ont vraiment un suivi adapté pour DYS / TDAH ?"
- "Tiers temps aux examens, c'est automatique ou faut le demander où ?"
- "[Phrasing brut] J'ai un cerveau qui marche pas comme les autres, tout le monde me dit de m'appliquer mais ça suffit pas"

### G3 — Rural / Agricole isolé (NOUVEAU v2)
**Persona** : 17 ans, lycée rural département isolé (Creuse, Lozère, Cantal, Ariège, Aveyron, etc.), grande exploitation agricole familiale ou village 500 habitants
**Context** : **Auto-censure forte** ("les grandes écoles c'est pour Paris, pas pour moi"), **transport** (pas de permis, pas de gare proche), **logement métropole inconnu**. Souvent 1ère génération étudiante de la famille
**Constraints** : `région:rural_isolé`, `transport:pas_permis`, `budget:bas`, `auto_censure:fort`, `1ère_génération_étudiante:probable`
**Tone** : tutoiement, valorisant explicitement (anti auto-censure)
**Sources priority** : **`1jeune1solution.gouv.fr`** (mobilité rurale), CROUS (logement métropole), associations dédiées (**Cordées de la Réussite**, **Frateli**, **Article 1**), Parcoursup (filières rurales/agricoles), ONISEP (témoignages 1ère génération étudiante), France Travail (aides mobilité rurale → métropole)
**Questions seed** :
- "Je suis dans un village de 500 habitants, comment je fais pour étudier à Paris ou Toulouse ?"
- "Mes parents ont une ferme, est-ce que je dois reprendre l'exploitation ou partir étudier ?"
- "Sciences-Po Paris pour quelqu'un de rural, c'est vraiment possible ?"
- "Comment payer le permis ET le logement étudiant, c'est trop cher en cumul"
- "[Phrasing brut] Personne dans ma famille n'a fait d'études, j'ai peur de pas y arriver à la fac"
- "[Test set v3 Q6] Quelles bonnes formations existent à Perpignan ?"

---

## 📌 Annexe — Mapping questions test set user_test_v3 vers prompts cibles

Les 10 questions du test set v3 (`results/user_test_v3/answers_to_show.md`) ont été testées par les 5 profils humains (Léo 17, Sarah 20, Thomas 23, Catherine 52, Dominique 48). À intégrer comme seeds réelles dans les prompts ci-dessous lors de la conversion YAML par Claudette :

| # | Question test set | Prompts cibles | Remarques retours humains |
|---|-------------------|----------------|---------------------------|
| Q1 | "J'ai 11 de moyenne en terminale générale, est-ce que je peux intégrer HEC ?" | A2 | Léo +1 sur clarté tour 2. Sarah note erreur persistante "Tremplin/Passerelle" pour HEC |
| Q2 | "Quelles sont les meilleures formations en cybersécurité en France ?" | A1 (fusion) | Léo +2 clarté, "vraie progression" |
| Q3 | "Compare ENSEIRB-MATMECA et EPITA pour la cybersécurité" | A1 (fusion) | Tableau apprécié, mais "EPITA 8 500€/an" erreur (réalité 10 500€) |
| Q4 | "C'est quoi une licence universitaire en France ?" | F2 | Léo et Sarah : "plus court et propre v3" |
| Q5 | "Je suis en L2 droit et je veux me réorienter vers l'informatique, comment ?" | B1 | 646 mots = trop long. VAE persistance erreur signalée |
| Q6 | "Quelles bonnes formations existent à Perpignan ?" | G3 (rural), A8 (boursier proximité) | "Périgueux 3h30 hallucination corrigée v3" |
| Q7 | "Je veux devenir médecin, comment faire ?" | A6 | "Bac S supprimé persiste" (depuis 2021) |
| Q8 | "J'ai 12 de moyenne générale en terminale, est-ce que j'ai mes chances en PASS ?" | A6 | Bug technique : "liens cassés vers github.com" |
| Q9 | "Compare devenir infirmier et kinésithérapeute" | A6, B2 | Tableau cassé en cours de rendu = régression UX |
| Q10 | "Je suis en L2 psychologie et je veux me réorienter vers l'orthophonie, comment ?" | B2 | Erreur grave : "concours candidat libre" alors qu'orthophonie sur Parcoursup depuis 2020 |

**Phrasings humains à embarquer** (depuis profils Léo 17, Sarah 20) pour les seeds "argot/angoisse brute" :

- Léo (lycéen) : "ma meuf veut médecine pas moi", "j'sais pas où aller", "Tremplin/Passerelle/AST que je comprends toujours pas", "C'est sérieux ? Au tour précédent ça marchait"
- Sarah (L2 LEA réo) : "Ma L2 langues va nulle part j'ai envie de tout plaquer", "j'peux pas distinguer un lien légitime d'un faux", "tout le monde dit que ça mène à rien"
- Thomas (M1 finance, 23) : "M1 finance, fintech vs banque traditionnelle pour la suite ?"
- Catherine (52, parent) : "Mon fils va sur Parcoursup, c'est moi qui panique plus que lui"

---

## ✅ Prochaines étapes après ta validation finale v2

1. **Tu valides cette v2 sur Telegram** → je ferme le loop avec Claudette
2. **Conversion en YAML par Claudette** dans le repo OrientIA (`config/diverse_prompts_50.yaml`) lors de l'Ordre 2/2
   - Étend les seeds à 5-6 par prompt en intégrant les questions test set v3 + phrasings humains (cf annexe)
3. **Dispatch Ordre 2/2** Sprint 9-data cet après-midi
4. **Lancement génération nuit 28-29** via Task tool sub-agents Opus 4.7
5. **Surveillance Jarvis nuit + report matin 7h**
