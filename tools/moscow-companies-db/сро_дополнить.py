"""Дописать в таблицу заказчика «не состоят в проекте / в изысках» и председателей советов.

Заказчик сам перестроил таблицу по России (листы «Регионы», «Руководители»,
«Стройка», «Проект», «Изыскания») и добавил пустые столбцы. Скрипт находит их
по смыслу заголовка — «Не состоят в проекте», «Не состоят в изиках» (так
у заказчика), «Председатель совета» — и заполняет по колонке «Рег. номер»,
не трогая остальное и оформление. Откуда взят каждый председатель — отдельным
листом «Председатели — где найдено» (страница сайта и фрагмент текста).

  python сро_дополнить.py --таблица СРО_России.xlsx --пересечения russia_2026_11/пересечения.json \\
         --председатели сро_председатели.xlsx --out СРО_России_дополнено.xlsx
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill


def _норм(h) -> str:
    return re.sub(r"\s+", "", str(h or "")).lower().replace("ё", "е")


def поле(заголовок) -> str | None:
    """Какое наше значение просит столбец заказчика."""
    н = _норм(заголовок)
    if "председател" in н:
        return "председатель"
    if "несост" in н and "проект" in н:
        return "не_в_проекте"
    if "несост" in н and ("изик" in н or "изыск" in н or "изыс" in н):
        return "не_в_изысканиях"
    return None


def председатели(путь: Path | None) -> dict[str, dict]:
    if not путь:
        return {}
    ws = openpyxl.load_workbook(путь, read_only=True).active
    строки = ws.iter_rows(values_only=True)
    шапка = [str(c or "") for c in next(строки)]
    out = {}
    for r in строки:
        z = dict(zip(шапка, r))
        if z.get("Рег. номер"):
            out[str(z["Рег. номер"]).strip()] = z
    return out


def дополнить(таблица: Path, пересечения: dict, пред: dict[str, dict], out: Path) -> dict:
    wb = openpyxl.load_workbook(таблица)
    счёт = {"не_в_проекте": 0, "не_в_изысканиях": 0, "председатель": 0, "без_данных": set()}
    for ws in wb.worksheets:
        шапка = [c.value for c in ws[1]]
        if "Рег. номер" not in [str(h or "").strip() for h in шапка]:
            continue
        кол_номер = [str(h or "").strip() for h in шапка].index("Рег. номер") + 1
        столбцы = {j + 1: поле(h) for j, h in enumerate(шапка) if поле(h)}
        for i in range(2, ws.max_row + 1):
            номер = str(ws.cell(i, кол_номер).value or "").strip()
            if not номер:
                continue
            for j, что in столбцы.items():
                if что == "председатель":
                    z = пред.get(номер) or {}
                    if z.get("Председатель совета"):
                        ws.cell(i, j, z["Председатель совета"])
                        счёт["председатель"] += 1
                else:
                    x = (пересечения.get("сро") or {}).get(номер)
                    if x is None:
                        счёт["без_данных"].add(номер)
                        continue
                    ws.cell(i, j, x.get(что, 0))
                    счёт[что] += 1
    if пред:
        if "Председатели — где найдено" in wb.sheetnames:
            del wb["Председатели — где найдено"]
        w = wb.create_sheet("Председатели — где найдено")
        шапка = ["Рег. номер", "СРО", "Председатель совета", "Как назван на сайте", "Где найдено",
                 "Фрагмент", "Сайт: итог"]
        w.append(шапка)
        for н, z in пред.items():
            w.append([н] + [z.get(к) or "" for к in шапка[1:]])
        for c in w[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="1F4E79")
            c.alignment = Alignment(wrap_text=True, vertical="center")
        for к, ш in zip("ABCDEFG", (20, 36, 34, 22, 40, 70, 22)):
            w.column_dimensions[к].width = ш
        w.freeze_panes = "B2"
        w.auto_filter.ref = w.dimensions
    wb.save(out)
    счёт["без_данных"] = sorted(счёт["без_данных"])
    return счёт


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--таблица", required=True)
    ap.add_argument("--пересечения", help="russia_2026_11/пересечения.json")
    ap.add_argument("--председатели", help="файл после председатели_сро.py")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    пересечения = json.loads(Path(a.пересечения).read_text(encoding="utf-8")) if a.пересечения else {}
    счёт = дополнить(Path(a.таблица), пересечения, председатели(Path(a.председатели) if a.председатели else None),
                     Path(a.out))
    print(счёт, "→", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
