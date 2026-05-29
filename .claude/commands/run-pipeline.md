---
name: run-pipeline
argument-hint: [url-opcional]
---

Ejecuta el pipeline completo de scraping + IA:
1. Si se pasa $ARGUMENTS como URL, úsala como target del scraper; si no, usa el scraper por defecto.
2. `venv/bin/python src/scraper/quotes_scraper.py` — extrae datos a `data/raw/`.
3. Confirma que `data/raw/` tiene registros antes de continuar.
4. `venv/bin/python src/cleaner/enricher.py` — enriquece con Claude API y exporta a `data/output/`.
5. Muestra resumen: N registros extraídos → N enriquecidos → CSV generado en `data/output/`.
