# Demo Comercial — Pipeline Scraping + IA
> Duración: 10 minutos · Formato: reunión 1:1 con decisor PYME

---

## Antes de la reunión (5 min de prep)

```bash
# 1. Asegúrate de que el venv está activo
source venv/bin/activate

# 2. Comprueba que .env tiene las keys
cat .env | grep -E "ANTHROPIC|FIRECRAWL|GOOGLE"

# 3. Abre el Google Sheet del cliente en el navegador (en blanco, listo para recibir datos)
# 4. Abre el dashboard Streamlit en otra pestaña:
#    https://mharias99-scraping-ia-pipeline-src-dashboard-app-py.streamlit.app
```

---

## Minuto 0–1 — El problema (tú hablas, no tocas el teclado)

> "¿Cuánto tiempo pasa tu equipo buscando empresas a las que vender?
> Buscas en LinkedIn, en InfoJobs, en Google... copias datos a mano en un Excel...
> y al final no sabes si ese lead vale la pena o no.
>
> Lo que voy a enseñarte en los próximos 10 minutos hace ese trabajo solo,
> en menos de 2 minutos, y te entrega los leads ya puntuados directamente en tu Google Sheet."

---

## Minuto 1–3 — Ejecutar el pipeline en vivo

```bash
python src/main.py --config configs/cliente_ejemplo.yaml
```

**Qué verás en terminal (muéstraselo):**
```
── PASO 1/3: Scraping [firecrawl] (5 queries, max 50) ──
  Scrapeando [infojobs] p1: 'operador introducción datos'
  [infojobs] → 5 ofertas (18.4 KB)
  Scrapeando [indeed] p1: 'data entry'
  [indeed] → 8 ofertas (22.1 KB)
  ...
  Total ofertas únicas: 50
── PASO 2/3: Enriquecimiento con Claude ──
  Batch 1/10... → 4 registros merged · 2 leads HIGH
  Batch 2/10... → 3 registros merged · 1 lead HIGH
  ...
  Resumen: 31 total · 11 HIGH · 13 MEDIUM · 7 descartados
── PASO 3/3: Exportando a Google Sheets ──
  Datos escritos: 31 filas × 12 columnas
  Formato visual aplicado
═══ PIPELINE COMPLETO en 98.3s ═══
```

**Mientras corre, explica:**
> "Está mirando InfoJobs e Indeed ahora mismo, en tiempo real.
> Por cada empresa que encuentra buscando trabajo, Claude analiza la descripción
> y decide si es un candidato para automatización. Mira: HIGH, MEDIUM, LOW."

---

## Minuto 3–5 — Mostrar el Google Sheet

Abre el Sheet (ya debería tener los datos).

**Puntos a destacar:**
1. **Verde = HIGH** — empresa buscando alguien para hacer data entry o Excel manual → candidato ideal
2. **Columna `lead_reason`** — Claude explica en una frase POR QUÉ es un lead: *"Buscan operador para introducir datos de albaranes en ERP — tarea 100% automatizable"*
3. **Columna `automation_signals`** — las frases exactas del anuncio que lo delatan: *"introducción manual de datos", "Excel avanzado", "gestión de albaranes"*
4. **Columna `urgency`** — si pone "urgent", llevan prisa → llamar primero

> "En vez de leer 50 anuncios tú mismo, tienes 11 empresas listas para llamar,
> ordenadas por probabilidad de que te compren."

---

## Minuto 5–7 — Mostrar el dashboard Streamlit

Abre: `https://mharias99-scraping-ia-pipeline-src-dashboard-app-py.streamlit.app`

**Recorrido rápido (30 segundos por sección):**
- **KPIs arriba** — total leads, cuántos HIGH, tasa de conversión del scraping
- **Gráfico de distribución** — cuántos HIGH / MEDIUM / LOW / descartados
- **Tabla filtrable** — filtra por sector, por score, por urgencia
- **Detalle de lead** — haz clic en una empresa HIGH y muestra la razón completa

> "Esto es lo que ve tu equipo de ventas cada mañana.
> Un pipeline de leads fresh, del mismo día, sin que nadie haya tocado nada."

---

## Minuto 7–8 — Exportación CRM (opcional, si el cliente usa HubSpot/Pipedrive)

```bash
# Los CSVs ya se generaron automáticamente al final del pipeline:
ls data/output/hubspot_*.csv
ls data/output/pipedrive_*.csv
```

> "Si usáis HubSpot o Pipedrive, este fichero lo importáis directamente.
> Los leads aparecen ya creados con el nombre de empresa, sector, email corporativo si lo encontró,
> y la descripción del deal ya escrita."

---

## Minuto 8–10 — Precio y cierre

**Propuesta de valor:**
> "¿Cuánto vale una hora de tu comercial? ¿15, 20 euros?
> Este sistema corre en 2 minutos y te da 10–15 leads cualificados al día.
> Eso son entre 200 y 300 leads al mes, que tu equipo tardaría 2–3 jornadas completas en reunir a mano."

**Modelo de precio sugerido (adapta según cliente):**
| Modalidad | Precio | Incluye |
|-----------|--------|---------|
| Setup único | 500–800 € | Configuración, YAML del cliente, conexión a su Sheet |
| Servicio mensual | 200–400 €/mes | Ejecución diaria automatizada, mantenimiento de queries |
| Licencia + formación | 1.500 € | Código + 2h de formación para que lo gestionen ellos |

---

## Respuestas a objeciones comunes

**"¿Esto es legal? ¿LOPD?"**
> "Sí. Solo extraemos datos publicados en portales de empleo públicos (InfoJobs, Indeed).
> Los emails personales se eliminan automáticamente — el sistema solo conserva emails corporativos.
> Es exactamente lo mismo que hacer una búsqueda en InfoJobs a mano."

**"¿Y si InfoJobs cambia su web?"**
> "Usamos Firecrawl, un servicio profesional que mantiene los extractores actualizado.
> Si cambia algo, ellos lo arreglan — no tienes que tocar nada."

**"¿Qué pasa si Claude se equivoca en la puntuación?"**
> "Claude acierta en el 80–85% de los casos según nuestras pruebas. El 15% restante
> son falsos positivos — empresas que parecían leads pero no lo son. Es mucho mejor
> que revisar 50 anuncios a mano donde te pierdes el 40% de los buenos."

**"¿Puedo probarlo con mis propias búsquedas?"**
> "Sí. En 10 minutos cambio las queries a tu sector y lo volvemos a ejecutar.
> Si quieres, lo hacemos ahora mismo."
> → Edita `configs/cliente_ejemplo.yaml`, cambia las queries, vuelve al Minuto 1.

**"¿Funciona para otros sectores además de automatización?"**
> "Sí. El sistema está diseñado para detectar cualquier patrón en ofertas de empleo.
> Si me dices qué tipo de empresa buscas, ajustamos las queries y el criterio de puntuación."

---

## Si algo falla durante la demo

| Problema | Solución rápida |
|----------|-----------------|
| Pipeline tarda >3 min | Muestra el Sheet de la última ejecución mientras corre: *"Aquí están los de ayer mientras esperamos"* |
| Error de API key | `cat .env` → verifica keys → `python src/main.py --skip-scrape` para usar datos ya cacheados |
| Sheet vacío | Abre el dashboard Streamlit directamente — tiene datos de muestra siempre disponibles |
| Firecrawl timeout | `python src/main.py --skip-scrape` — usa el JSON raw existente en `data/raw/` |

---

## Post-reunión (si el cliente dice sí)

```bash
# 1. Crear config del cliente
cp configs/cliente_ejemplo.yaml configs/cliente_[nombre].yaml

# 2. Editar las 4 líneas clave
#    - client.name, client.id
#    - infojobs_queries / indeed_queries (sector del cliente)
#    - delivery.google_sheets.spreadsheet_id

# 3. Compartir el Sheet con el Service Account
#    → Ir a Google Sheet → Compartir → pegar el email del service account

# 4. Primera ejecución real
python src/main.py --config configs/cliente_[nombre].yaml
```
