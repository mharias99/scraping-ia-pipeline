---
paths:
  - "src/cleaner/**/*.py"
---

# Reglas — Módulo Cleaner (IA + Pandas)

- Usar `anthropic.Anthropic()` con la key desde `os.getenv("ANTHROPIC_API_KEY")`
- Forzar JSON estructurado usando `tool_use` o system prompt con schema explícito
- Siempre validar que la respuesta de la API es JSON parseable antes de continuar
- Manejar `anthropic.APIError` y `anthropic.RateLimitError` con retry exponencial
- DataFrames: eliminar duplicados con `drop_duplicates()`, normalizar strings con `.str.strip().str.lower()`
- Export CSV siempre con `index=False` y `encoding="utf-8"`
- Nunca loggear el contenido completo de las respuestas de la API (pueden ser grandes)
