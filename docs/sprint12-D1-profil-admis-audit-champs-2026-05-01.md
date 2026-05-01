# Sprint 12 D1 — Audit champs profil_admis

**Date** : 2026-05-01
**Branche** : `feat/sprint12-D1-profil-admis-expose-rag`
**Référence ordre** : `2026-05-01-1659-claudette-orientia-sprint12-D1-profil-admis-expose-rag` (S1)
**Auteur** : Claudette
**Source** : `data/processed/formations_unified.json` (55 606 formations).

---

## Couverture

| Métrique | Valeur |
|---|---|
| Fiches total corpus | 55 606 |
| Fiches avec champ `profil_admis` (dict non-null) | **19 489 (35.0 %)** |
| Fiches avec `profil_admis` rempli (≥ 1 stat non-zéro) | **10 502 (18.9 %)** |

**Implication design** : un grand nombre de fiches ont un dict `profil_admis` placeholder rempli de zéros (Parcoursup ne remonte pas la donnée pour la formation). Le formatter de la S2 devra **skip les zéros et les sous-champs vides** au lieu de les dumper, pour ne pas polluer les embeddings avec du bruit "0% admis" non-informatif.

---

## Inventaire 7 sous-champs

| Sous-champ | Type | Couverture (% des présents avec stat non-zéro) |
|---|---|---|
| `acces_pct` | dict `{general, techno, pro}` (% taux d'accès par type bac) | 53.7 % |
| `bac_type_pct` | dict `{general, techno, pro}` (% admis par type bac) | 52.9 % |
| `neobacheliers_pct` | scalaire (% néobacheliers parmi admis) | 52.9 % |
| `mentions_pct` | dict `{tb, b, ab, sans}` (% admis par mention) | 52.9 % |
| `origine_academique_idf_pct` | scalaire (% origine académique Île-de-France) | 52.2 % |
| `femmes_pct` | scalaire (% femmes parmi admises) | 50.7 % |
| `boursiers_pct` | scalaire (% boursiers parmi admis) | 47.4 % |

Les 7 sous-champs sont quasi-toujours présents ensemble quand `profil_admis` est rempli (couvertures resserrées 47-54 %). Pas de séparation de feature flags — soit la fiche a tous les sous-champs, soit aucun.

---

## Sample concret représentatif

Formation **Bachelor Cybersécurité et Ethical Hacking — EFREI Bordeaux** :

```json
"profil_admis": {
  "mentions_pct": {"tb": 4.0, "b": 12.0, "ab": 29.0, "sans": 54.0},
  "bac_type_pct": {"general": 71.0, "techno": 17.0, "pro": 12.0},
  "acces_pct":    {"general": 79.0, "techno": 14.0, "pro": 6.0},
  "boursiers_pct": 21.0,
  "femmes_pct": 10.0,
  "neobacheliers_pct": 77.0,
  "origine_academique_idf_pct": 58.0
}
```

Format texte cible pour `fiche_to_text()` (non-JSON, structuré naturel pour embedding) :

> ## Profil des admis (Parcoursup 2025)
> Mentions au bac : 4 % très bien, 12 % bien, 29 % assez bien, 54 % sans mention.
> Type de bac : 71 % général, 17 % techno, 12 % pro.
> Taux d'accès par profil : 79 % pour bac général, 14 % pour bac techno, 6 % pour bac pro.
> 21 % boursiers, 10 % de femmes, 77 % néobacheliers, 58 % origine académique Île-de-France.

---

## Gotchas matching à anticiper S2

1. **Sous-champ vide** : `profil_admis = {}` ou `profil_admis = {"mentions_pct": {"tb":0, "b":0, ...}, ...}` (tout zéro). Détecter et skip — pas de section `## Profil des admis` dans le texte généré.
2. **Sous-champ partiel** : un seul dict imbriqué rempli (e.g. `mentions_pct` non-zéro mais `bac_type_pct` tout zéro). Inclure ce qui est meaningful, omettre le reste.
3. **Scalaires à 0.0** : `boursiers_pct: 0.0` peut être "vrai 0" (formation sans boursiers admis) OU placeholder. Dans le doute, skip si == 0 pour éviter le bruit "0% boursiers" qui flagge artificiellement.
4. **acces_pct vs taux_acces_parcoursup_2025** : `acces_pct.general` (= taux d'accès des bacs généraux à cette formation) est différent du `taux_acces_parcoursup_2025` (= taux d'accès global). Les deux sont déjà exposés dans v3 actuel pour le 2e (cf docstring). D1 ajoute le profil-spécifique.
5. **Formats nombre** : valeurs stockées en float (`27.0` pas `0.27` ni `"27%"`). Render `f"{val:.0f} %"` pour intégers, `f"{val:.1f} %"` si décimale significative.

---

## Suite (S2 — modif fiche_to_text)

- Helper privé `_format_profil_admis(profil_admis: dict | None) -> str | None` qui retourne :
  - `None` si profil_admis absent ou tous zéros
  - une chaîne `## Profil des admis (Parcoursup 2025)\n...` sinon
- Appel additif depuis `fiche_to_text(fiche)` quand le helper retourne non-None
- 5-10 tests unitaires : riche complet / partiel mentions seules / partiel bac_type seul / tous zéros (skip) / champ absent (skip) / valeurs limites (`100 %`, `0.5 %`)
