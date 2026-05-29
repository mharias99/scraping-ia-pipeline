#!/bin/bash
# Después de editar un archivo .py: auto-formatea con ruff

FILE="$1"

if [[ "$FILE" != *.py ]]; then
  exit 0
fi

if [ ! -f "venv/bin/ruff" ]; then
  exit 0
fi

venv/bin/ruff format "$FILE" --quiet
venv/bin/ruff check "$FILE" --fix --quiet

exit 0
