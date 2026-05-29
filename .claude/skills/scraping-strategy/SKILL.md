---
name: scraping-strategy
description: Aplica técnicas anti-detección y resiliencia cuando el sitio bloquea o tiene protección.
user-invocable: true
---

# Estrategia Anti-Bloqueo

## Identidad del browser
- User-Agent rotativo (lista de 5+ agentes reales de Chrome/Firefox)
- `viewport`: 1280x800, `locale`: es-ES o en-US según el sitio
- `geolocation` y `timezone` coherentes con el User-Agent

## Comportamiento humano
- Pausa entre páginas: `random.uniform(1.5, 3.5)` segundos
- Scroll suave antes de extraer: `page.evaluate("window.scrollBy(0, 300)")`
- Mouse move aleatorio si hay detección de bots

## Reintentos
- Retry con backoff exponencial: 1s → 2s → 4s (máx 3 intentos)
- Si status 429 o 403: pausa 30s antes de reintentar
- Si el sitio usa Cloudflare: usar `playwright-stealth` o cambiar a requests + cloudscraper

## Selectores CSS
- Siempre usar `wait_for_selector()` con timeout explícito
- Preferir selectores semánticos (`[data-testid]`, clases estables) sobre índices
- Verificar existencia con `page.query_selector()` antes de `.inner_text()`
