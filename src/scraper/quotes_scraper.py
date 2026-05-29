import asyncio
import json
import logging
import random
import time
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeout

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

BASE_URL = "https://quotes.toscrape.com"
OUTPUT_PATH = Path("data/raw/quotes_raw.json")

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]


def parse_quotes(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    quotes = []
    for block in soup.select("div.quote"):
        text = block.select_one("span.text")
        author = block.select_one("small.author")
        tags = block.select("a.tag")
        if not text or not author:
            continue
        quotes.append({
            "text": text.get_text(strip=True).strip("“”"),
            "author": author.get_text(strip=True),
            "tags": [t.get_text(strip=True) for t in tags],
        })
    return quotes


def has_next_page(html: str) -> bool:
    soup = BeautifulSoup(html, "lxml")
    return soup.select_one("li.next a") is not None


async def scrape_page(page: Page, url: str) -> str:
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_selector("div.quote", timeout=10000)
        return await page.content()
    except PlaywrightTimeout:
        logger.error("Timeout al cargar %s", url)
        raise


async def run_scraper(max_pages: int = 5) -> list[dict[str, Any]]:
    all_quotes: list[dict[str, Any]] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        current_url = BASE_URL
        page_num = 1

        while page_num <= max_pages:
            logger.info("Scrapeando página %d: %s", page_num, current_url)
            try:
                html = await scrape_page(page, current_url)
            except PlaywrightTimeout:
                logger.error("Se abandonó la página %d por timeout", page_num)
                break

            quotes = parse_quotes(html)
            all_quotes.extend(quotes)
            logger.info("  -> %d citas extraídas (total: %d)", len(quotes), len(all_quotes))

            if not has_next_page(html):
                logger.info("No hay más páginas.")
                break

            current_url = f"{BASE_URL}/page/{page_num + 1}/"
            page_num += 1
            time.sleep(random.uniform(0.8, 1.5))

        await browser.close()

    return all_quotes


def save_raw(data: list[dict[str, Any]]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info("Datos guardados en %s (%d registros)", OUTPUT_PATH, len(data))


if __name__ == "__main__":
    quotes = asyncio.run(run_scraper(max_pages=5))
    save_raw(quotes)
