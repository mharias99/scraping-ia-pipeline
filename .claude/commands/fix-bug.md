---
name: fix-bug
argument-hint: [descripcion-del-error o traceback]
---

Soluciona el bug: $ARGUMENTS
1. Analiza el traceback o descripción para identificar el archivo y línea exacta en `src/`.
2. Lee el archivo completo para entender el contexto.
3. Implementa la corrección mínima necesaria sin refactorizar código no relacionado.
4. Ejecuta `venv/bin/python src/main.py` (o el script relevante) para confirmar la solución.
5. Si existen tests en `tests/`, ejecuta `venv/bin/pytest tests/ -v` para confirmar que no hay regresiones.
6. Reporta: causa raíz, cambio aplicado, resultado de la verificación.
