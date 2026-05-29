#!/bin/bash
# Antes de guardar cualquier archivo .py: type check + lint
# Exit 2 = bloquea la acción. Exit 0 = permite continuar.

FILE="$1"

if [[ "$FILE" != *.py ]]; then
  exit 0
fi

if [ ! -f "venv/bin/ruff" ] || [ ! -f "venv/bin/mypy" ]; then
  exit 0
fi

venv/bin/ruff check "$FILE" --quiet || exit 2
venv/bin/mypy "$FILE" --ignore-missing-imports --quiet || exit 2

echo "Pre-save checks passed: $FILE"
exit 0
