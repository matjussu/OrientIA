# Handoff — Rewrite des `text` des fiches annexes du corpus v5 (Phase 3 V2)

> **Pour une autre instance Claude Code** qui n'a aucun contexte sur OrientIA.
> Ce document contient tout ce qu'il faut pour coder, lancer, valider et
> livrer la **vraie fix** au problème de retrieval des corpora annexes
> identifié dans l'ADR-058.

---

## 0. Mission en 1 paragraphe

OrientIA est un système RAG d'orientation post-bac française (Mistral + FAISS).
Le corpus de référence `data/processed/formations_v5.json` contient 47 193
fiches dont **13 417 fiches annexes** (DARES, CROUS, INSEE, ROME 4.0, etc.)
avec un champ `text` actuellement écrit en format **structuré/stat** (ex :
`"CROUS Lyon | 12000 logements | 25 restos U"`). Ce format produit des
embeddings éloignés sémantiquement des questions naturelles d'un lycéen
(ex : *"Combien coûte le logement étudiant CROUS à Lyon ?"*) — d'où mauvais
retrieval. **Ta mission : écrire `scripts/rewrite_annex_texts.py` qui appelle
Claude (Haiku 4.5 via Anthropic Batch API) sur les 13 417 fiches annexes
pour produire un `text` naturel aligné, en préservant 100% des chiffres
sources, puis valider avec re-embed + spot-check + mini-bench.**

---

## 1. Contexte projet OrientIA

### 1.1 C'est quoi

Système RAG (Retrieval-Augmented Generation) qui répond en français à des
questions d'orientation post-bac d'un lycéen :
- *"Je suis en terminale, j'hésite entre prépa et BUT info à Lyon"*
- *"Que fait un actuaire au quotidien ?"*
- *"Quels métiers vont recruter en 2030 ?"*

Stack : Python 3.12, Mistral (gen + embed), FAISS, FastAPI.

### 1.2 Pipeline rapide

10 étapes, dont les 3 critiques pour ce handoff :
1. **Retrieval** : `OrientIAPipeline._retrieve_with_annex_quota` — hybride
   double-index dense (FAISS) + BM25 lexical + RRF fusion (Phase C ADR-058).
2. **Generation** : Mistral Medium avec `SYSTEM_PROMPT_V4_STRICT` (R1-R6).
3. **Validation** : couche c1 (rules) + c2 (corpus_check) + retry-with-hint.

### 1.3 Lecture obligatoire avant de commencer

Dans cet ordre :
1. `docs/ARCHITECTURE_EXPLICATIVE.md` — vue d'ensemble pipeline (15 min)
2. `docs/DECISION_LOG.md` ADR-057 (corpus v5) + ADR-058 (workaround retrieval)
3. `src/rag/pipeline.py:_retrieve_with_annex_quota` — comment les annexes
   sont consommées au runtime
4. `src/rag/bm25_index.py` — BM25 + RRF fusion qu'on garde

### 1.4 Conventions strictes du projet

- **Français** dans tous les commits, docs, commentaires de code
- **TDD** : tests pytest avant code, ou en parallèle (jamais après)
- **ADR append-only** : pour toute décision structurelle, créer un nouvel ADR
  dans `docs/DECISION_LOG.md`. Numérotation continue (dernier en date :
  ADR-058 → ton ADR sera 059)
- **Pas de yes-man** : si tu vois un risque ou une contradiction dans ce
  handoff, signale-le avant d'exécuter
- **Spot-check obligatoire** avant merge (cf `feedback_spot_check_obligatoire.md`
  dans la mémoire) — toujours valider sur des cas réels avant de proclamer
  "ça marche"
- Pas de PR/push sur `main` sans validation explicite Matteo

---

## 2. Le problème à résoudre (cause racine ADR-058)

### 2.1 Symptôme observé

Le spot-check Phase C sur 13 questions ciblées sur les corpora annexes a
montré que **5/13 questions** ne retrouvent pas la fiche annexe attendue
dans le top-5, même après l'introduction de double-index + BM25 + RRF.

Exemples non-résolus restants :
- *"Que fait un actuaire au quotidien ?"* → top-5 ne contient pas la fiche
  ROME 4.0 actuaire
- *"Quelle insertion après un doctorat en chimie ?"* → top-5 ne contient pas
  la fiche `doctorat:chimie:2014` malgré sa présence dans le corpus
- *"Salaire moyen d'un cadre supérieur (PCS 37) ?"* → top-5 sans fiche
  INSEE PCS

### 2.2 Cause racine identifiée

Le pré-processing `text` des fiches annexes est **mal aligné sémantiquement**
avec les questions naturelles. Exemple concret :

**Fiche actuelle ROME 4.0 (`data/processed/rome_metier_corpus.json`)** :
```
"text": "Métier ROME M1402 : Conseil en organisation et management
d'entreprise | Compétences par enjeu : Conseil (Réaliser un audit
organisationnel, Élaborer des préconisations) ; Communication
(Présenter des orientations stratégiques) | Savoirs : Domaines
d'expertise (Méthodes d'analyse stratégique, Théories du management)"
```

→ Vecteur dans la zone sémantique "documentation technique structurée"

**Question naturelle d'un lycéen** :
```
"Que fait un actuaire au quotidien ?"
```

→ Vecteur dans la zone "conversation orientation lycéen"

Ces deux zones sont **éloignées dans l'espace d'embedding Mistral-embed**
peu importe le modèle ou l'index. Pas un bug FAISS, pas un bug du retrieval —
**format texte mal calibré pour embedding**.

### 2.3 Solution Phase 3 V2 (cette mission)

Re-rédaction du `text` des fiches annexes en **paragraphe naturel français**
qui :
- Place le vecteur dans la zone "conseil orientation"
- Préserve 100% des chiffres et faits de la fiche source (ne pas inventer)
- Inclut les entités nommées exactes (codes, noms officiels)
- Ressemble à ce qu'un conseiller d'orientation dirait

Exemple cible pour la fiche ROME M1402 ci-dessus :
```
"text": "Le métier de conseil en organisation et management d'entreprise
(code ROME M1402) consiste à accompagner les entreprises dans
l'optimisation de leur fonctionnement. Au quotidien, un consultant en
organisation réalise des audits, élabore des préconisations stratégiques
et présente des orientations aux dirigeants. Les compétences clés
incluent l'analyse stratégique, la communication et la maîtrise des
théories du management. Ce métier nécessite une solide formation
(souvent bac+5 école de commerce ou ingénieur)."
```

→ Le second vecteur tombe dans la zone "conseil métier post-bac" et
devient retrievable par n'importe quelle question naturelle équivalente
("Que fait un consultant ?", "C'est quoi le métier de conseil en
management ?", "Comment devenir consultant en stratégie ?").

---

## 3. Périmètre — corpora à traiter

### 3.1 Comptage exact

Charger `data/processed/formations_v5.json` (47 193 fiches au total).
Filtrer celles qui ont un champ `domain` non-vide → **13 417 fiches annexes**.

Distribution attendue (vérifier au début du script) :
```
metier_detail (ROME 4.0) :       1 584
metier (ONISEP IDEO + métiers) : 2 150
metier_prospective (DARES) :     1 160
formation_insertion (Inserjeunes lycée pro) : 2 693
competences_certif (RNCP blocs) : 4 891
insertion_pro (InserSup + Doctorat IP) : 608
parcours_bacheliers :              151
crous :                             39
insee_salaire :                     59
apec_region :                       13
territoire_drom :                   16
voie_pre_bac :                      20
financement_etudes :                28
correction_factuelle :               5

TOTAL : 13 417 fiches annexes
```

### 3.2 Schéma input par corpus

Chaque corpus a son schéma. Tu dois lire `data/processed/<nom>_corpus.json`
pour comprendre les champs disponibles. Voici les patterns :

#### `metier_detail` (ROME 4.0)
```json
{
  "id": "rome_metier:M1402",
  "domain": "metier_detail",
  "source": "rome_api_v4",
  "code_rome": "M1402",
  "libelle_metier": "Conseil en organisation et management d'entreprise",
  "competences_par_enjeu": [
    {"enjeu": "Conseil", "competences": ["Réaliser un audit", ...]}
  ],
  "savoirs_par_categorie": [
    {"categorie": "Domaines d'expertise", "savoirs": ["..."]}
  ],
  "url": "https://candidat.francetravail.fr/.../M1402",
  "provenance": {"tier": "tier_1", "source_label": "France Travail ROME 4.0"}
}
```

#### `metier_prospective` (DARES Métiers 2030)
```json
{
  "id": "dares:fap:A0Z",
  "domain": "metier_prospective",
  "code_fap": "A0Z",
  "fap_libelle": "Agriculteurs, éleveurs, sylviculteurs, bûcherons",
  "effectifs_2019_total_milliers": 431.659,
  "creations_destructions_total_milliers": -23.227,
  "departs_fin_carriere_total_milliers": 180.627,
  "postes_a_pourvoir_total_milliers": 157.4,
  "top_3_regions_effectifs": "...",
  "niveau_tension_dominant": "..."
}
```

#### `crous`
```json
{
  "id": "crous_region:lyon",
  "domain": "crous",
  "n_logements_total": 12000,
  "n_restos_total": 36,
  "regions_principales": ["Auvergne-Rhône-Alpes"]
}
```

#### `insee_salaire`
```json
{
  "id": "insee_salaire:cs:37",
  "domain": "insee_salaire",
  "cs_code": "37",
  "cs_libelle": "Cadres administratifs et commerciaux d'entreprise",
  "salaire_median_mensuel": 3400,
  "age_tranche": "40-49 ans",
  ...
}
```

(Les autres corpora suivent le même pattern — schémas disponibles via
`scripts/audit_corpora_schema_compliance.py` qui montre la structure.)

### 3.3 Cas particulier : éviter le re-rewrite des bons textes

Les fiches **ROME 4.0** (`metier_detail`, 1584) sont déjà semi-narratives
(produites par `build_rome_corpus.py`). Le rewrite peut les améliorer mais
priorité plus basse.

Les fiches **vraiment problématiques** (priorité 1) :
- `crous` (39 entrées stat très courtes)
- `insee_salaire` (59 entrées techniques codes PCS)
- `parcours_bacheliers` (151 entrées avec bac/mention/cohorte structurés)
- `apec_region` (13 entrées agrégat)
- `territoire_drom` (16 entrées)
- `voie_pre_bac` (20 entrées)
- `financement_etudes` (28 entrées)

Au total ~310 fiches priorité 1, le reste priorité 2.

Pour ce handoff : **traiter les 13 417 en un seul batch** (économie de
gestion, coût ~$2.5 avec Haiku Batch API). Pas de phasage.

---

## 4. Architecture du script `rewrite_annex_texts.py`

### 4.1 Localisation et signature

Path : `scripts/rewrite_annex_texts.py`

Pattern d'usage standard du projet :
```bash
# Lancement par défaut sur formations_v5.json
python scripts/rewrite_annex_texts.py

# Override pour test sur sample
python scripts/rewrite_annex_texts.py --sample 20

# Override paths
python scripts/rewrite_annex_texts.py \
  --input data/processed/formations_v5.json \
  --output data/processed/formations_v6.json \
  --batch-id custom_batch_001
```

### 4.2 Flow général

```
1. CHARGE corpus v5 (formations_v5.json, 47 193 fiches)
2. FILTRE fiches annexes (domain non-vide → 13 417 fiches)
3. POUR chaque fiche annexe :
   - Extract champs structurés (selon domain)
   - Construit prompt Claude (template par domain ou template générique)
   - Append à la liste batch
4. ENVOIE batch via Anthropic Batch API (Claude Haiku 4.5)
5. POLL le batch status (Anthropic recommande poll toutes les 60s)
6. RÉCUPÈRE les résultats
7. POUR chaque résultat :
   - Valide les garde-fous (chiffres préservés, length OK, no halluci)
   - Si OK : remplace le `text` de la fiche
   - Si KO : log + garde l'ancien text comme fallback
8. SAUVEGARDE dans formations_v6.json (corpus complet : annexes rewrittes
   + 33 776 formations principales inchangées)
9. STATS report : succès/échecs/fallbacks par domain
```

### 4.3 Modules à créer

```
scripts/rewrite_annex_texts.py        — orchestrateur CLI
src/rewrite/                          — nouveau package
├── __init__.py
├── prompts.py                        — templates prompts par domain
├── batch_submitter.py                — submission Anthropic Batch API
├── batch_poller.py                   — polling status batch
├── result_validator.py               — garde-fous post-réponse Claude
└── corpus_assembler.py               — fusion annexes_rewrittes + main
tests/test_rewrite/
├── test_prompts.py
├── test_batch_submitter.py
├── test_result_validator.py
└── test_corpus_assembler.py
```

---

## 5. Spécifications I/O

### 5.1 Input attendu

`data/processed/formations_v5.json` — list[dict] de 47 193 fiches.
Filter par `f.get("domain")` non-vide pour obtenir les 13 417 annexes.

### 5.2 Output cible

`data/processed/formations_v6.json` — list[dict] de 47 193 fiches dont :
- 33 776 fiches main (formations principales) **inchangées** (pas touchées
  par ce script)
- 13 417 fiches annexes **avec leur champ `text` réécrit** + nouveau champ
  `text_original` (préservation pour audit) + nouveau champ
  `provenance.rewritten_at` ("2026-XX-XX") + `provenance.rewriter` ("claude-haiku-4.5")

### 5.3 Format JSON corpus output

Chaque fiche annexe dans `formations_v6.json` doit avoir :
```json
{
  "id": "...",
  "domain": "...",
  "source": "...",
  "text": "<paragraphe naturel rewritten>",
  "text_original": "<text avant rewrite, préservé pour audit>",
  ... autres champs originaux inchangés (codes, libelles, etc.) ...,
  "provenance": {
    "tier": "tier_1",
    "source_label": "...",
    "rewritten_at": "2026-XX-XX",
    "rewriter": "claude-haiku-4.5"
  }
}
```

---

## 6. Prompt design pour Claude

### 6.1 Template générique (à utiliser pour tous les domains)

```python
SYSTEM_PROMPT = """Tu es un expert en orientation académique et professionnelle française.
Tu reçois une fiche issue d'un corpus officiel français (data.gouv.fr,
ONISEP, France Travail, INSEE, MESR, etc.). Ta mission : réécrire le
contenu de cette fiche en un paragraphe naturel français adapté à
l'embedding RAG pour répondre à des questions de lycéens.

## RÈGLES NON-NÉGOCIABLES

### R1 — Préservation des faits
Tu préserves **tous** les chiffres, codes, noms officiels, libellés
exacts présents dans la fiche source. Tu n'inventes rien. Tu n'ajoutes
aucune information non présente. Si un champ est null/vide, tu ne
mentionnes pas le sujet.

### R2 — Format
- Paragraphe unique de 60 à 150 mots (cap dur)
- Français naturel, ton de conseiller d'orientation
- Pas de listes à puces, pas de tableaux, pas de markdown
- Inclut au moins 1 entité nommée exacte (code, ville, nom officiel)
  si présente dans la fiche source

### R3 — Vocabulaire
Tu utilises des mots qu'un lycéen pourrait écrire dans une question
naturelle. Exemples :
- "logement étudiant CROUS" plutôt que "résidence universitaire CNOUS"
- "salaire après diplôme" plutôt que "rémunération post-diplomation"
- "métier de [X]" plutôt que "profession de [X]"

### R4 — Public cible
Tu écris pour un lycéen en terminale ou un étudiant en réorientation,
français, qui pose des questions naturelles sur l'orientation. Pas
pour un statisticien ni un économiste.

### R5 — Pas de "fluff"
Tu ne dis pas "ce métier est passionnant" ni "voici une formation
intéressante". Tu présentes les faits de façon utile, sans jugement.

## FORMAT RÉPONSE

Tu réponds **uniquement** par le paragraphe rewritten, sans
préambule, sans markdown, sans guillemets autour.
"""

USER_PROMPT_TEMPLATE = """Voici la fiche annexe à réécrire (corpus officiel
{source_label}, domain={domain}) :

{fiche_json_serialized}

Réécris son contenu en un paragraphe naturel français (60-150 mots) qui
respecte les 5 règles. Préserve tous les chiffres et entités nommées."""
```

### 6.2 Few-shot examples

À inclure dans le prompt si tests initiaux montrent des dérives. Format :
```python
FEW_SHOT_EXAMPLES = [
    {
        "input": {"id": "crous_region:lyon", "domain": "crous",
                  "n_logements_total": 12000, "n_restos_total": 36,
                  "regions_principales": ["Auvergne-Rhône-Alpes"]},
        "output": "Le CROUS de Lyon gère le logement étudiant et la "
                  "restauration universitaire pour les étudiants de la "
                  "région Auvergne-Rhône-Alpes. Il propose 12 000 "
                  "logements en résidences universitaires et 36 points de "
                  "restauration (cafétérias, restos U). Les étudiants "
                  "boursiers ont accès à des tarifs réduits. Pour les "
                  "étudiants à Lyon, Villeurbanne et leurs alentours qui "
                  "cherchent à se loger ou se restaurer pendant leurs études."
    },
    {
        "input": {"id": "rome_metier:M1402", "domain": "metier_detail",
                  "code_rome": "M1402",
                  "libelle_metier": "Conseil en organisation et management d'entreprise",
                  "competences_par_enjeu": [
                      {"enjeu": "Conseil", "competences": ["Réaliser un audit", "Élaborer des préconisations"]}
                  ]},
        "output": "Le métier de conseil en organisation et management "
                  "d'entreprise (code ROME M1402) consiste à accompagner "
                  "les entreprises dans l'optimisation de leur "
                  "fonctionnement. Au quotidien, un consultant en "
                  "organisation réalise des audits organisationnels et "
                  "élabore des préconisations stratégiques. Ce métier "
                  "exige des compétences en analyse stratégique et en "
                  "communication. Il est généralement accessible avec un "
                  "bac+5 (école de commerce ou ingénieur), souvent suivi "
                  "d'une expérience en cabinet de conseil."
    },
]
```

### 6.3 Modèle recommandé

**Claude Haiku 4.5** (`claude-haiku-4-5-20251001`) via Anthropic Batch API :
- 50% off vs API directe
- Résultats sous 24h (batch)
- Coût estimé total : **~$2.5** pour 13 417 fiches
- Tokens estimés : ~500 input + 200 output par fiche × 13 417 = 6.7M input
  + 2.7M output

Si Haiku produit des hallucinations sur sample test, escalade vers Sonnet 4.6
(coût × 12, mais qualité supérieure).

---

## 7. Garde-fous obligatoires

Le `result_validator.py` doit appliquer ces vérifications **avant** de
remplacer le `text` original de la fiche. Si un garde-fou échoue → garder
l'ancien `text` + log warning.

### G1 — Length cap

```python
def validate_length(rewritten_text: str) -> bool:
    """Le paragraphe doit faire entre 60 et 200 mots (cap souple à 200)."""
    n_words = len(rewritten_text.split())
    return 60 <= n_words <= 200
```

### G2 — Préservation chiffres

Pour chaque chiffre du texte source (extracted via regex `\d+`), vérifier
qu'il apparaît dans le texte rewritten ou qu'il est absent légitimement
(champ null dans la fiche).

```python
def validate_numbers_preserved(fiche_source: dict, rewritten_text: str) -> bool:
    """Vérifie que tous les chiffres significatifs (>=10) de la fiche
    sont présents dans le rewritten. Tolère arrondis (12000 → '12 000')."""
    import re
    source_numbers = set()
    for v in _flatten_dict_values(fiche_source):
        if isinstance(v, (int, float)) and abs(v) >= 10:
            source_numbers.add(int(v))
    # Tolère les formats "12 000" et "12000"
    rewritten_numbers = set(int(m) for m in re.findall(r"\d{2,}", rewritten_text.replace(" ", "")))
    missing = source_numbers - rewritten_numbers
    return len(missing) == 0
```

### G3 — Préservation entités nommées

Vérifier que les libellés / codes / noms officiels présents dans la fiche
apparaissent dans le rewritten :
```python
def validate_entities_preserved(fiche_source: dict, rewritten_text: str) -> bool:
    """Pour les champs identifiants (code_rome, code_fap, cs_code, libelle_*),
    vérifier qu'ils apparaissent dans le rewritten."""
    must_have = []
    for key in ("code_rome", "code_fap", "cs_code", "libelle_metier",
                "libelle", "fap_libelle"):
        v = fiche_source.get(key)
        if v and isinstance(v, str) and len(v) >= 2:
            must_have.append(v)
    rewritten_lower = rewritten_text.lower()
    missing = [e for e in must_have if e.lower() not in rewritten_lower]
    return len(missing) == 0
```

### G4 — Anti-hallu lexical

Liste noire de mots-clés indiquant une potentielle hallucination Claude :
```python
HALLU_REDFLAGS = [
    "généralement", "souvent", "il est important",
    "il est crucial", "il convient", "généralement reconnu",
    # Ces formulations sont OK ponctuellement mais leur présence
    # avec >2 occurrences dans <150 mots = sur-extrapolation Claude
]

def validate_anti_hallu(rewritten_text: str) -> bool:
    """Si >2 mots de la liste rouge → flag (Claude extrapole trop)."""
    n_red = sum(1 for w in HALLU_REDFLAGS if w in rewritten_text.lower())
    return n_red <= 2
```

### G5 — Format markdown / structuré refusé

```python
def validate_format(rewritten_text: str) -> bool:
    """Pas de markdown, pas de listes à puces, pas de \\n multiple."""
    if "**" in rewritten_text or "##" in rewritten_text:
        return False
    if rewritten_text.count("\n\n") > 0:
        return False
    if rewritten_text.count("- ") > 2:
        return False
    return True
```

### Pipeline garde-fous

```python
def is_rewrite_acceptable(fiche_source: dict, rewritten_text: str) -> tuple[bool, list[str]]:
    """Returns (accepted, issues_list)."""
    issues = []
    if not validate_length(rewritten_text):
        issues.append("length out of [60, 200] words")
    if not validate_numbers_preserved(fiche_source, rewritten_text):
        issues.append("missing numbers from source")
    if not validate_entities_preserved(fiche_source, rewritten_text):
        issues.append("missing named entities from source")
    if not validate_anti_hallu(rewritten_text):
        issues.append("anti-hallu redflags >2")
    if not validate_format(rewritten_text):
        issues.append("invalid format (markdown/lists)")
    return (len(issues) == 0, issues)
```

---

## 8. Tests à écrire (pytest)

Rejoindre la convention du projet : `tests/test_rewrite/`.

### tests/test_rewrite/test_prompts.py
- `test_user_prompt_includes_fiche_json` — vérifier serialization
- `test_system_prompt_contains_5_rules` — règles R1-R5 présentes

### tests/test_rewrite/test_result_validator.py
- `test_g1_length_validation` — fixtures texte trop court / trop long / OK
- `test_g2_numbers_preserved` — fixtures avec chiffres présents / manquants
- `test_g3_entities_preserved` — code_rome présent vs absent dans rewritten
- `test_g4_anti_hallu` — texte avec >2 redflags vs propre
- `test_g5_format_no_markdown` — texte avec `**` / `##` / liste rejeté
- `test_pipeline_acceptable` — combine les 5 G + assertion sur issues_list

### tests/test_rewrite/test_corpus_assembler.py
- `test_assembler_preserves_main_fiches_unchanged` — les 33 776 main
  ne doivent jamais être modifiées
- `test_assembler_replaces_annex_text_when_accepted` — quand rewrite OK
- `test_assembler_keeps_original_when_rejected` — fallback préservé
- `test_assembler_adds_text_original_field` — préservation pour audit

### tests/test_rewrite/test_batch_submitter.py (avec mock Anthropic API)
- `test_submit_batch_creates_anthropic_batch_object`
- `test_submit_batch_handles_empty_fiches_gracefully`
- `test_submit_batch_chunks_if_more_than_max_per_batch` (Anthropic cap = 10000 par batch)

---

## 9. Lancement batch (Anthropic Batch API)

### 9.1 Architecture batch

Anthropic Batch API permet de soumettre jusqu'à 10 000 requêtes par batch
avec 50% de réduction. 13 417 fiches → **2 batches** :
- Batch 1 : fiches 1-10 000
- Batch 2 : fiches 10 001-13 417

### 9.2 Code submitter (squelette)

```python
from anthropic import Anthropic

def submit_batch(fiches: list[dict], anthropic_client: Anthropic) -> str:
    """Submit un batch et retourne le batch_id."""
    requests = [
        {
            "custom_id": fiche["id"],  # tracker pour matcher result → fiche
            "params": {
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 400,
                "system": SYSTEM_PROMPT,
                "messages": [
                    {"role": "user",
                     "content": USER_PROMPT_TEMPLATE.format(
                         source_label=fiche.get("source", "?"),
                         domain=fiche["domain"],
                         fiche_json_serialized=json.dumps(fiche, ensure_ascii=False, indent=2),
                     )}
                ],
            },
        }
        for fiche in fiches
    ]
    batch = anthropic_client.messages.batches.create(requests=requests)
    return batch.id
```

### 9.3 Polling

Anthropic recommande poll toutes les 60s. Pas de webhook disponible.
Batch typique terminé en 1-6h pour Haiku.

```python
def poll_batch_until_complete(batch_id: str, anthropic_client: Anthropic, poll_interval_s: int = 60):
    """Bloque jusqu'à ce que le batch soit `ended`."""
    import time
    while True:
        batch = anthropic_client.messages.batches.retrieve(batch_id)
        if batch.processing_status == "ended":
            return batch
        time.sleep(poll_interval_s)
```

### 9.4 Récupération résultats

```python
def fetch_batch_results(batch_id: str, anthropic_client: Anthropic):
    """Stream les résultats du batch terminé."""
    results = []
    for entry in anthropic_client.messages.batches.results(batch_id):
        if entry.result.type == "succeeded":
            text = entry.result.message.content[0].text
            results.append({
                "custom_id": entry.custom_id,
                "rewritten_text": text,
                "input_tokens": entry.result.message.usage.input_tokens,
                "output_tokens": entry.result.message.usage.output_tokens,
            })
        else:
            results.append({
                "custom_id": entry.custom_id,
                "error": entry.result.error if entry.result.type == "errored" else "unknown",
            })
    return results
```

### 9.5 Doc Anthropic

Réf officielle : https://docs.claude.com/en/api/creating-message-batches

---

## 10. Validation post-batch

Workflow obligatoire :

### 10.1 Sample manuel sur 50 fiches AVANT le batch complet

```bash
python scripts/rewrite_annex_texts.py --sample 50 --output /tmp/sample_v6.json
```

Vérifier manuellement que :
- Les rewrittes ressemblent à un texte d'orientation naturel
- Aucune hallu factuelle (vérifier 5-10 fiches contre leur source)
- Le tone est cohérent

Si OK → lancer le batch complet.
Si KO → ajuster prompt, re-sample, re-vérifier.

### 10.2 Garde-fous automatiques sur le batch complet

Le `result_validator.py` filtre automatiquement les rewrittes qui échouent
les 5 garde-fous. Stats à logger :

```python
stats = {
    "n_total": 13417,
    "n_succeeded": 12_xxx,           # objectif: ≥95% (≥12 700)
    "n_rejected_length": ...,
    "n_rejected_numbers_missing": ...,
    "n_rejected_entities_missing": ...,
    "n_rejected_anti_hallu": ...,
    "n_rejected_format": ...,
    "n_kept_original_as_fallback": ...,  # ceux qui ont raté les guard-rails
}
```

Si taux acceptation < 90% → investigation du prompt avant le re-embed.

---

## 11. Re-embed FAISS

Une fois `formations_v6.json` produit :

```bash
ORIENTIA_CORPUS_PATH=data/processed/formations_v6.json \
ORIENTIA_INDEX_PATH=data/embeddings/formations_v6.index \
python -m scripts.rebuild_faiss_index
```

Coût Mistral : ~$2 (47 193 fiches × ~500 tokens avg).
Wall-clock : ~12-15 min.

---

## 12. Triple-gate validation (avant promotion v6)

Reproduire le triple-gate Phase C (cf `scripts/audit_phase_0_v5.py`,
`scripts/spot_check_v5.py`, `scripts/mini_bench.py`).

### Gate 1 — Audit Phase 0 v6
```bash
python scripts/audit_phase_0_v5.py --corpus data/processed/formations_v6.json
```
Vérifier que les métriques restent vertes/orange (pas de rouge nouveau).

### Gate 2 — Mini-bench v4.1
```bash
ORIENTIA_CORPUS_PATH=data/processed/formations_v6.json \
ORIENTIA_INDEX_PATH=data/embeddings/formations_v6.index \
python scripts/mini_bench.py --phase strict_v4 \
  --out results/mini_bench/v6_phase_3_strict_v4.json
```

Critères vert :
- `flagged ≤ 1` (vs 1 baseline v5 phase_c)
- `avg_honesty ≥ 0.987` (vs 0.987 baseline v5 phase_c)
- `avg_latency ≤ 9s`

### Gate 3 — Spot-check 13 questions
```bash
ORIENTIA_CORPUS_PATH=data/processed/formations_v6.json \
ORIENTIA_INDEX_PATH=data/embeddings/formations_v6.index \
python scripts/spot_check_v5.py
```

**Critère ouvre la promotion v6** : ≥ 11/13 questions avec domain attendu
dans top-5 (vs 8/13 actuel v5 phase_c).

---

## 13. Décision GO/NO-GO promotion v6

**GO promotion v6 → production** si :
- Gate 1 vert/orange (pas de régression structurelle)
- Gate 2 ≤ 1 flagged + honesty ≥ 0.987
- Gate 3 ≥ 11/13 spot-check

**NO-GO** si :
- Régression mini-bench > 1 flagged supplémentaire
- Spot-check < 11/13 (gain insuffisant pour justifier ré-embed)
- Tau acceptation rewrite < 90% (qualité Claude insuffisante)

Si NO-GO → analyse + adjustement prompt + re-batch (coût $2.5 supplémentaire).

Si GO → procédure promotion identique à Phase D :
```bash
mkdir -p data/archive/2026-XX-XX
mv data/processed/formations.json data/archive/2026-XX-XX/formations_v5.json
mv data/embeddings/formations.index data/archive/2026-XX-XX/formations_v5.index
cp data/processed/formations_v6.json data/processed/formations.json
cp data/embeddings/formations_v6.index data/embeddings/formations.index
```

Puis ADR-059 dans `docs/DECISION_LOG.md` actant la promotion v6.

---

## 14. Coût total estimé

| Étape | Coût |
|---|---|
| Sample test 50 fiches (Haiku direct API) | ~$0.05 |
| Batch complet 13 417 fiches (Haiku Batch API 50% off) | ~$2.5 |
| Re-embed FAISS Mistral | ~$2 |
| Spot-check (~13 questions × pipeline call) | ~$0.5 |
| Mini-bench Gate 2 (~23 questions) | ~$2.5 |
| **Total Phase 3 V2** | **~$7.5** |

---

## 15. Effort estimé

| Tâche | Durée |
|---|---|
| Lecture handoff + setup | 30 min |
| Lecture code projet (pipeline.py, bm25_index.py, ADR-058) | 1h |
| Code `prompts.py` + `result_validator.py` + tests | 3h |
| Code `batch_submitter.py` + `batch_poller.py` + tests | 2h |
| Code `corpus_assembler.py` + tests | 1h |
| Code `scripts/rewrite_annex_texts.py` orchestrateur | 1h |
| Sample test 50 fiches + tweaks prompt | 1h |
| Lancement batch complet (13 417) | nuit (6-12h passive) |
| Re-embed FAISS | 15 min |
| Triple-gate validation | 2h |
| ADR-059 + commit + promotion v6 | 1h |
| **Total dev actif** | **~12h ≈ 1.5 jour** |
| **Total wall-clock** | **2 jours** (incluant nuit batch) |

---

## 16. Ressources clés

### Documentation projet
- `docs/ARCHITECTURE_EXPLICATIVE.md` — vue d'ensemble pipeline
- `docs/DECISION_LOG.md` — ADR-057, ADR-058 (lecture obligatoire)
- `docs/AUDIT_PHASE_0.md` — état corpus pré-v5
- `~/.claude/plans/parfait-pour-les-adr-quiet-pebble.md` — plan corpus v5

### Code de référence à lire
- `src/rag/pipeline.py:_retrieve_with_annex_quota` (Phase C hybride)
- `src/rag/bm25_index.py` (BM25 + RRF — pattern modulaire à suivre)
- `src/collect/build_rome_corpus.py` (pattern transformer texte structuré)
- `scripts/spot_check_v5.py` (test framework)

### API Anthropic Batch
- Doc officielle : https://docs.claude.com/en/api/creating-message-batches
- Modèle recommandé : `claude-haiku-4-5-20251001`
- Cap par batch : 10 000 requests
- Latence batch : 1-24h (typique 1-6h)
- Discount : 50% vs API direct

### Variables d'environnement requises
- `ANTHROPIC_API_KEY` (déjà présent dans `.env` du projet, cf `src/config.py`)
- `MISTRAL_API_KEY` (pour re-embed FAISS)

---

## 17. Communication avec Matteo

- **Pas de PR/push sur main** sans validation explicite
- **Update vault Obsidian** quand le batch est lancé : laisser une note dans
  `~/obsidian-vault/05-Journal/YYYY-MM-DD.md` avec le statut
- **Spot-check obligatoire** avant le merge final (cf
  `feedback_spot_check_obligatoire.md`)
- En cas de blocage : message peer-claude vers Jarvis (peer ID dans
  `~/projets/CLAUDE.md`) ou ping Matteo via Telegram

---

## 18. Checklist livraison

- [ ] Code écrit, tests pytest passants (≥30 nouveaux tests)
- [ ] Sample 50 fiches validé manuellement
- [ ] Batch complet 13 417 fiches lancé et terminé
- [ ] Taux acceptation rewrite ≥ 95%
- [ ] `formations_v6.json` produit
- [ ] `formations_v6.index` re-embeddé
- [ ] Gate 1 audit Phase 0 v6 : vert/orange
- [ ] Gate 2 mini-bench : ≤ 1 flagged, honesty ≥ 0.987
- [ ] Gate 3 spot-check : ≥ 11/13
- [ ] ADR-059 rédigé et committé
- [ ] Promotion v6 → production faite (cp + archive)
- [ ] Suite globale tests : 0 failed
- [ ] Note journal Obsidian mise à jour
- [ ] Matteo notifié du résultat (Telegram)

---

*Handoff rédigé 2026-05-08 par instance Claude Code post-Phase C corpus v5.
Pour questions/clarifications, lire ADR-058 d'abord — il contient la
plupart des réponses.*
