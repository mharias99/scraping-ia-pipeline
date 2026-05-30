# _deprecated/

Código retirado del pipeline activo. Se conserva por si hay que volver.

| Archivo | Qué era | Por qué se retiró | Fecha |
|---------|---------|-------------------|-------|
| `gmaps_scraper_apify.py` | Scraper de Google Maps vía actor Apify no oficial | ToS de Google Maps prohíbe scraping; riesgo de baneo/suspensión de cuenta Apify | 2026-05-30 |
| `firecrawl_scraper_jobs.py` | Scraper de InfoJobs e Indeed vía Firecrawl | ToS de los portales prohíben scraping automatizado; RGPD con los emails extraídos | 2026-05-30 |
| `apify_jobs_scraper.py` | Scraper de InfoJobs e Indeed vía actores Apify | Mismo motivo que Firecrawl; además actor de terceros sin garantía de mantenimiento | 2026-05-30 |

Para reactivar cualquiera de estos archivos: copiar a `src/scraper/`, instalar dependencias necesarias y restaurar la ruta en `main.py`.
