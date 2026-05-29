import json
import logging
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

from dotenv import load_dotenv
from firecrawl import V1FirecrawlApp

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

OUTPUT_PATH = Path("data/raw/firecrawl_raw.json")
DELAY_BETWEEN_REQUESTS = 3.0

SEARCH_QUERIES = [
    "data entry",
    "administrativo excel",
    "grabador datos",
    "auxiliar administrativo excel",
    "facturación administrativa",
]

SOURCES = {
    "infojobs": "https://www.infojobs.net/jobsearch/search-results/list.xhtml?keyword={query}&sortBy=PUBLICATION_DATE",
    "indeed":   "https://es.indeed.com/jobs?q={query}&l=Espa%C3%B1a&sort=date",
}


def get_client() -> V1FirecrawlApp:
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        raise EnvironmentError("FIRECRAWL_API_KEY no definida en .env")
    return V1FirecrawlApp(api_key=api_key)


def parse_infojobs_markdown(md: str, query: str) -> list[dict[str, Any]]:
    jobs = []
    # Cada oferta en InfoJobs aparece como ## [Título](url)
    pattern = re.compile(
        r'##\s+\[([^\]]+)\]\((https://www\.infojobs\.net/[^\)]+)\)'
        r'.*?###\s+\[([^\]]+)\]'          # ### [Empresa]
        r'(.*?)(?=##|\Z)',
        re.DOTALL,
    )
    for m in pattern.finditer(md):
        title   = m.group(1).strip()
        url     = m.group(2).strip()
        company = m.group(3).strip()
        body    = m.group(4).strip()

        # Extraer ubicación (ignorar líneas que son URLs o markdown links)
        lines = [l.strip() for l in body.split('\n')
                 if l.strip() and not l.strip().startswith('(http') and not l.strip().startswith('[![')]
        location    = lines[0] if lines else ""
        # Limpiar guiones de metadatos de InfoJobs (ej: "- Barcelona - Presencial - Hace 4h")
        loc_parts   = [p.strip() for p in location.split('-') if p.strip()]
        location    = loc_parts[0] if loc_parts else location
        description = " ".join(lines[1:])[:2000]

        jobs.append({
            "title": title, "company": company,
            "location": location, "salary": None,
            "description": description, "requirements": "",
            "url": url, "query": query, "source": "infojobs",
            "scraped_at": datetime.utcnow().isoformat(),
        })
    return jobs


_INDEED_NOISE = {
    "sign in", "create account", "iniciar sesión", "skip to main content",
    "sube tu cv", "upload your resume", "post your resume",
    "deja que las empresas", "all jobs", "indeed", "keyword",
}


def parse_indeed_markdown(md: str, query: str) -> list[dict[str, Any]]:
    jobs = []
    title_pattern = re.compile(
        r'\[([^\]]{5,80})\]\((https://es\.indeed\.com/[^\)]+)\)',
    )
    seen = set()
    for m in title_pattern.finditer(md):
        title       = m.group(1).strip()
        url         = m.group(2).strip()
        title_lower = title.lower()
        if url in seen:
            continue
        if any(noise in title_lower for noise in _INDEED_NOISE):
            continue
        if len(title) < 8 or title_lower.startswith("\\"):
            continue
        seen.add(url)
        # Extraer contexto después del match para empresa/ubicación
        start = m.end()
        context = md[start:start+300].strip()
        lines = [l.strip() for l in context.split('\n') if l.strip()]
        company  = re.sub(r'<[^>]+>', '', lines[0]).strip() if lines else ""
        location = re.sub(r'<[^>]+>', '', lines[1]).strip() if len(lines) > 1 else ""

        # Filtrar noise: company con markdown de formato o single words
        if company.startswith(("\\-", "**", "-", "|")) or len(company) < 3:
            continue

        jobs.append({
            "title": title, "company": company,
            "location": location, "salary": None,
            "description": "", "requirements": "",
            "url": url, "query": query, "source": "indeed",
            "scraped_at": datetime.utcnow().isoformat(),
        })
    return jobs


PARSERS = {
    "infojobs": parse_infojobs_markdown,
    "indeed":   parse_indeed_markdown,
}


def scrape_page(
    app: V1FirecrawlApp, url: str, query: str, source: str
) -> list[dict[str, Any]]:
    try:
        result = app.scrape_url(
            url,
            formats=["markdown"],
            only_main_content=True,
            timeout=45000,
        )
        md = getattr(result, "markdown", "") or ""
        if not md or len(md) < 500:
            logger.warning("  [%s] respuesta muy corta (%d chars)", source, len(md))
            return []

        parser = PARSERS.get(source)
        jobs = parser(md, query) if parser else []
        logger.info("  [%s] '%s' → %d ofertas (%d chars)", source, query, len(jobs), len(md))
        return jobs

    except Exception as e:
        logger.error("  [%s] '%s' → %s: %s", source, query, type(e).__name__, str(e)[:120])
        return []


def run_firecrawl_scraper(
    queries: list[str] | None = None,
    sources: list[str] | None = None,
    max_results: int = 50,
) -> list[dict[str, Any]]:
    app = get_client()
    queries = queries or SEARCH_QUERIES
    sources = sources or list(SOURCES.keys())
    all_jobs: list[dict[str, Any]] = []
    seen: set[str] = set()

    for query in queries:
        encoded = quote_plus(query)
        for source in sources:
            if source not in SOURCES:
                continue
            url = SOURCES[source].format(query=encoded)
            logger.info("Scrapeando [%s]: '%s'", source, query)
            jobs = scrape_page(app, url, query, source)
            for job in jobs:
                key = f"{job['company'].lower()}|{job['title'].lower()}"
                if key not in seen and job["title"]:
                    seen.add(key)
                    all_jobs.append(job)
            if len(all_jobs) >= max_results:
                break
            time.sleep(DELAY_BETWEEN_REQUESTS)
        if len(all_jobs) >= max_results:
            break

    logger.info("Total ofertas únicas: %d", len(all_jobs))
    return all_jobs[:max_results]


def save_raw(data: list[dict[str, Any]], path: Path = OUTPUT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info("Guardado en %s (%d registros)", path, len(data))


if __name__ == "__main__":
    jobs = run_firecrawl_scraper(max_results=50)
    save_raw(jobs)
