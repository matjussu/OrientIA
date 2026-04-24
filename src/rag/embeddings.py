from mistralai.client import Mistral


EMBED_MODEL = "mistral-embed"


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
        t3 = ip.get("taux_emploi_3ans")
        t6 = ip.get("taux_emploi_6ans")
        tcdi = ip.get("taux_cdi")
        sal = ip.get("salaire_median_embauche")
        if t3 is not None:
            fragments.append(f"taux emploi 3 ans : {round(t3 * 100)}%")
        if t6 is not None:
            fragments.append(f"taux emploi 6 ans : {round(t6 * 100)}%")
        if tcdi is not None:
            fragments.append(f"taux CDI : {round(tcdi * 100)}%")
        if sal is not None:
            fragments.append(f"salaire médian embauche : {sal}€")
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
            v = ip.get(h_key)
            if v is not None:
                horizons.append(f"{h_lib} {round(v * 100)}%")
        if horizons:
            fragments.append("taux emploi " + ", ".join(horizons))
        va = ip.get("valeur_ajoutee_emploi_6m")
        if va is not None:
            fragments.append(f"valeur ajoutée emploi 6m : {round(va * 100)}pp")
        rupt = ip.get("taux_contrats_interrompus")
        if rupt is not None:
            fragments.append(f"taux contrats interrompus : {round(rupt * 100)}%")
        pours = ip.get("part_poursuite_etudes")
        if pours is not None:
            fragments.append(f"poursuite études : {round(pours * 100)}%")
        if fragments:
            return f"Insertion apprentissage (Inserjeunes CFA, {annee}) : " + " — ".join(fragments)

    return None


def _format_admission_stats(fiche: dict) -> str | None:
    """Stats admission Parcoursup / MonMaster sous forme verbatim embeddable.

    - Parcoursup : `taux_acces_parcoursup_2025` (%) + `nombre_places`
    - MonMaster : `taux_admission` ratio 0-1 + `n_candidats_pp` + `n_acceptes_total`
    """
    source = (fiche.get("source") or "").lower()
    fragments: list[str] = []

    tap = fiche.get("taux_acces_parcoursup_2025")
    places = fiche.get("nombre_places")
    if tap is not None:
        # Arrondi entier pour stabilité retrieval (52.0% → 52%)
        tap_int = int(round(float(tap)))
        fragments.append(f"taux d'accès {tap_int}%")
    if places is not None:
        fragments.append(f"{places} places")

    if source == "monmaster":
        ta_mm = fiche.get("taux_admission")
        n_cand = fiche.get("n_candidats_pp")
        n_acc = fiche.get("n_acceptes_total")
        if ta_mm is not None:
            fragments.append(f"sélectivité {round(ta_mm * 100)}% admis")
        if n_cand is not None:
            fragments.append(f"{n_cand} candidats")
        if n_acc is not None:
            fragments.append(f"{n_acc} acceptés")

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
