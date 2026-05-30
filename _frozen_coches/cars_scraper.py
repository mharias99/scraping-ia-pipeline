import logging
import os
from datetime import datetime, timedelta
from typing import Any

from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

MILANUNCIOS_ACTOR = "zen-studio/milanuncios-scraper"

# ID de categoría "Motor" en Milanuncios (enum verificado desde el schema del actor)
CARS_CATEGORY = "1"

BASE_URL = "https://www.milanuncios.com"


def _get_client() -> ApifyClient:
    from scraper._apify_base import get_apify_client
    return get_apify_client()


def _normalize(item: dict[str, Any], model_query: str) -> dict[str, Any] | None:
    """Convierte un item raw de Milanuncios al formato interno del pipeline."""
    title = (item.get("title") or "").strip()
    if not title:
        return None

    # Precio: {cash: {value: 8500}}
    price_num: float | None = None
    price_obj = item.get("price") or {}
    cash = price_obj.get("cash") or {}
    if cash.get("value") is not None:
        try:
            price_num = float(cash["value"])
        except (ValueError, TypeError):
            pass

    # Ubicación: {province: {name: "Madrid"}}
    loc_obj = item.get("location") or {}
    province = (loc_obj.get("province") or {}).get("name", "")
    city     = (loc_obj.get("city") or {}).get("name", "")
    location = city if city else province

    # URL: relativa → absoluta
    raw_url = item.get("url") or ""
    url = BASE_URL + raw_url if raw_url.startswith("/") else raw_url

    # Año y km desde attributes (ya estructurados por el actor)
    attrs = item.get("attributes") or {}
    year_raw = (attrs.get("year") or {}).get("raw")
    km_raw   = (attrs.get("kilometers") or {}).get("raw")
    year: int | None = None
    km:   int | None = None
    try:
        year = int(year_raw) if year_raw else None
    except (ValueError, TypeError):
        pass
    try:
        km = int(str(km_raw).replace(".", "").replace(",", "")) if km_raw else None
    except (ValueError, TypeError):
        pass

    # Teléfono (si el vendedor lo compartió)
    contact = item.get("contactMethods") or {}
    phone = item.get("phone") or ("disponible" if contact.get("phone") else "")

    return {
        "title":       title,
        "price":       price_num,
        "price_raw":   cash.get("label", ""),
        "location":    location,
        "description": (item.get("description") or "")[:1000],
        "url":         url,
        "phone":       str(phone).strip(),
        "seller":      (item.get("authorName") or "").strip(),
        "posted_at":   item.get("publicationDate") or "",
        "model_query": model_query,
        "source":      "milanuncios",
        "scraped_at":  datetime.utcnow().isoformat(),
        "year":        year,
        "km":          km,
        "market_median":   None,
        "price_delta_pct": None,
        "opportunity":     "UNKNOWN",
    }


def run_cars_scraper(
    car_models: list[str],
    max_results_per_model: int = 50,
    price_min: int = 1000,
    price_max: int = 30000,
    seller_type: str = "private",
) -> list[dict[str, Any]]:
    """
    Scrapes Milanuncios for used car listings of the given models.
    Returns raw listings ready for the cars_enricher.
    """
    client = _get_client()
    all_listings: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for model in car_models:
        logger.info("  [cars] Buscando: '%s' (max %d)", model, max_results_per_model)
        try:
            run = client.actor(MILANUNCIOS_ACTOR).call(
                run_input={
                    "text":        model,
                    "category":    CARS_CATEGORY,
                    "maxResults":  max_results_per_model,
                    "priceFrom":   price_min,
                    "priceTo":     price_max,
                    "sellerType":  seller_type,
                    "transaction": "supply",   # "supply" = anuncios de venta
                    "sort":        "newest",
                },
                run_timeout=timedelta(seconds=180),
            )
            if not run or not run.default_dataset_id:
                logger.warning("  [cars] Sin dataset para '%s'", model)
                continue

            items = list(client.dataset(run.default_dataset_id).iterate_items())
            logger.info("  [cars] '%s' → %d items raw", model, len(items))

            for item in items:
                listing = _normalize(item, model)
                if not listing:
                    continue
                url = listing["url"]
                if url and url in seen_urls:
                    continue
                if url:
                    seen_urls.add(url)
                all_listings.append(listing)

        except Exception as e:
            logger.error("  [cars] Error en '%s': %s", model, str(e)[:150])

    logger.info("[cars] Total listings: %d", len(all_listings))
    return all_listings
