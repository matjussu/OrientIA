# 🎯 Projet INRIA AI Grand Challenge — Outil IA d'Orientation Spécialisé

> **Objectif** : Démontrer empiriquement qu'un système RAG spécialisé avec re-ranking par labels institutionnels produit des réponses radicalement meilleures pour l'orientation des étudiants français que les LLM généralistes.

> **Thèse centrale** : Avec le même modèle de base, la bonne architecture de retrieval et le bon prompt system réduisent le biais marketing, augmentent le réalisme et améliorent l'agentivité des réponses d'orientation.

---

## 📋 Table des matières

1. [Contexte et problème](#1-contexte-et-problème)
2. [Stratégie technique retenue](#2-stratégie-technique-retenue)
3. [Étape 1 — Collecte et structuration des données](#3-étape-1--collecte-et-structuration-des-données)
4. [Étape 2 — System prompt spécialisé](#4-étape-2--system-prompt-spécialisé)
5. [Étape 3 — Pipeline RAG](#5-étape-3--pipeline-rag)
6. [Étape 4 — Benchmark comparatif](#6-étape-4--benchmark-comparatif)
7. [Étape 5 — Interface et démo](#7-étape-5--interface-et-démo)
8. [Architecture technique complète](#8-architecture-technique-complète)
9. [Sources de données détaillées](#9-sources-de-données-détaillées)
10. [Arguments clés pour le jury](#10-arguments-clés-pour-le-jury)

---

## 1. Contexte et problème

### Le constat (résumé du dossier)

- **Fracture d'information structurelle** : la qualité de l'orientation dépend du lycée, du réseau familial et du code postal. 25% de vœux sélectifs en aire parisienne vs 10% en commune isolée.
- **Système public saturé** : 1 PsyEN pour 1 500 élèves (recommandation européenne : 1 pour 1 000). 63% des lycées ne peuvent pas recevoir individuellement tous les Terminales.
- **Usage massif non encadré** : 86% des étudiants utilisent l'IA, 42% des 18-25 ans quotidiennement. L'IA est devenue le conseiller d'orientation de facto.
- **Biais marketing** : les LLM généralistes recommandent les formations avec le meilleur SEO, pas les meilleures formations. Exemple : "formations cybersécurité" → écoles privées au lieu des formations SecNumEdu ANSSI.
- **Absence de réalisme** : les LLM généralistes sont des "yes-men" qui disent "tout est possible" sans utiliser les données de sélectivité.

### Ce qu'on propose

Un outil public d'orientation par IA, spécialisé sur le système éducatif français, qui prouve par un benchmark comparatif que la spécialisation produit des réponses supérieures sur 6 critères mesurables.

---

## 2. Stratégie technique retenue

### RAG seul (pas de fine-tuning) — Justification

**Pourquoi RAG :**
- Les données Parcoursup changent chaque année → le RAG se met à jour sans ré-entraînement
- Les données sont factuelles et structurées (chiffres, taux, labels) → exactement ce que le RAG gère le mieux
- Chaque réponse est traçable jusqu'à sa source → argument transparence AI Act
- Déployable en quelques jours, coût quasi nul

**Pourquoi pas de fine-tuning :**
- Le fine-tuning est bon pour apprendre un style/raisonnement, pas pour mémoriser des données factuelles — il hallucinera les chiffres
- Coût et temps de préparation du dataset non justifiés pour un prototype
- Brouille le message scientifique : on ne peut plus isoler ce qui produit l'amélioration

**Référence recherche :**
- Paper arXiv 2401.08406 : RAG + fine-tuning sont cumulatifs (+6pp fine-tuning, +5pp RAG), mais le RAG seul donne déjà 80% du résultat
- Paper arXiv 2403.01432 : RAG surpasse systématiquement le fine-tuning, surtout combiné, mais l'avantage de la combinaison diminue sur les gros modèles
- RAFT (UC Berkeley) : le meilleur combo entraîne le modèle à raisonner sur le contexte récupéré, mais c'est hors scope pour un prototype

**Mention future :** Dans la conclusion du dossier, mentionner que "une amélioration future serait d'appliquer l'approche RAFT pour entraîner le modèle à mieux exploiter le contexte récupéré."

### Modèle choisi : Mistral via API

**Raisons :**
- **Souveraineté** : entreprise française, hébergement conforme RGPD, résidence des données dans l'UE
- **Coût** : free tier avec 1 milliard de tokens/mois, pas de carte de crédit requise
- **Pricing API** : Small 3.1 à $0.20/$0.60 par million de tokens, Medium 3 à $1/$3, Large 3 à $2/$6
- **RAG natif** : Agents API avec Document Library intégrée
- **Embeddings** : modèle `mistral-embed` pour vectoriser les documents
- **Open source** : argument auditabilité pour l'INRIA

---

## 3. Étape 1 — Collecte et structuration des données

### Sources de données disponibles

#### Source A — ONISEP Open Data
- **URL** : `api.opendata.onisep.fr`
- **Référencé sur** : `api.gouv.fr/les-api/api-onisep` et `data.gouv.fr`
- **Datasets clés** :
  - Formations initiales en France (code `5fa591127f501`) : **5 869 formations**, champs : type, durée, niveau de sortie, code RNCP, tutelle, domaine/sous-domaine, URL fiche ONISEP
  - Référentiel métiers (`5fa5949243f97`) : **1 000+ métiers** avec correspondance ROME et GFE
  - Idéo-fiches-métiers (format XML) : **~800 fiches rubriquées complètes**
- **Authentification** : gratuite, créer un compte → token JWT
- **Limite** : 5 requêtes/jour sans auth, illimité avec token
- **Alternative** : téléchargement bulk en CSV/JSON depuis data.gouv.fr

#### Source B — Parcoursup Open Data
- **URL** : `data.education.gouv.fr/explore/dataset/fr-esr-parcoursup/`
- **Téléchargement** : CSV direct depuis data.gouv.fr
- **Contenu** : **14 252 formations** (campagne 2025), 1 015 200 candidats
- **Champs critiques** : taux d'accès, profil des admis (bac général/techno/pro, mentions), nombre de places, répartition géographique des candidats
- **Cartographie** : dataset complémentaire avec géolocalisation de toutes les formations 2020-2026, mis à jour quotidiennement
- **⭐ Donnée la plus importante** : le taux d'accès par formation = base du réalisme

#### Source C — ROME 4.0 (France Travail)
- **URL** : `francetravail.io/data/api/rome-4-0-competences`
- **Téléchargement** : `francetravail.org/opendata/repertoire-operationnel-des-meti.html`
- **Contenu** : **1 584 fiches métiers** (objectif 2 000 en 2026)
- **Structure** : 507 macro-compétences, 17 825 savoir-faire, 15 383 savoirs, 179 contextes de travail
- **4 API** : compétences, contextes de travail, fiches métiers, savoirs
- **API ROMEO** : IA NLP qui rapproche un texte libre à des métiers/compétences ROME — potentiellement intégrable dans le pipeline pour convertir les intérêts de l'étudiant en métiers ROME
- **URL ROMEO** : `francetravail.io/data/api/romeo-2`

#### Source D — Labels officiels ANSSI SecNumEdu
- **URL** : `cyber.gouv.fr/secnumedu`
- **Contenu** : ~80 formations initiales labellisées en cybersécurité
- **Format** : page web + PDFs, à structurer manuellement (~1h)
- **Exemples de formations labellisées** : ENSIBS (3 formations), Télécom Paris, CyberSchool (Univ. Rennes), ENSSAT, INSA Centre Val de Loire, Télécom SudParis, EURECOM, IMT Atlantique
- **Utilité** : preuve directe du biais marketing (ces formations n'apparaissent pas dans les réponses de ChatGPT)

#### Source E — Données complémentaires
- **INSEE** : emploi/salaires par territoire et par métier
- **France Travail - Data Emploi** : tensions de recrutement par métier et par région
- **France Compétences** : RNCP (certifications)
- **MCP data.gouv** : déjà créé (mentionné dans le dossier)

### Format cible des fiches structurées

Chaque formation dans la base RAG doit suivre ce schéma :

```
FICHE FORMATION:
- id: "parcoursup_12345"
- nom: "Master Cybersécurité - CyberSchool"
- etablissement: "Université de Rennes"
- ville: "Rennes"
- region: "Bretagne"
- type_diplome: "Master"
- statut: "Public"
- labels: ["SecNumEdu ANSSI", "Grade Master"]
- taux_acces_parcoursup_2025: 18
- nombre_places: 30
- profil_admis:
    bac_general_pct: 85
    mention_minimum: "Bien"
- cout_annuel_euros: 250
- duree: "2 ans"
- debouches: ["Analyste SOC", "Pentester", "RSSI", "Consultant cybersécurité"]
- codes_rome: ["M1802", "M1805"]
- url_onisep: "https://..."
- url_parcoursup: "https://..."
- source: "Parcoursup 2025 + ANSSI SecNumEdu"
```

### Scope du prototype

**Ne PAS essayer de couvrir les 14 000 formations.** Se concentrer sur **3-4 domaines** :
1. **Cybersécurité** (~80 formations SecNumEdu + formations non labellisées pour comparaison)
2. **Data / IA** (~50-80 formations)
3. **Commerce / Finance** (~50-80 formations)
4. **Droit** (~30-50 formations)

Total cible : **200-300 fiches bien structurées**. C'est suffisant pour prouver le concept.

### Données synthétiques

Utilisées UNIQUEMENT pour le **jeu d'évaluation** (pas pour l'entraînement) :
- Prendre 30 formations réelles
- Générer 5-10 questions qu'un lycéen poserait sur chacune
- Rédiger les "réponses idéales" à partir des données officielles
- Méthodologie transparente et acceptée en recherche

---

## 4. Étape 2 — System prompt spécialisé

### Architecture en 4 couches

#### Couche 1 — Identité et mission

```
Tu es un conseiller d'orientation spécialisé dans le système éducatif français. 
Tu aides les lycéens et étudiants à explorer des formations et des métiers en 
t'appuyant EXCLUSIVEMENT sur des données officielles vérifiables.

Tu n'es PAS un moteur de recherche web. Tu ne recommandes JAMAIS une formation 
sur la base de sa visibilité en ligne. Tu privilégies les critères objectifs : 
labels officiels (SecNumEdu ANSSI, grade Licence/Master délivré par l'État, 
habilitation CTI, accréditation CGE), taux d'accès Parcoursup, taux d'insertion 
professionnelle, coût réel de la formation.
```

#### Couche 2 — Règles de comportement (le différenciateur)

```
NEUTRALITÉ :
- Quand tu listes des formations, inclus TOUJOURS les formations publiques 
  labellisées avant les formations privées non labellisées.
- Si une formation possède un label officiel (SecNumEdu, CTI, CGE, grade Master), 
  mentionne-le systématiquement.
- Ne reproduis JAMAIS le biais marketing : une école avec un bon SEO n'est pas 
  une meilleure école.

RÉALISME :
- Utilise les taux d'accès Parcoursup pour évaluer la faisabilité.
  - Taux < 10% : "Formation extrêmement sélective"
  - Taux 10-30% : "Formation sélective"  
  - Taux 30-60% : "Formation modérément sélective"
  - Taux > 60% : "Formation accessible"
- Quand un étudiant vise une formation très sélective, propose TOUJOURS 
  des alternatives réalistes ET des passerelles pour y accéder plus tard.
- Ne dis JAMAIS "tout est possible avec de la motivation". Dis la vérité 
  avec bienveillance.

AGENTIVITÉ :
- Ne donne JAMAIS une réponse unique et fermée.
- Propose toujours 2-3 options avec les critères de choix expliqués.
- Termine par une question ouverte qui pousse l'étudiant à réfléchir 
  sur SES priorités (localisation, coût, débouchés, ambiance).
- Rappelle régulièrement que c'est l'étudiant qui décide, pas toi.

SOURÇAGE :
- Cite TOUJOURS la source de chaque donnée factuelle :
  "Selon Parcoursup 2025, cette formation a un taux d'accès de X%"
  "Cette formation est labellisée SecNumEdu par l'ANSSI"
  "D'après les données France Travail, ce métier recrute X personnes/an"
- Si tu ne trouves pas l'information dans tes données, dis-le 
  explicitement. Ne fabrique JAMAIS de chiffre.
```

#### Couche 3 — Format de sortie structuré

```
Pour chaque formation recommandée, structure ta réponse ainsi :

📍 [Nom de la formation] — [Établissement], [Ville]
• Type : [Licence/Master/Ingénieur/BTS/etc.] | Statut : [Public/Privé]
• Labels : [SecNumEdu/CTI/CGE/Grade Master/aucun]
• Sélectivité : [Taux d'accès Parcoursup X%]
• Coût : [Droits universitaires / X€ par an]
• Débouchés principaux : [Métiers ROME associés]
• Source : [Parcoursup 2025 / ONISEP / ANSSI]

Après les recommandations, ajoute TOUJOURS :
🔀 Passerelles possibles : [comment y accéder si le profil ne correspond 
   pas directement]
💡 Question pour toi : [question ouverte pour stimuler la réflexion]
```

#### Couche 4 — Garde-fous et cas limites

```
CAS LIMITES :
- Si l'étudiant semble en détresse, oriente vers Fil Santé Jeunes 
  (0 800 235 236) et suggère un conseiller humain.
- Si la question est hors orientation, recentre poliment.
- Si l'étudiant demande "quelle est LA meilleure formation", explique 
  qu'il n'existe pas de réponse unique.
- Si tu n'as pas de données sur une formation spécifique, dis-le 
  clairement et suggère ONISEP ou Parcoursup.
```

### Bonnes pratiques prompt engineering appliquées

- **Clarté et spécificité** : chaque instruction est actionnable, pas vague
- **Format explicite** : le modèle sait exactement comment structurer sa réponse
- **Persona sans sur-contrainte** : "conseiller d'orientation spécialisé" plutôt qu'un rôle trop restrictif
- **Garde-fous éthiques** : inspirés du framework MIND-SAFE pour les chatbots conseil
- **Température recommandée** : 0.3 (déterminisme pour les données factuelles, légère variabilité pour la formulation)

---

## 5. Étape 3 — Pipeline RAG

### Option recommandée : RAG maison avec FAISS

Plus impressionnante techniquement que l'Agents API, et permet le **re-ranking par labels** (l'innovation technique).

### Code de référence (Mistral docs)

```python
from mistralai import Mistral
import numpy as np
import faiss

client = Mistral(api_key="MISTRAL_API_KEY")

# 1. Charger et chunker les fiches formations
fiches = load_fiches_formations("data/formations.json")
chunks = [fiche_to_text(f) for f in fiches]

# 2. Créer les embeddings
def get_embeddings(texts):
    response = client.embeddings.create(
        model="mistral-embed",
        inputs=texts
    )
    return [e.embedding for e in response.data]

embeddings = get_embeddings(chunks)

# 3. Créer l'index FAISS (tourne sur CPU, pas besoin de GPU)
dimension = len(embeddings[0])
index = faiss.IndexFlatL2(dimension)
index.add(np.array(embeddings).astype('float32'))

# 4. Fonction de retrieval avec re-ranking par labels
def retrieve_and_rerank(question, k=10, boost_labeled=True):
    q_embedding = get_embeddings([question])[0]
    distances, indices = index.search(
        np.array([q_embedding]).astype('float32'), k
    )
    
    results = []
    for i, idx in enumerate(indices[0]):
        fiche = fiches[idx]
        score = 1 / (1 + distances[0][i])  # normaliser
        
        # RE-RANKING : boost les formations labellisées
        if boost_labeled and fiche.get("labels"):
            if "SecNumEdu" in fiche["labels"]:
                score *= 1.5
            if "CTI" in fiche["labels"] or "Grade Master" in fiche["labels"]:
                score *= 1.3
            if fiche["statut"] == "Public":
                score *= 1.1
        
        results.append({"fiche": fiche, "score": score})
    
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:5]

# 5. Génération avec contexte RAG
def generate_response(question):
    retrieved = retrieve_and_rerank(question)
    context = "\n\n".join([
        format_fiche(r["fiche"]) for r in retrieved
    ])
    
    response = client.chat.complete(
        model="mistral-medium-latest",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"""
Voici les données de référence pour répondre à la question :

{context}

Question de l'étudiant : {question}

Réponds en suivant le format spécifié dans tes instructions.
"""}
        ],
        temperature=0.3
    )
    return response.choices[0].message.content
```

### Le re-ranking : l'innovation technique

Le re-ranking par labels institutionnels est le **cœur de la contribution scientifique** :
- Les formations avec labels officiels (SecNumEdu, CTI, CGE) sont boostées dans le score de similarité
- Les formations publiques sont légèrement favorisées par rapport aux privées sans label
- Ce mécanisme corrige directement le biais marketing identifié en Partie 2 du dossier

C'est une **contribution mesurable et reproductible** : "Nous démontrons que l'ajout d'un re-ranking par labels institutionnels augmente de X% la proportion de formations publiques labellisées dans les recommandations."

### Stack technique

```
[Interface web React — Vercel (gratuit)]
    ↓
[API Backend Python/FastAPI — Railway ou Vercel Serverless]
    ↓
[FAISS index (CPU) — fiches formations vectorisées]
    ↓
[API Mistral — mistral-medium-latest + mistral-embed]
```

Coût total : ~0€ (free tiers Mistral + Vercel + Railway)

---

## 6. Étape 4 — Benchmark comparatif

### Méthodologie : LLM-as-a-Judge

3 systèmes évalués sur les mêmes 30 questions :
1. **Notre outil** : Mistral + RAG spécialisé + re-ranking
2. **Mistral brut** : même modèle, sans RAG (baseline technique)
3. **ChatGPT** : réponses pré-enregistrées (ou API si budget)

Évaluation par un **LLM juge externe** (Claude ou GPT-4 — PAS Mistral pour éviter le self-preference bias).

### Les 30 questions

#### Catégorie A — Biais marketing (5 questions)
1. "Quelles sont les meilleures formations en cybersécurité en France ?"
2. "Je veux faire une école de commerce, lesquelles me recommandes-tu ?"
3. "Quelles écoles d'ingénieur informatique choisir ?"
4. "Je cherche un master en intelligence artificielle, que recommandes-tu ?"
5. "Quelles sont les meilleures formations en data science ?"

#### Catégorie B — Réalisme (5 questions)
6. "J'ai 11 de moyenne en terminale générale, est-ce que je peux intégrer HEC ?"
7. "Je suis en bac pro commerce, je veux faire médecine, c'est possible ?"
8. "J'ai un bac techno STI2D, je peux aller en prépa MP ?"
9. "Je veux intégrer l'X avec un dossier moyen, comment faire ?"
10. "J'ai 13 de moyenne, est-ce que Sciences Po Paris est réaliste ?"

#### Catégorie C — Découverte de métiers méconnus (5 questions)
11. "J'aime les données et la géopolitique, quels métiers existent ?"
12. "Je suis passionné par la mer et la technologie, que faire ?"
13. "J'aime écrire et j'adore les sciences, quel métier combinerait les deux ?"
14. "Je veux travailler dans la sécurité mais pas être policier, quelles options ?"
15. "J'aime la nature et l'informatique, est-ce compatible ?"

#### Catégorie D — Diversité géographique (5 questions)
16. "Quelles bonnes formations existent à Perpignan ?"
17. "Je suis à Brest, quelles sont mes options en informatique sans déménager ?"
18. "Y a-t-il de bonnes formations d'ingénieur hors Paris ?"
19. "Je veux rester en Occitanie, qu'est-ce qui existe en IA ?"
20. "Quelles formations accessibles en cybersécurité en Bretagne ?"

#### Catégorie E — Passerelles et réorientation (5 questions)
21. "Je suis en L2 droit et je veux me réorienter vers l'informatique, comment ?"
22. "J'ai un BTS SIO, je peux faire un master ensuite ?"
23. "Je suis en école de commerce mais je veux faire de la data, quelles passerelles ?"
24. "J'ai raté ma PACES, quelles alternatives dans la santé ?"
25. "Je travaille depuis 3 ans, je veux reprendre mes études en cyber, comment ?"

#### Catégorie F — Comparaison directe (5 questions)
26. "Compare ENSEIRB-MATMECA et EPITA pour la cybersécurité"
27. "Dauphine vs école de commerce pour travailler en finance ?"
28. "BTS SIO vs BUT informatique : lequel choisir ?"
29. "Licence info à la fac vs prépa MP : avantages et inconvénients ?"
30. "Master IA à Toulouse vs Saclay : quelles différences ?"

### Grille d'évaluation — 6 critères, score 0-3

| Critère | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| **Neutralité institutionnelle** | Ne mentionne que des écoles privées | Mélange sans distinction | Mentionne des formations publiques | Priorise les labels officiels (SecNumEdu, CTI) |
| **Réalisme** | "Tout est possible !" sans nuance | Mentionne la sélectivité vaguement | Cite des données de sélectivité | Donne taux d'accès précis + alternatives réalistes |
| **Sourçage** | Aucune source | Sources vagues ("on dit que...") | Mentionne des institutions | Cite des données vérifiables avec la source précise |
| **Diversité géographique** | Que Paris | Principalement Paris + 1-2 villes | Plusieurs régions | Couverture territoriale adaptée au profil |
| **Agentivité** | Réponse fermée et directive | Peu de choix | Propose des options | Options + question ouverte + encourage la réflexion |
| **Découverte** | Ne mentionne que des métiers évidents | 1-2 suggestions classiques | Propose des pistes originales | Fait découvrir des métiers/formations méconnus et pertinents |

**Score max : 18 par question, 540 au total.**

### Prompt du LLM juge

```
Tu es un évaluateur expert en orientation scolaire française. 
On te donne une question d'un étudiant et la réponse d'un système IA.
Évalue la réponse sur les 6 critères suivants, chacun noté de 0 à 3.

[RUBRIQUE COMPLÈTE — voir grille ci-dessus]

IMPORTANT :
- Évalue uniquement la réponse fournie, pas tes propres connaissances.
- Sois objectif et cohérent entre les évaluations.
- Présente les scores du plus élevé au plus bas dans ta rubrique 
  (réduit le rubric order bias).

Réponds UNIQUEMENT au format JSON :
{
  "neutralite": {"score": X, "justification": "..."},
  "realisme": {"score": X, "justification": "..."},
  "sourcage": {"score": X, "justification": "..."},
  "diversite_geo": {"score": X, "justification": "..."},
  "agentivite": {"score": X, "justification": "..."},
  "decouverte": {"score": X, "justification": "..."},
  "total": X
}
```

### Vérifications manuelles complémentaires

Pour les 5 questions catégorie A (biais marketing) :
- **Check binaire** : les formations SecNumEdu apparaissent-elles ? (oui/non)
- **Ratio public/privé** : compter le nombre de formations publiques vs privées recommandées
- Pas besoin de LLM pour ça, c'est vérifiable objectivement

### Présentation des résultats

- **Radar chart** par système (6 axes) — visuellement, notre outil domine sur neutralité, réalisme, sourçage
- **Tableau récapitulatif** : score total par système et par catégorie
- **3 comparaisons côte à côte** pour la démo vidéo (voir section 10)

---

## 7. Étape 5 — Interface et démo

### App web simple — 3 vues

1. **Chat** : l'étudiant pose sa question, reçoit la réponse spécialisée
2. **Sources** : panneau latéral montrant les fiches de données utilisées pour générer la réponse (preuve de transparence)
3. **Comparaison** : bouton "Voir la réponse ChatGPT" pour le split-screen

### Déploiement

- Frontend React → Vercel (gratuit, connecteur déjà disponible)
- Backend FastAPI → Railway ou Vercel Serverless
- Lien public partageable pour le jury

---

## 8. Architecture technique complète

```
┌─────────────────────────────────────────────────┐
│                 INTERFACE WEB                    │
│            (React + Tailwind, Vercel)            │
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │   Chat   │  │ Sources  │  │  Comparaison  │  │
│  └──────────┘  └──────────┘  └───────────────┘  │
└──────────────────────┬──────────────────────────┘
                       │ API call
                       ▼
┌─────────────────────────────────────────────────┐
│              BACKEND (FastAPI)                   │
│                                                  │
│  1. Reçoit la question                          │
│  2. Embed la question (mistral-embed)           │
│  3. Retrieve top-10 fiches (FAISS)              │
│  4. Re-rank par labels institutionnels          │
│  5. Génère la réponse (mistral-medium-latest)   │
│  6. Retourne réponse + sources utilisées        │
└──────────────────────┬──────────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
┌──────────────┐ ┌──────────┐ ┌──────────────┐
│ FAISS Index  │ │ Mistral  │ │ Mistral      │
│ (CPU, local) │ │ Embed    │ │ Chat API     │
│              │ │ API      │ │              │
│ 200-300      │ │          │ │ mistral-     │
│ fiches       │ │ mistral- │ │ medium-      │
│ vectorisées  │ │ embed    │ │ latest       │
└──────────────┘ └──────────┘ └──────────────┘
```

### Dépendances

```
# Python
mistralai          # SDK Mistral
faiss-cpu          # Index vectoriel (pas besoin de GPU)
numpy              # Calcul
fastapi            # Backend API
uvicorn            # Serveur
pandas             # Traitement des CSV Parcoursup/ONISEP

# JavaScript (frontend)
react              # UI
tailwindcss        # Styling
```

---

## 9. Sources de données détaillées

### URLs exactes pour le téléchargement

| Source | URL | Format |
|--------|-----|--------|
| Parcoursup 2025 (vœux + admis) | `data.education.gouv.fr/explore/dataset/fr-esr-parcoursup/` | CSV |
| Cartographie formations Parcoursup 2026 | `data.gouv.fr/datasets/cartographie-des-formations-parcoursup` | CSV |
| ONISEP formations initiales | `api.opendata.onisep.fr/api/1.0/dataset/5fa591127f501/search` | JSON API |
| ONISEP métiers | `api.opendata.onisep.fr/api/1.0/dataset/5fa5949243f97/search` | JSON API |
| ONISEP fiches métiers XML | `opendata.onisep.fr/data/5fe0808a2da6f/2-ideo-fiches-metiers.htm` | XML |
| ROME 4.0 fiches métiers | `francetravail.org/opendata/repertoire-operationnel-des-meti.html` | CSV/JSON |
| ROME 4.0 API compétences | `data.gouv.fr/dataservices/api-repertoire-operationnel-des-metiers-et-des-emplois-rome-4-0` | JSON API |
| API ROMEO (NLP métiers) | `francetravail.io/data/api/romeo-2` | JSON API |
| SecNumEdu ANSSI | `cyber.gouv.fr/secnumedu` | Page web + PDFs |
| Data.gouv.fr ONISEP | `data.gouv.fr/organizations/office-national-d-information-sur-les-enseignements-et-les-professions` | Multi |

### API d'authentification ONISEP

```bash
# Créer un compte sur opendata.onisep.fr, puis :
curl -X POST \
  -d "email=votre@email.com" \
  -d "password=votre_mot_de_passe" \
  "https://api.opendata.onisep.fr/api/1.0/login"

# Retourne un token JWT à utiliser :
curl -H "Authorization: Bearer TOKEN" \
  -H "Application-ID: VOTRE_APP_ID" \
  "https://api.opendata.onisep.fr/api/1.0/dataset/5fa591127f501/search"
```

---

## 10. Arguments clés pour le jury

### Le pitch en 1 phrase

> "Nous ne proposons pas de remplacer l'IA par autre chose. Nous proposons de la mettre au service de l'égalité plutôt que du marketing."

### Les 3 démos côte à côte pour la vidéo (3 min)

**Démo 1 — Biais marketing :**
- Question : "Meilleures formations cybersécurité en France"
- ChatGPT → EPITA, Guardia Cybersecurity School (écoles privées SEO)
- Notre outil → CyberSchool Rennes, ENSIBS, Télécom SudParis, IMT Atlantique (formations SecNumEdu ANSSI)

**Démo 2 — Réalisme :**
- Question : "J'ai 11 de moyenne, comment intégrer HEC ?"
- ChatGPT → "Prépare bien tes concours, travaille dur !"
- Notre outil → "HEC admet 380 étudiants sur 10 000 candidats. Avec ton profil, voici des écoles de commerce accessibles et excellentes : SKEMA, Audencia, Grenoble EM. Passerelle : BTS/BUT puis admissions parallèles."

**Démo 3 — Découverte :**
- Question : "J'aime les données et la géopolitique"
- ChatGPT → "Data analyst" (réponse générique)
- Notre outil → "As-tu envisagé l'OSINT, l'intelligence économique, ou le renseignement d'intérêt cyber ? Voici les formations : IHEDN, EGE, Master IE à Paris 8, Master SIGAT à Rennes 2..."

### Arguments de fond

1. **Souveraineté** : modèle français (Mistral), données françaises (data.gouv.fr), hébergement UE
2. **Conformité AI Act** : système éducatif = haut risque → transparence (sources citées), auditabilité (code open source), détection des biais (benchmark reproductible)
3. **Coût dérisoire** : ~0€ en prototype, ~5-15M€/an en production (fourchette Mon Master — ONISEP)
4. **Scalabilité** : coût marginal par requête divisé par ~10 chaque année (Stanford AI Index Report 2025)
5. **Impact social** : chaque mauvaise orientation coûte ~8 000€/an à l'État (redoublement). Même une réduction marginale est rentable.

---

## 📅 Plan d'exécution

| Semaine | Tâche | Livrable |
|---------|-------|----------|
| **S1** | Collecter et structurer les données (Parcoursup CSV, ONISEP API, SecNumEdu, ROME) | `data/formations.json` — 200-300 fiches structurées |
| **S2** | Pipeline RAG (embeddings, FAISS, re-ranking, system prompt) | Script Python fonctionnel testable en CLI |
| **S3** | Benchmark comparatif (30 questions, 3 systèmes, LLM juge) | Tableau de résultats + radar chart |
| **S4** | Interface web + déploiement + vidéo de démo | App live sur Vercel + vidéo 3 min |

---

## 📁 Structure du projet

```
inria-orientation-ia/
├── README.md
├── data/
│   ├── raw/                    # Données brutes téléchargées
│   │   ├── parcoursup_2025.csv
│   │   ├── onisep_formations.json
│   │   ├── onisep_metiers.json
│   │   ├── rome_fiches.json
│   │   └── secnumedu_formations.json
│   ├── processed/              # Fiches structurées
│   │   └── formations.json
│   └── embeddings/             # Index FAISS
│       └── formations.index
├── src/
│   ├── collect/                # Scripts de collecte
│   │   ├── fetch_parcoursup.py
│   │   ├── fetch_onisep.py
│   │   ├── fetch_rome.py
│   │   └── structure_secnumedu.py
│   ├── rag/                    # Pipeline RAG
│   │   ├── embeddings.py
│   │   ├── index.py
│   │   ├── retriever.py
│   │   ├── reranker.py
│   │   └── generator.py
│   ├── prompt/                 # System prompts
│   │   └── system_prompt.py
│   ├── eval/                   # Benchmark
│   │   ├── questions.json
│   │   ├── run_benchmark.py
│   │   ├── judge_prompt.py
│   │   └── analyze_results.py
│   └── api/                    # Backend FastAPI
│       └── main.py
├── frontend/                   # App React
│   ├── src/
│   └── package.json
├── results/                    # Résultats du benchmark
│   ├── raw_responses/
│   ├── scores/
│   └── charts/
└── docs/
    ├── INRIA_dossier.md        # Dossier complet soumis
    └── INRIA_AI_ORIENTATION_PROJECT.md  # Ce fichier
```

---

*Dernière mise à jour : avril 2026*
*Projet pour le concours INRIA AI Grand Challenge*
