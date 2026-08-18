# -*- coding: utf-8 -*-
"""Вытащить уровни ответственности из бланка заявления в настройки СРО.

    python scripts/extract_levels.py

У строительных СРО уровней пять, у проектировщиков и изыскателей — четыре,
и суммы взносов совершенно разные. Держать их в коде нельзя: программа
предложила бы уровень, которого у СРО нет, и документ вышел бы неверным.
Поэтому уровни читаются прямо из бланка и записываются в sro/<СРО>/sro.json.
"""

from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.docx_engine import W  # noqa: E402


def cell_text(tc) -> str:
    parts = ("".join(t.text or "" for t in p.iter(W + "t")) for p in tc.iter(W + "p"))
    return re.sub(r"\s+", " ", " ".join(x for x in parts if x.strip())).strip()


def level_tables(root) -> list[list[list[str]]]:
    """Все таблицы, похожие на таблицу уровней ответственности.

    У СИС таблица уровней вложена в «обёртку» 1×1. Обёртку пропускаем:
    иначе вся таблица читается как одна ячейка и уровней не видно.
    """
    found = []
    for table in root.iter(W + "tbl"):
        rows = table.findall(W + "tr")
        if not rows:
            continue
        cells = rows[0].findall(W + "tc")
        if not cells:
            continue
        if any(cell.find(".//" + W + "tbl") is not None for cell in cells):
            continue                      # это обёртка, настоящая таблица внутри
        head = [cell_text(tc) for tc in cells]
        if not head or "Уровн" not in head[0] or len(rows) < 2:
            continue
        found.append([[cell_text(tc) for tc in r.findall(W + "tc")] for r in rows])
    return found


NUMBER_WORDS = ["Первый", "Второй", "Третий", "Четвертый", "Пятый"]


def to_levels(rows: list[list[str]]) -> list[dict]:
    """Строки таблицы → список уровней."""
    levels = []
    for row in rows[1:]:
        if len(row) < 3 or not row[0].strip():
            continue
        title = row[0].strip()
        key = str(NUMBER_WORDS.index(title) + 1) if title in NUMBER_WORDS else str(len(levels) + 1)
        levels.append({"key": key, "title": title,
                       "limit": row[1].strip(), "fee": row[2].strip()})
    return levels


def main() -> int:
    changed = 0
    for folder in sorted((ROOT / "sro").iterdir()):
        if not folder.is_dir():
            continue
        blanks = sorted((folder / "templates" / "_originals").glob("Заявление*.docx"))
        if not blanks:
            print(f"{folder.name}: бланка заявления нет, пропускаю")
            continue
        root = etree.fromstring(
            zipfile.ZipFile(blanks[0]).read("word/document.xml"))
        tables = level_tables(root)
        if len(tables) < 2:
            print(f"{folder.name}: таблиц уровней найдено {len(tables)}, ожидалось 2 — пропускаю")
            continue

        profile_path = folder / "sro.json"
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        profile["_комментарий_уровни"] = [
            "Уровни ответственности взяты из бланка заявления этой СРО.",
            "harm — компенсационный фонд возмещения вреда,",
            "contract — компенсационный фонд обеспечения договорных обязательств.",
            "У строительных СРО уровней пять, у проектировщиков и изыскателей четыре.",
            "Пересобрать: python scripts/extract_levels.py",
        ]
        profile["levels"] = {
            "harm": to_levels(tables[0]),
            "contract": to_levels(tables[1]),
        }
        profile_path.write_text(
            json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        harm = profile["levels"]["harm"]
        print(f"{folder.name}: уровней {len(harm)} "
              f"(первый — {harm[0]['limit']}, взнос {harm[0]['fee']})")
        changed += 1
    print(f"\nОбновлено СРО: {changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
