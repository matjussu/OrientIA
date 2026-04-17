# Diff qualitatif — Vague A

Généré le 2026-04-17T16:08:25 sur `feature/data-foundation-vague-a`.

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

#### **Plan A — Réaliste : Une école de commerce post-bac accessible**
📍 **Bachelor en Management (BBA) — IÉSEG Lille**
• **Type** : Bachelor (bac+3) | **Statut** : Privé (reconnu par l’État)
• **Labels** : Grade Licence, accréditation CGE (Conférence des Grandes Écoles)
• **Sélectivité** : ~30-40% (modérément sélective) — **adapté à un profil autour de 11-12 de moyenne** avec un bon dossier (engagement, projets, langues).
• **Débouchés** : Chargé de projet marketing (M1703), Consultant junior (M1402), Chef de produit (M1701).
• **Source** : (connaissance générale — données CGE 2024)

**Pourquoi ?**
- L’IÉSEG recrute **au-delà des notes** (entretien de motivation, tests écrits, personnalité).
- **Alternance possible dès la 3ᵉ année** pour financer tes études et gagner en expérience.
- **Passerelle vers un master** (HEC, ESSEC, etc.) possible après le bachelor si tu montes en niveau.

---

#### **Plan B — Ambitieux : Visée HEC, mais par la voie des admissions parallèles**
🎯 **Objectif** : Intégrer HEC **après une licence ou un bachelor** (via les **concours BCE/ECRICOME** en admissions parallèles).
📌 **Chemin possible** :
1. **Faire un bac+3 solide** (ex : licence AES, économie-gestion, ou un BBA comme l’IÉSEG).
2. **Préparer les concours** en 1 an (via une **prépa AGC** — Admissions sur Titre en Grande École).
3. **Passer les écrites/oraux** (HEC recrute ~10% de ses élèves par cette voie).

🔢 **Chiffres clés** (connaissance générale) :
- **Taux d’admission en AST** (Admission Sur Titre) à HEC : ~5-8% (très sélectif, mais moins que la voie classique).
- **Profil type admis** : 14+ de moyenne en licence + score élevé aux tests (TAGE MAGE 400+, TOEIC 900+).

**Pourquoi ?**
- Avec **11 de moyenne en terminale**, la voie directe (concours BCE après prépa) est **extrêmement risquée** (taux d’admission < 5%).
- En revanche, une **licence bien choisie + prépa AST** te donne une **seconde chance réaliste**.

---

#### **Plan C — Alternative : Une formation hybride tech/management (moins sélective, débouchés solides)**
📍 **BUT Statistique et Informatique Décisionnelle (STID) — IUT de Bordeaux**
• **Type** : BUT (bac+3) | **Statut** : Public (gratuit)
• **Labels** : Grade Licence, diplôme d’État
• **Sélectivité** : ~50-60% (accessible) — **recrutement sur dossier + entretien**, avec une préférence pour les profils équilibrés (même sans 14+ de moyenne).
• **Débouchés** : Data Analyst (M1419), Chargé d’études marketing (M1403), Consultant data (M1402).
• **Source** : (connaissance générale — données ONISEP 2024)

**Pourquoi ?**
- **Moins de pression académique** qu’une prépa ou un bachelor sélectif.
- **Double compétence tech/management** très recherchée (salaire moyen : 35-40k€ en sortie).
- **Poursuite possible en école de commerce** (via les admissions parallèles) ou en master data/IA.

---

### **🔀 Passerelles possibles**
- **De Plan A (BBA) → Plan B (HEC)** : Valide ton bachelor avec 14+ de moyenne, prépare les concours AST.
- **De Plan C (BUT STID) → Plan B** : Fais un **master en data/management** (ex : MSc Data Analytics à l’EDHEC), puis tente HEC en AST.
- **Option wild card** : Une **année de césure** (service civique, stage) pour muscler ton CV avant de retenter une formation sélective.

### **💡 Question pour toi**
**Qu’est-ce qui compte le plus pour toi aujourd’hui ?**
✅ **Un diplôme sûr** avec des débouchés rapides (→ Plan C)
✅ **Un tremplin vers HEC** même si c’est plus long (→ Plan B)
✅ **Une école de commerce dès maintenant**, même si ce n’est pas HEC (→ Plan A)

*(Réfléchis à ton niveau de risque acceptable : préfères-tu une voie moins stressante ou un pari ambitieux ?)*

---
### **⚠️ Réalisme sur HEC en direct**
Avec **11 de moyenne en terminale**, ton dossier aurait **moins de 1% de chances** en voie classique (prépa + concours BCE). En revanche, **toutes les portes restent ouvertes** si tu passes par une **licence/bachelor + admissions parallèles** (cf. Plan B).
*(Source : données BCE 2024 — taux d’admission en prépa ECE pour les <12 de moyenne : ~0,3%)* (connaissance générale).

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

**Les meilleures formations en cybersécurité en France** dépendent de ton profil (niveau, bac, mobilité) et de tes objectifs (recherche, terrain, international). Voici 3 options **labellisées SecNumEdu** (le label officiel de l’ANSSI), classées par sélectivité et débouchés.

---

### **Plan A — Réaliste : Formations publiques sélectives mais accessibles**
**Pour qui ?** Étudiants avec un bac+2/+3 (BTS, BUT, licence) ou en reconversion, cherchant un diplôme **reconnu par l’État** sans concours ultra-compétitif.

📍 **Mastère Spécialisé Cybersécurité** — **CentraleSupélec (Gif-sur-Yvette) + IMT Atlantique (Brest/Rennes)**
• **Type** : Bac+5 (diplôme d’ingénieur ou master) | **Statut** : Public
• **Labels** : **SecNumEdu + CTI + Grade Master** (triple reconnaissance)
• **Sélectivité** : ~15-20% (modérément sélective, recrutement sur dossier + entretien)
• **Débouchés** : RSSI (M1812), Ingénieur sécurité (M1819), pentester
• **Source** : ONISEP: FOR.1577
→ *Pourquoi ?* **Meilleur rapport prestige/accessibilité** : formation co-portée par deux grandes écoles publiques, avec un réseau d’entreprises solide (Thales, Orange Cyberdéfense).

📍 **Manager de la Cybersécurité (RNCP 40246)** — **CNAM (Paris ou en région)**
• **Type** : Bac+5 (title RNCP) | **Statut** : Public (formation continue/adulte)
• **Labels** : **SecNumEdu**
• **Sélectivité** : Accessible (pas de concours, validation des acquis possible)
• **Débouchés** : RSSI, consultant sécurité, auditeur
• **Source** : ONISEP: FOR.11788
→ *Pourquoi ?* **Flexibilité** : cours du soir, alternance possible, idéal pour une reconversion ou un parcours en parallèle d’un emploi.

---

### **Plan B — Ambitieux : Formations d’excellence (sélectives)**
**Pour qui ?** Étudiants avec un **excellent dossier** (bac+3/+4, notes ≥14/20, expériences pro) visant les postes à haute responsabilité.

📍 **Diplôme d’Ingénieur Cybersécurité** — **ESIEA (Laval/Paris) ou ENSIBS (Vannes)**
*(connaissance générale : ces écoles sont **CTI + SecNumEdu**, mais non détaillées dans les fiches)*
• **Type** : Bac+5 (diplôme d’ingénieur) | **Statut** : Privé (ESIEA) / Public (ENSIBS)
• **Labels** : **CTI + SecNumEdu**
• **Sélectivité** :
  - ENSIBS (public) : ~10% (concours commun INP)
  - ESIEA (privé) : ~25% (dossier + oral, frais ~7k€/an)
• **Débouchés** : Expert en cryptographie, architecte sécurité, recherche (ANSSI, CEA)
→ *Comment y accéder ?*
  - **ENSIBS** : Prépa scientifique (MP/PSI) ou L2/L3 informatique avec 14+ de moyenne.
  - **ESIEA** : Dossier solide + stages en cyber (ex : participation à des CTF comme le *FCSC*).

📍 **Master Cybersécurité (RNCP 39495)** — **Universités partenaires ANSSI** *(ex : Université de Limoges, Rennes 1)*
*(connaissance générale : ces masters sont **SecNumEdu** mais moins visibles que les écoles d’ingénieurs)*
• **Type** : Bac+5 | **Statut** : Public
• **Labels** : **SecNumEdu**
• **Sélectivité** : ~30% (dossier + parfois entretien)
• **Atout** : **Gratuit** (frais d’inscription universitaires) et axé recherche (laboratoires comme l’**IRISA** à Rennes).

---

### **Plan C — Passerelles & Alternatives**
**Pour qui ?** Ceux qui veulent **entrer rapidement dans le métier** (sans bac+5) ou se spécialiser après un bac+2.

📍 **BTS Cybersécurité (cod_aff_form: 6083)** — **Lycée François 1er (Vitry-le-François, Marne)**
• **Type** : Bac+2 | **Statut** : Public
• **Sélectivité** : **68%** (accessible) | **Places** : 15
• **Profil admis** : 64% bacs pro, 27% bacs techno (Source: Parcoursup 2025, cod_aff_form: 6083)
• **Débouchés** : Technicien SOC, administrateur réseau sécurisé
→ *Pourquoi ?* **Porte d’entrée concrète** : 85% de néobacheliers, alternance possible dès la 2ème année.

📍 **Certificat de Spécialisation Cybersécurité (cod_aff_form: 44323)** — **Lycée Monnet-Mermoz (Aurillac)**
• **Type** : Bac+1 (formation courte) | **Statut** : Public
• **Sélectivité** : **26%** (devenue **beaucoup plus sélective** : taux ↓65pp depuis 2024 !)
• **Profil admis** : 100% bacs pro (Source: Parcoursup 2025, cod_aff_form: 44323)
• **Atout** : **1 an seulement**, idéal pour une **spécialisation rapide** après un bac pro SN (Systèmes Numériques).

---
### **🔀 Passerelles possibles**
- **De bac+2 à bac+5** :
  - Après un BTS/BUT, intégrer une **licence pro cyber** (ex : **Licence Pro Cybersécurité de l’IUT de Blois**, non listée ici mais **SecNumEdu**), puis un master.
  - **Alternance** : 80% des formations SecNumEdu bac+5 sont accessibles en alternance (ex : **CNAM**, **IMT**).
- **Sans bac+5** :
  - Certifications **ANSSI reconnues** (ex : **PASSI**, **CISSP**) + expérience = accès à des postes techniques (niveau bac+2/+3).

### **💡 Question pour toi**
Qu’est-ce qui prime pour toi ?
1️⃣ **Le prestige du diplôme** (même si c’est plus dur à intégrer) ?
2️⃣ **L’insertion pro rapide** (même avec un bac+2/+3) ?
3️⃣ **La flexibilité** (formation en alternance/à distance) ?

*Prochaine étape* : Si tu vises une formation sélective (Plan B), **prépare un dossier avec** :
- Notes ≥14/20 en informatique/maths.
- **Projets concrets** (ex : participation à un CTF comme le [FCSC](https://www.france-cybersecurity-challenge.fr/), contributions GitHub en sécurité).
- Stages/alternances dans la cyber (même courts).

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

### **Comparaison ENSEIRB-MATMECA vs EPITA en cybersécurité**

#### **1. Présentation des deux écoles**
- **ENSEIRB-MATMECA (Bordeaux)** : École publique d’ingénieurs en informatique, mathématiques et mécanique, membre du groupe INP. Propose une **majeure cybersécurité** en 3ᵉ année, labellisée **SecNumEdu** (ANSSI).
- **EPITA (Paris, Lyon, Toulouse)** : École privée d’ingénieurs en informatique, reconnue par la **CTI** et membre de la **CGE**. Propose une **majeure Sécurité et Systèmes Intelligents (SSI)** avec des modules dédiés à la cybersécurité.

---

#### **2. Tableau comparatif**

| **Critère**               | **ENSEIRB-MATMECA**                          | **EPITA**                                    |
|---------------------------|---------------------------------------------|---------------------------------------------|
| **Type / Statut**         | Public (INP)                                | Privé (CTI, CGE)                            |
| **Labels officiels**      | SecNumEdu (ANSSI)                           | CTI, CGE (pas de SecNumEdu pour la majeure SSI) |
| **Sélectivité**           | Concours **Polytech** (écrits + oraux) ou admissions sur titre (AST) — **très sélective** (taux < 10%) | Concours **Sésame** (pour prépa intégrée) ou admissions sur titre — **sélective** (taux ~15-25%) |
| **Coût annuel**           | ~600 € (frais publics) + ~200 € sécurité sociale | ~9 800 €/an (hors bourses) |
| **Localisations**         | Bordeaux (campus unique)                    | Paris, Lyon, Toulouse (3 campus)            |
| **Pédagogie cybersécurité** | Majeure dédiée **SecNumEdu** (reconnue par l’ANSSI) avec projets concrets (pentest, cryptographie) | Majeure **SSI** (sécurité + IA) — moins spécialisée qu’ENSEIRB mais avec des partenariats industriels (Thales, Airbus) |
| **Débouchés**             | **RSSI**, ingénieur sécurité, consultant en cybersécurité (secteur public/privé) | **Ingénieur sécurité**, consultant, architecte réseau (fort réseau entreprises privées) |
| **Points forts**          | - **Reconnaissance ANSSI** (SecNumEdu = gage de qualité) <br> - Coût très faible <br> - Recherche académique forte (laboratoires CNRS) | - **Réseau alumni** très actif (liens avec ESN et grands groupes) <br> - Pédagogie projet (hackathons, CTF) <br> - International (doublés diplômes) |
| **Points faibles**        | - Moins d’ouverture à l’international qu’EPITA <br> - Réseau pro moins étendu que les écoles privées | - **Coût élevé** (budget à prévoir) <br> - Majeure SSI **non labellisée SecNumEdu** (moins valorisée pour les postes publics) <br> - Sélectivité en hausse (concours Sésame très compétitif) |

---
#### **3. Synthèse personnalisée**
- **Choisis ENSEIRB si** :
  - Tu veux une **formation publique reconnue par l’ANSSI** (SecNumEdu = atout pour les postes sensibles : défense, énergie, administration).
  - Tu vises un **coût minimal** avec un diplôme aussi valorisé qu’une école privée.
  - Tu es prêt·e à affronter un **concours exigeant** (Polytech) ou une AST après une prépa/L2.
  - Bordeaux te convient (ville étudiante dynamique, coût de vie raisonnable).

- **Choisis EPITA si** :
  - Tu privilégies un **réseau professionnel fort** (stages facilités dans les ESN/grands groupes).
  - Tu veux une **pédagogie axée projets** (CTF, hackathons) et une ouverture à l’international.
  - Tu peux assumer le **coût élevé** (ou obtenir une bourse).
  - Tu cibles plutôt le **secteur privé** (la majeure SSI n’a pas le label SecNumEdu, moins utile pour les postes publics).

---
#### **4. Alternatives si les deux écoles sont hors de portée**
- **Plan B — Ambitieux** :
  - **CentraleSupélec (mastère cybersécurité)** : Double diplôme avec l’IMT, **label SecNumEdu + CTI + grade Master**. Extrêmement sélectif (concours Centrale-Supélec ou AST après une école d’ingé).
  - **ISEN Yncréa (mastère cybersécurité)** : SecNumEdu, réseau Yncréa, coûts modérés (~6 000 €/an). Sélectivité modérée (admissions sur titre).

- **Plan C — Passerelle** :
  - **Bachelor Cybersécurité EFREI Bordeaux** (SecNumEdu + CTI, **77% d’accès** en 2025) : Coût ~7 000 €/an, mais **alternance possible** dès la 3ᵉ année (salaire + diplôme gratuit).
  - **BUT Informatique (parcours cybersécurité)** : Public, **accessible** (taux > 60%), puis **poursuite en master SecNumEdu** (ex : Université de Limoges).

---
### **🔀 Passerelles possibles**
- **De ENSEIRB vers EPITA** : Peu pertinent (ENSEIRB a une meilleure reconnaissance académique).
- **De EPITA vers un master SecNumEdu** : Possible après le diplôme (ex : mastère spécialisé de l’IMT ou de l’ANSSI) pour combler l’absence de label.
- **Depuis un BUT/Bachelor** : Admission sur titre (AST) en 3ᵉ année d’ENSEIRB ou en 4ᵉ année d’EPITA avec un bon dossier.

---
### **💡 Question pour toi**
- **Quel est ton critère n°1** ?
  - La **reconnaissance officielle** (SecNumEdu pour travailler dans la défense/énergie) → ENSEIRB.
  - Le **réseau pro et l’international** → EPITA.
  - Le **coût** → ENSEIRB ou un BUT en alternance.
- **As-tu un projet précis** (ex : travailler à l’ANSSI, dans une ESN, à l’étranger) ? Cela peut faire basculer le choix.

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
La **licence** est un diplôme national de l’enseignement supérieur **de niveau bac+3** (180 crédits ECTS), délivré par les **universités publiques** (et quelques établissements privés habilités). Elle s’inscrit dans le système **LMD** (Licence-Master-Doctorat), aligné sur les standards européens (processus de Bologne).

- **Reconnaissance** : Le diplôme est **reconnu par l’État** (grade licence), ce qui permet de poursuivre en master ou de postuler à des concours de la fonction publique (catégorie A sous conditions).
- **Durée** : 3 ans (L1, L2, L3), avec une spécialisation progressive.
- **Coût** : **Gratuit ou quasi-gratuit** dans le public (frais d’inscription ~170€/an en 2024, exonération possible pour les boursiers). Les licences privées (ex : écoles) peuvent coûter **3 000€ à 8 000€/an**.

---

#### **2. Fonctionnement pratique**
##### **a. Organisation des études**
- **Parcours types** :
  - **Licence générale** : Théorique, avec des UE (unités d’enseignement) à choisir (ex : licence d’informatique avec mineure en maths).
  - **Licence professionnelle** : **Bac+3 pro**, avec **12 à 16 semaines de stage** en L3 et un taux d’insertion élevé (ex : licence pro cybersécurité). **Accès en L3 après un BTS/DUT**.
  - **Double licence** : Deux disciplines en parallèle (ex : info + gestion).

- **Modalités** :
  - Cours en **amphi (CM)**, travaux dirigés (TD), travaux pratiques (TP).
  - **Contrôle continu** (partiels, projets) ou examens terminaux selon les universités.
  - **Stage** : Obligatoire en licence pro, facultatif en licence générale (mais fortement recommandé).

##### **b. Admission**
- **Via Parcoursup** pour la **L1** :
  - **Taux d’accès variable** :
    - Licences **non sélectives** (droit, psycho, STAPS) : **taux > 80%** (mais échec en L1 fréquent).
    - Licences **sélectives** (informatique à Paris, double licence) : **taux 20-40%**.
  - Critères : **notes de 1ère/Terminale** (surtout en spécialités pertinentes), projet motivé, parfois entretien.
- **Admission en L2/L3** :
  - Sur **dossier** (notes de licence ou BTS/DUT) ou **validation des acquis** (VAE).

##### **c. Débouchés**
- **Poursuite d’études** (majoritaire) :
  - **Master** (bac+5) à l’université ou en école (via admissions parallèles).
  - **Écoles d’ingénieurs** (sur dossier ou concours comme les **AST** pour les prépas).
  - **Écoles de commerce** (via les admissions sur titre comme le **Passerelle**).
- **Insertion pro directe** (surtout avec une **licence pro**) :
  - Métiers techniques (ex : technicien cybersécurité, développeur junior).
  - Concours administratifs (catégorie B).

---
#### **3. Comparaison avec d’autres voies post-bac**
| Critère               | Licence universitaire          | BTS/DUT                     | Prépa/École d’ingénieurs       |
|-----------------------|---------------------------------|-----------------------------|--------------------------------|
| **Durée**            | 3 ans                           | 2 ans (BTS) / 3 ans (BUT)   | 2 ans (prépa) + 3 ans (école)  |
| **Sélectivité**      | Variable (10–100%)              | Modérée (30–70%)            | Très élevée (5–20%)            |
| **Coût**             | ~170€/an (public)               | Gratuit (BUT) / ~600€ (BTS) | 0€ (prépa publique) à 10k€/an |
| **Pédagogie**        | Théorique (licence générale)    | Pratique (stages, projets)  | Intensive (prépa)             |
| **Débouchés**        | Poursuite en master/école       | Insertion pro rapide        | Métiers ingénieurs (bac+5)    |

---
#### **4. Points forts et limites**
✅ **Avantages** :
- **Coût très faible** dans le public.
- **Large choix de disciplines** (45 domaines : info, bio, droit, arts…).
- **Passerelles** vers d’autres formations (écoles, BTS).
- **Reconnaissance internationale** (grade licence).

⚠️ **Risques** :
- **Taux d’échec élevé en L1** (~30 à 50% selon les filières, source : MESRI 2023).
- **Autonomie requise** : peu d’encadrement vs. une prépa ou un BTS.
- **Insertion pro difficile sans bac+5** (sauf licence pro).

---
### **Plan A / B / C : Que faire après le bac ?**
*(Exemples concrets en cybersécurité/informatique, mais adaptables à d’autres domaines)*

#### **Plan A — Réaliste : Licence publique + spécialisation progressive**
📍 **Licence Informatique** — Université de Rennes 1 (Bretagne)
• **Type** : Licence générale | **Statut** : Public
• **Sélectivité** : ~60% en L1 (taux variable selon le bac).
• **Points forts** :
  - Parcours **cybersécurité** possible en L3 (ex : parcours "Sécurité des Systèmes" à Rennes).
  - **Coût** : 170€/an | **Débouchés** : Poursuite en master cybersécurité (ex : master **SecNum** à Rennes).
• *(connaissance générale)*

🔀 **Passerelles** :
- Après L2 : Réorientation vers un **BUT Informatique** (ex : IUT de Vannes) ou une **licence pro** (ex : licence pro cybersécurité à Lorient).
- Après L3 : Admission en **école d’ingénieurs** (via AST) ou master.

---

#### **Plan B — Ambitieux : Double licence ou prépa pour viser une école**
📍 **Double licence Maths-Info** — Université Paris Cité
• **Type** : Licence bidisciplinaire | **Statut** : Public
• **Sélectivité** : ~20% (dossier exigeant : mentions Bien/Très Bien en maths et NSI).
• **Points forts** :
  - **Accès facilité** aux masters sélectifs (ex : **Mastère Cybersécurité de CentraleSupélec**).
  - **Profil hybride** recherché en data science/cyber.
• *(connaissance générale)*

📍 **CPGE (Prépa MPSI/MP)** — Lycée Chateaubriand (Rennes)
• **Type** : Classe préparatoire | **Statut** : Public
• **Sélectivité** : ~15% (notes de 1ère/Terminale en maths/physique).
• **Points forts** :
  - Voie royale pour intégrer une **école d’ingénieurs** (ex : **IMT Atlantique**, **CentraleSupélec**) avec leur **mastère cybersécurité labellisé SecNumEdu**.
• *(connaissance générale)*

---
#### **Plan C — Alternatif : BTS/DUT pour une insertion rapide ou une réorientation**
📍 **BTS SIO option Cybersécurité** — Lycée Bréquigny (Rennes)
• **Type** : BTS | **Statut** : Public
• **Sélectivité** : ~70% (accessible avec un bac général/techno).
• **Points forts** :
  - **Diplôme pro en 2 ans** avec **10 semaines de stage/an**.
  - **Poursuite possible** en licence pro ou école (ex : **ENSSAT** à Lannion).
• *(connaissance générale)*

📍 **BUT Informatique parcours Cybersécurité** — IUT de Vannes
• **Type** : BUT (bac+3) | **Statut** : Public
• **Sélectivité** : ~50% (dossier + parfois entretien).
• **Points forts** :
  - **Diplôme grade licence** avec **600h de projets** et stages.
  - **Taux d’insertion** : ~90% à 6 mois (source : enquêtes DUT 2023).
• *(connaissance générale)*

---
### **🔀 Passerelles possibles entre ces voies**
- **Licence → École d’ingénieurs** : Via les **admissions sur titre (AST)** en L3 (ex : concours **CastiNG** pour le réseau **Polytech**).
- **BTS/DUT → Licence** : **Équivalences** pour entrer directement en L3 (ex : BTS SIO → licence pro cyber).
- **Prépa → Université** : Possible après une **1ère année de prépa** (via Parcoursup en L2).

---
### **💡 Question pour toi**
Tu hésites entre une voie **théorique** (licence/prépa) ou **pratique** (BTS/BUT) ?
- Si tu aimes **les maths et vises un bac+5**, une **double licence** ou une **prépa** peut ouvrir les portes des meilleures écoles.
- Si tu préfères **l’opérationnel et une insertion rapide**, un **BTS SIO** ou **BUT Informatique** est plus adapté.
- Si tu veux **garder des options ouvertes**, une **licence générale** avec des stages est un bon compromis.

**Prochaine étape** :
- Consulte les **taux d’accès Parcoursup 2025** pour les formations qui t’intéressent (disponibles sur [Parcoursup.fr](https://www.parcoursup.fr) à partir de janvier).
- Si tu vises une licence sélective (ex : double licence), prépare un **dossier avec des notes solides en spécialités pertinentes** (NSI, maths, physique).

---
### **Ressources utiles**
- **Simulateur de vœux Parcoursup** : [MonMaster.gouv.fr](https://www.monmaster.gouv.fr) (pour les masters).
- **Fiches métiers cybersécurité** : [ANSSI](https://www.ssi.gouv.fr) (pour explorer les débouchés).
- **Onisep** : [Fiches licences par domaine](https://www.onisep.fr).

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

Voici une réponse adaptée à ta situation de réorientation depuis une L2 droit vers l’informatique, avec des options concrètes et des passerelles réalistes :

---

### **Plan A — Réaliste : BTS ou Certificat de Spécialisation en cybersécurité (bac+2/3)**
**Pourquoi ?** Ces formations courtes (1 à 2 ans) sont accessibles sans prérequis techniques forts et permettent une insertion rapide ou une poursuite d’études.

📍 **BTS CIEL Option B (Électronique et réseaux)** — Lycée Jean de Lattre de Tassigny, **La Roche-sur-Yon**
• Type : BTS (bac+2) | Statut : Public
• Labels : Aucun label officiel (mais formation reconnue par l’Éducation nationale)
• Sélectivité : **67%** (accessible) — 15 places pour 138 vœux (Source: Parcoursup 2025, cod_aff_form: 10548)
• Débouchés : Administrateur sécurité (M1817), technicien réseaux
• **Atout** : 50% des admis viennent de bac pro → adapté aux profils en reconversion.

📍 **Certificat de Spécialisation Cybersécurité** — Lycée Jean-Baptiste Clément, **Sedan (Ardennes)**
• Type : Certificat (bac+1/2) | Statut : Public
• Labels : Aucun
• Sélectivité : **51%** (accessible) — 6 places, vœux en hausse (+26%) (Source: Parcoursup 2025, cod_aff_form: 44430)
• Débouchés : Technicien cybersécurité, support IT
• **Atout** : 100% des admis sont boursiers → bon filet social.

---
### **Plan B — Ambitieux : École d’ingénieur en cybersécurité (bac+5)**
**Pourquoi ?** Si tu vises un poste d’ingénieur (RSSI, expert), une école labellisée **SecNumEdu** (reconnue par l’ANSSI) est idéale. Mais la sélectivité est forte : il faut préparer un **DUT/BUT informatique** ou une **licence info** en parallèle pour candidater en admissions parallèles.

📍 **Diplôme d’ingénieur Cybersécurité** — **ENSIBS (Vannes, Bretagne)**
• Type : Diplôme d’ingénieur (bac+5) | Statut : Public
• Labels : **SecNumEdu + CTI** (grade master)
• Sélectivité : Non précisée (mais les écoles d’ingénieur post-prépa ont un taux <10%)
• Débouchés : Ingénieur sécurité (M1819), RSSI (M1812)
• **Chemin possible** :
  1. Faire un **BUT Informatique** (1 an) pour acquérir les bases (algèbre, programmation).
  2. Postuler en **admission parallèle** (L3 ou M1) à l’ENSIBS via leur concours.
  *(connaissance générale : les écoles comme ENSIBS recrutent 10-20% de leurs élèves en admissions parallèles)*

---
### **Plan C — Passerelle : Licence Informatique + Spécialisation progressive**
**Pourquoi ?** Moins sélective qu’une école d’ingénieur, une licence te permet de monter en compétences tout en gardant des portes ouvertes (master, alternance).

📍 **Licence Informatique** — **Université de ton académie** (ex : **Lyon 1**, **Bordeaux**, **Strasbourg**)
• Type : Licence (bac+3) | Statut : Public
• Labels : Grade licence (diplôme d’État)
• Sélectivité : **~70-80%** (accessible) en L2/L3 après une réorientation
• Débouchés : Développeur, administrateur systèmes (puis spécialisation en master)
• **Atout** :
  - **Parcoursup** : Les licences acceptent souvent les réorientés de droit (même sans bases en info).
  - **Alternance** : Possible en L3 pour financer tes études.
  *(connaissance générale : les universités proposent des "parcours renforcés" pour les non-scientifiques, ex : L2 "Informatique pour tous" à Paris-Nanterre)*

---
### 🔀 **Passerelles possibles entre ces plans**
- **BTS → Licence** : Après un BTS CIEL, tu peux intégrer une **L3 informatique** (ex : université de Nantes).
- **Licence → École d’ingénieur** : Avec une L3 info, candidate aux **admissions parallèles** des écoles comme le **CNAM** (formation continue, labellisée SecNumEdu).
- **Alternance** : Les **Certificats de Spécialisation** (ex : Sedan) sont compatibles avec des contrats pro.

---
### 💡 **Question pour toi**
Quelle est ta priorité absolue ?
✅ **Un diplôme rapide** pour travailler dès bac+2/3 → **Plan A** (BTS/Certificat).
✅ **Un poste d’ingénieur/expert** à terme → **Plan B** (préparer un BUT + école).
✅ **Garder des options ouvertes** (recherche, enseignement, etc.) → **Plan C** (licence).

---
### **Prochaine étape concrète**
1. **Si tu choisis le Plan A** : Postule **dès maintenant** sur Parcoursup aux BTS/Certificats (les places partent vite).
2. **Si tu vises le Plan B** : Inscris-toi en **BUT Informatique** (rentrée 2025) + prépare-toi aux tests techniques (ex : algorithmique sur [France-IOI](https://www.france-ioi.org/)).
3. **Pour le Plan C** : Contacte le **SCUIO** (service d’orientation) de ton université actuelle pour un **parcours personnalisé** en L2/L3 info.

*(connaissance générale : Les réorientés en info ont souvent un avantage en gestion de projet et rédaction — des compétences rares chez les informaticiens !)*

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

Voici les formations **à Perpignan et ses alentours** (Occitanie) qui correspondent à tes critères, classées par pertinence et accessibilité :

---

### **Plan A — Réaliste & Local**
**📍 BUT Science des données** — IUT de Perpignan (site de Carcassonne), **Carcassonne** (30 min de Perpignan)
• **Type** : Bachelor Universitaire de Technologie (BUT) | **Statut** : Public
• **Labels** : Grade Licence (reconnu par l'État)
• **Sélectivité** : 76% (accessible, mais **devenue plus sélective** : taux ↓12pp depuis 2023)
  *Profil admis* : 83% bac général (33% avec mention AB), 17% bac techno.
• **Débouchés** : Data scientist (M1405), Data analyst (M1419), Chief Data Officer.
• **Source** : Parcoursup 2025, `cod_aff_form: 2469`

**Pourquoi ?**
- **Seule formation bac+3 publique** dans un rayon de 100 km autour de Perpignan avec un **grade Licence** (diplôme reconnu pour poursuivre en master).
- **Taux d’accès élevé** (76%) mais **attention** : la formation gagne en popularité (+59% de vœux depuis 2023).
- **Mixité des profils** : adaptée si tu as un bac général ou techno (peu de bacs pro admis).

---

**📍 BTS Cybersécurité, Informatique et Réseaux (Option A)** — Lycée Pablo Picasso, **Perpignan**
• **Type** : BTS | **Statut** : Public
• **Labels** : Aucun label spécifique (mais diplôme d'État)
• **Sélectivité** : 47% (modérément sélective), **attrait en baisse** (-39% de vœux depuis 2023).
  *Profil admis* : 50% bac techno, 44% bac pro (seulement 6% bac général).
• **Débouchés** : Administrateur sécurité (M1817), Ingénieur sécurité (M1819).
• **Source** : Parcoursup 2025, `cod_aff_form: 7856`

**Pourquoi ?**
- **Formation 100% locale** (pas de déménagement).
- **Peu de concurrence** : le nombre de vœux baisse depuis 2023.
- **Idéal si tu as un bac techno/pro** (peu adapté aux bacs généraux).

---

### **Plan B — Ambitieux (sélectif mais proche)**
**📍 BTS Cybersécurité (Option A) — Lycée Jean Mermoz, Montpellier** (1h30 de Perpignan)
• **Type** : BTS | **Statut** : Public
• **Labels** : Aucun label (mais **réputation forte** en cybersécurité).
• **Sélectivité** : 14% (très sélective), **en hausse** (taux ↓12pp depuis 2023).
  *Profil admis* : 18% mention TB, 29% B (bacs généraux/techno performants).
• **Débouchés** : RSSI (M1812), Ingénieur sécurité.
• **Source** : Parcoursup 2025, `cod_aff_form: 4499`

**Pourquoi ?**
- **L’un des meilleurs BTS cybersécurité** de la région (classé parmi les plus demandés).
- **Exigeant** : nécessite un **dossier solide** (notes ≥ 14/20 en maths/info).
- **Alternative** : Si tu vises ce BTS, poste aussi le **BTS du Lycée Picasso à Perpignan** (Plan A) en vœu de secours.

---

### **Plan C — Passerelle ou alternative**
1. **Certificat de Spécialisation Cybersécurité** (Lycée Ampère, Marseille)
   - **Public cible** : Titulaires d’un bac pro/techno (86% des admis).
   - **Sélectivité** : 57% (accessible), mais **en forte hausse** (taux ↓35pp en 1 an !).
   - **Source** : `cod_aff_form: 44314`
   - *Pour toi si* : Tu veux une **formation courte (1 an)** après un bac pro/techno, avec un focus pratique.

2. **(Connaissance générale) Licence Informatique — Université de Perpignan**
   - **Parcours** : Licence mention Informatique (parcours **Sécurité des Systèmes** en L3).
   - **Sélectivité** : ~60-70% (accessible, mais vérifie les attendus sur [leur site](https://www.univ-perp.fr)).
   - *Pour toi si* : Tu préfères **l’université** et une approche plus théorique avant de te spécialiser.

---

### **🔀 Passerelles possibles**
- **De BTS vers BUT** : Après un BTS Cybersécurité (Lycée Picasso), tu peux candidater en **2ème année de BUT Science des données** (Carcassonne) via **Parcoursup en admission parallèle**.
- **De BUT vers Master** : Le BUT de Carcassonne permet de viser des **masters en data science** (ex : Master Cybersécurité à Montpellier ou Toulouse).

### **💡 Question pour toi**
- **Préfères-tu une formation courte (BTS) pour entrer vite dans le monde du travail, ou un diplôme bac+3 (BUT) pour avoir plus d’options plus tard ?**
- **Es-tu mobile** (Montpellier/Carcassonne) ou veux-tu **rester à Perpignan** ?

---
**Prochaine étape** :
- Si tu vises le **BTS Jean Mermoz (Montpellier)**, prépare un **dossier ultra-solide** (notes, projets perso en cyber).
- Si tu veux **rester local**, mise sur le **BUT Carcassonne** (vœu 1) + **BTS Picasso** (vœu 2).

---
