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
