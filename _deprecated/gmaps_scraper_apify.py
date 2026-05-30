import logging
import os
from datetime import datetime, timedelta
from typing import Any

from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

GMAPS_ACTOR = "compass/crawler-google-places"

_FIELD_MAP: dict[str, list[str]] = {
    "name":           ["title", "name", "placeName"],
    "rating":         ["totalScore", "rating", "stars"],
    "review_count":   ["reviewsCount", "numberOfReviews", "reviewCount"],
    "address":        ["address", "street", "fullAddress", "location"],
    "phone":          ["phone", "phoneNumber", "telephone"],
    "website":        ["website", "websiteUrl", "url"],
    "category":       ["categoryName", "category", "businessType", "primaryType"],
    "maps_url":       ["url", "googleMapsUrl", "placeUrl"],
    "reviews_tags":   ["reviewsTags", "popularTimesLiveText"],
    "description":    ["description", "about", "summary"],
    "permanently_closed": ["permanentlyClosed", "isClosed", "closed"],
    "claimed":        ["claimed", "isVerified", "verified"],
}


def _get_client() -> ApifyClient:
    from scraper._apify_base import get_apify_client
    return get_apify_client()


def _extract(item: dict[str, Any], field: str) -> Any:
    for key in _FIELD_MAP[field]:
        val = item.get(key)
        if val is not None:
            return val
    return None


def _extract_str(item: dict[str, Any], field: str) -> str:
    val = _extract(item, field)
    if val is None:
        return ""
    return str(val).strip()


def _normalize(item: dict[str, Any], search_query: str) -> dict[str, Any] | None:
    name = _extract_str(item, "name")
    if not name:
        return None

    # Ignorar negocios permanentemente cerrados
    if _extract(item, "permanently_closed"):
        return None

    rating = _extract(item, "rating")
    try:
        rating = float(rating) if rating is not None else None
    except (ValueError, TypeError):
        rating = None

    review_count = _extract(item, "review_count")
    try:
        review_count = int(review_count) if review_count is not None else None
    except (ValueError, TypeError):
        review_count = None

    has_website = bool(_extract_str(item, "website"))

    return {
        "name":          name,
        "category":      _extract_str(item, "category"),
        "rating":        rating,
        "review_count":  review_count,
        "has_website":   has_website,
        "website":       _extract_str(item, "website"),
        "phone":         _extract_str(item, "phone"),
        "address":       _extract_str(item, "address"),
        "maps_url":      _extract_str(item, "maps_url"),
        "description":   _extract_str(item, "description")[:500],
        "claimed":       bool(_extract(item, "claimed")),
        "search_query":  search_query,
        "source":        "google_maps",
        "scraped_at":    datetime.utcnow().isoformat(),
        # Rellenados por el enricher
        "digital_score":  None,
        "weaknesses":     None,
        "call_script":    None,
    }


def run_gmaps_scraper(
    search_queries: list[str],
    location: str = "Madrid",
    max_results_per_query: int = 30,
    language: str = "es",
) -> list[dict[str, Any]]:
    """
    Scrapes Google Maps business listings for the given search queries.
    Returns normalized business records ready for digital_enricher.
    """
    client = _get_client()
    all_businesses: list[dict[str, Any]] = []
    seen: set[str] = set()

    for query in search_queries:
        full_query = f"{query} {location}".strip() if location not in query else query
        logger.info("  [gmaps] Buscando: '%s' (max %d)", full_query, max_results_per_query)
        try:
            run = client.actor(GMAPS_ACTOR).call(
                run_input={
                    "searchStringsArray":         [full_query],
                    "locationQuery":              location,
                    "maxCrawledPlacesPerSearch":  max_results_per_query,
                    "language":                   language,
                    "skipClosedPlaces":           True,
                    "scrapePlaceDetailPage":      False,
                },
                run_timeout=timedelta(seconds=240),
            )
            if not run or not run.default_dataset_id:
                logger.warning("  [gmaps] Sin dataset para '%s'", full_query)
                continue

            items = list(client.dataset(run.default_dataset_id).iterate_items())
            logger.info("  [gmaps] '%s' → %d items raw", full_query, len(items))

            for item in items:
                biz = _normalize(item, query)
                if not biz:
                    continue
                key = biz["name"].lower() + "|" + biz["address"][:30].lower()
                if key in seen:
                    continue
                seen.add(key)
                all_businesses.append(biz)

        except Exception as e:
            logger.error("  [gmaps] Error en '%s': %s", full_query, str(e)[:150])

    logger.info("[gmaps] Total negocios: %d", len(all_businesses))
    return all_businesses
