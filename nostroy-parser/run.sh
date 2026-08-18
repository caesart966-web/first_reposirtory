#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Запускалка для macOS и Linux.
#
# При первом запуске сама создаёт виртуальное окружение и ставит зависимости,
# дальше просто запускает разбор. Использование:
#
#     ./run.sh                          # спросит путь к файлу
#     ./run.sh "/путь/Реестр.rar"       # сразу с файлом
#     ./run.sh "/путь/Реестр.rar" --no-checko    # с любыми доп. ключами
# ---------------------------------------------------------------------------
set -e
cd "$(dirname "$0")"

# --- 1. Проверяем Python ---------------------------------------------------
PYTHON=""
for candidate in python3.13 python3.12 python3.11 python3.10 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
            PYTHON="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "ОШИБКА: не найден Python 3.10 или новее."
    echo "  macOS : brew install python@3.12"
    echo "  Ubuntu: sudo apt-get install python3 python3-venv"
    exit 1
fi
echo "Python: $("$PYTHON" --version)"

# --- 2. Готовим окружение (только при первом запуске) ----------------------
if [ ! -x ".venv/bin/python" ]; then
    echo "Первый запуск: создаю окружение и ставлю зависимости (пара минут)..."
    "$PYTHON" -m venv .venv
    ./.venv/bin/python -m pip install --upgrade pip --quiet
    ./.venv/bin/python -m pip install -r requirements.txt --quiet
    echo "Готово."
fi

# --- 3. Определяем, что разбирать ------------------------------------------
INPUT="$1"
if [ -n "$INPUT" ]; then
    shift
else
    echo
    echo "Перетащите сюда архив (.rar/.zip) или Excel-файл и нажмите Enter:"
    read -r INPUT
    # Терминал добавляет кавычки и экранирует пробелы — убираем.
    INPUT="${INPUT%\"}"; INPUT="${INPUT#\"}"
    INPUT="${INPUT%\'}"; INPUT="${INPUT#\'}"
    INPUT="$(printf '%s' "$INPUT" | sed 's/\\ / /g')"
fi

if [ ! -e "$INPUT" ]; then
    echo "ОШИБКА: файл или папка не найдены: $INPUT"
    exit 1
fi

# --- 4. Запускаем ----------------------------------------------------------
echo
./.venv/bin/python main.py --input "$INPUT" --output output "$@"
echo
echo "Результаты — в папке: $(pwd)/output"
