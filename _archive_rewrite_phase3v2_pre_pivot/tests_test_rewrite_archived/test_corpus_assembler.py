"""Tests pour ``src.rewrite.corpus_assembler``."""

from __future__ import annotations

import copy

import pytest

from src.rewrite.corpus_assembler import (
    AssemblyStats,
    _is_annex,
    assemble_v6,
)


def _main_fiche(idx: int) -> dict:
    return {
        "id": f"main:{idx}",
        "nom": f"Formation {idx}",
        "etablissement": f"Établissement {idx}",
        "ville": "Lyon",
        "text": f"Formation {idx} à Lyon, blah blah.",
    }


def _annex_fiche_crous() -> dict:
    return {
        "id": "crous_region:lyon",
        "domain": "crous",
        "source": "crous_combine",
        "n_logements_total": 12000,
        "regions_principales": ["Auvergne-Rhône-Alpes"],
        "text": "CROUS Lyon | 12000 logements | 36 restos U",
    }


def _annex_fiche_rome() -> dict:
    return {
        "id": "rome_metier:M1402",
        "domain": "metier_detail",
        "code_rome": "M1402",
        "libelle_metier": "Conseil en organisation et management d'entreprise",
        "text": "Métier ROME M1402 | Compétences | …",
    }


GOOD_REWRITE_CROUS = (
    "Le CROUS Auvergne-Rhône-Alpes gère le logement étudiant et la "
    "restauration universitaire pour les étudiants de la région et "
    "couvre principalement Lyon, Saint-Étienne, Grenoble et "
    "Clermont-Ferrand. Il propose 12 000 logements en résidences "
    "universitaires accessibles en priorité aux boursiers selon les "
    "critères sociaux comme les revenus de la famille et la distance "
    "au lieu d'études. Côté restauration, le réseau gère des restaurants "
    "et des cafétérias universitaires servant des repas à tarif social "
    "pour les étudiants. Le CROUS gère aussi les demandes de bourse "
    "sur critères sociaux, les aides ponctuelles et l'accompagnement "
    "social. Les étudiants postulent via le portail "
    "messervices.etudiant.gouv.fr."
)

GOOD_REWRITE_ROME = (
    "Le métier de conseil en organisation et management d'entreprise "
    "(code ROME M1402) consiste à accompagner les entreprises dans "
    "l'optimisation de leur fonctionnement. Au quotidien, un consultant "
    "réalise des audits organisationnels, élabore des préconisations "
    "stratégiques adaptées au contexte et présente ses orientations "
    "aux dirigeants. Ce métier demande une bonne capacité d'analyse, "
    "des qualités relationnelles solides et un sens de la pédagogie. "
    "Il s'exerce en cabinet de conseil ou en interne dans de grandes "
    "entreprises. L'accès se fait après un bac+5 école de commerce, "
    "école d'ingénieur ou master en management ou sciences humaines. "
    "Les juniors démarrent comme consultant, puis progressent vers des "
    "postes de manager ou directeur de mission."
)


class TestIsAnnex:
    def test_main_fiche_not_annex(self):
        assert _is_annex({"id": "x", "nom": "y"}) is False

    def test_empty_domain_not_annex(self):
        assert _is_annex({"id": "x", "domain": ""}) is False

    def test_filled_domain_is_annex(self):
        assert _is_annex({"id": "x", "domain": "crous"}) is True


class TestAssembleV6:
    def test_main_fiches_preserved_unchanged(self):
        v5 = [_main_fiche(1), _main_fiche(2)]
        v6, stats = assemble_v6(v5, rewrites={})
        assert v6[0] == v5[0]
        assert v6[1] == v5[1]
        assert stats.n_main_unchanged == 2
        assert stats.n_annex_total == 0

    def test_annex_text_replaced_when_accepted(self):
        crous = _annex_fiche_crous()
        v5 = [_main_fiche(1), crous]
        rewrites = {crous["id"]: GOOD_REWRITE_CROUS}
        v6, stats = assemble_v6(
            v5, rewrites, rewriter="claude-haiku-4-5", rewritten_at="2026-05-08"
        )
        # Main intacte
        assert v6[0] == v5[0]
        # Annex modifiée
        new_crous = v6[1]
        assert new_crous["text"] == GOOD_REWRITE_CROUS
        assert new_crous["text_original"] == crous["text"]
        assert new_crous["provenance"]["rewritten_at"] == "2026-05-08"
        assert new_crous["provenance"]["rewriter"] == "claude-haiku-4-5"
        assert new_crous["provenance"]["rewrite_accepted"] is True
        assert "rewrite_issues" not in new_crous["provenance"]
        # Stats
        assert stats.n_annex_accepted == 1
        assert stats.n_annex_rejected == 0
        assert stats.accepted_per_domain.get("crous") == 1

    def test_annex_text_kept_original_when_rejected(self):
        crous = _annex_fiche_crous()
        v5 = [crous]
        bad_rewrite = "Trop court."  # G1 fail
        v6, stats = assemble_v6(
            v5, {crous["id"]: bad_rewrite}, rewritten_at="2026-05-08"
        )
        new_crous = v6[0]
        assert new_crous["text"] == crous["text"]  # original conservé
        assert new_crous["text_original"] == crous["text"]
        assert new_crous["provenance"]["rewrite_accepted"] is False
        assert "rewrite_issues" in new_crous["provenance"]
        assert len(new_crous["provenance"]["rewrite_issues"]) > 0
        assert stats.n_annex_rejected == 1
        assert stats.n_annex_accepted == 0

    def test_annex_no_rewrite_tagged_no_rewrite_produced(self):
        crous = _annex_fiche_crous()
        v5 = [crous]
        v6, stats = assemble_v6(v5, rewrites={}, rewritten_at="2026-05-08")
        new_crous = v6[0]
        assert new_crous["text"] == crous["text"]
        assert "no_rewrite_produced" in new_crous["provenance"]["rewrite_issues"]
        assert stats.n_annex_no_rewrite == 1

    def test_text_original_always_added_for_annex(self):
        rome = _annex_fiche_rome()
        v5 = [rome]
        v6, _ = assemble_v6(v5, rewrites={rome["id"]: GOOD_REWRITE_ROME})
        assert "text_original" in v6[0]
        assert v6[0]["text_original"] == rome["text"]

    def test_text_original_not_added_for_main(self):
        main = _main_fiche(1)
        v5 = [main]
        v6, _ = assemble_v6(v5, rewrites={})
        assert "text_original" not in v6[0]

    def test_total_count_preserved(self):
        v5 = [_main_fiche(i) for i in range(5)] + [
            _annex_fiche_crous(),
            _annex_fiche_rome(),
        ]
        v6, stats = assemble_v6(
            v5,
            rewrites={
                "crous_region:lyon": GOOD_REWRITE_CROUS,
                "rome_metier:M1402": GOOD_REWRITE_ROME,
            },
        )
        assert len(v6) == len(v5)
        assert stats.n_total == 7
        assert stats.n_main_unchanged == 5
        assert stats.n_annex_total == 2
        assert stats.n_annex_accepted == 2

    def test_provenance_preserves_existing_fields(self):
        rome = _annex_fiche_rome()
        rome["provenance"] = {"tier": "tier_1", "source_label": "France Travail ROME 4.0"}
        v6, _ = assemble_v6(
            [rome],
            rewrites={rome["id"]: GOOD_REWRITE_ROME},
            rewritten_at="2026-05-08",
        )
        prov = v6[0]["provenance"]
        # Anciens champs préservés
        assert prov["tier"] == "tier_1"
        assert prov["source_label"] == "France Travail ROME 4.0"
        # Nouveaux ajoutés
        assert prov["rewritten_at"] == "2026-05-08"
        assert prov["rewrite_accepted"] is True

    def test_does_not_mutate_input(self):
        crous = _annex_fiche_crous()
        original_text = crous["text"]
        v5 = [crous]
        assemble_v6(v5, {crous["id"]: GOOD_REWRITE_CROUS})
        # input non muté
        assert crous["text"] == original_text
        assert "text_original" not in crous

    def test_rejection_reasons_aggregated(self):
        crous_a = _annex_fiche_crous()
        crous_b = copy.deepcopy(crous_a)
        crous_b["id"] = "crous_region:paris"
        v5 = [crous_a, crous_b]
        bad = "Trop court."
        v6, stats = assemble_v6(v5, {crous_a["id"]: bad, crous_b["id"]: bad})
        assert stats.n_annex_rejected == 2
        # Les deux échouent G1 (length)
        length_count = sum(
            v for k, v in stats.rejection_reasons.items() if "length" in k
        )
        assert length_count == 2
