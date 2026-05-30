"""
Google Places API scraper — fuente oficial, sin scraping.

Sustituye al actor Apify no oficial (ver _deprecated/gmaps_scraper_apify.py).
La interfaz de salida es idéntica: el resto del pipeline (digital_enricher,
web_inspector, sheets_exporter) no necesita cambios.

COSTE ESTIMADO POR EJECUCIÓN (5 queries × 25 negocios):
  · Text Search:     125 llamadas × $0.032 = ~$4.00
  · Place Details:   ~73 llamadas × $0.032 = ~$2.34  (solo los no-sanos)
  · Total estimado:  ~$6.34 por ejecución
  · Free tier Google: $200/mes → ~30 ejecuciones/mes sin coste
  · Con plan de pago ($200+): ~1.500 negocios/mes a coste marginal

SETUP:
  1. Google Cloud Console → Credenciales → Crear API Key
  2. Activar: "Places API" (legacy) o "Places API (New)"
  3. Añadir al .env:  GOOGLE_PLACES_API_KEY=AIza...
"""

import logging
import os
import time
from datetime import datetime
from typing import Any

import googlemaps
import googlemaps.exceptions
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Coste por llamada (USD) — Places API (Legacy)
_COST_TEXT_SEARCH  = 0.032   # $32 por 1.000 llamadas
_COST_PLACE_DETAIL = 0.032   # $32 por 1.000 llamadas (Contact tier)

# Pausa requerida por Google entre text search y next_page_token
_NEXT_PAGE_DELAY = 2.0


def _get_client() -> googlemaps.Client:
    key = os.getenv("GOOGLE_PLACES_API_KEY")
    if not key:
        raise EnvironmentError(
            "GOOGLE_PLACES_API_KEY no definida en .env\n"
            "  1. Abre https://console.cloud.google.com/apis/credentials\n"
            "  2. Crea una API Key\n"
            "  3. Activa 'Places API' en la consola\n"
            "  4. Añade GOOGLE_PLACES_API_KEY=AIza... a tu .env"
        )
    return googlemaps.Client(key=key)


def _is_healthy(rating: float | None, review_count: int | None) -> bool:
    """Gate de descarte: no gastamos Place Details en negocios bien posicionados."""
    return (
        rating is not None and float(rating) >= 4.5
        and review_count is not None and int(review_count) >= 100
    )


def _normalize_from_search(item: dict[str, Any], query: str) -> dict[str, Any]:
    """
    Convierte un resultado de Text Search al formato interno del pipeline.
    Los campos phone/website se rellenan más tarde con Place Details.
    """
    types    = item.get("types", [])
    category = types[0].replace("_", " ").title() if types else ""
    place_id = item.get("place_id", "")

    return {
        "name":           item.get("name", "").strip(),
        "place_id":       place_id,                         # interno, no va al Sheet
        "category":       category,
        "rating":         item.get("rating"),
        "review_count":   item.get("user_ratings_total"),
        "address":        item.get("formatted_address", ""),
        "maps_url":       f"https://www.google.com/maps/place/?q=place_id:{place_id}",
        # Rellenados con Place Details (o default si se omiten)
        "has_website":    False,
        "website":        "",
        "phone":          "",
        "description":    "",
        # La API solo devuelve negocios verificados → claimed = True
        "claimed":        True,
        "search_query":   query,
        "source":         "google_places_api",
        "scraped_at":     datetime.utcnow().isoformat(),
        # Rellenados por digital_enricher
        "digital_score":  None,
        "weaknesses":     None,
        "call_script":    None,
    }


def _fetch_place_details(
    biz: dict[str, Any],
    client: googlemaps.Client,
) -> dict[str, Any]:
    """
    Llama a Place Details (Contact tier) para obtener teléfono y web.
    Devuelve {} si el negocio está cerrado permanentemente (señal para omitir).
    """
    place_id = biz.get("place_id", "")
    if not place_id:
        return biz

    try:
        result = client.place(
            place_id,
            fields=["formatted_phone_number", "website",
                    "business_status", "permanently_closed"],
        ).get("result", {})

        permanently_closed = result.get("permanently_closed", False)
        business_status    = result.get("business_status", "OPERATIONAL")

        if permanently_closed or business_status == "CLOSED_PERMANENTLY":
            return {}   # señal para descartar

        website = result.get("website", "")
        biz["website"]    = website
        biz["has_website"] = bool(website)
        biz["phone"]      = result.get("formatted_phone_number", "")

    except (googlemaps.exceptions.ApiError,
            googlemaps.exceptions.Timeout,
            googlemaps.exceptions.TransportError) as e:
        logger.warning("  [places] Place Details falló para '%s': %s",
                       biz.get("name"), str(e)[:80])

    return biz


def run_gmaps_scraper(
    search_queries: list[str],
    location: str = "Madrid",
    max_results_per_query: int = 30,
    language: str = "es",
) -> list[dict[str, Any]]:
    """
    Extrae negocios locales usando la API oficial de Google Places.

    Estrategia de coste:
      1. Text Search → datos básicos (name, rating, review_count)
      2. Gate is_healthy → salta Place Details para los ya bien posicionados
      3. Place Details (Contact) → phone + website solo para candidatos a lead

    Returns:
        Lista en el mismo formato que el antiguo scraper Apify — el resto
        del pipeline (digital_enricher, web_inspector, Sheets) no cambia.
    """
    client = _get_client()

    all_businesses: list[dict[str, Any]] = []
    seen:           set[str]             = set()

    text_search_calls  = 0
    place_detail_calls = 0
    skipped_healthy    = 0
    skipped_closed     = 0

    for query in search_queries:
        full_query = (
            f"{query} {location}".strip()
            if location.lower() not in query.lower()
            else query
        )
        logger.info("  [places] Buscando: '%s'", full_query)

        try:
            # ── Text Search (paginado, máx 3 páginas × 20 resultados) ─────────
            raw_items:  list[dict] = []
            page_token: str | None = None
            max_pages = max(1, -(-max_results_per_query // 20))  # ceil division

            for _ in range(max_pages):
                if page_token:
                    time.sleep(_NEXT_PAGE_DELAY)
                    resp = client.places(full_query, language=language,
                                        page_token=page_token)
                else:
                    resp = client.places(full_query, language=language)

                text_search_calls += 1
                raw_items.extend(resp.get("results", []))
                page_token = resp.get("next_page_token")

                if not page_token or len(raw_items) >= max_results_per_query:
                    break

            logger.info("  [places] '%s' → %d resultados raw", query, len(raw_items))

            for item in raw_items[:max_results_per_query]:
                biz = _normalize_from_search(item, query)
                if not biz["name"]:
                    continue

                # Dedup por (nombre + dirección)
                key = biz["name"].lower() + "|" + biz["address"][:30].lower()
                if key in seen:
                    continue
                seen.add(key)

                # Gate: negocios sanos no son leads → ahorramos Place Details
                if _is_healthy(biz["rating"], biz["review_count"]):
                    skipped_healthy += 1
                    continue

                # Place Details → phone + website (Contact tier)
                biz = _fetch_place_details(biz, client)
                place_detail_calls += 1

                if not biz:     # cerrado permanentemente
                    skipped_closed += 1
                    continue

                all_businesses.append(biz)

        except googlemaps.exceptions.ApiError as e:
            logger.error("  [places] ApiError en '%s': %s", query, str(e)[:150])
        except googlemaps.exceptions.Timeout:
            logger.error("  [places] Timeout en '%s'", query)
        except googlemaps.exceptions.TransportError as e:
            logger.error("  [places] TransportError: %s", str(e)[:100])
        except Exception as e:
            logger.error("  [places] Error inesperado en '%s': %s", query, str(e)[:150])

    # ── Resumen de coste ──────────────────────────────────────────────────────
    estimated_cost = (
        text_search_calls  * _COST_TEXT_SEARCH
        + place_detail_calls * _COST_PLACE_DETAIL
    )
    logger.info(
        "[places] %d negocios | %d text searches | %d place details | "
        "%d sanos omitidos | %d cerrados omitidos | coste estimado $%.2f",
        len(all_businesses), text_search_calls, place_detail_calls,
        skipped_healthy, skipped_closed, estimated_cost,
    )
    return all_businesses
