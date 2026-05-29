---
paths:
  - "data/**/*"
  - "src/main.py"
---

# Reglas — Manejo de Datos

- `data/raw/` solo contiene JSON sin procesar — nunca modificar manualmente
- `data/output/` solo contiene CSVs finales — son el artefacto entregable
- Nombres de archivo con timestamp: `quotes_raw_20260529.json`, `dataset_20260529.csv`
- Validar que el JSON de entrada no está vacío antes de pasar al cleaner
- El CSV final debe tener mínimo las columnas: `text`, `author`, `tags`, `category` (o las definidas en el schema de la API)
