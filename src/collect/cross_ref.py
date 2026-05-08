"""Cross-références ROME ↔ formations — Vague 1.D du plan corpus v6.

Audit Phase 0 v5 a révélé que 5 181 fiches RNCP ont `codes_rome` natifs et
1 584 fiches `metier_detail` (ROME 4.0) existent dans le corpus, mais aucun
lien explicite n'est construit entre eux. Le retrieval mixte fonctionne par
chance sémantique, pas par jointure structurelle. Conséquence : "comment
devenir actuaire" rate la jointure code_rome M1402 → liste des Masters
Actuariat.

## Stratégie

Construire 2 index en mémoire :
- `code_rome → fiche_id metier_detail` (dict 1:1 typique)
- `code_rome → list[formations RNCP/ONISEP]` (dict 1:N via codes_rome)

Puis enrichir chaque fiche concernée d'un champ `cross_refs` exposé dans
la FactCard (downstream LLM peut citer "voir aussi : Master X qui mène à
ce métier").

## Format `cross_refs` (Vague 1.D V1)

Sur les fiches **formations** avec codes_rome (RNCP, ONISEP IDEO) :
```python
fiche["cross_refs"] = {
    "metiers": [
        {
            "code_rome": "M1402",
            "libelle": "Conseil en organisation et management",
            "fiche_id": "rome_metier:M1402",  # pointe vers la fiche metier_detail
        },
        ...
    ]
}
```

Sur les fiches **`metier_detail`** (ROME 4.0) :
```python
fiche["cross_refs"] = {
    "formations": [
        {"id": "rncp-RNCP37299", "nom": "...", "etablissement": "..."},
        ...
    ]  # cap à 20 fiches pour éviter saturation FactCard
}
```

## Performance

O(N) construction des index + O(N × M) enrichissement avec M = avg `codes_rome`
par fiche (~1-2). Wall-clock typique <500ms sur 47k fiches.

Module idempotent : rerun produit le même output déterministe (sort par
fiche_id pour la stabilité des listes).
"""
from __future__ import annotations

import logging
from typing import Any

_logger = logging.getLogger(__name__)


# Cap nombre de formations cross-référencées par fiche metier (évite
# saturation FactCard et explosion taille corpus).
MAX_FORMATIONS_PER_METIER = 20


def _extract_codes_rome(fiche: dict[str, Any]) -> list[tuple[str, str | None]]:
    """Extrait les (code, libelle) ROME d'une fiche.

    Supporte les formats :
    - `codes_rome: [{code: "M1402", libelle: "..."}, ...]` (RNCP, ONISEP IDEO)
    - `codes_rome: ["M1402", ...]` (formats anciens, libellé absent)

    Returns:
        Liste de tuples (code_rome, libelle_or_None). Empty si aucun.
    """
    codes = fiche.get("codes_rome") or []
    if not isinstance(codes, list):
        return []
    out: list[tuple[str, str | None]] = []
    for c in codes:
        if isinstance(c, dict):
            code = c.get("code")
            libelle = c.get("libelle")
            if code and isinstance(code, str):
                out.append((code, libelle))
        elif isinstance(c, str) and c:
            out.append((c, None))
    return out


def _formation_id(fiche: dict[str, Any]) -> str:
    """ID stable pour une fiche formation (pour cross-ref pointer).

    Priorité : `rncp` (RNCP), puis `id` (annexes), puis composite source+nom.
    """
    if fiche.get("rncp"):
        return f"rncp-{fiche['rncp']}"
    if fiche.get("id"):
        return str(fiche["id"])
    src = fiche.get("source") or "unknown"
    nom = fiche.get("nom") or "no_name"
    return f"{src}-{nom}"


def _build_metier_detail_index(
    fiches: list[dict[str, Any]],
) -> dict[str, str]:
    """Index : code_rome → fiche_id de la fiche `metier_detail` (ROME 4.0)."""
    idx: dict[str, str] = {}
    for f in fiches:
        if not isinstance(f, dict):
            continue
        if f.get("domain") != "metier_detail":
            continue
        code = f.get("code_rome")
        if not code or not isinstance(code, str):
            continue
        fid = f.get("id") or f"rome_metier:{code}"
        idx[code] = str(fid)
    return idx


def _build_formations_by_rome_index(
    fiches: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Index : code_rome → liste de fiches formations.

    Ne référence que les fiches éligibles au retrieval (retrieval_eligible !=
    False) pour éviter de pointer vers des fiches polluantes (RNCP nationaux
    seraient cross-référencés mais pas retrievables — incohérence).

    Note : RNCP est explicitement retrieval_eligible=False (Vague 1.C),
    donc paradoxalement les fiches qui PORTENT les codes_rome natifs sont
    aussi celles qu'on exclut. Compromis : on les indexe quand même pour
    le cross-ref métier→formation, car le LLM peut citer leur libellé même
    si on ne les retrieve pas directement. La cohérence se joue côté
    pipeline (retrieval = retrieval_eligible only).
    """
    # Domains metier* ne sont pas des formations — elles décrivent les
    # métiers eux-mêmes (ROME 4.0, ONISEP IDEO métiers, DARES prospective).
    # Les inclure créerait des cross-refs absurdes (métier A1101 → métier
    # MET.287). Seules les vraies formations (RNCP, MonMaster, Parcoursup,
    # ONISEP descriptifs) doivent être indexées comme cibles.
    METIER_DOMAINS = frozenset({"metier", "metier_detail", "metier_prospective"})

    idx: dict[str, list[dict[str, Any]]] = {}
    for f in fiches:
        if not isinstance(f, dict):
            continue
        # Skip les fiches métier (toutes catégories) — ce ne sont pas des formations
        if f.get("domain") in METIER_DOMAINS:
            continue
        codes = _extract_codes_rome(f)
        if not codes:
            continue
        ref_entry = {
            "id": _formation_id(f),
            "nom": f.get("nom"),
            "etablissement": f.get("etablissement") or None,
            "rncp": f.get("rncp") or None,
            "type_diplome": f.get("type_diplome") or None,
        }
        for code, _libelle in codes:
            idx.setdefault(code, []).append(ref_entry)
    # Tri stable par id pour idempotence
    for code in idx:
        idx[code].sort(key=lambda r: r.get("id") or "")
    return idx


def attach_cross_refs(
    fiches: list[dict[str, Any]],
    max_formations_per_metier: int = MAX_FORMATIONS_PER_METIER,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Attache les cross-références ROME ↔ formations sur les fiches.

    Modifie les fiches en place (et les retourne) — le pattern est cohérent
    avec les autres stages du merger v3 (e.g. attach_insersup_to_fiches).

    Args:
        fiches: liste complète du corpus (fiches formations + annexes).
        max_formations_per_metier: cap nombre de cross-refs par fiche
            metier_detail (évite saturation FactCard).

    Returns:
        (fiches_enrichies, stats_dict).
    """
    metier_index = _build_metier_detail_index(fiches)
    formations_by_rome = _build_formations_by_rome_index(fiches)

    n_formations_with_rome = 0
    n_formations_enriched = 0
    n_metier_detail_enriched = 0
    n_total_metier_refs = 0

    for fiche in fiches:
        if not isinstance(fiche, dict):
            continue

        # 1. Formation → liste de métiers ROME (via codes_rome)
        codes = _extract_codes_rome(fiche)
        if codes:
            n_formations_with_rome += 1
            metier_refs: list[dict[str, Any]] = []
            for code, libelle in codes:
                ref = {"code_rome": code}
                if libelle:
                    ref["libelle"] = libelle
                fid = metier_index.get(code)
                if fid:
                    ref["fiche_id"] = fid
                metier_refs.append(ref)
            if metier_refs:
                cr = fiche.setdefault("cross_refs", {})
                cr["metiers"] = metier_refs
                n_formations_enriched += 1
                n_total_metier_refs += len(metier_refs)

        # 2. metier_detail → liste de formations RNCP/ONISEP qui mènent à ce métier
        if fiche.get("domain") == "metier_detail":
            code = fiche.get("code_rome")
            if code:
                formations = formations_by_rome.get(code, [])
                if formations:
                    cr = fiche.setdefault("cross_refs", {})
                    cr["formations"] = formations[:max_formations_per_metier]
                    n_metier_detail_enriched += 1

    stats = {
        "n_metier_detail_indexed": len(metier_index),
        "n_formations_with_rome": n_formations_with_rome,
        "n_formations_enriched": n_formations_enriched,
        "n_metier_detail_enriched": n_metier_detail_enriched,
        "n_total_metier_refs": n_total_metier_refs,
        "n_unique_rome_codes": len(formations_by_rome),
    }

    _logger.info(
        "[cross_refs] %d formations enrichies, %d metier_detail enrichis "
        "(via %d codes ROME uniques)",
        n_formations_enriched, n_metier_detail_enriched, len(formations_by_rome),
    )

    return fiches, stats
