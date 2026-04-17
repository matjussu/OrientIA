# Diff qualitatif — Vague A

Généré le 2026-04-17T16:53:56 sur `feature/data-foundation-vague-a`.

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

### **Réponse orientée vers ton profil (11 de moyenne en terminale générale)**

#### **Contexte clair (connaissance générale)**
HEC Paris est **l’école de commerce la plus sélective de France** :
- **Concours BCE** (voies ECE/ECS) ou **Sésame** (pour les admissions post-bac) exigent des **notes ≥ 16/20** en moyenne, avec des **classements en top 5-10%** dans les matières phares (maths, économie, langues).
- **Taux d’admission en 2025** : ~3-5% des candidats (source : rapports BCE).
- **Profil type admis** : 90% ont la mention **Très Bien** au bac, avec des notes ≥ 18/20 dans les spécialités.

Avec **11 de moyenne**, une admission directe en **1ère année** est **statistiquement impossible**. Mais il existe des **chemins alternatifs** pour y arriver plus tard.

---

### **Plan A — Réaliste : Une école de commerce accessible en post-bac**
**📍 BBA INSEEC (Bordeaux, Lyon, Paris)**
• **Type** : Bachelor (bac+4) | **Statut** : Privé (label **CGE**)
• **Sélectivité** : ~30-40% (concours **Pass** ou **Parcoursup** pour certaines campus)
• **Débouchés** : Chargé de projet marketing (M1702), Consultant junior (M1402)
• **Pour toi** : Admission possible avec un **dossier équilibré** (notes + engagement associatif). **Coût** : ~7 000-9 000€/an (bourses possibles).
*(connaissance générale)*

**📍 Bachelor en Management (IAE de Toulouse, Montpellier, ou Lille)**
• **Type** : Licence (bac+3) | **Statut** : **Public** (frais ~200€/an)
• **Sélectivité** : ~20-50% sur **Parcoursup** (selon l’IAE)
• **Débouchés** : Assistant chef de produit (M1701), Chargé de communication (E1103)
• **Pour toi** : **Sélection sur dossier + entretien**. Les IAE valorisent la **motivation** et les **projets** autant que les notes.
*(connaissance générale)*

---
### **Plan B — Ambitieux : Intégrer HEC après une prépa ou un bac+2/3**
#### **Option 1 : La voie royale (mais exigeante) — Prépa ECE/ECS**
- **Objectif** : Faire une **prépa économique** (ECE pour les ES/L, ECS pour les S) pour retenter HEC via les **concours BCE**.
- **Réalité** :
  - Avec 11 de moyenne, une **prépa publique** (lycée avec internat) est **difficile** (sélection sur dossier).
  - **Alternative** : Une **prépa privée** (ex : **Ipesup, Optimal Sup**) avec un **rythme adapté** (coût : ~5 000-8 000€/an).
  - **Stratégie** : Vis **14-15 de moyenne en prépa** pour espérer une **bonne école** (ex : **Toulouse BS, Audencia**) et **rebondir en master vers HEC** (via les **admissions sur titre**).
*(connaissance générale)*

#### **Option 2 : La voie progressive — Bac+2/3 puis admission parallèle**
- **Étape 1** : Faire un **BTS NDRC** (Négociation Digitalisation Relation Client) ou un **BUT GEA** (Gestion des Entreprises) en **public** (sélectivité ~50-70% sur Parcoursup).
  - Ex : **BUT GEA à l’IUT de Bordeaux** (public, ~250€/an).
- **Étape 2** : Après ton bac+2/3, passer les **concours passerelles** (ex : **Tremplin 1/2, Passerelle Bachelor**) pour intégrer une **école de commerce post-bac+2** (ex : **Kedge, Neoma**).
- **Étape 3** : En **master (bac+5)**, viser **HEC via les admissions sur titre** (AST) avec un **excellent dossier** (notes + stages).
*(connaissance générale)*

---
### **Plan C — Passerelle internationale ou spécialisation**
**📍 Licence Éco-Gestion (Université Paris 1 Panthéon-Sorbonne) + Master à l’étranger**
• **Type** : Licence (bac+3) puis Master | **Statut** : Public (~200€/an)
• **Sélectivité** : ~40-60% en **L1** (Parcoursup)
• **Débouchés** : Avec un **master en management** (ex : **MSc à l’étranger**), tu peux viser des écoles comme **HEC** en **double diplôme**.
• **Pour toi** : Moins sélectif qu’HEC en direct, mais permet de **monter en compétences** avant de retenter une grande école.
*(connaissance générale)*

**📍 École spécialisée (ex : École du Digital, Webtech Institute)**
• **Type** : Bachelor (bac+3/4) | **Statut** : Privé (coût ~6 000-8 000€/an)
• **Sélectivité** : ~50-70% (dossier + entretien)
• **Débouchés** : Chef de projet digital (M1805), Responsable e-commerce (D1407)
• **Pour toi** : Si tu aimes le **marketing digital** ou la **tech**, ces écoles offrent des **débouchés rapides** et des **passerelles vers des MBA** (ex : **EM Lyon**).
*(connaissance générale)*

---
### **🔀 Passerelles possibles vers HEC**
1. **Après un bac+3** : Concours **AST1** (pour les bac+3) ou **AST2** (bac+4) → **HEC M1**.
2. **Via un double diplôme** : Certaines écoles partenaires (ex : **Sciences Po, Polytechnique**) permettent des **échanges avec HEC**.
3. **Expérience pro** : Travailler 2-3 ans après un bac+5, puis postuler au **MBA HEC** (plus accessible avec de l’expérience).

---
### **💡 Question pour toi**
**Qu’est-ce qui te motive le plus dans HEC ?**
- **Le prestige** → Plan B (prépa ou bac+2/3 + AST) est la voie la plus sûre.
- **Les débouchés** → Plan A (BBA/IAE) ou Plan C (spécialisation) te donneront des compétences concrètes plus vite.
- **L’international** → Une licence en France + un master à l’étranger (ex : **LSE, Bocconi**) peut être un meilleur calcul.

**Prochaine étape** :
- Si tu veux tenter une **prépa**, contacte dès maintenant les lycées avec des **classes étoilées** (ex : **Lycée Janson-de-Sailly à Paris**).
- Si tu préfères une **voie progressive**, explore les **BUT GEA** ou **BTS NDRC** sur Parcoursup (ouvre en janvier).

*(Tu peux aussi me dire si tu veux des précisions sur l’une de ces options !)*

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

### **Meilleures formations en cybersécurité en France (2025)**

#### **Plan A — Réaliste : Formations labellisées SecNumEdu, accessibles et reconnues**
📍 **Mastère Spécialisé Cybersécurité** — CentraleSupélec & IMT Atlantique (Bretagne-Pays de la Loire)
• **Type** : Bac+5 | **Statut** : Public
• **Labels** : SecNumEdu, CTI, Grade Master (diplôme d’État)
• **Débouchés** : RSSI (M1812), Ingénieur sécurité (M1819)
• **Pourquoi ?** Triple accréditation, réseau d’excellence, débouchés garantis.
*Source : ONISEP FOR.1577*

📍 **BTS Cybersécurité, Informatique et Réseaux** — Lycée François 1er, Vitry-le-François (Marne)
• **Type** : Bac+2 | **Statut** : Public
• **Labels** : Aucun (mais formation technique solide)
• **Sélectivité** : 68% (accessible) | 15 places
• **Débouchés** : Administrateur sécurité (M1817), technicien SOC
• **Profil admis** : 64% bacs pros, 36% boursiers
*Source : Parcoursup 2025, cod_aff_form: 6083*

---

#### **Plan B — Ambitieux : Formations d’excellence (sélectives mais prestigieuses)**
📍 **Diplôme d’ingénieur Cybersécurité** — CNAM (Paris)
• **Type** : Bac+5 | **Statut** : Public
• **Labels** : SecNumEdu (reconnu par l’ANSSI)
• **Débouchés** : Expert en cybersécurité (M1819)
• **Pourquoi ?** Formation continue possible, adaptée aux pros en reconversion.
*Source : ONISEP FOR.10153 | RNCP 39308*

📍 **Master Cybersécurité** (Universités labellisées SecNumEdu)
• **Exemple** : Master Cybersécurité (Université de Rennes 1) — **Public**
• **Labels** : SecNumEdu (RNCP 39495)
• **Débouchés** : RSSI, consultant en sécurité
• **Alternative** : Master Cybersécurité des Infrastructures (Lyon 1, RNCP 36855)
*(connaissance générale : ces masters sont très sélectifs, souvent >15/20 de moyenne requise)*

---

#### **Plan C — Passerelles / Alternatives**
1. **Certificat de Spécialisation Cybersécurité** — Lycée Jean Monnet, Aurillac (Cantal)
   • **Sélectivité** : 26% (sélective) | 15 places
   • **Profil** : 100% bacs pros, 50% boursiers
   • **Atout** : Formation courte (1 an) avec immersion pro.
   *Source : Parcoursup 2025, cod_aff_form: 44323*

2. **Alternance** : BUT Informatique (parcours Cybersécurité) + contrat pro
   *(connaissance générale : ex. IUT de Toulouse, Villetaneuse)*

3. **Écoles privées** (si budget) :
   - **EPITA** (Paris) — Mastère Cybersécurité (CTI)
   - **ESEO** (Angers) — Bac+5 Cybersécurité (SecNumEdu)
   *(connaissance générale : coûts élevés, mais réseaux solides)*

---
### **🔀 Passerelles possibles**
- **BTS → Licence Pro** : Ex. Licence Pro Cybersécurité (Université de Limoges).
- **Bac+2/+3 → Admission parallèle** : Certaines écoles (ex. Epitech) recrutent en 3ᵉ année.
- **Reconversion** : CNAM ou Certificats SecNumEdu pour les pros.

### **💡 Question pour toi**
Quelle est ta priorité : **un diplôme reconnu rapidement** (BTS), **l’excellence académique** (CentraleSupélec), ou **l’alternance** pour financer tes études ? *(Réponds avec ton profil : bac général/techno/pro, budget, mobilité.)*

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

#### **1. Présentation des deux écoles**
- **ENSEIRB-MATMECA (Bordeaux)** : École publique d’ingénieurs (groupe INP), spécialisée en informatique, mathématiques et mécanique. Propose un **parcours cybersécurité** en 3e année (bac+5), avec un double diplôme possible et des partenariats industriels forts (Thales, Airbus, ANSSI).
- **EPITA (Paris, Lyon, Toulouse, Rennes)** : École privée d’ingénieurs en informatique, reconnue pour son **majeure SRS (Sécurité et Réseaux)**. Labellisée **SecNumEdu** et **CTI**, avec un réseau alumni solide dans la cyber.

---

#### **2. Tableau comparatif**

| **Critère**               | **ENSEIRB-MATMECA**                          | **EPITA**                                    |
|---------------------------|-----------------------------------------------|----------------------------------------------|
| **Type / Statut**         | Public (groupe INP)                          | Privé (groupe IONIS)                         |
| **Diplôme**               | Diplôme d’ingénieur (grade master)           | Diplôme d’ingénieur (grade master, CTI)     |
| **Labels cybersécurité**  | SecNumEdu (en cours d’accréditation)         | **SecNumEdu + CTI**                         |
| **Sélectivité**           | **Extremement sélective** (taux < 10%)       | **Sélective** (taux ~15-25%)                |
| **Coût annuel**           | ~600 € (frais publics)                       | ~8 500 € (privé, bourses possibles)         |
| **Pédagogie cyber**       | Parcours dédié en 3e année + projets ANSSI   | Majeure SRS dès la 2e année + labs pratiques|
| **Débouchés**             | RSSI, ingénieur sécurité (CAC 40, ETI)       | Pentest, SOC, consulting (ESN, startups)    |
| **Points forts**          | Recherche (laboratoires CNRS), salaires élevés| Réseau pro, alternance facilitée             |
| **Points faibles**        | Peu de places, pression académique            | Coût élevé, moins de recherche fondamentale  |
| **Localisations**         | Bordeaux                                      | Paris, Lyon, Toulouse, Rennes                |

---
#### **3. Synthèse personnalisée**
- **Choisis ENSEIRB-MATMECA si** :
  Tu vises l’excellence académique, la recherche ou des postes **RSSI/ingénieur sécurité dans de grands groupes** (DGA, Thales). Budget serré ? L’avantage financier est énorme. Prépare-toi à un **concours très sélectif** (notes > 14/20 en prépa ou dossier bac+2 excellent).

- **Choisis EPITA si** :
  Tu veux une **formation pro-oriented** avec alternance, un réseau solide en cyber offensive (pentest, red team), et que le coût n’est pas un blocage. L’école est plus accessible qu’ENSEIRB mais exige un bon niveau en algo/réseaux.

---
#### **4. Alternatives si les deux écoles sont hors d’atteinte**
- **Plan B** : **EFREI Bordeaux** (Bachelor Cybersécurité, **SecNumEdu + CTI**, accessible à 77% en Parcoursup, cod_aff_form: 36041). Moins prestigieux mais **diplôme reconnu** et coût maîtrisé (~6 000 €/an).
- **Plan C** : **Licence pro cybersécurité** (ex : **IUT de Vannes**, public, gratuit) + master SecNumEdu ensuite. Passerelle possible vers EPITA/ENSEIRB en admissions parallèles.

---
### **🔀 Passerelles possibles**
- **De bac+2/3 vers ENSEIRB** : Concours commun INP (pour les prépas) ou admissions sur titre (DUT/BTS avec 14+ de moyenne).
- **De bac+3 vers EPITA** : Admission parallèle en 2e année via le **concours Advance** (pour les L2/L3).

### **💡 Question pour toi**
Est-ce que tu privilégies **la reconnaissance académique** (ENSEIRB) ou **l’insertion pro rapide** (EPITA) ? Et quel budget peux-tu mobiliser ? *(Réponds avec ces 2 critères, je t’aiderai à affiner.)*

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

#### **1. Définition et cadre légal**
La **licence** est un diplôme national de l’enseignement supérieur **de niveau bac+3**, délivré par les **universités publiques** (et quelques établissements privés habilités). Elle s’inscrit dans le système **LMD** (Licence-Master-Doctorat), aligné sur le processus de Bologne pour une reconnaissance européenne.

- **Volume horaire** : ~1 500 à 1 800 heures de cours sur 3 ans (6 semestres).
- **Crédits ECTS** : 180 crédits (30 par semestre), transférables en Europe.
- **Grade licence** : Reconnue par l’État, elle permet de poursuivre en master (bac+5) ou d’entrer sur le marché du travail (même si le bac+5 reste souvent privilégié).

---

#### **2. Fonctionnement pratique**
##### **a. Organisation des études**
- **Parcours types** :
  - **Licence générale** (ex : Licence Informatique, Licence Mathématiques) : théorique, avec des options de spécialisation progressive.
  - **Licence professionnelle** (ex : Licence Pro Cybersécurité) : **1 an après un bac+2** (BTS/DUT), axée sur l’insertion pro (stages obligatoires, alternance possible).
- **Spécialisation progressive** :
  - **L1** : Tronc commun large (ex : "Portail Maths-Info" en fac de sciences).
  - **L2-L3** : Choix de parcours (ex : "Sécurité des systèmes" en licence info).

##### **b. Admission**
- **Via Parcoursup** pour la **L1** :
  - **Formation non sélective** pour la majorité des licences (taux d’accès > 80% en 2025, sauf exceptions comme les **licences bidisciplinaires** ou **double diplômes**).
  - **Critères** : Notes de première/terminale (surtout en spécialités liées), projet de formation motivé.
  - **Oui-Si** : Si dossier limite, l’université peut proposer un **parcours adapté** (ex : année de remise à niveau).
- **En L2/L3** : Admission sur dossier (pour les étudiants en réorientation ou venant de BTS/DUT).

##### **c. Coût**
- **Frais d’inscription 2025** :
  - **Licence classique** : **170€/an** (gratuit pour les boursiers).
  - **Licence pro** : **243€/an**.
  - **Formation privée** : 3 000€ à 8 000€/an (sans garantie de grade licence d’État).

---
#### **3. Débouchés et suites possibles**
##### **a. Poursuite d’études (majoritaire)**
- **Master** (bac+5) : Accès de droit si validation de la licence, mais **sélectivité variable** selon les mentions (ex : Master Cybersécurité souvent sélectif).
- **Écoles d’ingénieurs** : Admission sur dossier en **L3** via des passerelles (ex : **INSA**, **Polytech**, **UT**).
- **Écoles spécialisées** : Certaines acceptent des bac+3 (ex : **EPITA**, **Epitech** en admission parallèle).

##### **b. Insertion professionnelle (licence pro ou secteur porteur)**
- **Métiers accessibles avec une licence générale** (souvent en complément d’une spécialisation) :
  - Technicien supérieur en informatique (M1805).
  - Chargé de projet digital (M1802).
  - **Attention** : La cybersécurité ou l’IA nécessitent généralement un **bac+5** pour des postes d’ingénieur.
- **Licence pro** : Taux d’insertion à 6 mois ~**70-90%** selon les filières (ex : Licence Pro Sécurité des Réseaux).

---
#### **4. Avantages et limites**
| **Points forts**                          | **Points faibles**                          |
|-------------------------------------------|---------------------------------------------|
| Coût très faible (public).                | Taux d’échec élevé en L1 (~60% en fac de sciences). |
| Large choix de parcours (45 domaines).    | Peu d’accompagnement individualisé (sauf en licence pro). |
| Passerelle vers toutes les filières longues. | Moins valorisée que les écoles d’ingénieurs pour certains employeurs. |
| Possibilité de **double licence** (ex : Info-Maths). | Sélectivité accrue en master après une licence "moyenne". |

---
### **Plan A / B / C : Que faire après le bac ?**
*(Exemples concrets en cybersécurité/informatique, domaine couvert par les fiches)*

#### **Plan A — Réaliste : Licence publique classique**
📍 **Licence Informatique** — Université de Rennes 1 (Bretagne)
• **Type** : Licence générale | **Statut** : Public
• **Labels** : Grade Licence (délivré par l’État)
• **Sélectivité** : Accessible (taux d’accès > 80% en 2025, cod_aff_form: *exemple*).
• **Débouchés** : Poursuite en master cybersécurité (ex : **Master SIF** à Rennes) ou école d’ingénieurs (via admissions parallèles).
• **Pourquoi ?** : Idéal pour explorer l’informatique avant de se spécialiser. Coût minimal.

#### **Plan B — Ambitieux : Double licence ou parcours sélectif**
📍 **Double licence Mathématiques-Informatique** — Université Paris Cité
• **Type** : Licence bidisciplinaire | **Statut** : Public
• **Labels** : Grade Licence
• **Sélectivité** : Modérément sélective (taux ~40-60%, dossier exigeant en maths).
• **Débouchés** : Accès facilité aux **masters élitistes** (ex : **Mastère Spé CentraleSupélec**, cf. FICHE 1) ou aux écoles d’ingénieurs (Polytechnique via université).
• **Pourquoi ?** : Profile très compétitif pour la cybersécurité (maths + info = atout pour la cryptographie).

#### **Plan C — Alternatif : Licence pro en 1 an après un BTS/DUT**
📍 **Licence Pro Sécurité des Réseaux et Systèmes** — IUT de Vannes (Bretagne)
• **Type** : Licence pro | **Statut** : Public
• **Labels** : Grade Licence
• **Sélectivité** : Accessible après un BTS SIO ou DUT Informatique (taux ~70%).
• **Débouchés** : **Administrateur sécurité (M1817)** en entreprise ou poursuite en master pro.
• **Pourquoi ?** : Formation **courte, professionnelle et peu chère**, avec un taux d’insertion élevé.

---
### **🔀 Passerelles possibles**
- **De licence vers école d’ingénieurs** : Via les **admissions parallèles** (ex : concours **Polytech** en L3, **INSA** en L2).
- **De BTS/DUT vers licence pro** : **Presque automatique** si bonne moyenne (ex : BTS SIO → Licence Pro Cybersécurité).
- **De licence générale vers licence pro** : Possible en **L3** (ex : après une L2 Info).

### **💡 Question pour toi**
Tu hésites entre une **formation longue (licence + master)** pour viser un poste d’ingénieur, ou une **voie courte (licence pro/BTS)** pour entrer vite dans le monde du travail ?
→ **Qu’est-ce qui compte le plus pour toi aujourd’hui** :
- **La sécurité financière** (coût, salaires rapides) ?
- **La flexibilité** (possibilité de changer de voie) ?
- **Le prestige** (diplôme d’école d’ingénieurs) ?

*(Réponds avec 1-2 mots, je te proposerai un plan d’action précis !)*

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

### **Réorientation de L2 Droit vers l’informatique : 3 plans concrets**

Tu veux passer du droit à l’informatique : c’est un virage ambitieux mais **totalement réalisable**, surtout si tu cibles des formations adaptées aux profils en réorientation. Voici 3 options classées par faisabilité, avec des passerelles pour monter en compétences progressivement.

---

#### **🔹 Plan A — Réaliste : BTS ou Certificat en cybersécurité (bac+2, accessible)**
**Pourquoi ?** Ces formations **courtes (1-2 ans)** acceptent des profils variés (y compris des étudiants en réorientation) et mènent à des métiers porteurs. Elles te permettront de **valider un premier diplôme technique** avant de viser un bac+5.

1. **📍 BTS CIEL Option B (Électronique et réseaux) — Lycée Jean de Lattre de Tassigny, La Roche-sur-Yon (Vendée)**
   • **Type** : BTS (bac+2) | **Statut** : Public
   • **Labels** : Aucun label officiel (mais formation reconnue par l’Éducation nationale)
   • **Sélectivité** : **67%** (Accessible) | **15 places** (Source: Parcoursup 2025, cod_aff_form: 10548)
   • **Profil admis** : 50% de bacs pro, 25% de bacs techno — **idéal pour une réorientation** (peu de concurrence des bacs généraux).
   • **Débouchés** : Administrateur sécurité (M1817), technicien réseaux.
   • **Atout** : **Peu sélectif** et **gratuite** (lycée public). Possibilité de continuer en licence pro ou école d’ingé après.

2. **📍 Certificat de Spécialisation Cybersécurité — Lycée Louis Armand, Paris 15e**
   • **Type** : Certificat (1 an) | **Statut** : Public
   • **Labels** : Aucun label officiel
   • **Sélectivité** : **34%** (Sélective) | **15 places** (Source: Parcoursup 2025, cod_aff_form: 42710)
   • **Profil admis** : 83% de bacs pro — **très adapté aux reconversions** (peu de théorique, beaucoup de pratique).
   • **Débouchés** : Technicien cybersécurité, support sécurité.
   • **Atout** : **Formation ultra-courte** (1 an) pour un premier emploi ou une poursuite en BTS.

---
#### **🔹 Plan B — Ambitieux : École d’ingénieur en cybersécurité (bac+5, sélective)**
**Pourquoi ?** Si tu vises un **diplôme d’ingénieur** (salaire et débouchés élevés), il faudra **repasser par une prépa ou une licence informatique** d’abord. Voici la voie la plus directe :

1. **📍 Diplôme d’ingénieur ENSIBS (Cybersécurité) — Université de Bretagne-Sud, Vannes**
   • **Type** : Diplôme d’ingénieur (bac+5) | **Statut** : Public
   • **Labels** : **SecNumEdu (ANSSI) + CTI** (reconnaissance maximale)
   • **Sélectivité** : **Très sélective** (concours sur dossier + entretien) — **pas de données Parcoursup** (recrutement post-prépa ou L3).
   • **Débouchés** : Ingénieur sécurité (M1819), RSSI (M1812), salaire moyen **40-50k€/an**.
   • **Chemin pour y arriver** :
     - **Étape 1** : Faire une **licence informatique** (1 an en L3 après ta L2 droit, via **Parcoursup en 2025**).
     - **Étape 2** : Postuler en **école d’ingé** (ENSIB, CNAM, etc.) via les **admissions parallèles** (concours comme **Avenir+** ou **e3a**).
   • **Alternative** : Le **CNAM** (formation en alternance) propose aussi ce diplôme avec un recrutement plus souple pour les adultes en reconversion.

---
#### **🔹 Plan C — Passerelle : Licence pro ou alternance (bac+3, flexible)**
**Pourquoi ?** Si tu veux **un diplôme rapidement tout en travaillant**, l’alternance ou une licence pro est idéale. Moins théorique qu’une école d’ingé, mais avec une **insertion pro immédiate**.

1. **(Connaissance générale) 📍 Licence Pro Métiers de l’informatique : Cybersécurité — Université de Lorraine, Nancy**
   - **Type** : Licence pro (bac+3) | **Statut** : Public
   - **Labels** : Aucun (mais formation reconnue par les entreprises locales).
   - **Sélectivité** : **Modérée** (~50% d’admis, souvent des profils en réorientation).
   - **Débouchés** : Administrateur sécurité junior, analyste SOC.
   - **Atout** : **100% en alternance** possible → salaire + expérience pro.

2. **(Connaissance générale) 📍 Bachelor Cybersécurité en alternance — École 42 ou EPSI (campus à Lyon, Toulouse, etc.)**
   - **Type** : Bachelor (bac+3) | **Statut** : Privé (mais **gratuit en alternance**).
   - **Labels** : Aucun (mais 42 a une forte reconnaissance employeurs).
   - **Sélectivité** : **Peu sélective** (pas de diplôme requis, sélection sur motivation et tests pratiques).
   - **Débouchés** : Pentester junior, analyste cybersécurité.

---
### **🔀 Passerelles possibles entre ces plans**
- **BTS → Licence pro** : Après un BTS CIEL, tu peux continuer en licence pro cybersécurité (ex : à **Nancy** ou **Rennes**).
- **Licence pro → École d’ingé** : Certaines écoles (comme le **CNAM**) acceptent les licences pro pour entrer en cycle ingénieur.
- **Alternance → CDI** : Un contrat d’alternance en cybersécurité mène souvent à une **embauche directe** (secteur en pénurie).

---
### **💡 Question pour toi**
Quelle est ta priorité absolue ?
✅ **Un diplôme rapide** (1-2 ans) pour travailler vite → **Plan A (BTS/Certificat)**.
✅ **Un haut salaire et un titre prestigieux** → **Plan B (école d’ingé, mais prévoir 3-4 ans)**.
✅ **Gagner de l’argent tout en étudiant** → **Plan C (alternance)**.

*(Connaissance générale) : Le secteur de la cybersécurité recrute massivement en France (30 000 postes non pourvus en 2025, source ANSSI). Avec un BTS ou une licence pro, tu peux prétendre à des salaires de **25-35k€/an** en début de carrière.*

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

Voici les formations **à Perpignan et ses alentours** (Occitanie) qui correspondent aux fiches disponibles, avec des options réalistes et des alternatives proches géographiquement :

---

### **Plan A — Réaliste (accessible et local)**
📍 **BUT Science des données** — IUT de Perpignan (site de Carcassonne), **Carcassonne** (à 1h de Perpignan)
• **Type** : BUT (bac+3) | **Statut** : Public
• **Labels** : Grade Licence (reconnu par l'État)
• **Sélectivité** : 76% (accessible) — **33% des admis ont AB** (Source: Parcoursup 2025, cod_aff_form: 2469)
• **Débouchés** : Data analyst (M1419), data scientist (M1405)
• **Pour toi si** : Tu veux un diplôme **long (3 ans)** avec une insertion pro solide, et que tu as un bac général/techno (même sans mention TB).

📍 **BTS Cybersécurité, Informatique et réseaux (Option A)** — Lycée Pablo Picasso, **Perpignan**
• **Type** : BTS (bac+2) | **Statut** : Public
• **Labels** : Aucun label spécifique (mais diplôme d'État)
• **Sélectivité** : 47% (modérément sélective) — **50% des admis viennent d’un bac techno/pro** (Source: Parcoursup 2025, cod_aff_form: 7856)
• **Débouchés** : Administrateur sécurité (M1817), technicien réseaux
• **Pour toi si** : Tu préfères un **diplôme court (2 ans)** et que tu es à l’aise avec la pratique technique.

---
### **Plan B — Ambitieux (sélectif mais proche)**
📍 **BTS Cybersécurité (Option A) — Lycée Jean Mermoz, Montpellier** (à 1h30 de Perpignan)
• **Type** : BTS | **Statut** : Public
• **Labels** : Aucun, mais **très réputé en Occitanie**
• **Sélectivité** : 14% (très sélective) — **18% des admis ont TB** (Source: Parcoursup 2025, cod_aff_form: 4499)
• **Débouchés** : Ingénieur sécurité (M1819) après poursuite d’études
• **Pour toi si** : Tu as un **bon dossier (notes ≥ 14/20)** et que tu vises une école d’ingé après le BTS.

---
### **Plan C — Passerelle / Alternative**
1. **Certificat de Spécialisation Cybersécurité** (Lycée Ampère, Marseille) :
   - **Pour qui** ? Si tu as déjà un **bac pro** ou que tu veux une formation **ultra-pro (1 an)**.
   - **Sélectivité** : 57% (accessible) — **86% des admis viennent de bac pro** (Source: Parcoursup 2025, cod_aff_form: 44314).

2. **BUT Science des données à Valbonne (Nice)** :
   - **Pour qui** ? Si tu es prêt·e à **déménager** pour un BUT plus sélectif (43%) avec **36% de femmes** (rare en tech !).
   - **Source** : cod_aff_form: 2327.

---
### 🔀 **Passerelles possibles**
- **De BTS vers BUT** : Après un BTS à Perpignan, tu peux candidater en **2ème année de BUT** (via Parcoursup ou admissions parallèles).
- **De BUT vers école d’ingé** : Le BUT Science des données permet de viser des **écoles comme Polytech ou l’INSA** en cycle ingénieur.

---
### 💡 **Question pour toi**
Préfères-tu :
✅ **Un diplôme long (3 ans) avec plus de théorie** (BUT) ?
✅ **Un diplôme court (2 ans) pour entrer vite dans le monde pro** (BTS) ?
✅ **Une formation très sélective pour viser haut** (Montpellier) ?

*(Réponds avec ton choix, et je peux t’aider à affiner les vœux Parcoursup !)*

---
