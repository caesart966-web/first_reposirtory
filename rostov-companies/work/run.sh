#!/bin/sh
# Запуск на macOS / Linux / Android (Termux):  sh run.sh   (параметры передаются дальше, например --limit 50)
cd "$(dirname "$0")" || exit 1
PY=python3
command -v python3 >/dev/null 2>&1 || PY=python
"$PY" -c 'import openpyxl' 2>/dev/null || "$PY" -m pip install --quiet --user openpyxl 2>/dev/null || "$PY" -m pip install --quiet openpyxl
exec "$PY" checko_status.py "$@"
