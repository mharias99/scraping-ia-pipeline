# Reglas de Programación Estrictas

- **Lenguaje y Tipos:** Usa Python 3.11+. Aplica Type Hints (ej: `def f(x: int) -> str:`) obligatoriamente en todas las funciones.
- **Manejo de Errores:** Nunca uses `print()`. Usa la librería `logging` (INFO/ERROR). 
- **Resiliencia:** Usa bloques `try/except` específicos para timeouts de red o elementos no encontrados.
- **Seguridad:** NUNCA escribas API keys en el código. Usa `os.getenv()`.
- **Estructura:** Código modular dividido en la carpeta `src/`.
