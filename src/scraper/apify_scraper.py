import logging
import os
from datetime import datetime, timedelta
from typing import Any

from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Actores verificados y funcionales
DEFAULT_ACTORS: dict[str, str] = {
    "infojobs": "unfenced-group/infojobs-net-scraper",  # 405 runs, API interna InfoJobs
    "indeed":   "misceres/indeed-scraper",               # 1.5M runs
}

# Mapeo de campos de salida: cada actor usa nombres distintos
# Formato: {campo_interno: [candidatos en orden de preferencia]}
_FIELD_MAP: dict[str, list[str]] = {
    "title":       ["positionName", "title", "jobTitle", "position", "name"],
    "company":     ["company", "companyName", "employer", "organizationName"],
    "location":    ["location", "city", "place", "address", "jobLocation"],
    "salary":      ["salaryRaw", "salary", "salaryRange", "salaryText", "compensation"],
    "description": ["descriptionText", "description", "jobDescription", "details", "summary", "text", "snippet"],
    "url":         ["url", "applyUrl", "jobUrl", "link", "detailUrl", "jobDetailUrl"],
}


def _get_client() -> ApifyClient:
    from scraper._apify_base import get_apify_client
    return get_apify_client()


def _extract(item: dict[str, Any], field: str) -> str:
    for key in _FIELD_MAP[field]:
        val = item.get(key)
        if val and isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def _normalize(item: dict[str, Any], query: str, source_tag: str) -> dict[str, Any] | None:
    title = _extract(item, "title")
    url   = _extract(item, "url")
    if not title or not url:
        return None
    return {
        "title":        title,
        "company":      _extract(item, "company"),
        "location":     _extract(item, "location"),
        "salary":       _extract(item, "salary") or None,
        "description":  _extract(item, "description")[:2000],
        "requirements": "",
        "url":          url,
        "query":        query,
        "source":       source_tag,
        "scraped_at":   datetime.utcnow().isoformat(),
    }


def _build_input_infojobs(
    query: str, location: str, max_items: int, actor_id: str
) -> dict[str, Any]:
    """
    unfenced-group/infojobs-net-scraper usa la API interna de InfoJobs.
    Campos: searchQuery, location (provincia), maxResults, daysOld.
    """
    return {
        "searchQuery": query,
        "location":    "",          # vacío = toda España
        "maxResults":  max_items,
        "daysOld":     30,
        "skipReposts": False,
    }


def _build_input_indeed(
    query: str, location: str, max_items: int, actor_id: str
) -> dict[str, Any]:
    """
    misceres/indeed-scraper espera position + country + maxItemsPerSearch.
    """
    return {
        "position": query,
        "country": "ES",
        "maxItemsPerSearch": max_items,
    }


_INPUT_BUILDERS: dict[str, Any] = {
    "infojobs": _build_input_infojobs,
    "indeed":   _build_input_indeed,
}


def _run_actor(
    client: ApifyClient,
    actor_id: str,
    run_input: dict[str, Any],
    max_items: int,
) -> list[dict[str, Any]]:
    try:
        logger.info("  [apify] Lanzando '%s' (max %d items)...", actor_id, max_items)
        run = client.actor(actor_id).call(
            run_input=run_input,
            run_timeout=timedelta(seconds=180),
        )
        # apify-client v3 devuelve un objeto Run (Pydantic), no un dict
        if run is None or not run.default_dataset_id:
            logger.warning("  [apify] '%s' no devolvió dataset.", actor_id)
            return []

        items = list(
            client.dataset(run.default_dataset_id).iterate_items(limit=max_items)
        )
        logger.info("  [apify] '%s' → %d items", actor_id, len(items))
        return items

    except Exception as e:
        logger.error(
            "  [apify] Error en '%s': %s — %s",
            actor_id, type(e).__name__, str(e)[:200],
        )
        return []


def run_apify_scraper(
    queries: list[str] | None = None,
    sources: list[str] | None = None,
    actors: dict[str, str] | None = None,
    max_results: int = 100,
    max_items_per_query: int = 50,
    location: str = "España",
) -> list[dict[str, Any]]:
    """
    Ejecuta actores de Apify para las fuentes y queries indicadas.
    Devuelve jobs normalizados al mismo formato que firecrawl_scraper.

    Args:
        queries:             búsquedas a lanzar en cada portal.
        sources:             portales — subconjunto de ["infojobs", "indeed"].
        actors:              {portal: actor_id} para sobrescribir los defaults.
        max_results:         máximo de resultados totales.
        max_items_per_query: máximo de items a pedir al actor por (query, fuente).
        location:            ubicación geográfica a pasar al actor.
    """
    client  = _get_client()
    queries = queries or []
    sources = sources or list(DEFAULT_ACTORS.keys())
    actors  = {**DEFAULT_ACTORS, **(actors or {})}

    all_jobs: list[dict[str, Any]] = []
    seen: set[str] = set()

    for source in sources:
        actor_id    = actors.get(source)
        build_input = _INPUT_BUILDERS.get(source)

        if not actor_id:
            logger.warning("  [apify] Sin actor definido para '%s' — omitido", source)
            continue
        if not build_input:
            logger.warning("  [apify] Fuente desconocida '%s' — omitida", source)
            continue

        source_tag = f"apify_{source}"

        for query in queries:
            if len(all_jobs) >= max_results:
                break

            run_input = build_input(query, location, max_items_per_query, actor_id)
            raw_items = _run_actor(client, actor_id, run_input, max_items_per_query)

            new_count = 0
            for item in raw_items:
                job = _normalize(item, query, source_tag)
                if not job:
                    continue
                key = f"{job['company'].lower()}|{job['title'].lower()}"
                if key not in seen:
                    seen.add(key)
                    all_jobs.append(job)
                    new_count += 1

            logger.info("  [apify/%s] '%s' → %d nuevas ofertas", source, query, new_count)

        if len(all_jobs) >= max_results:
            break

    logger.info("[apify] Total ofertas únicas: %d", len(all_jobs))
    return all_jobs[:max_results]
