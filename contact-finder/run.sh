#!/usr/bin/env bash
# Запуск на macOS/Linux:  bash run.sh
cd "$(dirname "$0")"

command -v python3 >/dev/null 2>&1 || { echo "Не найден python3. Установите Python 3.9+"; exit 1; }

python3 -m pip install -r requirements.txt --quiet 2>/dev/null

IN="${1:-company_list.xlsx}"
OUT="${2:-contacts_result.xlsx}"

if [ ! -f "$IN" ]; then
  echo "Не найден файл «$IN»."
  echo "Положите список рядом и назовите company_list.xlsx (1-й столбец — название, 2-й — ИНН)."
  exit 1
fi

# Если рядом есть прошлый результат — пропускаем уже найденное, бережём лимит API.
SKIP=()
[ -f "Телефоны_компаний_по_ИНН.xlsx" ] && SKIP=(--only-missing "Телефоны_компаний_по_ИНН.xlsx")
[ -f "$OUT" ] && SKIP=(--only-missing "$OUT")

python3 find_contacts.py --in "$IN" --out "$OUT" --delay 2 --verbose "${SKIP[@]}"
