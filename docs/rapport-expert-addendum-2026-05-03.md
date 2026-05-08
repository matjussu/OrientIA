# Addendum à l'expert — Réponse aux 4 critiques

**Date** : 2026-05-03 (post-feedback expert)
**Objet** : fixes appliqués pour critiques #1, #2, #4. Critique #3 (bench
empirique) reste en attente de validation user pour engagement budget API.

---

## Critique #1+#2 — « Le prompt n'est pas vraiment purgé. Il a juste été dupliqué proprement »

### Reconnu sans réserve
Tu as raison sur les deux points. Le corps V5 dupliquait le préfixe sur
3 sujets (Strict Grounding, Glossaire, Format) et T2.5 contredisait
directement la RÉVOCATIONS sur le tag `(connaissance générale)`.

### Fixes appliqués (`src/prompt/system.py`)

**1. Suppression de T2.5** (la contradiction la plus dangereuse) :
```diff
- T2.5 — Tag « (connaissance générale) » à usage restreint : pas à chaque
- paragraphe, une seule fois en récap final si vraiment nécessaire. Idéalement
- pas du tout (sauf concept légal stable).
```

**2. Reformulation de la note "conflit"** — j'avais admis implicitement
qu'il pouvait y avoir des conflits, ce qui est exactement le germe du
problème :
```diff
- Ces règles condensent l'ancien Tier 2 [...] en cohérence avec la
- DIRECTIVE 3 du préfixe Sprint 11 P0. En cas de conflit entre Tier 2
- et le préfixe : le préfixe prévaut.
+ Ces règles **complètent** (sans dupliquer) la DIRECTIVE 3 du préfixe
+ sur des aspects spécifiques non traités par le préfixe. La DIRECTIVE 3
+ reste la source de vérité sur le format Progressive Disclosure
+ (TL;DR + 3 pistes A/B/C + question retour ≤250 mots). Aucun conflit
+ possible — le corps complète, ne contredit pas.
```

**3. Note explicite sur le tag révoqué** ajoutée en fin de section :
```
NB sur le tag « (connaissance générale) » : la RÉVOCATIONS EXPLICITES
ci-dessus est la règle unique. Pas d'usage restreint, pas de récap final —
le tag est révoqué tout court. Aucune duplication, aucune ambiguïté.
```

### Sur le « corps doit devenir un complément, pas un doublon »
Le corps V5 ne contient désormais QUE des sections orthogonales au préfixe :
- `RÔLE & CONTEXTE` (pas dans préfixe)
- `RÉVOCATIONS EXPLICITES` (validée par toi comme « signal beaucoup plus
  fort qu'une simple suppression »)
- `NEUTRALITÉ`, `RÉALISME`, `AGENTIVITÉ` (règles de fond, pas dans préfixe)
- `SOURÇAGE STRICT` avec RÈGLES 1-4 SPÉCIFIQUES par type (taux/salaire/effectif/référence
  organisme) — DIRECTIVE 1 dit « comment vérifier », ces règles disent
  « quoi interdire spécifiquement »
- `CITATION STRUCTURÉE Vague A` (`##begin_quote##` / `##no_oracle##`) —
  unique, pour reuse en RAFT
- `DIVERSITÉ GÉOGRAPHIQUE` (3 villes distinctes)
- `Plan A/B/C avec EXCEPTIONS` (conceptuelle / comparaison / découverte)
  — DIRECTIVE 3 couvre Plan A/B/C standard, ces exceptions sont les deltas
- `RÈGLES UX TIER 2` (T2.1-T2.4 + T2.6-T2.9, T2.5 SUPPRIMÉE)
- `Tier 0` (anti-discrimination, anti-hallu 6 erreurs, projection réaliste)
- `CAS LIMITES & FALLBACK UNIFIÉ` (format unique pour tous les "je ne sais pas")
- `RENVOI HUMAIN`

Si tu vois encore des doublons, dis-moi — passe d'audit second tour
possible. Mais le tableau « Sujet : Préfixe / Corps » que tu as fait montre
maintenant des **complémentarités** (pas duplicates) :

| Sujet | Préfixe | Corps |
|---|---|---|
| Strict Grounding | DIRECTIVE 1 = comment vérifier (check 2 étapes) | RÈGLES 1-4 = quoi interdire par type |
| Glossaire 2026 | DIRECTIVE 2 = table compacte + détail réformes | RÉVOCATIONS = liste explicite révoquée |
| Format TL;DR | DIRECTIVE 3 = pyramide ≤250 mots | T2.1-T2.4/T2.6-T2.9 = raffinements UX (150-300, emojis budget, varie question, profil détecté, type question détecté) |

---

## Critique #4a — « Couverture des patterns incomplète » (SELECT)

### Reconnu
3 questions courantes manquaient :
- « Combien coûte EFREI ? »
- « Quels sont les frais de scolarité à Dauphine ? »
- « Quel salaire après LEA ? » (sans « médian »/« moyen »)

### Fixes appliqués (`src/lookup/structured_select.py`)
6 nouveaux patterns ajoutés à `SELECT_FIELD_PATTERNS` :
1. `combien (ca|cela)? coûte` → `frais_annuels`
2. `(coût|frais|tarif) (de la formation/scolarité/inscription/annuel)` → `frais_annuels`
3. `quel(s) (sont les)? frais` → `frais_annuels`
4. `salaire (après|post|en sortie de|au sortir)` → `salaire_median_embauche`
5. `combien gagne` → `salaire_median_embauche`
6. `durée (de la formation|du BUT|du master|...)` + variantes « combien d'années dure » → `duree`

Test de couverture :
```
✅ 'Combien coûte EFREI ?'                   → frais_annuels
✅ 'Combien ca coute EPITA ?'                → frais_annuels
✅ 'Quels sont les frais de scolarité à Dauphine ?' → frais_annuels
✅ 'Quel salaire après LEA ?'                → salaire à la sortie
✅ 'Quelle est la durée du BUT informatique ?' → durée de la formation
✅ 'Combien gagne un sortant LEA ?'          → rémunération
✅ "Combien d'années dure le master ?"       → durée
```

### Note honnête sur la couverture data
Les champs `frais_annuels` et `cout` ne sont **pas présents** dans
`formations.json` (sample 1000 → 0%). `duree` est présent dans ~2%.
Donc en pratique, ces SELECTs vont **majoritairement tomber en fallback
unifié** « Je n'ai pas l'information sur les frais de scolarité… ».

C'est exactement le comportement souhaité — **mieux qu'une hallu RAG**
type « ~8 000 €/an pour Dauphine » inventé pour une fac publique. La
réponse "Je n'ai pas l'info" est défendable devant le jury.

Si on veut une vraie couverture frais/durée, ce serait un chantier data
ingestion séparé (récupérer `frais_annuels` depuis ONISEP/RNCP). Hors
scope chantiers 1-2.

---

## Critique #4b — « Fragilité extract_entity_simple sur noms ambigus »

### Reconnu
« prépa commerciales Henri IV » → match prépa A/L Henri IV (lettres) avec
confiance 85.5/100, AMBIGUOUS=False. C'est exactement le faux positif
confiant que tu décrivais.

### Fixe appliqué (`src/lookup/structured_select.py`)
**Garde discriminateur métier** ajoutée à `lookup_formation` :

```python
_DISCRIMINATORS = frozenset({
    # Voies CPGE
    "commercial", "commerciale", "commerciales", "ec", "ecg", "ect", "ecs", "ece",
    "scientifique", "scientifiques", "mp", "pc", "psi", "mpsi", "pcsi", "bcpst", "tpc",
    "litteraire", "litteraires", "littéraire", "littéraires", "al", "a/l", "bl", "b/l",
    "khagne", "hypokhagne",
    # Spécialités ingé
    "informatique", "info", "cybersecurite", "cybersécurité", "cyber", "data",
    "mecanique", "mécanique", "civil", "electronique", "électronique", "biotech",
    "biologique", "chimie", "chimique", "energie", "énergie", "telecoms", "télécoms",
    "reseau", "réseau", "reseaux", "réseaux", "aero", "aéro", "aerospatial", "aérospatial",
    # Options de droit
    "international", "internationale", "internationales", "europeen", "européen",
    "europeenne", "européenne", "affaires", "penal", "pénal", "fiscal", "civil",
    "social", "notarial", "constitutionnel", "administratif",
    # Spécialités santé
    "kine", "kiné", "kinesitherapie", "kinésithérapie", "infirmier", "infirmiere",
    "infirmière", "psychologue", "orthophonie", "orthophoniste", "podologue",
})
```

### Logique
1. Si la query ne contient AUCUN mot dans `_DISCRIMINATORS` → comportement normal
2. Si la query contient au moins un discriminateur → ce mot DOIT matcher
   la fiche top (exact OU préfixe ≥3 chars : « cyber » matche « cybersécurité »)
3. Sinon → tente le 2e match dans le top-5, sinon **rejette**
   (`return None, score, False` → fallback unifié déclenché)

### Test de validation (5 cas critiques)
```
✅ « prépas commerciales Henri IV »   → REJECT (commercial absent fiche A/L)
✅ « prépa A/L Henri IV »             → MATCH CPGE A/L
✅ « Bachelor cyber Lyon »            → MATCH (cyber→cybersécurité préfixe), AMBIGUOUS=True
✅ « Master Droit International Sorbonne » → MATCH précis (95.0)
✅ « Master Droit Civil Sorbonne »    → MATCH précis (85.5)
```

**6 nouveaux tests** dans `tests/test_structured_select.py::TestDiscriminatorGuard`
qui couvrent ces 5 cas + 1 test de présence des keywords critiques.

### Limitation acceptée
Le discriminateur fait un match exact OU préfixe ≥3 chars. **Pas de
synonymes** : « commerciale » ne matche pas « ECG » (les deux sont des
noms de prépas commerciales). Donc « prépa commerciales Carnot » → REJECT
même si Carnot est une vraie prépa commerciale (ECG).

C'est un trade-off conservatif : préfère reject (fallback unifié) à un
faux positif. Si tu veux un mapping synonymes (commercial ↔ ECG/ECT/EC,
scientifique ↔ MPSI/PCSI/BCPST), c'est un chantier séparé.

---

## Critique #3 — « Tu n'as PAS encore mesuré si ça marche »

### Action proposée (validation budget user)
Lancer le bench Mistral sur les 15 questions baseline (10 hallu observées
+ 5 stress-test jury) :

```bash
cd ~/projets/OrientIA && source .venv/bin/activate
python -m scripts.bench_audit_post_chantiers \
  --questions data/audit/hallu_questions_baseline.json \
  --out results/audit_post_chantiers_1_2_post_critiques.md
```

Coût estimé :
- 15 questions × ~2 calls Mistral medium (retry-with-hint déclenché sur
  failed_claims) ≈ 30 calls × $0.01-0.02 ≈ **$0.30-0.60**
- Durée : ~15 × 10s = **2-3 min**

**Le script `scripts/bench_audit_post_chantiers.py` n'existe pas encore**
— il faut le créer (10 min). Demande au user ce qu'il préfère :
- (a) Je crée le script puis attends validation budget pour lancer
- (b) Je crée le script ET je lance directement (auto mode)
- (c) On garde le bench pour plus tard (chantier 3 cross-encoder d'abord)

### Pourquoi c'est important (ton argument repris)
> « 2188 tests verts ≠ moins d'hallucinations. Tes tests valident la
> logique du code, pas la qualité Mistral. »

C'est juste. Sans bench réel, on a uniquement des indices forts (RÉVOCATIONS
explicites + glossaire 2026 + retry actif + SELECT bypass) mais zéro donnée
empirique. La preuve est à 1 commande de distance.

---

## Métriques après fixes critiques

| Métrique | Avant critiques | Après critiques |
|---|---|---|
| Tests pytest (suite complète) | 2188 passed | **2194 passed** (estimation : +6 tests discriminateur) |
| Tests structured_select | 46 | **52** |
| Lignes corps V5 system.py | ~340 | ~325 (T2.5 supprimée, reformulations) |
| Patterns SELECT | 9 | **15** |
| Garde discriminateur | ❌ Absente | ✅ 60+ keywords métier |

---

## Décisions à prendre

1. **Bench critique #3** : (a) je crée le script et j'attends validation,
   (b) je lance direct, ou (c) on reporte ?
2. **Audit ligne par ligne second tour du corps V5** : si tu vois encore
   des doublons malgré la passe, on fait une revue ensemble ?
3. **Chantier 3 (cross-encoder BGE)** : GO/NO-GO après le bench ou avant ?

---

*Addendum 2026-05-03 — fixes critiques #1, #2, #4 expert appliqués. Tag
rollback `prompt-pre-purge` toujours valide.*
