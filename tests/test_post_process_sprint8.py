"""Tests pour `src/rag/post_process.py` — Sprint 8 Wave 1 anti-hallu post-process."""
from __future__ import annotations

from src.rag.post_process import (
    INVENTED_URL_DOMAINS,
    INVENTED_URL_REGEX,
    INVENTED_MARKDOWN_LINK_REGEX,
    ONISEP_SLUG_REGEX,
    TABLE_WITH_BULLETS_REGEX,
    fix_broken_markdown_tables,
    post_process_answer,
    strip_invented_urls,
    validate_onisep_slugs,
)


# -------- Bug Q8 — URL hallu --------


class TestStripInventedUrlsBugQ8:
    """Bug Q8 user_test_v3 : LLM génère github.com/matjussu/.../Paris."""

    def test_github_matjussu_url_replaced_in_markdown_link(self):
        """Markdown link [text](github.com/matjussu/...) → fallback gracieux."""
        response = (
            "Voir [PASS Sorbonne Université]"
            "(https://github.com/matjussu/OrientIA/blob/main/results/Paris) "
            "pour plus de détails."
        )
        out = strip_invented_urls(response)
        assert "github.com/matjussu" not in out
        assert "PASS Sorbonne Université" in out
        # Fallback générique présent
        assert "parcoursup.fr" in out or "onisep.fr" in out

    def test_github_url_alone_stripped(self):
        """URL nue github.com retirée silencieusement."""
        response = "Voir https://github.com/matjussu/OrientIA/Paris pour info."
        out = strip_invented_urls(response)
        assert "github.com/matjussu" not in out

    def test_jsdelivr_url_replaced(self):
        response = "Source [doc](https://jsdelivr.net/foo/bar)"
        out = strip_invented_urls(response)
        assert "jsdelivr.net" not in out
        assert "doc" in out

    def test_localhost_url_stripped(self):
        response = "Voir http://localhost:8080/foo pour test."
        out = strip_invented_urls(response)
        assert "localhost" not in out

    def test_legitimate_urls_preserved(self):
        """Non-régression : URLs officielles préservées intactes."""
        response = (
            "Voir [Parcoursup](https://www.parcoursup.fr/index.php?desc=offre) "
            "et [ONISEP fiche](https://www.onisep.fr/http/redirection/formation/slug/FOR.3293)."
        )
        out = strip_invented_urls(response)
        assert "https://www.parcoursup.fr" in out
        assert "https://www.onisep.fr" in out
        assert "FOR.3293" in out

    def test_empty_response(self):
        assert strip_invented_urls("") == ""

    def test_response_without_invented_url(self):
        """Pas de modification si aucune URL hallu détectée."""
        response = "Pour HEC, vise Tremplin/Passerelle après bac+3."
        assert strip_invented_urls(response) == response


# -------- Bug Q9 — Tableau markdown cassé --------


class TestFixBrokenMarkdownTablesBugQ9:
    """Bug Q9 : puces dans cellules → tableau malformé."""

    def test_simple_table_preserved(self):
        """Non-régression : tableau bien formé reste intact."""
        response = (
            "| Critère | Infirmier | Kiné |\n"
            "|---------|-----------|------|\n"
            "| Études  | 3 ans     | 5 ans|\n"
            "| Salaire | 1800€     | 2200€|\n"
        )
        out = fix_broken_markdown_tables(response)
        assert out == response

    def test_table_with_bullets_in_row_cleaned(self):
        """Tableau avec puces dans cellules → puces retirées."""
        response = (
            "| Métier | Étude | Salaire |\n"
            "- bullet which shouldn't be here\n"
            "- another bullet\n"
            "| Suite normale | 5 ans | 2200€ |\n"
        )
        out = fix_broken_markdown_tables(response)
        # Les puces directement après ligne tableau retirées
        assert out.count("- bullet which") == 0 or "- bullet which" not in out

    def test_response_without_table(self):
        response = "Pas de tableau ici, juste du texte."
        assert fix_broken_markdown_tables(response) == response

    def test_empty_response(self):
        assert fix_broken_markdown_tables("") == ""


# -------- Bug Q10 — Slug ONISEP hallu --------


class TestValidateOnisepSlugsBugQ10:
    """Bug Q10 : FOR.372 réutilisé pour 3 formations différentes."""

    def _make_sources(self, slugs: list[str]) -> list[dict]:
        """Helper : crée des sources avec slugs ONISEP donnés."""
        return [
            {
                "fiche": {
                    "nom": f"Formation slug {slug}",
                    "url_onisep": f"https://www.onisep.fr/http/redirection/formation/slug/FOR.{slug}",
                }
            }
            for slug in slugs
        ]

    def test_known_slug_preserved(self):
        """Slug présent dans top-K retrievé → garde tel quel."""
        sources = self._make_sources(["3293"])
        response = (
            "Voir [BBA INSEEC]"
            "(https://www.onisep.fr/http/redirection/formation/slug/FOR.3293)"
        )
        out, n = validate_onisep_slugs(response, sources)
        assert "FOR.3293" in out
        assert n == 0

    def test_unknown_slug_replaced_in_markdown_link(self):
        """Slug NON présent dans top-K → fallback gracieux."""
        sources = self._make_sources(["3293"])  # known slugs ne contient PAS 372
        response = (
            "Voir [Certificat orthoptiste]"
            "(https://www.onisep.fr/http/redirection/formation/slug/FOR.372)"
        )
        out, n = validate_onisep_slugs(response, sources)
        assert "FOR.372" not in out
        assert "Certificat orthoptiste" in out
        assert "onisep.fr" in out
        assert n == 1

    def test_for_372_reused_3_times_all_replaced(self):
        """Cas Q10 réel : FOR.372 cité 3 fois pour 3 formations différentes."""
        sources = self._make_sources(["3293"])  # ne contient PAS 372
        response = (
            "1. [L3 Santé](https://www.onisep.fr/http/redirection/formation/slug/FOR.372)\n"
            "2. [Orthoptiste](https://www.onisep.fr/http/redirection/formation/slug/FOR.372)\n"
            "3. [Orthoprothésiste](https://www.onisep.fr/http/redirection/formation/slug/FOR.372)\n"
        )
        out, n = validate_onisep_slugs(response, sources)
        assert "FOR.372" not in out
        assert n == 3
        # 3 fallback générés
        assert out.count("onisep.fr") >= 3

    def test_url_alone_unknown_replaced(self):
        """URL nue avec slug inconnu → remplacée par onisep.fr."""
        sources = self._make_sources(["3293"])
        response = "Voir https://www.onisep.fr/http/redirection/formation/slug/FOR.999"
        out, n = validate_onisep_slugs(response, sources)
        assert "FOR.999" not in out
        assert n >= 1

    def test_no_sources_all_slugs_treated_as_unknown(self):
        """Pas de fiches retrievées → tous slugs ONISEP traités comme hallu."""
        response = "Voir [fiche](https://www.onisep.fr/http/redirection/formation/slug/FOR.123)"
        out, n = validate_onisep_slugs(response, sources=[])
        assert "FOR.123" not in out
        assert n == 1

    def test_empty_response(self):
        out, n = validate_onisep_slugs("", sources=[])
        assert out == ""
        assert n == 0


# -------- Combined post_process_answer --------


class TestPostProcessAnswerCombined:
    """Test l'orchestration des 3 fixes."""

    def test_all_three_bugs_in_response_fixed(self):
        """Réponse avec 3 bugs P0 → tous corrigés."""
        sources = [{
            "fiche": {
                "nom": "BBA INSEEC",
                "url_onisep": "https://www.onisep.fr/http/redirection/formation/slug/FOR.3293",
            }
        }]
        response = (
            "Voir [PASS Sorbonne](https://github.com/matjussu/OrientIA/Paris) et "
            "[Orthoptiste](https://www.onisep.fr/http/redirection/formation/slug/FOR.999) et "
            "[BBA](https://www.onisep.fr/http/redirection/formation/slug/FOR.3293)."
        )
        out, stats = post_process_answer(response, sources)
        # Bug Q8 fixé
        assert "github.com/matjussu" not in out
        # Bug Q10 corrigé pour FOR.999, mais FOR.3293 préservé
        assert "FOR.999" not in out
        assert "FOR.3293" in out
        # Stats reflètent les corrections
        assert stats["had_invented_url"] is True
        assert stats["n_onisep_slugs_corrected"] == 1
        assert stats["chars_removed"] > 0

    def test_clean_response_passthrough(self):
        """Non-régression : réponse propre passe sans modification."""
        sources = [{"fiche": {"url_onisep": "https://www.onisep.fr/.../FOR.100"}}]
        response = (
            "Pour HEC avec 11 de moyenne, vise Tremplin/Passerelle après "
            "[BBA INSEEC](https://www.parcoursup.fr) ou "
            "[fiche ONISEP](https://www.onisep.fr/http/redirection/formation/slug/FOR.100)."
        )
        out, stats = post_process_answer(response, sources)
        # Réponse identique (URLs officielles + slug known préservés)
        assert "parcoursup.fr" in out
        assert "FOR.100" in out
        assert stats["had_invented_url"] is False
        assert stats["n_onisep_slugs_corrected"] == 0

    def test_empty_response(self):
        out, stats = post_process_answer("", [])
        assert out == ""
        assert stats["applied"] is False


# -------- Constants & regex sanity --------


class TestConstantsAndRegex:
    def test_invented_url_domains_includes_github(self):
        joined = "|".join(INVENTED_URL_DOMAINS)
        assert "github" in joined.lower()
        assert "matjussu" in joined.lower()

    def test_invented_url_regex_matches_real_bug_pattern(self):
        """Pattern réel observé dans user_test_v3 Q8."""
        url = "https://github.com/matjussu/OrientIA/blob/main/results/user_test_v3/Paris"
        assert INVENTED_URL_REGEX.search(url)

    def test_invented_url_regex_does_not_match_legitimate(self):
        """Non-régression : URLs officielles ne matchent pas."""
        for url in (
            "https://www.parcoursup.fr/index.php",
            "https://www.onisep.fr/foo/bar",
            "https://etudiant.gouv.fr/baz",
            "https://example.com/whatever",  # autre domaine non-OrientIA = OK
        ):
            assert not INVENTED_URL_REGEX.search(url), f"False positive on: {url}"

    def test_onisep_slug_regex_matches_for_format(self):
        for slug in ("FOR.123", "FOR.3293", "FOR.10401"):
            assert ONISEP_SLUG_REGEX.search(f"voir {slug} ici")

    def test_onisep_slug_regex_does_not_match_other(self):
        for txt in ("FOR.AB", "for.123", "FOR.12"):  # last is too short
            assert not ONISEP_SLUG_REGEX.search(txt), f"False positive on: {txt}"
