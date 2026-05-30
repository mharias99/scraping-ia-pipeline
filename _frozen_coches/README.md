# _frozen_coches/ — Vertical Arbitraje de Vehículos

**Estado:** CONGELADA · Fecha: 2026-05-30

## Por qué está congelada

| Motivo | Detalle |
|--------|---------|
| **Datos B2C de personas físicas** | Los anuncios de Milanuncios son de particulares (personas físicas). Cualquier uso de sus datos (precio, teléfono, ubicación) para fines comerciales está sujeto a RGPD estricto: necesitas base legal explícita, registro de actividades de tratamiento y posible nombramiento de DPD. |
| **ToS Milanuncios** | Los Términos de Uso de Milanuncios prohíben expresamente el scraping automatizado sin permiso escrito. Uso comercial = riesgo de acción legal. |
| **Anti-bot agresivos** | El actor Apify `zen-studio/milanuncios-scraper` es de terceros; Milanuncios puede bloquearlo en cualquier momento, haciendo el pipeline no fiable en producción. |
| **Modelo de negocio no validado** | La hipótesis (concesionarios pagarán por leads de arbitraje) no ha sido validada con clientes reales. |

## Qué habría que resolver para reactivarla

1. **Legal:** acuerdo explícito con Milanuncios (API oficial o contrato de datos) o migrar a fuente con licencia B2B (AutoScout24, coches.net, wallapop API).
2. **RGPD:** revisar base legal para tratar datos de particulares; no almacenar más de 24h si no hay base legal clara.
3. **Scraper:** sustituir por actor oficial del portal elegido o API oficial.
4. **Validación de mercado:** confirmar al menos 1 concesionario dispuesto a pagar antes de reactivar.

## Archivos conservados

- `cars_scraper.py` — scraper Apify Milanuncios (fuente no oficial)
- `cars_enricher.py` — algoritmo de arbitraje por mediana estadística (Python puro, sin IA)

El pipeline principal (`src/main.py`) **no importa nada de esta carpeta**.
La ruta `source: milanuncios` lanza un error explícito indicando que la vertical está congelada.
