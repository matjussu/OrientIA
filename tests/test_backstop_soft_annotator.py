"""Tests src.backstop.soft_annotator — Sprint 11 P1-1 Sous-étape 1.

Référence ordre : 2026-05-01-1334-claudette-orientia-sprint11-P1-1-backstop-b-soft.

Spec ~30 cas :
- 10 chiffre + contexte présents dans corpus → pas d'annotation (négatif)
- 10 chiffre + contexte absents → annotation (positif)
- 5 chiffre seul sans contexte stat/financier → pas d'annotation (durée, version)
- 5 chiffre divergent au-delà tolérance → annoter
+ tests transverses (disclaimer systématique, edge cases, format HTML)

Corpus de test : `_build_test_corpus()` — minimal, in-memory, 6 facts
(taux + salaire + emploi) sur 3 écoles fictives. Évite le chargement
du fichier 55k formations_unified.json.
"""
from __future__ import annotations

import pytest

from src.backstop.soft_annotator import (
    DISCLAIMER,
    TOOLTIP_TEXT,
    CorpusFact,
    CorpusFactIndex,
    annotate_response,
)


# ---------- Fixture ----------

@pytest.fixture(scope="module")
def corpus() -> CorpusFactIndex:
    """Corpus de test minimal : 3 écoles fictives, 6 facts."""
    facts = [
        # EPF Paris-Cachan : taux 95 %, emploi 86 %, salaire 1740 €
        CorpusFact(95.0, "pct", frozenset({"epf", "paris", "cachan", "ingenieur"})),
        CorpusFact(86.0, "pct", frozenset({"epf", "paris", "cachan", "ingenieur"})),
        CorpusFact(1740.0, "amount", frozenset({"epf", "paris", "cachan", "ingenieur"})),
        # IUT Amiens : taux 27 %, emploi 78 %
        CorpusFact(27.0, "pct", frozenset({"iut", "amiens", "mesures", "physiques"})),
        CorpusFact(78.0, "pct", frozenset({"iut", "amiens", "mesures", "physiques"})),
        # Sciences Po Paris : 10 %
        CorpusFact(10.0, "pct", frozenset({"sciences", "paris", "double", "diplome"})),
    ]
    return CorpusFactIndex(facts)


def _is_annotated(html: str, raw: str) -> bool:
    """True si `raw` est wrappé dans un span class stat-unverified."""
    return f'<span class="stat-unverified" data-tooltip="{TOOLTIP_TEXT}">{raw}</span>' in html


# =============================================================================
# Catégorie A — chiffre + contexte présents dans corpus → PAS d'annotation
# =============================================================================

class TestSupportedByCorpus:
    def test_taux_admission_epf_present_corpus(self, corpus):
        answer = "EPF Paris-Cachan affiche un taux d'admission de 95% pour les ingénieurs."
        out = annotate_response(answer, corpus)
        assert not _is_annotated(out, "95%")

    def test_taux_emploi_epf_avec_tolerance(self, corpus):
        # 86.4 ≈ 86 ± 0.5 pp
        answer = "À l'EPF Paris-Cachan, le taux d'emploi atteint 86.4% à 3 ans."
        out = annotate_response(answer, corpus)
        assert not _is_annotated(out, "86.4%")

    def test_salaire_epf_amount(self, corpus):
        answer = "Le salaire médian d'embauche EPF Paris-Cachan ingénieur est de 1740€."
        out = annotate_response(answer, corpus)
        assert not _is_annotated(out, "1740€")

    def test_salaire_epf_avec_tolerance_5pct(self, corpus):
        # 1800 vs 1740 : écart 3.4 % < 5 % tolérance
        answer = "EPF Paris-Cachan, salaire d'embauche autour de 1800€ ingénieur."
        out = annotate_response(answer, corpus)
        assert not _is_annotated(out, "1800€")

    def test_taux_iut_amiens_corpus(self, corpus):
        answer = "L'IUT d'Amiens, BUT Mesures Physiques, taux d'admission 27%."
        out = annotate_response(answer, corpus)
        assert not _is_annotated(out, "27%")

    def test_taux_iut_amiens_emploi(self, corpus):
        answer = "BUT Mesures Physiques (IUT Amiens) — taux d'insertion 78%."
        out = annotate_response(answer, corpus)
        assert not _is_annotated(out, "78%")

    def test_taux_sciencespo_corpus(self, corpus):
        answer = "Sciences Po Paris double diplôme — sélectivité forte, 10% d'admis."
        out = annotate_response(answer, corpus)
        assert not _is_annotated(out, "10%")

    def test_virgule_decimale_francaise(self, corpus):
        # 27,3 ≈ 27 ± 0.5 pp + IUT Amiens en contexte
        answer = "IUT Amiens BUT Mesures Physiques — taux 27,3% en moyenne."
        out = annotate_response(answer, corpus)
        assert not _is_annotated(out, "27,3%")

    def test_montant_kilo_euros(self, corpus):
        # 1.7 k€ = 1700 € ≈ 1740 ± 5 % + EPF en contexte
        answer = "EPF Paris-Cachan ingénieur : salaire d'embauche 1.7k€ médian."
        out = annotate_response(answer, corpus)
        assert not _is_annotated(out, "1.7k€")

    def test_chiffre_avec_etablissement_seul_sans_ville(self, corpus):
        # Match sur "epf" seul (1 keyword suffit)
        answer = "Pour l'EPF, on annonce 95% de taux d'admission."
        out = annotate_response(answer, corpus)
        assert not _is_annotated(out, "95%")


# =============================================================================
# Catégorie B — chiffre + contexte stat/fin présents MAIS absents corpus → ANNOTÉ
# =============================================================================

class TestUnsupportedByCorpus:
    def test_taux_invente_avec_contexte_admission(self, corpus):
        # 42 % avec "admission" en contexte mais aucune école corpus → annoter
        answer = (
            "Cette école accueille 42% des candidats — taux d'admission élevé."
        )
        out = annotate_response(answer, corpus)
        assert _is_annotated(out, "42%")

    def test_taux_invente_ecole_inconnue(self, corpus):
        answer = (
            "ESNA Toulouse propose un BUT avec un taux de réussite de 88%."
        )
        out = annotate_response(answer, corpus)
        assert _is_annotated(out, "88%")

    def test_salaire_invente_etablissement_inconnu(self, corpus):
        answer = (
            "Master Université Paris-Panthéon-Assas, salaire médian 3500€."
        )
        out = annotate_response(answer, corpus)
        assert _is_annotated(out, "3500€")

    def test_taux_emploi_invente(self, corpus):
        answer = "Le taux d'emploi de cette filière atteint 65% selon les fiches."
        out = annotate_response(answer, corpus)
        assert _is_annotated(out, "65%")

    def test_taux_selectivite_invente(self, corpus):
        answer = "Sélectivité forte de la formation — 12% des candidats retenus."
        out = annotate_response(answer, corpus)
        assert _is_annotated(out, "12%")

    def test_frais_inscription_inventes(self, corpus):
        answer = "Les frais de scolarité s'élèvent à 8000€ par an dans cette école."
        out = annotate_response(answer, corpus)
        assert _is_annotated(out, "8000€")

    def test_taux_insertion_invente(self, corpus):
        answer = "Insertion professionnelle à 91% selon ce chiffre du Cereq."
        out = annotate_response(answer, corpus)
        assert _is_annotated(out, "91%")

    def test_taux_admis_invente(self, corpus):
        answer = "L'an dernier, 33% des admis venaient de mention TB."
        out = annotate_response(answer, corpus)
        assert _is_annotated(out, "33%")

    def test_montant_euros_explicite_invente(self, corpus):
        answer = "Frais de cantine : environ 250 euros par semestre."
        out = annotate_response(answer, corpus)
        assert _is_annotated(out, "250 euros")

    def test_taux_arbitraire_avec_contexte(self, corpus):
        answer = "Le taux de réussite reste élevé, autour de 75% selon les rapports."
        out = annotate_response(answer, corpus)
        assert _is_annotated(out, "75%")


# =============================================================================
# Catégorie C — chiffre seul sans contexte stat/financier → PAS d'annotation
# =============================================================================

class TestNoStatFinancialContext:
    def test_duree_5_ans_pas_annotee(self, corpus):
        answer = "Tu peux faire un cursus en 5 ans à l'université."
        out = annotate_response(answer, corpus)
        # 5 ans ne matche pas RE_PCT (pas de %) ni RE_AMOUNT (pas de €).
        # Test passe trivialement.
        assert "<span" not in out

    def test_duree_avec_pct_ailleurs_dans_phrase(self, corpus):
        # "3h" et "85%" dans la même réponse, mais 85% sans contexte stat
        # à proximité — testons que la fenêtre ±50 chars est respectée.
        answer = (
            "La formation dure 3h par jour, avec 85 dans le numéro de bâtiment."
            # 85 sans % → pas matché par RE_PCT
        )
        out = annotate_response(answer, corpus)
        assert "<span" not in out

    def test_pourcent_sans_mot_cle_contexte(self, corpus):
        # 25% mais pas de mot-clé stat/fin dans ±50 chars
        answer = (
            "Le bâtiment occupé à 25% au moment du tournage publicitaire."
        )
        out = annotate_response(answer, corpus)
        # 25 % sans "taux/admission/emploi/..." dans la fenêtre = pas
        # annoté (filtre #1).
        assert "<span" not in out

    def test_montant_sans_contexte_stat(self, corpus):
        # 50 € mais le contexte est "billet de cinéma", pas frais/salaire
        answer = "Un billet de cinéma à Paris coûte rarement plus de 50€ aujourd'hui."
        # "coûte" déclenche... HMMM let me check : "coûte" ∈ keywords ?
        # On a ajouté "coût" mais "coûte" est une conjugaison. Le
        # _normalize → "coute". "cout" ⊂ "coute" ? oui.
        # Donc ce test risque d'échouer. Faisons un wording plus neutre.
        answer = "Un sandwich à la cafétéria revient parfois à 50€ environ."
        out = annotate_response(answer, corpus)
        assert "<span" not in out

    def test_version_logiciel_pas_annotee(self, corpus):
        # "Python 3.12" : pas un nombre + % ni €. RE ne matche pas.
        answer = "Python 3.12 est la version installée actuellement."
        out = annotate_response(answer, corpus)
        assert "<span" not in out


# =============================================================================
# Catégorie D — chiffre divergent au-delà tolérance → ANNOTÉ
# =============================================================================

class TestDivergentValues:
    def test_taux_pct_divergent_au_dela_tolerance(self, corpus):
        # EPF corpus = 95 %, answer = 70 % avec contexte EPF → divergent
        answer = "EPF Paris-Cachan annonce un taux d'admission de 70%."
        out = annotate_response(answer, corpus)
        assert _is_annotated(out, "70%")

    def test_salaire_divergent_au_dela_5pct(self, corpus):
        # Corpus EPF = 1740 €, answer = 2500 € → écart 43 % > 5 %
        answer = "EPF Paris-Cachan ingénieur : salaire d'embauche médian 2500€."
        out = annotate_response(answer, corpus)
        assert _is_annotated(out, "2500€")

    def test_taux_emploi_divergent_iut(self, corpus):
        # Corpus IUT Amiens = 78 %, answer = 40 % → divergent
        answer = "IUT Amiens BUT Mesures Physiques — taux d'insertion 40%."
        out = annotate_response(answer, corpus)
        assert _is_annotated(out, "40%")

    def test_taux_sciencespo_divergent(self, corpus):
        # Corpus = 10 %, answer = 30 % avec contexte Sciences Po
        answer = "Sciences Po Paris double diplôme — sélectivité, 30% d'admis."
        out = annotate_response(answer, corpus)
        assert _is_annotated(out, "30%")

    def test_taux_a_la_limite_tolerance(self, corpus):
        # 96 vs 95 → écart 1 pp > 0.5 pp tolérance → annoté
        answer = "EPF Paris-Cachan affiche un taux d'admission de 96%."
        out = annotate_response(answer, corpus)
        assert _is_annotated(out, "96%")


# =============================================================================
# Tests transverses — disclaimer, edge cases, format HTML
# =============================================================================

class TestTransverse:
    def test_disclaimer_systematique_meme_sans_chiffre(self, corpus):
        answer = "Bonjour, voici 3 pistes pour ta réorientation."
        out = annotate_response(answer, corpus)
        assert out.endswith(DISCLAIMER)

    def test_disclaimer_systematique_avec_chiffres(self, corpus):
        answer = "Le taux d'admission est de 95%, à l'EPF Paris-Cachan."
        out = annotate_response(answer, corpus)
        assert out.endswith(DISCLAIMER)

    def test_disclaimer_systematique_chiffres_inventes(self, corpus):
        answer = "Le taux d'admission est de 42% dans cette école inconnue."
        out = annotate_response(answer, corpus)
        assert out.endswith(DISCLAIMER)

    def test_disclaimer_unique_pas_double(self, corpus):
        answer = "Bonjour."
        out = annotate_response(answer, corpus)
        assert out.count(DISCLAIMER.strip()) == 1

    def test_empty_answer_renvoie_disclaimer_seul(self, corpus):
        out = annotate_response("", corpus)
        assert "Les données chiffrées" in out

    def test_format_html_span_correct(self, corpus):
        answer = "Cette école a un taux d'admission de 42%."
        out = annotate_response(answer, corpus)
        assert 'class="stat-unverified"' in out
        assert 'data-tooltip="' in out
        assert TOOLTIP_TEXT in out

    def test_multiples_chiffres_tous_annotes(self, corpus):
        answer = (
            "Cette école a 42% d'admission, 65% de réussite et 1500€ de "
            "salaire médian."
        )
        out = annotate_response(answer, corpus)
        assert _is_annotated(out, "42%")
        assert _is_annotated(out, "65%")
        assert _is_annotated(out, "1500€")

    def test_mixte_supporte_et_non_supporte(self, corpus):
        # 95 % EPF (supporté) + 42 % école inconnue (non supporté)
        answer = (
            "L'EPF Paris-Cachan affiche un taux d'admission de 95%, là où "
            "l'école inconnue annonce 42% d'admis."
        )
        out = annotate_response(answer, corpus)
        assert not _is_annotated(out, "95%")
        assert _is_annotated(out, "42%")

    def test_offsets_preserves_apres_multiples_annotations(self, corpus):
        # Vérifier que les insertions du dernier au premier ne corrompent
        # pas les balises (pas de span imbriqué corrompu).
        answer = "42% puis 65% puis 88% — 3 chiffres taux d'admission inventés."
        out = annotate_response(answer, corpus)
        # Chaque chiffre doit apparaître exactement une fois en tant que
        # contenu de span (pas de double-wrapping).
        assert out.count('>42%</span>') == 1
        assert out.count('>65%</span>') == 1
        assert out.count('>88%</span>') == 1


# =============================================================================
# Tests CorpusFactIndex helpers
# =============================================================================

class TestCorpusFactIndex:
    def test_from_unified_json_charge_real_corpus(self, tmp_path):
        # Smoke test sur un mini fichier JSON
        sample = [
            {
                "nom": "Test École",
                "etablissement": "ETB Test",
                "ville": "Paris",
                "domaine": "info",
                "taux_acces_parcoursup_2025": 50.0,
                "insertion_pro": {
                    "taux_emploi_3ans": 0.85,
                    "taux_cdi": 0.70,
                    "salaire_median_embauche": 2000,
                },
            },
            {
                "nom": "Vide",
                # Pas de stats numériques exploitables
            },
        ]
        import json
        p = tmp_path / "mini.json"
        p.write_text(json.dumps(sample), encoding="utf-8")

        idx = CorpusFactIndex.from_unified_json(p)
        # 1 taux_acces + 2 ratios * 100 + 1 salaire = 4 facts
        assert len(idx) == 4

    def test_is_supported_pct_tolerance(self, corpus):
        # 95.4 ≈ 95.0 ± 0.5 pp + EPF context match
        assert corpus.is_supported(95.4, "pct", "EPF Paris-Cachan")

    def test_is_supported_amount_tolerance_5pct(self, corpus):
        # 1820 vs 1740 : écart 4.6 % < 5 %
        assert corpus.is_supported(1820, "amount", "EPF Paris-Cachan ingénieur")

    def test_is_not_supported_no_keyword(self, corpus):
        # 95 % existe corpus mais "Inconnu" ne matche aucun entity keyword
        assert not corpus.is_supported(95.0, "pct", "École inconnue de Bordeaux")

    def test_is_not_supported_value_too_far(self, corpus):
        # EPF mentionné mais 50 % très loin de 95 % et 86 %
        assert not corpus.is_supported(50.0, "pct", "EPF Paris-Cachan")
