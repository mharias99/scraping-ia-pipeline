import asyncio
import json
import logging
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Page
from playwright.async_api import TimeoutError as PlaywrightTimeout

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

BASE_URL   = "https://es.indeed.com"
OUTPUT_PATH = Path("data/raw/indeed_raw.json")

SEARCH_QUERIES = [
    "data entry",
    "administrativo excel",
    "grabador datos",
    "auxiliar administrativo excel",
    "gestión documental",
]

RESULTS_PER_PAGE   = 15
MAX_PAGES_PER_QUERY = 3
DELAY_PAGES  = (2.5, 4.5)
DELAY_DETAIL = (2.0, 3.5)

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

async def dismiss_cookies(page: Page) -> None:
    for sel in [
        "button#onetrust-accept-btn-handler",
        "button[id*='accept']",
        "[aria-label*='Accept']",
        "button.icl-Button--primary",
    ]:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=2500):
                await btn.click()
                await page.wait_for_timeout(600)
                return
        except PlaywrightTimeout:
            continue


async def safe_goto(page: Page, url: str) -> bool:
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(2500)
        return True
    except PlaywrightTimeout:
        logger.warning("Timeout: %s", url)
        return False


# ── Fase 1: Resultados de búsqueda ───────────────────────────────────────────

def parse_search_results(html: str, query: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    jobs: list[dict[str, Any]] = []

    # Selectores validados en vivo (2026-05-29)
    cards = soup.select("td.resultContent")

    for card in cards:
        title_el    = card.select_one("a.jcs-JobTitle, a[data-jk]")
        company_el  = card.select_one("[data-testid='company-name']")
        location_el = card.select_one("[data-testid='text-location']")
        snippet_el  = card.select_one("[class*='snippet'], [data-testid='job-snippet']")

        if not title_el:
            continue

        href = title_el.get("href", "")
        jk   = title_el.get("data-jk", "")
        url  = f"{BASE_URL}/viewjob?jk={jk}" if jk else (
               BASE_URL + href if href.startswith("/") else href)

        jobs.append({
            "title":    title_el.get_text(strip=True),
            "company":  company_el.get_text(strip=True) if company_el else "",
            "location": location_el.get_text(strip=True) if location_el else "",
            "snippet":  snippet_el.get_text(strip=True) if snippet_el else "",
            "url":      url,
            "jk":       jk,
            "query":    query,
        })

    return jobs


async def scrape_search_page(
    page: Page, query: str, page_num: int, first_page: bool
) -> list[dict[str, Any]]:
    start = (page_num - 1) * RESULTS_PER_PAGE
    encoded = quote_plus(query)
    url = f"{BASE_URL}/jobs?q={encoded}&l=Espa%C3%B1a&sort=date&start={start}"

    if not await safe_goto(page, url):
        return []

    if first_page:
        await dismiss_cookies(page)

    results = parse_search_results(await page.content(), query)
    logger.info("  '%s' pág %d → %d ofertas", query, page_num, len(results))
    return results


# ── Fase 2: Detalle de cada oferta ───────────────────────────────────────────

def parse_job_detail(html: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "lxml")

    def txt(*selectors: str) -> str:
        for sel in selectors:
            el = soup.select_one(sel)
            if el:
                return el.get_text(separator=" ", strip=True)
        return ""

    title   = txt("h1.jobsearch-JobInfoHeader-title", "h1[class*='jobsearch']", "h1")
    company = txt(
        "[data-testid='inlineHeader-companyName'] a",
        "[data-testid='inlineHeader-companyName']",
        "[class*='companyName']",
    )
    location = txt(
        "[data-testid='job-location']",
        "[class*='location']",
    )
    description = txt(
        "#jobDescriptionText",
        "div.jobsearch-jobDescriptionText",
        "[class*='jobDescription']",
    )
    return {
        "title":       title,
        "company":     company,
        "location":    location,
        "description": description[:3500],
    }


async def scrape_detail(page: Page, job: dict[str, Any]) -> dict[str, Any] | None:
    if not await safe_goto(page, job["url"]):
        return None

    detail = parse_job_detail(await page.content())

    return {
        "title":       detail["title"]    or job.get("title", ""),
        "company":     detail["company"]  or job.get("company", ""),
        "location":    detail["location"] or job.get("location", ""),
        "description": detail["description"] or job.get("snippet", ""),
        "requirements": "",
        "url":         job["url"],
        "query":       job.get("query", ""),
        "scraped_at":  datetime.utcnow().isoformat(),
    }


# ── Orquestador ───────────────────────────────────────────────────────────────

async def run_indeed_scraper(
    max_pages_per_query: int = MAX_PAGES_PER_QUERY,
    max_detail_pages: int = 30,
) -> list[dict[str, Any]]:

    collected: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1366, "height": 768},
            locale="es-ES",
            timezone_id="Europe/Madrid",
        )
        page = await ctx.new_page()

        # ── Fase 1 ────────────────────────────────────────────────────────────
        first = True
        for query in SEARCH_QUERIES:
            logger.info("Buscando: '%s'", query)
            for pnum in range(1, max_pages_per_query + 1):
                results = await scrape_search_page(page, query, pnum, first)
                first = False
                if not results:
                    break
                for r in results:
                    if r["url"] not in seen_urls:
                        seen_urls.add(r["url"])
                        collected.append(r)
                time.sleep(random.uniform(*DELAY_PAGES))

        logger.info("Fase 1: %d ofertas únicas", len(collected))

        await browser.close()

    # Indeed bloquea páginas de detalle con bot-detection.
    # Los datos de búsqueda (título, empresa, ubicación, snippet) son suficientes
    # para que Claude detecte señales de automatización.
    all_jobs: list[dict[str, Any]] = [
        {
            "title":       job["title"],
            "company":     job["company"],
            "location":    job["location"],
            "description": job["snippet"],
            "requirements": "",
            "url":         job["url"],
            "query":       job["query"],
            "scraped_at":  datetime.utcnow().isoformat(),
        }
        for job in collected[:max_detail_pages]
    ]

    logger.info("Scraping completo: %d ofertas", len(all_jobs))
    return all_jobs


def save_raw(data: list[dict[str, Any]]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info("Guardado en %s (%d registros)", OUTPUT_PATH, len(data))


if __name__ == "__main__":
    jobs = asyncio.run(run_indeed_scraper(max_pages_per_query=2, max_detail_pages=20))
    save_raw(jobs)
