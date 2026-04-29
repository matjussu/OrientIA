"""Tests Sprint 10 chantier B — scripts/normalize_frontmatter.py.

Couvre :
- slug_region (normalize accents + casse → kebab-case)
- normalize_region (mapping aliases vers 18 canoniques)
- dept_to_region (lookup 105 départements FR + DOM)
- parse_niveau (bac+N + fallback type_diplome avec mastère=6)
- infer_alternance (multi-source : direct / domaine / statut / mots-clés nom)
- infer_budget (statut Public/CFA/Privé)
- infer_secteur (mapping étendu 18 domaines)
- parse_textualized_md (frontmatter YAML simple)
- normalize_*_record (3 sources : formations / textualized / golden_qa)
- Audit qualité sur sample 100 fiches dataset réel (E2E)

Tests E2E avec données réelles (pas mocks) — DoD durable post-update
`feedback_audit_claudette_rigueur`.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import sys
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import normalize_frontmatter as nf  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT_FORMATIONS = REPO_ROOT / "data" / "processed" / "formations.json"
OUTPUT_UNIFIED = REPO_ROOT / "data" / "processed" / "formations_unified.json"


# ──────────────────── slug_region ────────────────────


class TestSlugRegion:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("Île-de-France", "ile-de-france"),
            ("ILE-DE-FRANCE", "ile-de-france"),
            ("Auvergne-Rhône-Alpes", "auvergne-rhone-alpes"),
            ("Provence-Alpes-Côte d'Azur", "provence-alpes-cote-d-azur"),
            ("Bourgogne-Franche-Comté", "bourgogne-franche-comte"),
            ("La Réunion", "la-reunion"),
            ("  Occitanie  ", "occitanie"),
            ("", ""),
        ],
    )
    def test_normalize(self, raw, expected):
        assert nf.slug_region(raw) == expected


# ──────────────────── normalize_region ────────────────────


class TestNormalizeRegion:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("Île-de-France", "ile-de-france"),
            ("ILE-DE-FRANCE", "ile-de-france"),
            ("Ile-de-France", "ile-de-france"),
            ("Provence-Alpes-Côte d'Azur", "provence-alpes-cote-d-azur"),
            ("PACA", "provence-alpes-cote-d-azur"),
            ("La Réunion", "la-reunion"),
            ("Réunion", "la-reunion"),
            ("Centre", "centre-val-de-loire"),  # alias historique
            ("Occitanie", "occitanie"),
            (None, None),
            ("", None),
            ("Région inexistante", None),
        ],
    )
    def test_known(self, raw, expected):
        assert nf.normalize_region(raw) == expected


# ──────────────────── dept_to_region ────────────────────


class TestDeptToRegion:
    @pytest.mark.parametrize(
        "dept,expected",
        [
            ("Paris", "ile-de-france"),
            ("Loire-Atlantique", "pays-de-la-loire"),
            ("Haute-Garonne", "occitanie"),
            ("Bouches-du-Rhône", "provence-alpes-cote-d-azur"),
            ("Nord", "hauts-de-france"),
            ("Rhône", "auvergne-rhone-alpes"),
            ("Hauts-de-Seine", "ile-de-france"),
            ("Hérault", "occitanie"),
            ("Gironde", "nouvelle-aquitaine"),
            ("Bas-Rhin", "grand-est"),
            ("La Réunion", "la-reunion"),
            ("Guadeloupe", "guadeloupe"),
            ("Mayotte", "mayotte"),
            ("Corse-du-Sud", "corse"),
            (None, None),
            ("", None),
            ("Département-Inexistant", None),
        ],
    )
    def test_lookup(self, dept, expected):
        assert nf.dept_to_region(dept) == expected

    def test_dept_to_region_covers_top_10_real_dataset(self):
        """Top 10 départements du dataset réel doivent tous être mappés."""
        top_10 = ["Paris", "Nord", "Rhône", "Bouches-du-Rhône",
                  "Haute-Garonne", "Gironde", "Hauts-de-Seine", "Hérault",
                  "Loire-Atlantique", "Seine-Saint-Denis"]
        for dept in top_10:
            assert nf.dept_to_region(dept) is not None, f"Dept {dept} non mappé"


# ──────────────────── parse_niveau ────────────────────


class TestParseNiveau:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("bac+5", 5),
            ("bac+3", 3),
            ("bac+2", 2),
            ("bac+1", 1),
            ("BAC+5", 5),
            ("bac", 0),
            (None, None),
            ("", None),
            ("null", None),
            (5, 5),  # int direct
            (0, 0),
            (10, None),  # out of range
            ("mastère spécialisé", 6),  # fallback type_diplome
            ("mastere", 6),
            ("Master 1", 5),
            ("MSc Data", 5),
            ("diplôme d'ingénieur", 5),
            ("Bachelor cybersecurité", 3),
            ("BTS", 2),
            ("Random text", None),
        ],
    )
    def test_known(self, raw, expected):
        assert nf.parse_niveau(raw) == expected


# ──────────────────── infer_alternance ────────────────────


class TestInferAlternance:
    def test_direct_true(self):
        assert nf.infer_alternance({"alternance": True}) is True

    def test_direct_false(self):
        assert nf.infer_alternance({"alternance": False}) is False

    def test_domaine_apprentissage_yields_true(self):
        rec = {"domaine": "apprentissage", "alternance": None}
        assert nf.infer_alternance(rec) is True

    def test_statut_cfa_yields_true(self):
        rec = {"statut": "CFA Apprentissage"}
        assert nf.infer_alternance(rec) is True

    def test_nom_keyword_apprentissage(self):
        rec = {"nom": "BTS Compta en apprentissage"}
        assert nf.infer_alternance(rec) is True

    def test_nom_keyword_alternance(self):
        rec = {"nom": "Licence pro alternance gestion"}
        assert nf.infer_alternance(rec) is True

    def test_no_signals_returns_none(self):
        rec = {"nom": "BTS Compta", "domaine": "eco_gestion"}
        assert nf.infer_alternance(rec) is None


# ──────────────────── infer_budget ────────────────────


class TestInferBudget:
    @pytest.mark.parametrize(
        "statut,expected",
        [
            ("Public", "low"),
            ("public", "low"),
            ("CFA Apprentissage", "low"),
            ("Privé", "high"),
            ("prive", "high"),
            ("Privé associatif", "high"),
            ("Certificat RNCP", None),
            ("Inconnu", None),
            ("", None),
            (None, None),
        ],
    )
    def test_known(self, statut, expected):
        rec = {"statut": statut} if statut is not None else {}
        assert nf.infer_budget(rec) == expected


# ──────────────────── infer_secteur ────────────────────


class TestInferSecteur:
    @pytest.mark.parametrize(
        "domaine,expected_subset",
        [
            ("data_ia", ["informatique", "data_science"]),
            ("cyber", ["informatique", "securite"]),
            ("eco_gestion", ["commerce", "finance", "economie"]),
            ("ingenierie_industrielle", ["ingenierie", "industriel"]),
            ("sante", ["sante", "medical"]),
            ("droit", ["droit", "juridique"]),
            ("sport", ["sport", "education"]),
            ("communication", ["communication", "commerce"]),
        ],
    )
    def test_known_18_domaines(self, domaine, expected_subset):
        result = nf.infer_secteur({"domaine": domaine})
        assert result is not None
        for s in expected_subset:
            assert s in result, f"Domaine {domaine} → manque secteur {s}"

    def test_autre_yields_none(self):
        # 'autre' mappe vers liste vide → None
        assert nf.infer_secteur({"domaine": "autre"}) is None

    def test_unknown_domaine_yields_none(self):
        assert nf.infer_secteur({"domaine": "xyz_inexistant"}) is None

    def test_no_domaine_yields_none(self):
        assert nf.infer_secteur({}) is None


# ──────────────────── parse_textualized_md ────────────────────


class TestParseTextualizedMd:
    def test_parse_basic_frontmatter(self, tmp_path):
        path = tmp_path / "test.md"
        path.write_text(
            "---\n"
            "id: onisep-test\n"
            "source: onisep\n"
            "title: \"Test formation\"\n"
            "region: null\n"
            "niveau: 5\n"
            "alternance: null\n"
            "budget: null\n"
            "secteur: [informatique, data_science]\n"
            "duree_mois: 24\n"
            "rncp: 12345\n"
            "url: https://example.com\n"
            "---\n\n"
            "Le diplôme test est référencé...\n",
            encoding="utf-8",
        )
        rec = nf.parse_textualized_md(path)
        assert rec is not None
        assert rec["id"] == "onisep-test"
        assert rec["source"] == "onisep"
        assert rec["title"] == "Test formation"
        assert rec["region"] is None
        assert rec["niveau"] == 5
        assert rec["alternance"] is None
        assert rec["secteur"] == ["informatique", "data_science"]
        assert rec["duree_mois"] == 24
        assert "Le diplôme test est référencé" in rec["body"]


# ──────────────────── E2E audit qualité sample 100 fiches ────────────────────


class TestEndToEndQualitySample:
    """Audit qualité sur sample 100 fiches du dataset réel.

    Tests E2E avec données réelles obligatoires (DoD durable
    feedback_audit_claudette_rigueur)."""

    @pytest.fixture(scope="class")
    def sample_100(self):
        if not INPUT_FORMATIONS.exists():
            pytest.skip("formations.json absent")
        with INPUT_FORMATIONS.open() as f:
            data = json.load(f)
        return data[:100]

    def test_normalize_100_no_exception(self, sample_100):
        """Normaliser 100 fiches ne doit JAMAIS lever d'exception."""
        for i, rec in enumerate(sample_100):
            normalized = nf.normalize_formation_record(rec, i)
            assert isinstance(normalized, dict)
            assert "_normalized_v1" in normalized
            assert normalized["_normalized_v1"] is True

    def test_id_unique_on_sample_100(self, sample_100):
        """Les IDs composites doivent être uniques sur 100 fiches."""
        ids = [nf.normalize_formation_record(r, i)["id"] for i, r in enumerate(sample_100)]
        assert len(set(ids)) == len(ids), "Doublons d'IDs détectés"

    def test_secteur_coverage_high_on_sample(self, sample_100):
        """`domaine` 100% rempli sur le dataset → secteur_canonical doit être
        non-null sur quasi 100% (sauf domaine='autre' qui mappe à liste vide)."""
        results = [nf.normalize_formation_record(r, i) for i, r in enumerate(sample_100)]
        with_secteur = sum(1 for r in results if r.get("secteur_canonical"))
        # Au moins 85% (les 15% restants peuvent être 'autre' qui mappe vide)
        assert with_secteur >= 85, f"Secteur coverage trop bas : {with_secteur}/100"

    def test_region_coverage_with_dept_fallback(self, sample_100):
        """Région : direct + dept→region lookup. Couverture attendue >= 50%
        sur sample (cohérent avec les 62.8% du dataset complet)."""
        results = [nf.normalize_formation_record(r, i) for i, r in enumerate(sample_100)]
        with_region = sum(1 for r in results if r.get("region_canonical"))
        assert with_region >= 50, f"Region coverage trop bas : {with_region}/100"

    def test_backward_compat_original_fields_preserved(self, sample_100):
        """Les champs originaux (nom, etablissement, niveau, etc.) doivent être
        préservés pour ne pas casser fiche_to_text / format_context."""
        for i, rec in enumerate(sample_100[:10]):
            normalized = nf.normalize_formation_record(rec, i)
            # Tous les champs originaux présents
            for key in rec:
                assert key in normalized, f"Champ original {key} disparu post-normalize"
            # Et les nouveaux ajoutés sans conflict
            assert "region_canonical" in normalized
            assert "niveau_int" in normalized
            assert "_normalized_v1" in normalized


class TestUnifiedOutputCoverage:
    """Audit la sortie `formations_unified.json` complète si elle existe.

    Coverage stats attendues post-normalize (tels que mesurés au build) :
    - region_canonical >= 50%
    - niveau_int >= 60%
    - alternance_inferred >= 30%
    - budget_category >= 50%
    - secteur_canonical >= 80%
    """

    @pytest.fixture(scope="class")
    def unified(self):
        if not OUTPUT_UNIFIED.exists():
            pytest.skip("formations_unified.json non présent (run normalize_frontmatter.py first)")
        with OUTPUT_UNIFIED.open() as f:
            return json.load(f)

    def test_total_size_in_expected_range(self, unified):
        """Total ~55k = 48k formations + 6.7k textualized + (45 golden_qa si dispo)."""
        assert 50000 <= len(unified) <= 60000, f"Taille inattendue : {len(unified)}"

    def test_secteur_coverage_above_80pct(self, unified):
        with_secteur = sum(1 for r in unified if r.get("secteur_canonical"))
        pct = 100 * with_secteur / len(unified)
        assert pct >= 80.0, f"Secteur coverage : {pct:.1f}% < 80%"

    def test_alternance_coverage_above_30pct(self, unified):
        """Alternance inférence (domaine='apprentissage' + statut CFA + mots-clés)
        doit dépasser 30%."""
        with_alt = sum(1 for r in unified if r.get("alternance_inferred") is not None)
        pct = 100 * with_alt / len(unified)
        assert pct >= 30.0, f"Alternance coverage : {pct:.1f}% < 30%"

    def test_budget_coverage_above_50pct(self, unified):
        """Budget inférence depuis statut doit dépasser 50% (Public + CFA principalement)."""
        with_budget = sum(1 for r in unified if r.get("budget_category") is not None)
        pct = 100 * with_budget / len(unified)
        assert pct >= 50.0, f"Budget coverage : {pct:.1f}% < 50%"

    def test_all_regions_canonical_in_18_known(self, unified):
        """Toutes les region_canonical non-null doivent être dans les 18 régions FR."""
        valid_regions = set(nf.REGIONS_CANONIQUES)
        for r in unified[:1000]:  # sample 1000 pour speed
            region = r.get("region_canonical")
            if region is not None:
                assert region in valid_regions, f"Region invalide : {region}"
