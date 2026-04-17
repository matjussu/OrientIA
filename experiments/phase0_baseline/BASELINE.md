# Phase 0 — Baseline

**Pipeline** : run6_full_stack (443 fiches, ROME decouple + Parcoursup enrichissement, secnumedu_boost=1.0).

## Scores run 6 sur les 10 questions cibles (juge Claude Sonnet 4.5)

| qid | catégorie       | our_rag | mistral_raw | gap  |
|-----|-----------------|---------|-------------|------|
| A1  | biais_marketing | 16      | 17          | -1   |
| B1  | realisme        | 9       | 16          | **-7** |
| B4  | realisme        | 18      | 15          | **+3** |
| C1  | decouverte      | 16      | 11          | **+5** |
| C3  | decouverte      | 12      | 18          | -6   |
| D1  | diversite_geo   | 13      | 15          | -2   |
| D3  | diversite_geo   | 15      | 18          | -3   |
| E1  | passerelles     | 16      | 16          | 0    |
| E4  | passerelles     | 9       | 17          | **-8** |
| H1  | honnetete       | 15      | 15          | 0    |

Moyenne 10 q : `our_rag` 13.9 vs `mistral_raw` 15.8 → gap -1.9 (cohérent avec le plateau global -1.63).

Full run 6 aggregate (pour référence) : `our_rag` 14.28/18, `mistral_raw` 15.91/18.

## Métriques comportementales locales (après régénération Mistral paid tier)

| qid | mots | citations | confessions | handoffs | villes |
|-----|------|-----------|-------------|----------|--------|
| A1  | 771  | 45        | 0           | 1        | 0      |
| B1  | 850  | 13        | 1           | 0        | 3      |
| B4  | 1159 | 40        | 0           | 0        | 8      |
| C1  | 894  | 4         | 0           | 0        | 1      |
| C3  | 857  | 17        | 0           | 0        | 6      |
| D1  | 569  | 11        | 0           | 0        | 3      |
| D3  | 735  | 45        | 4           | 0        | 5      |
| E1  | 1066 | 30        | 0           | 0        | 4      |
| E4  | **355**  | 4         | **3**           | **3**    | **0**      |
| H1  | 628  | 32        | 1           | 0        | 1      |

**Agrégats** : mean words = **788** (cible Phase 1 : ≥1000), total confessions = **9**, total handoffs = **4**, questions avec confession = **4**.

## Patterns de perte observés (échantillons bruts)

**B1 (-7)** ouvre par : *« Ta question porte sur HEC Paris, qui n'apparaît pas dans les fiches fournies. »*
→ Pénalité juge ≈ -7 points alors que la suite est riche (850 mots, 13 citations, stats réelles).

**E4 (-8)** ouvre par : *« les fiches fournies concernent uniquement des formations en cybersécurité. Je ne peux donc pas te répondre précisément sur les filières santé… »* puis enchaîne sur « Te rediriger vers des ressources fiables » et termine en 355 mots — **tronquée par la confession**.

**D3 (-3)** répète 4 fois *« Donnée non disponible dans la fiche (à vérifier sur Parcoursup) »* au lieu de combler avec une estimation en `(connaissance générale)`.

**D1 (-2)** : ne nomme que 3 villes distinctes pour une question explicitement géographique. La règle "≥ 3 régions" du prompt v3 doit renforcer ce comptage.

## Verdict Phase 0

- Le pattern de confession **est bien le gros levier** — E4 et B1 cumulent -15 points à eux seuls.
- D3 montre une variante "confession technique" (`donnée non disponible dans la fiche`) qui n'était pas encore dans la grille — à cibler aussi dans le prompt v3.
- La verbosité est sous-dimensionnée : 788 mots en moyenne vs mistral_raw ~1062 (écart de 26 %).
- La variance inter-questions est énorme (355 à 1159 mots) — E4 est l'outlier qui tire la moyenne vers le bas.

## Cible Phase 1 (success gate pour run judge A)

Sur les mêmes 10 questions régénérées après Phase 1 :

- [ ] `total_confessions_v2 == 0` sur les 10 réponses (anti-confession + Plan A/B/C).
- [ ] `total_handoffs == 0` (pas de redirection vers ONISEP, on propose directement).
- [ ] `mean_word_count >= 1000` (rapprocher de mistral_raw).
- [ ] `distinct_cities >= 3` sur chaque question géographique (D1, D3).
- [ ] 0 régression sur les questions gagnées en baseline (B4, C1).

Si 4/5 atteints → GO run A ($1.15).
