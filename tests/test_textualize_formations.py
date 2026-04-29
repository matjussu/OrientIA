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


# ──────────────────── (k) infer_niveau_from_type (v1.1 fix Jarvis) ────────────────────


class TestInferNiveauFromType:
    """Fallback fix réserve audit Jarvis ONISEP : 18/18 mastères avaient
    niveau:null parce que la source JSON les renseigne pas.

    Correction Matteo via Jarvis 2026-04-29 : Mastère Spé (MS) = Bac+6,
    ≠ Master (Bac+5). Patterns mastère/MS séparés du master/MSc."""

    @pytest.mark.parametrize(
        "type_diplome,expected",
        [
            # Bac+6 — Mastère Spécialisé (CGE)
            ("mastère spécialisé", 6),
            ("Mastère spécialisé en cybersécurité", 6),
            ("mastere spe data science", 6),
            ("MS cybersécurité", 6),  # acronyme MS = Mastère Spé
            # Bac+5 — Master national / MSc / Ingé / MBA
            ("Master of Science", 5),
            ("MSc Data Science", 5),
            ("master recherche", 5),
            ("Master 2 informatique", 5),  # M2 = Master = Bac+5
            ("diplôme d'ingénieur", 5),
            ("formation d'ingenieur generaliste", 5),
            ("MBA management", 5),
            ("certificat de spécialisation", 5),
            # Bac+3
            ("bachelor en sciences et ingénierie", 3),
            ("Bachelor cybersécurité", 3),
            ("licence professionnelle", 3),
            ("BUT Informatique", 3),
            # Bac+2
            ("BTS Informatique", 2),
            ("DUT GEII", 2),
            # Bac (0)
            ("baccalauréat professionnel", 0),
            ("bac pro cybersécurité", 0),
            # No match
            ("formation d'école spécialisée", None),
            ("inconnu_random", None),
            (None, None),
            ("", None),
        ],
    )
    def test_patterns(self, type_diplome, expected):
        assert tx.infer_niveau_from_type(type_diplome) == expected

    def test_mastere_vs_master_distinction(self):
        """Régression : 'mastère' (CGE label, Bac+6) ne doit JAMAIS être
        confondu avec 'master' (diplôme national, Bac+5).
        Distinction insistée par Matteo 2026-04-29."""
        # Mastère → 6
        assert tx.infer_niveau_from_type("mastère spécialisé") == 6
        assert tx.infer_niveau_from_type("Mastère") == 6
        # Master → 5 (jamais 6)
        assert tx.infer_niveau_from_type("Master 1") == 5
        assert tx.infer_niveau_from_type("Master of Science") == 5

    def test_fallback_to_fiche_name_when_type_ambigu(self):
        """`formation d'école spécialisée` est ambigu (Top 5 ONISEP), mais
        si le NOM de la formation contient 'Master of Science' on récupère.
        Cas réel : 'Master of Science in Data Science' typé 'formation d'école
        spécialisée' dans la source ONISEP."""
        result = tx.infer_niveau_from_type(
            type_diplome="formation d'école spécialisée",
            fiche_name="Master of Science in Data Science",
        )
        assert result == 5

    def test_no_fallback_when_neither_match(self):
        result = tx.infer_niveau_from_type(
            type_diplome="formation d'école spécialisée",
            fiche_name="formation x y z",
        )
        assert result is None


class TestParseNiveauWithFallback:
    def test_direct_parse_works(self):
        # Source niveau valide → pas de fallback
        assert tx.parse_niveau_with_fallback("bac+5", type_diplome="mastère") == 5

    def test_fallback_when_source_null(self):
        # Source null → fallback type_diplome
        # Mastère Spé = Bac+6 (correction Matteo 2026-04-29)
        assert tx.parse_niveau_with_fallback(None, type_diplome="mastère spécialisé") == 6
        # Master = Bac+5 (distinction)
        assert tx.parse_niveau_with_fallback(None, type_diplome="master recherche") == 5

    def test_fallback_when_source_unparseable(self):
        # Source non-parseable → fallback
        assert tx.parse_niveau_with_fallback("invalid", type_diplome="bachelor") == 3

    def test_both_none_returns_none(self):
        assert tx.parse_niveau_with_fallback(None, type_diplome=None) is None


class TestOnisepMastereFix:
    """Test régression sur le fix mastère (réserve audit Jarvis ONISEP v1).
    Avant fix : 18/18 mastères avec niveau:null.
    Après fix : 0/18 mastères avec niveau:null (tous mappés à **6** —
    Mastère Spécialisé = Bac+6, correction Matteo via Jarvis 2026-04-29).
    """

    def test_mastere_specialise_with_null_source_yields_6(self):
        raw = {
            "source": "onisep",
            "domaine": "cyber",
            "nom": "mastère spé. cybersécurité",
            "niveau": None,
            "type_diplome": "mastère spécialisé",
        }
        fiche = tx.textualize_onisep_fiche(raw)
        assert fiche.niveau == 6  # Mastère = Bac+6

    def test_msc_in_formation_ecole_specialisee_yields_5(self):
        raw = {
            "source": "onisep",
            "domaine": "data_ia",
            "nom": "Master of Science in Data Science",
            "niveau": None,
            "type_diplome": "formation d'école spécialisée",
        }
        fiche = tx.textualize_onisep_fiche(raw)
        assert fiche.niveau == 5  # MSc = Bac+5 (master national)

    def test_real_dataset_mastere_coverage(self):
        """Couverture niveau sur dataset réel : 0 fiches mastère doivent
        rester avec niveau:null après le fix."""
        if not ONISEP_JSON.exists():
            pytest.skip("Dataset ONISEP non présent")
        with ONISEP_JSON.open() as f:
            data = json.load(f)
        mastere = [d for d in data if "mastère" in (d.get("nom") or "").lower()
                   or "mastere" in (d.get("nom") or "").lower()]
        if not mastere:
            pytest.skip("Pas de mastère dans le dataset")
        textualized = [tx.textualize_onisep_fiche(d) for d in mastere]
        null_count = sum(1 for f in textualized if f.niveau is None)
        assert null_count == 0, (
            f"Régression fix mastère : {null_count}/{len(textualized)} mastères "
            f"toujours avec niveau:null après le fix v1.1"
        )


# ──────────────────── (l) RNCP — parse_niveau_europe ────────────────────


class TestParseNiveauEurope:
    @pytest.mark.parametrize(
        "europe_label,expected",
        [
            ("NIV3", 0),  # CAP/BEP
            ("NIV4", 0),  # Bac
            ("NIV5", 2),  # Bac+2
            ("NIV6", 3),  # Bac+3 (Licence/Bachelor)
            ("NIV7", 5),  # Bac+5 (Master/Ingé) ← le plus commun RNCP
            ("NIV8", 5),  # Doctorat (mappé à 5 — lossy mais cohérent échelle)
            ("niv7", 5),  # case insensitive
            ("  NIV7  ", 5),  # trim
            ("", None),
            (None, None),
            ("REPRISE", None),  # cas "REPRISE" du RNCP — non mappé
            ("XYZ", None),
        ],
    )
    def test_mappings(self, europe_label, expected):
        assert tx.parse_niveau_europe(europe_label) == expected


# ──────────────────── (m) RNCP — textualize_rncp_fiche ────────────────────


class TestTextualizeRncpFiche:
    SAMPLE_ROW = {
        "Id_Fiche": "9523",
        "Numero_Fiche": "RNCP181",
        "Intitule": "Assistant(e) en comptabilité et gestion",
        "Abrege_Libelle": "TP",
        "Abrege_Intitule": "Titre professionnel",
        "Nomenclature_Europe_Niveau": "NIV4",
        "Nomenclature_Europe_Intitule": "Niveau 4",
        "Accessible_Nouvelle_Caledonie": "Non",
        "Accessible_Polynesie_Francaise": "Non",
        "Type_Enregistrement": "Enregistrement de droit",
        "Actif": "ACTIVE",
    }

    def test_id_format(self):
        fiche = tx.textualize_rncp_fiche(self.SAMPLE_ROW)
        assert fiche.id == "rncp-181"

    def test_source_is_rncp(self):
        fiche = tx.textualize_rncp_fiche(self.SAMPLE_ROW)
        assert fiche.source == "rncp"

    def test_niveau_mapped_correctly(self):
        fiche = tx.textualize_rncp_fiche(self.SAMPLE_ROW)
        assert fiche.niveau == 0  # NIV4 = Bac = 0

    def test_url_constructed(self):
        fiche = tx.textualize_rncp_fiche(self.SAMPLE_ROW)
        assert fiche.url is not None
        assert "francecompetences.fr" in fiche.url
        assert "181" in fiche.url

    def test_v11_limitations_null(self):
        """v1.1 : region/alternance/budget/secteur/duree_mois absents source."""
        fiche = tx.textualize_rncp_fiche(self.SAMPLE_ROW)
        assert fiche.region is None
        assert fiche.alternance is None
        assert fiche.budget is None
        assert fiche.secteur is None
        assert fiche.duree_mois is None

    def test_drom_clauses_in_paragraph(self):
        row = dict(self.SAMPLE_ROW)
        row["Accessible_Nouvelle_Caledonie"] = "Oui"
        row["Accessible_Polynesie_Francaise"] = "Oui"
        fiche = tx.textualize_rncp_fiche(row)
        assert "Nouvelle-Calédonie" in fiche.paragraph
        assert "Polynésie française" in fiche.paragraph

    def test_no_drom_clauses_when_inaccessible(self):
        fiche = tx.textualize_rncp_fiche(self.SAMPLE_ROW)
        assert "Nouvelle-Calédonie" not in fiche.paragraph
        assert "Polynésie française" not in fiche.paragraph

    def test_paragraph_anti_hallucination(self):
        """Tous les chiffres dans le paragraph viennent de la source."""
        fiche = tx.textualize_rncp_fiche(self.SAMPLE_ROW)
        para_nums = set(re.findall(r"\d+", fiche.paragraph))
        # Source nums : "181" (RNCP), "4" (Niveau 4 from europe label)
        expected_subset = {"181", "4"}
        unexpected = para_nums - expected_subset
        assert unexpected == set(), f"Hallucination RNCP: {unexpected}"


# ──────────────────── (n) RNCP — load_rncp_active ────────────────────


class TestLoadRncpActive:
    """Tests d'intégration sur le zip RNCP réel (skip si absent)."""

    @pytest.fixture(scope="class")
    def rncp_zip_present(self):
        return tx.INPUT_RNCP_ZIP.exists()

    def test_filter_only_active(self, rncp_zip_present):
        if not rncp_zip_present:
            pytest.skip("RNCP zip non présent")
        rows = tx.load_rncp_active()
        # Tous doivent être ACTIVE
        for r in rows[:100]:  # spot check 100 first
            assert r.get("Actif", "").strip().upper() == "ACTIVE"

    def test_count_in_expected_range(self, rncp_zip_present):
        """Le RNCP a typiquement 5000-7000 fiches actives en 2026."""
        if not rncp_zip_present:
            pytest.skip("RNCP zip non présent")
        rows = tx.load_rncp_active()
        assert 5000 <= len(rows) <= 10000, (
            f"Nombre de fiches ACTIVE inattendu : {len(rows)} (typique 5-7k)"
        )

    def test_all_have_numero_fiche(self, rncp_zip_present):
        if not rncp_zip_present:
            pytest.skip("RNCP zip non présent")
        rows = tx.load_rncp_active()
        sample = rows[:50]
        for r in sample:
            assert r.get("Numero_Fiche", "").startswith("RNCP")


# ──────────────────── (o) RNCP end-to-end ────────────────────


class TestRncpEndToEnd:
    @pytest.fixture(scope="class")
    def real_rncp_fiches(self):
        if not tx.INPUT_RNCP_ZIP.exists():
            pytest.skip("RNCP zip non présent")
        rows = tx.load_rncp_active()
        # Sample 5 first ACTIVE
        return [tx.textualize_rncp_fiche(r) for r in rows[:5]]

    def test_all_have_required_frontmatter_keys(self, real_rncp_fiches):
        required = {"id", "source", "title", "region", "niveau",
                    "alternance", "budget", "secteur", "duree_mois", "rncp", "url"}
        for f in real_rncp_fiches:
            md = f.to_markdown()
            for key in required:
                assert re.search(rf"^{key}:", md, re.MULTILINE), (
                    f"Frontmatter manque '{key}' pour {f.id}"
                )

    def test_anti_hallucination_real_dataset(self, real_rncp_fiches):
        """Sur 5 fiches RNCP réelles, vérifie 0 chiffre invented."""
        for f in real_rncp_fiches:
            para_nums = set(re.findall(r"\d+", f.paragraph))
            # Source nums : rncp_short (digit) + niveau europe label digit
            expected = set()
            if f.rncp:
                expected.update(re.findall(r"\d+", f.rncp))
            # Niveau européen label "Niveau N" cite un digit aussi
            # (capturé via paragraph clauses — le digit est dans le label
            # source, pas inventé)
            unexpected = para_nums - expected
            # Tolérance : le digit du label "Niveau N" peut sortir si pas
            # capturé dans rncp. On accepte à condition qu'il soit 0..8.
            for n in unexpected:
                assert int(n) in range(0, 9), (
                    f"Chiffre invented hors plage Niveau européen: {n} dans {f.id}"
                )
