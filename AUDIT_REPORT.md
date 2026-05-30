# AUDIT REPORT — Motor de Captación de Leads (3 Verticales)
> Auditoría pre-entrega · 2026-05-30 · Solo lectura — sin modificaciones al código

---

## 1. Resumen ejecutivo

### Estado de cada vertical

| Vertical | Estado | Para demo | Para cliente de pago |
|----------|--------|-----------|----------------------|
| B2B Leads (empleo) | 🟢 Madura | ✅ Sí | ⚠️ Sí, con condiciones menores |
| Auditoría Digital (PYMEs) | 🟡 Funcional | ✅ Sí | ⚠️ Necesita tests + validación legal |
| Arbitraje Coches | 🔴 Prototipo | ⚠️ Solo con datos reales previos | ❌ No — scraper no verificado en producción |

### Top 3 riesgos

1. **🔴 `data/seen/` no está en `.gitignore`** — Si se hace `git add .`, los archivos con historial de URLs de clientes reales se suben al repositorio público/compartido.
2. **🔴 `requirements.txt` sin versiones fijadas** — `anthropic>=0.30.0`, `firecrawl-py>=1.0.0`, etc. Un `pip install` en 3 meses puede traer breaking changes que rompan el pipeline en producción sin previo aviso.
3. **🟠 Arbitraje coches depende de mediana estadística con N potencialmente muy bajo** — Si Milanuncios devuelve <5 anuncios de un modelo en un rango de precio, la mediana no es significativa y generará HIGH falsos positivos.

### Top 3 oportunidades

1. **Motor genérico reutilizable al 65%** — El núcleo (config, sheets, crm, seen tracker, dashboard, stats) está completamente compartido. Añadir un cuarto vertical (ej. inmobiliaria, restaurantes) costaría 2-3 días, no semanas.
2. **Vertical Digital tiene el mejor ratio riesgo/retorno** — Scoring V2 con gate automático (no gasta Firecrawl en negocios bien establecidos), call_script personalizado por Claude, cero dependencia de portales de empleo con ToS restrictivos.
3. **Feedback loop de conversiones como moat defensivo** — Si se añade columna "Cerrado €" al Sheet del cliente y se lee periódicamente, el pipeline puede aprender qué señales predicen un cierre real. Ningún competidor pequeño tendrá ese dato.

---

## 2. Mapa de arquitectura

### Motor común vs específico

```
src/
├── main.py              ← ORQUESTADOR COMÚN (100% compartido)
├── config.py            ← CONFIG COMÚN (100% compartido)
├── scraper/
│   ├── firecrawl_scraper.py   ← B2B específico
│   ├── apify_scraper.py       ← B2B específico (volumen)
│   ├── cars_scraper.py        ← Cars específico
│   ├── gmaps_scraper.py       ← Digital específico
│   └── web_inspector.py       ← Digital específico
├── cleaner/
│   ├── lead_enricher.py       ← B2B específico (Claude tool_use)
│   ├── cars_enricher.py       ← Cars específico (Python puro, SIN IA)
│   └── digital_enricher.py    ← Digital específico (Claude + scoring Python)
└── delivery/
    ├── sheets_exporter.py     ← COMÚN (100% compartido, soporta los 3)
    ├── crm_exporter.py        ← COMÚN (solo B2B actualmente)
    ├── dashboard_builder.py   ← COMÚN (3 configs, 1 builder)
    ├── seen_tracker.py        ← COMÚN (100% compartido)
    └── stats_exporter.py      ← COMÚN (100% compartido)
```

**Estimación de código compartido: ~65%** del total de líneas es motor común reutilizado.
Cada vertical añade ~250-400 líneas de código específico (scraper + enricher).

### Flujo de datos por vertical

**B2B Leads:**
```
configs/demo_b2b.yaml
  → main.py step_scrape()
    → firecrawl_scraper.py (InfoJobs + Indeed, Firecrawl bypass anti-bot)
    → apify_scraper.py (InfoJobs + Indeed, volumen masivo)
    → data/raw/demo_b2b_raw.json
  → main.py step_enrich() → _enrich_b2b()
    → lead_enricher.py (Claude Haiku tool_use, batch=5)
    → JSON schema: lead_score, lead_reason, automation_signals, outreach_email
    → data/output/leads_demo_b2b_YYYYMMDD.csv
  → stats_exporter.py → data/web/stats.json (dashboard Next.js)
  → main.py step_sheets()
    → seen_tracker.filter_new() (dedup entre ejecuciones)
    → sheets_exporter.append_new_leads() → Google Sheet
    → dashboard_builder.build_b2b_dashboard() → tab "📊 Dashboard"
  → crm_exporter.run_crm_export() → hubspot_*.csv + pipedrive_*.csv
```

**Arbitraje Coches:**
```
configs/demo_cars.yaml
  → main.py step_scrape()
    → cars_scraper.py (Apify actor zen-studio/milanuncios-scraper)
    → data/raw/demo_cars_raw.json
  → main.py step_enrich() → _enrich_cars()
    → cars_enricher.py (Python puro, SIN Claude)
      · Extrae año y km con regex del título
      · Calcula mediana de precio por (modelo, año_bucket, km_bucket)
      · Marca HIGH si precio < mediana * (1 - threshold)
    → data/output/cars_demo_cars_YYYYMMDD.csv
  → stats_exporter.py + sheets_exporter.py + dashboard_builder (cars config)
  → [CRM export: solo B2B, coches NO genera hubspot/pipedrive]
```

**Auditoría Digital:**
```
configs/demo_digital.yaml
  → main.py step_scrape()
    → gmaps_scraper.py (Apify actor compass/crawler-google-places)
    → data/raw/demo_digital_raw.json
  → main.py step_enrich() → _enrich_digital()
    → digital_enricher.py
      · maps_score_v2(): scoring Python puro (0-50) sobre rating y reseñas
      · Gate auto-descarte: rating≥4.5 AND reviews≥100 → skip Firecrawl
      · web_inspector (Firecrawl) → HTTPS, reservas, pixel Meta/GA
      · web_score(): scoring Python puro (0-50) sobre resultado web
      · Claude Haiku: genera weaknesses + call_script (JSON)
      · Banda final: HIGH≥60 · MEDIUM 40-59 · LOW<40
    → data/output/digital_demo_digital_YYYYMMDD.csv
  → stats_exporter.py + sheets_exporter.py + dashboard_builder (digital config)
```

### Duplicación entre verticales que debería factorizarse

| Patrón duplicado | Archivos afectados | Impacto |
|------------------|--------------------|---------|
| `_get_client() → ApifyClient(os.getenv("APIFY_API_TOKEN"))` | `cars_scraper.py`, `gmaps_scraper.py`, `apify_scraper.py` | Bajo |
| `load_dotenv()` al inicio del módulo | `lead_enricher.py`, `digital_enricher.py`, `cars_scraper.py`, `gmaps_scraper.py` | Bajo |
| `OUTPUT_DIR = Path("data/output")` | `lead_enricher.py`, `cars_enricher.py`, `digital_enricher.py` | Bajo |
| `MAX_RETRIES = 3` + retry exponencial | `lead_enricher.py`, `digital_enricher.py` | Medio — si se corrige en uno, el otro queda sin parchar |
| Patrón de batching por IA (chunklist + sleep) | `lead_enricher.py`, `digital_enricher.py` | Medio — misma lógica, dos implementaciones |

---

## 3. Hallazgos técnicos

| Sev | Vertical | Descripción | Estado |
|-----|----------|-------------|--------|
| 🔴 | Todos | **`data/seen/` no está en `.gitignore`** | ✅ CORREGIDO |
| 🔴 | Todos | **`requirements.txt` sin versiones fijadas** | ✅ CORREGIDO — 99 paquetes fijados con pip freeze |
| 🟠 | Cars | **Mediana calculada sobre N<5** — falsos positivos HIGH | ✅ CORREGIDO — `MIN_SAMPLE_SIZE=5`, grupos pequeños → UNKNOWN |
| 🟠 | Cars | **Scraper Milanuncios sin validar en producción** | ⚙️ OPERACIONAL — requiere ejecución real con datos vivos |
| 🟠 | Digital | **`web_inspector.py` sin reintentos** | ✅ CORREGIDO — 1 reintento con backoff exponencial |
| 🟠 | Todos | **`configs/demo_*.yaml` con spreadsheet IDs** | ✅ MITIGADO — comentario de aviso añadido en los 3 configs |
| 🟡 | B2B | **Dedup por `company\|title` en lugar de URL** | ✅ CORREGIDO — prioriza URL; fallback a company\|title |
| 🟡 | Digital | **`permanently_closed` sin filtrar** | ✅ CORREGIDO |
| 🟡 | Cars/Digital | **CRM export genera CSVs B2B para otros pipelines** | ✅ CORREGIDO — solo ejecuta para `b2b_leads` |
| 🟡 | Todos | **`data/web/stats.json` no en `.gitignore`** | ✅ CORREGIDO |
| 🟡 | Todos | **`data/seen/` no compartido entre máquinas** | ⚙️ ARQUITECTURAL — requiere Redis/DB para multi-máquina |
| 🟡 | Todos | **`MAX_RETRIES` + retry duplicado entre enrichers** | ✅ CORREGIDO — `src/cleaner/_claude_retry.py` compartido |
| 🟢 | B2B | **`enricher.py` (legacy) coexiste con `lead_enricher.py`** | ✅ CORREGIDO — movido a `src/cleaner/legacy/` |
| 🟢 | Todos | **0 tests para Cars y Digital** | ✅ CORREGIDO — 29 tests nuevos (100 total en verde) |
| 🟢 | Todos | **Scrapers legacy en `src/scraper/`** | ✅ CORREGIDO — movidos a `src/scraper/legacy/` |

### Seguridad y secretos
- ✅ `.env` en `.gitignore` — OK
- ✅ `credentials/` en `.gitignore` — OK
- ✅ ANTHROPIC_API_KEY solo vía `os.getenv()` — OK
- ✅ Sanitización LOPD de emails personales — OK (B2B)
- ⚠️ `data/seen/` **NO** en `.gitignore` — Riesgo real
- ⚠️ `data/web/stats.json` **NO** en `.gitignore`

### Estimación de coste por vertical (por ejecución)

| Vertical | Coste Claude | Coste Firecrawl | Coste Apify | Total estimado |
|----------|-------------|-----------------|-------------|----------------|
| B2B (100 ofertas) | ~$0.003-0.005 | ~10 créditos | ~$0.002 | **~$0.007-0.010** |
| Cars (7 modelos × 50) | $0 (sin IA) | 0 | ~$0.005 | **~$0.005** |
| Digital (125 negocios) | ~$0.002-0.004 | ~30 créditos (30% pasan el gate) | ~$0.003 | **~$0.007-0.010** |

---

## 4. Checklist pre-entrega por vertical

### B2B Leads
- ✅ Pipeline E2E validado (100 ofertas → 55 leads → Sheet en 246s)
- ✅ Firecrawl bypass anti-bot InfoJobs + Indeed
- ✅ Claude Haiku tool_use con JSON schema + retries via `_claude_retry.py`
- ✅ Sanitización LOPD de emails personales
- ✅ Deduplicación entre ejecuciones (seen_tracker)
- ✅ Dedup cross-source mejorada (prioriza URL sobre company|title)
- ✅ Dashboard Google Sheets especializado (recreado en cada run)
- ✅ Export HubSpot + Pipedrive CSV (solo B2B)
- ✅ `data/seen/` y `data/web/stats.json` en `.gitignore`
- ✅ `requirements.txt` con versiones exactas (pip freeze)
- ✅ Scrapers legacy movidos a `src/scraper/legacy/`
- ✅ 100 tests en verde
- ⚙️ Validar que el cliente tiene acceso al Sheet antes de la demo

**Veredicto: ✅ LISTA — todos los blockers corregidos**

---

### Auditoría Digital (PYMEs)
- ✅ Scoring V2 Python puro (0-100) sin gastar IA en descartados
- ✅ Gate auto-descarte (rating≥4.5 AND reviews≥100) para no gastar Firecrawl
- ✅ `permanently_closed` filtrado antes del scoring
- ✅ `web_inspector.py` con timeout 30s + 1 reintento con backoff
- ✅ Claude Haiku genera call_script personalizado con datos reales
- ✅ Dashboard Google Sheets especializado (call-ready list, debilidades, sectores)
- ✅ 15 smoke tests del scoring, gate, dedup y filtro de cerrados
- ⚙️ Validar manualmente call_scripts en 10 casos reales antes de la demo
- ⚙️ Confirmar que el actor `compass/crawler-google-places` funciona en producción con queries en español
- ⚙️ Revisión legal de ToS de Google Maps para uso comercial

**Veredicto: ✅ LISTA CON CONDICIÓN OPERACIONAL — validar call_scripts manualmente**

---

### Arbitraje Coches
- ✅ Algoritmo de arbitraje (mediana por grupo) sólido conceptualmente
- ✅ Guard N<5: grupos con muestra insuficiente → UNKNOWN (no falsos HIGH)
- ✅ Regex para año y km funcionales
- ✅ Dashboard Google Sheets especializado (margen €, modelos, análisis precio)
- ✅ CRM export no genera CSVs incorrectos (skip para Cars)
- ✅ 14 tests del enricher en verde
- ❌ Scraper (`zen-studio/milanuncios-scraper`) no verificado en producción reciente
- ⚙️ Validar actor Apify con datos vivos antes de la demo
- ⚙️ Revisar ToS de Milanuncios para uso comercial

**Veredicto: ⚠️ LISTA CON CONDICIÓN OPERACIONAL — ejecutar una vez en producción antes de vender**

---

## 5. Quick wins y roadmap

### Quick wins (alto impacto, bajo esfuerzo)

| Impacto | Esfuerzo | Acción |
|---------|----------|--------|
| 🔴 Alto | 5 min | Añadir `data/seen/` y `data/web/stats.json` a `.gitignore` |
| 🔴 Alto | 10 min | `pip freeze > requirements.txt` en el entorno de producción — fijar versiones exactas |
| 🟠 Alto | 15 min | Filtrar `permanently_closed == True` en `digital_enricher.py` antes del scoring |
| 🟠 Alto | 20 min | Guard `if n < MIN_SAMPLE_SIZE: skip` en `cars_enricher.py` para grupos con <5 anuncios |
| 🟡 Medio | 30 min | Deshabilitar o mover scrapers legacy (`quotes_scraper`, `infojobs_scraper`, `indeed_scraper`) |
| 🟡 Medio | 30 min | Fix `crm_exporter.py` para no ejecutarse en pipelines Cars/Digital (o hacer mapeo correcto) |
| 🟡 Medio | 1h | Extraer `_get_client() → ApifyClient` a `src/scraper/_apify_base.py` para eliminar duplicación |
| 🟢 Bajo | 1h | Smoke tests mínimos para `cars_enricher.py` y `digital_enricher.py` (cobertura básica) |

### Mejoras de producto (futuro)

| Vertical | Mejora | Impacto | Esfuerzo | Riesgo |
|----------|--------|---------|----------|--------|
| B2B | Detectar si la vacante lleva >30 días publicada (republicación = empresa con dificultad para cubrir → lead más caliente) | Alto | Medio | Bajo |
| B2B | Enriquecer con LinkedIn company profile (tamaño real, sector, noticias recientes) | Alto | Alto | Medio (ToS LinkedIn) |
| Digital | Añadir análisis de redes sociales (Instagram/Facebook activos o no) | Medio | Medio | Bajo |
| Digital | Score de competencia local (si hay 10 dentistas en 500m con 4.8★, el lead es más difícil de cerrar) | Alto | Alto | Bajo |
| Cars | Histórico de precio del anuncio (si lleva 30 días y bajó precio = vendedor motivado) | Alto | Medio | Bajo |
| Cars | Comparar km vs mercado (no solo precio) para detectar coches sobrekilometrados vendidos a precio de mercado | Medio | Medio | Bajo |
| Todos | Feedback loop: columna "Cerrado €" en Sheet → pipeline aprende qué señales predicen cierre real | Muy Alto | Medio | Bajo |
| Todos | Envío automático diario (cron + email/Slack con resumen de leads nuevos) | Alto | Bajo | Bajo |

### Cuarto vertical más fácil de añadir

**Restaurantes y hostelería** — mismo motor que Digital (Apify Google Maps + web inspector + Claude), mismo scoring de presencia digital, mismo Sheet de salida. Cambio: queries de búsqueda, sector específico, call_script con argumentos de hostelería. **Estimado: 1 día de trabajo**, reutilizando el 95% del código de Digital.

---

## 6. Análisis de monetización

### Vertical 1 — B2B Leads (Empleo)
**A quién venderlo:** ETT (empresas de trabajo temporal) y agencias de RRHH que quieren acceder a empresas con vacantes activas para ofrecerles cubrir la posición.

| Modelo | Precio orientativo | Pros | Contras |
|--------|-------------------|------|---------|
| Pay-per-lead HIGH | €3-8/lead | Alineado al riesgo del cliente, fácil de vender | Ingresos variables, cliente descarta leads sin pagar |
| Suscripción mensual | €150-400/mes (50-150 leads HIGH) | Recurrente y predecible | Necesitas volumen constante |
| Setup fee + recurrente | €500 setup + €200/mes | Compromiso del cliente, cubre costes iniciales | Más difícil de cerrar |
| White-label (agencia revende) | €400-800/mes por zona/sector | Multiplica sin trabajo extra | Dependencia de un solo canal |

**Precio recomendado para arrancar:** €5/lead HIGH (pago por lead), mínimo 20 leads/mes. Equivale a €100/mes — umbral muy bajo para que una ETT justifique la prueba.

---

### Vertical 2 — Arbitraje Coches
**A quién venderlo:** Concesionarios de segunda mano o particulares que compran coches para revender. En España hay ~15.000 concesionarios y miles de compraventeros autónomos.

| Modelo | Precio orientativo | Pros | Contras |
|--------|-------------------|------|---------|
| Pay-per-lead HIGH | €10-25/oportunidad | Alto valor por operación (márgen típico €1.500-5.000) | Necesita validación real antes de vender |
| Suscripción por zona | €200-500/mes (modelo + radio 100km) | Exclusividad geográfica es atractiva | Comprador puede encontrar el coche antes de actuar |
| Alerta en tiempo real (Slack/email) | +€50/mes sobre suscripción | Diferenciador fuerte (velocidad = ventaja) | Requiere integración adicional |

**Precio recomendado:** €300/mes por zona exclusiva + modelo específico. Equivale a margen de 1 solo coche vendido en el mes.

⚠️ Esta vertical necesita más trabajo técnico antes de vender (ver sección 4).

---

### Vertical 3 — Auditoría Digital (PYMEs)
**A quién venderlo:** Agencias de marketing local, freelances de diseño web, agencias SEO que necesitan clientes con "dolor digital" activo.

| Modelo | Precio orientativo | Pros | Contras |
|--------|-------------------|------|---------|
| Pay-per-lead HIGH | €5-15/lead | Fácil de justificar (agencia cierra 1 cliente = factura €500-2.000) | Competencia de directorios de empresas |
| Pack mensual por ciudad/sector | €200-600/mes (40-80 HIGH) | Exclusividad por sector es muy vendible | Saturación si varios compradores ven los mismos leads |
| White-label para agencias | €800-1.500/mes (acceso API + panel) | Escalable, el comprador vende a sus clientes | Requiere más desarrollo (panel para el cliente) |
| Informe de auditoría para la PYME | €29-99/auditoría directa a la PYME | Canal alternativo sin intermediario | Difícil de escalar |

**Precio recomendado:** €15/lead HIGH, mínimo mensual €200. Para una agencia de marketing que cierra 1 cliente de cada 10 llamadas, €150 en leads = 1 cliente cerrado = ROI inmediato.

---

### Recomendación: por dónde empezar

**Empezar por Auditoría Digital**, en ese orden:

1. **Digital primero** — Menor riesgo legal (negocios públicos en Google Maps vs. datos de empleados), mayor demanda observable (las agencias de marketing están hambrientas de leads), call_script generado por IA es el diferenciador que ningún competidor tiene. Ciclo de venta corto: el cliente ve el lead, llama, cierra. El ROI es inmediato y medible.

2. **B2B segundo** — ETTs y agencias RRHH son clientes corporativos con presupuesto estructurado, pero el ciclo de venta es más largo. Aun así, el mercado es enorme y la vertical está lista.

3. **Cars tercero** — Necesita más trabajo técnico antes de vender. El mercado es real pero los compradores (compraventeros, concesionarios) son más escépticos con tecnología.

### Defendibilidad del negocio

- **Datos de feedback de conversiones** — Después de 6 meses con clientes reales, tienes señales de qué leads cierran. Imposible de copiar sin ese historial.
- **Integración profunda con Sheets del cliente** — El cliente empieza a vivir en tu Sheet, lo personaliza, forma a su equipo. Coste de cambio alto.
- **Exclusividad por zona/sector** — Si vendes a una agencia de marketing la exclusiva de "dentistas en Madrid", ningún competidor puede venderle lo mismo.
- **Velocidad de ejecución** — El pipeline corre en <5 min. Un competidor que scrape manualmente tarda horas.

---

## 7. Veredicto final

| Vertical | Estado técnico | Listo para cliente | Bloqueante pendiente |
|----------|---------------|-------------------|---------------------|
| B2B Leads | 🟢 Maduro | ✅ SÍ | Ninguno — todos corregidos |
| Auditoría Digital | 🟢 Funcional | ✅ SÍ (con validación manual) | Validar call_scripts en 10 casos reales antes de la demo |
| Arbitraje Coches | 🟡 Prototipo corregido | ⚠️ SÍ (con ejecución de prueba) | Ejecutar scraper Milanuncios en producción y verificar datos |

### Acciones inmediatas antes de cualquier demo con cliente real

```bash
# 1. Fijar versiones (5 min)
pip freeze > requirements.txt

# 2. Actualizar .gitignore (2 min)
echo "data/seen/" >> .gitignore
echo "data/web/stats.json" >> .gitignore

# 3. Validar call_scripts Digital en 10 casos reales
python src/main.py --config configs/demo_digital.yaml --skip-scrape
# revisar data/output/digital_demo_digital_*.csv columna call_script

# 4. Probar Cars en producción
python src/main.py --config configs/demo_cars.yaml
# verificar que el actor de Apify funciona y devuelve precios correctos
```

---

*Informe generado por revisión de código estática + análisis de arquitectura · 2026-05-30*
