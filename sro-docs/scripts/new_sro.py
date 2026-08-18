# -*- coding: utf-8 -*-
"""Завести новую саморегулируемую организацию.

    python scripts/new_sro.py "СФЕРА-А"
    python scripts/new_sro.py "СИС" --name "Ассоциация ..." --city "Санкт-Петербург"

Создаёт папку sro/<название>/ с заготовкой настроек и пустой папкой
для бланков. Дальше:

  1. положите DOCX-бланки этой СРО в sro/<название>/templates/;
  2. впишите в них переменные вида {{inn}} (список — в config/variables.json);
  3. опишите документы в sro/<название>/sro.json.

Код программы менять не нужно.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORBIDDEN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

TEMPLATE_README = """Сюда положите бланки СРО «{short}» в формате DOCX.

Как подготовить бланк
---------------------
1. Откройте бланк в Word.
2. В местах, куда должны подставляться данные компании, впишите переменные.
   Например, вместо пропуска для ИНН напишите:  {{{{inn}}}}
   Полный список переменных — в файле config/variables.json,
   а таблица с пояснениями — в ИНСТРУКЦИЯ.md, раздел 7.
3. Сохраните файл в этой папке.
4. Опишите документ в файле sro.json (папкой выше), в разделе "documents".

Совет: положите рядом папку _originals и храните в ней исходные бланки
без изменений — как это сделано у СРО «СССС».
"""


def make_profile(short_name: str, name: str, city: str) -> dict:
    return {
        "_комментарий": [
            "Настройки одной саморегулируемой организации.",
            "Бланки лежат в папке templates рядом с этим файлом.",
            "Пока раздел documents пуст, программа скажет, что бланки не загружены.",
        ],
        "name": name,
        "short_name": short_name,
        "city": city,
        "note": "",
        "defaults": {
            "power_number": "б/н"
        },
        "auto_fill": {
            "actual_address": "legal_address",
            "postal_address": "legal_address"
        },
        "_комментарий_документы": [
            "На каждый бланк — свой блок:",
            '{ "id": "application", "title": "Заявление о вступлении",',
            '  "template": "01_Заявление.docx", "enabled": true }',
        ],
        "documents": [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Создать папку новой СРО")
    parser.add_argument("short_name", help="короткое название, оно же имя папки")
    parser.add_argument("--name", help="полное официальное название")
    parser.add_argument("--city", default="", help="город")
    parser.add_argument("--force", action="store_true",
                        help="перезаписать настройки, если папка уже есть")
    args = parser.parse_args(argv)

    short = args.short_name.strip()
    if not short or FORBIDDEN.search(short):
        print(f"Название «{short}» не годится для имени папки.", file=sys.stderr)
        return 2

    folder = ROOT / "sro" / short
    profile_path = folder / "sro.json"
    if profile_path.exists() and not args.force:
        print(f"СРО «{short}» уже заведена: {profile_path}\n"
              f"Чтобы перезаписать настройки, добавьте --force.", file=sys.stderr)
        return 1

    templates = folder / "templates"
    templates.mkdir(parents=True, exist_ok=True)

    profile = make_profile(short, (args.name or short).strip(), args.city.strip())
    profile_path.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    readme = templates / "ПРОЧТИ_МЕНЯ.txt"
    if not readme.exists():
        readme.write_text(TEMPLATE_README.format(short=short),
                          encoding="utf-8-sig", newline="\r\n")

    print(f"Создана СРО «{short}»")
    print(f"  настройки : {profile_path}")
    print(f"  бланки    : {templates}  (пока пусто)")
    print()
    print("Дальше: положите DOCX-бланки в папку бланков, впишите в них")
    print("переменные вида {{inn}} и опишите документы в sro.json.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
