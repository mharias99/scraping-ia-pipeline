---
name: new-scraper
argument-hint: [url-del-sitio]
---

Crea un nuevo scraper para $ARGUMENTS:
1. Analiza la estructura de $ARGUMENTS con Playwright (abre la página, inspecciona el DOM).
2. Identifica los selectores CSS de los datos relevantes.
3. Crea `src/scraper/<nombre_sitio>_scraper.py` siguiendo el patrón de `quotes_scraper.py`.
4. Incluye: paginación automática, rotación de User-Agents, manejo de timeouts, salida a `data/raw/`.
5. Ejecuta el script para confirmar que extrae datos correctamente.
6. Reporta los campos extraídos y un ejemplo de registro.
