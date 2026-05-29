import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scraper.quotes_scraper import (
    has_next_page,
    parse_quotes,
    save_raw,
    scrape_page,
)
from conftest import (
    QUOTE_HTML_INCOMPLETE,
    QUOTE_HTML_NO_NEXT,
    QUOTE_HTML_WITH_NEXT,
)
from playwright.async_api import TimeoutError as PlaywrightTimeout


# ── parse_quotes ─────────────────────────────────────────────────────────────

class TestParseQuotes:
    def test_extracts_text_author_and_tags(self) -> None:
        quotes = parse_quotes(QUOTE_HTML_WITH_NEXT)
        assert len(quotes) == 2
        assert quotes[0]["author"] == "Steve Jobs"
        assert quotes[0]["tags"] == ["work", "passion"]
        assert "love what you do" in quotes[0]["text"]

    def test_strips_curly_quotes_from_text(self) -> None:
        quotes = parse_quotes(QUOTE_HTML_WITH_NEXT)
        assert not quotes[0]["text"].startswith("“")
        assert not quotes[0]["text"].endswith("”")

    def test_skips_blocks_missing_text_or_author(self) -> None:
        quotes = parse_quotes(QUOTE_HTML_INCOMPLETE)
        assert len(quotes) == 1
        assert quotes[0]["author"] == "Valid Author"

    def test_returns_empty_list_for_blank_html(self) -> None:
        assert parse_quotes("<html><body></body></html>") == []

    def test_quote_with_no_tags_returns_empty_list(self) -> None:
        quotes = parse_quotes(QUOTE_HTML_NO_NEXT)
        assert quotes[0]["tags"] == []


# ── has_next_page ─────────────────────────────────────────────────────────────

class TestHasNextPage:
    def test_returns_true_when_next_link_present(self) -> None:
        assert has_next_page(QUOTE_HTML_WITH_NEXT) is True

    def test_returns_false_when_no_next_link(self) -> None:
        assert has_next_page(QUOTE_HTML_NO_NEXT) is False

    def test_returns_false_for_empty_html(self) -> None:
        assert has_next_page("<html></html>") is False


# ── scrape_page ───────────────────────────────────────────────────────────────

class TestScrapePage:
    @pytest.mark.asyncio
    async def test_returns_html_on_success(self) -> None:
        page = AsyncMock()
        page.content = AsyncMock(return_value="<html>ok</html>")

        result = await scrape_page(page, "https://example.com")

        page.goto.assert_awaited_once()
        page.wait_for_selector.assert_awaited_once_with("div.quote", timeout=10000)
        assert result == "<html>ok</html>"

    @pytest.mark.asyncio
    async def test_raises_on_goto_timeout(self) -> None:
        page = AsyncMock()
        page.goto.side_effect = PlaywrightTimeout("timeout")

        with pytest.raises(PlaywrightTimeout):
            await scrape_page(page, "https://example.com")

    @pytest.mark.asyncio
    async def test_raises_on_selector_timeout(self) -> None:
        page = AsyncMock()
        page.wait_for_selector.side_effect = PlaywrightTimeout("selector timeout")

        with pytest.raises(PlaywrightTimeout):
            await scrape_page(page, "https://example.com")


# ── save_raw ──────────────────────────────────────────────────────────────────

class TestSaveRaw:
    def test_writes_valid_json(self, tmp_path: Path) -> None:
        data = [{"text": "Hello", "author": "World", "tags": ["a"]}]
        output = tmp_path / "raw" / "quotes_raw.json"

        with patch("scraper.quotes_scraper.OUTPUT_PATH", output):
            save_raw(data)

        assert output.exists()
        loaded = json.loads(output.read_text(encoding="utf-8"))
        assert loaded == data

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        output = tmp_path / "nested" / "deep" / "quotes.json"
        with patch("scraper.quotes_scraper.OUTPUT_PATH", output):
            save_raw([{"text": "x", "author": "y", "tags": []}])
        assert output.exists()

    def test_overwrites_existing_file(self, tmp_path: Path) -> None:
        output = tmp_path / "quotes_raw.json"
        output.write_text(json.dumps([{"old": "data"}]))

        with patch("scraper.quotes_scraper.OUTPUT_PATH", output):
            save_raw([{"text": "new", "author": "data", "tags": []}])

        loaded = json.loads(output.read_text())
        assert loaded[0]["text"] == "new"
