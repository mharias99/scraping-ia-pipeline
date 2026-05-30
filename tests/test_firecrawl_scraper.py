import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scraper.firecrawl_scraper import (
    _clean_indeed_company,
    get_client,
    parse_indeed_markdown,
    parse_infojobs_markdown,
    run_firecrawl_scraper,
    save_raw,
    scrape_page,
)

# ── Markdown fixtures ─────────────────────────────────────────────────────────

INFOJOBS_MD = """
## [Administrativo de Datos](https://www.infojobs.net/oferta/123)
### [Empresa Ejemplo S.L.]
- Barcelona - Presencial - Hace 4h
Gestión de bases de datos y Excel avanzado. Incorporación inmediata.
Se requiere conocimiento de hojas de cálculo y software de gestión empresarial.

## [Técnico de Facturación](https://www.infojobs.net/oferta/456)
### [Consultora ABC]
- Madrid - Teletrabajo - Hace 1d
Control de facturas y contabilidad básica. Manejo de ERP y herramientas ofimáticas.
Incorporación inmediata para cubrir baja temporal. Salario según convenio.
"""

INDEED_MD = """
Texto de navegación que debe ignorarse
[Auxiliar Administrativo Excel](https://es.indeed.com/viewjob?jk=abc123)
Empresa XYZ
Barcelona, España
Descripción del puesto de trabajo con Excel avanzado.

[Grabador de Datos](https://es.indeed.com/viewjob?jk=def456)
Logística Rápida S.A.
Madrid, España
Introducción de datos en sistema ERP.

[sign in](https://es.indeed.com/account/login)
Indeed
"""

INDEED_MD_DIRTY_COMPANY = """
[Operador de Datos](https://es.indeed.com/viewjob?jk=ghi789)
IGTP08916 Badalona
Hospitalet, España
"""


def _make_firecrawl_result(md: str) -> MagicMock:
    result = MagicMock()
    result.markdown = md
    return result


# ── parse_infojobs_markdown ───────────────────────────────────────────────────

class TestParseInfojobsMarkdown:
    def test_extracts_title_company_url(self) -> None:
        jobs = parse_infojobs_markdown(INFOJOBS_MD, "administrativo")
        assert len(jobs) == 2
        assert jobs[0]["title"] == "Administrativo de Datos"
        assert jobs[0]["company"] == "Empresa Ejemplo S.L."
        assert "infojobs.net/oferta/123" in jobs[0]["url"]

    def test_extracts_location_without_dash_metadata(self) -> None:
        jobs = parse_infojobs_markdown(INFOJOBS_MD, "administrativo")
        assert jobs[0]["location"] == "Barcelona"

    def test_source_field_is_infojobs(self) -> None:
        jobs = parse_infojobs_markdown(INFOJOBS_MD, "query")
        assert all(j["source"] == "infojobs" for j in jobs)

    def test_query_field_preserved(self) -> None:
        jobs = parse_infojobs_markdown(INFOJOBS_MD, "mi query")
        assert all(j["query"] == "mi query" for j in jobs)

    def test_returns_empty_on_blank_markdown(self) -> None:
        assert parse_infojobs_markdown("", "test") == []

    def test_returns_empty_when_no_matches(self) -> None:
        assert parse_infojobs_markdown("# No hay ofertas aquí\nTexto sin estructura.", "test") == []


# ── _clean_indeed_company ─────────────────────────────────────────────────────

class TestCleanIndeedCompany:
    def test_strips_leading_alphanumeric_code(self) -> None:
        assert _clean_indeed_company("IGTP08916 Badalona") == "Badalona"

    def test_strips_inline_postal_code(self) -> None:
        result = _clean_indeed_company("Empresa 08916")
        assert "08916" not in result

    def test_strips_html_tags(self) -> None:
        assert _clean_indeed_company("<b>Empresa</b>") == "Empresa"

    def test_strips_markdown_formatting(self) -> None:
        assert _clean_indeed_company("**Empresa**") == "Empresa"

    def test_strips_leading_dash(self) -> None:
        result = _clean_indeed_company("- Empresa ABC")
        assert not result.startswith("-")

    def test_clean_name_passes_through(self) -> None:
        assert _clean_indeed_company("Logística Rápida S.A.") == "Logística Rápida S.A."


# ── parse_indeed_markdown ─────────────────────────────────────────────────────

class TestParseIndeedMarkdown:
    def test_extracts_job_entries(self) -> None:
        jobs = parse_indeed_markdown(INDEED_MD, "administrativo")
        titles = [j["title"] for j in jobs]
        assert "Auxiliar Administrativo Excel" in titles
        assert "Grabador de Datos" in titles

    def test_filters_noise_titles(self) -> None:
        jobs = parse_indeed_markdown(INDEED_MD, "test")
        titles = [j["title"].lower() for j in jobs]
        assert not any("sign in" in t for t in titles)
        assert not any(t == "indeed" for t in titles)

    def test_deduplicates_by_url(self) -> None:
        md_duped = INDEED_MD + "\n[Auxiliar Administrativo Excel](https://es.indeed.com/viewjob?jk=abc123)\nDuplicado\n"
        jobs = parse_indeed_markdown(md_duped, "test")
        urls = [j["url"] for j in jobs]
        assert len(urls) == len(set(urls))

    def test_cleans_dirty_company_name(self) -> None:
        jobs = parse_indeed_markdown(INDEED_MD_DIRTY_COMPANY, "test")
        if jobs:
            assert "08916" not in jobs[0]["company"]
            assert "IGTP" not in jobs[0]["company"]

    def test_source_field_is_indeed(self) -> None:
        jobs = parse_indeed_markdown(INDEED_MD, "test")
        assert all(j["source"] == "indeed" for j in jobs)

    def test_returns_empty_on_blank_markdown(self) -> None:
        assert parse_indeed_markdown("", "test") == []


# ── scrape_page ───────────────────────────────────────────────────────────────

class TestScrapePage:
    def test_returns_parsed_jobs_on_success(self) -> None:
        app = MagicMock()
        app.scrape_url.return_value = _make_firecrawl_result(INFOJOBS_MD)

        jobs = scrape_page(app, "https://www.infojobs.net/...", "admin", "infojobs")

        assert isinstance(jobs, list)
        assert len(jobs) == 2

    def test_returns_empty_on_short_markdown(self) -> None:
        app = MagicMock()
        app.scrape_url.return_value = _make_firecrawl_result("corto")

        jobs = scrape_page(app, "https://www.infojobs.net/...", "admin", "infojobs")

        assert jobs == []

    def test_returns_empty_on_none_markdown(self) -> None:
        result = MagicMock()
        result.markdown = None
        app = MagicMock()
        app.scrape_url.return_value = result

        jobs = scrape_page(app, "https://www.infojobs.net/...", "admin", "infojobs")

        assert jobs == []

    def test_returns_empty_on_api_error(self) -> None:
        app = MagicMock()
        app.scrape_url.side_effect = RuntimeError("API failure")

        jobs = scrape_page(app, "https://www.infojobs.net/...", "admin", "infojobs")

        assert jobs == []

    def test_returns_empty_for_unknown_source(self) -> None:
        app = MagicMock()
        app.scrape_url.return_value = _make_firecrawl_result(INFOJOBS_MD)

        jobs = scrape_page(app, "https://example.com", "admin", "fuente_desconocida")

        assert jobs == []


# ── get_client ────────────────────────────────────────────────────────────────

class TestGetClient:
    def test_raises_without_api_key(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(EnvironmentError, match="FIRECRAWL_API_KEY"):
                get_client()


# ── run_firecrawl_scraper ─────────────────────────────────────────────────────

class TestRunFirecrawlScraper:
    def _patched_app(self, md: str) -> MagicMock:
        app = MagicMock()
        app.scrape_url.return_value = _make_firecrawl_result(md)
        return app

    def test_respects_max_results(self) -> None:
        app = self._patched_app(INFOJOBS_MD)
        with patch("scraper.firecrawl_scraper.get_client", return_value=app), \
             patch("scraper.firecrawl_scraper.time.sleep"):
            jobs = run_firecrawl_scraper(
                queries=["test"], sources=["infojobs"],
                max_results=1, max_pages_per_query=5,
            )
        assert len(jobs) <= 1

    def test_deduplicates_across_pages(self) -> None:
        # Same markdown returned every page → only 2 unique jobs, no matter how many pages
        app = self._patched_app(INFOJOBS_MD)
        with patch("scraper.firecrawl_scraper.get_client", return_value=app), \
             patch("scraper.firecrawl_scraper.time.sleep"):
            jobs = run_firecrawl_scraper(
                queries=["test"], sources=["infojobs"],
                max_results=50, max_pages_per_query=5,
            )
        assert len(jobs) == 2

    def test_stops_pagination_on_zero_new_results(self) -> None:
        # Page 1 → 2 new jobs; page 2 → same 2 (0 new) → stop
        app = self._patched_app(INFOJOBS_MD)
        with patch("scraper.firecrawl_scraper.get_client", return_value=app), \
             patch("scraper.firecrawl_scraper.time.sleep"):
            run_firecrawl_scraper(
                queries=["test"], sources=["infojobs"],
                max_results=50, max_pages_per_query=10,
            )
        assert app.scrape_url.call_count <= 2

    def test_ignores_unknown_sources(self) -> None:
        app = self._patched_app(INFOJOBS_MD)
        with patch("scraper.firecrawl_scraper.get_client", return_value=app), \
             patch("scraper.firecrawl_scraper.time.sleep"):
            jobs = run_firecrawl_scraper(
                queries=["test"], sources=["fuente_inexistente"],
                max_results=50,
            )
        assert jobs == []
        app.scrape_url.assert_not_called()

    def test_returns_list_of_dicts(self) -> None:
        app = self._patched_app(INFOJOBS_MD)
        with patch("scraper.firecrawl_scraper.get_client", return_value=app), \
             patch("scraper.firecrawl_scraper.time.sleep"):
            jobs = run_firecrawl_scraper(
                queries=["test"], sources=["infojobs"],
                max_results=10, max_pages_per_query=1,
            )
        assert all(isinstance(j, dict) for j in jobs)
        assert all("title" in j and "source" in j for j in jobs)


# ── save_raw ──────────────────────────────────────────────────────────────────

class TestSaveRaw:
    def test_writes_valid_json(self, tmp_path: Path) -> None:
        data = [{"title": "Dev", "company": "Acme", "source": "infojobs"}]
        output = tmp_path / "raw" / "firecrawl_raw.json"

        save_raw(data, path=output)

        assert output.exists()
        loaded = json.loads(output.read_text(encoding="utf-8"))
        assert loaded == data

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        output = tmp_path / "nested" / "firecrawl_raw.json"
        save_raw([{"title": "x"}], path=output)
        assert output.exists()

    def test_overwrites_existing_file(self, tmp_path: Path) -> None:
        output = tmp_path / "firecrawl_raw.json"
        output.write_text(json.dumps([{"old": "data"}]))

        save_raw([{"title": "new"}], path=output)

        loaded = json.loads(output.read_text())
        assert loaded[0]["title"] == "new"
