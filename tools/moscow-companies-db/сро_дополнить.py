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
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


def _норм(h) -> str:
    return re.sub(r"\s+", "", str(h or "")).lower().replace("ё", "е")


def поле(заголовок) -> str | None:
    """Какое наше значение просит столбец заказчика."""
    н = _норм(заголовок)
    if "председател" in н:
        return "председатель"
    if "руководител" in н:
        return "руководитель"
    if "несост" in н and "проект" in н:
        return "не_в_проекте"
    if "несост" in н and ("изик" in н or "изыск" in н or "изыс" in н):
        return "не_в_изысканиях"
    return None


def руководители(пути: list[Path]) -> dict[str, str]:
    """Рег. номер → «ФИО, должность» из файлов после checko_контакты.py (поздний файл главнее)."""
    out = {}
    for путь in пути:
        ws = openpyxl.load_workbook(путь, read_only=True).active
        строки = ws.iter_rows(values_only=True)
        шапка = [str(c or "").strip() for c in next(строки)]
        for r in строки:
            z = dict(zip(шапка, r))
            номер, фио = str(z.get("Рег. номер") or "").strip(), str(z.get("Руководитель") or "").strip()
            if номер and фио:
                должность = str(z.get("Должность") or "").strip()
                out[номер] = f"{фио}, {должность[:1].lower() + должность[1:]}" if должность else фио
    return out


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


def дополнить(таблица: Path, пересечения: dict, пред: dict[str, dict], out: Path,
              рук: dict[str, str] | None = None) -> dict:
    рук = рук or {}
    wb = openpyxl.load_workbook(таблица)
    счёт = {"не_в_проекте": 0, "не_в_изысканиях": 0, "председатель": 0, "руководитель": 0, "без_данных": set()}
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
                if что == "руководитель":
                    # только пустые клетки: заполненное заказчиком не трогаем
                    if not ws.cell(i, j).value and рук.get(номер):
                        ws.cell(i, j, рук[номер])
                        счёт["руководитель"] += 1
                    continue
                if что == "председатель":
                    z = пред.get(номер) or {}
                    if z.get("Председатель совета"):
                        клетка = ws.cell(i, j, z["Председатель совета"])
                        счёт["председатель"] += 1
                        if str(z.get("Уверенность") or "") == "низкая":
                            # видно сразу в таблице, не открывая лист источников
                            клетка.comment = Comment(
                                "Низкая уверенность: старый документ или косвенное указание. "
                                "Источник — лист «Председатели — где найдено».", "проверка")
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
        if any(z.get("Уверенность") for z in пред.values()):
            шапка.insert(6, "Уверенность")
        if any(z.get("Сайт") for z in пред.values()):
            шапка.insert(2, "Сайт")              # где искать вручную тех, кого не нашли
        if any(z.get("Дата документа") for z in пред.values()):
            шапка.insert(шапка.index("Сайт: итог"), "Дата документа")   # найденные в протоколах
        w.append(шапка)
        for н, z in пред.items():
            w.append([н] + [z.get(к) or "" for к in шапка[1:]])
        for c in w[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="1F4E79")
            c.alignment = Alignment(wrap_text=True, vertical="center")
        ширина = {"Рег. номер": 20, "СРО": 36, "Сайт": 28, "Председатель совета": 34, "Как назван на сайте": 22,
                  "Где найдено": 40, "Фрагмент": 70, "Уверенность": 14, "Дата документа": 14, "Сайт: итог": 30}
        for j, h in enumerate(шапка):
            w.column_dimensions[get_column_letter(j + 1)].width = ширина.get(h, 20)
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
    ap.add_argument("--руководители", nargs="*", default=[], help="файлы после checko_контакты.py")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    пересечения = json.loads(Path(a.пересечения).read_text(encoding="utf-8")) if a.пересечения else {}
    счёт = дополнить(Path(a.таблица), пересечения, председатели(Path(a.председатели) if a.председатели else None),
                     Path(a.out), руководители([Path(x) for x in a.руководители]))
    print(счёт, "→", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
