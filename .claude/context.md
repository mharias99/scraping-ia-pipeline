# Contexto del Proyecto: Pipeline de Scraping + IA (2026)

Este es un sistema B2B automatizado de extracción y enriquecimiento de datos.
El objetivo es extraer datos desestructurados de webs complejas usando Playwright, 
limpiarlos con BeautifulSoup, y enviarlos a la API de Claude (Anthropic) 
para categorizarlos y estructurarlos en JSON. 
Finalmente, se exportan a un CSV limpio usando Pandas.

**Flujo Principal:**
Web -> Playwright (src/scraper) -> Texto Crudo -> Anthropic API (src/cleaner) -> Pandas -> data/output/dataset.csv
