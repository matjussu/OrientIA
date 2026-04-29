"""Tests Sprint 10 chantier B — scripts/textualize_formations.py.

Couvre les 6 deliverables de l'ordre 0700b :
- (a) parsing niveau "bac+N" (cas valides + edge "bac" + None)
- (b) mapping domaine → secteur (data_ia + cyber + unknown)
- (c) parse durée "N ans" / "N mois" / "N semestres" → mois
- (d) frontmatter contient les 11 clés requises (id/source/title/region/niveau/
      alternance/budget/secteur/duree_mois/rncp/url)
- (e) paragraph length raisonnable (200-1500 chars)
- (f) anti-hallucination : tous les chiffres du paragraphe viennent du JSON
      source (RNCP, niveau, durée — pas inventés)

Tests en plus :
- (g) dedupe_ids : suffixe -2, -3 sur collisions
- (h) end-to-end sur 10 fiches diverses (smoke test)
- (i) YAML escape pour caractères spéciaux dans title

Source : `data/raw/onisep_formations.json` (102 fiches, 2 domaines, 8 niveaux/durées).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import sys
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import textualize_formations as tx  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
ONISEP_JSON = REPO_ROOT / "data" / "raw" / "onisep_formations.json"


# ──────────────────── (a) parse_niveau ────────────────────


class TestParseNiveau:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("bac+5", 5),
            ("bac+3", 3),
            ("bac+2", 2),
            ("bac+1", 1),
            ("BAC+5", 5),
            ("  bac+5  ", 5),
            ("bac", 0),
            (None, None),
            ("", None),
            ("license", None),
            ("bac+5+spec", None),
        ],
    )
    def test_known_and_edge(self, raw, expected):
        assert tx.parse_niveau(raw) == expected


# ──────────────────── (b) domaine_to_secteurs ────────────────────


class TestDomaineToSecteurs:
    def test_data_ia(self):
        assert tx.domaine_to_secteurs("data_ia") == ["informatique", "data_science"]

    def test_cyber(self):
        assert tx.domaine_to_secteurs("cyber") == ["informatique", "securite"]

    def test_unknown_returns_none(self):
        assert tx.domaine_to_secteurs("xyz") is None

    def test_none_input(self):
        assert tx.domaine_to_secteurs(None) is None

    def test_case_insensitive(self):
        assert tx.domaine_to_secteurs("DATA_IA") == ["informatique", "data_science"]


# ──────────────────── (c) parse_duree_mois ────────────────────


class TestParseDureeMois:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("1 an", 12),
            ("2 ans", 24),
            ("3 ans", 36),
            ("5 ans", 60),
            ("6 mois", 6),
            ("18 mois", 18),
            ("4 semestres", 24),
            ("1 semestre", 6),
            (None, None),
            ("", None),
            ("variable", None),
            ("3", None),  # sans unité
        ],
    )
    def test_known_and_edge(self, raw, expected):
        assert tx.parse_duree_mois(raw) == expected


# ──────────────────── (d) Frontmatter clés requises ────────────────────


class TestFrontmatterKeys:
    REQUIRED_KEYS = {
        "id", "source", "title", "region", "niveau", "alternance",
        "budget", "secteur", "duree_mois", "rncp", "url",
    }

    def test_all_keys_present_in_minimal_fiche(self):
        raw = {
            "source": "onisep",
            "domaine": "data_ia",
            "nom": "Test formation",
            "niveau": "bac+5",
            "duree": "2 ans",
        }
        fiche = tx.textualize_onisep_fiche(raw)
        md = fiche.to_markdown()
        for key in self.REQUIRED_KEYS:
            assert re.search(rf"^{key}:", md, re.MULTILINE), (
                f"Frontmatter manque la clé '{key}'"
            )

    def test_all_keys_present_in_empty_fiche(self):
        raw = {"source": "onisep"}  # tout vide
        fiche = tx.textualize_onisep_fiche(raw)
        md = fiche.to_markdown()
        for key in self.REQUIRED_KEYS:
            assert re.search(rf"^{key}:", md, re.MULTILINE)

    def test_yaml_null_for_absent_optional(self):
        raw = {"source": "onisep", "nom": "Test"}
        fiche = tx.textualize_onisep_fiche(raw)
        md = fiche.to_markdown()
        # Les champs absents apparaissent comme `null` (pas Python None)
        assert re.search(r"^region: null$", md, re.MULTILINE)
        assert re.search(r"^alternance: null$", md, re.MULTILINE)
        assert re.search(r"^budget: null$", md, re.MULTILINE)


# ──────────────────── (e) Paragraph length ────────────────────


class TestParagraphLength:
    def test_complete_fiche_length_range(self):
        raw = {
            "source": "onisep",
            "domaine": "cyber",
            "nom": "expert en cybersécurité des systèmes d'information",
            "niveau": "bac+5",
            "duree": "2 ans",
            "rncp": "37989",
            "type_diplome": "formation d'école spécialisée",
            "tutelle": "ministère",
        }
        fiche = tx.textualize_onisep_fiche(raw)
        # Borne basse 200 (info riche), borne haute 1500 (anti-bloat)
        assert 200 <= len(fiche.paragraph) <= 1500

    def test_minimal_fiche_still_has_paragraph(self):
        raw = {"source": "onisep", "nom": "Formation X"}
        fiche = tx.textualize_onisep_fiche(raw)
        # Au minimum la phrase d'identification + le pointeur ONISEP
        assert len(fiche.paragraph) >= 50


# ──────────────────── (f) Anti-hallucination ────────────────────


class TestAntiHallucination:
    """Garde-fou critique : aucun chiffre dans le paragraphe ne doit être
    inventé. Les seuls nombres possibles sont :
    - le code RNCP (cité tel quel)
    - le niveau "bac+N" (cité tel quel depuis source)
    - la durée "N ans" / "N mois" (citée telle quelle depuis source)
    """

    def _extract_numbers(self, text: str) -> set[str]:
        """Extract tous les nombres entiers du texte."""
        return set(re.findall(r"\d+", text))

    def test_no_invented_numbers_minimal(self):
        raw = {"source": "onisep", "nom": "Formation X"}
        fiche = tx.textualize_onisep_fiche(raw)
        # Aucun chiffre attendu (rien dans la source)
        nums = self._extract_numbers(fiche.paragraph)
        assert nums == set(), f"Chiffres invented dans paragraph: {nums}"

    def test_only_source_numbers_appear(self):
        raw = {
            "source": "onisep",
            "domaine": "cyber",
            "nom": "Formation X",
            "niveau": "bac+5",
            "duree": "2 ans",
            "rncp": "37989",
            "type_diplome": "mastère spécialisé",
        }
        fiche = tx.textualize_onisep_fiche(raw)
        nums = self._extract_numbers(fiche.paragraph)
        # Source numbers : "5" (de bac+5), "2" (de 2 ans), "37989" (rncp)
        expected_subset = {"5", "2", "37989"}
        unexpected = nums - expected_subset
        assert unexpected == set(), (
            f"Chiffres invented (pas dans source): {unexpected}"
        )

    def test_real_dataset_no_hallucination(self):
        """End-to-end sur 10 fiches du dataset réel : verify chaque
        nombre dans le paragraph existe dans la source."""
        if not ONISEP_JSON.exists():
            pytest.skip("Dataset ONISEP non présent")
        with ONISEP_JSON.open() as f:
            data = json.load(f)
        sample = data[:10]
        for raw in sample:
            fiche = tx.textualize_onisep_fiche(raw)
            para_nums = self._extract_numbers(fiche.paragraph)
            # Source nums : RNCP, niveau (digit après bac+), durée (digit)
            source_repr = " ".join([
                raw.get("rncp") or "",
                raw.get("niveau") or "",
                raw.get("duree") or "",
            ])
            source_nums = self._extract_numbers(source_repr)
            unexpected = para_nums - source_nums
            assert unexpected == set(), (
                f"Hallucination détectée fiche {fiche.id}: "
                f"paragraph={para_nums} source={source_nums}"
            )


# ──────────────────── (g) dedupe_ids ────────────────────


class TestDedupeIds:
    def test_no_duplicates_passthrough(self):
        f1 = tx.TextualizedFiche(
            id="onisep-1", source="onisep", title="A", region=None,
            niveau=None, alternance=None, budget=None, secteur=None,
            duree_mois=None, rncp=None, url=None, paragraph="x",
        )
        f2 = tx.TextualizedFiche(
            id="onisep-2", source="onisep", title="B", region=None,
            niveau=None, alternance=None, budget=None, secteur=None,
            duree_mois=None, rncp=None, url=None, paragraph="y",
        )
        result = tx.dedupe_ids([f1, f2])
        assert [r.id for r in result] == ["onisep-1", "onisep-2"]

    def test_duplicate_gets_suffix(self):
        f1 = tx.TextualizedFiche(
            id="onisep-X", source="onisep", title="A", region=None,
            niveau=None, alternance=None, budget=None, secteur=None,
            duree_mois=None, rncp=None, url=None, paragraph="x",
        )
        f2 = tx.TextualizedFiche(
            id="onisep-X", source="onisep", title="B", region=None,
            niveau=None, alternance=None, budget=None, secteur=None,
            duree_mois=None, rncp=None, url=None, paragraph="y",
        )
        f3 = tx.TextualizedFiche(
            id="onisep-X", source="onisep", title="C", region=None,
            niveau=None, alternance=None, budget=None, secteur=None,
            duree_mois=None, rncp=None, url=None, paragraph="z",
        )
        result = tx.dedupe_ids([f1, f2, f3])
        assert [r.id for r in result] == ["onisep-X", "onisep-X-2", "onisep-X-3"]

    def test_dedup_preserves_other_fields(self):
        f1 = tx.TextualizedFiche(
            id="onisep-X", source="onisep", title="A", region="occitanie",
            niveau=5, alternance=True, budget=2000, secteur=["informatique"],
            duree_mois=24, rncp="123", url="http://x", paragraph="hello",
        )
        f2 = tx.TextualizedFiche(
            id="onisep-X", source="onisep", title="B", region="occitanie",
            niveau=5, alternance=True, budget=2000, secteur=["informatique"],
            duree_mois=24, rncp="123", url="http://x", paragraph="world",
        )
        result = tx.dedupe_ids([f1, f2])
        assert result[1].id == "onisep-X-2"
        assert result[1].title == "B"
        assert result[1].paragraph == "world"
        assert result[1].rncp == "123"  # autres champs intacts


# ──────────────────── (h) End-to-end sur 10 fiches réelles ────────────────────


class TestEndToEndRealDataset:
    @pytest.fixture(scope="class")
    def real_fiches(self):
        if not ONISEP_JSON.exists():
            pytest.skip("Dataset ONISEP non présent")
        with ONISEP_JSON.open() as f:
            data = json.load(f)
        return [tx.textualize_onisep_fiche(d) for d in data[:10]]

    def test_all_have_required_fields(self, real_fiches):
        for f in real_fiches:
            assert f.id.startswith("onisep-")
            assert f.source == "onisep"
            assert f.title  # nom non vide
            assert f.paragraph

    def test_all_have_secteur_for_known_domains(self, real_fiches):
        # Domains data_ia + cyber sont 100% dans la source → 10/10 doivent
        # avoir secteur mappé non-None
        for f in real_fiches:
            assert f.secteur is not None, (
                f"Fiche {f.id} domaine connu sans secteur mappé : {f.title}"
            )

    def test_markdown_round_trip(self, real_fiches):
        for f in real_fiches:
            md = f.to_markdown()
            # Le frontmatter ouvre et ferme avec ---
            assert md.startswith("---\n")
            assert "\n---\n" in md
            # Paragraph présent après le second ---
            after_front = md.split("\n---\n", 1)[1]
            assert len(after_front.strip()) > 0


# ──────────────────── (i) YAML escape ────────────────────


class TestYamlEscape:
    def test_simple_string_no_quotes(self):
        result = tx._yaml_escape("simple")
        assert result == "simple"

    def test_string_with_colon_quoted(self):
        result = tx._yaml_escape("title: subtitle")
        assert result.startswith('"') and result.endswith('"')

    def test_none_yields_null(self):
        assert tx._yaml_escape(None) == "null"

    def test_empty_yields_null(self):
        assert tx._yaml_escape("") == "null"

    def test_internal_quote_escaped(self):
        result = tx._yaml_escape('a "quoted" string')
        assert '\\"' in result


# ──────────────────── (j) Slugify ────────────────────


class TestSlugify:
    def test_basic_lowercase_dashes(self):
        assert tx._slugify("Hello World!") == "hello-world"

    def test_accents_stripped(self):
        assert tx._slugify("café société") == "cafe-societe"

    def test_truncated_at_max_len(self):
        long_name = "a" * 200
        assert len(tx._slugify(long_name, max_len=50)) <= 50

    def test_empty_returns_untitled(self):
        assert tx._slugify("") == "untitled"

    def test_special_chars_only_returns_untitled(self):
        assert tx._slugify("@#$%") == "untitled"
