import asyncio
import json
import logging
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Browser, Page
from playwright.async_api import TimeoutError as PlaywrightTimeout

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ── Configuración ─────────────────────────────────────────────────────────────

BASE_URL = "https://www.infojobs.net"
OUTPUT_PATH = Path("data/raw/infojobs_raw.json")

# Palabras clave que indican empresas que pican datos manualmente
SEARCH_QUERIES = [
    "data entry",
    "administrativo excel",
    "grabador datos",
    "auxiliar administrativo excel",
    "gestión documental excel",
]

MAX_PAGES_PER_QUERY = 3
DELAY_BETWEEN_PAGES = (2.0, 4.0)
DELAY_BETWEEN_JOBS  = (1.5, 3.0)

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]


# ── Schema de salida del scraper ──────────────────────────────────────────────
#
# {
#   "title":        str   — título de la oferta
#   "company":      str   — nombre de la empresa
#   "location":     str   — ciudad / provincia
#   "salary":       str | None
#   "description":  str   — descripción completa del puesto
#   "requirements": str   — requisitos del puesto (texto libre)
#   "url":          str   — URL canónica de la oferta
#   "query":        str   — keyword que encontró esta oferta
#   "scraped_at":   str   — ISO 8601
# }


# ── Helpers ───────────────────────────────────────────────────────────────────

async def dismiss_cookies(page: Page) -> None:
    selectors = [
        "button#didomi-notice-agree-button",
        "button[id*='accept']",
        "button[class*='accept']",
        "#onetrust-accept-btn-handler",
    ]
    for sel in selectors:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=3000):
                await btn.click()
                logger.info("Cookie banner dismissed (%s)", sel)
                await page.wait_for_timeout(800)
                return
        except PlaywrightTimeout:
            continue


async def safe_goto(page: Page, url: str, wait_selector: str) -> bool:
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_selector(wait_selector, timeout=12000)
        return True
    except PlaywrightTimeout:
        logger.error("Timeout cargando %s", url)
        return False


# ── Fase 1: Recoger URLs desde resultados de búsqueda ────────────────────────

def parse_search_results(html: str, query: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    jobs: list[dict[str, Any]] = []

    # InfoJobs usa <li> con data-jobad-id o article con clase de oferta
    cards = soup.select("li[data-jobad-id], article.ij-OfferItem, div[class*='offer-item']")
    if not cards:
        # Fallback: cualquier enlace que apunte a /oferta-trabajo/
        links = soup.select("a[href*='/oferta-trabajo/']")
        for link in links:
            href = link.get("href", "")
            if href and href not in [j["url"] for j in jobs]:
                jobs.append({"url": href if href.startswith("http") else BASE_URL + href,
                              "query": query})
        return jobs

    for card in cards:
        title_el  = card.select_one("a[class*='ij-OfferItem-title'], h2 a, .js-o-link, a[href*='oferta-trabajo']")
        company_el = card.select_one("[class*='company'], [class*='empresa'], .ij-OfferItem-name")
        location_el = card.select_one("[class*='location'], [class*='location'], .ij-OfferItem-location")
        salary_el  = card.select_one("[class*='salary'], [class*='salario']")

        if not title_el:
            continue

        href = title_el.get("href", "")
        url  = href if href.startswith("http") else BASE_URL + href

        jobs.append({
            "title":    title_el.get_text(strip=True),
            "company":  company_el.get_text(strip=True) if company_el else "",
            "location": location_el.get_text(strip=True) if location_el else "",
            "salary":   salary_el.get_text(strip=True) if salary_el else None,
            "url":      url,
            "query":    query,
        })

    return jobs


async def scrape_search_page(
    page: Page, query: str, page_num: int
) -> list[dict[str, Any]]:
    encoded_query = query.replace(" ", "+")
    url = (
        f"{BASE_URL}/jobsearch/search-results/list.xhtml"
        f"?keyword={encoded_query}&page={page_num}&sortBy=PUBLICATION_DATE"
    )

    ok = await safe_goto(page, url, "body")
    if not ok:
        return []

    if page_num == 1:
        await dismiss_cookies(page)

    html = await page.content()
    results = parse_search_results(html, query)
    logger.info("  Query '%s' pág %d → %d ofertas encontradas", query, page_num, len(results))
    return results


# ── Fase 2: Entrar en cada oferta y extraer descripción completa ──────────────

def parse_job_detail(html: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "lxml")

    def get_text(*selectors: str) -> str:
        for sel in selectors:
            el = soup.select_one(sel)
            if el:
                return el.get_text(separator=" ", strip=True)
        return ""

    title    = get_text("h1.ij-OfferDetail-title", "h1[class*='title']", "h1")
    company  = get_text("[class*='company-name']", "[class*='empresa']", ".ij-OfferDetail-company")
    location = get_text("[class*='location']", ".ij-OfferDetail-location")
    salary   = get_text("[class*='salary']", "[class*='salario']")

    # Descripción y requisitos suelen estar en secciones separadas
    description = get_text(
        "#description", "[class*='description']",
        ".ij-OfferDetail-description", "[data-testid='offer-description']",
    )
    requirements = get_text(
        "#requirements", "[class*='requirements']",
        ".ij-OfferDetail-requirements", "[data-testid='offer-requirements']",
    )

    # Fallback: capturar todo el texto del bloque principal si los selectores no matchean
    if not description:
        main = soup.select_one("main, #main-content, .ij-OfferDetail")
        if main:
            description = main.get_text(separator=" ", strip=True)[:3000]

    return {
        "title":        title,
        "company":      company,
        "location":     location,
        "salary":       salary or None,
        "description":  description[:3000],
        "requirements": requirements[:1500],
    }


async def scrape_job_detail(
    page: Page, job: dict[str, Any]
) -> dict[str, Any] | None:
    ok = await safe_goto(page, job["url"], "body")
    if not ok:
        return None

    detail = parse_job_detail(await page.content())

    # Usar datos de la card si el detail no los pudo extraer
    return {
        "title":        detail["title"]    or job.get("title", ""),
        "company":      detail["company"]  or job.get("company", ""),
        "location":     detail["location"] or job.get("location", ""),
        "salary":       detail["salary"]   or job.get("salary"),
        "description":  detail["description"],
        "requirements": detail["requirements"],
        "url":          job["url"],
        "query":        job.get("query", ""),
        "scraped_at":   datetime.utcnow().isoformat(),
    }


# ── Orquestador principal ─────────────────────────────────────────────────────

async def run_infojobs_scraper(
    max_pages_per_query: int = MAX_PAGES_PER_QUERY,
    max_detail_pages: int = 30,
) -> list[dict[str, Any]]:

    all_jobs: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    async with async_playwright() as pw:
        browser: Browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1366, "height": 768},
            locale="es-ES",
            timezone_id="Europe/Madrid",
        )
        page = await context.new_page()

        # ── Fase 1: recoger URLs ──────────────────────────────────────────────
        collected: list[dict[str, Any]] = []

        for query in SEARCH_QUERIES:
            logger.info("Buscando: '%s'", query)
            for page_num in range(1, max_pages_per_query + 1):
                results = await scrape_search_page(page, query, page_num)
                if not results:
                    break
                for r in results:
                    if r.get("url") and r["url"] not in seen_urls:
                        seen_urls.add(r["url"])
                        collected.append(r)
                time.sleep(random.uniform(*DELAY_BETWEEN_PAGES))

        logger.info("Fase 1 completa: %d ofertas únicas recopiladas", len(collected))

        # ── Fase 2: extraer detalle de cada oferta ────────────────────────────
        to_scrape = collected[:max_detail_pages]
        logger.info("Fase 2: entrando en %d ofertas para extraer descripción completa", len(to_scrape))

        for i, job in enumerate(to_scrape, start=1):
            logger.info("  [%d/%d] %s", i, len(to_scrape), job.get("title") or job["url"])
            detail = await scrape_job_detail(page, job)
            if detail:
                all_jobs.append(detail)
            time.sleep(random.uniform(*DELAY_BETWEEN_JOBS))

        await browser.close()

    logger.info("Scraping completo: %d ofertas con descripción extraída", len(all_jobs))
    return all_jobs


def save_raw(data: list[dict[str, Any]]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info("Datos guardados en %s (%d registros)", OUTPUT_PATH, len(data))


if __name__ == "__main__":
    jobs = asyncio.run(run_infojobs_scraper(max_pages_per_query=2, max_detail_pages=20))
    save_raw(jobs)
