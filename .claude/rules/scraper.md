---
paths:
  - "src/scraper/**/*.py"
---

# Reglas — Módulo Scraper

- Playwright siempre en modo `headless=True` y asíncrono (`async/await`)
- `wait_for_selector()` antes de parsear, nunca parsear HTML inmediatamente tras `goto()`
- Timeouts explícitos en cada llamada de red (mínimo 10000ms)
- Rotación de User-Agents en cada instancia de browser context
- Pausa aleatoria entre páginas: `time.sleep(random.uniform(0.8, 2.0))`
- Salida siempre como `list[dict[str, Any]]` guardada en `data/raw/`
- Nunca guardar capturas de pantalla o HTML crudo en producción
