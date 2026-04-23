# TODO Matteo — Signups APIs externes (S+1 Axe 1 data foundation)

**Contexte** : Claudette a scaffoldé les clients API (PR à venir). Pour que
l'ingestion puisse démarrer dès J+1/J+2, 2 signups à faire dès que tu as 15min
devant l'interface web. Aucune étape bloquée chez toi n'est bloquée chez
Claudette — le code attend juste les credentials dans `.env`.

Ordre recommandé : 1 puis 2 (1 est le plus long à activer côté France Travail).

---

## 1. France Travail API — ROME 4.0 (D3 ingestion débouchés live)

**Durée estimée** : 8-10 min signup + 24-48h activation côté France Travail.

**URL** : https://francetravail.io

### Étapes

1. **Créer un compte développeur** sur https://francetravail.io/inscription
   - Email pro (matteolepietre@gmail.com suffit)
   - Mot de passe fort + stocker dans ton gestionnaire
   - Valider par l'email de confirmation
2. **Se connecter** puis aller dans le dashboard "Mes applications"
3. **Créer une app** :
   - Nom : `OrientIA — Assistant orientation INRIA`
   - Description courte : `Système RAG d'orientation académique française pour le concours INRIA AI Grand Challenge`
   - Callback URL : laisser vide (client_credentials flow, pas user-auth)
4. **Cocher les scopes** nécessaires :
   - ✅ `api_rome-metiersv1` (Référentiel des métiers ROME 4.0)
   - ✅ `api_rome-fiches-metiersv1` (Fiches métiers détaillées)
   - ✅ `nomenclatureRome` (Métadonnées nomenclature)
   - ⚪ (optionnel S+2) `api_labonnealternancev1` si on ajoute ingestion alternance
5. **Soumettre la demande d'accès**. France Travail review la demande sous 24-48h
   (parfois plus rapide en semaine). Tu reçois un email de validation.
6. **Récupérer `client_id` + `client_secret`** dans le dashboard une fois activé.
7. **Ajouter dans `~/projets/OrientIA/.env`** :
   ```bash
   FT_CLIENT_ID=<ton_client_id>
   FT_CLIENT_SECRET=<ton_client_secret>
   ```
8. **Ping Jarvis sur Telegram** : "clé France Travail active" → il dispatch
   à Claudette qui lance l'ingestion D3.

### Notes
- Le flow `client_credentials` n'a pas de refresh token — le client OrientIA
  régénère l'access_token à chaque expiration (~20 min) de façon automatique.
- Rate limit France Travail : ~5 req/s par app sur ROME 4.0. Le client
  `src/collect/rome_api.py` respecte déjà 180 RPM par défaut (marge 40%).

---

## 2. ONISEP OpenData API (D2 enrichissement formations)

**Durée estimée** : 5 min signup, activation immédiate (pas de review).

**URL** : https://opendata.onisep.fr

### Étapes

1. **Créer un compte** sur https://opendata.onisep.fr/inscription
   - Email pro
   - Mot de passe fort
2. **Valider l'email** de confirmation
3. **Se connecter** → onglet "Mes applications"
4. **Créer une application** :
   - Nom : `OrientIA INRIA`
   - Description : `Système RAG orientation`
5. **Récupérer `Application-ID`** (pas d'OAuth2 côté ONISEP — juste un
   header `Application-ID` + login par email/password pour token Bearer).
6. **Ajouter dans `~/projets/OrientIA/.env`** :
   ```bash
   ONISEP_EMAIL=<ton_email_onisep>
   ONISEP_PASSWORD=<ton_mot_de_passe_onisep>
   ONISEP_APP_ID=<ton_application_id>
   ```
7. **Ping Jarvis** : "clé ONISEP active" → Claudette lance D2 ingestion.

### Notes
- Le code `src/collect/onisep.py` existe déjà — il attend juste ces 3 env vars.
- ONISEP expose aussi un endpoint public sans auth (`_fetch_formations_public`)
  mais limité à ~500 résultats par query et pas de champs enrichis.

---

## 3. (Optionnel, décision S+2) Reddit OAuth — RAFT dataset génération γ

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
