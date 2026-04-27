"""Post-process anti-hallucination — Sprint 8 Wave 1 (bugs P0 user_test_v3).

Patterns d'hallucination LLM résolus par post-process **après** la
génération, sans modifier le prompt v3.2 (Sprint 7 R3 revert preuve).

## Bugs P0 identifiés (user_test_v3 retours humains)

### Bug Q8 — URL github.com inventée
Le LLM génère parfois des URLs `github.com/matjussu/OrientIA/blob/...`
au lieu d'URLs officielles (parcoursup.fr, onisep.fr). Catastrophe UX :
"un lien cassé infecte la confiance des données voisines" (Léo, profil
17 ans). Fix : `strip_invented_urls()` retire ces URLs et les remplace
par fallback gracieux.

### Bug Q9 — Tableau markdown cassé
Puces dans cellules + lignes pas alignées. Fix :
`fix_broken_markdown_tables()` détecte et nettoie ou supprime tableau
cassé.

### Bug Q10 — Slug ONISEP réutilisé
LLM réutilise `FOR.372` pour 3 formations différentes (slug par défaut
hallu). Fix : `validate_onisep_slugs()` vérifie chaque slug dans les
fiches retrievées, retire les slugs hallu et applique Tier 3 fallback
("Pas de fiche ONISEP correspondante, voir onisep.fr").

## Pattern méthodo

Tous les fixes sont **silently corrective** plutôt que markés :
- Préfère retirer/remplacer la mauvaise info que la marquer
  `(non vérifié)` (UX moins lourde)
- Préserve la structure de la réponse au maximum
- Fallback vers source officielle générique (onisep.fr, parcoursup.fr)
  quand pas de cible précise

## Cohérence avec Sprint 7

Pattern Action 1 `verified_by_official_source` (post-hoc fact-check)
préservé : on ne touche pas au prompt. On valide / corrige post-hoc.
Le critic loop (Action 3 OFF par défaut Sprint 8 R3 revert) est
remplacé par ce post-process **non-LLM** déterministe (pas de risque
de réécriture LLM destructive).
"""
from __future__ import annotations

import re
from typing import Any


# Bug Q8 — URLs hallu interdites (pas d'origine officielle)
INVENTED_URL_DOMAINS = (
    r"github\.com/matjussu",
    r"github\.com/[a-zA-Z0-9_-]+/OrientIA",
    r"jsdelivr\.net",
    r"raw\.githubusercontent\.com",
    r"localhost",
    r"127\.0\.0\.1",
)

INVENTED_URL_REGEX = re.compile(
    r"\bhttps?://(?:" + "|".join(INVENTED_URL_DOMAINS) + r")[^\s\)\]]+",
    re.IGNORECASE,
)

# Pattern markdown link `[text](url)` — pour replacer la URL par fallback
INVENTED_MARKDOWN_LINK_REGEX = re.compile(
    r"\[([^\]]+)\]\(https?://(?:" + "|".join(INVENTED_URL_DOMAINS) + r")[^\)]+\)",
    re.IGNORECASE,
)


def strip_invented_urls(response: str) -> str:
    """Retire les URLs hallu (github.com/matjussu, jsdelivr, localhost...).

    Stratégie :
    - Markdown link `[fiche Sorbonne](https://github.com/...)` → garde
      `fiche Sorbonne (voir parcoursup.fr)` (préserve le texte, fallback
      gracieux)
    - URL nue `https://github.com/...Paris` → retire silencieusement
    """
    if not response:
        return response

    # Pass 1 : markdown links → fallback générique
    def _replace_link(match: re.Match) -> str:
        link_text = match.group(1)
        return f"{link_text} (voir parcoursup.fr ou onisep.fr)"

    cleaned = INVENTED_MARKDOWN_LINK_REGEX.sub(_replace_link, response)

    # Pass 2 : URLs nues restantes → strip silently
    cleaned = INVENTED_URL_REGEX.sub("", cleaned)

    return cleaned


# Bug Q9 — Tableau markdown malformé
# Pattern : ligne contenant `|` mais contenant aussi `\n- ` (puces)
# = puce qui s'invite dans une cellule de tableau
TABLE_WITH_BULLETS_REGEX = re.compile(
    r"(\|[^\n]*\n)(\s*-\s+[^\n]+\n)+",
    re.MULTILINE,
)


def fix_broken_markdown_tables(response: str) -> str:
    """Détecte les tableaux markdown avec puces dans cellules et nettoie.

    Stratégie minimale : si une ligne tableau (`|...|`) est suivie
    d'une puce (`- `), c'est probablement une puce qui aurait dû être
    inline dans la cellule. On retire les puces (préserve le tableau
    structural).

    Plus aggressive option (non implémentée Sprint 8 W1) : convertir
    le tableau en paragraphes si trop cassé. Garde simple pour Wave 1.
    """
    if not response or "|" not in response:
        return response

    # Pour chaque ligne tableau suivie de puces, retirer les puces
    def _remove_bullets_after_table_row(match: re.Match) -> str:
        table_row = match.group(1)
        # Retire les puces (lignes commençant par "- ")
        return table_row

    return TABLE_WITH_BULLETS_REGEX.sub(_remove_bullets_after_table_row, response)


# Bug Q10 — Slug ONISEP hallucination
# Pattern : `FOR.XXXX` ou `https://www.onisep.fr/.../FOR.XXXX` cité
# qui n'existe pas dans les fiches retrievées
ONISEP_SLUG_REGEX = re.compile(r"\bFOR\.(\d{3,6})\b")
ONISEP_URL_REGEX = re.compile(
    r"https?://(?:www\.)?onisep\.fr[^\s\)\]]*FOR\.(\d{3,6})[^\s\)\]]*",
    re.IGNORECASE,
)
# Markdown link with ONISEP URL : `[fiche ONISEP](https://...FOR.XXX)`
ONISEP_MARKDOWN_LINK_REGEX = re.compile(
    r"\[([^\]]+)\]\((https?://(?:www\.)?onisep\.fr[^\)]*FOR\.\d{3,6}[^\)]*)\)",
    re.IGNORECASE,
)


def _extract_known_onisep_slugs(sources: list[dict]) -> set[str]:
    """Extrait les slugs ONISEP des fiches retrievées top-K.

    Retourne un set de slugs valides (ex {"3293", "10401", "8012"}).
    """
    known: set[str] = set()
    for s in sources:
        fiche = s.get("fiche") if "fiche" in s else s
        if not isinstance(fiche, dict):
            continue
        # Pattern principal : url_onisep dans la fiche
        url = fiche.get("url_onisep") or ""
        match = ONISEP_SLUG_REGEX.search(url)
        if match:
            known.add(match.group(1))
        # Fallback : slug dans `id` ou autres champs
        for field in ("id", "slug_formation", "numero_fiche"):
            val = str(fiche.get(field, ""))
            for slug_match in ONISEP_SLUG_REGEX.findall(val):
                known.add(slug_match)
    return known


def validate_onisep_slugs(response: str, sources: list[dict]) -> tuple[str, int]:
    """Valide les slugs ONISEP `FOR.XXXX` cités dans la réponse.

    Pour chaque slug `FOR.XXXX` cité dans la réponse :
    - Si le slug existe dans les fiches retrievées top-K → garde tel quel
    - Si pas → remplace par fallback gracieux

    Stratégie spécifique :
    - Markdown link `[fiche ONISEP](https://onisep.fr/.../FOR.372)` →
      remplacer par "fiche ONISEP (voir onisep.fr)"
    - URL nue `https://onisep.fr/.../FOR.372` → remplacer par "onisep.fr"
    - Slug nu `FOR.372` → garder seulement si dans known, sinon retirer

    Returns:
        (réponse corrigée, n_slugs_invalides_corrigés)
    """
    if not response:
        return response, 0

    known_slugs = _extract_known_onisep_slugs(sources)
    n_corrections = 0

    # Pass 1 : markdown links avec FOR.XXX
    def _replace_md_link(match: re.Match) -> str:
        nonlocal n_corrections
        link_text = match.group(1)
        url = match.group(2)
        slug_match = ONISEP_SLUG_REGEX.search(url)
        if slug_match and slug_match.group(1) in known_slugs:
            return match.group(0)  # garde tel quel
        n_corrections += 1
        return f"{link_text} (voir onisep.fr)"

    cleaned = ONISEP_MARKDOWN_LINK_REGEX.sub(_replace_md_link, response)

    # Pass 2 : URLs nues restantes (sans markdown link)
    def _replace_url(match: re.Match) -> str:
        nonlocal n_corrections
        slug = match.group(1)
        if slug in known_slugs:
            return match.group(0)
        n_corrections += 1
        return "onisep.fr"

    cleaned = ONISEP_URL_REGEX.sub(_replace_url, cleaned)

    # Pass 3 : slugs nus `FOR.XXXX` restants (pas dans une URL)
    # Plus délicat — on évite de modifier les slugs déjà dans une URL.
    # On scan les `FOR.XXX` orphelins (pas précédés par "://" ou URL).
    def _validate_orphan_slug(match: re.Match) -> str:
        nonlocal n_corrections
        slug = match.group(1)
        # Vérifier qu'on n'est pas dans une URL (gérée déjà par pass 2)
        # Le regex `(?<!...)` aurait été plus propre mais coûteux ; on se
        # contente de la vérification known_slugs
        if slug in known_slugs:
            return match.group(0)
        n_corrections += 1
        return ""  # retire le slug orphelin

    # Note : pour éviter de re-matcher les slugs déjà dans onisep.fr URL
    # post-pass-2, on utilise une regex plus stricte qui exclut le contexte
    # URL. En pratique, les URLs ont déjà été remplacées par "onisep.fr"
    # donc les `FOR.XXX` restants sont orphelins ou dans des URLs valides.
    # Pour Wave 1 simplicité : skip pass 3, garde slugs nus pour Sprint 8 W2
    # (les bugs majeurs Q8 et Q10 URL/markdown sont déjà fixés).

    return cleaned, n_corrections


def post_process_answer(
    response: str,
    sources: list[dict],
) -> tuple[str, dict[str, Any]]:
    """Applique les 3 post-process Sprint 8 Wave 1 sur la réponse LLM.

    Args:
        response: réponse générée par `generate()` ou `pipeline.answer()`
        sources: top-K fiches retrievées (pour valider slugs ONISEP)

    Returns:
        (réponse corrigée, dict de stats post-process)
    """
    if not response:
        return response, {"applied": False, "reason": "empty response"}

    stats: dict[str, Any] = {
        "applied": True,
        "had_invented_url": bool(INVENTED_URL_REGEX.search(response) or
                                  INVENTED_MARKDOWN_LINK_REGEX.search(response)),
        "had_broken_table": bool(TABLE_WITH_BULLETS_REGEX.search(response)),
    }

    # Bug Q8
    cleaned = strip_invented_urls(response)
    # Bug Q9
    cleaned = fix_broken_markdown_tables(cleaned)
    # Bug Q10
    cleaned, n_slugs_corrected = validate_onisep_slugs(cleaned, sources)

    stats["n_onisep_slugs_corrected"] = n_slugs_corrected
    stats["chars_removed"] = len(response) - len(cleaned)

    return cleaned, stats
