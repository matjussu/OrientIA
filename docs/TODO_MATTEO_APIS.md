# TODO Matteo — Signups APIs externes (Sprint 1 Axe 1 data foundation)

**Contexte** : checklist signups data sources pour OrientIA. Mis à jour au fur
et à mesure des activations. ✅ = activé + testé OK, ⏳ = en attente action
Matteo, 📋 = manual download requis.

**État au 2026-04-23 12:24** : **France Travail ROME 4.0 + ONISEP activés**
et opérationnels. La Bonne Alternance en attente habilitation. Céreq en
attente download manuel. 2 nouveaux scopes FT recommandés pour S+2 (Marché du
travail + Accès emploi demandeurs).

---

## 1. ✅ France Travail API — ROME 4.0 + scopes S+2 (ADR-042)

**Statut** : ✅ **ACTIVÉ 2026-04-23** pour les 4 APIs ROME 4.0. Credentials
testés OK :
- OAuth2 token ✓
- GET `/v1/metiers/metier` → 1 584 métiers ingérés
- Ingestion fiches détaillées en cours (background)

### Scopes actuellement activés (4 APIs ROME 4.0)

- ✅ `api_rome-metiersv1` — Référentiel des métiers
- ✅ `api_rome-fiches-metiersv1` — Fiches métiers détaillées
- ✅ `api_rome-competencesv1` — Compétences par métier
- ✅ `api_rome-contextes-travailv1` — Contextes de travail
- ✅ `nomenclatureRome` — Métadonnées nomenclature

### ⚠️ Scopes S+2 à activer (ADR-042, cf DECISION_LOG)

**2 min côté Matteo dans le dashboard app France Travail** (pour débloquer
les 3 APIs complémentaires analysées P1) :

- ⏳ `api_marche-travailv1` (tension marché par ROME × région, rate 10 RPS)
- ⏳ `api_acces-a-l-emploi-des-demandeurs-d-emploiv1` (taux retour emploi 6m,
  rate 10 RPS)
- (Anotéa v1 = auth HMAC-SHA256 custom, pas un scope OAuth2 — procédure dédiée
  si on l'active — plus tard S+2/S+3)

**Procédure** :
1. Aller sur https://francetravail.io → dashboard → ton app OrientIA
2. "Ajouter des habilitations" / "Gérer les scopes"
3. Cocher les 2 scopes ci-dessus
4. Soumettre. Activation immédiate (pas de review 24-48h pour des scopes
   additionnels sur app existante).
5. Ping Jarvis : "scopes MT + Accès Emploi activés" → Claudette code les 2
   modules S+2 (~10-14j cumul).

### Rate limits officiels (important pour tuning)

- ROME 4.0 (4 APIs) : **1 RPS** = 60 RPM → DEFAULT_RPM=50 dans `rome_api.py`
  (marge 17%)
- Anotéa v1 : 8 RPS
- Marché du travail v1 : 10 RPS
- Accès à l'emploi demandeurs v1 : 10 RPS

### Notes
- Le flow OAuth2 `client_credentials` régénère le token à chaque expiration
  (~20 min) automatiquement.
- Credentials stockés dans `.env` local uniquement (jamais committed, cf
  `.gitignore`).
- **Reco sécu post-usage** : revoke + regenerate `FT_CLIENT_SECRET` post-
  stabilisation projet (secret était exposé Telegram historique).

---

## 2. ✅ ONISEP OpenData API — formations scope étendu

**Statut** : ✅ **ACTIVÉ 2026-04-23**. Credentials testés OK :
- `authenticate(email, password)` → token JWT ✓
- `fetch_formations(token, app_id, "cybersécurité", size=5)` → 5 résultats
  avec champs riches (code_nsf, code_rncp, duree, niveau, sigle_formation, etc.)
- **Ingestion D2 extended lancée 2026-04-23** : 15 domaines OrientIA → **4 775 fiches
  uniques** ingérées dans `data/processed/onisep_formations_extended.json`
  (module `src/collect/onisep_formations_extended.py`)
- Distribution : eco_gestion 25% / lettres_arts 16% / ingenierie 13% /
  sciences fond 11% / sport 9% / droit 8% / communication 7% / 7 autres
- Phases : initial 62% (2 984) / master 38% (1 791)

### Notes
- Credentials dans `.env` local : `ONISEP_EMAIL` / `ONISEP_PASSWORD` /
  `ONISEP_APP_ID` / `ONISEP_USERNAME`
- Le code `src/collect/onisep.py` + `src/collect/onisep_formations_extended.py`
  sont opérationnels.
- ONISEP expose aussi un endpoint public sans auth (`_fetch_formations_public`)
  mais limité ~500 résultats par query et pas de champs enrichis.
- **Reco sécu post-usage** : changer `ONISEP_PASSWORD` post-stabilisation (secret
  était exposé Telegram historique).

---

## 3. ⏳ La Bonne Alternance — api.apprentissage.beta.gouv.fr (D10)

**Statut** : ⏳ **EN ATTENTE** — scaffold code prêt (`src/collect/labonnealternance.py`,
9 tests mockés verts). Activation dès que token Bearer arrive dans `.env`.

**Durée estimée** : 5 min signup + ~48h habilitation côté data.gouv.fr.

**Utilité** : formations en alternance (~26 k) + offres apprentissage actives
(~225 k) pour combler la **phase (b) réorientation/alternance à 0%** dans la
répartition actuelle du corpus (ADR-039 cible 33/33/34).

### Procédure signup complète (7 étapes)

1. **Aller sur** https://api.apprentissage.beta.gouv.fr/compte (portail dev
   officiel, pas api.gouv.fr)
2. **S'inscrire** avec email `matteolepietre@gmail.com` (cohérence avec FT + ONISEP)
3. **Valider l'email** de confirmation
4. **Se connecter** → profil dev
5. **Demander un token d'accès** aux APIs :
   - `/api/v1/formations` (formations alternance référencées)
   - `/api/v1/jobs` (offres emploi alternance temps quasi-réel)
   - Procédure beta.gouv standard = **habilitation "légère" sous ~24-48h** ouvrés
6. **Recevoir le token par email** (une fois habilitation validée)
7. **Ajouter dans `~/projets/OrientIA/.env`** :
   ```bash
   LBA_API_TOKEN=<ton_token_bearer>
   ```
8. **Ping Jarvis** : "token La Bonne Alternance OK" → Claudette active D10
   instantanément (code déjà là).

### Contact support

En cas de blocage habilitation : `labonnealternance@apprentissage.beta.gouv.fr`
(équipe beta.gouv apprentissage).

### Notes
- Licence Open Licence 2.0 (Etalab) — usage non-commercial OK pour OrientIA
  INRIA public.
- Pas de rate limit hostile (5-20 RPS selon endpoint). Client `labonnealternance.py`
  utilise RateLimiter 120 RPM (2 RPS) safe.
- La ressource "formations alternance" est quasi-stable (refresh mensuel), les
  offres jobs sont quasi temps-réel (refresh daily).

---

## 4. 📋 Céreq Enquêtes Génération — download manuel CSVs (D11)

**Statut** : 📋 **MANUEL** — parser scaffold prêt (`src/collect/cereq.py`, 13
tests), attend les CSVs téléchargés localement.

**Durée estimée** : 10 min download + copie fichiers locaux.

**Utilité** : taux d'insertion + salaire médian + % CDI par niveau diplôme ×
secteur pour enrichir les fiches OrientIA (phase c insertion pro).

### Procédure download

1. Aller sur https://www.cereq.fr/datavisualisation/insertion-professionnelle-des-jeunes/les-chiffres-cles-par-diplome
2. Télécharger les CSVs disponibles (boutons "Télécharger" / "Exporter" sur
   chaque dashboard — typiquement 1 CSV par niveau (BTS / Licence / Master) et
   par cohorte (Génération 2017 / 2021))
3. Copier les fichiers dans `~/projets/OrientIA/data/raw/cereq/` en nommant
   `cereq_<dashboard>_<cohorte>.csv` (ex : `cereq_chiffres_cles_gen2017.csv`,
   `cereq_salaires_master_gen2021.csv`)
4. Ping Jarvis : "CSVs Céreq disponibles" → Claudette parse automatiquement
   via `python -m src.collect.cereq`

### Notes
- Céreq ne publie pas d'API bulk-download standardisée — download manuel requis.
- Fallback si portail a changé : rapports PDF agrégés sur https://www.cereq.fr/publications
  (scraping au coup par coup, moins pratique).
- Le parser est permissif sur delimiters (`;` FR / `,` EN) et noms de colonnes
  (essaie plusieurs variantes).
- Future enquête Génération 2021 (collecte 2024, publication fin 2024/début 2025)
  = à re-télécharger quand elle sort pour rafraîchir les stats.

---

## 5. (Optionnel, décision S+2) Reddit OAuth — RAFT dataset génération γ

**Durée estimée** : 3-5 min signup, activation immédiate.

**Utilité** : pour scraper r/Parcoursup + r/EtudesSuperieures + r/AskFrance
afin de compléter 200-300 questions étudiants réels pour le dataset
fine-tuning RAFT (S+3 Axe 3).

**Quand décider** : fin S+2. Claudette démarre d'abord le scraping 100%
autonome (forums ONISEP + Parcoursup public + StackExchange + HackerNews).
Si volume final ≥ 200 questions propres, Reddit devient optionnel. Sinon,
Matteo fait les 5 min de signup pour compléter à 350-450 questions.

### Étapes (si on va Reddit)

1. https://www.reddit.com/prefs/apps → "create another app..."
2. Type : `script`
3. Name : `OrientIA-research`
4. Redirect URI : `http://localhost:8080` (pas utilisé en script mode)
5. Récupérer `client_id` (sous le nom de l'app) + `client_secret`
6. Ajouter dans `.env` :
   ```bash
   REDDIT_CLIENT_ID=<id>
   REDDIT_CLIENT_SECRET=<secret>
   REDDIT_USER_AGENT=OrientIA-research by /u/<ton-username>
   ```

---

## Check avant de commit `.env`

```bash
# Ne JAMAIS commit .env (il est déjà dans .gitignore, vérifier)
grep -l ".env" .gitignore || echo "⚠️ .env pas dans .gitignore — AJOUTER"
```

---

*Créé 2026-04-23 — Claudette scaffold S+1 (Ordre Jarvis 2026-04-23-0843,
amendment GO A+B). Mis à jour à chaque nouveau signup requis.*
