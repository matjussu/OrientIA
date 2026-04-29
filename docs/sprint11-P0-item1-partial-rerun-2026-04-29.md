# Sprint 11 P0 Item 1 — Re-run partiel test serving (4 questions)

**Date** : 2026-04-29
**Branche** : `feat/sprint11-P0-prompt-refonte`
**Prompt** : SYSTEM_PROMPT v4 (préfixe Sprint 11 P0 Strict Grounding + Glossaire + Progressive Disclosure)
**Pipeline** : OrientIAPipeline default (use_metadata_filter=True, use_golden_qa=True)

## Sample audit Jarvis avant Item 4 full re-run

Re-run uniquement les 3 questions où Matteo a détecté des hallucinations dans le chantier E (test serving) + 1 baseline cas standard pour vérifier pas de régression UX.

### Stats agrégées

- Word count moyen : **311 mots** (cible Progressive Disclosure ≤250)
- Word count range : 279 - 384
- Word count <=250 (cible Sprint 11 P0) : 0/4
- Latence moyenne : 10747 ms

---

## Q1 — J'ai raté ma PASS, est-ce que je peux quand même faire kiné ou infirmière ?

**Mesures** : t_total=10791ms | word_count=282 mots (cible ≤250 ✅' if False else '⚠️ DÉPASSEMENT')

**Q&A Golden top-1** : `A3` iter 0 (score 86, sim 0.70)

**Sources top-3** :
  1. Licence - Parcours d'Accès Spécifique Santé (PASS)
  2. Licence - Parcours d'Accès Spécifique Santé (PASS)
  3. Licence - Parcours d'Accès Spécifique Santé (PASS)

**Réponse Mistral (post Sprint 11 P0)** :

> **TL;DR**
> 1. Après un échec en PASS, **médecine/kiné en direct sont fermés** (concours MMOPK réservé aux PASS/L.AS validés).
> 2. **Infirmière reste accessible** via Parcoursup sur dossier (notes lycée + projet motivé), sans concours.
> 3. **Kinésithérapeute** exige une **Licence STAPS ou Sciences** + concours post-licence (4 ans d’études au total).
> 
> ---
> 
> ### **Plan A — Réaliste : Devenir infirmière·er (IFSI)**
> 📍 **Formation en Soins Infirmiers (IFSI)** — bac+3 public, **admission sur dossier Parcoursup** (pas de concours), sélectivité modérée (~30-50% selon IFSI).
> *Pour toi : accessible avec ton bac (même sans PASS), salariat garanti à la sortie (salaire médian ~1 800€ net).*
> → [Liste des IFSI sur Parcoursup](https://www.parcoursup.fr)
> 
> ### **Plan B — Ambitieux : Kinésithérapeute (post-licence)**
> 📍 **Licence STAPS** (ex : [Sorbonne Université](https://www.parcoursup.fr)) → **concours kiné en M1** (4 ans total).
> *Pour toi : exigeant (notes >14/20 en STAPS pour réussir le concours), mais débouchés solides (salaire ~2 200€ net).*
> 
> ### **Plan C — Alternative : Réorientation paramédicale (accès direct)**
> 📍 **DEAES (Aide Médico-Psychologique)** ou **DE Ambulancier** — bac+1/2, **admission sur dossier**, formations courtes et professionnalisantes.
> *Pour toi : si tu veux un métier rapide dans le soin, sans repartir en licence.*
> 
> ---
> **⚠ Attention**
> - **Kinésithérapeute = 0 place en PASS échoué** : la voie classique passe **obligatoirement** par une licence (STAPS/Sciences) + concours en M1.
> - **IFSI** : vérifie les **dates Parcoursup** (inscriptions souvent dès janvier) et prépare un **projet motivé solide** (stages en EHPAD/clinique = atout).
> 
> **Question pour toi** :
> Préfères-tu un **métier rapide** (IFSI/DEAES) ou **repartir dans des études longues** (kiné) pour un salaire plus élevé ? Je peux t’aider à affiner le choix. 👤 *Pour un accompagnement personnalisé, prends RDV avec le Psy-EN de ton lycée ou un CIO.*

---

## Q2 — Je travaille dans le tertiaire depuis 5 ans, je veux me reconvertir paramédical après un b...

**Mesures** : t_total=13928ms | word_count=384 mots (cible ≤250 ✅' if False else '⚠️ DÉPASSEMENT')

**Q&A Golden top-1** : `A2` iter 0 (score 84, sim 0.71)

**Sources top-3** :
  1. MASSEUR-KINESITHERAPEUTE (DIPLOME D'ETAT)
  2. Carrières sociales : Villes et territoires durables
  3. Carrières Sociales : Villes et territoires durables

**Réponse Mistral (post Sprint 11 P0)** :

> **TL;DR**
> Vous souhaitez une reconversion dans le paramédical après 5 ans dans le tertiaire : les métiers d’accompagnement et de soins à la personne (niveau bac) ou de conseiller en transition professionnelle (niveau bac+2) sont accessibles via des formations courtes, souvent en alternance ou financées par le CPF. La VAE peut aussi valoriser votre expérience.
> 
> ---
> **Plan A — Accès rapide : Formations niveau bac en accompagnement/soins**
> 📍 **Accompagnement, soins et services à la personne** (Trajectoire Formation / Polaris Formation / ASS Jeanne Mance) — formations courtes (niveau bac), sans prérequis stricts, éligibles CPF.
> *Pour vous : idéal pour tester le terrain paramédical sans engagement long, avec des débouchés immédiats (aide-soignant, auxiliaire de vie).*
> 
> **Plan B — Spécialisation : Conseiller en transition professionnelle (bac+2 RNCP)**
> 📍 **Conseiller emploi et accompagnement professionnel** (OpenClassrooms) ou **Conseiller en transition professionnelle** (Ministère des Armées) — certifications RNCP bac+2, 100% à distance, financées CPF.
> *Pour vous : valorise votre expérience tertiaire tout en basculant vers l’humain/social, avec des passerelles vers le paramédical (ex : DEAES ensuite).*
> 
> **Plan C — Projet long terme : Kinésithérapie (bac+5) via VAP/VAE**
> 📍 **Diplôme d’État de masseur-kinésithérapeute** (Institut Paramédical de Nevers) — bac+5, accessible après une L.AS/PASS ou via VAP (validation des acquis professionnels) si vous avez 3 ans d’expérience + tests.
> *Pour vous : exigeant, mais envisageable si vous visez un métier très technique. Commencez par un bilan de compétences (CPF) pour évaluer la faisabilité.*
> 
> ---
> **⚠ Attention aux pièges**
> - **Sélectivité des filières paramédicales longues** : Les formations comme kinésithérapie ou infirmier (non listées ici) nécessitent souvent un parcours santé (L.AS/PASS) ou un concours. Les fiches actuelles ne couvrent pas ces voies — vérifiez sur [ONISEP](https://www.onisep.fr) ou avec un conseiller en VAE.
> - **Financement** : Même éligibles CPF, certaines formations ont des restes à charge. Comparez les coûts réels sur [Mon Compte Formation](https://www.moncompteformation.gouv.fr).
> - **Débouchés listés incohérents** : Les métiers cités (médecin, sage-femme) dans les fiches ne correspondent pas aux formations proposées. Ces diplômes mènent plutôt à des postes d’accompagnant (ex : AES) ou de conseiller social.
> 
> **Question pour vous** :
> Préférez-vous une entrée immédiate dans le soin (Plan A), une transition progressive via le conseil (Plan B), ou un projet ambitieux à long terme comme la kinésithérapie (Plan C) ? Votre expérience tertiaire pourrait être un atout pour le Plan B.

---

## Q3 — Je suis en terminale L et tout le monde me dit que ça ne mène à rien, est-ce vrai ?

**Mesures** : t_total=7874ms | word_count=299 mots (cible ≤250 ✅' if False else '⚠️ DÉPASSEMENT')

**Q&A Golden top-1** : `A3` iter 0 (score 86, sim 0.81)

**Sources top-3** :
  1. Licence - Langues étrangères appliquées - Parcours LEA (Langues Etrangères Appliquées) ( 2
  2. LANGUES ETRANGERES APPLIQUEES (MASTER)
  3. LANGUES ETRANGERES APPLIQUEES (LIC LMD)

**Réponse Mistral (post Sprint 11 P0)** :

> **TL;DR**
> 1. La série L n'existe plus depuis 2021, mais ton profil littéraire est un atout pour des études en langues, communication ou enseignement.
> 2. Les formations en langues (LEA) ont un bon taux d'insertion (44% en emploi stable à 12 mois) et des débouchés variés.
> 3. Voici 3 pistes concrètes pour exploiter tes compétences en lettres et langues.
> 
> ---
> 
> ### **Plan A — Réaliste : Licence LEA (Langues Étrangères Appliquées)**
> 📍 **LEA (2 langues hors anglais)** à **Sorbonne Université (Paris)** — bac+3 public, sélectivité 42%, 45 places
> *Pour toi : idéal si tu aimes les langues et veux des débouchés en communication, commerce international ou traduction.*
> 
> ### **Plan B — Ambitieux : Double compétence langues + droit/économie**
> 📍 **Licence LEA + mineure en droit ou économie** (ex : **Université Lyon 2**) — bac+3 public
> *Pour toi : renforce ton profil pour des métiers comme juriste international ou chargé de projet à l’étranger.*
> 
> ### **Plan C — Alternative : Métiers de l’enseignement ou de la médiation culturelle**
> 📍 **Licence Langues, Enseignement, Médiation** (ex : **Université Gustave Eiffel**) — bac+3 public
> *Pour toi : si tu aimes transmettre, cette voie mène au professorat, à la médiation culturelle ou au tourisme.*
> 
> ---
> **⚠ Attention aux pièges**
> - **LEA à la Sorbonne est très demandée** (+238% de vœux depuis 2023) : prépare un dossier solide (notes de langues, projets liés).
> - **Les métiers "purement littéraires" (écrivain, traducteur freelance) sont précaires** : vise des doubles compétences pour sécuriser ton parcours.
> 
> ---
> **Question pour toi :**
> Est-ce que tu préfères un métier **concret et international** (LEA), un parcours **polyvalent** (double compétence), ou un métier **humain et pédagogique** (enseignement/médiation) ?
> 
> ---
> 👤 *Pour affiner ton projet, un RDV avec le Psy-EN de ton lycée ou un conseiller d’orientation (CIO) peut t’aider à préciser tes choix.*

---

## Q4 — Je suis en terminale spé maths-physique mais je sature des maths abstraites, alternatives ...

**Mesures** : t_total=10396ms | word_count=279 mots (cible ≤250 ✅' if False else '⚠️ DÉPASSEMENT')

**Q&A Golden top-1** : `A1` iter 6 (score 88, sim 0.94)

**Sources top-3** :
  1. Licence - Double diplôme - Licence Mathématiques, Physique et Sciences pour l'Ingénieur - 
  2. Licence - Mathématiques - Parcours Mathématiques et physique approfondies - Magistère (MPA
  3. Licence - Double diplôme - Licence Mathématiques et informatique appliquées aux sciences h

**Réponse Mistral (post Sprint 11 P0)** :

> **TL;DR**
> Si je te comprends bien, tu veux rester dans les sciences mais appliquer les maths à des projets concrets, sans tomber dans l’abstrait pur. Voici 3 pistes **réalistes** qui évitent la prépa MPSI tout en valorisant ton profil maths-physique.
> 
> ---
> 
> ### **Plan A — Double licence maths-physique appliquée**
> 📍 **[Licence Mathématiques, Physique et Applications](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=41045&typeBac=0&originePc=0)** (Versailles) — bac+5 public, sélectivité 27% (mention TB quasi obligatoire).
> *Pour toi :* Un équilibre entre théorie et applications (physique, modélisation), avec des projets concrets dès la L2. **Attention** : la sélectivité a explosé (+65% de vœux en 2 ans).
> 
> ### **Plan B — École d’ingé post-bac accessible**
> 📍 **[EPF Paris-Cachan](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=42994&typeBac=0&originePc=0)** (Cachan) — bac+5 privé, **95% d’admis** (mention AB acceptable).
> *Pour toi :* Cursus ingénieur **sans prépa**, avec des projets techniques dès la 1ère année. Coût élevé (privé), mais alternance possible en cycle master.
> 
> ### **Plan C — Maths appliquées + sciences sociales**
> 📍 **[Maths appliquées et Sciences sociales](https://dossierappel.parcoursup.fr/Candidats/public/fiches/afficherFicheFormation?g_ta_cod=32559&typeBac=0&originePc=0)** (Sciences Po Paris) — bac+3 public, **10% d’admis** (réservé aux mentions TB).
> *Pour toi :* Si tu veux **sortir des sciences dures** tout en gardant les maths : modélisation pour l’économie, la socio, ou le politique. **Très sélectif** mais unique en son genre.
> 
> ---
> **⚠ Attention aux pièges**
> - **EPF/ESILV** : Le privé coûte cher (8k-12k€/an). Vérifie les bourses ou l’alternance **avant** de postuler.
> - **Sciences Po** : 10% d’admis = dossier **ultra-solide** requis (notes + engagements).
> - **Double licence** : À Versailles, 73% des admis ont une mention TB. Si tu es en dessous, mise sur l’EPF.
> 
> **Question pour toi** : Préfères-tu un cursus **100% scientifique appliqué** (Plan A/B) ou un mix **maths + sciences humaines** (Plan C) ? On peut affiner ensemble !

---


## À auditer côté Jarvis

Pour chaque question, vérifier :
- Q1 (PASS/IFSI) : la réponse mentionne-t-elle un concours IFSI post-bac ? (= hallu si oui)
- Q2 (DEAMP) : la réponse mentionne-t-elle DEAMP ou propose-t-elle DEAES ? (DEAES = correct)
- Q3 (Terminale L) : la réponse parle-t-elle de série L ou recadre vers spécialités ? (recadrage = correct)
- Q4 (baseline MPSI) : pas de régression UX, formats Plan A/B/C ≤250 mots maintenu

Si les 4 réponses sont compliantes Strict Grounding + Glossaire actif → GO Item 2 (buffer mémoire) puis Item 4 (full re-run 10 questions).

*Re-run généré par `scripts/test_serving_partial_sprint11p0.py` sous l'ordre `2026-04-29-1700-claudette-orientia-sprint11-P0-corrections-prompt-buffer-judge` (Item 1 sample audit).*