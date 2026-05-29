# 📊 PROJECT DASHBOARD — App de Captación de Leads B2B
> Última actualización: 2026-05-29 · Estado global: 🟢 Operativo

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
| Deploy Streamlit Cloud | 🟡 En curso | 2026-05-29 | Repo pusheado, pendiente confirmar URL |
| Integración Firecrawl en `main.py` | ✅ Completado | 2026-05-29 | `1e9c84d` — `source: firecrawl` en YAML |
| Pipeline E2E con Firecrawl + Sheets | ✅ Completado | 2026-05-29 | 50 ofertas → 31 leads → Sheet en 98s |
| Vista visual del proyecto (Rosen Charts) | ✅ Completado | 2026-05-29 | `project-ui/` · Next.js + D3 · 5 gráficas |
| Integrar Apify para volumen masivo | ⬜ Pendiente | — | ADR-002 — cuando se supere free tier Firecrawl |
| Tests `firecrawl_scraper.py` | ⬜ Pendiente | — | Mock `V1FirecrawlApp` |
| Security review (`code-reviewer` agent) | ⬜ Pendiente | — | Sobre `src/delivery/` y `src/cleaner/` |
| Guion demo comercial 10 min | ⬜ Pendiente | — | Fase 5.5 |

---

## 2. Stack y herramientas en uso

| Herramienta / Paquete | Versión | Rol en el proyecto | Fecha alta |
|-----------------------|---------|--------------------|------------|
| Python | 3.11.15 | Runtime principal | 2026-05-29 |
| firecrawl-py | 4.28.2 | Scraping anti-bot InfoJobs + Indeed | 2026-05-29 |
| playwright | 1.60.0 | Scraping legacy (indeed_scraper, PoC) | 2026-05-29 |
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

### ADR-002 · Extracción de volumen masivo → Apify (planificado)
- **Fecha:** 2026-05-29 · **Estado:** Pendiente de implementación
- **Contexto:** Firecrawl free tier = 500 créditos/mes (~50-100 páginas/ejecución). Para clientes que necesiten >500 ofertas/semana, el coste y volumen de Firecrawl no escalan.
- **Decisión:** Usar Apify con sus actores oficiales para portales de empleo (InfoJobs, Indeed) para extracciones masivas de listas de ofertas.
- **Justificación técnica:** Actores ya mantenidos para cada portal. Proxies rotativos incluidos. Paralelización nativa. Output JSON directamente compatible con `lead_enricher.py`.
- **Justificación de negocio:** Time-to-market: horas vs semanas desarrollando scrapers robustos propios. Mantenimiento externalizado cuando los portales cambian su HTML.
- **Alternativas descartadas:**
  - *Playwright propio a escala*: requiere proxies propios (~$50-200/mes), rotación de IPs, mantenimiento de selectores CSS
  - *Firecrawl para volumen*: viable para inspección profunda oferta a oferta, no para miles de páginas
- **Trade-offs / riesgos asumidos:** Coste variable ~$0.005-0.01/run. Dependencia de proveedor externo. A 1K ofertas/día ≈ $5-10/día.

---

### ADR-003 · Inspección profunda por oferta → Firecrawl
- **Fecha:** 2026-05-29 · **Estado:** Aceptada · **Commit:** `c48a51a`
- **Contexto:** Playwright nativo bloqueado en InfoJobs (Distil/Imperva) e Indeed (bot detection en detalle). Sin descripción completa, Claude Haiku sólo puede puntuar por título → scoring de baja calidad.
- **Decisión:** Usar `firecrawl-py` v4.28.2 con `formats=["markdown"]` para leer contenido de InfoJobs e Indeed, parseando el markdown resultante con regex propios.
- **Justificación técnica:** Firecrawl gestiona render JS + cookies de sesión + fingerprint de browser + proxy residencial. InfoJobs: 19KB de contenido real vs 37KB de CAPTCHA page con Playwright. Indeed: descripción completa disponible.
- **Justificación de negocio:** Pipeline validado E2E: 50 ofertas → 31 leads (11 HIGH + 13 MEDIUM) en 98s. Sin Firecrawl, solo 16 ofertas con datos insuficientes.
- **Alternativas descartadas:**
  - *Playwright + playwright-stealth*: API incompatible con Playwright 1.60
  - *Proxies residenciales propios*: $50-200/mes, gestión compleja, ROI negativo en PoC
  - *Firecrawl `extract` mode*: timeout en 35s (LLM + stealth combinados)
- **Trade-offs / riesgos asumidos:** LinkedIn bloqueado (`WebsiteNotSupportedError`). Free tier = 500 créditos/mes → Plan de pago ($19/mes) necesario en producción.

---

## 5. Áreas de mejora / Deuda técnica

| Tema | Síntoma observado | Impacto | Acción propuesta |
|------|-------------------|---------|------------------|
| InfoJobs: volumen bajo | Solo 5 ofertas/query (primera página) | Alto | Implementar paginación en Firecrawl o migrar a Apify |
| Indeed: artefactos HTML | Empresa captura `<br>` y algunos links de nav pasan filtros | Medio | Mejorar regex + añadir lista de stopwords |
| Firecrawl créditos | 500 créditos/mes free → ~50 ejecuciones/mes máx | Alto | Plan de pago $19/mes o Apify para volumen |
| Tests Firecrawl scraper | `firecrawl_scraper.py` sin cobertura pytest | Medio | Mock `V1FirecrawlApp` con `unittest.mock` |
| Security review pendiente | `src/delivery/` y `src/cleaner/` sin revisión formal | Alto | Invocar agente `code-reviewer` |
| Queries en español | InfoJobs devuelve resultados no relacionados (call center, seguros) | Medio | Refinar queries + post-filtro por sector |
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

## 7. Métricas por sesión

| Fecha | Tareas cerradas | Tokens aprox. | Tiempo aprox. | Coste estimado |
|-------|-----------------|---------------|---------------|----------------|
| 2026-05-29 | 20 unidades de trabajo | ~500K tokens (sesión larga) | ~3h | Anthropic pipeline: ~$0.01/ejecución · Firecrawl: ~10 créditos/ejecución |
| — | Pipeline E2E (50 ofertas) | ~50K tokens Claude Haiku | 98.3s | ~$0.003-0.005 |
| — | 39 tests en verde | — | 1.34s | — |

---

## 8. Próximos pasos

- [ ] Confirmar URL pública de Streamlit Cloud funcionando con `data/sample/`
- [ ] Completar vista visual Rosen Charts (`project-ui/`)
- [ ] Integrar Apify para volumen masivo (>100 ofertas/query)
- [ ] Tests `firecrawl_scraper.py` con mock del SDK
- [ ] Security review con agente `code-reviewer`
- [ ] Guion demo comercial 10 min (Fase 5.5)

---

## 9. Changelog

| Fecha | Cambio |
|-------|--------|
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
