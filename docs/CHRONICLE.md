# CHRONICLE — Pipeline Scraping + IA

**Proyecto:** Sistema B2B de extracción y enriquecimiento de datos  
**Tech Lead:** Claude Sonnet 4.6  
**Inicio:** 2026-05-29  

---

## Timeline de Desarrollo — PoC Roadmap

### FASE 0 — Fundamentos ✅ COMPLETADA (2026-05-29)
> Objetivo: entorno reproducible, estructura profesional y pipeline esqueleto funcionando.

| # | Tarea | Agente | Estado |
|---|-------|--------|--------|
| 0.1 | Estructura de carpetas y archivos base | — | ✅ |
| 0.2 | Entorno virtual Python 3.11 + dependencias | — | ✅ |
| 0.3 | `.claude/` con 7 agentes, 3 comandos, hooks, rules, skills | — | ✅ |
| 0.4 | Scraper funcional: `quotes_scraper.py` (50 registros, 5 páginas) | `scraper-pro` | ✅ |
| 0.5 | Enricher esqueleto: `enricher.py` (tool_use, retry, export CSV) | `data-cleaner` | ✅ |
| 0.6 | `main.py` orquestador con flags `--skip-scrape` / `--skip-enrich` | — | ✅ |
| 0.7 | 39 tests pytest en verde (mocks red y API) | `test-writer` | ✅ |
| 0.8 | Git init + commit inicial | — | ✅ |

---

### FASE 1 — PoC Validada ✅ COMPLETADA (2026-05-29)
> Objetivo: ejecutar el pipeline E2E con datos reales y validar la calidad del output de Claude.

| # | Tarea | Agente | Estado |
|---|-------|--------|--------|
| 1.1 | Cargar créditos en Anthropic Console | — | ✅ |
| 1.2 | Ejecutar `main.py` completo y revisar `data/output/dataset.csv` | `pipeline-orchestrator` | ✅ |
| 1.3 | Validar calidad del enriquecimiento: categorías, sentimientos, temas | `data-cleaner` | ✅ |
| 1.4 | Ajustar el prompt del enricher si los resultados no son precisos | `data-cleaner` | ✅ Sin ajustes necesarios |
| 1.5 | Medir coste real por registro y tiempo total del pipeline | — | ✅ 31.9s · ~$0.001 total |

**Resultado:** 50/50 registros enriquecidos · 7 columnas · 78% sentimiento positivo · categorías coherentes.

---

### FASE 2 — Escalado del Scraper
> Objetivo: hacer el scraper genérico para poder apuntar a cualquier sitio B2B objetivo real.

| # | Tarea | Agente | Estado |
|---|-------|--------|--------|
| 2.1 | Identificar el sitio B2B objetivo real del cliente | — | ⏳ |
| 2.2 | Crear scraper específico con `/new-scraper [url]` | `scraper-pro` | ⏳ |
| 2.3 | Implementar anti-detección avanzada (skill: `scraping-strategy`) | `scraper-pro` | ⏳ |
| 2.4 | Probar con sitio real y medir tasa de éxito por página | `scraper-pro` | ⏳ |
| 2.5 | Añadir soporte multi-sitio: config YAML con targets | `scraper-pro` | ⏳ |

**Criterio de éxito Fase 2:** >90% de páginas scrapeadas sin bloqueo en 3 ejecuciones consecutivas.

---

### FASE 3 — Enriquecimiento Avanzado con IA
> Objetivo: schema de salida adaptado al caso de uso B2B real, con campos de negocio y cumplimiento legal.

| # | Tarea | Agente | Estado |
|---|-------|--------|--------|
| 3.1 | Definir schema de campos B2B necesarios (empresa, sector, contacto, etc.) | `data-cleaner` | ⏳ |
| 3.2 | Actualizar `ENRICH_TOOL` con el nuevo schema en `enricher.py` | `data-cleaner` | ⏳ |
| 3.3 | Implementar procesamiento en batch con prompt caching (reducir coste) | `data-cleaner` | ⏳ |
| 3.4 | Validación automática del output: columnas requeridas, tipos, nulos | `data-cleaner` | ⏳ |
| 3.5 | **Sanitización Legal LOPD:** filtro IA que elimina emails personales (gmail/hotmail/yahoo) y conserva solo emails corporativos públicos (dominio empresa) | `data-cleaner` | ⏳ |
| 3.6 | Tests de regresión para el nuevo schema + tests del filtro LOPD | `test-writer` | ⏳ |

**Criterio de éxito Fase 3:** Coste por registro <$0.005 · 0% emails personales en el output · calidad validada.

---

### FASE 4 — Productización (Modelo DaaS)
> Objetivo: pipeline robusto alojado en nuestra infraestructura. El cliente **no toca código** — solo recibe datos limpios.
> Decisión estratégica: eliminamos la entrega de Docker/README al cliente final. Nosotros operamos el servicio.

| # | Tarea | Agente | Estado |
|---|-------|--------|--------|
| 4.1 | Config externa: `config.yaml` con URL, campos, batch_size, modelo | — | ⏳ |
| 4.2 | Logging estructurado a fichero + rotación diaria | `python-debugger` | ⏳ |
| 4.3 | Notificación al finalizar: webhook o email interno al operador | — | ⏳ |
| 4.4 | Revisión de seguridad final del pipeline | `code-reviewer` | ⏳ |
| 4.5 | Documentación interna de operaciones (para el equipo, no para el cliente) | — | ⏳ |

**Criterio de éxito Fase 4:** Pipeline ejecutable por el equipo interno con un solo comando. Cliente no necesita intervención técnica.

---

### FASE 5 — La Última Milla (Entrega y Visualización)
> Objetivo: llevar los datos limpios hasta donde el cliente PYME ya trabaja, sin fricción técnica. Demo visual lista para reuniones comerciales.

| # | Tarea | Agente | Estado |
|---|-------|--------|--------|
| 5.1 | **Conector Google Sheets:** script `src/delivery/sheets_exporter.py` que inyecta el CSV directamente en la hoja del cliente vía Google Sheets API (oauth2 + gspread) | `data-cleaner` | ⏳ |
| 5.2 | **Conector CRM genérico:** exportador a formato compatible con HubSpot/Pipedrive (CSV con columnas mapeadas al schema del CRM) | `data-cleaner` | ⏳ |
| 5.3 | **Dashboard Streamlit:** `src/dashboard/app.py` con métricas clave: total leads, distribución por sector, top empresas, filtros interactivos, exportar selección a CSV | — | ⏳ |
| 5.4 | Despliegue del dashboard en Streamlit Cloud (gratuito, URL pública para demos) | — | ⏳ |
| 5.5 | **Demo comercial:** guion de demo de 10 min con datos reales para reuniones de ventas con PYMEs | — | ⏳ |
| 5.6 | Tests del conector Sheets (mock de la API de Google) | `test-writer` | ⏳ |

**Criterio de éxito Fase 5:** Comercial puede hacer demo en vivo en <10 min sin conocimientos técnicos. Cliente recibe datos en su Google Sheets en <2 min tras la ejecución del pipeline.

---

## Log de Ejecución

| Fecha | Acción | Resultado |
|-------|--------|-----------|
| 2026-05-29 | Creación estructura de proyecto: dirs, `.claude/`, agents, rules, hooks, settings | ✅ 35 archivos creados |
| 2026-05-29 | Instalación entorno: Python 3.11.15, venv, dependencias `requirements.txt` | ✅ playwright 1.60, anthropic 0.105.2, pandas 3.0.3 |
| 2026-05-29 | Instalación Playwright Chromium 148 + FFmpeg | ✅ Browsers listos en `~/.cache/ms-playwright` |
| 2026-05-29 | Creación `src/scraper/quotes_scraper.py` | ✅ 50 citas extraídas de 5 páginas en 7.7s |
| 2026-05-29 | Creación `src/cleaner/enricher.py` | ✅ tool_use + retry exponencial + export CSV |
| 2026-05-29 | Creación `src/main.py` orquestador | ✅ pipeline E2E con flags `--skip-scrape` / `--skip-enrich` |
| 2026-05-29 | Instalación skills Tier 1: firecrawl-agent, data-pipeline, pytest-testing, pandas-data-analysis | ✅ 4 skills globales instaladas |
| 2026-05-29 | Creación `tests/` (conftest + test_scraper + test_enricher) | ✅ 39/39 tests en verde en 1.34s |
| 2026-05-29 | `git init` + commit inicial `467f760` | ✅ 35 archivos, 1345 líneas |
| 2026-05-29 | Creación `docs/CHRONICLE.md` con roadmap PoC | ✅ Este archivo |
| 2026-05-29 | Ejecución pipeline E2E completo (scraping + Claude API) | ✅ 50 registros enriquecidos en 31.9s → `data/output/dataset_20260529.csv` |
| 2026-05-29 | Revisión estratégica del roadmap: pivote a modelo DaaS | ✅ Fase 4 rediseñada (sin Docker/README cliente), Fase 3 añade LOPD, nueva Fase 5 entrega + visualización |
| 2026-05-29 | Creación `src/scraper/infojobs_scraper.py` | ⚠️ Bloqueado por Distil/Imperva enterprise anti-bot |
| 2026-05-29 | Pivote a Indeed.es: inspección de selectores CSS en vivo | ✅ `td.resultContent`, `a.jcs-JobTitle`, `[data-testid='company-name']` confirmados |
| 2026-05-29 | Creación `src/scraper/indeed_scraper.py` con selectores validados | ✅ 16 ofertas reales extraídas (título, empresa, ubicación). Fase 2 bloqueada por bot detection en detail pages → usar solo fase 1 |
| 2026-05-29 | Creación `src/cleaner/lead_enricher.py` con JSON schema B2B | ✅ ENRICH_TOOL de lead qualification + sanitización LOPD integrada |
| 2026-05-29 | Ejecución lead_enricher sobre 16 ofertas de Indeed | ✅ 4 HIGH · 1 MEDIUM · 2 LOW · 9 DISCARD · leads_20260529.csv generado en 17s |
| 2026-05-29 | Creación `src/delivery/sheets_exporter.py` (Fase 5.1) | ✅ Conector Google Sheets con Service Account, colores por score, cabecera fija |
