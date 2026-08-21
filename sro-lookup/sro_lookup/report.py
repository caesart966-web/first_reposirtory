"""Запись результата: одна строка на членство в СРО."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

COLUMNS: list[tuple[str, int]] = [
    ("Название компании", 44),
    ("ИНН", 15),
    ("СРО", 52),
    ("Рег. номер СРО", 22),
    ("Реестр", 12),
    ("Статус членства", 24),
    ("Дата вступления", 16),
    ("Результат проверки", 34),
]

FONT = "Arial"
HEADER_FILL = PatternFill("solid", fgColor="1F3864")
#: Компания не состоит ни в одной СРО — розовая заливка.
NO_SRO_FILL = PatternFill("solid", fgColor="FCE9E9")
#: Проверка не состоялась — жёлтая: это не ответ, а повод перезапустить.
UNCHECKED_FILL = PatternFill("solid", fgColor="FFF4CE")
THIN = Side(style="thin", color="D0D7E5")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def write_report(rows: list[dict], path: Path, checked_on: date) -> None:
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "Членство в СРО"

    for index, (title, width) in enumerate(COLUMNS, start=1):
        cell = sheet.cell(1, index, title)
        cell.font = Font(name=FONT, size=10, bold=True, color="FFFFFF")
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER
        sheet.column_dimensions[get_column_letter(index)].width = width
    sheet.row_dimensions[1].height = 28

    for line, row in enumerate(rows, start=2):
        values = [
            row["name"], row["inn"], row["sro"], row["number"],
            row["registry"], row["status"], row["join"], row["note"],
        ]
        for index, value in enumerate(values, start=1):
            cell = sheet.cell(line, index, value)
            cell.font = Font(name=FONT, size=10)
            cell.border = BORDER
            cell.alignment = Alignment(
                vertical="top",
                wrap_text=index in (1, 3, 8),
                horizontal="center" if index in (2, 4, 5, 7) else "left",
            )
            if row.get("unchecked"):
                cell.fill = UNCHECKED_FILL
            elif not row["sro"]:
                cell.fill = NO_SRO_FILL
        sheet.cell(line, 2).number_format = "@"
        sheet.cell(line, 7).number_format = "DD.MM.YYYY"

    note = sheet.cell(
        len(rows) + 3, 1,
        "Источник: открытые реестры reestr.nostroy.ru (строители) и "
        f"reestr.nopriz.ru (проектировщики, изыскатели). Проверено {checked_on.strftime('%d.%m.%Y')}. "
        "Жёлтые строки — проверка не выполнена, реестр не ответил: их нужно перезапустить.",
    )
    note.font = Font(name=FONT, size=9, italic=True)

    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:{get_column_letter(len(COLUMNS))}1"
    book.save(path)
