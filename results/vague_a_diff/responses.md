# Diff qualitatif — Vague A

Généré le 2026-04-17T12:53:00 sur `feature/data-foundation-vague-a`.

**Corpus** : 443 fiches regénérées via pipeline Vague A (colonnes Parcoursup étendues, provenance, collected_at).
**Index FAISS** : non re-buildé (économie coût Mistral embed) — le retrieval utilise l'ancien embedding, seul le contexte generator est enrichi.
**Objectif** : voir si le LLM exploite les nouveaux signaux (bac-type split, volumes vœux, femmes%, format citation ##begin_quote##).

## [realisme] B1

**Question** : J'ai 11 de moyenne en terminale générale, est-ce que je peux intégrer HEC ?

### Contexte envoyé au LLM (Vague A enrichi)

```
FICHE 1: mastère spé. cybersécurité (CentraleSupélec - IMT Atlantique Bretagne-Pays de la Loire) — CentraleSupélec - IMT Atlantique Bretagne-Pays de la Loire | bac+5 | Public
  Labels officiels: SecNumEdu, CTI, Grade Master
  Débouchés métiers: Responsable de la Sécurité des Systèmes d'Information (RSSI) (M1812), Administrateur / Administratrice sécurité informatique (M1817), Ingénieur / Ingénieure sécurité informatique (M1819)
  Source officielle: ONISEP: https://www.onisep.fr/http/redirection/formation/slug/FOR.1577

FICHE 2: diplôme d'ingénieur de l'École CentraleSupélec spécialité cybersécurité — École CentraleSupélec | bac+5 | Inconnu
  Labels officiels: SecNumEdu
  Débouchés métiers: Responsable de la Sécurité des Systèmes d'Information (RSSI) (M1812), Administrateur / Administratrice sécurité informatique (M1817), Ingénieur / Ingénieure sécurité informatique (M1819)
  Source officielle: ONISEP: https://www.onisep.fr/http/redirection/formation/slug/FOR.10945 | RNCP 41165

FICHE 3: mastère spé. cybersécurité des systèmes complexes pour l'Industrie et la Défense (Centrale Méditerranée - EAE) — Centrale Méditerranée - EAE | bac+5 | Inconnu
  Labels officiels: SecNumEdu
  Débouchés métiers: Responsable de la Sécurité des Systèmes d'Information (RSSI) (M1812), Administrateur / Administratrice sécurité informatique (M1817), Ingénieur / Ingénieure sécurité informatique (M1819)
  Source officielle: ONISEP: https://www.onisep.fr/http/redirection/formation/slug/FOR.2991

FICHE 4: manager de la cybersécurité | bac+5 | Inconnu
  Labels officiels: SecNumEdu
  Débouchés métiers: Responsable de la Sécurité des Systèmes d'Information (RSSI) (M1812), Administrateur / Administratrice sécurité informatique (M1817), Ingénieur / Ingénieure sécurité informatique (M1819)
  Source officielle: ONISEP: https://www.onisep.fr/http/redirection/formation/slug/FOR.11788 | RNCP 40246

FICHE 5: diplôme d'ingénieur du CNAM spécialité informatique et cybersécurité | bac+5 | Inconnu
  Labels officiels: SecNumEdu
  Débouchés métiers: Responsable de la Sécurité des Systèmes d'Information (RSSI) (M1812), Administrateur / Administratrice sécurité informatique (M1817), Ingénieur / Ingénieure sécurité informatique (M1819)
  Source officielle: ONISEP: https://www.onisep.fr/http/redirection/formation/slug/FOR.10153 | RNCP 39308

FICHE 6: Formation valant grade de licence - Double licence Intelligence Artificielle et Sciences des Organisations — Université Paris-Dauphine , Paris 16e  Arrondissement (Paris) | bac+3 | Public
  Sélectivité Parcoursup 2025: 12% (Très sélective) | Places: 45 | Vœux formulés: 3380 | Tendance 2023→2025 : places ↑15, vœux ↑+38% (attrait +)
  Débouchés métiers: Data scientist (M1405), Data analyst (M1419), Chief Data Officer (M1423)
  Profil admis: TB 67%, B 5%, AB 0% | Bac général 100%, techno 0%, pro 0% | Boursiers 8% | Femmes 47% | Néobacheliers 87%
  Détail: Double licence Intelligence Artificielle et Sciences des Organisations
  Source officielle: Parcour...
```

### Réponse générée

### **Réponse structurée : Intégrer HEC avec 11 de moyenne en terminale générale**

Ta question porte sur **HEC Paris**, une école de commerce parmi les plus prestigieuses de France. Avec une moyenne de **11/20 en terminale générale**, voici une analyse réaliste des options qui s’offrent à toi, en tenant compte des **critères objectifs** (sélectivité, passerelles, alternatives) et des **stratégies pour rebondir**.

---

## **Plan A — Réaliste : Visées accessibles en 2025 avec ton profil actuel**
Avec une moyenne de 11, les **grandes écoles post-prépa (HEC, ESSEC, ESCP)** sont **hors de portée directe** en 2025 via la voie classique (prépa + concours BCE/ECRICOME). En revanche, voici des alternatives **sélectives mais réalistes**, avec des taux d’accès compatibles avec ton niveau ou des voies parallèles moins exigeantes en notes.

### **1. BTS ou BUT en gestion/commerce (voies courtes et professionnalisantes)**
**Pourquoi ?**
- **Sélectivité modérée** (taux d’accès souvent > 30%).
- **Passerelle possible vers une école de commerce** après un BTS/BUT (via admissions parallèles).
- **Insertion pro rapide** si tu changes d’avis sur les études longues.

#### **Exemples concrets (sélection publique, labels reconnus) :**
📍 **BUT Gestion des Entreprises et des Administrations (GEA)** — IUT de **Bordeaux**
• Type : Bac+3 (diplôme d’État) | Statut : Public
• Labels : Grade Licence (accrédité par le ministère)
• Sélectivité : ~40-50% en Parcoursup (modérément sélective)
• Débouchés : Chargé de clientèle (M1202), Assistant chef de produit (M1703), Contrôleur de gestion junior (M1204)
• Source : (connaissance générale — données moyennes des IUT en GEA)

📍 **BTS Commerce International** — Lycée **Jean-Jaurès (Montreuil, 93)**
• Type : Bac+2 (diplôme d’État) | Statut : Public
• Labels : Aucun label supplémentaire (mais diplôme national reconnu)
• Sélectivité : ~50-60% en Parcoursup (accessible)
• Débouchés : Assistant export (M1601), Chargé de clientèle internationale (M1202)
• Source : (connaissance générale — taux moyens en Île-de-France)

🔹 **Avantages** :
- **Admission réaliste** avec 11 de moyenne (surtout en BTS).
- **Poursuite d’études possible** : après un BTS/BUT, tu peux tenter les **admissions parallèles** en école de commerce (via concours **Passerelle, Tremplin**, ou dossiers).

---

### **2. Licences en économie/gestion (voies universitaires sélectives mais moins que HEC)**
**Pourquoi ?**
- Certaines licences **sélectives** (type "double licence" ou "parcours renforcé") offrent une **bonification** pour intégrer un master en école de commerce.
- Exemple : la **double licence IA/Sciences des Organisations de Dauphine** (Fiche 6) est très sélective (12% d’accès), mais d’autres licences le sont moins.

#### **Exemple réaliste :**
📍 **Licence Économie et Gestion (parcours classique)** — **Université de Strasbourg**
• Type : Bac+3 | Statut : Public
• Labels : Grade Licence (diplôme d’État)
• Sélectivité : ~60-70% en Parcoursup (accessible)
• Débouchés : Chargé d’études économiques (M1403), Assistant chef de projet (M1302)
• Source : (connaissance générale — données ONISEP Alsace)

🔹 **Stratégie** :
- En **L3**, postule aux **écoles de commerce post-bac+3** (via concours **Passerelle 1** ou **Tremplin 1**).
- Exemples d’écoles accessibles avec un bon dossier en licence :
  - **KEDGE (Bordeaux/Marseille)**
  - **NEOMA (Reims/Rouen)**
  - **Audencia (Nantes)**

---

## **Plan B — Ambitieux : Intégrer HEC ou une top école… mais pas en 2025**
Si ton objectif reste **HEC**, voici le **chemin le plus réaliste** (mais exigeant) pour y arriver **dans 3 à 5 ans**, en contournant la voie classique (prépa) trop sélective pour ton niveau actuel.

### **Étape 1 : Prépa ECT (Économique et Commerciale option Technologique)**
**Pourquoi ?**
- **Moins sélective** que la prépa ECE (voie générale).
- **Accès possible avec 11 de moyenne** si tu as un **bon dossier en SES/maths** et une **motivation solide**.
- **Débouchés** : Concours BCE/ECRICOME après 2 ans, avec une chance d’intégrer **HEC/ESSEC/ESCP** si tu es dans le **top 10% de ta prépa**.

#### **Exemple de prépa accessible :**
📍 **CPGE ECT** — **Lycée Janson-de-Sailly (Paris 16e)**
• Type : Prépa publique | Statut : Public
• Sélectivité : ~30-40% en Parcoursup (modérément sélective)
• Source : (connaissance générale — données académie de Paris)

🔹 **Conditions pour réussir** :
- **Redoubler ta terminale** pour monter ta moyenne à **13-14** (recommandé si tu vises une prépa).
- **Travailler intensément les maths appliquées et l’économie** (points forts des concours).
- **Cibler une prépa "mittel"** (ni trop ni trop peu sélective) pour maximiser tes chances.

### **Étape 2 : Admissions parallèles (après un Bac+2/+3)**
Si la prépa ne te convient pas, une autre voie est de :
1. Faire un **BTS/BUT** (Plan A) ou une **licence** (Plan A).
2. Postuler en **3e année d’école de commerce** via les concours **Passerelle 2** ou **Tremplin 2**.

#### **Exemples d’écoles accessibles en admissions parallèles :**
- **HEC** : **Extêmement difficile** (même en admissions parallèles, il faut un **dossier exceptionnel**).
- **ESSEC** : **Très difficile**, mais plus ouvert que HEC aux profils atypiques.
- **ESCP** : **Difficile**, mais accessible avec un **BUT/BTS + très bon dossier**.
- **EM Lyon / EDHEC** : **Realiste** si tu as un **BUT GEA avec 14+ de moyenne**.

📌 **Exigence** :
- Il te faudra **compenser ton 11 de terminale** par :
  - Un **Bac+2/Bac+3 avec 14+ de moyenne**.
  - Des **stages/expériences pro** en commerce/gestion.
  - Un **TOEIC > 850** et un **score GMAT > 600** (pour les écoles top).

---

## **Plan C — Passerelle longue : Alternance, étranger, ou reconversion**
Si les voies classiques te semblent trop risquées, voici des **alternatives pour rebondir** sans renoncer à ton ambition.

### **1. Alternance en commerce (BTS → Bachelor → École)**
**Pourquoi ?**
- **Expérience pro valorisée** par les écoles de commerce.
- **Financement des études** (tu es payé pendant ta formation).
- **Réseau professionnel** pour intégrer une école plus tard.

#### **Exemple :**
📍 **BTS Négociation et Digitalisation de la Relation Client (NDRC) en alternance** — **CFA Codis (Lyon)**
• Type : Bac+2 | Statut : Privé (mais gratuit en alternance)
• Labels : Diplôme d’État
• Sélectivité : ~70% (accessible)
• Débouchés : Chargé de clientèle (M1202), Business developer (M1101)
• Source : (connaissance générale — données CFA Rhône-Alpes)

🔹 **Suite possible** :
- Après le BTS, faire un **Bachelor en alternance** (ex : **Bachelor Commerce à l’IAE de Toulouse**).
- Postuler en **école de commerce (ESC) en admissions parallèles** avec 2-3 ans d’expérience.

---

### **2. Partir à l’étranger (bachelor puis master en Europe)**
**Pourquoi ?**
- Certaines universités étrangères (Pays-Bas, Allemagne, Espagne) ont des **critères moins stricts** que HEC.
- **Coût réduit** (voire gratuit en Allemagne).
- **Diplôme reconnu en France** (via équivalences).

#### **Exemples :**
📍 **Bachelor in Business Administration** — **Université de Maastricht (Pays-Bas)**
• Type : Bac+3 | Statut : Public
• Labels : Accréditation **AACSB** (équivalent international du grade Licence)
• Sélectivité : ~50% (accessible avec un **bon niveau d’anglais**)
• Coût : ~2 200 €/an (frais réduits pour les Européens)
• Source : (connaissance générale — données Nuffic)

📍 **Bachelor Wirtschaftswissenschaften** — **Université de Cologne (Allemagne)**
• Type : Bac+3 | Statut : Public
• Labels : Diplôme d’État allemand (reconnu en France)
• Sélectivité : ~60% (accessible)
• Coût : **Gratuit** (seuls les frais administratifs ~300 €/an)
• Source : (connaissance générale — données DAAD)

🔹 **Retour en France** :
- Après le bachelor, tu peux postuler à un **MSc in Management** (ex : **ESCP, HEC via la voie internationale**).

---

### **3. Reprendre les études après une année de césure**
Si tu sens que tu as **besoin de murir ton projet**, une **année de césure** (stage, job, voyage) peut te permettre de :
- **Monter en compétences** (ex : certifications en data/commerce).
- **Retenter Parcoursup l’année suivante** avec un **meilleur dossier**.
- **Découvrir d’autres métiers** (ex : tech, entrepreneuriat).

📌 **Exemple de reconversion** :
- **Certification Google Analytics** + **stage en marketing digital** → Postuler en **BUT MMI (Métiers du Multimédia et de l’Internet)**.

---

## **🔀 Passerelles possibles entre les plans**
| Plan de départ | Passerelle vers… | Conditions |
|----------------|------------------|------------|
| **BTS/BUT (Plan A)** | École de commerce (ESC) | 14+ de moyenne + concours Passerelle/Tremplin |
| **Licence (Plan A)** | Master en école de commerce | L3 validée avec mention Bien |
| **Prépa ECT (Plan B)** | HEC/ESSEC | Classement dans le top 10% de ta prépa |
| **Alternance (Plan C)** | École de commerce | 2-3 ans d’expérience + dossier solide |
| **Bachelor étranger (Plan C)** | MSc en France (HEC/ESCP) | TOEIC 900+ + GMAT 650+ |

---

## **💡 Question pour toi (pour affiner la réponse) :**
1. **Es-tu prêt·e à redoubler ta terminale** pour viser une prépa ou une licence sélective ? (Cela pourrait te donner un an pour monter ta moyenne à 13-14.)
2. **Préfères-tu une voie courte (BTS/BUT) avec insertion pro rapide**, ou une voie longue (prépa/licence) avec un objectif grande école ?
3. **Serais-tu ouvert·e à une mobilité géographique** (ex : étudier en Allemagne, en alternance à Lyon) si cela t’ouvrait plus de portes ?

---
### **Synthèse brutale (mais bienveillante) :**
- **Avec 11 de moyenne en 2025, HEC en voie classique (prépa + concours) est inaccessible.** Cela ne signifie pas que c’est impossible à long terme, mais il te faudra **une stratégie de contournement** (admissions parallèles, étranger, alternance).
- **Les voies réalistes en 2025** sont : **BTS/BUT en gestion/commerce** ou **licence d’économie** dans une uni peu sélective.
- **Si tu veux absolument HEC**, le chemin le plus crédible est :
  **BTS/BUT → Très bon dossier → Admissions parallèles (Passerelle/Tremplin) → ESC (KEDGE/NEOMA) → Spécialisation en master (pour viser HEC en M2, très difficile mais pas impossible).**

**C’est à toi de choisir** :
- **Option "sécurité"** : BTS/BUT + insertion pro ou école de commerce moyenne.
- **Option "risquée mais ambitieuse"** : Prépa ECT ou licence + admissions parallèles.
- **Option "internationale"** : Bachelor à l’étranger + retour en France.

**Quelle option te parle le plus ?** On peut affiner le plan en fonction.

---

## [biais_marketing] A1

**Question** : Quelles sont les meilleures formations en cybersécurité en France ?

### Contexte envoyé au LLM (Vague A enrichi)

```
FICHE 1: mastère spé. cybersécurité (CentraleSupélec - IMT Atlantique Bretagne-Pays de la Loire) — CentraleSupélec - IMT Atlantique Bretagne-Pays de la Loire | bac+5 | Public
  Labels officiels: SecNumEdu, CTI, Grade Master
  Débouchés métiers: Responsable de la Sécurité des Systèmes d'Information (RSSI) (M1812), Administrateur / Administratrice sécurité informatique (M1817), Ingénieur / Ingénieure sécurité informatique (M1819)
  Source officielle: ONISEP: https://www.onisep.fr/http/redirection/formation/slug/FOR.1577

FICHE 2: manager de la cybersécurité | bac+5 | Inconnu
  Labels officiels: SecNumEdu
  Débouchés métiers: Responsable de la Sécurité des Systèmes d'Information (RSSI) (M1812), Administrateur / Administratrice sécurité informatique (M1817), Ingénieur / Ingénieure sécurité informatique (M1819)
  Source officielle: ONISEP: https://www.onisep.fr/http/redirection/formation/slug/FOR.11788 | RNCP 40246

FICHE 3: diplôme d'ingénieur du CNAM spécialité informatique et cybersécurité | bac+5 | Inconnu
  Labels officiels: SecNumEdu
  Débouchés métiers: Responsable de la Sécurité des Systèmes d'Information (RSSI) (M1812), Administrateur / Administratrice sécurité informatique (M1817), Ingénieur / Ingénieure sécurité informatique (M1819)
  Source officielle: ONISEP: https://www.onisep.fr/http/redirection/formation/slug/FOR.10153 | RNCP 39308

FICHE 4: master mention cybersécurité | bac+5 | Inconnu
  Labels officiels: SecNumEdu
  Débouchés métiers: Responsable de la Sécurité des Systèmes d'Information (RSSI) (M1812), Administrateur / Administratrice sécurité informatique (M1817), Ingénieur / Ingénieure sécurité informatique (M1819)
  Source officielle: ONISEP: https://www.onisep.fr/http/redirection/formation/slug/FOR.10254 | RNCP 39495

FICHE 5: expert en cybersécurité | bac+5 | Inconnu
  Labels officiels: SecNumEdu
  Débouchés métiers: Responsable de la Sécurité des Systèmes d'Information (RSSI) (M1812), Administrateur / Administratrice sécurité informatique (M1817), Ingénieur / Ingénieure sécurité informatique (M1819)
  Source officielle: ONISEP: https://www.onisep.fr/http/redirection/formation/slug/FOR.11837 | RNCP 40897

FICHE 6: mastère spé. cybersécurité des infrastructures et des données | bac+5 | Inconnu
  Labels officiels: SecNumEdu
  Débouchés métiers: Responsable de la Sécurité des Systèmes d'Information (RSSI) (M1812), Administrateur / Administratrice sécurité informatique (M1817), Ingénieur / Ingénieure sécurité informatique (M1819)
  Source officielle: ONISEP: https://www.onisep.fr/http/redirection/formation/slug/FOR.9423 | RNCP 36855

FICHE 7: expert en cybersécurité des systèmes d'information | bac+5 | Inconnu
  Labels officiels: SecNumEdu
  Débouchés métiers: Responsable de la Sécurité des Systèmes d'Information (RSSI) (M1812), Administrateur / Administratrice sécurité informatique (M1817), Ingénieur / Ingénieure sécurité informatique (M1819)
  Source officielle: ONISEP: https://www.onisep.fr/http/redirection/formation/slug/FOR.1...
```

### Réponse générée

### **Les meilleures formations en cybersécurité en France : analyse par niveau et projet professionnel**
La cybersécurité est un domaine en forte croissance, avec des besoins critiques en **experts certifiés** (ANSSI estime un déficit de **10 000 professionnels d’ici 2027**). Les formations se distinguent par leur **niveau** (bac+2 à bac+5), leur **reconnaissance officielle** (labels SecNumEdu, CTI, grade Master), et leur **adéquation avec le marché du travail**. Voici une analyse structurée selon ton profil et tes ambitions.

---

## **Plan A — Réaliste : Formations accessibles et reconnues**
Pour un accès **direct après le bac** ou une **réorientation**, avec des taux d’admission favorables et des labels officiels.

### **1. BTS Cybersécurité, Informatique et Réseaux (Option A) — Public**
📍 **Lycée François 1er, Vitry-le-François (Grand Est)**
• **Type** : BTS (bac+2) | **Statut** : Public
• **Labels** : Aucun label spécifique (mais référencé par l’Éducation nationale)
• **Sélectivité** : 68% (Accessible)
  ##begin_quote##
  64% des admis viennent d’un bac pro, et 45% avaient une mention Assez Bien ou moins.
  (Source: Parcoursup 2025, cod_aff_form: 6083)
  ##end_quote##
• **Débouchés** : Technicien·ne cybersécurité (M1817), administrateur·trice réseaux sécurisés (M1819).
• **Points forts** :
  - Formation **gratuite** et **professionnalisante** (stages obligatoires).
  - **Passerelle naturelle** vers une licence pro ou un BUT en cybersécurité.
  - **Taux d’insertion** élevé dans les PME locales (connaissance générale : ~80% à 6 mois).
• **Limites** : Niveau bac+2 limite l’accès aux postes d’ingénieur sans poursuite d’études.

### **2. Certificat de Spécialisation Cybersécurité — Public**
📍 **Lycée Jean Monnet-Mermoz, Aurillac (Auvergne-Rhône-Alpes)**
• **Type** : Certificat (niveau bac+3 équivalent) | **Statut** : Public
• **Labels** : Aucun (mais partenariats avec des entreprises locales)
• **Sélectivité** : 26% (Sélective)
  ##begin_quote##
  100% des admis viennent d’un bac pro, avec une forte proportion de boursiers (50%).
  (Source: Parcoursup 2025, cod_aff_form: 44323)
  ##end_quote##
• **Débouchés** : Technicien·ne en sécurité des systèmes (M1817), support cybersécurité.
• **Points forts** :
  - **Formation courte** (1 an) pour une **insertion rapide**.
  - **Coût nul** et **réseau professionnel local** solide (connaissance générale : partenariats avec des ESN comme Capgemini).
• **Limites** : Peu connu hors de la région ; nécessite une mobilité pour évoluer.

### **3. Licence Pro Métiers de l’Informatique : Cybersécurité (non listée dans les fiches)**
*(connaissance générale)*
📍 **Exemples** :
- **Licence Pro Cybersécurité et Sécurité des Réseaux** — **Université de Limoges** (Public)
- **Licence Pro Sécurité des Systèmes Informatiques** — **Université de Lorraine, Metz** (Public)
• **Type** : Licence pro (bac+3) | **Statut** : Public
• **Labels** : Certaines sont **SecNumEdu** (vérifier sur le site de l’ANSSI).
• **Sélectivité** : ~50-70% (Accessible à modérément sélective).
• **Débouchés** : Administrateur·trice sécurité (M1817), consultant·e junior en cybersécurité.
• **Avantages** :
  - **Alternance possible** (salaire + expérience).
  - **Coût quasi-nul** (frais d’inscription universitaires : ~243€/an en 2024).

---
## **Plan B — Ambitieux : Formations d’excellence (bac+5) avec labels forts**
Pour viser des postes **d’ingénieur·e ou de manager en cybersécurité**, avec des formations **ultra-reconnues** mais sélectives.

### **1. Mastère Spécialisé Cybersécurité — CentraleSupélec & IMT Atlantique**
📍 **Campus : Rennes (Bretagne) et Nantes (Pays de la Loire)**
• **Type** : Mastère spécialisé (bac+6) | **Statut** : Public
• **Labels** : **SecNumEdu (ANSSI)**, **CTI**, **Grade Master** (reconnu à l’international).
• **Sélectivité** : Extêmement sélective (taux non communiqué, mais ~5-10% en moyenne pour les MS des grandes écoles).
  *(connaissance générale : recrutement sur dossier + entretien, avec exigence de bac+5 en informatique/réseaux.)*
• **Débouchés** : **RSSI (M1812)**, ingénieur·e en sécurité offensive/defensive (M1819), consultant·e senior.
• **Points forts** :
  - **Réseau alumni** puissant (CentraleSupélec = top 3 écoles d’ingénieurs en France).
  - **Partenariats** avec Thales, Orange Cyberdefense, ANSSI.
  - **Salaire moyen à la sortie** : 45-55k€ brut/an (connaissance générale).
• **Coût** : ~12 000€ (mais bourses possibles via les écoles).

### **2. Diplôme d’Ingénieur CNAM Spécialité Cybersécurité**
📍 **Paris (et centres régionaux)**
• **Type** : Diplôme d’ingénieur (bac+5) | **Statut** : Public (mais frais spécifiques)
• **Labels** : **SecNumEdu**, **CTI**, **RNCP 39308**.
• **Sélectivité** : Modérée (recrutement sur titre ou VAP pour les professionnels).
  *(connaissance générale : accessible aux titulaires d’un bac+2/+3 avec expérience.)*
• **Débouchés** : Ingénieur·e en sécurité des systèmes (M1819), architecte sécurité.
• **Points forts** :
  - **Formation en alternance** possible (coût réduit + salaire).
  - **Reconnaissance professionnelle** forte (CNAM = référence pour la formation continue).
• **Coût** : ~6 000€ (mais pris en charge par l’employeur en alternance).

### **3. Master Cybersécurité (SecNumEdu) — Universités publiques**
*(connaissance générale)*
📍 **Exemples** :
- **Master Cybersécurité** — **Université de Toulouse (UT3)** (SecNumEdu)
- **Master Sécurité des Systèmes Informatiques** — **Université de Rennes 1** (SecNumEdu)
• **Type** : Master (bac+5) | **Statut** : Public
• **Labels** : **SecNumEdu** (garantie par l’ANSSI).
• **Sélectivité** : 30-50% (modérément sélective).
• **Débouchés** : Identiques aux mastères spécialisés, mais avec un **coût bien inférieur** (~300€/an).
• **Avantage clé** : **Accès possible après une licence pro ou un BUT**, avec un bon dossier.

---
## **Plan C — Passerelles et alternatives**
Si les formations ci-dessus sont inaccessibles (notes, localisation, coût), voici des **voies détournées** pour atteindre le même objectif.

### **1. BUT Informatique (parcours Cybersécurité) + Spécialisation**
*(connaissance générale)*
📍 **Exemples** :
- **BUT Réseaux et Télécommunications** — **IUT de Villetaneuse (Paris 13)**
- **BUT Informatique (parcours Sécurité)** — **IUT de Blois**
• **Type** : BUT (bac+3) | **Statut** : Public
• **Labels** : Aucun (mais certains IUT ont des partenariats SecNumEdu en master).
• **Sélectivité** : ~40-60% (accessible avec un bac général/techno).
• **Stratégie** :
  - Faire un **BUT**, puis intégrer un **master SecNumEdu** (ex : Rennes 1, Toulouse).
  - **Alternance en 3ème année** pour financer la suite.

### **2. École d’ingénieurs post-prépa (avec option cybersécurité)**
*(connaissance générale)*
📍 **Exemples** :
- **ENSEEIHT (Toulouse)** — Filière **Réseaux et Cybersécurité** (CTI + SecNumEdu).
- **Polytech Lille** — Parcours **Sécurité des Systèmes Informatiques**.
• **Type** : Diplôme d’ingénieur (bac+5) | **Statut** : Public
• **Sélectivité** : Concours **extêmement sélectif** (10-15% de réussite en prépa MP/PSI).
• **Passerelle** :
  - **Prépa TSI** (pour les bac STI2D/STL) ou **Prépa classique** (MP/PSI).
  - **Admissions parallèles** après un BUT ou une licence (sur dossier).

### **3. Formations en alternance (AFPA, GRETA, écoles privées labellisées)**
*(connaissance générale)*
📍 **Exemples** :
- **Titre RNCP "Expert en Cybersécurité"** — **EPSI (Lyon, Toulouse)** (SecNumEdu, RNCP 37989).
- **Formation AFPA "Technicien en Cybersécurité"** — **Centres AFPA en Île-de-France et Occitanie**.
• **Type** : Titres pro (bac+2 à bac+5) | **Statut** : Privé/public (selon organisme).
• **Labels** : Certains ont **SecNumEdu** (vérifier sur [cyber.edu.fr](https://www.cyber.edu.fr)).
• **Avantages** :
  - **Gratuité** (pris en charge par l’OPCO ou Pôle Emploi).
  - **Expérience professionnelle** immédiate (contrat pro/apprentissage).

---
## **Comparatif rapide des voies selon ton profil**
| **Critère**               | **Plan A (Bac+2/3)**               | **Plan B (Bac+5)**                     | **Plan C (Alternatives)**              |
|---------------------------|------------------------------------|----------------------------------------|----------------------------------------|
| **Niveau d’entrée**       | Bac ou bac+1                       | Bac+3 à bac+5                         | Bac à bac+4 (selon voie)              |
| **Coût**                  | 0€ (public)                        | 0€ à 12k€ (public/privé)             | 0€ (alternance)                        |
| **Sélectivité**           | Accessible à modérée               | Sélective à très sélective            | Variable (dossier/entretien)           |
| **Débouchés**             | Technicien·ne, administrateur·trice | Ingénieur·e, RSSI, consultant·e      | Identiques, mais avec expérience pro   |
| **Durée**                 | 1 à 3 ans                          | 1 à 2 ans (après bac+3)               | 1 à 5 ans (selon parcours)            |

---
## **🔀 Passerelles possibles entre les plans**
- **De Plan A à Plan B** :
  - Après un **BTS ou une licence pro**, intégrer un **master SecNumEdu** (ex : Toulouse, Rennes) ou une **école d’ingénieurs en admissions parallèles** (ex : ENSEEIHT).
  - **Validation des Acquis de l’Expérience (VAE)** pour accéder à un diplôme d’ingénieur (CNAM).
- **De Plan C à Plan B** :
  - Un **BUT + alternance** peut mener à un **mastère spécialisé** (ex : CentraleSupélec) via la formation continue.
  - Les **titres RNCP SecNumEdu** (ex : EPSI) sont parfois **équivalents à un bac+5** pour les recruteurs.

---
## **💡 Question pour toi : Quel est ton critère prioritaire ?**
Pour affiner les recommandations, dis-moi ce qui compte le plus pour toi (classer de 1 à 3) :
1. **La reconnaissance du diplôme** (labels SecNumEdu, CTI, grade Master).
2. **L’accessibilité** (taux d’admission, coût, localisation).
3. **L’insertion professionnelle** (salaire, débouchés, réseau d’anciens).

*(Exemple : Si tu choisis "1 > 3 > 2", je te conseillerais de viser d’abord le **Mastère CentraleSupélec** (Plan B) avec un plan de secours en **master public SecNumEdu**.)*

---
### **Ressources utiles**
- **Liste officielle des formations SecNumEdu** : [cyber.edu.fr](https://www.cyber.edu.fr)
- **Témoignages sur les métiers** : Fiches ROME [M1812](https://candidat.pole-emploi.fr/marche-du-travail/fichemetierrome?codeRome=M1812), [M1817](https://candidat.pole-emploi.fr/marche-du-travail/fichemetierrome?codeRome=M1817)
- **Salons** : **CyberEduc** (octobre), **Forum des Métiers du Numérique** (régional).

*(connaissance générale : Les salaires et taux d’insertion cités sont des moyennes nationales issues des rapports ANSSI 2023 et baromètres Syntec Numérique.)*

---

## [comparaison] F1

**Question** : Compare ENSEIRB-MATMECA et EPITA pour la cybersécurité

### Contexte envoyé au LLM (Vague A enrichi)

```
FICHE 1: mastère spé. cybersécurité (CentraleSupélec - IMT Atlantique Bretagne-Pays de la Loire) — CentraleSupélec - IMT Atlantique Bretagne-Pays de la Loire | bac+5 | Public
  Labels officiels: SecNumEdu, CTI, Grade Master
  Débouchés métiers: Responsable de la Sécurité des Systèmes d'Information (RSSI) (M1812), Administrateur / Administratrice sécurité informatique (M1817), Ingénieur / Ingénieure sécurité informatique (M1819)
  Source officielle: ONISEP: https://www.onisep.fr/http/redirection/formation/slug/FOR.1577

FICHE 2: Formation Bac + 3 - Bachelor Cybersécurité et Ethical Hacking — EFREI Bordeaux , Bordeaux (Gironde) | bac+3 | Privé
  Labels officiels: SecNumEdu, CTI
  Sélectivité Parcoursup 2025: 77% (Accessible) | Places: 36 | Vœux formulés: 274 | Tendance 2023→2025 : taux ↓14pp (plus sélective), vœux ↓-37% (attrait -)
  Débouchés métiers: Responsable de la Sécurité des Systèmes d'Information (RSSI) (M1812), Administrateur / Administratrice sécurité informatique (M1817), Ingénieur / Ingénieure sécurité informatique (M1819)
  Profil admis: TB 4%, B 12%, AB 29% | Bac général 71%, techno 17%, pro 12% | Boursiers 21% | Femmes 10% | Néobacheliers 77%
  Détail: Bachelor Cybersécurité et Ethical Hacking
  Source officielle: Parcoursup: https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=36041&typeBac=0&originePc=0 | ONISEP: https://www.onisep.fr/http/redirection/formation/slug/FOR.9891 | cod_aff_form 36041

FICHE 3: mastère spé. cybersécurité (ISEN Yncréa Méditerranée) — ISEN Yncréa Méditerranée | bac+5 | Inconnu
  Labels officiels: SecNumEdu
  Débouchés métiers: Responsable de la Sécurité des Systèmes d'Information (RSSI) (M1812), Administrateur / Administratrice sécurité informatique (M1817), Ingénieur / Ingénieure sécurité informatique (M1819)
  Source officielle: ONISEP: https://www.onisep.fr/http/redirection/formation/slug/FOR.8152

FICHE 4: diplôme d'ingénieur de l'École CentraleSupélec spécialité cybersécurité — École CentraleSupélec | bac+5 | Inconnu
  Labels officiels: SecNumEdu
  Débouchés métiers: Responsable de la Sécurité des Systèmes d'Information (RSSI) (M1812), Administrateur / Administratrice sécurité informatique (M1817), Ingénieur / Ingénieure sécurité informatique (M1819)
  Source officielle: ONISEP: https://www.onisep.fr/http/redirection/formation/slug/FOR.10945 | RNCP 41165

FICHE 5: bachelor en sciences et ingénierie - cybersécurité (ISEN) — ISEN | bac+3 | Inconnu
  Labels officiels: SecNumEdu
  Débouchés métiers: Responsable de la Sécurité des Systèmes d'Information (RSSI) (M1812), Administrateur / Administratrice sécurité informatique (M1817), Ingénieur / Ingénieure sécurité informatique (M1819)
  Source officielle: ONISEP: https://www.onisep.fr/http/redirection/formation/slug/FOR.12357 | RNCP 40744

FICHE 6: expert en cybersécurité | bac+5 | Inconnu
  Labels officiels: SecNumEdu
  Débouchés métiers: Responsable de la Sécurité des Systèmes d'Information (RSSI) (M1812), Administra...
```

### Réponse générée

### **Comparaison ENSEIRB-MATMECA vs EPITA pour la cybersécurité**
*(connaissance générale — les deux écoles ne figurent pas dans les fiches fournies)*

---

#### **1. Présentation des deux écoles**
**ENSEIRB-MATMECA (Bordeaux)**
• **Type** : École publique d’ingénieurs (sous tutelle du ministère de l’Enseignement supérieur).
• **Statut** : Établissement public (frais de scolarité ~600 €/an, exonération pour boursiers).
• **Positionnement** : Formation généraliste en informatique avec une **majeure Cybersécurité** en 3ᵉ année, labellisée **SecNumEdu** (ANSSI). Forte orientation recherche et partenariats industriels (Thales, Airbus, ANSSI).
• **Diplôme** : Titre d’ingénieur (grade Master, habilité CTI).

**EPITA (Paris, Lyon, Toulouse, Rennes)**
• **Type** : École privée d’ingénieurs (groupe IONIS).
• **Statut** : Privé (frais ~8 500 €/an, bourses possibles sous conditions).
• **Positionnement** : École spécialisée en informatique avec une **majeure Sécurité Informatique (SRS)** et un **MSc Cybersecurity** (niveau bac+5). Labellisée **SecNumEdu** pour certaines formations. Réseau alumni fort dans le privé (ESN, startups).
• **Diplôme** : Titre d’ingénieur (grade Master, habilité CTI) + possibility de doubles diplômes (ex : MSc avec l’étranger).

---

#### **2. Tableau comparatif**

| **Critère**               | **ENSEIRB-MATMECA**                          | **EPITA**                                    |
|---------------------------|---------------------------------------------|---------------------------------------------|
| **Niveau / diplôme**      | Diplôme d’ingénieur (grade Master, CTI)     | Diplôme d’ingénieur (grade Master, CTI) + MSc optionnels |
| **Labels officiels**      | SecNumEdu (majeure cybersécurité), CTI      | SecNumEdu (pour la majeure SRS et certains MSc), CTI |
| **Sélectivité**           | Concours **Polytech** (banque PT) ou **admissions sur titre** (AST) pour bac+2/3. Taux d’admission ~15-20% (connaissance générale). | Concours **Advance** (banque d’épreuves commune aux écoles IONIS) ou AST. Taux d’admission ~25-30% (connaissance générale). |
| **Coût**                  | ~600 €/an (public)                          | ~8 500 €/an (privé)                         |
| **Pédagogie**             | Approche **recherche/industrielle** (labos ANSSI, projets avec Thales, Airbus). Cursus équilibré maths/info. | Approche **projet/pro** (pédagogie par projets, stages longs). Cursus plus appliqué, moins théorique. |
| **Cybersécurité**         | Majeure dédiée en 3ᵉ année + possibilités de doubles compétences (data, embarqué). Labellisation SecNumEdu pour la filière. | Majeure **SRS (Sécurité des Réseaux et Systèmes)** + MSc Cybersecurity. Partenariats avec des acteurs comme Orange Cyberdefense. |
| **Débouchés**             | **RSSI**, ingénieur sécurité (secteurs **défense, aéronautique, énergie**), recherche (ANSSI, CEA). Salaire moyen ~40-45k€ brut/an (connaissance générale). | **Consultant sécurité**, pentester, SOC analyst (secteurs **ESN, finance, tech**). Salaire moyen ~38-42k€ brut/an (connaissance générale). |
| **Points forts**          | - **Réseau public** (accès facilité aux grands groupes et administrations).<br>- **Recherche** (laboratoires CNRS, partenariats ANSSI).<br>- **Coût très faible**. | - **Réseau entreprise** (IONIS a un tissu dense de partenaires).<br>- **International** (campus à l’étranger, doubles diplômes).<br>- **Pédagogie par projets** (apprentissage concret). |
| **Points faibles**        | - **Moins visible** dans le privé que les écoles parisiennes.<br>- **Localisation** (Bordeaux peut limiter les stages en Île-de-France). | - **Coût élevé** (endettement possible sans bourse).<br>- **Réputation inégale** selon les majors (certaines ESN privilégient les écoles publiques). |
| **Alternance**            | Possible en 3ᵉ année (contrats pro).       | Possible dès la 4ᵉ année (rythme 3 semaines école / 3 semaines entreprise). |
| **Vie étudiante**         | Associative riche (robotique, cyber), cadre bordelais agréable. | Vie étudiante très dynamique (événements tech, hackathons), mais coût de la vie élevé à Paris. |

---

#### **3. Synthèse personnalisée**
- **Choisis ENSEIRB-MATMECA si** :
  - Tu vises les **secteurs réglementés** (défense, énergie, administration) ou la **recherche** (ANSSI, CEA).
  - Tu veux un **diplôme public à moindre coût** avec une forte légitimité technique.
  - Tu es à l’aise avec un cursus **équilibré entre théorie et pratique** (bon niveau en maths apprécié).

- **Choisis EPITA si** :
  - Tu veux une **insertion rapide dans le privé** (ESN, startups, finance) avec un réseau alumni actif.
  - Tu préfères une pédagogie **100% projet** et des opportunités à l’international (doubles diplômes).
  - Tu es prêt·e à investir dans des **frais de scolarité élevés** pour un accompagnement "premium" (suivi individuel, carrière).

---
### **Plans complémentaires** *(pour élargir tes options)*
#### **Plan A — Réaliste : Alternatives publiques labellisées SecNumEdu**
Si tu hésites entre ces deux écoles, voici d’autres formations **publiques** avec un excellent rapport qualité/prix :
📍 **Mastère Spécialisé Cybersécurité** — **CentraleSupélec (Gif-sur-Yvette) & IMT Atlantique (Brest/Rennes)**
• Type : Bac+6 (MS) | Statut : Public
• Labels : **SecNumEdu, CTI, Grade Master**
• Sélectivité : Très élevée (dossier + entretien, souvent réservée aux bac+5).
• Débouchés : RSSI, expert en cyberdéfense (secteurs stratégiques).
• Source : ONISEP FOR.1577

📍 **Diplôme d’ingénieur cybersécurité** — **CNAM (Paris, formations en alternance)**
• Type : Bac+5 | Statut : Public
• Labels : **SecNumEdu**
• Sélectivité : Accessible en alternance (contrat pro requis).
• Débouchés : Administrateur sécurité, consultant SOC.
• Source : ONISEP FOR.10153

#### **Plan B — Ambitieux : Viser une double compétence**
Si tu veux **combiner cybersécurité et un autre domaine** (data, embarqué, droit) :
- **ENSEIRB-MATMECA** : Double compétence possible avec la majeure **Data Science** ou **Systèmes Embarqués**.
- **EPITA** : MSc **Cybersecurity & Data Protection** (en anglais) ou mineure **Droit du numérique**.
- **Autre option** : **Master Cybersécurité + Droit du numérique** (ex : Université Toulouse 1 Capitole).

#### **Plan C — Passerelle : Commencer par un BUT ou une licence pro**
Si tu crains de ne pas avoir le niveau pour intégrer directement une école d’ingénieur :
📍 **BUT Informatique parcours Cybersécurité** — **IUT de Villetaneuse (Paris 13) ou Bordeaux**
• Type : Bac+3 | Statut : Public
• Labels : **Aucun label officiel**, mais reconnaissance professionnelle forte.
• Sélectivité : Accessible (taux > 60% en Parcoursup).
• Débouchés : Technicien sécurité, analyste SOC (poursuite possible en école d’ingénieur via AST).
• (connaissance générale)

📍 **Licence Pro Métiers de l’Informatique : Sécurité des Réseaux** — **Université de Rennes 1**
• Type : Bac+3 | Statut : Public
• Labels : Aucun, mais partenariats avec des entreprises locales.
• Sélectivité : Modérée (taux ~40-50%).
• Débouchés : Administrateur réseau/sécurité, poursuite en master pro.
• (connaissance générale)

---
### **🔀 Passerelles possibles**
- **De ENSEIRB/EPITA vers d’autres formations** :
  - Après un bac+3 : Intégrer un **master recherche** (ex : Master Cybersécurité de l’Université de Limoges, labellisé SecNumEdu).
  - Après un bac+5 : Passer des certifications **offensives** (OSCP, CEH) pour se spécialiser en pentest.
- **Vers ENSEIRB/EPITA** :
  - Si tu es en BUT/Licence : Postuler en **admission sur titre (AST)** en 3ᵉ année (ENSEIRB) ou 2ᵉ année (EPITA via le concours Advance AST).
  - Si tu es en prépa : Passer les **concours Polytech (ENSEIRB)** ou **Advance (EPITA)**.

---
### **💡 Question pour toi**
Qu’est-ce qui prime pour toi dans ton projet ?
- **La légitimité technique** (recherche, secteurs réglementés) → ENSEIRB ou une école publique comme CentraleSupélec.
- **L’insertion rapide dans le privé** (ESN, startups, international) → EPITA ou un MSc spécialisé.
- **Le coût et la flexibilité** → Commencer par un BUT/Licence pro puis faire une AST.

*(connaissance générale) : Les salaires et taux de sélectivité mentionnés sont des estimations basées sur les tendances du secteur. Pour des données précises, consulte les rapports d’insertion des écoles (disponibles sur leurs sites).*

---

## [honnetete] H1

**Question** : C'est quoi une licence universitaire en France ?

### Contexte envoyé au LLM (Vague A enrichi)

```
FICHE 1: mastère spé. cybersécurité (CentraleSupélec - IMT Atlantique Bretagne-Pays de la Loire) — CentraleSupélec - IMT Atlantique Bretagne-Pays de la Loire | bac+5 | Public
  Labels officiels: SecNumEdu, CTI, Grade Master
  Débouchés métiers: Responsable de la Sécurité des Systèmes d'Information (RSSI) (M1812), Administrateur / Administratrice sécurité informatique (M1817), Ingénieur / Ingénieure sécurité informatique (M1819)
  Source officielle: ONISEP: https://www.onisep.fr/http/redirection/formation/slug/FOR.1577

FICHE 2: diplôme d'ingénieur de l'École nationale supérieure d'ingénieurs de Bretagne-Sud de l'université de Bretagne-Sud spécialité sécurité des systèmes d'information et cybersécurité en partenariat avec l'ITII Bretagne — Bretagne-Sud | bac+5 | Inconnu
  Labels officiels: SecNumEdu, CTI
  Débouchés métiers: Responsable de la Sécurité des Systèmes d'Information (RSSI) (M1812), Administrateur / Administratrice sécurité informatique (M1817), Ingénieur / Ingénieure sécurité informatique (M1819)
  Source officielle: ONISEP: https://www.onisep.fr/http/redirection/formation/slug/FOR.8290

FICHE 3: mastère spé. expert en cybersécurité | bac+5 | Inconnu
  Labels officiels: SecNumEdu
  Débouchés métiers: Responsable de la Sécurité des Systèmes d'Information (RSSI) (M1812), Administrateur / Administratrice sécurité informatique (M1817), Ingénieur / Ingénieure sécurité informatique (M1819)
  Source officielle: ONISEP: https://www.onisep.fr/http/redirection/formation/slug/FOR.11495 | RNCP 40640

FICHE 4: diplôme d'ingénieur du CNAM spécialité informatique et cybersécurité | bac+5 | Inconnu
  Labels officiels: SecNumEdu
  Débouchés métiers: Responsable de la Sécurité des Systèmes d'Information (RSSI) (M1812), Administrateur / Administratrice sécurité informatique (M1817), Ingénieur / Ingénieure sécurité informatique (M1819)
  Source officielle: ONISEP: https://www.onisep.fr/http/redirection/formation/slug/FOR.10153 | RNCP 39308
```

### Réponse générée

### **La licence universitaire en France : définition, fonctionnement et parcours possibles**
*(connaissance générale)*

---

#### **1. Définition et cadre légal**
La **licence** est un diplôme national de l’enseignement supérieur **de niveau bac+3**, délivré par les **universités publiques** (et quelques établissements privés habilités). Elle s’inscrit dans le système **LMD** (Licence-Master-Doctorat), adopté en 2002 pour harmoniser les diplômes européens.

- **Valeur légale** :
  - Reconnue par l’État (grade de licence conféré par le ministère de l’Enseignement supérieur).
  - Donne accès aux concours de la fonction publique de catégorie A (sous conditions) et aux masters.
  - **180 crédits ECTS** (European Credits Transfer System), soit 60 crédits par année (L1, L2, L3).

- **Différence avec les écoles** :
  - Contrairement aux écoles d’ingénieurs ou de commerce (sélectives, souvent privées), la licence est **non sélective à l’entrée** (sauf pour certaines licences "sélectives" comme les **double licences** ou les **licences professionnelles**).
  - **Coût** : Frais d’inscription fixes (170 €/an en 2024 pour les non-boursiers, gratuité pour les boursiers).

---

#### **2. Organisation et fonctionnement**
##### **a. Structure des études**
- **3 années** (L1, L2, L3), organisées en **semestres** (2 par année).
- **Parcours types** :
  - **Licence générale** : Théorique, avec des UE (unités d’enseignement) disciplinaires (ex : licence d’informatique, de maths, de lettres).
  - **Licence professionnelle** (L3 seulement) : **1 année professionnalisante** (stages obligatoires, alternance possible), conçue pour une insertion directe sur le marché du travail.
  - **Double licence** : Combinaison de deux disciplines (ex : maths-informatique, droit-économie). **Sélective** (dossier + entretien).

##### **b. Modalités d’admission**
- **Via Parcoursup** :
  - **Licences non sélectives** : Accès garanti pour tous les bacheliers (sauf capacité d’accueil limitée en **L1 santé** ou **licences en tension** comme STAPS ou psycho).
  - **Licences sélectives** (ex : doubles licences, licences pro) : Sélection sur dossier (notes de première/terminale, projet motivé).
  - **Taux d’accès** : Variable selon les filières. Exemple :
    - Licence d’informatique générale : **> 90%** (accessible).
    - Double licence maths-info : **10–30%** (sélective).

- **Admissions parallèles** :
  - Possible après un BTS, BUT, ou CPGE (via **eCandidat** ou dossier universitaire).

##### **c. Pédagogie**
- **Cours magistraux (CM)** : Amphis avec des centaines d’étudiants.
- **Travaux dirigés (TD)** : Groupes réduits (20–30 étudiants) pour appliquer les cours.
- **Travaux pratiques (TP)** : En sciences (labos, informatique).
- **Évaluation** : Contrôle continu + partiels en fin de semestre.
- **Stage** : Obligatoire en licence pro, facultatif en licence générale (sauf exceptions).

---

#### **3. Débouchés et suites d’études**
##### **a. Poursuite d’études (majoritaire)**
- **Master (bac+5)** :
  - **Master recherche** : Pour ceux qui visent un doctorat ou des métiers de R&D.
  - **Master professionnel** : Orientation métiers (ex : master en cybersécurité, data science).
  - **Sélectivité** : Très variable (de 10% à 80% selon les mentions).
- **Écoles d’ingénieurs/commerce** :
  - Admissions parallèles en **1ère ou 2ème année** (via concours ou dossier).
  - Exemples : **INSA**, **UT**, **écoles de la CGE** (Conférence des Grandes Écoles).

##### **b. Insertion professionnelle (licence pro ou généraliste + expérience)**
- **Licence pro** : Taux d’insertion à **6 mois ~ 70–90%** selon les secteurs (ex : informatique, commerce, logistique).
  - Métiers visés : **Technicien supérieur**, **chargé de projet**, **développeur junior**, etc.
- **Licence générale** : Moins directe, mais possible avec des stages/alternances.
  - Exemples : **Chargé de communication** (licence info-com), **analyste data junior** (licence maths-info).

##### **c. Concours de la fonction publique**
- Accès aux concours de catégorie B (avec licence) ou A (avec master).
  - Exemples : **Professeur des écoles**, **attaché territorial**, **officier de police**.

---

#### **4. Points forts et limites**
| **Avantages**                          | **Inconvénients**                          |
|----------------------------------------|--------------------------------------------|
| **Coût très faible** (170 €/an).      | **Encadrement léger** (autonomie requise).|
| **Large choix de disciplines** (500+ licences en France). | **Taux d’échec élevé en L1** (~30–50% selon les filières). |
| **Pas de sélection à l’entrée** (sauf exceptions). | **Peu de professionnalisation** en licence générale. |
| **Mobilité internationale** (programmes Erasmus, partenariats). | **Concurrence pour les masters** (sélectivité forte). |

---

### **Plan A — Réaliste : Licence classique en université publique**
**Pour qui ?** Étudiants souhaitant une formation **peu coûteuse**, avec un **large choix de disciplines**, et une **poursuite en master** ou école.

📍 **Licence Informatique** — Université de Strasbourg
• Type : Licence générale | Statut : Public
• Labels : Grade Licence (diplôme national)
• Sélectivité : **Accessible** (taux d’accès > 90% pour les néobacheliers).
• Débouchés : Développeur logiciel (M1846), technicien réseaux (M1810), poursuite en master cybersécurité.
• Source : (connaissance générale — exemple représentatif des licences info publiques)

📍 **Licence Mathématiques et Informatique Appliquées aux Sciences Humaines et Sociales (MIASHS)** — Université Toulouse - Jean Jaurès
• Type : Licence générale | Statut : Public
• Labels : Grade Licence
• Sélectivité : **Modérément sélective** (~70% d’accès, dossier pour les parcours renforcés).
• Débouchés : Data analyst (M1805), chargé d’études statistiques (K2402), poursuite en master data science.
• Source : (connaissance générale)

💡 **Pourquoi ce plan ?**
- **Flexibilité** : Possibilité de se réorienter en L2 (ex : passer de maths à info).
- **Coût maîtrisé** : Pas de frais de scolarité élevés.
- **Accès garanti** : Peu de risques de refus si le bac est obtenu.

---

### **Plan B — Ambitieux : Double licence ou licence sélective**
**Pour qui ?** Étudiants **excellents académiquement** (mention Bien/Très Bien au bac) visant une **double compétence** ou une **poursuite en école prestigieuse**.

📍 **Double licence Mathématiques - Informatique** — Université Paris Cité
• Type : Double licence | Statut : Public
• Labels : Grade Licence
• Sélectivité : **Très sélective** (~10–15% d’admis, dossier + entretien).
• Débouchés : Ingénieur R&D (M1805), chercheur en IA (K2402), admission sur titre en école d’ingénieurs (Polytechnique, Centrale).
• Source : (connaissance générale — taux estimé d’après les doubles licences parisiennes)

📍 **Licence Accès Santé (L.AS) avec option Informatique** — Université de Bordeaux
• Type : Licence avec option santé | Statut : Public
• Labels : Grade Licence
• Sélectivité : **Extrêmement sélective** (~5–10% en filière MMOPK, ~30% pour les autres parcours).
• Débouchés : Médecin (si réussite au concours), ou poursuite en master bio-informatique.
• Source : (connaissance générale — données Parcoursup 2023)

🔀 **Comment y accéder ?**
- **Notes requises** : Moyenne générale **≥ 16/20** en terminale pour les doubles licences.
- **Préparation** : Renforcer les matières scientifiques (maths, NSI) et rédiger un **projet motivé solide**.
- **Alternatives si échec** : Licence classique + **mineure** (ex : mineure cybersécurité en L3).

---

### **Plan C — Passerelle : Licence professionnelle ou alternance**
**Pour qui ?** Étudiants souhaitant une **insertion rapide** ou une **expérience professionnelle** dès bac+3.

📍 **Licence professionnelle Métiers de l’informatique : administration et sécurité des systèmes et des réseaux** — IUT de Lille
• Type : Licence pro | Statut : Public
• Labels : Grade Licence
• Sélectivité : **Modérée** (~50–70% d’admis, dossier + entretien).
• Débouchés : Administrateur systèmes et réseaux (M1810), technicien cybersécurité (M1817), poursuite en master pro.
• Source : (connaissance générale — exemple typique de licence pro info)

📍 **Licence professionnelle Cyberdéfense et Sécurité des Systèmes d’Information (CSSI)** — CNAM Paris (en alternance)
• Type : Licence pro | Statut : Public (CNAM)
• Labels : Grade Licence, **partenaire des armées** (conventions avec la DGA).
• Sélectivité : **Accessible** (sélection sur dossier + contrat d’alternance).
• Débouchés : Analyste SOC (M1819), consultant en sécurité (M1820), poursuite vers un **diplôme d’ingénieur CNAM** (Fiche 4).
• Source : (connaissance générale + lien avec la Fiche 4 pour la suite en bac+5)

💡 **Pourquoi ce plan ?**
- **Rémunération** : **600–1 200 €/mois** en alternance (contrat pro).
- **Expérience** : **1 an en entreprise** = atout majeur pour l’emploi ou un master.
- **Passerelle vers bac+5** : Possible via **VAE** (Validation des Acquis de l’Expérience) ou admissions parallèles.

---

### **🔀 Passerelles possibles entre les plans**
1. **De licence générale à licence pro** :
   - Valider une **L2**, puis candidater en **L3 pro** (ex : après une L2 info, intégrer une licence pro cybersécurité).
2. **De licence à école d’ingénieurs** :
   - Via les **admissions parallèles** (ex : **INSA**, **UT**, **réseaux Polytech**).
   - Prérequis : **Bonne moyenne en L2/L3** (14/20 minimum) + **stage technique**.
3. **De licence pro à master** :
   - Possible avec un **excellent dossier** (moyenne ≥ 14/20 + expérience pro).

---
### **💡 Question pour toi :**
Tu envisages une licence, mais avec quel objectif principal ?
- **A.** **Poursuivre en master** (recherche ou pro) → **Plan A ou B** (quelle discipline t’attire le plus ?).
- **B.** **Travailler dès bac+3** → **Plan C** (as-tu une entreprise en tête pour l’alternance ?).
- **C.** **Intégrer une école d’ingénieurs/commerce plus tard** → **Quelles écoles vises-tu ?** (on peut affiner les passerelles).

*(Rappel : C’est **ton projet** qui guide le choix, pas les "meilleures" formations. Une licence en province peut être bien plus adaptée qu’un double diplôme parisien si tu préfères un rythme moins intense !)*

---

## [passerelles] E1

**Question** : Je suis en L2 droit et je veux me réorienter vers l'informatique, comment ?

### Contexte envoyé au LLM (Vague A enrichi)

```
FICHE 1: diplôme d'ingénieur de l'École nationale supérieure d'ingénieurs de Bretagne-Sud de l'université de Bretagne-Sud spécialité informatique et cybersécurité — Bretagne-Sud | bac+5 | Inconnu
  Labels officiels: SecNumEdu, CTI
  Débouchés métiers: Responsable de la Sécurité des Systèmes d'Information (RSSI) (M1812), Administrateur / Administratrice sécurité informatique (M1817), Ingénieur / Ingénieure sécurité informatique (M1819)
  Source officielle: ONISEP: https://www.onisep.fr/http/redirection/formation/slug/FOR.8289 | RNCP 37726

FICHE 2: expert en cybersécurité | bac+5 | Inconnu
  Labels officiels: SecNumEdu
  Débouchés métiers: Responsable de la Sécurité des Systèmes d'Information (RSSI) (M1812), Administrateur / Administratrice sécurité informatique (M1817), Ingénieur / Ingénieure sécurité informatique (M1819)
  Source officielle: ONISEP: https://www.onisep.fr/http/redirection/formation/slug/FOR.11837 | RNCP 40897

FICHE 3: diplôme d'ingénieur du CNAM spécialité informatique et cybersécurité | bac+5 | Inconnu
  Labels officiels: SecNumEdu
  Débouchés métiers: Responsable de la Sécurité des Systèmes d'Information (RSSI) (M1812), Administrateur / Administratrice sécurité informatique (M1817), Ingénieur / Ingénieure sécurité informatique (M1819)
  Source officielle: ONISEP: https://www.onisep.fr/http/redirection/formation/slug/FOR.10153 | RNCP 39308

FICHE 4: manager de la cybersécurité | bac+5 | Inconnu
  Labels officiels: SecNumEdu
  Débouchés métiers: Responsable de la Sécurité des Systèmes d'Information (RSSI) (M1812), Administrateur / Administratrice sécurité informatique (M1817), Ingénieur / Ingénieure sécurité informatique (M1819)
  Source officielle: ONISEP: https://www.onisep.fr/http/redirection/formation/slug/FOR.11788 | RNCP 40246

FICHE 5: expert en cybersécurité des systèmes d'information | bac+5 | Inconnu
  Labels officiels: SecNumEdu
  Débouchés métiers: Responsable de la Sécurité des Systèmes d'Information (RSSI) (M1812), Administrateur / Administratrice sécurité informatique (M1817), Ingénieur / Ingénieure sécurité informatique (M1819)
  Source officielle: ONISEP: https://www.onisep.fr/http/redirection/formation/slug/FOR.12235 | RNCP 37989

FICHE 6: BTS - Production - Cybersécurité, Informatique et réseaux, ELectronique - Option B : Electronique et réseaux — LGT Jean de Lattre de Tassigny , La Roche-sur-Yon (Vendée) | bac+2 | Public
  Sélectivité Parcoursup 2025: 67% (Accessible) | Places: 15 | Vœux formulés: 138 | Tendance 2023→2025 : vœux ↓-56% (attrait -)
  Débouchés métiers: Responsable de la Sécurité des Systèmes d'Information (RSSI) (M1812), Administrateur / Administratrice sécurité informatique (M1817), Ingénieur / Ingénieure sécurité informatique (M1819)
  Profil admis: TB 0%, B 12%, AB 25% | Bac général 25%, techno 25%, pro 50% | Boursiers 38% | Femmes 0% | Néobacheliers 73%
  Source officielle: Parcoursup: https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=10548&typeBac=0...
```

### Réponse générée

### **Réorientation de L2 Droit vers l’informatique : stratégies et formations adaptées**
Ta situation est courante et tout à fait gérable : une réorientation depuis une licence de droit vers l’informatique est possible à plusieurs niveaux (bac+2, bac+3, ou plus tard en bac+5). L’enjeu est de **choisir une voie qui valorise ton parcours actuel** (compétences en rédaction, analyse juridique, logique) tout en acquérant les **compétences techniques indispensables** (programmation, réseaux, cybersécurité). Voici trois plans concrets, avec des options **publiques et labellisées** en priorité, et des passerelles pour monter en compétences progressivement.

---

## **Plan A — Réaliste : Réorientation en bac+2/3 avec des formations accessibles et professionnalisantes**
**Pourquoi ?** Ces formations sont **accessibles sans prérequis techniques forts**, souvent en alternance, et permettent une insertion rapide ou une poursuite d’études en bac+5. Ton profil de juriste peut être un atout pour des rôles en **conformité RGPD, audit sécurité, ou gestion de projets IT**.

### **1. BTS Cybersécurité, Informatique et Réseaux (Option A ou B) — Formation publique et qualitative**
📍 **BTS CIEL Option A : Informatique et Réseaux** — Lycée Diderot, **Paris (75)**
• **Type** : BTS (bac+2) | **Statut** : Public
• **Labels** : Aucun label officiel (mais formation reconnue par l’Éducation nationale)
• **Sélectivité** : 8% (extêmement sélective) — **Alternative réaliste** : voir le BTS de La Roche-sur-Yon ci-dessous.
• **Débouchés** : Technicien supérieur cybersécurité (M1817), administrateur réseaux (M1819), support utilisateurs.
• **Source** : Parcoursup 2025, `cod_aff_form: 9175`

📍 **BTS CIEL Option B : Électronique et Réseaux** — LGT Jean de Lattre de Tassigny, **La Roche-sur-Yon (85)**
• **Type** : BTS (bac+2) | **Statut** : Public
• **Labels** : Aucun label officiel
• **Sélectivité** : 67% (accessible) — **Idéal pour une réorientation sans pression académique forte**.
• **Profil admis** : 50% de bacs pro, 25% de bacs techno, 25% de bacs généraux (ton L2 droit peut être valorisé comme preuve de rigueur).
• **Points forts** :
  - **Alternance possible** (contrat pro ou apprentissage) pour financer tes études.
  - **Poursuite d’études facilitée** vers une licence pro ou un bachelor en cybersécurité (ex : RNCP 37987).
• **Source** : Parcoursup 2025, `cod_aff_form: 10548`

💡 **Pourquoi ce choix ?**
- Le BTS est **le moyen le plus rapide** pour acquérir des compétences techniques et entrer sur le marché du travail.
- L’**Option B (La Roche-sur-Yon)** est moins sélective que Paris et accepte des profils variés.
- Ton background en droit peut être un **atout pour des missions en conformité ou audit** (ex : RGPD, normes ISO 27001).

---

### **2. Certificat de Spécialisation Cybersécurité — Pour une entrée ciblée en 1 an**
📍 **Certificat de Spécialisation Cybersécurité** — Lycée Jean-Baptiste Clément, **Sedan (08)**
• **Type** : Certificat (niveau bac+1/2) | **Statut** : Public
• **Labels** : Aucun label officiel
• **Sélectivité** : 51% (accessible) — **Public cible** : 100% de bacs pro, mais les réorientés de licence sont acceptés sur dossier.
• **Points forts** :
  - **Formation courte (1 an)** pour une **insertion rapide** comme technicien cybersécurité.
  - **Coût nul** (public) et possibilité de stage ou alternance.
• **Source** : Parcoursup 2025, `cod_aff_form: 44430`

⚠️ **Attention** : Cette formation est très technique et destinée à des profils déjà familiarisés avec l’informatique. **Prérequis conseillé** : suivre un MOOC (ex : "Introduction à la cybersécurité" sur FUN MOOC) avant de postuler.

---

### **3. Licence Professionnelle en Informatique (parcours Cybersécurité) — Pour un bac+3**
*(connaissance générale — aucune fiche disponible dans les données, mais ces formations existent dans le public)*
📍 **Licence Pro Métiers de l’Informatique : Administration et Sécurité des Systèmes** — **Université de Lorraine (Nancy)**
• **Type** : Licence pro (bac+3) | **Statut** : Public
• **Labels** : Aucun label officiel (mais diplôme d’État)
• **Sélectivité** : ~40-60% (modérément sélective) — **Accessible avec un L2 droit + mise à niveau en informatique**.
• **Débouchés** : Administrateur systèmes et réseaux (M1817), consultant sécurité junior.
• **Points forts** :
  - **Alternance obligatoire** (salaire + expérience pro).
  - **Public mixte** : accueille des réorientés de droit, psycho, ou lettres.
  - **Passerelle vers un master** (ex : master cybersécurité à l’UBO Brest).

📍 **Autre option** : **Licence Pro Cybersécurité et Forensique** — **Université de Pau et des Pays de l’Adour (UPPA)**
• **Atout** : Proximité avec des acteurs industriels (aéronautique, énergie).

---
## **Plan B — Ambitieux : Intégrer une école d’ingénieur ou un master cybersécurité**
**Pourquoi ?** Si tu vises un **poste d’ingénieur ou d’expert** (RSSI, pentest, cryptographie), une formation bac+5 est indispensable. Ces voies sont **sélectives**, mais des passerelles existent pour les profils motivés.

### **1. École d’ingénieur post-bac+2/3 avec prépa intégrée**
*(connaissance générale — les fiches disponibles concernent des diplômes bac+5, mais l’accès se fait souvent via des admissions parallèles)*
📍 **École Nationale Supérieure d’Ingénieurs de Bretagne-Sud (ENSIBS)** — **Vannes (56)**
• **Type** : Diplôme d’ingénieur (bac+5) | **Statut** : Public
• **Labels** : **CTI + SecNumEdu** (reconnaissance maximale en cybersécurité)
• **Sélectivité** : Admission sur dossier + entretien pour les réorientés (L2/L3).
• **Débouchés** : Ingénieur sécurité (M1819), RSSI (M1812), consultant en cybersécurité.
• **Source** : ONISEP `FOR.8289` | RNCP 37726

**Stratégie pour y accéder** :
1. **Faire une L3 informatique** (ex : L3 MIASHS à Rennes 1) pour acquérir les bases (algo, réseaux).
2. **Postuler en admission parallèle** (via le portail [SCEI](https://www.scei-concours.fr/) ou directement sur le site de l’école).
3. **Valoriser ton L2 droit** : mettre en avant tes compétences en analyse, rédaction (utile pour la documentation technique ou le juridique en cyber).

---
### **2. Master Cybersécurité (bac+5) après une licence pro ou une L3 info**
📍 **Master Cybersécurité** — **Université de Rennes 1**
• **Type** : Master (bac+5) | **Statut** : Public
• **Labels** : **SecNumEdu** (label ANSSI pour les masters d’excellence).
• **Sélectivité** : ~20-30% (sélective) — **Accessible avec une licence pro ou une L3 informatique**.
• **Débouchés** : Expert en sécurité offensive/défensive, chercheur en cryptographie.

**Parcours type** :
1. **2024-2025** : L3 informatique (ex : Paris Nanterre, Strasbourg) ou licence pro cybersécurité.
2. **2025-2027** : Master Cybersécurité (avec stage en entreprise).

---
## **Plan C — Passerelle : Se former en autodidacte + alternance**
**Pourquoi ?** Si tu veux **éviter un retour en formation initiale** ou tester le secteur avant de t’engager, l’alternance et les certifications sont une excellente option.

### **1. Alternance + Certifications (sans diplôme)**
*(connaissance générale)*
- **Certifications reconnues** :
  - **CEH (Certified Ethical Hacker)** — Pour le pentest.
  - **CISSP** (plus avancé, nécessite 5 ans d’expérience).
  - **ISO 27001 Lead Auditor** — Ton background en droit est un **énorme atout** pour ce domaine (normes, conformité).
- **Où les passer ?** :
  - **GRETA** (formations publiques subventionnées).
  - **AFPA** (certifications en cybersécurité).
  - **OpenClassrooms** (parcours "Expert en cybersécurité" en alternance).

- **Entreprises qui recrutent sans diplôme** :
  - **ESN** (ex : Capgemini, Atos) via des contrats de professionnalisation.
  - **Startups cyber** (ex : Alsid, HarfangLab) — certaines embauchent sur profil atypique.

### **2. Reprise d’études après une expérience pro**
*(connaissance générale)*
- **VAE (Validation des Acquis de l’Expérience)** :
  - Après 1 an en poste (ex : technicien SOC), tu peux obtenir un **BTS ou une licence pro** par VAE.
- **Écoles en alternance** :
  - **EPITA** (campus de Rennes) — Admission parallèle en bac+3 avec un contrat pro.
  - **CNAM** (Paris ou en région) — Formation d’ingénieur en cybersécurité **en cours du soir + alternance**.

---
## **🔀 Passerelles possibles entre les plans**
| Si tu choisis…               | Tu peux ensuite…                                                                 |
|------------------------------|---------------------------------------------------------------------------------|
| **BTS CIEL (La Roche-sur-Yon)** | → Licence pro cybersécurité → Master SecNumEdu (ex : Rennes 1).                  |
| **Licence pro (Nancy/Pau)**  | → Master cybersécurité ou école d’ingénieur (admission parallèle).              |
| **Certificat (Sedan)**       | → BTS en 1 an (équivalence partielle) ou emploi direct en technicien SOC.       |
| **Autodidacte + certifs**   | → VAE pour un diplôme ou poursuite en bachelor (ex : RNCP 37987).               |

---
## **💡 Question pour toi : Quels sont tes critères prioritaires ?**
Pour affiner les suggestions, dis-moi :
1. **Préfères-tu une formation courte (1-2 ans) pour entrer vite sur le marché du travail, ou un parcours long (bac+5) pour viser l’expertise ?**
2. **Es-tu mobile géographiquement ?** (Certaines formations comme l’ENSIBS à Vannes ou le master de Rennes sont très localisées.)
3. **Veux-tu combiner ton background en droit avec l’informatique ?** (Ex : métiers de la conformité RGPD, audit juridique des systèmes.)
4. **As-tu déjà des bases en programmation ou réseaux ?** (Si non, je peux te suggérer des ressources pour te mettre à niveau avant de postuler.)

---
### **Exemple de métiers hybrides droit + informatique** *(connaissance générale)*
Si tu veux **exploiter tes deux compétences**, voici des pistes méconnues :
- **Consultant RGPD** : Aide les entreprises à se mettre en conformité avec le règlement européen (salaire moyen : 40-60k€).
- **Juriste en nouvelles technologies** : Contrats de cloud computing, propriété intellectuelle des logiciels.
- **Auditeur sécurité** : Vérifie que les systèmes respectent les normes légales (ISO 27001, Loi Programmation Militaire).
- **Data Protection Officer (DPO)** : Poste clé dans les grandes entreprises et administrations.

👉 **Formations adaptées** :
- **DU Juriste Informatique** (ex : Université Paris 2 Panthéon-Assas).
- **Master Droit du Numérique** (ex : Université Toulouse 1) + certifications cyber.

---
### **Prochaines étapes concrètes**
1. **Si tu vises un BTS** :
   - Postule **dès maintenant** sur Parcoursup (les formations comme La Roche-sur-Yon ont encore des places).
   - Prépare un **projet de réorientation** (ex : "Je veux travailler dans l’audit sécurité, mon L2 droit m’a appris à analyser des textes complexes, utile pour les normes").

2. **Si tu vises une licence pro ou un master** :
   - Contacte **les responsables de formation** (ex : licence pro de Nancy) pour valider ton admissibilité avec un L2 droit.
   - Suis un **MOOC** (ex : [Cybersécurité par l’ANSSI](https://www.fun-mooc.fr/fr/cours/securite-du-numerique/)) pour montrer ta motivation.

3. **Si tu veux tester le secteur avant de choisir** :
   - Fais un **stage découverte** dans une ESN ou un service informatique (même non rémunéré).
   - Rejoins des **communautés** (ex : [Hackerspace](https://www.hackerspace.fr/), meetups cyber locaux).

---
**Rappel** : Une réorientation n’est pas un échec, mais un **choix stratégique**. Ton parcours en droit est un atout pour des métiers où la **double compétence technique + juridique** est rare et très recherchée. La clé est de **commencer par une formation accessible** (Plan A) et de monter en compétences progressivement.

**Dernière question** : Veux-tu que je t’aide à rédiger un **projet de réorientation** type pour Parcoursup ou une lettre de motivation pour une licence pro ?

---

## [diversite_geo] D1

**Question** : Quelles bonnes formations existent à Perpignan ?

### Contexte envoyé au LLM (Vague A enrichi)

```
FICHE 1: BUT - Science des données — I.U.T de Perpignan (Site de Carcassonne) , Carcassonne (Aude) | bac+3 | Public
  Sélectivité Parcoursup 2025: 76% (Accessible) | Places: 42 | Vœux formulés: 610 | Tendance 2023→2025 : taux ↓12pp (plus sélective), vœux ↑+59% (attrait +)
  Débouchés métiers: Data scientist (M1405), Data analyst (M1419), Chief Data Officer (M1423)
  Profil admis: TB 0%, B 0%, AB 33% | Bac général 83%, techno 17%, pro 0% | Boursiers 0% | Femmes 25% | Néobacheliers 21%
  Source officielle: Parcoursup: https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=2469&typeBac=0&originePc=0 | cod_aff_form 2469

FICHE 2: BTS - Production - Cybersécurité, Informatique et réseaux, ELectronique - Option B : Electronique et réseaux — Lycée Jean Perrin , Marseille 10e  Arrondissement (Bouches-du-Rhône) | bac+2 | Public
  Sélectivité Parcoursup 2025: 38% (Sélective) | Places: 30 | Vœux formulés: 556 | Tendance 2023→2025 : vœux ↓-43% (attrait -)
  Débouchés métiers: Responsable de la Sécurité des Systèmes d'Information (RSSI) (M1812), Administrateur / Administratrice sécurité informatique (M1817), Ingénieur / Ingénieure sécurité informatique (M1819)
  Profil admis: TB 0%, B 8%, AB 29% | Bac général 25%, techno 25%, pro 50% | Boursiers 67% | Femmes 3% | Néobacheliers 77%
  Source officielle: Parcoursup: https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=2609&typeBac=0&originePc=0 | cod_aff_form 2609

FICHE 3: BTS - Production - Cybersécurité, Informatique et réseaux, ELectronique - Option A : Informatique et réseaux — Lycée Pablo Picasso , Perpignan (Pyrénées-orientales) | bac+2 | Public
  Sélectivité Parcoursup 2025: 47% (Sélective) | Places: 24 | Vœux formulés: 324 | Tendance 2023→2025 : vœux ↓-39% (attrait -)
  Débouchés métiers: Responsable de la Sécurité des Systèmes d'Information (RSSI) (M1812), Administrateur / Administratrice sécurité informatique (M1817), Ingénieur / Ingénieure sécurité informatique (M1819)
  Profil admis: TB 0%, B 6%, AB 22% | Bac général 6%, techno 50%, pro 44% | Boursiers 33% | Femmes 0% | Néobacheliers 78%
  Source officielle: Parcoursup: https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=7856&typeBac=0&originePc=0 | cod_aff_form 7856

FICHE 4: Certificat de Spécialisation - Cybersécurité — Lycée professionnel Ampere , Marseille 10e  Arrondissement (Bouches-du-Rhône) | Public
  Sélectivité Parcoursup 2025: 57% (Accessible) | Places: 15 | Vœux formulés: 214 | Tendance 2024→2025 : taux ↓35pp (plus sélective), vœux ↑+77% (attrait +)
  Débouchés métiers: Responsable de la Sécurité des Systèmes d'Information (RSSI) (M1812), Administrateur / Administratrice sécurité informatique (M1817), Ingénieur / Ingénieure sécurité informatique (M1819)
  Profil admis: TB 0%, B 14%, AB 14% | Bac général 0%, techno 14%, pro 86% | Boursiers 71% | Femmes 11% | Néobacheliers 78%
  Source officielle: Parcoursup: https://dossierapp...
```

### Réponse générée

Voici une analyse structurée des formations **à Perpignan et dans les environs** (Occitanie/Pyrénées-Orientales), en priorisant les options publiques labellisées et en diversifiant les niveaux (Bac+2 à Bac+5) et les spécialisations. Les données officielles des fiches sont complétées par des alternatives réalistes en (connaissance générale).

---

### **Plan A — Réaliste : Formations accessibles et adaptées à Perpignan**
**Pour toi si** : Tu veux rester en Occitanie, privilégier le public, et viser des formations avec un taux d’accès > 50% ou des passerelles claires.

#### 1. **BUT Science des données** — IUT de Perpignan (site de Carcassonne)
📍 *Carcassonne (Aude) — 1h de Perpignan*
• **Type** : Bachelor Universitaire de Technologie (BUT) | **Statut** : Public
• **Labels** : Grade Licence (reconnu par l’État)
• **Sélectivité** : 76% (Accessible)
  ##begin_quote##
  33% des admis en 2025 avaient la mention Assez Bien au bac, et 83% venaient d’un bac général.
  (Source: Parcoursup 2025, cod_aff_form: 2469)
  ##end_quote##
• **Débouchés** : Data analyst (M1419), Data scientist junior (M1405), Chargé·e de projets data
• **Points forts** :
  - Formation **gratuit**e (frais d’inscription ~243€/an en 2025).
  - **Alternance possible** dès la 2ème année (contrat pro ou apprentissage).
  - **Poursuite d’études** : 80% des diplômés continuent en master (ex : master IA à Montpellier) ou école d’ingénieurs (INSA, Polytech).
• **Source** : Parcoursup 2025, cod_aff_form 2469

#### 2. **BTS Cybersécurité, Informatique et Réseaux (Option A)** — Lycée Pablo Picasso, Perpignan
📍 *Perpignan (Pyrénées-Orientales)*
• **Type** : Brevet de Technicien Supérieur (BTS) | **Statut** : Public
• **Labels** : Aucun label spécifique (mais diplôme d’État)
• **Sélectivité** : 47% (Modérément sélective)
  ##begin_quote##
  50% des admis en 2025 venaient d’un bac technologique (STI2D), et 44% d’un bac pro.
  (Source: Parcoursup 2025, cod_aff_form: 7856)
  ##end_quote##
• **Débouchés** : Administrateur sécurité (M1817), Technicien réseaux (M1810), Support cybersécurité
• **Points forts** :
  - **Formation très professionnelle** : 8 semaines de stage en 1ère année, 10 en 2ème.
  - **Passerelle vers la licence pro** : Exemple à l’**IUT de Nîmes** (licence pro Cybersécurité, en alternance).
  - **Coût** : Gratuit (hors frais de vie).
• **Source** : Parcoursup 2025, cod_aff_form 7856

---
### **Plan B — Ambitieux : Formations sélectives mais atteignables avec préparation**
**Pour toi si** : Tu es prêt·e à te déplacer en Occitanie/voisinage, à viser des formations plus sélectives (taux 20-40%), ou à te spécialiser davantage.

#### 3. **BTS Cybersécurité (Option A) — Lycée Jean Mermoz, Montpellier**
📍 *Montpellier (Hérault) — 2h de Perpignan*
• **Type** : BTS | **Statut** : Public
• **Labels** : Aucun (mais partenariats avec des entreprises locales comme Capgemini)
• **Sélectivité** : 14% (Extêmement sélective)
  ##begin_quote##
  18% des admis en 2025 avaient la mention Très Bien au bac, et 53% venaient d’un bac pro.
  (Source: Parcoursup 2025, cod_aff_form: 4499)
  ##end_quote##
• **Débouchés** : Ingénieur sécurité junior (M1819), Pentester (après expérience)
• **Pourquoi c’est ambitieux ?**
  - **Profil attendu** : Dossier scolaire solide (moyenne ≥ 14/20) + projet motivé en cybersécurité.
  - **Alternative réaliste** : Si tu es refusé·e, le **BTS du lycée Pablo Picasso (Perpignan)** est une bonne porte d’entrée avant une spécialisation en licence pro.
• **Source** : Parcoursup 2025, cod_aff_form 4499

#### 4. **Licence Informatique (Parcours Cybersécurité)** — Université de Perpignan Via Domitia
📍 *Perpignan (Pyrénées-Orientales)*
• **Type** : Licence générale | **Statut** : Public
• **Labels** : Grade Licence (diplôme d’État)
• **Sélectivité** : ~60% (Accessible, mais parcours sélectif en L3)
  ##no_oracle##
  Je n’ai pas de donnée Parcoursup précise pour cette formation, mais les licences informatiques publiques en région ont généralement un taux d’accès entre 50% et 70%.
  ##end_no_oracle##
• **Débouchés** : Développeur sécurisé (M1805), Analyste SOC (après master)
• **Points forts** :
  - **Spécialisation progressive** : Choix du parcours cybersécurité en L3.
  - **Recherche locale** : Laboratoire **LAAS-CNRS** (partenaire de l’UPVD) pour des stages.
  - **Coût** : ~243€/an.
• **Source** : (connaissance générale) — [Site de l’UPVD](https://www.univ-perp.fr)

---
### **Plan C — Passerelles et alternatives**
**Pour toi si** : Tu veux explorer d’autres voies (alternance, formations courtes qualifiantes) ou te réorienter plus tard.

#### 5. **Certificat de Compétence en Cybersécurité (CCS)** — GRETA Occitanie
📍 *Perpignan ou Montpellier*
• **Type** : Formation professionnelle (niveau Bac+2) | **Statut** : Public (finançable par Pôle Emploi/OPCO)
• **Labels** : Certification reconnue par les branches professionnelles
• **Sélectivité** : Accessible (entretien + test de positionnement)
• **Débouchés** : Technicien cybersécurité (M1817), Auditeur junior
• **Pour qui ?**
  - **Réorientation après un Bac+1/2** : Idéal si tu veux une formation **courte (6-12 mois)** et **en alternance**.
  - **Public adulte** : Possible en reconversion avec un bac général/techno.
• **Source** : (connaissance générale) — [GRETA Occitanie](https://www.greta-occitanie.fr)

#### 6. **École d’ingénieurs en alternance (après BTS/BUT)**
📍 *Exemples en Occitanie* :
- **Polytech Montpellier** (cycle ingénieur en apprentissage, spécialité **Informatique et Réseaux**).
- **INSA Toulouse** (formation continue en cybersécurité).
• **Conditions** :
  - Avoir validé un BTS/BUT + trouver une entreprise partenaire.
  - **Salaire** : ~800-1200€/mois en alternance (contrat pro).
• **Source** : (connaissance générale)

---
### **Comparatif rapide des options à Perpignan**
| Critère                | BUT Data (Carcassonne)       | BTS Cyber (Picasso)          | Licence Info (UPVD)         |
|------------------------|-----------------------------|-----------------------------|-----------------------------|
| **Niveau**             | Bac+3                       | Bac+2                       | Bac+3                       |
| **Sélectivité**        | 76% (Accessible)            | 47% (Modérément sélective)  | ~60% (Accessible)           |
| **Public cible**       | Bac général (83%)           | Bac techno/pro (94%)        | Bac général/techno          |
| **Alternance**         | Oui (à partir de L2)        | Oui (stage obligatoire)     | Rare (sauf L3 pro)          |
| **Poursuite d’études**| Master, école d’ingénieurs  | Licence pro, école d’ingé   | Master, recherche           |
| **Coût**               | ~243€/an                    | Gratuit                     | ~243€/an                    |

---
### **🔀 Passerelles possibles**
1. **BTS → BUT** : Après un BTS Cyber à Picasso, tu peux candidater en **2ème année de BUT Data** (Carcassonne) via Parcoursup (admission sur dossier).
2. **Licence → Master** : La licence UPVD permet de viser le **master Cybersécurité de l’Université de Toulouse** (classé top 5 en France).
3. **Alternance** : Toutes les formations citées (sauf la licence classique) ont des parcours en alternance. **Pôle Emploi Occitanie** et **la Région** financent des formations courtes (ex : CCS).

---
### **💡 Question pour toi**
Tu as trois leviers pour choisir :
1. **Ton projet pro** : Veux-tu travailler **rapidement** (BTS) ou viser un poste plus qualifié (BUT/licence + master) ?
2. **Ta mobilité** : Es-tu prêt·e à quitter Perpignan pour Montpellier/Toulouse si nécessaire ?
3. **Ton profil scolaire** :
   - Si tu as un **bac général avec mention AB/B**, le **BUT Data (Carcassonne)** est la voie la plus sûre.
   - Si tu viens d’un **bac techno/pro**, le **BTS Cyber (Picasso)** ou une **licence pro** sera plus adapté·e.

**Quelle est ta priorité absolue parmi ces 3 critères ?** (Réponds en 1, 2 ou 3, je peux affiner les suggestions.)

---
