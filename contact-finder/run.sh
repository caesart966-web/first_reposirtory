#!/usr/bin/env bash
# Запуск на Linux/macOS. Кладите список рядом как company_list.xlsx (или укажите свой).
set -e
cd "$(dirname "$0")"

IN="${1:-company_list.xlsx}"
OUT="${2:-contacts_result.xlsx}"

python3 -m pip install -r requirements.txt --quiet 2>/dev/null || true
python3 find_contacts.py --in "$IN" --out "$OUT" --delay 2 --verbose
