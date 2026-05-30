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

# Cómo construir la URL de la página N (1-indexed) para cada fuente
PAGINATION = {
    "infojobs": lambda base: lambda page: f"{base}&page={page}" if page > 1 else base,
    "indeed":   lambda base: lambda page: f"{base}&start={(page - 1) * 10}" if page > 1 else base,
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
        lines = [ln.strip() for ln in body.split('\n')
                 if ln.strip() and not ln.strip().startswith('(http') and not ln.strip().startswith('[![')]
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

_LEADING_CODE_RE = re.compile(r'^[A-Z]{2,}\d{4,}\s*')   # "IGTP08916 " → ""
_POSTAL_CODE_RE  = re.compile(r'\b\d{5}\b\s*')           # "08916 " → ""
_MARKDOWN_FMT_RE = re.compile(r'[*_`|\\]+')


def _clean_indeed_company(raw: str) -> str:
    text = re.sub(r'<[^>]+>', '', raw).strip()
    text = _LEADING_CODE_RE.sub('', text)
    text = _POSTAL_CODE_RE.sub('', text)
    text = _MARKDOWN_FMT_RE.sub('', text).strip()
    # Eliminar prefijos de lista o separadores residuales
    text = re.sub(r'^[-–—·•\s]+', '', text).strip()
    return text


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
        start = m.end()
        context = md[start:start + 300].strip()
        lines = [ln.strip() for ln in context.split('\n') if ln.strip()]
        company  = _clean_indeed_company(lines[0]) if lines else ""
        location = re.sub(r'<[^>]+>', '', lines[1]).strip() if len(lines) > 1 else ""

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
    max_pages_per_query: int = 3,
) -> list[dict[str, Any]]:
    app = get_client()
    queries = queries or SEARCH_QUERIES
    sources = sources or list(SOURCES.keys())
    all_jobs: list[dict[str, Any]] = []
    seen: set[str] = set()

    for query in queries:
        if len(all_jobs) >= max_results:
            break
        encoded = quote_plus(query)
        for source in sources:
            if source not in SOURCES:
                continue
            base_url = SOURCES[source].format(query=encoded)
            paginate = PAGINATION[source](base_url)

            for page in range(1, max_pages_per_query + 1):
                if len(all_jobs) >= max_results:
                    break
                url = paginate(page)
                logger.info("Scrapeando [%s] p%d: '%s'", source, page, query)
                jobs = scrape_page(app, url, query, source)

                new_count = 0
                for job in jobs:
                    key = f"{job['company'].lower()}|{job['title'].lower()}"
                    if key not in seen and job["title"]:
                        seen.add(key)
                        all_jobs.append(job)
                        new_count += 1

                if new_count == 0:
                    logger.info("  [%s] p%d sin resultados nuevos — deteniendo paginación", source, page)
                    break
                time.sleep(DELAY_BETWEEN_REQUESTS)

    logger.info("Total ofertas únicas: %d", len(all_jobs))
    return all_jobs[:max_results]


def save_raw(data: list[dict[str, Any]], path: Path = OUTPUT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info("Guardado en %s (%d registros)", path, len(data))


if __name__ == "__main__":
    jobs = run_firecrawl_scraper(max_results=50, max_pages_per_query=3)
    save_raw(jobs)
