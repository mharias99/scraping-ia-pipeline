# 📊 PROJECT DASHBOARD — Motor de Captación de Leads (Stack Legal)
> Última actualización: 2026-05-30 · Estado global: 🟢 Operativo · Rama activa: `refactor/stack-legal`

## Verticales activas

| Vertical | Fuente de datos | Estado |
|----------|----------------|--------|
| **Auditoría digital PYMEs** | Google Places API oficial | 🟢 Activa |
| **Empleo B2B (leads ETT/RRHH)** | API InfoJobs (validación interna) + Agregador con licencia (producción) | 🟡 En refactor |

## Verticales congeladas

| Vertical | Motivo | Fecha congelación |
|----------|--------|-------------------|
| **Arbitraje Coches** | Datos B2C personas físicas (RGPD), ToS Milanuncios, actor Apify sin garantía | 2026-05-30 |

Ver condiciones de reactivación en `_frozen_coches/README.md`

---

---

## 1. Timeline / Estado

| Hito | Estado | Fecha | Notas |
|------|--------|-------|-------|
| Estructura del proyecto + Python 3.11 | ✅ Completado | 2026-05-29 | `467f760` — 35 archivos, entorno venv |
| 7 agentes Claude + reglas + hooks | ✅ Completado | 2026-05-29 | `.claude/agents/`, `.claude/rules/` |
| Scraper PoC (quotes.toscrape.com) | ✅ Completado | 2026-05-29 | 50 registros, 7.7s |
| Pipeline PoC E2E validado | ✅ Completado | 2026-05-29 | 50 → CSV en 31.9s, ~$0.001 |
| Scraper InfoJobs (Playwright) | ❌ Bloqueado | 2026-05-29 | Distil/Imperva — CAPTCHA inmediato |
| Scraper Indeed (Playwright) | ⚠️ Parcial | 2026-05-29 | Fase 1 OK, fase 2 (detalle) bloqueada |
| **Scraper Firecrawl** (InfoJobs + Indeed) | ✅ Completado | 2026-05-29 | 50 ofertas únicas, anti-bot bypasseado |
| Lead enricher B2B + LOPD | ✅ Completado | 2026-05-29 | JSON schema, lead_score, sanitización emails |
| `config.yaml` por cliente | ✅ Completado | 2026-05-29 | `configs/cliente_ejemplo.yaml` |
| Logging rotativo a fichero | ✅ Completado | 2026-05-29 | `logs/pipeline.log`, 30 días |
| Conector Google Sheets | ✅ Completado | 2026-05-29 | Service Account, colores por score |
| Conector CRM (HubSpot + Pipedrive CSV) | ✅ Completado | 2026-05-29 | `src/delivery/crm_exporter.py` |
| Dashboard Streamlit (demo comercial) | ✅ Completado | 2026-05-29 | `src/dashboard/app.py`, :8501 |
| Deploy Streamlit Cloud | ✅ Completado | 2026-05-29 | https://mharias99-scraping-ia-pipeline-src-dashboard-app-py.streamlit.app |
| Integración Firecrawl en `main.py` | ✅ Completado | 2026-05-29 | `1e9c84d` — `source: firecrawl` en YAML |
| Pipeline E2E con Firecrawl + Sheets | ✅ Completado | 2026-05-29 | 50 ofertas → 31 leads → Sheet en 98s |
| Vista visual del proyecto (Rosen Charts) | ✅ Completado | 2026-05-29 | `project-ui/` · Next.js + D3 · 5 gráficas |
| Rediseño UI premium + 4 páginas | ✅ Completado | 2026-05-30 | LeadOS design system · sidebar nav · framer-motion · B2B/Coches/Digital pages |
| Dashboard live via stats.json    | ✅ Completado | 2026-05-30 | `src/delivery/stats_exporter.py` · `data/web/stats.json` · `lib/stats.ts` · SSR sin rebuild |
| Fix Google Sheets dashboard      | ✅ Completado | 2026-05-30 | `dashboard_builder.py`: gspread 6.x `update(values, range)` + batch writes (2 calls vs 20+) + 3 pipelines |
| Correcciones AUDIT_REPORT.md     | ✅ Completado | 2026-05-30 | 9 fixes: .gitignore, req.txt pin, permanently_closed, N<5 guard, CRM type-gate, _apify_base, legacy/, 29 tests nuevos (100 total) |
| Dashboards Sheets especializados | ✅ Completado | 2026-05-30 | 3 dashboards distintos: B2B (embudo+outreach), Cars (margen€+modelos), Digital (debilidades+call-ready) · KPIs específicos por vertical |
| Integrar Apify para volumen masivo | ✅ Completado | 2026-05-29 | `src/scraper/apify_scraper.py` · `source: "both"` en YAML · coexiste con Firecrawl |
| Tests `firecrawl_scraper.py` | ✅ Completado | 2026-05-29 | 32 tests en `tests/test_firecrawl_scraper.py` — suite total 71 |
| Security review (`code-reviewer` agent) | ✅ Completado | 2026-05-29 | 7 bugs corregidos en `src/delivery/` y `src/cleaner/` |
| Guion demo comercial 10 min | ✅ Completado | 2026-05-29 | `docs/DEMO_SCRIPT.md` — 10 min, objeciones, precios, plan de fallo |

---

## 2. Stack y herramientas en uso

| Herramienta / Paquete | Versión | Rol en el proyecto | Fecha alta |
|-----------------------|---------|--------------------|------------|
| Python | 3.11.15 | Runtime principal | 2026-05-29 |
| **googlemaps** | **4.10.0** | **Google Places API oficial (Digital)** | **2026-05-30** |
| firecrawl-py | 4.28.2 | Inspección web oficial de empresas (web_inspector) | 2026-05-30 |
| playwright | 1.60.0 | Scraping legacy (deprecated, PoC) | 2026-05-29 |
| beautifulsoup4 | 4.14.3 | Parsing HTML/markdown scrapeado | 2026-05-29 |
| anthropic | 0.105.2 | Enriquecimiento IA (Claude Haiku tool_use) | 2026-05-29 |
| pandas | 3.0.3 | DataFrames, limpieza, export CSV | 2026-05-29 |
| gspread | 6.2.1 | Escritura Google Sheets via Service Account | 2026-05-29 |
| gspread-formatting | — | Colores por lead_score en Sheets | 2026-05-29 |
| google-auth | ≥2.0.0 | OAuth Service Account | 2026-05-29 |
| streamlit | 1.58.0 | Dashboard demo comercial (leads) | 2026-05-29 |
| plotly | 6.7.0 | Gráficos interactivos en Streamlit | 2026-05-29 |
| pyyaml | ≥6.0 | Config por cliente (`configs/*.yaml`) | 2026-05-29 |
| python-dotenv | 1.2.2 | Gestión de secrets desde `.env` | 2026-05-29 |
| pytest | 9.0.3 | Suite de tests (39 tests en verde) | 2026-05-29 |
| pytest-asyncio | 1.4.0 | Tests async para Playwright | 2026-05-29 |
| ruff | 0.15.15 | Linting + formato Python | 2026-05-29 |
| mypy | 2.1.0 | Type checking Python | 2026-05-29 |
| apify-client | 3.0.2 | Volumen masivo InfoJobs + Indeed — actores `unfenced-group` + `misceres` | 2026-05-29 |
| **Rosen Charts** | latest | Vista visual del proyecto (React/d3) | 2026-05-29 |
| Skills instaladas | — | firecrawl-agent, data-pipeline, pytest-testing, pandas-data-analysis, context-compressor, token-optimizer, token-dashboard | 2026-05-29 |

---

## 3. Herramientas evaluadas y descartadas

| Herramienta | Para qué | Motivo del descarte | Fecha |
|-------------|----------|---------------------|-------|
| Playwright nativo en InfoJobs | Scraping de ofertas | Distil/Imperva anti-bot: CAPTCHA inmediato en headless. `canonical → /distil/captcha.xhtml` | 2026-05-29 |
| Playwright en Indeed (fase 2) | Descripción completa de ofertas | Bot detection bloquea páginas de detalle. "Additional Verification Required" | 2026-05-29 |
| playwright-stealth | Evasión bot detection | API incompatible con Playwright 1.60 (`stealth_async` no existe, `Stealth.__aenter__` falla) | 2026-05-29 |
| LinkedIn Jobs (scraping) | Fuente de ofertas premium | `WebsiteNotSupportedError` en Firecrawl (acuerdo comercial). API oficial: $1K+/mes | 2026-05-29 |
| Firecrawl `extract` mode + `proxy=stealth` | Extracción estructurada directa | Timeout en 35s (LLM extraction + stealth proxy combinados). Sustituido por `markdown` + parser regex | 2026-05-29 |
| bobmatnyc/session-compression (skill) | Compresión de contexto | Skill renombrada a `mcp-protocol-builder` en el repo, ya no disponible | 2026-05-29 |

---

## 4. ADR — Decisiones Arquitectónicas

### ADR-001 · Almacenamiento de leads → Google Sheets con Service Account
- **Fecha:** 2026-05-29 · **Estado:** Aceptada
- **Contexto:** El pipeline genera un CSV de leads cualificados que debe llegar al cliente PYME de forma usable y sin fricción técnica.
- **Decisión:** Entregar los leads directamente en Google Sheets del cliente usando `gspread` con autenticación Service Account (JSON key descargado de Google Cloud Console).
- **Justificación técnica:** Setup en <10 min. SDK Python maduro. Sin gestión de servidor. Colores y formato aplicados automáticamente. Actualización idempotente (clear + rewrite).
- **Justificación de negocio:** El cliente PYME ya trabaja en Sheets — cero fricción. Demo impresionante: datos aparecen en <2 min. Coste cero (free tier Google Sheets API).
- **Alternativas descartadas:**
  - *PostgreSQL/SQLite*: cliente no ve los datos sin herramienta técnica adicional
  - *OAuth nativo (usuario)*: requiere flujo interactivo en cada ejecución; Service Account es headless
  - *Airtable*: coste mensual + API con rate limits más restrictivos
- **Trade-offs / riesgos asumidos:** Límite 300 writes/min → cuello de botella a >500 leads/ejecución. Sin historial de versiones nativo. Escalabilidad limitada a ~10K registros.

---

### ADR-002 · Extracción de volumen masivo → Apify + Firecrawl coexistiendo
- **Fecha:** 2026-05-29 · **Estado:** Implementado · **Commit:** pendiente
- **Contexto:** Firecrawl free tier = 500 créditos/mes (~50-100 páginas/ejecución). Para clientes que necesiten >500 ofertas/semana, el coste y volumen de Firecrawl no escalan.
- **Decisión:** Usar Apify con sus actores oficiales para portales de empleo (InfoJobs, Indeed) para extracciones masivas de listas de ofertas.
- **Justificación técnica:** Actores ya mantenidos para cada portal. Proxies rotativos incluidos. Paralelización nativa. Output JSON directamente compatible con `lead_enricher.py`.
- **Justificación de negocio:** Time-to-market: horas vs semanas desarrollando scrapers robustos propios. Mantenimiento externalizado cuando los portales cambian su HTML.
- **Alternativas descartadas:**
  - *Playwright propio a escala*: requiere proxies propios (~$50-200/mes), rotación de IPs, mantenimiento de selectores CSS
  - *Firecrawl para volumen*: viable para inspección profunda oferta a oferta, no para miles de páginas
- **Trade-offs / riesgos asumidos:** Coste variable ~$0.005-0.01/run. Dependencia de proveedor externo. A 1K ofertas/día ≈ $5-10/día.

---

### ADR-003 · Inspección profunda por oferta → Firecrawl (solo webs oficiales de empresa)
- **Fecha:** 2026-05-29 (actualizado 2026-05-30) · **Estado:** Aceptada (alcance reducido)
- **Decisión actualizada:** Firecrawl se usa SOLO para inspeccionar la web oficial de la empresa (no los portales de empleo). El scraping de InfoJobs/Indeed se ha eliminado por ToS.
- **Uso actual:** `web_inspector.py` visita la web pública de cada empresa para detectar HTTPS, reservas, píxeles → inputs para el scoring Digital y el call_script de Empleo.
- **Trade-offs:** Solo se extrae lo disponible públicamente en la web oficial de la empresa.

---

### ADR-004 · Fuente de empleo → Agregador con licencia comercial (producción)
- **Fecha:** 2026-05-30 · **Estado:** Pendiente de confirmar proveedor
- **Contexto:** El scraping de InfoJobs/Indeed viola sus ToS. La API oficial de InfoJobs prohíbe el uso comercial de los datos para contactar empresas fuera de la plataforma.
- **Decisión:** Para producción, usar un agregador de empleo con licencia comercial explícita (TheirStack, LoopCV, o equivalente). La licencia ampara el uso de los datos para identificar empresas con necesidad activa de contratación y contactarlas con una oferta de servicio ETT.
- **Justificación técnica:** Sin mantenimiento de anti-bot, datos enriquecidos (repost_count, first_seen), multi-portal por diseño.
- **Justificación de negocio:** Coste de licencia (~$100-300/mes) << coste de proxies + tiempo de ingeniería + riesgo legal del scraping.
- **Alternativas descartadas:**
  - *Scraping de portales*: ToS prohíben uso comercial; riesgo legal real en producción
  - *API InfoJobs en producción*: sus condiciones prohíben redistribución comercial del contenido
- **⚠️ Nota legal:** El uso de datos de vacantes para contactar a empresas bajo "interés legítimo LSSI/RGPD" es un marco A VALIDAR CON UN ABOGADO antes del primer cliente de pago. Esta decisión refleja la dirección técnica, no un dictamen legal.

---

### ADR-005 · API InfoJobs (validación interna únicamente)
- **Fecha:** 2026-05-30 · **Estado:** Aceptada
- **Contexto:** Antes de comprometerse con el coste de un agregador con licencia, se necesita validar que el scoring de "vacante caliente" produce leads que una ETT compraría.
- **Decisión:** Usar la API oficial de InfoJobs (registro como developer, HTTP Basic auth) SOLO para validación interna del modelo de scoring. Todos los leads en este modo se marcan `uso="solo_validacion_interna"` y NUNCA entran en un flujo de contacto comercial.
- **Regla dura:** Los leads obtenidos con la API de InfoJobs en modo `validation` NO se pueden usar para contactar empresas. Los ToS de InfoJobs lo prohíben explícitamente. Esta distinción está forzada en el código (`JobSourceAdapter`): el modo `validation` marca cada lead con `uso="solo_validacion_interna"` y el modo `production` usa el agregador con licencia.
- **⚠️ Nota legal:** Igual que ADR-004 — a validar con abogado antes de producción.

---

### ADR-006 · Enriquecimiento de contacto solo a nivel empresa (no personas físicas)
- **Fecha:** 2026-05-30 · **Estado:** Aceptada
- **Decisión:** El enriquecimiento de contacto se limita al buzón GENÉRICO de la empresa (info@, rrhh@, contacto@dominio). Es dato de la persona jurídica, no de una persona física.
- **Explícitamente PROHIBIDO en el código:**
  - Extraer o inferir emails personales (nombre.apellido@empresa)
  - Teléfonos directos de individuos
  - Perfiles de LinkedIn de personas físicas
  - Waterfall enrichment (Apollo, ZoomInfo, Hunter.io, etc.) de personas
- **Motivo:** `nombre.apellido@empresa` y móviles personales son datos personales bajo RGPD Art. 4(1). El buzón genérico de empresa no es dato de persona física identificable → fuera del ámbito del RGPD personal.
- **Consecuencia práctica:** El lead se entrega a nivel empresa; la ETT preguntará por el responsable al llamar. Esto es el modelo de negocio estándar de las ETTs.
- **⚠️ Nota legal:** El marco de "interés legítimo" para contactar empresas vía buzón genérico es razonable pero A VALIDAR CON UN ABOGADO antes del primer cliente de pago.

---

## Herramientas descartadas (con motivo)

| Herramienta | Para qué | Motivo del descarte | Fecha |
|-------------|----------|---------------------|-------|
| Scraper Apify Google Maps | Extracción de negocios locales | ToS Google Maps prohíbe scraping; riesgo de baneo/suspensión | 2026-05-30 |
| Firecrawl para portales de empleo | Bypass anti-bot InfoJobs/Indeed | ToS portales prohíben scraping; RGPD con emails extraídos | 2026-05-30 |
| Apify actores InfoJobs/Indeed | Volumen masivo de ofertas | Mismo motivo que Firecrawl; actor terceros sin garantía | 2026-05-30 |
| Waterfall enrichment (Apollo/ZoomInfo) | Datos de contacto personales | Datos de personas físicas bajo RGPD; no permitido en este modelo | 2026-05-30 |
| LinkedIn scraping / Voyager API | Perfiles de responsables | ToS LinkedIn + RGPD estricto sobre datos personales | 2026-05-30 |

## 5. Áreas de mejora / Deuda técnica

| Tema | Síntoma observado | Impacto | Acción propuesta |
|------|-------------------|---------|------------------|
| InfoJobs: volumen bajo | ~~Solo 5 ofertas/query~~ → hasta 15/query con paginación 3 páginas | ~~Alto~~ Resuelto | Paginación implementada en `run_firecrawl_scraper(max_pages_per_query=3)` |
| Indeed: artefactos HTML | ~~Empresa captura `<br>` y algunos links de nav pasan filtros~~ → `_clean_indeed_company()` limpia códigos postales, HTML, markdown | ~~Medio~~ Resuelto | `_clean_indeed_company()` en `firecrawl_scraper.py` |
| Firecrawl créditos | 500 créditos/mes free → ~50 ejecuciones/mes máx | Alto | Plan de pago $19/mes o Apify para volumen |
| Tests Firecrawl scraper | `firecrawl_scraper.py` sin cobertura pytest | Medio | Mock `V1FirecrawlApp` con `unittest.mock` |
| Security review pendiente | `src/delivery/` y `src/cleaner/` sin revisión formal | Alto | Invocar agente `code-reviewer` |
| Queries en español | ~~InfoJobs devuelve resultados no relacionados~~ → queries específicas por portal en `configs/*.yaml` | ~~Medio~~ Resuelto | `infojobs_queries` + `indeed_queries` en config + `ScraperConfig` |
| Sheets rate limit | A >300 leads puede alcanzar límite API | Medio | Escribir en lotes de 100 con `time.sleep(1)` |

---

## 6. Riesgos y bloqueos abiertos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Firecrawl cambia ToS o precio | Media | Alto | Plan B: Apify actores para InfoJobs/Indeed |
| Google Sheets API quota excedida | Baja (PoC) | Medio | Migrar a BigQuery o escribir en lotes |
| Anthropic rate limit en producción | Baja | Alto | Retry exponencial implementado + reducir batch_size |
| InfoJobs cambia estructura HTML | Alta (6-12m) | Medio | Firecrawl actualiza parsers automáticamente |
| Streamlit Cloud: paths relativos | Media | Bajo | `data/sample/leads_sample.csv` como fallback ya implementado |

---

## 7. Volumen esperado en producción

> Basado en pruebas reales con las APIs en free tier. Escalado a planes de pago (~€60/mes en APIs).

| Pipeline | Free (ahora) | Producción (€60/mes APIs) |
|----------|-------------|--------------------------|
| B2B leads únicos/día | 20-30 | **80-150** |
| B2B leads únicos/semana | ~100 | **400-600** |
| B2B leads únicos/mes | ~300 | **1.500-2.500** |
| Coches oportunidades HIGH/día | ~15 | **50-100** |
| Auditoría digital negocios HIGH/día | ~10 (1 ciudad) | **40-80** (4 ciudades) |

**Techo real:** InfoJobs + Indeed España tienen ~50.000 ofertas activas de administrativo/data entry/mes.
Con queries afinadas por sector, **2.000+ leads únicos/mes sin repetir** por categoría.

**Coste APIs en producción:**
- Firecrawl $49/mes → 10.000 créditos (~1.000 ejecuciones)
- Apify $49/mes → créditos suficientes para 2.000 runs/mes
- Anthropic Claude Haiku ~$0.003-0.005/ejecución de 100 leads

---

## 8. Métricas por sesión

| Fecha | Tareas cerradas | Tokens aprox. | Tiempo aprox. | Coste estimado |
|-------|-----------------|---------------|---------------|----------------|
| 2026-05-29 | 20 unidades de trabajo | ~500K tokens (sesión larga) | ~3h | Anthropic pipeline: ~$0.01/ejecución · Firecrawl: ~10 créditos/ejecución |
| — | Pipeline E2E (50 ofertas) | ~50K tokens Claude Haiku | 98.3s | ~$0.003-0.005 |
| — | 39 tests en verde | — | 1.34s | — |

---

## 8. Próximos pasos

> Ordenados por prioridad. Cada bloque incluye qué hacer, por qué es urgente y cómo arrancarlo.

---

### 🔴 CRÍTICO — Hacer antes de mostrar el producto a un cliente

**A. ~~Confirmar deploy Streamlit Cloud~~ ✅ COMPLETADO**
- URL pública confirmada: https://mharias99-scraping-ia-pipeline-src-dashboard-app-py.streamlit.app
- Sirviendo `data/sample/leads_sample.csv` como fallback. Listo para compartir con clientes.

**B + C + D + E + F ✅ TODOS COMPLETADOS — Ver changelog**

**B. ~~Volumen de ofertas insuficiente~~ ✅ COMPLETADO**
- Paginación implementada en `run_firecrawl_scraper(max_pages_per_query=3)` — InfoJobs e Indeed.
- URL builder por fuente en `PAGINATION` dict: InfoJobs usa `&page=N`, Indeed usa `&start=(N-1)*10`.
- Stop automático si una página no devuelve resultados nuevos.
- Capacidad: 5 queries × 2 fuentes × 3 páginas × ~5 ofertas = ~150 ofertas/ejecución (antes: ~25).

**C. Calidad de datos de Indeed (ruido en empresa/ubicación)**
- **Qué:** El campo `company` en resultados de Indeed sigue capturando artefactos: códigos postales pegados al nombre (`IGTP08916 Badalona`), tags HTML residuales. Claude los puntúa igualmente pero la presentación al cliente es sucia.
- **Por qué ahora:** Si enseñas el Sheet a un cliente y ve "IGTP08916 Badalona" en la columna Empresa, pierde confianza.
- **Cómo:** En `firecrawl_scraper.py → parse_indeed_markdown()`, añadir limpieza post-extracción: separar código postal del nombre de empresa, strip de dígitos al inicio.
- **Archivo:** `src/scraper/firecrawl_scraper.py` línea ~105

---

### 🟡 IMPORTANTE — Hacer antes de primer cliente de pago

**D. Security review del código de entrega**
- **Qué:** Los módulos `src/delivery/` (Sheets, CRM) y `src/cleaner/` (enricher, lead_enricher) nunca han sido revisados formalmente.
- **Por qué:** Manejan credenciales Google y API keys de Anthropic. Un leak en producción es un problema legal.
- **Cómo:** Ejecutar `/code-review` o invocar el agente `code-reviewer` sobre esos dos módulos.
- **Tiempo estimado:** 15 min.

**E. Tests para `firecrawl_scraper.py`**
- **Qué:** El scraper principal no tiene cobertura de tests. Si se rompe (cambio en InfoJobs/Indeed), no hay alerta automática.
- **Cómo:** Crear `tests/test_firecrawl_scraper.py` mockeando `V1FirecrawlApp` con `unittest.mock.MagicMock`. Cubrir: parser InfoJobs, parser Indeed, filtros de ruido, deduplicación.
- **Archivo de referencia:** `tests/test_scraper.py` (patrón ya establecido).

**F. Queries irrelevantes en InfoJobs**
- **Qué:** La query "data entry" en InfoJobs devuelve teleoperadores de seguros (GRUPO CONSTANT), farmacéuticos, etc. — empresas que NO son leads de automatización.
- **Por qué:** Las queries son demasiado genéricas para InfoJobs que interpreta diferente al motor de Indeed.
- **Cómo:** En `configs/cliente_ejemplo.yaml`, añadir queries más específicas para InfoJobs: `"operador introducción datos"`, `"grabador datos excel"`, `"administrativo base de datos"`. Crear un campo `infojobs_queries` separado de `indeed_queries` en el config.
- **Archivo:** `src/config.py` + `configs/cliente_ejemplo.yaml`

---

### 🟢 MEJORA — Para escalar el negocio

**G. ~~Guion demo comercial~~ ✅ COMPLETADO**
- `docs/DEMO_SCRIPT.md`: script de 10 min, comandos exactos, 5 objeciones con respuesta, tabla de precios, plan de fallo, pasos post-reunión.

**H. Créditos Firecrawl: pasar a plan de pago**
- **Qué:** Free tier = 500 créditos/mes. Con 10 requests por ejecución, son 50 ejecuciones/mes máx. En producción con varios clientes se agotará.
- **Cuándo:** Cuando tengas el primer cliente de pago.
- **Plan:** $19/mes → 3.000 créditos · $49/mes → 10.000 créditos.
- **URL:** firecrawl.dev/pricing

**I. Primer YAML de cliente real**
- **Qué:** Duplicar `configs/cliente_ejemplo.yaml` → `configs/cliente_[nombre].yaml` con las queries específicas del sector del cliente, su Spreadsheet ID y su nombre.
- **Cómo:** `cp configs/cliente_ejemplo.yaml configs/cliente_acme.yaml` → editar las 4 líneas relevantes.
- **Tiempo:** 5 minutos.

---

## 9. Changelog

| Fecha | Cambio |
|-------|--------|
| 2026-05-29 | Integración Apify: `apify_scraper.py` + `source: "both"` · Firecrawl=calidad · Apify=volumen · dedup unificado |
| 2026-05-29 | Guion demo comercial: `docs/DEMO_SCRIPT.md` — 10 min, comandos, 5 objeciones, precios, plan de fallo |
| 2026-05-29 | Security review `src/delivery/` + `src/cleaner/`: 7 bugs corregidos (KeyError, TypeError, except genérico, off-by-one, batch formatting) |
| 2026-05-29 | Tests `firecrawl_scraper.py`: 32 tests nuevos → suite total 71 en verde |
| 2026-05-29 | Queries por portal: `infojobs_queries` + `indeed_queries` en config + `ScraperConfig` + `step_scrape` |
| 2026-05-29 | Indeed calidad: `_clean_indeed_company()` elimina códigos postales, HTML, markdown del campo empresa |
| 2026-05-29 | Paginación InfoJobs + Indeed: `max_pages_per_query=3`, stop automático sin resultados nuevos |
| 2026-05-29 | Deploy Streamlit Cloud confirmado: https://mharias99-scraping-ia-pipeline-src-dashboard-app-py.streamlit.app |
| 2026-05-30 | Rediseño UI premium: sidebar nav · glassmorphism · framer-motion · 4 páginas (Home/B2B/Coches/Digital) · animaciones CSS + número count-up |
| 2026-05-29 | Vista visual Rosen Charts completada: `project-ui/` Next.js + D3 · funnel, donut, bar, breakdown, metrics · build OK |
| 2026-05-29 | Creado `PROJECT_DASHBOARD.md` con histórico completo · plantilla oficial aplicada |
| 2026-05-29 | Firecrawl integrado en `main.py` vía `cfg.scraper.source` — `1e9c84d` |
| 2026-05-29 | `firecrawl_scraper.py`: InfoJobs + Indeed, markdown parsing, 50 ofertas únicas |
| 2026-05-29 | Pipeline E2E Firecrawl + Claude + Sheets validado: 50 → 31 leads en 98s |
| 2026-05-29 | CRM export automático: `hubspot_*.csv` + `pipedrive_*.csv` |
| 2026-05-29 | Logging rotativo `logs/pipeline.log` (30 días retención) |
| 2026-05-29 | `config.yaml` por cliente + `src/config.py` tipado con dataclasses |
| 2026-05-29 | Google Sheets export validado: 31 leads, colores por score, 15s |
| 2026-05-29 | Dashboard Streamlit + deploy a Streamlit Cloud |
| 2026-05-29 | Playwright nativo descartado para InfoJobs (Distil) e Indeed detalle |
| 2026-05-29 | Lead enricher B2B validado: 50 → 32 leads cualificados |
| 2026-05-29 | Pipeline PoC validado: quotes.toscrape.com → CSV en 31.9s |
| 2026-05-29 | Estructura inicial + Python 3.11 + 39 tests en verde |
