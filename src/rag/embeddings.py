from mistralai.client import Mistral


EMBED_MODEL = "mistral-embed"


def _safe_pct(val, arrondi: bool = True) -> str | None:
    """Convertit un ratio [0,1] en pourcentage string, robuste aux NaN.

    Retourne None si val est None, NaN, ou non-convertible. Utilise
    `arrondi=True` par défaut pour stabilité retrieval (85.23% → 85%).
    """
    if val is None:
        return None
    import math
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return f"{int(round(f * 100))}%" if arrondi else f"{f * 100:.1f}%"
    except (ValueError, TypeError):
        return None


def _format_insertion_pro(ip: dict) -> str | None:
    """Formate le dict `insertion_pro` en verbatim embedding-friendly.

    Supporte 2 schémas hétérogènes (v3 ADR-046-bis) :

    **Schéma Céreq** (source='cereq', 32 704 fiches, majoritairement Parcoursup/
    MonMaster enrichies par `attach_cereq_insertion`) :
        {taux_emploi_3ans, taux_emploi_6ans, taux_cdi, salaire_median_embauche,
         source, cohorte}

    **Schéma CFA** (source='inserjeunes_cfa', 11 314 fiches apprentissage) :
        {taux_emploi_6m/12m/18m/24m, taux_emploi_6m_attendu,
         valeur_ajoutee_emploi_6m, taux_contrats_interrompus,
         part_poursuite_etudes, part_emploi_6m, part_autres_situations,
         source, annee}

    Retourne une string concaténée (verbatim narratif) ou None si pas de data
    exploitable. Objectif : rendre les stats **retrievables** via l'embedding
    (au lieu d'être ignorées comme dans la baseline v2).
    """
    if not isinstance(ip, dict):
        return None
    source = (ip.get("source") or "").lower()
    fragments: list[str] = []

    # Schéma Céreq (insertion à 3 et 6 ans, agrégé par niveau+domaine)
    if "taux_emploi_3ans" in ip or "taux_emploi_6ans" in ip:
        cohorte = ip.get("cohorte") or "cohorte récente"
        t3 = _safe_pct(ip.get("taux_emploi_3ans"))
        t6 = _safe_pct(ip.get("taux_emploi_6ans"))
        tcdi = _safe_pct(ip.get("taux_cdi"))
        sal = ip.get("salaire_median_embauche")
        if t3:
            fragments.append(f"taux emploi 3 ans : {t3}")
        if t6:
            fragments.append(f"taux emploi 6 ans : {t6}")
        if tcdi:
            fragments.append(f"taux CDI : {tcdi}")
        if sal is not None and isinstance(sal, (int, float)):
            import math
            sal_f = float(sal)
            if not math.isnan(sal_f):
                fragments.append(f"salaire médian embauche : {int(sal_f)}€")
        if fragments:
            return f"Insertion pro (source Céreq, {cohorte}) : " + " — ".join(fragments)

    # Schéma CFA Inserjeunes (horizons 6/12/18/24 mois, apprentissage)
    if "taux_emploi_6m" in ip or "valeur_ajoutee_emploi_6m" in ip:
        annee = ip.get("annee") or "cumul récent"
        horizons: list[str] = []
        for h_key, h_lib in (
            ("taux_emploi_6m", "6 mois"),
            ("taux_emploi_12m", "12 mois"),
            ("taux_emploi_18m", "18 mois"),
            ("taux_emploi_24m", "24 mois"),
        ):
            pct = _safe_pct(ip.get(h_key))
            if pct:
                horizons.append(f"{h_lib} {pct}")
        if horizons:
            fragments.append("taux emploi " + ", ".join(horizons))
        va = _safe_pct(ip.get("valeur_ajoutee_emploi_6m"))
        if va:
            fragments.append(f"valeur ajoutée emploi 6m : {va[:-1]}pp")  # 8% → 8pp
        rupt = _safe_pct(ip.get("taux_contrats_interrompus"))
        if rupt:
            fragments.append(f"taux contrats interrompus : {rupt}")
        pours = _safe_pct(ip.get("part_poursuite_etudes"))
        if pours:
            fragments.append(f"poursuite études : {pours}")
        if fragments:
            return f"Insertion apprentissage (Inserjeunes CFA, {annee}) : " + " — ".join(fragments)

    return None


def _format_profil_admis(profil_admis: dict | None) -> str | None:
    """Formate le dict `profil_admis` Parcoursup en verbatim embeddable.

    **Sprint 12 D1 (2026-05-01)** — exposition au RAG du champ profil
    historiquement présent dans les fiches mais ignoré par fiche_to_text.
    Élimine empiriquement ~30 % des hallu Sprint 11 P1.1 sur "qui est
    admis dans cette formation ?" (taux profil-spécifiques inventés
    faute de source exposée).

    Couverture corpus : 18,9 % des fiches (10 502 / 55 606) ont au moins
    une stat non-zéro (cf `docs/sprint12-D1-profil-admis-audit-champs-2026-05-01.md`).
    Le reste a soit un dict absent, soit un placeholder tout-zéros que
    Parcoursup n'a pas rempli pour la formation. Skip silencieux dans
    les deux cas pour ne pas polluer l'embedding avec "0 % boursiers"
    non-informatif.

    Sous-champs supportés (3 dicts imbriqués + 4 scalaires) :
    - `mentions_pct` {tb, b, ab, sans} : % admis par mention bac
    - `bac_type_pct` {general, techno, pro} : % admis par type bac
    - `acces_pct` {general, techno, pro} : taux d'accès profil-spécifique
        (≠ taux_acces_parcoursup_2025 global déjà exposé)
    - `boursiers_pct`, `femmes_pct`, `neobacheliers_pct`,
        `origine_academique_idf_pct` : scalaires démographiques

    Format de sortie (exemple EFREI Bordeaux Bachelor cyber) :
        "Profil des admis (Parcoursup 2025) : mentions au bac : 4 %
         très bien, 12 % bien, 29 % assez bien, 54 % sans mention —
         type de bac admis : 71 % bac général, 17 % bac techno, 12 %
         bac pro — taux d'accès par profil : 79 % pour bac général,
         14 % pour bac techno, 6 % pour bac pro — profil démographique :
         21 % boursiers, 10 % femmes, 77 % néobacheliers, 58 % origine
         académique Île-de-France"

    Valeurs déjà en pourcentage (e.g. `27.0` = 27 %, pas ratio 0-1) →
    pas de conversion `_safe_pct` ratio→%.
    """
    if not isinstance(profil_admis, dict):
        return None

    fragments: list[str] = []

    # 1. Mentions au bac (dict {tb, b, ab, sans})
    mentions = profil_admis.get("mentions_pct")
    if isinstance(mentions, dict):
        parts_m: list[str] = []
        for k, lib in (
            ("tb", "très bien"),
            ("b", "bien"),
            ("ab", "assez bien"),
            ("sans", "sans mention"),
        ):
            v = mentions.get(k)
            if isinstance(v, (int, float)) and v > 0:
                parts_m.append(f"{int(round(v))} % {lib}")
        if parts_m:
            fragments.append("mentions au bac : " + ", ".join(parts_m))

    # 2. Type de bac (admis) — dict {general, techno, pro}
    bt = profil_admis.get("bac_type_pct")
    if isinstance(bt, dict):
        parts_bt: list[str] = []
        for k, lib in (
            ("general", "bac général"),
            ("techno", "bac techno"),
            ("pro", "bac pro"),
        ):
            v = bt.get(k)
            if isinstance(v, (int, float)) and v > 0:
                parts_bt.append(f"{int(round(v))} % {lib}")
        if parts_bt:
            fragments.append("type de bac admis : " + ", ".join(parts_bt))

    # 3. Taux d'accès par profil bac — dict {general, techno, pro}
    # ≠ taux_acces_parcoursup_2025 global, profil-spécifique discriminant
    ac = profil_admis.get("acces_pct")
    if isinstance(ac, dict):
        parts_ac: list[str] = []
        for k, lib in (
            ("general", "bac général"),
            ("techno", "bac techno"),
            ("pro", "bac pro"),
        ):
            v = ac.get(k)
            if isinstance(v, (int, float)) and v > 0:
                parts_ac.append(f"{int(round(v))} % pour {lib}")
        if parts_ac:
            fragments.append("taux d'accès par profil : " + ", ".join(parts_ac))

    # 4. Scalaires démographiques (boursiers / femmes / néo / IDF)
    scalaires: list[str] = []
    for key, lib in (
        ("boursiers_pct", "boursiers"),
        ("femmes_pct", "femmes"),
        ("neobacheliers_pct", "néobacheliers"),
        ("origine_academique_idf_pct", "origine académique Île-de-France"),
    ):
        v = profil_admis.get(key)
        if isinstance(v, (int, float)) and v > 0:
            scalaires.append(f"{int(round(v))} % {lib}")
    if scalaires:
        fragments.append("profil démographique : " + ", ".join(scalaires))

    if not fragments:
        return None

    return "Profil des admis (Parcoursup 2025) : " + " — ".join(fragments)


def _format_admission_stats(fiche: dict) -> str | None:
    """Stats admission Parcoursup / MonMaster sous forme verbatim embeddable.

    - Parcoursup : `taux_acces_parcoursup_2025` (%) + `nombre_places`
    - MonMaster : `taux_admission` ratio 0-1 + `n_candidats_pp` + `n_acceptes_total`
    """
    source = (fiche.get("source") or "").lower()
    fragments: list[str] = []

    import math

    tap = fiche.get("taux_acces_parcoursup_2025")
    places = fiche.get("nombre_places")
    if tap is not None:
        try:
            tap_f = float(tap)
            if not math.isnan(tap_f):
                # Arrondi entier pour stabilité retrieval (52.0% → 52%)
                fragments.append(f"taux d'accès {int(round(tap_f))}%")
        except (ValueError, TypeError):
            pass
    if places is not None:
        fragments.append(f"{places} places")

    if source == "monmaster":
        import math
        ta_mm_pct = _safe_pct(fiche.get("taux_admission"))
        if ta_mm_pct:
            fragments.append(f"sélectivité {ta_mm_pct} admis")
        n_cand = fiche.get("n_candidats_pp")
        n_acc = fiche.get("n_acceptes_total")
        if isinstance(n_cand, (int, float)) and not math.isnan(float(n_cand)):
            fragments.append(f"{int(n_cand)} candidats")
        if isinstance(n_acc, (int, float)) and not math.isnan(float(n_acc)):
            fragments.append(f"{int(n_acc)} acceptés")

    return ("Admission : " + " — ".join(fragments)) if fragments else None


def fiche_to_text(fiche: dict) -> str:
    """Construit le texte embedded pour une fiche.

    **v3 (2026-04-24)** — injection des stats chiffrées retrievables :
    - `insertion_pro.taux_emploi_*` (Céreq 3ans/6ans ou CFA 6/12/18/24m)
    - `insertion_pro.salaire_median_embauche` + `taux_cdi` Céreq
    - `taux_admission` MonMaster + `taux_acces_parcoursup_2025`
    - `n_candidats_pp` / `n_acceptes_total` MonMaster

    Motivation : bench v2 (bench_personas_2026-04-24) a révélé que le
    modèle hallucinait des statistiques précises parce que le retrieval
    ne les exposait pas. En les injectant dans le texte embedding, elles
    deviennent retrievables + citables par le générateur.
    """
    parts = [
        f"Formation : {fiche.get('nom', '')}",
        f"Établissement : {fiche.get('etablissement', '')}",
        f"Ville : {fiche.get('ville', '')}",
    ]
    if fiche.get("type_diplome"):
        parts.append(f"Diplôme : {fiche['type_diplome']}")
    if fiche.get("niveau"):
        parts.append(f"Niveau : {fiche['niveau']}")
    if fiche.get("phase"):
        parts.append(f"Phase : {fiche['phase']}")
    if fiche.get("statut"):
        parts.append(f"Statut : {fiche['statut']}")
    labels = fiche.get("labels") or []
    if labels:
        parts.append(f"Labels : {', '.join(labels)}")
    if fiche.get("domaine"):
        parts.append(f"Domaine : {fiche['domaine']}")
    if fiche.get("departement"):
        parts.append(f"Département : {fiche['departement']}")
    if fiche.get("region"):
        parts.append(f"Région : {fiche['region']}")

    # v3 — stats admission retrievables
    adm = _format_admission_stats(fiche)
    if adm:
        parts.append(adm)

    # Sprint 12 D1 — profil_admis Parcoursup retrievable (mentions, bac type,
    # taux d'accès profil-spécifique, démographie). Skip silencieux quand
    # placeholder tout-zéros (~ 81 % du corpus).
    pa_text = _format_profil_admis(fiche.get("profil_admis"))
    if pa_text:
        parts.append(pa_text)

    # Détail narratif (Vague B.3, 800 chars) — sémantique formation
    detail = (fiche.get("detail") or "").strip()
    if detail:
        parts.append(f"Détail : {detail[:800]}")

    # Débouchés ROME libellés (Vague B.3) — appellations métiers
    debouches = fiche.get("debouches") or []
    if debouches:
        libelles = [
            d.get("libelle", "").strip()
            for d in debouches if d.get("libelle")
        ]
        if libelles:
            parts.append(f"Métiers possibles : {', '.join(libelles)}")

    # v3 — Insertion pro retrievable (taux emploi + salaire Céreq ou horizons CFA)
    ip = fiche.get("insertion_pro")
    if ip:
        ip_text = _format_insertion_pro(ip)
        if ip_text:
            parts.append(ip_text)

    return " | ".join(parts)


def embed_texts(client: Mistral, texts: list[str]) -> list[list[float]]:
    response = client.embeddings.create(model=EMBED_MODEL, inputs=texts)
    return [d.embedding for d in response.data]


def embed_texts_batched(client: Mistral, texts: list[str], batch_size: int = 64) -> list[list[float]]:
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        all_embeddings.extend(embed_texts(client, batch))
    return all_embeddings
