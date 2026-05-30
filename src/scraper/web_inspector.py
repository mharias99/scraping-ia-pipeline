"""
Web Inspector — Paso 4 del Pipeline V2 de Auditoría Digital

Solo se ejecuta para los negocios que:
  a) Pasaron el gate de auto-descarte (Maps score suficiente)
  b) Tienen URL de web registrada en Google Maps

Detecta con Firecrawl:
  - HTTPS activo
  - Sitio accesible (no 404 / caído)
  - Formulario de reserva/cita online
  - Píxel de Meta (Facebook Ads)
  - Google Analytics / Tag Manager

Caché por dominio: si dos sedes comparten web, solo se inspecciona una vez.
Timeout graceful: si Firecrawl tarda o falla → web_status = "revisar_manual".
"""

import logging
import re
from typing import Any
from urllib.parse import urlparse
logger = logging.getLogger(__name__)

# Señales de reserva online en el contenido de la página
_BOOKING_SIGNALS = re.compile(
    r'\b(reservar|reserva\s+cita|pedir\s+cita|book\s+now|booking|appointment|'
    r'agenda\s+online|cita\s+online|solicitar\s+cita|reserve\s+now|'
    r'calendly|acuity|doctoralia|fresha|treatwell)\b',
    re.IGNORECASE,
)

# Señales de Meta Pixel
_META_PIXEL = re.compile(
    r'(fbq\s*\(|facebook\.net/en_US/fbevents\.js|connect\.facebook\.net|'
    r'facebook-pixel|fb_pixel)',
    re.IGNORECASE,
)

# Señales de Google Analytics / GTM
_GA_SIGNALS = re.compile(
    r'(gtag\s*\(|googletagmanager\.com|google-analytics\.com|'
    r"ga\s*\(\s*['\"]create|UA-\d+|G-[A-Z0-9]+)",
    re.IGNORECASE,
)


def _extract_domain(url: str) -> str:
    try:
        parsed = urlparse(url if url.startswith("http") else f"https://{url}")
        return parsed.netloc.lower().lstrip("www.")
    except Exception:
        return url.lower()


_WEB_INSPECTOR_RETRIES = 1  # 1 reintento antes de marcar revisar_manual


def _inspect_one(url: str, app: Any, attempt: int = 1) -> dict[str, Any]:
    """Scrapes a single URL with Firecrawl and returns web_* fields.
    Reintenta una vez ante timeout o error transitorio.
    """
    import time as _time
    is_https = url.lower().startswith("https://")
    try:
        result = app.scrape_url(
            url,
            formats=["markdown"],
            only_main_content=False,  # necesitamos scripts/head para detectar píxeles
            timeout=30000,
        )
        md = getattr(result, "markdown", "") or ""

        if not md or len(md) < 200:
            return {
                "web_live":        False,
                "web_https":       is_https,
                "web_booking":     False,
                "web_pixel_meta":  False,
                "web_pixel_ga":    False,
                "web_status":      "down",
                "web_score":       20,   # site caído = dolor real
            }

        has_booking     = bool(_BOOKING_SIGNALS.search(md))
        has_meta_pixel  = bool(_META_PIXEL.search(md))
        has_ga          = bool(_GA_SIGNALS.search(md))

        score = 0
        if not is_https:
            score += 20
        if not has_booking:
            score += 20
        if not has_meta_pixel and not has_ga:
            score += 10

        return {
            "web_live":        True,
            "web_https":       is_https,
            "web_booking":     has_booking,
            "web_pixel_meta":  has_meta_pixel,
            "web_pixel_ga":    has_ga,
            "web_status":      "ok",
            "web_score":       min(score, 50),
        }

    except Exception as e:
        if attempt <= _WEB_INSPECTOR_RETRIES:
            logger.warning("  [web] intento %d fallido para %s (%s) — reintentando...",
                           attempt, url, str(e)[:60])
            _time.sleep(2 ** attempt)
            return _inspect_one(url, app, attempt + 1)
        logger.warning("  [web] timeout/error definitivo en %s — %s", url, str(e)[:80])
        return {
            "web_live":        False,
            "web_https":       is_https,
            "web_booking":     False,
            "web_pixel_meta":  False,
            "web_pixel_ga":    False,
            "web_status":      "revisar_manual",
            "web_score":       10,
        }


def _no_web_fields() -> dict[str, Any]:
    return {
        "web_live":        False,
        "web_https":       False,
        "web_booking":     False,
        "web_pixel_meta":  False,
        "web_pixel_ga":    False,
        "web_status":      "no_web",
        "web_score":       25,   # sin web = +25 fijo
    }


def inspect_websites(
    businesses: list[dict[str, Any]],
    top_n: int = 25,
) -> list[dict[str, Any]]:
    """
    Para los top_n negocios (ordenados por maps_score desc):
      - Si tienen web → Firecrawl inspection (con caché por dominio)
      - Si no → web_score = 25 fijo, sin Firecrawl

    Añade campos web_* + web_score a cada negocio.
    """
    from scraper.firecrawl_scraper import get_client
    app = get_client()

    # Ordenar por maps_score desc y tomar top_n
    candidates = sorted(businesses, key=lambda b: b.get("maps_score", 0), reverse=True)[:top_n]

    domain_cache: dict[str, dict[str, Any]] = {}
    total_inspected = 0

    for biz in candidates:
        website = biz.get("website", "").strip()
        if not website:
            biz.update(_no_web_fields())
            continue

        domain = _extract_domain(website)

        if domain in domain_cache:
            # Mismo dominio ya inspeccionado (ej: cadena con varias sedes)
            biz.update(domain_cache[domain])
            logger.debug("  [web] caché hit: %s", domain)
            continue

        logger.info("  [web] Inspeccionando: %s", website)
        fields = _inspect_one(website, app)
        domain_cache[domain] = fields
        biz.update(fields)
        total_inspected += 1

    # Los que no están en candidates (descartados antes del top_n) también necesitan defaults
    candidate_set = {id(b) for b in candidates}
    for biz in businesses:
        if id(biz) not in candidate_set:
            # No llegaron al top_n — marcamos como no inspeccionado
            biz.update({
                "web_live": False, "web_https": False, "web_booking": False,
                "web_pixel_meta": False, "web_pixel_ga": False,
                "web_status": "no_inspeccionado", "web_score": 0,
            })

    logger.info("[web_inspector] %d webs inspeccionadas (%d dominios únicos)",
                total_inspected, len(domain_cache))
    return businesses
