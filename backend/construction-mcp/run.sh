#!/usr/bin/env bash
# Самобутстрапящийся запуск MCP-сервера construction-mcp.
# При первом старте создаёт .venv и ставит зависимости; далее сразу запускает сервер.
# ВАЖНО: весь бутстрап-вывод идёт в stderr — stdout принадлежит MCP-протоколу.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$DIR/.venv"

if [ ! -x "$VENV/bin/construction-mcp" ]; then
  echo "[construction-mcp] первичная установка окружения..." 1>&2
  python3 -m venv "$VENV" 1>&2
  "$VENV/bin/pip" install -q --upgrade pip 1>&2
  "$VENV/bin/pip" install -q -e "$DIR" 1>&2
  echo "[construction-mcp] окружение готово" 1>&2
fi

exec "$VENV/bin/construction-mcp"
