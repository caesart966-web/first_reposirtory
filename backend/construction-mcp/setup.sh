#!/usr/bin/env bash
# Ручная установка окружения backend'а (venv + зависимости + editable-пакет).
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 -m venv "$DIR/.venv"
"$DIR/.venv/bin/pip" install --upgrade pip
"$DIR/.venv/bin/pip" install -e "$DIR[dev]"
echo "OK: окружение готово в $DIR/.venv"
echo "Тесты:  $DIR/.venv/bin/python -m pytest -q"
echo "Демо:   $DIR/.venv/bin/python examples/demo_seed.py"
echo "Для реального анализа кадров: pip install -e '$DIR[vision]' и задайте ANTHROPIC_API_KEY"
