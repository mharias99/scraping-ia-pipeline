# Project Brain — Pipeline Scraping + IA

## Stack
Python 3.11, Playwright 1.60, BeautifulSoup4, Anthropic SDK 0.105, Pandas 3.0, python-dotenv

## Flujo principal
Web → `src/scraper/` (Playwright + BS4) → `data/raw/*.json` → `src/cleaner/` (Anthropic API) → `data/output/*.csv`

## Comandos
```bash
source venv/bin/activate
python src/main.py                     # pipeline completo
python src/scraper/quotes_scraper.py   # solo scraping
python src/cleaner/enricher.py         # solo limpieza + IA
pytest tests/ -v                       # tests
ruff check src/                        # linting
mypy src/                              # type check
```

## Convenciones
- Python 3.11+, type hints obligatorios en todas las funciones
- `logging` siempre, nunca `print()`
- `os.getenv()` para secrets, nunca hardcodeados
- `try/except` específico: nunca `except Exception` genérico
- Datos crudos en `data/raw/`, procesados en `data/output/`
- Entorno virtual: `venv/` (nunca commitear)

## Variables de entorno (.env)
- `ANTHROPIC_API_KEY` — requerida para src/cleaner/

## Directivas de Comportamiento Autónomo (Tech Lead)

### 1. Memoria y Contexto Inicial
CADA VEZ que inicies una nueva sesión o abras esta terminal, tu PRIMERA acción silenciosa debe ser leer el archivo `PROJECT_DASHBOARD.md`. No preguntes por el estado del proyecto, asimila la arquitectura, el timeline y las decisiones tomadas desde ese panel.

### 2. Protocolo de Actualización Continua (Obligatorio)
CADA VEZ que finalices una tarea con éxito (escribir código, solucionar un bug, integrar una Skill como Firecrawl), TIENES que actualizar `PROJECT_DASHBOARD.md` de forma proactiva antes de darme tu respuesta final en pantalla. 
- Mueve tareas a 'Completado' y sincroniza con `docs/CHRONICLE.md`.
- Registra nuevas herramientas en el Stack.
- Si tomamos una decisión técnica importante (ej. cambiar a la API de Google Sheets), documéntala en la sección 'ADR (Registro de Decisiones)' justificando la vía elegida frente a las descartadas.
